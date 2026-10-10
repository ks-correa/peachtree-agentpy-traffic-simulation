"""B1 validation only: frozen physics, exogenous acquisition adapter, no fitting."""
import csv,json,hashlib,math,types
from functools import lru_cache
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp,wasserstein_distance
from simulation.training_data import ROOT
from simulation.parameters import FOOT_M,IDMParameters
from simulation.signals import controllers_from_inputs
from calibration.final_structure import FinalStructureModel,final_inputs
from calibration.structural import COLUMNS,contextualize
from calibration.structural_metrics import stop_episodes,crossings,STOP_FT_S,temporal
from calibration import control_envelope as envelope

OUT=ROOT/'outputs/peachtree5'
TITLE='TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify():
    audit=json.loads((OUT/'pre_validation_integrity.json').read_text())
    for path in ['outputs/peachtree3u/structural_model_freeze.json','outputs/peachtree4/calibration_freeze.json']:
        if json.loads((ROOT/path).read_text())['status']!='FROZEN':raise RuntimeError('Integrity: freeze not FROZEN')
    for path,expected in audit['prior_artifact_hashes'].items():
        if sha(ROOT/path)!=expected:raise RuntimeError('Integrity: previous artifact changed '+path)
    for path,expected in audit['snapshot_hashes'].items():
        if not path.startswith('ui\\') and sha(ROOT/path)!=expected:raise RuntimeError('Integrity: frozen code/parameters changed '+path)
    return audit

def read_b1_csv(path):
    # Acquisition route before numerical parsing, in a validation-only loader.
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        return pd.DataFrame([r for r in csv.DictReader(f) if r.get('acquisition_id',r.get('component'))=='B1'])

@lru_cache(maxsize=1)
def full_b1():
    if not (OUT/'pre_validation_integrity.json').exists():raise PermissionError('B1 requires prevalidated freezes and explicit phase5')
    cache=OUT/'b1_source.parquet'
    if cache.exists():d=pd.read_parquet(cache)
    else:
        rows=[];origins=set()
        with (ROOT/'data/peachtree_full.csv').open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                origin=int(r['global_time'])-100*int(r['frame_id']);origins.add(origin)
                if origin<1163030300:rows.append(r)
        if len(origins)!=2 or max(origins)!=1163030300:raise RuntimeError('Acquisition routing fingerprint changed')
        d=pd.DataFrame(rows)
        for col in d:
            if col!='location':d[col]=pd.to_numeric(d[col],errors='raise')
        d['acquisition_id']='B1';d['trajectory_key']='B1:'+d.vehicle_id.astype(str)
        d['t_relative']=(d.frame_id-d.frame_id.min())*.1
        d=d.sort_values(['vehicle_id','frame_id'],kind='stable');d.to_parquet(cache,index=False)
    if not d.acquisition_id.eq('B1').all():raise PermissionError('Validation cache is not isolated B1')
    return d

