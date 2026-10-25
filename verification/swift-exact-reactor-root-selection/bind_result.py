"""Bind the one completed diagnostic without rerunning the target."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/swift-exact-reactor-diagnostic"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


assert sha(PACKET / "seal.json") == "5ffef712aa63ab727e68659bfbd3e6509ab920994c122b19093a2f61247e4a53"
seal = read(PACKET / "seal.json")
for name, expected in seal["files"].items():
    assert sha(PACKET / name) == expected, name
for name, expected in seal["externalFiles"].items():
    assert sha(ROOT / name) == expected, name
result = read(PACKET / "target-once-result.json")
command = read(PACKET / "commands/target-once/receipt.json")
classification = read(PACKET / "target-once-classification.json")
assert command["exitCode"] == 101 and command["processGroupEmpty"] and not command["timedOut"]
assert result["firstFailure"] is None and not result["diagnosticCompleted"] and not result["ownedCleanupEmpty"]
assert classification["ownedValidationPassed"] and classification["originalOwnerConstructed"]
assert not classification["initializerCompleted"] and classification["corpusCallsAttempted"] == 0
stderr = (PACKET / "commands/target-once/stderr").read_text()
assert "frame_operations_tests.rs:107:9" in stderr and "assertion failed: ordinal < 64" in stderr
assert sha(PACKET / "commands/target-once/stderr") == classification["rawStderrSHA256"]
assert sha(PACKET / "target-once-result.json") == classification["originalResultSHA256"]
assert not (PACKET / "owned-scratch").exists()
output = HERE / "result-binding.json"
assert not output.exists()
record = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "verifierSHA256": sha(Path(__file__)), "sealSHA256": sha(PACKET / "seal.json"),
    "verifiedInternalFiles": len(seal["files"]), "verifiedExternalFiles": len(seal["externalFiles"]),
    "classification": classification["status"], "rawExitCode": command["exitCode"],
    "fullModuleValidationPassed": True, "originalOwnerConstructionPassed": True,
    "initializerCompleted": False, "corpusCallsAttempted": 0,
    "typedVMFailureObserved": False, "ownedCleanupObserved": False,
    "processGroupEmpty": True, "ownedScratchRemoved": True,
    "nextAction": "Repair only the default test release observer, reproduce with original owners, preserve selected fault tests and production bytes, then separately select another diagnostic.",
    "fullReactorAccepted": False, "nativePublicSignedAccepted": False, "gaAccepted": False,
}
output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
