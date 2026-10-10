import unittest,tempfile,json
from pathlib import Path
import numpy as np
import pandas as pd
from calibration.structural_metrics import stopped,STOP_FT_S,stop_episodes,phase_stopping,temporal,discharge,release_delays,queues
from calibration.structural import full_b2,main as diagnose
from simulation.training_data import HoldoutLockedError,ROOT
from simulation.signals import SignalController,SignalInterval
from simulation.model import run_baseline
from simulation.parameters import IDMParameters,FOOT_M
from test_baseline import inputs,vehicle,P

def observations(speeds,frames=None):
    if frames is None:frames=list(range(len(speeds)))
    return pd.DataFrame({'id':['A']*len(speeds),'frame':frames,'time':np.array(frames)*.1,'speed':speeds,
        'phase':['RED']*len(speeds),'intersection':[2]*len(speeds),'distance':[10.]*len(speeds),
        'direction':[2]*len(speeds),'lane':[1]*len(speeds),'length':[15.]*len(speeds)})

class StructuralMeasurementTests(unittest.TestCase):
    def test_operational_classifier_external_rule(self):
        self.assertEqual(stopped([0.,STOP_FT_S,STOP_FT_S+1e-5]).tolist(),[True,True,False])
    def test_stop_episode_censoring_and_duration(self):
        q=observations([0.,0.,1.,0.,1.]);e=stop_episodes(q)
        self.assertEqual(len(e),2);self.assertAlmostEqual(e.duration_s.iloc[0],.2);self.assertTrue(e.left_censored.iloc[0]);self.assertFalse(e.right_censored.iloc[0])
    def test_missing_frame_splits_episode(self):
        q=observations([0.,0.,1.],[0,2,3]);e=stop_episodes(q)
        self.assertEqual(len(e),2);self.assertTrue(e.right_censored.iloc[0])
    def test_phase_conditioned_denominator(self):
        q=observations([0.,1.,0.]);q.loc[2,'phase']='GREEN';a=phase_stopping(q,'TEST')
        self.assertEqual(a[a.phase=='RED'].operational_stopped_fraction.iloc[0],.5);self.assertEqual(a[a.phase=='GREEN'].operational_stopped_fraction.iloc[0],1.)
    def test_queue_connected_and_head_blocked(self):
        q=observations([0.,0.,0.]);q['id']=['A','B','C'];q['frame']=0;q['time']=0.;q['distance']=[10.,30.,100.]
        result,ts=queues(q,'TEST',10.,0.);self.assertEqual(result[result.direction==2]['max'].max(),2)
        q.loc[0,'speed']=2.;result,_=queues(q,'TEST',10.,0.);self.assertEqual(result['max'].max(),0)
    def test_temporal_throughput_counts_and_timing(self):
        q=observations([1.]*30);_,flow=temporal(q,q,np.array([1.,2.]),np.array([1.5,2.5]),30.,'TEST')
        self.assertTrue((flow.real_total==2).all());self.assertTrue((flow.simulated_total==2).all());self.assertTrue(np.allclose(flow.timing_bias_s,.5))
    def test_empty_occupancy_is_not_zero_speed(self):
        a=observations([1.,1.,1.,1.],[0,1,100,101]);b=observations([1.,1.],[0,1])
        metrics,_=temporal(a,b,np.array([]),np.array([]),30.,'TEST')
        speed=metrics[metrics.metric.eq('speed')&metrics.bin_s.eq(10.)].iloc[0]
        self.assertEqual(speed.bins_compared,1);self.assertEqual(speed.RMSE,0.)
    def test_discharge_lane_specific(self):
        bank={(2,2):SignalController(2,2,[SignalInterval(0,10,'GREEN')])}
        c=pd.DataFrame({'intersection':[2]*3,'direction':[2]*3,'lane':[1,1,2],'time':[1.,3.,2.]})
        a=discharge(c,{},bank,'TEST');self.assertEqual(a.headway_s.tolist(),[2.])
    def test_release_delay_observable(self):
        bank={(2,2):SignalController(2,2,[SignalInterval(0,.2,'RED'),SignalInterval(.2,1.,'GREEN')])}
        q=observations([0.,0.,0.,1.,1.]);a=release_delays(q,bank,'TEST');self.assertAlmostEqual(a.release_delay_s.iloc[0],.1)
    def test_b1_forbidden_in_diagnostics(self):
        from calibration.run_revision import main as run_revision
        from scripts.audit_peachtree3r import main as audit_revision
        from scripts.finish_peachtree3r import main as finish_revision
        for f in [full_b2,diagnose,run_revision,audit_revision,finish_revision]:
            with self.assertRaises(HoldoutLockedError):f('B1')
    def test_release_hold_physical_and_single_event(self):
        d=inputs([vehicle(200*FOOT_M-P.s0,0.)],state='RED',release=10.)
        d['revision']={'operational_stop_m_s':.1,'signal_release_delay_s':1.6,'queue_head_window_ft':100.}
        a=run_baseline(d,P,steps=110);self.assertLessEqual(a.all_agents[0].speed,.1);self.assertEqual(len(a.release_events),1)
        b=run_baseline(d,P,steps=117);self.assertGreater(b.all_agents[0].speed,.1);self.assertEqual(len(b.release_events),1)
        self.assertGreaterEqual(b.all_agents[0].position,a.all_agents[0].position)
    def test_target_background_physical_interaction(self):
        background=dict(vehicle(8.,0.),agent_role='BACKGROUND')
        a=run_baseline(inputs([vehicle(0.,7.),background]),P,steps=10)
        b=run_baseline(inputs([vehicle(0.,7.)]),P,steps=10)
        self.assertLess(a.all_agents[0].position,b.all_agents[0].position);self.assertEqual(a.recorder.times[-1]['background_active'],1)
        self.assertEqual(a.recorder.times[-1]['target_active'],1);a.assert_invariants()
    def test_stopline_geometry_preserved(self):
        from simulation.training_data import load_inputs
        from simulation.network import PeachtreeEnvironment
        d=load_inputs();n=PeachtreeEnvironment(d['network'])
        expected={(2,2):632.5395,(2,4):777.262,(3,2):1168.9155,(3,4):1240.7775}
        for l in n.stop_lines:self.assertAlmostEqual(l.local_y_ft,expected[(l.intersection,l.direction)])
    def test_aligned_crossing_interpolation(self):
        from calibration.structural_metrics import crossings
        d=observations([2.,2.]);d['y']=[499.,501.]
        c=crossings(d,{'network':{'stop_lines':[{'direction':2,'intersection':2,'local_y_ft':500.}]}})
        self.assertAlmostEqual(c.time.iloc[0],.05)
    def test_omitted_leader_classification(self):
        from calibration.structural import leader_audit
        d=pd.DataFrame({'preceding':[2,3,4,0],'speed':[0.]*4})
        lead=pd.DataFrame({'vehicle_id':[2.,3.,4.,np.nan],'v_class':[2.,2.,2.,np.nan],'local_y':[500.,600.,1600.,np.nan]})
        valid=pd.Series([True,True,True,False]);a=leader_audit(d,lead,valid,{'B2:2'})
        z=a[a.subset=='ALL_PRECEDING_REFERENCES'];self.assertEqual(z[z.category=='A_TARGET'].frames.iloc[0],1);self.assertEqual(z[z.category=='B_EXCLUDED_CLASS23_IN_BAND'].frames.iloc[0],1);self.assertEqual(z[z.category=='C_OTHER_OBSERVED'].frames.iloc[0],1)
    def test_safe_insertion_phase_change_accounted(self):
        from calibration.structural import DiagnosticModel
        event={**vehicle(),'requested_time_s':0.};d=inputs([vehicle()],[event],state='RED',release=.2)
        m=DiagnosticModel({'steps':100,'seed':10},inputs=d,idm=P,trace=False,queue_gap=3.);m.run(display=False)
        for row in m.arrival_audit:self.assertAlmostEqual(row['delay'],row['actual_entry_time']-row['scheduled_entry_time'])
    def test_fifo_boundary_does_not_allow_overtaking(self):
        from simulation.model import PeachtreeModel
        d=inputs([vehicle(10.,0.)],[dict(vehicle(),requested_time_s=0.,_sampled_speed=12.),dict(vehicle(),requested_time_s=.01,_sampled_speed=0.)],state='RED')
        d['revision']={'safe_insertion_fifo':True}
        m=PeachtreeModel({'steps':1,'seed':10},inputs=d,idm=P,trace=False,queue_gap=3.);m.sim_setup();m.insert_arrivals(.1)
        self.assertEqual(m.entered,0);self.assertEqual(len(m.demand.pending),2);m.assert_invariants()
    def test_old_mode_physics_matches_original(self):
        from simulation.training_data import load_inputs
        p=IDMParameters.load(ROOT/'outputs/b2_calibrated_parameters.json');m=run_baseline(load_inputs(),p,seed=10)
        saved=pd.read_csv(ROOT/'outputs/b2_real_vs_simulated.csv').set_index('indicator')
        self.assertAlmostEqual(m.summary['mean_speed_ft_s'],saved.loc['speed','simulated_mean'],places=10)
        self.assertAlmostEqual(m.summary['mean_travel_time_s'],saved.loc['route_travel_time','simulated_mean'],places=10)
    def test_ui_rejects_holdout_revision_filename(self):
        from ui.streamlit_app import read_revision_csv
        with self.assertRaises(PermissionError):read_revision_csv('b1_metrics.csv')
    def test_revised_engine_has_no_source_reader_after_init(self):
        from unittest.mock import patch
        d=inputs([vehicle(200*FOOT_M-P.s0,0.)],state='RED',release=1.)
        d['revision']={'operational_stop_m_s':.1,'signal_release_delay_s':1.6,'queue_head_window_ft':100.,'safe_insertion_fifo':True}
        with patch('simulation.training_data.load_b2_source',side_effect=AssertionError('Historical replay prohibited')):
            m=run_baseline(d,P,steps=40)
        self.assertGreater(m.all_agents[0].speed,.1)
    def test_old_artifact_preservation(self):
        p=ROOT/'outputs/peachtree3r/old_baseline_manifest.json'
        if not p.exists():self.skipTest('Preservation manifest not yet finalized')
        from scripts.evaluate_local import digest
        for name,sha in json.loads(p.read_text(encoding='utf-8'))['hashes'].items():self.assertEqual(digest(ROOT/name),sha)

if __name__=='__main__':unittest.main()
