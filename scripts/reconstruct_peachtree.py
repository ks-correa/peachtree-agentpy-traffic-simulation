"""PEACHTREE-2: source-based topology, clocks, signals, gates and draft contract.

No ABM, parameter calibration, signal optimization or held-out freeze occurs.
"""
from __future__ import annotations

import json
import time
import shutil
import zipfile
import csv as csv_module
from pathlib import Path
import numpy as np
import pandas as pd
import shapefile

from scripts.evaluate_local import digest,peak_memory_mb
from scripts.peachtree_system import (canonicalize,parse_signal,lookup_state,annotated_crossings,
    fixed_gate_crossings,pair_travel_times,confirm_lane_changes,annotation_travel_times,
    INTERSECTIONS,PERIODS,DIRECTIONS,MOVEMENTS)

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs';REF=ROOT/'data/reference'
SOURCE=ROOT/'data/peachtree_full.csv'
SIGNALS=REF/'auxiliary/signal-timing/signal-change/Original Text files'
YMIN=400.;YMAX=1400.
REPORT_SOURCE='Peachtree data analysis reports: PDF p10 (identifiers), p11 Fig4 (topology/zones), p12 Table1 (acquisition fingerprint), p9 (tracking extension)'


def csv(name,rows):pd.DataFrame(rows).to_csv(OUT/name,index=False)
def safe_json(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,Path):return str(value)
    raise TypeError(str(type(value)))
def statistics(values):
    a=np.asarray(values,dtype=float)
    a=a[np.isfinite(a)]
    return {name:float(fn(a)) if len(a) else None for name,fn in [('min',np.min),('median',np.median),('max',np.max)]}


def inventory():
    rows=[]
    for p in [SOURCE,REF/'Peachtree_Street_Metadata_Documentation.pdf']+sorted(REF.glob('peachtree-street-*.zip')):
        rows.append({'path':str(p.relative_to(ROOT)),'member':'','format':p.suffix,'bytes':p.stat().st_size,
            'sha256':digest(p),'role':'VEHICULAR_SOURCE' if p==SOURCE else 'PEACHTREE_SUPPORT'})
        if p.suffix=='.zip':
            with zipfile.ZipFile(p) as archive:
                for member in archive.infolist():
                    target=REF/'auxiliary'/member.filename
                    rows.append({'path':str(p.relative_to(ROOT)),'member':member.filename,
                        'format':Path(member.filename).suffix,'bytes':member.file_size,
                        'sha256':digest(target) if target.is_file() else '',
                        'role':'SUPPORT_MEMBER' if not member.is_dir() else 'DIRECTORY'})
    # Unfetched imagery is explicitly inventoried without interpreting it.
    remote=json.loads((REF/'peachtree_auxiliary_outer_inventory.json').read_text())
    for r in remote:
        if not (REF/r['name']).exists():
            rows.append({'path':'OFFICIAL_OUTER_ZIP','member':r['name'],'format':Path(r['name']).suffix,
                'bytes':r['size'],'sha256':'','role':'REMOTE_IMAGERY_NOT_NEEDED' if 'aerial' in r['name'] else 'REMOTE_VEHICLE_MEMBER_NOT_USED'})
    return rows


def geometry(d,entry,exit):
    intersections=[];sections=[];mouths=[]
    for i,(street,controller,control) in INTERSECTIONS.items():
        q=d[d.int_id==i]
        for direction in [2,4]:
            for label,z in [('ENTRY',entry),('EXIT',exit)]:
                samples=z[z.intersection_id.eq(i)&z.direction.eq(direction)].crossing_y_ft
                mouths.append({'intersection_id':i,'direction':direction,'event':label,'n':len(samples),
                    'crossing_y_median_ft':samples.median(),'p05_ft':samples.quantile(.05),'p95_ft':samples.quantile(.95),
                    'source':'Observed section/int transition front centers, not surveyed painted stop line'})
        intersections.append({'intersection_id':i,'street':street+' Street NE','controller_id':controller,
            'control_type':control,'south_section':i,'north_section':i+1,
            'observed_y_min_ft':q.local_y.min(),'observed_y_max_ft':q.local_y.max(),
            'observed_y_median_ft':q.local_y.median(),'rows':len(q),
            'source':REPORT_SOURCE,'confidence':'DOCUMENTED_TOPOLOGY_OBSERVED_EXTENT'})
    mouths=pd.DataFrame(mouths)
    for i in range(1,7):
        q=d[d.section_id==i]
        if i==1:lower=0.
        else:lower=d[d.int_id==i-1].local_y.max()
        if i==6:upper=d.local_y.max()
        else:upper=d[d.int_id==i].local_y.min()
        # Coordinate spans include angled, direction-dependent mouths. The main
        # length is the observed coded-section extent, not a surveyed link length.
        sections.append({'section_id':i,'south_intersection':i-1 if i>1 else None,
            'north_intersection':i if i<=5 else None,'rows':len(q),
            'observed_y_min_ft':q.local_y.min(),'observed_y_max_ft':q.local_y.max(),
            'observed_extent_length_ft':q.local_y.max()-q.local_y.min(),
            'between_intersection_extent_lower_ft':lower,'between_intersection_extent_upper_ft':upper,
            'interior_clear_span_ft':max(0.,upper-lower),
            'confidence':'DOCUMENTED_TOPOLOGY; LENGTH_DATASET_DERIVED_APPROXIMATION',
            'source':REPORT_SOURCE})
    lanes=[]
    for (section,direction,lane),q in d[d.section_id.gt(0)].groupby(['section_id','direction','lane_id']):
        lanes.append({'section_id':section,'direction':direction,'lane_id':lane,'rows':len(q),
            'local_x_p05_ft':q.local_x.quantile(.05),'local_x_median_ft':q.local_x.median(),'local_x_p95_ft':q.local_x.quantile(.95),
            'meaning':'LEFT_TURN_BAY' if lane==11 else 'REGULAR_NUMBERED_LANE' if lane in [1,2,3] else 'UNRESOLVED_OR_INTERSECTION_CODE',
            'source':'Data analysis Fig4 plus metadata lane dictionary; geometry ranges from CSV',
            'confidence':'DOCUMENTED_LABEL_PLUS_OBSERVED_POSITION' if lane in [1,2,3,11] else 'UNRESOLVED'})
    movements=d.groupby(['acquisition_id','int_id','direction','movement']).agg(rows=('vehicle_id','size'),vehicles=('vehicle_id','nunique')).reset_index()
    movements['meaning']=movements.movement.map(MOVEMENTS);movements['direction_meaning']=movements.direction.map(DIRECTIONS)
    return pd.DataFrame(sections),pd.DataFrame(intersections),pd.DataFrame(lanes),movements,mouths


