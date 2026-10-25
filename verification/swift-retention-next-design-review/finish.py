#!/usr/bin/env python3
"""Finalize only this independent review. No product/producer/metadata writes."""
import ast
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/swift-retention-next-design"
DOC = ROOT / "docs/swift-retention-next-design-review.md"


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    assert not (HERE / "seal.json").exists()
    producer_seal = sha((PACKET / "seal.json").read_bytes())
    assert producer_seal == "9fb43c9111e0b4bf5f340358983f404087a5980e7da27c9c3e40483b1649ae57"
    assert (PACKET / "seal.sha256").read_text() == producer_seal + "\n"
    for member in load(PACKET / "seal.json")["members"]:
        payload = (ROOT / member["path"]).read_bytes()
        assert (len(payload), sha(payload)) == (member["bytes"], member["sha256"])
    contexts = {}
    for name, expected_count in (("independent-attempt-1", 18), ("producer-regression-attempt-1", 24)):
        attempt = HERE / name
        command, result, cleanup = (load(attempt / file) for file in ("command.json", "result.json", "cleanup.json"))
        assert result["exit_code"] == 0 and result["exception"] is None and result["ordinary_live_source_closure_unchanged"]
        assert result["all_inputs_unchanged"] and not result["input_changes"]
        assert sha((attempt / "stdout").read_bytes()) == result["stdout_sha256"]
        assert sha((attempt / "stderr").read_bytes()) == result["stderr_sha256"]
        stderr = (attempt / "stderr").read_text()
        assert f"Ran {expected_count} tests" in stderr and stderr.endswith("\nOK\n")
        assert cleanup["identity_unchanged"] and cleanup["absent_after_cleanup"]
        assert not Path(cleanup["owned_temporary_path"]).exists()
        assert not cleanup["signals_sent"] and not cleanup["process_discovery"]
        plan = next(member for member in load(attempt / "inputs.json") if member["path"] == "PLAN.md")
        contexts[name] = {"source_revision_before": result["source_revision_before"], "source_revision_after": result["source_revision_after"],
                          "historical_plan_sha256": plan["sha256"], "python_version": command["python_version"]}
        for member in load(attempt / "inputs.json"):
            if member["path"] == "PLAN.md":
                continue
            payload = (ROOT / member["path"]).read_bytes()
            assert (len(payload), sha(payload)) == (member["bytes"], member["sha256"]), member["path"]
    independent = load(HERE / "independent-attempt-1/stdout")
    assert independent["counts"] == {"oracle_cases": 292, "oracle_requests": 46550, "sealed_members": 30}
    expected = load(ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
    actual = {name: sha((ROOT / "vm" / name).read_bytes()) for name in expected}
    assert actual == expected and len(actual) == 132
    closure_digest = sha((json.dumps(actual, indent=2, sort_keys=True) + "\n").encode())
    assert closure_digest == "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd"
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    git_version = subprocess.run(["git", "--version"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    finalization = HERE / "finalization"
    finalization.mkdir()
    output = (json.dumps({"independent_methods": 18, "producer_regression_methods": 24, "oracle_cases": 292, "oracle_requests": 46550,
                         "producer_seal_verified": True, "ordinary_live_source_closure_unchanged": True, "all_owned_scratch_absent": True,
                         "selection": "withheld-no-implementation-no-integration-no-full-target"}, sort_keys=True) + "\n").encode()
    (finalization / "stdout").write_bytes(output)
    (finalization / "stderr").write_bytes(b"")
    write(finalization / "command.json", {"argv": [sys.executable, "-B", str(HERE / "finish.py")], "cwd": str(ROOT),
          "started_utc": started, "python_version": sys.version, "python_executable": sys.executable,
          "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()), "platform": platform.platform(),
          "machine": platform.machine(), "source_revision": revision, "git_version": git_version,
          "scope": "Pure byte/JSON/syntax/receipt review with git identity reads; no scratch, compiler, VM, target, native, UI/capture or process discovery"})
    write(HERE / "receipt.json", {"schema": 1, "producer_seal_sha256": producer_seal,
          "source_revision": revision, "ordinary_live_source_closure": {"files": 132, "digest": closure_digest},
          "independent_tests": {"methods": 18, "oracle_cases": 292, "oracle_requests": 46550},
          "producer_regression_methods": 24, "attempt_contexts": contexts,
          "producer_initial_model_revision": load(PACKET / "model-attempt-1/command.json")["source_revision"],
          "producer_final_seal_revision": load(PACKET / "seal.json")["source_revision"],
          "producer_historical_plan_change": load(PACKET / "metadata-context-change.json"),
          "current_plan_sha256": sha((ROOT / "PLAN.md").read_bytes()),
          "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "finalization_stdout_sha256": sha(output), "finalization_stderr_sha256": sha(b""),
          "all_owned_scratch_absent": True, "owned_compile_products_created": 0,
          "process_discovery": False, "signals_sent": [],
          "selection": "withheld-no-implementation-no-integration-no-full-target",
          "finding": "No material finite-model/result discrepancy found; actual VM work, hit parity, Rust reservations and runtime improvement remain unmeasured",
          "scope": "Host-only finite model/accounting-boundary/result review; no product/producer/metadata edits, no commit/push, no native/full-target/GA qualification"})
    own_paths = [DOC, *[path for path in HERE.rglob("*") if path.is_file() and path.name not in ("seal.json", "seal.sha256")]]
    assert not any(path.is_symlink() for path in own_paths)
    assert not any(path.suffix == ".pyc" for path in own_paths)
    for path in own_paths:
        if path.suffix == ".py":
            ast.parse(path.read_text(), filename=str(path))
        if path.suffix == ".json":
            load(path)
        if path.suffix in (".py", ".md", ".json"):
            assert all(line == line.rstrip() for line in path.read_text().splitlines()), path
    members = [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
               for path in sorted(own_paths)]
    write(HERE / "seal.json", {"schema": 1, "source_revision": revision, "members": members,
          "producer_seal_sha256": producer_seal, "ordinary_live_source_closure_digest": closure_digest,
          "selection": "withheld-no-implementation-no-integration-no-full-target",
          "scope": "Independent finite review only; no actual runtime improvement or Rust memory qualification"})
    (HERE / "seal.sha256").write_text(sha((HERE / "seal.json").read_bytes()) + "\n")
    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
