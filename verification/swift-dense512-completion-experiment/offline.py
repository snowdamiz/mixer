"""Install process/network/custody and out-of-lane write guards for pure checks."""
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
READS = set()
START = time.monotonic()


def denied(*args, **kwargs):
    raise AssertionError("offline process/socket/signal/wait forbidden")


def install():
    sys.dont_write_bytecode = True
    def audit(event, args):
        if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
            "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec",
            "os.kill", "os.killpg", "os.chdir",
        }:
            denied()
        if event == "open":
            name, mode, flags = args
            writing = isinstance(mode, str) and any(c in mode for c in "wax+")
            writing |= isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
            if isinstance(name, (str, bytes, os.PathLike)):
                path = Path(os.fsdecode(name)).resolve()
                if writing and not path.is_relative_to(HERE):
                    raise AssertionError("write outside owned experiment lane")
                if not writing and path.is_relative_to(ROOT) and not path.is_relative_to(HERE):
                    READS.add(path)
            elif writing:
                denied()
        if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.rename"}:
            name = Path(os.fsdecode(args[0]))
            # shutil's fd-relative cleanup is restricted to a single basename;
            # its parent descriptors come from the audited lane-only temp roots.
            relative_cleanup = event in {"os.remove", "os.rmdir"} and len(args) > 1 and isinstance(args[1], int) and args[1] >= 0 and len(name.parts) == 1
            if not relative_cleanup and not name.resolve().is_relative_to(HERE):
                raise AssertionError("filesystem mutation outside owned experiment lane")
    sys.addaudithook(audit)
    subprocess.Popen = socket.socket = socket.create_connection = signal.signal = denied
    for name in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen"):
        if hasattr(os, name):
            setattr(os, name, denied)


def bounded():
    if time.monotonic() - START > 60:
        raise AssertionError("offline verification exceeded 60 seconds")
