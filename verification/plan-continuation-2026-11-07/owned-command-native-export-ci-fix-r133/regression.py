#!/usr/bin/env python3
"""Run only the export regression; all Git and temp files stay in fresh userdata."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
os.environ.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                  GIT_TERMINAL_PROMPT='0', GIT_CONFIG_COUNT='0')
ownership = json.loads((HERE / 'ownership.json').read_text())
fixture = json.loads((HERE / 'fixture.json').read_text())
tempfile.tempdir = ownership['ownedRoot']
spec = importlib.util.spec_from_file_location('r133_test_builder',
    ROOT / 'experimental-capability-runtime/build-tests/test_builder.py')
tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tests)
# The suite's pinned ABI inputs are supplied by the fresh committed canonical
# fixture instead of invoking Git in the stalled original repository.
tests.PIN = fixture['revision']
tests.REPO = Path(ownership['repo'])
suite = unittest.TestSuite([tests.BuilderTests(
    'test_frozen_export_contains_declared_feature_gated_example')])
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
