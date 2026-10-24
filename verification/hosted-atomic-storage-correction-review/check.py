#!/usr/bin/env python3
"""Read-only integrity and counterexample verification; no candidate acceptance."""
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = HERE.parent / "hosted-atomic-storage-corrected-preflight"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


seal = read(HERE / "seal.json")
manifest = read(HERE / "artifact-manifest.json")
assert sha((HERE / "artifact-manifest.json").read_bytes()) == seal["manifest_sha256"]
seen = set()
for item in manifest["files"]:
    data = (ROOT / item["path"]).read_bytes()
    assert sha(data) == item["sha256"] and len(data) == item["bytes"], item["path"]
    assert item["path"] not in seen
    seen.add(item["path"])
assert len(seen) == seal["bindings"]
receipt = read(HERE / "receipt.json")
assert receipt["status"] == "correction-required-CR01-no-complete-AS05-acceptance"
assert not any(receipt[key] for key in ["root_acceptance", "repository_acceptance", "product_implementation", "migration", "provider_or_ga_acceptance", "native_or_physical_runs", "dependency_additions", "commits_created"])
assert receipt["original_corrected_suite_summary"] == {"total": 73, "failures": 0, "skipped": 0, "excluded": 0}
assert receipt["final_adversarial_summary"] == {"total": 83, "failures": 2, "skipped": 0, "excluded": 0}

for name, bindings in [("hosted-atomic-storage-preflight", 239), ("hosted-atomic-storage-review", 134), ("hosted-atomic-storage-corrected-preflight", 269)]:
    result = subprocess.run(["python3", "-B", str(HERE.parent / name / "check.py")], cwd=ROOT, capture_output=True, text=True, check=True)
    actual = json.loads(result.stdout)
    assert actual["verified"] and actual["bindings"] == bindings

expected = [(73, 0), (81, 2), (83, 2), (83, 2)]
assert sorted(p.name for p in HERE.glob("run-*") if p.is_dir()) == [f"run-{n}" for n in range(1, 5)]
upstream = PRODUCER / "run-6/inputs"
baseline_test = (upstream / "probe/probe_test.exs").read_text()
marker = "\nend\n\nresult = ExUnit.run()"
prefix, suffix = baseline_test.split(marker)
for number, (total, failures) in enumerate(expected, 1):
    run = HERE / f"run-{number}"
    result, tests = read(run / "receipt.json"), read(run / "tests.json")
    assert result["test_summary"] == tests["summary"] == {"total": total, "failures": failures, "skipped": 0, "excluded": 0}
    assert result["passed"] == (number == 1)
    clean = result["cleanup"]
    assert all(clean[key] for key in ["owned_proxy_stopped", "owned_postgres_stopped", "owned_scratch_removed", "owned_socket_removed"])
    assert not clean["other_clusters_touched"] and not clean["native_processes_started"]
    assert not pathlib.Path(clean["owned_scratch"]).exists()
    sources = read(run / "source-manifest.json")
    assert sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) == result["probe_source_tree_digest"]
    for source in sources:
        data = (run / "inputs" / source["path"]).read_bytes()
        assert sha(data) == source["sha256"] and len(data) == source["bytes"]
        if source["path"].startswith("probe/") and source["path"] != "probe/probe_test.exs":
            assert data == (upstream / source["path"]).read_bytes(), source["path"]
    test = (run / "inputs/probe/probe_test.exs").read_text()
    assert test.startswith(prefix) and test.endswith(marker + suffix)
    if number == 1:
        assert test == baseline_test
    for contract in read(run / "contract-inputs.json"):
        assert sha((run / "inputs/contracts" / contract["path"]).read_bytes()) == contract["sha256"]
    assert (run / "dependency-source-manifest.json").read_bytes() == (PRODUCER / "run-6/dependency-source-manifest.json").read_bytes()
    commands = read(run / "commands.json")
    command = next(c for c in commands if c["argv"] == ["mix", "run", "probe_test.exs"])
    assert command["returncode"] == (0 if number == 1 else 1)
    if number > 1:
        failed = re.findall(r"\n\s+\d+\) test (I\d\d) ", command["stdout"])
        assert failed == ["I02", "I03"], failed
    wire = [json.loads(line) for line in (run / "proxy.jsonl").read_text().splitlines()]
    assert any(x.get("dropped") == "COMMIT CommandComplete" and x["server_commit_completed"] and not x["client_ack_sent"] for x in wire)
    assert tests["observations"]["uncertain_commit_restart"]["exact_original_retry"]
    if number != 2:
        assert sha((run / "installed-catalog.json").read_bytes()) == "5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883"

final = read(HERE / "run-4/tests.json")["observations"]
assert len(final["independent_canonical_suffixes"]) == 312
assert all(x["elixir"] == "rejected" and x["postgres"] == "rejected" for x in final["independent_canonical_suffixes"])
assert len(final["independent_unicode_display"]) == 45
assert all(x["codecs_equal"] for x in final["independent_unicode_display"])
assert [x["text_hex"] for x in final["independent_unicode_display"] if not x["display_equal"]] == ["0b", "0e", "0f", "1a", "1b", "1c", "1d", "1e", "1f"]
assert final["independent_pre_effect_observation"]["rejected_attempts_never_called_trigger"]
assert final["independent_pre_effect_observation"]["positive_insert_and_audit_called_trigger_twice"]
assert final["independent_pre_effect_observation"]["review_instrumentation_dropped_after_case"]
assert final["independent_literal_escape_control"]["cases"] == 10
assert final["independent_literal_escape_control"]["literal_case_and_text_unchanged"]
assert len(final["independent_private_execute"]) == 19
assert all(x["runtime_denied"] and x["foreign_denied"] for x in final["independent_private_execute"])
assert len(read(HERE / "findings.json")["findings"]) == 1
oracle = subprocess.run(["python3", "-B", str(HERE / "row-oracle.py")], cwd=ROOT, capture_output=True, text=True, check=True)
assert json.loads(oracle.stdout)["actual_retained_rows"] == 8
print(json.dumps({"verified": True, "bindings": len(seen), "original_corrected_suite": receipt["original_corrected_suite_summary"], "final_adversarial_suite": receipt["final_adversarial_summary"], "preserved_known_contract_failures": ["I02", "I03"], "mandatory_findings": ["CR01"], "actual_catalog_sha256": receipt["installed_catalog_sha256"], "all_four_owned_cleanup_verified": True, "root_acceptance": False, "repository_acceptance": False, "full_as05_acceptance": False}))
