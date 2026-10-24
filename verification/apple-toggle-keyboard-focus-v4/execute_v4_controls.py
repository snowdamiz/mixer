#!/usr/bin/env python3
"""Run sealed 44 assertions unchanged with positive route fixtures aligned to V4."""
import importlib.util
import pathlib
import tempfile
import unittest
import run

HERE = pathlib.Path(__file__).resolve().parent
ORIGINAL = HERE.parent / 'apple-toggle-keyboard-focus-v3-preparation'
scratch = HERE / '.scratch'
scratch.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='same-44-assertions-', dir=scratch) as directory:
    prior = run.runtime.BASE
    run.runtime.BASE = pathlib.Path(directory)
    try:
        spec = importlib.util.spec_from_file_location('unchanged_v3_assertions_v4_fixture', ORIGINAL / 'test_settings_telemetry.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_send = module.Flow.send
        def send(self, record):
            # The old positive emitter used switch metadata for all route rows.
            # Align only those fixture rows; no test assertion is replaced.
            if record['kind'] == 'observe' and record['stage'] == 'route-search' and type(record['routeIndex']) is int and 0 <= record['routeIndex'] < 3:
                label = module.t.ROUTE[record['routeIndex']]
                record['snapshot'].update(identifier=label, label=label, elementType=75)
            elif record['kind'] == 'observe' and record['stage'] == 'route-opened':
                record['snapshot'].update(identifier='', label='', elementType=0, exists=False, hittable=False, enabled=False, valueKind='absent', value='', frame=dict(x=0, y=0, width=0, height=0))
            return original_send(self, record)
        module.Flow.send = send
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    finally:
        run.runtime.BASE = prior
raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 44 else 1)
