#!/usr/bin/env python3
"""Read-only independent packet integrity check; no compiler or guest execution."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    seal = read(HERE / "seal.json")
    for name, expected in seal["files"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in seal["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    assert not (HERE / "owned-scratch").exists()
    cleanup = read(HERE / "cleanup.json")
    assert cleanup["removed"] and cleanup["holderExitCode"] == 1
    baseline = read(HERE / "baseline-manifest.json")
    assert len(baseline) == 132
    for name, expected in baseline.items():
        assert sha(HERE / "baseline" / name) == expected
    digest = hashlib.sha256((json.dumps(baseline, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
    assert digest == "6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8"
    binary = read(HERE / "binary.json")
    with gzip.open(HERE / "bin/exact-tests.gz", "rb") as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == binary["retained"]["sha256"]
    assert sha(HERE / "harness.rs") == binary["harnessSHA256"]
    selected = read(HERE / "root-selection.json")
    assert selected["exactCommandSelected"] and selected["baselineClosure"] == digest
    assert selected["binarySHA256"] == binary["retained"]["sha256"]
    assert selected["harnessSHA256"] == sha(HERE / "harness.rs")
    assert selected["driverSHA256"] == sha(HERE / "diagnostic.py")
    commands = []
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        receipt = read(path)
        assert receipt["processGroupEmpty"] and receipt["sourceUnchanged"] and receipt["toolsUnchanged"]
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / stream) == receipt[stream]["sha256"]
        assert sha(path.parent / "harness.rs") == receipt["harnessSHA256"]
        assert sha(path.parent / "diagnostic.py") == receipt["driverSHA256"]
        assert receipt["exitCode"] is not None
        if path.parent.name != "target-once":
            assert receipt["passed"]
        commands.append(path.parent.name)
    attempt = read(HERE / "commands/target-once/receipt.json")
    assert attempt["argv"] == selected["argv"] and attempt["timeoutSeconds"] == 170
    result = read(HERE / "target-once-result.json")
    events = read(HERE / "target-once-events.json")
    assert result["commandPassed"] == attempt["passed"]
    assert result["targetAttempted"] is True and result["GAaccepted"] is False
    assert result["nativeSignedPublicAccepted"] is False
    assert result["productionAccountingAccepted"] is False
    raw = (HERE / "commands/target-once/stdout").read_text()
    reconstructed = []
    for line in raw.splitlines():
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            reconstructed.append(json.loads(line[at + len("MIXER_EXACT "):]))
    assert reconstructed == events
    failures = [event for event in events if event["event"] in (
        "validation_failure", "adoption_failure", "construction_failure", "runtime_failure",
        "guest_output_failure", "phase_failed")]
    assert result["firstFailure"] == (failures[0] if failures else None)
    classification = read(HERE / "target-once-classification.json")
    assert classification["originalResultSHA256"] == sha(HERE / "target-once-result.json")
    assert classification["rawStderrSHA256"] == sha(HERE / "commands/target-once/stderr")
    assert classification["actualTypedVMFailure"] is None
    assert classification["consumingOwnedCleanupObserved"] is False
    assert classification["corpusCallsAttempted"] == 0
    assert "assertion failed: ordinal < 64" in (HERE / "commands/target-once/stderr").read_text()
    assert result["phasesBegun"] == ["validation", "initialize"]
    for event in events:
        payload = event["payload"]
        if isinstance(payload, dict) and "stdout_hex" in payload:
            for stream in ("stdout", "stderr"):
                encoded = bytes.fromhex(payload[stream + "_hex"])
                try:
                    text = encoded.decode("utf-8", errors="strict")
                except UnicodeDecodeError:
                    text = None
                assert payload[stream] == text
    print(json.dumps({"integrityVerified": True, "commands": commands,
        "targetCommandPassed": result["commandPassed"], "nativeParity": result["nativeParity"],
        "firstFailure": result["firstFailure"], "ownedScratchRemoved": cleanup["removed"],
        "GAaccepted": False}))


if __name__ == "__main__":
    main()
