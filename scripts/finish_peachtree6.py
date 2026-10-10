"""Paired multicriteria evaluation of exactly three frozen alternatives."""
import json
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.stats import t
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from calibration.scenarios import OUT,ROOT,MODES,PRIMARY,design,verify,scenario_inputs,rollout,queues,sha
from ui.canvas_renderer import finite_json

def interval(values):
    x=pd.Series(values).dropna();n=len(x);sd=x.std();half=t.ppf(.975,n-1)*sd/np.sqrt(n) if n>1 else np.nan
    return dict(n=n,mean=x.mean(),SD=sd,CI95_low=x.mean()-half,CI95_high=x.mean()+half,median=x.median(),P25=x.quantile(.25),P75=x.quantile(.75))

def ratios(a,b,keys):return float(np.mean([a[k]/b[k]-1 if b[k]!=0 else 0 if a[k]==0 else np.inf for k in keys]))

def score(a,b):
    travel=ratios(a,b,['travel_mean_s','section_travel_mean_s'])
    stopping=ratios(a,b,['operational_stopped','vehicles_stopped_fraction','mean_stopped_time_per_vehicle_s','stop_episodes_per_vehicle'])
    flow=ratios(a,b,['departure_t50_s','departure_t90_s','departure_final_s'])
    balance=max(ratios(a,b,[di+'_travel_mean_s',di+'_operational_stopped']) for di in ['NB','SB'])
    return dict(TRAVEL=travel,STOPPING=stopping,TEMPORAL_FLOW=flow,DIRECTIONAL_BALANCE=balance,DECISION_SCORE=np.mean([travel,stopping,flow,balance]))

def trace_for(context,mode,seed=7000):
    m,d=rollout(context,mode,seed,True);q,r,p=queues(d,m.inputs);bytime={round(time,1):g for time,g in q[q.queue.gt(0)].groupby('time')}
    for frame in m.recorder.traces:
        group=bytime.get(round(frame['time'],1));frame['queue_heads']=[] if group is None else [dict(id=a.head_id,queue=a.queue,spatial_ft=a.spatial_ft) for a in group.itertuples()]
    return finite_json(dict(mode='SCENARIO_EXPERIMENTATION',context=context,scenario=mode,seed=seed,seed_role='ILLUSTRATIVE PREDECLARED SEED',
        network=m.inputs['network'],frames=m.recorder.traces,summary=m.summary,receiving_scope=m.inputs['receiving_scope'],control_envelopes=m.inputs['control_envelopes'],progression=design()['E2'],
        signal_intervals=m.inputs['signals'],source_window_start_relative_s=m.inputs['source_window_start_relative_s']))

