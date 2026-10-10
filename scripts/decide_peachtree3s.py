"""Scope decision on physical observation evidence, before simulated fit."""
import json
import numpy as np
import pandas as pd
from calibration.receiving import OUT,LAST,full_b2,real_targets,leaders,crossing_events
from calibration.receiving_scope import NEW_EXIT
from calibration.structural_metrics import STOP_FT_S
from simulation.training_data import ROOT,load_b2_source,load_inputs,require_train
from simulation.signals import controllers_from_inputs

def main(acquisition='B2'):
    require_train(acquisition);f=full_b2();d=pd.read_parquet(OUT/'target_full_downstream_observations.parquet');bank=controllers_from_inputs(load_inputs())
    q=d[d.speed.le(STOP_FT_S)&d.region.eq('POST_CONTROL_REGION')].copy();q['last_phase']=[bank[(3 if di==2 else 2,int(di))].at(tm) for di,tm in zip(q.cohort_direction,q.time)]
    q.groupby(['cohort_direction','int_id','lane','last_phase']).agg(frames=('id','size'),vehicles=('id','nunique'),min_y=('y','min'),median_y=('y','median'),max_y=('y','max')).reset_index().to_csv(OUT/'post_control_own_intersection_audit.csv',index=False)
    nb=d[d.cohort_direction.eq(2)&d.y.between(1246.452,1400)&d.speed.le(STOP_FT_S)]
    sb=d[d.cohort_direction.eq(4)&d.y.between(597.878,647.878)&d.speed.le(STOP_FT_S)]
    rows=[]
    for di in [2,4]:
        for name,mask in [('INSIDE_13TH_INTERSECTION',d.y.between(1586.464,1653.066)),('APPROACH_13TH_150FT',d.y.between(1436.464,1586.464))]:
            z=d[d.cohort_direction.eq(di)&mask]
            rows.append({'direction':di,'region':name,'observed_rows':len(z),'vehicles':z.id.nunique(),'operational_stopped_frames':z.speed.le(STOP_FT_S).sum(),'movements':str(sorted(z.movement.unique().tolist()))})
    pd.DataFrame(rows).to_csv(OUT/'thirteenth_control_diagnostic.csv',index=False)
    receiving=f[(f.direction==4)&f.v_class.isin([2,3])&f.t_relative.ge(93.4)&f.local_y.lt(647.878)&f.v_vel.le(STOP_FT_S)]
    rear=float((receiving.local_y+receiving.v_length).max())
    gap=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['queue_gap_m']/(1200/3937)
    buffer_audit=[]
    for width in [25.,50.,100.]:
        cut=647.878-width;clearance=cut-rear
        buffer_audit.append({'direction':4,'physical_discharge_buffer_ft':width,'candidate_exit_ft':cut,'maximum_observed_receiving_stopped_rear_ft':rear,
            'clearance_ft':clearance,'required_standstill_gap_plus_position_allowance_ft':gap+4.,'passes_physical_clearance':clearance>=gap+4.,
            'rule':'largest predeclared buffer with receiving stopped vehicle BODY separated by existing B2 gapP90 + official nominal longitudinal4ft allowance; no SIM fit'})
    pd.DataFrame(buffer_audit).to_csv(OUT/'physical_buffer_selection.csv',index=False)
    mechanisms=[
        ('NEXT_SIGNAL','10thSB/14thNB schedules and target stop clusters observed','NB has zero receiving stops inside current exit;10thSB future turning/context demand is not closed','Schedule yes; full receiving-agent system no','B2 full + afternoon report + signalTXT','MEDIUM','Multiple movements/context agents',True),
        ('STOP_CONTROL','13th atNB1589.104,189.104ft beyond current1400','No targetNB operational stops in1500..1678; STOP sign/priority by approach not assigned','No essential arterial priority/gap law','Official report intersection4 STOP + B2','LOW','Priority/conflict interactions',True),
        ('FINITE_RECEIVING_CAPACITY','Conditional stopped upstream/downstream and discharge gaps observed SB','Observed exits confound demand/control; cannot estimate supply by copying outflow','No capacity/service law identified','B2 current boundary flow and frame observations','MEDIUM','Needs independent supply or downstream model',True),
        ('QUEUE_SPILLBACK','SB stopped followers with stopped leaders near400 and10th','NB proxy-post stops are own12th, not13th spillback; no causal backward-wave identification','Footprint observable; external rule not identified','B2 leaders/speeds/positions','MEDIUM','Downstream controls plus exogenous context',True),
        ('LANE_DROP','Two normal lanes before/afternext intersections','No supported lane drop; bays distinct from normal lanes','No identified drop','B2 lane labels + official schematic','LOW','Unneeded topology',False),
        ('TURNING_INTERACTION','Target paths may turn after original exits; lane11/context seen','Proximity is not causal conflict or identifiable gap acceptance','Routes partly observed; complete conflict priorities no','B2 movement/O-D/lane','MEDIUM','Turning paths/conflicts',True),
        ('BACKGROUND_LEADER','SB post-region omitted references measurable','Omitted share does not materially rise inside current post region; NBvalid-stopped-leader0','Arrivals/context not closed for full downstream system','B2 same-frame references','MEDIUM','Additional autonomous routes',True),
        ('BOUNDARY_OBSERVATION_ARTIFACT','Some stop episodes right-censored; rawspeed precision/jitter','Many complete stop/release episodes nearknown control, cannot call them tracking artifacts','Observation state, not new physics','B2 full track endpoints','MEDIUM','Measurement/censoring',False),
        ('OTHER_OWN_CONTROL_REGION_MISCLASSIFICATION','4304NB proxy-post stopped frames allY1174..1192;4064RED12th; zero afterfullI3 to1400','Annotation mouths are not surveyed bars; do not derive new paintedbar solely fromstops','Region classification identifiable; lane-specific physical stop reference still uncertain','B2 intersection labels + frozen I3proxy','HIGH','Correct interpretation/controlled-area audit',False)]
    pd.DataFrame(mechanisms,columns=['mechanism','evidence','counterevidence','parameters_identifiable','data_source','confidence','complexity','agent_based_interaction_required']).to_csv(OUT/'mechanism_candidates.csv',index=False)
    freeze={'phase':'PEACHTREE-3S','decision':'B. FREEZE_REDUCED_SCOPE','selection_basis':'Physical junction envelopes and receiving body clearance, selected before any new SIM score. Direction-specific exits preserve original observed upstream approach entries.',
        'entry_ft':{'NB':400.,'SB':1400.},'exit_ft':{'NB':NEW_EXIT[2],'SB':NEW_EXIT[4]},'route_lengths_ft':{'NB':NEW_EXIT[2]-400.,'SB':1400.-NEW_EXIT[4]},
        'keeps_intersections':[2,3],'NB_discharge_buffer_ft':100.,'SB_discharge_buffer_ft':50.,'SB_receiving_body_max_y_ft':rear,'SB_body_clearance_ft':NEW_EXIT[4]-rear,
        'target_stopped_frames_in_retained_NB_postjunction':len(nb[nb.y<=NEW_EXIT[2]]),'target_stopped_frames_in_retained_SB_postjunction':len(sb),
        'IDM_changed':False,'threshold_changed':False,'stoplines_changed':False,'offsets_changed':False,'new_background_agents':0,
        'seeds_paired':list(range(3000,3030)),'reference_seed':210,'B1_LOCKED':True,
        'scenario_interpretation':'11th/12th performance conditional on observed inputs and the reduced receiving cuts; no claim about full network or effects at10th/14th.',
        'readiness':'B. NEEDS_ONE_MORE_STRUCTURAL_REVISION','readiness_reason':'Large external SB stopping footprint excluded and NB falsely called receiving is own12th. Before finalB2 calibration, audit B2 lane-specific controlled-region/front reference (classification past nominal proxy) without fitting offsets/IDM or inventing a stopbar.',
        'next_step':'Resolve the B2 control/reference representation inside11th/12th; keep reduced receiving boundaries frozen and B1 locked.'}
    (OUT/'decision.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
    # Directional candidates and formal comparison include full approaches.
    specs=pd.read_csv(OUT/'scope_candidates.csv');specs['selected']=False;specs['receiving_observability']='Insufficient for autonomous extension; candidate receiving effects must be screened'
    selected={'candidate':'REDUCED_DIRECTIONAL_DISCHARGE','low_ft':np.nan,'high_ft':np.nan,'length_ft':np.nan,'vehicles_observed':274,
        'complete_route_vehicles':253,'north_entry_ft':400.,'north_exit_ft':NEW_EXIT[2],'south_entry_ft':1400.,'south_exit_ft':NEW_EXIT[4],
        'keeps_11th_12th':True,'selected':True,'physical_interpretability':'Preserve observed ingress approaches; terminate afterfull junction bylargest physically separated candidate buffer per direction',
        'receiving_observability':'No target operational stopped inretained truepost-junction buffers; known external queue footprint outsidecuts',
        'scenario_relevance':'Both signals and intersignal road retained; conditional receiving interpretation only'}
    comparison=pd.concat([specs,pd.DataFrame([selected])],ignore_index=True);comparison.to_csv(OUT/'scope_comparison.csv',index=False)
    (OUT/'selection_order.json').write_text(json.dumps({'scope_decided_before_SIM_evaluation':True,'sim_fit_used_for_cut_selection':False,'physics_extension_authorized':False,'B1_LOCKED':True},indent=2),encoding='utf-8')
    print(json.dumps(freeze,indent=2))
if __name__=='__main__':main()
