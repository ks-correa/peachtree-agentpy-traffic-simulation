"""Regression checks for unit-correct labels, frozen quantiles and export fidelity."""
import json,hashlib,unittest
import numpy as np
from PIL import Image
from ui.presentation_data import *

class StaticChartTests(unittest.TestCase):
    def test_paired_labels_use_exact_official_intervals_and_units(self):
        d=read_csv('outputs/peachtree6/paired_differences.csv')
        for key,factor,unit in [('travel_mean_s',1,'s'),('operational_stopped',100,'p.p.')]:
            fig=paired_chart(key);labels=' '.join(a.text for a in fig.layout.annotations)
            for r in d[d.scenario.eq('E1')&d.metric.eq(key)].itertuples():
                self.assertIn(f'{r.mean*factor:+.2f} {unit}',labels)
                self.assertIn(f'IC95 [{r.CI95_low*factor:.2f}, {r.CI95_high*factor:.2f}] {unit}',labels)
            self.assertLess(fig.layout.xaxis.range[0],0);self.assertGreater(fig.layout.xaxis.range[1],0)
    def test_scenario_labels_and_bars_reconcile(self):
        for c in ['B1','B2']:
            official=read_csv(f'outputs/peachtree6/{c.lower()}_scenario_summary.csv')
            for key,factor in [('travel_mean_s',1),('operational_stopped',100)]:
                fig=scenario_chart(c,key);data=official[official.metric.eq(key)].set_index('scenario');base=data.loc['BASE','mean']
                self.assertEqual([t.name for t in fig.data],['BASE','E1','E2','E3'])
                for t in fig.data:
                    r=data.loc[t.name];self.assertAlmostEqual(float(t.y[0]),r['mean']*factor)
                    self.assertIn(f'{r["mean"]*factor:.2f}',t.text[0])
                    if t.name!='BASE':self.assertIn(f'{(r["mean"]/base-1)*100:+.2f}%',t.text[0])
    def test_departure_quantiles_are_not_inferred_from_30s_bins(self):
        for c in ['B1','B2']:
            fig=departures(c);labels=' '.join(a.text for a in fig.layout.annotations)
            d=read_csv(f'outputs/peachtree6/{c.lower()}_scenario_summary.csv')
            for r in d[d.metric.isin(['departure_t50_s','departure_t90_s','departure_final_s'])].itertuples():self.assertIn(f'{r.mean:.2f}',labels)
            self.assertIn('temporal_departures.csv',fig.layout.meta['source_artifact']);self.assertIn('scenario_summary.csv',fig.layout.meta['source_artifact'])
    def test_all_exports_and_audit(self):
        audit=read_json('presentation_assets/presentation_chart_audit.json')
        self.assertTrue(audit['all_presentation_ready'])
        for r in audit['figures']:
            self.assertTrue(r['presentation_ready'],r['filename'])
            with Image.open(ASSETS/r['filename']) as im:
                self.assertEqual(im.size,(1920,1080));self.assertEqual(im.info['source_artifact'],r['source_artifact'])
    def test_boxplots_have_separate_context_positions(self):
        for filename in ['06_speed_boxplot.json','06_travel_boxplot.json']:
            fig=assets_chart(filename);self.assertEqual([t.x[0] for t in fig.data],['B1','B2'])
    def test_scientific_hashes(self):
        for path,h in read_json('presentation_assets/pre_chart_improvement_hashes.json').items():
            self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),h,path)

if __name__=='__main__':unittest.main()
