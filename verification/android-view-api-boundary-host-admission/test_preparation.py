"""Bounded pure data + mocked custody controls; deny surfaces before subject import.

No compiler, JVM, SDK runtime, product, subprocess, signal, socket or sleep occurs.
All custody child/session/group/wait/clock/stream behavior is synthetic data.
"""
import ast
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import resource
import selectors
import signal
import socket
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def need(value, message):
    if not value:
        raise RuntimeError(message)


def denied(*args, **kwargs):
    raise RuntimeError("PREPARATION DENIED real process/session/group/signal/timer/wait/socket surface")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run():
    local = HERE / "local"
    local.mkdir(exist_ok=True)
    count = 1
    while (local / ("controls-" + str(count))).exists():
        count += 1
    out = local / ("controls-" + str(count))
    out.mkdir()
    observations = []
    report = {"scope": "guarded pure data and mocked custody only", "passed": False,
              "real_runtime_or_process_actions": False, "checks": observations,
              "command": [sys.executable, "-B", str(Path(__file__).resolve())],
              "python": sys.version, "failed_setups_retained": True,
              "reported_root_revision_context_only": "5b6fc4f5c119cb0b2770f8ee752f6cba57761229",
              "revision_verified_with_Git": False}
    def check(name, value):
        need(value, name)
        observations.append({"name": name, "passed": True})
    def refuses(name, action):
        try:
            action()
        except (RuntimeError, ValueError):
            check(name, True)
        else:
            check(name, False)
    try:
        with ExitStack() as guards:
            # Patch actual module surfaces BEFORE importing either subject.
            denied_surfaces = []
            for module, names in (
                (subprocess, ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput")),
                (os, ("system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "execv", "execve", "execl", "execlp", "execvp", "execvpe", "setsid", "setpgid", "getpgid", "getsid", "getpid", "kill", "killpg", "wait", "waitpid", "waitid")),
                (signal, ("signal", "alarm", "setitimer", "pause", "pthread_kill", "sigwait", "sigwaitinfo", "sigtimedwait")),
                (time, ("sleep", "monotonic", "perf_counter", "time")),
                (threading, ("Thread", "Timer")),
                (socket, ("socket", "socketpair", "create_connection", "getaddrinfo")),
                (resource, ("setrlimit",)),
                (selectors, ("DefaultSelector",)),
            ):
                for name in names:
                    if hasattr(module, name):
                        guards.enter_context(patch.object(module, name, denied))
                        denied_surfaces.append(module.__name__ + "." + name)
            report["denied_before_subject_import"] = denied_surfaces
            collector = load(HERE / "collect.py", "view_api_candidate_guarded_collector")
            custody = load(HERE / "custody.py", "view_api_candidate_guarded_custody")
            check("subjects import inert under denied surfaces", True)
            manifest = json.loads((HERE / "input-manifest.json").read_bytes())
            profile = json.loads((HERE / "tool-profile.json").read_bytes())
            runtime_rows = json.loads((HERE / "jdk-runtime-members.json").read_bytes())
            check("Linux exact runtime74 official manifest totals", len(runtime_rows) == 74 and sum(e["bytes"] for e in runtime_rows) == 198674633)
            runtime_paths = {e["path"] for e in runtime_rows}
            check("JDK compiler modules/signatures and native libraries pinned", {"bin/java", "bin/javac", "release", "lib/modules", "lib/ct.sym", "lib/server/libjvm.so", "lib/libjli.so"} <= runtime_paths)
            check("CA/source exclusions explicit", "lib/security/cacerts" not in runtime_paths and "lib/src.zip" not in runtime_paths)
            check("Linux profile selected without installer or historical fallback", profile["identity_mode"] == "official-jdk-runtime-files-v1" and profile["host_os"] == "linux")
            observed = collector.verify_frozen_inputs()
            check("frozen producer115 + source/review/inspector manifest and product16", observed["host_inputs"] == 103 and observed["sdk_inputs"] == 17)
            plan = collector.build_plan(ROOT, out / "planned-only", profile, manifest)
            commands = plan["commands"]
            check("finite six fixed commands plus emitted-map D8", [e["name"] for e in commands] == ["java-version", "javac-version", "d8-version", "host-compile", "focused-main", "sdk37-compile"] and plan["command_count"] == 7)
            java_inputs = lambda e: [a for a in e["argv"] if a.endswith(".java")]
            check("host exact103 Java inputs", len(java_inputs(commands[3])) == 103)
            check("SDK exact17 excludes host leaves and focused test", len(java_inputs(commands[5])) == 17 and not any("host-leaves" in a or "ViewApiBoundaryTests" in a for a in java_inputs(commands[5])))
            check("only narrow main", commands[4]["argv"][-2] == "dev.mixer.android.ViewApiBoundaryTests")
            check("direct D8 pinned jar min28", plan["d8_prefix"][-7:] == ["com.android.tools.r8.D8", "--min-api", "28", "--lib", plan["platform_jar"], "--output", plan["dex_dir"]])
            workflow = (HERE / "workflow.DRAFT.yml").read_text()
            actions = json.loads((HERE / "workflow-actions.json").read_bytes())["actions"]
            check("workflow actions use reviewed full commit identities", all(value in workflow for value in actions.values()) and "@v4" not in workflow)
            check("workflow remains draft with manual-only trigger", "workflow_dispatch:" in workflow and "\n  push:" not in workflow and "\n  pull_request:" not in workflow)
            changed = out / "changed-input.json"
            changed.write_bytes(b"changed")
            refuses("copied-byte mismatch against pinned source row refuses", lambda: collector.verify_rows(out, [{"path": changed.name, "bytes": 0, "sha256": "0" * 64}]))
            refuses("duplicate source members refuse", lambda: collector.verify_rows(out, [{"path": changed.name, **collector.identity(changed)}] * 2))
            refuses("escaping source member refuses", lambda: collector.verify_rows(out, [{"path": "../outside", "bytes": 0, "sha256": "0" * 64}]))
            for entry in commands:
                custody._validate(entry["argv"], profile["bounds"])
            check("all explicit argv/bounds accepted as data", True)
            refuses("relative executable refused", lambda: custody._validate(["java"], profile["bounds"]))
            refuses("unreviewed wall bound refused", lambda: custody._validate(["/tool/java"], {**profile["bounds"], "wall_seconds": 61}))
            refuses("root selection requires hosted context", lambda: collector.validate_selection({}, {}))
            golden = {k: True for k in ("spawned", "direct_exit_observed_without_reap", "signals_retired", "direct_reaped", "group_absent", "stdout_eof", "stderr_eof", "preflight_ok", "postflight_ok")}
            golden.update(exit_code=0, errors=[])
            check("independent terminal reduction positive", custody.terminal_verdict(golden))
            for key in tuple(k for k in golden if k not in ("exit_code", "errors")):
                check("terminal evidence independently required: " + key, not custody.terminal_verdict({**golden, key: False}))
            check("nonzero exit independently refused", not custody.terminal_verdict({**golden, "exit_code": 1}))
            check("custody error independently refused", not custody.terminal_verdict({**golden, "errors": ["failure"]}))
            held = {"spawned": True, "pid": 991001, "pgid": 991001, "signals": [], "direct_reaped": False, "signals_retired": True}
            refuses("attempted post-retirement signal denied before OS call", lambda: custody.signal_owned(held, signal.SIGKILL, "must-not-call"))
            refuses("lost direct leader authority denied before OS call", lambda: custody.signal_owned({**held, "signals_retired": False, "direct_reaped": True}, signal.SIGKILL, "must-not-call"))
            refuses("foreign numeric group denied before OS call", lambda: custody.signal_owned({**held, "signals_retired": False, "pgid": 991002}, signal.SIGKILL, "must-not-call"))
            refuses("terminal group observation before reap refused", lambda: custody.observe_terminal_group(held))
            refuses("second terminal group observation refused before OS call", lambda: custody.observe_terminal_group({**held, "direct_reaped": True, "group_probe_count": 1}))
            for mode in ("normal", "stdout-no-eof", "group-present", "group-eperm", "preflight-fail", "bad-bounds"):
                events = []
                descriptors = {101: [b"focused synthetic output\n", b""], 102: [b""]}
                class Stream:
                    def __init__(self, fd): self.fd = fd
                    def fileno(self): return self.fd
                    def close(self): events.append(("close", self.fd))
                class Child:
                    pid = 991003
                    stdout = Stream(101)
                    stderr = Stream(102)
                    def wait(self, timeout):
                        events.append(("direct-wait", timeout))
                        return 0
                class Selector:
                    def __init__(self): self.entries = {}
                    def register(self, stream, event, data): self.entries[stream.fileno()] = (stream, data)
                    def unregister(self, stream): del self.entries[stream.fileno()]
                    def select(self, timeout):
                        events.append(("select", timeout))
                        return [(SimpleNamespace(data=data), 1) for stream, data in list(self.entries.values())]
                    def close(self): events.append(("selector-close",))
                tick = [0.0]
                def now():
                    tick[0] += 10 if mode == "stdout-no-eof" else 0.01
                    return tick[0]
                def popen(*args, **kwargs):
                    need(kwargs["start_new_session"] and kwargs["shell"] is False and kwargs["close_fds"], "mock exact spawn options")
                    events.append(("spawn",))
                    return Child()
                def waitid(*args):
                    need(args == (os.P_PID, 991003, os.WEXITED | os.WNOHANG | os.WNOWAIT), "mock nonreaping wait flags")
                    events.append(("nonreaping-wait",))
                    return SimpleNamespace(si_pid=991003, si_code=1, si_status=0)
                def read(fd, limit):
                    need(limit == 65536, "bounded read")
                    if mode == "stdout-no-eof" and fd == 101: return b"not EOF\n"
                    return descriptors[fd].pop(0)
                def killpg(pgid, sig):
                    need(pgid == 991003, "only synthetic owned group")
                    events.append(("group", sig))
                    if sig == 0:
                        if mode == "group-present": return None
                        if mode == "group-eperm": raise PermissionError("mock inaccessible")
                        raise ProcessLookupError("mock terminal absence")
                def flight():
                    if mode == "preflight-fail": raise RuntimeError("mock setup failure")
                    return {"pure_mock": True}
                with ExitStack() as fakes:
                    for module, name, value in ((subprocess,"Popen",popen),(os,"waitid",waitid),
                        (os,"killpg",killpg),(os,"set_blocking",lambda *a: None),(os,"read",read),
                        (selectors,"DefaultSelector",Selector),(time,"monotonic",now)):
                        fakes.enter_context(patch.object(module,name,value))
                    bounds = dict(profile["bounds"])
                    if mode == "bad-bounds": bounds["wall_seconds"] = 61
                    destination = out / mode
                    if mode == "normal":
                        state = custody.run_command(mode, ["/synthetic/java", "-version"], out, {}, destination, bounds, flight, flight)
                        check("mock normal direct reap/group absence/two EOF pass", state["accepted"])
                    else:
                        refuses("mock " + mode + " refuses", lambda: custody.run_command(mode, ["/synthetic/java", "-version"], out, {}, destination, bounds, flight, flight))
                    state = json.loads((destination / "result.json").read_bytes())
                    if mode in ("preflight-fail", "bad-bounds"):
                        check(mode + " retained before any spawn", not state["spawned"] and not any(e[0] == "spawn" for e in events))
                    else:
                        wait_index = next(j for j,e in enumerate(events) if e[0] == "direct-wait")
                        group_events = [(j,e[1]) for j,e in enumerate(events) if e[0] == "group"]
                        check(mode + " all signals before direct reap", all(j < wait_index for j,sig in group_events if sig != 0))
                        check(mode + " exactly one absence-only post-reap probe", len([(j,sig) for j,sig in group_events if sig == 0]) == 1 and all(j > wait_index for j,sig in group_events if sig == 0))
                        check(mode + " no later probe or signal", not any(e[0] == "group" for e in events[max(j for j,sig in group_events)+1:]))
                    if mode == "stdout-no-eof":
                        check("missing stdout EOF preserved independently", not state["stdout_eof"] and state["stderr_eof"])
                    if mode in ("group-present", "group-eperm"):
                        check(mode + " held without cleanup assertion", not state["accepted"] and not state["group_absent"] and state["signals_retired"])
                report.setdefault("mock_events", {})[mode] = events
            for file in ("collect.py", "custody.py", "test_preparation.py"):
                tree = ast.parse((HERE / file).read_text())
                check(file + " parsed only; no compiler process", isinstance(tree, ast.Module))
            report["source_identities"] = {name: collector.identity(HERE / name) for name in ("collect.py", "custody.py", "input-manifest.json", "tool-profile.json", "workflow.DRAFT.yml", "test_preparation.py")}
            report["preparation_interpreter"] = {"path": str(Path(sys.executable).resolve()), **collector.identity(sys.executable)}
            report["frozen_source_observation"] = observed
            report["passed"] = True
    except BaseException as error:
        report["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        (out / "result.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(observations), "evidence": str(out / "result.json")}))


if __name__ == "__main__":
    run()
