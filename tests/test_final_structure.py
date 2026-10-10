"""3U physical invariants, using synthetic scenes and existing B2-only artifacts."""
import json,unittest
from unittest.mock import patch
import pandas as pd
from calibration.final_structure import references,LEGACY,final_inputs,run_final,FinalStructureModel
from calibration.control_envelope import associate
from calibration.receiving_scope import inputs_for
from simulation.training_data import ROOT
from simulation.network import PeachtreeEnvironment
from simulation.parameters import FOOT_M,IDMParameters
from simulation.model import run_baseline
from scripts.run_peachtree3u import synthetic

class FinalStructureTests(unittest.TestCase):
    def test_effective_values_immutable(self):
        refs=references();self.assertEqual(dict(refs),{(2,2):649.846,(2,4):777.245,(3,2):1184.777,(3,4):1241.529})
        with self.assertRaises(TypeError):refs[(2,2)]=640.
    def test_legacy_preserved(self):
        original={(r['intersection'],r['direction']):r['local_y_ft'] for r in inputs_for('NEW_REDUCED_SCOPE')['network']['stop_lines']}
        for row in final_inputs()['network']['stop_lines']:
            self.assertEqual(row['legacy_signal_proxy_ft'],original[(row['intersection'],row['direction'])])
        self.assertAlmostEqual(inputs_for('NEW_REDUCED_SCOPE')['network']['stop_lines'][0]['local_y_ft'],632.5395,places=10)
    def test_nb_sign(self):
        env=PeachtreeEnvironment(final_inputs()['network']);self.assertGreater(env.progress(1184.777,2),env.progress(1174,2))
    def test_sb_sign(self):
        env=PeachtreeEnvironment(final_inputs()['network']);self.assertGreater(env.progress(777.245,4),env.progress(790,4))
    def test_all_red_no_cross_and_green_release(self):
        checks=pd.read_csv(ROOT/'outputs/peachtree3u/direct_control_checks.csv')
        self.assertEqual(len(checks),8)
        self.assertTrue(checks[['red_no_cross','stopped_before_reference','green_release']].all().all())
    def test_12th_nb_full_envelope_association(self):
        from calibration.control_envelope import SignalControlEnvelope
        data=final_inputs();env=[SignalControlEnvelope(**r) for r in data['control_envelopes']]
        d=pd.DataFrame([dict(direction=2,lane=lane,y=y,length=15,speed=0,time=0) for lane in [1,2] for y in [1174,1184.777,1192]])
        self.assertTrue(associate(d,env).intersection.eq(3).all())
    def test_reference_is_entry_not_head_or_sim_fit(self):
        original=pd.read_csv(ROOT/'outputs/peachtree3t/intersection_envelopes.csv')
        for key,value in references().items():
            self.assertTrue(original[original.intersection.eq(key[0])&original.direction.eq(key[1])].entry.eq(value).all())
        with patch('calibration.final_structure.pd.read_csv',side_effect=AssertionError('No simulation output may select reference')):
            self.assertEqual(references()[(2,2)],649.846)
    def test_boundaries_unchanged(self):
        self.assertEqual(final_inputs()['receiving_scope'],inputs_for('NEW_REDUCED_SCOPE')['receiving_scope'])
    def test_only_control_location_changed(self):
        old=inputs_for('NEW_REDUCED_SCOPE');new=final_inputs()
        for key in ['initial','entries','entry_speed_samples_m_s','signals','revision','dt','receiving_scope']:
            self.assertEqual(old[key],new[key])
    def test_idm_unchanged(self):
        baseline=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
        freeze=json.loads((ROOT/'outputs/peachtree3u/structural_model_freeze.json').read_text())
        self.assertEqual(freeze['pre_calibration_IDM'],baseline['parameters'])
    def test_b1_inaccessible(self):
        for function in [references,final_inputs]:
            with self.assertRaises(PermissionError):function('B1')
        with self.assertRaises(PermissionError):run_final(3000,acquisition='B1')
    def test_conservation_no_overlap(self):
        d=pd.read_csv(ROOT/'outputs/peachtree3u/final_structure_30_replica_runs.csv')
        self.assertTrue(d[['conservation_every_tick','conservation_verified','no_overlap']].all().all())
        self.assertTrue(d.remaining.eq(0).all());self.assertTrue(d.pending.eq(0).all())
    def test_deterministic_same_seed(self):
        a=synthetic(3,4,seed=3000);b=synthetic(3,4,seed=3000)
        self.assertEqual(a.summary,b.summary);self.assertEqual(a.recorder.traces,b.recorder.traces)
    def test_freeze_generated(self):
        freeze=json.loads((ROOT/'outputs/peachtree3u/structural_model_freeze.json').read_text())
        self.assertEqual(freeze['status'],'FROZEN');self.assertTrue(freeze['B1_LOCKED'])
    def test_no_new_follower_delay(self):
        self.assertEqual(final_inputs()['revision'],inputs_for('NEW_REDUCED_SCOPE')['revision'])
    def test_directional_signal_not_reversed(self):
        data=final_inputs();data['entries']=[];data['source_window_start_relative_s']=0.;data['horizon_s']=12.
        data['signals']=[dict(intersection_id=i,direction=di,t_start_s=0,t_end_s=13,state='RED' if di==2 else 'GREEN') for i in [2,3] for di in [2,4]]
        data['initial']=[dict(vehicle_class=2,length_m=4,width_m=1.8,position_m=((649.846-80)-400)*FOOT_M,speed_m_s=8,lane=1,direction=2,movement=1),
            dict(vehicle_class=2,length_m=4,width_m=1.8,position_m=(1400-(1241.529+80))*FOOT_M,speed_m_s=8,lane=1,direction=4,movement=1)]
        p=IDMParameters.load(ROOT/'outputs/b2_calibrated_parameters.json');m=run_baseline(data,p,steps=120)
        self.assertLess(m.network.local_y(m.all_agents[0].position,2),649.846)
        self.assertLess(m.network.local_y(m.all_agents[1].position,4),1241.529)
    def test_final_ui_scenarios_and_overlays(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        next(x for x in app.selectbox if x.label=='Versión del baseline').set_value('FINAL_STRUCTURE').run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(all(b.disabled for b in app.button if b.label in ['E1','E2','E3']))
        next(x for x in app.checkbox if x.label=='Show effective control references').set_value(True).run()
        self.assertEqual(app.session_state['trace']['mode'],'FINAL_STRUCTURE')

if __name__=='__main__':unittest.main()
