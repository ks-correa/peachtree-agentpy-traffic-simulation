"""Complete structural audit before any dynamics or parameter revision."""
import json
import numpy as np
import pandas as pd
from calibration.structural import OUT,full_b2,contextualize
from calibration.structural_metrics import *
from simulation.training_data import ROOT,load_inputs,require_train
from simulation.signals import controllers_from_inputs

def episode_summary(d,label):
    ep=stop_episodes(d);ep['series']=label
    complete=ep[~ep.left_censored&~ep.right_censored];dur=complete.duration_s
    counts=ep.groupby('id').size().reindex(d.id.unique(),fill_value=0)
    row={'series':label,'vehicles':d.id.nunique(),'vehicles_stopped':ep.id.nunique(),'fraction_vehicles_stopped':ep.id.nunique()/d.id.nunique(),
        'episodes':len(ep),'complete_episodes':len(complete),'mean_stops_per_vehicle':counts.mean(),'median_stops_per_vehicle':counts.median(),
        'duration_mean_s':dur.mean(),'duration_median_s':dur.median(),'duration_P25_s':dur.quantile(.25),'duration_P75_s':dur.quantile(.75),'duration_max_s':dur.max(),
        'censored_episodes':len(ep)-len(complete)}
    return ep,row

def stopline_audit(d,inputs,label):
    rows=[];samples=[]
    for (inter,direction,lane,time),q in d[d.intersection.isin([2,3])&d.lane.isin([1,2])&d.phase.eq('RED')].groupby(['intersection','direction','lane','time']):
        head=q.sort_values('distance').iloc[0]
        if head.speed>STOP_FT_S:continue
        samples.append({'series':label,'intersection':inter,'direction':direction,'lane':lane,'time':time,'distance_ft':head.distance,'y_ft':head.y,'id':head.id})
    samples=pd.DataFrame(samples)
    for line in inputs['network']['stop_lines']:
        q=samples[(samples.intersection==line['intersection'])&(samples.direction==line['direction'])]
        rows.append({'series':label,'intersection':line['intersection'],'direction':line['direction'],'OLD_STOPLINE':line['local_y_ft'],'NEW_STOPLINE':line['local_y_ft'],
            'head_stopped_RED_frames':len(q),'distance_median_ft':q.distance_ft.median(),'distance_P25_ft':q.distance_ft.quantile(.25),'distance_P75_ft':q.distance_ft.quantile(.75),
            'distance_P95_ft':q.distance_ft.quantile(.95),'EVIDENCE':'nearest observed arterial normal-lane approach head, operationally stopped on RED; proxy not surveyed bar',
            'REASON':'Audit only: observed queue fronts are not direct painted-bar coordinates. Do not infer geometry by fitting stopped_fraction.'})
    return pd.DataFrame(rows),samples

def interactions(full,real):
    target=set(real.id);band=full[full.local_y.between(400,1400)&full.v_class.isin([2,3])].copy()
    # Same-frame geometric predecessor, independent of potentially bad Preceding IDs.
    arterial=band[band.direction.isin([2,4])&band.lane_id.isin([1,2])].copy()
    arterial['progress']=np.where(arterial.direction==2,arterial.local_y,-arterial.local_y)
    arterial=arterial.sort_values(['frame_id','direction','lane_id','progress'],ascending=[True,True,True,False])
    group=arterial.groupby(['frame_id','direction','lane_id'])
    arterial['geometric_leader_key']=group.trajectory_key.shift();arterial['geometric_gap']=group.progress.shift()-group.v_length.shift()-arterial.progress
    arterial['geometric_leader_speed']=group.v_vel.shift()
    ego=arterial[arterial.trajectory_key.isin(target)&arterial.t_relative.ge(93.4)]
    excluded=ego.geometric_leader_key.notna()&~ego.geometric_leader_key.isin(target)&ego.geometric_gap.gt(0)
    rows=[{'interaction':'same_lane_geometric_predecessor','target_frames':int(excluded.sum()),'target_vehicles':ego[excluded].trajectory_key.nunique(),
        'background_vehicles':ego[excluded].geometric_leader_key.nunique(),'interpretation':'geometric interaction opportunity; not independent causal effect'}]
    queue=excluded&ego.v_vel.le(STOP_FT_S)&ego.geometric_leader_speed.le(STOP_FT_S)
    rows.append({'interaction':'operationally_stopped_queue_predecessor','target_frames':int(queue.sum()),'target_vehicles':ego[queue].trajectory_key.nunique(),
        'background_vehicles':ego[queue].geometric_leader_key.nunique(),'interpretation':'observed adjacent queued predecessor outside target cohort'})
    counts={'adjacent_lane_overlap':set(),'nearby_turning_50ft':set()};others={k:set() for k in counts};egos={k:set() for k in counts}
    for frame,q in band[band.t_relative.ge(93.4)].groupby('frame_id',sort=False):
        t=q[q.trajectory_key.isin(target)];b=q[~q.trajectory_key.isin(target)]
        if t.empty or b.empty:continue
        for a in t.itertuples():
            delta=(b.local_y-a.local_y).abs()
            masks={'adjacent_lane_overlap':b.direction.eq(a.direction)&(b.lane_id-a.lane_id).abs().eq(1)&delta.le((b.v_length+a.v_length)/2),
                'nearby_turning_50ft':b.movement.isin([2,3])&delta.le(50.)}
            for name,mask in masks.items():
                if mask.any():counts[name].add((frame,a.trajectory_key));egos[name].add(a.trajectory_key);others[name].update(b.loc[mask,'trajectory_key'])
    for name in counts:rows.append({'interaction':name,'target_frames':len(counts[name]),'target_vehicles':len(egos[name]),'background_vehicles':len(others[name]),'interpretation':'spatial proximity proxy only; no assertion of conflict or influence'})
    return pd.DataFrame(rows)

