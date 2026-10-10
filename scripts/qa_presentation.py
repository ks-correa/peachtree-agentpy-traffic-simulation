"""QA only new presentation layer. Scientific tests/results remain untouched."""
import json,unittest,hashlib
from pathlib import Path
from ui.presentation_data import ROOT,ASSETS

def main():
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_presentation_dashboard.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    old=json.loads((ROOT/'outputs/peachtree6/test_report.json').read_text())
    report=dict(presentation_tests=result.testsRun,passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
        failures=len(result.failures),errors=len(result.errors),scientific_test_report_retained=old,
        no_scientific_test_rerun=True,no_new_experiments=True)
    (ASSETS/'test_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
