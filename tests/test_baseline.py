import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
import agentpy as ap
from simulation.agents import VehicleAgent,ballistic,idm_acceleration
from simulation.model import run_baseline,PeachtreeModel,PhysicsInvariantError,STEP_ORDER
from simulation.network import PeachtreeEnvironment
from simulation.parameters import IDMParameters,DT,FOOT_M
from simulation.signals import SignalController,SignalInterval
from simulation.training_data import HoldoutLockedError,load_inputs,load_b2_source,load_b2_cf,read_train_csv,ROOT
from calibration.objective import TrainTargets
from calibration.diagnostics import estimate_parameters
from calibration.calibrate import main as calibrate

P=IDMParameters(12.,1.5,2.,1.5,2.) # Synthetic test fixture, never deployed parameters.
def vehicle(position=0.,speed=0.,lane=1,direction=2):
    return dict(vehicle_class=2,length_m=4.,width_m=1.8,position_m=position,speed_m_s=speed,lane=lane,direction=direction,movement=1)
def inputs(initial=None,entries=None,state='GREEN',release=None,horizon=100.):
    signals=[]
    for di in [2,4]:
        parts=[(0.,horizon+1.,state)] if release is None else [(0.,release,state),(release,horizon+1.,'GREEN')]
        for start,end,s in parts:signals.append(dict(intersection_id=2,direction=di,t_start_s=start,t_end_s=end,state=s))
    return dict(acquisition_id='B2',dt=.1,horizon_s=horizon,source_window_start_relative_s=0.,initial=initial or [],entries=entries or [],
        entry_speed_samples_m_s={'2':[3.,5.,7.],'4':[4.]},signals=signals,network=dict(y_min_ft=400.,y_max_ft=1400.,main_lanes=[1,2],
        stop_lines=[dict(intersection=2,direction=2,local_y_ft=600.),dict(intersection=2,direction=4,local_y_ft=600.)]))
def model(data,steps=500,seed=10):return run_baseline(data,P,steps=steps,seed=seed)

class BaselineEngineTests(unittest.TestCase):
    def test_actual_agentpy_classes(self):
        m=model(inputs([vehicle()]),1);self.assertIsInstance(m,ap.Model);self.assertIsInstance(m.all_agents[0],VehicleAgent);self.assertIsInstance(m.all_agents[0],ap.Agent)
    def test_free_flow_acceleration(self):
        m=model(inputs([vehicle()]),200);self.assertGreater(m.all_agents[0].speed,11.);self.assertLessEqual(m.all_agents[0].speed,P.v0)
    def test_slow_leader(self):
        a=idm_acceleration(10.,12.,3.,P);self.assertLess(a,0.);self.assertLess(a,idm_acceleration(10.,None,0.,P))
    def test_red_stop(self):
        m=model(inputs([vehicle(speed=8.)],state='RED'),800);v=m.all_agents[0];self.assertLess(v.position,200*FOOT_M);self.assertLess(v.speed,1e-5);self.assertEqual(v.state,'STOPPED_SIGNAL')
    def test_green_release(self):
        m=model(inputs([vehicle(speed=8.)],state='RED',release=50.),650);self.assertGreater(m.all_agents[0].position,200*FOOT_M)
    def test_leader_follower_selection(self):
        m=model(inputs([vehicle(0.,8.),vehicle(12.,1.),vehicle(4.,5.,lane=2)]),1)
        self.assertEqual(m.all_agents[0].leader_id,m.all_agents[1].agent_id);self.assertEqual(m.all_agents[1].follower_id,m.all_agents[0].agent_id);self.assertIsNone(m.all_agents[2].leader_id)
    def test_no_overlap_and_nonnegative(self):
        m=model(inputs([vehicle(0.,12.),vehicle(5.,0.)],state='RED'),900)
        self.assertGreaterEqual(m.all_agents[1].position-m.all_agents[1].length-m.all_agents[0].position,0.);self.assertTrue(all(v.speed>=0 for v in m.all_agents));m.assert_invariants()
    def test_invalid_initial_overlap_rejected(self):
        with self.assertRaises(PhysicsInvariantError):model(inputs([vehicle(0.),vehicle(2.)]),1)
    def test_exit_state(self):
        m=model(inputs([vehicle(303.,10.)]),10);self.assertEqual(m.exited,1);self.assertEqual(len(m.agents),0);self.assertEqual(m.all_agents[0].state,'EXITED');self.assertIsNotNone(m.all_agents[0].exit_time)
    def test_conservation_every_tick(self):
        event={**vehicle(),'requested_time_s':.5};m=model(inputs([vehicle(80.,5.)],[event]),500)
        for r in m.recorder.times:self.assertEqual(r['initial_vehicles']+r['vehicles_entered'],r['vehicles_active']+r['vehicles_exited'])
    def test_same_seed(self):
        event={**vehicle(),'requested_time_s':.5};a=model(inputs(entries=[event]),100,77);b=model(inputs(entries=[event]),100,77)
        self.assertEqual(a.summary,b.summary);self.assertEqual(a.all_agents[0].position,b.all_agents[0].position)
    def test_order_independence(self):
        data=inputs([vehicle(0.,9.),vehicle(10.,2.),vehicle(5.,3.,lane=2)])
        a=model(data,80);b=model(inputs(list(reversed(data['initial']))),80)
        self.assertEqual(sorted((round(x.position,9),round(x.speed,9),x.lane) for x in a.all_agents),sorted((round(x.position,9),round(x.speed,9),x.lane) for x in b.all_agents))
    def test_dt_and_si(self):
        self.assertEqual(DT,.1);dx,v=ballistic(10.,2.,DT);self.assertAlmostEqual(dx,1.01);self.assertAlmostEqual(v,10.2)
        self.assertAlmostEqual(1000*FOOT_M,PeachtreeEnvironment(inputs()['network']).length)
        m=model(inputs([vehicle()]),10);self.assertAlmostEqual(m.simulation_time,1.)
    def test_ballistic_stop_inside_tick(self):
        dx,v=ballistic(1.,-20.,.1);self.assertEqual(v,0.);self.assertAlmostEqual(dx,.025)
    def test_signal_boundaries(self):
        c=SignalController(2,2,[SignalInterval(1.,2.,'RED'),SignalInterval(2.,3.,'YELLOW'),SignalInterval(3.,4.,'GREEN')])
        self.assertEqual([c.at(t) for t in [0,1,2,3,4]],['UNKNOWN','RED','YELLOW','GREEN','UNKNOWN'])
    def test_yellow_conservative_stop(self):
        m=model(inputs([vehicle(speed=6.)],state='YELLOW'),700);self.assertLess(m.all_agents[0].position,200*FOOT_M)
    def test_step_order(self):
        self.assertEqual(STEP_ORDER,('signals','arrivals','leaders_followers','lane_changes','accelerations','velocities','positions','boundary_crossings','EXITED','metrics'))
    def test_wrong_dt_rejected(self):
        d=inputs();d['dt']=1.
        with self.assertRaises(ValueError):model(d,1)
    def test_unsafe_entry_queues(self):
        m=model(inputs([vehicle()],[{**vehicle(),'requested_time_s':0.}],state='RED'),1)
        self.assertEqual(m.entered,0);self.assertEqual(len(m.demand.pending),1)
    def test_no_historical_replay_input(self):
        d=inputs([vehicle()]);a=model(d,30);d['real_position_t']=[999]*30;d['real_speed_t']=[999]*30;b=model(d,30)
        self.assertEqual(a.all_agents[0].position,b.all_agents[0].position);self.assertEqual(a.all_agents[0].speed,b.all_agents[0].speed)

