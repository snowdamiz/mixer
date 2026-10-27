"""New correction-only bounded host runner; never executes an old runner."""
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
ORIGINAL = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract"
REVIEW = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-independent"
SEALS = ((ORIGINAL, "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e", 36, 448460),
         (REVIEW, "0d9c3d4eb6e99a9daa34f2a8ee798c739b0c6e9c41b35b6ef54c2e900684caa2", 42, 928074))
ROOT_RETURN = ROOT / "verification/swift-semantic-adapter-root-review/guarded-snapshot-prepaid-input-owner-return.json"
CONTRACT = REVIEW / "correction-contract.json"


def digest(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def custody():
    paths = set()
    declared = json.loads((ORIGINAL / "commands/host-model-final2/input-custody.json").read_bytes())
    for row in declared:
        path = ROOT / row["path"]
        assert digest(path) == row, ("frozen original input changed", row["path"])
        paths.add(path)
    assert len(declared) == 299 and sum(r["bytes"] for r in declared) == 40253112
    for base, expected, count, byte_count in SEALS:
        seal_path = base / "seal.json"
        assert digest(seal_path)["sha256"] == expected
        seal = json.loads(seal_path.read_bytes())
        actual_set = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file() and p != seal_path}
        assert actual_set == {r["path"] for r in seal["members"]}
        assert len(seal["members"]) == count and sum(r["bytes"] for r in seal["members"]) == byte_count
        for row in seal["members"]:
            path = base / row["path"]
            got = digest(path)
            assert (got["bytes"], got["sha256"]) == (row["bytes"], row["sha256"])
            paths.add(path)
        paths.add(seal_path)
    assert digest(ROOT_RETURN)["sha256"] == "1d3ce2645c959673393c60b0e1b61f938e9be2d8f3758416e45392a3e3542d28"
    assert digest(CONTRACT)["sha256"] == "243d2ff88e6e9d0b129a23d5a0a97420801fe7f6ff7a9cc21c7f9a273d6e475d"
    paths.update((ROOT_RETURN, CONTRACT))
    return sorted((digest(p) for p in paths), key=lambda r: r["path"])


def source_rows():
    return [digest(p) for p in sorted(HERE.iterdir()) if p.is_file() and
            (p.suffix == ".py" or p.name in ("contract.json", "interface.inc.rs"))]


def main():
    label, group = sys.argv[1:]
    assert label and all(ch.isalnum() or ch == "-" for ch in label)
    groups = {
        "legacy": ["test_legacy"],
        "independent": ["test_independent_migrated.IndependentControls"],
        "returned": ["test_independent_migrated.CandidateDesiredPropertyRegressions"],
        "regressions": ["test_regressions"],
        "all": ["test_legacy", "test_independent_migrated", "test_regressions"],
    }
    assert group in groups
    directory = HERE / "commands" / label
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before = custody()
    sources = source_rows()
    for row in sources:
        source = ROOT / row["path"]
        (directory / source.name).write_bytes(source.read_bytes())
    write(directory / "input-before.json", before)
    tool = Path(sys.executable).resolve()
    # A minimal complete recorded environment contains no inherited credentials.
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "TZ": "UTC",
                   "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0"}
    argv = [str(tool), "-B", "-m", "unittest", "-v"] + groups[group]
    plan = {"schema": 1, "argv": argv, "cwd": str(HERE), "environment_exact": environment,
        "parent_argv": [str(tool), "-B", str(Path(__file__).resolve()), label, group],
        "tool": {**digest(tool), "version": sys.version}, "source": sources,
        "source_tree_digest": hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "source146": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
        "host11": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
        "root_revision_from_frozen_return_only": "a96712bbd79ff4c0709d2811dd2846b4a0ea0096",
        "git_invoked": False, "timeout_seconds": 55,
        "scope": "pure synthetic Python model and immutable source-custody controls; no compiler/product/native/UI/capture; no global process inventory"}
    write(directory / "plan.json", plan)
    child = None
    timed_out, absent, reaped = False, False, False
    out = err = b""
    try:
        child = subprocess.Popen(argv, cwd=HERE, env=environment, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        try:
            out, err = child.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            out, err = child.communicate()
        reaped = child.returncode is not None
    finally:
        if child is not None and child.returncode is None:
            os.killpg(child.pid, signal.SIGKILL)
            out, err = child.communicate()
            reaped = True
        if child is not None:
            try:
                os.killpg(child.pid, 0)  # exact owned PGID ONLY
            except ProcessLookupError:
                absent = True
        (directory / "stdout").write_bytes(out)
        (directory / "stderr").write_bytes(err)
        after = custody()
        write(directory / "input-after.json", after)
        receipt = {"schema": 1, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "elapsed_seconds": time.monotonic() - started,
            "exit": child.returncode if child else None, "timed_out": timed_out,
            "owned_pid_pgid": child.pid if child else None, "child_reaped": reaped,
            "owned_group_absent": absent, "inputs_unchanged": before == after,
            "source_before": sources, "source_after": source_rows(), "tool_after": digest(tool),
            "outputs": [digest(directory / name) for name in ("stdout", "stderr", "input-before.json", "input-after.json")],
            "native_compiler_product_processes_started": 0, "owned_scratch": [],
            "scope": plan["scope"]}
        write(directory / "receipt.json", receipt)
    print(json.dumps({"command": label, "group": group, "exit": child.returncode,
                      "input_members": len(before), "inputs_unchanged": before == after,
                      "owned_group_absent": absent, "elapsed_seconds": receipt["elapsed_seconds"]}))
    return 0 if (child.returncode == 0 and not timed_out and before == after and sources == source_rows() and absent and reaped) else 1


if __name__ == "__main__":
    raise SystemExit(main())
