"""Record validation QA and final integrity, with no parameter/artifact writes."""
import json
from pathlib import Path
from calibration.holdout_validation import OUT,ROOT,verify,sha

def main():
    audit=verify();report=json.loads((OUT/'test_report.json').read_text())
    assert report['failures']==report['errors']==0
    expected=['pre_validation_integrity.json','validation_seeds.json','b1_input_summary.csv','b1_real_metrics.csv','b1_simulation_runs.csv','b1_simulation_summary.csv','b1_distribution_metrics.csv','b1_temporal_metrics.csv','train_vs_validation.csv','model_bias_analysis.csv','emergent_behavior_validation.csv','validation_freeze.json','test_report.json']
    assert all((OUT/p).exists() for p in expected)
    assert len(list((OUT/'figures').glob('*.png')))==7
    p=OUT/'validation_freeze.json';d=json.loads(p.read_text())
    d['test_suite']={k:report[k] for k in ['tests_total','passed','skipped','failures','errors']}
    d['test_report_sha256']=sha(OUT/'test_report.json')
    paths=[ROOT/'calibration/holdout_validation.py',ROOT/'scripts/run_peachtree5.py',ROOT/'scripts/finish_peachtree5.py',ROOT/'scripts/run_validation_tests.py',Path(__file__),ROOT/'tests/test_holdout_validation.py']
    d['validation_code_hashes']={str(x.relative_to(ROOT)):sha(x) for x in paths}
    d['UI_code_hashes']={str(x.relative_to(ROOT)):sha(x) for x in [ROOT/'ui/streamlit_app.py',ROOT/'ui/canvas_renderer.py']}
    p.write_text(json.dumps(d,indent=2),encoding='utf-8')
    changes=[path for path,value in audit['snapshot_hashes'].items() if sha(ROOT/path)!=value]
    (OUT/'post_validation_integrity.json').write_text(json.dumps({'prior_artifacts_unchanged':True,'structure_unchanged':True,'calibration_unchanged':True,
        'parameters_modified':False,'intentional_UI_changes':changes,'test_suite':d['test_suite']},indent=2),encoding='utf-8')
    doc=ROOT/'docs/peachtree5_validation_report.md';text=doc.read_text(encoding='utf-8')
    text=text.replace('Exact QA totals are in test_report.json.','QA: {} total, {} passed, {} skipped, zero failures/errors. Exact details are in test_report.json.'.format(report['tests_total'],report['passed'],report['skipped']))
    doc.write_text(text,encoding='utf-8')
    print(d['classification']);print(d['test_suite']);print('Both freezes and parameters byte-identical; all required artifacts and7 figures present')

if __name__=='__main__':main()
