"""Final predeclared structure: direct checks before paired B2 evaluation."""
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from calibration.final_structure import final_inputs,references,LEGACY,run_final
from calibration.receiving_scope import inside,metric_bundle,source_data,real_travel,exit_times,NEW_EXIT
from calibration.structural import contextualize
from simulation.training_data import ROOT,load_inputs
from simulation.parameters import FOOT_M,IDMParameters
from simulation.model import run_baseline
from scripts.run_peachtree3t import digest,analyze,summary,envelopes

OUT=ROOT/'outputs/peachtree3u'

def preserve():
    OUT.mkdir(parents=True,exist_ok=True);path=OUT/'pre_revision_hashes.json'
    if path.exists():return
    paths=[]
    for directory in ['outputs/peachtree3','outputs/peachtree3r','outputs/peachtree3s','outputs/peachtree3t']:
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file())
    paths.extend(p for p in (ROOT/'outputs').glob('b2_*') if p.is_file())
    paths.extend(p for p in (ROOT/'docs').glob('peachtree3*.md'))
    for directory in ['simulation','ui']:
        paths.extend((ROOT/directory).glob('*.py'))
    paths.extend([ROOT/'calibration/receiving_scope.py',ROOT/'calibration/control_envelope.py'])
    path.write_text(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in sorted(set(paths))},indent=2),encoding='utf-8')

def synthetic(i,di,lane=1,seed=10):
    data=final_inputs();data['source_window_start_relative_s']=0.;data['horizon_s']=45.;data['entries']=[]
    data['signals']=[dict(intersection_id=ii,direction=dd,t_start_s=start,t_end_s=end,state=state)
        for ii in [2,3] for dd in [2,4] for start,end,state in [(0.,25.,'RED'),(25.,46.,'GREEN')]]
    front=references()[(i,di)]-(1 if di==2 else -1)*100
    def vehicle(y):
        return dict(vehicle_class=2,length_m=4.,width_m=1.8,
            position_m=(y-400 if di==2 else 1400-y)*FOOT_M,speed_m_s=8.,lane=lane,direction=di,movement=1)
    data['initial']=[vehicle(front),vehicle(front-(1 if di==2 else -1)*30)]
    p=IDMParameters.load(ROOT/'outputs/b2_calibrated_parameters.json')
    # Same existing physics; synthetic test inputs never read real trajectories.
    model=run_baseline(data,p,seed=seed,trace=True,queue_gap=4.9414274828549685)
    return model

def direct_checks():
    checks=[]
    for (i,di),ref in references().items():
        for lane in [1,2]:
            model=synthetic(i,di,lane)
            sign=1 if di==2 else -1;head=model.all_agents[0]
            red=[a for f in model.recorder.traces if f['time']<=25. for a in f['agents'] if a['agent_id']==head.agent_id]
            late=[a for f in model.recorder.traces if 20<=f['time']<=25 for a in f['agents'] if a['agent_id']==head.agent_id]
            no_cross=all((a['position']-ref)*sign<0 for a in red)
            green=any(c['agent_id']==head.agent_id and c['intersection']==i and c['time_s']>25 for c in model.recorder.crossings)
            monotone=all((b['position']-a['position'])*sign>=-1e-8 for a,b in zip(red,red[1:]))
            conserved=all(x['initial_vehicles']+x['vehicles_entered']==x['vehicles_active']+x['vehicles_exited'] for x in model.recorder.times)
            minimum_gap=np.inf
            for f in model.recorder.traces:
                group=sorted(f['agents'],key=lambda a:-sign*a['position'])
                if len(group)>1:minimum_gap=min(minimum_gap,sign*(group[0]['position']-group[1]['position'])-group[0]['length_ft'])
            checks.append(dict(intersection=i,direction=di,lane=lane,effective_reference_ft=ref,red_no_cross=no_cross,
                stopped_before_reference=all(a['speed']<=.1/FOOT_M for a in late),green_release=green,
                correct_sign=monotone,no_overlap=minimum_gap>=-1e-7,minimum_gap_ft=minimum_gap,conservation=conserved))
    frame=pd.DataFrame(checks);frame.to_csv(OUT/'direct_control_checks.csv',index=False)
    columns=['red_no_cross','stopped_before_reference','green_release','correct_sign','no_overlap','conservation']
    if not frame[columns].all().all():raise RuntimeError('Concrete direct control invariant failed; see direct_control_checks.csv')
    return frame

def prepare():
    preserve();data=final_inputs();(OUT/'final_inputs.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    records=[dict(intersection=i,direction=di,EFFECTIVE_SIGNAL_CONTROL_REFERENCE=ref,
        LEGACY_SIGNAL_PROXY=LEGACY[(i,di)],difference_ft=ref-LEGACY[(i,di)],
        source='outputs/peachtree3t/intersection_envelopes.csv: entry',classification='DATASET_DERIVED',
        interpretation='Empirical adjacent-section to intersection annotation boundary; not a painted stop bar') for (i,di),ref in references().items()]
    pd.DataFrame(records).to_csv(OUT/'effective_control_references.csv',index=False)
    direct_checks();print('All 8 intersection/direction/lane direct physical checks passed',flush=True)

def worker(seed):
    model,d=run_final(seed);dc=d[inside(d)].copy()
    real=source_data();rc=contextualize(real[inside(real)],load_inputs())
    rtt=real_travel(real,NEW_EXIT);rex=exit_times(real,NEW_EXIT).time.to_numpy()
    ex=pd.DataFrame(model.recorder.exits).rename(columns={'agent_id':'id','exit_time_s':'time'})
    entry={a.agent_id:a.entry_time for a in model.all_agents if not a.initial}
    travel=np.array([t-entry[id] for id,t in zip(ex.id,ex.time) if id in entry])
    general=metric_bundle(dc,travel,ex.time.to_numpy(),rc,rtt,rex)
    a,q,m,h,r,p=analyze(dc,envelopes())
    for name,frame in [('heads',h),('residual',r),('propagation',p)]:
        frame.assign(seed=seed,series='FINAL_STRUCTURE').to_csv(OUT/'replicas'/f'{name}_{seed}.csv',index=False)
    # No fixed stop-zone supplied to dynamics; the four input coordinates alone changed.
    minimum_gap=d.gap.dropna().min()
    general.update(summary(q,h,r,p))
    general.update(seed=seed,mode='FINAL_STRUCTURE',conservation_verified=model.summary['conservation_verified'],
        conservation_every_tick=all(x['initial_vehicles']+x['vehicles_entered']==x['vehicles_active']+x['vehicles_exited'] for x in model.recorder.times),
        no_overlap=minimum_gap>=-1e-7,minimum_gap_ft=minimum_gap,remaining=model.summary['vehicles_remaining'],
        pending=model.summary['pending_arrivals'],section_travel_mean_s=np.mean([x['travel_time_s'] for x in model.recorder.section_times]))
    return general

def evaluate():
    direct=pd.read_csv(OUT/'direct_control_checks.csv')
    if not direct[['red_no_cross','green_release','no_overlap','conservation']].all().all():raise RuntimeError('Direct checks must pass first')
    (OUT/'replicas').mkdir(exist_ok=True);results=[]
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(worker,range(3000,3030)):
            results.append(row);pd.DataFrame(results).to_csv(OUT/'final_structure_30_replica_runs.csv',index=False)
            print(f'FINAL_STRUCTURE seed{row["seed"]}: stopped={row["operational_stopped"]:.4f} TT={row["travel_mean_s"]:.3f}',flush=True)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','evaluate'])
    stage=parser.parse_args().stage
    prepare() if stage=='prepare' else evaluate()
