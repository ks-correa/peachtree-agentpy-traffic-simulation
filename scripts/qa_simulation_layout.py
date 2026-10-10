"""Run only presentation/UI tests, preserving scientific test reports."""
import json,unittest
from ui.presentation_data import ROOT,ASSETS

def main():
    suite=unittest.TestSuite()
    for pattern in ['test_presentation_dashboard.py','test_presentation_chart_labels.py','test_simulation_view.py']:
        suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    with (ASSETS/'simulation_test_details.log').open('w',encoding='utf-8') as log:
        r=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report={'UI_tests':r.testsRun,'passed':r.testsRun-len(r.failures)-len(r.errors),'failures':len(r.failures),'errors':len(r.errors),
        'scientific_tests_rerun':False,'new_scientific_experiments':False}
    (ASSETS/'simulation_test_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
    if not r.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
