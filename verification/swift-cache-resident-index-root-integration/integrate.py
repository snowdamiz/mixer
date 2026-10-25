#!/usr/bin/env python3
"""Integrate only the independently accepted six-file candidate and test live bytes."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PACKET = ROOT / "verification/swift-cache-resident-index"
TOOLS = Path("/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


assert not (OUT / "receipt.json").exists(), "One integration only"
selection = json.loads((OUT / "selection.json").read_text())
assert selection["acceptedForDevelopmentIntegration"] is True
for name, expected in selection["bindings"].items():
    assert sha(ROOT / name) == expected, name
baseline = json.loads((PACKET / "baseline-manifest.json").read_text())
candidate = json.loads((PACKET / "candidate-source-manifest.json").read_text())
assert len(baseline) == len(candidate) == 132
assert {name: sha(ROOT / "vm" / name) for name in baseline} == baseline
assert {name: sha(PACKET / "source" / name) for name in candidate} == candidate
changed = [name for name in baseline if baseline[name] != candidate[name]]
assert changed == selection["changedFiles"] and len(changed) == 6
for name in changed:
    shutil.copyfile(PACKET / "source" / name, ROOT / "vm" / name)
assert {name: sha(ROOT / "vm" / name) for name in candidate} == candidate
save("integrated-manifest.json", candidate)
target = OUT / "target"
assert not target.exists()
env = {**os.environ, "CARGO_TARGET_DIR": str(target), "CARGO_NET_OFFLINE": "true",
       "CARGO_BUILD_JOBS": "2", "RUST_TEST_THREADS": "1", "CARGO_INCREMENTAL": "0"}
env["PATH"] = str(TOOLS) + ":" + env["PATH"]
commands = []
accepted = False
try:
    for label, features, test_filter, expected in [
        ("cache-debug", "experimental-swift-reactor", "experimental_swift_reactor::cache_tests::", 29),
        ("lifecycle-sl13", "experimental-swift-reactor", "swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage", 1),
        ("lifecycle-sl14", "experimental-swift-reactor", "swift_lifecycle_sl14_later_work_cache_and_absolute_deadline_do_not_reset", 1),
        ("frozen-trace", "experimental-function-cache", "frozen_layout_and_trace_observation", 1),
    ]:
        argv = [str(TOOLS / "cargo"), "test", "--locked", "--offline", "--no-default-features",
                "--features", features, "--lib", test_filter, "--", "--nocapture", "--test-threads=1"]
        began = time.monotonic()
        sent = []
        timed_out = False
        with (OUT / (label + ".stdout")).open("wb") as stdout, (OUT / (label + ".stderr")).open("wb") as stderr:
            child = subprocess.Popen(argv, cwd=ROOT / "vm", env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                code = child.wait(timeout=120)
            except subprocess.TimeoutExpired:
                timed_out = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    if child.poll() is not None:
                        break
                    os.killpg(child.pid, sig)
                    sent.append(sig.name)
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        continue
                code = child.poll()
        table = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,pgid="], capture_output=True, timeout=5)
        assert table.returncode == 0
        rows = [list(map(int, line.split())) for line in table.stdout.decode().splitlines() if line.strip()]
        assert all(len(row) == 3 for row in rows)
        matching = [row for row in rows if row[2] == child.pid]
        results = re.findall(r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;", (OUT / (label + ".stdout")).read_text())
        binaries = []
        for value in re.findall(r"Running .*?\(([^)]+)\)", (OUT / (label + ".stderr")).read_text()):
            binary = Path(value)
            if not binary.is_absolute():
                binary = ROOT / "vm" / binary
            if binary.is_file():
                binaries.append({"path": str(binary), "sha256": sha(binary), "bytes": binary.stat().st_size})
        record = {"argv": argv, "cwd": str(ROOT / "vm"), "exitCode": code,
                  "elapsedSeconds": time.monotonic() - began, "timeoutSeconds": 120,
                  "timedOut": timed_out, "pid": child.pid, "processGroup": child.pid,
                  "processGroupMembers": matching, "signalsSent": sent,
                  "streamEOF": {"stdout": True, "stderr": True}, "expectedTests": expected,
                  "testResults": results, "executedBinaries": binaries,
                  "sourceManifestSHA256": sha(PACKET / "candidate-source-manifest.json"),
                  "stdoutSHA256": sha(OUT / (label + ".stdout")), "stderrSHA256": sha(OUT / (label + ".stderr"))}
        commands.append(record)
        save(label + ".command.json", record)
        print(json.dumps({"label": label, "exitCode": code, "tests": results, "groupEmpty": not matching}), flush=True)
        assert code == 0 and not timed_out and not matching and results == [(str(expected), "0", "0")] and binaries
    accepted = True
finally:
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(target)], capture_output=True, timeout=20)
    (OUT / "holders.stdout").write_bytes(holders.stdout)
    (OUT / "holders.stderr").write_bytes(holders.stderr)
    clean = holders.returncode == 1 and holders.stdout == holders.stderr == b"" and all(not c["processGroupMembers"] for c in commands)
    if clean and target.exists():
        shutil.rmtree(target)
    final = {name: sha(ROOT / "vm" / name) for name in candidate}
    tools = {name: {"sha256": sha(TOOLS / name), "version": subprocess.check_output([str(TOOLS / name), "--version"], text=True).strip()} for name in ("rustc", "cargo")}
    save("receipt.json", {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "accepted-live-private-resident-index-integration" if accepted and clean and final == candidate else "incomplete",
        "selectionSHA256": sha(OUT / "selection.json"), "sourceManifestSHA256": sha(PACKET / "candidate-source-manifest.json"),
        "sourceFiles": 132, "sourceUnchangedDuringTests": final == candidate, "commands": commands, "tools": tools,
        "ownedTargetRemoved": not target.exists(), "holderCheckExitCode": holders.returncode,
        "fullTargetSelected": False, "nativeExecuted": False, "gaAccepted": False,
    })
assert accepted and clean and final == candidate
