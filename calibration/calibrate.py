"""Bounded TRAIN-only search; development seeds averaged, final seeds fixed."""
import json,time,hashlib
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import qmc,t
from simulation.training_data import ROOT,require_train,load_inputs
from simulation.parameters import IDMParameters
from simulation.model import run_baseline
from .objective import TrainTargets
from .diagnostics import estimate_parameters,figures

NAMES=['v0','T','s0','a','b']
def initialize_worker(queue_gap):
    global TARGET,INPUTS,GAP
    TARGET=TrainTargets();INPUTS=load_inputs();GAP=queue_gap

def evaluate_worker(job):
    values,seed=job
    start=time.perf_counter()
    model=run_baseline(INPUTS,IDMParameters(**dict(zip(NAMES,values))),seed=seed,queue_gap=GAP)
    return {'seed':seed,**model.summary,**TARGET.errors(model),'runtime_s':time.perf_counter()-start}

def main(acquisition='B2'):
    require_train(acquisition)
    initial,bounds,gap=estimate_parameters();target=TrainTargets();inputs=load_inputs()
    limits=np.array([bounds[n] for n in NAMES]);low=limits[:,0];span=limits[:,1]-low
    criteria=json.loads((ROOT/'docs/b2_estimation_criteria.json').read_text())
    seeds=criteria['calibration_seeds'];logs=[];candidate=0;best=[float('inf'),None]
    fingerprint=hashlib.sha256(b''.join(p.read_bytes() for folder in ['simulation','calibration'] for p in sorted((ROOT/folder).glob('*.py')))).hexdigest()
    search={'training_acquisition':'B2','development_seeds':seeds,'final_seeds':criteria['final_train_seeds'],
        'latin_hypercube_candidates':16,'search_seed':20261009,'powell_maxfev':40,'coordinate_scale':'unit empirical bounds',
        'selection':'minimum fixed-seed mean objective; no seed selection','code_sha256':fingerprint,'B1_LOCKED':True}
    (ROOT/'outputs/b2_search_plan.json').write_text(json.dumps(search,indent=2),encoding='utf-8')
    with ProcessPoolExecutor(max_workers=3,initializer=initialize_worker,initargs=(gap,)) as pool:
        def objective(z):
            nonlocal candidate
            z=np.clip(z,0,1);values=low+span*z;candidate+=1
            results=list(pool.map(evaluate_worker,[(values.tolist(),seed) for seed in seeds]))
            score=float(np.mean([r['objective'] for r in results]))
            for r in results:logs.append({'candidate':candidate,'stage':'development','acquisition':'B2',**dict(zip(NAMES,values)),**r,'code_sha256':fingerprint})
            pd.DataFrame(logs).to_csv(ROOT/'outputs/b2_calibration_runs.csv',index=False)
            if score<best[0]:best[:]=[score,values.copy()]
            print(f'Candidate {candidate:03d}: mean objective={score:.6f}; best={best[0]:.6f}',flush=True)
            return score
        objective((np.array([getattr(initial,n) for n in NAMES])-low)/span)
        for z in qmc.LatinHypercube(5,seed=20261009).random(16):objective(z)
        result=minimize(objective,(best[1]-low)/span,method='Powell',bounds=[(0,1)]*5,options={'maxfev':40,'xtol':.025,'ftol':.005})
        parameters=IDMParameters(**{name:float(value) for name,value in zip(NAMES,best[1])})
        final=list(pool.map(evaluate_worker,[(best[1].tolist(),seed) for seed in criteria['final_train_seeds']]))
    final_df=pd.DataFrame(final);final_df.to_csv(ROOT/'outputs/b2_final_replicates.csv',index=False)
    summary=[]
    for name in final_df.select_dtypes(include='number').columns:
        if name=='seed':continue
        v=final_df[name].dropna();mean=float(v.mean());sd=float(v.std(ddof=1));margin=float(t.ppf(.975,len(v)-1)*sd/np.sqrt(len(v)))
        summary.append({'metric':name,'n':len(v),'mean':mean,'SD':sd,'CI95_low':mean-margin,'CI95_high':mean+margin,'acquisition':'B2','stage':'TRAIN_CALIBRATION_DEVELOPMENT'})
    pd.DataFrame(summary).to_csv(ROOT/'outputs/b2_calibration_summary.csv',index=False)
    payload={'training_acquisition':'B2','parameters':asdict(parameters),'queue_gap_m':gap,'bounds':bounds,'development_objective':best[0],
        'code_sha256':fingerprint,'search_plan':search,'optimizer_message':str(result.message),'reference_seed':10,'reference_seed_selection':'fixed before search, never selected for fit','B1_LOCKED':True}
    (ROOT/'outputs/b2_calibrated_parameters.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    export_reference(target,inputs,parameters,gap)

def export_reference(target,inputs,parameters,gap):
    reference=run_baseline(inputs,parameters,seed=10,trace=True,queue_gap=gap)
    pd.DataFrame(reference.recorder.times).to_csv(ROOT/'outputs/b2_baseline_timeseries.csv',index=False)
    target.real_ts.to_csv(ROOT/'outputs/b2_observed_timeseries.csv',index=False)
    target.comparisons(reference).to_csv(ROOT/'outputs/b2_real_vs_simulated.csv',index=False)
    pd.DataFrame(reference.recorder.travels).to_csv(ROOT/'outputs/b2_simulated_travel_times.csv',index=False)
    pd.DataFrame(reference.recorder.exits).to_csv(ROOT/'outputs/b2_simulated_exits.csv',index=False)
    pd.DataFrame(reference.recorder.section_times).to_csv(ROOT/'outputs/b2_simulated_section_times.csv',index=False)
    bins=target.bins
    pd.DataFrame({'time':bins[:-1],'real_exits':target.exit_hist,'simulated_exits':np.histogram([r['exit_time_s'] for r in reference.recorder.exits],bins=bins)[0]}).to_csv(ROOT/'outputs/b2_throughput_bins.csv',index=False)
    # Downsample only exported ECDF visualization points; objective uses full samples.
    distribution=[]
    for name,real,pred in [('speed',target.speed,reference.recorder.speeds),('headway',target.headway,reference.recorder.headways),('travel_time',target.travel,[r['travel_time_s'] for r in reference.recorder.travels])]:
        for label,values in [('B2 real',real),('AgentPy',pred)]:
            for prob,value in zip(np.linspace(0,1,501),np.quantile(values,np.linspace(0,1,501))):distribution.append({'indicator':name,'series':label,'probability':prob,'value':value})
    pd.DataFrame(distribution).to_csv(ROOT/'outputs/b2_distributions.csv',index=False)
    trace={'training_acquisition':'B2','seed':10,'frames':reference.recorder.traces,'network':inputs['network'],'summary':reference.summary}
    def native(value):
        if isinstance(value,dict):return {k:native(v) for k,v in value.items()}
        if isinstance(value,list):return [native(v) for v in value]
        if isinstance(value,np.generic):value=value.item()
        if isinstance(value,float) and not np.isfinite(value):return None
        return value
    (ROOT/'outputs/b2_reference_trace.json').write_text(json.dumps(native(trace),separators=(',',':'),allow_nan=False),encoding='utf-8')
    figures(target,reference)
    print(json.dumps(native({'parameters':asdict(parameters),'reference_summary':reference.summary,'reference_errors':target.errors(reference)}),indent=2),flush=True)

if __name__=='__main__':main()