def code_dictionary(d):
    rows=[]
    for field,mapping in [('direction',DIRECTIONS),('movement',MOVEMENTS)]:
        for code,meaning in mapping.items():rows.append({'field':field,'code':code,'meaning':meaning,
            'source':'Peachtree metadata PDF p14','confidence':'DOCUMENTED'})
    for i,(street,controller,control) in INTERSECTIONS.items():
        rows.append({'field':'int_id','code':i,'meaning':f'{street} St; controller {controller}; {control}',
            'source':REPORT_SOURCE,'confidence':'DOCUMENTED_AND_SPATIAL_ORDER_VERIFIED'})
    for i in range(1,7):rows.append({'field':'section_id','code':i,
        'meaning':f'Arterial section {i}, between intersections {i-1} and {i}; study limit substitutes at ends',
        'source':REPORT_SOURCE,'confidence':'DOCUMENTED'})
    for value in sorted(d.lane_id.unique()):rows.append({'field':'lane_id','code':int(value),
        'meaning':'LEFT_TURN_BAY' if value==11 else 'NORMAL_FROM_MEDIAN_ORDER' if value in [1,2,3] else 'UNDOCUMENTED_OR_SPECIAL_NOT_ASSIGNED',
        'source':'Peachtree metadata p13 and data analysis Fig4; observed codes','confidence':'DOCUMENTED' if value in [1,2,3,11] else 'UNRESOLVED'})
    # Zone positions are read from Fig4; never guessed from frequency.
    zone_map={101:'South study edge, Peachtree NB',201:'South study edge, Peachtree SB',
        114:'North study edge, Peachtree SB',214:'North study edge, Peachtree NB',
        102:'10th east origin',202:'10th east destination',123:'10th west origin',223:'10th west destination',
        103:'11th east origin',203:'11th east destination',122:'11th west origin',222:'11th west destination',
        106:'12th east origin',206:'12th east destination',121:'12th west origin',221:'12th west destination',
        112:'13th east origin',212:'13th east destination',119:'13th west parking exit',
        113:'14th east origin',213:'14th east destination',115:'14th west origin',215:'14th west destination',
        105:'Section3 east driveway origin',205:'Section3 east driveway destination',204:'Section3 east driveway destination',
        110:'Section4 east driveway origin',210:'Section4 east driveway destination',
        111:'Section4 east driveway origin',211:'Section4 east driveway destination',
        116:'Section5 west driveway origin',216:'Section5 west driveway destination',
        117:'Section5 west driveway origin',217:'Section5 west driveway destination',
        118:'Section5 west driveway origin',218:'Section5 west driveway destination',
        120:'Section4 west driveway origin',220:'Section4 west driveway destination',
        207:'Section4 east driveway destination',208:'Section4 east driveway destination',209:'Section4 east driveway destination'}
    for field in ['o_zone','d_zone']:
        for code in sorted(d[field].unique()):rows.append({'field':field,'code':int(code),'meaning':zone_map.get(code,'UNRESOLVED_ZERO_ZONE' if code==0 else 'ZONE_ON_FIGURE4_NOT_TRANSCRIBED'),
            'source':'Data analysis PDF p11 Fig4; names distinguish origin vs destination',
            'confidence':'DOCUMENTED_FIGURE' if code in zone_map else 'UNRESOLVED'})
    for cls,meaning in [(1,'MOTORCYCLE'),(2,'AUTOMOBILE'),(3,'TRUCK_OR_BUS')]:rows.append({'field':'v_class','code':cls,'meaning':meaning,
        'source':'Data analysis PDF p12 Table1 / text; metadata p13 says truck','confidence':'DOCUMENTED'})
    return rows


def controller_pdf_transcription():
    # Reviewed both raster pages of all four official sheets. Values are stamped
    # configuration, not asserted as the active November acquisition program.
    cycles=[95,80,80,100,90,80,100,90,80]
    offsets={51:[75,79,79,65,49,49,37,28,5],52:[92,10,75,78,62,65,60,39,79],
             53:[93,11,70,79,55,12,79,40,32],73:[61,55,55,47,48,48,79,26,26]}
    params={
        51:([5,15,8,12,8,15,5,16],[10,45,15,30,10,45,15,30],[3.6,3.8,3.6,3.6,3.6,3.8,3.6,3.6],[1.2,2.6,2.1,1.9,1.2,2.6,2.1,1.9]),
        52:([0,15,0,9,0,15,0,9],[0,45,0,21,0,45,0,21],[0,3.6,0,3.2,0,3.6,0,3.2],[0,2.9,0,2.6,0,2.9,0,2.6]),
        53:([0,15,0,9,0,15,0,9],[0,50,0,28,0,50,0,28],[0,3.6,0,3.2,0,3.6,0,3.2],[0,2.1,0,2.6,0,2.1,0,2.6]),
        73:([5,15,5,9,5,15,0,9],[10,40,12,34,12,40,0,34],[3.6,3.7,3.6,3.2,3.6,3.7,0,3.2],[1.6,2.6,1.6,2.4,1.6,2.6,0,2.4])}
    rows=[];phases=['WBL','EBT','NBL','SBT','EBL','WBT','SBL','NBT']
    for controller in [51,52,53,73]:
        for phase,name in enumerate(phases,1):
            minimum,maximum,yellow,clearance=params[controller]
            rows.append({'controller_id':controller,'record_type':'PHASE_BANK_1','code':phase,'movement_label':name,
                'min_initial_s':minimum[phase-1],'max_limit_s':maximum[phase-1],'yellow_s':yellow[phase-1],
                'red_clear_s':clearance[phase-1],'printed_cycle_s':None,'offset_A':None,
                'source':f'int{controller}.pdf p1','sheet_capture_date':'2006-01-27','active_acquisition_plan_status':'NOT_CERTIFIED_FROM_PRINTED_SHEET'})
        for plan,(cycle,offset) in enumerate(zip(cycles,offsets[controller]),1):
            rows.append({'controller_id':controller,'record_type':'COORDINATION_PLAN','code':plan,'movement_label':'',
                'min_initial_s':None,'max_limit_s':None,'yellow_s':None,'red_clear_s':None,
                'printed_cycle_s':cycle,'offset_A':offset,'source':f'int{controller}.pdf p2',
                'sheet_capture_date':'2006-01-27','active_acquisition_plan_status':'NOT_CERTIFIED; printed TOD at09:30 plan1 and15:45 plan7, not asserted field activation'})
    return rows


def auxiliary_profiles():
    tube=[]
    folder=REF/'auxiliary/tube-data/Original Text files'
    for p in sorted(folder.glob('*.txt')):
        lines=p.read_text(encoding='utf-8-sig',errors='replace').splitlines()
        header=next((i for i,line in enumerate(lines) if line.startswith('Date\tTime\t')),None)
        if header is None:
            tube.append({'file':p.name,'status':'NO_TABULAR_HEADER'});continue
        rows=list(csv_module.reader(lines[header+1:],delimiter='\t'))
        good=[r[:3] for r in rows if len(r)>=3 and r[0].strip()]
        dates=sorted({r[0] for r in good})
        tube.append({'file':p.name,'rows':len(good),'date_literals':','.join(dates),
            'columns_exact':lines[header].strip(),'first_date_time':good[0][0]+' '+good[0][1] if good else '',
            'last_date_time':good[-1][0]+' '+good[-1][1] if good else '',
            'sha256':digest(p),'unit_as_labeled':'Volume(veh/hr); time records at15-minute intervals',
            'role':'AGGREGATE_CONTEXT_ONLY_NOT_INDIVIDUAL_ENTRY_EVENTS','status':'INSPECTED_NO_MICROSCOPIC_ARRIVALS_INFERRED'})
    reader=shapefile.Reader(str(REF/'auxiliary/gis-files/camera-coverage.shp'))
    cameras=[]
    for r in reader.iterShapeRecords():
        xs=[x for x,y in r.shape.points];ys=[y for x,y in r.shape.points]
        cameras.append({'camera_id':int(r.record[0]),'global_x_min_ft':min(xs),'global_x_max_ft':max(xs),
            'global_y_min_ft':min(ys),'global_y_max_ft':max(ys),'vertices':len(r.shape.points),
            'layer_role':'CAMERA_COVERAGE_POLYGON_NOT_LANE_OR_STOPLINE_GEOMETRY'})
    cad=REF/'auxiliary/cad-diagram/Atlanta-Peachtree.dwg'
    return tube,cameras,{'file':str(cad.relative_to(ROOT)),'dwg_signature':cad.read_bytes()[:6].decode('ascii'),
        'entity_parse_status':'NOT_PARSED_NO_DWG_CONVERTER; OFFICIAL_REPORT_FIG4_USED_FOR_TOPOLOGY'}


