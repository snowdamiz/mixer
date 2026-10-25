#!/usr/bin/env python3
"""Bind a selected frozen V2 packet, then copy only the isolated startup closure."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
UP = ROOT / "verification/hosted-worker-transport-v2"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(value, reason):
    if not value:
        raise ValueError(reason)

def main():
    expected_receipt = sys.argv[1]
    target = BASE / "upstream-binding.json"
    require(not target.exists(), "existing binding must be preserved")
    raw = (UP / "receipt.json").read_bytes()
    require(sha(raw) == expected_receipt, "receipt changed")
    receipt = json.loads(raw)
    rows = json.loads((UP / receipt["source_map"]).read_bytes())["inputs"]
    require(len(rows) == receipt["input_count"], "input count differs")
    require(sha(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_digest"], "source digest differs")
    expected = {row["path"]: row for row in rows}
    require(len(expected) == len(rows), "duplicate source path")
    for path in expected:
        require(path == "THIRD_PARTY.yml" or path == "docs/hosted-worker-transport-v2.md" or path.startswith("verification/hosted-worker-transport-v2/"), "unexpected source root")
        require(not Path(path).is_absolute() and ".." not in Path(path).parts, "unsafe source path")
        require("catalog" not in path.lower() and "authority" not in path.lower(), "frozen lane excluded")
    archive = UP / receipt["input_archive"]
    require(sha(archive.read_bytes()) == receipt["input_archive_sha256"], "input archive changed")
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        require(len(members) == len(rows) and {m.name for m in members} == set(expected), "archive membership differs")
        for member in members:
            row = expected[member.name]
            require(member.isfile() and not member.issym() and not member.islnk(), "nonregular member")
            data = tar.extractfile(member).read()
            require(sha(data) == row["sha256"] and len(data) == row["size"], "archived source changed")
            live = ROOT / member.name
            require(not live.is_symlink() and sha(live.read_bytes()) == row["sha256"], "current frozen source changed")
    for row in receipt["output_bindings"]:
        path = UP / row["path"]
        require(not path.is_symlink() and path.stat().st_size == row["size"] and sha(path.read_bytes()) == row["sha256"], "output binding changed")
    commands = json.loads((UP / receipt["commands"]).read_bytes())["commands"]
    for cmd in commands:
        require(cmd["exit_code"] == 0, "selected producer command failed")
        for stream in ["stdout", "stderr"]:
            require(sha((UP / cmd[stream]).read_bytes()) == cmd[stream + "_sha256"], "command output changed")
    require(sum(g["tests"] for g in receipt["test_groups"]) == receipt["tests"], "test count differs")
    require(all(g["failures"] == g["skipped"] == g["excluded"] == 0 and g["frozen_modules_loaded"] == [] for g in receipt["test_groups"]), "producer test failure")
    require(receipt["vectors"]["vectors"] == 36 and receipt["vectors"]["immutable_binding_matches"], "wire vectors differ")
    require(receipt["production_exports"]["fixture_start_absent"] and receipt["production_exports"]["phase_barrier_branches_absent"] and receipt["production_exports"]["marker_reset_api_absent"], "production export check failed")
    require(not (UP / "build").exists(), "producer scratch remains")

    copies = []
    for source in sorted(list((UP / "candidate/context").rglob("*.ex")) + list((UP / "candidate/lib").rglob("*.ex")) + list((UP / "locked/hosted/_build/test/lib").rglob("*"))):
        if not source.is_file():
            continue
        relative = source.relative_to(UP)
        require(str(source.relative_to(ROOT)) in expected, "copy not in frozen closure")
        destination = BASE / (relative if relative.parts[0] == "locked" else Path("transport") / relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(not destination.exists(), "copy already exists")
        shutil.copyfile(source, destination)
        copies.append({"source": str(source.relative_to(ROOT)), "copy": str(destination.relative_to(BASE)), "sha256": sha(source.read_bytes())})
    for name in ["identity/encoding.ex", "identity/manifest.ex", "identity/startup_config.ex"]:
        source = ROOT / "hosted/lib/mixer_hosted" / name
        destination = BASE / "context" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        require(not destination.exists(), "context copy already exists")
        shutil.copyfile(source, destination)
        copies.append({"source": str(source.relative_to(ROOT)), "copy": str(destination.relative_to(BASE)), "sha256": sha(source.read_bytes())})
    source = ROOT / "hosted/test/runtime_config_test.exs"
    destination = BASE / "context/runtime_config_test.exs"
    shutil.copyfile(source, destination)
    copies.append({"source": str(source.relative_to(ROOT)), "copy": str(destination.relative_to(BASE)), "sha256": sha(source.read_bytes())})
    original_overlays = [{"path": str(p.relative_to(BASE / "candidate")), "liveSHA256": sha((ROOT / p.relative_to(BASE / "candidate")).read_bytes()), "candidateSHA256": sha(p.read_bytes())} for p in sorted((BASE / "candidate").rglob("*")) if p.is_file()]
    result = {"schema": 1, "receiptSHA256": expected_receipt, "sourceDigest": receipt["source_digest"],
        "currentAndArchivedInputs": len(rows), "outputBindings": len(receipt["output_bindings"]), "commandOutputSets": len(commands),
        "producerTests": receipt["tests"], "vectors": receipt["vectors"]["vectors"], "copiedInputs": copies, "startupOverlays": original_overlays,
        "status": "bound-for-isolated-startup-testing-not-independent-transport-acceptance", "independentTransportReviewPending": True,
        "fullApplicationIntegrationPending": True, "command": sys.argv, "verifierSHA256": sha(Path(__file__).read_bytes())}
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "currentAndArchivedInputs", "outputBindings", "producerTests", "vectors"]}))

if __name__ == "__main__":
    main()
