"""Prepare one bounded fixture amendment delivery and mirrored status metadata."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
AMEND = ROOT / "verification/identity-network-fixture-amendment-v1"
BASE = "e9fc0e7d984c79bf2d3493f5d5d16a0b167b3af7"
TREE = "b13260085c83ac346596e012e6c07fccd47f1f3f"
GLOBALS = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]

def read(path): return json.loads(path.read_bytes())
def row(path):
    body = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")

assert read(AMEND / "pure-controls.json")["exit"] == 0
assert "Ran 136 tests" in (AMEND / "pure-controls.stderr").read_text()
for path, expected in read(AMEND / "pure-controls.json")["files"].items():
    assert {key: row(ROOT / path)[key] for key in ("bytes", "sha256")} == expected
before = [row(ROOT / path) for path in GLOBALS]
summary = ROOT / "verification/github-delivery-positive-timestamp/ci-review/public-summary-candidate.json"
shutil.copyfile(summary, OUT / "prior-reviewed-ci-summary.json")
amendment = read(AMEND / "preparation.json")
selection = {
    "schema": 1, "at": datetime.now(timezone.utc).isoformat(), "basisRevision": BASE, "basisTree": TREE,
    "source_count": 178, "source_digest_sha256": "ab8f8dbec5894ca96dd673db828a01afdc39a54ad008a2a2d4e598c1c62ce2f7",
    "predecessor_source_count": 177, "predecessor_source_digest_sha256": "023df04c9a4599c3d5a6cdf2afb53a95e2faf37765d8b96ba2bcc0e1b007c92e",
    "amendment_sha256": amendment["source_amendment_sha256"], "amendment_packet_sha256": amendment["packet_tree_digest_sha256"],
    "amendment_packet_manifest": row(AMEND / "metadata/packet-manifest.json"),
    "independent_review_packet": row(AMEND / "metadata/independent-review/packet-manifest.json"),
    "producer_and_fresh_review_models": {"producer": {"model": "gpt-6-astra", "reasoning": "xhigh"}, "reviewer": {"model": "gpt-6-astra", "reasoning": "xhigh"}, "basis": "parent root confirmed actual spawned producer/reviewer launch metadata; controlling model unchanged"},
    "producer_source_controls": 6, "independent_source_checks": 9, "independent_source_refusals": 16, "accounting_model_cases": 15,
    "collector_pure_controls": 136, "collector_controls_receipt": row(AMEND / "pure-controls.json"),
    "prior_sanitized_review": row(OUT / "prior-reviewed-ci-summary.json"), "prior_review_candidate_source": row(summary),
    "latest_prior_workflow_status": row(OUT / "prior-ci-status.json"),
    "original_network_files_methods_assertions_and_argv_unchanged": True,
    "ordinary_Phoenix_controls_pending": 4, "fresh_original_network_methods_pending": 2,
    "remote_execution_selected": True, "local_runtime_compiler_Docker_Postgres_native_UI_capture_selected": False,
    "runtime_or_GA_accepted": False, "new_manual_dispatch_or_retry_selected": False,
    "protected_dirty_paths_excluded": [".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/store.ex"],
    "other_active_lanes_FieldLog_sources_raw_and_large_CI_raw_excluded": True,
    "stop_conditions": ["Any lifecycle failure: retain exact output and categorical terminal state before further action.",
                        "Original startup failure persists: retain its failed semantics; do not infer leak clearance.",
                        "Four Phoenix controls and two network methods pass: accept only exact delivered scoped behavior after evidence review."],
}
save(OUT / "selection.json", selection)
checkpoint = {"selection": row(OUT / "selection.json"), "source_count": 178, "source_digest_sha256": selection["source_digest_sha256"],
              "historical177_contracts_immutable": True, "collector_pure_controls": 136,
              "ordinary_Phoenix_controls_pending": 4, "fresh_original_network_methods_pending": 2,
              "prior_network": {"revision": BASE, "run": 40770270255, "passed": 1, "failed": 1, "JOSE_Erlang_sources_compiled": 113,
                                "K03_passed": True, "IS04_IS05_startup_third_close_failed": True, "all_three_containers_removed_and_absent": True},
              "prior_workflow_status": {"Engine": {"run": 40770270242, "conclusion": "success", "workflow_status_only": True},
                                        "Phoenix": {"run": 40770270238, "conclusion": "success", "passed": 697, "skipped": 2, "protocol": 45, "storage": 24, "migration": 1}},
              "remote_execution_selected": True, "runtime_or_GA_accepted": False}
work = read(ROOT / "work-graph.json")
gates = read(ROOT / "gates/ga.json")
assert work["packages"][13]["identityProductionNetworkCI"] == gates["gates"][21]["identityProductionNetworkCI"]
for document, entry in [(work, work["packages"][13]), (gates, gates["gates"][21])]:
    value = entry["identityProductionNetworkCI"]
    value["fixture_source_amendment_selection"] = checkpoint
    value["effective_source_files"] = 178
    value["effective_source_tree_sha256"] = selection["source_digest_sha256"]
    value["existing_product_and_tests_unchanged"] = False
    value["original_production_modules_and_network_tests_unchanged"] = True
assert {state: sum(item["status"] == state for item in gates["gates"]) for state in ("running", "planned", "verified")} == {"running": 8, "planned": 30, "verified": 0}
for name, document in [("work-graph.json", work), ("gates/ga.json", gates)]:
    (ROOT / name).write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n")
plan = ROOT / "PLAN.md"
text = plan.read_text()
marker = "## Execution priority and blocker escalation\n"
assert marker in text
text = text.replace(marker, """## Selected fixture source amendment

