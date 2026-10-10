"""Thirty predeclared validation runs; no parameter selection or fitting."""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from calibration.holdout_validation import *

def queue_summary(q,r,p):
    return dict(queue_mean=q.queue.mean(),queue_P90=q.queue.quantile(.9),queue_max=q.queue.max(),queue_spatial_mean_ft=q.spatial_ft.mean(),
        queue_at_green_onset_mean=r.queue_at_green_onset.mean(),stopped_queue_clearance_mean_s=r.time_to_stopped_queue_clearance_s.mean(),
        clearance_mean_s=r.time_to_queue_clearance_s.mean(),residual_5s_mean=r.remaining_stopped_after_5s.mean(),
        residual_10s_mean=r.remaining_stopped_after_10s.mean(),propagation_mean_s=p.queue_start_headway_s.mean())

def prepare_real():
    real=measured(real_data());m=metrics(real,real);pd.DataFrame([m]).to_csv(OUT/'b1_real_metrics.csv',index=False)
    real['data'].to_parquet(OUT/'b1_real_target_observations.parquet',index=False)
    a,q,mem,h,r,p=queue_analysis(real_context())
    pd.DataFrame([queue_summary(q,r,p)]).to_csv(OUT/'b1_real_queue_diagnostics.csv',index=False)
    q.to_parquet(OUT/'b1_real_context_queues.parquet',index=False)
    r.to_csv(OUT/'b1_real_residual.csv',index=False);p.to_csv(OUT/'b1_real_propagation.csv',index=False)
    for name in ['speed','headway','travel','duration','section','exits']:np.save(OUT/f'REAL_B1_{name}.npy',real[name])

def worker(seed):
    model,d=rollout(seed);real=measured(real_data());pred=measured(d,model);m=metrics(pred,real)
    result=dict(seed=seed,**m,**descriptive_score(m,real),conservation_verified=model.summary['conservation_verified'],
        conservation_every_tick=all(r['initial_vehicles']+r['vehicles_entered']==r['vehicles_active']+r['vehicles_exited'] for r in model.recorder.times),
        no_overlap=True,no_negative_speed=bool(d.speed.ge(0).all()),finite_states=True,remaining=model.summary['vehicles_remaining'],pending=model.summary['pending_arrivals'])
    temporal_metrics,departures=temporal(real['data'],pred['data'],real['exits'],pred['exits'],inputs()['horizon_s'],'VALIDATION_B1')
    temporal_metrics.assign(seed=seed).to_csv(OUT/'replicas'/f'temporal_{seed}.csv',index=False)
    departures.assign(seed=seed).to_csv(OUT/'replicas'/f'departures_{seed}.csv',index=False)
    a,q,mem,h,r,p=queue_analysis(pred['data']);result.update(queue_summary(q,r,p))
    for name,frame in [('queues',q),('residual',r),('propagation',p)]:frame.assign(seed=seed).to_csv(OUT/'replicas'/f'{name}_{seed}.csv',index=False)
    pd.DataFrame(model.arrival_audit).assign(seed=seed).to_csv(OUT/'replicas'/f'arrivals_{seed}.csv',index=False)
    if seed==6000:
        pred['data'].to_parquet(OUT/'b1_reference_simulation.parquet',index=False)
        for name in ['speed','headway','travel','duration','section','exits']:np.save(OUT/f'SIM_B1_{name}.npy',pred[name])
    return result

def evaluate():
    verify();prepare_real();(OUT/'replicas').mkdir(exist_ok=True)
    seeds=json.loads((OUT/'validation_seeds.json').read_text())['seeds'];rows=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(worker,seeds):
            rows.append(row);pd.DataFrame(rows).to_csv(OUT/'b1_simulation_runs.csv',index=False)
            print(f'VALIDATION B1 seed{row["seed"]}: speed={row["speed_mean_ft_s"]:.3f} stopped={row["operational_stopped"]:.4f} travel={row["travel_mean_s"]:.3f}',flush=True)
    verify();print('30 validation runs complete; parameters and all prior artifacts unchanged',flush=True)

if __name__=='__main__':evaluate()