def load_signals(d):
    bank={};rows=[];timeline=[]
    first=d.groupby('acquisition_id').frame_id.min().to_dict();last=d.groupby('acquisition_id').frame_id.max().to_dict()
    for acq,period in PERIODS.items():
        for inter,(street,controller,control) in INTERSECTIONS.items():
            if control!='SIGNAL':continue
            for direction,dirname in DIRECTIONS.items():
                path=SIGNALS/f'Peachtree_{street}_{dirname}_{period}.txt'
                phases,warnings,raw=parse_signal(path)
                for phase,z in phases.items():
                    bank[(acq,inter,direction,phase)]=z
                    st=statistics(z['cycle_s']);gr=statistics(z['green_s']);ye=statistics(z['yellow_s']);re=statistics(z['red_s'])
                    rows.append({'acquisition_id':acq,'civil_period_label_documented':period,'intersection_id':inter,
                        'controller_id':controller,'street':street,'direction':direction,'phase':phase,'file':str(path.relative_to(ROOT)),
                        'sha256':digest(path),'events':len(z['frames']),'valid_timing_triples':z['valid_triples'],
                        'first_event_frame':int(z['frames'][0]) if len(z['frames']) else None,
                        'last_event_frame':int(z['frames'][-1]) if len(z['frames']) else None,
                        'events_after_last_trajectory_frame':int((z['frames']>last[acq]).sum()),
                        'cycle_median_s':st['median'],'cycle_min_s':st['min'],'cycle_max_s':st['max'],
                        'green_median_s':gr['median'],'green_min_s':gr['min'],'green_max_s':gr['max'],
                        'yellow_median_s':ye['median'],'red_median_s':re['median'],
                        'offset_reference_first_green_s':next(((int(f)-first[acq])*.1 for f,state in zip(z['frames'],z['states']) if state=='GREEN'),None),
                        'missing_cells':z['missing_cells'],'warnings':';'.join(warnings),
                        'mapping_evidence':'Data analysis Table1 acquisition fingerprint + metadata frame definition + report controller map',
                        'offset_type':'FIRST_OBSERVED_GREEN_REFERENCE_NOT_ASSUMED_FIXED_CONTROLLER_OFFSET'})
                    for index,(frame,state) in enumerate(zip(z['frames'],z['states'])):
                        end=int(z['frames'][index+1]) if index+1<len(z['frames']) else last[acq]+1
                        if frame>last[acq]:continue
                        timeline.append({'acquisition_id':acq,'intersection_id':inter,'direction':direction,'phase':phase,
                            'start_frame':int(frame),'end_frame_exclusive':min(end,last[acq]+1),'state':state,
                            't_start_s':(int(frame)-first[acq])*.1,'t_end_s':(min(end,last[acq]+1)-first[acq])*.1,
                            'initial_before_first_event':'UNKNOWN; no backfill'})
    return bank,pd.DataFrame(rows),pd.DataFrame(timeline)


def signal_verification(d,entry,mouths,bank):
    rows=[]
    for (acq,inter,direction,phase),schedule in sorted(bank.items()):
        if phase!='Thru':continue
        source=d[d.acquisition_id.eq(acq)]
        events=entry[entry.acquisition_id.eq(acq)&entry.intersection_id.eq(inter)&entry.direction.eq(direction)&entry.movement.eq(1)].copy()
        events['state']=lookup_state(events.frame_id,schedule)
        mouth=mouths[mouths.intersection_id.eq(inter)&mouths.direction.eq(direction)&mouths.event.eq('ENTRY')].crossing_y_median_ft
        pos=float(mouth.iloc[0]) if len(mouth) else np.nan
        if direction in [2,4] and np.isfinite(pos):
            section=inter if direction==2 else inter+1
            distance=pos-source.local_y if direction==2 else source.local_y-pos
            # Window is a spatial diagnostic band, not an optimized alignment.
            q=source[source.direction.eq(direction)&source.section_id.eq(section)&source.int_id.eq(0)&source.movement.eq(1)&distance.between(0,150)].copy()
        else:q=source.iloc[:0].copy()
        q['state']=lookup_state(q.frame_id,schedule)
        red=q[q.state=='RED'];green=q[q.state=='GREEN']
        contrast=len(red)>0 and len(green)>0 and green.v_vel.mean()>red.v_vel.mean() and red.v_vel.eq(0).mean()>green.v_vel.eq(0).mean()
        direct=events[events.state.isin(['GREEN','RED'])]
        crossing_support=not direct.empty and (direct.state=='GREEN').sum()>(direct.state=='RED').sum()
        status='SIGNAL_SYNC_CONFIRMED' if contrast and crossing_support else 'SIGNAL_SYNC_PROBABLE' if direction not in [2,4] else 'SIGNAL_SYNC_UNRESOLVED'
        rows.append({'acquisition_id':acq,'intersection_id':inter,'direction':direction,'phase':phase,
            'status':status,'approach_band_ft':150,'approach_rows':len(q),'red_rows':len(red),'green_rows':len(green),
            'red_mean_speed_ft_s':red.v_vel.mean(),'green_mean_speed_ft_s':green.v_vel.mean(),
            'red_exactly_stopped_fraction':red.v_vel.eq(0).mean() if len(red) else np.nan,
            'green_exactly_stopped_fraction':green.v_vel.eq(0).mean() if len(green) else np.nan,
            'entries_green':int(events.state.eq('GREEN').sum()),'entries_yellow':int(events.state.eq('YELLOW').sum()),
            'entries_red':int(events.state.eq('RED').sum()),'entries_unknown':int(events.state.eq('UNKNOWN').sum()),
            'offset_fitted':False,'frame_scale_fitted':False,
            'evidence':'Declared trajectory frame numbers, documented IDs/acquisition, observed red/green contrast and entry timing; annotation mouths are not painted stop bars',
            'scope_of_confirmation':'THROUGH_ARTERIAL_APPROACH' if direction in [2,4] else 'DOCUMENTARY_MAPPING_ONLY_NO_OBSERVED_UPSTREAM_APPROACH'})
    return pd.DataFrame(rows)


