"""Five-parameter B2 calibration on the immutable FINAL_STRUCTURE engine."""
import json,hashlib,math
from functools import lru_cache
from types import MappingProxyType
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp,wasserstein_distance
from calibration.final_structure import FinalStructureModel,final_inputs
from calibration.receiving_scope import inside,source_data,headway,real_travel,exit_times,NEW_EXIT
from calibration.structural import COLUMNS,contextualize
from calibration.structural_metrics import stop_episodes,crossings,STOP_FT_S
from simulation.training_data import ROOT,require_train
from simulation.parameters import IDMParameters,FOOT_M

OUT=ROOT/'outputs/peachtree4'
NAMES=('v0','T','s0','a','b')
DOMAINS=('speed','headway','travel','stopping','temporal_flow','section_travel')
WEIGHTS=MappingProxyType({name:1/6 for name in DOMAINS})

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_structure(acquisition='B2'):
    require_train(acquisition)
    freeze=ROOT/'outputs/peachtree3u/structural_model_freeze.json'
    d=json.loads(freeze.read_text())
    if d['status']!='FROZEN':raise RuntimeError('3U must be FROZEN')
    for field in ['structural_code_hashes','source_hashes']:
        for path,expected in d[field].items():
            if sha(ROOT/path)!=expected:raise RuntimeError('Frozen3U changed: '+path)
    final_inputs();return sha(freeze)

def plan(acquisition='B2'):
    require_train(acquisition);d=json.loads((OUT/'search_plan.json').read_text())
    for path,expected in d['frozen_artifact_hashes'].items():
        if sha(ROOT/path)!=expected:raise RuntimeError('Predeclared calibration artifact changed: '+path)
    if verify_structure()!=d['structural_freeze_sha256']:raise RuntimeError('3U freeze hash changed')
    return d

def parameters(values):
    if set(values)!=set(NAMES):raise ValueError('Only v0,T,s0,a,b are calibratable')
    bounds=pd.read_csv(OUT/'parameter_bounds.csv').set_index('parameter')
    for key,value in values.items():
        if not np.isfinite(value) or not bounds.loc[key,'lower']<=value<=bounds.loc[key,'upper']:
            raise ValueError('INVALID_CANDIDATE: outside bounds/nonfinite '+key)
    return IDMParameters(**values,delta=4.)

class CheckedCalibrationModel(FinalStructureModel):
    """Assertions only. No overridden physical decision/integration logic."""
    def assert_invariants(self):
        super().assert_invariants()
        for a in self.agents:
            if not all(math.isfinite(x) for x in [a.position,a.speed,a.acceleration,a.length]):raise RuntimeError('INVALID_CANDIDATE: nonfinite agent')
            if not 0<=a.position<=self.network.length+1e-7:raise RuntimeError('INVALID_CANDIDATE: global route violation')
            if a.direction not in [2,4] or a.lane not in [1,2,11]:raise RuntimeError('INVALID_CANDIDATE: direction/lane')
            if a.agent_role!='TARGET':raise RuntimeError('INVALID_CANDIDATE: population changed')
    def step(self):
        # Delegate every physical operation, then check reduced cuts after removal.
        super().step()
        for a in self.agents:
            cut=self.network.progress(self.exit_cuts[a.direction],a.direction)
            if a.position>=cut+1e-7:raise RuntimeError('INVALID_CANDIDATE: reduced boundary violation')

