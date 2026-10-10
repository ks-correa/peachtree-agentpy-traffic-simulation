"""Exactly three predeclared signal-only alternatives; no scenario search."""
import json,copy,math,types
from datetime import datetime,timezone
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from calibration.final_structure import final_inputs,FinalStructureModel
from calibration.holdout_validation import inputs as b1_inputs,frozen_parameters,train_queue_gap,sha
from calibration.final_calibration import targets,section_times
from calibration.structural import COLUMNS
from calibration.structural_metrics import crossings,stop_episodes,STOP_FT_S
from calibration import control_envelope as env
from simulation.training_data import ROOT

OUT=ROOT/'outputs/peachtree6';MODES=('BASE','E1','E2','E3')
PRIMARY=['travel_mean_s','section_travel_mean_s','operational_stopped','vehicles_stopped_fraction','stop_episodes_per_vehicle',
         'departure_t50_s','departure_t90_s','departure_final_s','NB_travel_mean_s','SB_travel_mean_s','NB_operational_stopped','SB_operational_stopped']

def verify():
    audit=json.loads((OUT/'pre_experiment_integrity.json').read_text())
    for path,value in audit['prior_artifact_hashes'].items():
        if sha(ROOT/path)!=value:raise RuntimeError('Prior freeze/artifact changed: '+path)
    return audit

def original(context):return final_inputs() if context=='B2' else b1_inputs() if context=='B1' else (_ for _ in ()).throw(ValueError('Unknown context'))

def cycles(rows):
    rows=sorted(rows,key=lambda r:r['t_start_s']);found=[]
    for j in range(len(rows)-3):
        parts=rows[j:j+4]
        if [p['state'] for p in parts]==['GREEN','YELLOW','RED','GREEN']:
            if any(abs(parts[k]['t_end_s']-parts[k+1]['t_start_s'])>1e-7 for k in range(3)):raise RuntimeError('Noncontiguous schedule')
            found.append(parts)
    return found

def extend_edges(rows,start,end):
    """Periodic extension of nearest complete observed G/Y/R cycle at edges.

    Observed interior remains untouched; no inferred field program claimed.
    Needed when translating B1's first recorded signal beyond simulation origin.
    """
    rows=copy.deepcopy(sorted(rows,key=lambda r:r['t_start_s']));blocks=cycles(rows)
    if not blocks:raise RuntimeError('No complete observed cycle for edge extension')
    for edge,block in [('left',blocks[0]),('right',blocks[-1])]:
        period=block[3]['t_start_s']-block[0]['t_start_s']
        if edge=='left':
            boundary=rows[0]['t_start_s'];anchor=block[0]['t_start_s']
            extra=[]
            for shift in np.arange(-period, start-anchor-2*period, -period):
                for p in block[:3]:
                    a=p['t_start_s']+shift;b=p['t_end_s']+shift
                    if a<boundary and b>start-period:
                        r=dict(p,t_start_s=float(a),t_end_s=float(min(b,boundary)),edge_extension=True)
                        if r['t_end_s']>r['t_start_s']:extra.append(r)
            # The cycle preceding its anchor fills the unobserved prefix; partial
            # first observed phase can begin earlier than the original anchor.
            rows=sorted(extra+rows,key=lambda r:r['t_start_s'])
            # Trim overlap against the first observed event, never its timing.
            clean=[]
            for r in rows:
                if clean and r['t_start_s']<clean[-1]['t_end_s']-1e-8:
                    clean[-1]['t_end_s']=r['t_start_s']
                if r['t_end_s']>r['t_start_s']:clean.append(r)
            rows=clean
        else:
            boundary=rows[-1]['t_end_s'];anchor=block[0]['t_start_s'];extra=[]
            for shift in np.arange(period, end-anchor+2*period,period):
                for p in block[:3]:
                    a=p['t_start_s']+shift;b=p['t_end_s']+shift
                    if b>boundary and a<end+period:
                        r=dict(p,t_start_s=float(max(a,boundary)),t_end_s=float(b),edge_extension=True)
                        if r['t_end_s']>r['t_start_s']:extra.append(r)
            rows+=extra;rows=sorted(rows,key=lambda r:r['t_start_s'])
    return rows

