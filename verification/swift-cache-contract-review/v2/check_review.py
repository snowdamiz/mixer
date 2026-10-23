#!/usr/bin/env python3
"""Independently check refined contract artifacts without running engine collectors."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTRACT = ROOT / "verification/swift-cache-stage-contract"
ENV = dict(os.environ)
ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV.get("PATH", "")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    files = [ROOT / "AGENTS.md", ROOT / "mixer-product-plan.md",
             ROOT / "docs/swift-reactor-execution-stage-design.md",
             ROOT / "docs/swift-cache-stage-contract.md",
             HERE.parent / "review.md", HERE.parent / "receipt.json", Path(__file__)]
    files.extend(path for path in CONTRACT.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return {str(path.relative_to(ROOT)): digest(path) for path in sorted(files)}


def command(argv):
    result = subprocess.run(argv, cwd=ROOT, env=ENV, text=True, capture_output=True)
    return {"argv": argv, "resolved_executable": shutil.which(argv[0], path=ENV["PATH"]),
            "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main():
    before = inventory()
    original = json.loads((HERE.parent / "receipt.json").read_text())
    archive = json.loads((CONTRACT / "historical-v1/archive-manifest.json").read_text())
    history = []
    for original_path, entry in archive["files"].items():
        actual = digest(ROOT / entry["archived_path"])
        expected = original["source_before"][original_path]
        history.append({"original": original_path, "archived": entry["archived_path"],
                        "actual_sha256": actual, "original_independent_review_sha256": expected,
                        "archive_manifest_sha256": entry["sha256"],
                        "matches_original_independent_review": actual == expected == entry["sha256"]})
    proposal = json.loads((CONTRACT / "proposal-receipt.json").read_text())
    bindings = [{"path": path, "observed_sha256": digest(ROOT / path), "receipt_sha256": sha,
                 "matches": digest(ROOT / path) == sha}
                for path, sha in proposal["contract_artifact_sha256"].items()]
    commands = [["python3", "--version"], ["rustc", "-Vv"], ["cargo", "-V"],
                ["python3", "-B", "verification/swift-cache-stage-contract/check_contract.py"],
                ["python3", "-B", "-O", "verification/swift-cache-stage-contract/check_contract.py"],
                ["python3", "-B", "verification/swift-cache-stage-contract/artifact_checks.py", "-v"],
                ["python3", "-B", "-O", "verification/swift-cache-stage-contract/artifact_checks.py", "-v"]]
    receipt = {
        "schema": "mixer-swift-cache-contract-independent-review-v2",
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "decision": "bounded_contract_acceptance_pending_prerequisite_and_implementation_layout_evidence",
        "remaining_concrete_contract_blockers": [],
        "scope": "Independent refined-contract ownership/accounting/ordering review and artifact-only checks",
        "revision": command(["git", "rev-parse", "HEAD"]),
        "dirty_state": command(["git", "status", "--short"]),
        "source_before": before,
        "source_manifest_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        "historical_v1_compared_against_original_independent_review": history,
        "current_proposal_receipt_artifact_bindings": bindings,
        "commands": [command(argv) for argv in commands],
        "cache_engine_acceptance_tests_executed": 0,
        "producer_seal_collectors_executed": False,
        "target_instantiated": False, "device_discovery_or_runs": False,
        "product_or_proposal_modified": False, "commits_pushes_publication": False,
        "limitations": ["Contract acceptance does not accept code prerequisites or a nonexistent whole-cache implementation.",
                        "Actual cleanup and final-tail layouts, simultaneous object counts and foundation mapping remain mandatory implementation evidence.",
                        "All 18 named cache tests, regression suites, bounded target runner, devices, published consumer and GA gates remain pending."],
    }
    receipt["source_after"] = inventory()
    receipt["reviewed_sources_stable"] = before == receipt["source_after"]
    receipt["artifact_checks_passed"] = (all(c["exit_code"] == 0 for c in receipt["commands"])
                                         and all(h["matches_original_independent_review"] for h in history)
                                         and all(b["matches"] for b in bindings)
                                         and receipt["reviewed_sources_stable"])
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("decision", "remaining_concrete_contract_blockers",
                                                   "artifact_checks_passed", "reviewed_sources_stable",
                                                   "cache_engine_acceptance_tests_executed")}, indent=2))
    return 0 if receipt["artifact_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