def attach_signal_context(d,mouths,bank):
    result=d.copy();target=np.where(result.int_id.gt(0),result.int_id,
        np.where(result.direction.eq(2),result.section_id,np.where(result.direction.eq(4),result.section_id-1,-1)))
    result['control_intersection']=target.astype(int)
    result['signal_state']='UNKNOWN';result['signal_permission_status']='UNRESOLVED'
    result['distance_to_intersection_ft']=np.nan
    for (acq,inter,direction,phase),schedule in bank.items():
        selection=result.acquisition_id.eq(acq)&result.control_intersection.eq(inter)&result.direction.eq(direction)
        if phase=='Left':selection &= result.movement.eq(2)
        else:selection &= result.movement.isin([1,3]) | (result.movement.eq(2)&((acq,inter,direction,'Left') not in bank))
        if not selection.any():continue
        result.loc[selection,'signal_state']=lookup_state(result.loc[selection,'frame_id'],schedule)
        result.loc[selection,'signal_permission_status']=np.where(result.loc[selection,'movement'].eq(1),'THROUGH_PHASE_MAPPED','TURN_PERMISSION_REQUIRES_CONFLICT_OR_RIGHT_ON_RED_RULE')
        pos=mouths[mouths.intersection_id.eq(inter)&mouths.direction.eq(direction)&mouths.event.eq('ENTRY')].crossing_y_median_ft
        if len(pos) and np.isfinite(pos.iloc[0]) and direction in [2,4]:
            result.loc[selection,'distance_to_intersection_ft']=(pos.iloc[0]-result.loc[selection,'local_y'])*(1 if direction==2 else -1)
    stop=result.control_intersection.eq(4);result.loc[stop,'signal_state']='STOP_CONTROLLED'
    result.loc[stop,'signal_permission_status']='STOP_CONTROL_NOT_A_SIGNAL_PHASE'
    return result


def coverage(d,entry,exit,full_travel):
    intersection_times=annotation_travel_times(entry,exit)
    g=d.groupby('trajectory_key',sort=False)
    rows=[];section_times=[]
    fullkeys=set(full_travel.trajectory_key) if len(full_travel) else set()
    # Runs of Section/Intersection codes retain observed entrance/exit context.
    for key,q in g:
        first=q.iloc[0];last=q.iloc[-1]
        sections=sorted(set(q.section_id)-{0});ints=sorted(set(q.int_id)-{0})
        contexts=list(zip(q.section_id.to_numpy(),q.int_id.to_numpy()))
        starts=[0]+[i for i in range(1,len(contexts)) if contexts[i]!=contexts[i-1]]
        ends=starts[1:]+[len(q)]
        complete_sections=[]
        for begin,end in zip(starts,ends):
            section,inter=contexts[begin]
            if not section or begin==0 or end>=len(q):continue
            before=q.iloc[begin-1];after=q.iloc[end]
            if before.int_id>0 and after.int_id>0 and before.int_id!=after.int_id:
                complete_sections.append(int(section))
                section_times.append({'acquisition_id':first.acquisition_id,'trajectory_key':key,'vehicle_id':first.vehicle_id,
                    'metric':'section_travel_time','section_id':int(section),'entry_frame':int(q.iloc[begin].frame_id),
                    'exit_frame':int(after.frame_id),'travel_time_s':(after.frame_id-q.iloc[begin].frame_id)*.1,
                    'entry_y_ft':.5*(before.local_y+q.iloc[begin].local_y),'exit_y_ft':.5*(q.iloc[end-1].local_y+after.local_y),
                    'definition':'Observed int-to-section and section-to-next-int code boundaries, not first/last trajectory record'})
        crossing_count=int(intersection_times.trajectory_key.eq(key).sum()) if len(intersection_times) else 0
        if key in fullkeys:kind='CORRIDOR_TRAVERSAL_FIXED_CUTS'
        elif len(sections)>=2:kind='MULTI_SECTION_OBSERVED'
        elif complete_sections:kind='SECTION_COMPLETE_OBSERVED_BOUNDARIES'
        elif crossing_count:kind='INTERSECTION_CROSSING_OBSERVED_BOUNDARIES'
        else:kind='LOCAL_OBSERVATION_NOT_PROVEN_FRAGMENT'
        step=np.hypot(q.global_x.diff(),q.global_y.diff())
        rows.append({'acquisition_id':first.acquisition_id,'trajectory_key':key,'vehicle_id':first.vehicle_id,
            'first_section':int(first.section_id),'last_section':int(last.section_id),'first_intersection':int(first.int_id),
            'last_intersection':int(last.int_id),'origin':int(first.o_zone),'destination':int(first.d_zone),
            'duration_observed_s':(last.frame_id-first.frame_id)*.1,'distance_polyline_ft':step.sum(),
            'max_position_step_ft':step.max(),'sections_visited':len(sections),'section_ids':','.join(map(str,sections)),
            'intersections_visited':len(ints),'intersection_ids':','.join(map(str,ints)),
            'intersections_with_observed_entry_exit':crossing_count,'sections_with_observed_entry_exit':len(set(complete_sections)),
            'first_direction':int(first.direction),'last_direction':int(last.direction),'movement_first':int(first.movement),
            'frames_observed':len(q),'declared_total_frames':int(first.total_frames),
            'frames_match_declared':len(q)==first.total_frames,'frame_gap_count':int(q.frame_id.diff().gt(1).sum()),
            'trajectory_class':kind,'fragmentation_evidence':'NONE_FROM_COUNT_OR_TIME_GAPS; no cross-ID stitching attempted'})
    return pd.DataFrame(rows),pd.DataFrame(section_times),intersection_times


def handoff_candidates(d):
    """Probe possible cross-ID loss without ever joining or repairing identities."""
    rows=[]
    for acq,q in d.groupby('acquisition_id'):
        first=q.groupby('trajectory_key').head(1).sort_values('frame_id')
        last=q.groupby('trajectory_key').tail(1)
        start_frames=first.frame_id.to_numpy()
        for end in last.itertuples():
            begin=np.searchsorted(start_frames,end.frame_id+1)
            finish=np.searchsorted(start_frames,end.frame_id+11)
            candidates=first.iloc[begin:finish]
            candidates=candidates[candidates.v_class.eq(end.v_class)&candidates.direction.eq(end.direction)
                &candidates.v_length.sub(end.v_length).abs().le(.1+1e-9)&candidates.v_width.sub(end.v_width).abs().le(.1+1e-9)]
            for start in candidates.itertuples():
                dt=(start.frame_id-end.frame_id)*.1
                distance=float(np.hypot(start.global_x-end.global_x,start.global_y-end.global_y))
                if distance>2*np.hypot(2,4)+(start.v_vel+end.v_vel)/2*dt:continue
                rows.append({'acquisition_id':acq,'end_trajectory_key':end.trajectory_key,'start_trajectory_key':start.trajectory_key,
                    'end_frame':end.frame_id,'start_frame':start.frame_id,'gap_s':dt,'distance_ft':distance,
                    'class':end.v_class,'length_difference_ft':start.v_length-end.v_length,
                    'width_difference_ft':start.v_width-end.v_width,'end_int_id':end.int_id,'start_int_id':start.int_id,
                    'end_destination_code':end.d_zone,'start_origin_code':start.o_zone,
                    'status':'COMPATIBLE_CANDIDATE_NOT_IDENTITY_PROOF_NOT_STITCHED'})
    return pd.DataFrame(rows,columns=['acquisition_id','end_trajectory_key','start_trajectory_key','end_frame','start_frame','gap_s','distance_ft','class','length_difference_ft','width_difference_ft','end_int_id','start_int_id','end_destination_code','start_origin_code','status'])


