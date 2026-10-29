#!/usr/bin/env python3
"""One selected actual DATA audit; no product, compiler or artifact-code execution."""
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
import encodings.cp437
from types import SimpleNamespace

HERE = Path('/Users/andreyyurlov/Documents/dev/mixer/verification/rust-1991-actual-audit-preparation-v2')
OUT = HERE / 'local' / 'first-audit'
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
        if not target.resolve(strict=False).is_relative_to(OUT) or any(p.is_symlink() for p in [*target.parents, target]):
            outer_block()
    if event == 'os.mkdir':
        target = Path(os.fsdecode(args[0])).absolute()
        if args[2] not in (-1, None) or not target.resolve(strict=False).is_relative_to(OUT) or any(p.is_symlink() for p in [*target.parents, target]):
            outer_block()
    if event in {'os.remove', 'os.rmdir', 'os.rename', 'os.link', 'os.symlink', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate'}:
        outer_block()


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


assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.dont_write_bytecode == 1
assert hashlib.sha256((HERE / 'preparation-seal.json').read_bytes()).hexdigest() == '26051a74891b420c487b6262b865ab5ecf3160a3989a14cc34acf4c4dd439213'
assert hashlib.sha256((HERE / 'audit_actual.py').read_bytes()).hexdigest() == '6ab801562475b4cca7a5ca496b49758184b956caf1d868a79932fc8a4197dfd8'
assert hashlib.sha256((HERE / 'deny_runtime.py').read_bytes()).hexdigest() == '69873787132f3c8d8f29977c87101e5c3d0337ae8429104bb49f1658b102cb74'
sys.argv = [str(HERE / 'audit_actual.py'), '--root-binding', '/Users/andreyyurlov/Documents/dev/mixer/verification/rust-1991-first-actual-result/root-binding.json', '--root-binding-sha256', 'efc7afb2e4bd1809eb6491af2c5ae7ccd7518f885e1440fe7168b9597e26e1d1', '--preparation-seal-sha256', '26051a74891b420c487b6262b865ab5ecf3160a3989a14cc34acf4c4dd439213', '--artifact', '/Users/andreyyurlov/Documents/dev/mixer/verification/rust-1991-first-actual-result/local/artifact.zip', '--out', str(OUT)]
spec = importlib.util.spec_from_file_location('root_selected_actual_audit', HERE / 'audit_actual.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
exit_code = subject.main()
outer_result = {'schema': 1, 'scope': 'selected actual DATA audit only', 'outer_denied': OUTER_DENIED, 'inner_return': exit_code, 'python': {'executable': sys.executable, 'version': sys.version}, 'flags': {'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site, 'dont_write_bytecode': sys.flags.dont_write_bytecode}, 'cp437_preloaded': 'encodings.cp437' in sys.modules, 'compiler_or_product_execution': False, 'artifact_code_execution': False, 'retry_selected': False}
if OUT.exists():
    (OUT / 'outer-guard.json').write_text(json.dumps(outer_result, sort_keys=True, indent=2) + '\n')
print(json.dumps(outer_result, sort_keys=True))
sys.exit(exit_code if not OUTER_DENIED else 1)
