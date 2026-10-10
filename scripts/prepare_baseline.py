"""Freeze authorized scope, isolate B2, and declare criteria BEFORE rollouts."""
import json,csv
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd

from simulation.training_data import ROOT,read_train_csv,extract_b2_source,load_b2_cf
from simulation.parameters import FOOT_M
from scripts.evaluate_local import digest

CRITERIA={
 'v0':'Prespecified P85 positive speed of no-leader normal-lane road observations; next signal GREEN or no next signal; exclude saturation and kinematic jumps. P50/P95 bounds. Amendment before any successful rollout: original sample mostly starts, not free cruise.',
 'T':'Median valid reported Time_Headway in cleaned moving GREEN CF sample at or above median strictly positive CF speed; front-to-front seed, then calibrated net-gap parameter',
 's0':'Median positive cleaned CF bumper gap at exactly reported zero speed',
 'a':'Median strictly positive nonsaturated cleaned CF acceleration',
 'b':'Median absolute strictly negative nonsaturated cleaned CF acceleration',
 'bounds':'Prespecified empirical P10/P90 of each estimation sample; median is initial candidate. Bounds not selected on visual fit.',
 'queue_proxy':'Exactly stopped connected lane chain; adjacency gap bounded by TRAIN standstill-gap P90. Numerical zero tolerance1e-6m/s; no cognitive threshold.',
 'yellow':'Inspect B2 sample first; conservative comfortable-stopping-distance rule if no stable decision rule identifiable.',
 'calibration_seeds':[10,11,12], 'final_train_seeds':list(range(1000,1030)),
 'delta':{'value':4,'classification':'LITERATURE_DERIVED','source':'https://mtreiber.de/MicroApplet/IDM.html'},
 'objective_components':['mean_speed_relative_error','speed_W1_normalized','headway_W1_normalized','route_time_relative_error','stopped_fraction_absolute_error','throughput_temporal_normalized_error'],
 'objective_weights':'Equal arithmetic mean of individually reported dimensionless errors; missing exits/unfinished demand add explicit feasibility penalty',
 'optimization':'Bounded deterministic parameter search followed by Powell; candidate score is average of fixed development seeds, never best seed'}

