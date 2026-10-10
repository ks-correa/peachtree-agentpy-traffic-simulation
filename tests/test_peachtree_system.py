import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.evaluate_local import digest
from scripts.peachtree_system import (trajectory_key,canonicalize,parse_signal,lookup_state,
    fixed_gate_crossings,pair_travel_times,confirm_lane_changes,INTERSECTIONS,MOVEMENTS,DIRECTIONS)
from scripts.reconstruct_peachtree import signal_verification

ROOT=Path(__file__).resolve().parents[1]


def record(frame=1,y=5.,x=0.,acq='B1',vehicle=1,direction=2,lane=1):
    return {'acquisition_id':acq,'trajectory_key':acq+':'+str(vehicle),'vehicle_id':vehicle,
        'frame_id':frame,'global_time':10000+frame*100,'total_frames':3,'t_relative':(frame-1)*.1,
        'local_x':x,'local_y':y,'global_x':x,'global_y':y,'v_vel':100.,'v_acc':0.,
        'lane_id':lane,'section_id':2,'int_id':0,'direction':direction,'movement':1,
        'v_class':2,'v_length':15.,'v_width':7.,'preceding':0,'following':0,
        'space_headway':0.,'time_headway':0.,'o_zone':101,'d_zone':214,'location':'peachtree'}


