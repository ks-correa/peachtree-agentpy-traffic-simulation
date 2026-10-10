import json
from pathlib import Path
import numpy as np
import pandas as pd
from simulation.training_data import ROOT,load_b2_source,load_b2_cf,read_train_csv,require_train
from simulation.parameters import FOOT_M,IDMParameters

def estimate_parameters(acquisition='B2'):
    require_train(acquisition)
    if (ROOT/'outputs/peachtree3r/old_baseline_manifest.json').exists():
        raise RuntimeError('PEACHTREE-3 artifacts are preserved. Use the revision namespace; legacy estimation would overwrite original results.')
    criteria=json.loads((ROOT/'docs/b2_estimation_criteria.json').read_text())
    raw=load_b2_source();cf=load_b2_cf()
    cf=cf[cf.t_relative.ge(93.4)]
    keyed=raw.set_index(['vehicle_id','frame_id'])
    points=keyed.reindex(pd.MultiIndex.from_frame(cf[['vehicle_id','frame_id']])).reset_index(drop=True)
    positive=cf.ego_speed[cf.ego_speed>0];moving_cut=float(positive.median())
    valid_h=(cf.ego_speed.to_numpy()>=moving_cut)&cf.signal_state.eq('GREEN').to_numpy()&points.time_headway.gt(0).to_numpy()&points.time_headway.lt(9999.99).to_numpy()
    h=points.loc[valid_h,'time_headway'].to_numpy(float)
    stood=cf[cf.ego_speed.eq(0)].gap.to_numpy(float)*FOOT_M
    acceleration=cf[cf.acceleration.gt(0)].acceleration.to_numpy(float)*FOOT_M
    braking=-cf[cf.acceleration.lt(0)].acceleration.to_numpy(float)*FOOT_M
    # Signal states are immutable B2 input schedules, not a fitted mask.
    inputs=json.loads((ROOT/'data/b2_exogenous_inputs.json').read_text())
    from simulation.network import PeachtreeEnvironment
    from simulation.signals import controllers_from_inputs
    env=PeachtreeEnvironment(inputs['network']);bank=controllers_from_inputs(inputs)
    free=[]
    ordered=raw.sort_values(['trajectory_key','frame_id'])
    previous=ordered.groupby('trajectory_key')
    dy=np.hypot(ordered.global_x-previous.global_x.shift(),ordered.global_y-previous.global_y.shift())
    same=ordered.trajectory_key.eq(ordered.trajectory_key.shift()) & ordered.frame_id.diff().eq(1)
    expected=(ordered.v_vel+ordered.v_vel.shift())*.05+2*np.hypot(2.,4.)
    jump=(same & dy.gt(expected))
    # Existing +/-1s road-transition quality exclusion also applies to free-speed seeds.
    events=read_train_csv(ROOT/'outputs/peachtree_lane_transition_classification.csv')
    active=np.zeros(len(ordered),dtype=bool)
    events['frame_id']=pd.to_numeric(events.frame_id)
    events=events[pd.to_numeric(events.int_id).eq(0)&pd.to_numeric(events.section_id).gt(0)]
    windows={k:np.sort(q.frame_id.to_numpy()) for k,q in events.groupby('trajectory_key')}
    for key,indices in ordered.groupby('trajectory_key').indices.items():
        ef=windows.get(key)
        if ef is None:continue
        fr=ordered.iloc[indices].frame_id.to_numpy();loc=np.searchsorted(ef,fr)
        distances=np.minimum(abs(fr-ef[np.maximum(0,loc-1)]),abs(fr-ef[np.minimum(len(ef)-1,loc)]))
        active[indices]=distances<=10
    candidates=ordered[ordered.t_relative.ge(93.4)&ordered.preceding.eq(0)&ordered.lane_id.isin([1,2])&ordered.int_id.eq(0)&ordered.v_vel.gt(0)&~np.isclose(ordered.v_acc.abs(),12.27)&~jump&~active]
    for r in candidates.itertuples():
        line=env.next_line(r.direction,env.progress(r.local_y,r.direction))
        if not line or bank[(line.intersection,r.direction)].at(r.t_relative-93.4)=='GREEN':free.append(r.v_vel*FOOT_M)
    samples={'v0':np.asarray(free),'T':h,'s0':stood,'a':acceleration,'b':braking}
    units={'v0':'m/s','T':'s','s0':'m','a':'m/s^2','b':'m/s^2'}
    rows=[];initial={};bounds={}
    for name,values in samples.items():
        values=values[np.isfinite(values)&(values>0)]
        if not len(values):raise RuntimeError('No identifiable TRAIN seed sample: '+name)
        value=float(np.quantile(values,.85 if name=='v0' else .5));low=float(np.quantile(values,.5 if name=='v0' else .1));high=float(np.quantile(values,.95 if name=='v0' else .9))
        if low==high:low=max(value*.5,1e-5);high=value*1.5
        initial[name]=value;bounds[name]=[low,high]
        rows.append({'parameter':name,'initial_estimate':value,'unit':units[name],'sample_n':len(values),
            'bound_low':low,'bound_high':high,'source':'B2_ONLY','classification':'DATASET_DERIVED_INITIAL; CALIBRATED_FINAL',
            'criterion':criteria[name],'moving_speed_cut_ft_s_if_T':moving_cut if name=='T' else np.nan})
    queue_gap=float(np.quantile(stood,.9))
    rows.append({'parameter':'delta','initial_estimate':4.,'unit':'dimensionless','source':criteria['delta']['source'],'classification':'LITERATURE_DERIVED'})
    pd.DataFrame(rows).to_csv(ROOT/'outputs/b2_parameter_estimates.csv',index=False)
    output={'training_acquisition':'B2','parameters':initial,'bounds':bounds,'queue_gap_m':queue_gap,
        'criteria_sha':__import__('scripts.evaluate_local',fromlist=['digest']).digest(ROOT/'docs/b2_estimation_criteria.json')}
    (ROOT/'outputs/b2_initial_parameters.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    events=read_train_csv(ROOT/'outputs/peachtree_confirmed_lane_changes.csv')
    events=events[events.trajectory_key.isin(raw.trajectory_key)&pd.to_numeric(events.local_y).between(400,1400)]
    lane={'training_acquisition':'B2','confirmed_scope_events':len(events),'scope_vehicles':raw.trajectory_key.nunique(),
        'observed_exposure_vehicle_seconds':len(raw)*.1,'model':'Necessary topology only; discretionary disabled',
        'classification':'ASSUMPTION_SIMPLIFICATION_SUPPORTED_BY_SPARSE_TRAIN_SAMPLE',
        'reason':'21 events do not robustly identify a multivariate gap/speed/distance probability; no B1 used'}
    (ROOT/'outputs/b2_lane_change_diagnostics.json').write_text(json.dumps(lane,indent=2),encoding='utf-8')
    print(json.dumps(output,indent=2))
    return IDMParameters(**initial),bounds,queue_gap

def figures(target,model):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=ROOT/'outputs/b2_figures';folder.mkdir(exist_ok=True)
    data=[('speed_comparison.png','Speed (ft/s)',target.speed,np.array(model.recorder.speeds)),
        ('headway_comparison.png','Front-to-front headway (ft)',target.headway,np.array(model.recorder.headways)),
        ('travel_time_comparison.png','Cut-to-cut travel time (s)',target.travel,np.array([x['travel_time_s'] for x in model.recorder.travels]))]
    for filename,label,real,pred in data:
        fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
        for name,values in [('B2 real',real),('AgentPy TRAIN',pred)]:
            if len(values):
                x=np.sort(values);ax.plot(x,np.arange(1,len(x)+1)/len(x),label=name)
        ax.set(xlabel=label,ylabel='Empirical CDF',title='TRAIN calibration/development  -  not validation')
        ax.legend();ax.grid(alpha=.2);fig.savefig(folder/filename,dpi=160);plt.close(fig)
    sim=pd.DataFrame(model.recorder.times)
    for filename,col,label in [('stopped_fraction.png','stopped_fraction','Exactly stopped fraction')]:
        fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
        for name,z in [('B2 real',target.real_ts),('AgentPy TRAIN',sim)]:
            q=z.groupby((z.simulation_time//30)*30)[col].mean();ax.plot(q.index,q,label=name)
        ax.set(xlabel='Simulation-relative time (s)',ylabel=label,title='TRAIN  -  30s means');ax.legend();ax.grid(alpha=.2)
        fig.savefig(folder/filename,dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    ax.step(target.bins[:-1],target.exit_hist,where='post',label='B2 real')
    counts=np.histogram([r['exit_time_s'] for r in model.recorder.exits],bins=target.bins)[0]
    ax.step(target.bins[:-1],counts,where='post',label='AgentPy TRAIN');ax.set(xlabel='Time (s)',ylabel='Exit crossings /30s',title='TRAIN temporal throughput')
    ax.legend();ax.grid(alpha=.2);fig.savefig(folder/'throughput.png',dpi=160);plt.close(fig)
