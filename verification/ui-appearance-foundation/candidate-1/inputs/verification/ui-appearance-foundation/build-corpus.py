#!/usr/bin/env python3
"""Capture every sealed design-oracle input for additional real Swift execution.
This records the oracle corpus; it adds no native resource/renderer authority.
"""
import base64
import importlib
import json
from pathlib import Path
import sys
import unittest
HERE = Path(__file__).resolve().parent
DESIGN = HERE.parent / 'ui-shared-appearance-contract/v2'
sys.path.insert(0, str(DESIGN))
tests = importlib.import_module('test_descriptor')
original = tests.decode
cases = []
active = ''
def capture(data):
    try:
        result = original(data)
    except tests.DescriptorError:
        cases.append(dict(name=active, base64=base64.b64encode(data).decode(), accepted=False))
        raise
    cases.append(dict(name=active, base64=base64.b64encode(data).decode(), accepted=True))
    return result
tests.decode = capture
suite = unittest.defaultTestLoader.loadTestsFromTestCase(tests.DescriptorTests)
result = unittest.TestResult()
for test in suite:
    active = test.id().split('.')[-1]
    test.run(result)
if not result.wasSuccessful():
    raise RuntimeError(result.errors + result.failures)
(HERE / 'design-corpus.json').write_text(json.dumps(cases, sort_keys=True, indent=2) + '\n')
print(f'{result.testsRun} design tests; {len(cases)} Swift corpus cases; {sum(c["accepted"] for c in cases)} accepted')
