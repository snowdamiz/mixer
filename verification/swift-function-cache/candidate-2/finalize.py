#!/usr/bin/env python3
"""Bind completed producer commands to one immutable logical source snapshot.

This collector does not confer independent acceptance or execute any guest.
"""
import datetime
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = "39199ae5475de5d03926807ce60add5dcb0741c2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


reg = read("qualification/regressions.json")
named = read("qualification/named/receipt.json")
extra = read("qualification/additional-reference-receipt.json")
legacy = read("legacy-parity-receipt.json")
surface = read("surface-receipt.json")
layout = read("layout-map.json")
assert reg["status"] == extra["status"] == legacy["status"] == surface["status"] == "pass"
assert named["status"] == "named_synthetic_commands_passed_review_pending"
assert len(reg["commands"]) == 21 and len(extra["commands"]) == 2
assert len(named["commands"]) == 36
assert all(c["exit_code"] == 0 for c in reg["commands"] + extra["commands"] + named["commands"])
assert all(c["exactly_one_passed"] for c in named["commands"])
assert all(c["exactly_two_passed"] for c in extra["commands"])
assert len(legacy["comparisons"]) == 4 and all(c["equal"] for c in legacy["comparisons"])
assert legacy["baseline_revision"] == BASE
assert len(surface["current_exports"]) == 28 and len(surface["headers"]) == 3
assert surface["original_exports"] == surface["current_exports"]
assert reg["unchanged_source"] and named["source_manifest"] == named["source_manifest_after"]

assert not (HERE / "producer-receipt.json").exists(), "candidate already sealed"
source = {}
for manifest in [reg["source_manifest"], named["source_manifest"], legacy["current_source_manifest"]]:
    for name, value in manifest.items():
        assert name not in source or source[name] == value, name
        assert digest((ROOT / name).read_bytes()) == value, name
        source[name] = value
assert extra["source_manifest"] == reg["source_manifest"]
source = dict(sorted(source.items()))
source_digest = digest(json.dumps(source, sort_keys=True).encode())

owned = [
    "vm/src/experimental/cache/mod.rs",
    "vm/src/experimental/cache/decode.rs",
    "vm/src/experimental/cache/borrowed.rs",
    "vm/src/experimental/cache/tests.rs",
    "vm/src/experimental_swift_reactor/cache.rs",
    "vm/src/experimental_swift_reactor/cache_tests.rs",
]
root_expected = {
    "vm/src/experimental/mod.rs": "c33b8da10f8a2b7a47b5fcece6709f10f294cc0b926f4727ab607fbdb7bc0c81",
    "vm/src/experimental/descriptors.rs": "05d35c81eaeb2d86e8bc7c63f2b0122e1286198788730a927d439cd0a2a979ae",
    "vm/src/experimental_swift_reactor/mod.rs": "427fba158aa06825914d887ed9d19649453b1b2671d5c4cd962ca7c9cced6e2c",
    "vm/src/experimental_swift_reactor/control.rs": "55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f",
    "vm/src/experimental_swift_reactor/control_tests.rs": "0618d894583264b194d69f90c7a29a01a6a62f96a6118c337a508c5b910236b7",
    "vm/tests/swift_reactor_validation_allocations.rs": "5fc2aafcd477f3f9845e787116a4ab73ec68319c0aa1996090a57b95571a3cb6",
    "verification/swift-cache-stage-acceptance.json": "7214cb876a18df7ddedc364acc52f57cc04b2b8916968ef360ee4a0eb7f28089",
    "verification/swift-cache-stage-contract/proposal-receipt.json": "94476317a7bf4ea59266e7cad2f75d99bfae8196bd05abd21df4f64ed40628a3",
}
for name, value in root_expected.items():
    assert digest((ROOT / name).read_bytes()) == value, name

overlays = {}
for name, value in source.items():
    p = subprocess.run(["git", "show", BASE + ":" + name], cwd=ROOT, capture_output=True)
    original = digest(p.stdout) if p.returncode == 0 else None
    if original != value:
        overlays[name] = {"baseline_sha256": original, "frozen_sha256": value}
save("source-freeze.json", {"baseline_revision": BASE, "source_manifest": source,
                            "source_manifest_sha256": source_digest,
                            "overlays": overlays})

# Store exact source bytes with fixed archive metadata; subsequent checks use hashes.
tar_bytes = io.BytesIO()
with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
    for name, value in source.items():
        data = (ROOT / name).read_bytes()
        assert digest(data) == value
        item = tarfile.TarInfo(name)
        item.size = len(data)
        item.mode = 0o644
        item.mtime = 0
        archive.addfile(item, io.BytesIO(data))
with (HERE / "frozen-source.tar.gz").open("wb") as output:
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as zipped:
        zipped.write(tar_bytes.getvalue())

