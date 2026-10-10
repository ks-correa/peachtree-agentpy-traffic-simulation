"""Read-only source audit. Never treats detector observations as trajectories."""
from pathlib import Path
import csv, io, zipfile, hashlib, json, time, tempfile, shutil, re, ctypes

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'Vehicle_ID', 'Frame_ID', 'Global_Time', 'Local_X', 'Local_Y', 'Lane_ID'}

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def parse_csv(stream):
    return csv.reader(io.TextIOWrapper(stream, encoding='utf-8-sig', newline=None), skipinitialspace=True)

def is_trajectory(columns):
    return REQUIRED.issubset({c.strip() for c in columns})

def period_from_path(path):
    m = re.search(r'(\d{4}pm-\d{4}pm)', path)
    return m.group(1) if m else None

def inventory(path):
    rows = []
    with zipfile.ZipFile(path) as outer:
        for item in outer.infolist():
            rows.append(dict(path=item.filename, size_bytes=item.file_size, compressed_bytes=item.compress_size, format=Path(item.filename).suffix, directory=item.is_dir(), period=period_from_path(item.filename)))
            if item.filename.lower().endswith('.zip'):
                # Disk spool avoids loading aerial imagery into RAM; no images/videos decoded.
                with tempfile.TemporaryFile() as spool:
                    with outer.open(item) as src: shutil.copyfileobj(src, spool, 1024*1024)
                    spool.seek(0)
                    with zipfile.ZipFile(spool) as nested:
                        for child in nested.infolist():
                            rows.append(dict(path=item.filename+'!'+child.filename, size_bytes=child.file_size, compressed_bytes=child.compress_size, format=Path(child.filename).suffix, directory=child.is_dir(), period=period_from_path(child.filename)))
    return rows

def write_csv(out, name, fields, rows):
    with (out/name).open('w', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

def peak_memory_mb():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    c=Counters(); c.cb=ctypes.sizeof(c)
    handle=ctypes.windll.kernel32.GetCurrentProcess
    handle.restype=ctypes.c_void_p
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(handle()),ctypes.byref(c),c.cb): return round(c.PeakWorkingSetSize/1024**2,2)
    return None

