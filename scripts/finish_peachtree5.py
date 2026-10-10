"""Freeze actual holdout results, including limitations, without model edits."""
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibration.holdout_validation import OUT,ROOT,TITLE,sha,verify,inputs,measured,real_data,rollout,queue_analysis,frozen_parameters,stop_episodes

CLASSIFICATION='B. BASELINE_VALIDATED_WITH_LIMITATIONS'

def trace_for(seed=6000):
    from ui.canvas_renderer import finite_json
    model,d=rollout(seed,True)
    a,q,m,h,r,p=queue_analysis(d)
    bytime={round(time,1):g for time,g in q[q.queue.gt(0)].groupby('time')}
    for frame in model.recorder.traces:
        group=bytime.get(round(frame['time'],1))
        frame['queue_heads']=[] if group is None else [dict(id=row.head_id,queue=row.queue,spatial_ft=row.spatial_ft) for row in group.itertuples()]
    return finite_json(dict(mode='VALIDATION_B1',acquisition_id='B1',data_role='VALIDATION',validation_only=True,seed=seed,
        network=model.inputs['network'],frames=model.recorder.traces,summary=model.summary,receiving_scope=model.inputs['receiving_scope'],
        control_envelopes=model.inputs['control_envelopes'],validation_name=TITLE,seed_role='ILLUSTRATIVE PREDECLARED SEED'))

def stats(d):
    rows=[]
    for key in d.select_dtypes(include='number'):
        if key=='seed':continue
        v=d[key].dropna();n=len(v);sd=v.std();half=t.ppf(.975,n-1)*sd/np.sqrt(n)
        rows.append(dict(metric=key,n=n,mean=v.mean(),SD=sd,CI95_low=v.mean()-half,CI95_high=v.mean()+half))
    return pd.DataFrame(rows)

