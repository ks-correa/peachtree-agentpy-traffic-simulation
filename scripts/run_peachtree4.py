"""Predeclare bounds/objective/seeds, then one finite two-stage calibration."""
import json,hashlib
from datetime import datetime,timezone
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy.stats import qmc
from scipy.optimize import minimize
from calibration.final_calibration import OUT,ROOT,NAMES,DOMAINS,WEIGHTS,verify_structure,targets,scales,sha,plan,evaluate_job
from scripts.run_peachtree3t import digest

DEV=list(range(5000,5005));FINAL=list(range(4000,4030))

def now():return datetime.now(timezone.utc).isoformat()

def prepare():
    OUT.mkdir(exist_ok=True);freezehash=verify_structure()
    if (OUT/'search_plan.json').exists():plan();print('Existing immutable plan verified');return
    previous=[]
    for folder in ['peachtree3','peachtree3r','peachtree3s','peachtree3t','peachtree3u']:
        previous.extend(p for p in (ROOT/'outputs'/folder).rglob('*') if p.is_file())
    previous.extend(p for p in (ROOT/'outputs').glob('b2_*') if p.is_file())
    previous.extend(p for p in (ROOT/'docs').glob('peachtree3*.md'))
    (OUT/'pre_calibration_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in sorted(previous)},indent=2),encoding='utf-8')
    initial=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
    estimates=pd.read_csv(ROOT/'outputs/b2_parameter_estimates.csv').set_index('parameter');rows=[]
    for key in NAMES:
        r=estimates.loc[key];low,high=initial['bounds'][key]
        if abs(low-r.bound_low)>1e-12 or abs(high-r.bound_high)>1e-12:raise RuntimeError('Prior B2 bounds provenance mismatch')
        rows.append(dict(parameter=key,current_value=initial['parameters'][key],lower=low,upper=high,source='outputs/b2_parameter_estimates.csv; existing B2 quantiles',
            reason=r.criterion+'; positive physical range, unchanged prior empirical bounds',classification='DATASET_DERIVED',sample_n=int(r.sample_n)))
    pd.DataFrame(rows).to_csv(OUT/'parameter_bounds.csv',index=False)
    (OUT/'development_seeds.json').write_text(json.dumps({'seeds':DEV,'purpose':'Optimization mean of all five; no best-seed','frozen_at':now()},indent=2))
    (OUT/'final_replication_seeds.json').write_text(json.dumps({'seeds':FINAL,'purpose':'Final TRAIN evaluation only; never selection','frozen_at':now()},indent=2))
    r=targets();spec=dict(training_acquisition='B2',weights=dict(WEIGHTS),scales=scales(),
        real_scalars={'speed_mean':float(np.mean(r['speed'])),'headway_mean':float(np.mean(r['headway'])),'travel_mean':float(np.mean(r['travel'])),
            'stopped':float(r['stopped']),'vehicles_stopped':r['vehicles_stopped'],'episodes':r['episodes'],'section_mean':float(np.mean(r['section']))},
        components={'speed':['speed_mean','speed_KS','speed_W1'],'headway':['headway_mean','headway_KS','headway_W1'],
            'travel':['travel_mean','travel_W1'],'stopping':['stopped_fraction','vehicles_stopped','stop_episodes','stop_duration_W1'],
            'temporal_flow':['flow_histogram','flow_cumulative'],'section_travel':['section_mean']},
        normalization='Means relative to REAL positive means; W1 by REAL IQR; KS by1; stopped/incidence/count errors relative to REAL; flow by REAL departures. Mean within domain, equal mean of six domains.',
        population='Frozen B2 Through class2/3 target cohort; same directional scope and window',
        definitions={'speed':'Vehicle-time speed including stopped','headway':'Existing cleaned same-lane/same-road CF observations; front-to-front, leader inside scope',
            'travel':'Complete entry-to-directional-exit journeys; initial vehicles excluded',
            'stopping':'Operational <=0.1m/s; contiguous0.1s episodes; durations exclude left/right censoring',
            'flow':'All TARGET departures incl initial;30s histogram L1 and full0.1s-clock mean cumulative departure deviation',
            'section':'Complete pair of same effective controls, same linear crossing interpolation REAL/SIM',
            'queue':'SECONDARY_DIAGNOSTIC only: REAL all-observed context differs from SIM TARGET'},frozen_at=now())
    (OUT/'objective_definition.json').write_text(json.dumps(spec,indent=2),encoding='utf-8')
    paths=[OUT/'parameter_bounds.csv',OUT/'development_seeds.json',OUT/'final_replication_seeds.json',OUT/'objective_definition.json']
    search=dict(training_acquisition='B2',structural_freeze_sha256=freezehash,development_seeds=DEV,final_seeds=FINAL,
        exploration='40 Latin Hypercube candidates plus unchanged initial baseline',LHS_seed=20261010,LHS_candidates=40,
        local_algorithm='Bounded Nelder-Mead in unit empirical bounds; two best LHS starts',local_starts=2,local_maxfev_per_start=50,
        total_local_maxfev=100,score='Arithmetic mean of all five development seeds; any invalid rollout disqualifies set',
        selection='Minimum predeclared objective over all valid evaluated sets; no manual override',
        frozen_artifact_hashes={str(p.relative_to(ROOT)):sha(p) for p in paths},created_at=now())
    (OUT/'search_plan.json').write_text(json.dumps(search,indent=2),encoding='utf-8')
    print('Bounds, six equal domains, development/final seeds frozen BEFORE optimization',flush=True)

def search():
    p=plan();bounds=pd.read_csv(OUT/'parameter_bounds.csv').set_index('parameter').loc[list(NAMES)]
    low=bounds.lower.to_numpy();high=bounds.upper.to_numpy();current=bounds.current_value.to_numpy()
    if (OUT/'final_parameters.json').exists():raise RuntimeError('Single calibration already selected parameters; a second calibration is prohibited')
    candidates=[];history=[];cache={};counter=0
    def persist():
        pd.DataFrame(candidates).to_csv(OUT/'calibration_candidates.csv',index=False)
        pd.DataFrame(history).to_csv(OUT/'optimization_history.csv',index=False)
    with ProcessPoolExecutor(max_workers=3) as pool:
        def score(x,stage):
            nonlocal counter
            x=np.clip(np.asarray(x),0,1);values=dict(zip(NAMES,low+x*(high-low)));key=tuple(values.values())
            if key in cache:return cache[key]['objective']
            counter+=1;cid=counter;results=list(pool.map(evaluate_job,[(cid,values,seed) for seed in p['development_seeds']]))
            history.extend(dict(stage=stage,**row) for row in results)
            valid=all(row['status']=='VALID' for row in results)
            summary=dict(candidate=cid,stage=stage,status='VALID' if valid else 'INVALID_CANDIDATE',**values,n_seeds=len(results),
                objective=float(np.mean([row['objective'] for row in results])) if valid else float('inf'))
            if valid:
                for k in results[0]:
                    if k.startswith(('component_','E_')):summary[k]=float(np.mean([row[k] for row in results]))
            candidates.append(summary);cache[key]=summary;persist()
            print(f'{stage} candidate{cid}: objective={summary["objective"]:.6f} {summary["status"]}',flush=True)
            return summary['objective']
        score((current-low)/(high-low),'PRECALIBRATION')
        samples=qmc.LatinHypercube(d=5,seed=p['LHS_seed']).random(p['LHS_candidates'])
        for x in samples:score(x,'LHS')
        good=sorted([c for c in candidates if c['stage']=='LHS' and c['status']=='VALID'],key=lambda c:c['objective'])
        if not good:raise RuntimeError('No valid LHS candidate')
        local_results=[]
        for start,c in enumerate(good[:p['local_starts']],1):
            x=(np.array([c[k] for k in NAMES])-low)/(high-low)
            result=minimize(lambda z:score(z,f'LOCAL_{start}'),x,method='Nelder-Mead',bounds=[(0.,1.)]*5,
                options={'maxfev':p['local_maxfev_per_start'],'maxiter':p['local_maxfev_per_start'],'xatol':1e-3,'fatol':1e-5})
            local_results.append(dict(start_candidate=c['candidate'],calls=int(result.nfev),terminated=True,converged=bool(result.success),message=str(result.message)))
    plan();winner=min((c for c in candidates if c['status']=='VALID'),key=lambda c:c['objective'])
    output=dict(training_acquisition='B2',values={k:winner[k] for k in NAMES},delta=4.,objective=winner['objective'],
        component_errors={k:v for k,v in winner.items() if k.startswith(('component_','E_'))},selected_candidate=winner['candidate'],
        evaluated_parameter_sets=len(candidates),bounds={k:[bounds.loc[k,'lower'],bounds.loc[k,'upper']] for k in NAMES},
        source='B2 ONLY; predeclared equal-domain score, mean over five development seeds',optimizer=p,
        local_termination=local_results,seed_set=p['development_seeds'],timestamp=now(),
        hashes={'structural_freeze_sha256':p['structural_freeze_sha256'],**p['frozen_artifact_hashes']})
    (OUT/'final_parameters.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print('SINGLE FINAL PARAMETER SET SELECTED; no further calibration',flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','search'])
    prepare() if parser.parse_args().stage=='prepare' else search()
