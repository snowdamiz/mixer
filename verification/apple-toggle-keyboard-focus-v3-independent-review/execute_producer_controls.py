#!/usr/bin/env python3
"""Run the exact sealed 44-method suite, with exporter output isolated here.

The original test module is loaded byte-for-byte. Its mocked exporter exception
test otherwise attempts to write a preparation/runtime receipt even in a host
test. Redirecting only that exporter's BASE prevents writes to the sealed packet.
"""
import importlib.util
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
PRODUCER = HERE.parent / 'apple-toggle-keyboard-focus-v3-preparation'
sys.path.insert(0, str(PRODUCER))
import run

scratch = HERE / '.scratch'
scratch.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='producer-controls-', dir=scratch) as temporary:
    original = run.runtime.BASE
    run.runtime.BASE = pathlib.Path(temporary)
    try:
        spec = importlib.util.spec_from_file_location('sealed_v3_controls', PRODUCER / 'test_settings_telemetry.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    finally:
        run.runtime.BASE = original
sys.exit(0 if result.wasSuccessful() and result.testsRun == 44 else 1)
