import ast,json,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from calibration import holdout_validation as v
from calibration.final_structure import final_inputs,FinalStructureModel
from simulation.training_data import require_train

class HoldoutValidationTests(unittest.TestCase):
    def test_freezes_unchanged(self):
        audit=v.verify();self.assertEqual(v.sha(v.ROOT/'outputs/peachtree3u/structural_model_freeze.json'),audit['structural_freeze_sha256'])
        self.assertEqual(v.sha(v.ROOT/'outputs/peachtree4/calibration_freeze.json'),audit['calibration_freeze_sha256'])
    def test_parameters_unchanged(self):
        expected=json.loads((v.ROOT/'outputs/peachtree4/final_parameters.json').read_text())['values']
        self.assertEqual({k:getattr(v.frozen_parameters(),k) for k in expected},expected);self.assertEqual(v.frozen_parameters().delta,4)
    def test_no_optimization_import_or_call(self):
        forbidden={'minimize','differential_evolution','LatinHypercube','NelderMead','Powell','calibrate'}
        for path in [v.ROOT/'calibration/holdout_validation.py',v.ROOT/'scripts/run_peachtree5.py',v.ROOT/'scripts/finish_peachtree5.py']:
            tree=ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith(('scipy.optimize','scipy.stats.qmc')))
                if isinstance(node,ast.Call):
                    name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
                    self.assertNotIn(name,forbidden)
    def test_training_B1_remains_locked(self):
        with self.assertRaises(PermissionError):require_train('B1')
        self.assertTrue(v.full_b1().acquisition_id.eq('B1').all())
    def test_exogenous_payload_has_no_replay_arrays(self):
        data=v.inputs()
        self.assertEqual(data['acquisition_id'],'B1')
        self.assertNotIn('real_position_t',data);self.assertNotIn('real_speed_t',data)
        for r in data['entries']:self.assertNotIn('v_vel',r);self.assertNotIn('real_exit_time',r)
        self.assertEqual(data['entry_speed_samples_m_s'],final_inputs()['entry_speed_samples_m_s'])
    def test_same_scope_controls_rules(self):
        a=v.inputs();b=final_inputs()
        for key in ['network','revision','dt','receiving_scope','control_envelopes']:self.assertEqual(a[key],b[key])
    def test_B1_signals_exogenous(self):
        a=v.inputs();self.assertEqual(a['signal_schedule_source'],'B1 OBSERVED EXOGENOUS INPUT')
        self.assertTrue(all(row['acquisition_id']=='B1' for row in a['signals']))
        self.assertNotEqual(a['signals'],final_inputs()['signals'])
    def test_start_not_fit_selected(self):
        a=v.inputs();self.assertEqual(a['source_window_start_frame'],515)
        self.assertAlmostEqual(a['source_window_start_relative_s'],a['initial_protocol']['first_known_all_four_s']+a['initial_protocol']['inherited_TRAIN_margin_s'])
    def test_seeds_frozen_distinct(self):
        seeds=json.loads((v.OUT/'validation_seeds.json').read_text())['seeds'];self.assertEqual(seeds,list(range(6000,6030)))
        plan=json.loads((v.ROOT/'outputs/peachtree4/search_plan.json').read_text())
        self.assertFalse(set(seeds)&set(plan['development_seeds']+plan['final_seeds']))
    def test_all30_invariants(self):
        d=pd.read_csv(v.OUT/'b1_simulation_runs.csv');self.assertEqual(len(d),30)
        self.assertTrue(d[['conservation_verified','conservation_every_tick','no_overlap','no_negative_speed','finite_states']].all().all())
    def test_validation_freeze(self):
        f=json.loads((v.OUT/'validation_freeze.json').read_text());self.assertEqual(f['status'],'FROZEN');self.assertFalse(f['parameters_modified'])
        self.assertEqual(f['validation_name'],v.TITLE)
    def test_adapter_does_not_change_physics(self):
        from ui.canvas_renderer import finite_json
        data=final_inputs();data['horizon_s']=1.;data['entries']=[];p=v.frozen_parameters();models=[]
        for cls,acq in [(FinalStructureModel,'B2'),(v.ValidationModel,'B1')]:
            given=dict(data,acquisition_id=acq,validation_only=True)
            m=cls({'steps':10,'seed':6000},inputs=given,idm=p,trace=True,queue_gap=v.train_queue_gap());m.run(display=False);models.append(m)
        self.assertEqual(finite_json(models[0].recorder.traces),finite_json(models[1].recorder.traces))
        self.assertEqual(models[1].inputs['acquisition_id'],'B1')
    def test_no_replay_source_read_after_setup(self):
        data=v.inputs();data['horizon_s']=1.;data['entries']=[]
        with patch('calibration.holdout_validation.full_b1',side_effect=AssertionError('No history in engine')):
            m=v.ValidationModel({'steps':10,'seed':6000},inputs=data,idm=v.frozen_parameters(),trace=False,queue_gap=v.train_queue_gap());m.run(display=False)
    def test_metric_definitions_preserved(self):
        f=json.loads((v.OUT/'validation_freeze.json').read_text());spec=json.loads((v.ROOT/'outputs/peachtree4/objective_definition.json').read_text())
        self.assertEqual(f['metric_definitions'],spec['definitions'])
    def test_descriptive_score_not_parameter_selection(self):
        self.assertFalse((v.OUT/'optimization_history.csv').exists());self.assertFalse((v.OUT/'parameter_bounds.csv').exists())
    def test_UI_validation_tab(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(v.ROOT/'streamlit_app.py'),default_timeout=30)
        app.session_state['phase_tabs']='VALIDACIÓN';app.run()
        self.assertEqual(len(app.exception),0);self.assertIn('VALIDACIÓN',[x.label for x in app.tabs])
        self.assertTrue(all(b.disabled for b in app.button if b.label in ['E1','E2','E3']))

if __name__=='__main__':unittest.main()
