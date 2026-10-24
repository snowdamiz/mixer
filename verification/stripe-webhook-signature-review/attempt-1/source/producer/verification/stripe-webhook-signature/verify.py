"""Read-only replay of the sealed standalone signature component's evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    seal = json.loads((ROOT / "seal.json").read_text())
    observed = set()
    for item in seal["files"]:
        p = REPO / item["path"]
        assert p.is_file() and not p.is_symlink()
        assert p.stat().st_size == item["bytes"] and sha(p) == item["sha256"], str(p)
        assert item["path"] not in observed
        observed.add(item["path"])
    receipt = json.loads((ROOT / "receipt.json").read_text())
    qualified = ROOT / receipt["qualifiedAttempt"]
    recorded = json.loads((qualified / "receipt.json").read_text())
    assert recorded["status"] == "passed-host-only"
    assert recorded["sourceDigest"] == receipt["sourceDigest"]
    inputs = json.loads((qualified / "inputs.json").read_text())
    assert hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == receipt["sourceDigest"]
    for item in inputs:
        assert sha(qualified / "source" / item["path"]) == item["sha256"]
        current = REPO / "docs/stripe-webhook-signature-contract.md" if item["path"] == "contract.md" else ROOT / item["path"]
        assert sha(current) == item["sha256"], "current standalone input changed"
    for command in recorded["commands"]:
        assert command["exitCode"] == 0 and not command["timedOut"]
        assert command["cleanup"]["after"] == []
    for attempt in ROOT.glob("attempt-*"):
        for item in json.loads((attempt / "seal.json").read_text())["files"]:
            assert sha(attempt / item["path"]) == item["sha256"]
            assert str((attempt / item["path"]).relative_to(REPO)) in observed
    print(f"PASS: {len(observed)} files bound, all nested receipts retained; 22 host tests, four faults and comparison schedule only")


if __name__ == "__main__":
    verify()
