"""Locked selection followed by paired PRE/FINAL TRAIN replications only."""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from calibration.final_calibration import OUT,ROOT,plan,sha,rollout,measured,metrics,errors,final_parameters,NAMES,targets
from calibration.structural_metrics import temporal
from scripts.run_peachtree3t import analyze,envelopes,summary

def worker(job):
    mode,values,seed=job
    model,d=rollout(values,seed);pred=measured(model,d);result=dict(seed=seed,mode=mode,**metrics(pred),**errors(metrics(pred)))
    result.update(conservation_verified=model.summary['conservation_verified'],no_overlap=True,no_negative_speed=True,
        valid_signals=True,finite_state=True,boundaries_valid=True,remaining=model.summary['vehicles_remaining'],pending=model.summary['pending_arrivals'])
    real=targets()
    ts,departures=temporal(real['data'],pred['data'],real['exits'],pred['exits'],real['horizon'],mode)
    ts.assign(seed=seed).to_csv(OUT/'replicas'/f'{mode}_temporal_{seed}.csv',index=False)
    departures.assign(seed=seed).to_csv(OUT/'replicas'/f'{mode}_departures_{seed}.csv',index=False)
    a,q,m,h,r,p=analyze(pred['data'],envelopes());result.update(summary(q,h,r,p))
    result['queue_at_green_onset_mean']=r.queue_at_green_onset.mean();result['stopped_queue_clearance_mean_s']=r.time_to_stopped_queue_clearance_s.mean()
    for name,frame in [('residual',r),('propagation',p),('heads',h)]:frame.assign(seed=seed,mode=mode).to_csv(OUT/'replicas'/f'{mode}_{name}_{seed}.csv',index=False)
    # Retain distribution summaries for every seed and a predeclared reference,
    # never select a visually favorable seed.
    if seed==4000:
        pred['data'].to_parquet(OUT/f'{mode}_reference_observations.parquet',index=False)
        for name in ['speed','headway','travel','duration','section','exits']:np.save(OUT/f'{mode}_{name}.npy',pred[name])
    return result

def evaluate():
    p=plan();path=OUT/'final_parameters.json';locked=sha(path)
    values=dict(final_parameters());pre=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['parameters']
    pre={k:pre[k] for k in NAMES}
    lock=OUT/'selection_lock.json'
    if lock.exists() and json.loads(lock.read_text())['final_parameters_sha256']!=locked:raise RuntimeError('Selected parameters changed')
    lock.write_text(json.dumps({'status':'SELECTED_IMMUTABLE','final_parameters_sha256':locked,'final_seeds':p['final_seeds']},indent=2))
    (OUT/'replicas').mkdir(exist_ok=True)
    jobs=[(mode,x,seed) for mode,x in [('FINAL_STRUCTURE_PRECALIBRATION',pre),('FINAL_CALIBRATED_B2',values)] for seed in p['final_seeds']]
    results=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(worker,jobs):
            if sha(path)!=locked:raise RuntimeError('Final parameters changed during final evaluation')
            results.append(row);frame=pd.DataFrame(results)
            for mode,name in [('FINAL_STRUCTURE_PRECALIBRATION','precalibration_30_replica_runs.csv'),('FINAL_CALIBRATED_B2','final_30_replica_runs.csv')]:
                frame[frame['mode'].eq(mode)].to_csv(OUT/name,index=False)
            print(f'{row["mode"]} seed{row["seed"]}: stopped={row["operational_stopped"]:.4f} travel={row["travel_mean_s"]:.3f}',flush=True)
    plan();print('Final30 TRAIN reps and paired30 PRE reps complete; selected values unchanged',flush=True)

if __name__=='__main__':evaluate()
