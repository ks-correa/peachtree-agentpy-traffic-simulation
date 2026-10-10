"""Five-parameter scope, immutable TRAIN plans and final calibration guards."""
import json,unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from calibration.final_calibration import OUT,ROOT,NAMES,WEIGHTS,parameters,plan,verify_structure,final_parameters,evaluate_job,sha,errors

class FinalCalibrationTests(unittest.TestCase):
    def initial(self):
        values=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())['parameters']
        return {k:values[k] for k in NAMES}
    def test_structure_hash_unchanged(self):
        self.assertEqual(verify_structure(),plan()['structural_freeze_sha256'])
    def test_only_five_parameters(self):
        self.assertEqual(set(NAMES),{'v0','T','s0','a','b'})
        with self.assertRaises(ValueError):parameters(dict(self.initial(),release=2))
    def test_delta_fixed(self):
        self.assertEqual(parameters(self.initial()).delta,4)
        with self.assertRaises(ValueError):parameters(dict(self.initial(),delta=3))
    def test_release_fixed(self):
        from calibration.final_structure import final_inputs
        expected=json.loads((ROOT/'outputs/peachtree3u/final_inputs.json').read_text())['revision']['signal_release_delay_s']
        self.assertEqual(final_inputs()['revision']['signal_release_delay_s'],expected)
        self.assertAlmostEqual(expected,1.6,places=12)
    def test_effective_references(self):
        from calibration.final_structure import references
        self.assertEqual(dict(references()),{(2,2):649.846,(2,4):777.245,(3,2):1184.777,(3,4):1241.529})
    def test_bounds_frozen_hash(self):
        self.assertEqual(sha(OUT/'parameter_bounds.csv'),plan()['frozen_artifact_hashes']['outputs\\peachtree4\\parameter_bounds.csv'])
    def test_bounds_tamper_rejected(self):
        original=sha
        with patch('calibration.final_calibration.sha',side_effect=lambda p:'changed' if p.name=='parameter_bounds.csv' else original(p)):
            with self.assertRaises(RuntimeError):plan()
    def test_weights_equal_immutable(self):
        self.assertEqual(set(WEIGHTS.values()),{1/6})
        with self.assertRaises(TypeError):WEIGHTS['stopping']=1
    def test_objective_tamper_rejected(self):
        original=sha
        with patch('calibration.final_calibration.sha',side_effect=lambda p:'changed' if p.name=='objective_definition.json' else original(p)):
            with self.assertRaises(RuntimeError):plan()
    def test_b1_inaccessible(self):
        from calibration.final_calibration import rollout
        for f in [verify_structure,plan,final_parameters]:
            with self.assertRaises(PermissionError):f('B1')
        with self.assertRaises(PermissionError):rollout(self.initial(),5000,acquisition='B1')
    def test_invalid_candidate_rejected(self):
        row=evaluate_job((999,dict(self.initial(),a=float('nan')),5000))
        self.assertEqual(row['status'],'INVALID_CANDIDATE');self.assertTrue(np.isinf(row['objective']))
    def test_development_seeds(self):self.assertEqual(plan()['development_seeds'],list(range(5000,5005)))
    def test_final_seeds_disjoint(self):
        p=plan();self.assertFalse(set(p['development_seeds'])&set(p['final_seeds']));self.assertEqual(p['final_seeds'],list(range(4000,4030)))
    def test_no_best_seed(self):
        hist=pd.read_csv(OUT/'optimization_history.csv');cand=pd.read_csv(OUT/'calibration_candidates.csv')
        for row in cand[cand.status.eq('VALID')].itertuples():
            seeds=hist[hist.candidate.eq(row.candidate)]
            self.assertEqual(set(seeds.seed),set(plan()['development_seeds']))
            self.assertAlmostEqual(row.objective,seeds.objective.mean(),places=12)
    def test_final_parameters_immutable(self):
        values=final_parameters()
        with self.assertRaises(TypeError):values['v0']=0
        with patch('calibration.final_calibration.sha',return_value='changed'):
            with self.assertRaises(RuntimeError):final_parameters()
    def test_freeze_generated(self):
        freeze=json.loads((OUT/'calibration_freeze.json').read_text())
        self.assertEqual(freeze['status'],'FROZEN');self.assertTrue(freeze['B1_LOCKED'])
    def test_final_choice_is_objective_minimum(self):
        selected=json.loads((OUT/'final_parameters.json').read_text());candidates=pd.read_csv(OUT/'calibration_candidates.csv')
        self.assertAlmostEqual(selected['objective'],candidates[candidates.status.eq('VALID')].objective.min(),places=12)
    def test_final_replications_invariants(self):
        d=pd.read_csv(OUT/'final_30_replica_runs.csv');self.assertEqual(len(d),30)
        self.assertTrue(d[['conservation_verified','no_overlap','no_negative_speed','finite_state','valid_signals','boundaries_valid']].all().all())
    def test_same_final_seed(self):
        # Frozen engine with stochastic synthetic arrivals, avoiding939s replay.
        from calibration.final_structure import final_inputs
        from calibration.final_calibration import CheckedCalibrationModel
        data=final_inputs();data['horizon_s']=3.;data['initial']=[]
        data['entries']=[dict(vehicle_class=2,length_m=4.,width_m=1.8,position_m=0.,speed_m_s=0.,lane=lane,direction=2,movement=1,requested_time_s=t)
            for lane,t in [(1,0.),(2,.4)]]
        p=parameters(dict(final_parameters()))
        runs=[]
        for _ in range(2):
            m=CheckedCalibrationModel({'steps':30,'seed':4000},inputs=data,idm=p,trace=True,queue_gap=4.9414274828549685)
            m.run(display=False);runs.append(m)
        from ui.canvas_renderer import finite_json
        self.assertEqual(finite_json(runs[0].recorder.traces),finite_json(runs[1].recorder.traces))
    def test_checks_do_not_modify_frozen_dynamics(self):
        from calibration.final_structure import final_inputs,FinalStructureModel
        from calibration.final_calibration import CheckedCalibrationModel
        data=final_inputs();data['horizon_s']=1.;data['entries']=[]
        p=parameters(self.initial());states=[]
        for cls in [FinalStructureModel,CheckedCalibrationModel]:
            m=cls({'steps':10,'seed':4000},inputs=data,idm=p,trace=False,queue_gap=4.9414274828549685)
            m.run(display=False);states.append([(a.agent_id,a.position,a.speed,a.state) for a in m.all_agents])
        self.assertEqual(states[0],states[1])
    def test_final_ui_read_only_and_scenarios(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        next(x for x in app.selectbox if x.label=='Versión del baseline').set_value('FINAL_CALIBRATED_B2').run()
        self.assertEqual(len(app.exception),0)
        self.assertTrue(all(b.disabled for b in app.button if b.label in ['E1','E2','E3']))
        self.assertEqual(app.session_state['trace']['mode'],'FINAL_CALIBRATED_B2')

if __name__=='__main__':unittest.main()