plan = json.loads((ROOT / "verification/swift-cache-stage-contract/acceptance.json").read_text())
test_source = (ROOT / owned[-1]).read_text()
tests = []
for test in plan["tests"]:
    name = test["name"]
    function = re.search(r"^fn " + re.escape(name) + r"\(", test_source, re.M)
    assert function is not None, name
    selections = [i for i, c in enumerate(named["commands"])
                  if any(a.endswith("::" + name) for a in c["argv"])]
    assert len(selections) == 2
    assert ["--release" in named["commands"][i]["argv"] for i in selections] == [False, True]
    tests.append({"name": name, "source": owned[-1], "line": test_source[:function.start()].count("\n") + 1,
                  "named_command_indices": selections, "executed_modes": ["debug", "release"],
                  "contract_requirements": test["assertions"], "independent_assertion_review": "pending"})
# Requirements are retained verbatim for comparison, not asserted as all executed.
qualifications = {
    "decoder_opcode_and_count_build_parity": {"promoted_helper": "review_every_decoded_instruction_matches_independent_owned_ir", "observed": "376 owned-IR Operation matches plus 3 target/offset matches; complete validator original Swift fixture"},
    "parameters_and_function_inclusive_depth": {"promoted_helper": "review_parameter_and_group_boundaries", "observed": "128 params+128 locals succeeds; 129 params and257 locals reject;256 local groups succeeds/257 rejects;512 function-inclusive depth succeeds/513 rejects"},
    "pins_hits_lru_and_eviction": {"promoted_helper": "review_64_distinct_live_pins_then_65th_and_terminal_release", "observed": "64 distinct simultaneously live function pins;65th fails without allocations; all original pins can terminal-release"},
    "foreign_stale_nonce_and_control_ownership": {"observed": "stale pin, nonce exhaustion, foreign cache/control cleanup rejection preserves Some owner, failed release returns owned foreign pin", "not_claimed_in_named_body": ["cache owner identity exhaustion", "missing-WASI or same-owner WASI-underflow injection"], "cross_named_evidence": ["construction_and_operation_phase_boundaries", "first_cause_retains_actual_wasi_usage", "component_cleanup_and_first_cleanup_invariant"]},
    "construction_and_operation_phase_boundaries": {"promoted_helper": "review_exact_phase_and_header_admission_boundaries", "observed": "exact-minus1/exact combined construction/operation admission; header-minus1/header/header+patch-minus1/exact fixed arena thresholds; no allocations before denial; existing one-shot/foreign-proof/omitted-completion/nested previous-bound cases"},
    "component_cleanup_and_first_cleanup_invariant": {"promoted_helpers": ["review_final_header_refund_fault_actual_wasi_and_prior_cause", "review_cleanup_expired_deadline_exact_work_and_latched_terminal"], "observed": "actual-WASI final header foreign-ticket fault preserves original charge and prior cause; ordinary failure/invariant/expired-clock/exact-work/terminal cleanup remain allocation-free", "not_claimed_in_named_body": ["missing-WASI or same-owner WASI-underflow injection"]},
    "sticky_failure_has_no_new_effects": {"observed": "PinLimit first failure repeated five times; exact failure, no new allocation/work/reservation/live/cache-usage effects", "not_claimed_in_named_body": ["repetition after every other terminal failure kind"]},
    "frozen_layout_allocation_work_error_snapshots": {"observed": "compiler sizes/alignments/offsets, explicit inventory fit checks, exact current cache snapshots", "separate_executable_evidence": "legacy-parity-receipt.json covers unchanged original full allocation/work/error traces in four mode/feature pairs; full replay is not asserted inside this named body"},
    "external_surface_and_borrow_privacy": {"observed": "downstream positive and negative compilation privacy probes, internal ordinary view lifetime and owned pin release", "separate_executable_evidence": "candidate1 independent internal borrow/privacy probes remain separate review evidence"},
}
for test in tests:
    test["execution_scope"] = qualifications.get(test["name"], {"observed": "Original named source assertions and exact executed output; requirement completeness remains an independent review question."})
save("coverage-map.json", {"scope": "exact command/source mapping with explicit assertion qualifications; contract requirements are not blanket execution claims", "tests": tests,
    "independent_review_only": {"missing_or_same_owner_underflow_WASI": "verification/swift-function-cache-review/independent-probes.json", "internal_borrow_privacy": "verification/swift-function-cache-review/internal-privacy.json"}})

preserved = json.loads((HERE.parent / "candidate-1/preservation-map.json").read_text())
assert preserved["producer_receipt_sha256"] == "90d80a9b29aca64f07bcda56196b29523dbf1635fedb8d393f807591e5c43fdd"
for item in preserved["evidence"].values():
    assert digest((ROOT / item["preserved"]).read_bytes()) == item["sha256"]
