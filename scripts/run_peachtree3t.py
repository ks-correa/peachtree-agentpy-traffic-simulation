"""Reproducible B2 envelope audit. Outputs isolated from all previous phases."""
import json,hashlib
from pathlib import Path
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from calibration.structural import full_b2
from calibration.receiving_scope import run,inside,NEW_EXIT
from calibration.control_envelope import SignalControlEnvelope,associate,queue_series,dynamics,KEY,STOP
from simulation.training_data import ROOT,load_inputs,require_train
from simulation.parameters import FOOT_M

OUT=ROOT/'outputs/peachtree3t'
PROXIES={(2,2):632.5395,(2,4):777.262,(3,2):1168.9155,(3,4):1240.7775}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def preserve():
    OUT.mkdir(parents=True,exist_ok=True)
    target=OUT/'pre_revision_hashes.json'
    if target.exists():return
    paths=[]
    for folder in ['outputs/peachtree3','outputs/peachtree3r','outputs/peachtree3s']:
        paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
    paths.extend(p for p in (ROOT/'outputs').glob('b2_*') if p.is_file())
    paths.extend((ROOT/'simulation').glob('*.py'))
    payload={str(p.relative_to(ROOT)):digest(p) for p in sorted(paths)}
    target.write_text(json.dumps(payload,indent=2),encoding='utf-8')

def envelopes():
    # Only B2 annotation extents; observational references, not painted stop bars.
    ext=pd.read_csv(ROOT/'outputs/peachtree3s/b2_intersection_extents.csv').set_index('int_id')
    mouth=pd.read_csv(ROOT/'outputs/peachtree3s/b2_intersection_entry_mouths.csv').set_index(['intersection','direction'])
    out=[]
    for i in [2,3]:
        for di in [2,4]:
            entry=float(mouth.loc[(i,di),'median']);exit=float(ext.loc[i,'max' if di==2 else 'min'])
            # Partition the retained roads at observed previous intersection exit.
            start=(400. if i==2 else float(ext.loc[2,'max'])) if di==2 else (1400. if i==3 else float(ext.loc[3,'min']))
            end=(1346.452 if i==3 else float(ext.loc[3,'min'])) if di==2 else (597.878 if i==2 else float(ext.loc[2,'max']))
            for lane in [1,2]:out.append(SignalControlEnvelope(i,di,lane,start,entry,exit,end))
    return out

def real_data():
    full=full_b2();origin=load_inputs()['source_window_start_relative_s']
    d=full[full.direction.isin([2,4])&full.v_class.isin([2,3])].sort_values(['vehicle_id','frame_id']).copy()
    d['source_lane']=d.lane_id
    # A junction's lane 0 is only recovered if bracketing normal lanes agree,
    # both samples are contiguous and direction/through movement are unchanged.
    d['normal']=d.lane_id.where(d.lane_id.isin([1,2]))
    # Never bridge tracking gaps or direction changes while recovering lane 0.
    breaks=d.vehicle_id.ne(d.vehicle_id.shift())|d.frame_id.diff().ne(1)|d.direction.ne(d.direction.shift())
    d['continuous_run']=breaks.cumsum()
    group=d.groupby('continuous_run',sort=False)
    before=group.normal.ffill();after=group.normal.bfill()
    valid=d.lane_id.eq(0)&before.eq(after)&before.notna()&d.movement.eq(1)&d.int_id.isin([2,3])
    d.loc[valid,'lane_id']=before[valid]
    d['lane_recovered']=valid
    d['lane_exclusion']=np.where(d.lane_id.isin([1,2]),'', 'AMBIGUOUS_OR_NON_THROUGH_LANE_CODE')
    d=d.rename(columns={'trajectory_key':'id','frame_id':'frame','lane_id':'lane','local_y':'y','v_vel':'speed','v_length':'length'})
    d['time']=d.t_relative-origin
    return d[d.time.ge(0)&inside(d)].copy()

def analyze(d,env):
    gap=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['queue_gap_m']/FOOT_M
    a=associate(d,env);q,m=queue_series(a,gap);h,r,p=dynamics(a,q,m)
    return a,q,m,h,r,p

