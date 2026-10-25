#!/usr/bin/env python3
"""Read-only prepared packet check; never compiles or executes a guest."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSURE = "02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d"
HARNESS = "d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00"


def sha(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def strict(text):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def raw_events(path):
    result = []
    for line in Path(path).read_text().splitlines():
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            result.append(strict(line[at + len("MIXER_EXACT "):]))
    return result


def main():
    assert not (HERE / "target-attempt-started.json").exists(), "preparation verifier only"
    assert not (HERE / "commands/target-once").exists()
    seal = read(HERE / "prepared-seal.json")
    files = {str(p.relative_to(HERE)) for p in HERE.rglob("*")
             if p.is_file() and "owned-scratch" not in p.relative_to(HERE).parts
             and p.name not in ("prepared-seal.json", "root-selection.json")}
    assert files == set(seal["files"]), "prepared inventory changed"
    for name, expected in seal["files"].items():
        assert sha(HERE / name) == expected, name
    for name, expected in seal["externalFiles"].items():
        assert sha(ROOT / name) == expected, name
    baseline = read(HERE / "baseline-manifest.json")
    assert len(baseline) == 132 and sha(HERE / "baseline-manifest.json") == CLOSURE
    for name, expected in baseline.items():
        assert sha(ROOT / "vm" / name) == expected, name
        assert sha(HERE / "baseline" / name) == expected, name
    copied = read(HERE / "copied-build-manifest.json")
    assert [name for name in baseline if baseline[name] != copied[name]] == [
        "src/experimental_swift_reactor/lifecycle_tests.rs"]
    for name, expected in copied.items():
        assert sha(HERE / "owned-scratch/vm" / name) == expected, name
    append = '\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!(' + json.dumps(str(HERE / "harness.rs")) + ');\n'
    test = "src/experimental_swift_reactor/lifecycle_tests.rs"
    assert (HERE / "owned-scratch/vm" / test).read_bytes() == (HERE / "baseline" / test).read_bytes() + append.encode()
    assert sha(HERE / "harness.rs") == HARNESS
    binding = read(HERE / "binding.json")
    assert binding["baselineClosure"] == CLOSURE
    for info in binding["inputs"]:
        assert sha(info["path"]) == info["sha256"], info["path"]
    target = binding["target"]
    assert target["bytes"] == Path(target["path"]).stat().st_size == 53_777_114
    assert sha(target["path"]) == target["sha256"] == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    binary = read(HERE / "binary.json")
    assert sha(HERE / "bin/exact-tests") == binary["retained"]["sha256"]
    proposal = read(HERE / "prepared-selection.json")
    assert proposal["status"] == "prepared-awaiting-root-exact-selection"
    assert proposal["targetAttempted"] is False and proposal["maxTargetAttempts"] == 1
    assert proposal["baselineClosure"] == CLOSURE
    assert proposal["harnessSHA256"] == HARNESS and proposal["driverSHA256"] == sha(HERE / "diagnostic.py")
    assert proposal["binarySHA256"] == binary["retained"]["sha256"]
    assert proposal["inputBindingSHA256"] == sha(HERE / "binding.json")
    for name, expected in proposal["boundEvidence"].items():
        assert sha(HERE / name) == expected, name
    commands = []
    for path in sorted((HERE / "commands").glob("*/receipt.json")):
        command = read(path)
        assert command["passed"] and command["exitCode"] == 0 and not command["timedOut"]
        assert command["processGroupEmpty"] and command["finalGroupObservation"]["state"] == "absent"
        assert command["signalSent"] == [] and command["rawStreamEOFConfirmed"]
        for field in ("sourceUnchanged", "toolsUnchanged", "allBoundInputsUnchanged", "harnessUnchanged", "driverUnchanged", "argvFilesUnchanged"):
            assert command[field], (path, field)
        for stream in ("stdout", "stderr"):
            assert sha(path.parent / stream) == command[stream]["sha256"]
        assert sha(path.parent / "harness.rs") == command["harnessSHA256"]
        assert sha(path.parent / "diagnostic.py") == command["driverSHA256"]
        for info in command["argvFileIdentities"]:
            assert sha(info["path"]) == info["sha256"], info["path"]
        commands.append(path.parent.name)
    assert commands == ["build-001", "control-001", "control-002", "driver-observation-controls", "list-001"]
    for name in ("control-001", "control-002"):
        events = read(HERE / (name + "-events.json"))
        assert events == raw_events(HERE / "commands" / name / "stdout")
        result = read(HERE / (name + "-result.json"))
        assert result["commandPassed"] and result["diagnosticCompleted"] and result["ownedCleanupEmpty"]
        assert result["targetAttempted"] is False
    stderr = (HERE / "commands/driver-observation-controls/stderr").read_text()
    assert "Ran 10 tests" in stderr and stderr.rstrip().endswith("OK")
    print(json.dumps({"preparedIntegrityVerified": True, "retainedMembers": len(files),
        "sourceFiles": 132, "sourceManifestSHA256": CLOSURE, "commands": commands,
        "wiringControlsPassed": 2, "hostProcessObservationControlsPassed": 10,
        "targetAttempted": False, "rootSelectionRequired": True, "gaAccepted": False}))


if __name__ == "__main__":
    main()
