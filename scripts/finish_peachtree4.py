"""One selected parameter set, all TRAIN tradeoffs, immutable calibration freeze."""
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.stats import t,spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibration.final_calibration import OUT,ROOT,NAMES,DOMAINS,targets,rollout,measured,metrics,errors,final_parameters,verify_structure,plan,sha
from scripts.run_peachtree3t import analyze,envelopes
from scripts.finish_peachtree3t import table
from ui.canvas_renderer import finite_json

CLASSIFICATION='A. CALIBRATION_FROZEN_READY_FOR_B1_VALIDATION'

def trace_for(seed):
    model,d=rollout(dict(final_parameters()),seed,True)
    pred=measured(model,d);a,q,m,h,r,p=analyze(pred['data'],envelopes())
    bytime={round(t,1):g for t,g in q[q.queue.gt(0)].groupby('time')}
    for frame in model.recorder.traces:
        group=bytime.get(round(frame['time'],1))
        frame['queue_heads']=[] if group is None else [dict(id=row.head_id,queue=row.queue,spatial_ft=row.spatial_ft) for row in group.itertuples()]
    return finite_json(dict(mode='FINAL_CALIBRATED_B2',training_acquisition='B2',seed=seed,network=model.inputs['network'],
        frames=model.recorder.traces,summary=model.summary,receiving_scope=model.inputs['receiving_scope'],control_envelopes=model.inputs['control_envelopes']))

def statistics(d):
    rows=[]
    for col in d.select_dtypes(include='number').columns:
        if col=='seed':continue
        v=d[col].dropna();n=len(v);sd=v.std();half=t.ppf(.975,n-1)*sd/np.sqrt(n) if n>1 else np.nan
        rows.append(dict(metric=col,n=n,mean=v.mean(),SD=sd,CI95_low=v.mean()-half,CI95_high=v.mean()+half))
    return pd.DataFrame(rows)

def sensitivity():
    # Space-filling LHS only avoids correlations dominated by the local cluster.
    d=pd.read_csv(OUT/'calibration_candidates.csv');d=d[d.stage.eq('LHS')&d.status.eq('VALID')]
    rows=[]
    for param in NAMES:
        correlations=[]
        for domain in [*['E_'+x for x in DOMAINS],'objective']:
            result=spearmanr(d[param],d[domain]);correlations.append(abs(result.statistic))
            rows.append(dict(parameter=param,error_domain=domain,Spearman_rho=result.statistic,p_value=result.pvalue,n=len(d)))
        strength=max(correlations)
        label='WELL_INFORMED' if strength>=.6 else 'MODERATELY_INFORMED' if strength>=.3 else 'WEAKLY_INFORMED'
        for row in rows:
            if row['parameter']==param:row['classification']=label
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'parameter_sensitivity.csv',index=False)
    return frame

