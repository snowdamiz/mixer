"""Review-required v3 owned-fixture derivative of pinned deny_runtime.py.

Known-source DATA_ONLY only, not a sandbox for arbitrary hostile Python.
Added authority: owned fixture symlink/FIFO creation and unlink/rmdir; one-use
read-only descriptor wrapping for ordinary fixture or selected packet files.
All process/network/signal/thread/FFI prohibitions are inherited unchanged.
"""
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
import stat
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
DENIED_COUNT = 0
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND


def blocked(*args, **kwargs):
    global DENIED_COUNT
    DENIED_COUNT += 1
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


def install(write_root, packet_root):
    root,packet = Path(write_root),Path(packet_root)
    if (not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir()
            or not packet.is_absolute() or packet.resolve(strict=True) != packet or not packet.is_dir()
            or root.is_relative_to(packet) or packet.is_relative_to(root)):
        raise RuntimeError("Separate canonical owned fixture root and packet required")
    with os.scandir(root) as entries:
        if next(entries,None) is not None:
            raise RuntimeError("New empty owned fixture root required")
    original_io_open,original_os_open,original_close = io.open,posix.open,posix.close
    original_mkfifo,original_symlink = posix.mkfifo,posix.symlink
    original_remove,original_rmdir = posix.unlink,posix.rmdir
    descriptors = {}
    wrapping = None

    def status(value):
        return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

    def fixture_leaf(value):
        if isinstance(value,int) or not isinstance(value,(str,bytes,os.PathLike)):
            blocked()
        path = Path(os.fsdecode(value)).absolute()
        if ".." in path.parts or path == root or not path.is_relative_to(root):
            blocked()
        if path.parent.resolve(strict=True) != path.parent:
            blocked()
        return path

    def descriptor_path(value):
        if isinstance(value,int) or not isinstance(value,(str,bytes,os.PathLike)):
            blocked()
        path = Path(os.fsdecode(value)).absolute()
        if ".." in path.parts or not (path.is_relative_to(root) or path.is_relative_to(packet)):
            blocked()
        if path.resolve(strict=True) != path or not stat.S_ISREG(path.lstat().st_mode):
            blocked()
        return path

    def fixture_symlink(source,destination,*args,**kwargs):
        if args or set(kwargs)-{'target_is_directory'}:
            blocked()
        destination = fixture_leaf(destination)
        write_path(destination,root)
        if not isinstance(source,(str,bytes,os.PathLike)):
            blocked()
        source_path = Path(os.fsdecode(source))
        target = source_path if source_path.is_absolute() else destination.parent/source_path
        fixture_leaf(target)
        if target.is_symlink():
            blocked()
        return original_symlink(source,destination,**kwargs)

    def fixture_mkfifo(path,mode=0o600,**kwargs):
        if kwargs or mode != 0o600:
            blocked()
        path = fixture_leaf(path); write_path(path,root)
        return original_mkfifo(path,mode)

    def fixture_remove(path,*args,**kwargs):
        if args or kwargs:
            blocked()
        return original_remove(fixture_leaf(path))

    def fixture_rmdir(path,*args,**kwargs):
        if args or kwargs:
            blocked()
        return original_rmdir(fixture_leaf(path))

    def descriptor_open(path,flags,*args,**kwargs):
        if args or kwargs or flags != os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK:
            blocked()
        path = descriptor_path(path)
        descriptor = original_os_open(path,flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            original_close(descriptor); blocked()
        descriptors[descriptor] = status(opened)
        return descriptor

    def read_fdopen(descriptor,mode='r',*args,**kwargs):
        nonlocal wrapping
        if (type(descriptor) is not int or mode != 'rb' or args or kwargs
                or descriptor not in descriptors or wrapping is not None
                or status(os.fstat(descriptor)) != descriptors[descriptor]):
            blocked()
        wrapping = descriptor
        try:
            return original_io_open(descriptor,'rb')
        finally:
            wrapping = None
            descriptors.pop(descriptor,None)

    def close_descriptor(descriptor):
        if type(descriptor) is not int or descriptor not in descriptors:
            blocked()
        descriptors.pop(descriptor,None)
        return original_close(descriptor)
    sys.dont_write_bytecode = True

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.', 'ctypes.', 'pty.', 'multiprocessing.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty', 'os.exec',
                'os.kill', 'os.killpg', 'os.startfile', 'os.putenv', 'os.unsetenv'}:
            blocked()
        if event == 'open':
            if isinstance(args[0], int):
                if args[0] != wrapping or args[2] & WRITE_FLAGS:
                    blocked()
                return
            if args[2] & WRITE_FLAGS:
                write_path(args[0], root)
        elif event == 'os.mkdir':
            if len(args) > 2 and args[2] not in {-1, None}:
                blocked()
            write_path(args[0], root)
        elif event in {'os.rmdir','os.remove'}:
            if len(args) > 1 and args[1] not in {-1,None}:
                blocked()
            fixture_leaf(args[0])
        elif event == 'os.symlink':
            if len(args) > 2 and args[2] not in {-1,None}:
                blocked()
            destination = fixture_leaf(args[1]); write_path(destination,root)
            source = Path(os.fsdecode(args[0]))
            target = source if source.is_absolute() else destination.parent/source
            fixture_leaf(target)
            if target.is_symlink(): blocked()
        elif event in {'os.chmod', 'os.chown', 'os.utime', 'os.truncate','os.rename', 'os.link'}:
            blocked()

    sys.addaudithook(audit)
    # Capture original file operations before patching their public/C aliases.
    for module in (builtins, io, _io):
        module.open = file_open_wrapper(module.open, root)
    original_open = posix.open
    os.open = posix.open = descriptor_open
    os.close = posix.close = close_descriptor
    os.symlink = posix.symlink = fixture_symlink
    os.mkfifo = posix.mkfifo = fixture_mkfifo
    os.unlink = os.remove = posix.unlink = posix.remove = fixture_remove
    os.rmdir = posix.rmdir = fixture_rmdir
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

    os.fdopen = read_fdopen
    sys._mixer_pair7_fixture_guard = True
