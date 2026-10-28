"""Bounded offline source/diff bookkeeping; no Elixir or producer import."""
from pathlib import Path
import datetime
import difflib
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
V1 = ROOT / "verification/hosted-dependency-advisory-correction/http2-implementation-v1"
REVIEW = ROOT / "verification/hosted-dependency-advisory-correction-independent/http2-implementation-review-1"
FORMAT = ROOT / "verification/hosted-http2-format-root-1"
REVISION = "c51f67c5c51b4172d8cae03b966b43f891bddb2d"
FIXTURE = "hosted/test/support/http2_wire_fixture.ex"
TEST = "hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs"
COLLECTOR = "hosted/scripts/test-local.py"
EXPECTED = {
    FIXTURE: "c0ba4561576060c525e586414fcfeacc88cfa19b14607d4f13dffaca32da7f4e",
    TEST: "4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8",
    COLLECTOR: "78292dbf027bff4fae67d638fec9504c042cbeac39b6bca40e38321178bb5951",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, expected=None):
    data = path.read_bytes()
    assert len(data) < 300_000, "source/evidence read bound"
    if expected is not None:
        assert sha(data) == expected, "pin mismatch: " + str(path)
    return data


def pin(path):
    data = read(path)
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


v1_seal = read(V1 / "seal.sha256", "c95f5695d426be95cd9fa8ac65e545dc8265cfdb4f2d952d14c56da30bd1f327")
v1_members = v1_seal.decode().splitlines()
assert len(v1_members) == 8
for line in v1_members:
    digest, name = line.split("  ", 1)
    read(V1 / name, digest)
review_bytes = read(REVIEW / "review-seal.json", "5cdc76fa8e1bb40c4aadb7e4978419eede33a5109d3e47b3d80cdb5f6dbd6055")
review = json.loads(review_bytes)
assert review["findings"] == [] and review["recommend_root_deliver_for_ordinary_remote_format_compile_test"]
for item in review["files"]:
    read(REVIEW / item["path"], item["sha256"])
evidence = json.loads(read(V1 / "source-evidence.json"))
baseline = dict(evidence["current_original_input_pins"])
for key in ["canonical_dependency_bytes_match_accepted_application", "protected_observed_current_bytes_not_edited_by_this_lane", "new_test_source"]:
    for item in evidence[key]:
        if item["path"] in baseline:
            assert baseline[item["path"]]["sha256"] == item["sha256"]
        baseline[item["path"]] = item
assert len(evidence["current_original_input_pins"]) == 24 and len(baseline) == 28
current = {}
drift = []
for relative, old in sorted(baseline.items()):
    actual = pin(ROOT / relative)
    current[relative] = actual
    if actual["sha256"] != old["sha256"]:
        assert relative in [FIXTURE, COLLECTOR], "unexpected V1 input drift: " + relative
        assert actual["sha256"] == EXPECTED[relative], "unselected drift bytes: " + relative
        drift.append({"path": relative, "before_sha256": old["sha256"], "after_sha256": actual["sha256"]})
assert {item["path"] for item in drift} == {FIXTURE, COLLECTOR}
for relative, expected in EXPECTED.items():
    read(ROOT / relative, expected)

# The root's operation and application evidence is consumed once and pinned.
format_bytes = read(FORMAT / "receipt.json")
formatter = json.loads(format_bytes)
application_bytes = read(FORMAT / "application.json")
application = json.loads(application_bytes)
assert formatter["status"] == "passed" and formatter["AST_equivalent"]
assert formatter["exit"] == 0 and 0 < formatter["elapsed_seconds"] < 1
assert all(formatter[key] for key in ["reaped", "owned_group_absent", "scratch_removed"])
assert formatter["compiler_tests_listeners_or_native_OpenSSL_run"] is False
assert formatter["canonical_changed"] is False
assert application["status"] == "AST-equivalent-formatter-output-applied"
assert application["changes"] == [{
    "path": FIXTURE,
    "before": baseline[FIXTURE]["sha256"],
    "after": EXPECTED[FIXTURE],
}]
for key in ["stdout", "stderr"]:
    item = formatter[key]
    read(Path(item["path"]), item["sha256"])
assert read(FORMAT / "stderr") == b""
stdout = read(FORMAT / "stdout").decode()
assert "ELIXIR 1.20.4\n" in stdout
assert "AST_EQUAL http2_wire_fixture.ex\n" in stdout
assert "AST_EQUAL raw_webhook_capture_http2_test.exs\n" in stdout
for item in formatter["canonical_before"]:
    relative = str(Path(item["path"]).relative_to(ROOT))
    assert relative in [FIXTURE, TEST]
    read(V1 / "source" / relative, item["sha256"])
for item in formatter["formatted_outputs"]:
    name = Path(item["path"]).name
    relative = FIXTURE if name == "http2_wire_fixture.ex" else TEST
    output = read(Path(item["path"]), EXPECTED[relative])
    assert item["sha256"] == EXPECTED[relative]
    assert output == read(ROOT / relative)

