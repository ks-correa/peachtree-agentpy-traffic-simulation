"""Freeze predeclared effective controls after physical invariants, not SIM fit."""
import json,hashlib
import numpy as np
import pandas as pd
from scipy.stats import t
from calibration.final_structure import final_inputs,run_final,references,REFERENCE_SOURCE
from scripts.run_peachtree3u import OUT
from scripts.run_peachtree3t import digest,analyze,envelopes
from scripts.finish_peachtree3t import table
from simulation.training_data import ROOT
from ui.canvas_renderer import finite_json

CLASSIFICATION='A. STRUCTURE_FROZEN_READY_FOR_FINAL_CALIBRATION'

def trace_for(seed):
    model,d=run_final(seed,True)
    from calibration.receiving_scope import inside
    a,q,m,h,r,p=analyze(d[inside(d)],envelopes())
    bytime={round(time,1):g for time,g in q[q.queue.gt(0)].groupby('time')}
    for frame in model.recorder.traces:
        heads=bytime.get(round(frame['time'],1))
        frame['queue_heads']=[] if heads is None else [dict(id=row.head_id,queue=row.queue,spatial_ft=row.spatial_ft) for row in heads.itertuples()]
    return finite_json(dict(mode='FINAL_STRUCTURE',training_acquisition='B2',seed=seed,network=model.inputs['network'],
        frames=model.recorder.traces,summary=model.summary,receiving_scope=model.inputs['receiving_scope'],control_envelopes=model.inputs['control_envelopes']))

def components(data,params):
    return pd.DataFrame([
        ('dt',.1,'DATASET_DERIVED','NGSIM10Hz; existing dt'),
        ('effective control references',dict((f'{i}/{di}',ref) for (i,di),ref in references().items()),'DATASET_DERIVED','3T entry artifact; predeclared before3U SIM'),
        ('signal schedules','Existing B2 RED/YELLOW/GREEN clock; no offsets/splits changes','DATASET_DERIVED','B2 exogenous signal inputs; official afternoon files'),
        ('coordinate semantics','front=Local_Y; longitudinal center/rear projections','DATASET_DERIVED','Official metadata printed p13;3T'),
        ('reduced scope','NB400→1346.452; SB1400→597.878 ft','DATASET_DERIVED','3S frozen directional scope using B2 geometry/body clearance'),
        ('initial snapshot/arrival requests','Existing B2 Through class2/3 cohort','DATASET_DERIVED','B2 exogenous inputs'),
        ('entry speed samples','Existing B2 distributions with paired seeds','DATASET_DERIVED','B2 exogenous inputs'),
        ('IDM v0/T/s0/a/b',params['parameters'],'CALIBRATED','CALIBRATED_B2; original baseline full precision unchanged'),
        ('IDM delta',4.,'LITERATURE_DERIVED','Existing IDM exponent convention'),
        ('IDM acceleration/ballistic integration','Existing gap/speed law; simultaneous feasible acceleration constraint','LITERATURE_DERIVED','Existing VehicleAgent/IDM ballistic implementation'),
        ('numerical feasibility guard','Constrain acceleration to available displacement; no position or speed reset','ASSUMPTION','Existing implementation safety rule'),
        ('yellow handling','Latched comfortable-stop decision','ASSUMPTION','Existing yellow rule; no changes'),
        ('green release delay',1.6,'DATASET_DERIVED','B2 pooled simplification; no stratification'),
        ('FIFO safe insertion','Preserve per direction/lane pending order and braking gap','ASSUMPTION','Existing3R correction'),
        ('followers','IDM only; no added propagation delay','ASSUMPTION','Frozen model choice'),
        ('main lanes/bay connector','Two normal lanes; only necessary safe lane11 merge','ASSUMPTION','Existing logical lane handling; sparse B2 lane-change sample'),
        ('stopped',.1,'ASSUMPTION','Frozen external operational threshold in m/s'),
        ('standstill queue gap',params['queue_gap_m'],'DATASET_DERIVED','Existing B2 stoodP90'),
        ('head selection window',100.,'ASSUMPTION','Inherited100ft window; observed-entry measurement'),
        ('queue chain','First same-lane stopped head, Following where available, positive frozen-gap chain','ASSUMPTION','3T reproducible measurement; observational lane0 recovery'),
        ('observational stop zones','Preserved3T lane/cycle P10–P90 bands; no physical force','DATASET_DERIVED','3T head distributions'),
        ('receiving condition','Free removal at frozen direction-specific cuts','ASSUMPTION','3S reduced boundary implementation'),
        ('target-only population','Through class2/3; no Background Agents','ASSUMPTION','Frozen cohort modelling scope'),
        ('future green split','NOT_IMPLEMENTED; E1/E2/E3 disabled','EXPERIMENTAL','Future scenario only, outside phase')
    ],columns=['component','value/rule','classification','source'])

