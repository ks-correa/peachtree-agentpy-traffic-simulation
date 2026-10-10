"""Compare all states/temporalities and emit truthful revision decision."""
import json
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp,wasserstein_distance,t
from calibration.structural import OUT,semantics
from calibration.structural_metrics import *
from calibration.objective import TrainTargets
from scripts.audit_peachtree3r import episode_summary,stopline_audit
from simulation.training_data import ROOT,require_train,load_inputs
from simulation.signals import controllers_from_inputs
from scripts.evaluate_local import digest

def replace_series(path,new):
    old=pd.read_csv(path);old=old[old.series.ne('REVISED_BASELINE')]
    pd.concat([old,new],ignore_index=True).to_csv(path,index=False)

def sim_headway(d):
    def section(y):return np.where(((y>=630.810)&(y<=777.753))|((y>=1155.863)&(y<=1246.452)),0,np.where(y<630.810,2,np.where(y<1155.863,3,4)))
    leader=d.set_index(['frame','id']).reindex(pd.MultiIndex.from_arrays([d.frame,d.leader]))
    e=section(d.y.to_numpy());l=section(leader.y.to_numpy())
    return d.loc[(e>0)&(e==l)&d.intersection.gt(0)&d.lane.isin([1,2])&d.headway.notna(),'headway'].to_numpy()

def compare(real,old,rev):
    target=TrainTargets();rows=[]
    arrays={'speed':(target.speed,old.speed.to_numpy(),rev.speed.to_numpy()),'headway':(target.headway,sim_headway(old),sim_headway(rev)),
        'travel_time':(target.travel,pd.read_csv(ROOT/'outputs/b2_simulated_travel_times.csv').travel_time_s.to_numpy(),pd.read_csv(OUT/'revised_travel_times.csv').travel_time_s.to_numpy())}
    for name,(a,b,c) in arrays.items():
        rows.append({'metric':name+'_mean','REAL_B2':np.mean(a),'OLD_BASELINE':np.mean(b),'REVISED_BASELINE':np.mean(c),'population':'TARGET'})
        rows.append({'metric':name+'_KS','REAL_B2':0.,'OLD_BASELINE':ks_2samp(a,b,method='asymp').statistic,'REVISED_BASELINE':ks_2samp(a,c,method='asymp').statistic,'population':'TARGET'})
        rows.append({'metric':name+'_W1','REAL_B2':0.,'OLD_BASELINE':wasserstein_distance(a,b),'REVISED_BASELINE':wasserstein_distance(a,c),'population':'TARGET'})
    for metric,function in [('exact_zero_stopped',lambda d:d.speed.eq(0).mean()),('operational_stopped',lambda d:np.mean(stopped(d.speed)))]:
        rows.append({'metric':metric,'REAL_B2':function(real),'OLD_BASELINE':function(old),'REVISED_BASELINE':function(rev),'population':'TARGET vehicle-time'})
    for name in ['duration_mean_s','duration_median_s','episodes','fraction_vehicles_stopped']:
        ep=pd.read_csv(OUT/'stop_episode_real_vs_sim.csv').set_index('series');rows.append({'metric':name,**{k:ep.loc[k,name] for k in ['REAL_B2','OLD_BASELINE','REVISED_BASELINE']},'population':'TARGET; complete episodes for durations'})
    internal_real=pd.read_csv(ROOT/'outputs/b2_observed_section_times.csv').travel_time_s.mean()
    internal_old=pd.read_csv(ROOT/'outputs/b2_simulated_section_times.csv').travel_time_s.mean();internal_rev=pd.read_csv(OUT/'revised_section_times.csv').travel_time_s.mean()
    rows.append({'metric':'section_travel_time_mean','REAL_B2':internal_real,'OLD_BASELINE':internal_old,'REVISED_BASELINE':internal_rev,'population':'TARGET complete same-reference cut pairs'})
    rows.append({'metric':'throughput_total','REAL_B2':len(target.real_exits),'OLD_BASELINE':len(pd.read_csv(ROOT/'outputs/b2_simulated_exits.csv')),'REVISED_BASELINE':len(pd.read_csv(OUT/'revised_exits.csv')),'population':'TARGET including initial'})
    return pd.DataFrame(rows)