def transform(data,mode,design):
    if mode not in MODES:raise ValueError('Exactly BASE/E1/E2/E3')
    out=copy.deepcopy(data)
    if mode=='BASE':out['scenario']='BASE';out['scenario_context']=data['acquisition_id'];return out
    records=[];shift=design['E2']['OFFSET_SHIFT_SECONDS'];down=design['E2']['downstream_intersection']
    start=data['source_window_start_relative_s'];end=start+data['horizon_s']
    for (i,di),group in pd.DataFrame(data['signals']).groupby(['intersection_id','direction']):
        rows=group.to_dict('records')
        # Only shifted downstream series need extrapolation outside known data.
        if mode in ['E2','E3'] and i==down:rows=extend_edges(rows,start-shift-1,end-shift+1)
        if mode in ['E1','E3']:
            for block in cycles(rows):
                green,yellow,red,_=block;g=green['t_end_s']-green['t_start_s'];r=red['t_end_s']-red['t_start_s']
                increment=math.floor((min(.1*g,r-.1)+1e-8)/.1)*.1
                increment=max(0.,increment)
                green['t_end_s']+=increment;yellow['t_start_s']+=increment;yellow['t_end_s']+=increment;red['t_start_s']+=increment
        if mode in ['E2','E3'] and i==down:
            for r in rows:r['t_start_s']+=shift;r['t_end_s']+=shift
        records.extend(rows)
    out['signals']=records;out['scenario']=mode;out['scenario_context']=data['acquisition_id'];out['progression']=design['E2'];return out

