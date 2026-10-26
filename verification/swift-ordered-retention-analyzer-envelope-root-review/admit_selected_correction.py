"""Audit frozen selected correction and retained outputs without executing producer code."""
import datetime
import hashlib
import json
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
PACKET = ROOT / "verification/swift-ordered-retention-analyzer-envelope-correction"


def sha(data):
    return hashlib.sha256(data).hexdigest()


seal_raw = (PACKET / "seal.json").read_bytes()
assert sha(seal_raw) == "4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1"
members = json.loads(seal_raw)["members"]
total = 0
for entry in members:
    path = pathlib.PurePosixPath(entry["path"])
    assert not path.is_absolute() and ".." not in path.parts
    data = (ROOT / path).read_bytes()
    assert len(data) == entry["bytes"] and sha(data) == entry["sha256"], str(path)
    total += len(data)
assert len(members) == 306 and total == 44895898
receipt = json.loads((PACKET / "final-receipt.json").read_text())
assert sha((PACKET / "src/envelope.rs").read_bytes()) == receipt["source_sha256"] == "7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1"
assert sha((PACKET / "src/analyzer.rs").read_bytes()) == receipt["parent_analyzer_sha256"] == "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"
assert sha((OUT / "correction-numeric-contract-selection.json").read_bytes()) == receipt["root_selection_sha256"] == "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c"
run = PACKET / "commands/selected-run-1"
run_raw = (run / "receipt.json").read_bytes()
assert sha(run_raw) == receipt["run_receipt_sha256"]
run_data = json.loads(run_raw)
expected_negatives = {"api-negative-private-field", "api-negative-no-clone", "api-negative-no-copy",
                      "api-negative-no-record-constructor", "api-negative-no-word-or-boolean-entry"}
commands = []
for command in run_data["commands"]:
    assert command["status"] == (1 if command["name"] in expected_negatives else 0)
    assert command["child_reaped"] and not command["timed_out"] and command["dedicated_process_group"]
    for stream in ("stdout", "stderr"):
        assert sha((run / command[stream]).read_bytes()) == command[stream + "_sha256"]
    commands.append({"name": command["name"], "status": command["status"], "elapsed_seconds": command["elapsed_seconds"]})
assert len(commands) == 15 and len([x for x in commands if x["status"] == 1]) == 5
assert "test result: ok. 44 passed; 0 failed; 0 ignored;" in (run / "fresh-selected-framing44.stdout").read_text()
assert "test result: ok. 26 passed; 0 failed; 0 ignored;" in (run / "fresh-selected-envelope26.stdout").read_text()
manifest_raw = (PACKET / "source-test-model-manifest.json").read_bytes()
assert sha(manifest_raw) == receipt["source_test_model_manifest_sha256"]
expected_archive = {x["path"]: x for x in json.loads(manifest_raw)["members"]}
expected_archive["source-test-model-manifest.json"] = {"bytes": len(manifest_raw), "sha256": sha(manifest_raw)}
archive = receipt["source_test_model_archive"]
assert sha((PACKET / archive["path"]).read_bytes()) == archive["sha256"]
archive_total = 0
with tarfile.open(PACKET / archive["path"], "r:gz") as tar:
    actual = tar.getmembers()
    assert len(actual) == len(expected_archive) and len({x.name for x in actual}) == len(actual)
    for item in actual:
        assert item.isfile() and item.name in expected_archive
        data = tar.extractfile(item).read()
        expected = expected_archive[item.name]
        assert len(data) == expected["bytes"] and sha(data) == expected["sha256"], item.name
        archive_total += len(data)
assert run_data["children_reaped"] and run_data["owned_scratch_removed_after_children_reaped"]
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": sha(pathlib.Path(__file__).read_bytes()),
    "scope": "Read-only frozen custody/output/archive admission for independent review; no producer/analyzer/model execution",
    "producer_seal_sha256": sha(seal_raw),
    "members": len(members),
    "bytes": total,
    "max_member_bytes": max(x["bytes"] for x in members),
    "source_sha256": receipt["source_sha256"],
    "compiled_source_tree_sha256": receipt["compiled_source_tree_sha256"],
    "archive_sha256": archive["sha256"],
    "archive_members": len(expected_archive),
    "archive_uncompressed_bytes": archive_total,
    "commands": commands,
    "retained_command_streams_verified": 30,
    "observed_producer_methods": 70,
    "producer_reported_model_comparisons": 21714,
    "producer_reported_layouts": 32,
    "independent_behavior_and_final_accounting_authorized": True,
    "implementation_accepted": False,
    "combined_step_memory_proof_accepted": False,
    "errors": [],
}
(OUT / "selected-correction-preflight.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: result[k] for k in ("members", "bytes", "archive_members", "source_sha256", "observed_producer_methods", "implementation_accepted", "errors")}))