class SystemMethodsTests(unittest.TestCase):
    def test_tuple_identity_and_no_cross_acquisition_pairing(self):
        self.assertEqual(trajectory_key('B1',1),('B1',1))
        self.assertNotEqual(trajectory_key('B1',1),trajectory_key('B2',1))
        with self.assertRaises(ValueError):trajectory_key('unknown',1)
        d=pd.DataFrame([record(1,5),record(2,15),record(1,15,acq='B2'),record(2,25,acq='B2')])
        crossings=fixed_gate_crossings(d,10.,20.)
        self.assertEqual(len(crossings),2)
        self.assertTrue(pair_travel_times(crossings,10.,20.).empty)

    def test_relative_clock_origin_and_determinism(self):
        records=[]
        for origin in [10000,10100]:
            for f in [5,6,7]:
                r=record(f);r['global_time']=origin+f*100;records.append(r)
        original=pd.DataFrame(records)
        original=original.drop(columns=['acquisition_id','trajectory_key','t_relative'])
        untouched=original.copy(deep=True)
        a,clock=canonicalize(original)
        b,otherclock=canonicalize(original.sample(frac=1,random_state=9))
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(clock,otherclock)
        self.assertTrue(a.groupby('acquisition_id').t_relative.min().eq(0).all())
        self.assertTrue(a.groupby('trajectory_key').t_relative.diff().dropna().sub(.1).abs().lt(1e-12).all())
        pd.testing.assert_frame_equal(original,untouched)

    def test_documented_topology_and_movement(self):
        self.assertEqual(INTERSECTIONS[2],('11th',52,'SIGNAL'))
        self.assertEqual(INTERSECTIONS[3],('12th',53,'SIGNAL'))
        self.assertEqual(INTERSECTIONS[4],('13th',None,'STOP'))
        self.assertEqual(MOVEMENTS,{1:'THROUGH',2:'LEFT_TURN',3:'RIGHT_TURN'})
        self.assertEqual(DIRECTIONS[2],'NB');self.assertEqual(DIRECTIONS[4],'SB')

    def test_signal_parser_boundaries_unknown_and_timing(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'signal.txt';p.write_text('BG_Thru\tBY_Thru\tBR_Thru\n10\t20\t25\n40\t50\t55\n')
            bank,warnings,raw=parse_signal(p);phase=bank['Thru']
            self.assertEqual(lookup_state([9,10,19,20,24,25,39,40],phase).tolist(),
                ['UNKNOWN','GREEN','GREEN','YELLOW','YELLOW','RED','RED','GREEN'])
            self.assertEqual(phase['green_s'].tolist(),[1.,1.])
            self.assertEqual(phase['cycle_s'].tolist(),[3.])

    def test_conflicting_phase_is_unknown_not_silently_backfilled(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'bad.txt';p.write_text('BG_Thru\tBY_Thru\tBR_Thru\n10\t20\t25\n25\t40\t50\n')
            bank,warnings,raw=parse_signal(p)
            self.assertIn('CONFLICTING_STATES_AT_SAME_FRAME',warnings)
            self.assertEqual(lookup_state([25,30],bank['Thru']).tolist(),['UNKNOWN','UNKNOWN'])

    def test_synchronization_uses_fixed_reference_not_fitted_offset(self):
        phase={'frames':np.array([10,20,30,40]),'states':np.array(['GREEN','YELLOW','RED','GREEN'])}
        d=pd.DataFrame([record(11,y=500),record(12,y=500),record(31,y=500)])
        d.loc[d.frame_id==31,'v_vel']=0.;d.loc[d.frame_id<20,'v_vel']=20.
        entry=d.copy();entry['intersection_id']=2
        mouth=pd.DataFrame([{'intersection_id':2,'direction':2,'event':'ENTRY','crossing_y_median_ft':600.}])
        result=signal_verification(d,entry,mouth,{('B1',2,2,'Thru'):phase})
        self.assertEqual(result.status.iloc[0],'SIGNAL_SYNC_CONFIRMED')
        self.assertFalse(result.offset_fitted.iloc[0])

    def test_physical_entry_exit_and_travel_time_not_last_minus_first(self):
        d=pd.DataFrame([record(1,5),record(2,15),record(3,25)])
        events=fixed_gate_crossings(d,10.,20.)
        self.assertEqual(events.event.tolist(),['ENTRY','EXIT'])
        self.assertAlmostEqual(events.t_cross_s.iloc[0],.05)
        self.assertAlmostEqual(events.t_cross_s.iloc[1],.15)
        paired=pair_travel_times(events,10.,20.)
        self.assertAlmostEqual(paired.travel_time_s.iloc[0],.1)
        self.assertNotAlmostEqual(paired.travel_time_s.iloc[0],d.t_relative.max()-d.t_relative.min())
        self.assertEqual(len(events[events.event=='EXIT']),1) # Throughput counts crossings, not three rows.

    def test_first_appearance_inside_is_not_entry(self):
        d=pd.DataFrame([record(1,15),record(2,25)])
        events=fixed_gate_crossings(d,10.,20.)
        self.assertEqual(events.event.tolist(),['EXIT'])
        self.assertTrue(pair_travel_times(events,10.,20.).empty)

    def test_discontinuous_jump_does_not_create_valid_route(self):
        d=pd.DataFrame([record(1,5),record(2,25)])
        d['v_vel']=0.
        events=fixed_gate_crossings(d,10.,20.)
        self.assertTrue(events.spatial_discontinuity_flag.all())
        self.assertTrue(pair_travel_times(events,10.,20.).empty)

    def test_southbound_physical_entry_exit(self):
        d=pd.DataFrame([record(1,25,direction=4),record(2,15,direction=4),record(3,5,direction=4)])
        events=fixed_gate_crossings(d,10.,20.)
        self.assertEqual(events.boundary.tolist(),['NORTH_CUT','SOUTH_CUT'])
        self.assertEqual(events.event.tolist(),['ENTRY','EXIT'])

    def test_confirmed_lane_change_and_bay_exclusion(self):
        rows=[]
        for i in range(30):
            r=record(i+1,y=i*5.,x=max(0,min(10,(i-5)*.5)),lane=1 if i<15 else 2)
            rows.append(r)
        d=pd.DataFrame(rows);events=confirm_lane_changes(d)
        self.assertEqual(events.confirmed.sum(),1)
        d.loc[d.lane_id==2,'lane_id']=11
        self.assertEqual(confirm_lane_changes(d).confirmed.sum(),0)


class ActualSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((ROOT/'outputs/peachtree_system_audit.json').read_text(encoding='utf-8'))

    def test_all_sources_stay_intact(self):
        for rel,expected in self.audit['source_hashes'].items():
            self.assertEqual(digest(ROOT/rel),expected)

    def test_documented_sections_intersections(self):
        sections=pd.read_csv(ROOT/'outputs/peachtree_sections.csv')
        ints=pd.read_csv(ROOT/'outputs/peachtree_intersections.csv')
        self.assertEqual(sections.section_id.tolist(),[1,2,3,4,5,6])
        self.assertEqual(ints.intersection_id.tolist(),[1,2,3,4,5])
        self.assertEqual(ints.loc[ints.intersection_id==4,'control_type'].iloc[0],'STOP')
        self.assertEqual(ints.loc[ints.intersection_id.isin([2,3]),'signal_sync_status'].tolist(),['SIGNAL_SYNC_CONFIRMED']*2)

    def test_real_clock_counts_and_document_association(self):
        z=pd.read_csv(ROOT/'outputs/peachtree_acquisition_timing.csv')
        self.assertEqual(z.rows.sum(),873887)
        self.assertEqual(z.relative_start_s.tolist(),[0,0])
        self.assertEqual(z.relative_end_s.tolist(),[1020.3,1032.7])
        self.assertTrue(z.epoch_status.eq('NOT_USED_OR_CORRECTED').all())

    def test_real_physical_cohort_pairs_and_conservation(self):
        events=pd.read_csv(ROOT/'outputs/peachtree_physical_gate_events.csv')
        tt=pd.read_csv(ROOT/'outputs/peachtree_fixed_gate_travel_times.csv')
        self.assertTrue(tt.travel_time_s.gt(0).all())
        self.assertTrue(tt.measurement_length_ft.eq(1000).all())
        self.assertTrue(tt.entry_time_s.lt(tt.exit_time_s).all())
        pairs=events.groupby(['acquisition_id','trajectory_key','event']).size().unstack('event',fill_value=0)
        self.assertTrue(pairs.ENTRY.eq(1).all());self.assertTrue(pairs.EXIT.eq(1).all())
        self.assertTrue(events.local_y_cross_ft.isin([400.,1400.]).all())
        self.assertEqual(len(pairs),len(tt))

    def test_real_throughput_matches_events_not_records(self):
        counted=pd.read_csv(ROOT/'outputs/peachtree_throughput_crossings.csv')
        events=pd.read_csv(ROOT/'outputs/peachtree_physical_gate_events.csv')
        self.assertEqual(int(counted.crossings.sum()),len(events))
        self.assertEqual(int(counted[counted.event=='EXIT'].crossings.sum()),len(events[events.event=='EXIT']))
        self.assertLess(len(events),sum(r['scope_rows'] for r in self.audit['scope_comparison']))

    def test_parquet_qc_scope_identity_and_integrity(self):
        for manifest in self.audit['cf_preparation']:
            p=ROOT/manifest['path'];self.assertEqual(digest(p),manifest['sha256'])
            z=pd.read_parquet(p)
            self.assertEqual(len(z),manifest['rows'])
            self.assertTrue(z.acquisition_id.eq(manifest['acquisition_id']).all())
            self.assertTrue(z.trajectory_key.str.startswith(manifest['acquisition_id']+':').all())
            self.assertTrue(z.gap.gt(0).all())
            self.assertTrue(z.signal_state.isin(['GREEN','YELLOW','RED']).all())
            self.assertTrue(z.movement.eq(1).all())
            self.assertFalse(np.isclose(z.acceleration.abs(),12.27).any())
            self.assertTrue(z.control_intersection.isin([2,3]).all())

    def test_confirmed_events_follow_protocol(self):
        z=pd.read_csv(ROOT/'outputs/peachtree_confirmed_lane_changes.csv')
        self.assertTrue(z.confirmed.all())
        self.assertTrue(z.origin_lane.sub(z.destination_lane).abs().eq(1).all())
        self.assertTrue(z.int_id.eq(0).all())
        self.assertFalse(z.turn_bay_transition.any())
        self.assertTrue(z.before_run_frames.ge(5).all())
        self.assertTrue(z.after_run_frames.ge(5).all())
        self.assertFalse(z.spatial_jump_in_event_window.any())

    def test_draft_is_not_a_freeze_or_calibration(self):
        for field in ['test_frozen','calibration_performed','abm_implemented','signal_offset_optimized']:
            self.assertFalse(self.audit[field])
        draft=(ROOT/'outputs/peachtree_validation_contract_draft.md').read_text(encoding='utf-8')
        self.assertIn('NOT FROZEN',draft)
        self.assertIn('NOT all',draft)
        self.assertIn('Omitted turning/local',draft)

    def test_actual_deterministic_output_hashes(self):
        proof=json.loads((ROOT/'outputs/peachtree_deterministic_preprocessing.json').read_text(encoding='utf-8'))
        self.assertTrue(proof['all_match'])
        self.assertEqual(proof['outputs_checked'],7)
        for rel,record in proof['files'].items():
            self.assertTrue(record['unchanged_on_repeated_preprocessing'])
            self.assertEqual(digest(ROOT/'outputs'/rel),record['sha256'])


if __name__=='__main__':unittest.main()