def prepare():
    audit=verify()
    if (OUT/'scenario_design_freeze.json').exists():raise RuntimeError('Scenario design already frozen; no redesign')
    b2=targets();d=b2['data'];counts=d.groupby('direction').id.nunique().to_dict();dominant=max(counts,key=lambda k:(counts[k],-k))
    upstream,downstream=(2,3) if dominant==2 else (3,2)
    c=crossings(b2['full'],final_inputs());pairs=c.pivot_table(index='id',columns='intersection',values='time').dropna();times=[]
    for id,row in pairs.iterrows():
        q=b2['full'][b2['full'].id.eq(id)];di=int(q.direction.iloc[0])
        a,b=row[upstream],row[downstream]
        if di!=dominant or b<=a:continue
        link=q[q.time.between(a,b)]
        if len(link) and not link.speed.le(STOP_FT_S).any() and (np.diff(link.frame)==1).all() and link.movement.eq(1).all():times.append(b-a)
    refs={(r['intersection'],r['direction']):r['local_y_ft'] for r in final_inputs()['network']['stop_lines']}
    source='B2 REAL complete no-stop Through effective-cut trips'
    if len(times)>=10:tau=float(np.median(times))
    else:
        link=d[d.direction.eq(dominant)&d.y.between(min(refs[(2,dominant)],refs[(3,dominant)]),max(refs[(2,dominant)],refs[(3,dominant)]))&d.speed.gt(STOP_FT_S)]
        tau=abs(refs[(2,dominant)]-refs[(3,dominant)])/link.speed.median();source='B2 REAL distance / median moving link speed; fewer than10 complete no-stop trips'
    data=final_inputs();origin=data['source_window_start_relative_s'];sig=pd.DataFrame(data['signals'])
    def greens(i):return sig[sig.intersection_id.eq(i)&sig.direction.eq(dominant)&sig.state.eq('GREEN')].t_start_s.to_numpy()
    up=greens(upstream);dn=greens(downstream);upref=float(up[up>=origin][0]);dnref=float(dn[dn>=origin][0]);cycle=float(np.median(np.diff(dn)))
    base_offset=(dnref-upref)%cycle;e2offset=tau%cycle;shift=(e2offset-base_offset+cycle/2)%cycle-cycle/2
    design=dict(status='FROZEN',created_at=datetime.now(timezone.utc).isoformat(),configurations=list(MODES),exactly_three_alternatives=True,
        BASE={'rule':'Own observed acquisition schedule, byte-equivalent signal rows'},
        E1={'rule':'Nominal Through green+10%; extra green from same-cycle RED; G onset and nextG onset fixed; Y duration fixed',
            'classification':'EXPERIMENTAL_RULE','increment_rule':'floor(min(0.1*G,RED-0.1)/0.1)*0.1;0.1s grid and positive RED constraint only',
            'partial_cycles':'Unchanged unless a complete observed/edge-extended G/Y/R/G cycle is available','all_red':'Not separately observed in modeled schedules; no independent all-red phase changed'},
        E2={'rule':'Single downstream intersection shift applied equally to both modeled NB/SB phase series',
            'DOMINANT_PROGRESSION_DIRECTION':'NB' if dominant==2 else 'SB','direction':int(dominant),'B2_demand_counts':{str(k):int(v) for k,v in counts.items()},
            'upstream_intersection':upstream,'downstream_intersection':downstream,'PROGRESSION_TRAVEL_TIME':tau,'n_no_stop':len(times),
            'P25':float(np.quantile(times,.25)) if times else None,'P75':float(np.quantile(times,.75)) if times else None,
            'IQR':float(np.quantile(times,.75)-np.quantile(times,.25)) if times else None,'source':source,'minimum_no_stop_n':10,
            'reference_cycle_s':cycle,'upstream_green_reference_s':upref,'downstream_green_reference_s':dnref,
            'BASE_OFFSET':base_offset,'E2_OFFSET':e2offset,'OFFSET_SHIFT_SECONDS':shift,
            'interpretation':'CORRIDOR PROGRESSION STRATEGY FOR B2 DOMINANT THROUGH DIRECTION; same shift in B1, no B1 design'},
        E3={'rule':'Exactly E1 then E2; same predeclared shift, never recompute offset'},
        edge_rule='Nearest complete observed G/Y/R cycle repeated only outside observed clock coverage to support a shifted full horizon; experimental edge assumption, interior durations unchanged',
        decision_score={'weights':{'TRAVEL':.25,'STOPPING':.25,'TEMPORAL_FLOW':.25,'DIRECTIONAL_BALANCE':.25},
            'TRAVEL':'mean(corridor/BASE, section/BASE)-1',
            'STOPPING':'mean(stopped_fraction/BASE, vehicles_stopped/BASE, mean_stopped_time_per_vehicle/BASE, stop_episodes_per_vehicle/BASE)-1',
            'TEMPORAL_FLOW':'mean(t50/BASE,t90/BASE,tfinal/BASE)-1',
            'DIRECTIONAL_BALANCE':'max over NB/SB of mean(travel/BASE-1, stopped/BASE-1); lower is better',
            'tie_rule':'Pareto first; among alternatives non-dominated in both contexts, minimum equally pooled B1/B2 score with negative score in both; else NO_ALTERNATIVE_DOMINATES_BASELINE',
            'robustness':'mean negative in both and >50% paired seeds negative in each = ROBUST_IMPROVEMENT; opposite mean signs CONTEXT_DEPENDENT; positive both and majority positive ROBUST_WORSENING; otherwise MIXED'},
        primary_metrics=PRIMARY,negative_difference_means_improvement=True,temporal_convention='Earlier t50/t90/final lower=better; positive cumulative departure E-BASE means earlier progression',
        scenario_optimization=False,design_may_change_after_results=False,freeze_hashes=audit['freeze_hashes'])
    for context in ['B2','B1']:
        for mode in MODES:
            altered=transform(original(context),mode,design)
            (OUT/f'signals_{context}_{mode}.json').write_text(json.dumps(altered['signals'],indent=2))
            validate_schedule(altered)
    seeds={'seeds':list(range(7000,7030)),'illustrative_seed':7000,'paired_all_contexts_modes':True}
    (OUT/'experiment_seeds.json').write_text(json.dumps(seeds,indent=2))
    design['signal_hashes']={str(p.relative_to(ROOT)):sha(p) for p in OUT.glob('signals_*.json')}
    design['seed_hash']=sha(OUT/'experiment_seeds.json');design['code_hash']=sha(__file__)
    (OUT/'scenario_design_freeze.json').write_text(json.dumps(design,indent=2))
    (OUT/'scenario_design_lock.json').write_text(json.dumps({'sha256':sha(OUT/'scenario_design_freeze.json')},indent=2))
    print(json.dumps(design['E2'],indent=2),flush=True)

