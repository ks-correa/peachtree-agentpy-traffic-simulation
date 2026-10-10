"""PEACHTREE-3S: directional receiving audit, no tuning or trajectory replay."""
import json
import numpy as np
import pandas as pd
from calibration.structural import full_b2
from calibration.structural_metrics import STOP_FT_S,stop_episodes
from simulation.training_data import ROOT,require_train,load_inputs,load_b2_source,read_train_csv
from simulation.signals import controllers_from_inputs

OUT=ROOT/'outputs/peachtree3s'
LAST={2:1168.9155,4:777.262}
EXIT={2:1400.,4:400.}
NEXT={2:4,4:1}
SIGNAL_NEXT={2:5,4:1}

def sign(direction):return 1 if direction==2 else -1
def region(y,direction):
    p=(np.asarray(y)-LAST[direction])*sign(direction)
    return np.where(p<=0,'CONTROLLED_REGION',np.where((np.asarray(y)-EXIT[direction])*sign(direction)<=0,'POST_CONTROL_REGION','BEYOND_CURRENT_EXIT'))

def bin_stops(d,width):
    rows=[]
    for direction,observed in d[d.downstream_ft.gt(0)].groupby('cohort_direction'):
        observed=observed.copy();observed['bin_start_ft']=np.floor(observed.downstream_ft/width)*width
        for start in np.arange(0,observed.bin_start_ft.max()+width,width):
            sample=observed[observed.bin_start_ft.eq(start)];q=sample[sample.speed.le(STOP_FT_S)]
            rows.append({'direction':direction,'bin_width_ft':width,'bin_start_ft':start,'bin_end_ft':start+width,'observed_frames':len(sample),
                'stopped_frames':len(q),'vehicles':q.id.nunique(),'vehicle_seconds':len(q)*.1,'density_vehicle_seconds_per_ft':len(q)*.1/width if len(sample) else np.nan})
    return pd.DataFrame(rows)

def crossing_events(d,cut,direction):
    rows=[]
    for key,q in d[d.cohort_direction.eq(direction)&d.direction.eq(direction)].sort_values(['id','frame']).groupby('id',sort=False):
        y=q.y.to_numpy()*sign(direction);boundary=cut*sign(direction);hit=np.flatnonzero((y[:-1]<boundary)&(y[1:]>=boundary)&(np.diff(q.frame)==1))
        if len(hit):
            j=hit[0];t=q.time.iloc[j]+.1*(boundary-y[j])/(y[j+1]-y[j]);rows.append({'id':key,'direction':direction,'cut_ft':cut,'time':t})
    return pd.DataFrame(rows,columns=['id','direction','cut_ft','time'])

def next_mouths(full):
    rows=[]
    for _,q in full[full.direction.isin([2,4])].sort_values(['trajectory_key','frame_id']).groupby('trajectory_key',sort=False):
        previous=q.shift();hit=q.int_id.gt(0)&previous.int_id.eq(0)&q.direction.eq(previous.direction)&q.frame_id.sub(previous.frame_id).eq(1)
        for r in q[hit].itertuples():rows.append({'intersection':int(r.int_id),'direction':int(r.direction),'y_ft':r.local_y})
    d=pd.DataFrame(rows)
    return d.groupby(['intersection','direction']).y_ft.agg(['count','median','min','max']).reset_index()

def real_targets(full):
    base=load_b2_source();directions=base.groupby('trajectory_key').direction.first()
    d=full[full.trajectory_key.isin(directions.index)&full.t_relative.ge(93.4-1e-8)].copy()
    d=d.rename(columns={'trajectory_key':'id','frame_id':'frame','local_y':'y','lane_id':'lane','v_vel':'speed','v_acc':'acceleration','v_length':'length'})
    d['time']=d.t_relative-93.4;d['cohort_direction']=d.id.map(directions);d['downstream_ft']=(d.y-d.cohort_direction.map(LAST))*d.cohort_direction.map({2:1,4:-1})
    d['region']='CONTROLLED_REGION'
    for direction in [2,4]:
        mask=d.cohort_direction.eq(direction);d.loc[mask,'region']=region(d.loc[mask,'y'],direction)
    d['longitudinal_observation']=d.direction.eq(d.cohort_direction)
    d['intersection']=d.int_id;d['distance']=d.downstream_ft;d['phase']='NOT_ASSIGNED_TO_UNKNOWN_CONTROL'
    return d

