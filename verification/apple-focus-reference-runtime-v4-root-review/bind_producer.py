"""Bind the V4 packet as data without importing or executing its code."""
from pathlib import Path
import datetime
import hashlib
import json
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PACKET = ROOT / "verification/apple-focus-reference-runtime-v4"
EXPECTED = "79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, row):
    path = ROOT / name
    assert ".." not in Path(name).parts
    assert row["kind"] == "file" and path.is_file() and not path.is_symlink(), name
    assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    assert stat.S_IMODE(path.stat().st_mode) == row["mode"], name


def main():
    target = BASE / "producer-binding.json"
    assert not target.exists(), "preserve existing observation"
    handoff = PACKET / "handoff.json"
    assert digest(handoff) == EXPECTED
    data = json.loads(handoff.read_bytes())
    for name, row in data["members"].items():
        assert not Path(name).is_absolute(), name
        check(name, row)
    frozen = json.loads((PACKET / "derivation-inputs.json").read_bytes())
    for name, row in frozen.items():
        check(name, row)
    assert digest(PACKET / "packet.json") == "4622a27a5e4c9dc9651b3eee6022e850dab1f55db3b48ac8f0daa4921b80e77a"
    assert digest(PACKET / "host-attempt-2/receipt.json") == "771d70983473916cc8004d2c3a4893b2ce82bfc0e0a992ce657cd853fa5e35c3"
    assert data["nativeExecuted"] is False and data["runtimeSelected"] is False
    assert data["gaAccepted"] is False and data["independentV4ReviewPending"] is True
    result = {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "verifierSHA256": digest(Path(__file__)), "handoffSHA256": EXPECTED,
        "status": "producer-bindings-verified-independent-review-pending",
        "verifiedMembers": len(data["members"]), "verifiedFrozenInputs": len(frozen),
        "producerReportedResults": {key: data[key] for key in [
            "retainedProducerControls", "focusedRepairControls", "historicalIndependentControls",
            "v3ReviewerReplay", "newExactTimestampControls", "frozenV3ActualAdapterPrecisionReplay"]},
        "nativeSelected": False, "gaAccepted": False,
        "reviewedCodeImportedOrExecuted": False,
        "cleanup": "Data-only verification; no native, compiler, service or scratch created.",
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "verifiedMembers", "verifiedFrozenInputs"]}))


if __name__ == "__main__":
    main()
