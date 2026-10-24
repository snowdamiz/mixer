#!/usr/bin/env python3
"""Root-only bounded diagnostic session. Actual input/screenshots are CUA-only.

Ownership, baseline, container, and PID guards are adapted from the frozen reviewed
apple-authored-toggle-runtime-preflight/runtime.py. No native call runs on import.
Use a supervised session so finish, timeout, interruption, and errors clean up.
"""
import argparse
import datetime
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
from packet import BASE, ROOT, CONFIGS, SOURCE_CLOSURE, file_sha, read_json, require, restore, verify_packet, verify_restored, verify_installed

OUT = BASE / "runtime"
LIFECYCLE = OUT / "lifecycle.json"
DEVELOPER = pathlib.Path("/Applications/Xcode_26.6.app/Contents/Developer")
SIMULATOR = DEVELOPER / "Applications/Simulator.app/Contents/MacOS/Simulator"
RUNTIME_ID = "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
DEVICE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
DEVICE_NAME = "MixerAuthoredToggleDiagnosticsRetryRuntime"
PROTECTED = {"24DD0059-D1DD-456D-ADF9-0946595DDE66", "1A7E942B-CF97-4DBB-8786-1D982744EBE4", "D55AD884-6D5A-4403-9D16-A0FEE48A29C5", "328CA6E8-BA26-4404-8D47-63EF761B0F91"}
ALLOWED_COMMANDS = {"self-tests", "reset", "set-on", "disable", "stale", "resume", "rtl", "dark", "cancel", "focus", "authored-value", "clear-authored-value"}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def record(kind, value):
    path = OUT / "events" / (str(time.time_ns()) + "-" + uuid.uuid4().hex + ".json")
    write_json(path, {"utc": utc(), "kind": kind, "sourceClosureSHA256": SOURCE_CLOSURE, "runnerSHA256": file_sha(pathlib.Path(__file__)), **value})
    return path