delta = []
delivery = []
new_source = []
for relative in [FIXTURE, TEST]:
    old = read(V1 / "source" / relative)
    data = read(ROOT / relative, EXPECTED[relative])
    assert data.endswith(b"\n") and len(data) < 40_000
    destination = OUT / "source" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    new_source.append(pin(ROOT / relative))
    if data != old:
        delta += [f"diff --git a/{relative} b/{relative}\n"]
        delta += list(difflib.unified_diff(old.decode().splitlines(True), data.decode().splitlines(True), fromfile="a/" + relative, tofile="b/" + relative))
    delivery += [f"diff --git a/{relative} b/{relative}\n", "new file mode 100644\n"]
    delivery += list(difflib.unified_diff([], data.decode().splitlines(True), fromfile="/dev/null", tofile="b/" + relative))
delta_text = "".join(delta)
assert len(delta_text.encode()) < 4_096
(OUT / "formatting-only.patch").write_text(delta_text)
(OUT / "two-file.patch").write_text("".join(delivery))
receipt = {
    "schema": 1,
    "status": "formatted-successor-frozen-awaiting-final-delta-review-and-ordinary-remote-delivery",
    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
    "python": sys.version,
    "python_executable": sys.executable,
    "source_revision_observed": REVISION,
    "revision_observation_command": ["git", "rev-parse", "HEAD"],
    "preserved_v1_seal": pin(V1 / "seal.sha256"),
    "v1_sealed_members_verified_unchanged": len(v1_members),
    "passed_v1_independent_review_seal": pin(REVIEW / "review-seal.json"),
    "passed_v1_review_members_verified": len(review["files"]),
    "root_formatter_evidence": {
        "receipt": {"path": str((FORMAT / "receipt.json").relative_to(ROOT)), "bytes": len(format_bytes), "sha256": sha(format_bytes)},
        "application": {"path": str((FORMAT / "application.json").relative_to(ROOT)), "bytes": len(application_bytes), "sha256": sha(application_bytes)},
        "stdout": pin(FORMAT / "stdout"),
        "stderr": pin(FORMAT / "stderr"),
        "elapsed_seconds_observed_in_root_receipt": formatter["elapsed_seconds"],
        "AST_equivalent_observed_by_root": True,
        "root_child_reaped_group_absent_scratch_removed": True,
        "our_successor_repeated_formatter_parser_or_process_observation": False,
    },
    "frozen_delivery_source": new_source,
    "fixture_formatting_delta": "Five blank lines and parentheses around read.finished - read.started; normalized AST equivalence is root-observed evidence, not recomputed here.",
    "test_source_byte_unchanged_from_v1": True,
    "implementation_behavior_change_selected": False,
    "original_design_inputs_count": 24,
    "unique_v1_current_input_pins_rechecked": len(baseline),
    "current_input_pins": current,
    "authorized_drift_exactly": drift,
    "unexpected_drift": [],
    "separate_collector_change": {
        "path": COLLECTOR,
        "sha256": EXPECTED[COLLECTOR],
        "authorization": "Explicit root follow-up selected these exact later collector bytes",
        "independent_review": "pending separately",
        "behavior_review_or_acceptance_by_this_packet": False,
        "included_in_two_file_delivery_patch": False,
    },
    "prospective_CI": {
        "unchanged_reviewed_test_plan": pin(V1 / "ci-plan.json"),
        "current_runner": current[COLLECTOR],
        "root_delivery_pending": ["final formatting-delta review", "separate collector independent review", "coherent root commit/push"],
        "existing_remote_checks": ["mix deps.get --check-locked", "mix format --check-formatted", "mix compile --warnings-as-errors", "mix test --warnings-as-errors --seed 0 --trace"],
        "methods": 5,
        "finite_subcases_and_required_receipts": 7,
        "green_enclosing_tests_and_full_CI_required_in_addition_to_receipts": True,
        "workflow_change_by_this_packet": False,
        "new_local_runtime_command_proposed": False,
    },
    "our_new_formatter_Elixir_Mix_compiler_tests_listener_network_native_capture_process_probe_invocations": 0,
    "wire_qualifications": {"HTTP2_BATCHING_APPLICATION_BYTE_CAPS": "pending", "HTTP2_NONPROGRESS_PUBLIC_READ_DEADLINE": "pending"},
    "deadline_scope": "25-second shared admission/cooperative-wait deadline; separate 26-second per-test failure guard, no hard module wall-time claim",
    "acceptance_limit": "No broad advisory, exploit, memory/backpressure, provider/production, native/device or GA inference",
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
members = sorted(p for p in OUT.rglob("*") if p.is_file() and p.name != "seal.sha256")
assert len(members) == 7
seal = "".join(sha(p.read_bytes()) + "  " + str(p.relative_to(OUT)) + "\n" for p in members)
(OUT / "seal.sha256").write_text(seal)
print(json.dumps({"status": "formatted-v2-frozen", "members": len(members), "v1_current_pins_rechecked": len(baseline), "authorized_drifts": [item["path"] for item in drift], "unexpected_drift": [], "new_runtime_invocations": 0, "seal_sha256": sha(seal.encode())}))