def plots(comparison):
    folder=OUT/'figures';folder.mkdir(exist_ok=True)
    def save(name):plt.tight_layout();plt.savefig(folder/name,dpi=170);plt.close()
    for key,label,file in [('speed','Speed (ft/s)','validation_speed.png'),('headway','Front-to-front headway (ft)','validation_headway.png'),('travel','Entry-to-exit travel (s)','validation_travel.png'),('duration','Complete stop duration (s)','validation_stopping.png')]:
        plt.figure(figsize=(9,4))
        for name,x in [('REAL B1',np.load(OUT/f'REAL_B1_{key}.npy')),('SIM B1 seed6000 · illustrative predeclared',np.load(OUT/f'SIM_B1_{key}.npy'))]:
            x=np.sort(x);plt.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=name)
        plt.xlabel(label);plt.ylabel('ECDF · holdout, prior summary exposure');plt.legend();save(file)
    real=pd.read_parquet(OUT/'b1_real_target_observations.parquet');sim=pd.read_parquet(OUT/'b1_reference_simulation.parquet')
    plt.figure(figsize=(11,4))
    for name,d in [('REAL B1',real),('SIM B1 seed6000',sim)]:
        q=d.assign(tick=np.rint(d.time*10).astype(int)).groupby('tick').speed.mean();q=q.groupby(q.index//300).mean()
        plt.plot(q.index*30,q,label=name)
    plt.xlabel('Time (s)');plt.ylabel('Speed ·30s frame means (ft/s)');plt.legend();save('validation_temporal_speed.png')
    plt.figure(figsize=(11,4));bins=np.arange(0,inputs()['horizon_s']+30,30)
    for name,x in [('REAL B1',np.load(OUT/'REAL_B1_exits.npy')),('SIM B1 seed6000',np.load(OUT/'SIM_B1_exits.npy'))]:
        plt.step(bins[:-1],np.histogram(x,bins)[0],where='post',label=name)
    plt.xlabel('Time (s)');plt.ylabel('Departures /30s');plt.legend();save('validation_throughput.png')
    keys=['speed_mean_ft_s','headway_mean_ft','travel_mean_s','operational_stopped']
    fig,axes=plt.subplots(1,4,figsize=(15,4))
    for ax,key in zip(axes,keys):
        row=comparison[comparison.metric.eq(key)].iloc[0]
        ax.bar(['B2 REAL','B2 SIM','B1 REAL','B1 SIM'],[row.TRAIN_REAL_B2,row.TRAIN_SIM_B2,row.VALIDATION_REAL_B1,row.VALIDATION_SIM_B1])
        ax.tick_params(axis='x',rotation=45);ax.set_ylabel(key)
    save('validation_train_vs_test.png')

def finish():
    audit=verify();runs=pd.read_csv(OUT/'b1_simulation_runs.csv')
    seeds=json.loads((OUT/'validation_seeds.json').read_text())['seeds']
    if len(runs)!=30 or set(runs.seed)!=set(seeds):raise RuntimeError('Incomplete validation replications')
    if not runs[['conservation_verified','conservation_every_tick','no_overlap','no_negative_speed','finite_states']].all().all():raise RuntimeError('Physical invariant failed')
    summary=stats(runs);summary.to_csv(OUT/'b1_simulation_summary.csv',index=False)
    real=pd.read_csv(OUT/'b1_real_metrics.csv').iloc[0].to_dict();real.update(pd.read_csv(OUT/'b1_real_queue_diagnostics.csv').iloc[0].to_dict())
    errors=summary.copy();errors['REAL_B1']=errors.metric.map(real);errors['absolute_error']=(errors['mean']-errors.REAL_B1).abs()
    errors['signed_bias']=errors['mean']-errors.REAL_B1;errors['relative_error']=errors.absolute_error/errors.REAL_B1.replace(0,np.nan)
    errors.to_csv(OUT/'b1_validation_errors.csv',index=False)
    errors[errors.metric.str.contains('_KS|_W1_')].to_csv(OUT/'b1_distribution_metrics.csv',index=False)
    times=pd.concat([pd.read_csv(p) for p in (OUT/'replicas').glob('temporal_*.csv')]);times.to_csv(OUT/'b1_temporal_metrics.csv',index=False)
    times.groupby(['bin_s','metric'])[['RMSE','MAE','bias','correlation','bins_compared']].agg(['mean','std']).to_csv(OUT/'b1_temporal_summary.csv')
    train=pd.read_csv(ROOT/'outputs/peachtree4/pre_vs_post_calibration.csv').set_index('metric')
    comparison=summary[['metric','mean']].rename(columns={'mean':'VALIDATION_SIM_B1'})
    comparison['TRAIN_REAL_B2']=comparison.metric.map(train.REAL_B2)
    comparison['TRAIN_SIM_B2']=comparison.metric.map(train.FINAL_CALIBRATED)
    comparison['VALIDATION_REAL_B1']=comparison.metric.map(real)
    comparison=comparison[['metric','TRAIN_REAL_B2','TRAIN_SIM_B2','VALIDATION_REAL_B1','VALIDATION_SIM_B1']]
    comparison.to_csv(OUT/'train_vs_validation.csv',index=False)
    scalar=['speed_mean_ft_s','headway_mean_ft','travel_mean_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','section_travel_mean_s']
    bias=[]
    for row in comparison[comparison.metric.isin(scalar)].itertuples():
        b2=row.TRAIN_SIM_B2-row.TRAIN_REAL_B2;b1=row.VALIDATION_SIM_B1-row.VALIDATION_REAL_B1
        bias.append(dict(metric=row.metric,TRAIN_B2_bias=b2,VALIDATION_B1_bias=b1,
            classification='SYSTEMATIC MODEL BIAS' if np.sign(b1)==np.sign(b2) else 'HOLDOUT GENERALIZATION DISCREPANCY',
            interpretation='Signs only; sizes and uncertainty retained, no arbitrary validation percentage'))
    pd.DataFrame(bias).to_csv(OUT/'model_bias_analysis.csv',index=False)
    # Quantitative emergent evidence: every replica, no illustrative-seed selection.
    emerging=[];realq=pd.read_parquet(OUT/'b1_real_context_queues.parquet')
    for seed in seeds:
        q=pd.read_csv(OUT/'replicas'/f'queues_{seed}.csv');res=pd.read_csv(OUT/'replicas'/f'residual_{seed}.csv')
        emerging.append(dict(seed=seed,queue_RED_mean=q[q.phase.eq('RED')].queue.mean(),queue_GREEN_mean=q[q.phase.eq('GREEN')].queue.mean(),
            REAL_RED_queue_mean=realq[realq.phase.eq('RED')].queue.mean(),REAL_GREEN_queue_mean=realq[realq.phase.eq('GREEN')].queue.mean(),
            observed_green_cohorts=len(res),green_releases_observed=int(res.time_to_first_release_s.notna().sum()),
            stopped_clearance_mean_s=res.time_to_stopped_queue_clearance_s.mean(),
            discharge_clearance_mean_s=res.time_to_queue_clearance_s.mean(),stop_episodes=float(runs[runs.seed.eq(seed)].stop_episodes.iloc[0])))
    # Vehicle accumulation and stop-and-go are measured from AgentPy states.
    d=pd.read_parquet(OUT/'b1_reference_simulation.parquet');rd=pd.read_parquet(OUT/'b1_real_target_observations.parquet')
    for label,source in [('SIM_B1_ILLUSTRATIVE_PREDECLARED_6000',d),('REAL_B1_TARGET',rd)]:
        frame=source.groupby('frame').agg(active=('id','size'),speed=('speed','mean'))
        eps=stop_episodes(source);repeated=eps.groupby('id').size().ge(2).sum()
        emerging.append(dict(series=label,active_max=frame.active.max(),active_mean=frame.active.mean(),frame_speed_SD=frame.speed.std(),
            vehicles_with_multiple_stop_episodes=int(repeated),stop_episodes=len(eps)))
    pd.DataFrame(emerging).to_csv(OUT/'emergent_behavior_validation.csv',index=False)
    plots(comparison)
    trace=trace_for();(OUT/'b1_validation_trace.json').write_text(json.dumps(trace,allow_nan=False,default=lambda x:x.item()),encoding='utf-8')
    limitations=['Headway too high in TRAIN and holdout; long-gap tail remains inaccurate',
        'Too few stopping episodes and overly long complete stops in both acquisitions',
        'B1 speed KS is affected by real exact-zero mass versus positive near-zero IDM speeds; operational threshold not changed',
        'Temporal flow useful but bin discrepancies remain; equal total throughput is demand closure, not capacity validation',
        'REAL queue context includes non-target arterial vehicles; secondary only',
        'Restricted Through class2/3 population, omitted turning/local streams and free receiving cuts',
        'Entry speeds use frozen B2 boundary pool, not newly estimated B1 speeds',
        'Prior feasibility-summary exposure; no blind or fully-unseen claim',
        'Comparative experiments only within frozen scope and stated assumptions; no full-network or absolute-capacity claim']
    freeze=dict(status='FROZEN',validation_name=TITLE,classification=CLASSIFICATION,
        reason='Useful speed/travel/operational-stop and signal/queue patterns generalize, with relevant systematic headway and stopping-duration/episode discrepancies; no qualitative physical failure. Suitable for bounded comparative experimentation with limitations, not perfect absolute prediction.',
        structural_freeze_hash=audit['structural_freeze_sha256'],calibration_freeze_hash=audit['calibration_freeze_sha256'],
        B1_source_hash=sha(OUT/'b1_source.parquet'),raw_dataset_sha256=sha(ROOT/'data/peachtree_full.csv'),
        validation_seeds=seeds,illustrative_seed=6000,illustrative_seed_role='ILLUSTRATIVE PREDECLARED SEED',
        parameters=json.loads((ROOT/'outputs/peachtree4/final_parameters.json').read_text())['values'],delta=4,
        scope=inputs()['receiving_scope'],metric_definitions=json.loads((ROOT/'outputs/peachtree4/objective_definition.json').read_text())['definitions'],
        results=summary.to_dict('records'),limitations=limitations,no_optimizer=True,no_recalibration=True,parameters_modified=False,
        B1_use='VALIDATION AND EXOGENOUS ACQUISITION INPUTS ONLY',B1_calibration_locked=True,NO_REPLAY=True,
        signal_schedule_source='B1 OBSERVED EXOGENOUS INPUT',entry_speed_source=inputs()['entry_speed_source'],
        constructor_adapter='Private B2 constructor token for frozen TRAIN-only DemandStream guard; payload is B1 exogenous only, public model provenance restored B1 immediately. Frozen demand methods and physics unchanged.',
        queue_adapter='Exact frozen measurement code bound to B1 signals; private ID aliases only for literal Following namespace, restored on outputs. No geometry/threshold changes.',
        invariants_passed=True,completed_replicas=30,next_phase='PEACHTREE-6 SCENARIO EXPERIMENTATION',
        E1_E2_E3='READY FOR NEXT PHASE; DISABLED AND NOT IMPLEMENTED',UI_status='UI_IMPLEMENTED_NOT_BROWSER_VALIDATED',
        source_hashes=json.loads((OUT/'b1_source_hashes.json').read_text()),
        validation_code_hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'calibration/holdout_validation.py',ROOT/'scripts/run_peachtree5.py',ROOT/'scripts/finish_peachtree5.py']},
        date_time=datetime.now(timezone.utc).isoformat())
    (OUT/'validation_freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    report(freeze,comparison,errors,times,pd.DataFrame(bias))
    verify();print(CLASSIFICATION,flush=True)

def table(d):
    def val(x):return f'{x:.4f}' if isinstance(x,(float,np.floating)) and np.isfinite(x) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(val(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)])

