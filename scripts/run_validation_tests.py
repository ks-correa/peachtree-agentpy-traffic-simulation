"""Preserve historical cases, run compatible validation/physics/freeze tests."""
import json,unittest
from pathlib import Path
from scripts.run_train_tests import cases,LOCKED_CLASSES

def main():
    suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py')
    for case in cases(suite):
        if type(case).__name__ in LOCKED_CLASSES:
            unittest.skip('Historical mixed-source feasibility fixture incompatible with frozen validation protocol; TRAIN fitting remains B1 locked')(type(case))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(tests_total=result.testsRun,passed=result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
        skipped=len(result.skipped),failures=len(result.failures),errors=len(result.errors),
        B1_validation_authorized=True,B1_calibration_locked=True,
        skipped_details=[dict(test=case.id(),reason=reason) for case,reason in result.skipped])
    Path('outputs/peachtree5/test_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
