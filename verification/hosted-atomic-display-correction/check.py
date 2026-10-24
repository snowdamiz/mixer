#!/usr/bin/env python3
"""Read-only frozen evidence checker; does not accept or integrate the candidate."""
import difflib
import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCUMENT = ROOT / "docs/hosted-atomic-display-correction.md"
CATALOG = "5824cfe3629e65e2da8dcf4d831a10f22589a5b2bd38c02bbf58f90d23971883"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify_item(base, item):
    relative = pathlib.PurePosixPath(item["path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    data = (base / relative).read_bytes()
    assert sha(data) == item["sha256"] and len(data) == item["bytes"], str(relative)


seal, manifest, receipt = (read(HERE / name) for name in ["seal.json", "artifact-manifest.json", "receipt.json"])
assert sha((HERE / "artifact-manifest.json").read_bytes()) == seal["manifest_sha256"]
assert sha((HERE / "receipt.json").read_bytes()) == seal["receipt_sha256"]
seen = set()
for item in manifest["files"]:
    verify_item(ROOT, item)
    assert item["path"] not in seen
    seen.add(item["path"])
assert len(seen) == seal["bindings"]
actual_files = {str(path.relative_to(ROOT)) for path in HERE.rglob("*") if path.is_file() and path not in {HERE / "artifact-manifest.json", HERE / "seal.json"}}
assert seen == actual_files | {str(DOCUMENT.relative_to(ROOT))}
assert receipt["status"] == "isolated-display-correction-passed-independent-review-pending"
assert receipt["independent_review_pending"] and seal["independent_review_pending"]
for key in ["root_acceptance", "repository_acceptance", "full_as05_acceptance", "product_implementation", "migration", "provider_or_ga_acceptance", "native_or_physical_runs", "dependency_additions", "commits_created"]:
    assert receipt[key] is False, key
for item in read(HERE / "upstream-inputs.json")["files"]:
    verify_item(ROOT, item)
assert len(read(HERE / "upstream-inputs.json")["files"]) == receipt["upstream_bindings_verified"] == 488
assert sha((ROOT / "verification/hosted-atomic-storage-correction-review/receipt.json").read_bytes()) == receipt["upstream_final_review_receipt_sha256"]
assert sha((ROOT / "verification/hosted-atomic-storage-correction-review/seal.json").read_bytes()) == receipt["upstream_final_review_seal_sha256"]
validation = read(HERE / "upstream-validation.json")
assert validation["returncode"] == 0 and json.loads(validation["stdout"])["bindings"] == 213
assert sha(validation["stdout"].encode()) == validation["stdout_sha256"]
assert sha(validation["stderr"].encode()) == validation["stderr_sha256"]

base = ROOT / receipt["frozen_base"] / "probe"
for path in (HERE / "upstream/producer-probe").rglob("*"):
    if path.is_file():
        assert path.read_bytes() == (base / path.relative_to(HERE / "upstream/producer-probe")).read_bytes()
reviewer = HERE / "upstream/reviewer-probe_test.exs"
assert reviewer.read_bytes() == (ROOT / "verification/hosted-atomic-storage-correction-review/run-4/inputs/probe/probe_test.exs").read_bytes()
original_codec = (base / "lib/codec.ex").read_text()
candidate_codec = (HERE / "probe/lib/codec.ex").read_text()
formatter_start, formatter_end = "  def postgres_display(v) when is_map(v) do", "  defp ensure(true, _)"
assert original_codec.split(formatter_start)[0] == candidate_codec.split(formatter_start)[0]
assert original_codec.split(formatter_end)[1] == candidate_codec.split(formatter_end)[1]
expected_patch = "".join(difflib.unified_diff(original_codec.splitlines(True), candidate_codec.splitlines(True), fromfile="frozen-producer/lib/codec.ex", tofile="corrected-specimen/lib/codec.ex"))
assert (HERE / "formatter-only.patch").read_text() == expected_patch
for path in (HERE / "probe").rglob("*"):
    if path.is_file() and str(path.relative_to(HERE / "probe")) not in ["lib/codec.ex", "probe_test.exs"]:
        assert path.read_bytes() == (base / path.relative_to(HERE / "probe")).read_bytes(), path
marker = "\nend\n\nresult = ExUnit.run()"
prefix, suffix = reviewer.read_text().split(marker)
focused_marker = marker.replace("result = ExUnit.run()", 'if System.get_env("MXAS_FOCUSED") == "1", do: ExUnit.configure(exclude: [:test], include: [:display_correction])\n\nresult = ExUnit.run()')
assert (HERE / "probe/probe_test.exs").read_text() == prefix + "\n\n" + (HERE / "display-cases.exs").read_text() + focused_marker + suffix
assert len(re.findall(r'^  test "', reviewer.read_text(), re.M)) == 83
assert len(re.findall(r'^  test "', (HERE / "display-cases.exs").read_text(), re.M)) == 5
assert read(HERE / "exact-delta.json")["all_other_implementation_files_byte_identical"]

expected = [("baseline", 83, 2, 0, False), ("full", 88, 1, 0, False), ("full", 88, 0, 0, True), ("focused", 88, 0, 83, True)]
assert sorted(path.name for path in HERE.glob("run-*") if path.is_dir()) == ["run-1", "run-2", "run-3", "run-4"]
for number, (mode, total, failures, excluded, passed) in enumerate(expected, 1):
    run = HERE / f"run-{number}"
    result, tests = read(run / "receipt.json"), read(run / "tests.json")
    assert result["mode"] == mode and result["passed"] == passed
    assert result["test_summary"] == tests["summary"] == {"total": total, "failures": failures, "skipped": 0, "excluded": excluded}
    assert result["verified_upstream_bindings"] == 488
    assert result["independent_review_pending"] and not result["root_acceptance"] and not result["repository_acceptance"]
    clean = result["cleanup"]
    assert all(clean[key] for key in ["owned_proxy_stopped", "owned_postgres_stopped", "owned_scratch_removed", "owned_socket_removed"])
    assert not clean["other_clusters_touched"] and not clean["native_processes_started"]
    assert not pathlib.Path(clean["owned_scratch"]).exists()
    sources = read(run / "source-manifest.json")
    assert sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) == result["probe_source_tree_digest"]
    for item in sources:
        verify_item(run / "inputs", item)
    for item in read(run / "contract-inputs.json"):
        verify_item(run / "inputs/contracts", item)
    for item in read(run / "legacy-source-manifest.json"):
        verify_item(run / "inputs", item)
        assert (run / "inputs" / item["path"]).read_bytes() == (HERE / "legacy-services" / pathlib.Path(item["path"]).relative_to("services")).read_bytes()
    assert (run / "accepted-baseline.mix.lock").read_bytes() == (HERE / "accepted-baseline.mix.lock").read_bytes()
    assert (run / "dependency-source-manifest.json").read_bytes() == (HERE.parent / "hosted-atomic-storage-corrected-preflight/run-6/dependency-source-manifest.json").read_bytes()
    for path in (run / "inputs/probe").rglob("*"):
        if path.is_file() and str(path.relative_to(run / "inputs/probe")) not in ["lib/codec.ex", "probe_test.exs"]:
            assert path.read_bytes() == (base / path.relative_to(run / "inputs/probe")).read_bytes()
    codec = (run / "inputs/probe/lib/codec.ex").read_text()
    test = (run / "inputs/probe/probe_test.exs").read_text()
    assert codec == (original_codec if number == 1 else candidate_codec)
    if number == 1:
        assert test == reviewer.read_text()
        assert result["expected_baseline_failure_reproduced"]
    else:
        assert test.startswith(prefix) and test.endswith(focused_marker + suffix)
        if number == 2:
            old = '    refute scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e")'
            new = '    assert_raise Postgrex.Error, fn -> scalar("SELECT mixer_hosted_release.row_valid(e) FROM mixer_hosted_release.audit_events e") end'
            assert test.replace(old, new) == (HERE / "probe/probe_test.exs").read_text()
        else:
            assert test == (HERE / "probe/probe_test.exs").read_text()
    commands = read(run / "commands.json")
    for command in commands:
        for stream in ["stdout", "stderr"]:
            if stream + "_sha256" in command:
                assert sha((command.get(stream) or "").encode()) == command[stream + "_sha256"]
    mix = next(command for command in commands if command["argv"] == ["mix", "run", "probe_test.exs"])
    assert mix["returncode"] == (1 if number <= 2 else 0)
    failed_names = re.findall(r"\n\s+\d+\) test ((?:I|D)\d\d) ", mix["stdout"])
    assert failed_names == (["I02", "I03"] if number == 1 else ["D05"] if number == 2 else [])
    assert sha((run / "installed-catalog.json").read_bytes()) == CATALOG
    if mode != "focused":
        wire = [json.loads(line) for line in (run / "proxy.jsonl").read_text().splitlines()]
        assert any(item.get("dropped") == "COMMIT CommandComplete" and item["server_commit_completed"] and not item["client_ack_sent"] for item in wire)
        assert tests["observations"]["uncertain_commit_restart"]["exact_original_retry"]

full = read(HERE / "run-3/tests.json")["observations"]
assert len(full["independent_canonical_suffixes"]) == 312
assert all(item["elixir"] == "rejected" and item["postgres"] == "rejected" for item in full["independent_canonical_suffixes"])
assert len(full["independent_unicode_display"]) == 45
assert all(item["codecs_equal"] and item["display_equal"] for item in full["independent_unicode_display"])
assert len(full["independent_uploaded_unicode"]) == 8
assert all(item["sql_row"] and item["elixir_row"] == "accepted" and item["exact_replay"] for item in full["independent_uploaded_unicode"])
assert full["independent_pre_effect_observation"]["rejected_attempts_never_called_trigger"]
assert full["independent_pre_effect_observation"]["positive_insert_and_audit_called_trigger_twice"]
assert full["independent_pre_effect_observation"]["review_instrumentation_dropped_after_case"]
assert all(item["runtime_denied"] and item["foreign_denied"] for item in full["independent_private_execute"])
assert len(full["independent_private_execute"]) == 19
assert full["display_correction_uploaded_rows"]["count"] == 56
assert all(item["exact_replay"] and item["sql_row"] and item["elixir_row"] == "accepted" for item in full["display_correction_uploaded_rows"]["rows"])
controls = {bytes.fromhex(item["text_hex"]) for item in full["display_correction_parity"]["cases"]}
assert all(bytes([control]) in controls for control in list(range(1, 32)) + [127])
assert b"\\u000B" in controls and b"\\u000b" in controls
assert full["display_correction_exact_equality"]["case_variant_rejected_by_both_rows"]
assert full["display_correction_byte_bounds"]["limits_not_changed"]
assert full["display_correction_invalid_storage"]["successful_invalid_rows"] == 0
assert full["display_correction_invalid_storage"]["valid_surrogate_pair_control"]
for run, expected_rows in [("run-3", 64), ("run-4", 56)]:
    oracle = subprocess.run(["python3", "-B", str(HERE / "row-oracle.py"), run], cwd=ROOT, capture_output=True, text=True, check=True)
    assert json.loads(oracle.stdout)["actual_retained_rows"] == expected_rows
print(json.dumps({"verified": True, "bindings": len(seen), "upstream_bindings": 488, "full_summary": receipt["full_summary"], "focused_summary": receipt["focused_summary"], "original_assertions_preserved": 83, "all_four_owned_cleanups_verified": True, "actual_retained_rows_cross_checked": 64, "independent_review_pending": True, "root_acceptance": False, "repository_acceptance": False, "full_as05_acceptance": False}))