def main(acquisition='B2'):
    require_train(acquisition);inputs=load_inputs();bank=controllers_from_inputs(inputs);target=TrainTargets()
    real=pd.read_parquet(OUT/'real_observations.parquet');old=pd.read_parquet(OUT/'old_observations.parquet');rev=pd.read_parquet(OUT/'revised_observations.parquet')
    replace_series(OUT/'signal_conditioned_stopping.csv',phase_stopping(rev,'REVISED_BASELINE'))
    ep,stats=episode_summary(rev,'REVISED_BASELINE');replace_series(OUT/'stop_episodes_detail.csv',ep);replace_series(OUT/'stop_episode_real_vs_sim.csv',pd.DataFrame([stats]))
    pd.read_csv(OUT/'stop_episode_real_vs_sim.csv').to_csv(ROOT/'outputs/b2_stop_episode_comparison.csv',index=False)
    q,qt=queues(rev,'REVISED_BASELINE',json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['queue_gap_m']/FOOT_M,inputs['horizon_s'])
    replace_series(OUT/'queue_real_vs_sim.csv',q);replace_series(OUT/'queue_timeseries.csv',qt)
    replace_series(OUT/'conditional_headway.csv',conditional_headway(rev,'REVISED_BASELINE'))
    replace_series(OUT/'green_release_delay.csv',release_delays(rev,bank,'REVISED_BASELINE'))
    c=crossings(rev,inputs);c['series']='REVISED_BASELINE';replace_series(OUT/'signal_crossings.csv',c)
    replace_series(OUT/'discharge_headway.csv',discharge(c,inputs,bank,'REVISED_BASELINE'))
    line,samples=stopline_audit(rev,inputs,'REVISED_BASELINE');replace_series(OUT/'stopline_audit.csv',line);replace_series(OUT/'red_head_positions.csv',samples)
    speed,through=temporal(real,rev,target.real_exits.time.to_numpy(),pd.read_csv(OUT/'revised_exits.csv').exit_time_s.to_numpy(),inputs['horizon_s'],'REVISED_BASELINE')
    replace_series(OUT/'temporal_speed_comparison.csv',speed);replace_series(OUT/'temporal_throughput_comparison.csv',through)
    sem=semantics(real,rev);sem=sem[sem.series.eq('OLD_BASELINE')];sem['series']='REVISED_BASELINE';replace_series(OUT/'stop_speed_semantics.csv',sem)
    insertion=pd.read_csv(OUT/'safe_insertion_delay.csv')
    if 'series' not in insertion:insertion['series']='OLD_BASELINE'
    insertion=insertion[insertion.series.ne('REVISED_BASELINE')];new=pd.read_csv(OUT/'revised_safe_insertion.csv');new['series']='REVISED_BASELINE'
    pd.concat([insertion,new]).to_csv(OUT/'safe_insertion_delay.csv',index=False)
    summary=[]
    for label,d in [('OLD_BASELINE',insertion),('REVISED_BASELINE',new)]:
        if 'lane' not in d:
            first_lane=(old if label=='OLD_BASELINE' else rev).groupby('id').lane.first()
            d=d.copy();d['lane']=d.id.map(first_lane)
        inversions=0
        for _,group in d.groupby(['direction','lane']):
            actual=group.sort_values('scheduled_entry_time').actual_entry_time.to_numpy();inversions+=int(np.triu(actual[:,None]>actual[None,:],1).sum())
        summary.append({'series':label,'n':len(d),'mean_s':d.delay.mean(),'median_s':d.delay.median(),'P95_s':d.delay.quantile(.95),'max_s':d.delay.max(),
            'same_lane_order_inversion_pairs':inversions,
            'percentage_delayed_beyond_one_tick':100*d.delay.gt(.1+1e-8).mean(),'phase_changed_count':d.scheduled_phase.ne(d.actual_phase).sum(),'phase_changed_fraction':d.scheduled_phase.ne(d.actual_phase).mean(),
            'note':'Sub-tick clock rounding is not unsafe insertion delay; up to one tick expected'})
    pd.DataFrame(summary).to_csv(OUT/'safe_insertion_summary.csv',index=False)
    comparison=compare(real,old,rev);comparison.to_csv(OUT/'old_vs_revised.csv',index=False)
    histogram=[];edges=np.arange(0,3.0001,.01)
    for label,d in [('REAL_B2',real),('OLD_BASELINE',old),('REVISED_BASELINE',rev)]:
        hist=np.histogram(d.speed,edges)[0]
        for lo,hi,n in zip(edges[:-1],edges[1:],hist):histogram.append({'series':label,'low_ft_s':lo,'high_ft_s':hi,'count':n,'fraction_all_frames':n/len(d)})
    pd.DataFrame(histogram).to_csv(OUT/'low_speed_histogram.csv',index=False)
    paired_old=pd.read_csv(OUT/'paired_old_replicates.csv').set_index('seed');paired_new=pd.read_csv(OUT/'revised_replicates.csv').set_index('seed')
    deltas=[]
    for name in ['mean_speed_ft_s','mean_headway_ft','mean_travel_time_s','operational_stopped_fraction','fraction_vehicles_stopped','stop_duration_W1_s','throughput_temporal_normalized_error','max_cumulative_deviation_10s','throughput_MAE_10s']:
        v=paired_new[name]-paired_old[name];margin=t.ppf(.975,29)*v.std(ddof=1)/np.sqrt(30)
        deltas.append({'metric':name,'OLD_mean':paired_old[name].mean(),'REVISED_mean':paired_new[name].mean(),'paired_delta_mean':v.mean(),'paired_delta_SD':v.std(ddof=1),'CI95_delta_low':v.mean()-margin,'CI95_delta_high':v.mean()+margin})
    pd.DataFrame(deltas).to_csv(OUT/'paired_old_vs_revised.csv',index=False)
    preserved=json.loads((OUT/'old_baseline_manifest.json').read_text());checks={p:digest(ROOT/p)==sha for p,sha in preserved['hashes'].items()}
    if not all(checks.values()):raise RuntimeError('Original artifact changed: '+str([p for p,v in checks.items() if not v]))
    (OUT/'preservation_check.json').write_text(json.dumps({'all_original_hashes_match':True,'checks':checks},indent=2),encoding='utf-8')
    decision={'classification':'B. BASELINE_NEEDS_REVISION','reason':'Operational measurement and empirical green-release mechanism are implemented, but the dominant residual stopping is downstream of included controls. Episode frequency, queue/temporal residuals and throughput improvement are insufficient for readiness. No unsupported receiving rule or turning agent was fabricated.',
        'B1_LOCKED':True,'background_agents_added':0,'ui_status':'UI_IMPLEMENTED_NOT_BROWSER_VALIDATED','IDM_recalibrated':False,
        'IDM_reason':'Avoid compensating unmodeled receiving-context structure with fitted parameters; retain existing B2 IDM while isolating the measured release mechanism.',
        'scenarios':'E1/E2/E3 DISABLED','next_step':'Identify receiving restrictions or revise observability/evaluation at the existing cuts from B2 and official evidence; no B1 until structural gap is resolved.'}
    (OUT/'decision.json').write_text(json.dumps(decision,indent=2),encoding='utf-8')
    print(comparison.to_string(index=False));print(pd.DataFrame(deltas).to_string(index=False));print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':main()
