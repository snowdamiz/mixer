#!/usr/bin/env python3
"""Root-operated lifecycle and observation runner. Actual native input is CUA only.

No product source, fixture, compiler, physical-device, synthesized input, or UI
automation APIs are used. This wrapper does not start a Simulator frontend.
"""
from __future__ import annotations
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
from packet import (BASE, ROOT, ORIGINAL, APP_NAME, BUNDLE_ID, SOURCE_CLOSURE,
                    file_sha, read_json, require, restore, verify_original, verify_restored)
from verify import verify_handoff

OUT = BASE / "runtime"
LIFECYCLE = OUT / "lifecycle.json"
DEVELOPER = pathlib.Path("/Applications/Xcode_26.6.app/Contents/Developer")
SIMULATOR = DEVELOPER / "Applications/Simulator.app/Contents/MacOS/Simulator"
SIMCTL = DEVELOPER / "usr/bin/simctl"
RUNTIME_ID = "com.apple.CoreSimulator.SimRuntime.iOS-26-5"
DEVICE_TYPE = "com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro"
DEVICE_NAME = "MixerAuthoredToggleCandidate2Runtime"
PROTECTED = {"24DD0059-D1DD-456D-ADF9-0946595DDE66", "1A7E942B-CF97-4DBB-8786-1D982744EBE4",
             "D55AD884-6D5A-4403-9D16-A0FEE48A29C5", "328CA6E8-BA26-4404-8D47-63EF761B0F91"}
ALLOWED_COMMANDS = {"self-tests", "reset", "set-on", "disable", "stale", "resume", "rtl", "dark", "cancel",
                    "focus", "authored-value", "clear-authored-value"}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def record(kind, value):
    value = {"utc": utc(), "kind": kind, "sourceClosureSHA256": SOURCE_CLOSURE,
             "runnerSHA256": file_sha(pathlib.Path(__file__)), **value}
    path = OUT / "events" / (str(time.time_ns()) + "-" + uuid.uuid4().hex + ".json")
    write_json(path, value)
    return path


