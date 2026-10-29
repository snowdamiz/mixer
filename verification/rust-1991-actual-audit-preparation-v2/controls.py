#!/usr/bin/env python3
"""Small inert controls; separate outer deny guard precedes both subject imports."""
import builtins
import ctypes
import _ctypes
import _thread
import _strptime
import importlib.util
import io
import os
import posix
from pathlib import Path
import signal
import _signal
import socket
import _socket
import subprocess
import _posixsubprocess
import sys
import threading
import time
import hashlib
import json
import struct
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
OUTER_DENIED = []


def outer_block(*args, **kwargs):
    if len(OUTER_DENIED) < 8:
        OUTER_DENIED.append('active-api')
    raise RuntimeError('Outer inert-control guard blocks active APIs')


def outer_audit(event, args):
    if event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.')) or event in {
            'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty', 'os.exec',
            'os.kill', 'os.killpg', 'os.putenv', 'os.unsetenv', 'os.startfile'}:
        outer_block()
    if event == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
        if isinstance(args[0], int):
            outer_block()
        target = Path(os.fsdecode(args[0])).absolute()
        if not target.resolve(strict=False).is_relative_to(HERE / 'local') or any(p.is_symlink() for p in [*target.parents, target]):
            outer_block()
    if event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.rename', 'os.link', 'os.symlink', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate'}:
        outer_block()  # fixtures are in memory; the pre-created local evidence directory suffices


sys.dont_write_bytecode = True
sys.addaudithook(outer_audit)
for module in (os, posix):
    for name in dir(module):
        if name.startswith(('exec', 'spawn')) or name in {
                'system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'setsid', 'setpgid',
                'getsid', 'getpgid', 'getpgrp', 'getpid', 'getppid', 'kill', 'killpg', 'wait', 'waitpid',
                'waitid', 'wait3', 'wait4', 'pidfd_open', 'openpty', 'login_tty', 'pipe', 'pipe2', 'popen',
                'getloadavg', 'sched_getaffinity', 'sched_setaffinity', 'register_at_fork', 'fdopen',
                'open', 'write', 'writev', 'pwrite', 'pwritev', 'ftruncate', 'fchmod', 'fchown',
                'sendfile', 'copy_file_range', 'dup', 'dup2'}:
            setattr(module, name, outer_block)
for name in ('Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput', '_fork_exec'):
    if hasattr(subprocess, name):
        setattr(subprocess, name, outer_block)
_posixsubprocess.fork_exec = outer_block
for module in (signal, _signal):
    for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo', 'sigtimedwait',
                 'pthread_kill', 'pthread_sigmask', 'raise_signal', 'siginterrupt', 'getitimer', 'getsignal',
                 'sigpending', 'set_wakeup_fd', 'pidfd_send_signal', 'valid_signals'):
        if hasattr(module, name):
            setattr(module, name, outer_block)