def summary(q,h,r,p):
    # Per occupied lane/time approach snapshots; denominator explicit in report.
    return {'queue_mean':q.queue.mean(),'queue_P90':q.queue.quantile(.9),'queue_max':q.queue.max(),
        'queue_spatial_mean_ft':q.spatial_ft.mean(),'queue_spatial_P90_ft':q.spatial_ft.quantile(.9),
        'head_mean_y_ft':h.position_y.mean() if len(h) else np.nan,
        'release_mean_s':r.time_to_first_release_s.mean() if len(r) else np.nan,
        'clearance_mean_s':r.time_to_queue_clearance_s.mean() if len(r) else np.nan,
        'clearance_observed_n':r.time_to_queue_clearance_s.notna().sum() if len(r) else 0,
        'residual_5s_mean':r.remaining_stopped_after_5s.mean() if len(r) else np.nan,
        'residual_10s_mean':r.remaining_stopped_after_10s.mean() if len(r) else np.nan,
        'propagation_mean_s':p.queue_start_headway_s.mean() if len(p) else np.nan,
        'propagation_observed_n':p.queue_start_headway_s.notna().sum() if len(p) else 0}

def worker(job):
    mode,seed=job if isinstance(job,tuple) else ('NEW_REDUCED_SCOPE',job)
    model,d=run(mode,seed)
    a,q,m,h,r,p=analyze(d[inside(d)],envelopes())
    folder=OUT/'replicas';folder.mkdir(exist_ok=True)
    for name,frame in [('heads',h),('residual',r),('propagation',p)]:
        frame.assign(seed=seed,series=mode).to_csv(folder/f'{mode}_{name}_{seed}.csv',index=False)
    return dict(summary(q,h,r,p),seed=seed,mode=mode,conservation_verified=model.summary['conservation_verified'])

