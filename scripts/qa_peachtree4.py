"""Attach completed TRAIN QA without changing selection or previous artifacts."""
import json
from pathlib import Path
from calibration.final_calibration import OUT,ROOT,sha,verify_structure,plan

def main():
    p=OUT/'calibration_freeze.json';d=json.loads(p.read_text());q=json.loads((OUT/'test_report.json').read_text())
    assert q['failures']==q['errors']==0
    assert verify_structure()==d['structural_freeze_sha256']
    assert sha(OUT/'final_parameters.json')==d['final_parameters_sha256']
    plan()
    for path,expected in d['code_hashes'].items():
        if path!='tests\\test_final_calibration.py':assert sha(ROOT/path)==expected,path
    d['code_hashes']['tests\\test_final_calibration.py']=sha(ROOT/'tests/test_final_calibration.py')
    d['code_hashes'][str(Path(__file__).relative_to(ROOT))]=sha(Path(__file__))
    d['test_suite']={k:q[k] for k in ['tests_total','passed','skipped','failures','errors']}
    d['test_report_sha256']=sha(OUT/'test_report.json')
    prior=json.loads((OUT/'pre_calibration_hashes.json').read_text())
    assert all(sha(ROOT/path)==value for path,value in prior.items())
    required=['parameter_bounds.csv','development_seeds.json','calibration_candidates.csv','optimization_history.csv','parameter_sensitivity.csv','final_parameters.json','final_30_replica_runs.csv','final_30_replica_summary.csv','pre_vs_post_calibration.csv','temporal_comparison.csv','calibration_freeze.json','test_report.json']
    assert all((OUT/name).exists() for name in required)
    assert len(list((OUT/'figures').glob('*.png')))==7
    p.write_text(json.dumps(d,indent=2),encoding='utf-8')
    doc=ROOT/'docs/peachtree4_final_calibration.md';text=doc.read_text(encoding='utf-8')
    text=text.replace('Exact final counts are in outputs/peachtree4/test_report.json.',
        'Final QA: {} collected, {} passed, {} skipped, zero failures/errors. Exact details are in outputs/peachtree4/test_report.json.'.format(q['tests_total'],q['passed'],q['skipped']))
    doc.write_text(text,encoding='utf-8')
    print(d['classification']);print('QA:',d['test_suite']);print('Structure, parameters, prior artifacts and frozen plans verified unchanged')

if __name__=='__main__':main()
