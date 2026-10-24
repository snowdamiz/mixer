"""Independent read-only audit of every producer file, nested receipt, and command."""
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(sys.argv[1]).resolve()
ROOT = REPO / "verification/stripe-webhook-signature"
EXPECTED_SEAL = "27191daebc5ce6dc41e93251027b72b7cabed491aa7b50450daa40346d964e16"
EXPECTED_CANDIDATE = "3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(base, item):
    rel = Path(item["path"])
    assert not rel.is_absolute() and ".." not in rel.parts
    path = base / rel
    assert path.is_file() and not path.is_symlink(), str(path)
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], str(path)
    return rel.as_posix()


assert sha(ROOT / "seal.json") == EXPECTED_SEAL
seal = json.loads((ROOT / "seal.json").read_text())
bound = [checked(REPO, item) for item in seal["files"]]
assert len(bound) == len(set(bound)) == 89
actual = {p.relative_to(REPO).as_posix() for p in ROOT.rglob("*") if p.is_file() and p != ROOT / "seal.json"}
assert actual == {p for p in bound if p.startswith("verification/stripe-webhook-signature/")}
assert set(bound) - actual == {"docs/stripe-webhook-signature-contract.md", "docs/stripe-webhook-signature-evidence.md"}
assert sha(ROOT / "candidate/webhook_signature.ex") == EXPECTED_CANDIDATE
summary = []
for attempt in sorted(ROOT.glob("attempt-*")):
    nested = json.loads((attempt / "seal.json").read_text())["files"]
    paths = [checked(attempt, item) for item in nested]
    assert len(paths) == len(set(paths))
    assert set(paths) == {p.relative_to(attempt).as_posix() for p in attempt.rglob("*") if p.is_file() and p.name != "seal.json"}
    assert all((attempt / p).relative_to(REPO).as_posix() in bound for p in paths)
    receipt = json.loads((attempt / "receipt.json").read_text())
    inputs = json.loads((attempt / "inputs.json").read_text())
    for item in inputs:
        checked(attempt / "source", item)
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert receipt["sourceDigest"] == digest
    assert sha(attempt / "source/candidate/webhook_signature.ex") == EXPECTED_CANDIDATE
    assert receipt["head"] == "d4909e275df7e757a5218cc0a88112f4fc3f088b"
    assert receipt["ownedProcessHelper"]["sha256"] == "209290a7b3638f7510bb1b88dfcdb272f657b89fffe96dcc2f2b631b8f244216"
    for index, command in enumerate(receipt["commands"]):
        checked(ROOT, command["output"])
        assert command["cleanup"]["after"] == [] and not command["timedOut"]
        expected = 0 if attempt.name in ["attempt-3", "attempt-4"] or index < len(receipt["commands"])-1 else (1 if attempt.name == "attempt-1" else 2)
        assert command["exitCode"] == expected
    expected_status = "passed-host-only" if attempt.name in ["attempt-3", "attempt-4"] else "failed"
    assert receipt["status"] == expected_status
    summary.append({"attempt": attempt.name, "status": receipt["status"], "commands": len(receipt["commands"]), "sourceDigest": digest})
assert "No file named --warnings-as-errors" in (ROOT / "attempt-1/command-06.log").read_text()
assert "Result: 21/22 passed" in (ROOT / "attempt-2/command-07.log").read_text()
assert ":null" in (ROOT / "attempt-2/command-07.log").read_text()
assert all("Result: 22 passed" in (ROOT / a / "command-07.log").read_text() for a in ["attempt-3", "attempt-4"])
receipt = json.loads((ROOT / "receipt.json").read_text())
assert receipt["qualifiedAttempt"] == "attempt-4"
assert receipt["candidateSHA256"] == EXPECTED_CANDIDATE
assert receipt["sourceDigest"] == summary[-1]["sourceDigest"] == "d0bffad55874dc9cece9d9ec4e6ccd9adda01e4c8117623475126aab7a5f7f6f"
print(json.dumps({"status": "pass", "allBoundFiles": len(bound), "packetSealSHA256": EXPECTED_SEAL, "attempts": summary}, sort_keys=True))
