"""Replay exact supplied tests using its supplied fake process implementation."""
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / 'native-custody-premise'
sys.path.insert(0, str(CANDIDATE))
import cleanup_control as c
import optimized_fake_controls as fake
import host_controls as controls

MODE = 'optimized' if sys.flags.optimize else 'normal'
OUT = HERE / MODE
resource.setrlimit(resource.RLIMIT_CPU, (110, 115))
signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(RuntimeError('115s fake-only deadline')))
signal.alarm(115)
original_mkdtemp = tempfile.mkdtemp
original_pump = c.Commands.pump

def owned_mkdtemp(*args, **kwargs):
    if Path(kwargs.get('dir', '.')) != CANDIDATE:
        raise RuntimeError('unexpected fake test scratch owner')
    kwargs['dir'] = OUT
    return original_mkdtemp(*args, **kwargs)

def pump(manager, seconds=.02):
    for child in fake.children.values():
        child.tick()
    return original_pump(manager, seconds)

with patch.object(c.subprocess, 'Popen', side_effect=fake.Child), \
        patch.object(c.os, 'killpg', side_effect=fake.group), \
        patch.object(c.Commands, 'pump', pump), \
        patch.object(c.subprocess, 'run', side_effect=RuntimeError('helper launch forbidden')), \
        patch.object(tempfile, 'mkdtemp', side_effect=owned_mkdtemp):
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(controls.Controls)
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)

receipt = {
    'status': 'passed' if result.wasSuccessful() else 'failed',
    'tests': result.testsRun, 'mode': MODE, 'python': sys.version,
    'failures': [(str(t), s) for t, s in result.failures],
    'errors': [(str(t), s) for t, s in result.errors],
    'command': [sys.executable, '-B', *(['-O'] if sys.flags.optimize else []), str(Path(__file__))],
    'controllerSHA256': controls.identity(CANDIDATE / 'run_native_probe.py')['sha256'],
    'lifecycleSHA256': controls.identity(CANDIDATE / 'cleanup_control.py')['sha256'],
    'controlsSHA256': controls.identity(CANDIDATE / 'host_controls.py')['sha256'],
    'fakeDriverSHA256': controls.identity(CANDIDATE / 'optimized_fake_controls.py')['sha256'],
    'elapsedSeconds': time.monotonic() - controls.START,
    'processMode': 'FAKE_ONLY_WITH_REAL_PIPES',
    'innerRealProcessLaunches': 0, 'innerRealGroupCalls': 0,
    'scratchRedirectionOnly': True,
    'commands': controls.Controls.all_records, 'cleanup': controls.Controls.cleanups,
}
(OUT / 'replay.json').write_text(json.dumps(receipt, indent=2) + '\n')
sys.exit(0 if result.wasSuccessful() else 1)
