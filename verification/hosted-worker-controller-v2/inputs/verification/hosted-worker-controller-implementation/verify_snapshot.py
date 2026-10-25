#!/usr/bin/env python3
"""Read-only seal/cleanup verification; does not claim operational acceptance."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def check(record):
    path = ROOT / record["path"]
    assert path.stat().st_size == record["bytes"], record["path"]
    assert digest(path) == record["sha256"], record["path"]

def main():
    receipt = json.loads((HERE / "receipt.json").read_text())
    for entry in receipt["artifacts"]:
        check(entry)
    for name in ["source-manifest.json", "dependency-files.json", "jason-beams.json"]:
        for entry in json.loads((HERE / name).read_text())["files"]:
            check(entry)
    source = json.loads((HERE / "source-manifest.json").read_text())
    tree = hashlib.sha256(json.dumps(source["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert tree == receipt["source_tree_sha256"] == source["tree_sha256"]
    with tarfile.open(HERE / "source-snapshot.tar.gz") as archive:
        expected = {entry["path"]: entry for entry in source["files"]}
        assert set(archive.getnames()) == set(expected)
        for member in archive:
            raw = archive.extractfile(member).read()
            assert hashlib.sha256(raw).hexdigest() == expected[member.name]["sha256"]
    report = json.loads((HERE / "test-report.json").read_text())
    assert report["status"] == "passed" and len(report["results"]) == 28
    paths = [x["persist"] for x in report["cleanup"] if "persist" in x]
    assert all(not Path(path).exists() for path in paths)
    assert receipt["cleanup"]["matching_workerd_processes"] == []
    assert receipt["results"]["dependency_install_scripts_executed"] == 0
    print(json.dumps({"status": "passed", "scope": "frozen-source-dependency-artifact-and-recorded-cleanup-integrity-only",
                      "source_tree_sha256": tree, "reported_groups": 28, "independent_review": "pending"}))

if __name__ == "__main__":
    main()