def rollout(values,seed,trace=False,acquisition='B2'):
    require_train(acquisition);p=parameters(values);data=final_inputs()
    frozen=json.loads((ROOT/'outputs/peachtree3u/structural_model_freeze.json').read_text())
    model=CheckedCalibrationModel({'steps':round(data['horizon_s']/.1),'seed':int(seed)},
        inputs=data,idm=p,trace=trace,queue_gap=frozen['queue_gap_m'])
    model.run(display=False)
    if not all(np.isfinite(r['exit_time_s']) and 0<=r['exit_time_s']<=data['horizon_s']+.1 for r in model.recorder.exits):raise RuntimeError('INVALID_CANDIDATE: invalid exit time')
    # Signal restriction is evaluated at tick start, crossing ledger at tick end.
    for r in model.recorder.crossings:
        if model.controllers[(r['intersection'],r['direction'])].at(round(r['time_s']-.1,9))=='RED':raise RuntimeError('INVALID_CANDIDATE: RED crossing')
    if any(c.at(t)=='UNKNOWN' for c in model.controllers.values() for t in [0,data['horizon_s']-.1]):raise RuntimeError('INVALID_CANDIDATE: invalid schedule')
    return model,pd.DataFrame(model.observations,columns=COLUMNS)

def section_times(d):
    c=crossings(d,final_inputs())
    pairs=c.pivot_table(index=['id','direction'],columns='intersection',values='time',aggfunc='first').dropna()
    return np.abs(pairs[3]-pairs[2]).to_numpy()

@lru_cache(maxsize=1)
def targets():
    # Guarded isolated B2 cache, never a historical mixed report.
    require_train('B2');full=source_data();d=contextualize(full[inside(full)],final_inputs())
    ep=stop_episodes(d);dur=ep[~ep.left_censored&~ep.right_censored].duration_s.to_numpy()
    return dict(data=d,full=full,speed=d.speed.to_numpy(),headway=headway(d),travel=real_travel(full,NEW_EXIT),
        duration=dur,section=section_times(full),exits=exit_times(full,NEW_EXIT).time.to_numpy(),episodes=len(ep),
        vehicles_stopped=ep.id.nunique()/d.id.nunique(),stopped=d.speed.le(STOP_FT_S).mean(),
        horizon=final_inputs()['horizon_s'])

def scales():
    r=targets();return {name:float(max(np.quantile(r[name],.75)-np.quantile(r[name],.25),1e-9)) for name in ['speed','headway','travel','duration']}

def measured(model,d):
    dc=d[inside(d)];ep=stop_episodes(dc);dur=ep[~ep.left_censored&~ep.right_censored].duration_s.to_numpy()
    exits=pd.DataFrame(model.recorder.exits)
    entry={a.agent_id:a.entry_time for a in model.all_agents if not a.initial}
    times=exits.exit_time_s.to_numpy() if len(exits) else np.array([])
    tt=np.array([row.exit_time_s-entry[row.agent_id] for row in exits.itertuples() if row.agent_id in entry]) if len(exits) else np.array([])
    # Same effective reference cuts and interpolation for REAL and SIM.
    section=section_times(dc)
    return dict(data=dc,speed=dc.speed.to_numpy(),headway=headway(dc),travel=tt,duration=dur,section=section,exits=times,
        episodes=len(ep),vehicles_stopped=ep.id.nunique()/dc.id.nunique(),stopped=dc.speed.le(STOP_FT_S).mean())

def metrics(pred):
    real=targets();rows={}
    for domain,unit in [('speed','ft_s'),('headway','ft'),('travel','s')]:
        x=pred[domain];r=real[domain]
        if not len(x) or not np.isfinite(x).all():raise RuntimeError('INVALID_CANDIDATE: empty/nonfinite '+domain)
        rows[domain+'_mean_'+unit]=float(np.mean(x));rows[domain+'_W1_'+unit]=wasserstein_distance(r,x)
        if domain!='travel':rows[domain+'_KS']=ks_2samp(r,x,method='asymp').statistic
    if not len(pred['duration']) or not len(pred['section']):raise RuntimeError('INVALID_CANDIDATE: empty stopped duration/section')
    rows.update(operational_stopped=float(pred['stopped']),vehicles_stopped_fraction=pred['vehicles_stopped'],stop_episodes=pred['episodes'],
        complete_stop_duration_mean_s=np.mean(pred['duration']),stop_duration_W1_s=wasserstein_distance(real['duration'],pred['duration']),
        section_travel_mean_s=np.mean(pred['section']),exact_zero_fraction=np.mean(pred['speed']==0),throughput_total=len(pred['exits']))
    bins=np.arange(0,real['horizon']+30,30.)
    rh=np.histogram(real['exits'],bins)[0];ph=np.histogram(pred['exits'],bins)[0]
    rows['throughput_temporal_L1_normalized']=np.abs(rh-ph).sum()/max(1,len(real['exits']))
    clock=np.arange(round(real['horizon']/.1)+1)*.1
    difference=np.searchsorted(np.sort(pred['exits']),clock,side='right')-np.searchsorted(np.sort(real['exits']),clock,side='right')
    rows['cumulative_departure_mean_abs_normalized']=np.abs(difference).mean()/max(1,len(real['exits']))
    rows['cumulative_departure_max_abs_normalized']=np.abs(difference).max()/max(1,len(real['exits']))
    return rows

