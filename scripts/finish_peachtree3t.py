"""Publish an explicitly non-frozen structural decision, with auditable evidence."""
import json
from dataclasses import asdict
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.run_peachtree3t import OUT,ROOT,PROXIES,envelopes,analyze,digest
from calibration.control_envelope import SignalControlEnvelope,KEY
from calibration.receiving_scope import run,inside
from simulation.training_data import load_inputs,load_b2_source
from simulation.signals import controllers_from_inputs
from ui.canvas_renderer import finite_json

def trace_for(seed):
    model,d=run('NEW_REDUCED_SCOPE',seed,True)
    a,q,m,h,r,p=analyze(d[inside(d)],envelopes())
    heads=q[q.queue.gt(0)].copy()
    bytime={round(t,1):g for t,g in heads.groupby('time')}
    for frame in model.recorder.traces:
        group=bytime.get(round(frame['time'],1))
        frame['queue_heads']=[] if group is None else [dict(id=row.head_id,queue=row.queue,spatial_ft=row.spatial_ft) for row in group.itertuples()]
    env=pd.read_csv(OUT/'intersection_envelopes.csv').to_dict('records')
    return finite_json({'training_acquisition':'B2','seed':seed,'network':model.inputs['network'],'summary':model.summary,
        'frames':model.recorder.traces,'receiving_scope':model.inputs['receiving_scope'],'control_envelopes':env,
        'mode':'CONTROL_ENVELOPE_REVISION','physical_engine':'NEW_REDUCED_SCOPE_UNCHANGED'})

def table(d):
    def value(x):
        if isinstance(x,(float,np.floating)):return f'{x:.3f}' if np.isfinite(x) else 'NA'
        return str(x).replace('|','/')
    lines=['| '+' | '.join(map(str,d.columns))+' |','| '+' | '.join(['---']*len(d.columns))+' |']
    lines+=['| '+' | '.join(value(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)]
    return '\n'.join(lines)

def figures(real,sim):
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    zones=pd.read_csv(OUT/'stop_zone_candidates.csv');heads=pd.read_csv(OUT/'queue_head_by_cycle.csv')
    residual=pd.read_csv(OUT/'residual_queue_after_green.csv');prop=pd.read_csv(OUT/'queue_start_propagation.csv')
    def save(name):
        plt.tight_layout();plt.savefig(figdir/name,dpi=180);plt.close()
    plt.figure(figsize=(10,5))
    for key,g in heads.groupby(KEY):plt.scatter(g.cycle,g.position_y,label='/'.join(map(str,key)),s=22)
    plt.xlabel('Observed RED interval index');plt.ylabel('Front-center Local_Y (ft)');plt.legend(ncol=4,fontsize=8);save('queue_head_positions.png')
    plt.figure(figsize=(12,5))
    for n,e in enumerate(pd.read_csv(OUT/'intersection_envelopes.csv').itertuples()):
        plt.plot([e.approach_start,e.exit],[n,n],lw=7,alpha=.25,color='steelblue')
        plt.plot([e.stop_low,e.stop_high],[n,n],lw=7,color='goldenrod')
        plt.scatter([e.entry,e.exit],[n,n],marker='|',s=100,color='black')
    plt.yticks(range(8),[f'{x.intersection}/{x.direction}/L{x.lane}' for x in zones.itertuples()]);plt.xlabel('Local_Y (ft) · bands are observational');save('controlled_envelope_map.png')
    a=pd.read_parquet(OUT/'real_envelope_observations.parquet');red=a[a.stopped&a.phase.eq('RED')]
    plt.figure(figsize=(11,4));plt.scatter(red.y,red.intersection+red.direction/10,s=1,alpha=.15);plt.xlabel('Front-center Local_Y (ft)');plt.ylabel('Intersection + direction / 10');save('red_stop_positions.png')
    plt.figure(figsize=(8,4))
    for name,g in residual.groupby('series'):
        plt.plot([5,10],[g.remaining_stopped_after_5s.mean(),g.remaining_stopped_after_10s.mean()],marker='o',label=name)
    plt.xlabel('Seconds after GREEN');plt.ylabel('Mean stopped members of initial queue');plt.legend();save('green_residual_queue.png')
    plt.figure(figsize=(9,4))
    for name,g in residual.groupby('series'):
        x=np.sort(g.time_to_queue_clearance_s.dropna());plt.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=name)
    plt.xlabel('Seconds to last initial member beyond junction exit · censored excluded');plt.ylabel('ECDF');plt.legend();save('queue_clearance.png')
    plt.figure(figsize=(9,4))
    for name,g in prop.groupby('series'):
        x=np.sort(g.queue_start_headway_s.dropna());plt.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=name)
    plt.xlabel('Follower movement onset minus leader onset (s)');plt.ylabel('ECDF');plt.legend();save('start_propagation.png')
    plt.figure(figsize=(8,4));plt.bar(['REAL B2','NEW reduced','Envelope revision'],[real.queue_mean.iloc[0],sim.queue_mean.mean(),sim.queue_mean.mean()]);plt.ylabel('Vehicles / observed occupied-lane snapshot');save('real_vs_sim_queue_length.png')

