"""Guard for a future separately selected data audit; no subject imports here."""
import builtins
import ctypes
import _strptime
import _thread
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time

DENIED = []


def install(write_root):
    root = Path(write_root).resolve()
    sys.dont_write_bytecode = True

    def blocked(*args, **kwargs):
        DENIED.append('active-runtime-api')
        raise RuntimeError('DATA_ONLY audit forbids process, discovery, signal, timer, socket or FFI operations')

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.', 'multiprocessing.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
                'os.exec', 'os.kill', 'os.killpg', 'os.startfile', 'os.putenv', 'os.unsetenv'}:
            DENIED.append(event)
            raise RuntimeError('DATA_ONLY audit forbids ' + event)
        targets = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                targets = [(args[0], -1)]
        elif event == 'os.mkdir':
            targets = [(args[0], args[2] if len(args) > 2 else -1)]
        elif event in {'os.rmdir', 'os.remove', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate',
                       'os.rename', 'os.link', 'os.symlink'}:
            raise RuntimeError('DATA_ONLY audit refuses deletion, rename, link or metadata mutation')
        for value, directory_fd in targets:
            if directory_fd not in {-1, None}:
                raise RuntimeError('DATA_ONLY audit refuses descriptor-relative mutation')
            target = Path(os.fsdecode(value)).absolute()
            for part in [*reversed(target.parents), target]:
                if part.is_symlink():
                    raise RuntimeError('DATA_ONLY audit refuses mutation through a symlink')
            target = target.resolve(strict=False)
            if target == root or not target.is_relative_to(root):
                raise RuntimeError('Write outside owned audit directory')

    sys.addaudithook(audit)
    for name in dir(os):
        if (name.startswith(('exec', 'spawn')) or name in {
                'system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'setsid', 'setpgid',
                'getsid', 'getpgid', 'getpgrp', 'getpid', 'getppid', 'kill', 'killpg', 'wait',
                'waitpid', 'waitid', 'wait3', 'wait4', 'pidfd_open', 'openpty', 'login_tty',
                'pipe', 'pipe2', 'popen', 'startfile', 'getloadavg', 'sched_getaffinity',
                'sched_setaffinity', 'register_at_fork'}):
            setattr(os, name, blocked)
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput', '_fork_exec'):
        if hasattr(subprocess, name):
            setattr(subprocess, name, blocked)
    for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo', 'sigtimedwait',
                 'pthread_kill', 'pthread_sigmask', 'raise_signal', 'siginterrupt', 'getitimer',
                 'getsignal', 'sigpending', 'set_wakeup_fd', 'pidfd_send_signal', 'valid_signals'):
        if hasattr(signal, name):
            setattr(signal, name, blocked)
    for name in ('socket', 'socketpair', 'fromfd', 'fromshare', 'create_connection', 'create_server',
                 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr', 'getnameinfo',
                 'gethostname', 'setdefaulttimeout'):
        if hasattr(socket, name):
            setattr(socket, name, blocked)
    time.sleep = blocked
    for module in (_thread, threading):
        for name in ('start_new_thread', 'start_new', 'start_joinable_thread', '_start_new_thread', '_start_joinable_thread'):
            if hasattr(module, name):
                setattr(module, name, blocked)
    threading.Thread.start = blocked
    threading.Timer.start = blocked
    for name in ('CDLL', 'PyDLL', 'WinDLL', 'OleDLL', 'CFUNCTYPE', 'PYFUNCTYPE', 'WINFUNCTYPE',
                 'cdll', 'pydll', 'windll', 'oledll', 'pythonapi', 'cast', 'memmove', 'memset',
                 'string_at', 'wstring_at', 'memoryview_at', 'get_errno', 'set_errno'):
        if hasattr(ctypes, name):
            setattr(ctypes, name, blocked)
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split('.')[0] in {'_ctypes', 'ctypes', 'multiprocessing', 'pty', '_posixsubprocess',
                                  'psutil', 'resource', 'concurrent', 'asyncio', 'threading', '_thread'}:
            blocked()
        return original_import(name, *args, **kwargs)

    builtins.__import__ = guarded_import