def run(argv, check=True, timeout=45):
    argv = list(map(str, argv))
    before = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, "DEVELOPER_DIR": str(DEVELOPER)}, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        record("command", {"argv": argv, "cwd": str(ROOT), "DEVELOPER_DIR": str(DEVELOPER), "timedOut": True, "stdout": str(error.stdout or ""), "stderr": str(error.stderr or ""), "elapsedSeconds": time.monotonic()-before})
        raise
    record("command", {"argv": argv, "cwd": str(ROOT), "DEVELOPER_DIR": str(DEVELOPER), "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr, "elapsedSeconds": time.monotonic()-before})
    if check and result.returncode:
        raise RuntimeError("Command failed: " + repr(argv) + "\n" + result.stdout + result.stderr)
    return result


def simctl(*args, check=True, timeout=45):
    return run(["/usr/bin/xcrun", "simctl", *args], check, timeout).stdout.strip()


def flatten(devices):
    return {device["udid"]: {**device, "runtimeIdentifier": runtime} for runtime, group in devices["devices"].items() for device in group}


def native_snapshot():
    return json.loads(simctl("list", "devices", "--json"))


def baseline_guard(snapshot):
    devices = flatten(snapshot)
    require(PROTECTED.issubset(devices), "Protected iOS27 device missing; do not alter it")
    require(all(devices[key]["state"] == "Shutdown" for key in PROTECTED), "Protected iOS27 device active; do not alter it")
    require(not any(device["name"] == DEVICE_NAME for device in devices.values()), "Unrecorded owned-name instance exists; reconcile ownership")


def owned_guard(current, snapshot):
    identifier = current["ownedSimulator"]
    require(identifier not in PROTECTED and identifier not in flatten(current["before"]), "Refusing baseline/protected ownership")
    device = flatten(snapshot).get(identifier)
    if device:
        require(device["name"] == DEVICE_NAME and device["runtimeIdentifier"] == RUNTIME_ID and device["deviceTypeIdentifier"] == DEVICE_TYPE, "Owned simulator identity changed")
    return device


def data(active=True):
    current = read_json(LIFECYCLE)
    require(current["sourceClosureSHA256"] == SOURCE_CLOSURE, "Lifecycle belongs to different sources")
    if active:
        require(not current.get("cleanedUp") and current.get("ready"), "Session is not ready/active")
    return current


def documents(current=None, key=None):
    current = current or data()
    key = key or current["selectedCandidate"]
    path = pathlib.Path(current["apps"][key]["container"])
    parent = pathlib.Path.home() / "Library/Developer/CoreSimulator/Devices" / current["ownedSimulator"] / "data/Containers/Data/Application"
    require(path.parent == parent and path.resolve() == path and path.is_dir(), "Container outside recorded owned device")
    result = path / "Documents"
    require(result.resolve() == result and not result.is_symlink(), "Documents path is redirected")
    return result


def observation(current=None, key=None):
    path = documents(current, key) / "observations.json"
    require(not path.is_symlink() and path.resolve() == path, "Observation path redirected")
    value = read_json(path)
    require(isinstance(value.get("state"), dict) and isinstance(value.get("events"), list), "Invalid app observations")
    return value


def frontend_pids():
    result = run(["/usr/bin/pgrep", "-f", "/Simulator.app/Contents/MacOS/Simulator"], check=False)
    return [int(value) for value in result.stdout.split()]


def process_snapshot(pid):
    result = run(["/bin/ps", "-p", str(pid), "-o", "lstart=", "-o", "stat=", "-o", "comm="], check=False)
    if result.returncode or not result.stdout.strip():
        return None
    parts = result.stdout.strip().split(None, 6)
    require(len(parts) == 7, "Unparseable frontend identity; do not signal")
    return {"pid": pid, "start": " ".join(parts[:5]), "state": parts[5], "command": parts[6]}


def frontend_identity(pid):
    current = process_snapshot(pid)
    if current:
        require(current["command"] == str(SIMULATOR) and not current["state"].startswith("Z"), "Frontend is not the live pinned Simulator executable")
    return current


def stop_frontend(frontend):
    pid = frontend.get("rootStartedPID")
    if not pid:
        frontend.update(ownedFrontendAbsent=True, cleanupScope="No registered owned frontend; baseline frontends preserved")
        return
    current = process_snapshot(pid)
    if current is None:
        frontend["ownedFrontendAbsent"] = True
        return
    expected = frontend["identity"]
    require(current["start"] == expected["start"], "Frontend PID identity changed; do not signal")
    if not current["state"].startswith("Z"):
        require(current["command"] == expected["command"] == str(SIMULATOR), "Frontend PID identity changed; do not signal")
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            frontend["ownedFrontendAbsent"] = True
            return
        record("frontend-stop", {"pid": pid, "identity": current, "signal": "SIGTERM"})
    # Once signalled, only observe. A transient zombie/command label is not an
    # excuse to signal again; a reused PID is preserved as a different process.
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        current = process_snapshot(pid)
        if current is None:
            frontend["ownedFrontendAbsent"] = True
            return
        if current["start"] != expected["start"]:
            frontend.update(ownedFrontendAbsent=True, pidReusedAfterExit=current)
            return
        record("frontend-exit-poll", {"expected": expected, "observed": current})
        time.sleep(0.1)
    frontend["ownedFrontendAbsent"] = False


def label(value):
    require(value and len(value) <= 90 and all(c.isalnum() or c in "-_" for c in value), "Invalid evidence label")
    return value


def capture(name):
    current = data()
    path = OUT / "captures" / (label(name) + ".json")
    require(not path.exists(), "Capture already exists; use a new label")
    result = {"utc": utc(), "candidate": current["selectedCandidate"], "sourceClosureSHA256": CONFIGS[current["selectedCandidate"]]["source"], "observations": observation(current), "actualInput": "CUA only; root must retain exact inputs", "screenshot": "Pending root CUA compositor capture; this runner does not capture pixels"}
    write_json(path, result)
    record("observation-capture", {"path": str(path), "sha256": file_sha(path)})
    return result


def launch(key):
    require(key in CONFIGS, "Unknown candidate")
    current = data()
    require(owned_guard(current, native_snapshot()), "Owned device absent")
    prior = current.get("selectedCandidate")
    if prior:
        simctl("terminate", current["ownedSimulator"], CONFIGS[prior]["bundle"], check=False)
    verify_installed(pathlib.Path(current["apps"][key]["installedApp"]["path"]), key, record)
    current["selectedCandidate"] = key
    write_json(LIFECYCLE, current)
    simctl("launch", current["ownedSimulator"], CONFIGS[key]["bundle"])
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        if (documents(current, key) / "observations.json").is_file():
            record("candidate-launch", {"candidate": key, "identity": CONFIGS[key], "observations": observation(current, key)})
            return
        time.sleep(0.1)
    raise RuntimeError("App did not record initial state")


def install():
    require(not LIFECYCLE.exists(), "Reuse recorded session; this packet is terminal after cleanup")
    verified = verify_packet()
    restored = {key: restore(OUT / "restored-app" / key, key) for key in CONFIGS}
    version = run([DEVELOPER / "usr/bin/xcodebuild", "-version"]).stdout.strip()
    require(version.startswith("Xcode 26.6\n"), "Pinned native tool version changed")
    fingerprints = {str(p): file_sha(p) for p in [pathlib.Path(sys.executable).resolve(), pathlib.Path("/usr/bin/xcrun"), DEVELOPER / "usr/bin/simctl", SIMULATOR, DEVELOPER.parent / "Info.plist"]}
    help_output = simctl("help")
    before = native_snapshot()
    baseline_guard(before)
    runtimes = json.loads(simctl("list", "runtimes", "--json"))["runtimes"]
    matching = [r for r in runtimes if r.get("isAvailable") and r["identifier"] == RUNTIME_ID and r["version"] == "26.5" and r["buildversion"] == "23F77"]
    require(len(matching) == 1 and DEVICE_TYPE in {d["identifier"] for d in matching[0]["supportedDeviceTypes"]}, "Exact iOS26.5(23F77)/iPhone17Pro runtime unavailable")
    baseline_frontends = frontend_pids()
    identifier = simctl("create", DEVICE_NAME, DEVICE_TYPE, RUNTIME_ID)
    uuid.UUID(identifier)
    current = {"sourceClosureSHA256": SOURCE_CLOSURE, "verifiedPacket": verified, "tools": {"python": sys.version, "Xcode": version, "files": fingerprints, "simctlHelp": help_output}, "ownedSimulator": identifier, "before": before, "runtime": matching[0], "startedUTC": utc(), "ready": False, "apps": {}, "selectedCandidate": None, "frontend": {"baselinePIDs": baseline_frontends, "rootStartedPID": None}, "cleanedUp": False, "physicalDevicesQueried": False, "actualInput": "CUA only"}
    write_json(LIFECYCLE, current)
    try:
        owned_guard(current, native_snapshot())
        simctl("boot", identifier)
        simctl("bootstatus", identifier, "-b", timeout=60)
        simctl("status_bar", identifier, "override", "--time", "9:41", "--dataNetwork", "wifi", "--wifiMode", "active", "--wifiBars", "3", "--batteryState", "charged", "--batteryLevel", "100")
        for key, config in CONFIGS.items():
            app = pathlib.Path(restored[key]["path"])
            verify_restored(app, key)
            simctl("install", identifier, app)
            installed = pathlib.Path(simctl("get_app_container", identifier, config["bundle"], "app"))
            current["apps"][key] = {"identity": config, "restoredApp": restored[key], "installedApp": verify_installed(installed, key, record), "container": simctl("get_app_container", identifier, config["bundle"], "data")}
            write_json(LIFECYCLE, current)
        current["ready"] = True
        write_json(LIFECYCLE, current)
        launch("comparator")
        return current
    except BaseException as error:
        current = data(False)
        current["installFailure"] = repr(error)
        write_json(LIFECYCLE, current)
        raise


def send_command(value, strict=True):
    require(value in ALLOWED_COMMANDS, "Unsupported harness command")
    current = data()
    docs = documents(current)
    before = observation(current)
    stages = (["runtime-barrier-" + uuid.uuid4().hex] if before["stage"] == value else []) + [value]
    for stage in stages:
        (docs / "command.txt").write_text(stage)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            after = observation(current)
            if after["stage"] == stage and (docs / "stage.txt").read_text() == stage and (stage != "self-tests" or current["selectedCandidate"] != "diagnostic" or after.get("diagnosticSuiteState") == "complete"):
                break
            time.sleep(0.03)
        else:
            raise RuntimeError("App command not acknowledged/completed: " + stage)
    checks = after.get("checks", [])
    if value == "self-tests":
        fresh = checks if current["selectedCandidate"] == "diagnostic" else checks[len(before.get("checks", [])):]
        expected = 19 if current["selectedCandidate"] == "diagnostic" else 12
        passed = len(fresh) == expected and all(item.get("pass") is True for item in fresh)
    else:
        fresh, passed = [], None
    result = {"candidate": current["selectedCandidate"], "command": value, "writtenStages": stages, "before": before, "after": after, "checks": fresh, "checksPassed": passed, "scope": "Explicit fixture state only; no native touch/key/AX synthesis"}
    record("harness-command", result)
    if strict and value == "self-tests":
        require(passed, "Programmatic native checks failed; failure retained, not carrier acceptance")
    return result


def cleanup():
    if not LIFECYCLE.exists():
        return {"cleanedUp": True, "scope": "No instance created"}
    current = data(False)
    errors = []
    try:
        snapshot = native_snapshot()
        device = owned_guard(current, snapshot)
        if device:
            for key in current.get("apps", {}):
                try:
                    write_json(OUT / (key + "-final-observations.json"), observation(current, key))
                except (FileNotFoundError, ValueError) as error:
                    record("final-observation-unavailable", {"candidate": key, "error": repr(error)})
            if device["state"] != "Shutdown":
                simctl("shutdown", current["ownedSimulator"], check=False)
            simctl("delete", current["ownedSimulator"], check=False)
    except BaseException as error:
        errors.append({"scope": "device cleanup", "error": repr(error)})
    try:
        stop_frontend(current["frontend"])
        unknown = sorted(set(frontend_pids()) - set(current["frontend"]["baselinePIDs"]) - {current["frontend"].get("rootStartedPID")})
        current["frontend"]["unattributedNewPIDsPreserved"] = unknown
        require(not unknown, "Unattributed new frontend preserved; root must reconcile ownership before cleanup is accepted")
    except BaseException as error:
        errors.append({"scope": "frontend cleanup", "error": repr(error)})
    after = native_snapshot()
    after_flat, baseline = flatten(after), flatten(current["before"])
    current.update(after=after, endedUTC=utc(), ready=False, ownedDeviceAbsent=current["ownedSimulator"] not in after_flat,
                   preservedExistingDeviceIDsAndStates=all(key in after_flat and after_flat[key]["state"] == value["state"] for key, value in baseline.items()), cleanupErrors=errors)
    current["cleanedUp"] = current["ownedDeviceAbsent"] and current["frontend"].get("ownedFrontendAbsent", False) and not errors
    write_json(LIFECYCLE, current)
    require(current["cleanedUp"] and current["preservedExistingDeviceIDsAndStates"], "Cleanup incomplete; retained receipt requires safe retry")
    return current


def session(seconds):
    require(30 <= seconds <= 900, "Session bound must be 30...900 seconds")
    for name in ["finish-request.json", "abort-request.json"]:
        require(not (OUT / name).exists(), "Old session request exists; this packet is single-use")
    interrupted = []
    previous = {}
    for signum in [signal.SIGINT, signal.SIGTERM]:
        previous[signum] = signal.signal(signum, lambda received, frame: interrupted.append(received))
    try:
        install()
        print(json.dumps({"ready": True, "deadlineSeconds": seconds, "lifecycle": str(LIFECYCLE)}), flush=True)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and not interrupted and not any((OUT / name).exists() for name in ["finish-request.json", "abort-request.json"]):
            time.sleep(0.2)
        record("session-ending", {"interrupted": interrupted, "finishRequested": (OUT / "finish-request.json").exists(), "abortRequested": (OUT / "abort-request.json").exists(), "deadlineReached": time.monotonic() >= deadline})
    finally:
        try:
            with (OUT / "command.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                cleanup()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["verify", "restore", "session", "finish", "status", "launch", "command", "probe", "capture", "held", "frontend", "note", "cleanup"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--seconds", type=int, default=600)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--after-held-command", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("--when", choices=["touch", "pan"], default="touch")
    args = parser.parse_args()
    verified = verify_packet()
    if args.operation == "verify":
        print(json.dumps(verified, indent=2)); return
    require(not OUT.is_symlink() and OUT.resolve() == OUT, "Mutable runtime path redirected")
    OUT.mkdir(exist_ok=True)
    owner_path = OUT / "owner.json"
    expected_owner = {"schema": "mixer.apple-toggle-diagnostics-retry-owner.1", "sourceClosureSHA256": SOURCE_CLOSURE, "handoffSealSHA256": verified["sealSHA256"]}
    if owner_path.exists():
        require(not owner_path.is_symlink() and read_json(owner_path) == expected_owner, "Mutable runtime belongs to another handoff")
    else:
        require(not any(OUT.iterdir()), "Mutable runtime contains unrecorded files")
        write_json(owner_path, expected_owner)
    if args.operation in {"session", "cleanup"}:
        lifecycle_lock = (OUT / "lifecycle.lock").open("a")
        fcntl.flock(lifecycle_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.operation == "session":
        session(args.seconds); return
    if args.operation == "finish":
        write_json(OUT / "finish-request.json", {"utc": utc()}); print("Finish requested; supervisor performs cleanup"); return
    if args.operation == "cleanup":
        print(json.dumps(cleanup(), indent=2)); return
    if args.operation == "status":
        print(json.dumps(data(False) if LIFECYCLE.exists() else {"status": "not-started"}, indent=2)); return
    with (OUT / "command.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if args.operation == "restore":
                result = {key: restore(OUT / "restored-app" / key, key) for key in CONFIGS}
            elif args.operation == "launch":
                result = launch(args.value)
            elif args.operation in {"command", "probe"}:
                result = send_command(args.value, strict=args.operation == "command")
            elif args.operation == "capture":
                result = capture(args.value)
            elif args.operation == "held":
                deadline = time.monotonic() + 18
                while time.monotonic() < deadline:
                    state = observation()["state"]
                    if state["panActive"] if args.when == "pan" else state["highlighted"] and state["tracking"]:
                        break
                    time.sleep(0.03)
                else:
                    raise RuntimeError("No actual native hold observed")
                result = capture(args.value + "-held")
                if args.after_held_command:
                    send_command(args.after_held_command)
                    result = capture(args.value + "-" + args.after_held_command)
            elif args.operation == "frontend":
                current = data()
                if args.value == "reuse":
                    result = {"scope": "Baseline frontend reused; never signalled by this runner"}
                    current["frontend"]["reuse"] = True
                else:
                    require(args.value == "register" and args.pid and args.pid not in current["frontend"]["baselinePIDs"] and not current["frontend"].get("rootStartedPID"), "Cannot own baseline/missing/already registered frontend")
                    identity = frontend_identity(args.pid)
                    require(identity, "Frontend does not exist")
                    current["frontend"].update(rootStartedPID=args.pid, identity=identity)
                    result = current["frontend"]
                write_json(LIFECYCLE, current)
            elif args.operation == "note":
                note = read_json(pathlib.Path(args.value))
                require(all(key in note for key in ["tool", "command", "result", "scope"]), "CUA note needs exact tool/command/result/scope")
                result = {"record": str(record("root-cua-evidence", note))}
            print(json.dumps(result, indent=2))
        except BaseException as error:
            record("operation-failure", {"operation": args.operation, "error": repr(error)})
            if LIFECYCLE.exists() and not data(False).get("cleanedUp"):
                write_json(OUT / "abort-request.json", {"utc": utc(), "operation": args.operation, "error": repr(error)})
            raise


if __name__ == "__main__":
    main()
