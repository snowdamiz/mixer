"""Root data-only binding of the completed independent V2 review."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / "verification/hosted-worker-controller-v2-independent-review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(row):
    path = ROOT / row["path"]
    assert path.is_file() and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]
    return path


def archive(archive_row, manifest_row):
    manifest = json.loads(check(manifest_row).read_bytes())
    records = manifest["files"]
    assert hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == manifest["tree_sha256"]
    expected = {r["path"]: r for r in records}
    assert len(expected) == len(records)
    with tarfile.open(check(archive_row)) as stream:
        members = stream.getmembers()
        assert len(members) == len(records) and {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            data = stream.extractfile(member).read()
            assert len(data) == expected[member.name]["bytes"]
            assert hashlib.sha256(data).hexdigest() == expected[member.name]["sha256"]
    return len(records)


assert sha(PACKET / "receipt.json") == "479149ee401cd42261334f6e0dfd60f0eebaba113a8223ec3dac8fd4b56578c2"
assert sha(PACKET / "handoff.json") == "c803ea5fe1e0e744e926a056a09cfa2313f7dc3d8a49c3e82042ed530f652e76"
receipt = json.loads((PACKET / "receipt.json").read_bytes())
handoff = json.loads((PACKET / "handoff.json").read_bytes())
check(handoff["receipt"]); check(handoff["report"])
assert receipt["new_correctness_findings"] == []
for row in receipt["artifacts"]:
    check(row)
inputs = archive(receipt["complete_frozen_inputs"], receipt["complete_frozen_manifest"])
fixtures = archive(receipt["executed_fixture_archive"], receipt["executed_fixture_manifest"])
commands = 0
for run in receipt["commands"]:
    assert run["cleanup"]["scratch_removed"] and not Path(run["cleanup"]["scratch"]).exists()
    for command in run["commands"]:
        check(command["stdout"]); check(command["stderr"]); commands += 1
    for row in run["cleanup"]["actions"]:
        if "persist" in row:
            assert not Path(row["persist"]).exists()
assert receipt["frozen_producer_groups_passed"] == 72 and receipt["distinct_added_independent_groups_passed"] == 17
assert receipt["cleanup"]["matching_owned_workerd"] == []
assert not Path(receipt["cleanup"]["shared_dependency_copy_scratch"]).exists()
record = {
    "schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "verifierSHA256": sha(Path(__file__)), "receiptSHA256": sha(PACKET / "receipt.json"),
    "status": "independent-review-accepted-for-exact-local-integration",
    "sourceTreeSHA256": receipt["reviewed_source_tree_sha256"],
    "verifiedArtifacts": len(receipt["artifacts"]), "verifiedArchivedInputs": inputs,
    "verifiedArchivedFixtures": fixtures, "verifiedCommandOutputPairs": commands,
    "producerGroupsPassed": 72, "additionalIndependentGroupsPassed": 17,
    "originalBaselineFailedGroups": 3, "originalBaselineFailuresPreserved": True,
    "rootIntegratedRuntimeChecksPending": True, "productionEnabled": False, "gaAccepted": False,
}
output = HERE / "independent-decision.json"
assert not output.exists()
output.write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
