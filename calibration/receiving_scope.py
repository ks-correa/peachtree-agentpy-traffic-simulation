"""Directional reduced exits; inherited AgentPy dynamics remain frozen."""
import json,math
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp,wasserstein_distance,t
from calibration.receiving import OUT,EXIT,LAST,real_targets,leaders,full_b2,crossing_events
from calibration.structural import DiagnosticModel,COLUMNS
from calibration.structural_metrics import STOP_FT_S,stop_episodes
from simulation.parameters import IDMParameters,DT
from simulation.training_data import ROOT,load_inputs,load_b2_cf,load_b2_source,require_train

NEW_EXIT={2:1346.452,4:597.878}

def inside(d,exits=NEW_EXIT):
    direction=d.cohort_direction if 'cohort_direction' in d else d.direction
    return (direction.eq(2)&d.y.between(400,exits[2]))|(direction.eq(4)&d.y.between(exits[4],1400))

class ReducedBoundaryModel(DiagnosticModel):
    def setup(self,*args,**kwargs):
        super().setup(*args,**kwargs);self.exit_cuts={int(k):v for k,v in self.inputs['receiving_scope']['exit_ft'].items()}
        if any((a.direction==2 and self.network.local_y(a.position,2)>self.exit_cuts[2]) or (a.direction==4 and self.network.local_y(a.position,4)<self.exit_cuts[4]) for a in self.agents):
            raise RuntimeError('Initial agent already outside reduced route; explicit initialization amendment required')
    def step(self):
        before={a.agent_id:(a.position,a.speed) for a in self.agents};super().step()
        for a in list(self.agents):
            cut=self.network.progress(self.exit_cuts[a.direction],a.direction)
            if a.position<cut:continue
            old,v=before.get(a.agent_id,(0.,a.speed));distance=max(0.,cut-old)
            root=math.sqrt(max(0.,v*v+2*a.acceleration*distance));within=2*distance/(v+root) if v+root>0 else 0.
            a.exit_time=self.simulation_time-DT+min(DT,max(0.,within));a.state='EXITED';self.exited+=1
            self.recorder.exits.append({'agent_id':a.agent_id,'boundary':'REDUCED_EXIT','direction':a.direction,'exit_time_s':a.exit_time})
            if not a.initial:self.recorder.travels.append({'agent_id':a.agent_id,'direction':a.direction,'travel_time_s':a.exit_time-a.entry_time,'entry_time_s':a.entry_time,'exit_time_s':a.exit_time})
            self.agents.remove(a)
        self.refresh_relations();self.assert_invariants()

def inputs_for(mode):
    d=json.loads((ROOT/'outputs/peachtree3r/revised_inputs.json').read_text()) if mode!='OLD' else load_inputs()
    if mode=='NEW_REDUCED_SCOPE':d['receiving_scope']={'entry_ft':{'2':400.,'4':1400.},'exit_ft':{str(k):v for k,v in NEW_EXIT.items()}}
    return d

def run(mode,seed,trace=False):
    p=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text());data=inputs_for(mode)
    cls=ReducedBoundaryModel if mode=='NEW_REDUCED_SCOPE' else DiagnosticModel
    m=cls({'steps':round(data['horizon_s']/.1),'seed':seed},inputs=data,idm=IDMParameters(**p['parameters']),trace=trace,queue_gap=p['queue_gap_m']);m.run(display=False)
    return m,pd.DataFrame(m.observations,columns=COLUMNS)

def source_data():
    full=full_b2();real=real_targets(full);real=leaders(real,full,set(load_b2_source().trajectory_key));real=real[real.longitudinal_observation].copy()
    real['headway']=real.space_headway;return real

