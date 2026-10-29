"""Install the source/data-only guard before loading packet implementation."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def denied(*args, **kwargs):
    raise AssertionError("lint source packet: live process/session/group/signal/wait/socket denied")


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
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.rename", "os.chmod"}:
            if not Path(os.fsdecode(args[0])).resolve().is_relative_to(HERE):
                denied()
            if event == "os.rename" and not Path(os.fsdecode(args[1])).resolve().is_relative_to(HERE):
                denied()

    sys.addaudithook(audit)
    # These imports occur only after the audit guard is active. Attribute guards
    # cover APIs whose CPython audit surface is incomplete (notably wait/session).
    import signal
    import socket
    import subprocess
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