def spatial_scopes(d):
    scopes=[];candidate_trips={};events_by_scope={}
    for name,lower,upper,definition in [
        ('A_FULL_CORRIDOR',80.,2050.,'Observed arterial cut-to-cut path; contains four signals and STOP I4; incomplete side-approach coverage'),
        ('B_TWO_INTERSECTION_REGION',YMIN,YMAX,'I2/I3 plus arterial approaches; entire observed population includes internal tracking appearances'),
        ('C_SINGLE_INTERSECTION_REGION',400.,900.,'I2 and approaches; offset/coordination not an internal intervention'),
        ('D_THROUGH_ARTERIAL_SUBCORRIDOR',YMIN,YMAX,'Only complete NB/SB through journeys between fixed cuts; excludes side/local journeys; conditional cohort model, not whole-network conservation')]:
        events=fixed_gate_crossings(d,lower,upper);trips=pair_travel_times(events,lower,upper)
        events_by_scope[name]=events;candidate_trips[name]=trips
        for acq,q in d.groupby('acquisition_id'):
            inside=q.local_y.between(lower,upper)
            first=q.groupby('trajectory_key').head(1);last=q.groupby('trajectory_key').tail(1)
            ev=events[events.acquisition_id.eq(acq)];tt=trips[trips.acquisition_id.eq(acq)]
            scopes.append({'scope':name,'acquisition_id':acq,'y_min_ft':lower,'y_max_ft':upper,
                'rows_in_y_band':int(inside.sum()),'vehicles_in_y_band':q.loc[inside,'trajectory_key'].nunique(),
                'physical_ns_entry_events':int((ev.event.eq('ENTRY')&~ev.spatial_discontinuity_flag).sum()),'physical_ns_exit_events':int((ev.event.eq('EXIT')&~ev.spatial_discontinuity_flag).sum()),
                'complete_cut_to_cut_trajectories':tt.trajectory_key.nunique(),
                'tracking_first_appearance_inside':int(first.local_y.between(lower,upper).sum()),
                'initial_appearance_inside_at_acquisition_first_frame':int((first.local_y.between(lower,upper)&first.frame_id.eq(q.frame_id.min())).sum()),
                'first_appearance_inside_after_acquisition_start':int((first.local_y.between(lower,upper)&first.frame_id.gt(q.frame_id.min())).sum()),
                'gate_crossings_flagged_spatial_discontinuity':int(ev.spatial_discontinuity_flag.sum()),
                'tracking_last_appearance_inside':int(last.local_y.between(lower,upper).sum()),
                'definition':definition,'recommended':name=='D_THROUGH_ARTERIAL_SUBCORRIDOR',
                'status':'CONDITIONAL_POPULATION_RESTRICTION' if name.startswith('D_') else 'FULL_POPULATION_BOUNDARY_CLOSURE_NOT_ESTABLISHED'})
            inside_rows=q.loc[inside]
            region_index=pd.MultiIndex.from_frame(inside_rows[['acquisition_id','frame_id','vehicle_id']])
            leader_index=pd.MultiIndex.from_arrays([inside_rows.acquisition_id,inside_rows.frame_id,inside_rows.preceding])
            follower_index=pd.MultiIndex.from_arrays([inside_rows.acquisition_id,inside_rows.frame_id,inside_rows.following])
            scopes[-1].update({'classes':','.join(map(str,sorted(inside_rows.v_class.unique()))),
                'movements':','.join(map(str,sorted(inside_rows.movement.unique()))),
                'lanes':','.join(map(str,sorted(inside_rows.lane_id.unique()))),
                'intersections_observed':','.join(map(str,sorted(set(inside_rows.int_id)-{0}))),
                'leader_valid_inside_y_band_pct':100*(inside_rows.preceding.ne(0)&leader_index.isin(region_index)).mean(),
                'follower_valid_inside_y_band_pct':100*(inside_rows.following.ne(0)&follower_index.isin(region_index)).mean(),
                'signal_coverage':'I1/I2/I3 arterial NB/SB confirmed; I5 NB confirmed / SB unobserved; I4 STOP' if name.startswith('A_') else 'I2/I3 arterial NB/SB confirmed' if not name.startswith('C_') else 'I2 arterial NB/SB confirmed; no internal coordination pair',
                'validation_indicators':'Fixed-cut traversal, speed/headway and temporal crossing counts; complete-cohort restrictions must be stated'})
    return pd.DataFrame(scopes),candidate_trips,events_by_scope


def study_population(d,trips,bank):
    eligible=[];exclusions=[]
    # No class behavior can be learned for the single observed motorcycle.
    for r in trips.itertuples():
        q=d[d.trajectory_key.eq(r.trajectory_key)&d.t_relative.ge(r.entry_time_s-.1)&d.t_relative.le(r.exit_time_s+.1)]
        problems=[]
        if not q.v_class.isin([2,3]).all():problems.append('CLASS1_SINGLE_OBSERVATION_OUT_OF_BASELINE_SCOPE')
        if not q.movement.eq(1).all():problems.append('NOT_STRAIGHT_THROUGH_ROUTE')
        if not q.direction.eq(r.direction).all():problems.append('DIRECTION_CODE_CHANGED_IN_CORE_ROUTE')
        if not problems:eligible.append(r._asdict())
        else:exclusions.append({'trajectory_key':r.trajectory_key,'reason':';'.join(problems)})
    selected=pd.DataFrame(eligible)
    keys=set(selected.trajectory_key)
    scope=d[d.trajectory_key.isin(keys)&d.local_y.between(YMIN,YMAX)].copy()
    # Labels observed throughout every relevant schedule; before that is UNKNOWN.
    known_start={}
    first=d.groupby('acquisition_id').frame_id.min().to_dict()
    for acq in ['B1','B2']:
        start=max(int(bank[(acq,i,di,'Thru')]['frames'][0]) for i in [2,3] for di in [2,4])
        known_start[acq]=(start-first[acq])*.1
    selected['valid_signal_window_start_s']=selected.acquisition_id.map(known_start)
    selected['eligible_for_complete_route_validation']=selected.entry_time_s.ge(selected.valid_signal_window_start_s)
    return scope,selected,pd.DataFrame(exclusions),known_start