def report(freeze,comparison,errors,times,bias):
    primary=['speed_mean_ft_s','speed_median_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_median_s','travel_W1_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','stop_duration_W1_s','throughput_total','throughput_temporal_L1_normalized','section_travel_mean_s','validation_summary_score']
    text=f'''# PEACHTREE-5 — {TITLE}

**{CLASSIFICATION}**. Next: **PEACHTREE-6 SCENARIO EXPERIMENTATION**. No recalibration or scenario execution performed. This is temporal/acquisition holdout validation with acknowledged prior aggregate feasibility exposure, not blind/fully-unseen validation.

## 1–6. Inputs, seeds and immutable parameters

{table(pd.read_csv(OUT/'b1_input_summary.csv'))}

Initial snapshot and arrivals follow the TRAIN protocol: original eligible class2/3 Through cohort, same gate-event routing/interpolation/normal-lane fallback and body attributes. Start is earliest all-four known Through signal coverage plus the inherited TRAIN0.5s margin: B1 frame515, relative51s, end1020.3s, horizon969.3s. No frame chosen by fit. Directions retain NB400→1346.452 and SB1400→597.878. Controls retain649.846/777.245/1184.777/1241.529ft; no B1 estimate. Initial speeds use the single B1 snapshot. Future entry speeds retain the frozen B2 direction-specific pool, consistent with the permitted B1 input list and frozen arrival-speed policy; no B1 speed distribution fitted. Dimensions are necessary immutable body attributes. Source keys are audit-only, never trajectory handles.

Signals: **B1 OBSERVED EXOGENOUS INPUT**, official1245–0100 Through files for11th/12th NB/SB, with frame-relative mapping. B2 schedules are not copied. All source hashes are retained; original raw frame/time affine routing isolates B1 before numeric behavior parsing. Legacy B1 cohort/gate/CF artifacts are reused with their unchanged filters, not regenerated according to errors. Initial2 + arrivals249 = modeled251; eligible original Through cohort251.

Seeds6000–6029 were frozen before validation, disjoint from all development/TRAIN final seeds. Seed6000 is **ILLUSTRATIVE PREDECLARED SEED**; conclusions use all30 runs. Parameters unchanged: {freeze['parameters']}; delta4. Release remains its exact frozen value1.599999999999966s (reported1.6s), stopped0.1m/s, FIFO, lane handling, schedules-as-exogenous and queue definitions unchanged.

The frozen DemandStream constructor rejects acquisitions other than B2. A validation-only adapter supplies a private constructor token with the B1 exogenous payload, then immediately restores public provenance B1. No TRAIN guard/loader/code is modified and no B1 values enter fitting. Parent demand, signals, integration, VehicleAgent and reduced-boundary methods remain identical. A frozen-code measurement adapter binds only B1 signal inputs, with temporary identifier aliases to honor the original literal Following namespace; IDs are restored. These compatibility adapters do not supply real positions/speeds/accelerations after initialization or real exit times to agents.

## 7–18. REAL/SIM, errors, TRAIN versus holdout

{table(comparison[comparison.metric.isin(primary)])}

{table(errors[errors.metric.isin(primary)][['metric','REAL_B1','mean','SD','CI95_low','CI95_high','absolute_error','relative_error']])}

Distributions report KS/W1; travel reports median/mean as well. Full errors remain exported. No percentage acceptance threshold. Section travel uses the same effective cuts and interpolation in both acquisitions. Headway retains the original cleaned CF/same-road/in-scope-leader methodology. Complete duration excludes left/right-censored episodes. Queue metrics use unchanged observational chains and real all-arterial context versus simulated TARGET population, so remain SECONDARY_DIAGNOSTIC, never acceptance or fitting objectives.

The B1 **VALIDATION SUMMARY SCORE** uses unchanged B2 weights, scales and normalization constants, with discrepancy numerators versus REAL B1. It is descriptive only; the B2 stopping/episode normalization and different acquisition exposure limit direct causal interpretation. No optimizer, parameter choice, weight change or model modification uses this score.

## 19. Systematic versus generalization discrepancies

{table(bias)}

The signs alone classify systematic bias; sizes and intervals are shown separately. Headway high, episodes low and complete stops long persist across acquisitions. B1 speed KS is substantially worse than TRAIN: real has an exact-zero mass whereas many simulated RED-stopped speeds remain positive near zero under IDM. Operational stopped is still exactly<=0.1m/s; no rounding or threshold change conceals that distribution discrepancy. This is a material limitation, not a physical collision or signal failure.

## 20–24. Temporal/emergent behavior, replicas, intervals and tests

All30 runs quantify accumulation, queue formation under RED, observed GREEN releases and clearances, collective speed variation, stop episodes and throughput. emergent_behavior_validation.csv contains every-seed queue-state evidence plus illustrative/source accumulation and repeated-stop counts. Graphs alone are not evidence. Temporal files contain10/30/60s RMSE/MAE/bias/correlation for speed, operational stopped, active vehicles and throughput; undefined correlations/empty speed bins remain missing. Equal251 throughput means demand closure, not capacity validation. The illustrative trace repeats predeclared seed6000 and is not another selection or independent replica.

Mean/SD/95%t CI across30 simulation seeds are in b1_simulation_summary.csv. CI quantifies simulation variability, not uncertainty of REAL. The189 prior tests are preserved. Historical mixed-source feasibility fixtures remain skipped when incompatible with the frozen validation protocol; TRAIN B1 fitting guards remain locked. New validation tests verify integrity, immutable parameters, no optimizer API, acquisition adapters/no replay, scope/metrics/seeds and physical invariants. Exact QA totals are in test_report.json.

## 25–29. Integrity, decision, limitations and next phase

Structural and calibration freeze files are byte-identical, verified before opening B1 and after execution. Parameters modified: **NO**. All prior output artifacts remain intact. Existing simulation and calibration files are unchanged; only new validation code and authorized UI updates are added. UI exposes VALIDACIÓN results with TRAIN B2 versus VALIDATION B1 and READ ONLY parameters; E1/E2/E3 are READY FOR NEXT PHASE but remain disabled/not implemented. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED.

**{CLASSIFICATION}**: speed/travel magnitudes, operational stopping and signal/queue patterns provide useful within-scope compatibility, with significant distribution, headway and stopping episode/duration limitations. Conservation and no-overlap/negative-speed/finite-state checks pass in all30 runs. No qualitative physical failure is observed. This supports comparative experimentation under the frozen scope/assumptions, not full-network or absolute-capacity prediction.

Limitations:
'''+''.join('- '+x+'\n' for x in freeze['limitations'])+'''
NEXT = **PEACHTREE-6 SCENARIO EXPERIMENTATION**. Stop without recalibrating, changing structure/parameters or implementing E1/E2/E3 in this phase. B1 results are accepted as obtained.
'''
    (ROOT/'docs/peachtree5_validation_report.md').write_text(text,encoding='utf-8')

if __name__=='__main__':finish()