def plots(pre,post):
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True);real=targets()
    def save(name):plt.tight_layout();plt.savefig(figdir/name,dpi=170);plt.close()
    candidates=pd.read_csv(OUT/'calibration_candidates.csv');candidates=candidates[candidates.status.eq('VALID')]
    fig,axes=plt.subplots(1,5,figsize=(15,3.5))
    for ax,key in zip(axes,NAMES):
        ax.scatter(candidates[key],candidates.objective,c=np.where(candidates.stage.eq('LHS'),0,1),s=14,alpha=.6)
        ax.set(xlabel=key,ylabel='Mean5-seed objective')
    save('parameter_profiles.png')
    for key,label,name in [('speed','Speed (ft/s)','speed_real_vs_sim.png'),('headway','Front-to-front headway (ft)','headway_real_vs_sim.png'),('travel','Entry-to-exit travel (s)','travel_real_vs_sim.png')]:
        plt.figure(figsize=(9,4))
        for series,x in [('REAL B2',real[key]),('PRE seed4000',np.load(OUT/f'FINAL_STRUCTURE_PRECALIBRATION_{key}.npy')),('FINAL seed4000',np.load(OUT/f'FINAL_CALIBRATED_B2_{key}.npy'))]:
            x=np.sort(x);plt.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=series)
        plt.xlabel(label);plt.ylabel('ECDF · reference seed predeclared, TRAIN only');plt.legend();save(name)
    fig,axes=plt.subplots(2,2,figsize=(11,7))
    for ax,metric,label,truth in zip(axes.flat,['operational_stopped','vehicles_stopped_fraction','stop_episodes'],
            ['Operational stopped fraction','Fraction vehicles stopped','Stop episodes'],[real['stopped'],real['vehicles_stopped'],real['episodes']]):
        ax.bar(['REAL','PRE30','FINAL30'],[truth,pre[metric].mean(),post[metric].mean()],color=['#2a9d8f','#7a86c2','#e9a23b'])
        ax.set_ylabel(label)
    ax=axes[1,1]
    for series,x in [('REAL B2',real['duration']),('PRE seed4000',np.load(OUT/'FINAL_STRUCTURE_PRECALIBRATION_duration.npy')),('FINAL seed4000',np.load(OUT/'FINAL_CALIBRATED_B2_duration.npy'))]:
        x=np.sort(x);ax.step(x,np.arange(1,len(x)+1)/len(x),where='post',label=series)
    ax.set(xlabel='Complete stopped duration (s)',ylabel='ECDF');ax.legend(fontsize=8);save('stopping_real_vs_sim.png')
    r=real['data'];a=pd.read_parquet(OUT/'FINAL_STRUCTURE_PRECALIBRATION_reference_observations.parquet');b=pd.read_parquet(OUT/'FINAL_CALIBRATED_B2_reference_observations.parquet')
    plt.figure(figsize=(11,4))
    for name,d in [('REAL B2',r),('PRE seed4000',a),('FINAL seed4000',b)]:
        frame=d.assign(tick=np.rint(d.time*10).astype(int)).groupby('tick').speed.mean()
        group=frame.groupby(frame.index//300).mean();plt.plot(group.index*30,group,label=name)
    plt.xlabel('Time (s) ·30s averages');plt.ylabel('Mean speed (ft/s)');plt.legend();save('temporal_speed.png')
    plt.figure(figsize=(11,4));edges=np.arange(0,real['horizon']+30,30)
    for name,ex in [('REAL B2',real['exits']),('PRE seed4000',np.load(OUT/'FINAL_STRUCTURE_PRECALIBRATION_exits.npy')),('FINAL seed4000',np.load(OUT/'FINAL_CALIBRATED_B2_exits.npy'))]:
        plt.step(edges[:-1],np.histogram(ex,edges)[0],where='post',label=name)
    plt.xlabel('Time (s)');plt.ylabel('Departures /30s');plt.legend();save('temporal_throughput.png')

def finish():
    p=plan();selected=json.loads((OUT/'final_parameters.json').read_text());paramhash=sha(OUT/'final_parameters.json')
    if paramhash!=json.loads((OUT/'selection_lock.json').read_text())['final_parameters_sha256']:raise RuntimeError('Selection changed')
    pre=pd.read_csv(OUT/'precalibration_30_replica_runs.csv');post=pd.read_csv(OUT/'final_30_replica_runs.csv')
    for d in [pre,post]:
        if len(d)!=30 or set(d.seed)!=set(p['final_seeds']):raise RuntimeError('Final replication seeds/count changed')
        if not d[['conservation_verified','no_overlap','no_negative_speed','valid_signals','finite_state','boundaries_valid']].all().all():raise RuntimeError('Physical invariant failed')
    poststats=statistics(post);poststats.to_csv(OUT/'final_30_replica_summary.csv',index=False)
    prestats=statistics(pre);prestats.to_csv(OUT/'precalibration_30_replica_summary.csv',index=False)
    real=targets();realmetrics=metrics(real);realmetrics.update(errors(realmetrics))
    # Queue context is intentionally secondary, not hidden inside primary score.
    rq=pd.read_csv(ROOT/'outputs/peachtree3t/real_vs_sim_queue_dynamics.csv').iloc[0].to_dict();realmetrics.update({k:v for k,v in rq.items() if k not in ['mode','seed']})
    rr=pd.read_csv(ROOT/'outputs/peachtree3t/residual_queue_after_green.csv');rr=rr[rr.series.eq('REAL_B2')]
    realmetrics.update(queue_at_green_onset_mean=rr.queue_at_green_onset.mean(),stopped_queue_clearance_mean_s=rr.time_to_stopped_queue_clearance_s.mean())
    # metrics(real) reports self-distance0 for KS/W1; primary REAL scalars agree.
    compare=poststats.rename(columns={'mean':'FINAL_CALIBRATED'});compare['REAL_B2']=compare.metric.map(realmetrics)
    compare['PRECALIBRATION']=compare.metric.map(prestats.set_index('metric')['mean'])
    compare['absolute_change']=compare.FINAL_CALIBRATED-compare.PRECALIBRATION
    compare['relative_change']=compare.absolute_change/compare.PRECALIBRATION.replace(0,np.nan)
    interpretations=[]
    for row in compare.itertuples():
        if row.metric.startswith(('E_','component_')) or row.metric in ['objective'] or '_KS' in row.metric or '_W1_' in row.metric or row.metric.startswith(('cumulative_departure','throughput_temporal')):
            interpretations.append('LOWER_ERROR' if row.absolute_change<0 else 'HIGHER_ERROR' if row.absolute_change>0 else 'UNCHANGED')
        elif not np.isfinite(row.REAL_B2):interpretations.append('DIAGNOSTIC_ONLY')
        elif row.metric.startswith(('queue','clearance','residual','release','propagation','stopped_queue')):interpretations.append('SECONDARY_DIAGNOSTIC_POPULATION_LIMIT')
        else:interpretations.append('CLOSER_TO_REAL' if abs(row.FINAL_CALIBRATED-row.REAL_B2)<abs(row.PRECALIBRATION-row.REAL_B2) else 'FARTHER_FROM_REAL' if row.absolute_change!=0 else 'UNCHANGED')
    compare['interpretation']=interpretations;compare.to_csv(OUT/'pre_vs_post_calibration.csv',index=False)
    temporal=pd.concat([pd.read_csv(x) for x in (OUT/'replicas').glob('*_temporal_*.csv')],ignore_index=True)
    temporal.to_csv(OUT/'temporal_comparison.csv',index=False)
    temporal.groupby(['series','bin_s','metric'])[['RMSE','MAE','bias','correlation','bins_compared']].agg(['mean','std']).to_csv(OUT/'temporal_summary.csv')
    candidates=pd.read_csv(OUT/'calibration_candidates.csv');sens=sensitivity()
    bounds=pd.read_csv(OUT/'parameter_bounds.csv');audit=[]
    for row in bounds.itertuples():
        value=selected['values'][row.parameter];fraction=(value-row.lower)/(row.upper-row.lower)
        audit.append(dict(parameter=row.parameter,value=value,lower=row.lower,upper=row.upper,unit_bound_position=fraction,
            BOUNDARY_HIT='LOWER' if fraction<=.001 else 'UPPER' if fraction>=.999 else 'NO',rule='within0.1% of frozen interval; no expansion'))
    audit=pd.DataFrame(audit);audit.to_csv(OUT/'parameter_boundary_audit.csv',index=False)
    trace=trace_for(4000);(OUT/'final_calibrated_trace.json').write_text(json.dumps(trace,allow_nan=False,default=lambda x:x.item()),encoding='utf-8')
    plots(pre,post)
    # Verify every previous phase artifact after selection/evaluation and UI edits.
    prior=json.loads((OUT/'pre_calibration_hashes.json').read_text());changed=[path for path,expected in prior.items() if sha(ROOT/path)!=expected]
    if changed:raise RuntimeError('Prior phase artifact changed: '+str(changed))
    freezehash=verify_structure()
    source_paths=[ROOT/'outputs/peachtree3u/structural_model_freeze.json',ROOT/'outputs/b2_parameter_estimates.csv',ROOT/'outputs/b2_calibrated_parameters.json',ROOT/'data/b2_all_observed.parquet',ROOT/'data/b2_baseline_source.parquet',ROOT/'outputs/working/peachtree_cf_preparation_B2.parquet']
    code_paths=[ROOT/'calibration/final_calibration.py',ROOT/'scripts/run_peachtree4.py',ROOT/'scripts/evaluate_peachtree4.py',ROOT/'scripts/finish_peachtree4.py',ROOT/'tests/test_final_calibration.py',ROOT/'ui/streamlit_app.py',ROOT/'ui/canvas_renderer.py']
    freeze=dict(status='FROZEN',classification=CLASSIFICATION,reason='Finite two-stage optimizer completed; minimum equal-domain5-seed parameter set frozen;30 final TRAIN runs passed invariants; structure untouched; no B1 used.',
        structural_freeze_sha256=freezehash,final_parameters_sha256=paramhash,final_parameter_values=selected['values'],delta=4,
        parameter_bounds=selected['bounds'],objective_definition=json.loads((OUT/'objective_definition.json').read_text()),
        development_seeds=p['development_seeds'],final_replication_seeds=p['final_seeds'],optimizer_termination=selected['local_termination'],
        selection_objective=selected['objective'],selected_candidate=selected['selected_candidate'],evaluated_parameter_sets=len(candidates),
        final_replications=30,invariants_passed=True,B1_LOCKED=True,E1_E2_E3='DISABLED',structure_intact=True,
        future_validation_name='TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE',
        next_phase='PEACHTREE-5 VALIDATION B1',B1_opened_in_this_phase=False,parameters_may_change_during_B1=False,
        source_hashes={str(x.relative_to(ROOT)):sha(x) for x in source_paths},code_hashes={str(x.relative_to(ROOT)):sha(x) for x in code_paths},
        frozen_artifact_hashes=p['frozen_artifact_hashes'],date_time=datetime.now(timezone.utc).isoformat(),
        UI_status='UI_IMPLEMENTED_NOT_BROWSER_VALIDATED')
    (OUT/'calibration_freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    (OUT/'preservation_check.json').write_text(json.dumps({'all_prior_phase_artifacts_unchanged':True,'structural_freeze_intact':True,'changes':changed},indent=2))
    report(selected,bounds,audit,sens,compare,pre,post)
    print(CLASSIFICATION,flush=True)

def report(selected,bounds,audit,sens,compare,pre,post):
    start=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['parameters']
    values=pd.DataFrame([dict(parameter=k,PRE=start[k],FINAL=selected['values'][k]) for k in NAMES])
    primary=['speed_mean_ft_s','speed_KS','speed_W1_ft_s','headway_mean_ft','headway_KS','headway_W1_ft','travel_mean_s','travel_W1_s','operational_stopped','vehicles_stopped_fraction','stop_episodes','complete_stop_duration_mean_s','stop_duration_W1_s','throughput_total','throughput_temporal_L1_normalized','cumulative_departure_mean_abs_normalized','section_travel_mean_s','objective']
    queues=['queue_mean','queue_P90','queue_max','queue_spatial_mean_ft','queue_spatial_P90_ft','queue_at_green_onset_mean','stopped_queue_clearance_mean_s','clearance_mean_s','residual_5s_mean','residual_10s_mean','propagation_mean_s']
    columns=['metric','REAL_B2','PRECALIBRATION','FINAL_CALIBRATED','absolute_change','relative_change','interpretation']
    objective=pd.DataFrame([dict(component=k,error=v) for k,v in selected['component_errors'].items()])
    text=f'''# PEACHTREE-4 — Final B2 calibration and parameter freeze

**{CLASSIFICATION}**. Calibration **FROZEN**. Structure3U **FROZEN and byte-identical**. Next phase: **PEACHTREE-5 VALIDATION B1**, not another calibration or structural audit. No B1 data accessed.

## 1–9. Bounds, search, objective, parameters, boundary audit and sensitivity

Bounds copied from existing B2-only parameter-estimation distributions before optimization. v0 P50/P95; other parameters P10/P90 of their documented samples. Physical positivity is respected; no literature bounds were invented because B2 provides ranges. The existing Time_Headway estimate is a front-to-front seed for the net-gap IDM T parameter, not direct identity; acceleration/braking distributions provide bounds, not perfect parameter identification.

{table(bounds)}

Evaluated parameter sets: **{selected['evaluated_parameter_sets']}**. Stage A40 reproducible Latin Hypercube points plus unchanged baseline; Stage B bounded Nelder-Mead from the best2 LHS candidates, at most50 calls each. Every set is scored on all5 development seeds **5000–5004**, using their arithmetic mean, never the best seed. All candidates and all seed/component outcomes remain in CSVs. Local budget termination is finite completion, not proof of global convergence. The final set is the minimum predeclared score among all valid evaluated sets; there is no manual/visual override or second calibration.

Final development objective: **{selected['objective']:.8f}**. Six domains have equal1/6 weight. Components are normalized before averaging within domain: mean errors relative to REAL means; W1 by REAL IQR; KS by1; stopping/incidence/episode errors relative to REAL; flow by REAL departures. Scale/weight files were hashed before the first optimizer call and never changed. Queues have zero calibration weight because REAL context and SIM TARGET populations differ.

{table(objective)}

{table(values)}

delta remains4. Release1.6s, effective references, schedules/offsets, FIFO, arrivals, scope, lanes, population, stopped0.1m/s and queue threshold remain unchanged. CheckedCalibrationModel delegates physical dynamics and adds invariant assertions only.

{table(audit)}

BOUNDARY_HIT means within0.1% of the frozen interval; this flags uncertainty and never expands bounds. Sensitivity is Spearman on the40 valid LHS points, excluding the locally clustered sample. Descriptor WELL/MODERATELY/WEAKLY_INFORMED uses max absolute parameter→domain/total correlation >=0.6 / >=0.3 / otherwise. These are exploratory search-response descriptors, not proof of unique or causal identification; p-values are descriptive, no multiple-comparison inference claimed.

{table(sens)}

## 10–17. Primary REAL/PRE/FINAL metrics and tradeoffs

{table(compare[compare.metric.isin(primary)][columns])}

REAL and SIM share frozen target cohort/scope/window for primary domains. Complete travel excludes initial agents; throughput includes them. Headway retains the existing cleaned same-lane/road definition and in-scope leader requirement. Stop durations use complete contiguous episodes, preserving censoring. Section travel is recomputed with the same effective cut pair and linear crossing interpolation for both REAL and SIM: historical3U section means used different REAL cuts and are not reused for this objective. This is a measurement-comparability correction, not a structural change.

absolute_change is signed FINAL−PRE; relative_change divides by PRE and is undefined when PRE=0. Improvement means lower KS/W1/temporal/objective errors, or a scalar closer to REAL. All worsened metrics remain visible. No10% pass threshold or TRAIN validation claim. Lower total objective can involve tradeoffs between domains.

## 18. Secondary queue diagnostics

{table(compare[compare.metric.isin(queues)][columns])}

Queue means/P90/extents use the unchanged3T observed occupied-lane snapshot definition. REAL all-observed arterial context differs from SIM TARGET; diagnostic differences cannot reopen structure. Green onset membership, stopped clearance, empirical-exit discharge clearance and residual5/10s retain source censoring and definitions. No queue threshold, band or follower delay was fitted.

## 19–23. Final TRAIN replications, temporal diagnostics, intervals and QA

30 FINAL runs use **4000–4029**, disjoint from development and unused for selection. An additional30 PRE runs use the same evaluation seeds for a paired comparison. Parameters are hash-locked before these rollouts and unchanged afterwards. Every rollout checks conservation, no overlap/negative speed, finite states/acceleration, valid signals/exits and reduced boundaries.30 final invariant results are in final_30_replica_runs.csv.

Mean/SD/t-based95% CI of simulation means are in final_30_replica_summary.csv, not confidence intervals for REAL or validation. Temporal comparison contains all60 PRE/FINAL seed results at10/30/60s for speed, operational stopped fraction, active vehicles and throughput, with RMSE/MAE/bias/correlation. Empty-clock speed/stopped fractions remain undefined; occupancy/throughput zero is meaningful. Correlation is undefined for constant/insufficient series. Final-seed4000 plots are a predeclared illustration, not selected by appearance; all30 numerical results remain available.

TRAIN tests retain all168 previous cases and add calibration-scope/freeze/seed/invariant tests. Exact final counts are in outputs/peachtree4/test_report.json. Historical actual-source fixtures remain skipped before setUpClass. UI shows final five parameters READ ONLY and BASELINE CALIBRATED — TRAIN B2; TEST B1 LOCKED, E1/E2/E3 disabled. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED; automated checks do not establish visual browser validation.

## 24–28. Freeze, holdout and exit decision

Structural freeze intact: **YES**. Calibration freeze: **FROZEN**. B1 LOCKED: **YES**. All earlier artifacts/reports remain byte-identical; preservation manifest verifies this. Both freezes record hashes, values, rules, dates, bounds and seeds. The final parameters must not change during B1 validation. A worse B1 result will be a validation outcome, never permission to fit B1 or start another calibration.

**{CLASSIFICATION}**. Next step: **PEACHTREE-5 VALIDATION B1**. Future validation must be titled **TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE**, acknowledging prior feasibility-summary exposure. Stop here without opening B1, implementing E1/E2/E3, modifying structure or executing a second calibration.
'''
    (ROOT/'docs/peachtree4_final_calibration.md').write_text(text,encoding='utf-8')

if __name__=='__main__':finish()