def prepare_following(d,scope,lane_events):
    index=d.set_index(['acquisition_id','frame_id','vehicle_id'])
    leader=index.reindex(pd.MultiIndex.from_arrays([scope.acquisition_id,scope.frame_id,scope.preceding])).reset_index(drop=True)
    ego=scope.reset_index(drop=True).copy()
    sample_keys=pd.MultiIndex.from_frame(ego[['acquisition_id','frame_id','vehicle_id']])
    leader_keys=pd.MultiIndex.from_arrays([ego.acquisition_id,ego.frame_id,ego.preceding])
    ego['leader_speed']=leader.v_vel;ego['gap']=ego.space_headway-leader.v_length
    g=d.groupby('trajectory_key',sort=False)
    step=np.hypot(d.global_x-g.global_x.shift(),d.global_y-g.global_y.shift())
    nominal_error=2*np.hypot(2,4)
    suspicious=step>((d.v_vel+g.v_vel.shift())/2*.1+nominal_error)
    flags=pd.Series(suspicious.to_numpy(),index=pd.MultiIndex.from_frame(d[['acquisition_id','frame_id','vehicle_id']]))
    ego_suspicious=flags.reindex(sample_keys).fillna(False).to_numpy()
    leader_suspicious=flags.reindex(leader_keys).fillna(False).to_numpy()
    active=np.zeros(len(ego),dtype=bool)
    raw=lane_events[lane_events.int_id.eq(0)&lane_events.section_id.gt(0)]
    event_frames={k:np.sort(q.frame_id.to_numpy()) for k,q in raw.groupby('trajectory_key')}
    for key,idx in ego.groupby('trajectory_key').groups.items():
        ef=event_frames.get(key)
        if ef is None:continue
        fr=ego.loc[idx,'frame_id'].to_numpy();loc=np.searchsorted(ef,fr)
        diff=np.minimum(np.abs(fr-ef[np.maximum(loc-1,0)]),np.abs(fr-ef[np.minimum(loc,len(ef)-1)]))
        active[np.asarray(idx)]=diff<=10
    referred_key=ego.acquisition_id+':'+ego.preceding.astype(str)
    for key,idx in referred_key.groupby(referred_key).groups.items():
        ef=event_frames.get(key)
        if ef is None:continue
        fr=ego.loc[idx,'frame_id'].to_numpy();loc=np.searchsorted(ef,fr)
        diff=np.minimum(np.abs(fr-ef[np.maximum(loc-1,0)]),np.abs(fr-ef[np.minimum(loc,len(ef)-1)]))
        active[np.asarray(idx)] |= diff<=10
    mismatch=leader.lane_id.ne(ego.lane_id)|leader.direction.ne(ego.direction)|leader.section_id.ne(ego.section_id)
    rules={
        'NO_SAME_FRAME_LEADER':ego.preceding.eq(0)|leader.v_vel.isna(),
        'LEADER_OUTSIDE_STUDY_POPULATION_OR_GATE_BAND':~leader_keys.isin(sample_keys),
        'LEADER_CONTEXT_MISMATCH':mismatch,
        'INVALID_BUMPER_GAP':~ego.gap.gt(0),
        'SPATIAL_KINEMATIC_DISCONTINUITY':ego_suspicious|leader_suspicious,
        'ACCELERATION_AT_OBSERVED_SATURATION':np.isclose(ego.v_acc.abs(),12.27),
        'LANE_TRANSITION_ACTIVE_WINDOW':active,
        'AMBIGUOUS_SIGNAL_INTERSECTION_OR_LANE':ego.int_id.ne(0)|~ego.lane_id.isin([1,2,3])|~ego.control_intersection.isin([2,3])|~ego.signal_state.isin(['GREEN','YELLOW','RED'])|~ego.movement.eq(1),
        'HEADWAY_POSITION_DISAGREEMENT':(np.abs(leader.local_y-ego.local_y)-ego.space_headway).abs().gt(8),
    }
    reason={
        'NO_SAME_FRAME_LEADER':'Zero means no leader; nonzero absent references are invalid',
        'LEADER_OUTSIDE_STUDY_POPULATION_OR_GATE_BAND':'Do not calibrate responses to agents absent from the proposed limited model',
        'LEADER_CONTEXT_MISMATCH':'Same direction, section and lane required',
        'INVALID_BUMPER_GAP':'Front-to-front headway minus leader length must be positive',
        'SPATIAL_KINEMATIC_DISCONTINUITY':'Step distance > mean reported speed*0.1s + 2*hypot(2ft,4ft); accuracy-derived diagnostic, not a guaranteed error bound',
        'ACCELERATION_AT_OBSERVED_SATURATION':'Exact observed +/-12.27ft/s^2 accumulation; no inference of true extreme acceleration',
        'LANE_TRANSITION_ACTIVE_WINDOW':'Within +/-1s of an observed road lane-label transition; descriptive maneuver exclusion, not a reaction parameter',
        'AMBIGUOUS_SIGNAL_INTERSECTION_OR_LANE':'Road approaches controlled by I2/I3 only; no intersection interior, special lanes or unknown phases',
        'HEADWAY_POSITION_DISAGREEMENT':'Absolute front-to-front positional discrepancy >8ft (two nominal 4ft longitudinal errors)'}
    filters=[];excluded=np.zeros(len(ego),dtype=bool)
    for name,mask in rules.items():
        mask=np.asarray(mask,dtype=bool);excluded |= mask
        for acq,indices in ego.groupby('acquisition_id').groups.items():
            idx=np.asarray(indices);filters.append({'acquisition_id':acq,'rule':name,'reason':reason[name],
                'rows_affected':int(mask[idx].sum()),'denominator_scope_rows':len(idx),'percentage':100*mask[idx].mean(),
                'overlap_note':'Nonexclusive flags; do not sum rows affected','status':'DRAFT_BEFORE_CALIBRATION_NOT_SELECTED_ON_MODEL_ERRORS'})
    ego['ego_speed']=ego.v_vel;ego['relative_speed']=ego.leader_speed-ego.ego_speed;ego['acceleration']=ego.v_acc
    ego['lane']=ego.lane_id;ego['section']=ego.section_id
    kept=ego[~excluded]
    columns=['acquisition_id','trajectory_key','vehicle_id','frame_id','t_relative','ego_speed','leader_speed','relative_speed','gap','acceleration','lane','movement','direction','section','signal_state','control_intersection','distance_to_intersection_ft','v_class','local_x','local_y']
    folder=OUT/'working';folder.mkdir(exist_ok=True)
    manifest=[]
    for acq in ['B1','B2']:
        sample=kept[kept.acquisition_id==acq][columns]
        path=folder/f'peachtree_cf_preparation_{acq}.parquet';sample.to_parquet(path,index=False,compression='zstd')
        manifest.append({'acquisition_id':acq,'rows':len(sample),'vehicles':sample.trajectory_key.nunique(),
            'path':str(path.relative_to(ROOT)),'sha256':digest(path),'unit_speed':'ft/s','unit_gap':'ft','unit_acceleration':'ft/s^2',
            'signal_distance_reference':'Observed median intersection entry annotation; NOT_SURVEYED_STOP_BAR',
            'purpose':'POTENTIAL_TRAIN_ONLY_AFTER_APPROVAL' if acq=='B2' else 'CURRENT_RECONSTRUCTION_DIAGNOSTIC; NOT_FOR_FUTURE_FITTING_AFTER_FREEZE'})
    return kept,pd.DataFrame(filters),manifest


