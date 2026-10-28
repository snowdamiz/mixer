#!/usr/bin/env python3
"""Run exactly three mocked diagnostics; deny process/socket audit events."""
import hashlib
import importlib.util
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SOURCE = ROOT / 'verification/swift-cache-state-ci'
NAMES = [
    'test_mocked_primary_and_stop_exceptions_retain_terminal_receipt',
    'test_mocked_cleanup_only_exception_is_reported_and_held',
    'test_mocked_success_still_requires_positive_group_disappearance',
]
denied = []

def audit(event, args):
    if (event.startswith(('subprocess.', 'socket.', 'os.exec', 'os.spawn'))
            or event in {'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty',
                         'os.kill', 'os.killpg'}):
        denied.append(event)
        raise RuntimeError('Process/socket audit denial: ' + event)

sys.addaudithook(audit)
import unittest

def bindings():
    rows = []
    for name in ['check_cache_state.py', 'test_runner.py']:
        data = (SOURCE / name).read_bytes()
        rows.append({'path': str(SOURCE / name), 'bytes': len(data),
                     'sha256': hashlib.sha256(data).hexdigest()})
    return rows

before = bindings()
started = time.monotonic()
spec = importlib.util.spec_from_file_location('cache_mocked_diagnostic_controls', SOURCE / 'test_runner.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
suite = unittest.TestSuite(module.RunnerControls(name) for name in NAMES)
with (BASE / 'mocked-controls.stderr').open('x') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
after = bindings()
receipt = {
    'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 -B verification/swift-cache-controls-diagnostic-correction/run_mocked_controls.py',
    'python': sys.version, 'selected_methods': NAMES,
    'tests_run': result.testsRun, 'failures': len(result.failures),
    'errors': len(result.errors), 'skipped': len(result.skipped),
    'denied_process_or_socket_events': denied,
    'process_socket_audit_denial_installed_before_runner_import': True,
    'all_Popen_killpg_read_and_process_wait_interactions_mocked': True,
    'real_process_or_group_discovery_attempted': False,
    'full_runner_suite_executed': False, 'compiler_executed': False,
    'source_before': before, 'source_after': after,
    'source_unchanged_during_controls': before == after,
    'elapsed_seconds': round(time.monotonic() - started, 6),
    'scope': 'Three synthetic-process diagnostics only; no original CI cause, process cleanup, compiler, native, release or GA validation',
}
passed = result.wasSuccessful() and not denied and before == after and result.testsRun == 3
receipt['status'] = 'passed-three-mocked-diagnostic-controls' if passed else 'failed'
with (BASE / 'mocked-controls.json').open('x') as stream:
    stream.write(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(json.dumps({'status': receipt['status'], 'tests_run': result.testsRun,
                  'denied_events': denied, 'source_unchanged': before == after}))
raise SystemExit(0 if passed else 1)