def figures(frame,paired,robust):
    folder=OUT/'figures';folder.mkdir(exist_ok=True)
    def save(name):plt.tight_layout();plt.savefig(folder/name,dpi=160);plt.close()
    means=frame.groupby(['context','scenario']).mean(numeric_only=True)
    for file,keys in [('travel_time_scenarios.png',['travel_mean_s','section_travel_mean_s']),('stopping_scenarios.png',['operational_stopped','vehicles_stopped_fraction']),('stopped_time_scenarios.png',['mean_stopped_time_per_vehicle_s']),('directional_travel.png',['NB_travel_mean_s','SB_travel_mean_s']),('directional_stopping.png',['NB_operational_stopped','SB_operational_stopped']),('queue_scenarios.png',['queue_mean','queue_P90','queue_max','clearance_mean_s'])]:
        fig,axes=plt.subplots(1,len(keys),figsize=(max(7,4*len(keys)),4),squeeze=False)
        for ax,key in zip(axes.flat,keys):
            for k,context in enumerate(['B2','B1']):ax.bar(np.arange(4)+(k-.5)*.35,[means.loc[(context,s),key] for s in MODES],width=.35,label=context)
            ax.set_xticks(range(4),MODES);ax.set_ylabel(key);ax.legend()
        save(file)
    fig,axes=plt.subplots(4,1,figsize=(13,8),sharex=True)
    colors={'GREEN':'#29a37a','RED':'#e36b66','YELLOW':'#e5b445'}
    for ax,mode in zip(axes,MODES):
        data=scenario_inputs('B2',mode);origin=data['source_window_start_relative_s']
        for r in data['signals']:
            if r['direction']!=design()['E2']['direction']:continue
            start=r['t_start_s']-origin;end=r['t_end_s']-origin
            if end>0 and start<400:ax.broken_barh([(max(0,start),min(400,end)-max(0,start))],(r['intersection_id']-.3,.6),facecolors=colors[r['state']])
        ax.set_yticks([2,3],['11th','12th']);ax.set_ylabel(mode)
    axes[-1].set_xlabel('B2 simulation time (s) · dominant SB · first400s');save('signal_timeline_scenarios.png')
    plt.figure(figsize=(10,4))
    for mode in MODES:
        ex=pd.read_csv(OUT/'replicas'/f'departures_B2_{mode}_7000.csv').time.sort_values();plt.step(ex,np.arange(1,len(ex)+1),where='post',label=mode)
    plt.xlabel('B2 time(s), illustrative predeclared seed7000');plt.ylabel('Cumulative departures');plt.legend();save('temporal_departures.png')
    plot=paired[paired.metric.eq('travel_mean_s')]
    plt.figure(figsize=(8,4))
    for context,x in plot.groupby('context'):
        plt.errorbar(x.scenario,x['mean'],yerr=[x['mean']-x.CI95_low,x.CI95_high-x['mean']],marker='o',label=context)
    plt.axhline(0,color='gray',lw=1);plt.ylabel('Paired travel effect(s) · E−BASE');plt.legend();save('scenario_robustness.png')
    for mode in MODES:
        fig,axes=plt.subplots(1,2,figsize=(13,4.5))
        d=pd.read_parquet(OUT/f'illustrative_B2_{mode}.parquet')
        for ax,di in zip(axes,[2,4]):
            for id,g in d[d.direction.eq(di)].groupby('id'):ax.plot(g.time,g.y,lw=.5,alpha=.6)
            ax.set(xlim=(0,400),xlabel='B2 time(s) · illustrative seed7000',ylabel='Front-center Local_Y(ft)',title=mode+' '+('NB' if di==2 else 'SB'))
        save(f'space_time_{mode}.png')