for module in (socket, _socket):
    for name in ('socket', 'SocketType', 'socketpair', 'fromfd', 'create_connection', 'create_server',
                 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr', 'getnameinfo', 'gethostname'):
        if hasattr(module, name):
            setattr(module, name, outer_block)
for module in (ctypes, _ctypes):
    for name in ('CDLL', 'PyDLL', 'CFUNCTYPE', 'PYFUNCTYPE', 'cdll', 'pydll', 'pythonapi', 'cast',
                 'memmove', 'memset', 'string_at', 'wstring_at', 'memoryview_at', 'dlopen', 'dlsym',
                 'call_function', 'call_cdeclfunction', 'PyObj_FromPtr'):
        if hasattr(module, name):
            setattr(module, name, outer_block)
for module in (_thread, threading):
    for name in ('start_new_thread', 'start_new', 'start_joinable_thread', '_start_new_thread', '_start_joinable_thread'):
        if hasattr(module, name):
            setattr(module, name, outer_block)
threading.Thread.start = threading.Timer.start = outer_block
time.sleep = outer_block


def subject(name):
    path = HERE / (name + '.py')
    spec = importlib.util.spec_from_file_location('inert_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


before = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
          for name in ('audit_actual.py', 'deny_runtime.py', 'controls.py')}
a = subject('audit_actual')
g = subject('deny_runtime')
results = []


def expect_reject(action):
    try:
        action()
    except (RuntimeError, ValueError):
        return
    raise AssertionError('Expected inert refusal')


def check(value):
    if not value:
        raise AssertionError('Control assertion failed')


def run(name, action, limits=None):
    saved = dict(a.JSON_LIMITS)
    a.JSON_USED.update(raw_bytes=0, nodes=0, keys=0)
    a.CHECKS.update(total=0, passed=0, failed=0, failure_labels=[])
    if limits:
        a.JSON_LIMITS.update(limits)
    try:
        action()
        results.append({'name': name, 'passed': True})
    except BaseException as error:
        results.append({'name': name, 'passed': False, 'error': type(error).__name__ + ': ' + str(error)[:256]})
    finally:
        a.JSON_LIMITS.clear()
        a.JSON_LIMITS.update(saved)


run('json-small-valid', lambda: check(a.strict(b'{"a":[1,true,null]}') == {'a': [1, True, None]}))
run('json-duplicate-key', lambda: expect_reject(lambda: a.strict(b'{"a":1,"a":2}')))
run('json-depth-before-decode', lambda: expect_reject(lambda: a.strict(b'[' * 33 + b'0' + b']' * 33)))
run('json-node-limit', lambda: expect_reject(lambda: a.strict(b'[0,0,0,0]')), {'nodes': 6})
run('json-key-limit', lambda: expect_reject(lambda: a.strict(b'{"a":1,"b":2}')), {'keys': 1})
run('json-raw-limit', lambda: expect_reject(lambda: a.strict(b'[0,0,0]')), {'raw_bytes': 6})
run('json-string-limit', lambda: expect_reject(lambda: a.strict(b'"abcd"')), {'string_chars': 3})
run('json-aggregate-bytes', lambda: (a.strict(b'null'), a.strict(b'null'), expect_reject(lambda: a.strict(b'null'))), {'aggregate_raw_bytes': 10})
run('json-aggregate-nodes', lambda: (a.strict(b'[0]'), expect_reject(lambda: a.strict(b'[0]'))), {'aggregate_nodes': 5})
run('bounded-report', lambda: expect_reject(lambda: a.report_bytes({'x': 'a' * 100})), {'report_bytes': 64})


def ledger_control():
    for _ in range(10000):
        a.need(True, 'inert-check')
    for _ in range(12):
        expect_reject(lambda: a.need(False, 'inert-refusal'))
    check(a.CHECKS['total'] == 10012 and len(a.CHECKS['failure_labels']) == 8 and set(a.CHECKS) == {'total', 'passed', 'failed', 'failure_labels'})


run('constant-shape-check-ledger', ledger_control)


def zip_input(original='safe/path', effective=None, local=None, central_extra=b'', local_extra=b''):
    local_name = (original if local is None else local).encode('utf-8')
    header = struct.pack('<4s5H3I2H', b'PK\x03\x04', 20, 0x800, 0, 0, 0, 0, 0, 0, len(local_name), len(local_extra))
    info = SimpleNamespace(orig_filename=original, filename=original if effective is None else effective,
                           extra=central_extra, header_offset=0, flag_bits=0x800, compress_type=0)
    return info, header + local_name + local_extra


run('zip-matching-original-local', lambda: check(a.zip_member_name(*zip_input()) == ('safe/path', False)))
run('zip-nul-sanitization', lambda: expect_reject(lambda: a.zip_member_name(*zip_input('safe/path\x00suffix', effective='safe/path'))))
run('zip-original-nul-equal', lambda: expect_reject(lambda: a.zip_member_name(*zip_input('safe/path\x00suffix'))))
run('zip-central-unicode-override', lambda: expect_reject(lambda: a.zip_member_name(*zip_input(central_extra=struct.pack('<HH', 0x7075, 0)))))
run('zip-local-name-mismatch', lambda: expect_reject(lambda: a.zip_member_name(*zip_input(local='other/path'))))
run('zip-local-unicode-override', lambda: expect_reject(lambda: a.zip_member_name(*zip_input(local_extra=struct.pack('<HH', 0x7075, 0)))))


def early_control():
    retention = {'test_files': {str(n): {'path': 'retained/' + str(n)} for n in range(92)}, 'compiler_products': {}}
    files = {'_temp/analyzer-envelope/retained/' + str(n) for n in range(92)} | {'fixed'}
    expect_reject(lambda: a.early_archive_closure(files | {'unexpected.json'}, set(), {'fixed'}, retention))


run('unknown-file-early-closure', early_control)
calls = []
fake = lambda *args, **kwargs: calls.append((args, kwargs)) or 'fake-only'
run('fake-os-open-dir-fd-refusal', lambda: expect_reject(lambda: g.os_open_wrapper(fake, HERE)(str(HERE / 'local/unused'), os.O_WRONLY, dir_fd=7)))
run('fake-file-open-opener-refusal', lambda: expect_reject(lambda: g.file_open_wrapper(fake, HERE)(str(HERE / 'local/unused'), 'w', opener=fake)))
run('fake-file-open-descriptor-refusal', lambda: expect_reject(lambda: g.file_open_wrapper(fake, HERE)(7, 'w')))
run('fake-open-delegate-only', lambda: check(g.file_open_wrapper(fake, HERE)(str(HERE / 'local/unused'), 'w') == 'fake-only'))
check(len(calls) == 1)  # the only delegate is this explicitly inert lambda

selected = {'run_id': 1001, 'artifact': {'id': 2001, 'bytes': 12, 'sha256': 'a' * 64}}
acquisition = {'schema': 1, 'run_id': 1001, 'attempt': 1, 'artifact_id': 2001, 'bytes': 12,
    'sha256': 'a' * 64, 'bounded_consumer_invocations': 1, 'body_completed': True, 'reader_released': True,
    'attempt_budget': {'selected': 1, 'consumed': 1, 'remaining': 0}, 'independent_transport_eof_proven': False,
    'lease_invalidation_proven': False, 'provider_disposal_proven': False}
run('acquisition-record-valid', lambda: check(a.acquisition_record(acquisition, selected) == acquisition))
run('acquisition-incomplete-body', lambda: expect_reject(lambda: a.acquisition_record({**acquisition, 'body_completed': False}, selected)))
run('acquisition-unconsumed-attempt', lambda: expect_reject(lambda: a.acquisition_record({**acquisition, 'attempt_budget': {'selected': 1, 'consumed': 0, 'remaining': 1}}, selected)))
run('acquisition-unproven-disposal', lambda: expect_reject(lambda: a.acquisition_record({**acquisition, 'provider_disposal_proven': True}, selected)))


def alias_metadata_control():
    g.install(HERE / 'local')
    check(posix.getpid is g.blocked and posix.waitpid is g.blocked and _signal.signal is g.blocked
          and _signal.setitimer is g.blocked and _socket.socket is g.blocked
          and _posixsubprocess.fork_exec is g.blocked and _ctypes.dlopen is g.blocked
          and os.open is posix.open)


run('installed-alias-metadata-only', alias_metadata_control)
after = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in before}
result = {'schema': 1, 'scope': 'Inert parser/ZIP-name/acquisition/fake-open controls only; no actual archive/main/product/compiler/33-suite execution',
    'tests': len(results), 'passed': all(row['passed'] for row in results), 'results': results,
    'outer_guard_precedes_subject_imports': True, 'outer_denied': OUTER_DENIED,
    'new_guard_refusals_are_fake_wrapper_controls': list(g.DENIED), 'active_api_calls': 0,
    'descriptor_write_or_process_signal_socket_probes': 0, 'fake_open_delegate_calls': len(calls),
    'source_before': before, 'source_after': after, 'source_unchanged': before == after,
    'scratch_cleanup': {'fixtures_in_memory_only': True, 'control_scratch_absent': not (HERE / 'local/control-scratch').exists(),
                        'unused_fake_output_absent': not (HERE / 'local/unused').exists()},
    'python': {'executable': sys.executable, 'version': sys.version}}
(HERE / 'local/control-result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps({'tests': result['tests'], 'passed': result['passed'], 'outer_denied': OUTER_DENIED,
                  'source_unchanged': before == after, 'scratch_cleanup': result['scratch_cleanup']}, sort_keys=True))
sys.exit(0 if result['passed'] and not OUTER_DENIED and before == after else 1)
