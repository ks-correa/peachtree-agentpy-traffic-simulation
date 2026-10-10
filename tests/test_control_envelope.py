import unittest
from dataclasses import asdict
import numpy as np
import pandas as pd
from unittest.mock import patch
from calibration.control_envelope import bumpers,SignalControlEnvelope,queue_snapshot,STOP,onset,associate,queue_series,dynamics
from simulation.signals import SignalController,SignalInterval
from calibration.receiving_scope import NEW_EXIT,inputs_for
from simulation.training_data import require_train

class ControlEnvelopeTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame([dict(id='B2:1',direction=2,lane=1,y=100.,rear=85.,length=15.,speed=0.,following=2),
                             dict(id='B2:2',direction=2,lane=1,y=80.,rear=65.,length=15.,speed=0.,following=0)])
    def test_front_is_local_y(self):self.assertEqual(bumpers(100.,20.,2)[0],100.)
    def test_nb_rear(self):self.assertEqual(bumpers(100.,20.,2)[2],80.)
    def test_sb_rear(self):self.assertEqual(bumpers(100.,20.,4)[2],120.)
    def test_center(self):self.assertEqual(bumpers(100.,20.,4)[1],110.)
    def test_first_head(self):self.assertEqual(queue_snapshot(self.fixture(),6.)[0].id,'B2:1')
    def test_not_second_head(self):
        q=queue_snapshot(self.fixture().iloc[::-1],6.);self.assertEqual([a.id for a in q],['B2:1','B2:2'])
    def test_moving_front_prevents_head(self):
        d=self.fixture();d.loc[0,'speed']=STOP+1;self.assertEqual(queue_snapshot(d,6.),[])
    def test_gap_breaks_chain(self):self.assertEqual(len(queue_snapshot(self.fixture(),4.)),1)
    def test_following_disagreement(self):
        d=self.fixture();d.loc[0,'following']=3;self.assertEqual(len(queue_snapshot(d,6.)),1)
    def test_envelope(self):
        e=SignalControlEnvelope(2,2,1,400,650,778,1173,630,649)
        self.assertEqual(e.zone(700),'INTERSECTION_INTERIOR');self.assertEqual(e.zone(640),'STOP_ZONE')
    def test_discharge(self):self.assertEqual(SignalControlEnvelope(2,2,1,400,650,778,1173).zone(900),'DISCHARGE_ZONE')
    def test_lane_specific(self):
        e=SignalControlEnvelope(2,2,1,400,650,778,1173)
        d=pd.DataFrame([dict(direction=2,lane=2,y=640,length=15,speed=0,time=0)])
        self.assertEqual(associate(d,[e]).intersection.iloc[0],0)
    def test_deterministic(self):
        d=self.fixture();self.assertEqual([r.id for r in queue_snapshot(d,6.)],[r.id for r in queue_snapshot(d,6.)])
    def test_scope(self):self.assertEqual(NEW_EXIT,{2:1346.452,4:597.878})
    def test_previous_inputs(self):
        self.assertNotIn('receiving_scope',inputs_for('OLD'));self.assertNotIn('receiving_scope',inputs_for('REVISED'))
    def test_holdout(self):
        with self.assertRaises(PermissionError):require_train('B1')
    def test_release(self):
        d=pd.DataFrame({'time':[1,1.1,1.2],'speed':[0,0,1]});self.assertAlmostEqual(onset(d,1,2),.2)
    def test_release_censored(self):
        d=pd.DataFrame({'time':[1,1.3],'speed':[0,1]});self.assertTrue(np.isnan(onset(d,1,2)))
    def test_envelope_has_no_dynamics(self):
        self.assertNotIn('speed',asdict(SignalControlEnvelope(2,2,1,400,650,778,1173)))

    def synthetic_cycle(self):
        rows=[]
        for tick in range(40):
            t=tick/10
            for id,y,release in [('head',100.,1.2),('follower',80.,1.5)]:
                rows.append(dict(id=id,frame=tick,time=t,direction=2,lane=1,y=y+40*max(0,t-release),
                                 speed=40 if t>=release-1e-8 else 0.,length=10.))
        bank={(2,2):SignalController(2,2,[SignalInterval(0,1,'RED'),SignalInterval(1,4,'GREEN')])}
        with patch('calibration.control_envelope.controllers_from_inputs',return_value=bank):
            d=associate(pd.DataFrame(rows),[SignalControlEnvelope(2,2,1,0,100,120,300)])
            q,m=queue_series(d,15.)
            return dynamics(d,q,m)
    def test_cycle_grouping(self):
        h,r,p=self.synthetic_cycle();self.assertEqual(set(h.cycle),{0});self.assertEqual(len(r),1)
    def test_green_queue_cohort(self):
        h,r,p=self.synthetic_cycle();self.assertEqual(r.queue_at_green_onset.iloc[0],2)
    def test_stopped_clearance(self):
        h,r,p=self.synthetic_cycle();self.assertAlmostEqual(r.time_to_stopped_queue_clearance_s.iloc[0],.5)
    def test_discharge_clearance(self):
        h,r,p=self.synthetic_cycle();self.assertAlmostEqual(r.time_to_queue_clearance_s.iloc[0],1.5)
    def test_start_propagation(self):
        h,r,p=self.synthetic_cycle();self.assertAlmostEqual(p.queue_start_headway_s.iloc[0],.3)
    def test_missing_residual_is_not_zero(self):
        h,r,p=self.synthetic_cycle();self.assertTrue(np.isnan(r.remaining_stopped_after_5s.iloc[0]))
    def test_control_not_falsely_frozen(self):
        import json
        from simulation.training_data import ROOT
        freeze=json.loads((ROOT/'outputs/peachtree3t/structural_model_freeze.json').read_text())
        self.assertEqual(freeze['status'],'NOT_FROZEN');self.assertFalse(freeze['physical_references_changed'])
    def test_stop_band_reproducibility(self):
        from simulation.training_data import ROOT
        heads=pd.read_csv(ROOT/'outputs/peachtree3t/queue_head_by_cycle.csv')
        zones=pd.read_csv(ROOT/'outputs/peachtree3t/stop_zone_candidates.csv')
        for row in zones.itertuples():
            g=heads[heads.intersection.eq(row.intersection)&heads.direction.eq(row.direction)&heads.lane.eq(row.lane)]
            self.assertAlmostEqual(g.position_y.quantile(.1),row.P10)
            self.assertAlmostEqual(g.position_y.quantile(.9),row.P90)
    def test_idm_preserved(self):
        import json
        from simulation.training_data import ROOT
        freeze=json.loads((ROOT/'outputs/peachtree3t/structural_model_freeze.json').read_text())
        parameters=json.loads((ROOT/'outputs/b2_calibrated_parameters.json').read_text())
        self.assertEqual(freeze['IDM_parameters'],parameters['parameters'])
    def test_ui_overlays_do_not_change_states(self):
        from streamlit.testing.v1 import AppTest
        from simulation.training_data import ROOT
        app=AppTest.from_file(str(ROOT/'streamlit_app.py'),default_timeout=30).run()
        next(x for x in app.selectbox if x.label=='Versión del baseline').set_value('CONTROL_ENVELOPE_REVISION').run()
        before=app.session_state['trace']['summary'].copy()
        app.checkbox[0].set_value(True).run();app.checkbox[1].set_value(True).run()
        self.assertEqual(len(app.exception),0)
        self.assertEqual(before,app.session_state['trace']['summary'])
        self.assertEqual(app.session_state['trace']['receiving_scope']['exit_ft'],{'2':1346.452,'4':597.878})

if __name__=='__main__':unittest.main()