def scope_comparison(d,scope,selected,known_start,kept,confirmed):
    rows=[]
    for acq in ['B1','B2']:
        q=scope[scope.acquisition_id==acq];tt=selected[selected.acquisition_id==acq];cf=kept[kept.acquisition_id==acq]
        classes=q.groupby('trajectory_key').v_class.first().value_counts().to_dict()
        lc=confirmed[confirmed.acquisition_id.eq(acq)&confirmed.trajectory_key.isin(q.trajectory_key.unique())&confirmed.local_y.between(YMIN,YMAX)]
        rows.append({'acquisition_id':acq,'role_proposed':'TRAIN' if acq=='B2' else 'TEST','gate_region':'400 <= Local_Y <= 1400 ft',
            'scope_population':'Class2/3 complete constant-direction through journeys; not entire observed network population',
            'scope_rows':len(q),'scope_vehicles':q.trajectory_key.nunique(),'class_counts':json.dumps(classes),
            'directions':','.join(map(str,sorted(q.direction.unique()))),'movements':','.join(map(str,sorted(q.movement.unique()))),
            'lanes_observed':','.join(map(str,sorted(q.lane_id.unique()))),'speed_min_ft_s':q.v_vel.min(),'speed_max_ft_s':q.v_vel.max(),
            'speed_mean_ft_s':q.v_vel.mean(),'speed_median_ft_s':q.v_vel.median(),'gap_kept_median_ft':cf.gap.median(),
            'cf_rows_kept':len(cf),'cf_vehicles_kept':cf.trajectory_key.nunique(),'physical_entries_cohort':len(tt),
            'physical_exits_cohort':len(tt),'complete_route_validation_after_known_phase_count':int(tt.eligible_for_complete_route_validation.sum()),
            'route_travel_time_median_s':tt.travel_time_s.median(),'route_travel_time_mean_s':tt.travel_time_s.mean(),
            'confirmed_lane_changes_in_scope':len(lc),'known_all_target_signal_start_s':known_start[acq],
            'internal_unobserved_births_in_selected_cohort':0,'selected_cohort_conservation':'entered=exited; complete paired paths only',
            'full_population_conservation':'NOT_CLAIMED; omitted local/turning/initial observations remain external',
            'test_frozen':False,'contract_status':'DRAFT_REQUIRES_SCOPE_AND_POPULATION_APPROVAL'})
    return pd.DataFrame(rows)


