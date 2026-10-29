"""Source-review controls: deny live effects before subject imports."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ATTEMPTS = []


def denied(*args, **kwargs):
    ATTEMPTS.append("denied-live-api")
    raise AssertionError("independent admission: live API denied")


def install():
    sys.dont_write_bytecode = True

    def audit(event, args):
        if event.startswith(("subprocess.", "socket.", "pty.", "ctypes.")) or event in {
            "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec",
            "os.kill", "os.killpg", "os.chdir",
        }:
            denied()
        if event == "open":
            name, mode, flags = args
            writing = isinstance(mode, str) and any(c in mode for c in "wax+")
            writing |= isinstance(flags, int) and bool(flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ))
            if writing and (not isinstance(name, (str, bytes, os.PathLike)) or
                            not Path(os.fsdecode(name)).resolve().is_relative_to(HERE)):
                denied()
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.chmod", "os.symlink", "os.link"}:
            targets = args[:2] if event in {"os.rename", "os.link"} else args[:1]
            if event == "os.symlink":
                targets = args[1:2]
            for target in targets:
                if not Path(os.fsdecode(target)).resolve().is_relative_to(HERE):
                    denied()

    sys.addaudithook(audit)
    import signal
    import socket
    import subprocess
    import resource
    import threading
    import _thread
    import time
    subprocess.Popen = subprocess.run = subprocess.call = denied
    subprocess.check_call = subprocess.check_output = denied
    socket.socket = socket.create_connection = socket.socketpair = denied
    for name in dir(os):
        if name.startswith(("exec", "spawn", "posix_spawn")) or name in {
            "system", "fork", "forkpty", "kill", "killpg", "wait", "waitpid",
            "wait3", "wait4", "waitid", "popen", "setsid", "setpgid", "getpgid", "getsid",
        }:
            setattr(os, name, denied)
    for name in ("signal", "setitimer", "alarm", "getsignal", "raise_signal", "pthread_kill", "sigwait", "sigwaitinfo", "sigtimedwait"):
        if hasattr(signal, name):
            setattr(signal, name, denied)
    resource.getrusage = denied
    threading.Thread.start = _thread.start_new_thread = time.sleep = denied
