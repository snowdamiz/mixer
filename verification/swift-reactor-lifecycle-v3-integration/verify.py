#!/usr/bin/env python3
"""Read-only replay of exact live integration and bounded host observations."""
from pathlib import Path
import gzip
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / "verification/swift-reactor-lifecycle-runtime-v3"
CLOSURE = "93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38"
ACCEPTANCE_SHA = "4ab6960d7e0bf99d94db569bc8d29a7a62bab53a9f3bd8d9fcef6c8799222c2e"
FINAL_SEAL_SHA = "027d3895f69f3f6c92638c44e7304fa2f65e34075f564e388c8751e3ea133d27"


def enc(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def manifest(tree):
    return {
        str(path.relative_to(tree)): digest(path)
        for name in ["Cargo.lock", "Cargo.toml", "include", "src", "tests"]
        for path in ([tree / name] if (tree / name).is_file() else sorted((tree / name).rglob("*")))
        if path.is_file()
    }


def verify():
    seal = read(HERE / "seal.json")
    for name, expected in seal["files"].items():
        assert digest(HERE / name) == expected, name
    assert sha(enc(seal["files"])) == seal["packetClosureSHA256"]
    assert digest(ROOT / seal["document"]["path"]) == seal["document"]["sha256"]
    assert digest(HERE / "root-runtime-acceptance.json") == ACCEPTANCE_SHA
    assert digest(ROOT / "verification/swift-reactor-lifecycle-runtime-v3-root-review/runtime-acceptance.json") == ACCEPTANCE_SHA
    acceptance = read(HERE / "root-runtime-acceptance.json")
    assert acceptance["candidateClosure"] == CLOSURE and acceptance["liveIntegrationSelected"] and acceptance["selectedRuntimeSubsetAccepted"]
    assert digest(HERE / "retained-runtime-final-seal.json") == FINAL_SEAL_SHA
    assert digest(PRIOR / "runtime-final-seal.json") == FINAL_SEAL_SHA
    retained_seal = read(HERE / "retained-runtime-final-seal.json")
    for name, expected in retained_seal["files"].items():
        assert digest(PRIOR / name) == expected, name
    assert len(retained_seal["files"]) == 978
    assert sha(enc(retained_seal["files"])) == retained_seal["closureSHA256"]
    candidate = read(HERE / "candidate-manifest.json")
    assert candidate == read(PRIOR / "candidate-manifest.json") == manifest(PRIOR / "candidate")
    assert sha(enc(candidate)) == CLOSURE and len(candidate) == 132
    assert candidate == manifest(ROOT / "vm")
    for name in ["live-after-manifest.json", "live-final-manifest.json"]:
        assert read(HERE / name) == candidate
    before = dict(candidate)
    for row in acceptance["exactSelectedChanges"]:
        relative = row["path"].removeprefix("vm/")
        assert candidate[relative] == row["afterSHA256"]
        assert digest(ROOT / row["source"]) == row["afterSHA256"]
        if row["beforeSHA256"] is None:
            del before[relative]
        else:
            before[relative] = row["beforeSHA256"]
    assert before == read(HERE / "live-before-manifest.json")
    integration = read(HERE / "integration.json")
    assert integration["exactSelectedChanges"] == acceptance["exactSelectedChanges"]
    assert integration["candidateClosure"] == CLOSURE and integration["scopeFiles"] == 132
    assert integration["liveScopeEqualsCandidate"] and integration["allUnselectedScopeBytesUnchanged"]
    assert integration["gitMutated"] is False and integration["publicAPIChanged"] is False
    retained = read(HERE / "retained-evidence.json")
    assert retained["observedTotals"] == acceptance["observedTotals"]
    assert retained["priorMatrixReexecuted"] is False and retained["verifiedFinalPins"] == 978
    scratch = read(HERE / "owned-scratch.json")
    expected_compiler = read(PRIOR / "runtime-attempts/focused-swift-debug/build-tools.json")["compiler"]
    artifact = read(HERE / "focused-artifact.json")
    executable = artifact["originalPath"]
    raw = gzip.decompress((HERE / artifact["path"]).read_bytes())
    assert sha(raw) == artifact["sha256"] and len(raw) == artifact["bytes"]
    cargo_artifact = read(HERE / "cargo-artifact.json")
    assert cargo_artifact["executable"] == executable and not cargo_artifact["fresh"]
    assert Path(executable).is_relative_to(Path(scratch["path"]) / "target")
    expected_commands = {
        "focused-build": ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib", "--features", "experimental-swift-reactor", "--no-run", "--message-format=json-render-diagnostics"],
        "focused-list": [executable, "swift_lifecycle_", "--list"],
        "focused-execute": [executable, "swift_lifecycle_", "--nocapture", "--test-threads=1"],
        "swift-clippy": ["cargo", "clippy", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib", "--features", "experimental-swift-reactor", "--", "-D", "warnings"],
    }
    logs = {}
    commands = {}
    for name, argv in expected_commands.items():
        path = HERE / (name + ".json")
        if not path.exists():
            continue
        row = read(path)
        commands[name] = row
        assert row["argv"] == argv and row["cwd"] == str(ROOT)
        assert row["environment"] == scratch["environment"]
        assert row["sourceClosure"] == row["sourceBeforeSHA256"] == CLOSURE
        assert row["sourceUnchanged"] and not row["remainingGroup"] and row["launched"]
        for suffix in ["-tools.json", "-post-tools.json"]:
            tools = read(HERE / (name + suffix))
            assert tools["compiler"] == expected_compiler
            assert tools["explicitPATH"] == scratch["environment"]["PATH"]
            assert tools["qualifiedSysrootFiles"] == len(expected_compiler["actualCompiler"]["sysrootCompilerFiles"])
            assert tools["probes"]["rustc -vV"]["stdout"] == expected_compiler["rustc"]["stdout"]
            assert tools["probes"]["cargo -V"]["stdout"] == expected_compiler["cargo"]["stdout"]
        for stream in ["stdout", "stderr"]:
            raw = gzip.decompress((HERE / (name + "-" + stream + ".gz")).read_bytes())
            assert sha(raw) == row[stream + "SHA256"]
            logs[(name, stream)] = raw
        if name in ["focused-list", "focused-execute"]:
            assert row["executableSHA256"] == artifact["sha256"] and row["executableBytes"] == artifact["bytes"]
    assert all(name in commands for name in ["focused-build", "focused-list", "focused-execute"])
    assert commands["focused-build"]["exitCode"] == commands["focused-list"]["exitCode"] == 0
    names = [line[:-6] for line in logs[("focused-list", "stdout")].decode().splitlines() if line.endswith(": test")]
    assert names == read(HERE / "exact-tests.json") == read(PRIOR / "runtime-attempts/focused-swift-debug/exact-tests.json")
    assert len(names) == len(set(names)) == 23
    text = logs[("focused-execute", "stdout")].decode(errors="replace")
    observed = re.findall(r"^test (\S+) \.\.\. (ok|FAILED|ignored)$", text, re.M)
    assert read(HERE / "observed-identities.json") == [{"test": name, "status": status, "fullPlannedSLRowComplete": False} for name, status in observed]
    result = read(HERE / "host-result.json")
    assert result["focusedTestsPassed"] == (commands["focused-execute"]["exitCode"] == 0 and observed == [(name, "ok") for name in names] and "23 passed; 0 failed; 0 ignored;" in text)
    if "swift-clippy" in commands:
        assert result["clippyPassed"] == (commands["swift-clippy"]["exitCode"] == 0)
        assert result["clippyWorkflowSHA256"] == digest(ROOT / result["clippyWorkflowPath"])
        workflow = (ROOT / result["clippyWorkflowPath"]).read_text()
        assert "cargo clippy --locked --manifest-path vm/Cargo.toml --lib --features experimental-swift-reactor -- -D warnings" in workflow
    cleanup = read(HERE / "cleanup.json")
    assert cleanup["scratch"] == scratch["path"] and cleanup["holderCheckEmpty"] and cleanup["removed"]
    assert not Path(scratch["path"]).exists() and cleanup["nativeInstancesCreated"] == 0
    assert cleanup["otherProjectProcessesChanged"] is False
    assert result["fullPlannedSLRowsComplete"] is False
    return {"schema": "mixer.swift-lifecycle.live-v3-read-only-replay.1", "verified": True, "candidateClosure": CLOSURE, "liveScopeEqualsCandidate": True, "scopeFiles": 132, "retainedRuntimePinsVerified": 978, "retainedPassedHostTestExecutions": retained["observedTotals"]["passedIdentityExecutions"], "focusedLiveTests": len(names), "focusedLiveTestsPassed": result["focusedTestsPassed"], "swiftOnlyClippyPassed": result["clippyPassed"], "ownedTargetRemoved": True, "fullPlannedSLRowsComplete": False, "nativeOrPhysicalEvidence": False, "runtimeOrCompilerRerun": False}


if __name__ == "__main__":
    print(enc(verify()).decode())
