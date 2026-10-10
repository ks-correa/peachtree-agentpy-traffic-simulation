import csv, io, json, unittest
from scripts.evaluate_local import ROOT, inventory, digest, is_trajectory, parse_csv, period_from_path

class AuditTests(unittest.TestCase):
    def test_parser(self):
        self.assertEqual(list(parse_csv(io.BytesIO(b' Station_Id, Global_Time\r\r\n1,2\r\r\n'))), [['Station_Id','Global_Time'],[],['1','2'],[]])

    def test_detector_not_trajectory(self):
        audit=json.loads((ROOT/'outputs/data_quality_audit.json').read_text(encoding='utf-8'))
        self.assertFalse(is_trajectory(audit['detector']['columns']))
        self.assertEqual(audit['trajectory_rows'],0)
        self.assertIsNone(audit['unique_vehicles'])

    def test_period_detection(self):
        self.assertEqual(period_from_path('data-analysis/0400pm-0415pm/report.pdf'),'0400pm-0415pm')
        self.assertIsNone(period_from_path('detector-data.csv'))

    def test_source_integrity(self):
        audit=json.loads((ROOT/'outputs/data_quality_audit.json').read_text(encoding='utf-8'))
        for path,expected in audit['sources'].items(): self.assertEqual(digest(ROOT/path),expected)

    def test_reproducible_inventory(self):
        with (ROOT/'outputs/dataset_inventory.csv').open(encoding='utf-8',newline='') as f: saved=list(csv.DictReader(f))
        actual=inventory(ROOT/'data/I-80-Emeryville-CA.zip')
        self.assertEqual([r['path'] for r in saved],[r['path'] for r in actual])
        self.assertEqual([int(r['size_bytes']) for r in saved],[r['size_bytes'] for r in actual])

    def test_unavailable_metrics_not_zero(self):
        for file in ['car_following_summary.csv','lane_change_summary.csv','merge_summary.csv']:
            with (ROOT/'outputs'/file).open(encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f): self.assertEqual(row['value'],'')

    def test_no_fabricated_split(self):
        with (ROOT/'outputs/train_test_strategy_comparison.csv').open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                self.assertEqual(r['status'],'MISSING_VEHICLE_TRAJECTORIES')
                self.assertEqual(r['train_rows'],'')

    @unittest.skip('No local trajectories: cannot test Vehicle_ID or identity leakage')
    def test_vehicle_id_and_no_leakage(self): pass
    @unittest.skip('No local trajectories: cannot test vehicle time monotonicity')
    def test_vehicle_time(self): pass
    @unittest.skip('No local trajectories: cannot test leader/follower references')
    def test_leader_follower(self): pass
    @unittest.skip('No local trajectories: cannot test headway semantics')
    def test_headway(self): pass
    @unittest.skip('No local trajectories: cannot test lane-change detection')
    def test_lane_changes(self): pass
    @unittest.skip('No local trajectories: cannot verify real TRAIN/TEST isolation')
    def test_train_test_isolation(self): pass

if __name__=='__main__': unittest.main()