def leaders(d,full,target_ids):
    q=d.reset_index(drop=True).copy();lookup=full.set_index(['frame_id','vehicle_id'],drop=False)
    l=lookup.reindex(pd.MultiIndex.from_arrays([q.frame,q.preceding])).reset_index(drop=True)
    dist=(l.local_y-q.y)*q.cohort_direction.map({2:1,4:-1});gap=dist-l.v_length
    valid=q.preceding.gt(0)&l.vehicle_id.notna()&l.direction.eq(q.direction)&l.lane_id.eq(q.lane)&l.section_id.eq(q.section_id)&dist.gt(0)&gap.gt(0)&q.longitudinal_observation
    ids='B2:'+l.vehicle_id.fillna(-1).astype(int).astype(str)
    # Categories exclusive; turning precedes non-target class23.
    category=np.where(~valid,'E_UNKNOWN_UNUSABLE',np.where(ids.isin(target_ids),'A_TARGET_THROUGH',np.where(l.movement.isin([2,3]),'C_TURNING',np.where(l.direction.isin([1,3]),'D_CROSS_LOCAL',np.where(l.v_class.isin([2,3]),'B_CLASS23_NON_TARGET','E_UNKNOWN_UNUSABLE')))))
    q['leader_category']=category;q['leader_valid']=valid;q['leader_speed']=l.v_vel;q['leader_y']=l.local_y;q['leader_distance_ft']=dist;q['leader_key']=np.where(valid,ids,'');q['gap_ft']=np.where(valid,gap,np.nan)
    q['leader_stopped']=valid&l.v_vel.le(STOP_FT_S)
    return q

def block_episodes(frame_data):
    """Necessary observed conditions; not proof of a particular capacity law."""
    rows=[]
    for direction,q in frame_data.groupby('direction'):
        q=q.sort_values('tick');mask=q.upstream_stopped.gt(0)&q.downstream_stopped.gt(0)&q.last_control_phase.eq('GREEN')&q.crossings.eq(0)
        start=None
        for i,(tick,yes) in enumerate(zip(q.tick,mask)):
            if yes and start is None:start=i
            end=not yes or i==len(q)-1 or (i+1<len(q) and q.tick.iloc[i+1]!=tick+1)
            if start is not None and end:
                stop=i if yes else i-1;z=q.iloc[start:stop+1]
                if len(z):rows.append({'direction':direction,'start_s':z.time.iloc[0],'end_s':z.time.iloc[-1]+.1,'duration_s':len(z)*.1,
                    'upstream_stopped_mean':z.upstream_stopped.mean(),'downstream_stopped_mean':z.downstream_stopped.mean(),'downstream_occupancy_mean':z.downstream_occupancy.mean(),
                    'definition':'GREEN last control + stopped targets upstream of exit + observed stopped class23 arterial downstream + no crossing during contiguous0.1s ticks',
                    'interpretation':'OBSERVED_RECEIVING_BLOCK_CANDIDATE, not identified service capacity/priority law'})
                start=None
    return pd.DataFrame(rows,columns=['direction','start_s','end_s','duration_s','upstream_stopped_mean','downstream_stopped_mean','downstream_occupancy_mean','definition','interpretation'])

