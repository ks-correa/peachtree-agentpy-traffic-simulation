import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from simulation.training_data import ROOT

class StreamlitBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30)

    def test_render_and_train_only_metrics(self):
        original=pd.read_csv;opened=[]
        def guarded(path,*a,**kw):
            opened.append(str(path));self.assertTrue(str(path).split('\\')[-1].split('/')[-1].startswith('b2_') or 'peachtree3r' in str(path))
            return original(path,*a,**kw)
        with patch('pandas.read_csv',side_effect=guarded):self.app.run()
        self.assertEqual(len(self.app.exception),0);self.assertGreater(len(opened),4)
        self.assertTrue(all('B1' not in path for path in opened))

    def test_run_pause_reset_and_scenario_controls(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        self.assertEqual(len(app.exception),0)
        buttons={b.label:b for b in app.button}
        self.assertTrue(all(buttons[x].disabled for x in ['E1','E2','E3']))
        original_id=app.session_state['run_id'];original_summary=app.session_state['trace']['summary'].copy()
        buttons['Run'].click().run();self.assertTrue(app.session_state['playing'])
        next(b for b in app.button if b.label=='Pause').click().run();self.assertFalse(app.session_state['playing'])
        next(b for b in app.button if b.label=='Reset').click().run();self.assertFalse(app.session_state['playing'])
        self.assertNotEqual(original_id,app.session_state['run_id']);self.assertEqual(original_summary,app.session_state['trace']['summary'])
        self.assertEqual(len(app.exception),0)

    def test_seed_run_uses_engine_visual_speed_does_not(self):
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        app.number_input[0].set_value(11)
        next(b for b in app.button if b.label=='Run').click().run()
        self.assertEqual(app.session_state['trace']['seed'],11);self.assertEqual(len(app.exception),0)
        summary=app.session_state['trace']['summary'].copy();app.slider[0].set_value(20.).run()
        self.assertEqual(summary,app.session_state['trace']['summary'])

if __name__=='__main__':unittest.main()
