"""Integrate the exact reviewed test observer and run its three real-owner controls."""
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/swift-release-observer-repair"
SCRATCH = HERE / "owned-target"
TEST = "src/experimental_swift_reactor/frame_operations_tests.rs"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


assert not SCRATCH.exists()
assert sha(PACKET / "seal.json") == "b19a8f93c1dd9a6dd4f09cf51c139753b1500be657296d2de09bd0771c22e19c"
seal = json.loads((PACKET / "seal.json").read_text())
for name, expected in seal["files"].items():
    assert sha(PACKET / name) == expected, name
for name, expected in seal["externalFiles"].items():
    assert sha(ROOT / name) == expected, name
baseline = json.loads((PACKET / "baseline-manifest.json").read_text())
candidate = json.loads((PACKET / "candidate-manifest.json").read_text())
for name, expected in baseline.items():
    assert sha(ROOT / "vm" / name) == expected, name
assert [name for name in baseline if baseline[name] != candidate[name]] == [TEST]
guard = b"        if hooks.release_mask == 0 {\n            return false;\n        }\n"
original = (PACKET / "baseline" / TEST).read_bytes()
changed = (PACKET / "candidate" / TEST).read_bytes()
regressions = (PACKET / "regressions.rs").read_bytes()
assert changed.endswith(regressions)
assert changed[:-len(regressions)].replace(guard, b"", 1) == original
(ROOT / "vm" / TEST).write_bytes(changed)
for name, expected in candidate.items():
    assert sha(ROOT / "vm" / name) == expected, name
save("integrated-manifest.json", candidate)
save("source-review.json", {
    "reviewer": "/root", "reviewedFiles": len(seal["files"]),
    "originalSourceFilesMatched": len(baseline), "changedFiles": [TEST],
    "review": "Zero release mask now bypasses test-only recording; nonzero mask logic and original 64-slot bound unchanged. Existing release count/order assertions opt into nonzero masks. Module and callsites are cfg(test). Three controls use actual owners, pins, entry/finish and retained cleanup.",
    "producerTests": 1516, "productionChecks": 4, "productionCfgNegativeChecks": 4,
    "productionBytesChanged": False, "originalSerialTimeoutStillIncomplete": True,
    "gaAccepted": False,
})
SCRATCH.mkdir()
(SCRATCH / "tmp").mkdir()
env = {name: os.environ[name] for name in ("HOME", "USER", "LOGNAME") if name in os.environ}
env.update(PATH="/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true",
    CARGO_TARGET_DIR=str(SCRATCH / "target"), TMPDIR=str(SCRATCH / "tmp"))
tools = {}
expected_tools = json.loads((PACKET / "tools.json").read_text())
for name, flags in (("cargo", ["-V"]), ("rustc", ["-vV"])):
    path = Path(subprocess.check_output(["rustup", "which", name], env=env, text=True).strip())
    assert sha(path) == expected_tools[name]["sha256"], name
    tools[name] = {"path": str(path), "sha256": sha(path), "version": subprocess.check_output([str(path), *flags], env=env, text=True).strip()}
argv = ["cargo", "test", "--lib", "--locked", "--offline", "--no-default-features",
        "--features", "experimental-swift-reactor", "swift_release_observer_", "--", "--nocapture", "--test-threads=1"]
receipt = {"schema": 1, "startedUTC": datetime.now(timezone.utc).isoformat(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "argv": argv, "cwd": str(ROOT / "vm"), "environment": env, "tools": tools,
    "sourceClosure": sha(PACKET / "candidate-manifest.json"), "recorderSHA256": sha(Path(__file__)),
    "timeoutSeconds": 180, "signals": [], "timedOut": False, "productionBytesChanged": False}
start = time.monotonic()
with (HERE / "stdout").open("wb") as stdout, (HERE / "stderr").open("wb") as stderr:
    child = subprocess.Popen(argv, cwd=ROOT / "vm", env=env, stdout=stdout, stderr=stderr, start_new_session=True)
    receipt["pid"] = child.pid
    try:
        child.wait(timeout=180)
    except subprocess.TimeoutExpired:
        receipt["timedOut"] = True
    def group_rows():
        result = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,command="], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            raise RuntimeError("Owned process group observation failed")
        return [row for row in result.stdout.splitlines() if len(row.split(None, 4)) == 5 and row.split(None, 4)[2] == str(child.pid)]
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if not group_rows():
            break
        try:
            os.killpg(child.pid, sig)
            receipt["signals"].append(sig.name)
        except ProcessLookupError:
            break
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and group_rows():
            child.poll()
            time.sleep(.05)
    child.poll()
    receipt.update(exitCode=child.returncode, finalOwnedGroupRows=group_rows())
receipt.update(durationSeconds=time.monotonic() - start, stdoutSHA256=sha(HERE / "stdout"), stderrSHA256=sha(HERE / "stderr"))
receipt["sourcesUnchanged"] = all(sha(ROOT / "vm" / name) == expected for name, expected in candidate.items())
receipt["testsPassed"] = "test result: ok. 3 passed; 0 failed; 0 ignored;" in (HERE / "stdout").read_text()
holders = subprocess.run(["/usr/sbin/lsof", "+D", str(SCRATCH)], capture_output=True, text=True, timeout=30)
(HERE / "holders.stdout").write_text(holders.stdout)
(HERE / "holders.stderr").write_text(holders.stderr)
receipt["cleanup"] = {"holderExitCode": holders.returncode, "removed": False}
if not receipt["finalOwnedGroupRows"] and holders.returncode == 1 and not holders.stdout.strip() and not holders.stderr.strip():
    shutil.rmtree(SCRATCH)
    receipt["cleanup"]["removed"] = True
receipt["status"] = "accepted-test-only-live-integration" if receipt["exitCode"] == 0 and receipt["testsPassed"] and receipt["sourcesUnchanged"] and receipt["cleanup"]["removed"] and not receipt["timedOut"] else "failed-live-integration"
receipt.update(fullReactorRun=False, nativeAccepted=False, gaAccepted=False)
save("receipt.json", receipt)
print(json.dumps(receipt, indent=2))
assert receipt["status"] == "accepted-test-only-live-integration"