def main():
 out=ROOT/'outputs';out.mkdir(exist_ok=True)
 criteria_path=ROOT/'docs/b2_estimation_criteria.json'
 if criteria_path.exists():
  if json.loads(criteria_path.read_text())!=CRITERIA:raise RuntimeError('Estimation criteria changed; explicit amendment required')
 else:criteria_path.write_text(json.dumps(CRITERIA,indent=2),encoding='utf-8')
 trips=read_train_csv(out/'peachtree_fixed_gate_travel_times.csv')
 for col in ['entry_time_s','exit_time_s','entry_frame','exit_frame','direction','vehicle_id']:
  trips[col]=pd.to_numeric(trips[col])
 if len(trips)!=276:raise RuntimeError('Authorized B2 cohort changed')
 source=ROOT/'data/peachtree_full.csv';rawpath=ROOT/'data/b2_baseline_source.parquet'
 if not rawpath.exists():extract_b2_source(source,set(trips.trajectory_key)).to_parquet(rawpath,index=False,compression='zstd')
 d=pd.read_parquet(rawpath)
 if not d.acquisition_id.eq('B2').all():raise RuntimeError('Holdout contamination')
 signals=read_train_csv(out/'peachtree_signal_timeline.csv')
 signals=signals[signals.intersection_id.isin(['2','3'])&signals.direction.isin(['2','4'])&signals.phase.eq('Thru')]
 for col in ['intersection_id','direction','start_frame','end_frame_exclusive','t_start_s','t_end_s']:
  signals[col]=pd.to_numeric(signals[col])
 start=93.4;start_frame=936;end=1032.7
 mouth=pd.read_csv(out/'peachtree_intersection_mouths.csv') # Approved static reconstruction, not behavioral TEST metrics.
 stop=[]
 for inter in [2,3]:
  for direction in [2,4]:
   line=float(mouth[(mouth.intersection_id==inter)&(mouth.direction==direction)&mouth.event.eq('ENTRY')].crossing_y_median_ft.iloc[0])
   stop.append({'intersection':inter,'direction':direction,'local_y_ft':line,
       'reference':'APPROVED_OBSERVED_INTERSECTION_MOUTH_PROXY_NOT_SURVEYED_PAINTED_STOP_BAR','classification':'ASSUMPTION_SUPPORTED_BY_RECONSTRUCTION'})
 initial=[];attrs={}
 for key,q in d.groupby('trajectory_key',sort=True):
  first=q.iloc[0];attrs[key]={'vehicle_class':int(first.v_class),'length_m':float(first.v_length*FOOT_M),'width_m':float(first.v_width*FOOT_M)}
  row=q[q.frame_id==start_frame]
  if row.empty:continue
  r=row.iloc[0];lane=int(r.lane_id)
  if lane not in [1,2,11]:
   prior=q[q.frame_id<=start_frame];prior=prior[prior.lane_id.isin([1,2,11])]
   lane=int(prior.lane_id.iloc[-1]) if len(prior) else 1
  initial.append({**attrs[key],'position_m':float((r.local_y-400 if r.direction==2 else 1400-r.local_y)*FOOT_M),
      'lane':lane,'speed_m_s':float(r.v_vel*FOOT_M),'direction':int(r.direction),'movement':1,
      'initial_age_s':float(start-trips.set_index('trajectory_key').loc[key,'entry_time_s']),
      'source_key_for_boundary_audit_only':key})
 gate=read_train_csv(out/'peachtree_physical_gate_events.csv')
 for col in ['t_cross_s','direction','lane_id','v_vel','vehicle_id']:gate[col]=pd.to_numeric(gate[col])
 gate=gate[gate.event.eq('ENTRY')&gate.t_cross_s.ge(start)]
 entries=[];entry_speeds={}
 for r in gate.sort_values(['t_cross_s','vehicle_id']).itertuples():
  lane=int(r.lane_id);lane=lane if lane in [1,2,11] else 1
  entries.append({**attrs[r.trajectory_key],'requested_time_s':float(r.t_cross_s-start),'lane':lane,'direction':int(r.direction),
      'movement':1,'boundary':r.boundary,'source_key_for_boundary_audit_only':r.trajectory_key})
  entry_speeds.setdefault(str(int(r.direction)),[]).append(float(r.v_vel*FOOT_M))
 bay=[]
 for direction in [2,4]:
  q=d[(d.direction==direction)&(d.lane_id==11)]
  if len(q):bay.append({'direction':direction,'observed_y_min_ft':float(q.local_y.min()),'observed_y_max_ft':float(q.local_y.max()),
      'model_role':'LOGICAL_THROUGH_CONNECTOR_TO_LANE1; NOT_A_NEW_STREET','classification':'ASSUMPTION_FOR_AMBIGUOUS_THROUGH_COHORT_BAY_LABEL'})
 inputs={'acquisition_id':'B2','source_window_start_relative_s':start,'source_window_start_frame':start_frame,'horizon_s':end-start,
      'dt':.1,'initial':initial,'entries':entries,'entry_speed_samples_m_s':entry_speeds,'signals':signals.to_dict('records'),
      'network':{'y_min_ft':400.,'y_max_ft':1400.,'main_lanes':[1,2],'stop_lines':stop,'bay_connectors':bay},
      'requested_entry_count':len(entries),'initial_count':len(initial),
      'note':'No internal historical trajectories/speeds are passed to the engine after initialization.'}
 inputpath=ROOT/'data/b2_exogenous_inputs.json';inputpath.write_text(json.dumps(inputs,indent=2),encoding='utf-8')
 filters=read_train_csv(out/'peachtree_quality_filters.csv')
 sources=[source,rawpath,inputpath,criteria_path,out/'working/peachtree_cf_preparation_B2.parquet',out/'peachtree_signal_timeline.csv',
     out/'peachtree_intersection_mouths.csv',ROOT/'simulation/training_data.py']
 freeze={'phase':'PEACHTREE-3','dataset':'NGSIM Peachtree Street','dataset_sha256':digest(source),
   'client_date':'2026-10-09','created_utc':datetime.now(timezone.utc).isoformat(),
   'scope':{'local_y_ft':[400,1400],'population':'ARTERIAL_THROUGH_COHORT','classes':[2,3],'train_cohort_eligible':276,'test_cohort_eligible_from_authorized_prior_summary':251,
       'intersections':[2,3],'streets':['11th','12th'],'sections':[2,3,4],'boundaries':['SOUTH_CUT400','NORTH_CUT1400'],
       'limitations':['Omitted turning/local interactions','Stop bars represented by previously reconstructed annotation mouths','Lane11 through labels require logical connector assumption']},
   'TRAIN':'B2','TEST':'B1','B1_LOCKED':True,'validation_description':'TEMPORAL/ACQUISITION HOLDOUT VALIDATION WITH PRIOR FEASIBILITY SUMMARY EXPOSURE',
   'dt_s':.1,'simulation_window_B2_relative_s':[start,end],'signal_series':[{'intersection':i,'direction':di,'phase':'Thru','acquisition':'B2'} for i in [2,3] for di in [2,4]],
   'quality_filters':filters[['rule','reason']].drop_duplicates().to_dict('records'),
   'preprocessing_version':'PEACHTREE3-TRAIN-ONLY-v2','estimation_criteria':CRITERIA,
   'hashes':{str(p.relative_to(ROOT)):digest(p) for p in sources},
   'authorization':'Explicit user instruction approving reduced scope and B2/B1 lock; no blind-validation claim',
   'freeze_kind':'SCOPE_DATA_METRICS_CRITERIA; behavior model may be revised using TRAIN only, with run version recorded'}
 freeze_path=out/'baseline_scope_freeze.json'
 if freeze_path.exists():
  old=json.loads(freeze_path.read_text(encoding='utf-8'))
  for field in ['scope','TRAIN','TEST','dt_s','hashes','estimation_criteria']:
   if old[field]!=freeze[field]:raise RuntimeError('Frozen design changed: '+field)
 else:freeze_path.write_text(json.dumps(freeze,indent=2),encoding='utf-8')
 (ROOT/'docs/baseline_methodology.md').write_text('''# PEACHTREE-3: approved baseline methodology

Official scope: class2/3 arterial through-cohort around11th/12th, Local_Y400–1400ft.
TRAIN=B2, TEST=B1. B1 is locked from this phase for calibration, selection, visual
adjustment and optimization. The correct future label is temporal/acquisition
holdout validation with prior feasibility summary exposure, never fully blind.

Source hash, geometry, quality filters, clocks, signal series, preprocessing and
predeclared estimation/search criteria are frozen in outputs/baseline_scope_freeze.json.
Source files are untouched. The mixed source is routed by frame/time acquisition
metadata before numeric behavioral values are parsed; B1 data is not returned.

Physical dt=0.1s. Start at B2 relative93.4s (frame936), when the four Through
signals are known, and end at1032.7s. Existing agents use one initial snapshot;
later inputs are observed entry times/boundaries/classes/routes/dimensions.
Entry speeds are sampled from a fixed B2 boundary-speed distribution by direction,
with AgentPy-seeded randomness. Internal position/speed/acceleration histories
are never supplied to the simulation. Waiting upstream when insertion is unsafe
is measured explicitly rather than forcing an overlap or moving an agent.

The longitudinal physics uses SI; US survey foot=1200/3937m. IDM is pooled over
classes2/3. Delta4 is literature-derived; v0,T,s0,a,b are initialized by frozen
B2 criteria and then calibrated using aggregate TRAIN errors. No visual fitting.

The stop-line reference is the previously approved observed intersection-mouth
proxy, not a surveyed painted bar. Lane0 at initialization carries the last valid
B2 approach lane; lane11 through records are represented as logical connectors
requiring safe merge to lane1. Neither assumption adds a street. Discretionary
lane changes remain simplified unless the small B2 sample supports a stable rule.

The reduced cohort omits local/turning streams that affect real traffic. This is
a material limitation, not full-network conservation or proof of counterfactual
benefit. Inputs are exogenous boundary conditions, not trajectory replay.

All data-dependent rules are TRAIN-only. Signals use recorded B2 schedules;
there is no offset/green optimization. E1/E2/E3 remain disabled until a later
baseline validation decision. Model changes and calibration versions are logged.
''',encoding='utf-8')
 print(json.dumps({'scope_frozen':True,'B1':'LOCKED','b2_source_rows':len(d),'initial_count':len(initial),
     'exogenous_entries':len(entries),'entry_lanes':pd.Series([x['lane'] for x in entries]).value_counts().to_dict(),
     'initial_lanes':pd.Series([x['lane'] for x in initial]).value_counts().to_dict(),'horizon_s':inputs['horizon_s']}))

if __name__=='__main__':main()
