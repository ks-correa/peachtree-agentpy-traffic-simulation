import json
import unittest
from pathlib import Path

import pandas as pd

from scripts.audit_peachtree import ROOT, SOURCE, detect_components, join_relations, lane_events, trajectory_table
from scripts.evaluate_local import digest


def row(component='B1',vehicle=1,frame=1,leader=0,follower=0,lane=1):
    return dict(component=component,vehicle_id=vehicle,frame_id=frame,total_frames=3,
        global_time=10000+frame*100,relative_s=frame*.1,local_x=1.,local_y=frame*3.+vehicle*30.,
        global_x=1.,global_y=frame*3.+vehicle*30.,v_length=15.,v_width=7.,v_class=2,
        v_vel=30.,v_acc=0.,lane_id=lane,o_zone=101,d_zone=201,int_id=0,
        section_id=1,direction=2,movement=1,preceding=leader,following=follower,
        space_headway=30. if leader else 0.,time_headway=1. if leader else 0.,location='peachtree')


class PeachtreeMethodsTests(unittest.TestCase):
    def test_affine_groups_detected_despite_interleaved_timestamps(self):
        rows=[]
        for origin in [10000,10100]:
            for frame in [1,2,3]:
                r=row(frame=frame);r['global_time']=origin+frame*100;rows.append(r)
        d,clock=detect_components(pd.DataFrame(rows))
        self.assertEqual(clock['large_gap_count'],0)
        self.assertEqual(clock['affine_component_count'],2)
        self.assertEqual(d.groupby('component').size().tolist(),[3,3])
        self.assertEqual(clock['calendar_labels_status'],'UNCONFIRMED_FOR_LOCAL_ACQUISITION_COMPONENTS')

    def test_leader_join_isolated_by_component_and_frame(self):
        d=pd.DataFrame([row(leader=2),row(vehicle=2,follower=1),
            row(component='B2',leader=2),row(component='B2',vehicle=2,follower=1)])
        d.loc[3,'v_vel']=10.
        r=join_relations(d)
        self.assertEqual(r.leader_speed.iloc[0],30.)
        self.assertEqual(r.leader_speed.iloc[2],10.)
        self.assertTrue(r.loc[[0,2],'leader_reciprocal'].all())
        self.assertTrue(r.loc[[0,2],'car_following_usable'].all())

    def test_missing_leader_is_not_matched_to_another_frame(self):
        r=join_relations(pd.DataFrame([row(leader=2),row(vehicle=2,frame=2)]))
        self.assertFalse(r.leader_valid.iloc[0])

    def test_ambiguous_relation_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            join_relations(pd.DataFrame([row(),row()]))

    def test_context_and_sentinel_filter(self):
        d=pd.DataFrame([row(leader=2),row(vehicle=2,follower=1)])
        d.loc[0,'time_headway']=9999.99
        r=join_relations(d)
        self.assertTrue(r.car_following_usable.iloc[0])
        self.assertFalse(r.finite_time_headway_usable.iloc[0])
        d.loc[1,'direction']=4
        self.assertFalse(join_relations(d).car_following_usable.iloc[0])

    def test_temporal_gap_and_complete_trajectory_detection(self):
        d=pd.DataFrame([row(frame=f) for f in [1,2,4]])
        s,t=trajectory_table(d)
        self.assertTrue(t.has_gap.iloc[0])
        self.assertFalse(t.observed_journey_candidate.iloc[0])
        self.assertAlmostEqual(t.duration_s.iloc[0],.3)

    def test_excursions_nonadjacent_and_turn_bay(self):
        d=pd.DataFrame([row(frame=i+1,lane=lane) for i,lane in enumerate([1,2,1,1,3,3,3,11])])
        d['total_frames']=8
        s,t=trajectory_table(d)
        events,summary=lane_events(s)
        self.assertEqual(len(events),4)
        self.assertEqual(events.one_frame_excursion_transition.sum(),2)
        self.assertEqual(events.nonadjacent_main_lane_transition.sum(),1)
        self.assertEqual(events.semantic_candidate.sum(),1)
        self.assertEqual(events[events.semantic_candidate].destination_lane.iloc[0],11)
        self.assertTrue(events.headway_before_ft.isna().all())
        self.assertTrue(events.headway_after_ft.isna().all())
        self.assertTrue(events.headway_after_ft_raw.eq(0).all())


class PeachtreeSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((ROOT/'outputs/peachtree_dataset_audit.json').read_text(encoding='utf-8'))

    def test_source_integrity_and_reconciliation(self):
        self.assertEqual(digest(SOURCE),self.audit['source_sha256'])
        self.assertEqual(sum(p['rows'] for p in self.audit['periods']),873887)
        self.assertEqual(sum(p['vehicles'] for p in self.audit['periods']),self.audit['component_vehicle_trajectories'])

    def test_actual_frames_and_identity_isolation(self):
        d=pd.read_csv(SOURCE)
        d,clock=detect_components(d)
        self.assertEqual(sorted(d.location.unique()),['peachtree'])
        self.assertFalse(d.duplicated(['component','frame_id','vehicle_id']).any())
        counts=d.groupby(['component','vehicle_id']).size()
        declared=d.groupby(['component','vehicle_id']).total_frames.first()
        pd.testing.assert_series_equal(counts,declared,check_names=False)
        delta=d.sort_values(['component','vehicle_id','frame_id']).groupby(['component','vehicle_id']).global_time.diff().dropna()
        self.assertTrue(delta.eq(100).all())

    def test_source_not_declared_frozen_or_calibrated(self):
        for field in ['test_frozen','calibration_performed','abm_implemented']:
            self.assertFalse(self.audit[field])
        strategies=pd.read_csv(ROOT/'outputs/peachtree_train_test_strategies.csv')
        self.assertEqual(strategies.loc[strategies.recommended,'train'].tolist(),['B2'])
        self.assertTrue(strategies.component_vehicle_key_overlap.eq(0).all())

    def test_reciprocal_counts_and_filter_denominators(self):
        for r in self.audit['leader_follower']:
            self.assertEqual(r['leader_missing_same_frame'],0)
            self.assertEqual(r['leader_reciprocity_pct_conditional'],100.)
            self.assertLessEqual(r['usable_car_following_rows'],r['valid_leader_rows'])
            self.assertAlmostEqual(r['usable_car_following_pct'],100*r['usable_car_following_rows']/r['rows'])

    def test_transferability_orientation_and_categorical_types(self):
        z=pd.read_csv(ROOT/'outputs/peachtree_transferability.csv')
        self.assertTrue(z.train_component.eq('B2').all())
        self.assertTrue(z.test_component.eq('B1').all())
        c=z[z.indicator.str.startswith('vehicle_class_')]
        self.assertTrue(c.ks_statistic.isna().all())
        self.assertTrue(c.wasserstein_distance.isna().all())


if __name__=='__main__':unittest.main()
