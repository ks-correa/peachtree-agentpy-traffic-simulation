"""TRAIN-only access boundary. B1 is locked for PEACHTREE-3.

Mixed legacy CSVs are routed on acquisition before reading numerical targets.
The mixed raw source is routed on frame/time metadata, before parsing movement.
Runtime simulation receives only exogenous inputs and one initial snapshot.
"""
import csv,json
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
TRAIN='B2'

class HoldoutLockedError(PermissionError):pass

def require_train(acquisition):
    if acquisition!='B2':raise HoldoutLockedError('B1 LOCKED: no calibration, model selection or development metrics')

def read_train_csv(path,acquisition='B2'):
    require_train(acquisition)
    rows=[]
    with Path(path).open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            label=row.get('acquisition_id',row.get('component'))
            if label!='B2':continue
            rows.append(row)
    return pd.DataFrame(rows)

def extract_b2_source(source,keys):
    rows=[]
    with Path(source).open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            # Only routing metadata is inspected for non-TRAIN rows.
            if int(row['global_time'])-100*int(row['frame_id'])!=1163030300:continue
            if 'B2:'+row['vehicle_id'] not in keys:continue
            if not 400<=float(row['local_y'])<=1400:continue
            rows.append(row)
    d=pd.DataFrame(rows)
    for col in d.columns:
        if col!='location':d[col]=pd.to_numeric(d[col],errors='raise')
    d['acquisition_id']='B2';d['trajectory_key']='B2:'+d.vehicle_id.astype(str)
    d['t_relative']=(d.frame_id-2)*.1
    return d.sort_values(['vehicle_id','frame_id'],kind='stable').reset_index(drop=True)

def load_b2_source(acquisition='B2'):
    require_train(acquisition)
    return pd.read_parquet(ROOT/'data/b2_baseline_source.parquet')

def load_b2_cf(acquisition='B2'):
    require_train(acquisition)
    data=pd.read_parquet(ROOT/'outputs/working/peachtree_cf_preparation_B2.parquet')
    if not data.acquisition_id.eq('B2').all():raise HoldoutLockedError('Mixed data in TRAIN preparation')
    return data

def load_inputs(acquisition='B2'):
    require_train(acquisition)
    inputs=json.loads((ROOT/'data/b2_exogenous_inputs.json').read_text(encoding='utf-8'))
    if inputs['acquisition_id']!='B2':raise HoldoutLockedError('Non-TRAIN inputs')
    return inputs