def finish():
    verify();spec=design();frame=pd.concat([pd.read_csv(OUT/f'{context.lower()}_scenario_runs.csv') for context in ['B2','B1']],ignore_index=True)
    if len(frame)!=240 or frame.groupby(['context','scenario']).seed.nunique().ne(30).any():raise RuntimeError('Incomplete240 experiment')
    if not frame[['conservation_verified','no_overlap','no_negative_speed']].all().all():raise RuntimeError('Physical invariant failed')
    numeric=[k for k in frame.select_dtypes(include='number') if k!='seed'];summary=[];effects=[];scores=[]
    for (context,mode),g in frame.groupby(['context','scenario']):
        for key in numeric:summary.append(dict(context=context,scenario=mode,metric=key,**interval(g[key])))
    summaries=pd.DataFrame(summary)
    for context in ['B2','B1']:summaries[summaries.context.eq(context)].to_csv(OUT/f'{context.lower()}_scenario_summary.csv',index=False)
    for context,g in frame.groupby('context'):
        base=g[g.scenario.eq('BASE')].set_index('seed')
        for mode in ['E1','E2','E3']:
            alt=g[g.scenario.eq(mode)].set_index('seed')
            for key in numeric:
                diff=alt[key]-base[key]
                effects.append(dict(context=context,scenario=mode,metric=key,**interval(diff),
                    mean_percentage_change=(diff/base[key].replace(0,np.nan)*100).mean(),fraction_seeds_improved=diff.lt(0).mean()))
            for seed in base.index:scores.append(dict(context=context,scenario=mode,seed=seed,**score(alt.loc[seed],base.loc[seed])))
    paired=pd.DataFrame(effects);paired.to_csv(OUT/'paired_differences.csv',index=False)
    summaries[summaries.metric.str.startswith(('NB_','SB_'))].to_csv(OUT/'directional_results.csv',index=False)
    summaries[summaries.metric.str.startswith(('queue','clearance'))].to_csv(OUT/'queue_results.csv',index=False)
    scoreframe=pd.DataFrame(scores);scoreframe.to_csv(OUT/'decision_score.csv',index=False)
    robustness=[]
    for (mode,key),g in paired.groupby(['scenario','metric']):
        b2=g[g.context.eq('B2')].iloc[0];b1=g[g.context.eq('B1')].iloc[0]
        if b2['mean']<0 and b1['mean']<0 and b2.fraction_seeds_improved>.5 and b1.fraction_seeds_improved>.5:label='ROBUST_IMPROVEMENT'
        elif b2['mean']*b1['mean']<0:label='CONTEXT_DEPENDENT'
        elif b2['mean']>0 and b1['mean']>0 and b2.fraction_seeds_improved<.5 and b1.fraction_seeds_improved<.5:label='ROBUST_WORSENING'
        else:label='MIXED'
        robustness.append(dict(scenario=mode,metric=key,classification=label,B2_effect=b2['mean'],B1_effect=b1['mean']))
    robust=pd.DataFrame(robustness);robust.to_csv(OUT/'robustness_summary.csv',index=False)
    mean=frame.groupby(['context','scenario']).mean(numeric_only=True);pareto=[]
    for context in ['B2','B1']:
        for a in MODES:
            for b in MODES:
                if a==b:continue
                x=mean.loc[(context,a),PRIMARY];y=mean.loc[(context,b),PRIMARY]
                pareto.append(dict(context=context,scenario=a,other=b,dominates=bool((x<=y).all() and (x<y).any())))
    pareto=pd.DataFrame(pareto);pareto.to_csv(OUT/'pareto_analysis.csv',index=False)
    eligible=[]
    for mode in ['E1','E2','E3']:
        dominated=pareto[pareto.other.eq(mode)&pareto.dominates]
        if dominated.empty and (scoreframe[scoreframe.scenario.eq(mode)].groupby('context').DECISION_SCORE.mean()<0).all():eligible.append(mode)
    chosen=min(eligible,key=lambda mode:scoreframe[scoreframe.scenario.eq(mode)].DECISION_SCORE.mean()) if eligible else 'NO_ALTERNATIVE_DOMINATES_BASELINE'
    # Counterfactual departure data contain only SIM outputs, never REAL_E labels.
    pd.concat([pd.read_csv(p) for p in (OUT/'replicas').glob('departures_*.csv')],ignore_index=True).to_csv(OUT/'temporal_departures.csv',index=False)
    pd.concat([pd.read_csv(p) for p in (OUT/'replicas').glob('emergent_*.csv')],ignore_index=True).to_csv(OUT/'emergent_behavior.csv',index=False)
    figures(frame,paired,robust)
    (OUT/'traces').mkdir(exist_ok=True)
    for context in ['B2','B1']:
        for mode in MODES:(OUT/'traces'/f'{context}_{mode}_7000.json').write_text(json.dumps(trace_for(context,mode),allow_nan=False,default=lambda x:x.item()))
    freeze=dict(status='COMPLETED',classification='A. SCENARIO_EXPERIMENTATION_COMPLETE',scenario_design_hash=sha(OUT/'scenario_design_freeze.json'),
        freeze_hashes=spec['freeze_hashes'],seeds=json.loads((OUT/'experiment_seeds.json').read_text())['seeds'],exactly_three_alternatives=['E1','E2','E3'],
        official_rollouts=240,scenario_parameters={k:spec[k] for k in MODES},all_summary_results=summaries.to_dict('records'),
        recommended_alternative=chosen,recommendation_rule=spec['decision_score']['tie_rule'],recommended_label='RECOMMENDED_WITHIN_SCOPE' if eligible else chosen,
        limitations=json.loads((ROOT/'outputs/peachtree5/validation_freeze.json').read_text())['limitations'],
        no_scenario_optimization=True,no_IDM_change=True,no_scope_change=True,UI_status='UI_IMPLEMENTED_NOT_BROWSER_VALIDATED',
        date_time=datetime.now(timezone.utc).isoformat())
    (OUT/'experiment_freeze.json').write_text(json.dumps(freeze,indent=2))
    report(spec,summaries,paired,robust,pareto,scoreframe,freeze)
    verify();print('A. SCENARIO_EXPERIMENTATION_COMPLETE; recommendation:',chosen,flush=True)

