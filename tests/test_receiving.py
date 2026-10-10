import json,unittest
import numpy as np
import pandas as pd
from calibration.receiving import region,bin_stops,block_episodes,audit,NEXT,OUT
from calibration.receiving_scope import inside,ReducedBoundaryModel,NEW_EXIT,evaluate
from simulation.parameters import IDMParameters,DT
from simulation.training_data import ROOT,HoldoutLockedError
from scripts.evaluate_local import digest
from test_baseline import inputs,vehicle,P

class ReceivingBoundaryTests(unittest.TestCase):
    def test_direction_specific_geometry(self):
        self.assertEqual(region([1000,1300,1500],2).tolist(),['CONTROLLED_REGION','POST_CONTROL_REGION','BEYOND_CURRENT_EXIT'])
        self.assertEqual(region([900,500,300],4).tolist(),['CONTROLLED_REGION','POST_CONTROL_REGION','BEYOND_CURRENT_EXIT'])
    def test_next_control_mapping(self):self.assertEqual(NEXT,{2:4,4:1})
    def test_spatial_bins_reproducible(self):
        d=pd.DataFrame({'speed':[0.,0.,1.],'downstream_ft':[10.,25.,50.],'cohort_direction':[2]*3,'id':['a','b','c']})
        q=bin_stops(d,25.);self.assertEqual(q.stopped_frames.sum(),2);self.assertEqual(q[q.stopped_frames>0].bin_start_ft.tolist(),[0.,25.]);self.assertEqual(q[q.bin_start_ft.eq(50)].stopped_frames.iloc[0],0);pd.testing.assert_frame_equal(q,bin_stops(d,25.))
    def test_post_stop_episode_annotation_available(self):
        q=pd.read_csv(OUT/'post_control_stops.csv');self.assertTrue(q.distance_ft.gt(0).all());self.assertTrue(q.onset_region.isin(['POST_CONTROL_REGION','BEYOND_CURRENT_EXIT']).all())
    def test_block_detection_requires_both_sides_and_green(self):
        q=pd.DataFrame({'direction':[4]*4,'tick':[0,1,2,3],'time':[0,.1,.2,.3],'upstream_stopped':[1]*4,'downstream_stopped':[1]*4,'downstream_occupancy':[1]*4,'last_control_phase':['RED','GREEN','GREEN','GREEN'],'crossings':[0,0,0,1]})
        e=block_episodes(q);self.assertEqual(len(e),1);self.assertAlmostEqual(e.duration_s.iloc[0],.2)
        q['downstream_stopped']=0;self.assertEqual(len(block_episodes(q)),0)
    def test_identical_source_sim_scope_mask(self):
        d=pd.DataFrame({'direction':[2,2,4,4],'y':[400.,1400.,600.,500.]});r=d.assign(cohort_direction=d.direction)
        self.assertEqual(inside(d).tolist(),inside(r).tolist());self.assertEqual(inside(d).tolist(),[True,False,True,False])
    def test_scope_keeps_both_intersections(self):
        f=json.loads((OUT/'decision.json').read_text());self.assertEqual(f['keeps_intersections'],[2,3]);self.assertLess(400,632.5395);self.assertGreater(NEW_EXIT[2],1246.452);self.assertLess(NEW_EXIT[4],647.878)
    def test_scope_selected_before_fit(self):
        f=json.loads((OUT/'selection_order.json').read_text());self.assertTrue(f['scope_decided_before_SIM_evaluation']);self.assertFalse(f['sim_fit_used_for_cut_selection'])
    def test_b1_forbidden(self):
        for fun in [audit,evaluate]:
            with self.assertRaises(HoldoutLockedError):fun('B1')
    def test_prior_stages_hashes_preserved(self):
        hashes=json.loads((OUT/'pre_revision_hashes.json').read_text())['hashes']
        for p,expected in hashes.items():self.assertEqual(digest(ROOT/p),expected,p)
    def test_new_exits_event_ledger_and_conservation(self):
        d=inputs([vehicle(10.,8.)]);d['receiving_scope']={'exit_ft':{'2':450.,'4':450.}}
        m=ReducedBoundaryModel({'steps':30,'seed':10},inputs=d,idm=P,trace=False,queue_gap=3.);m.run(display=False)
        self.assertEqual(m.exited,1);self.assertEqual(len(m.recorder.exits),1);self.assertEqual(len(m.agents),0);self.assertTrue(m.summary['conservation_verified'])
        self.assertEqual(m.all_agents[0].state,'EXITED');self.assertLess(m.all_agents[0].exit_time,3.)
    def test_no_replay_in_boundary_step(self):
        import inspect
        s=inspect.getsource(ReducedBoundaryModel.step);self.assertNotIn('read_parquet',s);self.assertNotIn('real_position',s);self.assertNotIn('agent.position =',s)
    def test_old_parameter_and_threshold_freeze(self):
        f=json.loads((OUT/'decision.json').read_text());self.assertFalse(f['IDM_changed']);self.assertFalse(f['threshold_changed']);self.assertFalse(f['stoplines_changed']);self.assertFalse(f['offsets_changed'])
    def test_downstream_leader_partition(self):
        q=pd.read_csv(OUT/'post_control_leaders.csv');q=q[q.denominator>0]
        self.assertTrue(np.allclose(q.groupby(['direction','region','subset']).fraction.sum(),1.))

if __name__=='__main__':unittest.main()
