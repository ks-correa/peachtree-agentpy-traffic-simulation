"""Fixed-parameter structural experiment; no opaque optimization or seed choice."""
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import numpy as np
import pandas as pd
from scipy.stats import t,wasserstein_distance,ks_2samp
from simulation.training_data import ROOT,require_train
from calibration.structural import OUT,rollout
from calibration.structural_metrics import stopped,stop_episodes,temporal
from scripts.audit_peachtree3r import episode_summary

def worker(seed,revised=True):
    from simulation.training_data import load_inputs
    inputs=json.loads((OUT/'revised_inputs.json').read_text(encoding='utf-8')) if revised else load_inputs();model,d=rollout(inputs,seed)
    ep,summary=episode_summary(d,'REVISED_BASELINE' if revised else 'OLD_BASELINE')
    real=pd.read_parquet(OUT/'real_observations.parquet');real_episodes=stop_episodes(real);real_dur=real_episodes[~real_episodes.left_censored&~real_episodes.right_censored].duration_s
    summary={**model.summary,**summary,'seed':seed,'release_events':len(model.release_events),'operational_stopped_fraction':float(np.mean(stopped(d.speed))),
        'exact_zero_fraction_literal':float(d.speed.eq(0).mean()),'speed_KS':ks_2samp(real.speed,d.speed,method='asymp').statistic,'speed_W1_ft_s':wasserstein_distance(real.speed,d.speed),
        'stop_duration_W1_s':wasserstein_distance(real_dur,ep[~ep.left_censored&~ep.right_censored].duration_s)}
    from calibration.objective import TrainTargets
    target=TrainTargets();errors=target.errors(model)
    # Preserve separate errors; literal legacy stopped term must not be confused
    # with the revised operational target.
    errors['operational_stopping_absolute_error']=abs(summary['operational_stopped_fraction']-np.mean(stopped(real.speed)))
    errors.pop('stopped_fraction_absolute_error');errors.pop('objective')
    summary.update(errors)
    _,flow=temporal(real,d,target.real_exits.time.to_numpy(),np.array([r['exit_time_s'] for r in model.recorder.exits]),inputs['horizon_s'],'REVISED_BASELINE')
    summary['max_cumulative_deviation_10s']=flow[flow.bin_s.eq(10)].maximum_cumulative_departure_deviation.iloc[0]
    summary['throughput_MAE_10s']=flow[flow.bin_s.eq(10)].MAE_per_bin.iloc[0]
    return summary

def old_worker(seed):return worker(seed,False)

def paired_old():
    freeze=json.loads((OUT/'revision_freeze.json').read_text())
    with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(old_worker,freeze['final_seeds']))
    pd.DataFrame(rows).to_csv(OUT/'paired_old_replicates.csv',index=False)
    print('Paired OLD controls:',len(rows),flush=True)

def main(acquisition='B2'):
    require_train(acquisition);freeze=json.loads((OUT/'revision_freeze.json').read_text())
    with ProcessPoolExecutor(max_workers=3) as pool:
        development=list(pool.map(worker,freeze['development_seeds']));pd.DataFrame(development).to_csv(OUT/'development_replicates.csv',index=False)
        final=[]
        for result in pool.map(worker,freeze['final_seeds']):
            final.append(result);print(f'Revised TRAIN replica {result["seed"]}: operational stop={result["operational_stopped_fraction"]:.4f}, travel={result["mean_travel_time_s"]:.2f}s',flush=True)
    df=pd.DataFrame(final);df.to_csv(OUT/'revised_replicates.csv',index=False)
    rows=[]
    for name in df.select_dtypes(include='number').columns:
        if name=='seed':continue
        v=df[name].dropna();mean=v.mean();sd=v.std(ddof=1);margin=t.ppf(.975,len(v)-1)*sd/np.sqrt(len(v))
        rows.append({'metric':name,'n':len(v),'mean':mean,'SD':sd,'CI95_low':mean-margin,'CI95_high':mean+margin})
    pd.DataFrame(rows).to_csv(OUT/'revised_30_replica_summary.csv',index=False)
    inputs=json.loads((OUT/'revised_inputs.json').read_text());reference,d=rollout(inputs,210,True)
    d.to_parquet(OUT/'revised_observations.parquet',index=False);pd.DataFrame(reference.recorder.times).to_csv(OUT/'revised_timeseries.csv',index=False)
    pd.DataFrame(reference.recorder.exits).to_csv(OUT/'revised_exits.csv',index=False);pd.DataFrame(reference.recorder.travels).to_csv(OUT/'revised_travel_times.csv',index=False)
    pd.DataFrame(reference.recorder.section_times).to_csv(OUT/'revised_section_times.csv',index=False);pd.DataFrame(reference.arrival_audit).to_csv(OUT/'revised_safe_insertion.csv',index=False)
    pd.DataFrame(reference.release_events).to_csv(OUT/'release_events.csv',index=False)
    from ui.canvas_renderer import finite_json
    trace={'training_acquisition':'B2','seed':210,'frames':reference.recorder.traces,'network':inputs['network'],'summary':reference.summary,'revision':'PEACHTREE-3R'}
    (OUT/'revised_trace.json').write_text(json.dumps(finite_json(trace),separators=(',',':'),default=lambda value:value.item(),allow_nan=False),encoding='utf-8')
    p=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text());rows=[{'parameter':k,'old_value':v,'revised_value':v,'unit':{'v0':'m/s','T':'s','s0':'m','a':'m/s2','b':'m/s2','delta':'dimensionless'}[k],'classification':'RETAINED_B2_CALIBRATED' if k!='delta' else 'LITERATURE_DERIVED'} for k,v in p['parameters'].items()]
    rows.extend([{'parameter':'signal_release_delay','revised_value':freeze['signal_release_delay_s'],'unit':'s','classification':'DATASET_DERIVED_B2_POOLED_MEDIAN'},
        {'parameter':'operational_stop_threshold','revised_value':.1,'unit':'m/s','classification':'LITERATURE_DERIVED_MEASUREMENT_ONLY'}])
    pd.DataFrame(rows).to_csv(OUT/'revised_parameters.csv',index=False)
    (OUT/'revised_parameters.json').write_text(json.dumps(dict(p,revision=freeze),indent=2),encoding='utf-8')
    print(pd.DataFrame(rows).to_string(index=False));print(pd.DataFrame(rows).shape)
    paired_old()
if __name__=='__main__':main()
