"""Known-source DATA_ONLY guard; not a sandbox for arbitrary hostile Python."""
import builtins
import ctypes
import _ctypes
import _strptime
import _thread
import io
import _io
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

DENIED = []
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def blocked(*args, **kwargs):
    if len(DENIED) < 8:
        DENIED.append('active-api-or-unselected-write')
    raise RuntimeError('Known-source DATA_ONLY guard refuses active API or unselected write')


def write_path(value, root):
    if isinstance(value, int) or not isinstance(value, (str, bytes, os.PathLike)):
        blocked()
    target = Path(os.fsdecode(value)).absolute()
    for part in [*reversed(target.parents), target]:
        if part.is_symlink():
            blocked()
    target = target.resolve(strict=False)
    if target == root or not target.is_relative_to(root):
        blocked()


def file_open_wrapper(original, root):
    def guarded(file, *args, **kwargs):
        if isinstance(file, int) or 'dir_fd' in kwargs or kwargs.get('opener') is not None:
            blocked()
        if len(args) > 6 and args[6] is not None:
            blocked()  # positional opener callback
        mode = kwargs.get('mode', args[0] if args else 'r')
        if type(mode) is not str:
            blocked()
        if any(flag in mode for flag in 'wax+'):
            write_path(file, root)
        return original(file, *args, **kwargs)
    return guarded


def os_open_wrapper(original, root):
    def guarded(path, flags, *args, **kwargs):
        if isinstance(path, int) or type(flags) is not int or len(args) > 1 or set(kwargs) - {'mode'}:
            blocked()  # all dir_fd forms and unknown open keywords are refused
        if flags & WRITE_FLAGS:
            write_path(path, root)
        return original(path, flags, *args, **kwargs)
    return guarded


def mkdir_wrapper(original):
    def guarded(path, *args, **kwargs):
        if len(args) > 1 or set(kwargs) - {'mode'}:
            blocked()
        return original(path, *args, **kwargs)
    return guarded


def install(write_root):
    root = Path(write_root).resolve()
    sys.dont_write_bytecode = True

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.', 'multiprocessing.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty', 'os.exec',
                'os.kill', 'os.killpg', 'os.startfile', 'os.putenv', 'os.unsetenv'}:
            blocked()
        if event == 'open':
            if isinstance(args[0], int):
                blocked()
            if args[2] & WRITE_FLAGS:
                write_path(args[0], root)
        elif event == 'os.mkdir':
            if len(args) > 2 and args[2] not in {-1, None}:
                blocked()
            write_path(args[0], root)
        elif event in {'os.rmdir', 'os.remove', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate',
                       'os.rename', 'os.link', 'os.symlink'}:
            blocked()

    sys.addaudithook(audit)
    # Capture original file operations before patching their public/C aliases.
    for module in (builtins, io, _io):
        module.open = file_open_wrapper(module.open, root)
    original_open = posix.open
    os.open = posix.open = os_open_wrapper(original_open, root)
    original_mkdir = posix.mkdir
    os.mkdir = posix.mkdir = mkdir_wrapper(original_mkdir)
    for module in (io, _io):
        module.FileIO = blocked
    for module in (os, posix):
        for name in dir(module):
            if name.startswith(('exec', 'spawn')) or name in {
                    'system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty', 'setsid', 'setpgid',
                    'getsid', 'getpgid', 'getpgrp', 'getpid', 'getppid', 'kill', 'killpg', 'wait', 'waitpid',
                    'waitid', 'wait3', 'wait4', 'pidfd_open', 'openpty', 'login_tty', 'pipe', 'pipe2',
                    'popen', 'startfile', 'getloadavg', 'sched_getaffinity', 'sched_setaffinity',
                    'register_at_fork', 'fdopen', 'write', 'writev', 'pwrite', 'pwritev', 'ftruncate',
                    'fchmod', 'fchown', 'sendfile', 'copy_file_range', 'dup', 'dup2'}:
                setattr(module, name, blocked)
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output', 'getoutput', 'getstatusoutput', '_fork_exec'):
        if hasattr(subprocess, name):
            setattr(subprocess, name, blocked)
    _posixsubprocess.fork_exec = blocked
    for module in (signal, _signal):
        for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo', 'sigtimedwait',
                     'pthread_kill', 'pthread_sigmask', 'raise_signal', 'siginterrupt', 'getitimer',
                     'getsignal', 'sigpending', 'set_wakeup_fd', 'pidfd_send_signal', 'valid_signals'):
            if hasattr(module, name):
                setattr(module, name, blocked)
    for module in (socket, _socket):
        for name in ('socket', 'SocketType', 'socketpair', 'fromfd', 'fromshare', 'create_connection',
                     'create_server', 'getaddrinfo', 'gethostbyname', 'gethostbyname_ex', 'gethostbyaddr',
                     'getnameinfo', 'gethostname', 'setdefaulttimeout'):
            if hasattr(module, name):
                setattr(module, name, blocked)
    time.sleep = blocked
    for module in (_thread, threading):
        for name in ('start_new_thread', 'start_new', 'start_joinable_thread', '_start_new_thread', '_start_joinable_thread'):
            if hasattr(module, name):
                setattr(module, name, blocked)
    threading.Thread.start = threading.Timer.start = blocked
    for module in (ctypes, _ctypes):
        for name in ('CDLL', 'PyDLL', 'WinDLL', 'OleDLL', 'CFUNCTYPE', 'PYFUNCTYPE', 'WINFUNCTYPE',
                     'cdll', 'pydll', 'windll', 'oledll', 'pythonapi', 'cast', 'memmove', 'memset',
                     'string_at', 'wstring_at', 'memoryview_at', 'get_errno', 'set_errno', 'dlopen',
                     'dlsym', 'call_function', 'call_cdeclfunction', 'PyObj_FromPtr'):
            if hasattr(module, name):
                setattr(module, name, blocked)
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.split('.')[0] in {'posix', 'nt', '_signal', '_socket', '_posixsubprocess', '_ctypes',
                                  'ctypes', 'multiprocessing', 'pty', 'psutil', 'resource', 'concurrent',
                                  'asyncio', 'threading', '_thread'}:
            blocked()
        return original_import(name, *args, **kwargs)

    builtins.__import__ = guarded_import
