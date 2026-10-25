"""Bind the completed independent runner review to the final local runtime run."""
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


review_dir = "verification/hosted-worker-controller-ci-review"
manifest_path = ROOT / review_dir / "review-manifest.json"
manifest = json.loads(manifest_path.read_text())
for item in manifest["files"]:
    path = ROOT / item["path"]
    assert path.is_file() and not path.is_symlink(), item["path"]
    assert path.stat().st_size == item["bytes"], item["path"]
    assert digest(path) == item["sha256"], item["path"]
snapshot = read(f"{review_dir}/final/snapshot.json")
for name, item in snapshot["manifest"].items():
    assert digest(ROOT / name) == item["sha256"], name
review = read(f"{review_dir}/receipt.json")
assert review["status"] == "reviewed-no-open-findings-for-final-source"
assert all(item["status"].startswith("resolved-") for item in review["findings"])
assert read(f"{review_dir}/cleanup-final.json")["allKnownToyPIDsAbsent"] is True
assert digest(ROOT / "hosted-worker-controller/test/check.mjs") == review["finalRunnerSHA256"]

binding = read("verification/hosted-worker-controller-v2-integration/check-4-binding.json")
run = read("verification/hosted-worker-controller-v2-integration/check-4/receipt.json")
assert run["status"] == "passed"
assert run["sourceDigest"] == review["verification"]["rootCheck4SourceDigest"]
assert digest(OUT / "check-4/receipt.json") == binding["receiptSHA256"]
assert binding["testGroupsPassed"] == {"original": 28, "regressions": 7, "focused": 36}
for command in run["commands"]:
    assert command["exitCode"] == 0 and not command["timedOut"]
    assert command["eofObserved"] and command["directChildTerminal"]
    assert command["processGroupEmpty"] and command["scratchRemoved"]
    assert not command["processManagementErrors"]
for name, expected in binding["compiledReviewedFilesMatched"].items():
    assert digest(ROOT / name) == expected, name
for item in read("verification/hosted-worker-controller-v2-integration/source-integration.json")["changedFiles"]:
    assert digest(ROOT / item["path"]) == item["afterSHA256"], item["path"]

files = [
    f"{review_dir}/review-manifest.json", f"{review_dir}/receipt.json",
    "verification/hosted-worker-controller-v2-root-review/independent-decision.json",
    "verification/hosted-worker-controller-v2-integration/source-integration.json",
    "verification/hosted-worker-controller-v2-integration/check-4-binding.json",
    "verification/hosted-worker-controller-v2-integration/check-4/receipt.json",
    "verification/hosted-worker-controller-v2-integration/accept.py",
]
result = {
    "schema": 1,
    "observedUTC": datetime.now(timezone.utc).isoformat(),
    "reviewer": "/root",
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python": platform.python_version(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "accepted-local-controller-integration-and-recurring-test-runner",
    "bindings": {name: digest(ROOT / name) for name in files},
    "reviewMembersVerified": len(manifest["files"]),
    "currentReviewedSourceFilesMatched": len(snapshot["manifest"]),
    "localGroupsPassed": 71,
    "compiledReviewedProductionFilesMatched": len(binding["compiledReviewedFilesMatched"]),
    "runnerFindingsResolved": len(review["findings"]),
    "ownedRunCleanupConfirmed": True,
    "scope": "macOS arm64 Node22.23.3 and local workerd/SQLite; separate frozen review records 72 producer and 17 independent groups",
    "linuxCI": "pending-push-and-terminal-result",
    "productionEnabled": False,
    "nativeAccepted": False,
    "gaAccepted": False,
}
(OUT / "acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