def finish():
    data=final_inputs();params=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
    runs=pd.read_csv(OUT/'final_structure_30_replica_runs.csv')
    residual=pd.concat([pd.read_csv(p) for p in sorted((OUT/'replicas').glob('residual_*.csv'))])
    extra=residual.groupby('seed').agg(queue_at_green_onset_mean=('queue_at_green_onset','mean'),
        stopped_queue_clearance_mean_s=('time_to_stopped_queue_clearance_s','mean'))
    for metric in extra:runs[metric]=runs.seed.map(extra[metric])
    direct=pd.read_csv(OUT/'direct_control_checks.csv')
    assert len(runs)==30 and set(runs.seed)==set(range(3000,3030))
    if not runs[['conservation_verified','conservation_every_tick','no_overlap']].all().all():raise RuntimeError('Concrete implementation invariant failed')
    if not direct[['red_no_cross','stopped_before_reference','green_release','correct_sign','no_overlap','conservation']].all().all():raise RuntimeError('Direct physical control bug')
    if runs.remaining.ne(0).any() or runs.pending.ne(0).any():raise RuntimeError('Unclosed cohort: investigate concrete implementation')
    rows=[]
    for metric in runs.select_dtypes(include='number').columns:
        if metric=='seed':continue
        v=runs[metric];sd=v.std();half=t.ppf(.975,29)*sd/np.sqrt(30)
        rows.append(dict(metric=metric,n=30,mean=v.mean(),SD=sd,CI95_low=v.mean()-half,CI95_high=v.mean()+half))
    stats=pd.DataFrame(rows);stats.to_csv(OUT/'final_structure_30_replica_summary.csv',index=False)
    new=pd.read_csv(ROOT/'outputs/peachtree3t/paired_30_replica_comparison.csv');new=new[new['mode'].eq('NEW_REDUCED_SCOPE')]
    metrics=[r['metric'] for r in rows if r['metric'] in new.columns]
    paired=runs.set_index('seed')[metrics]-new.set_index('seed')[metrics]
    paired.reset_index().to_csv(OUT/'paired_final_minus_new.csv',index=False)
    real=pd.read_csv(ROOT/'outputs/peachtree3s/real_same_scope_metrics.csv').iloc[0].to_dict()
    real.update(pd.read_csv(ROOT/'outputs/peachtree3t/real_vs_sim_queue_dynamics.csv').iloc[0].to_dict())
    real['section_travel_mean_s']=pd.read_csv(ROOT/'outputs/b2_observed_section_times.csv').travel_time_s.mean()
    real_residual=pd.read_csv(ROOT/'outputs/peachtree3t/residual_queue_after_green.csv')
    real_residual=real_residual[real_residual.series.eq('REAL_B2')]
    real['queue_at_green_onset_mean']=real_residual.queue_at_green_onset.mean()
    real['stopped_queue_clearance_mean_s']=real_residual.time_to_stopped_queue_clearance_s.mean()
    old_residual=pd.read_csv(ROOT/'outputs/peachtree3t/residual_queue_after_green.csv')
    old_extra=old_residual[old_residual.series.eq('NEW_REDUCED_SCOPE')].groupby('seed').agg(
        queue_at_green_onset_mean=('queue_at_green_onset','mean'),stopped_queue_clearance_mean_s=('time_to_stopped_queue_clearance_s','mean'))
    for metric in old_extra:new[metric]=new.seed.map(old_extra[metric])
    compare=stats.copy();compare['REAL_B2']=compare.metric.map(real)
    compare['NEW_REDUCED_SCOPE']=compare.metric.map(new.mean(numeric_only=True))
    compare['FINAL_STRUCTURE']=compare['mean']
    compare.to_csv(OUT/'real_vs_final_structure.csv',index=False)
    h=pd.concat([pd.read_csv(p) for p in sorted((OUT/'replicas').glob('heads_*.csv'))])
    per_seed=h.groupby(['intersection','direction','lane','seed']).position_y.median().reset_index()
    hs=per_seed.groupby(['intersection','direction','lane']).position_y.agg(final_head_median_mean='mean',final_head_median_SD='std',n_seeds='count').reset_index()
    original=pd.read_csv(ROOT/'outputs/peachtree3t/real_vs_sim_head_positions.csv')
    hs=original.merge(hs,on=['intersection','direction','lane']);hs['FINAL_minus_REAL_ft']=hs.final_head_median_mean-hs.real_median
    hs.to_csv(OUT/'queue_head_comparison.csv',index=False)
    for name in ['residual','propagation']:
        pd.concat([pd.read_csv(p) for p in sorted((OUT/'replicas').glob(f'{name}_*.csv'))]).to_csv(OUT/f'final_{name}.csv',index=False)
    comp=components(data,params);comp.to_csv(OUT/'component_classification.csv',index=False)
    structural_paths=list((ROOT/'simulation').glob('*.py'))+[ROOT/'calibration/final_structure.py',ROOT/'calibration/receiving_scope.py',ROOT/'calibration/structural.py',ROOT/'calibration/control_envelope.py']
    source_paths=[REFERENCE_SOURCE,ROOT/'outputs/peachtree3s/decision.json',ROOT/'outputs/peachtree3t/stop_zone_candidates.csv',ROOT/'data/b2_exogenous_inputs.json',ROOT/'outputs/peachtree3r/revised_inputs.json',ROOT/'outputs/b2_calibrated_parameters.json',ROOT/'data/b2_baseline_source.parquet',ROOT/'data/reference/Peachtree_metadata_text.txt']
    before=json.loads((OUT/'pre_revision_hashes.json').read_text());changed=[k for k,v in before.items() if digest(ROOT/k)!=v]
    unexpected=[k for k in changed if not k.startswith('ui\\')]
    if unexpected:raise RuntimeError('Previous artifacts changed: '+str(unexpected))
    freeze=dict(phase='PEACHTREE-3U',mode='FINAL_STRUCTURE',status='FROZEN',classification=CLASSIFICATION,
        reason='Predeclared empirical annotation-entry controls; all physical invariants passed. Statistical differences become PARAMETRIC / MODEL DISCREPANCY, not a reason for another structural phase.',
        scope={'intersections':[2,3],'link':'11th–12th only'},boundaries=data['receiving_scope'],
        signal_control_references={f'{i}/{di}':ref for (i,di),ref in references().items()},
        reference_type='EFFECTIVE_SIGNAL_CONTROL_REFERENCE',reference_interpretation='INTERSECTION_ENTRY_REFERENCE; empirical adjacent-section to intersection annotation boundary; not a painted or surveyed stop bar',
        legacy_signal_proxies={f'{r["intersection"]}/{r["direction"]}':r['legacy_signal_proxy_ft'] for r in data['network']['stop_lines']},
        signal_schedules=data['signals'],dt_s=.1,coordinate_semantics='Local_Y front center; no length added; center/rear longitudinal projections by direction',
        arrival_policy='Existing exogenous B2 arrival requests and entry speed sampling; one initial snapshot',FIFO='Existing corrected per-direction/lane safe insertion; no changes',
        release_rule={'pooled_delay_s':1.6,'classification':'DATASET_DERIVED_SIMPLIFICATION','implementation':'Existing head hold1.5s plus0.1s observable onset; acceleration constraint, no reset'},
        VehicleAgent_states=['ENTERING','FREE_FLOW','FOLLOWING','STOPPED_SIGNAL','LANE_CHANGING','EXITED'],
        VehicleAgent_rules='Existing IDM, actual/virtual leaders, simultaneous feasibility and ballistic integration; no clipping, position/speed reset or trajectory replay',
        lane_handling='Existing two normal lanes; safe necessary lane11 merge only; no discretionary changes',
        queue_definition='3T first stopped same-lane/direction front chain; Following where available; frozen standstill gap; observable head window100ft from entry',
        queue_gap_m=params['queue_gap_m'],stopped_definition='Operational speed<=0.1m/s; exact zero separately',
        controlled_envelopes=data['control_envelopes'],stop_zones='Observational only; no force or speed rule',
        agent_population='TARGET Through Vehicle_Class2/3; no Background Agents',
        excluded_mechanisms=['New propagation delay','Background Agents','10th/13th/14th extension','New geometry audit','Painted stop-bar search','Trajectory replay','E1/E2/E3'],
        pre_calibration_IDM=params['parameters'],IDM_recalibrated=False,remaining_discrepancy='PARAMETRIC / MODEL DISCREPANCY',
        invariant_results={'direct_groups_passed':8,'paired_replicas_passed':30,'conservation_every_tick':True,'no_overlap':True,'red_no_cross_direct_tests':True,'wrong_direction_signal':False},
        allowed_structure_reopening=['Reproducible collision','Conservation loss','Signal applied to wrong direction','Unit error','Verifiable implementation bug'],
        statistical_discrepancy_authorizes_structure_reopening=False,next_phase='PEACHTREE-4 FINAL B2 CALIBRATION',
        B1_LOCKED=True,E1_E2_E3='DISABLED',UI_status='UI_IMPLEMENTED_NOT_BROWSER_VALIDATED',
        future_validation='TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE',
        structural_input_signature=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        structural_code_hashes={str(p.relative_to(ROOT)):digest(p) for p in structural_paths},
        source_hashes={str(p.relative_to(ROOT)):digest(p) for p in source_paths},
        analysis_and_UI_code_hashes={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'scripts/run_peachtree3u.py',ROOT/'scripts/finish_peachtree3u.py',ROOT/'calibration/control_envelope.py',ROOT/'ui/canvas_renderer.py',ROOT/'ui/streamlit_app.py']})
    (OUT/'structural_model_freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    (OUT/'preservation_check.json').write_text(json.dumps({'previous_artifacts_unchanged':True,'intentional_UI_changes':changed,'unexpected_changes':unexpected},indent=2),encoding='utf-8')
    trace=trace_for(210);(OUT/'final_structure_trace.json').write_text(json.dumps(trace,allow_nan=False,default=lambda x:x.item()),encoding='utf-8')
    report(compare,hs,freeze,comp)
    print(CLASSIFICATION,flush=True)

def report(compare,heads,freeze,comp):
    refs=pd.read_csv(OUT/'effective_control_references.csv')
    cols=['metric','REAL_B2','NEW_REDUCED_SCOPE','FINAL_STRUCTURE','SD','CI95_low','CI95_high']
    wanted=['speed_mean_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_W1_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','stop_duration_W1_s','queue_mean','queue_P90','queue_max','queue_spatial_mean_ft','queue_spatial_P90_ft','queue_at_green_onset_mean','stopped_queue_clearance_mean_s','release_mean_s','clearance_mean_s','residual_5s_mean','residual_10s_mean','propagation_mean_s','throughput_total','throughput_temporal_L1_normalized','section_travel_mean_s']
    text=f'''# PEACHTREE-3U — FINAL STRUCTURAL REVISION AND FREEZE

**{CLASSIFICATION}**. Status **FROZEN**. Next phase: **PEACHTREE-4 FINAL B2 CALIBRATION**. No calibration performed here.

The methodological choice was explicitly predeclared by the user: use the existing3T INTERSECTION_ENTRY_REFERENCE as EFFECTIVE_SIGNAL_CONTROL_REFERENCE. This is the observable annotation boundary from adjacent approach section to intersection envelope. It is not a painted stop bar, physical stop bar or surveyed stop line. No coordinate was recomputed, optimized, chosen from queue-head output or subsequently shifted to improve fit. The original3T CSV is byte-hash pinned in code; references are an immutable mapping.

## 1–2. Effective references and legacy differences

{table(refs)}

Legacy proxies remain in all historical modes and in FINAL input provenance. The effective coordinates relocate the virtual signal leader; schedules, offsets, cycle/splits/yellow, units and integration are unchanged. Existing IDM and acceleration feasibility constraints govern braking. There is no zone-stop rule, speed reset or position clipping.

## 3. First queue heads REAL / SIM, by intersection/direction/lane

{table(heads)}

REAL uses the existing3T cycle-head observations; FINAL uses the median head position within each seed, then mean/SD across30 paired seeds. The preserved NEW head comparison is also included. Different lane-cycle counts and sparse outliers remain visible. These are diagnostics; references will not be moved to reduce these errors. Front=Local_Y. STOP_ZONE is preserved observational P10–P90 only. Association of Y1174–1192 NB with own12th extends through its envelope to1246.452, including positions after the effective entry; association does not imply a downstream force after crossing.

## 4–9. Paired metrics

{table(compare[compare.metric.isin(wanted)][cols])}

Seeds3000–3029 are fixed, no selection. FINAL is30 fresh AgentPy rollouts. NEW baseline measurements are the preserved same-seed3S/3T results. REAL general speed/headway/travel/stopping use the frozen Through target cohort. REAL physical queue diagnostic uses all observed arterial class2/3 context; target-only sensitivity remains in3T. Queue means/P90/spatial extent use occupied-lane approach snapshots, not full-clock demand-normalized means; source coverage and omitted agents limit magnitude comparisons. Queue max is per lane. Complete stopped duration excludes censored episodes. Residual counts at5/10s preserve missing observations as missing, not zero. Queue discharge clearance is last initial RED-cohort member beyond empirical junction exit, whereas stopped clearance is first simultaneous all-moving snapshot. Separate residual/propagation files preserve both definitions and censoring. Aggregated30-seed CI is uncertainty of simulation mean, not uncertainty of REAL or methodological validity.

Section travel time uses crossings of approved control reference cuts: FINAL now uses effective cuts; NEW retains legacy cuts. Consequently part of the section-time difference is measurement-boundary change; it is not interpreted solely as traffic improvement. Throughput temporal discrepancy uses the same30s bins.274 exiting vehicles represent the observed cohort, not road capacity. Changes may improve or worsen individual metrics; the freeze criterion is not statistical perfection.

## 10–11. Physical invariants

All8 direct control tests passed: RED virtual restriction, first-head stop before reference, no numerical red crossing, GREEN release, correct NB increasing/SB decreasing coordinates, conservation, no overlap. All30 full-cohort runs pass conservation at every tick and no overlap; zero pending/remaining agents at end. A direction-specific RED NB/GREEN SB test additionally checks signal application. Existing physical guards still run every tick. No collision or conservation loss is concealed by statistical summaries.

## 12–15. QA, holdout, freeze and decision

The TRAIN runner retains all151 prior cases, adds FINAL-specific tests and writes outputs/peachtree3u/test_report.json. Actual-source historical fixtures remain skipped before setUpClass. Exact final totals are in that report. UI adds FINAL_STRUCTURE and Show effective control references, while retaining envelope/head toggles and all old modes. UI is a consumer of simulated AgentPy states. TEST B1 LOCKED; E1/E2/E3 disabled. **UI_IMPLEMENTED_NOT_BROWSER_VALIDATED**; AppTest/Canvas tests do not establish browser visual validation.

All previous phase outputs, reports and docs remain byte-identical. Only current UI code changes are intentional; preservation manifest/check is in3U. B1 was not accessed. Future validation retains the name TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE.

`structural_model_freeze.json`: **FROZEN**. It records scope, boundaries, controls/schedules, dt, front semantics, arrivals/FIFO, release, states/rules, lane handling, queues/stopped/population, excluded mechanisms and source/code hashes. Runtime checks reject changed structural code or input signature. The five baseline IDM values remain at their original full precision; release remains1.6s and followers IDM only. No new delay or agents.

Remaining differences are **PARAMETRIC / MODEL DISCREPANCY** under this final modelling convention. Statistical mismatch does not authorize another structural review. Reopening requires a reproducible collision, conservation loss, wrong-direction signal, unit error or implementation bug. No PEACHTREE-3V, new geometric audit or painted-bar search is proposed. Stop here; next work is PEACHTREE-4 FINAL B2 CALIBRATION.

## Component provenance

{table(comp)}
'''
    (ROOT/'docs/peachtree3u_final_structure.md').write_text(text,encoding='utf-8')

if __name__=='__main__':finish()