def validate_schedule(data):
    from simulation.signals import controllers_from_inputs
    for key,c in controllers_from_inputs(data).items():
        for a,b in zip(c.intervals,c.intervals[1:]):
            if abs(a.end-b.start)>1e-6:raise RuntimeError('Signal gap/overlap '+str(key))
        if any(c.at(t)=='UNKNOWN' for t in [0.,data['horizon_s']-.1]):raise RuntimeError('Missing scenario signal coverage '+str(key))

def design():
    lock=OUT/'scenario_design_lock.json'
    if lock.exists() and sha(OUT/'scenario_design_freeze.json')!=json.loads(lock.read_text())['sha256']:raise RuntimeError('Scenario design changed after freeze')
    d=json.loads((OUT/'scenario_design_freeze.json').read_text())
    for path,value in d['signal_hashes'].items():
        if sha(ROOT/path)!=value:raise RuntimeError('Frozen scenario schedule changed')
    if sha(OUT/'experiment_seeds.json')!=d['seed_hash']:raise RuntimeError('Seed design changed')
    return d

def scenario_inputs(context,mode):
    d=design();out=original(context);out['signals']=json.loads((OUT/f'signals_{context}_{mode}.json').read_text());out['scenario']=mode;out['progression']=d['E2'];return out

class ScenarioModel(FinalStructureModel):
    def setup(self,inputs,idm,trace=False,queue_gap=3.):
        context=inputs['acquisition_id'];super().setup(inputs=dict(inputs,acquisition_id='B2'),idm=idm,trace=trace,queue_gap=queue_gap)
        self.inputs=inputs;self.demand.acquisition_id=context
    def assert_invariants(self):
        super().assert_invariants()
        if any(not all(math.isfinite(v) for v in [a.speed,a.position,a.acceleration]) for a in self.agents):raise RuntimeError('Nonfinite state')

def rollout(context,mode,seed,trace=False):
    data=scenario_inputs(context,mode);m=ScenarioModel({'steps':round(data['horizon_s']/.1),'seed':int(seed)},inputs=data,idm=frozen_parameters(),trace=trace,queue_gap=train_queue_gap())
    m.run(display=False);return m,pd.DataFrame(m.observations,columns=COLUMNS)

def queues(d,data):
    bank=lambda:data
    assoc=types.FunctionType(env.associate.__code__,dict(env.associate.__globals__,load_inputs=bank))
    dynamic=types.FunctionType(env.dynamics.__code__,dict(env.dynamics.__globals__,load_inputs=bank))
    a=assoc(d,[env.SignalControlEnvelope(**r) for r in data['control_envelopes']],'B2')
    q,mem=env.queue_series(a,train_queue_gap()/(1200/3937));h,r,p=dynamic(a,q,mem);return q,r,p

