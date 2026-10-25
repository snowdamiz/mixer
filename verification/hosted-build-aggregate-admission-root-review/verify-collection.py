#!/usr/bin/env python3
"""Verify a completed aggregate-admission collection against live and archived bytes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import platform
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("collection", type=Path)
    parser.add_argument("--passed", type=int, required=True)
    parser.add_argument("--independent", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "preserve existing review")
    folder = args.collection.resolve()
    raw = (folder / "receipt.json").read_bytes()
    receipt = json.loads(raw)
    require(receipt["status"] == "passed", "collection failed")
    require(receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}, "cleanup incomplete")
    inputs = receipt["inputs"]
    require(sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"], "source digest differs")
    archive = folder / "source.tar.gz"
    require(sha(archive.read_bytes()) == receipt["source_archive_sha256"], "archive digest differs")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        require(len(members) == len(inputs) and {m.name for m in members} == set(inputs), "archive membership differs")
        for member in members:
            require(member.isfile() and not member.islnk() and not member.issym(), "unexpected archive member")
            require(sha(tar.extractfile(member).read()) == inputs[member.name], "archived source differs")
            path = ROOT / member.name
            require(path.is_file() and not path.is_symlink(), "live input absent or symlinked")
            require(sha(path.read_bytes()) == inputs[member.name], f"live input differs: {member.name}")
    for command in receipt["commands"]:
        require(sha((folder / command["log"]).read_bytes()) == command["sha256"], "command output differs")
        expected = 1 if command["label"] == "release-missing-config" else 0
        require(command["exit_code"] == expected, f"unexpected command exit: {command['label']}")
    log = (folder / "tests.log").read_text()
    skipped = 0 if receipt["test_selection"] == "explicit independent tests only" else 2
    summary = f"Result: {args.passed} passed" + (f", {skipped} skipped" if skipped else "")
    result_lines = [line.strip() for line in log.splitlines() if line.startswith("Result:")]
    require(result_lines == [summary], "test result differs")
    release = (folder / "release-test-exclusion.log").read_text()
    require("production_build_coordinator: present; modeled dispatch helpers: absent" in release, "production fixture exclusion absent")
    require((folder / "postgres-timezone.log").read_text().strip() == "UTC", "fixture timezone differs")
    result = {
        "schema": 1,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv],
        "python": sys.version,
        "platform": platform.platform(),
        "verifierSHA256": sha(Path(__file__).read_bytes()),
        "receipt": str((folder / "receipt.json").relative_to(ROOT)),
        "receiptSHA256": sha(raw),
        "sourceTreeSHA256": receipt["source_tree_sha256"],
        "currentAndArchivedInputsVerified": len(inputs),
        "commandOutputsVerified": len(receipt["commands"]),
        "passed": args.passed,
        "skipped": skipped,
        "independentControlsIncludedInTotal": args.independent,
        "skipScope": "Two identity controls require Linux plus MIXER_ISOLATED_NETNS=1; skipped checks receive no credit.",
        "packagedCoordinatorPresentAndFixturesAbsent": True,
        "cleanup": receipt["cleanup"],
        "scope": receipt["scope"],
        "externalProviderQualified": False,
        "productionMigrationApplied": False,
        "gaAccepted": False,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("currentAndArchivedInputsVerified", "commandOutputsVerified", "passed", "skipped", "cleanup")}))


if __name__ == "__main__":
    main()
