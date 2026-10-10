"""Signal-only scenario design, paired evidence and frozen-engine UI QA."""
import ast,copy,json,unittest
import numpy as np
import pandas as pd
from calibration import scenarios as s

class ScenarioTests(unittest.TestCase):
    def test_prior_freezes_intact(self):self.assertTrue(s.verify()['integrity_verified_before_scenarios'])
    def test_IDM_immutable(self):
        expected=json.loads((s.ROOT/'outputs/peachtree4/final_parameters.json').read_text())['values']
        self.assertEqual({k:getattr(s.frozen_parameters(),k) for k in expected},expected)
    def test_exactly_three_alternatives(self):self.assertEqual(s.MODES,('BASE','E1','E2','E3'))
    def test_no_fourth_mode(self):
        with self.assertRaises(ValueError):s.transform(s.original('B2'),'E4',s.design())
    def test_BASE_unchanged(self):
        for context in ['B1','B2']:self.assertEqual(s.scenario_inputs(context,'BASE')['signals'],s.original(context)['signals'])
    def test_E1_preserves_cycles_yellow(self):
        for context in ['B1','B2']:
            old=s.original(context);new=s.scenario_inputs(context,'E1')
            for key,g in pd.DataFrame(old['signals']).groupby(['intersection_id','direction']):
                n=[r for r in new['signals'] if (r['intersection_id'],r['direction'])==key]
                for block in s.cycles(g.to_dict('records')):
                    updated=next(b for b in s.cycles(n) if abs(b[0]['t_start_s']-block[0]['t_start_s'])<1e-7)
                    self.assertAlmostEqual(updated[3]['t_start_s']-updated[0]['t_start_s'],block[3]['t_start_s']-block[0]['t_start_s'])
                    self.assertAlmostEqual(updated[1]['t_end_s']-updated[1]['t_start_s'],block[1]['t_end_s']-block[1]['t_start_s'])
                    inc=updated[0]['t_end_s']-block[0]['t_end_s'];self.assertGreaterEqual(inc,0)
                    self.assertLessEqual(inc,.1*(block[0]['t_end_s']-block[0]['t_start_s'])+1e-7)
                    self.assertGreater(updated[2]['t_end_s']-updated[2]['t_start_s'],0)
    def test_E2_only_offset_and_preserves_durations(self):
        spec=s.design()['E2'];shift=spec['OFFSET_SHIFT_SECONDS'];down=spec['downstream_intersection']
        for context in ['B1','B2']:
            old=s.original(context);new=s.scenario_inputs(context,'E2')
            for row in old['signals']:
                delta=shift if row['intersection_id']==down else 0
                hit=[r for r in new['signals'] if r['intersection_id']==row['intersection_id'] and r['direction']==row['direction'] and abs(r['t_start_s']-row['t_start_s']-delta)<1e-7 and not r.get('edge_extension')]
                self.assertEqual(len(hit),1);r=hit[0]
                self.assertEqual(r['state'],row['state']);self.assertAlmostEqual(r['t_end_s']-r['t_start_s'],row['t_end_s']-row['t_start_s'])
    def test_E3_exact_rules_on_same_extended_clock(self):
        spec=s.design();down=spec['E2']['downstream_intersection'];shift=spec['E2']['OFFSET_SHIFT_SECONDS']
        for context in ['B1','B2']:
            data=s.original(context);extended=copy.deepcopy(data);rows=[];start=data['source_window_start_relative_s'];end=start+data['horizon_s']
            for (i,di),g in pd.DataFrame(data['signals']).groupby(['intersection_id','direction']):
                parts=g.to_dict('records');rows+=s.extend_edges(parts,start-shift-1,end-shift+1) if i==down else parts
            extended['signals']=rows;expected=s.transform(extended,'E1',spec)
            for r in expected['signals']:
                if r['intersection_id']==down:r['t_start_s']+=shift;r['t_end_s']+=shift
            actual=s.scenario_inputs(context,'E3')['signals']
            self.assertEqual(len(expected['signals']),len(actual))
            for a,b in zip(expected['signals'],actual):
                self.assertEqual((a['intersection_id'],a['direction'],a['state']),(b['intersection_id'],b['direction'],b['state']))
                np.testing.assert_allclose([a['t_start_s'],a['t_end_s']],[b['t_start_s'],b['t_end_s']],rtol=0,atol=1e-8)
    def test_demand_and_rules_same_across_modes(self):
        for context in ['B1','B2']:
            old=s.original(context)
            for mode in s.MODES:
                data=s.scenario_inputs(context,mode)
                for key in ['initial','entries','entry_speed_samples_m_s','network','revision','receiving_scope','dt']:self.assertEqual(data[key],old[key])
    def test_schedule_valid(self):
        for context in ['B1','B2']:
            for mode in s.MODES:s.validate_schedule(s.scenario_inputs(context,mode))
    def test_design_frozen(self):
        lock=json.loads((s.OUT/'scenario_design_lock.json').read_text());self.assertEqual(s.sha(s.OUT/'scenario_design_freeze.json'),lock['sha256'])
        spec=s.design();self.assertFalse(spec['design_may_change_after_results']);self.assertEqual(spec['code_hash'],s.sha(s.__file__))
    def test_no_scenario_optimization(self):
        tree=ast.parse((s.ROOT/'calibration/scenarios.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):self.assertFalse((node.module or '').startswith(('scipy.optimize','scipy.stats.qmc')))
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):self.assertNotIn(node.func.id,['minimize','LatinHypercube'])
    def test_paired30_every_config_context(self):
        for context in ['B1','B2']:
            d=pd.read_csv(s.OUT/f'{context.lower()}_scenario_runs.csv')
            self.assertEqual(len(d),120)
            for mode in s.MODES:self.assertEqual(set(d[d.scenario.eq(mode)].seed),set(range(7000,7030)))
    def test_all_invariants(self):
        for context in ['B1','B2']:
            d=pd.read_csv(s.OUT/f'{context.lower()}_scenario_runs.csv')
            self.assertTrue(d[['conservation_verified','no_overlap','no_negative_speed']].all().all())
            self.assertTrue(d.remaining.eq(0).all());self.assertTrue(d.pending.eq(0).all())
    def test_score_frozen_equal_domains(self):
        weights=s.design()['decision_score']['weights'];self.assertEqual(set(weights.values()),{.25})
    def test_recommendation_from_frozen_rule(self):
        f=json.loads((s.OUT/'experiment_freeze.json').read_text());score=pd.read_csv(s.OUT/'decision_score.csv');pareto=pd.read_csv(s.OUT/'pareto_analysis.csv')
        eligible=[mode for mode in ['E1','E2','E3'] if pareto[pareto.other.eq(mode)&pareto.dominates].empty and (score[score.scenario.eq(mode)].groupby('context').DECISION_SCORE.mean()<0).all()]
        expected=min(eligible,key=lambda mode:score[score.scenario.eq(mode)].DECISION_SCORE.mean()) if eligible else 'NO_ALTERNATIVE_DOMINATES_BASELINE'
        self.assertEqual(f['recommended_alternative'],expected)
    def test_UI_selector_drives_AgentPy_schedule(self):
        from streamlit.testing.v1 import AppTest
        app=AppTest.from_file(str(s.ROOT/'streamlit_app.py'),default_timeout=30).run()
        next(x for x in app.selectbox if x.label=='Versión del baseline').set_value('SCENARIO_EXPERIMENTATION').run()
        next(x for x in app.selectbox if x.label=='Escenario').set_value('E2 — Coordinación semafórica').run()
        self.assertEqual(len(app.exception),0);self.assertEqual(app.session_state['trace']['scenario'],'E2')
        self.assertEqual(app.session_state['trace']['signal_intervals'],s.scenario_inputs('B2','E2')['signals'])
        self.assertTrue(all(not b.disabled for b in app.button if b.label in ['E1','E2','E3']))
        next(b for b in app.button if b.label=='Run').click().run()
        self.assertEqual(len(app.exception),0);self.assertEqual(app.session_state['trace']['scenario'],'E2')

if __name__=='__main__':unittest.main()