The independently reviewed TLS fixture EOF correction is selected for fresh
ordinary Phoenix and isolated network CI. The explicit source amendment preserves
historical 177/023df04 contracts and selects exactly 178/ab8f8d sources: one fixture
replacement and one canonical test with four ordinary controls. All 136 pure
collector decisions pass with children/sockets denied. The existing K03 and
IS04/IS05 test files, assertions and observer argv stay exact. Compile/format,
all four new controls and both original methods remain pending for this source.
Retain any new failure before another decision; no manual rerun is selected.
[Selection](verification/github-delivery-fixture-eof/selection.json) binds the
accepted candidate, complete review, source/helper manifests and sanitized prior
CI summary. No native, local runtime/custody, UnitA or GA hold is released.

""" + marker, 1)
plan.write_text(text)
status = ROOT / "STATUS.md"
text = status.read_text()
marker = "Current delivery addendum:"
assert marker in text
text = text.replace(marker, """Current fixture amendment: the exact independently accepted fixture EOF candidate is integrated with a sealed 178-file source amendment and all 136 pure collector controls passing. Historical 177/023df04 contracts remain immutable; only the TLS fixture changes among old sources, and one four-control test is added. The fixture observes silent-stall peer EOF immediately and credits only observed peer closure, with accepted registration before handler work and bounded categorical diagnostics. The original two production network files, methods, assertions and argv are unchanged. Format/compile, four ordinary Phoenix controls and both original network methods remain pending for the amended source. [Selection and limits](verification/github-delivery-fixture-eof/selection.json) retain both amendment-preparation failures, their corrections and the complete fresh independent source review. No local Elixir/compiler/Docker/PostgreSQL/native/UI/capture or held-group probe ran. Gates remain 8 running, 30 planned, 0 verified.

The preceding e9fc0e7d network run 40770270255 compiled all 113 JOSE Erlang sources and passed K03, then failed the unchanged startup third-connection closure assertion; all three exact owned containers were removed and observed absent. Phoenix 40770270238 passes 697 tests with two existing skips plus 45 protocol, 24 storage and one migration checks. The latest live workflow observation records Engine 40770270242 success; detailed Engine artifact acceptance is separate. Architecture comparison 40768719255 exhausted both attempts at FrameLimit 65/64 in Corpus 1, with no complete observation or Corpus 2 and no production winner; its next frame/pin proposal remains unexecuted. Public FieldLog 146f2a27 run 40771309900 failed dependency-pin fetch at 180.084 seconds before resolve/build/tests: zero observed tests, unavailable failure count, ten remote and thirty-seven local groups cleaned with one remote SIGTERM. Its next transport proposal remains unexecuted. Raw CI and FieldLog packets stay local; no raw source or large archives join this delivery.

Historical timestamp-only checkpoint:""", 1)
status.write_text(text)
save(OUT / "metadata-checkpoint.json", {"schema": 1, "before": before, "after": [row(ROOT / path) for path in GLOBALS], "gate_counts": {"running": 8, "planned": 30, "verified": 0}, "mirrors_equal": True})
print(json.dumps({"globals": len(GLOBALS), "selected": row(OUT / "selection.json"), "metadata": row(OUT / "metadata-checkpoint.json")}))