def finish():
    previous=pd.read_csv(ROOT/'outputs/peachtree3s/paired_pre_recalibration_runs.csv')
    queues=pd.concat([pd.read_csv(OUT/'paired_queue_replicas.csv'),pd.read_csv(OUT/'previous_paired_queue_replicas.csv')],ignore_index=True)
    if len(queues)!=90 or queues.groupby('mode').seed.nunique().ne(30).any():raise RuntimeError('Incomplete paired queue evaluation')
    paired=previous.merge(queues.drop(columns='conservation_verified'),on=['mode','seed'],validate='one_to_one')
    revision=paired[paired['mode'].eq('NEW_REDUCED_SCOPE')].copy();revision['mode']='CONTROL_ENVELOPE_REVISION'
    revision['evaluation_basis']='IDENTICAL_AGENTPY_STATES_MEASUREMENT_ONLY_REVISION'
    paired['evaluation_basis']='PRESERVED_3S_GENERAL_METRICS_PLUS_3T_QUEUE_ROLLOUT'
    paired=pd.concat([paired,revision],ignore_index=True);paired.to_csv(OUT/'paired_30_replica_comparison.csv',index=False)
    numeric=list(paired.select_dtypes(include='number').columns)
    paired.groupby('mode')[numeric].agg(['mean','std']).to_csv(OUT/'paired_summary.csv')
    real=pd.read_csv(OUT/'real_vs_sim_queue_dynamics.csv').iloc[:1]
    pd.concat([real,queues,queues[queues['mode'].eq('NEW_REDUCED_SCOPE')].assign(mode='CONTROL_ENVELOPE_REVISION')]).to_csv(OUT/'real_vs_sim_queue_dynamics.csv',index=False)
    # The new mode does not duplicate physics runs: same immutable state stream,
    # measurement association differs from the old nominal next_line classifier.
    residual=pd.read_csv(OUT/'residual_queue_after_green.csv');residual=residual[residual.series.eq('REAL_B2')]
    propagation=pd.read_csv(OUT/'queue_start_propagation.csv');propagation=propagation[propagation.series.eq('REAL_B2')]
    head_files=list((OUT/'replicas').glob('NEW_REDUCED_SCOPE_heads_*.csv'))
    if not head_files:head_files=list((OUT/'replicas').glob('heads_*.csv'))
    sim_heads=pd.concat([pd.read_csv(p) for p in head_files],ignore_index=True)
    real_heads=pd.read_csv(OUT/'queue_head_by_cycle.csv')
    per_seed=sim_heads.groupby(KEY+['seed']).position_y.median().reset_index()
    hs=per_seed.groupby(KEY).position_y.agg(sim_seed_median_mean='mean',sim_seed_median_SD='std',n_seeds='count').reset_index()
    rh=real_heads.groupby(KEY).position_y.agg(real_median='median',real_SD='std',real_head_cycles='count').reset_index()
    hs=hs.merge(rh,on=KEY);hs['sim_minus_real_ft']=hs.sim_seed_median_mean-hs.real_median
    hs.to_csv(OUT/'real_vs_sim_head_positions.csv',index=False)
    for name,base,target in [('residual',residual,'residual_queue_after_green.csv'),('propagation',propagation,'queue_start_propagation.csv')]:
        files=list((OUT/'replicas').glob(f'NEW_REDUCED_SCOPE_{name}_*.csv'))
        if not files:files=list((OUT/'replicas').glob(f'{name}_*.csv'))
        sim=pd.concat([pd.read_csv(p) for p in files],ignore_index=True)
        if sim.seed.nunique()!=30:raise RuntimeError('Missing replica dynamics')
        pd.concat([base,sim]).to_csv(OUT/target,index=False)
    # Same-vehicle annotation transitions with a temporal bracket, not a stop-bar estimate.
    from calibration.structural import full_b2
    full=full_b2();head=pd.read_csv(OUT/'first_queue_heads.csv');events=[]
    bank=controllers_from_inputs(load_inputs());origin=load_inputs()['source_window_start_relative_s']
    for row in head.itertuples():
        vehicle=int(row.id.split(':')[1]);track=full[full.vehicle_id.eq(vehicle)].sort_values('frame_id')
        prev=track.shift();sign=1 if row.direction==2 else -1
        entry=track.int_id.eq(row.intersection)&prev.int_id.ne(row.intersection)&track.frame_id.sub(prev.frame_id).eq(1)&track.direction.eq(row.direction)&track.movement.eq(1)
        for idx,a in track[entry].iterrows():
            before=prev.loc[idx];time=a.t_relative-origin
            if row.red_start<=time<=row.red_end+60:
                events.append({'id':row.id,'intersection':row.intersection,'direction':row.direction,'lane':row.lane,'cycle':row.cycle,
                    'from_section':before.section_id,'to_int':a.int_id,'from_lane':before.lane_id,'to_lane':a.lane_id,
                    'time_before':before.t_relative-origin,'time_after':time,'front_before_ft':before.local_y,'front_after_ft':a.local_y,
                    'phase':bank[(row.intersection,row.direction)].at(time),'reference_type':'ANNOTATION_ENTRY_CROSSING_BRACKET_NOT_STOP_BAR',
                    'head_stop_front_ft':row.front_bumper_position})
    pd.DataFrame(events).to_csv(OUT/'head_crossing_references.csv',index=False)
    changes=[]
    zones=pd.read_csv(OUT/'stop_zone_candidates.csv')
    for (i,di),old in PROXIES.items():
        changes.append({'intersection':i,'direction':di,'OLD_REFERENCE':old,'NEW_REFERENCE':old,'WHY':'NO_PHYSICAL_CHANGE: B2 head band and annotation mouth do not survey painted signal stop bar',
            'SOURCE':'Official metadata p13; B2 front heads; B2 section/int transitions','N_OBSERVATIONS':int(zones[zones.intersection.eq(i)&zones.direction.eq(di)].n.sum()),
            'UNCERTAINTY':'Physical stop bar unresolved; lane/head variability retained','changed':False})
    pd.DataFrame(changes).to_csv(OUT/'control_reference_changes.csv',index=False)
    errors=[
        ('MEASUREMENT_REFERENCE_ERROR','HIGH','Convention verified: Local_Y is front center; no extra half-length error confirmed in existing engine.'),
        ('CONTROL_ZONE_ERROR','HIGH','Nominal next_line loses own12th association before B2 stopped front/head band.'),
        ('QUEUE_HEAD_ERROR','HIGH','Approach-only proxy can miss head beyond nominal control; recovered lane0 requires bracketing agreement.'),
        ('SIGNAL_RELEASE_ERROR','MEDIUM','Group medians vary but only 5–8 valid releases/group; retain1.6s, do not fit.'),
        ('FOLLOWER_PROPAGATION_ERROR','MEDIUM','Observed onset lags are measurable; no mechanism added without stable gap-conditioned evidence.'),
        ('IDM_DYNAMIC_ERROR','LOW','Magnitude differences exist, but unresolved physical reference prevents parametric attribution.'),
        ('UNIDENTIFIED','HIGH','Painted stop-bar coordinates not established by available metadata/annotation; do not freeze physical model.')]
    pd.DataFrame(errors,columns=['error_class','confidence','evidence']).to_csv(OUT/'structural_error_classification.csv',index=False)
    params=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
    freeze={'phase':'PEACHTREE-3T','status':'NOT_FROZEN','classification':'B. NEEDS_STRUCTURAL_REVISION','remaining_difference':'STRUCTURAL',
        'reason':'Envelope association is corrected, but physical stop references are not independently identified. No fit-selected shift or artificial delay is allowed.',
        'scope':{'intersections':[2,3],'NB':{'entry_ft':400.,'exit_ft':1346.452},'SB':{'entry_ft':1400.,'exit_ft':597.878}},
        'control_references':changes,'signals_sha256':digest(ROOT/'data/b2_exogenous_inputs.json'),
        'signal_schedules':'Existing B2 observed schedules, no timing/offset changes',
        'stopped_definition':'speed <= 0.1 m/s, exact zero separate','queue_definition':'Front-most stopped same lane/direction, actual Following when available, contiguous spatial chain; frozen standstill gap',
        'queue_gap_m':params['queue_gap_m'],'head_window_ft':100,'head_window_reference':'B2 observed entry, not nominal physical proxy',
        'release_logic':'Existing1.6s pooled signal hold; followers IDM only','arrival_logic':'Existing B2 exogenous requests and safe-insertion FIFO',
        'VehicleAgent_rules':'Unchanged AgentPy IDM/ballistic/no clipping/no replay','lane_handling':'Existing necessary bay merge; discretionary LC disabled; diagnostic lane0 only contiguous bracketing normal-lane agreement',
        'dt_s':.1,'IDM_parameters':params['parameters'],'IDM_changed':False,'physical_references_changed':False,
        'new_mode':'CONTROL_ENVELOPE_REVISION: measurement/association only, NEW_REDUCED_SCOPE states unchanged',
        'B1_LOCKED':True,'E1_E2_E3':'DISABLED','final_calibration_authorized':False,'UI_status':'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED',
        'future_validation_name':'TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE'}
    (OUT/'structural_model_freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    (OUT/'decision.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    trace=trace_for(210);(OUT/'control_envelope_trace.json').write_text(json.dumps(trace,allow_nan=False,default=lambda x:x.item()),encoding='utf-8')
    figures(real,queues[queues['mode'].eq('NEW_REDUCED_SCOPE')])
    report(paired,real,zones,freeze)
    before=json.loads((OUT/'pre_revision_hashes.json').read_text());changed=[k for k,v in before.items() if digest(ROOT/k)!=v]
    unexpected=[k for k in changed if not k.startswith('ui\\')]
    (OUT/'preservation_check.json').write_text(json.dumps({'previous_artifacts_unchanged':not unexpected,'changed_files':changed,'unexpected_changes':unexpected},indent=2))
    if unexpected:raise RuntimeError('Prior artifact modification: '+str(unexpected))
    print('PEACHTREE-3T: B. NEEDS_STRUCTURAL_REVISION. 120 paired rows; measurement-only identity explicit.',flush=True)

def report(paired,real,zones,freeze):
    real_general=pd.read_csv(ROOT/'outputs/peachtree3s/real_same_scope_metrics.csv')
    real_general['section_travel_mean_s']=pd.read_csv(ROOT/'outputs/b2_observed_section_times.csv').travel_time_s.mean()
    metrics=['speed_mean_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_W1_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','stop_duration_W1_s','queue_mean','queue_P90','queue_max','queue_spatial_mean_ft','residual_5s_mean','residual_10s_mean','clearance_mean_s','propagation_mean_s','throughput_total','throughput_temporal_L1_normalized','section_travel_mean_s']
    comparison=paired.groupby('mode')[metrics].mean().T
    comparison['REAL_B2']=[real_general.iloc[0].get(k,real.iloc[0].get(k,np.nan)) for k in comparison.index]
    comparison.reset_index(names='metric').to_csv(OUT/'metric_comparison.csv',index=False)
    from scripts.run_peachtree3t import summary
    observed=pd.read_parquet(OUT/'real_envelope_observations.parquet')
    targets=set(load_b2_source().trajectory_key)
    _,tq,tm,th,tr,tp=analyze(observed[observed.id.isin(targets)],envelopes())
    pd.DataFrame([dict(summary(tq,th,tr,tp),series='REAL_B2_TARGET_ONLY_SENSITIVITY')]).to_csv(OUT/'real_target_queue_sensitivity.csv',index=False)
    release=pd.read_csv(OUT/'release_delay_by_group.csv');green=pd.read_csv(OUT/'green_stopping_classification.csv')
    green_counts=green.groupby('classification').size().reset_index(name='vehicle_frames')
    problem=pd.read_csv(OUT/'problem_12th_NB_frames.csv');ps=problem.groupby(['phase','source_lane','int_id','section_id','movement']).size().reset_index(name='frames')
    ps.to_csv(OUT/'problem_12th_NB_summary.csv',index=False)
    rq=pd.read_csv(OUT/'residual_queue_after_green.csv');pp=pd.read_csv(OUT/'queue_start_propagation.csv')
    dynamics=rq.groupby('series')[['queue_at_green_onset','time_to_first_release_s','time_to_stopped_queue_clearance_s','time_to_queue_clearance_s','remaining_stopped_after_5s','remaining_stopped_after_10s']].mean().reset_index()
    propagation=pp.groupby('series').queue_start_headway_s.agg(['count','mean','median','std']).reset_index()
    body=f'''# PEACHTREE-3T — Controlled envelope / queue head reconstruction

Decision: **B. NEEDS_STRUCTURAL_REVISION**. Remaining discrepancy: **STRUCTURAL**. No final IDM calibration, B1 validation or scenarios authorized by this result. `structural_model_freeze.json` explicitly says NOT_FROZEN.

1. Local_Y is the longitudinal front-center coordinate in feet (official Peachtree metadata attribute definition, printed page13); Local_X is its lateral coordinate. Neither is the vehicle centroid.
2. Front=Local_Y; center=Y−sign·length/2; rear=Y−sign·length. NB sign+1, SB−1. Rear/center are straight longitudinal projections; turning geometry is not reconstructed from length alone.
3. First physical stopped heads, separate intersection/direction/lane groups:

{table(zones[['intersection','direction','lane','n','n_cycles','median','SD','P10','P90','IQR']])}

Same-control/lane REAL versus30-seed SIM head positions (median per seed before averaging; no inter-junction pooling):

{table(pd.read_csv(OUT/'real_vs_sim_head_positions.csv'))}

4. Each head/cycle contributes one median position, not hundreds of independent frames. Within-cycle SD, between-cycle variance and outliers are saved. All groups have only5–9 cycles. 12th NB lane1 includes a distant sparse-queue head; it is retained as an outlier, not used to infer a painted stop bar. Repeated identical SB coordinates also require caution about source coding/position precision. Outlier labels use1.5IQR; IQR=0 can make several distinct values flagged. No positions were deleted to improve SIM fit.
5. P10–P90 observational head bands are STOP_ZONE candidates, not physically identified stop points. Bands are classification only; no vehicle is stopped, clipped or fixed because it is inside one. Sample sizes do not establish a surveyed lane-specific reference.
6–7. 11th/12th observational envelopes:

{table(pd.read_csv(OUT/'intersection_envelopes.csv'))}

ENTRY uses B2 adjacent section→intersection transition median. EXIT uses B2 annotation extent. APPROACH begins at the preceding observed junction exit or frozen ingress. DISCHARGE extends to the next observed junction entry/retained exit. These are annotation envelopes, not lane centerline surveys. INTERSECTION_ENTRY_REFERENCE, INTERSECTION_EXIT_REFERENCE, SIGNAL_CONTROL_REFERENCE and QUEUE_HEAD_REFERENCE remain distinct. STOP bands can overlap annotated interior; zone labels prioritize interior rather than concealing overlap.
8. Y1174–1192 NB is below the own12th exit1246.452 and lies across the observed road/int coding seam. Heads above1168.9155 are observed under own12th RED; using next_line at that proxy reassigns control too soon. Raw int/section/movement/source lane, front, head/follower flags are in problem_12th_NB_frames.csv; no inference from appearance was used. Unrecoverable lane0 remains OUTSIDE/unknown, not reassigned arbitrarily. Summary:

{table(ps)}

9. GREEN stopped vehicle-frame classification:

{table(green_counts)}

A requires membership in the previous RED onset cohort and no earlier movement onset. B requires an observed same-lane/direction stopped leader; C is an incompatible turn/local movement. D requires a stopped leader in the retained discharge zone; E preserves unknown cause. This is association, not causal proof. No green=free-flow assumption.
10–12. Initial RED queue membership is frozen at GREEN−0.1s. Release is movement onset >0.1m/s with contiguous tracking; stopped-queue clearance is the first simultaneous all-moving snapshot; discharge clearance is the last initial member past observational junction EXIT. Missing traces/crossings are censored, never filled with zero. Snapshot discharge timing has0.1s resolution. Means:

{table(dynamics)}

13. Existing1.6s pooled release is retained. Group samples are5–8 valid releases; differing medians are candidates for future study, not fitted strata. Neither the B2 head band nor these delays supplies a physical stop bar:

{table(release)}

14–15. START-UP PROPAGATION (follower onset minus leader onset), never cognitive reaction time:

{table(propagation)}

Negative lags are retained as observations, not clipped. This audit does not establish a stable gap-conditioned mechanism independent of IDM, so no propagation hold was added.
16. Main structural discrepancy: a point proxy loses own-intersection association while real front heads remain controlled, especially12th NB. HIGH confidence for association/measurement error; insufficient independent evidence for the replacement physical signal reference.
17. Physical references modified: NO. Current632.5395/777.262 (11th NB/SB) and1168.9155/1240.7775 (12th NB/SB) remain unchanged; their physical validity is unresolved. No mouth/head median was substituted as a stop bar.
18. Implemented immutable SignalControlEnvelope, front/rear semantics, contiguous bracketing lane0 recovery, front-most stopped chain using Following/spatial gap, cycle head bands, residual/release/discharge/propagation diagnostics and rendering overlays. All physics remain existing AgentPy. CONTROL_ENVELOPE_REVISION is a measurement-only mode consuming the identical NEW_REDUCED_SCOPE state stream; no claimed dynamic correction.
19–26. Paired seeds3000–3029: 90 new diagnostic rollouts of existing modes. General metrics come from preserved3S same-seed/same-scope results, avoiding duplicate calculations; queue dynamics are remeasured in3T. The30 revision rows share the exact NEW state stream by construction, explicitly tagged, not represented as an independent experiment. Before/after physical metrics are identical, and no success is claimed from measurement relabeling:

{table(comparison.reset_index(names='metric'))}

REAL general speed/headway/travel metrics use the frozen target cohort. REAL physical queue audit uses all observed arterial class2/3 context; SIM contains target agents only. Queue means/P90/spatial lengths use observed occupied-lane approach snapshots, not a full-clock demand-normalized mean; coverage and omitted agents limit causal interpretation. Queue max is per lane; old pooled queue proxy is retained separately. Clearance distributions omit censored observations and report observed counts in replica outputs. Temporal throughput uses the same30s bins as3S. Throughput total is observed demand, not road capacity. Section travel metric follows the unchanged3S definition. These limits prohibit a parametric-only conclusion.
27. TRAIN runner report: outputs/peachtree3t/test_report.json; all122 prior cases retained. New semantic/chain/envelope/holdout tests added; no legacy actual-source fixtures run. Final exact totals are in that report.
28. B1 LOCKED. No B1 behavioral data opened. Prior artifacts are hashed, and the preservation check identifies only intentional UI source changes. Historical exposure remains acknowledged: future validation must be called TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.
29. Remaining difference: STRUCTURAL, not defensibly PARAMETRIC. This does not prove an absent propagation mechanism; it identifies unresolved control geometry before such attribution.
30. B. NEEDS_STRUCTURAL_REVISION. No structural freeze is issued. Scope/dt/signals/IDM/demand are unchanged; the JSON contains the current constraints and explicit NOT_FROZEN status.
31. Next step: independently identify lane-specific painted control references from official scaled geometry/ortho or additional authorized TRAIN evidence, then formal structural revision and the same paired diagnostics. Do not choose coordinates by fit. Do not recalibrate IDM, open B1, expand the corridor or implement E1/E2/E3 now.

UI: Show control envelopes / Show queue heads are rendering-only overlays. Reduced boundaries remain400→1346.452 NB and1400→597.878 SB. TEST locked and scenarios disabled. **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**; automated unit/AppTest/Canvas checks do not establish visual browser validation.
'''
    (ROOT/'docs/peachtree3t_control_envelope.md').write_text(body,encoding='utf-8')
    (ROOT/'docs/peachtree3t_structural_freeze_report.md').write_text('# PEACHTREE-3T structural freeze report\n\nB. NEEDS_STRUCTURAL_REVISION — NOT_FROZEN.\n\nPhysical stop references remain unverified; observational heads and annotation mouths cannot uniquely survey a stop bar. CONTROL_ENVELOPE_REVISION changes measurement/association only. IDM, AgentPy dt0.1s, signals, demand and frozen directional boundaries remain unchanged. No final calibration or B1 validation permitted in this phase.\n\nSee peachtree3t_control_envelope.md for all31 requested conclusions and quantitative evidence. See outputs/peachtree3t/structural_model_freeze.json for explicit current constraints/status. Future validation: TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.\n',encoding='utf-8')

if __name__=='__main__':finish()