def main():
    start=time.perf_counter(); out=ROOT/'outputs'; out.mkdir(exist_ok=True)
    candidates=sorted(ROOT.glob('**/I-80-Emeryville-CA.zip'))
    if len(candidates)!=1: raise RuntimeError('Expected exactly one I-80 source ZIP')
    source=candidates[0]; before=digest(source); rows=inventory(source)
    write_csv(out,'dataset_inventory.csv',list(rows[0]),rows)
    with zipfile.ZipFile(source) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read('i-80-detector-data.zip'))) as z:
            hashes={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.endswith(('.csv','.txt'))}
            with z.open('detector-data/detector-data.csv') as stream:
                reader=parse_csv(stream); columns=next(reader); assert not is_trajectory(columns)
                count=0; missing=0; malformed=0; duplicates=0; keys=set(); stations=set(); times=set(); prev={}; nonmonotonic=0
                for row in reader:
                    if not row: continue
                    count+=1; missing+=sum(v.strip()=='' for v in row)
                    if len(row)!=len(columns): malformed+=1; continue
                    sid=row[0]; t=int(row[2]); key=(sid,t)
                    duplicates+=key in keys; keys.add(key); stations.add(sid); times.add(t)
                    if sid in prev and t<=prev[sid]: nonmonotonic+=1
                    prev[sid]=t
    reason='MISSING_VEHICLE_TRAJECTORIES'
    checks=['missing_values','exact_duplicates','vehicle_frame_duplicates','vehicle_time_monotonicity','impossible_positions','negative_velocity','extreme_acceleration','negative_headway','missing_preceding','missing_following','unexpected_lane_id','impossible_lane_changes','position_discontinuities','tracking_errors','smoothing','cross_period_vehicle_identity']
    audit=dict(classification='NOT_VIABLE_FOR_AGENTPY',scope='LOCAL_FILES_ONLY',reason=reason,trajectory_files=0,trajectory_rows=0,unique_vehicles=None,detector=dict(rows=count,columns=columns,stations=sorted(stations),timestamps=len(times),global_time_min=min(times),global_time_max=max(times),timestamp_step_ms=sorted({b-a for a,b in zip(sorted(times), sorted(times)[1:])}),missing_cells=missing,malformed_rows=malformed,duplicate_station_time_keys=duplicates,nonmonotonic_station_rows=nonmonotonic,csv_txt_same_bytes=len(set(hashes.values()))==1,sha256=hashes),trajectory_checks={c:dict(status='NOT_EVALUABLE',value=None,reason=reason) for c in checks},sources={str(source.relative_to(ROOT)):before},missing_metadata='I-80 Metadata Documentation.pdf',unrelated_metadata='data/1-_US_101_Metadata_Documentation.pdf')
    for pdf in sorted((ROOT/'data').glob('*.pdf')): audit['sources'][str(pdf.relative_to(ROOT))]=digest(pdf)
    periods=sorted({r['period'] for r in rows if r['period']})
    write_csv(out,'period_summary.csv',['period','source_type','vehicles','rows','mean_speed','density','status'],[dict(period=p,source_type='AGGREGATE_PDF_REPORT',vehicles='',rows='',mean_speed='',density='',status=reason) for p in periods])
    for file,metrics in {'car_following_summary.csv':['gap_acceleration_correlation','relative_speed_acceleration_correlation','leader_valid_percentage','follower_valid_percentage','reciprocity'], 'lane_change_summary.csv':['total_changes','vehicles_with_changes','changes_per_vehicle','time_between_changes'], 'merge_summary.csv':['merging_vehicles','merge_time','merge_speed','merge_headway']}.items():
        write_csv(out,file,['metric','value','status'],[dict(metric=m,value='',status=reason) for m in metrics])
    params=['desired_speed','reaction/headway behavior','safe_gap','acceleration distribution','deceleration distribution','lane-change tendency','merge behavior','vehicle class proportions','arrival pattern','flow distribution']
    write_csv(out,'parameter_identifiability.csv',['parameter','source','method','classification','identifiable','future_use'],[dict(parameter=p,source='Unavailable trajectory data',method='Not estimable',classification='CALIBRATED' if p in params[:3] else 'DATASET_DERIVED',identifiable='NO_WITH_LOCAL_FILES',future_use='Conditional; classification is intended future method, not an estimate') for p in params])
    indicators={'mean_speed':'PRIMARY_VALIDATION','speed_distribution':'PRIMARY_VALIDATION','acceleration':'SECONDARY_VALIDATION','Space_Headway':'PRIMARY_VALIDATION','Time_Headway':'SECONDARY_VALIDATION','flow':'PRIMARY_VALIDATION','density':'PRIMARY_VALIDATION','travel_time':'PRIMARY_VALIDATION','lane_changes':'SECONDARY_VALIDATION','queue':'SECONDARY_VALIDATION','braking_waves':'SECONDARY_VALIDATION','throughput':'PRIMARY_VALIDATION'}
    write_csv(out,'validation_indicator_candidates.csv',['indicator','classification','local_status','requirement'],[dict(indicator=k,classification=v,local_status='NOT_EVALUABLE_FOR_RESERVED_TRAJECTORIES',requirement='Classification conditional on obtaining trajectories, geometry and independent TEST') for k,v in indicators.items()])
    strategies=[('A','P1+P2','P3'),('B','P1','P2'),('C','P1 then P1+P2','P2 then P3')]
    write_csv(out,'train_test_strategy_comparison.csv',['strategy','train','test','train_vehicles','train_rows','train_duration','test_vehicles','test_rows','test_duration','traffic_condition','leakage_risk','distribution_shift','status'],[dict(strategy=a,train=b,test=c,train_vehicles='',train_rows='',train_duration='',test_vehicles='',test_rows='',test_duration='',traffic_condition='Unknown from trajectories',leakage_risk='Cannot verify IDs or physical identity across periods',distribution_shift='Not calculable',status=reason) for a,b,c in strategies])
    write_csv(out,'train_test_transferability.csv',['indicator','difference_mean','difference_median','ks_statistic','wasserstein_distance','status'],[dict(indicator=i,difference_mean='',difference_median='',ks_statistic='',wasserstein_distance='',status='NOT_RUN_NO_TRAIN_TEST_TRAJECTORIES') for i in ['speed','acceleration','headway','vehicle_class','lane_change_frequency']])
    write_csv(out,'scenario_feasibility.csv',['scenario','changed_rule','experimental_parameter','indicator','status'],[dict(scenario=s,changed_rule=r,experimental_parameter=p,indicator=i,status='CONCEPTUAL_ONLY_BASELINE_NOT_VALIDATABLE_LOCALLY') for s,r,p,i in [('E1','Ramp arrival timing','Meter interval','Ramp queue, throughput'),('E2','Speed control','Speed target','Speed, travel time'),('E3','Both','Interval and speed target','Queue, throughput, travel time')]])
    assert digest(source)==before, 'Source modified'
    audit['performance']=dict(detector_rows_processed=count,trajectory_rows_processed=0,elapsed_seconds=round(time.perf_counter()-start,3),peak_process_working_set_mb=peak_memory_mb(),memory_scope='Entire audit process; Windows peak working set, excludes temporary disk spool')
    (out/'data_quality_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'detector':audit['detector'],'performance':audit['performance'],'inventory_entries':len(rows)},ensure_ascii=False))

if __name__=='__main__': main()