def measurements(d,m,direction=None):
    q=d if direction is None else d[d.direction.eq(direction)]
    ex=pd.DataFrame(m.recorder.exits).rename(columns={'agent_id':'id','exit_time_s':'time'});ex=ex if direction is None else ex[ex.direction.eq(direction)]
    entry={a.agent_id:a.entry_time for a in m.all_agents if not a.initial};tt=np.array([a.time-entry[a.id] for a in ex.itertuples() if a.id in entry])
    ep=stop_episodes(q);cross=crossings(q,m.inputs);pair=cross.pivot_table(index='id',columns='intersection',values='time').dropna()
    sec=np.abs(pair[3]-pair[2]);stopped=q.speed.le(STOP_FT_S);counts=stopped.groupby(q.id).sum()*.1
    times=np.sort(ex.time);n=q.id.nunique()
    expected=sum(1 for a in [*m.inputs['initial'],*m.inputs['entries']] if direction is None or a['direction']==direction)
    def departure_fraction(f):return times[math.ceil(f*expected)-1] if len(times)>=math.ceil(f*expected) else np.nan
    rows=dict(travel_mean_s=tt.mean(),section_travel_mean_s=sec.mean(),operational_stopped=stopped.mean(),
        vehicles_stopped_fraction=ep.id.nunique()/n,stop_episodes=len(ep),stop_episodes_per_vehicle=len(ep)/n,
        total_stopped_time_s=counts.sum(),mean_stopped_time_per_vehicle_s=counts.sum()/n,speed_mean_ft_s=q.speed.mean(),speed_median_ft_s=q.speed.median(),
        headway_mean_ft=q.headway[q.headway.gt(0)].mean(),departure_t50_s=departure_fraction(.5),departure_t90_s=departure_fraction(.9),departure_final_s=departure_fraction(1.),throughput_total=len(times))
    return rows,ex

def worker(job):
    context,mode,seed=job;m,d=rollout(context,mode,seed);row,ex=measurements(d,m)
    directional=[]
    for di,name in [(2,'NB'),(4,'SB')]:
        stats,_=measurements(d,m,di);row.update({name+'_'+k:v for k,v in stats.items()});directional.append(dict(context=context,scenario=mode,seed=seed,direction=name,**stats))
    q,r,p=queues(d,m.inputs)
    row.update(queue_mean=q.queue.mean(),queue_P90=q.queue.quantile(.9),queue_max=q.queue.max(),queue_spatial_mean_ft=q.spatial_ft.mean(),
        queue_at_green_onset_mean=r.queue_at_green_onset.mean(),clearance_mean_s=r.time_to_queue_clearance_s.mean())
    row.update(context=context,scenario=mode,seed=seed,conservation_verified=m.summary['conservation_verified'],no_overlap=True,
        no_negative_speed=bool(d.speed.ge(0).all()),remaining=m.summary['vehicles_remaining'],pending=m.summary['pending_arrivals'])
    folder=OUT/'replicas';pd.DataFrame(directional).to_csv(folder/f'directional_{context}_{mode}_{seed}.csv',index=False)
    ex.assign(context=context,scenario=mode,seed=seed).to_csv(folder/f'departures_{context}_{mode}_{seed}.csv',index=False)
    q.assign(context=context,scenario=mode,seed=seed).to_parquet(folder/f'queues_{context}_{mode}_{seed}.parquet',index=False)
    ep=stop_episodes(d);frame=d.groupby('frame').agg(active=('id','size'),speed=('speed','mean'))
    emerging=dict(context=context,scenario=mode,seed=seed,peak_active=frame.active.max(),speed_frame_SD=frame.speed.std(),
        RED_queue_mean=q[q.phase.eq('RED')].queue.mean(),GREEN_queue_mean=q[q.phase.eq('GREEN')].queue.mean(),
        vehicles_multiple_stops=int(ep.groupby('id').size().ge(2).sum()),green_clearance_s=r.time_to_queue_clearance_s.mean())
    pd.DataFrame([emerging]).to_csv(folder/f'emergent_{context}_{mode}_{seed}.csv',index=False)
    if seed==7000:d.to_parquet(OUT/f'illustrative_{context}_{mode}.parquet',index=False)
    return row

def evaluate():
    verify();d=design();(OUT/'replicas').mkdir(exist_ok=True);rows=[]
    seeds=json.loads((OUT/'experiment_seeds.json').read_text())['seeds']
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(worker,[(context,mode,seed) for context in ['B2','B1'] for mode in MODES for seed in seeds]):
            rows.append(row);frame=pd.DataFrame(rows)
            for context in ['B2','B1']:frame[frame.context.eq(context)].to_csv(OUT/f'{context.lower()}_scenario_runs.csv',index=False)
            print(f'{row["context"]} {row["scenario"]} seed{row["seed"]}: travel={row["travel_mean_s"]:.2f} stop={row["operational_stopped"]:.3f}',flush=True)
    verify();print('240 paired AgentPy rollouts complete',flush=True)
