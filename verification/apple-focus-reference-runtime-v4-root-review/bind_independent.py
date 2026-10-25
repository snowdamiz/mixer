"""Verify the frozen independent V4 rejection without executing reviewed code."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
REVIEW = ROOT / "verification/apple-focus-reference-runtime-v4-independent-review"
EXPECTED = "93c6505ba122b532aafe3fdcd65a3a09273d046fafc37d633b9ec860dd503233"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = BASE / "independent-decision.json"
    assert not target.exists(), "preserve existing decision"
    assert digest(REVIEW / "handoff.json") == EXPECTED
    review = json.loads((REVIEW / "handoff.json").read_bytes())
    for name, row in review["members"].items():
        path = ROOT / name
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert row["kind"] == "file" and path.is_file() and not path.is_symlink()
        assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    assert review["reviewAccepted"] is False and review["nativeExecuted"] is False
    assert review["dispatchAuthorized"] is False and review["gaAccepted"] is False
    assert review["producerHandoffSHA256"] == "79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07"
    assert review["independentControls"]["run"] == 36
    assert review["independentControls"]["failed"] == 6
    result = {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "verifierSHA256": digest(Path(__file__)), "handoffSHA256": EXPECTED,
        "status": "reject-v4-native-dispatch-four-reproduced-findings",
        "verifiedMembers": len(review["members"]),
        "findings": review["findings"], "independentControls": review["independentControls"],
        "closedReplay": review["exactClosureReplay"],
        "supplementalReplay": review["supplementalReplay"],
        "supplementalHistoricalInputFiles": review["supplementalHistoricalInputFiles"],
        "supplementalWasBoundByProducer": review["supplementalWasBoundByProducer"],
        "cleanup": review["cleanup"], "nativeSelected": False, "gaAccepted": False,
        "rootImportedOrExecutedReviewedCode": False,
        "nextImplementation": "Separate V5 repair: exactly representable canonical root wall time, complete closed historical fixture inputs, ambient Decimal isolation and current schema for incomplete reports. Replay independently before fresh root native selection.",
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "verifiedMembers", "independentControls"]}))


if __name__ == "__main__":
    main()
