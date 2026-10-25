"""Owned amendment controls, bytewise history audit and final scope inventory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from run_review import ROOT, OWN, UPSTREAM, sha, verify


def archive_matches(archive, expected_archive, expected_members):
    assert sha(archive) == expected_archive
    seen = set()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        assert len(members) == len(expected_members)
        for member in members:
            assert member.isfile() and member.name not in seen
            seen.add(member.name)
            assert member.name in expected_members, member.name
            expected = expected_members[member.name]
            raw = tar.extractfile(member).read()
            assert len(raw) == expected["bytes"] and hashlib.sha256(raw).hexdigest() == expected["sha256"], member.name
    assert seen == set(expected_members)
    return {"path": str(archive.relative_to(ROOT)), "sha256": expected_archive,
            "members": len(seen), "extracted_restored_imported_or_executed": False}


def with_seal_pair(root, name, rows):
    result = {r["path"]: r for r in rows}
    for suffix in ("seal.json", "seal.sha256"):
        rel = name + "/" + suffix
        p = root / rel
        result[rel] = {"path": rel, "bytes": p.stat().st_size, "sha256": sha(p)}
    return result


def main():
    assert sys.dont_write_bytecode
    assert os.environ.get("FSM_REVIEW_FREEZE") == "producer-freeze-2"
    run = OWN / "commands" / "amendment-controls"
    run.mkdir(parents=True, exist_ok=False)
    before = [verify(ROOT, *entry) for entry in UPSTREAM]
    expected = "bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193"
    producer_before = verify(ROOT, "swift-ordered-retention-analyzer-fsm-contract", expected, 245)
    frozen_root = OWN / "producer-freeze-2/repository"
    frozen_before = verify(frozen_root, "swift-ordered-retention-analyzer-fsm-contract", expected, 245)
    for name in ("test_amendment.py", "audit_amendment.py"):
        shutil.copyfile(OWN / name, run / ("executed-" + name))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    argv = [sys.executable, "-B", str(OWN / "test_amendment.py")]
    result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=60)
    (run / "controls.stdout").write_bytes(result.stdout)
    (run / "controls.stderr").write_bytes(result.stderr)
    producer_name = "verification/swift-ordered-retention-analyzer-fsm-contract"
    initial_root = OWN / "producer-freeze-1/repository"
    initial_rows = json.loads((initial_root / producer_name / "seal.json").read_bytes())["members"]
    first = with_seal_pair(initial_root, producer_name, initial_rows)
    finding_rows = json.loads((OWN / "findings-freeze1-seal.json").read_bytes())["members"]
    findings = {r["path"]: r for r in finding_rows}
    for name in ("findings-freeze1-seal.json", "findings-freeze1-seal.sha256"):
        p = OWN / name
        findings[str(p.relative_to(ROOT))] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    archives = [archive_matches(frozen_root / producer_name / "history/first-freeze/packet.tar.gz",
                "ee5bfd08111a0bd0993b91814add86948622e041d003eb85a6cad678edabdbdc", first),
                archive_matches(frozen_root / producer_name / "history/findings-freeze-1/packet.tar.gz",
                "4d1a0f8ea4ae290831059e3cf3cd54e5e53c6701eb43d5a56397bd1de5c8282c", findings)]
    after = [verify(ROOT, *entry) for entry in UPSTREAM]
    producer_after = verify(ROOT, "swift-ordered-retention-analyzer-fsm-contract", expected, 245)
    frozen_after = verify(frozen_root, "swift-ordered-retention-analyzer-fsm-contract", expected, 245)
    assert before == after and producer_before == producer_after and frozen_before == frozen_after
    bytecode = [str(p.relative_to(ROOT)) for p in OWN.rglob("__pycache__")]
    assert not bytecode
    source_names = ("oracle.py", "test_oracle.py", "test_frozen_contract.py", "test_amendment.py", "run_review.py", "audit_amendment.py")
    sources = [{"path": str((OWN / name).relative_to(ROOT)), "bytes": (OWN / name).stat().st_size, "sha256": sha(OWN / name)} for name in source_names]
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.UTC).isoformat(),
               "upstream_before": before, "upstream_after": after,
               "producer_before": producer_before, "producer_after": producer_after,
               "frozen_before": frozen_before, "frozen_after": frozen_after,
               "command": {"argv": argv, "cwd": str(ROOT), "exit": result.returncode,
                           "stdout_sha256": sha(run / "controls.stdout"), "stderr_sha256": sha(run / "controls.stderr")},
               "archives": archives, "source_rows": sources,
               "source_tree_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
               "independent_additional_methods": 8,
               "candidate_proposal": {"payload_bytes": 96, "owner_bytes": 2048,
                                      "init_roles": 4728, "call_roles": 4536,
                                      "reserved_roles": 5120, "setup_debit": 534,
                                      "record_debit": 128, "actual_Rust_lifetimes_qualified": False,
                                      "combined_8192_preflight_qualified": False},
               "cleanup": {"disposable_scratch_created": False, "owned_pycache": bytecode,
                           "synchronous_children_reaped": True,
                           "layout_binaries": "Retained exact host value probes as immutable evidence",
                           "native_capture_target_or_unrelated_processes_started_or_queried": False},
               "passed": result.returncode == 0,
               "storedPrefixValidated": False, "fullReplayAccepted": False,
               "semantic_counters_valid": False}
    (run / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed": receipt["passed"], "additional_methods": 8,
                      "archive_members": [a["members"] for a in archives],
                      "upstream_members_unchanged": sum(r["members"] for r in before),
                      "source_tree_sha256": receipt["source_tree_sha256"]}, sort_keys=True))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
