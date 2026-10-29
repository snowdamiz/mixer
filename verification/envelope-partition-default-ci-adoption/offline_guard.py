"""Deny real process/session/group/signal/wait/socket operations before subjects load."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

DENIED = []


def install(write_root):
    root = Path(write_root).resolve()
    sys.dont_write_bytecode = True
    owned_directories = {}

    def blocked(*args, **kwargs):
        DENIED.append('process/session/group/signal/wait/socket')
        raise RuntimeError('Independent source-only controls forbid runtime operations')

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
                'os.exec', 'os.kill', 'os.killpg', 'os.startfile'}:
            DENIED.append(event)
            raise RuntimeError('Independent source-only controls forbid ' + event)
        targets = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                targets = [(args[0], -1)]
        elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
            index = 2 if event in {'os.mkdir', 'os.chmod'} else 1
            targets = [(args[0], args[index] if len(args) > index else -1)]
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            targets = [(value, -1) for value in args[:2]]
        for value, directory_fd in targets:
            target = Path(os.fsdecode(value))
            if not target.is_absolute() and directory_fd is not None and directory_fd >= 0:
                # shutil uses fd-relative unlink/rmdir. Locate that directory by
                # filesystem identity inside this owned root; never inspect processes.
                identity = os.fstat(directory_fd)
                key = (identity.st_dev, identity.st_ino)
                parent = owned_directories.get(key)
                if parent is None or not parent.is_dir() or (parent.stat().st_dev, parent.stat().st_ino) != key:
                    for p in [root, *root.rglob('*')]:
                        if p.is_dir() and not p.is_symlink():
                            observed = p.stat(); owned_directories[(observed.st_dev, observed.st_ino)] = p
                    parent = owned_directories.get(key)
                if parent is None: raise RuntimeError('Unowned directory descriptor mutation')
                target = parent / target
            target = target.absolute()
            if not target.resolve(strict=False).is_relative_to(root):
                raise RuntimeError('Write outside independent review: ' + str(target))

    sys.addaudithook(audit)
    for name in ('system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty',
                 'setsid', 'setpgid', 'getsid', 'getpgid', 'getpgrp', 'kill', 'killpg',
                 'wait', 'waitpid', 'waitid', 'wait3', 'wait4'):
        if hasattr(os, name): setattr(os, name, blocked)
    for name in ('Popen', 'run', 'call', 'check_call', 'check_output'):
        setattr(subprocess, name, blocked)
    for name in ('signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
                 'sigtimedwait', 'pthread_kill', 'pthread_sigmask', 'raise_signal',
                 'siginterrupt', 'getitimer', 'getsignal', 'sigpending'):
        if hasattr(signal, name): setattr(signal, name, blocked)
    socket.socket = blocked
    socket.create_connection = blocked
    time.sleep = blocked
