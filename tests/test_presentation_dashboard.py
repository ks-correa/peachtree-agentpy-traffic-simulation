"""Presentation-only QA: frozen data and app views, no scientific rollouts."""
import ast,json,hashlib,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from PIL import Image
from streamlit.testing.v1 import AppTest
from ui.presentation_data import ROOT,ASSETS,SECTIONS,scenario_table,freezes

class PresentationDashboardTests(unittest.TestCase):
    def test_scientific_results_and_engine_unchanged(self):
        d=json.loads((ASSETS/'pre_presentation_integrity.json').read_text())
        for section in ['scientific_artifact_hashes','scientific_engine_hashes']:
            for path,value in d[section].items():self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),value,path)
    def test_all17_manifest_entries(self):
        d=json.loads((ASSETS/'presentation_manifest.json').read_text());self.assertEqual([r['slide_number'] for r in d['slides']],list(range(1,18)))
        for row in d['slides']:
            for key in ['section','recommended_title','main_message','data_source','metrics','figure_file','table_file','limitations','speaker_note_summary']:self.assertIn(key,row)
            self.assertTrue((ASSETS/row['figure_file']).exists());self.assertTrue((ASSETS/row['table_file']).exists())
    def test_required_assets(self):
        names=['02_problem_scope','04_agents_environment','05_dataset_evidence','06_speed_distribution','06_headway_distribution','06_travel_distribution','07_conceptual_model','08_agentpy_architecture','09_calibration','10_validation','11_scenarios','11_signal_timeline','12_travel_comparison','12_stopping_comparison','12_scenario_table','12_directional_results','13_space_time_base','13_space_time_e1','13_emergent_behavior','14_paired_effects','14_robustness','14_final_decision','15_limitations','16_conclusions']
        for name in names:
            with Image.open(ASSETS/(name+'.png')) as img:self.assertEqual(img.size,(1920,1080));self.assertTrue(img.info.get('source_artifact'))
    def test_table_sources_and_numeric_statistics(self):
        for path in (ASSETS/'tables').glob('*.csv'):self.assertIn('source_artifact',pd.read_csv(path).columns,path.name)
        d=pd.read_csv(ASSETS/'tables/descriptive_statistics.csv');self.assertEqual(set(d.context),{'B1','B2'})
        self.assertTrue(np.allclose(d.Variance,d.SD**2));self.assertTrue(d.N.gt(0).all())
        self.assertTrue(set(['speed','acceleration','Space_Headway','Time_Headway','travel_time','vehicle_length','interarrival','stopped_episode_duration']).issubset(set(d.Variable)))
    def test_statistics_reconcile_official_means(self):
        d=pd.read_csv(ASSETS/'tables/descriptive_statistics.csv')
        b1=pd.read_csv(ROOT/'outputs/peachtree5/b1_real_metrics.csv').iloc[0]
        b2=pd.read_csv(ROOT/'outputs/peachtree4/pre_vs_post_calibration.csv').set_index('metric').REAL_B2
        for c,truth in [('B1',b1),('B2',b2)]:
            q=d[d.context.eq(c)].set_index('Variable').Mean
            for key,metric in [('speed','speed_mean_ft_s'),('Space_Headway','headway_mean_ft'),('travel_time','travel_mean_s'),('stopped_episode_duration','complete_stop_duration_mean_s')]:self.assertAlmostEqual(q[key],truth[metric],places=8)
    def test_scenario_table_uses_official_values(self):
        for c in ['B1','B2']:
            view=scenario_table(c).set_index('scenario');original=pd.read_csv(ROOT/f'outputs/peachtree6/{c.lower()}_scenario_summary.csv')
            for row in original[original.metric.eq('travel_mean_s')].itertuples():self.assertEqual(view.loc[row.scenario,'Tiempo de recorrido (s)'],row.mean)
    def test_no_experiment_calls_in_presentation(self):
        for path in [ROOT/'ui/presentation_data.py',ROOT/'ui/presentation_app.py',ROOT/'scripts/build_presentation_assets.py']:
            tree=ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    name=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ''
                    self.assertNotIn(name,['rollout','run_final','run_baseline','evaluate_job','minimize','sim_step','step'])
    def test_presentation_default(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60).run()
        self.assertEqual(len(app.exception),0);self.assertEqual(app.session_state['dashboard_mode'],'PRESENTATION MODE')
        self.assertEqual([t.label for t in app.tabs],SECTIONS)
    def test_all12_sections_render_without_model_runs(self):
        import agentpy
        with patch.object(agentpy.Model,'run',side_effect=AssertionError('No new scientific run')):
            for section in SECTIONS:
                with self.subTest(section=section):
                    app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60)
                    app.session_state['presentation_section']=section;app.run();self.assertEqual(len(app.exception),0)
    def test_simulation_controls_only_playback(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60);app.session_state['presentation_section']='Simulación';app.run()
        for label in ['Iniciar','Pausar','Continuar','Reiniciar']:
            next(b for b in app.button if b.label==label).click().run();self.assertEqual(len(app.exception),0)
        self.assertEqual(app.session_state['presentation_playing'],False)
        playback=next(x for x in app.selectbox if x.label=='Playback');self.assertEqual(playback.options,['x0.5','x1','x2','x5','x10'])
    def test_export_center_downloads(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60);app.session_state['presentation_section']='Material para presentación';app.run()
        self.assertEqual(len(app.exception),0);self.assertTrue((ASSETS/'presentation_material.zip').exists())
    def test_technical_mode_available(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60);app.session_state['dashboard_mode']='TECHNICAL MODE';app.run()
        self.assertEqual(len(app.exception),0);self.assertTrue(any(x.label=='Contexto de simulación' for x in app.selectbox))

if __name__=='__main__':unittest.main()