def table(d):
    def val(x):return f'{x:.4f}' if isinstance(x,(float,np.floating)) and np.isfinite(x) else str(x).replace('|','/')
    return '\n'.join(['| '+' | '.join(d.columns)+' |','| '+' | '.join(['---']*len(d.columns))+' |']+['| '+' | '.join(val(x) for x in row)+' |' for row in d.itertuples(index=False,name=None)])

def report(spec,summaries,paired,robust,pareto,scores,freeze):
    keys=['travel_mean_s','section_travel_mean_s','operational_stopped','vehicles_stopped_fraction','mean_stopped_time_per_vehicle_s','stop_episodes_per_vehicle','speed_mean_ft_s','headway_mean_ft','queue_mean','clearance_mean_s','departure_t50_s','departure_t90_s','departure_final_s','NB_travel_mean_s','SB_travel_mean_s','NB_operational_stopped','SB_operational_stopped']
    brief=summaries[summaries.metric.isin(keys)].pivot_table(index=['context','metric'],columns='scenario',values='mean').reset_index()
    text=f'''# PEACHTREE-6 — final scenario experimentation

**A. SCENARIO_EXPERIMENTATION_COMPLETE**. Recommended within evaluated alternatives: **{freeze['recommended_alternative']}**. Exactly3 alternatives, BASE reference, two observed acquisition contexts; no optimizer or new timing search.

## 1–10. Frozen scenario design

BASE preserves each acquisition's observed schedule. E1 nominal Through green+10%, funded from same-cycle RED, with0.1s floor and RED>=0.1s feasibility constraint. GREEN onset/next GREEN onset (cycle) and YELLOW duration remain fixed. Partial cycles remain unchanged unless covered by complete experimental edge-extension cycles. All-red is not separately represented/observed; no independent all-red phase is altered. E1 is EXPERIMENTAL_RULE, never operational field timing.

E2 dominant B2 direction={spec['E2']['DOMINANT_PROGRESSION_DIRECTION']}; counts={spec['E2']['B2_demand_counts']}. Progression median={spec['E2']['PROGRESSION_TRAVEL_TIME']:.6f}s, n={spec['E2']['n_no_stop']}, P25={spec['E2']['P25']}, P75={spec['E2']['P75']}, IQR={spec['E2']['IQR']}. Source B2 REAL no-stop complete Through trips between effective controls, contiguous tracking, operational<=0.1m/s exclusion; minimum10 trips predeclared. No B1 or SIM outcome selects the direction/time.

Upstream={spec['E2']['upstream_intersection']}, downstream={spec['E2']['downstream_intersection']}. BASE offset={spec['E2']['BASE_OFFSET']:.6f}s; E2 offset={spec['E2']['E2_OFFSET']:.6f}s; reference cycle={spec['E2']['reference_cycle_s']:.6f}s; single shift={spec['E2']['OFFSET_SHIFT_SECONDS']:.6f}s. Translate the entire downstream intersection NB/SB timelines by that SAME shift, both contexts. Observed cycle/phase durations retained internally; nearest complete observed cycle repeats only outside original coverage to support horizon-edge translation. This edge assumption is explicit, never selected by outcome. E3 is exactly E1+the same E2 shift, no recalculation.

Design and score were hashed before first scenario rollout. Seeds7000–7029 paired for all4 modes and both contexts: **240 official runs**. Extra repeated seed7000 traces support rendering only, not statistical sample size or seed selection. All arrivals/snapshots/speed pools/physics/parameters/controls/lanes/FIFO/thresholds/scopes remain frozen; only signal inputs differ. No REAL_E1/E2/E3 data exist or are generated.

## 11–23. Results and directional tradeoffs

{table(brief)}

Headway here reports all positive simulated leader spacing across the route, including interior, as SECONDARY_DIAGNOSTIC; it is not the cleaned road-CF absolute validation statistic and must not be compared to that value as a change of bias. Speed is contextual, never higher=automatically better. Queues have identical modeled populations across alternatives, so paired differences are informative; absolute REAL context remains different. Total throughput is fixed demand closure, never the primary improvement criterion. Departure50/90/final times use the full expected cohort; unfinished horizon-censored quantiles remain missing rather than use a smaller completed subset. Negative time differences improve progression; positive cumulative E−BASE departures indicate earlier discharge.

Stopped time equals sum of operational-stopped0.1s samples per vehicle, including zero-stop vehicles in the population mean. Total stopped-time exposure is separately retained. Initial-vehicle travel is censored and excluded from corridor mean, as in baseline. Section travel uses identical effective cuts/interpolation. NB/SB are reported separately so opposite-direction deterioration is explicit.

## 24–28. Paired effects, robustness, Pareto and score

{table(paired[paired.metric.isin(PRIMARY)][['context','scenario','metric','mean','SD','CI95_low','CI95_high','median','P25','P75','mean_percentage_change','fraction_seeds_improved']])}

{table(robust[robust.metric.isin(PRIMARY)])}

Pareto uses all predeclared primary metrics (including both directions), exact mean weak dominance plus one strict improvement; no p-values or post-hoc weights. Non-dominated alternatives must have a negative score in both contexts before the frozen equal-context score selects one; otherwise no alternative is recommended. Four score domains have equal25% weight: normalized corridor/section travel; normalized stopped fraction/incidence/time/episodes; departure50/90/final timing; worst-direction average relative travel/stopped change. Lower score is better. It is a secondary tie-break, not traffic timing optimization.

{table(pareto[pareto.dominates])}

{table(scores.groupby(['context','scenario'])[['TRAVEL','STOPPING','TEMPORAL_FLOW','DIRECTIONAL_BALANCE','DECISION_SCORE']].mean().reset_index())}

## 29–37. Emergence, interpretation, integrity, recommendation and UI

All configurations quantify queues under RED/GREEN, vehicle accumulation, collective speed variability, multiple-stop vehicles and GREEN discharge/clearance. Space-time figures separate NB/SB for predeclared B2 seed7000; the timelines show SB progression at both intersections. Results and conclusions use30 runs, not plots alone. Full per-seed queue/departure files and emergent_behavior.csv preserve collective evidence.

Recommended within scope: **{freeze['recommended_alternative']}**, derived by the frozen Pareto/score rule above. Read directional effects before interpreting global benefit. These are relative model effects under BASELINE_VALIDATED_WITH_LIMITATIONS: headway/stop episode/duration biases persist; turning/local/background/cross traffic and lateral-street effects are omitted; receiving cuts remain free; total demand is closed. This is not a field-ready plan, absolute capacity estimate, full Peachtree prediction or globally optimal timing.

All prior freezes and artifacts remain byte-identical. Experiment freeze=COMPLETED. No IDM/scope/baseline rules changed. Exactly3 alternatives. Tests preserve205 prior cases and add signal-only, cycle/yellow/offset/combination/paired-seed/invariant/UI/design checks; final exact totals are in test_report.json. UI enables scenario/context/illustrative-seed controls, frozen IDM READ ONLY, live AgentPy scenario traces and explanatory progression overlay. Official statistics use the30 paired replicas. UI_IMPLEMENTED_NOT_BROWSER_VALIDATED.
'''
    (ROOT/'docs/peachtree6_scenario_experimentation.md').write_text(text,encoding='utf-8')
    (ROOT/'docs/peachtree6_final_decision.md').write_text('# Final scenario decision\n\nA. SCENARIO_EXPERIMENTATION_COMPLETE\n\nRECOMMENDED_WITHIN_SCOPE: '+freeze['recommended_alternative']+'\n\nThe frozen Pareto and equal-domain decision score, cross-context paired evidence and directional tradeoffs support this decision. See peachtree6_scenario_experimentation.md and paired_differences.csv for full effects/CI; no timing optimization or field-ready recommendation claimed. All documented baseline limitations apply.\n',encoding='utf-8')

if __name__=='__main__':finish()
