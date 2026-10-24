#!/usr/bin/env python3
"""Frozen read-only independent formatter review checker; no integration authority."""
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/hosted-atomic-display-correction"
CODEC_SHA = "7152ab6d9c2fec56cd6e707ef09bb4f5fb3a8477edb7b0b5410a884278fe37ee"
CATALOG_SHA = "5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify(base, item):
    name = pathlib.PurePosixPath(item["path"])
    assert not name.is_absolute() and ".." not in name.parts
    data = (base / name).read_bytes()
    assert len(data) == item["bytes"] and sha(data) == item["sha256"], name


def cleanup(result):
    clean = result["cleanup"]
    for key in ["owned_proxy_stopped", "owned_postgres_stopped", "owned_scratch_removed", "owned_socket_removed"]:
        assert clean[key] is True, key
    assert not clean["other_clusters_touched"] and not clean["native_processes_started"]
    assert not pathlib.Path(clean["owned_scratch"]).exists()


seal, receipt, manifest = [read(HERE / x) for x in ["seal.json", "receipt.json", "artifact-manifest.json"]]
assert sha((HERE / "artifact-manifest.json").read_bytes()) == seal["manifest_sha256"]
assert sha((HERE / "receipt.json").read_bytes()) == seal["receipt_sha256"]
seen = set()
for item in manifest["files"]:
    verify(ROOT, item)
    assert item["path"] not in seen
    seen.add(item["path"])
assert len(seen) == seal["bindings"]
actual = {str(x.relative_to(ROOT)) for x in HERE.rglob("*") if x.is_file() and x not in [HERE / "artifact-manifest.json", HERE / "seal.json"]}
assert seen == actual | {"docs/hosted-atomic-display-review.md"}
assert receipt["status"] == "independent-review-recommends-formatter-only-CR01-acceptance"
assert receipt["reviewer_accepts_formatter_correction"] is True
assert receipt["root_acceptance"] is False and receipt["repository_acceptance"] is False
for key in ["full_as05_acceptance", "production_startup_catalog_acceptance", "combined_authority_schema_acceptance", "product_implementation", "migration", "provider_or_ga_acceptance", "native_or_physical_runs", "dependency_additions", "commits_created"]:
    assert receipt[key] is False, key
review_inputs = read(HERE / "review-inputs.json")["files"]
assert len(review_inputs) == 1509
for item in review_inputs:
    verify(ROOT, item)
for result in read(HERE / "upstream-validation.json"):
    assert result["returncode"] == 0
    for stream in ["stdout", "stderr"]:
        assert sha(result[stream].encode()) == result[stream + "_sha256"]
assert json.loads(read(HERE / "upstream-validation.json")[0]["stdout"])["bindings"] == 213
assert json.loads(read(HERE / "upstream-validation.json")[1]["stdout"])["bindings"] == 1019
assert sha((PRODUCER / "receipt.json").read_bytes()) == "ebecf05358733c2a2069907ecc5e3e693ec9c484e594a8dd10a44eace76f8c91"
assert sha((PRODUCER / "seal.json").read_bytes()) == "ae01864e0b82003141d627109c6a37a3a0bb7ec4b384193878b77ed28fa0b0a7"
assert (HERE / "run.py").read_bytes() == (HERE / "replay-runner.py").read_bytes() == (PRODUCER / "run.py").read_bytes()
assert sha((HERE / "probe/lib/codec.ex").read_bytes()) == CODEC_SHA
for path in (PRODUCER / "probe").rglob("*"):
    if path.is_file() and path.name != "probe_test.exs":
        assert path.read_bytes() == (HERE / "probe" / path.relative_to(PRODUCER / "probe")).read_bytes()
base = ROOT / "verification/hosted-atomic-storage-corrected-preflight/run-6/inputs/probe"
changed = []
for path in (PRODUCER / "probe").rglob("*"):
    if path.is_file() and path.name != "probe_test.exs" and path.read_bytes() != (base / path.relative_to(PRODUCER / "probe")).read_bytes():
        changed.append(str(path.relative_to(PRODUCER / "probe")))
