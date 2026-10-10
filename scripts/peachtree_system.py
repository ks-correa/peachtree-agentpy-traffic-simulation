"""Deterministic PEACHTREE-2 reconstruction utilities; no behavioral fitting."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

from scripts.audit_peachtree import detect_components

INTERSECTIONS={1:('10th',51,'SIGNAL'),2:('11th',52,'SIGNAL'),3:('12th',53,'SIGNAL'),
               4:('13th',None,'STOP'),5:('14th',73,'SIGNAL')}
PERIODS={'B1':'1245-0100','B2':'0400-0415'}
DIRECTIONS={1:'EB',2:'NB',3:'WB',4:'SB'}
MOVEMENTS={1:'THROUGH',2:'LEFT_TURN',3:'RIGHT_TURN'}
ROAD_LANES={1,2,3,11}


def trajectory_key(acquisition_id,vehicle_id):
    """Canonical identity; CSV/Parquet use lossless B1:integer serialization."""
    if acquisition_id not in ['B1','B2']:raise ValueError('Unknown acquisition')
    return acquisition_id,int(vehicle_id)


def canonicalize(source):
    d,clock=detect_components(source)
    d=d.rename(columns={'component':'acquisition_id'})
    first=d.groupby('acquisition_id').frame_id.transform('min')
    d['t_relative']=(d.frame_id-first)*.1
    d['trajectory_key']=d.acquisition_id+':'+d.vehicle_id.astype(str)
    d=d.sort_values(['acquisition_id','vehicle_id','frame_id'],kind='stable').reset_index(drop=True)
    if d.duplicated(['acquisition_id','vehicle_id','frame_id']).any():
        raise ValueError('Ambiguous canonical trajectory frame')
    return d,clock


def parse_signal(path):
    """Preserve unknown before first event; don't infer a starting phase."""
    table=pd.read_csv(path,sep='\t')
    phases={};warnings=[]
    for phase in ['Thru','Left']:
        cols=[f'{prefix}_{phase}' for prefix in ['BG','BY','BR']]
        if not all(c in table for c in cols):continue
        events=[]
        for col,state in zip(cols,['GREEN','YELLOW','RED']):
            for value in table[col].dropna():
                if value==0:
                    warnings.append('ZERO_FRAME_EVENT_NOT_USED_WITHOUT_INITIAL_STATE_EVIDENCE');continue
                if value<0 or value!=int(value):
                    warnings.append('INVALID_EVENT_FRAME');continue
                events.append((int(value),state))
        events=sorted(set(events))
        duplicate_frames=pd.Series([x[0] for x in events]).duplicated().sum()
        if duplicate_frames:
            warnings.append('CONFLICTING_STATES_AT_SAME_FRAME')
            conflicted={f for f in {x[0] for x in events} if len({st for fr,st in events if fr==f})>1}
            events=[(f,st) for f,st in events if f not in conflicted]+[(f,'UNKNOWN') for f in conflicted]
            events.sort()
        frames=np.array([x[0] for x in events],dtype=np.int64)
        states=np.array([x[1] for x in events],dtype=object)
        triples=table[cols].dropna()
        good=(triples[cols[0]]>0)&(triples[cols[0]]<triples[cols[1]])&(triples[cols[1]]<triples[cols[2]])
        triples=triples[good]
        green=(triples[cols[1]]-triples[cols[0]])*.1
        yellow=(triples[cols[2]]-triples[cols[1]])*.1
        bg=table[cols[0]].dropna();bg=bg[bg>0].sort_values()
        cycle=bg.diff().dropna()*.1
        red=(table[cols[0]].shift(-1)-table[cols[2]])*.1
        red=red[(table[cols[0]].shift(-1)>0)&(table[cols[2]]>0)&red.ge(0)]
        phases[phase]={'frames':frames,'states':states,
            'green_s':green.to_numpy(),'yellow_s':yellow.to_numpy(),'red_s':red.dropna().to_numpy(),
            'cycle_s':cycle.to_numpy(),'valid_triples':len(triples),'missing_cells':int(table[cols].isna().sum().sum())}
    return phases,sorted(set(warnings)),table


def lookup_state(frames,phase):
    values=np.asarray(frames)
    if not len(phase['frames']):return np.full(len(values),'UNKNOWN',dtype=object)
    idx=np.searchsorted(phase['frames'],values,side='right')-1
    result=phase['states'][np.maximum(idx,0)].copy()
    result[idx<0]='UNKNOWN'
    return result


