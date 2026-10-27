"""Fresh finite host-only runner; never invokes any retained one-shot runner."""
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
REVIEW = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-correction-independent"
RETURN = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-correction-return.json"


def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")


def custody():
    paths = set()
    # Exact already-declared source146/host11/proposal and earlier packet inputs;
    # no new source query, compiler, generation, or old runner is performed.
    earlier = json.loads((REVIEW / "commands/concrete-findings/input-before.json").read_bytes())
    assert len(earlier) == 443
    for entry in earlier:
        path = ROOT / entry["path"]
        assert row(path) == entry, ("frozen input changed", entry["path"])
        paths.add(path)
    for base, expected, count, size in (
        (CANDIDATE, "f3e4ac2543fde4fe7b1e03019fb49bbb5ba9aca078097e5aeb0fc972703de7a3", 61, 1323422),
        (REVIEW, "a64f0cbb775265509b98bea63faca5e144e6d4b8f685898251ea12d506c8840a", 34, 829896),
    ):
        seal_path = base / "seal.json"
        assert row(seal_path)["sha256"] == expected
        members = json.loads(seal_path.read_bytes())["members"]
        assert len(members) == count and sum(e["bytes"] for e in members) == size
        assert {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != seal_path} == {e["path"] for e in members}
        for member in members:
            path = base / member["path"]
            actual = row(path)
            assert (actual["bytes"], actual["sha256"]) == (member["bytes"], member["sha256"])
            paths.add(path)
        paths.add(seal_path)
    assert row(REVIEW / "correction-contract.json")["sha256"] == "b023b8e816c5a68cfe565f0cf901676998ec50b189aca1ead0bb49dbce142d51"
    assert row(RETURN)["sha256"] == "97aa4d370d6c490e37302ad036e2af029cb6607972147c40c7dd63c410a28c9c"
    paths.add(RETURN)
    return sorted((row(p) for p in paths), key=lambda e: e["path"])


def source_rows():
    return [row(p) for p in sorted(HERE.iterdir()) if p.is_file() and
            (p.suffix == ".py" or p.name in ("contract.json", "interface.inc.rs"))]


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    label, group = sys.argv[1:]
    assert label.isascii() and label.replace("-", "").isalnum()
    groups = {
        "focused": ["test_affine_refusal", "test_recent_review.RequiredPropertyControls"],
        "all": ["test_legacy", "test_independent_migrated", "test_regressions", "test_recent_review", "test_affine_refusal"],
    }
    assert group in groups
    destination = HERE / "commands" / label
    destination.mkdir(parents=True, exist_ok=False)
    start, started = time.monotonic(), datetime.datetime.now(datetime.timezone.utc).isoformat()
    before, sources = custody(), source_rows()
    for entry in sources:
        source = ROOT / entry["path"]
        (destination / source.name).write_bytes(source.read_bytes())
    write(destination / "input-before.json", before)
    tool = Path(sys.executable).resolve()
    env = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
           "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    argv = [str(tool), "-B", "-m", "unittest", "-v"] + groups[group]
    write(destination / "plan.json", {
        "schema": 1, "argv": argv, "cwd": str(HERE), "environment_exact": env,
        "parent_argv": [str(tool), "-B", str(Path(__file__).resolve()), label, group],
        "parent_environment_exact": dict(os.environ), "tool": {**row(tool), "version": sys.version},
        "source": sources, "source_tree_sha256": tree(sources), "input_members": len(before),
        "source_revision_from_frozen_return_only": "a96712bbd79ff4c0709d2811dd2846b4a0ea0096",
        "source146": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
        "host11": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
        "timeout_seconds": 55,
        "scope": "pure synthetic Python host ownership/schema/control regression; frozen-source hashing only; no actual native/compiler/product/UI/capture/Git/global inventory",
        "reused_review_methods_are_fresh_independent_review": False,
    })
    child = None
    stdout = stderr = b""
    timeout, absent, reaped = False, False, False
    try:
        child = subprocess.Popen(argv, cwd=HERE, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            timeout = True
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
        reaped = child.returncode is not None
    finally:
        if child is not None and child.returncode is None:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=5)
            reaped = True
        if child is not None:
            try: os.killpg(child.pid, 0)  # exact owned group only
            except ProcessLookupError: absent = True
        (destination / "stdout").write_bytes(stdout)
        (destination / "stderr").write_bytes(stderr)
        after = custody()
        write(destination / "input-after.json", after)
        own_after = source_rows()
        receipt = {
            "schema": 1, "started_at": started, "elapsed_seconds": time.monotonic() - start,
            "exit": child.returncode if child else None, "timed_out": timeout,
            "owned_pid_pgid": child.pid if child else None, "child_reaped": reaped,
            "owned_group_absent": absent, "input_members": len(before), "inputs_unchanged": before == after,
            "source_before": sources, "source_after": own_after, "source_unchanged": sources == own_after,
            "tool_after": row(tool),
            "outputs": [row(destination / n) for n in ("stdout", "stderr", "input-before.json", "input-after.json")],
            "owned_scratch": [], "native_compiler_product_UI_capture_processes_started": 0,
            "global_process_inventory": False,
        }
        write(destination / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("exit", "elapsed_seconds", "input_members", "inputs_unchanged", "source_unchanged", "child_reaped", "owned_group_absent")}))
    return 0 if child.returncode == 0 and not timeout and absent and reaped and before == after and sources == own_after else 1


if __name__ == "__main__":
    raise SystemExit(main())