assert changed == ["lib/codec.ex"]
original, corrected = [(x / "lib/codec.ex").read_text() for x in [base, PRODUCER / "probe"]]
start, end = "  def postgres_display(v) when is_map(v) do", "  defp ensure(true, _)"
assert original.split(start)[0] == corrected.split(start)[0]
assert original.split(end)[1] == corrected.split(end)[1]
assert "display_bytes == postgres_display(d)" in corrected
prior = (ROOT / "verification/hosted-atomic-storage-correction-review/run-4/inputs/probe/probe_test.exs").read_text()
marker = "\nend\n\nresult = ExUnit.run()"
prefix, suffix = prior.split(marker)
candidate = (PRODUCER / "probe/probe_test.exs").read_text()
assert candidate.startswith(prefix) and candidate.endswith(suffix)
assert len(re.findall(r'^  test "', prior, re.M)) == 83
assert len(re.findall(r'^  test "', candidate, re.M)) == 88
review_marker = '\nend\n\nif System.get_env("MXAS_FOCUSED")'
extension = "\n\n" + (HERE / "review-cases.exs").read_text()
assert (HERE / "probe/probe_test.exs").read_text() == candidate.replace(review_marker, extension + review_marker)
assert len(re.findall(r'^  test "', (HERE / "probe/probe_test.exs").read_text(), re.M)) == 94
assert sorted(x.name for x in HERE.glob("run-*") if x.is_dir()) == ["run-1", "run-2"]
for number, total in [(1, 88), (2, 94)]:
    run = HERE / f"run-{number}"
    result, tests = read(run / "receipt.json"), read(run / "tests.json")
    assert result["passed"] and result["error"] is None and result["mode"] == "full"
    assert tests["summary"] == result["test_summary"] == {"total": total, "failures": 0, "skipped": 0, "excluded": 0}
    assert result["observed_head"] == "4250e05a132c04370d5ccb971c9faaf1b82a9395"
    assert result["verified_upstream_bindings"] == 488
    assert not result["root_acceptance"] and not result["repository_acceptance"]
    cleanup(result)
    sources = read(run / "source-manifest.json")
    assert sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) == result["probe_source_tree_digest"]
    for item in sources:
        verify(run / "inputs", item)
    for item in read(run / "contract-inputs.json"):
        verify(run / "inputs/contracts", item)
    for item in read(run / "legacy-source-manifest.json"):
        verify(run / "inputs", item)
    assert (run / "accepted-baseline.mix.lock").read_bytes() == (HERE / "accepted-baseline.mix.lock").read_bytes()
    assert (run / "dependency-source-manifest.json").read_bytes() == (PRODUCER / "run-3/dependency-source-manifest.json").read_bytes()
    assert sha((run / "inputs/probe/lib/codec.ex").read_bytes()) == CODEC_SHA
    assert sha((run / "installed-catalog.json").read_bytes()) == result["installed_catalog_sha256"] == CATALOG_SHA
    if number == 1:
        assert (run / "inputs/probe/probe_test.exs").read_text() == candidate
        assert result["probe_source_tree_digest"] == "1beaec6474ddb51257ca8eda34c47777344019d4e02c4213ea5e1030cc9fcd0c"
    else:
        assert (run / "inputs/probe/probe_test.exs").read_bytes() == (HERE / "probe/probe_test.exs").read_bytes()
        assert (run / "inputs/probe/review-corpus.json").read_bytes() == (HERE / "probe/review-corpus.json").read_bytes()
    for command in read(run / "commands.json"):
        for stream in ["stdout", "stderr"]:
            if stream + "_sha256" in command:
                assert sha((command.get(stream) or "").encode()) == command[stream + "_sha256"]
    mix = [x for x in read(run / "commands.json") if x["argv"] == ["mix", "run", "probe_test.exs"]]
    assert len(mix) == 1 and mix[0]["returncode"] == 0
    wire = [json.loads(line) for line in (run / "proxy.jsonl").read_text().splitlines()]
    assert any(x.get("dropped") == "COMMIT CommandComplete" and x["server_commit_completed"] and not x["client_ack_sent"] for x in wire)
    observations = tests["observations"]
    assert observations["uncertain_commit_restart"]["exact_original_retry"] and observations["uncertain_commit_restart"]["no_duplicate_event"]
    assert "server stopped" in observations["uncertain_commit_restart"]["stop_output"]
    assert "server started" in observations["uncertain_commit_restart"]["start_output"]
    pre = observations["independent_pre_effect_observation"]
    assert all(pre[k] for k in ["before_dml_trigger_sequence_is_nontransactional", "rejected_attempts_never_called_trigger", "positive_insert_and_audit_called_trigger_twice", "no_candidate_function_was_modified", "review_instrumentation_dropped_after_case"])
    for name in ["expiry", "stale46", "unexpired139"]:
        assert pre[name]["pg_observed_wait"]
    assert len(observations["independent_private_execute"]) == 19
    assert all(x["runtime_denied"] and x["foreign_denied"] for x in observations["independent_private_execute"])
for number in range(1, 5):
    cleanup(read(PRODUCER / f"run-{number}/receipt.json"))
assert read(PRODUCER / "run-1/tests.json")["summary"] == {"total": 83, "failures": 2, "skipped": 0, "excluded": 0}
assert read(PRODUCER / "run-2/tests.json")["summary"] == {"total": 88, "failures": 1, "skipped": 0, "excluded": 0}
assert read(PRODUCER / "run-4/tests.json")["summary"] == {"total": 88, "failures": 0, "skipped": 0, "excluded": 83}
assert read(HERE / "findings.json")["resolved"] == ["CR01"]
assert read(HERE / "findings.json")["new_blocking_findings"] == []
oracle = subprocess.run(["python3", "-B", str(HERE / "byte-oracle.py")], cwd=ROOT, capture_output=True, text=True, check=True)
assert json.loads(oracle.stdout)["actual_chain_rows_cross_checked"] == 185
print(json.dumps({"verified": True, "bindings": len(seen), "review_input_bindings": 1509,
                  "producer_bindings": 1019, "upstream_bindings": 488, "original_assertions_preserved": 83,
                  "exact_replay": {"total": 88, "failures": 0, "skipped": 0, "excluded": 0},
                  "independent_expanded": {"total": 94, "failures": 0, "skipped": 0, "excluded": 0},
                  "actual_chain_rows_cross_checked": 185, "producer_cleanups": 4, "review_cleanups": 2,
                  "formatter_only_acceptance_recommended": True, "root_acceptance": False,
                  "repository_acceptance": False, "full_as05_acceptance": False,
                  "production_startup_catalog_acceptance": False, "combined_authority_schema_acceptance": False}))