def prepare():
    require_train('B2');preserve();env=envelopes();real=real_data()
    real[real.lane_exclusion.ne('')].groupby(['direction','source_lane','lane_exclusion']).size().rename('frames').to_csv(OUT/'lane_exclusions.csv')
    a,q,m,h,r,p=analyze(real,env)
    a.to_parquet(OUT/'real_envelope_observations.parquet',index=False)
    q.to_parquet(OUT/'real_queue_timeseries.parquet',index=False)
    m.to_parquet(OUT/'real_queue_members.parquet',index=False)
    candidates=a[a.intersection.isin([2,3])&a.lane.isin([1,2])].copy()
    candidates['order']=candidates.y*np.where(candidates.direction.eq(2),-1,1)
    fronts=candidates.sort_values(['frame']+KEY+['order']).drop_duplicates(['frame']+KEY)
    fronts['selection_status']=np.select([fronts.speed.gt(STOP),fronts.movement.ne(1),(fronts.y-fronts.control_entry).abs().gt(100)],
        ['FRONT_MOVING_NO_STANDING_HEAD','INCOMPATIBLE_MOVEMENT','OUTSIDE_FROZEN_100FT_HEAD_WINDOW'],default='FIRST_STOPPED_HEAD')
    fronts[['id','frame','time']+KEY+['y','movement','source_lane','lane_recovered','selection_status']].to_csv(OUT/'queue_head_exclusions.csv',index=False)
    h['distance_to_current_proxy']=[(PROXIES[(i,di)]-y)*(1 if di==2 else -1) for i,di,y in zip(h.intersection,h.direction,h.position_y)]
    lengths=a.groupby('id').length.median();h['vehicle_length']=h.id.map(lengths)
    # Keep changing heads separate within each cycle; never pool frames as independent cycles.
    h.to_csv(OUT/'first_queue_heads.csv',index=False);h.to_csv(OUT/'queue_head_by_cycle.csv',index=False)
    stats=[]
    for key,g in h.groupby(KEY):
        x=g.position_y;lo,hi=x.quantile([.1,.9]);q1,q3=x.quantile([.25,.75])
        stats.append(dict(zip(KEY,key),n=len(x),n_cycles=g.cycle.nunique(),mean=x.mean(),median=x.median(),SD=x.std(),P10=lo,P25=q1,P75=q3,P90=hi,IQR=q3-q1,
            within_cycle_SD_mean=g.within_cycle_SD_ft.mean(),between_cycle_variance=x.var(),outliers=int(((x<q1-1.5*(q3-q1))|(x>q3+1.5*(q3-q1))).sum()),
            interpretation='OBSERVED_HEAD_BAND_NOT_SURVEYED_STOP_BAR',point_identified=False))
    zones=pd.DataFrame(stats);zones.to_csv(OUT/'stop_zone_candidates.csv',index=False)
    from dataclasses import replace
    enriched=[]
    for e in env:
        z=zones[(zones.intersection==e.intersection)&(zones.direction==e.direction)&(zones.lane==e.lane)]
        enriched.append(replace(e,stop_low=z.P10.iloc[0],stop_high=z.P90.iloc[0]) if len(z) else e)
    pd.DataFrame([asdict(e) for e in enriched]).to_csv(OUT/'intersection_envelopes.csv',index=False)
    r.assign(series='REAL_B2').to_csv(OUT/'residual_queue_after_green.csv',index=False)
    p.assign(series='REAL_B2').to_csv(OUT/'queue_start_propagation.csv',index=False)
    release=r.groupby(KEY).time_to_first_release_s.agg(n='count',median='median',P25=lambda x:x.quantile(.25),P75=lambda x:x.quantile(.75)).reset_index()
    release['IQR']=release.P75-release.P25;release['policy']='KEEP_1.6_S_PENDING_IDENTIFIABLE_PHYSICAL_CONTROL_REFERENCE'
    release.to_csv(OUT/'release_delay_by_group.csv',index=False)
    # Explicit source metadata and coding retained for the problematic interval.
    problem=a[a.direction.eq(2)&a.y.between(1174,1192)].copy()
    headkeys=set(zip(m[m['rank'].eq(1)].id,m[m['rank'].eq(1)].frame))
    memberkeys=set(zip(m.id,m.frame))
    problem['first_queue_head']=[(i,f) in headkeys for i,f in zip(problem.id,problem.frame)]
    problem['queue_follower']=[(i,f) in memberkeys and (i,f) not in headkeys for i,f in zip(problem.id,problem.frame)]
    problem.to_csv(OUT/'problem_12th_NB_frames.csv',index=False)
    green=a[a.stopped&a.phase.eq('GREEN')].copy()
    prior_ids=[]
    for row in r.itertuples():
        prior=m[(m.time-row.green_start+.1).abs().lt(.051)&m.intersection.eq(row.intersection)&m.direction.eq(row.direction)&m.lane.eq(row.lane)]
        for v in prior.id:
            control=__import__('simulation.signals',fromlist=['controllers_from_inputs']).controllers_from_inputs(load_inputs())[(row.intersection,row.direction)]
            interval=next(x for x in control.intervals if x.state=='GREEN' and abs(x.start-row.green_start)<1e-6)
            track=a[a.id.eq(v)&a.time.ge(row.green_start)&a.time.lt(interval.end)]
            moving=track[track.speed.gt(STOP)]
            release=moving.time.iloc[0] if len(moving) else interval.end
            prior_ids.append((v,row.intersection,row.direction,row.green_start,release))
    def category(row):
        if any(row.id==v and row.intersection==i and row.direction==di and t<=row.time<release for v,i,di,t,release in prior_ids):return 'A_RESIDUAL_PREVIOUS_RED'
        if row.movement!=1:return 'C_TURNING_LOCAL_INTERACTION'
        return 'E_UNKNOWN'
    green['classification']=[category(row) for row in green.itertuples()]
    lookup=a.set_index(['frame','vehicle_id'])
    for idx,row in green[green.classification.eq('E_UNKNOWN')].iterrows():
        key=(row.frame,row.preceding)
        if row.preceding>0 and key in lookup.index:
            leader=lookup.loc[key]
            if isinstance(leader,pd.Series) and leader.direction==row.direction and leader.lane==row.lane and leader.stopped:
                green.loc[idx,'classification']='D_DOWNSTREAM_QUEUE_INSIDE_MODEL' if leader.discharge_intersection==row.intersection else 'B_BLOCKED_BY_STOPPED_LEADER'
    green.to_csv(OUT/'green_stopping_classification.csv',index=False)
    pd.DataFrame([dict(summary(q,h,r,p),mode='REAL_B2',seed=-1)]).to_csv(OUT/'real_vs_sim_queue_dynamics.csv',index=False)
    (OUT/'coordinate_semantics.md').write_text('Local_X and Local_Y are lateral/longitudinal coordinates of the FRONT CENTER, in feet. Official Peachtree Metadata, attribute definitions, printed page 13 (extracted lines 604–617). Origin: southern study boundary. FRONT = Local_Y; CENTER = Local_Y - sign(direction)*length/2; REAR = Local_Y - sign(direction)*length. NB sign +1; SB -1. Center/rear are longitudinal straight-path projections, not surveyed body coordinates in curves. Length must NOT be added to Local_Y. Space headway is front-to-front, not bumper gap. No stop-bar coordinate is specified by these definitions.\n',encoding='utf-8')
    print('B2 reconstruction complete; cycle heads:',len(h),'green cohorts:',len(r),flush=True)

def evaluate(previous=False):
    results=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        jobs=[(mode,seed) for mode in (['OLD','REVISED'] if previous else ['NEW_REDUCED_SCOPE']) for seed in range(3000,3030)]
        for result in pool.map(worker,jobs):
            results.append(result);print('Measured',result['mode'],'seed',result['seed'],flush=True)
            pd.DataFrame(results).to_csv(OUT/('previous_paired_queue_replicas.csv' if previous else 'paired_queue_replicas.csv'),index=False)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','evaluate','previous'])
    stage=parser.parse_args().stage
    prepare() if stage=='prepare' else evaluate(stage=='previous')