def main():
    start=time.perf_counter();source_hash=digest(SOURCE)
    if not (OUT/'archive/peachtree1_signal_inventory.csv').exists():
        (OUT/'archive').mkdir(exist_ok=True);shutil.copy2(OUT/'peachtree_signal_inventory.csv',OUT/'archive/peachtree1_signal_inventory.csv')
    d,clock=canonicalize(pd.read_csv(SOURCE));original_hashes={'data/peachtree_full.csv':source_hash}
    inventories=inventory()
    tubes,cameras,cad_status=auxiliary_profiles()
    for r in inventories:
        if not r['member'] and r['sha256']:original_hashes[r['path']]=r['sha256']
    entry,exit=annotated_crossings(d)
    sections,intersections,lanes,movements,mouths=geometry(d,entry,exit)
    bank,signal_inventory,timeline=load_signals(d)
    sync=signal_verification(d,entry,mouths,bank)
    for i in intersections.intersection_id:
        z=sync[sync.intersection_id.eq(i)&sync.direction.isin([2,4])]
        complete=(len(z)==4 and z.status.eq('SIGNAL_SYNC_CONFIRMED').all())
        intersections.loc[intersections.intersection_id==i,'signal_sync_status']='NOT_APPLICABLE_STOP_CONTROL' if i==4 else 'SIGNAL_SYNC_CONFIRMED' if complete else 'SIGNAL_SYNC_PROBABLE' if z.status.eq('SIGNAL_SYNC_CONFIRMED').any() else 'SIGNAL_SYNC_UNRESOLVED'
    d=attach_signal_context(d,mouths,bank)
    scope_options,trips_by_scope,scope_events=spatial_scopes(d)
    trajectories,section_times,intersection_times=coverage(d,entry,exit,trips_by_scope['A_FULL_CORRIDOR'])
    handoffs=handoff_candidates(d)
    scope,selected,exclusions,known_start=study_population(d,trips_by_scope['D_THROUGH_ARTERIAL_SUBCORRIDOR'],bank)
    lane_events=confirm_lane_changes(d);confirmed=lane_events[lane_events.confirmed].copy()
    kept,filters,cf_manifest=prepare_following(d,scope,lane_events)
    compare=scope_comparison(d,scope,selected,known_start,kept,confirmed)
    selected_events=scope_events['D_THROUGH_ARTERIAL_SUBCORRIDOR']
    selected_events=selected_events[selected_events.trajectory_key.isin(selected.trajectory_key)]
    class_counts=trajectories.groupby(['acquisition_id','trajectory_class']).size().reset_index(name='vehicles')
    class_counts['percentage']=100*class_counts.vehicles/class_counts.acquisition_id.map(trajectories.groupby('acquisition_id').size())
    timing=[]
    source_fingerprints={'B1':{2:1092,3:23},'B2':{1:1,2:1199,3:22}}
    for acq,q in d.groupby('acquisition_id'):
        classes=q.groupby('trajectory_key').v_class.first().value_counts().to_dict()
        if classes!=source_fingerprints[acq]:raise RuntimeError('Acquisition/document class fingerprint no longer matches')
        delta=q.groupby('trajectory_key').frame_id.diff().dropna()
        if not delta.eq(1).all():raise RuntimeError('Frame clock no longer contiguous')
        timing.append({'acquisition_id':acq,'label':acq+'_TIME_RELATIVE','first_frame':q.frame_id.min(),
            'last_frame':q.frame_id.max(),'unique_frames':q.frame_id.nunique(),'rows':len(q),'vehicles':q.trajectory_key.nunique(),
            'relative_start_s':0,'relative_end_s':q.t_relative.max(),'dominant_delta_s':.1,'intervals_at_dominant_pct':100.,
            'civil_recording_label_from_report':'12:45-13:00 detection, tracking to 13:02:01' if acq=='B1' else '16:00-16:15 detection, tracking to 16:17:13',
            'civil_label_evidence':'Exact Table1 total/class fingerprint and matching tracking tail duration; not decoded Global_Time',
            'epoch_status':'NOT_USED_OR_CORRECTED','formula':'(Frame_ID - first_frame_of_acquisition) * 0.1',
            'all_target_signal_known_from_relative_s':known_start[acq],'test_frozen':False})
    # Direct crossings are physical measured gates; not the first/last record.
    boundaries=[]
    for boundary,y in [('SOUTH_CUT',YMIN),('NORTH_CUT',YMAX)]:
        for event in ['ENTRY','EXIT']:
            z=selected_events[selected_events.boundary.eq(boundary)&selected_events.event.eq(event)]
            boundaries.append({'boundary':boundary,'event':event,'local_y_ft':y,
                'direction':2 if (boundary=='SOUTH_CUT' and event=='ENTRY') or (boundary=='NORTH_CUT' and event=='EXIT') else 4,
                'measurement':'Front-center sign crossing from two consecutive observations, interpolated <=0.1s',
                'scope':'Selected complete class2/3 through-route cohort only','B1_events':int(z.acquisition_id.eq('B1').sum()),
                'B2_events':int(z.acquisition_id.eq('B2').sum()),'geometry_status':'DEFINED_TRANSVERSE_MEASUREMENT_CUT_IN_DOCUMENTED_SECTION_NOT_CURB_OR_STUDY_EDGE'})
    throughput=selected_events[~selected_events.spatial_discontinuity_flag].copy()
    throughput['time_bin_start_s']=(throughput.t_cross_s//30).astype(int)*30
    throughput=throughput.groupby(['acquisition_id','boundary','event','time_bin_start_s']).agg(crossings=('trajectory_key','size'),distinct_vehicle_keys=('trajectory_key','nunique')).reset_index()
    # Source-level short observations are classified by coverage, never assumed
    # to be a complete corridor journey or stitched to another numeric ID.
    short=trajectories.duration_observed_s.lt(5)
    short_stats=trajectories.assign(short=short).groupby(['acquisition_id','short','first_direction','last_direction']).agg(vehicles=('trajectory_key','size'),median_duration_s=('duration_observed_s','median')).reset_index()
    summary={'phase':'PEACHTREE-2','source_sha256':source_hash,'clock':clock,
        'acquisition_association_status':'DOCUMENTARY_FINGERPRINT_CONFIRMED; RAW_EPOCH_UNRESOLVED_AND_UNUSED',
        'classification':'SYSTEM_RECONSTRUCTION_PARTIAL','decision':'AJUSTAR A SUBCORREDOR',
        'selected_scope':'D_THROUGH_ARTERIAL_SUBCORRIDOR','selected_spatial_interval_ft':[YMIN,YMAX],
        'scope_population_restriction':'Complete class2/3 NB/SB straight-through trajectories between physical measurement cuts; not full mixed-turn network',
        'scope_caveat':'Omitted turning/local streams influence real through traffic; cohort closure is not full-network closure. Must approve reduced claim; baseline validity remains to be tested.',
        'gis_camera_polygon_count':len(cameras),'tube_original_files_inspected':len(tubes),'cad_status':cad_status,
        'intersections':intersections.to_dict('records'),'scope_comparison':compare.to_dict('records'),
        'signal_sync_counts':sync.status.value_counts().to_dict(),'signal_files_txt':32,
        'confirmed_lane_changes_by_acquisition':confirmed.groupby('acquisition_id').size().to_dict(),
        'raw_lane_transitions_by_acquisition':lane_events.groupby('acquisition_id').size().to_dict(),
        'compatible_id_handoff_candidates':len(handoffs),'confirmed_id_handoffs':0,
        'handoff_protocol':'1..10 frames between end/start, same class/direction, dimensions within0.1ft, distance within nominal position allowance + movement; compatibility only, no stitching',
        'cf_preparation':cf_manifest,'recommended_train':'B2','recommended_test':'B1',
        'split_recommendation':'Conditional on approving restricted through-population model and external interaction limitations; no approval/freeze executed',
        'test_frozen':False,'calibration_performed':False,'abm_implemented':False,'signal_offset_optimized':False,
        'source_hashes':original_hashes,'performance':{'elapsed_seconds':round(time.perf_counter()-start,3),'peak_working_set_mb':peak_memory_mb()}}
    def records(frame):return frame.to_dict('records')
    for name,frame in [
        ('peachtree_source_inventory.csv',inventories),('peachtree_acquisition_timing.csv',timing),
        ('peachtree_tube_data_profile.csv',tubes),('peachtree_camera_coverage.csv',cameras),
        ('peachtree_code_dictionary.csv',code_dictionary(d)),('peachtree_sections.csv',sections),
        ('peachtree_intersections.csv',intersections),('peachtree_lanes.csv',lanes),('peachtree_movements.csv',movements),
        ('peachtree_intersection_mouths.csv',mouths),('peachtree_signal_inventory.csv',signal_inventory),
        ('peachtree_controller_pdf_parameters.csv',controller_pdf_transcription()),
        ('peachtree_signal_sync.csv',sync),('peachtree_signal_timeline.csv',timeline),
        ('peachtree_trajectory_coverage.csv',trajectories),('peachtree_trajectory_classes.csv',class_counts),
        ('peachtree_short_trajectory_diagnosis.csv',short_stats),('peachtree_entry_boundaries.csv',[r for r in boundaries if r['event']=='ENTRY']),
        ('peachtree_id_handoff_candidates.csv',handoffs),
        ('peachtree_exit_boundaries.csv',[r for r in boundaries if r['event']=='EXIT']),
        ('peachtree_physical_gate_events.csv',selected_events),('peachtree_fixed_gate_travel_times.csv',selected),
        ('peachtree_scope_population_exclusions.csv',exclusions),('peachtree_section_travel_times.csv',section_times),
        ('peachtree_intersection_travel_times.csv',intersection_times),('peachtree_throughput_crossings.csv',throughput),
        ('peachtree_quality_filters.csv',filters),('peachtree_lane_transition_classification.csv',lane_events),
        ('peachtree_confirmed_lane_changes.csv',confirmed),('peachtree_spatial_scope_comparison.csv',scope_options),
        ('peachtree_train_test_scope_comparison.csv',compare),('peachtree_cf_preparation_manifest.csv',cf_manifest)]:csv(name,frame)
    # JSON has no non-standard NaN values.
    summary=json.loads(json.dumps(summary,default=safe_json))
    def clean(v):
        if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
        if isinstance(v,list):return [clean(x) for x in v]
        if isinstance(v,float) and not np.isfinite(v):return None
        return v
    summary=clean(summary)
    if digest(SOURCE)!=source_hash:raise RuntimeError('Original vehicle CSV modified')
    (OUT/'peachtree_system_audit.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    from scripts.peachtree_system_report import write_reports
    write_reports(summary,trajectories,class_counts,compare,sync,filters,sections)
    spatial_figure(d,intersections)
    print(json.dumps({'classification':summary['classification'],'decision':summary['decision'],'scope':records(compare),
        'signals':summary['signal_sync_counts'],'lane_changes':summary['confirmed_lane_changes_by_acquisition'],'cf':cf_manifest,
        'performance':summary['performance']},indent=2,default=safe_json))


def spatial_figure(d,intersections):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    fig,ax=plt.subplots(figsize=(7,9),layout='constrained')
    count=ax.hist2d(d.local_x,d.local_y,bins=[120,430],range=[[-60,60],[0,2150]],norm=LogNorm(),cmap='Greys')
    fig.colorbar(count[3],ax=ax,label='Vehicle-frame observations')
    ax.axhspan(YMIN,YMAX,color='tab:blue',alpha=.08)
    for r in intersections.itertuples():
        ax.axhspan(r.observed_y_min_ft,r.observed_y_max_ft,alpha=.15,color='tab:orange')
        ax.text(43,r.observed_y_median_ft,f'I{r.intersection_id}: {r.street}',fontsize=9)
    for cut in [YMIN,YMAX]:ax.axhline(cut,color='tab:blue',linestyle='--',linewidth=2)
    ax.set(xlabel='Local_X (ft), +/-60ft view of arterial',ylabel='Local_Y (ft)',
        title='Peachtree: observed extent and defined measurement cuts\nNot a surveyed curb/stop-line plan')
    (OUT/'figures').mkdir(exist_ok=True)
    fig.savefig(OUT/'figures/peachtree_reconstructed_scope.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