def headway(d):
    if 'vehicle_id' in d:
        cf=load_b2_cf();keys=set(zip(cf.vehicle_id,cf.frame_id));mask=np.array([(v,f) in keys for v,f in zip(d.vehicle_id,d.frame)])
        leader_inside=(d.direction.eq(2)&d.leader_y.between(400,NEW_EXIT[2]))|(d.direction.eq(4)&d.leader_y.between(NEW_EXIT[4],1400))
        return d.loc[mask&d.headway.gt(0)&leader_inside,'headway'].to_numpy()
    from scripts.finish_peachtree3r import sim_headway
    return sim_headway(d)

def queue_proxy(d):
    q=d[d.intersection.isin([2,3])&d.lane.isin([1,2])].sort_values(['frame','intersection','direction','lane','distance']).copy()
    if q.empty:return 0.,0.
    groups=q.groupby(['frame','intersection','direction','lane']);previous_distance=groups.distance.shift();previous_length=groups.length.shift()
    gap=q.distance-previous_distance-previous_length;limit=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['queue_gap_m']/(1200/3937)
    q['connected']=q.speed.le(STOP_FT_S)&(previous_distance.isna()|gap.le(limit));q['prefix']=q.groupby(['frame','intersection','direction','lane']).connected.cumprod()
    count=q.groupby('frame').prefix.sum();return float(count.mean()),float(count.max())

def exit_times(d,exits):
    temp=d.copy();temp['cohort_direction']=temp.direction
    return pd.concat([crossing_events(temp,exits[di],di) for di in [2,4]])

def real_travel(d,exits):
    events=pd.concat([crossing_events(d,400.,2).assign(event='ENTRY'),crossing_events(d,1400.,4).assign(event='ENTRY'),
        crossing_events(d,exits[2],2).assign(event='EXIT'),crossing_events(d,exits[4],4).assign(event='EXIT')])
    pairs=events.pivot_table(index='id',columns='event',values='time',aggfunc='first').dropna();return (pairs.EXIT-pairs.ENTRY).to_numpy()

def metric_bundle(d,travel,exits,real,real_tt,real_exits):
    episodes=stop_episodes(d);complete=episodes[~episodes.left_censored&~episodes.right_censored].duration_s
    real_ep=stop_episodes(real);real_dur=real_ep[~real_ep.left_censored&~real_ep.right_censored].duration_s
    h=headway(d);rh=headway(real);qmean,qmax=queue_proxy(d)
    bins=np.arange(0,load_inputs()['horizon_s']+30,30)
    hist=np.histogram(exits,bins)[0];realhist=np.histogram(real_exits,bins)[0]
    return {'speed_mean_ft_s':d.speed.mean(),'speed_KS':ks_2samp(real.speed,d.speed,method='asymp').statistic,'speed_W1_ft_s':wasserstein_distance(real.speed,d.speed),
        'headway_mean_ft':h.mean(),'headway_KS':ks_2samp(rh,h,method='asymp').statistic,'headway_W1_ft':wasserstein_distance(rh,h),
        'travel_mean_s':np.mean(travel),'travel_W1_s':wasserstein_distance(real_tt,travel),'operational_stopped':d.speed.le(STOP_FT_S).mean(),
        'stop_episodes':len(episodes),'vehicles_stopped_fraction':episodes.id.nunique()/d.id.nunique(),'complete_stop_duration_mean_s':complete.mean(),
        'stop_duration_W1_s':wasserstein_distance(real_dur,complete),'queue_proxy_mean':qmean,'queue_proxy_max':qmax,
        'throughput_total':len(exits),'throughput_temporal_L1_normalized':np.abs(hist-realhist).sum()/max(1,realhist.sum()),'rows':len(d)}