def annotated_crossings(d):
    g=d.groupby('trajectory_key',sort=False)
    previous_int=g.int_id.shift();previous_section=g.section_id.shift();previous_dir=g.direction.shift()
    consecutive=d.frame_id.sub(g.frame_id.shift()).eq(1)
    columns=['acquisition_id','trajectory_key','vehicle_id','frame_id','t_relative','local_x','local_y','lane_id','direction','movement','section_id','int_id','v_vel']
    enters=consecutive&d.int_id.gt(0)&previous_int.eq(0)&previous_section.gt(0)&d.direction.eq(previous_dir)
    exits=consecutive&previous_int.gt(0)&d.int_id.eq(0)&d.section_id.gt(0)&d.direction.eq(previous_dir)
    entry=d.loc[enters,columns].copy();entry['intersection_id']=entry.int_id
    entry['event']='ANNOTATED_INTERSECTION_ENTRY';entry['from_section']=previous_section.loc[enters].astype(int)
    exit=d.loc[exits,columns].copy();exit['intersection_id']=previous_int.loc[exits].astype(int)
    exit['event']='ANNOTATED_INTERSECTION_EXIT';exit['from_section']=previous_section.loc[exits].astype(int)
    entry['crossing_y_ft']=.5*(d.local_y.loc[enters]+g.local_y.shift().loc[enters])
    exit['crossing_y_ft']=.5*(d.local_y.loc[exits]+g.local_y.shift().loc[exits])
    return entry,exit


def fixed_gate_crossings(d,ymin,ymax):
    """Interpolated front-center crossings; requires two consecutive samples.

    The cuts are defined measurement gates, not inferred detection/first-record
    boundaries. A segment failing the documented kinematic diagnostic is flagged.
    """
    g=d.groupby('trajectory_key',sort=False)
    py=g.local_y.shift();px=g.local_x.shift();pf=g.frame_id.shift()
    pt=g.t_relative.shift();pv=g.v_vel.shift()
    step=np.hypot(d.global_x-g.global_x.shift(),d.global_y-g.global_y.shift())
    # Two position estimates with documented ~2 ft X / ~4 ft Y accuracy.
    allowance=2*np.hypot(2,4)
    suspicious=step>((d.v_vel+pv)/2*.1+allowance)
    consecutive=d.frame_id.sub(pf).eq(1)
    records=[]
    for bound,name in [(ymin,'SOUTH_CUT'),(ymax,'NORTH_CUT')]:
        up=consecutive&py.lt(bound)&d.local_y.ge(bound)
        down=consecutive&py.gt(bound)&d.local_y.le(bound)
        for mask,direction in [(up,2),(down,4)]:
            mask=mask&d.direction.eq(direction)
            if not mask.any():continue
            q=d.loc[mask,['acquisition_id','trajectory_key','vehicle_id','frame_id','lane_id','direction','movement','v_class','v_vel','o_zone','d_zone']].copy()
            alpha=(bound-py.loc[mask])/(d.local_y.loc[mask]-py.loc[mask])
            q['t_cross_s']=pt.loc[mask]+alpha*.1
            q['local_x_cross_ft']=px.loc[mask]+alpha*(d.local_x.loc[mask]-px.loc[mask])
            q['local_y_cross_ft']=bound;q['boundary']=name
            q['event']='ENTRY' if (name=='SOUTH_CUT' and direction==2) or (name=='NORTH_CUT' and direction==4) else 'EXIT'
            q['spatial_discontinuity_flag']=suspicious.loc[mask]
            q['interpolation']='LINEAR_FRONT_CENTER_BETWEEN_CONSECUTIVE_0_1S_SAMPLES'
            records.append(q)
    if not records:
        return pd.DataFrame(columns=['acquisition_id','trajectory_key','vehicle_id','frame_id','lane_id','direction','movement','v_class','v_vel','o_zone','d_zone','t_cross_s','local_x_cross_ft','local_y_cross_ft','boundary','event','spatial_discontinuity_flag','interpolation'])
    return pd.concat(records,ignore_index=True).sort_values(['trajectory_key','t_cross_s','event']).reset_index(drop=True)


def pair_travel_times(events,ymin,ymax):
    records=[]
    for key,q in events[~events.spatial_discontinuity_flag].groupby('trajectory_key',sort=True):
        pending=None
        for r in q.sort_values('t_cross_s').itertuples():
            if r.event=='ENTRY':pending=r
            elif pending is not None:
                if r.boundary!=pending.boundary and r.direction==pending.direction:
                    records.append({'acquisition_id':r.acquisition_id,'trajectory_key':key,'vehicle_id':r.vehicle_id,
                        'direction':r.direction,'entry_boundary':pending.boundary,'exit_boundary':r.boundary,
                        'entry_frame':pending.frame_id,'exit_frame':r.frame_id,'entry_time_s':pending.t_cross_s,
                        'exit_time_s':r.t_cross_s,'travel_time_s':r.t_cross_s-pending.t_cross_s,
                        'measurement_length_ft':ymax-ymin,'unit':'s','definition':'FIXED_CUT_TO_OPPOSITE_FIXED_CUT_FRONT_CENTER'})
                pending=None
    return pd.DataFrame(records)


