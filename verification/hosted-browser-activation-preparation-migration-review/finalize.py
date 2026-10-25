#!/usr/bin/env python3
"""Verify retained review packets and seal the completed bounded review."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / "docs/hosted-browser-activation-preparation-migration-review.md"
ACCEPTED = "attempts/20261025T191835.833795Z-706578d4/receipt.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


spec = importlib.util.spec_from_file_location("migration_review_runner", BASE / "run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
checks = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "command": ["python3", str(Path(__file__).resolve())],
          "frozen_producer": runner.verify_frozen(), "attempts": [], "commands": []}
for path in sorted((BASE / "attempts").glob("*/receipt.json")):
    receipt = json.loads(path.read_text())
    mismatches = [rel for rel, value in receipt["outputs_sha256"].items() if sha(path.parent / rel) != value]
    assert not mismatches, (path, mismatches)
    assert all(receipt["cleanup"].values()), path
    checks["attempts"].append({"receipt": str(path.relative_to(BASE)), "sha256": sha(path),
                               "accepted": path == BASE / ACCEPTED,
                               "success": receipt["success"], "output_mismatches": mismatches,
                               "cleanup": receipt["cleanup"]})
accepted = json.loads((BASE / ACCEPTED).read_text())
assert accepted["success"]
assert accepted["suites"]["selected-ten-migrations"]["counts"] == {"total": 1, "failures": 0, "skipped": 0, "excluded": 0}
assert accepted["suites"]["independent-adversity"]["counts"] == {"total": 11, "failures": 0, "skipped": 0, "excluded": 0}
assert all(sha(ROOT / rel) == value for rel, value in accepted["sources_sha256"].items())
dependencies = json.loads((BASE / ACCEPTED).with_name("dependency-beams.json").read_text())
assert all(sha(ROOT / rel) == value for rel, value in dependencies.items())
for name in ["selected-compile", "actual-mix-format", "selected-ten-migrations", "independent-adversity"]:
    assert not (BASE / ACCEPTED).with_name(name + ".stderr").read_bytes()
for path in [DOC, BASE / "review.exs", BASE / "run.py", BASE / "finalize.py"]:
    command = ["git", "diff", "--no-index", "--check", "/dev/null", str(path)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True)
    checks["commands"].append({"argv": command, "exit_code": result.returncode,
                               "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})
    # With --no-index, status 1 denotes the expected new-file difference.
    assert result.returncode in (0, 1) and not result.stdout and not result.stderr
for path in [BASE / "run.py", BASE / "finalize.py"]:
    compile(path.read_text(), str(path), "exec")
checks.update(success=True, source_and_dependency_hashes_stable=True,
              all_attempt_outputs_verified=True, no_product_edits=True,
              no_native_capture_or_production_execution=True)
save(BASE / "final-checks.json", checks)
members = {str(path.relative_to(BASE)): sha(path) for path in sorted(BASE.rglob("*"))
           if path.is_file() and path.name not in {"seal.json", "seal.sha256", "handoff.json", "handoff.sha256"}}
assert not list(BASE.rglob("__pycache__")), "Do not leave own Python cache products"
save(BASE / "seal.json", {"schema": 1, "at": checks["at"], "members_sha256": members,
                          "review_doc": {"path": str(DOC.relative_to(ROOT)), "sha256": sha(DOC)},
                          "scope": "All retained attempts including failures, copied sources, raw outputs, SQL observations, source review, final checks and review scripts; handoff/seal self references excluded."})
(BASE / "seal.sha256").write_text(sha(BASE / "seal.json") + "  seal.json\n")
save(BASE / "handoff.json", {"schema": 1, "at": checks["at"], "status": "independent-development-review-passed",
                             "finding": "No blocking product finding observed within this bounded review.",
                             "source_revision": accepted["source_revision"],
                             "source_tree_sha256": accepted["source_tree_sha256"],
                             "dependency_manifest_sha256": accepted["dependency_manifest_sha256"],
                             "accepted_receipt": ACCEPTED, "accepted_receipt_sha256": sha(BASE / ACCEPTED),
                             "suites": accepted["suites"], "do_not_sum_suites": True,
                             "producer_frozen": checks["frozen_producer"],
                             "seal_sha256": sha(BASE / "seal.json"), "sealed_members": len(members),
                             "review_doc_sha256": sha(DOC), "retained_failed_attempts": 3,
                             "cleanup": accepted["cleanup"],
                             "doc_link_resolution": "Producer doc/seal remain immutable. Current review directly links selected d888cda9; older linked b5b7c1ed binds identical product/test bytes and the same six controls. Only their doc snapshots differ.",
                             "pending": accepted["pending"], "commits_or_pushes": False,
                             "native_capture_or_production_execution": False})
(BASE / "handoff.sha256").write_text(sha(BASE / "handoff.json") + "  handoff.json\n")
print(json.dumps({"handoff_sha256": sha(BASE / "handoff.json"), "seal_sha256": sha(BASE / "seal.json"), "members": len(members), "accepted_receipt_sha256": sha(BASE / ACCEPTED), "success": True}))