def prepare():
    verify();full=full_b1();trips=read_b1_csv(ROOT/'outputs/peachtree_fixed_gate_travel_times.csv')
    for col in ['entry_time_s','exit_time_s','direction','vehicle_id']:trips[col]=pd.to_numeric(trips[col])
    keys=set(trips.trajectory_key);core=full[full.trajectory_key.isin(keys)&full.local_y.between(400,1400)].copy()
    signals=read_b1_csv(ROOT/'outputs/peachtree_signal_timeline.csv')
    signals=signals[signals.phase.eq('Thru')&signals.intersection_id.isin(['2','3'])&signals.direction.isin(['2','4'])].copy()
    for col in ['intersection_id','direction','start_frame','end_frame_exclusive','t_start_s','t_end_s']:signals[col]=pd.to_numeric(signals[col])
    train=final_inputs();first_known=signals.groupby(['intersection_id','direction']).t_start_s.min().max()
    # Inherit TRAIN's deterministic0.5s start margin; never select a better frame.
    margin=train['source_window_start_relative_s']-pd.DataFrame(train['signals']).groupby(['intersection_id','direction']).t_start_s.min().max()
    start=float(first_known+margin);first=int(full.frame_id.min());startframe=first+round(start*10);end=float(full.t_relative.max())
    initial=[];attrs={}
    tripindex=trips.set_index('trajectory_key')
    for key,q in core.groupby('trajectory_key',sort=True):
        row=q.iloc[0];attrs[key]=dict(vehicle_class=int(row.v_class),length_m=float(row.v_length*FOOT_M),width_m=float(row.v_width*FOOT_M))
        hit=q[q.frame_id.eq(startframe)]
        if hit.empty:continue
        r=hit.iloc[0];lane=int(r.lane_id)
        if lane not in [1,2,11]:
            prior=q[q.frame_id.le(startframe)&q.lane_id.isin([1,2,11])];lane=int(prior.lane_id.iloc[-1]) if len(prior) else 1
        if (r.direction==2 and r.local_y>1346.452) or (r.direction==4 and r.local_y<597.878):continue
        initial.append(dict(**attrs[key],position_m=float((r.local_y-400 if r.direction==2 else 1400-r.local_y)*FOOT_M),lane=lane,
            speed_m_s=float(r.v_vel*FOOT_M),direction=int(r.direction),movement=1,
            initial_age_s=float(start-tripindex.loc[key,'entry_time_s']),source_key_for_boundary_audit_only=key))
    gates=read_b1_csv(ROOT/'outputs/peachtree_physical_gate_events.csv')
    for col in ['t_cross_s','direction','lane_id','vehicle_id']:gates[col]=pd.to_numeric(gates[col])
    gates=gates[gates.event.eq('ENTRY')&gates.t_cross_s.ge(start)&gates.trajectory_key.isin(keys)]
    entries=[]
    for r in gates.sort_values(['t_cross_s','vehicle_id']).itertuples():
        lane=int(r.lane_id);lane=lane if lane in [1,2,11] else 1
        entries.append(dict(**attrs[r.trajectory_key],requested_time_s=float(r.t_cross_s-start),lane=lane,direction=int(r.direction),movement=1,
            boundary=r.boundary,source_key_for_boundary_audit_only=r.trajectory_key))
    inputs=dict(train,acquisition_id='B1',validation_only=True,source_window_start_relative_s=start,source_window_start_frame=startframe,
        horizon_s=end-start,initial=initial,entries=entries,signals=signals.to_dict('records'),initial_count=len(initial),requested_entry_count=len(entries),
        signal_schedule_source='B1 OBSERVED EXOGENOUS INPUT',entry_speed_source='Frozen TRAIN B2 boundary distributions; no B1 speed sample fit',
        initial_protocol={'first_known_all_four_s':float(first_known),'inherited_TRAIN_margin_s':float(margin),'selected_frame':startframe},
        validation_name=TITLE)
    (OUT/'b1_exogenous_inputs.json').write_text(json.dumps(inputs,indent=2),encoding='utf-8')
    core.to_parquet(OUT/'b1_target_core.parquet',index=False)
    summary=pd.DataFrame([dict(acquisition='B1',eligible_original_through_cohort=len(keys),initial_vehicles=len(initial),arrivals=len(entries),
        modeled_vehicles=len(initial)+len(entries),start_relative_s=start,start_frame=startframe,end_relative_s=end,horizon_s=end-start,
        signal_schedule_source=inputs['signal_schedule_source'],entry_speed_source=inputs['entry_speed_source'])])
    summary.to_csv(OUT/'b1_input_summary.csv',index=False)
    paths=[ROOT/'data/peachtree_full.csv',ROOT/'outputs/peachtree_fixed_gate_travel_times.csv',ROOT/'outputs/peachtree_physical_gate_events.csv',ROOT/'outputs/peachtree_signal_timeline.csv',ROOT/'outputs/working/peachtree_cf_preparation_B1.parquet']
    paths += [ROOT/'data/reference/auxiliary/signal-timing/signal-change/Original Text files'/f'Peachtree_{street}_{direction}_1245-0100.txt' for street in ['11th','12th'] for direction in ['NB','SB']]
    (OUT/'b1_source_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):sha(p) for p in paths},indent=2))
    model=ValidationModel({'steps':1,'seed':6000},inputs=inputs,idm=frozen_parameters(),trace=False,queue_gap=train_queue_gap());model.run(display=False)
    print(summary.to_string(index=False),flush=True)

def frozen_parameters():
    d=json.loads((ROOT/'outputs/peachtree4/final_parameters.json').read_text());return IDMParameters(**d['values'],delta=4.)

def train_queue_gap():return json.loads((ROOT/'outputs/peachtree3u/structural_model_freeze.json').read_text())['queue_gap_m']

def inputs():return json.loads((OUT/'b1_exogenous_inputs.json').read_text())

class ValidationModel(FinalStructureModel):
    def setup(self,inputs,idm,trace=False,queue_gap=3.):
        if inputs.get('acquisition_id')!='B1' or not inputs.get('validation_only'):raise PermissionError('B1 validation-only adapter')
        # The frozen DemandStream constructor has a TRAIN routing guard. Supply
        # a private constructor token only; all values are the authorized B1
        # exogenous payload. Restore truthful B1 provenance immediately.
        # No TRAIN loader is changed or given B1, and demand methods stay identical.
        super().setup(inputs=dict(inputs,acquisition_id='B2'),idm=idm,trace=trace,queue_gap=queue_gap)
        self.inputs=inputs;self.demand.acquisition_id='B1';self.validation_only=True
    def assert_invariants(self):
        super().assert_invariants()
        for a in self.agents:
            if not all(math.isfinite(x) for x in [a.position,a.speed,a.acceleration]):raise RuntimeError('Nonfinite validation state')
    def step(self):
        super().step()
        for a in self.agents:
            if a.position>=self.network.progress(self.exit_cuts[a.direction],a.direction)+1e-7:raise RuntimeError('Reduced boundary violation')

def rollout(seed,trace=False):
    data=inputs();m=ValidationModel({'steps':round(data['horizon_s']/.1),'seed':int(seed)},inputs=data,idm=frozen_parameters(),trace=trace,queue_gap=train_queue_gap())
    m.run(display=False);d=pd.DataFrame(m.observations,columns=COLUMNS)
    for r in m.recorder.crossings:
        if m.controllers[(r['intersection'],r['direction'])].at(round(r['time_s']-.1,9))=='RED':raise RuntimeError('RED crossing')
    return m,d

@lru_cache(maxsize=1)
def real_data():
    data=inputs();core=pd.read_parquet(OUT/'b1_target_core.parquet');keys=set(core.trajectory_key)
    directions=core.groupby('trajectory_key').direction.first()
    full=full_b1();d=full[full.trajectory_key.isin(keys)&full.t_relative.ge(data['source_window_start_relative_s'])].copy()
    d=d.rename(columns={'trajectory_key':'id','frame_id':'frame','lane_id':'lane','local_y':'y','v_vel':'speed','v_length':'length'})
    d['cohort_direction']=d.id.map(directions);d=d[d.direction.eq(d.cohort_direction)].copy()
    d['time']=d.t_relative-data['source_window_start_relative_s'];d['headway']=d.space_headway
    return d

def inside(d):return (d.direction.eq(2)&d.y.between(400,1346.452))|(d.direction.eq(4)&d.y.between(597.878,1400))

def heading(d):
    if 'vehicle_id' in d:
        cf=pd.read_parquet(ROOT/'outputs/working/peachtree_cf_preparation_B1.parquet')
        if not cf.acquisition_id.eq('B1').all():raise RuntimeError('Not B1 CF preparation')
        keys=set(zip(cf.vehicle_id,cf.frame_id));full=full_b1().set_index(['frame_id','vehicle_id'])
        leader=full.reindex(pd.MultiIndex.from_arrays([d.frame,d.preceding]));ly=leader.local_y.to_numpy()
        ok=np.array([(v,f) in keys for v,f in zip(d.vehicle_id,d.frame)])
        ok &= np.where(d.direction.eq(2), (ly>=400)&(ly<=1346.452),(ly>=597.878)&(ly<=1400))
        return d.loc[ok&d.headway.gt(0),'headway'].to_numpy()
    # Byte-equivalent frozen road/headway measurement from3R/4, no optimizer import.
    def section(y):return np.where(((y>=630.810)&(y<=777.753))|((y>=1155.863)&(y<=1246.452)),0,np.where(y<630.810,2,np.where(y<1155.863,3,4)))
    lead=d.set_index(['frame','id']).reindex(pd.MultiIndex.from_arrays([d.frame,d.leader]));e=section(d.y.to_numpy());l=section(lead.y.to_numpy())
    return d.loc[(e>0)&(e==l)&d.intersection.gt(0)&d.lane.isin([1,2])&d.headway.notna(),'headway'].to_numpy()

def events(d,cut,di):
    rows=[]
    for key,q in d[d.direction.eq(di)].sort_values(['id','frame']).groupby('id',sort=False):
        y=q.y.to_numpy()*(1 if di==2 else -1);boundary=cut*(1 if di==2 else -1)
        hit=np.flatnonzero((y[:-1]<boundary)&(y[1:]>=boundary)&(np.diff(q.frame)==1))
        if len(hit):
            j=hit[0];t=q.time.iloc[j]+.1*(boundary-y[j])/(y[j+1]-y[j]);rows.append(dict(id=key,time=t))
    return pd.DataFrame(rows,columns=['id','time'])

def section_times(d):
    c=crossings(d,inputs());p=c.pivot_table(index=['id','direction'],columns='intersection',values='time',aggfunc='first').dropna()
    return np.abs(p[3]-p[2]).to_numpy()

def measured(d,model=None):
    crop=contextualize(d[inside(d)],inputs());ep=stop_episodes(crop);duration=ep[~ep.left_censored&~ep.right_censored].duration_s.to_numpy()
    if model is None:
        ex=pd.concat([events(d,1346.452,2),events(d,597.878,4)])
        ent=pd.concat([events(d,400,2),events(d,1400,4)])
        pair=ent.merge(ex,on='id',suffixes=('_entry','_exit'));travel=(pair.time_exit-pair.time_entry).to_numpy()
    else:
        ex=pd.DataFrame(model.recorder.exits).rename(columns={'exit_time_s':'time','agent_id':'id'})
        entry={a.agent_id:a.entry_time for a in model.all_agents if not a.initial}
        travel=np.array([r.time-entry[r.id] for r in ex.itertuples() if r.id in entry])
    return dict(data=crop,speed=crop.speed.to_numpy(),headway=heading(crop),travel=travel,duration=duration,section=section_times(d),
        exits=ex.time.to_numpy(),stopped=crop.speed.le(STOP_FT_S).mean(),vehicles_stopped=ep.id.nunique()/crop.id.nunique(),episodes=len(ep))

def metrics(pred,real):
    rows={}
    for name,unit in [('speed','ft_s'),('headway','ft'),('travel','s')]:
        x=pred[name];r=real[name]
        rows[name+'_mean_'+unit]=np.mean(x);rows[name+'_median_'+unit]=np.median(x)
        rows[name+'_KS']=ks_2samp(r,x,method='asymp').statistic;rows[name+'_W1_'+unit]=wasserstein_distance(r,x)
    rows.update(operational_stopped=pred['stopped'],vehicles_stopped_fraction=pred['vehicles_stopped'],stop_episodes=pred['episodes'],
        complete_stop_duration_mean_s=np.mean(pred['duration']),stop_duration_W1_s=wasserstein_distance(real['duration'],pred['duration']),
        section_travel_mean_s=np.mean(pred['section']),exact_zero_fraction=np.mean(pred['speed']==0),throughput_total=len(pred['exits']))
    horizon=inputs()['horizon_s'];bins=np.arange(0,horizon+30,30)
    diff=np.histogram(pred['exits'],bins)[0]-np.histogram(real['exits'],bins)[0]
    rows['throughput_temporal_L1_normalized']=np.abs(diff).sum()/max(1,len(real['exits']))
    clock=np.arange(round(horizon/.1)+1)*.1
    delta=np.searchsorted(np.sort(pred['exits']),clock,side='right')-np.searchsorted(np.sort(real['exits']),clock,side='right')
    rows['cumulative_departure_mean_abs_normalized']=np.abs(delta).mean()/max(1,len(real['exits']))
    return rows

def descriptive_score(m,real):
    spec=json.loads((ROOT/'outputs/peachtree4/objective_definition.json').read_text());s=spec['scales'];normal=spec['real_scalars']
    truth={'speed_mean':np.mean(real['speed']),'headway_mean':np.mean(real['headway']),'travel_mean':np.mean(real['travel']),
        'stopped':real['stopped'],'vehicles_stopped':real['vehicles_stopped'],'episodes':real['episodes'],'section_mean':np.mean(real['section'])}
    c=dict(speed_mean=abs(m['speed_mean_ft_s']-truth['speed_mean'])/normal['speed_mean'],speed_KS=m['speed_KS'],speed_W1=m['speed_W1_ft_s']/s['speed'],
        headway_mean=abs(m['headway_mean_ft']-truth['headway_mean'])/normal['headway_mean'],headway_KS=m['headway_KS'],headway_W1=m['headway_W1_ft']/s['headway'],
        travel_mean=abs(m['travel_mean_s']-truth['travel_mean'])/normal['travel_mean'],travel_W1=m['travel_W1_s']/s['travel'],
        stopped_fraction=abs(m['operational_stopped']-truth['stopped'])/normal['stopped'],vehicles_stopped=abs(m['vehicles_stopped_fraction']-truth['vehicles_stopped'])/normal['vehicles_stopped'],
        stop_episodes=abs(m['stop_episodes']-truth['episodes'])/normal['episodes'],stop_duration_W1=m['stop_duration_W1_s']/s['duration'],
        flow_histogram=m['throughput_temporal_L1_normalized'],flow_cumulative=m['cumulative_departure_mean_abs_normalized'],
        section_mean=abs(m['section_travel_mean_s']-truth['section_mean'])/normal['section_mean'])
    domains={name:np.mean([c[k] for k in keys]) for name,keys in spec['components'].items()}
    return dict(**{'E_'+k:v for k,v in domains.items()},validation_summary_score=sum(spec['weights'][k]*v for k,v in domains.items()))

def queue_analysis(d):
    env=[envelope.SignalControlEnvelope(**r) for r in inputs()['control_envelopes']]
    # Bind the frozen measurement function's signal input, without global patch
    # or code changes. Only the acquisition guard is validation-specific.
    def guard(acq):
        if acq!='B1':raise PermissionError('Validation measurement must be B1')
    assoc=types.FunctionType(envelope.associate.__code__,dict(envelope.associate.__globals__,load_inputs=inputs,require_train=guard))
    dynamic=types.FunctionType(envelope.dynamics.__code__,dict(envelope.dynamics.__globals__,load_inputs=inputs))
    d=d.copy()
    if 'vehicle_id' in d:
        d=d.sort_values(['id','frame']);d['normal']=d.lane.where(d.lane.isin([1,2]))
        breaks=d.id.ne(d.id.shift())|d.frame.diff().ne(1)|d.direction.ne(d.direction.shift());group=d.groupby(breaks.cumsum())
        before=group.normal.ffill();after=group.normal.bfill()
        recovered=d.lane.eq(0)&before.eq(after)&before.notna()&d.movement.eq(1)&d.int_id.isin([2,3])
        d.loc[recovered,'lane']=before[recovered]
    a=assoc(d,env,'B1');aliased=a.copy()
    # Original Following verifier has a literal B2 namespace; private aliases
    # change only identifiers for that check, then restore B1 on every output.
    aliased['id']=aliased.id.str.replace('B1:','B2:',regex=False)
    q,m=envelope.queue_series(aliased,train_queue_gap()/FOOT_M)
    q['head_id']=q.head_id.str.replace('B2:','B1:',regex=False);m['id']=m.id.str.replace('B2:','B1:',regex=False)
    m['head_id']=m.head_id.str.replace('B2:','B1:',regex=False)
    h,r,p=dynamic(a,q,m)
    return a,q,m,h,r,p

def real_context():
    full=full_b1();d=full[full.direction.isin([2,4])&full.v_class.isin([2,3])&full.t_relative.ge(inputs()['source_window_start_relative_s'])].copy()
    d=d.rename(columns={'trajectory_key':'id','frame_id':'frame','lane_id':'lane','local_y':'y','v_vel':'speed','v_length':'length'})
    d['time']=d.t_relative-inputs()['source_window_start_relative_s'];return d[inside(d)]