def confirm_lane_changes(d):
    g=d.groupby('trajectory_key',sort=False)
    prev=g.lane_id.shift();frame_delta=d.frame_id.sub(g.frame_id.shift())
    raw=frame_delta.eq(1)&prev.notna()&d.lane_id.ne(prev)
    next_lane=g.lane_id.shift(-1);next_frame=g.frame_id.shift(-1)
    excursion=raw&next_frame.sub(d.frame_id).eq(1)&next_lane.eq(prev)
    excursion_transition=excursion|excursion.groupby(d.trajectory_key).shift(fill_value=False)
    same_context=d.section_id.gt(0)&d.section_id.eq(g.section_id.shift())&d.int_id.eq(0)&g.int_id.shift().eq(0)&d.direction.eq(g.direction.shift())
    normal=d.lane_id.isin([1,2,3])&prev.isin([1,2,3])
    adjacent=d.lane_id.sub(prev).abs().eq(1)
    run=d.lane_id.ne(prev).groupby(d.trajectory_key).cumsum()
    grouped=d.groupby([d.trajectory_key,run],sort=False).frame_id
    begin=grouped.transform('min');end=grouped.transform('max')
    previous_run_length=(d.frame_id-begin+1).groupby(d.trajectory_key).shift()
    next_run_length=end-d.frame_id+1
    before_x=g.local_x.transform(lambda x:x.shift().rolling(10,min_periods=10).median())
    after_x=g.local_x.transform(lambda x:x.iloc[::-1].rolling(10,min_periods=10).median().iloc[::-1])
    delta_x=after_x-before_x
    expected_sign=np.where(d.direction.eq(2),1,np.where(d.direction.eq(4),-1,0))*np.sign(d.lane_id-prev)
    physical=expected_sign*delta_x>4  # Two nominal 2ft lateral coordinate errors; diagnostic protocol.
    global_step=np.hypot(d.global_x-g.global_x.shift(),d.global_y-g.global_y.shift())
    discontinuity=global_step>((d.v_vel+g.v_vel.shift())/2*.1+2*np.hypot(2,4))
    back=discontinuity.groupby(d.trajectory_key).transform(lambda x:x.rolling(11,min_periods=1).max())
    forward=discontinuity.groupby(d.trajectory_key).transform(lambda x:x.iloc[::-1].rolling(11,min_periods=1).max().iloc[::-1])
    event_jump=back.astype(bool)|forward.astype(bool)
    confirmed=raw&same_context&normal&adjacent&~excursion_transition&previous_run_length.ge(5)&next_run_length.ge(5)&physical&~event_jump
    e=d.loc[raw,['acquisition_id','trajectory_key','vehicle_id','frame_id','t_relative','local_x','local_y','lane_id','section_id','int_id','direction','movement','v_vel']].copy()
    e['origin_lane']=prev.loc[raw].astype(int);e['destination_lane']=e.lane_id
    e['oscillation_transition']=excursion_transition.loc[raw]
    e['turn_bay_transition']=e.origin_lane.eq(11)|e.destination_lane.eq(11)
    e['intersection_or_context_transition']=~same_context.loc[raw]
    e['undocumented_lane_transition']=~e.origin_lane.isin([0,1,2,3,11])|~e.destination_lane.isin([0,1,2,3,11])
    e['before_run_frames']=previous_run_length.loc[raw];e['after_run_frames']=next_run_length.loc[raw]
    e['lateral_median_difference_ft']=delta_x.loc[raw]
    e['spatial_jump_in_event_window']=event_jump.loc[raw]
    e['confirmed']=confirmed.loc[raw]
    e['classification']=np.where(e.confirmed,'CONFIRMED_LANE_CHANGE','RAW_TRANSITION_NOT_CONFIRMED')
    e['confirmation_method']='Operational: adjacent normal lanes, same section/direction, no intersection/excursion, >=5 frames stable each side, signed 10-frame median lateral shift >4ft; no video confirmation'
    return e


def annotation_travel_times(entry,exit):
    records=[]
    for key,z in pd.concat([entry,exit]).groupby('trajectory_key',sort=True):
        opened={}
        for r in z.sort_values('frame_id').itertuples():
            if r.event=='ANNOTATED_INTERSECTION_ENTRY':opened[r.intersection_id]=r
            elif r.intersection_id in opened:
                first=opened.pop(r.intersection_id)
                records.append({'acquisition_id':r.acquisition_id,'trajectory_key':key,'vehicle_id':r.vehicle_id,
                    'metric':'intersection_traversal_time','intersection_id':r.intersection_id,
                    'direction_in':first.direction,'direction_out':r.direction,'entry_frame':first.frame_id,
                    'exit_frame':r.frame_id,'travel_time_s':(r.frame_id-first.frame_id)*.1,
                    'entry_y_ft':first.crossing_y_ft,'exit_y_ft':r.crossing_y_ft,
                    'definition':'OBSERVED_SECTION_TO_INTERSECTION_TO_SECTION_ANNOTATION_CROSSINGS',
                    'length_status':'PATH_DEPENDENT_NOT_A_UNIVERSAL_INTERSECTION_LENGTH'})
    return pd.DataFrame(records)
