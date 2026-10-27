"""New review-only runner: finite child group, exact custody, no old runner."""
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
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-correction"
RELEASE = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-correction-frozen-release.json"


def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def custody():
    expected = json.loads((CANDIDATE / "commands/all-final/input-before.json").read_bytes())
    assert len(expected) == 380
    paths = set()
    for entry in expected:
        path = ROOT / entry["path"]
        assert row(path) == entry, entry["path"]
        paths.add(path)
    seals = ((CANDIDATE, "f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3", 61, 1323422),
             (ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract",
              "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e", 36, 448460),
             (ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-independent",
              "0d9c3d4eb6e99a9daa34f2a8ee798c739b0c6e9c41b35b6ef54c2e900684caa2", 42, 928074))
    for base, digest, count, size in seals:
        seal = base / "seal.json"
        assert row(seal)["sha256"] == digest
        members = json.loads(seal.read_bytes())["members"]
        assert len(members) == count and sum(e["bytes"] for e in members) == size
        assert {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != seal} == {e["path"] for e in members}
        for e in members:
            p = base / e["path"]
            assert (row(p)["bytes"], row(p)["sha256"]) == (e["bytes"], e["sha256"])
            paths.add(p)
        paths.add(seal)
    assert row(RELEASE)["sha256"] == "9ddb0cc5f6c6c1e8a1a5e8ad398cb9f2b1039576bda8f63fbca71ed2fb3a1e1b"
    paths.add(RELEASE)
    return sorted((row(p) for p in paths), key=lambda e: e["path"])


def main():
    label, group = sys.argv[1:]
    assert label.isascii() and label.replace("-", "").isalnum()
    assert group in ("positive", "properties", "witness")
    target = "review_controls." + ("IndependentPositiveControls" if group == "positive" else "RequiredPropertyControls")
    destination = HERE / "commands" / label
    destination.mkdir(parents=True, exist_ok=False)
    before = custody()
    own = [row(p) for p in sorted(HERE.glob("*.py"))]
    for entry in own:
        p = ROOT / entry["path"]
        (destination / p.name).write_bytes(p.read_bytes())
    write(destination / "input-before.json", before)
    tool = Path(sys.executable).resolve()
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    argv = ([str(tool), "-B", str(HERE / "finding_witness.py")] if group == "witness"
            else [str(tool), "-B", "-m", "unittest", "-v", target])
    write(destination / "plan.json", {"schema": 1, "argv": argv, "cwd": str(HERE),
        "environment_exact": env, "parent_environment_exact": dict(os.environ),
        "parent_argv": [str(tool), "-B", str(Path(__file__).resolve()), label, group],
        "tool": {**row(tool), "version": sys.version}, "source": own,
        "source_tree_sha256": hashlib.sha256(json.dumps(own, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "candidate_model": row(CANDIDATE / "model.py"), "input_members": len(before),
        "revision_from_frozen_release_only": "a96712bbd79ff4c0709d2811dd2846b4a0ea0096",
        "source146": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
        "host11": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
        "timeout_seconds": 55, "scope": "pure Python independent host source-model controls only",
        "compiler_native_product_capture_UI_Git_global_inventory": False})
    start = time.monotonic()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    process = subprocess.Popen(argv, cwd=HERE, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timeout = False
    try:
        stdout, stderr = process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timeout = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    absent = False
    try: os.killpg(process.pid, 0)  # Only our exact new process group.
    except ProcessLookupError: absent = True
    if not absent:
        os.killpg(process.pid, signal.SIGKILL)
        try: os.killpg(process.pid, 0)
        except ProcessLookupError: absent = True
    (destination / "stdout").write_bytes(stdout)
    (destination / "stderr").write_bytes(stderr)
    after = custody()
    write(destination / "input-after.json", after)
    own_after = [row(p) for p in sorted(HERE.glob("*.py"))]
    receipt = {"schema": 1, "started": started, "elapsed_seconds": time.monotonic() - start,
               "exit": process.returncode, "timed_out": timeout, "owned_pid_pgid": process.pid,
               "child_reaped": process.returncode is not None, "owned_group_absent": absent,
               "input_members": len(before), "inputs_unchanged": before == after,
               "own_source_unchanged": own == own_after, "tool_after": row(tool),
               "outputs": [row(destination / n) for n in ("stdout", "stderr", "input-before.json", "input-after.json")],
               "owned_scratch": [], "native_compiler_product_capture_processes_started": 0}
    write(destination / "receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if process.returncode == 0 and before == after and own == own_after and absent and not timeout else 1


if __name__ == "__main__":
    raise SystemExit(main())
