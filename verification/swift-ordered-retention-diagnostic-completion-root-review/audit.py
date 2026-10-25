"""Read-only root audit of the sealed finite completion and independent review."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import tarfile

P = Path(__file__).resolve().parent
R = P.parents[1]
F = P.parent / "swift-ordered-retention-diagnostic-completion"
V = P.parent / "swift-ordered-retention-diagnostic-completion-review"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


seals = {}
for packet, expected, count in [
    (F, "2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba", 222),
    (V, "87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc", 158),
]:
    assert sha((packet / "seal.json").read_bytes()) == expected
    seal = read(packet / "seal.json")
    assert len(seal["members"]) == count
    paths = set()
    for member in seal["members"]:
        relative = Path(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert str(relative) not in paths
        paths.add(str(relative))
        path = R / relative
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == member["bytes"] and sha(raw) == member["sha256"]
    seals[packet.name] = {"sha256": expected, "members": count}

for side in ("baseline", "candidate"):
    manifest = read(F / (side + "-manifest.json"))
    assert len(manifest) == 132
    with tarfile.open(F / (side + "-source.tar.gz"), "r:gz") as archive:
        assert sorted(archive.getnames()) == sorted(manifest)
        for member in archive:
            assert member.isfile()
            assert sha(archive.extractfile(member).read()) == manifest[member.name]
baseline = read(F / "baseline-manifest.json")
assert {name: sha((R / "vm" / name).read_bytes()) for name in baseline} == baseline
assert not (F / ".scratch").exists() and not (V / ".scratch").exists()
assert read(F / "cleanup.json")["ownedScratchRemoved"]
cleanup = read(V / "cleanup.json")
assert cleanup["scratchRemoved"] and cleanup["allSynchronousChildrenReaped"]
assert cleanup["nativeCaptureUIInstancesStarted"] == 0
assert read(V / "packet-audit.json")["reverseAll132Restored"]

result = read(V / "result.json")
assert result["verdict"] == "accepted-selected-finite-completion-with-reviewer-inventory-supplement"
assert result["counts"]["freshExactCandidateSwift"] == 362
assert result["counts"]["freshProducerCustody"] == 21
assert result["counts"]["independentControls"] == 6
assert result["fullReplayAccepted"] is False
assert result["foreignCleanupInvariant"] == 1
assert result["foreignQuarantineBytes"] == result["foreignQuarantineTickets"] == 1
for name, command in result["commands"].items():
    for stream, binding in command["outputs"].items():
        raw = (V / "commands" / name / (stream + ".txt")).read_bytes()
        assert len(raw) == binding["bytes"] and sha(raw) == binding["sha256"]
for name in ["candidate-swift", "baseline-generic-private", "candidate-generic-private",
             "baseline-generic-integration", "candidate-generic-integration",
             "producer-custody", "independent-controls-2", "actual-owner-layout",
             "reverse-patch", "inventory-supplement-2"]:
    assert result["commands"][name]["exitCode"] == 0
assert result["commands"]["independent-controls"]["exitCode"] == 1

inventory = read(V / "inventory-supplement.json")
assert len(inventory["phases"]) == 19
for phase in inventory["phases"].values():
    assert phase["corrected"] == phase["frozenProvisional"] + sum(phase["additions"].values())
    assert phase["corrected"] <= 16384
assert max(phase["corrected"] for phase in inventory["phases"].values()) == 16186
assert inventory["correctedMargin"] == 198
assert inventory["correctedAllPhaseNamedRoleUnion"] == 51712
assert inventory["unionIsSimultaneousPeak"] is False
assert inventory["debugMaximumHelperDepth"] == 7 < inventory["chargedDebugHelperLevels"] == 8
assert inventory["producerInventorySHA256"] == sha((F / "logical-inventory.json").read_bytes())
evidence = read(V / "evidence-verify.json")
assert evidence["verified"] and evidence["linkTargetsReadOnlyFromArchive"]
assert evidence["rawMembers"] == 157 and evidence["retainedBinaries"] == 11

print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=R, text=True).strip(),
    "audit_sha256": sha(Path(__file__).read_bytes()),
    "seals": seals,
    "verified_members": 380,
    "both_archives_files": 132,
    "live132_unchanged": True,
    "owned_scratch_absent": True,
    "commands_and_outputs_bound": True,
    "review_counts": result["counts"],
    "selected_inventory": "Independent supplement supersedes producer provisional 16114",
    "logical_peak": 16186,
    "logical_ceiling": 16384,
    "margin": 198,
    "phases": 19,
    "distinct_union_not_peak": 51712,
    "host_copy_peak": 103777,
    "host_copy_ceiling": 131072,
    "fullReplayAccepted": False,
    "scope": "Root frozen evidence audit only; selected finite completion, no live engine/fulltarget/native/GA acceptance",
}, indent=2, sort_keys=True))