def errors(m):
    spec=json.loads((OUT/'objective_definition.json').read_text());r=spec['real_scalars'];s=spec['scales'];c={}
    c['speed_mean']=abs(m['speed_mean_ft_s']-r['speed_mean'])/r['speed_mean']
    c['speed_KS']=m['speed_KS'];c['speed_W1']=m['speed_W1_ft_s']/s['speed']
    c['headway_mean']=abs(m['headway_mean_ft']-r['headway_mean'])/r['headway_mean']
    c['headway_KS']=m['headway_KS'];c['headway_W1']=m['headway_W1_ft']/s['headway']
    c['travel_mean']=abs(m['travel_mean_s']-r['travel_mean'])/r['travel_mean'];c['travel_W1']=m['travel_W1_s']/s['travel']
    c['stopped_fraction']=abs(m['operational_stopped']-r['stopped'])/r['stopped']
    c['vehicles_stopped']=abs(m['vehicles_stopped_fraction']-r['vehicles_stopped'])/r['vehicles_stopped']
    c['stop_episodes']=abs(m['stop_episodes']-r['episodes'])/r['episodes'];c['stop_duration_W1']=m['stop_duration_W1_s']/s['duration']
    c['flow_histogram']=m['throughput_temporal_L1_normalized'];c['flow_cumulative']=m['cumulative_departure_mean_abs_normalized']
    c['section_mean']=abs(m['section_travel_mean_s']-r['section_mean'])/r['section_mean']
    domains={domain:float(np.mean([c[key] for key in keys])) for domain,keys in spec['components'].items()}
    if not np.isfinite(list(c.values())).all():raise RuntimeError('INVALID_CANDIDATE: nonfinite error')
    total=sum(WEIGHTS[k]*domains[k] for k in DOMAINS)
    return dict(**{'component_'+k:v for k,v in c.items()},**{'E_'+k:v for k,v in domains.items()},objective=float(total))

def evaluate_job(job):
    candidate,values,seed=job
    try:
        model,d=rollout(values,seed);m=metrics(measured(model,d));err=errors(m)
        return dict(candidate=candidate,seed=seed,status='VALID',**values,**m,**err,
            conservation=True,no_overlap=True,no_negative_speed=True,valid_signals=True,valid_exits=True,
            finite_state=True,boundaries_valid=True,remaining=model.summary['vehicles_remaining'],pending=model.summary['pending_arrivals'])
    except (ValueError,RuntimeError,ArithmeticError) as exc:
        return dict(candidate=candidate,seed=seed,status='INVALID_CANDIDATE',reason=str(exc),objective=float('inf'),**values)

def final_parameters(acquisition='B2'):
    require_train(acquisition);path=OUT/'final_parameters.json'
    d=json.loads(path.read_text());freeze=OUT/'calibration_freeze.json'
    if freeze.exists() and sha(path)!=json.loads(freeze.read_text())['final_parameters_sha256']:raise RuntimeError('Final parameters changed after freeze')
    return MappingProxyType(d['values'])
