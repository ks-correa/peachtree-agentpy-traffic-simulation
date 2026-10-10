"""Tests exercise real parsing/filter boundaries without inventing I-80 data."""
import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_export import (
    ROOT, BLOCKED, digest, i80_location, profile_export, read_rows, token_kind,
)


class ExportParserTests(unittest.TestCase):
    def test_locale_formats_remain_distinct(self):
        expected={
            '1,11885E+12':'comma_decimal_scientific',
            '2.230.502.921':'multiple_dot_groups_ambiguous',
            '2,195.462':'comma_grouped_candidate',
            '1,156':'comma_grouped_candidate',
            '-5.359':'dot_decimal_literal',
            '1163368300':'integer_literal',
            'NA':'missing', '':'missing', 'NaN':'missing',
        }
        for raw,kind in expected.items():
            with self.subTest(raw=raw): self.assertEqual(token_kind(raw),kind)

    def test_exact_location_filter(self):
        self.assertTrue(i80_location(' i-80 '))
        self.assertTrue(i80_location('I-80'))
        for other in ['us-101','peachtree','lankershim','I-800','some i-80 site','']:
            self.assertFalse(i80_location(other))

    def test_parser_filter_preserves_raw_values(self):
        content=('Vehicle_ID;Frame_ID;Global_Time;Lane_ID;Location\n'
                 '1;2;1,11885E+12;1;us-101\n'
                 '2;3;1234567890123;2;I-80\n'
                 '3;4;4;3;peachtree\n')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source.csv'; subset=root/'subset.csv'
            source.write_text(content,encoding='utf-8'); before=digest(source)
            report=profile_export(source,subset)
            self.assertEqual(report['rows'],3)
            self.assertEqual(report['i80_rows'],1)
            self.assertEqual(report['i80_vehicle_ids'],1)
            entries=list(read_rows(subset))
            self.assertEqual(entries[1],['2','3','1234567890123','2','I-80'])
            self.assertEqual(len(entries),2)
            self.assertEqual(digest(source),before)
            first_subset=digest(subset)
            self.assertEqual(report,profile_export(source,subset))
            self.assertEqual(digest(subset),first_subset)

    def test_empty_subset_is_header_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source.csv'; subset=root/'subset.csv'
            source.write_text('Vehicle_ID;Frame_ID;Global_Time;Lane_ID;Location\n1;2;3;4;us-101\n',encoding='utf-8')
            report=profile_export(source,subset)
            self.assertEqual(report['i80_rows'],0)
            self.assertEqual(len(list(read_rows(subset))),1)

    def test_missing_location_cannot_be_certified(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'source.csv'
            source.write_text('Vehicle_ID;Frame_ID\n1;2\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Missing Location'):
                profile_export(source,root/'subset.csv')


class ActualExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((ROOT/'outputs/i80_trajectory_audit.json').read_text(encoding='utf-8'))

    def test_population_reconciliation(self):
        p=self.audit['export']
        self.assertEqual(p['rows'],sum(p['locations_exact'].values())+p['malformed_rows'])
        for name,c in p['column_profiles'].items():
            self.assertEqual(sum(c['lexical_types'].values()),p['rows']-p['malformed_rows'],name)
        self.assertEqual(p['i80_rows'],sum(n for site,n in p['locations_exact'].items() if i80_location(site)))
        self.assertEqual(self.audit['reason'],BLOCKED)

    def test_independent_full_location_scan(self):
        from collections import Counter
        counts=Counter()
        with (ROOT/'data/export.csv').open(encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f,delimiter=';'): counts[row['Location']]+=1
        self.assertEqual(dict(counts),self.audit['export']['locations_exact'])

    def test_export_and_subset_integrity(self):
        self.assertEqual(digest(ROOT/'data/export.csv'),self.audit['source_sha256'])
        m=json.loads((ROOT/'outputs/working/i80_subset_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(m['source_sha256'],self.audit['source_sha256'])
        self.assertEqual(digest(ROOT/'outputs/working/i80_trajectories_raw.csv'),m['subset_sha256'])
        self.assertEqual(len(list(read_rows(ROOT/'outputs/working/i80_trajectories_raw.csv'))),1)

    def test_previous_audit_preserved(self):
        archive=ROOT/'outputs/archive/audit_without_trajectories'
        manifest=json.loads((archive/'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['label'],'AUDIT_WITHOUT_TRAJECTORIES')
        for rel,expected in manifest['files_sha256'].items():
            self.assertEqual(digest(archive/rel),expected)
        old=(archive/'docs/ngsim_i80_feasibility.md').read_text(encoding='utf-8')
        self.assertIn('No existe un archivo de trayectorias',old)

    def test_unavailable_percentages_are_null(self):
        for name,check in self.audit['i80_checks'].items():
            self.assertIsNone(check['value'],name)
            self.assertEqual(check['status'],'NOT_EVALUABLE')
        with (ROOT/'outputs/i80_car_following_summary.csv').open(encoding='utf-8',newline='') as f:
            for row in csv.DictReader(f): self.assertEqual(row['value'],'')

    def test_no_fabricated_split_or_transferability(self):
        for name,fields in [('i80_train_test_comparison.csv',['train_rows','test_rows','vehicle_id_overlap']),
                            ('i80_transferability.csv',['difference_mean','difference_median','ks','wasserstein'])]:
            with (ROOT/'outputs'/name).open(encoding='utf-8',newline='') as f:
                for row in csv.DictReader(f):
                    self.assertEqual(row['status'],BLOCKED)
                    for field in fields:self.assertEqual(row[field],'')


if __name__=='__main__': unittest.main()