def main(acquisition='B2'):
    require_train(acquisition);inputs=load_inputs();bank=controllers_from_inputs(inputs)
    real=pd.read_parquet(OUT/'real_observations.parquet');sim=pd.read_parquet(OUT/'old_observations.parquet');full=full_b2()
    # Independent operational standard, frozen before revised physics/runs, not selected on fit.
    freeze={'phase':'PEACHTREE-3R','B1_LOCKED':True,'stopped_speed_max_m_s':STOP_M_S,'stopped_speed_max_ft_s':STOP_FT_S,
        'classification':'LITERATURE_DERIVED_OPERATIONAL_NEAR_STANDSTILL','source':'https://sumo.dlr.de/docs/Simulation/Output/TripInfo.html',
        'reason':'B2 has exact-zero atom and 0.01ft/s output precision but no clear gap separating creeping from rest. Use external 0.1m/s waiting criterion, not the threshold minimizing TRAIN error.',
        'secondary_metric':'EXACT_ZERO_STOPPED: literal speed==0; preserve legacy numerical-rest metric separately',
        'episodes':'maximal consecutive observed 0.1s ticks classified stopped; gaps split episodes; left/right censoring explicit; no invented minimum dwell',
        'distance_bands_ft':[0,50,100,200,'INF'],'release_sample':'normal-lane arterial head within100ft immediately before green, same classifier for onset/release',
        'revision_development_seeds':[210,211,212],'revision_final_seeds':list(range(3000,3030)),'IDM_initially_fixed':True,'optimization':'NONE until structural audit complete'}
    (OUT/'measurement_freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    # Full observed arterial context for queue heads and release; targets remain evaluation population.
    allroad=full[full.t_relative.ge(93.4)&full.local_y.between(400,1400)&full.direction.isin([2,4])&full.v_class.isin([2,3])].rename(columns={'trajectory_key':'id','frame_id':'frame','lane_id':'lane','local_y':'y','v_vel':'speed','v_length':'length'}).copy()
    allroad['time']=allroad.t_relative-93.4;allroad=contextualize(allroad,inputs)
    phase=[];episodes=[];epstats=[];queue=[];qt=[];head=[];release=[];cross=[];dis=[]
    for label,d in [('REAL_B2',real),('OLD_BASELINE',sim)]:
        phase.append(phase_stopping(d,label));ep,row=episode_summary(d,label);episodes.append(ep);epstats.append(row)
        q,timeline=queues(d,label,json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['queue_gap_m']/FOOT_M,inputs['horizon_s']);queue.append(q);qt.append(timeline)
        head.append(conditional_headway(d,label));release.append(release_delays(d,bank,label));c=crossings(d,inputs);c['series']=label;cross.append(c);dis.append(discharge(c,inputs,bank,label))
    pd.concat(phase).to_csv(OUT/'signal_conditioned_stopping.csv',index=False)
    pd.concat(episodes).to_csv(OUT/'stop_episodes_detail.csv',index=False);pd.DataFrame(epstats).to_csv(OUT/'stop_episode_real_vs_sim.csv',index=False)
    pd.DataFrame(epstats).to_csv(ROOT/'outputs/b2_stop_episode_comparison.csv',index=False)
    pd.concat(queue).to_csv(OUT/'queue_real_vs_sim.csv',index=False);pd.concat(qt).to_csv(OUT/'queue_timeseries.csv',index=False)
    pd.concat(head).to_csv(OUT/'conditional_headway.csv',index=False)
    pd.concat(release).to_csv(OUT/'green_release_delay.csv',index=False)
    # True observed head sample includes omitted arterial vehicles; distinguish target-only ranks.
    all_release=release_delays(allroad,bank,'REAL_B2_ALL_OBSERVED_ARTERIAL')
    all_release.to_csv(OUT/'green_release_all_context.csv',index=False)
    in_band=full[full.local_y.between(400,1400)]
    through_ids=set(k for k,z in in_band.groupby('trajectory_key') if z.movement.eq(1).all() and z.direction.nunique()==1 and z.direction.iloc[0] in [2,4])
    release_sample=all_release[all_release.queue_rank.eq(1)&~all_release.censored&all_release.id.isin(through_ids)]
    release_sample.to_csv(OUT/'release_estimation_sample.csv',index=False)
    pd.concat(cross).to_csv(OUT/'signal_crossings.csv',index=False);pd.concat(dis).to_csv(OUT/'discharge_headway.csv',index=False)
    a,samples=stopline_audit(allroad,inputs,'REAL_B2_ALL_OBSERVED_ARTERIAL');b,b_samples=stopline_audit(sim,inputs,'OLD_BASELINE')
    pd.concat([a,b]).to_csv(OUT/'stopline_audit.csv',index=False);pd.concat([samples,b_samples]).to_csv(OUT/'red_head_positions.csv',index=False)
    interactions(full,real).to_csv(OUT/'omitted_interaction_summary.csv',index=False)
    real_exits=pd.read_csv(ROOT/'outputs/b2_throughput_bins.csv') # TRAIN-only exported counts are not raw holdout access.
    from calibration.objective import TrainTargets
    observed=TrainTargets().real_exits.time.to_numpy();pred=pd.read_csv(ROOT/'outputs/b2_simulated_exits.csv').exit_time_s.to_numpy()
    temporal_speed,temporal_flow=temporal(real,sim,observed,pred,inputs['horizon_s'],'OLD_BASELINE')
    temporal_speed.to_csv(OUT/'temporal_speed_comparison.csv',index=False);temporal_flow.to_csv(OUT/'temporal_throughput_comparison.csv',index=False)
    alignment=[]
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    for (inter,direction),controller in bank.items():
        c=pd.concat(cross);r=c[(c.series=='REAL_B2')&(c.intersection==inter)&(c.direction==direction)].copy();r['phase']=[controller.at(t) for t in r.time]
        alignment.append({'intersection':inter,'direction':direction,'crossings':len(r),'GREEN_crossings':r.phase.eq('GREEN').sum(),'RED_crossings':r.phase.eq('RED').sum(),'YELLOW_crossings':r.phase.eq('YELLOW').sum(),
            'UNKNOWN_crossings':r.phase.eq('UNKNOWN').sum(),'OLD_OFFSET_s':0.,'NEW_OFFSET_s':0.,'decision':'KEEP_OBSERVED_SCHEDULE; no documented offset/direction/frame correction identified'})
        fig,axes=plt.subplots(3,1,figsize=(12,6),sharex=True,layout='constrained')
        times=np.arange(0,inputs['horizon_s'],.1);axes[0].step(times,[{'RED':0,'YELLOW':1,'GREEN':2,'UNKNOWN':-1}[controller.at(t)] for t in times],where='post',color='#19727a');axes[0].set_yticks([0,1,2],['RED','YELLOW','GREEN'])
        for label,d in [('REAL_B2',real),('OLD_BASELINE',sim)]:
            z=d[(d.intersection==inter)&(d.direction==direction)].copy();z['stop']=stopped(z.speed);counts=z.groupby('time').stop.sum();axes[1].plot(counts.index,counts,label=label,alpha=.8)
            crossings_df=c[(c.series==label)&(c.intersection==inter)&(c.direction==direction)];edges=np.arange(0,inputs['horizon_s']+10,10);counts=np.histogram(crossings_df.time,edges)[0];axes[2].step(edges[:-1],counts,where='post',label=label)
        axes[0].set_title(f'B2 observed signal plan - I{inter}, direction{direction} - no offset fitting');axes[1].set_ylabel('Operational stops');axes[2].set_ylabel('Crossings /10s');axes[2].set_xlabel('Simulation time(s)');axes[1].legend();axes[2].legend()
        fig.savefig(figdir/f'signal_{inter}_{direction}.png',dpi=140);plt.close(fig)
    pd.DataFrame(alignment).to_csv(OUT/'signal_alignment_audit.csv',index=False)
    print('EPISODES',pd.DataFrame(epstats).to_string(index=False))
    print('STOPLINES',pd.concat([a,b])[['series','intersection','direction','distance_median_ft','distance_P95_ft']].to_string(index=False))
    print('RELEASE',pd.concat(release).groupby(['series','queue_rank']).release_delay_s.agg(['count','median','mean']).to_string())
    print('UNCONTROLLED stop exposure:',real[(real.intersection==0)&(real.speed<=STOP_FT_S)].shape[0]/len(real),sim[(sim.intersection==0)&(sim.speed<=STOP_FT_S)].shape[0]/len(sim))
if __name__=='__main__':main()
