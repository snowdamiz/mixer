"""Focused owned-command custody; import is inert and Popen never proves a reap.

No subject child has run during preparation. A standalone Linux x64 collector is
required: SIGCHLD default without SA_NOCLDWAIT, one Python main thread, no active
Popen cleanup entries, and this module as the exclusive wait owner. Unknown or
lost ownership permanently holds this loaded collector before evidence writes.
"""
import sys
sys.dont_write_bytecode = True
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import subprocess
import threading
import time


class Refusal(RuntimeError):
    pass


class CustodySession:
    """In-memory latch survives all failed persistence in this loaded collector."""
    def __init__(self):
        self.held = False
        self.reasons = []
        self.active = None
        self.references = []

    def claim(self, state):
        if self.held or self.active is not None:
            reason = "new command denied after hold or unresolved custody"
            if self.active is not None:
                self.reject(self.active, reason, lost=True)
            else:
                self.held = True
                self.reasons.append(reason)
            raise Refusal(reason)
        self.active = state

    def reject(self, state, reason, lost=False):
        # These assignments precede every fallible evidence operation.
        self.held = True
        self.reasons.append(reason)
        state["held"] = True
        state["accepted"] = False
        state.setdefault("errors", []).append(reason)
        if lost:
            state["custody_lost"] = True
            state["ownership_valid"] = False
            state["signals_retired"] = True


SESSION = getattr(sys, "_mixer_view_api_custody_session", None)
if SESSION is None:
    SESSION = CustodySession()
    sys._mixer_view_api_custody_session = SESSION


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def identity(path):
    h = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return {"bytes": size, "sha256": h.hexdigest()}


def terminal_verdict(state):
    required = ("spawned", "direct_exit_observed_without_reap", "signals_retired",
                "direct_reaped", "exact_kernel_waitpid", "group_absent", "stdout_eof",
                "stderr_eof", "preflight_ok", "postflight_ok", "wait_owner_preconditions")
    return (all(state.get(k) is True for k in required)
            and state.get("exit_code") == 0 and not state.get("errors")
            and state.get("held") is False and state.get("custody_lost") is False)


def _validate(argv, bounds):
    if not isinstance(argv, list) or not 1 <= len(argv) <= 768:
        raise Refusal("explicit bounded argv required")
    if not all(isinstance(a, str) and a and "\0" not in a and len(a) <= 4096 for a in argv):
        raise Refusal("invalid argv member")
    if not Path(argv[0]).is_absolute():
        raise Refusal("absolute executable required")
    if bounds != {"wall_seconds": 60, "cleanup_seconds": 6,
                  "stream_bytes": 4194304, "address_bytes": 8589934592,
                  "file_bytes": 67108864, "cpu_seconds": 60, "open_files": 128}:
        raise Refusal("unreviewed command bounds")


