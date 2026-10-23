#!/usr/bin/env python3
"""Run only copied artifact tests; observe rejected mutation count."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
import artifact_checks
checker=artifact_checks.check_contract
validate=checker.validate_plan
counts={'rejected_mutations':0}
def observe(plan):
    try:return validate(plan)
    except ValueError:
        counts['rejected_mutations']+=1
        raise
checker.validate_plan=observe
suite=unittest.defaultTestLoader.loadTestsFromModule(artifact_checks)
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(suite)
assert result.wasSuccessful() and result.testsRun==3 and counts['rejected_mutations']==36
print(json.dumps({'artifact_tests':result.testsRun,**counts,'passed':True}))
