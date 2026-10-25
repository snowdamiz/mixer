"""Read-only root binding of the frozen controller producer; executes no candidate."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PACKET = ROOT / "verification/hosted-worker-controller-implementation"
RECEIPT_SHA = "fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a"
TREE_SHA = "6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95"
ARCHIVE_SHA = "d6894fdae991b51485e7bec04a86027f87d84261ddc527e292e072c8b8dd55b7"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(row: dict) -> Path:
    name = Path(row["path"])
    if name.is_absolute():
        path = name
    else:
        assert ".." not in name.parts, name
        path = ROOT / name
    if "symlink_target" in row:
        assert path.is_symlink() and os.readlink(path) == row["symlink_target"], path
    else:
        assert not path.is_symlink(), path
    data = path.read_bytes()
    assert len(data) == row["bytes"] and sha(data) == row["sha256"], path
    if "mode" in row:
        mode = row["mode"]
        expected = int(mode, 8) if isinstance(mode, str) else mode
        assert stat.S_IMODE(path.stat().st_mode) == expected, path
    return path


def load_binding(row: dict) -> dict:
    return json.loads(check(row).read_text())


def main() -> None:
    raw = (PACKET / "receipt.json").read_bytes()
    assert sha(raw) == RECEIPT_SHA
    receipt = json.loads(raw)
    assert receipt["source_tree_sha256"] == TREE_SHA
    assert receipt["source_archive"]["sha256"] == ARCHIVE_SHA
    source = load_binding(receipt["source_manifest"])
    assert source["tree_sha256"] == TREE_SHA
    assert sha(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode()) == TREE_SHA
    dependencies = load_binding(receipt["dependency_manifest"])
    jason = load_binding(receipt["jason_beams"])
    assert type(jason["loaded_mixer_modules"]) is int and jason["loaded_mixer_modules"] == 0
    for rows in [source["files"], dependencies["files"], jason["files"],
                 receipt["artifacts"], receipt["runtime_binary_inputs"]]:
        assert len({row["path"] for row in rows}) == len(rows)
        for row in rows:
            check(row)
    rows = {row["path"]: row for row in source["files"]}
    archive = check(receipt["source_archive"])
    with tarfile.open(archive, "r:gz") as stream:
        members = stream.getmembers()
        assert len(members) == len(rows)
        assert len({member.name for member in members}) == len(members)
        assert {member.name for member in members} == set(rows)
        for member in members:
            assert member.isfile(), member.name
            row = rows[member.name]
            data = stream.extractfile(member).read()
            assert len(data) == row["bytes"] and sha(data) == row["sha256"], member.name
    historical = []
    for command in receipt["commands_and_outputs"]:
        for field in ["stdout", "stderr"]:
            check(command[field])
        if command["observed_exit_code"] != 0:
            historical.append({"argv": command["argv"], "exit": command["observed_exit_code"]})
    revision_command = ["git", "rev-parse", "HEAD"]
    revision = subprocess.run(revision_command, cwd=ROOT, check=True,
                              text=True, capture_output=True)
    decision = {
        "schema": 1, "observedUTC": datetime.now(timezone.utc).isoformat(),
        "status": "frozen-producer-data-bindings-verified-not-runtime-acceptance",
        "sourceRevision": revision.stdout.strip(), "revisionCommand": revision_command,
        "command": [sys.executable, "-B", str(Path(__file__).resolve())],
        "python": sys.version, "verifierSHA256": sha(Path(__file__).read_bytes()),
        "receiptSHA256": RECEIPT_SHA, "sourceTreeSHA256": TREE_SHA,
        "sourceArchiveSHA256": ARCHIVE_SHA,
        "verified": {
            "currentAndArchivedSourceFiles": len(rows),
            "dependencyFiles": len(dependencies["files"]),
            "jasonFiles": len(jason["files"]),
            "artifacts": len(receipt["artifacts"]),
            "runtimeInputs": len(receipt["runtime_binary_inputs"]),
            "commandOutputPairs": len(receipt["commands_and_outputs"]),
        },
        "producerReportedResults": receipt["results"],
        "historicalFailedCommandsPreserved": historical,
        "historicalSourceLimit": receipt["historical_attempt_limits"],
        "rootBindingSetupCorrection": "Initial root assertion expected an empty list; the producer records the zero Mixer module count as integer 0. Corrected before binding acceptance; producer unchanged.",
        "runtimeRerun": False, "candidateAccepted": False,
        "independentReview": "pending-frozen-report",
        "limitations": receipt["not_verified"],
        "cleanup": "Read-only binding; no candidate import, scratch, runtime, native instance or service.",
    }
    (OUT / "producer-binding.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps({"status": decision["status"], **decision["verified"]}, sort_keys=True))


if __name__ == "__main__":
    main()