def audit(acquisition='B2'):
    require_train(acquisition);OUT.mkdir(parents=True,exist_ok=True);full=full_b2();inputs=load_inputs();bank=controllers_from_inputs(inputs)
    all_signals=read_train_csv(ROOT/'outputs/peachtree_signal_timeline.csv');all_signals=all_signals[all_signals.phase.eq('Thru')&all_signals.direction.isin(['2','4'])].copy()
    signal_inputs=dict(inputs,signals=all_signals.to_dict('records'));all_bank=controllers_from_inputs(signal_inputs)
    mouths=next_mouths(full);mouths.to_csv(OUT/'b2_intersection_entry_mouths.csv',index=False)
    extents=full[full.int_id.gt(0)].groupby('int_id').local_y.agg(['min','max']);extents.to_csv(OUT/'b2_intersection_extents.csv')
    geometry=[]
    for direction in [2,4]:
        inter=NEXT[direction];mouth=mouths[(mouths.intersection==inter)&(mouths.direction==direction)].iloc[0]['median']
        before=4 if direction==2 else 2;after=5 if direction==2 else 1
        lane_before=sorted(full[(full.section_id==before)&(full.direction==direction)&full.lane_id.isin([1,2,3])].lane_id.unique().tolist());lane_after=sorted(full[(full.section_id==after)&(full.direction==direction)&full.lane_id.isin([1,2,3])].lane_id.unique().tolist())
        geometry.append({'direction':direction,'last_control_intersection':3 if direction==2 else 2,'last_stopline_ft':LAST[direction],
            'current_exit':EXIT[direction],'last_control_to_exit_ft':abs(EXIT[direction]-LAST[direction]),'next_section':before,'section_after_next_intersection':after,
            'next_intersection':inter,'next_street':'13th' if direction==2 else '10th','control_type':'STOP_INTERSECTION_APPROACH_PRIORITY_UNASSIGNED' if direction==2 else 'SIGNAL_51',
            'next_control_mouth_B2_ft':mouth,'lane_count_before':len(lane_before),'lane_count_after':len(lane_after),'lane_labels_before':str(lane_before),'lane_labels_after':str(lane_after),
            'distance_ft':abs(mouth-EXIT[direction]),'next_signal_intersection':SIGNAL_NEXT[direction],
            'evidence_source':'B2 annotation transitions + official afternoon report Fig4,p11 and control description,p10; GIS camera polygons not lane geometry; DWG available not decoded',
            'confidence':'HIGH_PHYSICAL_LOCATION; CONTROL_DIRECTION_PRIORITY_PARTIAL' if direction==2 else 'HIGH_LOCATION_AND_RECORDED_SIGNAL'})
    pd.DataFrame(geometry).to_csv(OUT/'downstream_geometry.csv',index=False)
    d=real_targets(full);d=leaders(d,full,set(load_b2_source().trajectory_key));d.to_parquet(OUT/'target_full_downstream_observations.parquet',index=False)
    # Retain episode trajectory endpoints and source termination context.
    ep=stop_episodes(d[d.longitudinal_observation]);ep['onset_y_ft']=ep.direction.map(LAST)+ep.distance_ft*ep.direction.map({2:1,4:-1})
    lookup=d.set_index(['id','time'])
    rows=[]
    for e in ep.itertuples():
        if e.distance_ft<=0:continue
        q=d[d.id.eq(e.id)];at=q.iloc[np.argmin(abs(q.time-e.start_time))];last=q.iloc[np.argmin(abs(q.time-(e.end_time-.1)))];release=q[q.time.ge(e.end_time-1e-7)]
        end=q.iloc[-1];has_release=not e.right_censored
        rows.append({**e._asdict(),'release_y_ft':release.y.iloc[0] if has_release and len(release) else np.nan,'end_y_ft':last.y,
            'section_id':at.section_id,'int_id':at.int_id,'lane':at.lane,'movement':at.movement,'origin':at.o_zone,'destination':at.d_zone,
            'onset_region':at.region,'leader_key':at.leader_key,'leader_category':at.leader_category,'leader_stopped':at.leader_stopped,
            'leader_distance_ft':at.leader_distance_ft,'leader_speed_ft_s':at.leader_speed,
            'track_termination_time_s':end.time,'track_termination_y_ft':end.y,
            'observation_class':'OBSERVED_PHYSICAL_STOP_AND_RELEASE' if has_release else 'STOP_WITH_RIGHT_CENSORED_TRACK_OR_WINDOW_END',
            'time_since_last_control_s':np.nan})
    episodes=pd.DataFrame(rows);episodes.to_csv(OUT/'post_control_stops.csv',index=False)
    # Last-control passage time only when physically crossed in this acquisition window.
    passages=pd.concat([crossing_events(d,LAST[di],di) for di in [2,4]])
    passage_time=passages.set_index('id').time;d['time_since_last_control_s']=d.time-d.id.map(passage_time)
    d.to_parquet(OUT/'target_full_downstream_observations.parquet',index=False)
    episodes['time_since_last_control_s']=episodes.start_time-episodes.id.map(passage_time);episodes.to_csv(OUT/'post_control_stops.csv',index=False)
    hist=pd.concat([bin_stops(d[d.longitudinal_observation],w) for w in [10.,25.,50.]]);hist.to_csv(OUT/'post_control_spatial_bins.csv',index=False)
    clusters=[]
    # Reproducible histogram groupings; no automatic intersection inference.
    for di in [2,4]:
        z=episodes[episodes.direction.eq(di)].copy();z['onset_bin25_ft']=np.floor(z.distance_ft/25)*25
        for b,q in z.groupby('onset_bin25_ft'):
            center=q.onset_y_ft.median();near=mouths[mouths.direction.eq(di)].copy();near['distance']=abs(near['median']-center);n=near.sort_values('distance').iloc[0]
            match=n.distance<=25
            clusters.append({'direction':di,'center_ft':center,'distance_after_last_control_ft':q.distance_ft.median(),'spread_P25_ft':q.onset_y_ft.quantile(.25),'spread_P75_ft':q.onset_y_ft.quantile(.75),
                'vehicles':q.id.nunique(),'episodes':len(q),'associated_section':int(q.section_id.mode().iloc[0]),'associated_intersection':int(q.int_id.mode().iloc[0]),
                'known_control_nearby':int(n.intersection) if match else None,'classification':'PHYSICAL_CONTROL_MATCH' if match else 'UNKNOWN_RECEIVING_CONSTRAINT',
                'note':'25ft histogram grouping, descriptive not physical intersection discovery; sensitivity10/25/50 exported'})
    pd.DataFrame(clusters).to_csv(OUT/'post_control_stop_clusters.csv',index=False)
    rows=[];shares=[]
    for di in [2,4]:
        for reg in ['CONTROLLED_REGION','POST_CONTROL_REGION','BEYOND_CURRENT_EXIT']:
            q=d[d.cohort_direction.eq(di)&d.region.eq(reg)&d.longitudinal_observation].copy();valid=q[q.leader_valid]
            if reg=='CONTROLLED_REGION':q=q[q.y.between(400,1400)];valid=q[q.leader_valid]
            for subset,z in [('ALL_VALID_FOLLOWING',valid),('OPERATIONAL_STOPPED_VALID_FOLLOWING',valid[valid.speed.le(STOP_FT_S)]),('ALL_STOPPED_INCLUDING_UNUSABLE',q[q.speed.le(STOP_FT_S)])]:
                for cat in ['A_TARGET_THROUGH','B_CLASS23_NON_TARGET','C_TURNING','D_CROSS_LOCAL','E_UNKNOWN_UNUSABLE']:
                    x=z[z.leader_category==cat];rows.append({'direction':di,'region':reg,'subset':subset,'category':cat,'frames':len(x),'denominator':len(z),'fraction':len(x)/len(z) if len(z) else np.nan,
                        'vehicles':x.id.nunique(),'interaction_vehicle_seconds':len(x)*.1,'leader_distance_median_ft':x.leader_distance_ft.median(),'leader_speed_median_ft_s':x.leader_speed.median(),
                        'fraction_leader_operationally_stopped':x.leader_stopped.mean() if len(x) else np.nan})
            shares.append({'direction':di,'region':reg,'valid_following_frames':len(valid),'omitted_leader_share':valid.leader_category.ne('A_TARGET_THROUGH').mean() if len(valid) else np.nan,
                'stopped_frames':q.speed.le(STOP_FT_S).sum(),'vehicles_stopped':q[q.speed.le(STOP_FT_S)].id.nunique(),
                'stopped_with_valid_stopped_leader_fraction':q[q.speed.le(STOP_FT_S)].leader_stopped.mean() if q.speed.le(STOP_FT_S).any() else np.nan})
    pd.DataFrame(rows).to_csv(OUT/'post_control_leaders.csv',index=False);pd.DataFrame(shares).to_csv(OUT/'background_share_by_region.csv',index=False)
    # Receiving flow and necessary blocking conditions from simultaneously observed data.
    capacity=[];frame_rows=[];exit_events=[]
    allroad=full[full.direction.isin([2,4])&full.v_class.isin([2,3])&full.t_relative.ge(93.4)].copy();allroad['tick']=np.rint((allroad.t_relative-93.4)/.1).astype(int)
    for di in [2,4]:
        crossings=crossing_events(d,EXIT[di],di);exit_events.append(crossings)
        for width in [5.,10.,30.,60.]:
            edges=np.r_[np.arange(0,inputs['horizon_s'],width),inputs['horizon_s']+1e-7];counts=np.histogram(crossings.time,edges)[0]
            for start,end,count in zip(edges[:-1],edges[1:],counts):capacity.append({'direction':di,'bin_s':width,'start_s':start,'end_s':end,'crossings':count,'observed_flow_veh_h':count*3600/(end-start),'interpretation':'Observed demand-conditioned discharge, not identified capacity'})
        target=d[d.cohort_direction.eq(di)&d.longitudinal_observation];near=(target.y-EXIT[di])*sign(di)
        up=target[near.between(-100,0)].copy();up['tick']=np.rint(up.time/.1).astype(int);up['stop']=up.speed.le(STOP_FT_S)
        down=allroad[allroad.direction.eq(di)&((allroad.local_y-EXIT[di])*sign(di)).between(0,200)].copy();down['stop']=down.v_vel.le(STOP_FT_S)
        u=up.groupby('tick').stop.agg(['sum','size']);v=down.groupby('tick').stop.agg(['sum','size']);events=np.floor(crossings.time/.1+1e-7).astype(int).value_counts()
        ctrl=bank[(3 if di==2 else 2,di)]
        for tick in range(round(inputs['horizon_s']/.1)+1):
            frame_rows.append({'direction':di,'tick':tick,'time':tick*.1,'upstream_stopped':u.loc[tick,'sum'] if tick in u.index else 0,
                'upstream_occupancy':u.loc[tick,'size'] if tick in u.index else 0,'downstream_stopped':v.loc[tick,'sum'] if tick in v.index else 0,
                'downstream_occupancy':v.loc[tick,'size'] if tick in v.index else 0,'last_control_phase':ctrl.at(tick*.1),'crossings':events.get(tick,0)})
    frame=pd.DataFrame(frame_rows);frame.to_csv(OUT/'receiving_frame_audit.csv',index=False);block_episodes(frame).to_csv(OUT/'receiving_block_episodes.csv',index=False)
    pd.DataFrame(capacity).to_csv(OUT/'receiving_capacity.csv',index=False);pd.concat(exit_events).to_csv(OUT/'current_boundary_crossings.csv',index=False)
    control=[]
    for di,inter in [(4,1),(2,4),(2,5)]:
        controller=all_bank.get((inter,di));mouth=mouths[(mouths.intersection==inter)&(mouths.direction==di)].iloc[0]['median']
        control.append({'direction':di,'intersection':inter,'street':{1:'10th',4:'13th',5:'14th'}[inter],'mouth_B2_ft':mouth,
            'control_type':'STOP_INTERSECTION' if inter==4 else 'SIGNAL','observability':'KNOWN_BUT_UNPARAMETERIZED' if inter==4 else 'PARTIALLY_OBSERVED',
            'signal_schedule_available':controller is not None,'unknown_clock_ticks':sum(controller.at(t*.1)=='UNKNOWN' for t in range(round(inputs['horizon_s']/.1)+1)) if controller else None,
            'priority_identified':False if inter==4 else None,'essential_gap_acceptance_identified':False if inter==4 else None,
            'evidence':'Official B2 report: intersection4 STOP; signalTXT for10thSB/14thNB. Fig4 does not assign arterial approach priority/conflicts. Schedules alone do not identify receiving supply.'})
    pd.DataFrame(control).to_csv(OUT/'next_control_audit.csv',index=False)
    # Local track endpoints and real observation artifacts are separated, not discarded.
    no_leader=d[d.downstream_ft.gt(0)&d.speed.le(STOP_FT_S)&~d.leader_stopped].copy()
    endings=d.groupby('id').time.max();no_leader['seconds_to_track_end']=no_leader.id.map(endings)-no_leader.time
    no_leader.groupby(['cohort_direction','region','section_id','int_id','lane','movement']).agg(frames=('id','size'),vehicles=('id','nunique'),median_time_to_track_end_s=('seconds_to_track_end','median')).reset_index().to_csv(OUT/'stops_without_stopped_leader.csv',index=False)
    # Exploratory scope cuts declared by physical geometry before any REAL/SIM fit.
    low=float(extents.loc[2,'min']);high=float(extents.loc[3,'max'])
    specs=[('FULL_CURRENT_SCOPE',400.,1400.,'Existing S2/S4 arbitrary mid-section cuts'),('EXTENDED_TO_NEXT_CONTROLS',100.,float(extents.loc[4,'max']+25),'Contains10th and13th; STOP priority/receiving supply unresolved')]
    for buffer in [25.,50.,100.]:specs.append((f'REDUCED_JUNCTION_ENVELOPE_PLUS_{int(buffer)}FT',low-buffer,high+buffer,'Observed full I2/I3 envelopes plus prespecified physical discharge buffer; no fit-based selection'))
    (OUT/'scope_candidate_plan.json').write_text(json.dumps({'B1_LOCKED':True,'basis':'Observed B2 intersection envelopes, buffers25/50/100ft. No SIM metrics inspected to select a boundary. Must keep both junctions plus downstream room and exclude unidentified interacting context, not merely its frames.',
        'specs':[{'name':n,'low_ft':lo,'high_ft':hi,'basis':why} for n,lo,hi,why in specs]},indent=2),encoding='utf-8')
    scope=[]
    for name,lo,hi,why in specs:
        cuts=pd.concat([crossing_events(d,lo,2).assign(event='ENTRY'),crossing_events(d,hi,2).assign(event='EXIT'),crossing_events(d,hi,4).assign(event='ENTRY'),crossing_events(d,lo,4).assign(event='EXIT')])
        pairs=cuts.pivot_table(index=['id','direction'],columns='event',values='time',aggfunc='first').dropna();pairs=pairs[pairs.EXIT>pairs.ENTRY]
        q=d[d.y.between(lo,hi)&d.longitudinal_observation];valid=q[q.leader_valid]
        scope.append({'candidate':name,'low_ft':lo,'high_ft':hi,'length_ft':hi-lo,'vehicles_observed':q.id.nunique(),'complete_route_vehicles':len(pairs),
            'mean_travel_time_s':(pairs.EXIT-pairs.ENTRY).mean(),'throughput_observed':cuts.event.eq('EXIT').sum(),'operational_stopped_fraction':q.speed.le(STOP_FT_S).mean(),
            'headway_observations':len(valid),'leader_available_fraction':q.leader_valid.mean(),'observation_rows':len(q),'keeps_11th_12th':lo<low and hi>high,
            'physical_interpretability':why,'receiving_observability':'UNKNOWN_FULL_SYSTEM_CLOSURE','scenario_relevance':'Both11th/12th retained, but unidentified receiving may affect their approaches'})
    pd.DataFrame(scope).to_csv(OUT/'scope_candidates.csv',index=False)
    print(pd.DataFrame(geometry).to_string(index=False));print(episodes.groupby(['direction','onset_region']).agg(episodes=('id','size'),vehicles=('id','nunique'),median_onset_y=('onset_y_ft','median'),median_duration_s=('duration_s','median')).to_string())
    print(pd.DataFrame(shares).to_string(index=False));print(pd.DataFrame(scope).to_string(index=False))
    return d,full,all_bank

if __name__=='__main__':audit()
