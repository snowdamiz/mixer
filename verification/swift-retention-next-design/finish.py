#!/usr/bin/env python3
"""Reproduce derived arithmetic, verify immutable finite results and seal this lane."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs/swift-retention-next-design.md"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def members(paths):
    return [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
             "sha256": sha(p.read_bytes())} for p in sorted(paths)]


def main():
    first = load(HERE / "model-attempt-1/command.json")
    assert first["contract_sha256_before_execution"] == sha((HERE / "contract.json").read_bytes())
    metadata_changes = {}
    for directory in ("model-attempt-1", "tests-attempt-1"):
        packet = HERE / directory
        result = load(packet / "result.json")
        assert result["exit_code"] == 0 and result["all_consulted_inputs_unchanged"] and result["source_closure_unchanged"]
        assert sha((packet / "stdout").read_bytes()) == result["stdout_sha256"]
        assert sha((packet / "stderr").read_bytes()) == result["stderr_sha256"]
        for member in load(packet / "inputs.json"):
            actual = sha((ROOT / member["path"]).read_bytes())
            if actual != member["sha256"]:
                assert member["path"] == "PLAN.md", member["path"]
                metadata_changes[member["path"]] = {"historical_sha256": member["sha256"], "current_sha256": actual,
                    "scope": "Root-owned execution index changed after the completed finite invocations; ordinary VM and frozen policy remain unchanged. Root confirmed its separate delivery update."}
        cleanup = load(packet / "cleanup.json")
        assert cleanup["absent_after_cleanup"] and not Path(cleanup["owned_temporary_path"]).exists()
    test_stderr = (HERE / "tests-attempt-1/stderr").read_text()
    assert "Ran 24 tests" in test_stderr and test_stderr.endswith("\nOK\n")
    vm_manifest = load(ROOT / "verification/swift-cost-retention-candidate/live-baseline-source-manifest.json")
    assert len(vm_manifest) == 132
    for name, expected in vm_manifest.items():
        assert sha((ROOT / "vm" / name).read_bytes()) == expected
    temporary = Path(tempfile.mkdtemp(prefix="mixer-swift-retention-next-design-finish-"))
    identity = temporary.stat()
    analysis = HERE / "analysis-reproduction"
    analysis.mkdir()
    argv = [sys.executable, "-B", str(HERE / "analyze.py")]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMPDIR=str(temporary)), capture_output=True, timeout=20)
        (analysis / "stdout").write_bytes(result.stdout)
        (analysis / "stderr").write_bytes(result.stderr)
        assert result.returncode == 0
        assert result.stdout == (HERE / "comparison.json").read_bytes()
    finally:
        current = temporary.stat()
        assert (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino)
        assert not list(temporary.iterdir())
        shutil.rmtree(temporary)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True).stdout.strip()
    write(HERE / "metadata-context-change.json", {"changes": metadata_changes,
          "initial_seal_preflight_failure_preserved": "seal-preflight-attempt-1/",
          "model_or_test_rerun_for_metadata_change": False, "policy_retuned": False})
    write(analysis / "receipt.json", {"argv": argv, "cwd": str(ROOT), "started_utc": started,
          "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "python_executable": sys.executable, "python_executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
          "python_version": sys.version, "platform": platform.platform(), "machine": platform.machine(),
          "exit_code": result.returncode, "stdout_sha256": sha(result.stdout), "stderr_sha256": sha(result.stderr),
          "analysis_source_sha256": sha((HERE / "analyze.py").read_bytes()),
          "derived_output_exactly_reproduced": True, "source_revision": revision,
          "owned_temporary_path": str(temporary), "owned_temporary_identity": {"device": identity.st_dev, "inode": identity.st_ino},
          "temporary_removed": not temporary.exists(), "temporary_removed_files": 0, "temporary_removed_logical_bytes": 0,
          "signals_sent": [], "process_discovery": False,
          "scope": "Own arithmetic analyzer only; no prior producer, VM, compiler, native or actual-target execution"})
    own_files = [DOC, *[p for p in HERE.rglob("*") if p.is_file() and p.name not in ("seal.json", "seal.sha256")]]
    assert not any(p.is_symlink() for p in own_files)
    for p in own_files:
        if p.suffix == ".py":
            ast.parse(p.read_text(), filename=str(p))
        if p.suffix == ".json":
            load(p)
        if p.suffix in (".py", ".json", ".md"):
            assert all(line == line.rstrip() for line in p.read_text().splitlines()), p
    seal = {"schema": 1, "selection": "unselected-no-live-integration-no-full-target",
            "scope": "24 finite Python host methods and fixed synthetic traces; no product/runtime qualification",
            "source_revision": revision, "ordinary_live_source_closure": first["source_closure"],
            "historical_engine_evidence_and_live_source_unchanged": True,
            "root_owned_metadata_changes_after_completed_invocations": metadata_changes,
            "frozen_model_and_contract_unchanged": True,
            "all_three_owned_temporary_directories_absent": True,
            "members": members(own_files)}
    write(HERE / "seal.json", seal)
    digest = sha((HERE / "seal.json").read_bytes())
    (HERE / "seal.sha256").write_text(digest + "\n")
    for member in seal["members"]:
        assert sha((ROOT / member["path"]).read_bytes()) == member["sha256"]
    print(json.dumps({"selection": seal["selection"], "checks_passed": 24, "sealed_members": len(seal["members"]),
                      "seal_sha256": digest, "ordinary_live_closure_unchanged": True, "all_owned_temporary_directories_removed": True}, sort_keys=True))


if __name__ == "__main__":
    main()
