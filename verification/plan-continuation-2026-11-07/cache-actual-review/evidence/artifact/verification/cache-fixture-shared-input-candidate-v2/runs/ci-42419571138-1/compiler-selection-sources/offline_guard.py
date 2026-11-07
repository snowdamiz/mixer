"""Deny runtime operations and confine control writes before subject imports."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

DENIED = []


def install(root):
    root = root.resolve()
    sys.dont_write_bytecode = True

    def blocked(*args, **kwargs):
        DENIED.append('runtime-operation')
        raise RuntimeError('Pure controls forbid runtime operations')

    def audit(event, args):
        if event.startswith(('subprocess.', 'socket.')) or event in {
                'os.system', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty',
                'os.exec', 'os.kill', 'os.killpg', 'os.startfile'}:
            blocked()
        targets = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                targets = [args[0]]
        elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
            targets = [args[0]]
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            targets = args[:2]
        for target in targets:
            if not Path(os.fsdecode(target)).resolve(strict=False).is_relative_to(root):
                raise RuntimeError('Control write outside owned cache-fix directory')

    sys.addaudithook(audit)
    for module, names in [
        (os, 'system posix_spawn posix_spawnp fork forkpty setsid setpgid getsid getpgid getpgrp kill killpg wait waitpid waitid wait3 wait4 abort _exit execl execle execlp execlpe execv execve execvp execvpe spawnl spawnle spawnlp spawnlpe spawnv spawnve spawnvp spawnvpe pidfd_open openpty'),
        (subprocess, 'Popen run call check_call check_output getstatusoutput getoutput'),
        (signal, 'signal alarm setitimer pause sigwait sigwaitinfo sigtimedwait pthread_kill pthread_sigmask raise_signal siginterrupt getitimer getsignal sigpending pidfd_send_signal'),
        (socket, 'socket socketpair fromfd fromshare create_connection create_server getaddrinfo gethostbyname gethostbyname_ex gethostbyaddr'),
        (time, 'sleep clock_settime clock_settime_ns'),
    ]:
        for name in names.split():
            if hasattr(module, name):
                setattr(module, name, blocked)
