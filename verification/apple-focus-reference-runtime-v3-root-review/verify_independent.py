#!/usr/bin/env python3
"""Bind frozen independent review as data; no importer or native execution."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
REVIEW = ROOT / "verification/apple-focus-reference-runtime-v3-independent-review"

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    target = BASE / "independent-decision.json"
    assert not target.exists(), "preserve previous decision"
    source = REVIEW / "handoff.json"
    expected = "70f56f2e9495cf6ca18c0298fdf83300849b484298b62830a4facf744c6eebe1"
    assert digest(source) == expected
    review = json.loads(source.read_bytes())
    for name, row in review["members"].items():
        path = ROOT / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert row["kind"] == "file" and path.is_file() and not path.is_symlink()
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    assert review["accepted"] is False and review["nativeExecuted"] is False and review["gaAccepted"] is False
    result = {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))], "python": sys.version,
        "verifierSHA256": digest(Path(__file__)), "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "status": "reject-v3-native-dispatch-exact-timestamp-repair-required", "handoffSHA256": expected,
        "verifiedMembers": len(review["members"]), "frozenInputCount": review["frozenInputCount"],
        "producerControls": review["producerControls"], "repairControls": review["repairControls"],
        "historicalControls": review["historicalControls"], "independentControls": review["independentControls"],
        "findings": review["findings"], "nativeSelected": False, "gaAccepted": False,
        "rootImportedOrExecutedReviewedCode": False, "nextImplementation": "Separate V4 exact arithmetic repair, then independent host review before any fresh native selection."}
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "verifiedMembers", "frozenInputCount", "independentControls"]}))

if __name__ == "__main__":
    main()
