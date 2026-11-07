"""Guard pure controls against process, session, signal, wait and socket access."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

DENIED = []


def install(root):
    root = Path(root).absolute()
    sys.dont_write_bytecode = True

    def blocked(*args, **kwargs):
        DENIED.append('process/session/group/signal/wait/socket entry')
        raise RuntimeError('Pure controls prohibit this operation')

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
                'os.exec', 'os.kill', 'os.killpg', 'os.startfile'}:
            DENIED.append(event)
            raise RuntimeError('Pure controls prohibit ' + event)
        targets = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                targets = [args[0]]
        elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
            targets = [args[0]]
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            targets = args[:2]
        for target in targets:
            candidate = Path(os.fsdecode(target))
            if candidate.is_absolute() and not candidate.is_relative_to(root):
                raise RuntimeError('Write outside owned candidate')

    sys.addaudithook(audit)
    for name in ['system', 'posix_spawn', 'posix_spawnp', 'fork', 'forkpty',
                 'setsid', 'setpgid', 'getsid', 'getpgid', 'getpgrp',
                 'kill', 'killpg', 'wait', 'waitpid', 'waitid', 'wait3', 'wait4']:
        if hasattr(os, name):
            setattr(os, name, blocked)
    for name in ['Popen', 'run', 'call', 'check_call', 'check_output']:
        setattr(subprocess, name, blocked)
    for name in ['signal', 'alarm', 'setitimer', 'pause', 'sigwait', 'sigwaitinfo',
                 'sigtimedwait', 'pthread_kill', 'pthread_sigmask', 'raise_signal',
                 'siginterrupt', 'getitimer', 'getsignal', 'sigpending']:
        if hasattr(signal, name):
            setattr(signal, name, blocked)
    socket.socket = blocked
    socket.create_connection = blocked
    time.sleep = blocked
