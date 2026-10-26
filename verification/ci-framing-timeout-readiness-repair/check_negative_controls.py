"""Verify the repaired control still detects failed readiness and descendant leaks."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock

root = Path(__file__).resolve().parents[2]
path = root / 'scripts/ci/tests/test_analyzer_framing_runner.py'
spec = importlib.util.spec_from_file_location('framing_readiness_negative', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
real_popen, real_kill = subprocess.Popen, os.kill
run = module.MODULE.Commands.run
owned = []

def record_run(commands, *args, **kwargs):
    owned.append(commands)
    return run(commands, *args, **kwargs)

def unready_spawn(argv, *args, **kwargs):
    return real_popen([*argv[:2], 'raise SystemExit(0)', *argv[3:]], *args, **kwargs)

controls = []
for name, patch, expected in [
    ('parent-only-kill-is-detected', mock.patch.object(module.MODULE.os, 'killpg', real_kill),
     'True is not false'),
    ('startup-failure-is-detected-and-reaped', mock.patch.object(module.MODULE.subprocess, 'Popen', unready_spawn),
     'Owned timeout-control children did not become ready'),
]:
    owned.clear()
    log = io.StringIO()
    case = module.FramingRunnerTests('test_timeout_returns_owned_child_and_preserves_partial_logs')
    with patch, mock.patch.object(module.MODULE.Commands, 'run', record_run):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(case)
    if len(result.failures) != 1 or result.errors or expected not in result.failures[0][1]:
        raise AssertionError(name + '\n' + log.getvalue())
    if len(owned) != 1 or owned[0].active is not None or not owned[0].receipt['commands'][0]['child_returned']:
        raise AssertionError('owned parent not reaped')
    controls.append({'name': name, 'expected_failure_detected': True,
                     'owned_parent_reaped': True, 'output': log.getvalue()})
print(json.dumps({'status': 'passed', 'controls': controls}, indent=2))
