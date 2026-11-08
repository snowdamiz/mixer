"""Owned write guard; one scoped CPython DEVNULL-open capability, no monkeypatch."""
import contextlib
import contextvars
import os
from pathlib import Path
import subprocess
import sys

_stdin_scope = contextvars.ContextVar('accepted_controller_stdin', default=False)
_devnull_code = subprocess.Popen._get_devnull.__code__

@contextlib.contextmanager
def accepted_stdin():
    token = _stdin_scope.set(True)
    try:
        yield
    finally:
        _stdin_scope.reset(token)

def write_guard(root):
    root = Path(root).resolve()
    sys.dont_write_bytecode = True
    def audit(event, args):
        paths = []
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                # Only the unchanged stdlib stdin setup can consume this capability.
                if (_stdin_scope.get() and os.fsdecode(args[0]) == '/dev/null'
                        and args[2] == os.O_RDWR | getattr(os, 'O_CLOEXEC', 0)
                        and sys._getframe(1).f_code is _devnull_code):
                    return
                paths = [args[0]]
        elif event in {'os.mkdir', 'os.rmdir', 'os.remove', 'os.chmod'}:
            if len(args) > 1 and isinstance(args[-1], int) and args[-1] != -1:
                return
            paths = [args[0]]
        elif event in {'os.rename', 'os.link', 'os.symlink'}:
            paths = args[:2]
        for value in paths:
            if not Path(os.fsdecode(value)).resolve().is_relative_to(root):
                raise RuntimeError('Write outside owned correction: ' + str(value))
        if event.startswith('socket.'):
            raise RuntimeError('Network forbidden')
    sys.addaudithook(audit)

def run_direct(controller, argv, cwd):
    with accepted_stdin():
        return controller.run('optimized-member-validation', argv, cwd, timeout=15, allowed=(0, 1))
