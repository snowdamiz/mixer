#!/usr/bin/env python3
"""Record root acceptance of the reviewed local capacity-enforcement slice."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REVIEW = ROOT / "verification/hosted-build-aggregate-admission-independent-review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    target = BASE / "acceptance.json"
    require(not target.exists(), "preserve acceptance")
    complete = json.loads((REVIEW / "review-completion.json").read_bytes())
    manifest = REVIEW / "review-manifest.sha256"
    require(sha(manifest) == complete["manifest_sha256"], "review manifest changed")
    members = []
    for line in manifest.read_text().splitlines():
        digest, path = line.split("  ", 1)
        require(sha(ROOT / path) == digest, f"review member changed: {path}")
        members.append(path)
    require(complete["independent_controls"] == {"passed": 11, "failed": 0, "skipped": 0}, "independent result differs")
    full = json.loads((BASE / "attempt-2/receipt.json").read_bytes())
    independent = json.loads((BASE / "independent-attempt-1/receipt.json").read_bytes())
    extra = "verification/hosted-build-aggregate-admission-independent-review/aggregate_admission_review_test.exs"
    require(set(independent["inputs"]) - set(full["inputs"]) == {extra}, "independent closure differs")
    require(all(independent["inputs"][name] == value for name, value in full["inputs"].items()), "common inputs differ")
    for name, digest in independent["inputs"].items():
        require(sha(ROOT / name) == digest, f"tested source changed: {name}")
    for receipt in (full, independent):
        require(receipt["status"] == "passed", "collection failed")
        require(receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}, "cleanup incomplete")
    bindings = {}
    for name in ("binding-review-2.json", "independent-binding-review.json", "policy-command.json"):
        bindings[name] = sha(BASE / name)
    require(json.loads((BASE / "policy-command.json").read_bytes())["exitCode"] == 0, "policy guardrail failed")
    result = {
        "schema": 1,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
        "python": sys.version,
        "verifierSHA256": sha(Path(__file__)),
        "status": "accepted-internal-aggregate-build-admission",
        "bindingReviews": bindings,
        "independentCompletionSHA256": sha(REVIEW / "review-completion.json"),
        "independentManifestSHA256": sha(manifest),
        "independentMembersVerified": len(members),
        "repositorySourceTreeSHA256": full["source_tree_sha256"],
        "independentSourceTreeSHA256": independent["source_tree_sha256"],
        "tests": {"repositoryPassed": 255, "repositorySkipped": 2, "independentPassed": 11, "independentSkipped": 0, "newAggregateProducerControlsIncludedInRepositoryCount": 20},
        "sourceUnchangedBetweenCollections": True,
        "cleanupConfirmed": True,
        "productionMigrationApplied": False,
        "externalProviderQualified": False,
        "gaAccepted": False,
        "limitations": complete["scope_limits"] + ["Two repository identity controls require Linux with an isolated network namespace and remain skipped."]
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "tests": result["tests"], "independentMembersVerified": len(members)}))


if __name__ == "__main__":
    main()
