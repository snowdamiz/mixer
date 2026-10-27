"""One specifically authorized Debug compile or exact host witness run."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = HERE / "witness-source"
BUILD = HERE / "witness-build"
BUILD.mkdir(exist_ok=True)
mode = sys.argv[1]
assert mode in ("build", "run")
OUT = HERE / "commands" / ("witness-" + mode + "-001")
OUT.mkdir(parents=True, exist_ok=False)
compiler = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "RUSTC_BOOTSTRAP": "1", "SDKROOT": "/Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk", "CARGO_MANIFEST_DIR": str(WORK / "vm"), "TMPDIR": str(BUILD)}
binary = BUILD / "independent-tests-debug"
if mode == "build":
    argv = [str(compiler), "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin", "-C", "overflow-checks=yes", "-C", "panic=unwind"]
    for feature in ("experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"):
        argv += ["--cfg", f'feature="{feature}"']
    argv += ["--cfg", "mixer_bootstrap_one_fixture_v1", "--test", "-C", "opt-level=0", str(WORK / "vm/src/lib.rs"), "-o", str(binary)]
else:
    argv = [str(binary), "experimental_swift_reactor::retained_profile_loader_v1::prepaid_input_owner_v1::prepaid_actual_owner_v1::independent_result_live_acquisition_retirement_v1", "--exact", "--test-threads=1", "--nocapture"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest():
    return [{"path": str(p.relative_to(WORK)), "bytes": len(p.read_bytes()), "sha256": sha(p.read_bytes())} for p in sorted(WORK.rglob("*")) if p.is_file()]


before = manifest()
expected = json.loads((HERE / "witness-source-manifest.json").read_bytes())
assert before == expected["after"]
compiler_before = sha(compiler.read_bytes())
assert compiler_before == "dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0"
tool_path = compiler if mode == "build" else binary
tool_hash = sha(tool_path.read_bytes())
plan = {"schema": 1, "argv": argv, "environment": environment, "tool_path": str(tool_path), "tool_sha256": tool_hash, "compiler_version_from_exact_frozen_tool_receipt": "rustc 1.99.0 (b940084d7 2026-09-28), LLVM23.1.1", "source_manifest_sha256": sha((HERE / "witness-source-manifest.json").read_bytes()), "source_tree_sha256": expected["source_tree_sha256"], "revision_attribution": {"historical_frozen_baseline": "9398732c23648a82097d5a72b02b1c77af818e41", "root_orchestration": "d6af73813244c330a979afb83b45f53490ff5b29", "root_released_HEAD_console_only": "b231f3d405c06bfb348f193d46a348af0529bd84", "producer_contemporaneous_HEAD_queried": False}, "deadline_seconds": 55, "stdout_stderr_each_cap_bytes": 4194304, "native_or_UI_execution": False}
(OUT / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True)+"\n")
t0 = time.monotonic()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
with (OUT / "stdout").open("wb") as stdout, (OUT / "stderr").open("wb") as stderr:
    proc = subprocess.Popen(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
    pgid = os.getpgid(proc.pid)
    timed_out = False
    try:
        code = proc.wait(timeout=51)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(pgid, signal.SIGKILL)
        code = proc.wait(timeout=3)
try:
    os.killpg(pgid, 0)
    absent = False
except ProcessLookupError:
    absent = True
after = manifest()
receipt = {"schema": 1, "mode": mode, "started_at": started, "seconds": time.monotonic()-t0, "exit_code": code, "desired_property_passed": code == 0 if mode == "run" else None, "timed_out": timed_out, "pid": proc.pid, "pgid": pgid, "waited": True, "owned_process_group_absent": absent, "source_unchanged": before == after, "tool_unchanged": sha(tool_path.read_bytes()) == tool_hash, "native_or_UI_execution": False}
for output in ("stdout", "stderr"):
    data = (OUT / output).read_bytes()
    receipt[output] = {"bytes": len(data), "sha256": sha(data)}
    assert len(data) <= 4194304
for name, value in (("input-before.json", before), ("input-after.json", after), ("receipt.json", receipt)):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")
assert absent and before == after and not timed_out
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(code)
