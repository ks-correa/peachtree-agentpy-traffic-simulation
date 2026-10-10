"""View-only checks for context isolation, horizon, exports and scientific integrity."""
import ast,hashlib,io,json,unittest
from unittest.mock import patch
import agentpy
import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest
from ui.simulation_view import *

class SimulationViewTests(unittest.TestCase):
    def test_all_eight_context_scenario_views_without_physics(self):
        with patch.object(agentpy.Model,'run',side_effect=AssertionError('No new physics')):
            for context in ['B1','B2']:
                for scenario in SCENARIOS:
                    with self.subTest(context=context,scenario=scenario):
                        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60)
                        app.session_state['presentation_section']='Simulación';app.session_state['simulation_context']=context;app.session_state['simulation_scenario']=scenario;app.run()
                        self.assertFalse(app.exception);self.assertEqual(len(app.get('plotly_chart')),8)
                        self.assertEqual(app.session_state['presentation_trace_id'],f'{context}:{scenario}:7000:180 s')
    def test_horizon_and_population_are_artifact_values(self):
        for context,horizon,total in [('B1',969.3,251),('B2',939.3,274)]:
            for scenario in SCENARIOS:
                trace,inputs,path,source=saved_run(context,scenario)
                self.assertAlmostEqual(inputs['horizon_s'],horizon);self.assertEqual(len(inputs['initial'])+len(inputs['entries']),total)
                self.assertEqual(trace['context'],context);self.assertEqual(trace['scenario'],scenario)
                self.assertEqual(inputs['dt'],.1);self.assertLessEqual(trace['frames'][-1]['time'],horizon)
        self.assertEqual(clock_label(969.3),'16:09.3');self.assertEqual(clock_label(939.3),'15:39.3')
    def test_window_change_resets_visual_identity_only(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=60);app.session_state['presentation_section']='Simulación';app.run()
        identity=app.session_state['presentation_run_id']
        next(s for s in app.selectbox if s.label=='Ventana visual').select('60 s').run()
        self.assertNotEqual(identity,app.session_state['presentation_run_id']);self.assertFalse(app.session_state['presentation_playing'])
    def test_temporal_series_and_official_means_are_distinct(self):
        for c in ['B1','B2']:
            trace,inputs,path,_=saved_run(c,'E1');fig,d=temporal_figure(trace,120,'departures',path)
            self.assertTrue(d.simulation_time.le(120).all());self.assertEqual(d.throughput_cumulative.iloc[0],trace['frames'][0]['metrics']['throughput_cumulative'])
            np.testing.assert_array_equal(fig.data[0].y,d.throughput_cumulative)
            self.assertIn('Corrida ilustrativa',fig.layout.title.text)
            self.assertIn('30 réplicas',scenario_chart(c,'travel_mean_s').layout.title.text)
    def test_export_dimensions_sources_and_read_only_code(self):
        trace,_,source,_=saved_run('B2','BASE');fig,_=temporal_figure(trace,60,'speed_stopped',source)
        with Image.open(io.BytesIO(png_bytes(fig.to_json()))) as image:
            self.assertEqual(image.size,(1920,1080));self.assertEqual(image.info['source_artifact'],source)
        text=(ROOT/'ui/simulation_view.py').read_text(encoding='utf-8');tree=ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                name=getattr(node.func,'id',getattr(node.func,'attr',''))
                self.assertNotIn(name,['rollout','run_baseline','run_final','minimize','sim_step','step'])
    def test_scientific_hashes_intact(self):
        for path,h in read_json('presentation_assets/pre_simulation_layout_hashes.json').items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),h,path)

if __name__=='__main__':unittest.main()
