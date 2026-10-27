#!/usr/bin/env python3
"""Run one root-released immutable command once, with owned-group cleanup."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
import traceback

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
CAP = 4 * 1024 * 1024
WORK_SECONDS = 51.0
CLEANUP_SECONDS = 54.5


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump_exclusive(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def verify_pins(roster, freeze):
    for member in freeze["members"]:
        data = (PACKET / member["path"]).read_bytes()
        assert len(data) == member["bytes"] and sha(data) == member["sha256"], member["path"]
    for manifest_name, sub in [("independent-vm-manifest.json", "vm"), ("independent-host-manifest.json", "host")]:
        manifest = json.loads((PACKET / manifest_name).read_text())
        actual = []
        for file in sorted((PACKET / "source" / sub).rglob("*")):
            if file.is_file():
                data = file.read_bytes()
                actual.append({"path": str(file.relative_to(PACKET / "source" / sub)), "bytes": len(data), "sha256": sha(data)})
        assert actual == manifest["members"], manifest_name
    tool = roster["tool"]
    data = Path(tool["path"]).read_bytes()
    assert len(data) == tool["bytes"] and sha(data) == tool["sha256"], "tool pin"


def group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def cleanup_owned(process, start, actions):
    # Target only the exact new session/PGID returned by this Popen.
    if group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGTERM)
            actions.append("SIGTERM exact owned PGID")
        except ProcessLookupError:
            pass
        end = min(start + CLEANUP_SECONDS - 0.4, time.monotonic() + 0.35)
        while time.monotonic() < end and group_alive(process.pid):
            process.poll()
            time.sleep(0.01)
    if group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            actions.append("SIGKILL exact owned PGID")
        except ProcessLookupError:
            pass
    remaining = max(0.01, min(0.35, start + CLEANUP_SECONDS - time.monotonic()))
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        actions.append("child reap timeout")


parser = argparse.ArgumentParser()
parser.add_argument("command_id")
parser.add_argument("--release", required=True)
args = parser.parse_args()
roster_bytes = (PACKET / "proposed-command-roster.json").read_bytes()
freeze_bytes = (PACKET / "command-freeze.json").read_bytes()
roster = json.loads(roster_bytes)
freeze = json.loads(freeze_bytes)
release_path = Path(args.release).resolve()
release_bytes = release_path.read_bytes()
release = json.loads(release_bytes)
assert release["execution_released"] is True
assert release["independent_roster_sha256"] == sha(roster_bytes)
assert release["independent_freeze_sha256"] == sha(freeze_bytes)
commands = {command["id"]: command for command in roster["commands"]}
assert len(commands) == len(roster["commands"])
command = commands[args.command_id]
verify_pins(roster, freeze)
destination = PACKET / "commands" / command["id"]
destination.mkdir(parents=True, exist_ok=False)
for output in command.get("output_files", []):
    assert not Path(output).exists(), "output already exists"
environment = dict(roster["environment"])
environment.update(command.get("environment_additions", {}))
plan = {
    "schema": 1,
    "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "id": command["id"], "kind": command["kind"],
    "argv": command["argv"], "cwd": str(ROOT), "environment": environment,
    "root_release": {"path": str(release_path), "sha256": sha(release_bytes)},
    "roster_sha256": sha(roster_bytes), "freeze_sha256": sha(freeze_bytes),
    "production_candidate_tree_sha256": roster["production_candidate_tree_sha256"],
    "independent_instrumented_tree_sha256": roster["independent_instrumented_tree_sha256"],
    "tool": roster["tool"], "tool_version_from_producer": roster["tool_version"],
    "work_seconds_max": WORK_SECONDS, "total_seconds_max": 55,
    "stdout_stderr_each_bytes_max": CAP,
    "scope": command["scope"],
}
dump_exclusive(destination / "plan.json", plan)
start = time.monotonic()
process = None
selector = selectors.DefaultSelector()
observed = {"stdout": 0, "stderr": 0}
captured = {"stdout": bytearray(), "stderr": bytearray()}
failure = []
actions = []
exception = None
returncode = None
postpins = False
try:
    process = subprocess.Popen(command["argv"], cwd=ROOT, env=environment,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    dump_exclusive(destination / "owned-process.json", {
        "pid": process.pid, "pgid": process.pid, "new_session": True,
        "no_global_inventory": True,
    })
    for stream, name in [(process.stdout, "stdout"), (process.stderr, "stderr")]:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    while True:
        if time.monotonic() - start >= WORK_SECONDS:
            failure.append("work deadline")
            break
        for key, _ in selector.select(timeout=0.025):
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                continue
            if not data:
                selector.unregister(key.fileobj)
                continue
            name = key.data
            observed[name] += len(data)
            left = max(0, CAP - len(captured[name]))
            captured[name].extend(data[:left])
            if observed[name] > CAP:
                failure.append(name + " output cap")
        if failure:
            break
        if process.poll() is not None and not selector.get_map():
            break
except BaseException:
    exception = traceback.format_exc()
    failure.append("spawn/capture exception")
finally:
    if process is not None:
        cleanup_owned(process, start, actions)
        returncode = process.poll()
    # Drain only already available bounded data after terminating owned group.
    for key in list(selector.get_map().values()):
        while len(captured[key.data]) <= CAP:
            try:
                data = os.read(key.fileobj.fileno(), 65536)
            except BlockingIOError:
                break
            if not data:
                break
            observed[key.data] += len(data)
            left = max(0, CAP - len(captured[key.data]))
            captured[key.data].extend(data[:left])
            if observed[key.data] > CAP:
                failure.append(key.data + " output cap")
                break
    selector.close()
    for stream in ([] if process is None else [process.stdout, process.stderr]):
        if stream is not None:
            stream.close()
    for name, data in captured.items():
        with (destination / name).open("xb") as stream:
            stream.write(data)
    try:
        verify_pins(roster, freeze)
        postpins = True
    except BaseException:
        failure.append("postrun pin failure")
        exception = (exception or "") + traceback.format_exc()
    absent = process is None or not group_alive(process.pid)
    reaped = process is None or process.poll() is not None
    if not absent:
        failure.append("exact owned group remains")
    if not reaped:
        failure.append("child not reaped")
    text = captured["stderr"].decode(errors="replace")
    if command["kind"] == "compiler-negative":
        if returncode != 1:
            failure.append("negative did not refuse with compiler status 1")
        for phrase in command["intended_diagnostic_phrases"]:
            if phrase not in text:
                failure.append("intended phrase absent: " + phrase)
    elif command["kind"] == "compiler-observation":
        if returncode not in [0, 1]:
            failure.append("historical compatibility observation abnormal exit")
    elif returncode != 0:
        failure.append("command failed")
    if command["kind"] == "host":
        output = captured["stdout"].decode(errors="replace")
        if "42 passed; 0 failed" not in output or "470 filtered out" not in output:
            failure.append("unexpected filtered host test count")
    seconds = time.monotonic() - start
    if seconds > 55:
        failure.append("total 55 second bound")
    outputs = {name: {"bytes": len(data), "sha256": sha(data)} for name, data in captured.items()}
    receipt = {
        "schema": 1, "id": command["id"], "kind": command["kind"],
        "exit": returncode, "seconds": seconds, "outputs": outputs,
        "observed_output_bytes": observed, "captured_bytes_within_caps": all(n <= CAP for n in observed.values()),
        "owned_pid": None if process is None else process.pid,
        "owned_pgid": None if process is None else process.pid,
        "child_reaped": reaped, "exact_owned_group_absent": absent,
        "cleanup_actions": actions, "postrun_pins_verified": postpins,
        "failure_classifications": list(dict.fromkeys(failure)), "exception": exception,
        "success": not failure,
        "semantic_diagnostic_review": "Pending; token matching is not acceptance",
        "scope": command["scope"],
        "no_native_File_VM_fixture_product_leaf_UI_capture_phone_network_global_inventory": True,
    }
    dump_exclusive(destination / "receipt.json", receipt)
print(json.dumps({"id": command["id"], "exit": returncode, "success": not failure,
                  "seconds": seconds, "failure_classifications": list(dict.fromkeys(failure)),
                  "exact_owned_group_absent": absent}))
raise SystemExit(0 if not failure else 1)
