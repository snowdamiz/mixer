"""Bounded independent host runner. Writes only this review packet, never inputs."""
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
CANDIDATE = ROOT / "verification/swift-guarded-snapshot-prepaid-input-owner-contract"


def digest(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def custody():
    seed = CANDIDATE / "commands/host-model-final2/input-custody.json"
    expected = json.loads(seed.read_bytes())
    for row in expected:
        actual = digest(ROOT / row["path"])
        if actual != row:
            raise ValueError(("producer-declared input mismatch", row, actual))
    seal_bytes = (CANDIDATE / "seal.json").read_bytes()
    if hashlib.sha256(seal_bytes).hexdigest() != "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e":
        raise ValueError("candidate seal changed")
    seal = json.loads(seal_bytes)
    actual_members = {str(p.relative_to(CANDIDATE)) for p in CANDIDATE.rglob("*") if p.is_file() and p.name != "seal.json"}
    if actual_members != {m["path"] for m in seal["members"]}:
        raise ValueError("candidate membership changed")
    for row in seal["members"]:
        actual = digest(CANDIDATE / row["path"])
        if (actual["bytes"], actual["sha256"]) != (row["bytes"], row["sha256"]):
            raise ValueError(("candidate member changed", row))
    root_receipts = {
        "guarded-snapshot-prepaid-input-owner-frozen-release.json": "3f7c771eb0ef9a0e44633dac0dab6c4120cc16ed925909441e503a9e9584434e",
        "guarded-snapshot-scoped-binding-source-host-acceptance.json": "1bc55306a1f6cf220660efa8ab9e34485d610ae806ebd56a1733d892ddfcd2e1",
        "guarded-snapshot-owned-binding-provider-host-acceptance.json": "998a7f6de2918e6b643360b4e67475fdc9a468d69792eb5cda3bb773272fcba3"}
    for name, sha in root_receipts.items():
        path = ROOT / "verification/swift-semantic-adapter-root-review" / name
        if digest(path)["sha256"] != sha:
            raise ValueError(("root receipt changed", name))
    paths = {ROOT / r["path"] for r in expected}
    paths |= {CANDIDATE / r["path"] for r in seal["members"]}
    paths |= {CANDIDATE / "seal.json"}
    paths |= {ROOT / "verification/swift-semantic-adapter-root-review" / p for p in root_receipts}
    paths |= {ROOT / p for p in ("AGENTS.md", "PLAN.md", "mixer-product-plan.md")}
    return sorted((digest(p) for p in paths), key=lambda r: r["path"]), len(expected), sum(r["bytes"] for r in expected)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    label = sys.argv[1]
    if label not in ("candidate-desired-properties", "independent-controls", "source-comparison"):
        raise ValueError("fixed label only")
    destination = HERE / "commands" / label
    destination.mkdir(parents=True, exist_ok=False)
    before, original_count, original_bytes = custody()
    tool = Path(sys.executable).resolve()
    sources = [HERE / ("source_comparison.py" if label == "source-comparison" else "review_controls.py"), Path(__file__).resolve()]
    source_before = [digest(p) for p in sources]
    for source in sources:
        (destination / source.name).write_bytes(source.read_bytes())
    write(destination / "input-before.json", before)
    argv = [str(tool), "-B", str(sources[0])]
    if label == "candidate-desired-properties":
        argv.append("--candidate-regressions")
    plan = {"argv": argv, "cwd": str(ROOT), "timeout_seconds": 55,
            "tool": {**digest(tool), "version": sys.version}, "sources": source_before,
            "original_frozen_input_paths": original_count, "original_frozen_input_bytes": original_bytes,
            "candidate_source_tree": "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d",
            "root_HEAD_at_release": "b20cd3bcd83f9110fbbc62ce60a265373f2a85e5",
            "scope": "pure Python host controls; no compiler, product or native runtime; synthetic funding/handles"}
    write(destination / "plan.json", plan)
    started = time.monotonic()
    began = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    timed_out = False
    try:
        out, err = child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        out, err = child.communicate()
    (destination / "stdout").write_bytes(out)
    (destination / "stderr").write_bytes(err)
    after, _, _ = custody()
    write(destination / "input-after.json", after)
    group_absent = False
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        group_absent = True
    receipt = {"started_at": began, "elapsed_seconds": time.monotonic() - started,
        "exit": child.returncode, "timed_out": timed_out, "child_pid_pgid": child.pid,
        "child_reaped": child.returncode is not None, "owned_group_absent": group_absent,
        "inputs_unchanged": before == after, "source_before": source_before,
        "source_after": [digest(p) for p in sources], "tool_after": digest(tool),
        "outputs": [digest(destination / p) for p in ("stdout", "stderr", "input-before.json", "input-after.json")],
        "compiler_product_native_processes_started": 0,
        "scope": plan["scope"], "expected_candidate_regression_failure": label == "candidate-desired-properties"}
    write(destination / "receipt.json", receipt)
    print(json.dumps({"path": str(destination.relative_to(ROOT)), "exit": child.returncode,
                      "inputs_unchanged": before == after, "owned_group_absent": group_absent}))
    return 0 if (not timed_out and before == after and group_absent) else 2


if __name__ == "__main__":
    raise SystemExit(main())
