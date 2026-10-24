"""Read-only verification of the independently reviewed, sealed host packet."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(base):
    return {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}


def check(base, item):
    rel = Path(item["path"])
    assert not rel.is_absolute() and ".." not in rel.parts
    path = base / rel
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == item["bytes"] and sha(path) == item["sha256"], str(path)
    return rel.as_posix()


def verify_attempt(attempt):
    seal = json.loads((attempt / "seal.json").read_text())
    bound = [check(attempt, item) for item in seal["files"]]
    assert len(bound) == len(set(bound))
    assert set(bound) == files(attempt) - {"seal.json"}
    receipt = json.loads((attempt / "receipt.json").read_text())
    assert receipt["status"] == "passed-bounded-host-review"
    inputs = json.loads((attempt / "inputs.json").read_text())
    assert receipt["sourceDigest"] == hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for item in inputs:
        check(attempt / "source", item)
    assert {item["path"] for item in inputs} == files(attempt / "source")
    for command in receipt["commands"]:
        check(attempt, command["output"])
        assert command["exitCode"] == 0 and not command["timedOut"] and command["cleanup"]["after"] == []
    assert receipt["independentCaseCount"] == 2352
    assert len(receipt["commands"]) == 22
    return receipt


def verify():
    seal = json.loads((ROOT / "seal.json").read_text())
    bound = [check(REPO, item) for item in seal["files"]]
    assert len(bound) == len(set(bound))
    actual = {str((ROOT / path).relative_to(REPO)) for path in files(ROOT) - {"seal.json"}}
    assert set(bound) == actual | {"docs/stripe-webhook-signature-review.md"}
    accepted = json.loads((ROOT / "receipt.json").read_text())
    assert accepted["status"] == "accepted-isolated-signature-freshness-only"
    attempt = ROOT / accepted["reviewAttempt"]
    receipt = verify_attempt(attempt)
    assert accepted["reviewSourceDigest"] == receipt["sourceDigest"]
    replay = ROOT / "final-replay"
    replay_receipt = json.loads((replay / "receipt.json").read_text())
    assert replay_receipt["status"] == "passed-read-only-replays"
    for command in replay_receipt["commands"]:
        check(replay, command["output"])
        assert command["exitCode"] == 0 and not command["timedOut"] and command["cleanup"]["after"] == []
    print(f"PASS: {len(bound)} review files sealed, 2352 independent cases, 22 host commands, all final replays and nested producer receipts bound; isolated signature/freshness acceptance only")


if __name__ == "__main__":
    verify()
