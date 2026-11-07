#!/usr/bin/env python3
"""Replay unchanged candidate controls; redirect their temporary writes to review ownership."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'generated-java-ci-integration'
spec = importlib.util.spec_from_file_location('candidate_controls', CANDIDATE / 'test_bootstrap.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original = tempfile.TemporaryDirectory

def owned_temporary_directory(*args, **kwargs):
    if Path(kwargs.get('dir', HERE)) == CANDIDATE:
        kwargs['dir'] = HERE
    return original(*args, **kwargs)

tempfile.TemporaryDirectory = owned_temporary_directory
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
raise SystemExit(0 if result.wasSuccessful() else 1)
