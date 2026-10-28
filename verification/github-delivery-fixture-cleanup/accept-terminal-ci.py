"""Accept only the remotely tested fixture correction, preserving failed harnesses."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
DEST = OUT / "terminal-acceptance.json"

def read(path):
    return json.loads(path.read_bytes())

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

assert not DEST.exists(), "One-shot; do not replay"
delivery = read(OUT / "receipt.json")
commit = delivery["commit"]
assert commit == "a4f1d13fe83415377e84b3fc33869e667da30fae"
phoenix = read(OUT / "ci-jobs-3.stdout")
engine = read(OUT / "ci-jobs-4.stdout")
for run in [phoenix, engine]:
    assert run["headSha"] == commit and run["status"] == "completed"
    assert run["conclusion"] == "success" and run["attempt"] == 1
    assert all(job["conclusion"] == "success" for job in run["jobs"])
    assert all(step["conclusion"] == "success" for job in run["jobs"] for step in job["steps"])
assert len(engine["jobs"]) == 6 and sum(len(x["steps"]) for x in engine["jobs"]) == 64
assert len(phoenix["jobs"]) == 1 and len(phoenix["jobs"][0]["steps"]) == 13
artifact = OUT / "phoenix-remote-artifact"
r = read(artifact / "receipt.json")
assert r["status"] == "passed" and r["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
assert (artifact / "revision.log").read_text().strip() == commit
assert (artifact / "compile.log").read_text() == "Compiling 95 files (.ex)\nGenerated mixer_hosted app\n"
assert not (artifact / "format.log").read_bytes()
assert all(c["exit_code"] == c.get("expected_exit_code", 0) for c in r["commands"])
assert next(c for c in r["commands"] if c["label"] == "compile")["argv"] == ["mix", "compile", "--warnings-as-errors"]
tests = (artifact / "tests.log").read_text()
assert "Result: 690 passed, 2 skipped" in tests and "Failed: " not in tests
plan = read(ROOT / "verification/console-key-owner-fixture-cleanup-ci-correction/prepared-4/execution-plan.json")
assert all(name in tests for name in plan["selection"]["tests"])
paths = ["hosted/test/mixer_hosted/identity/key_owner_test.exs",
         "hosted/lib/mixer_hosted/identity/admission.ex", "hosted/lib/mixer_hosted/identity/key_owner.ex",
         "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"]
for path in paths:
    assert row(ROOT / path)["sha256"] == r["inputs"][path]
acceptance = {"status": "accepted-remote-host-fixture-supervision-correction", "commit": commit,
              "canonical_source": row(ROOT / paths[0]), "canonical_product_changed": False,
              "Engine": {"run": engine["databaseId"], "url": engine["url"], "jobs": 6, "steps": 64, "attempt": 1, "skipped_steps": 0},
              "Phoenix": {"run": phoenix["databaseId"], "url": phoenix["url"], "steps": 13, "attempt": 1,
                          "compiled_files": 95, "compile_warnings": 0, "formatting_passed": True,
                          "tests_passed": 690, "existing_tests_skipped": 2, "selected_regression_names": plan["selection"]["tests"],
                          "Elixir": "1.20.4", "OTP": "29", "PostgreSQL": "16.15", "cleanup": r["cleanup"],
                          "receipt": row(artifact / "receipt.json"), "test_log": row(artifact / "tests.log")},
              "matched_remote_source_hashes": {p: r["inputs"][p] for p in paths},
              "local_harness_failures_preserved": True, "local_runtime_acceptance_claim": False,
              "pending": ["In-flight lifecycle desired-property tests and explicit OpenSSL wrapper custody",
                          "Separately selected Bandit/JOSE advisory correction and post-upgrade validation",
                          "Production provider/browser/session/ingress/operations, native/device and GA qualification"],
              "callback_independent_storage_acceptance_or_replay": False, "GA_accepted": False}
w = read(ROOT / "work-graph.json")
g = read(ROOT / "gates/ga.json")
f = w["packages"][13]["fixedWorkspaceDispatcher"]
assert f == g["gates"][21]["fixedWorkspaceDispatcher"]
correction = f["key_owner_supervised_lifecycle"]["fixture_cleanup_correction"]
correction["status"] = acceptance["status"]
correction["acceptance"] = copy.deepcopy(acceptance)
correction["delivery"]["status"] = "Engine-and-Phoenix-passed-attempt-one"
g["gates"][21]["fixedWorkspaceDispatcher"] = copy.deepcopy(f)
c = w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c == g["gates"][1]["fixtureCacheStateContractCandidate"]
b = c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_accounting_join"]["delivery"]["status"] = "Engine-and-Phoenix-passed-attempt-one"
g["gates"][1]["fixtureCacheStateContractCandidate"] = copy.deepcopy(c)
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
old = "Checkpoint `a4f1d13f` is pushed with 197 selected paths. The only canonical change makes KeyOwnerTest fixture teardown explicitly supervised; zero-warning source compilation passes, while full Engine and Phoenix CI are running. The closed Swift accounting join and dispatch/lifetime source contract are included. Unfinished local TLS harness and model implementation remain excluded, with no new runtime or GA acceptance."
new = "Checkpoint `a4f1d13f` is pushed with 197 selected paths. The test-only KeyOwnerTest supervision correction now has remote host acceptance: Phoenix passes all thirteen steps, 95-file zero-warning compilation, formatting and 690 tests, with two existing skips; all six previously failing teardown cases and K07g pass. PostgreSQL16.15 and scratch cleanup complete, and the remote source hash matches the correction. Engine passes all six jobs and 64 steps on attempt one without skips. The closed Swift accounting join and dispatch/lifetime source contract are included. Unfinished local TLS harness and model implementation remain excluded; their separate failures and pending gates are preserved."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new, 1))
assert sum(x["status"] == "running" for x in g["gates"]) == 8
assert sum(x["status"] == "planned" for x in g["gates"]) == 30
with DEST.open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "acceptance": acceptance,
               "artifact_selection": row(OUT / "artifact-selection.json"), "GA_verified": 0}, handle, indent=2)
    handle.write("\n")
print(json.dumps({"accepted": commit, "tests_passed": 690, "existing_skips": 2, "Engine_jobs": 6, "GA_verified": 0}))
