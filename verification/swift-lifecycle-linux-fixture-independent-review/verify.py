#!/usr/bin/env python3
"""Read-only integrity and acceptance audit; does not execute the VM."""
import gzip
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRODUCER = HERE.parent / "swift-lifecycle-linux-fixture-repair"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def verify():
    seal = read("seal.json")
    members = {str(path.relative_to(HERE)) for path in HERE.rglob("*") if path.is_file() and path != HERE / "seal.json"}
    assert members == set(seal["files"])
    for name, digest in seal["files"].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    for name, digest in seal["externalFiles"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    audit = read("source-review.json")
    assert sha((PRODUCER / "seal.json").read_bytes()) == audit["producerSealSHA256"]
    producer_seal = json.loads((PRODUCER / "seal.json").read_text())
    for name, digest in producer_seal["files"].items():
        assert sha((PRODUCER / name).read_bytes()) == digest, name
    for name, digest in producer_seal["externalFiles"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    manifest = read("candidate-manifest.json")
    assert len(manifest) == 132
    assert sha((HERE / "candidate-manifest.json").read_bytes()) == "6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8"
    for name, digest in manifest.items():
        assert sha((ROOT / "vm" / name).read_bytes()) == digest, name
        assert sha((PRODUCER / "candidate" / name).read_bytes()) == digest, name
    commands = {path.stem: json.loads(path.read_text()) for path in (HERE / "commands").glob("*.json")}
    assert len(commands) == 8
    negative = {"independent-no-expiry-execute", "independent-production-helper-absent"}
    source_control = "src/experimental_swift_reactor/control.rs"
    original = (PRODUCER / "candidate" / source_control).read_text()
    no_expiry = original.replace((HERE / "exact-helper.txt").read_text(), (HERE / "no-expiry-helper.txt").read_text())
    probe = original + "\n" + (HERE / "production-helper-probe.rs").read_text()
    spent = 0
    for name, command in commands.items():
        assert command["exitCode"] == (101 if name in negative else 0), name
        assert not command["timedOut"] and command["sourceUnchanged"] and not command["remainingProcessGroup"], name
        assert command["tools"] == command["postTools"], name
        assert command["timeoutSeconds"] <= 180
        spent += command["durationSeconds"]
        expected = dict(manifest)
        if name.startswith("independent-no-expiry-"):
            expected[source_control] = sha(no_expiry.encode())
        if name == "independent-production-helper-absent":
            expected[source_control] = sha(probe.encode())
        assert command["sourceManifest"] == expected, name
        for suffix in ("stdout", "stderr"):
            assert sha((HERE / "commands" / (name + "." + suffix)).read_bytes()) == command[suffix + "SHA256"], name
    assert spent < 600
    selected = (HERE / "commands/independent-selected-execute.stdout").read_text()
    mutant = (HERE / "commands/independent-no-expiry-execute.stdout").read_text()
    passed = sorted(re.findall(r"^test (\S+) \.\.\. ok$", selected, re.M))
    failed = sorted(re.findall(r"^test (\S+) \.\.\. FAILED$", mutant, re.M))
    assert len(passed) == len(failed) == 3 and passed == failed
    assert "test result: ok. 3 passed; 0 failed; 0 ignored;" in selected
    assert "test result: FAILED. 0 passed; 3 failed; 0 ignored;" in mutant
    assert mutant.count("expected actual failed operation with accounted cleanup") == 3
    missing = (HERE / "commands/independent-production-helper-absent.stderr").read_text()
    assert "error[E0599]: no method named `test_expire_deadline`" in missing
    assert "due to 1 previous error" in missing
    for name, artifact_name in (("selected-debug.gz", "selected-artifact.json"), ("no-expiry-debug.gz", "no-expiry-artifact.json")):
        artifact = read(artifact_name)
        archive = (HERE / name).read_bytes()
        assert sha(archive) == artifact["archiveSHA256"]
        assert sha(gzip.decompress(archive)) == artifact["executableSHA256"]
    producer_verified = json.loads((HERE / "commands/producer-readonly-verifier.stdout").read_text())
    assert producer_verified["verified"] and producer_verified["qualifiedIdentityExecutions"] == 196
    cleanup = read("cleanup.json")
    assert cleanup["targetsAbsent"] and not cleanup["otherProjectProcessesTouched"]
    for name, row in cleanup["ownedPaths"].items():
        assert not (HERE / name).exists() and row["removed"] and not row["liveHolders"]
        assert sha((HERE / (name + "-holders.stdout")).read_bytes()) == row["lsofStdoutSHA256"]
        assert sha((HERE / (name + "-holders.stderr")).read_bytes()) == row["lsofStderrSHA256"]
    assert read("restore.json")["finalSourceRestoredExactly"]
    receipt = read("receipt.json")
    assert receipt["blockingFindings"] == 0 and receipt["acceptedForRootReview"]
    assert not receipt["linuxReplayPerformed"] and not receipt["GAcredit"] and not receipt["newProductionAccountingCredit"]
    print(json.dumps({"verified": True, "blockingFindings": 0, "candidateClosure": audit["sourceClosureSHA256"], "independentSelectedPasses": 3, "noExpiryControlExpectedFailures": 3, "ordinaryProductionHelperAbsent": True, "ownedSourceAndTargetRemoved": True, "producerExecutionsAudited": 196}, sort_keys=True))


if __name__ == "__main__":
    verify()
