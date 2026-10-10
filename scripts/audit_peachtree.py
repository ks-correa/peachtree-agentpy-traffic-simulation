"""PEACHTREE-1: descriptive feasibility, never ABM calibration or TEST freeze.

Raw source stays untouched. Acquisition components are derived from the affine
frame/time relationship, because this API's epoch timestamps are inconsistent.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, wasserstein_distance

from scripts.evaluate_local import digest, peak_memory_mb

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/peachtree_full.csv'
OUT = ROOT/'outputs'
KEY = ['component','vehicle_id']
ROAD_LANES = {1,2,3,4,11}
METADATA_URL = 'https://data.transportation.gov/api/views/8ect-6jqj/files/8b5a833b-e286-467f-8c55-af45be37c8ab?download=true&filename=4-+Peachtree+Street+Metadata+Documentation.pdf'
AUX_URL = 'https://data.transportation.gov/api/views/8ect-6jqj/files/7244a8b5-077f-4851-bc06-3cfc7a75f0b0'


def save_csv(name, records):
    pd.DataFrame(records).to_csv(OUT/name,index=False)


def describe(x):
    x=pd.Series(x).replace([np.inf,-np.inf],np.nan).dropna()
    if x.empty:return {'n':0,'mean':None,'median':None,'p05':None,'p10':None,'p90':None,'p95':None,'min':None,'max':None,'std':None}
    return {'n':int(len(x)),'mean':float(x.mean()),'median':float(x.median()),
        **{f'p{int(q*100):02}':float(x.quantile(q)) for q in [.05,.1,.9,.95]},
        'min':float(x.min()),'max':float(x.max()),'std':float(x.std()) if len(x)>1 else None}


def detect_components(d):
    """Detect gaps first; then expose affine source components, not fake dates."""
    unique=np.sort(d.global_time.unique())
    steps=np.diff(unique)
    dominant=int(pd.Series(steps).mode().iloc[0])
    # A gap >10 acquisition ticks is only a diagnostic rule, not proof of period.
    big=steps>10*dominant
    offsets=d.global_time-d.frame_id*dominant
    origins=sorted(offsets.unique())
    result=d.copy()
    result['clock_origin_raw']=offsets
    result['component']=offsets.map({origin:f'B{i+1}' for i,origin in enumerate(origins)})
    result['relative_s']=result.frame_id*dominant/1000
    return result, {'dominant_global_step_raw':dominant,
        'large_gap_rule':'delta > 10 * dominant raw tick; diagnostic only',
        'large_gap_count':int(big.sum()),'timestamp_only_blocks':int(big.sum()+1),
        'affine_component_count':len(origins),'affine_origins_raw':[int(x) for x in origins],
        'calendar_labels_status':'UNCONFIRMED_FOR_LOCAL_ACQUISITION_COMPONENTS',
        'raw_epoch_status':'INCONSISTENT_WITH_DOCUMENTED_MILLISECONDS_AND_2006_COLLECTION',
        'seconds_conversion':'Within-component differences / 1000, supported by documented millisecond increments; no calendar correction',
        'expected_calendar_periods_from_metadata':['12:45-13:00','16:00-16:15'],
        'assignment_method':'component = unique(global_time - dominant_tick * frame_id)'}


def trajectory_table(d):
    s=d.sort_values(KEY+['frame_id','global_time'],kind='stable').reset_index(drop=True)
    g=s.groupby(KEY,sort=False)
    delta=g.global_time.diff(); frame_delta=g.frame_id.diff()
    s['delta_raw']=delta; s['frame_delta']=frame_delta
    s['step_distance_ft']=np.hypot(g.global_x.diff(),g.global_y.diff())
    s['y_step_ft']=g.local_y.diff()
    t=g.agg(observations=('vehicle_id','size'),first_frame=('frame_id','first'),
        last_frame=('frame_id','last'),first_time_raw=('global_time','first'),last_time_raw=('global_time','last'),
        declared_frames=('total_frames','first'),declared_variants=('total_frames','nunique'),
        first_x=('local_x','first'),last_x=('local_x','last'),first_y=('local_y','first'),last_y=('local_y','last'),
        first_speed=('v_vel','first'),last_speed=('v_vel','last'),first_lane=('lane_id','first'),last_lane=('lane_id','last'),
        vehicle_class=('v_class','first'),length_ft=('v_length','first'),width_ft=('v_width','first'),
        origin=('o_zone','first'),destination=('d_zone','first'),initial_direction=('direction','first'),
        movement=('movement','first'),distance_polyline_ft=('step_distance_ft','sum'),
        max_position_step_ft=('step_distance_ft','max'))
    t['duration_s']=(t.last_time_raw-t.first_time_raw)/1000
    t['source_frames_complete']=t.observations.eq(t.declared_frames)&t.declared_variants.eq(1)
    gaps=s.assign(gap=s.frame_delta.gt(1)).groupby(KEY).gap.any()
    t['has_gap']=gaps
    bounds=d.groupby('component').frame_id.agg(['min','max'])
    t=t.reset_index()
    t['at_acquisition_boundary']=[a<=bounds.loc[c,'min'] or b>=bounds.loc[c,'max'] for c,a,b in zip(t.component,t.first_frame,t.last_frame)]
    t['valid_od']=t.origin.between(101,123)&t.destination.between(201,223)
    t['observed_journey_candidate']=t.source_frames_complete&~t.has_gap&~t.at_acquisition_boundary&t.valid_od&t.duration_s.gt(0)
    t['polyline_mean_speed_ft_s']=t.distance_polyline_ft/t.duration_s.replace(0,np.nan)
    return s,t


def lane_events(s):
    g=s.groupby(KEY,sort=False)
    previous=g.lane_id.shift(); future=g.lane_id.shift(-1)
    contiguous=s.frame_delta.eq(1)
    next_contiguous=g.frame_id.shift(-1).sub(s.frame_id).eq(1)
    raw=contiguous&previous.notna()&s.lane_id.ne(previous)
    # Mark both transitions of an A -> B -> A consecutive-frame excursion.
    excursion=raw&next_contiguous&future.eq(previous)
    bad=excursion|excursion.groupby([s.component,s.vehicle_id]).shift(fill_value=False)
    stable_context=s.section_id.eq(g.section_id.shift())&s.direction.eq(g.direction.shift())&s.int_id.eq(0)&g.int_id.shift().eq(0)
    road=raw&stable_context&s.lane_id.isin(ROAD_LANES)&previous.isin(ROAD_LANES)
    nonadjacent_main=road&s.lane_id.between(1,4)&previous.between(1,4)&s.lane_id.sub(previous).abs().gt(1)
    semantic=road&~bad&~nonadjacent_main
    # Lane label runs provide sensitivity summaries, not maneuver duration.
    runs=s.lane_id.ne(previous).groupby([s.component,s.vehicle_id]).cumsum()
    run_end=s.groupby([s.component,s.vehicle_id,runs]).frame_id.transform('max')
    remaining=(run_end-s.frame_id+1)*.1
    events=s.loc[raw,['component','vehicle_id','frame_id','relative_s','v_vel','space_headway','time_headway','lane_id','section_id','int_id','direction']].copy()
    events['origin_lane']=previous.loc[raw].astype(int)
    events['destination_lane']=events.lane_id
    before_headway=g.space_headway.shift()
    before_preceding=g.preceding.shift()
    events['headway_before_ft_raw']=before_headway.loc[raw]
    events['headway_after_ft_raw']=events.space_headway
    events['preceding_before']=before_preceding.loc[raw]
    events['preceding_after']=s.preceding.loc[raw]
    events['headway_before_ft']=before_headway.where(before_preceding.gt(0)&before_headway.gt(0)).loc[raw]
    events['headway_after_ft']=events.space_headway.where(events.preceding_after.gt(0)&events.space_headway.gt(0))
    events['one_frame_excursion_transition']=bad.loc[raw]
    events['comparable_road_context']=road.loc[raw]
    events['nonadjacent_main_lane_transition']=nonadjacent_main.loc[raw]
    events['semantic_candidate']=semantic.loc[raw]
    events['destination_label_persistence_s']=remaining.loc[raw]
    events['main_lane_candidate']=events.semantic_candidate&events.origin_lane.between(1,4)&events.destination_lane.between(1,4)
    summaries=[]
    for c,q in s.groupby('component'):
        e=events[events.component==c]; usable=e[e.semantic_candidate]
        rates=usable.groupby('vehicle_id').size().reindex(q.vehicle_id.unique(),fill_value=0)
        summaries.append({'component':c,'raw_label_transitions':len(e),
            'one_frame_excursion_transitions':int(e.one_frame_excursion_transition.sum()),
            'comparable_road_transitions_before_excursion_filter':int(e.comparable_road_context.sum()),
            'nonadjacent_main_lane_transitions':int(e.nonadjacent_main_lane_transition.sum()),
            'semantic_candidates_including_turn_bay':len(usable),'main_lane_candidates':int(e.main_lane_candidate.sum()),
            'vehicles_with_semantic_candidate':usable.vehicle_id.nunique(),'all_vehicles':q.vehicle_id.nunique(),
            'semantic_changes_per_vehicle_mean':rates.mean(),'semantic_speed_mean_ft_s':usable.v_vel.mean(),
            'semantic_headway_before_mean_ft':usable.headway_before_ft.mean(),'semantic_headway_after_mean_ft':usable.headway_after_ft.mean(),
            'persistence_ge_0_3_s':int(usable.destination_label_persistence_s.ge(.3-1e-9).sum()),
            'persistence_ge_0_5_s':int(usable.destination_label_persistence_s.ge(.5-1e-9).sum()),
            'persistence_ge_1_s':int(usable.destination_label_persistence_s.ge(1-1e-9).sum()),
            'maneuver_duration_status':'NOT_IDENTIFIABLE_FROM_DISCRETE_LANE_LABEL_CHANGE'})
    return events,pd.DataFrame(summaries)


def join_relations(d):
    """Unique acquisition component + frame + ID; never join on raw ID alone."""
    keys=['component','frame_id','vehicle_id']
    if d.duplicated(keys).any():raise ValueError('Ambiguous leader/follower join keys')
    indexed=d.set_index(keys)
    arrays=[d.component,d.frame_id]
    leader=indexed.reindex(pd.MultiIndex.from_arrays(arrays+[d.preceding])).reset_index(drop=True)
    follower=indexed.reindex(pd.MultiIndex.from_arrays(arrays+[d.following])).reset_index(drop=True)
    ego=d.reset_index(drop=True).copy()
    ego['leader_valid']=ego.preceding.ne(0)&leader.v_vel.notna()
    ego['follower_valid']=ego.following.ne(0)&follower.v_vel.notna()
    ego['leader_reciprocal']=ego.leader_valid&leader.following.eq(ego.vehicle_id)
    ego['follower_reciprocal']=ego.follower_valid&follower.preceding.eq(ego.vehicle_id)
    ego['leader_same_lane']=ego.leader_valid&leader.lane_id.eq(ego.lane_id)
    ego['leader_same_context']=ego.leader_same_lane&leader.direction.eq(ego.direction)&leader.section_id.eq(ego.section_id)&ego.section_id.ne(0)&ego.int_id.eq(0)&leader.int_id.eq(0)
    ego['leader_speed']=leader.v_vel
    ego['relative_speed']=leader.v_vel-ego.v_vel
    ego['bumper_gap_ft']=ego.space_headway-leader.v_length
    ego['car_following_usable']=ego.leader_same_context&ego.lane_id.isin(ROAD_LANES)&ego.space_headway.gt(0)&ego.bumper_gap_ft.gt(0)
    ego['finite_time_headway_usable']=ego.car_following_usable&ego.v_vel.gt(0)&ego.time_headway.gt(0)&ego.time_headway.lt(9999.99)
    ego['headway_position_abs_error_ft']=(np.abs(leader.local_y-ego.local_y)-ego.space_headway).abs()
    return ego


def following_summaries(relations):
    summaries=[]; correlations=[]; bins=[]
    for component,q in relations.groupby('component'):
        n=len(q);valid=q.leader_valid.sum();fvalid=q.follower_valid.sum()
        summaries.append({'component':component,'rows':n,'preceding_nonzero':int(q.preceding.ne(0).sum()),
            'following_nonzero':int(q.following.ne(0).sum()),'valid_leader_rows':int(valid),'valid_follower_rows':int(fvalid),
            'valid_leader_pct':100*valid/n,'valid_follower_pct':100*fvalid/n,
            'leader_missing_same_frame':int((q.preceding.ne(0)&~q.leader_valid).sum()),
            'follower_missing_same_frame':int((q.following.ne(0)&~q.follower_valid).sum()),
            'leader_reciprocity_pct_conditional':100*q.leader_reciprocal.sum()/valid if valid else np.nan,
            'follower_reciprocity_pct_conditional':100*q.follower_reciprocal.sum()/fvalid if fvalid else np.nan,
            'same_lane_leader_rows':int(q.leader_same_lane.sum()),'same_road_context_leader_rows':int(q.leader_same_context.sum()),
            'usable_car_following_rows':int(q.car_following_usable.sum()),'usable_car_following_pct':100*q.car_following_usable.mean(),
            'finite_time_headway_rows':int(q.finite_time_headway_usable.sum())})
        for sample,selection in [('same_frame_leader',q.leader_valid),('same_road_positive_gap',q.car_following_usable)]:
            z=q[selection]
            for variable in ['relative_speed','space_headway','bumper_gap_ft','v_vel']:
                correlations.append({'component':component,'sample':sample,'x':variable,'y':'v_acc','n':len(z),
                    'pearson':z[variable].corr(z.v_acc,method='pearson'),'spearman':z[variable].corr(z.v_acc,method='spearman'),
                    'interpretation':'Descriptive repeated observations; no independent-sample p-values or causal identification'})
        z=q[q.car_following_usable]
        for var,edges in [('space_headway',[0,20,40,60,100,200,400,np.inf]),
                          ('relative_speed',[-np.inf,-20,-10,-5,-1,1,5,10,20,np.inf])]:
            cats=pd.cut(z[var],edges,right=False)
            for label,section in z.groupby(cats,observed=True):
                bins.append({'component':component,'variable':var,'bin':str(label),'n':len(section),
                    'acceleration_mean_ft_s2':section.v_acc.mean(),'acceleration_median_ft_s2':section.v_acc.median(),
                    'acceleration_std_ft_s2':section.v_acc.std(),'ego_speed_mean_ft_s':section.v_vel.mean()})
    return pd.DataFrame(summaries),pd.DataFrame(correlations),pd.DataFrame(bins)


def quality(d,s,t,relations):
    records=[]
    for component,q in s.groupby('component'):
        v=t[t.component==component];r=relations[relations.component==component]
        g=q.groupby('vehicle_id');y=q.y_step_ft
        wrong_y=((q.direction.eq(2)&y.lt(0))|(q.direction.eq(4)&y.gt(0)))&q.section_id.ne(0)&q.int_id.eq(0)&q.frame_delta.eq(1)
        stable_dir=q.direction.eq(g.direction.shift())&q.section_id.eq(g.section_id.shift())
        extreme_cut=float(q.v_acc.abs().quantile(.99))
        vals={'rows':len(q),'vehicles':q.vehicle_id.nunique(),'exact_duplicate_rows':int(q.duplicated(list(d.columns[:25])).sum()),
            'vehicle_frame_duplicate_excess':int(q.duplicated(['vehicle_id','frame_id']).sum()),
            'vehicle_time_duplicate_excess':int(q.duplicated(['vehicle_id','global_time']).sum()),
            'nonpositive_time_intervals_after_sort':int(q.delta_raw.le(0).sum()),'nonmonotonic_source_order_intervals':int(d[d.component==component].groupby('vehicle_id').global_time.diff().le(0).sum()),
            'frame_gaps':int(q.frame_delta.gt(1).sum()),'vehicles_with_gaps':int(v.has_gap.sum()),'vehicles_with_gaps_pct':100*v.has_gap.mean(),
            'missing_local_x':int(q.local_x.isna().sum()),'missing_local_y':int(q.local_y.isna().sum()),
            'negative_speed_rows':int(q.v_vel.lt(0).sum()),'negative_space_headway_rows':int(q.space_headway.lt(0).sum()),
            'negative_time_headway_rows':int(q.time_headway.lt(0).sum()),
            'acceleration_abs_p99_ft_s2':extreme_cut,'acceleration_at_abs_limit_12_27_rows':int(np.isclose(q.v_acc.abs(),12.27).sum()),
            'acceleration_negative_rows':int(q.v_acc.lt(0).sum()),'unexpected_lane_undocumented_nonzero_rows':int((~q.lane_id.isin(ROAD_LANES|{0})).sum()),
            'lane_zero_rows':int(q.lane_id.eq(0).sum()),'lane_9999_rows':int(q.lane_id.eq(9999).sum()),
            'same_context_main_lane_jump_gt1_rows':int((q.frame_delta.eq(1)&q.lane_id.between(1,4)&g.lane_id.shift().between(1,4)&q.lane_id.sub(g.lane_id.shift()).abs().gt(1)&stable_dir&q.int_id.eq(0)).sum()),
            'wrong_direction_y_step_rows':int((wrong_y&stable_dir).sum()),
            'wrong_direction_y_step_gt1ft_rows':int((wrong_y&stable_dir&y.abs().gt(1)).sum()),
            'position_step_distance_p99_ft':float(q.step_distance_ft.quantile(.99)),
            'position_step_distance_max_ft':float(q.step_distance_ft.max()),
            'position_step_gt20ft_rows':int(q.step_distance_ft.gt(20).sum()),
            'position_step_gt50ft_rows':int(q.step_distance_ft.gt(50).sum()),
            'trajectories_with_position_step_gt20ft':int(v.max_position_step_ft.gt(20).sum()),
            'within_vehicle_dimension_variant_count':int(g.v_length.nunique().gt(1).sum()),
            'declared_frame_complete_vehicles':int(v.source_frames_complete.sum()),
            'journey_candidate_vehicles':int(v.observed_journey_candidate.sum()),
            'boundary_censored_vehicles':int(v.at_acquisition_boundary.sum()),
            'median_observations_per_vehicle':float(v.observations.median()),
            'mean_duration_s':float(v.duration_s.mean()),'median_duration_s':float(v.duration_s.median()),
            'duration_lt5s_vehicles':int(v.duration_s.lt(5).sum()),
            'missing_preceding_same_frame':int((r.preceding.ne(0)&~r.leader_valid).sum()),
            'missing_following_same_frame':int((r.following.ne(0)&~r.follower_valid).sum()),
            'time_headway_sentinel_9999_99_rows':int(np.isclose(q.time_headway,9999.99).sum()),
            'time_headway_above_sentinel_rows':int(q.time_headway.gt(9999.99).sum()),
            'same_road_headway_position_error_median_ft':float(r.loc[r.car_following_usable,'headway_position_abs_error_ft'].median())}
        records.extend({'component':component,'metric':key,'value':value} for key,value in vals.items())
        dt=q.delta_raw.dropna()/1000
        records.extend({'component':component,'metric':'delta_t_s_'+key,'value':value} for key,value in describe(dt).items())
        records.append({'component':component,'metric':'delta_t_dominant_pct','value':100*dt.eq(dt.mode().iloc[0]).mean()})
    return pd.DataFrame(records)


def traffic_windows(d,t,events):
    rows=[];arrivals=[]
    for component,q in d.groupby('component'):
        zero=q.relative_s.min(); q=q.assign(elapsed_s=q.relative_s-zero)
        tr=t[t.component==component].copy();tr['first_elapsed_s']=tr.first_frame*.1-zero
        e=events[(events.component==component)&events.semantic_candidate].copy();e['elapsed_s']=e.relative_s-zero
        for width in [10,30,60]:
            a=tr.assign(window=(tr.first_elapsed_s//width).astype(int)*width)
            for (start,origin,lane),a0 in a.groupby(['window','origin','first_lane']):
                arrivals.append({'component':component,'window_s':width,'start_s':int(start),'origin':int(origin),'entry_lane':int(lane),'first_observations':len(a0),'boundary_censored_first':int(a0.at_acquisition_boundary.sum()),'interpretation':'Tracking entries; not verified boundary demand'})
            if width==10:continue
            frame_counts=q.groupby('frame_id').size()
            for start,z in q.groupby((q.elapsed_s//width).astype(int)*width):
                active=frame_counts.reindex(z.frame_id.unique())
                positive_hw=z.loc[z.preceding.ne(0)&z.space_headway.gt(0),'space_headway']
                arrivals0=tr.first_elapsed_s.ge(start)&tr.first_elapsed_s.lt(start+width)
                end_elapsed=tr.last_frame*.1-zero
                exits=end_elapsed.ge(start)&end_elapsed.lt(start+width)
                lc=e.elapsed_s.ge(start)&e.elapsed_s.lt(start+width)
                rows.append({'component':component,'window_s':width,'start_s':int(start),'end_s':float(min(start+width,q.elapsed_s.max()+.1)),
                    'observed_frames':z.frame_id.nunique(),'rows':len(z),'active_vehicles_per_frame_mean':active.mean(),'active_vehicles_per_frame_max':active.max(),
                    'unique_vehicles_in_window':z.vehicle_id.nunique(),'mean_speed_ft_s':z.v_vel.mean(),'median_speed_ft_s':z.v_vel.median(),
                    'p10_speed_ft_s':z.v_vel.quantile(.1),'p90_speed_ft_s':z.v_vel.quantile(.9),
                    'positive_referenced_headway_mean_ft':positive_hw.mean(),'positive_referenced_headway_median_ft':positive_hw.median(),
                    'negative_acceleration_fraction':z.v_acc.lt(0).mean(),'exactly_stopped_fraction':z.v_vel.eq(0).mean(),
                    'creeping_le_1ft_s_fraction':z.v_vel.le(1).mean(),'semantic_lane_changes':int(lc.sum()),
                    'first_observations':int(arrivals0.sum()),'last_observations':int(exits.sum()),
                    'density_status':'NOT_ESTIMATED_WITHOUT_MEASURED_NETWORK_LENGTH_LANE_COVERAGE',
                    'boundary_flow_status':'FIRST_LAST_OBSERVATION_PROXY_ONLY'})
    return pd.DataFrame(rows),pd.DataFrame(arrivals)


def transfer(a,b,label):
    a=pd.Series(a).dropna();b=pd.Series(b).dropna()
    if a.empty or b.empty:return {'indicator':label,'train_n':len(a),'test_n':len(b),'status':'NO_COMPARABLE_SAMPLES'}
    return {'indicator':label,'train_n':len(a),'test_n':len(b),'difference_mean_test_minus_train':b.mean()-a.mean(),
        'difference_median_test_minus_train':b.median()-a.median(),
        'ks_statistic':ks_2samp(a,b,method='asymp').statistic,'wasserstein_distance':wasserstein_distance(a,b),
        'train_mean':a.mean(),'test_mean':b.mean(),'train_median':a.median(),'test_median':b.median(),
        'train_component':'B2','test_component':'B1','status':'PREMODEL_DESCRIPTIVE_ONLY_NO_ACCEPTANCE_THRESHOLD'}


def compare_periods(d,t,rel,events,lane_summary):
    rows=[];transfer_rows=[];sample={}
    for component,q in d.groupby('component'):
        tr=t[t.component==component];r=rel[rel.component==component];lc=events[(events.component==component)&events.semantic_candidate]
        usable=r[r.car_following_usable];finite=r[r.finite_time_headway_usable]
        v=tr[tr.observed_journey_candidate];n=q.vehicle_id.nunique()
        c_counts=tr.vehicle_class.value_counts(normalize=True)
        l_counts=lc.groupby('vehicle_id').size().reindex(tr.vehicle_id,fill_value=0).to_numpy()
        durations=tr.set_index('vehicle_id').duration_s
        lane_rate=pd.Series(l_counts,index=tr.vehicle_id)/durations.reindex(tr.vehicle_id).to_numpy()*60
        sample[component]={'speed':q.v_vel,'acceleration':q.v_acc,'space_headway':usable.space_headway,
            'time_headway':finite.time_headway,'observed_journey_time':v.duration_s,
            'lane_changes_per_vehicle':pd.Series(l_counts),'lane_change_frequency_per_observed_vehicle_min':lane_rate}
        stats={'component':component,'rows':len(q),'vehicles':n,'raw_start':q.global_time.min(),'raw_end':q.global_time.max(),
            'frame_min':q.frame_id.min(),'frame_max':q.frame_id.max(),'frames':q.frame_id.nunique(),
            'duration_s':(q.global_time.max()-q.global_time.min())/1000,
            'calendar_start':'UNCONFIRMED','calendar_end':'UNCONFIRMED','raw_clock_origin':q.clock_origin_raw.iloc[0],
            'lanes':','.join(map(str,sorted(q.lane_id.unique()))),'classes':','.join(map(str,sorted(q.v_class.unique()))),
            'active_vehicles_per_frame_mean':q.groupby('frame_id').size().mean(),'exactly_stopped_fraction':q.v_vel.eq(0).mean(),
            'creeping_le_1ft_s_fraction':q.v_vel.le(1).mean(),'negative_acceleration_fraction':q.v_acc.lt(0).mean(),
            'tracking_arrivals':n,'tracking_arrivals_per_min':60*n/((q.frame_id.max()-q.frame_id.min()+1)*.1),
            'travel_time_candidate_count':len(v),'travel_time_candidate_pct':100*len(v)/len(tr),
            'raw_lane_transitions':len(events[events.component==component]),'semantic_lane_candidates':len(lc),
            'movements_per_initial_vehicle':json.dumps(tr.movement.value_counts().to_dict()),
            'class_proportions_per_vehicle':json.dumps(c_counts.to_dict()),'density':'NOT_ESTIMATED'}
        for name,x in sample[component].items():
            for stat,value in describe(x).items():stats[f'{name}_{stat}']=value
        rows.append(stats)
    for name in sample['B1']:
        transfer_rows.append(transfer(sample['B2'][name],sample['B1'][name],name))
    a=t[t.component=='B2'].vehicle_class.value_counts(normalize=True)
    b=t[t.component=='B1'].vehicle_class.value_counts(normalize=True)
    total_variation=.5*sum(abs(a.get(c,0)-b.get(c,0)) for c in sorted(set(a.index)|set(b.index)))
    for cls in sorted(set(a.index)|set(b.index)):
        transfer_rows.append({'indicator':f'vehicle_class_{cls}_proportion','train_n':len(t[t.component=='B2']),
            'test_n':len(t[t.component=='B1']),'train_mean':a.get(cls,0),'test_mean':b.get(cls,0),
            'difference_mean_test_minus_train':b.get(cls,0)-a.get(cls,0),'ks_statistic':np.nan,'wasserstein_distance':np.nan,
            'categorical_total_variation':total_variation,'train_component':'B2','test_component':'B1',
            'status':'CATEGORICAL_PROPORTIONS_NOT_CONTINUOUS_CODES'})
    return pd.DataFrame(rows),pd.DataFrame(transfer_rows)


def signal_summary():
    folder=ROOT/'data/reference/auxiliary/signal-timing/signal-change/Original Text files'
    result=[]
    for path in sorted(folder.glob('*.txt')):
        z=pd.read_csv(path,sep='\t')
        values=z.stack().dropna()
        result.append({'file':path.name,'calendar_label':path.stem.split('_')[-1],
            'rows':len(z),'columns':','.join(z.columns),'min_event_frame':values.min(),'max_event_frame':values.max(),
            'missing_cells':int(z.isna().sum().sum()),'zero_event_fields':int(z.eq(0).sum().sum()),
            'sha256':digest(path),'synchronization_status':'NOT_VERIFIED_WITH_ACQUISITION_COMPONENTS'})
    return pd.DataFrame(result)


def parameter_candidates():
    rows=[]
    for parameter,kind,method,identifiability in [
        ('vehicle_class_proportions','DATASET_DERIVED','Per (component,ID), not row weighted','YES'),
        ('vehicle_dimensions','DATASET_DERIVED','Length/width distribution by class; check within-trajectory consistency','YES'),
        ('arrival_process','DATASET_DERIVED','First observations by O_Zone; remove boundary censoring and define modeled entrances','PARTIAL'),
        ('desired_free_speed','CALIBRATED','Free-flow candidate observations; signal constraints prevent direct desired-speed inference','PARTIAL'),
        ('acceleration_behavior','CALIBRATED','Conditional response with clipping/noise audit','PARTIAL'),
        ('braking_behavior','CALIBRATED','Conditional negative acceleration; censoring/clipping must be explicit','PARTIAL'),
        ('headway_behavior','DATASET_DERIVED','Valid same-context positive gaps; separate stopped and moving','YES'),
        ('response_to_leader','CALIBRATED','Use contemporaneous leader matches and evaluate time response on TRAIN only','PARTIAL'),
        ('relative_speed_response','CALIBRATED','Conditional acceleration vs leader_speed - ego_speed','PARTIAL'),
        ('lane_change_frequency','DATASET_DERIVED','Same direction/section regular labels; document excursions and pocket entries','PARTIAL'),
        ('lane_change_context','CALIBRATED','Pre-event gap/speed/route associations; no latent intention','PARTIAL'),
        ('movement_proportions','DATASET_DERIVED','Movement by approach and vehicle, accounting for direction changes','YES'),
        ('intersection_approach_behavior','CALIBRATED','Stopping/braking by approach conditional on correctly aligned signals','PENDING_SIGNAL_ALIGNMENT'),
        ('cognitive_reaction_time','ASSUMPTION','Not a column and not identifiable from headway','NO'),
        ('aggressiveness_perception_priority','ASSUMPTION','Latent attributes; avoid unless independently supported','NO'),
        ('lane_change_intention','ASSUMPTION','Not observed; use empirical conditional probabilities instead','NO'),
        ('intervention_compliance','EXPERIMENTAL','External evidence/ranges required','NO_BASELINE_ESTIMATE')]:
        rows.append({'parameter':parameter,'classification':kind,'source':'Candidate B2 TRAIN only after approved design',
            'method':method,'identifiable':identifiability,'status':'NO_PARAMETER_FITTED_IN_PEACHTREE1'})
    return rows


def validation_candidates():
    specs=[('observed_OD_journey_time','PRIMARY','s','Duration between observed O/D endpoints; route-stratified','ONLY_MATCHED_OD_FULL_TRACKING_AND_BOUNDARIES'),
        ('mean_speed','PRIMARY','ft/s','Time-weighted mean for the same direction/section/window','AVAILABLE'),
        ('speed_distribution','PRIMARY','ft/s','Distribution with same observation/exposure convention','AVAILABLE'),
        ('throughput','PRIMARY','vehicles/window','Count geometric downstream crossings, not last observations','PENDING_GEOMETRY_AND_BOUNDARY_RULES'),
        ('flow','PRIMARY','vehicles/window','Count a fixed section-crossing detector','PENDING_GEOMETRY_AND_BOUNDARY_RULES'),
        ('space_headway','PRIMARY','ft','Front-to-front distance to contemporaneous same-lane leader','AVAILABLE_WITH_CONTEXT_FILTER'),
        ('time_headway','PRIMARY','s','Moving ego distance/speed; sentinel separated','AVAILABLE_WITH_SENTINEL_FILTER'),
        ('lane_change_frequency','SECONDARY','events/vehicle-minute','Context-valid lane transitions/exposure','AVAILABLE_AFTER_EVENT_PROTOCOL'),
        ('acceleration','SECONDARY','ft/s^2','Reported acceleration distribution with clipping audit','AVAILABLE_WITH_LIMITATIONS'),
        ('active_vehicles','SECONDARY','vehicles','Count agents inside identical visibility boundary at frame','AVAILABLE_WITH_BOUNDARY_MATCH'),
        ('queue_congestion','SECONDARY','vehicles/ft/s','Stopped/creeping fraction now; connected spatial queues later','PROXY_AVAILABLE_QUEUE_NEEDS_GEOMETRY')]
    return [{'indicator':name,'classification':kind,'unit':unit,'definition':definition,'local_status':status,
        'from_train':'Compute only on approved TRAIN with fixed measurement protocol',
        'from_test':'Apply same frozen protocol to reserved acquisition component; never fit parameters',
        'from_agentpy':'Collect independent generated trajectories and apply same observational measurement; no historical replay'} for name,kind,unit,definition,status in specs]


def scenarios():
    return [
        {'scenario':'E1','intervention':'Advisory speed harmonization','experimental_variable':'Target speed/cap and equipped/compliant fraction',
         'changed_rule':'Free-motion speed target; preserve compulsory stops/turns','decision_indicators':'Travel time, speed variability, throughput, creeping fraction',
         'future_external_evidence':'Legal speed limits, implementation, compliance and effect ranges',
         'observed_or_counterfactual':'COUNTERFACTUAL','status':'CONCEPTUAL_ONLY_AFTER_BASELINE_VALIDATION'},
        {'scenario':'E2','intervention':'Longitudinal assistance for smoother following','experimental_variable':'Target time gap and acceleration/braking smoothing for participating vehicles',
         'changed_rule':'Leader response and desired following gap','decision_indicators':'Headway, negative acceleration, travel time, queue/throughput',
         'future_external_evidence':'Assistance behavior, safe feasible bounds and adoption; no cognitive reaction claim',
         'observed_or_counterfactual':'COUNTERFACTUAL','status':'CONCEPTUAL_ONLY_AFTER_BASELINE_VALIDATION'},
        {'scenario':'E3','intervention':'Management of discretionary lane changes','experimental_variable':'Discretionary change propensity or benefit criterion; compulsory route changes retained',
         'changed_rule':'Lane-change conditional decision in same approach/section','decision_indicators':'Lane changes, travel time, throughput, stopped fraction',
         'future_external_evidence':'Operational intervention and compliance; route-required vs discretionary protocol',
         'observed_or_counterfactual':'COUNTERFACTUAL','status':'CONCEPTUAL_ONLY_AFTER_BASELINE_VALIDATION'}]


def main():
    start=time.perf_counter();before=digest(SOURCE);OUT.mkdir(exist_ok=True)
    d=pd.read_csv(SOURCE)
    if set(d.location.unique())!={'peachtree'}:raise ValueError('Other locations in source')
    original_columns=list(d.columns);original_types={k:str(v) for k,v in d.dtypes.items()}
    d,clock=detect_components(d)
    if clock['affine_component_count']!=2:raise RuntimeError('Revisit design: not two affine acquisition components')
    s,t=trajectory_table(d);events,lane_summary=lane_events(s)
    relations=join_relations(d)
    leader_summary,following,bins=following_summaries(relations)
    q=quality(d,s,t,relations)
    windows,arrivals=traffic_windows(d,t,events)
    comparison,transferability=compare_periods(d,t,relations,events,lane_summary)
    signals=signal_summary()
    ids={c:set(z.vehicle_id) for c,z in d.groupby('component')};shared=ids['B1']&ids['B2']
    attrs=t[t.vehicle_id.isin(shared)].pivot(index='vehicle_id',columns='component',values=['length_ft','width_ft','vehicle_class','origin','destination'])
    collisions={col:int(attrs[col]['B1'].ne(attrs[col]['B2']).sum()) for col in ['length_ft','width_ft','vehicle_class','origin','destination']}
    rawkeydup=int(d.duplicated(['vehicle_id','frame_id']).sum())
    qualitydict={c:{r.metric:r.value for r in z.itertuples()} for c,z in q.groupby('component')}
    strategies=[]
    for name,train,test in [('A','B1','B2'),('B','B2','B1')]:
        train0=d[d.component==train];test0=d[d.component==test]
        strategies.append({'strategy':name,'train':train,'test':test,'train_rows':len(train0),'test_rows':len(test0),
            'train_vehicle_keys':len(ids[train]),'test_vehicle_keys':len(ids[test]),'raw_id_overlap':len(shared),
            'component_vehicle_key_overlap':0,'raw_id_overlap_train_pct':100*len(shared)/len(ids[train]),
            'raw_id_overlap_test_pct':100*len(shared)/len(ids[test]),
            'classes_train':','.join(map(str,sorted(train0.v_class.unique()))),'classes_test':','.join(map(str,sorted(test0.v_class.unique()))),
            'lanes_train':','.join(map(str,sorted(train0.lane_id.unique()))),'lanes_test':','.join(map(str,sorted(test0.lane_id.unique()))),
            'speed_train_min':train0.v_vel.min(),'speed_train_max':train0.v_vel.max(),'speed_test_min':test0.v_vel.min(),'speed_test_max':test0.v_vel.max(),
            'distribution_shift':'Quantified in transferability; not a pass/fail threshold',
            'leakage':'No trajectory crosses components; raw IDs reused. Physical identity not independently certified',
            'recommended':name=='B','status':'PROPOSED_NOT_APPROVED_NOT_FROZEN','calendar_order':'NOT_CONFIRMED'})
    audit={'phase':'PEACHTREE-1','vehicle_source_only':'data/peachtree_full.csv','source_sha256':before,
        'file_bytes':SOURCE.stat().st_size,'rows':len(d),'raw_vehicle_id_unique':d.vehicle_id.nunique(),
        'component_vehicle_trajectories':len(t),'columns_exact':original_columns,'column_types':original_types,
        'missing':d[original_columns].isna().sum().to_dict(),'locations':d.location.value_counts().to_dict(),
        'clock_detection':clock,'periods':comparison[['component','rows','vehicles','frame_min','frame_max','frames','duration_s','raw_start','raw_end','raw_clock_origin']].to_dict('records'),
        'shared_raw_vehicle_ids':len(shared),'shared_raw_id_fraction_by_component':{c:len(shared)/len(ids[c]) for c in ids},
        'shared_id_attribute_conflicts':collisions,'raw_vehicle_frame_duplicate_excess_if_components_ignored':rawkeydup,
        'exact_duplicate_rows':int(d.duplicated(original_columns).sum()),'quality':qualitydict,
        'leader_follower':leader_summary.to_dict('records'),'lane_changes':lane_summary.to_dict('records'),
        'traffic_window_count':len(windows),'signal_status':'SIGNAL_DATA_NOT_IN_TRAJECTORY_CSV',
        'signal_auxiliary_files_txt':len(signals),'signal_auxiliary_alignment':'PENDING_COMPONENT_CALENDAR_GEOMETRY_FRAME_ALIGNMENT',
        'near_stopped_definition':'v_vel <= 1 ft/s (approx 0.305 m/s): diagnostic creeping proxy; not calibrated threshold',
        'stopped_sensitivity':{c:{str(limit):float(z.v_vel.le(limit).mean()) for limit in [0,.5,1,2]} for c,z in d.groupby('component')},
        'travel_time_status':'Observed OD journey duration only; not all trajectories span full corridor',
        'density_status':'NOT_ESTIMATED','classification':'VIABLE_WITH_LIMITATIONS','decision':'CONTINUAR',
        'classification_scope':'Empirical baseline feasibility on two recoverable acquisition components; clock, route geometry and signals must be resolved before freeze/calibration',
        'test_frozen':False,'calibration_performed':False,'abm_implemented':False,
        'reference_sources':{'metadata_pdf':{'url':METADATA_URL,'local_path':'data/reference/Peachtree_Street_Metadata_Documentation.pdf','sha256':digest(ROOT/'data/reference/Peachtree_Street_Metadata_Documentation.pdf')},
            'auxiliary_zip':{'url':AUX_URL,'method':'HTTP ranges, only CAD/GIS/signal ZIPs; trajectory member not downloaded or analyzed'}},
        'performance':{'elapsed_seconds':round(time.perf_counter()-start,3),'peak_process_working_set_mb':peak_memory_mb()},
        'source_unchanged':digest(SOURCE)==before}
    if not audit['source_unchanged']:raise RuntimeError('Source changed')
    save_csv('peachtree_periods.csv',comparison[['component','rows','vehicles','frame_min','frame_max','frames','duration_s','raw_start','raw_end','raw_clock_origin','calendar_start','calendar_end','lanes','classes']])
    save_csv('peachtree_trajectory_quality.csv',q)
    save_csv('peachtree_leader_follower.csv',leader_summary)
    save_csv('peachtree_car_following.csv',following)
    save_csv('peachtree_car_following_bins.csv',bins)
    save_csv('peachtree_lane_changes.csv',lane_summary)
    save_csv('peachtree_lane_change_events.csv',events)
    save_csv('peachtree_lane_change_transitions.csv',events[events.semantic_candidate].groupby(['component','origin_lane','destination_lane']).size().reset_index(name='events'))
    save_csv('peachtree_period_comparison.csv',comparison)
    save_csv('peachtree_transferability.csv',transferability)
    save_csv('peachtree_train_test_strategies.csv',strategies)
    save_csv('peachtree_parameter_identifiability.csv',parameter_candidates())
    save_csv('peachtree_validation_candidates.csv',validation_candidates())
    save_csv('peachtree_scenario_feasibility.csv',scenarios())
    save_csv('peachtree_traffic_windows.csv',windows)
    save_csv('peachtree_arrivals.csv',arrivals)
    save_csv('peachtree_trajectory_summary.csv',t)
    save_csv('peachtree_signal_inventory.csv',signals)
    (OUT/'peachtree_dataset_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False,default=lambda x:x.item() if isinstance(x,np.generic) else str(x),allow_nan=False),encoding='utf-8')
    make_figures(d,windows,events)
    from scripts.peachtree_report import write_report
    write_report(audit,comparison,transferability,following,windows)
    print(json.dumps({'classification':audit['classification'],'clock':clock,'periods':audit['periods'],'leader':audit['leader_follower'],'lane_changes':audit['lane_changes'],'performance':audit['performance']},indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x)))


def make_figures(d,windows,events):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=OUT/'figures';folder.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained',sharex=True)
    for comp,z in windows[windows.window_s==30].groupby('component'):
        axes[0].plot(z.start_s,z.mean_speed_ft_s,label=comp)
        axes[1].plot(z.start_s,z.exactly_stopped_fraction*100,label=comp)
    axes[0].set(ylabel='Mean reported speed (ft/s)',title='Peachtree: provisional acquisition components, not calendar labels')
    axes[1].set(ylabel='Exactly stopped observations (%)',xlabel='Seconds from first frame in each component')
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.savefig(folder/'peachtree_traffic_over_time.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for comp,z in d.groupby('component'):
        ax.hist(z.v_vel,bins=np.linspace(0,60,61),density=True,histtype='step',label=comp)
    ax.set(xlabel='Reported speed (ft/s)',ylabel='Density',title='Time/vehicle observation-weighted speed distributions')
    ax.legend();fig.savefig(folder/'peachtree_speed_distribution.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
