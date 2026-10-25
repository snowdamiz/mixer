"""Read-only root verification of the final coordinator host collection."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
COLLECTION = BASE.parent / "attempt-5-final"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    receipt_bytes = (COLLECTION / "receipt.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    assert receipt["status"] == "passed"
    assert receipt["test_selection"] == "repository suite and explicit independent tests"
    assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
    inputs = receipt["inputs"]
    assert len(inputs) == 92
    assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
    archive = COLLECTION / "source.tar.gz"
    assert sha(archive.read_bytes()) == receipt["source_archive_sha256"]
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        assert len(members) == len(inputs) and {m.name for m in members} == set(inputs)
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk()
            assert sha(tar.extractfile(member).read()) == inputs[member.name]
            path = ROOT / member.name
            assert path.is_file() and not path.is_symlink()
            assert sha(path.read_bytes()) == inputs[member.name]
    assert len(receipt["commands"]) == 21
    for command in receipt["commands"]:
        assert sha((COLLECTION / command["log"]).read_bytes()) == command["sha256"]
        expected = 1 if command["label"] == "release-missing-config" else 0
        assert command["exit_code"] == expected, command
    log = (COLLECTION / "tests.log").read_text()
    assert "Result: 261 passed, 2 skipped" in log and "Failed:" not in log
    for fragment in [
        "independent_coordinator_processor_proof:",
        'creation: %{id: 1, state: "completed", attempt: 1}',
        'successor: %{id: 2, state: "scheduled", attempt: 0}',
        "testing: :disabled",
        'worker: "MixerHosted.Builds.Coordinator"',
        "callbacks: [:query, :ensure_started]",
        "held_reservations: 1",
        'database: [["mixer_coordinator_review_test", "UTC"]]',
        "independent_coordinator_processor_cleanup: owned Oban supervisor stopped; dedicated database rows cleared",
    ]:
        assert fragment in log, fragment
    release = (COLLECTION / "release-test-exclusion.log").read_text()
    assert "production_build_coordinator: present; modeled dispatch helpers: absent" in release
    assert "production_build_coordinator_processor_review: absent" in release
    assert (COLLECTION / "postgres-timezone.log").read_text().strip() == "UTC"
    result = {
        "schema": 1,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python": sys.version,
        "platform": platform.platform(),
        "verifierSHA256": sha(Path(__file__).read_bytes()),
        "receiptSHA256": sha(receipt_bytes),
        "sourceTreeSHA256": receipt["source_tree_sha256"],
        "currentAndArchivedInputsVerified": len(inputs),
        "commandOutputsVerified": len(receipt["commands"]),
        "passed": 261,
        "skipped": 2,
        "skipScope": "Identity controls require Linux plus MIXER_ISOLATED_NETNS=1; no skipped gate receives credit.",
        "coordinatorProducerTests": 19,
        "independentCoordinatorTests": 14,
        "independentProcessorTests": 1,
        "countsIncludedInTotal": True,
        "actualAsynchronousObanProcessor": True,
        "externalProvider": "modeled only; no production adapter configured",
        "packagedCoordinatorPresentAndFixturesAbsent": True,
        "cleanup": receipt["cleanup"],
        "scope": "Current-source host integration with disposable PostgreSQL and local Oban processor; external workers remain unqualified.",
        "gaAccepted": False,
    }
    (BASE / "binding-review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
