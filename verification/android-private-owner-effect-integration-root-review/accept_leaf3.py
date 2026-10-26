"""Audit immutable leaf-only evidence before selecting bounded mechanical reuse."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def identity(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Nonregular input: {path}")
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


review_path = ROOT / "verification/android-private-owner-independent-review/leaf-review-1/manifest.json"
review_sha = "a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7"
require(identity(review_path)["sha256"] == review_sha, "Review manifest differs")
review = json.loads(review_path.read_bytes())
for name, expected in review["files"].items():
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path")
    require(identity(ROOT / relative) == expected, "Review member differs: " + name)
require(len(review["files"]) == review["members"] == 298, "Review count")
require(sum(row["bytes"] for row in review["files"].values()) == review["bytes"] == 918884, "Review bytes")
actual = {p.relative_to(ROOT).as_posix() for p in review_path.parent.rglob("*") if p.is_file()}
expected = set(review["files"]) - {review["external_owned_document"]}
expected |= {(review_path.parent / name).relative_to(ROOT).as_posix() for name in review["excluded_metadata"]}
require(actual == expected, "Review closure differs")
leaf_path = ROOT / "verification/android-private-owner-integration-implementation/leaf-candidate-3/manifest.json"
leaf_sha = "d772bfae9febf9106b1338be259cb026e4293d8e287fa792939340754ccdda38"
require(identity(leaf_path)["sha256"] == leaf_sha, "Leaf manifest differs")
leaf = json.loads(leaf_path.read_bytes())
for name, expected in leaf["files"].items():
    require(identity(leaf_path.parent / "inputs" / name) == expected, "Leaf member differs: " + name)
require(len(leaf["files"]) == 74 and sum(r["bytes"] for r in leaf["files"].values()) == 96805, "Leaf totals")
require(len(leaf["substituteFQCNs"]) == 73, "Substitute count")
receipt = json.loads(review_path.with_name("receipt.json").read_bytes())
require(receipt["leaf3"]["controls"] == 12 and receipt["leaf3"]["assertions"] == 82, "Leaf result")
require(not receipt["leaf3"]["remaining_leaf_only_blockers"], "Leaf blocker")
require(receipt["product_subjects_compiled_or_executed"] == 0 and not receipt["product_candidate_or_producer_tests_or_parent_evidence_access"], "Scope changed")
require(receipt["cleanup"]["all_owned_child_commands_reaped"] and receipt["cleanup"]["scratch_absent"], "Cleanup evidence")
outcome = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script_sha256": identity(Path(__file__))["sha256"],
    "status": "exact-leaf3-selected-for-bounded-mechanical-reuse",
    "review_manifest": review_path.relative_to(ROOT).as_posix(), "review_manifest_sha256": review_sha,
    "review_members": 298, "review_bytes": 918884,
    "leaf_manifest": leaf_path.relative_to(ROOT).as_posix(), "leaf_manifest_sha256": leaf_sha,
    "leaf_members": 74, "leaf_bytes": 96805, "substitute_FQCNs": 73,
    "controls": 12, "assertions": 82, "independent_custody_assertions": 404,
    "tool_scope": "OpenJDK 27 host with javac --release 17; no Java17 runtime or Android runtime evidence",
    "leaf2_runtime_failure_preserved": True, "mechanical_leaf_accepted": True,
    "limits": "Independent semantic-limits.json applies. Strong descriptor/BCI capability is not actual product-site coverage. Further leaf/probe deltas require separate review.",
    "pending": receipt["mandatory_remaining"][1:],
    "product_tests": 0, "implementation_accepted": False, "public_V2_selected": False,
    "native_runtime_or_capture_started": False, "GA_qualified": False,
}
destination = OUT / "leaf3-reuse-selection.json"
destination.write_text(json.dumps(outcome, indent=2) + "\n")
print(json.dumps({"path": destination.relative_to(ROOT).as_posix(), **identity(destination)}))
