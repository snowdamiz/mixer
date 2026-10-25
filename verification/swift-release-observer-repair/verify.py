#!/usr/bin/env python3
"""Read-only observer repair evidence check; never compiles or executes guests."""
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    seal = read(HERE / "seal.json")
    for name, expected in seal["files"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in seal["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    receipt = read(HERE / "receipt.json")
    assert receipt["passed"] and receipt["baselinePanicReproduced"]
    assert receipt["liveVMUnchanged"] and receipt["toolsUnchanged"]
    assert receipt["cleanup"]["removed"] and not (HERE / "owned-scratch").exists()
    assert receipt["fullReactorReadOrRun"] is False and receipt["GAaccepted"] is False
    baseline = read(HERE / "baseline-manifest.json")
    candidate = read(HERE / "candidate-manifest.json")
    test = "src/experimental_swift_reactor/frame_operations_tests.rs"
    assert len(baseline) == 132 and [k for k in baseline if baseline[k] != candidate[k]] == [test]
    for name, expected in baseline.items():
        assert sha(HERE / "baseline" / name) == expected
    original = (HERE / "baseline" / test).read_bytes()
    actual = (HERE / "candidate" / test).read_bytes()
    regression = (HERE / "regressions.rs").read_bytes()
    guard = b"        if hooks.release_mask == 0 {\n            return false;\n        }\n"
    assert actual.endswith(regression)
    changed = actual[:-len(regression)]
    assert changed.count(guard) == 1 and changed.replace(guard, b"", 1) == original
    assert sha(HERE / "candidate" / test) == candidate[test]
    assert read(HERE / "final-source-manifest.json") == candidate
    commands = []
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        entry = read(path)
        assert entry["passedExpectedOutcome"] and entry["groupEmpty"]
        assert entry["sourcesUnchanged"] and entry["toolsUnchanged"]
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / stream) == entry[stream + "SHA256"]
        assert sha(path.parent / "run.py") == entry["recorderSHA256"]
        manifest = read(path.parent / "source-manifest.json")
        for name in (test, "src/experimental_swift_reactor/frame_operations.rs"):
            assert sha(path.parent / name) == manifest[name]
        commands.append(path.parent.name)
    assert len(commands) == receipt["commandCount"]
    assert receipt["productionCfgNegativeChecks"] == 4
    for directory in (HERE / "commands").glob("*-cfg-negative"):
        assert re.findall(r"error\[(E\d+)\]", (directory / "stderr").read_text()) == ["E0433"]
    serial = read(HERE / "serial-attempt/classification.json")
    assert serial["exactCommandTerminalReceiptMissing"] and serial["actualDirectChildExitCode"] is None
    assert serial["processGroupState"] == "absent"
    assert sha(HERE / "serial-attempt/receipt.json") == serial["originalFailureReceiptSHA256"]
    assert sha(HERE / "serial-attempt/run.py") == serial["originalRunScriptSHA256"]
    configs = receipt["normalConfigurations"]
    assert len(configs) == 4 and all(row["identities"] == row["passed"] and row["ignored"] == 0 for row in configs)
    assert sum(row["passed"] for row in configs) == receipt["normalIdentityExecutions"]
    for info in (HERE / "binaries").glob("*.json"):
        value = read(info)
        assert sha(HERE / value["retained"]) == value["gzipSHA256"]
        with gzip.open(HERE / value["retained"], "rb") as stream:
            assert hashlib.sha256(stream.read()).hexdigest() == value["sha256"]
    print(json.dumps({"integrityVerified": True, "commands": len(commands),
        "candidateClosure": receipt["candidateClosure"],
        "normalIdentityExecutions": receipt["normalIdentityExecutions"],
        "productionCfgNegativeChecks": 4, "ownedScratchRemoved": True,
        "liveVMChanged": False, "fullReactorReadOrRun": False, "GAaccepted": False}))


if __name__ == "__main__":
    main()
