"""Prepare a test-only CI correction; local TLS harness qualification is pending."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent

def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

assert not (OUT / "source-review.json").exists(), "One-shot; do not replay"
lane = ROOT / "verification/console-key-owner-fixture-cleanup-ci-correction"
plan = json.loads((lane / "prepared-4/execution-plan.json").read_bytes())
test = ROOT / "hosted/test/mixer_hosted/identity/key_owner_test.exs"
expected = next(x for x in plan["canonical_inputs"] if x["path"] == str(test.relative_to(ROOT)))
assert row(test) == expected
observed = lane / "executions/candidate-3"
log = (observed / "corrected/stdout.txt").read_text()
assert "COMPILED 19 frozen accepted identity modules; warnings=0" in log
assert "COMPILED 4 frozen canonical support modules; warnings=0" in log
assert "COMPILED 1 full canonical KeyOwnerTest module; warnings=0" in log
assert "** (KeyError) key :test not found" in log
receipt = json.loads((observed / "receipt.json").read_bytes())
assert receipt["status"] == "failed"
for name in ["receipt.json", "observations.json", "corrected/stdout.txt"]:
    destination = OUT / "local-pretest-failure" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write((observed / name).read_bytes())

review = {"status": "source-reviewed-test-correction-awaiting-full-remote-CI",
          "canonical_source": row(test), "base": "fd92138ac0b8c4ecd0d872a9050204da5ceb5d2f",
          "problem": "Six existing fixture on_exit callbacks race the new correct linked-owner shutdown.",
          "change": "ExUnit supervises the temporary fixture owner after its worker supervisor; reverse child teardown drains the owner first. on_exit only asserts owner/worker/name/table/admission cleanup. K07g verifies the intentionally stopped temporary owner stays absent.",
          "reviewer": "root independently reviewed the canonical helper and exact two-hunk diff; prior independent fixture reviews remain preserved",
          "local_compile": {"product_modules": 19, "support_modules": 4, "test_modules": 1, "warnings": 0},
          "local_tests_run": 0, "local_formatting_result": "not reached",
          "local_harness": "Two successive pre-test failures (missing support module, premature ExUnit tag assertion) remain preserved. Prepared-4 filter correction is unexecuted; local TLS execution is deferred while native process custody is corrected in the separate in-flight lane.",
          "runtime_validation": "Full ordinary remote Phoenix CI is required before accepting this correction.",
          "canonical_product_changed": False, "GA_accepted": False}
with (OUT / "source-review.json").open("x") as handle:
    json.dump({"schema": 1, "at": datetime.now(timezone.utc).isoformat(), **review}, handle, indent=2)
    handle.write("\n")

failure = ROOT / "verification/console-session-and-checkout-root-review/key-owner-fixture-cleanup-candidate-4-release-precondition-failure.json"
with failure.open("x") as handle:
    json.dump({"at": datetime.now(timezone.utc).isoformat(), "status": "root-precondition-failure-before-runtime-release",
               "error": "Root compared the whole selection object; only its include_filter explanatory text changed. The selected names and 29/7/22 counts remain identical.",
               "dependent_runner_attempt": "Missing release file rejected before output directory, scratch, VM or OpenSSL launch.",
               "candidate_4_executed": False, "disposition": "Preserved; local TLS deferred in favor of full remote CI for the canonical test-only correction."}, handle, indent=2)
    handle.write("\n")

w = json.loads((ROOT / "work-graph.json").read_bytes())
g = json.loads((ROOT / "gates/ga.json").read_bytes())
dispatcher = w["packages"][13]["fixedWorkspaceDispatcher"]
assert dispatcher == g["gates"][21]["fixedWorkspaceDispatcher"]
dispatcher["key_owner_supervised_lifecycle"]["fixture_cleanup_correction"] = copy.deepcopy(review)
g["gates"][21]["fixedWorkspaceDispatcher"] = copy.deepcopy(dispatcher)
for name, value in [("work-graph.json", w), ("gates/ga.json", g)]:
    (ROOT / name).write_text(json.dumps(value, indent=2) + "\n")
paragraph = "The six failing KeyOwnerTest teardown callbacks now use explicit ExUnit supervision, with cleanup assertions and temporary-child behavior. Source review and zero-warning compilation pass; local tests have not run because the isolated harness stopped on two setup errors. The test-only correction is selected for full remote CI. The separate in-flight run stopped on a deprecated test literal before tests and exposed a native OpenSSL process-group accounting gap; its recorded group was later confirmed absent, and a custody correction is in preparation. The reviewed Swift dispatch/lifetime contract is selected for a two-file isolated model; physical capacity, numerical prices and all GA gates remain pending."
for name in ["PLAN.md", "STATUS.md"]:
    path = ROOT / name
    text = path.read_text()
    marker = "Checkpoint `fd92138a` is pushed"
    assert text.count(marker) == 1
    path.write_text(text.replace(marker, paragraph + "\n\n" + marker, 1))
print(json.dumps({"source": row(test), "local_tests_run": 0, "remote_CI_required": True}))
