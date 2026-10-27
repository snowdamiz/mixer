#!/usr/bin/python3
"""Finalize this owned compiler/privacy subreview only; launch no children."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parents[1] / "swift-selected-profile-adoption"

def sha(b):
    return hashlib.sha256(b).hexdigest()

def write(p, value):
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

def ident(p):
    b = p.read_bytes()
    return {"path": str(p), "bytes": len(b), "sha256": sha(b)}

def tree(root):
    assert not any(p.is_symlink() for p in root.rglob("*"))
    members = [{"path": str(p.relative_to(root)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(root.rglob("*")) if p.is_file()]
    return {"member_count": len(members), "members": members, "tree_sha256": sha(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())}

def main():
    assert sha((CANDIDATE / "seal.json").read_bytes()) == "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad"
    selected = json.loads((CANDIDATE / "source-manifest.json").read_text())
    assert selected["tree_sha256"] == "22b6e945a062b3465156bb9995bce610bd712fa9d3e283e176316d75104bb442"
    copied = tree(HERE / "source/vm")
    assert copied["member_count"] == 144 and copied["members"] == selected["members"]
    assert copied["tree_sha256"] == selected["tree_sha256"]
    for member in selected["members"]:
        b = (CANDIDATE / "source/vm" / member["path"]).read_bytes()
        assert len(b) == member["bytes"] and sha(b) == member["sha256"]
    records = [json.loads(p.read_text()) for p in sorted((HERE / "commands").glob("*/receipt.json"))]
    assert len(records) == 120, len(records)
    assert all(r["expectation_met"] and r["terminally_waited"] and not r["supervisor_killed_for"] for r in records)
    for r in records:
        assert r["timeout_seconds"] <= 60
        for name in ("stdout", "stderr"):
            actual = ident(Path(r[name]["path"]))
            assert actual == r[name]
        history = HERE / "runner-history" / (r["runner"]["sha256"] + ".py")
        assert history.exists() and sha(history.read_bytes()) == r["runner"]["sha256"]
    negatives = [r for r in records if r["expected_diagnostic"] is not None]
    positives = [r for r in records if r["expected_diagnostic"] is None and "public-library" not in r["label"] and r["label"] != "rustc-version"]
    assert len(negatives) == 112 and len(positives) == 5
    scratch = HERE / "scratch"
    assert scratch.parent == HERE and scratch.name == "scratch" and not scratch.is_symlink()
    measurement = tree(scratch)
    write(HERE / "scratch-measured-before-removal.json", measurement)
    shutil.rmtree(scratch)
    cleanup = {"schema": 1, "all_120_recorded_direct_compiler_children_terminally_waited": True, "owned_scratch_removed_after_terminal_children": not scratch.exists(), "owned_variant_source_directories_removed": True, "retained_exact_source_copy_is_evidence_not_scratch": True, "native_simulator_emulator_UI_capture_or_process_inventory_used": False, "candidate_or_canonical_sources_or_git_modified": False, "other_projects_processes_or_files_touched": False}
    write(HERE / "cleanup.json", cleanup)
    write(HERE / "verified-source-manifest.json", copied)
    tools = json.loads((CANDIDATE / "build-input-manifest.json").read_text())["tools"]
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "bounded-independent-compiler-privacy-pass", "scope": "safe Rust API privacy and lifetime subreview under trusted launcher/compiler and quiescent local macOS host; no root or canonical acceptance", "candidate_seal_sha256": "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad", "selected_source_members": 144, "selected_source_tree_sha256": selected["tree_sha256"], "candidate_git_revision_context": json.loads((CANDIDATE / "build-input-manifest.json").read_text())["git_revision_context"], "candidate_git_revision_context_live_rechecked": False, "compiler": tools["rustc"], "compiler_version": records[0]["stdout"], "review_runner": ident(HERE / "replay.py"), "review_finalizer": ident(Path(__file__).resolve()), "review_python": ident(Path(sys.executable).resolve()), "review_python_version": sys.version, "compiler_children": 120, "compiler_controls": 117, "negative_controls": 112, "positive_controls": 5, "additional_library_metadata_builds": 2, "additional_compiler_version_commands": 1, "contexts": {"Debug production sibling": {"positive": 1, "negative": 35}, "optimized production sibling": {"positive": 1, "negative": 35}, "Debug test sibling": {"positive": 1, "negative": 34}, "Debug public separate crate": {"positive": 1, "negative": 4}, "optimized public separate crate": {"positive": 1, "negative": 4}}, "all_observed_expectations_met": True, "unexpected_compiler_failures": [], "first_diagnostic_tooling_failure": "preparation/source-inspection-first-failure.json", "candidate_or_frozen_runners_executed": False, "actionable_compiler_privacy_defects": [], "source_review": "source-review.json", "cleanup": cleanup, "unrun": ["optimized test-context controls; production controls replayed independently in both Debug and optimized", "admission/cache/accounting runtime replay is parent scope", "native/device/simulator/emulator/UI/capture/process inventory", "canonical/exporter/context/operational loader storage, FieldLog immutable published packages, OTA/store/customer/operations and GA"]}
    write(HERE / "receipt.json", receipt)
    files = [p for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "seal.json"]
    assert not any(p.is_symlink() for p in files)
    members = [{"path": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in files]
    write(HERE / "seal.json", {"schema": 1, "scope": "owned bounded independent compiler/privacy subreview only; no root/canonical/GA acceptance", "member_count": len(members), "member_bytes": sum(m["bytes"] for m in members), "members": members})
    print(json.dumps({"status": receipt["status"], "compiler_controls": 117, "compiler_children": 120, "negative_controls": 112, "positive_controls": 5, "member_count": len(members), "seal_sha256": sha((HERE / "seal.json").read_bytes()), "scratch_removed": not scratch.exists()}, sort_keys=True))

if __name__ == "__main__":
    main()
