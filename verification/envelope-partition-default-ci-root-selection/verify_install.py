#!/usr/bin/env python3
"""Guarded exact source and installed adapter verification."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time

DENIED = []
def deny(name):
    def blocked(*args, **kwargs):
        DENIED.append(name)
        raise RuntimeError('Forbidden source-check operation: ' + name)
    return blocked
for module, names in [
    (subprocess, ['Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput']),
    (os, ['fork', 'forkpty', 'posix_spawn', 'posix_spawnp', 'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'spawnv', 'spawnve', 'spawnvp', 'spawnvpe', 'system', 'popen', 'execl', 'execle', 'execlp', 'execlpe', 'execv', 'execve', 'execvp', 'execvpe', '_exit', 'kill', 'killpg', 'getpid', 'getppid', 'getpgid', 'getpgrp', 'getsid', 'setsid', 'setpgid', 'wait', 'waitpid', 'waitid', 'wait3', 'wait4']),
    (signal, ['signal', 'alarm', 'setitimer', 'pause', 'raise_signal', 'pthread_kill', 'sigwait', 'sigwaitinfo', 'sigtimedwait']),
    (socket, ['socket', 'socketpair', 'create_connection', 'create_server', 'getaddrinfo']),
    (time, ['sleep']),
    (threading.Thread, ['start']),
    (threading.Event, ['wait']),
]:
    for name in names:
        if hasattr(module, name):
            setattr(module, name, deny(getattr(module, '__name__', str(module)) + '.' + name))

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ADOPTION = ROOT / 'verification/envelope-partition-default-ci-adoption'
mode = sys.argv[1] if len(sys.argv) > 1 else 'candidate'
assert mode in {'candidate', 'installed'}
current = (ROOT / '.github/workflows/verify.yml').read_text()
changes = json.loads((ADOPTION / 'workflow/changes.json').read_text())['changes']
if mode == 'candidate':
    before, candidate = current, current
    for change in changes:
        assert candidate.count(change['before']) == 1
        candidate = candidate.replace(change['before'], change['after'], 1)
else:
    before, candidate = current, current
    for change in reversed(changes):
        assert before.count(change['after']) == 1
        before = before.replace(change['after'], change['before'], 1)
assert hashlib.sha256(before.encode()).hexdigest() == '1240d486c1591611599ef4f9a3357d607e4aa5ccaea67b017cfb50248bfe1866'
assert hashlib.sha256(candidate.encode()).hexdigest() == 'a90bab7dea218e5a098e45eb370e9b666afdf0bda9100cb35ec14dfc779de024'
spec = importlib.util.spec_from_file_location('guarded_envelope_adoption_root', ADOPTION / 'adopt_envelope.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.job_text(candidate) == (ADOPTION / 'workflow/swift-job.yml').read_text()
assert before.replace(module.job_text(before), '', 1) == candidate.replace(module.job_text(candidate), '', 1)
assert '        timeout-minutes: 12\n' in module.job_text(candidate)
assert '          export RUSTUP_AUTO_INSTALL=0\n' in module.job_text(candidate)
runner, base, policy_proof = module.load_runner()
for name in module.POLICY_FUNCTIONS:
    assert getattr(runner, name) is getattr(base, name)
    assert getattr(runner, name).__globals__ is base.__dict__
proof = module.verify(installed=mode == 'installed')
if mode == 'installed':
    assert (ROOT / '.github/workflows/verify.yml').read_text() == candidate
else:
    assert (ROOT / '.github/workflows/verify.yml').read_text() == before
assert not DENIED
result = {'schema': 1, 'mode': mode, 'passed': True, 'python': sys.version,
          'yamlParser': 'unavailable; no parser or actionlint acceptance claimed',
          'exactCompilerFunctionsAndOriginalGlobals': True,
          'sourceOnly': True, 'subjectRuntimeCommands': 0, 'deniedCalls': DENIED,
          'workflowSHA256': hashlib.sha256(candidate.encode()).hexdigest(),
          'allUnrelatedJobsUnchanged': True, 'adapterProof': proof,
          'limitations': ['Exact workflow spans and job identity checked; YAML parser unavailable; actionlint and shell runtime were not executed.', 'Actual ordinary-host execution remains pending.']}
(HERE / ('checks-' + mode + '.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps(result, sort_keys=True))