class TrainBoundaryTests(unittest.TestCase):
    def test_b1_forbidden_before_io(self):
        for function in [load_inputs,load_b2_source,load_b2_cf,TrainTargets,estimate_parameters,calibrate]:
            with self.assertRaises(HoldoutLockedError):function('B1')
    def test_mixed_legacy_routed_before_numeric(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'mixed.csv';p.write_text('acquisition_id,value\nB1,DO_NOT_PARSE\nB2,3\n')
            self.assertEqual(read_train_csv(p).value.tolist(),['3'])
    def test_only_b2_parameters_load(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'p.json';p.write_text(json.dumps({'training_acquisition':'B1','parameters':{}}))
            with self.assertRaises(ValueError):IDMParameters.load(p)
    def test_exogenous_schema_no_replay_arrays(self):
        d=load_inputs();self.assertEqual(d['acquisition_id'],'B2');self.assertNotIn('trajectories',d)
        for e in d['entries']:self.assertNotIn('position_m',e);self.assertNotIn('speed_m_s',e);self.assertNotIn('acceleration',e)
    def test_parameters_reject_nonfinite(self):
        for v in [float('nan'),float('inf'),0.,-1.]:
            with self.assertRaises(ValueError):IDMParameters(v,1.,1.,1.,1.)
    def test_ui_has_no_physics(self):
        s=(ROOT/'ui/streamlit_app.py').read_text(encoding='utf-8');self.assertNotIn('idm_acceleration',s);self.assertNotIn('agent.position =',s);self.assertIn('run_baseline',s);self.assertNotIn('working/peachtree_cf_preparation_B1',s)
    def test_scenarios_disabled_and_playback_separate(self):
        s=(ROOT/'ui/streamlit_app.py').read_text(encoding='utf-8');self.assertIn('disabled=True',s);self.assertIn('Disponibles después de validación del modelo base',s)
        js=(ROOT/'ui/canvas_renderer.py').read_text(encoding='utf-8');self.assertIn('requestAnimationFrame',js);self.assertNotIn('run_baseline',js)

if __name__=='__main__':unittest.main()