for name,value in preserved["source"].items():
    if isinstance(value,dict):
        assert digest((ROOT/value["preserved"]).read_bytes())==value["sha256"]

# Binding every C2 evidence file preserves failed development models as history.
bindings = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "producer-receipt.json" and "__pycache__" not in p.parts}
for name in [
    "verification/swift-cache-stage-acceptance.json",
    "verification/swift-cache-stage-contract/proposal-receipt.json",
    "verification/swift-cache-stage-contract/acceptance.json",
    "verification/swift-observation-accounting/acceptance.json",
    "verification/swift-validation-deadline-repair/isolated-2/receipt.json",
    "docs/swift-cache-stage-contract.md", "docs/swift-reactor-execution-stage-design.md",
    "verification/swift-function-cache/candidate-1/preservation-map.json",
    "verification/swift-function-cache/candidate-1/evidence/producer-receipt.json",
    "verification/swift-function-cache-review/candidate-1-review-receipt.json",
    "verification/swift-function-cache-review/independent-probes.json",
    "verification/swift-function-cache-review/internal-privacy.json",
    "verification/swift-function-cache-review/candidate2-final-map/decision-receipt.json",
    "verification/swift-function-cache-review/candidate2-final-map/map-check-receipt.json",
    "verification/swift-function-cache-review/candidate2-final-map/measurement-receipt.json",
    "verification/swift-function-cache-review/candidate2-final-map/assessment.md",
]:
    bindings[name] = digest((ROOT / name).read_bytes())

matrix = [{"argv": c["argv"], "passed": c["total_passed"]} for c in reg["commands"][:16]]
receipt = {
    "schema": "mixer-private-swift-function-cache-producer-v2",
    "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "producer_commands_passed_independent_acceptance_pending",
    "baseline_revision": BASE,
    "source_manifest_sha256": source_digest,
    "source_manifest": "verification/swift-function-cache/candidate-2/source-freeze.json",
    "owned_source_sha256": {name: source[name] for name in owned},
    "root_owned_frozen_sha256": root_expected,
    "regression_source_manifest_sha256": reg["source_manifest_sha256"],
    "named_source_manifest_sha256": named["source_manifest_sha256"],
    "tools": reg["tools"],
    "feature_matrix": matrix,
    "qualification": {"regression_commands": 21, "supplemental_reference_commands": 2,
                      "named_commands": 36, "named_tests_per_mode": 18,
                      "explicit_ignored_reference_tests_per_mode": 9,
                      "legacy_comparisons": legacy["comparisons"],
                      "native_exports_unchanged": 28, "native_headers_unchanged": 3},
    "layout": {"cleanup": 62096, "header": 62424, "construction": 57128,
               "operation": 80566, "foundation": 16504,
               "accounting": "named logical Rust object and requested payload model; not compiler-stack or RSS"},
    "historical_observations": [
        {"result": "Candidate1 commands passed but independent review found missing named assertions and typed/scalar accounting. Exact original receipt/source/evidence remain preserved; candidate2 is a new qualification."},
        {"result": "Intermediate preflight models exceeded their initially assigned slots and stopped before root foundation edits. Explicit const evaluation and complete natural-group whole-slot phases fit unchanged16504; all failed measurements are preserved."},
        {"result": "Original root10ms validation-allocation timing failure and separate root-owned bounded-retry test repair remain bound through candidate1 preservation and root receipt; no validator or budget semantics change."},
        {"result": "Named nonce-only exhaustion and PinLimit-only sticky repetition are accurately qualified; missing/same-owner-WASI-underflow and internal borrow probes stay independent review evidence."},
    ],
    "bindings": bindings,
    "pending": ["independent cache implementation source/assertion/accounting review and root acceptance",
                "executor implementation and composed final-tail accounting",
                "53,777,114-byte target instantiation/initialization/invocation and target performance",
                "physical iOS/Android runs (phones disconnected)",
                "immutable published package consumer/dogfood, signing, stores, release and GA gates"],
    "limits": {"target_instantiated": False, "target_initialized": False, "target_invoked": False,
               "physical_devices_discovered_or_run": False, "public_execution_route_added": False,
               "dependencies_added": False, "commits_or_pushes_by_cache_agent": False,
               "ga_gate_state_changes": 0},
}
assert layout["exclusive_cache_header"]["total"] == receipt["layout"]["header"]
for name, value in source.items():
    assert digest((ROOT / name).read_bytes()) == value, name
save("producer-receipt.json", receipt)
print(json.dumps({"status": receipt["status"], "source_manifest_sha256": source_digest,
                  "producer_receipt_sha256": digest((HERE / "producer-receipt.json").read_bytes()),
                  "source_files": len(source), "overlay_files": len(overlays)}, indent=2))