def _apply_limits(bounds):
    for limit, value in ((resource.RLIMIT_AS, bounds["address_bytes"]),
                         (resource.RLIMIT_FSIZE, bounds["file_bytes"]),
                         (resource.RLIMIT_CPU, bounds["cpu_seconds"]),
                         (resource.RLIMIT_NOFILE, bounds["open_files"]),
                         (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(limit, (value, value))


class NonReapingPopen(subprocess.Popen):
    """Keep Popen's session/exec setup, disable all later implicit/public reapers.

    CPython may directly waitpid on constructor exec failure. That path never
    grants signal authority or successful custody and always holds this session.
    References are retained even when construction raises; __del__ is inert and
    cannot append to subprocess._active or invoke a captured waitpid alias.
    """
    def __del__(self):
        pass

    def _forbidden(self, *args, **kwargs):
        if SESSION.active is not None:
            SESSION.reject(SESSION.active, "forbidden Popen reap/signal API attempted", lost=True)
        raise Refusal("Popen reap/signal/context APIs forbidden; exact kernel custody only")

    poll = wait = _internal_poll = _wait = _try_wait = _handle_exitstatus = _forbidden
    communicate = _communicate = send_signal = terminate = kill = _forbidden
    __enter__ = __exit__ = _forbidden


def wait_owner_preconditions():
    """Read dispositions only; do not repair unknown assumptions by mutation."""
    if (sys.platform != "linux" or platform.machine() != "x86_64"
            or ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(ctypes.c_ulong) != 8
            or ctypes.sizeof(ctypes.c_int) != 4):
        raise Refusal("read-only sigaction contract requires selected Linux x64 ABI")
    main = threading.main_thread()
    if threading.current_thread() is not main or threading.enumerate() != [main]:
        raise Refusal("exclusive main-thread wait ownership unavailable")
    if not hasattr(subprocess, "_active") or type(subprocess._active) is not list or subprocess._active != []:
        raise Refusal("unknown or competing Popen cleanup ownership")
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
        raise Refusal("SIGCHLD must already be default; no disposition change permitted")
    # Linux/glibc x86_64 sigaction ABI only. Python getsignal cannot reveal
    # inherited SA_NOCLDWAIT; a read-only sigaction(NULL) query is also required.
    class Sigaction(ctypes.Structure):
        _fields_ = [("handler", ctypes.c_void_p), ("mask", ctypes.c_ulong * 16),
                    ("flags", ctypes.c_int), ("restorer", ctypes.c_void_p)]
    if (ctypes.sizeof(Sigaction) != 152
            or (Sigaction.handler.offset, Sigaction.mask.offset, Sigaction.flags.offset,
                Sigaction.restorer.offset) != (0, 8, 136, 144)):
        raise Refusal("unknown sigaction layout")
    query = ctypes.CDLL(None, use_errno=True).sigaction
    query.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(Sigaction))
    query.restype = ctypes.c_int
    current = Sigaction()
    if query(signal.SIGCHLD, None, ctypes.byref(current)) != 0:
        raise Refusal("SIGCHLD flags could not be read")
    if current.handler not in (None, 0) or current.flags & 2:  # SA_NOCLDWAIT
        raise Refusal("native SIGCHLD handler/SA_NOCLDWAIT does not retain wait ownership")
    return {"SIGCHLD": "SIG_DFL", "SA_NOCLDWAIT": False,
            "read_only_sigaction": True, "python_main_thread_only": True,
            "subprocess_active_empty": True,
            "exclusive_wait_owner_scope": "standalone selected collector; no external reaper proof"}


def _persist(state, path, value):
    try:
        save(path, value)
    except BaseException as error:
        SESSION.reject(state, "evidence persistence: " + type(error).__name__ + ": " + str(error)[:1000], lost=True)
        raise


def evidence_open(state, path):
    try:
        return Path(path).open("wb")
    except BaseException as error:
        _lose(state, error)
        raise


def evidence_write(state, stream, data):
    try:
        return stream.write(data)
    except BaseException as error:
        _lose(state, error)
        raise


def _lose(state, error):
    SESSION.reject(state, "custody lost: " + type(error).__name__ + ": " + str(error)[:1000], lost=True)


def observe_direct(state):
    if SESSION.active is not state or not state.get("ownership_valid") or state.get("custody_lost"):
        error = Refusal("direct wait ownership already lost or unregistered")
        _lose(state, error)
        raise error
    try:
        result = os.waitid(os.P_PID, state["pid"], os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if result is not None:
            if (type(result.si_pid) is not int or result.si_pid != state["pid"]
                    or type(result.si_code) is not int
                    or result.si_code not in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED)
                    or type(result.si_status) is not int
                    or not 0 <= result.si_status <= (255 if result.si_code == os.CLD_EXITED else 127)
                    or (result.si_code != os.CLD_EXITED and not 0 < result.si_status < signal.NSIG)):
                raise Refusal("nonreaping direct exit identity/status mismatch")
            row = {"pid": result.si_pid, "code": result.si_code, "status": result.si_status}
            if state.get("waitid_status", row) != row:
                raise Refusal("nonreaping direct terminal status changed")
            state["direct_exit_observed_without_reap"] = True
            state["waitid_status"] = row
            state["observed_exit_code"] = result.si_status if result.si_code == os.CLD_EXITED else -result.si_status
        elif state["direct_exit_observed_without_reap"]:
            raise Refusal("previously observed unreaped direct terminal child disappeared")
        return result is not None
    except BaseException as error:
        _lose(state, error)
        raise


def signal_owned(state, sig, label):
    if (SESSION.active is not state or state.get("signals_retired") or state.get("direct_reaped")
            or state.get("custody_lost") or not state.get("ownership_valid")
            or not state.get("spawned") or state.get("pgid") != state.get("pid")
            or type(state.get("pgid")) is not int or state["pgid"] <= 0):
        error = Refusal("owned signal authority lost or retired")
        _lose(state, error)
        raise error
    # Fresh WNOWAIT ownership observation before every allowed numeric signal.
    observe_direct(state)
    try:
        os.killpg(state["pgid"], sig)
        state["signals"].append({"target": state["pgid"], "signal": label})
    except ProcessLookupError:
        pass
    except BaseException as error:
        _lose(state, error)
        raise


def retire_signals(state, directory):
    state["signals_retired"] = True
    _persist(state, directory / "signal-authority-retired.json", {
        "pgid": state["pid"], "irreversible": True, "before_direct_reap": True,
        "further_signals_or_repeated_group_probes": False})


def exact_reap(state):
    if (SESSION.active is not state or not state.get("signals_retired") or state.get("custody_lost")
            or not state.get("ownership_valid") or not state.get("direct_exit_observed_without_reap")
            or state.get("direct_reaped")):
        error = Refusal("exact direct reap ordering/ownership")
        _lose(state, error)
        raise error
    try:
        result = os.waitpid(state["pid"], os.WNOHANG)
        state["kernel_waitpid_result"] = {"python_type": type(result).__name__, "repr": repr(result)[:1000]}
        if type(result) is not tuple or len(result) != 2:
            raise Refusal("kernel waitpid result must be an exact two-member tuple")
        pid, raw = result
        if (type(pid) is not int or pid != state["pid"] or type(raw) is not int
                or not 0 <= raw <= 65535 or not (os.WIFEXITED(raw) or os.WIFSIGNALED(raw))):
            raise Refusal("exact waitpid direct pid/terminal status mismatch")
        observed = state["waitid_status"]
        expected = ((observed["status"] << 8) if observed["code"] == os.CLD_EXITED
                    else observed["status"] | (128 if observed["code"] == os.CLD_DUMPED else 0))
        if raw != expected:
            raise Refusal("exact waitpid raw status differs from unreaped observation")
        state["exit_code"] = os.WEXITSTATUS(raw) if os.WIFEXITED(raw) else -os.WTERMSIG(raw)
        state["exact_kernel_waitpid"] = True
        state["direct_reaped"] = True
        state["ownership_valid"] = False
        if state["exit_code"] != 0:
            SESSION.reject(state, "nonzero direct child status: " + str(state["exit_code"]))
    except BaseException as error:
        _lose(state, error)
        raise


def observe_terminal_group(state):
    if (SESSION.active is not state or SESSION.held or state.get("held") or state.get("custody_lost")
            or not state.get("signals_retired") or not state.get("exact_kernel_waitpid")
            or not state.get("direct_reaped") or not state.get("stdout_eof")
            or not state.get("stderr_eof") or not state.get("spawned")
            or state.get("pid") != state.get("pgid")
            or type(state.get("pgid")) is not int or state["pgid"] <= 0
            or state.get("group_probe_count", 0) != 0):
        error = Refusal("terminal group observation ordering/count/hold")
        _lose(state, error)
        raise error
    state["group_probe_count"] = 1  # Consume before syscall, including unknown errors.
    try:
        os.killpg(state["pgid"], 0)
    except ProcessLookupError:
        state["group_absent"] = True
        return True
    except BaseException as error:
        _lose(state, error)
        raise
    SESSION.reject(state, "post-reap numeric group present: held, no further access or signals", lost=True)
    return False


def run_command(name, argv, cwd, env, record_dir, bounds, preflight, postflight):
    state = {"schema": 2, "name": name, "argv": argv, "cwd": str(cwd),
             "env": dict(sorted(env.items())), "bounds": bounds,
             "spawned": False, "direct_reaped": False, "exact_kernel_waitpid": False,
             "group_absent": False, "stdout_eof": False, "stderr_eof": False,
             "preflight_ok": False, "postflight_ok": False, "exit_code": None,
             "errors": [], "direct_exit_observed_without_reap": False,
             "signals_retired": False, "held": False, "custody_lost": False,
             "ownership_valid": False, "wait_owner_preconditions": False,
             "signals": [], "retries": 0, "shell": False,
             "group_origin": "this invocation NonReapingPopen.pid with start_new_session=True",
             "terminal_group_observation": "at most one numeric absence-only probe after exact reap and both EOFs; no later signal/probe"}
    SESSION.claim(state)  # No filesystem operation or child precedes this claim.
    directory = Path(record_dir)
    child = selector = None
    streams = {}
    started = cleanup_started = None
    terminated = killed = False
    try:
        directory.mkdir(parents=True, exist_ok=False)
        _persist(state, directory / "command.json", state)
        _validate(argv, bounds)
        if not all(hasattr(os, key) for key in ("waitid", "waitpid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT", "CLD_EXITED", "CLD_KILLED", "CLD_DUMPED")):
            raise Refusal("nonreaping waitid and exact waitpid facilities required; no fallback")
        state["input_preflight"] = preflight()
        state["preflight_ok"] = True
        state["wait_owner_observation"] = wait_owner_preconditions()
        state["wait_owner_preconditions"] = True
        started = time.monotonic()
        child = NonReapingPopen.__new__(NonReapingPopen)
        SESSION.references.append(child)  # Retain even if __init__ raises.
        try:
            child.__init__(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True,
                shell=False, start_new_session=True, preexec_fn=lambda: _apply_limits(bounds))
        except BaseException as error:
            _lose(state, error)  # Constructor failure never grants signal authority.
            raise
        if (type(child.pid) is not int or child.pid <= 0 or child.returncode is not None
                or child._child_created is not True):
            _lose(state, Refusal("unknown/cached child construction state"))
            raise Refusal("unknown/cached child construction state")
        state.update(spawned=True, pid=child.pid, pgid=child.pid, ownership_valid=True)
        _persist(state, directory / "spawn.json", {"pid": child.pid, "pgid": child.pid, "new_session": True})
        selector = selectors.DefaultSelector()
        for key, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
            os.set_blocking(stream.fileno(), False)
            streams[key] = {"stream": stream, "written": 0, "file": evidence_open(state, directory / key)}
            selector.register(stream, selectors.EVENT_READ, key)
        while True:
            now = time.monotonic()
            observe_direct(state)
            if state["direct_exit_observed_without_reap"] and state["stdout_eof"] and state["stderr_eof"]:
                break
            if now - started >= bounds["wall_seconds"] and cleanup_started is None:
                SESSION.reject(state, "wall deadline: direct terminal observation/independent EOF incomplete")
                cleanup_started = now
            if cleanup_started is not None:
                if not terminated:
                    signal_owned(state, signal.SIGTERM, "SIGTERM")
                    terminated = True
                if now - cleanup_started >= 2 and not killed:
                    signal_owned(state, signal.SIGKILL, "SIGKILL")
                    killed = True
                if now - cleanup_started >= bounds["cleanup_seconds"]:
                    SESSION.reject(state, "bounded cleanup exhausted")
                    break
            for event, _ in selector.select(timeout=0.05):
                key = event.data
                entry = streams[key]
                chunk = os.read(entry["stream"].fileno(), 65536)
                if not chunk:
                    state[key + "_eof"] = True
                    selector.unregister(entry["stream"])
                    continue
                remaining = bounds["stream_bytes"] - entry["written"]
                evidence_write(state, entry["file"], chunk[:remaining])
                entry["written"] += min(len(chunk), remaining)
                if len(chunk) > remaining and cleanup_started is None:
                    SESSION.reject(state, key + " output bound exceeded; prefix retained")
                    cleanup_started = time.monotonic()
    except BaseException as error:
        SESSION.reject(state, type(error).__name__ + ": " + str(error)[:1000])
    finally:
        if state["spawned"] and not state["custody_lost"]:
            try:
                if not (state["direct_exit_observed_without_reap"] and state["stdout_eof"] and state["stderr_eof"]):
                    if not killed:
                        signal_owned(state, signal.SIGKILL, "SIGKILL-final")
                    final_deadline = time.monotonic() + 2
                    while not observe_direct(state):
                        if time.monotonic() >= final_deadline:
                            _lose(state, Refusal("final direct observation deadline exhausted"))
                            raise Refusal("final direct observation deadline exhausted")
                        time.sleep(0.01)
                # Both EOFs precede retirement on the normal success path.
                retire_signals(state, directory)
                exact_reap(state)
                if not SESSION.held:
                    observe_terminal_group(state)
            except BaseException as error:
                SESSION.reject(state, "terminal custody: " + type(error).__name__ + ": " + str(error)[:1000], lost=True)
        try:
            if selector is not None:
                selector.close()
            for entry in streams.values():
                entry["file"].close()
                entry["stream"].close()
            for key in ("stdout", "stderr"):
                path = directory / key
                if not path.exists():
                    path.write_bytes(b"")
                state[key + "_identity"] = identity(path)
            state["input_postflight"] = postflight()
            state["postflight_ok"] = True
        except BaseException as error:
            SESSION.reject(state, "stream settlement/postflight: " + type(error).__name__ + ": " + str(error)[:1000], lost=True)
        state["elapsed_seconds"] = None if started is None else time.monotonic() - started
        state["held"] = SESSION.held
        state["accepted"] = terminal_verdict(state)
        _persist(state, directory / "result.json", state)
    if not state["accepted"]:
        raise Refusal(name + " refused; retained " + str(directory))
    SESSION.active = None  # Only complete persisted success permits the next child.
    return state