def run(argv, check=True, timeout=45):
    argv = [str(value) for value in argv]
    started = utc()
    before = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=ROOT, env={**os.environ, "DEVELOPER_DIR": str(DEVELOPER)},
                                text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        record("command", {"argv": argv, "cwd": str(ROOT), "DEVELOPER_DIR": str(DEVELOPER),
                           "startedUTC": started, "elapsedSeconds": time.monotonic() - before,
                           "timedOut": True, "stdout": str(error.stdout or ""), "stderr": str(error.stderr or "")})
        raise
    record("command", {"argv": argv, "cwd": str(ROOT), "DEVELOPER_DIR": str(DEVELOPER),
                       "startedUTC": started, "elapsedSeconds": time.monotonic() - before,
                       "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    if check and result.returncode:
        raise RuntimeError("Command failed: " + repr(argv) + "\n" + result.stdout + result.stderr)
    return result


def simctl(*args, check=True, timeout=45):
    return run(["/usr/bin/xcrun", "simctl", *args], check=check, timeout=timeout).stdout.strip()


def flatten(devices):
    return {device["udid"]: {**device, "runtimeIdentifier": runtime}
            for runtime, group in devices["devices"].items() for device in group}


def native_snapshot():
    return json.loads(simctl("list", "devices", "--json"))


def baseline_guard(snapshot):
    devices = flatten(snapshot)
    require(PROTECTED.issubset(devices), "A protected iOS27 device is missing; do not alter it")
    require(all(devices[key]["state"] == "Shutdown" for key in PROTECTED), "A protected iOS27 device is active; do not alter it")
    require(not any(device["name"] == DEVICE_NAME for device in devices.values()), "An unrecorded owned-name instance exists; reconcile ownership before installing")


def owned_guard(data, snapshot):
    identifier = data["ownedSimulator"]
    require(identifier not in PROTECTED and identifier not in flatten(data["before"]), "Refusing ownership of a baseline/protected device")
    device = flatten(snapshot).get(identifier)
    if device is not None:
        require(device["name"] == DEVICE_NAME and device["runtimeIdentifier"] == RUNTIME_ID
                and device["deviceTypeIdentifier"] == DEVICE_TYPE, "Owned simulator identity changed")
    return device


def data(require_active=True):
    current = read_json(LIFECYCLE)
    require(current["candidate"] == "candidate-2-directional-pan" and current["sourceClosureSHA256"] == SOURCE_CLOSURE,
            "Lifecycle is for a different candidate")
    if require_active:
        require(not current.get("cleanedUp"), "Owned instance has been cleaned up")
    return current


def documents(current=None):
    current = current or data()
    path = pathlib.Path(current["container"])
    device_root = pathlib.Path.home() / "Library/Developer/CoreSimulator/Devices" / current["ownedSimulator"] / "data/Containers/Data/Application"
    require(path.parent == device_root and path.resolve() == path and path.is_dir(), "App container is outside the recorded owned device")
    return path / "Documents"


def observation(current=None):
    result = read_json(documents(current) / "observations.json")
    require(isinstance(result.get("state"), dict) and isinstance(result.get("events"), list), "Invalid app observation")
    return result


def send_command(value):
    require(value in ALLOWED_COMMANDS, "Unsupported harness command")
    docs = documents()
    before = observation()
    # The frozen app ignores a command equal to its current stage. A harmless,
    # unique default-switch barrier ensures repeated requested commands execute.
    sequence = (["runtime-barrier-" + uuid.uuid4().hex] if before["stage"] == value else []) + [value]
    for stage in sequence:
        (docs / "command.txt").write_text(stage)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            current = observation()
            if current["stage"] == stage and (docs / "stage.txt").read_text() == stage:
                break
            time.sleep(0.03)
        else:
            raise RuntimeError("No app command acknowledgement: " + stage)
    record("harness-command", {"requestedCommand": value, "writtenStages": sequence,
                               "before": before, "after": current,
                               "scope": "Explicit test-harness state; no native touch/key/AX input"})
    if value == "self-tests":
        fresh_checks = current.get("checks", [])[len(before.get("checks", [])):]
        require(len(fresh_checks) == 12 and all(item.get("pass") is True for item in fresh_checks),
                "Native programmatic self-tests did not return 12 passing checks; actual input remains separate")
    return current


def label(value):
    require(value and len(value) <= 90 and all(char.isalnum() or char in "-_" for char in value), "Invalid evidence label")
    return value


def capture(name):
    name = label(name)
    path = OUT / "captures" / (name + ".json")
    require(not path.exists(), "Capture already exists; use a new label")
    result = {"utc": utc(), "observations": observation(), "actualInput": "CUA only; see root CUA evidence",
              "screenshot": "Pending root CUA capture; this command does not capture compositor pixels"}
    write_json(path, result)
    record("observation-capture", {"path": str(path), "sha256": file_sha(path)})
    return result


def frontend_identity(pid):
    result = run(["/bin/ps", "-p", str(pid), "-o", "lstart=", "-o", "comm="], check=False)
    if result.returncode or not result.stdout.strip():
        return None
    value = result.stdout.strip()
    require(value.endswith(" " + str(SIMULATOR)), "Frontend PID is not the pinned Simulator executable")
    return value


def frontend_pids():
    result = run(["/usr/bin/pgrep", "-f", "/Simulator.app/Contents/MacOS/Simulator"], check=False)
    return [int(value) for value in result.stdout.split()]


def tool_fingerprints():
    import plistlib
    info = DEVELOPER.parent / "Info.plist"
    parsed = plistlib.loads(info.read_bytes())
    require(parsed["CFBundleShortVersionString"] == "26.6", "Pinned Xcode version differs")
    paths = [pathlib.Path(sys.executable).resolve(), pathlib.Path("/usr/bin/xcrun"), SIMCTL, SIMULATOR, info]
    return {"python": sys.version, "XcodeInfoVersion": parsed["CFBundleShortVersionString"],
            "files": {str(path): file_sha(path) for path in paths}, "DEVELOPER_DIR": str(DEVELOPER)}


def install():
    require(not LIFECYCLE.exists() or data(False).get("cleanedUp"), "Reuse the recorded active owned instance")
    require(not LIFECYCLE.exists(), "This run is terminal after cleanup; preserve its evidence and use a new reviewed run packet")
    verify_handoff()
    producer = verify_original()
    restored = restore(OUT / "restored-app")
    tools = tool_fingerprints()
    version = run([str(DEVELOPER / "usr/bin/xcodebuild"), "-version"]).stdout.strip()
    require(version.startswith("Xcode 26.6\n"), "Native tool version does not match pin")
    # simctl has no required standalone version flag; retain its help output,
    # the enclosing Xcode version, and the exact simctl executable fingerprint.
    simctl_help = simctl("help")
    before = native_snapshot()
    baseline_guard(before)
    runtimes = json.loads(simctl("list", "runtimes", "--json"))["runtimes"]
    candidates = [item for item in runtimes if item.get("isAvailable") and item["identifier"] == RUNTIME_ID
                  and item["version"] == "26.5" and item["buildversion"] == "23F77"]
    require(len(candidates) == 1, "Exact iOS26.5 runtime23F77 is not available")
    runtime = candidates[0]
    require(DEVICE_TYPE in {item["identifier"] for item in runtime["supportedDeviceTypes"]}, "Runtime does not support the pinned device type")
    frontend_before = frontend_pids()
    identifier = simctl("create", DEVICE_NAME, DEVICE_TYPE, RUNTIME_ID)
    uuid.UUID(identifier)
    current = {"candidate": "candidate-2-directional-pan", "sourceClosureSHA256": SOURCE_CLOSURE,
               "producer": producer, "restoredApp": restored, "tools": tools,
               "xcodebuildVersion": version, "simctlHelp": simctl_help,
               "ownedSimulator": identifier, "runtime": runtime, "before": before,
               "startedUTC": utc(), "frontend": {"baselinePIDs": frontend_before, "startedByRunner": False,
               "rootStartedPID": None, "status": "Root must register a newly started pinned frontend or record reuse"},
               "physicalDevicesQueried": False, "actualInput": "CUA only", "cleanedUp": False}
    write_json(LIFECYCLE, current)
    try:
        owned_guard(current, native_snapshot())
        simctl("boot", identifier)
        simctl("bootstatus", identifier, "-b", timeout=60)
        simctl("status_bar", identifier, "override", "--time", "9:41", "--dataNetwork", "wifi", "--wifiMode", "active",
               "--wifiBars", "3", "--batteryState", "charged", "--batteryLevel", "100")
        app = OUT / "restored-app" / APP_NAME
        verify_restored(app)
        simctl("install", identifier, app)
        installed_app = pathlib.Path(simctl("get_app_container", identifier, BUNDLE_ID, "app"))
        current["installedApp"] = verify_restored(installed_app)
        current["container"] = simctl("get_app_container", identifier, BUNDLE_ID, "data")
        write_json(LIFECYCLE, current)
        simctl("launch", identifier, BUNDLE_ID)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if (documents(current) / "observations.json").is_file():
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("App did not record initial state")
        return capture("initial")
    except BaseException as error:
        current = data(False)
        current["installFailure"] = repr(error)
        write_json(LIFECYCLE, current)
        cleanup()
        raise


def cleanup():
    if not LIFECYCLE.exists():
        return {"ownedSimulator": None, "cleanup": "No instance was created by this packet"}
    current = data(False)
    before_cleanup = native_snapshot()
    device = owned_guard(current, before_cleanup)
    if device:
        if "container" in current and (documents(current) / "observations.json").exists():
            write_json(OUT / "final-observations.json", observation(current))
        if device["state"] != "Shutdown":
            simctl("shutdown", current["ownedSimulator"], check=False)
        simctl("delete", current["ownedSimulator"], check=False)
    frontend = current["frontend"]
    pid = frontend.get("rootStartedPID")
    if pid:
        identity = frontend_identity(pid)
        if identity:
            require(identity == frontend["identity"], "Frontend PID identity changed; refusing to stop it")
            os.kill(pid, signal.SIGTERM)
            record("frontend-stop", {"pid": pid, "identity": identity, "signal": "SIGTERM"})
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and frontend_identity(pid):
                time.sleep(0.1)
        frontend["ownedFrontendAbsent"] = frontend_identity(pid) is None
    else:
        frontend["ownedFrontendAbsent"] = True
        frontend["cleanupScope"] = "No registered owned frontend; baseline/other frontends untouched"
    after = native_snapshot()
    after_flat = flatten(after)
    before_flat = flatten(current["before"])
    current.update(after=after, endedUTC=utc(), ownedDeviceAbsent=current["ownedSimulator"] not in after_flat,
                   preservedExistingDeviceIDsAndStates=all(key in after_flat and after_flat[key]["state"] == value["state"]
                                                         for key, value in before_flat.items()))
    current["cleanedUp"] = current["ownedDeviceAbsent"] and frontend["ownedFrontendAbsent"]
    write_json(LIFECYCLE, current)
    require(current["cleanedUp"], "Owned cleanup incomplete; inspect lifecycle and retry cleanup")
    require(current["preservedExistingDeviceIDsAndStates"], "Existing simulator state changed; preserve and investigate without modifying it")
    return current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["restore", "install", "command", "capture", "held", "collect", "cleanup", "frontend", "note"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--after-held-command", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument("--when", choices=["touch", "pan"], default="touch")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--started-by-root", action="store_true")
    args = parser.parse_args()
    verify_handoff()
    require(not OUT.is_symlink() and OUT.resolve() == OUT, "Mutable runtime path is linked or redirected")
    OUT.mkdir(exist_ok=True)
    owner_path = OUT / "owner.json"
    expected_owner = {"schema": "mixer.apple-toggle-runtime-owner.1", "candidate": "candidate-2-directional-pan",
                      "sourceClosureSHA256": SOURCE_CLOSURE, "handoffSealSHA256": file_sha(BASE / "packet-seal.json")}
    if owner_path.exists():
        require(read_json(owner_path) == expected_owner, "Mutable runtime belongs to a different handoff")
    else:
        write_json(owner_path, expected_owner)
    if args.operation in {"install", "cleanup", "frontend"}:
        lock = (OUT / "lifecycle.lock").open("a")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.operation == "restore":
        result = restore(OUT / "restored-app")
    elif args.operation == "install":
        result = install()
    elif args.operation == "command":
        result = send_command(args.value)
    elif args.operation == "capture":
        result = capture(args.value)
    elif args.operation == "held":
        deadline = time.monotonic() + 18
        while time.monotonic() < deadline:
            state = observation()["state"]
            if (state["panActive"] if args.when == "pan" else state["highlighted"] and state["tracking"]):
                break
            time.sleep(0.03)
        else:
            raise RuntimeError("No actual native " + args.when + " hold observed within 18 seconds")
        result = capture(args.value + "-held")
        if args.after_held_command:
            send_command(args.after_held_command)
            result = capture(args.value + "-" + args.after_held_command)
    elif args.operation == "collect":
        result = capture(args.value or "collected")
    elif args.operation == "cleanup":
        result = cleanup()
    elif args.operation == "frontend":
        current = data()
        if args.started_by_root:
            require(args.pid and args.pid not in current["frontend"]["baselinePIDs"], "Cannot own a baseline/missing frontend PID")
            require(not current["frontend"].get("rootStartedPID"), "An owned frontend is already registered")
            identity = frontend_identity(args.pid)
            require(identity, "Owned frontend does not exist")
            current["frontend"].update(rootStartedPID=args.pid, identity=identity, status="Root started pinned frontend; cleanup may stop this exact process")
        else:
            require(args.value == "reuse", "Use frontend reuse or register --pid --started-by-root")
            current["frontend"]["status"] = "Root reuses a baseline frontend; cleanup will preserve it"
        write_json(LIFECYCLE, current)
        result = current["frontend"]
    elif args.operation == "note":
        note = read_json(pathlib.Path(args.value))
        require(all(key in note for key in ["tool", "command", "result", "scope"]), "CUA note needs tool/command/result/scope")
        if note.get("screenshotPath"):
            screenshot = pathlib.Path(note["screenshotPath"])
            require(screenshot.is_absolute() and screenshot.is_file(), "CUA screenshot must be an existing absolute file")
            note["screenshotSHA256"] = file_sha(screenshot)
        result = {"note": str(record("root-cua-evidence", note))}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