def worker(job):
    mode,seed=job;model,d=run(mode,seed)
    # Same directional exits for all metric comparisons; OLD/REVISED physics
    # continue beyond them, NEW physically exits there. No history moves an agent.
    real=source_data();rc=real[inside(real)].copy();dc=d[inside(d)].copy()
    from calibration.structural import contextualize
    rc=contextualize(rc,load_inputs())
    rtt=real_travel(real,NEW_EXIT);rex=exit_times(real,NEW_EXIT).time.to_numpy()
    if mode=='NEW_REDUCED_SCOPE':
        ex=pd.DataFrame(model.recorder.exits).rename(columns={'agent_id':'id','exit_time_s':'time'})
    else:ex=exit_times(d,NEW_EXIT)
    cross=ex.set_index('id').time
    entry={a.agent_id:a.entry_time for a in model.all_agents if not a.initial}
    travel=np.array([time-entry[key] for key,time in cross.items() if key in entry])
    bundle=metric_bundle(dc,travel,ex.time.to_numpy(),rc,rtt,rex)
    bundle.update(mode=mode,seed=seed,conservation_verified=model.summary['conservation_verified'],remaining=model.summary['vehicles_remaining'],pending=model.summary['pending_arrivals'],
        north_exit_ft=NEW_EXIT[2],south_exit_ft=NEW_EXIT[4],north_entry_ft=400.,south_entry_ft=1400.,
        section_travel_mean_s=np.mean([x['travel_time_s'] for x in model.recorder.section_times]))
    return bundle

def evaluate(acquisition='B2'):
    require_train(acquisition)
    plan=json.loads((OUT/'decision.json').read_text())
    if plan['decision']!='B. FREEZE_REDUCED_SCOPE':raise RuntimeError('No reduced scope frozen')
    seeds=list(range(3000,3030));jobs=[(mode,seed) for mode in ['OLD','REVISED','NEW_REDUCED_SCOPE'] for seed in seeds]
    results=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(worker,jobs):
            results.append(row);print(f'{row["mode"]} seed{row["seed"]}: stop={row["operational_stopped"]:.4f} TT={row["travel_mean_s"]:.2f}',flush=True)
            pd.DataFrame(results).to_csv(OUT/'paired_pre_recalibration_runs.csv',index=False)
    frame=pd.DataFrame(results);frame.to_csv(OUT/'paired_pre_recalibration_runs.csv',index=False)
    rows=[]
    for mode,d in frame.groupby('mode'):
        for metric in d.select_dtypes(include='number').columns:
            if metric=='seed':continue
            v=d[metric];sd=v.std(ddof=1);half=t.ppf(.975,29)*sd/np.sqrt(30)
            rows.append({'mode':mode,'metric':metric,'n':30,'mean':v.mean(),'SD':sd,'CI95_low':v.mean()-half,'CI95_high':v.mean()+half})
    pd.DataFrame(rows).to_csv(OUT/'pre_recalibration_metrics.csv',index=False)
    model,d=run('NEW_REDUCED_SCOPE',210,True);d.to_parquet(OUT/'new_scope_reference_observations.parquet',index=False)
    pd.DataFrame(model.recorder.times).to_csv(OUT/'new_scope_reference_timeseries.csv',index=False)
    from ui.canvas_renderer import finite_json
    trace={'training_acquisition':'B2','seed':210,'network':model.inputs['network'],'frames':model.recorder.traces,'summary':model.summary,'receiving_scope':model.inputs['receiving_scope']}
    (OUT/'new_scope_reference_trace.json').write_text(json.dumps(finite_json(trace),default=lambda x:x.item(),allow_nan=False),encoding='utf-8')
    real=source_data();rc=real[inside(real)].copy()
    from calibration.structural import contextualize
    rc=contextualize(rc,load_inputs());rc.to_parquet(OUT/'real_same_scope_observations.parquet',index=False)
    source=metric_bundle(rc,real_travel(real,NEW_EXIT),exit_times(real,NEW_EXIT).time.to_numpy(),rc,real_travel(real,NEW_EXIT),exit_times(real,NEW_EXIT).time.to_numpy())
    pd.DataFrame([source]).to_csv(OUT/'real_same_scope_metrics.csv',index=False)
    print(pd.DataFrame(rows)[pd.DataFrame(rows).metric.isin(['speed_mean_ft_s','travel_mean_s','operational_stopped'])].to_string(index=False))

if __name__=='__main__':evaluate()
