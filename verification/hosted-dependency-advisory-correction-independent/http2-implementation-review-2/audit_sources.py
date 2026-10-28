#!/usr/bin/env python3
"""Bounded byte/hash/retained-JSON review; no source parser or producer replay."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = REPO / "verification/hosted-dependency-advisory-correction"
V1, V2 = BASE / "http2-implementation-v1", BASE / "http2-implementation-v2"
FORMATTING = REPO / "verification/hosted-http2-format-root-1"
FIXTURE = "hosted/test/support/http2_wire_fixture.ex"
TEST = "hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs"
NEW_FIXTURE = "c0ba4561576060c525e586414fcfeacc88cfa19b14607d4f13dffaca32da7f4e"
TEST_SHA = "4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8"
COLLECTOR = "78292dbf027bff4fae67d638fec9504c042cbeac39b6bca40e38321178bb5951"


def sha(path):
    assert time.monotonic() - START < 55
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def sealed(path, expected, count):
    assert sha(path) == expected
    names = []
    for line in path.read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(path.parent / name) == digest
        names.append(name)
    assert len(names) == len(set(names)) == count


def main():
    v2_sha = "50e7045f90361141d3a3b76ea9e7a59c6a3533ece9adf7fc4759f5c6ce1ab120"
    sealed(V2 / "seal.sha256", v2_sha, 7)
    sealed(V1 / "seal.sha256", "c95f5695d426be95cd9fa8ac65e545dc8265cfdb4f2d952d14c56da30bd1f327", 8)
    prior_path = OUT.parent / "http2-implementation-review-1/review-seal.json"
    assert sha(prior_path) == "5cdc76fa8e1bb40c4aadb7e4978419eede33a5109d3e47b3d80cdb5f6dbd6055"
    for pin in read(prior_path)["files"]:
        assert sha(prior_path.parent / pin["path"]) == pin["sha256"]
    receipt = read(V2 / "receipt.json")
    for pin in receipt["root_formatter_evidence"].values():
        if isinstance(pin, dict) and "path" in pin:
            path = REPO / pin["path"]
            assert path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"]
    formatting = read(FORMATTING / "receipt.json")
    application = read(FORMATTING / "application.json")
    assert formatting["status"] == "passed" and type(formatting["exit"]) is int and formatting["exit"] == 0
    assert formatting["AST_equivalent"] is True and formatting["canonical_changed"] is False
    assert formatting["reaped"] is True and formatting["owned_group_absent"] is True and formatting["scratch_removed"] is True
    assert formatting["pid"] == formatting["pgid"] == 23609
    assert formatting["compiler_tests_listeners_or_native_OpenSSL_run"] is False
    assert formatting["elapsed_seconds"] == 0.22870133398100734
    assert not (FORMATTING / "scratch").exists()
    assert {path.name for path in FORMATTING.iterdir()} == {"receipt.json", "application.json", "stdout", "stderr", "http2_wire_fixture.ex", "raw_webhook_capture_http2_test.exs"}
    assert all(stat.S_ISREG(path.lstat().st_mode) for path in FORMATTING.iterdir())
    for group in [formatting["formatted_outputs"], [formatting["stdout"], formatting["stderr"], formatting["tool"]]]:
        for pin in group:
            path = Path(pin["path"])
            assert path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"]
    stdout = (FORMATTING / "stdout").read_text()
    assert "ELIXIR 1.20.4" in stdout and "OTP Erlang/OTP 29" in stdout
    assert stdout.count("AST_EQUAL ") == 2 and (FORMATTING / "stderr").read_bytes() == b""
    old = (V1 / "source" / FIXTURE).read_bytes()
    new = (V2 / "source" / FIXTURE).read_bytes()
    assert sha(REPO / FIXTURE) == sha(V2 / "source" / FIXTURE) == sha(FORMATTING / "http2_wire_fixture.ex") == NEW_FIXTURE
    assert (REPO / FIXTURE).read_bytes() == new
    assert sha(REPO / TEST) == sha(V2 / "source" / TEST) == sha(V1 / "source" / TEST) == sha(FORMATTING / "raw_webhook_capture_http2_test.exs") == TEST_SHA
    assert application["changes"] == [{"path":FIXTURE,"before":hashlib.sha256(old).hexdigest(),"after":NEW_FIXTURE}]
    assert application["runtime_tests_or_listeners_run"] is False
    # Exact text comparison, not source parsing: ignore only the five inserted
    # empty lines and one explicit parenthesis pair around the known subtraction.
    unparenthesized = new.replace(b'check((read.finished - read.started) in 900..1_600,', b'check(read.finished - read.started in 900..1_600,')
    assert unparenthesized != new
    old_lines, new_lines = old.splitlines(keepends=True), unparenthesized.splitlines(keepends=True)
    assert [line for line in old_lines if line.strip()] == [line for line in new_lines if line.strip()]
    assert len(new_lines) - len(old_lines) == 5
    patch = "diff --git a/" + FIXTURE + " b/" + FIXTURE + "\n" + "".join(difflib.unified_diff(old.decode().splitlines(keepends=True),new.decode().splitlines(keepends=True),fromfile="a/"+FIXTURE,tofile="b/"+FIXTURE))
    assert (V2 / "formatting-only.patch").read_text() == patch
    old_evidence = read(V1 / "source-evidence.json")
    old_pins = {}
    for group in [old_evidence["current_original_input_pins"].values(), old_evidence["new_test_source"], old_evidence["protected_observed_current_bytes_not_edited_by_this_lane"]]:
        for pin in group:
            name = pin["path"]
            if name in old_pins:
                assert old_pins[name] == pin
            old_pins[name] = pin
    assert len(old_pins) == len(receipt["current_input_pins"]) == 28
    assert old_pins.keys() == receipt["current_input_pins"].keys()
    drift = []
    for name, pin in receipt["current_input_pins"].items():
        path = REPO / name
        assert path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"]
        if old_pins[name]["sha256"] != pin["sha256"]:
            drift.append(name)
    assert sorted(drift) == ["hosted/scripts/test-local.py", FIXTURE]
    collector_decision_path = REPO / "verification/console-key-owner-inflight-lifecycle-independent/remote-ci-collector-review-1/decision.json"
    assert sha(collector_decision_path) == "0ce0be7ff2783b1726855d1c39747ff0c2823bd791570b9a7251f8a1ea781cb8"
    collector_decision = read(collector_decision_path)
    assert collector_decision["canonical_collector_sha256"] == sha(REPO / "hosted/scripts/test-local.py") == COLLECTOR
    assert collector_decision["recommendation"]["source_integration_adequate_for_root_delivery_selection"] is True
    assert collector_decision["required_actual_acceptance"]["actual_runtime_or_GA_qualified_by_this_review"] is False
    for key in ["preserved_v1_seal", "passed_v1_independent_review_seal"]:
        assert sha(REPO / receipt[key]["path"]) == receipt[key]["sha256"]
    result = {"schema":1,"status":"adequate-formatting-delta-source-review-recommend-root-ordinary-delivery",
        "created_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,
        "command":"python3 -B verification/hosted-dependency-advisory-correction-independent/http2-implementation-review-2/audit_sources.py",
        "script_sha256":sha(Path(__file__)),"v2_seal_sha256":v2_sha,
        "prior_v1_review_seal_sha256":sha(prior_path),"v1_review_reusable":True,
        "canonical_fixture_sha256":NEW_FIXTURE,"canonical_test_sha256":TEST_SHA,
        "verified_counts":{"v2_members":7,"preserved_v1_members":8,"prior_review_members":4,"current_input_pins":28,"unchanged_v1_pins":26},
        "delta":"Exactly five inserted blank lines and parentheses around read.finished - read.started; test file unchanged",
        "root_formatter_receipt_sha256":sha(FORMATTING / "receipt.json"),
        "root_formatter_AST_equivalence":"Observed by root for both files; not re-parsed or recomputed in this review",
        "root_formatter_terminal":"exit0, reaped/group-absent/scratch-removed recorded at0.228701s; evidence hashes verified, no process observations repeated",
        "separate_collector_sha256":COLLECTOR,"separate_collector_decision_sha256":sha(collector_decision_path),
        "collector_scope":"Only exact-byte association with separate adequate source decision; collector behavior not re-reviewed. V2 preparation's earlier pending field is historical.",
        "findings":[],"recommend_root_source_delivery":True,
        "methods":5,"finite_subcases":7,"wire_qualifications_passed":False,
        "ordinary_CI_format_compile_test_for_these_files":"pending",
        "deadline_scope":"25s shared admission/cooperative waits;26s per-test failure guard, not a hard module wall bound",
        "source_parser_formatter_Elixir_Mix_compiler_test_listener_dependency_process_or_network_probe_invocations":0,
        "canonical_or_global_metadata_writes":0,
        "acceptance":"Delivered source/lock/version, green enclosing CI and seven passing cleanup-complete receipts still required; no broader advisory/provider/production/native/device/GA acceptance.",
        "elapsed_seconds":round(time.monotonic()-START,6)}
    (OUT / "decision.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
