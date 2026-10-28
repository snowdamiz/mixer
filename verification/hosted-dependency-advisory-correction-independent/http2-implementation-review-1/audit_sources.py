#!/usr/bin/env python3
"""Read/hash-only HTTP2 implementation review; no producer import/runtime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = REPO / "verification/hosted-dependency-advisory-correction/http2-implementation-v1"
FIXTURE = "hosted/test/support/http2_wire_fixture.ex"
TEST = "hosted/test/mixer_hosted/billing/raw_webhook_capture_http2_test.exs"


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


def main():
    seal_sha = "c95f5695d426be95cd9fa8ac65e545dc8265cfdb4f2d952d14c56da30bd1f327"
    assert sha(PACKET / "seal.sha256") == seal_sha
    members = []
    for line in (PACKET / "seal.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert sha(PACKET / name) == expected
        members.append(name)
    assert len(members) == len(set(members)) == 8
    evidence = read(PACKET / "source-evidence.json")
    preparation = read(PACKET / "preparation-receipt.json")
    plan = read(PACKET / "ci-plan.json")
    for group in [evidence["current_original_input_pins"].values(), evidence["new_test_source"], evidence["protected_observed_current_bytes_not_edited_by_this_lane"]]:
        for pin in group:
            path = REPO / pin["path"]
            assert path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"]
    for key in ["root_selection", "independent_review_seal"]:
        pin = evidence[key]
        assert sha(REPO / pin["path"]) == pin["sha256"]
    earlier = REPO / evidence["independent_review_seal"]["path"]
    for member in read(earlier)["files"]:
        assert sha(earlier.parent / member["path"]) == member["sha256"]
    for pin in evidence["official_commit_source_blobs"]:
        path = REPO / pin["local_evidence_path"]
        raw = path.read_bytes()
        assert sha(path) == pin["sha256"]
        assert hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == pin["git_blob_sha"]
    assert len(evidence["current_original_input_pins"]) == preparation["original_design_inputs_actual_count"] == 24
    assert len(evidence["official_commit_source_blobs"]) == 8
    assert sha(REPO / FIXTURE) == "965c38f6dac459de2baaf3fee98c66ee663a013ccc9401d14d233fbab27794af"
    assert sha(REPO / TEST) == "4656e1f05e20ddfe8767be837a38d8323313efd7ef77efa7176a748c518c8ce8"
    for name in [FIXTURE, TEST]:
        assert (PACKET / "source" / name).read_bytes() == (REPO / name).read_bytes()
    fixture, tests = (REPO / FIXTURE).read_text(), (REPO / TEST).read_text()
    names = re.findall(r'^  test "([^"]+)"', tests, re.M)
    assert names == preparation["methods_source_inventory_only"] and len(names) == 5
    assert tests.count('for profile <- [:settings, :window_update]') == 2
    assert preparation["finite_subcases"] == plan["finite_subcases"] == 7
    # Source inventory supplements the independent manual control-flow review.
    assert 'prefix = for n <- 0..31' in tests and 'binary_part(body, 32_800, 7_201)' in tests
    assert 'oversized = Enum.any?(F.reads(), &(&1.bytes > 32_768))' in tests
    assert 'paced(body, 32, true)' in tests and 'paced(body, 31, false)' in tests
    assert 'binary_part(body, @cap, 1), true' in tests
    assert 'send_frames(frames)' in fixture and 'check(:gen_tcp.send(state().socket, iodata) == :ok' in fixture
    assert 'state().conn_credit >= total and state().stream_credit >= total' in fixture
    assert 'real HTTP/2 adapter/framing required' in fixture and 'Bandit.Adapter, []' in fixture
    assert 'case s.module.read_req_body(s.adapter, opts)' in fixture
    assert 'latest = %{latest | adapter: {observed.module, observed.adapter}}' in fixture
    assert 'read.finished - read.started in 900..1_600' in fixture
    assert 'before_return >= 3' in fixture and 'result.reason == :no_progress' in tests
    assert 'shutdown_timeout: 100' in fixture and 'Map.put(:shutdown, 400)' in fixture
    assert 'Map.put(:restart, :temporary)' in fixture and 'not s.startup_pending' in fixture
    assert 'Process.monitor(pid)' in fixture and ':atomics.put(s.budget, 3, 1)' in fixture
    assert 'now() + 25_000' in fixture and '@moduletag timeout: 26_000' in tests
    assert 'check(byte_size(line) <= 2_048' in fixture and 'IO.puts("HTTP2_WIRE_RECEIPT " <> line)' in fixture
    assert 'Application.spec(:bandit, :vsn) == ~c"1.14.0"' in fixture
    relation = REPO / "verification/hosted-dependency-relation-binding-correction/freeze.json"
    assert sha(relation) == "f5010dabd52fd3c36fd311d42b8266de9d48780402200e955eeb2511eff2fd7f"
    for name, pin in read(relation)["canonical_delta"].items():
        assert sha(REPO / name) == pin["after"]
    primary = read(OUT / "ci-primary-source.json")
    assert len(primary["files"]) == 5 and len(primary["supplementary_reads"]) == 2
    result = {"schema":1,"status":"independent-source-review-passed-for-ordinary-remote-format-compile-test",
        "created_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,
        "command":"python3 -B verification/hosted-dependency-advisory-correction-independent/http2-implementation-review-1/audit_sources.py",
        "script_sha256":sha(Path(__file__)),"implementation_seal_sha256":seal_sha,
        "source_revision_observed_by_producer":preparation["source_revision_observed"],
        "verified_counts":{"producer_members":8,"new_canonical_files":2,"original_local_pins":24,"official_Bandit_blobs":8,"protected_pins":5,"prior_review_members":14},
        "canonical_files":evidence["new_test_source"],"method_names_textual_inventory_only":names,
        "finite_subcases":7,"closed_design_refinements":["H2R01","H2R02","H2R03","H2R04"],
        "manual_review":{"adapter":"same stream owner, real Bandit.Adapter, faithful two-method observer and newest-state unwrap before response",
            "B1":"32 tiny prefix frames plus legal bounded tail, correlated PING fence and mandatory measured return above requested length",
            "B2":"32 paced exact-target reads, terminal payload END_STREAM, exact bytes/signature and finite admission",
            "B3":"31 paced tranches plus reserved-credit single final 32769-byte send; rejects too_large without extra-byte-consumption claim",
            "D1_D2":"separate SETTINGS/WINDOW_UPDATE processing witnesses before fixed empty-more return; Mixer no_progress checked separately",
            "frame_flow":"passive fixed-header/payload parser, strict selected frames/refusals, both credits updated and all frame/input/read/event bounds retained",
            "cleanup":"temporary owned ExUnit listener, public shutdown100ms/child400ms, correlated disposal and recorded socket/stream/connection/query/listener closure; failure poisons next admission",
            "CI":"normal test/support compilation and *_test.exs discovery, no workflow change; official Mix source explains .app metadata load under --no-start"},
        "deadline_scope":"25s shared monotonic admission/cooperative waits; listener startup and OS calls are not hard preempted. 26s ExUnit guard is per-test failure containment, not hard cumulative module wall time.",
        "findings":[],"recommend_root_deliver_for_ordinary_remote_CI":True,
        "formatting_compilation_runtime_execution_proven":False,"HTTP2_wire_qualifications_passed":False,
        "relation_binding_canonical_three_files_preserved":True,
        "network_source_reads":"7 official Elixir1.20.4 GitHub file GETs solely to resolve --no-start app loading; no runtime/network probe",
        "formatter_Mix_compiler_test_listener_native_process_or_DNS_probe_invocations":0,
        "receipt_acceptance":"Require delivered source/version, successful format/compile/full test outcome and exactly seven passing case receipts with cleanup; never accept a receipt alone if the enclosing test or suite fails.",
        "scope":"Finite package read/batching and Mixer capture admission only; no hard arbitrary read cancellation, exhaustive advisory/memory/backpressure/provider/production/native/device/GA acceptance.",
        "elapsed_seconds":round(time.monotonic()-START,6)}
    (OUT / "audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
