#!/usr/bin/env python3
"""Read-only reviewer freeze checker; does not start PostgreSQL or accept product work."""
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = HERE.parent / "hosted-atomic-storage-preflight"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path):
    return json.loads(path.read_text())


seal = read(HERE / "seal.json")
manifest = read(HERE / "artifact-manifest.json")
assert sha((HERE / "artifact-manifest.json").read_bytes()) == seal["manifest_sha256"]
seen = set()
for item in manifest["files"]:
    path = ROOT / item["path"]
    value = path.read_bytes()
    assert len(value) == item["bytes"] and sha(value) == item["sha256"], item["path"]
    assert item["path"] not in seen
    seen.add(item["path"])
assert len(seen) == seal["bindings"]

producer_check = subprocess.run(
    ["python3", "-B", str(PRODUCER / "check.py")],
    cwd=ROOT, capture_output=True, text=True, check=True,
)
producer_result = json.loads(producer_check.stdout)
assert producer_result["bindings"] == 239
assert producer_result["source_tree_digest"] == "0f72c5b18c333f74b27f58ff17707fc909175a0c9ea4cf974c3015fb65007d7e"
assert producer_result["all_owned_cleanup_verified"]

receipt = read(HERE / "receipt.json")
assert receipt["status"] == "mechanics-only-recommended-with-mandatory-corrections"
assert not any(receipt[key] for key in [
    "product_implementation", "product_repository_accepted", "full_typed_validation_pass",
    "root_acceptance", "migration", "provider_http_ga_acceptance", "producer_packet_mutated",
    "tracker_mutation", "commits_created", "native_or_physical_runs", "dependency_additions",
])
assert receipt["original_cases"] == 41 and receipt["independently_authored_cases"] == 20
assert receipt["summary"] == {"total": 61, "failures": 0, "skipped": 0, "excluded": 0}

attempts = receipt["all_attempts"]
assert [item["run"] for item in attempts] == ["run-1", "run-2", "run-3"]
assert [item["test_summary"]["total"] for item in attempts] == [57, 60, 61]
for attempt in attempts:
    directory = HERE / attempt["run"]
    actual = read(directory / "receipt.json")
    tests = read(directory / "tests.json")
    assert actual["passed"] and actual["error"] is None
    assert tests["summary"] == attempt["test_summary"] == actual["test_summary"]
    assert all(tests["summary"][key] == 0 for key in ["failures", "skipped", "excluded"])
    cleanup = actual["cleanup"]
    assert cleanup == attempt["cleanup"]
    assert all(cleanup[key] for key in ["owned_proxy_stopped", "owned_postgres_stopped", "owned_scratch_removed", "owned_socket_removed"])
    assert not cleanup["other_clusters_touched"] and not cleanup["native_processes_started"]
    assert not pathlib.Path(cleanup["owned_scratch"]).exists()
    sources = read(directory / "source-manifest.json")
    digest = sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode())
    assert digest == actual["probe_source_tree_digest"] == attempt["source_tree_digest"]
    for item in sources:
        assert sha((directory / "inputs" / item["path"]).read_bytes()) == item["sha256"]
        if attempt["run"] == receipt["passing_run"]:
            assert sha((HERE / item["path"]).read_bytes()) == item["sha256"]
    for item in read(directory / "contract-inputs.json"):
        assert sha((directory / "inputs/contracts" / item["path"]).read_bytes()) == item["sha256"]
    assert (directory / "dependency-source-manifest.json").read_bytes() == (PRODUCER / "run-8/dependency-source-manifest.json").read_bytes()
    commands = read(directory / "commands.json")
    go = [command for command in commands if command["argv"][:2] in [["go", "test"], ["go", "run"]]]
    assert len(go) == 2 and all(command["returncode"] == 0 for command in go)
    proxy = [json.loads(line) for line in (directory / "proxy.jsonl").read_text().splitlines()]
    assert any(item.get("dropped") == "COMMIT CommandComplete" and item["server_commit_completed"] and not item["client_ack_sent"] for item in proxy)
    for name in ["schema.sql", "lib/context.ex", "lib/codec.ex", "lib/blob.ex", "lib/bounds.ex", "proxy.py", "mix.exs"]:
        assert (directory / "inputs/probe" / name).read_bytes() == (PRODUCER / "run-8/inputs/probe" / name).read_bytes()

final = HERE / receipt["passing_run"]
observations = read(final / "tests.json")["observations"]
assert observations["review_numeric_typmod_rounding"]["post_cast"] == [["150", "0", True, True]]
assert observations["review_expiry_validation_gap"]["all_accepted_by_specimen"]
assert observations["review_idempotency_material_gap"]["changed_status_and_body_returned"]
assert observations["review_idempotency_event_gap"]["wrong_existing_event_accepted"]
assert observations["review_expiry_before_effect_gap"]["actual_relation_lock_wait_confirmed"]
assert observations["review_expiry_before_effect_gap"]["expiry"] == observations["review_expiry_before_effect_gap"]["clock_at_insert"] == "140"
assert observations["review_expiry_before_effect_gap"]["completion_still_within_age45"]
for key in ["review_policy_after_wait", "review_expiry_after_wait", "review_completion_after_wait"]:
    assert observations[key]["actual_runtime_lock_wait_confirmed"]
assert observations["review_uint64_independent"]["vector_count"] == 120
for vector in read(HERE / "probe/review-uint64-vectors.json"):
    number = int(vector["decimal"])
    if number < 24:
        expected = bytes([number])
    else:
        width = next(width for width in [1, 2, 4, 8] if number < 256 ** width)
        expected = bytes([{1: 24, 2: 25, 4: 26, 8: 27}[width]]) + number.to_bytes(width, "big")
    assert vector["cbor_hex"] == expected.hex()

findings = read(HERE / "findings.json")["findings"]
assert [finding["id"] for finding in findings] == ["F01", "F02", "F03", "F04", "F05", "F06", "F07"]
assert all(finding["reproduced"] and finding["required_before_repository_acceptance"] and not finding["corrected_in_this_review"] for finding in findings)
assert not seal["root_accepted"]
print(json.dumps({
    "verified": True, "bindings": len(seen), "passing_run": final.name,
    "summary": receipt["summary"], "source_tree_digest": receipt["review_source_tree_digest"],
    "producer_bindings_reverified": 239, "all_three_review_cleanup_verified": True,
    "mandatory_uncorrected_findings": len(findings),
    "recommendation": "mechanics-only; no repository or full typed validation acceptance",
    "root_accepted": False,
}))
