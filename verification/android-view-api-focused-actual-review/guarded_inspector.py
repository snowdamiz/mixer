"""Guard preparation only. No subject analyzer is imported by this module.

Future exact inspector execution must occur in a separate, already-acquired data
phase under -I -B -S, with these denials installed before the subject import.
"""
import sys
sys.dont_write_bytecode = True
import builtins
import ctypes
import _ctypes
import _thread
import _socket
import binascii
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import socket
import stat
import struct
import subprocess
import threading
import time
import types
import unicodedata
import zipfile
import zlib


class ActiveAPIDenied(RuntimeError):
    pass


def deny(*args, **kwargs):
    raise ActiveAPIDenied("active process/session/group/signal/timer/wait/socket/native API denied")


class DeniedObject:
    def __getattr__(self, name):
        return deny
    def __call__(self, *args, **kwargs):
        return deny(*args, **kwargs)


def install_guards():
    if not (sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode):
        raise ActiveAPIDenied("Python -I -B -S required before analyzer imports")
    if getattr(sys, "_mixer_actual_review_guards", False):
        raise ActiveAPIDenied("guards already installed; no subject reload")
    patched = []
    def patch(module, names):
        for name in names:
            if hasattr(module, name):
                setattr(module, name, deny)
                patched.append(module.__name__ + "." + name)
    process_names = [n for n in dir(os) if n.startswith(("exec", "spawn", "posix_spawn", "fork", "wait"))]
    process_names += ["system", "popen", "kill", "killpg", "setsid", "setpgid", "getpgid", "getpgrp", "getsid", "tcgetpgrp", "tcsetpgrp", "startfile"]
    patch(os, process_names)
    native_os = sys.modules.get(os.name)
    if native_os is not None:
        patch(native_os, process_names)
    patch(subprocess, ["run", "call", "check_call", "check_output", "getoutput", "getstatusoutput", "_fork_exec", "_posix_spawn", "_waitpid", "_cleanup"])
    patch(subprocess.Popen, ["__init__", "__del__", "poll", "wait", "_wait", "_try_wait", "_internal_poll", "_handle_exitstatus", "communicate", "_communicate", "send_signal", "terminate", "kill", "__enter__", "__exit__"])
    safe = getattr(subprocess, "_del_safe", None)
    if safe is not None and hasattr(safe, "waitpid"):
        safe.waitpid = deny
        patched.append("subprocess._del_safe.waitpid")
    for module_name, names in [("_posixsubprocess", ["fork_exec"]), ("_winapi", ["CreateProcess", "TerminateProcess", "WaitForSingleObject", "WaitForMultipleObjects"])]:
        module = sys.modules.get(module_name)
        if module is not None:
            patch(module, names)
    patch(signal, ["signal", "getsignal", "raise_signal", "pthread_kill", "pthread_sigmask", "sigwait", "sigwaitinfo", "sigtimedwait", "sigpending", "alarm", "pause", "setitimer", "getitimer"])
    patch(time, ["sleep", "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns", "process_time", "process_time_ns", "thread_time", "thread_time_ns", "clock_gettime", "clock_gettime_ns", "clock_getres", "clock_settime", "clock_settime_ns", "get_clock_info"])
    patch(threading.Thread, ["start"])
    patch(threading, ["Timer", "_start_new_thread", "_start_joinable_thread"])
    patch(_thread, ["start_new_thread", "start_new", "start_joinable_thread"])
    patch(socket, ["socket", "SocketType", "socketpair", "create_connection", "create_server", "fromfd", "fromshare", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"])
    patch(_socket, ["socket", "socketpair", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"])
    patch(resource, ["getrusage", "getrlimit", "setrlimit", "prlimit"])
    patch(ctypes, ["CDLL", "PyDLL", "WinDLL", "OleDLL", "_dlopen", "CFUNCTYPE", "PYFUNCTYPE", "WINFUNCTYPE", "cast", "memmove", "memset", "string_at", "wstring_at", "memoryview_at"])
    patch(_ctypes, ["dlopen", "dlsym", "call_function", "call_cdeclfunction", "LoadLibrary", "FreeLibrary"])
    for name in ("cdll", "pydll", "windll", "oledll", "pythonapi"):
        if hasattr(ctypes, name):
            setattr(ctypes, name, DeniedObject())
            patched.append("ctypes." + name)
    # Imports by exact reviewed inspector source are limited to data libraries.
    original_import = builtins.__import__
    permitted = {"sys", "binascii", "hashlib", "io", "_io", "codecs", "json", "math", "os", "pathlib", "re", "stat", "struct", "unicodedata", "zipfile", "zlib", "encodings", "warnings"}
    def bounded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name.split(".")[0] not in permitted:
            raise ActiveAPIDenied("unreviewed analyzer import: " + name)
        return original_import(name, globals, locals, fromlist, level)
    builtins.__import__ = bounded_import
    def audit(event, args):
        if (event.startswith(("subprocess.", "socket.", "ctypes."))
                or event in ("os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "pty.spawn")):
            deny()
    sys.addaudithook(audit)
    sys._mixer_actual_review_guards = True
    return {"installed_before_subject_import": True, "patched_api_count": len(patched), "patched_apis": sorted(patched),
            "subject_import_performed": False, "subject_execution_performed": False}


def load_data_module(path, name):
    """Own review modules only; caller installs guards before invoking this."""
    if not getattr(sys, "_mixer_actual_review_guards", False):
        raise ActiveAPIDenied("guards must precede analyzer import")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    code = compile(Path(path).read_bytes(), str(path), "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module
