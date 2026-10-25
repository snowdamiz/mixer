#!/usr/bin/env python3
"""Bind the frozen producer candidate as data, without accepting implementation."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
CANDIDATE = ROOT / "verification/hosted-worker-transport"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def main():
    target = BASE / "candidate-v1-binding.json"
    require(not target.exists(), "preserve previous binding review")
    raw = (CANDIDATE / "receipt.json").read_bytes()
    receipt = json.loads(raw)
    for name, field in [("source-map.json", "source_map_sha256"), ("commands.json", "commands_sha256"), ("compiled-artifacts.json", "compiled_artifacts_sha256"), ("cross-runtime-vectors.json", "cross_runtime_vectors_sha256")]:
        require(sha((CANDIDATE / name).read_bytes()) == receipt[field], f"changed evidence: {name}")
    rows = json.loads((CANDIDATE / "source-map.json").read_bytes())["sources"]
    require(len(rows) == receipt["input_count"] == 86, "input count differs")
    require(sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_digest"], "source tree differs")
    expected = {row["path"]: row for row in rows}
    require(len(expected) == len(rows), "duplicate source input")
    archive = CANDIDATE / "candidate-inputs.tar.gz"
    require(sha(archive.read_bytes()) == receipt["archive_sha256"], "archive changed")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        require(len(members) == len(rows) and {member.name for member in members} == set(expected), "archive membership differs")
        for member in members:
            require(member.isfile() and not member.issym() and not member.islnk(), "nonregular archive member")
            row = expected[member.name]
            value = tar.extractfile(member).read()
            require(len(value) == row["size"] and sha(value) == row["sha256"], "archived bytes differ")
            live = ROOT / member.name
            require(live.is_file() and not live.is_symlink() and sha(live.read_bytes()) == row["sha256"], f"live input changed: {member.name}")
    contexts = json.loads((CANDIDATE / "context-map.json").read_bytes())
    require(len(contexts) == 6, "safe context closure changed")
    for context in contexts:
        require(sha((ROOT / context["source"]).read_bytes()) == context["sha256"], "live context differs")
        require(sha((CANDIDATE / context["snapshot"]).read_bytes()) == context["sha256"], "copied context differs")
    commands = json.loads((CANDIDATE / "commands.json").read_bytes())["commands"]
    for command in commands:
        require(command["exit_code"] == 0, "producer command failed")
        for stream in ("stdout", "stderr"):
            require(sha((CANDIDATE / (command["name"] + "." + stream)).read_bytes()) == command[stream + "_sha256"], "output changed")
    test_result = json.loads((CANDIDATE / "final-tests.stdout").read_text().splitlines()[-1])
    require(test_result == receipt["test_result"], "test result differs")
    require((test_result["tests"], test_result["failures"], test_result["skipped"], test_result["excluded"]) == (25, 0, 0, 0), "producer test failure")
    require(test_result["frozen_modules_loaded"] == [], "unexpected loaded modules")
    require(receipt["vectors"]["vectors"] == 36 and receipt["vectors"]["immutable_binding_matches"] is True, "vector result differs")
    require(not (CANDIDATE / "build").exists(), "owned compiler directory remains")
    result = {
        "schema": 1,
        "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, str(Path(__file__).relative_to(ROOT))],
        "python": sys.version,
        "verifierSHA256": sha(Path(__file__).read_bytes()),
        "status": "producer-candidate-evidence-bound-independent-review-pending",
        "receiptSHA256": sha(raw),
        "sourceDigest": receipt["source_digest"],
        "sourceArchiveSHA256": receipt["archive_sha256"],
        "currentAndArchivedInputsVerified": len(rows),
        "safeContextCopiesVerified": len(contexts),
        "commandOutputsVerified": len(commands),
        "producerTests": 25,
        "crossRuntimeVectors": 36,
        "producerScope": receipt["scope"],
        "rootImportedCandidateCode": False,
        "productionIntegrationAccepted": False,
        "independentReviewPending": True,
        "gaAccepted": False,
        "limitations": receipt["pending"] + ["Historical intermediate attempt logs are retained diagnostics, not newly source-qualified executions."]
    }
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "currentAndArchivedInputsVerified", "safeContextCopiesVerified", "commandOutputsVerified")}))


if __name__ == "__main__":
    main()
