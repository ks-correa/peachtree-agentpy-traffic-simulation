"""Keep legacy tests, block actual B1-reading fixtures before setUpClass."""
import unittest,json
from pathlib import Path

LOCKED_CLASSES={'ActualExportTests','ActualSystemTests','PeachtreeSourceTests'}
def cases(suite):
    for item in suite:
        if isinstance(item,unittest.TestSuite):yield from cases(item)
        else:yield item
def main(report_path=None):
    if report_path is None:
        report_path='outputs/peachtree3r/test_report.json' if Path('outputs/peachtree3r/revision_freeze.json').exists() else 'outputs/b2_test_report.json'
    suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py')
    for case in cases(suite):
        if type(case).__name__ in LOCKED_CLASSES:
            unittest.skip('B1 LOCKED: historical source/mixed-metric fixture retained, not opened in PEACHTREE-3')(type(case))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'tests_total':result.testsRun,'passed':result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
        'skipped':len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),
        'skipped_details':[{'test':t.id(),'reason':reason} for t,reason in result.skipped],'B1_LOCKED':True}
    Path(report_path).write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--report',default=None)
    main(parser.parse_args().report)
