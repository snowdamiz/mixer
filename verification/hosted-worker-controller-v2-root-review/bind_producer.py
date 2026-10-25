"""Root verification of frozen V2 data; does not execute the candidate."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
PACKET = ROOT / "verification/hosted-worker-controller-v2"
EXPECTED = "143295674a760138c358ce5d9ab749724d00848e7fe6eaae312228f6782c8a39"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(row, base=ROOT):
    name = Path(row["path"])
    assert ".." not in name.parts
    path = base / name
    assert path.is_file()
    assert path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], name
    return path


def archive(row, records):
    expected = {record["path"]: record for record in records}
    assert len(expected) == len(records)
    with tarfile.open(check(row), "r:gz") as stream:
        members = stream.getmembers()
        assert len(members) == len(expected) and {m.name for m in members} == set(expected)
        for member in members:
            name = Path(member.name)
            assert member.isfile() and not name.is_absolute() and ".." not in name.parts
            value = stream.extractfile(member).read()
            assert len(value) == expected[member.name]["bytes"]
            assert hashlib.sha256(value).hexdigest() == expected[member.name]["sha256"]


def main():
    assert digest(PACKET / "receipt.json") == EXPECTED
    receipt = json.loads((PACKET / "receipt.json").read_bytes())
    assert receipt["accepted"] is False
    for row in receipt["artifacts"]:
        check(row)
    counts = {}
    for name, prefix, tree, archive_field in [
        ("source_manifest", PACKET / "candidate", "source_tree_sha256", "source_archive"),
        ("input_closure_manifest", ROOT, "input_closure_tree_sha256", "input_closure_archive")]:
        manifest = json.loads(check(receipt[name]).read_bytes())
        rows = manifest["files"]
        computed = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        assert computed == receipt[tree]
        for row in rows:
            check(row, prefix)
        archive(receipt[archive_field], rows)
        counts[name] = len(rows)
    command_count = 0
    for run in receipt["commands"]:
        for command in run["commands"]:
            check(command["stdout"])
            check(command["stderr"])
            command_count += 1
        cleanup = run["cleanup"]
        assert cleanup["scratch_removed"] and not Path(cleanup["scratch"]).exists()
        assert cleanup["matching_owned_workerd"] == []
        for action in cleanup["actions"]:
            if "persist" in action:
                assert not Path(action["persist"]).exists()
    result = {
        "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
        "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        "verifierSHA256": digest(Path(__file__)), "receiptSHA256": EXPECTED,
        "status": "frozen-v2-data-bindings-verified-independent-review-pending",
        "sourceTreeSHA256": receipt["source_tree_sha256"],
        "inputClosureTreeSHA256": receipt["input_closure_tree_sha256"],
        "verified": {**counts, "artifacts": len(receipt["artifacts"]), "commandOutputPairs": command_count},
        "producerReportedFinalResults": receipt["final_results"],
        "baselineFailuresPreserved": receipt["baseline_reproduced_failures"],
        "cleanup": receipt["cleanup"], "rootImportedOrExecutedCandidate": False,
        "candidateAccepted": False, "productionEnabled": False, "gaAccepted": False,
        "notVerified": receipt["not_verified"],
    }
    target = BASE / "producer-binding.json"
    assert not target.exists(), "preserve existing observation"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], **result["verified"]}))


if __name__ == "__main__":
    main()
