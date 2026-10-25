"""Bind the independent controller rejection as data; no candidate execution."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
REVIEW = ROOT / "verification/hosted-worker-controller-implementation-independent-review"
EXPECTED = "7e146e6f341afc93dca4f108bbee7ee50f7c4a406eb329bd5fa96405463f5b7e"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(row):
    name = Path(row["path"])
    assert not name.is_absolute() and ".." not in name.parts
    path = ROOT / name
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    return path


def main():
    target = BASE / "independent-decision.json"
    assert not target.exists(), "preserve existing decision"
    assert digest(REVIEW / "receipt.json") == EXPECTED
    receipt = json.loads((REVIEW / "receipt.json").read_bytes())
    assert receipt["reviewed_producer_receipt_sha256"] == "fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a"
    assert receipt["reviewed_source_tree_sha256"] == "6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95"
    for row in receipt["artifacts"] + receipt["commands"]:
        check(row)
    archive = check(receipt["review_fixture_archive"])
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        assert len({member.name for member in members}) == len(members)
        for member in members:
            name = Path(member.name)
            assert member.isfile() and not name.is_absolute() and ".." not in name.parts
            assert hashlib.sha256(stream.extractfile(member).read()).hexdigest() == digest(ROOT / name)
    assert receipt["producer_groups_passed"] == 28
    assert receipt["independent_groups_failed"] == 3 and receipt["independent_groups_passed"] == 5
    assert receipt["cleanup"]["status"] == "passed"
    assert not Path(receipt["cleanup"]["owned_scratch"]).exists()
    result = {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "verifierSHA256": digest(Path(__file__)), "receiptSHA256": EXPECTED,
        "status": "rejected-controller-candidate-two-correctness-findings",
        "verifiedArtifacts": len(receipt["artifacts"]), "verifiedCommandRecords": len(receipt["commands"]),
        "verifiedArchivedFixtures": len(members), "producerGroupsPassed": 28,
        "independentGroupsPassed": 5, "independentGroupsFailed": 3,
        "findings": receipt["findings"], "cleanup": receipt["cleanup"],
        "rootImportedOrExecutedReviewedCode": False, "candidateAccepted": False,
        "productionEnabled": False, "gaAccepted": False,
        "nextImplementation": "Separate V2 repair of the final claim authority fence and persisted qualified-clock history, preserving consumed claims and all failed evidence; fresh independent runtime review before acceptance.",
        "notVerified": receipt["not_verified"],
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ["status", "verifiedArtifacts", "verifiedArchivedFixtures", "independentGroupsFailed"]}))


if __name__ == "__main__":
    main()
