#!/usr/bin/env python3
"""Read-only sealed review/output/snapshot audit; executes no product or tests."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/swift-ordered-retention-analyzer-library-review"
PRODUCER = ROOT / "verification/swift-ordered-retention-analyzer-library"
EXPECTED = "a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e"
PRODUCER_SHA = "777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_row(row, base=ROOT):
    path = base / row["path"]
    assert path.is_file() and not path.is_symlink()
    assert path.resolve().is_relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == row["bytes"] and digest(raw) == row["sha256"], str(path)


def verify_seal(path, expected):
    raw = path.read_bytes()
    assert digest(raw) == expected
    seal = json.loads(raw)
    assert len({row["path"] for row in seal["members"]}) == len(seal["members"])
    for row in seal["members"]:
        verify_row(row)
    return seal


seal = verify_seal(BASE / "seal.json", EXPECTED)
producer = verify_seal(PRODUCER / "seal.json", PRODUCER_SHA)
assert len(seal["members"]) == 624
assert sum(row["bytes"] for row in seal["members"]) == 89_222_620
assert (BASE / "seal.sha256").read_text().split()[0] == EXPECTED
actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file()}
actual.add("docs/swift-ordered-retention-analyzer-library-review.md")
assert actual == {row["path"] for row in seal["members"]} | set(seal["excluded"])
for attempt in ("run-1", "run-2"):
    snapshot = BASE / "snapshots" / attempt
    assert digest((snapshot / "producer-seal.json").read_bytes()) == PRODUCER_SHA
    for row in producer["members"]:
        verify_row(row, snapshot)
final = json.loads((BASE / "final-receipt.json").read_bytes())
assert final["passed"] is True and final["product_findings"] == []
assert final["producer_seal_sha256"] == PRODUCER_SHA
assert final["storedPrefixValidated"] is False and final["fullReplayAccepted"] is False
assert digest(json.dumps(final["review_source_members"], sort_keys=True, separators=(",", ":")).encode()) == final["review_source_tree_sha256"]
for row in final["review_source_members"]:
    verify_row(row)
run_path = ROOT / final["final_execution"]
run = json.loads(run_path.read_bytes())
assert run["passed"] is True and run["quiescent_before_after"] is True
for name, command in zip(("rust-version", "python-version", "compile", "execute"), run["commands"], strict=True):
    assert command["exit"] == 0
    for stream in ("stdout", "stderr"):
        assert digest((run_path.parent / (name + "." + stream)).read_bytes()) == command[stream + "_sha256"]
assert "44 passed; 0 failed" in (run_path.parent / "execute.stdout").read_text()
product = (PRODUCER / "src/analyzer.rs").read_bytes()
assert digest(product) == final["producer_source_sha256"] == run["unmodified_product_source_sha256"]
executed = (run_path.parent / "inputs/framing.rs").read_bytes()
assert executed == product + b"\n" + (BASE / "private_io_tests.rs").read_bytes()
assert digest(executed) == run["executed_product_sha256"]
assert (run_path.parent / "tests/fixture_tests.rs").read_bytes() == (PRODUCER / "tests/fixture_tests.rs").read_bytes()
assert digest((run_path.parent / "executed-independent-tests.rs").read_bytes()) == run["test_source_sha256"]
for name in ("python", "rustc"):
    assert digest(Path(final["tools"][name + "_path"]).read_bytes()) == final["tools"][name + "_sha256"]
cleanup = json.loads((BASE / "cleanup.json").read_bytes())
assert cleanup["scratch_root_absent"] and not (BASE / "scratch").exists()
archive_members = 0
for row in cleanup["owned_scratch"]:
    assert row["removed"] and not (ROOT / row["scratch"]).exists()
    archive = row["retained_owned_inputs_archive"]
    verify_row(archive)
    retained = {entry["path"]: entry for entry in row["members"] if "/" in entry["path"]}
    with tarfile.open(ROOT / archive["path"], "r:gz") as packet:
        members = packet.getmembers()
        assert len({member.name for member in members}) == len(members)
        files = [member for member in members if member.isfile() or member.islnk()]
        assert {member.name for member in files} == set(retained)
        for member in files:
            raw = packet.extractfile(member).read()
            expected = retained[member.name]
            assert len(raw) == expected["bytes"] and digest(raw) == expected["sha256"]
        archive_members += len(files)
print(json.dumps({
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "python": platform.python_version(),
    "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "script_sha256": digest(Path(__file__).read_bytes()),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "producer_seal_sha256": PRODUCER_SHA,
    "review_seal_sha256": EXPECTED,
    "review_members": len(seal["members"]),
    "review_bytes": sum(row["bytes"] for row in seal["members"]),
    "review_source_tree_sha256": final["review_source_tree_sha256"],
    "complete_producer_snapshots_verified": 2,
    "combined_final_rust_methods": 44,
    "independent_methods": 24,
    "producer_methods": 20,
    "unchanged_product_plus_test_only_append_verified": True,
    "cleanup_archives_files_verified": archive_members,
    "owned_scratch_roots_absent": 2,
    "scope": "Read-only review packet integrity and executable-output audit; fixture foundation only",
    "product_or_test_execution": False,
    "storedPrefixValidated": False,
    "fullReplayAccepted": False,
}, indent=2))
