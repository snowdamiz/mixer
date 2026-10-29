"""One explicit owned command; no import-time process, probe, timer or cleanup.

Prepared for a separately selected hosted run. This module has not launched a child.
EOF, direct reap and owned process-group absence are independent requirements.
"""
import hashlib
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import time


class Refusal(RuntimeError):
    pass


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
    """Pure reducer. A zero return code alone never grants acceptance."""
    required = ("spawned", "direct_exit_observed_without_reap", "signals_retired",
                "direct_reaped", "group_absent", "stdout_eof",
                "stderr_eof", "preflight_ok", "postflight_ok")
    return (all(state.get(k) is True for k in required)
            and state.get("exit_code") == 0 and not state.get("errors"))


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
    # Runs only in the newly forked owned child, before exec. No provider installer.
    for limit, value in ((resource.RLIMIT_AS, bounds["address_bytes"]),
                         (resource.RLIMIT_FSIZE, bounds["file_bytes"]),
                         (resource.RLIMIT_CPU, bounds["cpu_seconds"]),
                         (resource.RLIMIT_NOFILE, bounds["open_files"]),
                         (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(limit, (value, value))


def signal_owned(state, sig, label):
    """Signal only while the original direct leader is still unreaped."""
    if (state.get("signals_retired") or state.get("direct_reaped")
            or not state.get("spawned") or state.get("pgid") != state.get("pid")
            or not isinstance(state.get("pgid"), int) or state["pgid"] <= 0):
        raise Refusal("owned signal authority lost or retired")
    try:
        os.killpg(state["pgid"], sig)
        state["signals"].append({"target": state["pgid"], "signal": label})
    except ProcessLookupError:
        pass


def observe_terminal_group(state):
    """Root-selected single post-reap numeric observation, never signal authority."""
    if (not state.get("signals_retired") or not state.get("direct_reaped")
            or not state.get("spawned") or state.get("pid") != state.get("pgid")
            or not isinstance(state.get("pgid"), int) or state["pgid"] <= 0
            or state.get("group_probe_count", 0) != 0):
        raise Refusal("terminal group observation ordering/count")
    state["group_probe_count"] = 1
    try:
        os.killpg(state["pgid"], 0)
    except ProcessLookupError:
        return True
    except PermissionError as error:
        raise Refusal("terminal numeric group inaccessible; held without further access") from error
    return False


def run_command(name, argv, cwd, env, record_dir, bounds, preflight, postflight):
    """Run exactly once; retain setup, independent streams and failed state.

    No retries or fallback. The only process-group target is Popen.pid from
    start_new_session=True. No process inventory, historical PID or native access.
    """
    directory = Path(record_dir)
    directory.mkdir(parents=True, exist_ok=False)
    state = {"schema": 1, "name": name, "argv": argv, "cwd": str(cwd),
             "env": dict(sorted(env.items())), "bounds": bounds,
             "spawned": False, "direct_reaped": False, "group_absent": False,
             "stdout_eof": False, "stderr_eof": False, "preflight_ok": False,
             "postflight_ok": False, "exit_code": None, "errors": [],
             "direct_exit_observed_without_reap": False, "signals_retired": False,
             "terminal_group_observation": "at most one numeric absence-only probe after reap; no subsequent signal authority",
             "signals": [], "retries": 0, "shell": False,
             "group_origin": "this invocation Popen.pid with start_new_session=True"}
    save(directory / "command.json", state)
    child = None
    selector = None
    streams = {}
    started = None
    cleanup_started = None
    terminated = False
    killed = False
    try:
        _validate(argv, bounds)
        if not all(hasattr(os, name) for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")):
            raise Refusal("nonreaping waitid WNOWAIT required; no fallback")
        state["input_preflight"] = preflight()
        state["preflight_ok"] = True
        started = time.monotonic()
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 close_fds=True, shell=False, start_new_session=True,
                                 preexec_fn=lambda: _apply_limits(bounds))
        state.update(spawned=True, pid=child.pid, pgid=child.pid)
        save(directory / "spawn.json", {"pid": child.pid, "pgid": child.pid,
                                       "new_session": True})
        selector = selectors.DefaultSelector()
        for key, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
            os.set_blocking(stream.fileno(), False)
            streams[key] = {"stream": stream, "written": 0,
                            "file": (directory / key).open("wb")}
            selector.register(stream, selectors.EVENT_READ, key)
        while True:
            now = time.monotonic()
            result = os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if result is not None:
                if result.si_pid != child.pid or result.si_code not in (os.CLD_EXITED, os.CLD_KILLED, os.CLD_DUMPED):
                    raise Refusal("nonreaping direct exit identity/status mismatch")
                state["direct_exit_observed_without_reap"] = True
                state["waitid_status"] = {"pid": result.si_pid, "code": result.si_code,
                                          "status": result.si_status}
                state["observed_exit_code"] = result.si_status if result.si_code == os.CLD_EXITED else -result.si_status
            if (state["direct_exit_observed_without_reap"] and state["stdout_eof"]
                    and state["stderr_eof"]):
                break
            if now - started >= bounds["wall_seconds"] and cleanup_started is None:
                state["errors"].append("wall deadline: reap/group/independent EOF incomplete")
                cleanup_started = now
            if cleanup_started is not None:
                if not terminated:
                    signal_owned(state, signal.SIGTERM, "SIGTERM")
                    terminated = True
                if now - cleanup_started >= 2 and not killed:
                    signal_owned(state, signal.SIGKILL, "SIGKILL")
                    killed = True
                if now - cleanup_started >= bounds["cleanup_seconds"]:
                    state["errors"].append("bounded cleanup exhausted")
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
                entry["file"].write(chunk[:remaining])
                entry["written"] += min(len(chunk), remaining)
                if len(chunk) > remaining and cleanup_started is None:
                    state["errors"].append(key + " output bound exceeded; prefix retained")
                    cleanup_started = time.monotonic()
    except BaseException as error:
        state["errors"].append(type(error).__name__ + ": " + str(error)[:1000])
    finally:
        # Exceptional setup/read failures receive the same finite owned cleanup.
        if child is not None:
            try:
                if not (state["direct_exit_observed_without_reap"] and state["stdout_eof"] and state["stderr_eof"]):
                    signal_owned(state, signal.SIGKILL, "SIGKILL-final")
                # Never poll/reap while signal authority remains. The unreaped
                # direct leader pins this session identity through every signal.
                state["signals_retired"] = True
                save(directory / "signal-authority-retired.json", {"pgid": child.pid,
                     "irreversible": True, "before_direct_reap": True,
                     "further_signals_or_repeated_group_probes": False})
                state["exit_code"] = child.wait(timeout=2)
                state["direct_reaped"] = True
                if state.get("observed_exit_code") != state["exit_code"]:
                    state["errors"].append("direct reaped status differs from nonreaping observation")
                # Numeric ESRCH is a terminal observation only. A present or
                # inaccessible group fails held; never signal/probe it again.
                state["group_absent"] = observe_terminal_group(state)
                if not state["group_absent"]:
                    state["errors"].append("post-reap numeric group present: held, no further access or signals")
            except BaseException as error:
                state["errors"].append("terminal custody: " + type(error).__name__ + ": " + str(error)[:1000])
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
        try:
            state["input_postflight"] = postflight()
            state["postflight_ok"] = True
        except BaseException as error:
            state["errors"].append("postflight: " + type(error).__name__ + ": " + str(error)[:1000])
        state["elapsed_seconds"] = None if started is None else time.monotonic() - started
        state["accepted"] = terminal_verdict(state)
        save(directory / "result.json", state)
    if not state["accepted"]:
        raise Refusal(name + " refused; retained " + str(directory))
    return state
