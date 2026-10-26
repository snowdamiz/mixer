"""Root reconciliation of corrected runner evidence, without executing fixtures."""
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/swift-envelope-ci-runner-correction"
REVIEW = ROOT / "verification/swift-envelope-ci-independent-review/correction-review-1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(base, rows):
    for row in rows:
        p = base / row["path"]
        if not p.is_file() or p.is_symlink() or p.stat().st_size != row["bytes"] or sha(p) != row["sha256"]:
            raise ValueError("Evidence differs: " + str(p))
    return {"members": len(rows), "bytes": sum(r["bytes"] for r in rows)}


def selected(path, digest):
    if sha(path) != digest:
        raise ValueError("Selected seal differs: " + str(path))
    return json.loads(path.read_bytes())


producer = selected(PRODUCER / "seal.json", "853d2af30d63e4a6941625871d9b3787f1c6ab304c2bf7625d2d278bfdda8739")
producer_count = check(PRODUCER, producer["members"])
check(ROOT, producer["external_files"])
review = selected(REVIEW / "seal.json", "ffd313b3b6b1f267c248f058d4c85751960f053d5520237aa30f22b68c608e22")
review_count = check(ROOT, review["members"])
if producer_count != {"members": 368, "bytes": 72314809} or review_count != {"members": 10789, "bytes": 826693684}:
    raise ValueError("Packet totals differ")
tree = hashlib.sha256(json.dumps(review["members"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
if tree != review["tree_sha256"] or review["remaining_blockers"]:
    raise ValueError("Review binding/recommendation differs")
pack = ROOT / "verification/swift-envelope-ci-pack"
manifest = selected(pack / "manifest.json", "4800e90fa39b81d0e6514afa087a77b93f838204883974df7fbbec4c69a21b9a")
pack_count = check(pack, manifest["members"])
audit = json.loads((REVIEW / "raw-evidence-audit.json").read_bytes())
for row in audit["prior_seals_preserved"]:
    if sha(ROOT / row["path"]) != row["sha256"]:
        raise ValueError("Prior seal changed")
if audit["remaining_blockers"] or audit["producer_tests_loaded"]:
    raise ValueError("Independent scope differs")
commands = streams = runs = 0
for run in sorted((REVIEW / "portable-root/runs").iterdir()):
    receipt_path = run / "receipt.json"
    if not receipt_path.is_file():
        raise ValueError("Incomplete recorded review run")
    receipt = json.loads(receipt_path.read_bytes())
    for command in receipt["commands"]:
        if not command["child_returned"] or not command["owned_group_gone"] or command["timed_out"]:
            raise ValueError("Unfinished recorded command")
        check(run, [command["stdout"], command["stderr"]])
        commands += 1
        streams += 2
    runs += 1
if (runs, commands, streams) != (83, 795, 1590):
    raise ValueError("Recorded invocation/command/stream totals differ")
clean_row = audit["clean_actual_host"]["receipt"]
check(ROOT, [clean_row])
clean_path = ROOT / clean_row["path"]
clean = json.loads(clean_path.read_bytes())
if clean["status"] != "passed-host-fixture-check" or clean["errors"] or len(clean["commands"]) != 23:
    raise ValueError("Clean full closure incomplete")
for command in clean["commands"]:
    expected = 1 if command["name"].startswith("api-negative-") else 0
    if command["exit"] != expected:
        raise ValueError("Unexpected clean-run exit")
retained = clean["cleanup"]["test_files"]
if len(retained) != 92 or not clean["cleanup"]["removed"]:
    raise ValueError("Clean retention/cleanup incomplete")
for row in retained.values():
    path = clean_path.parent / row["path"]
    check(clean_path.parent, [row])
    data = gzip.decompress(path.read_bytes()) if row["encoding"] == "gzip" else path.read_bytes()
    if len(data) != row["original_bytes"] or hashlib.sha256(data).hexdigest() != row["original_sha256"]:
        raise ValueError("Retained original bytes differ")
control_map = json.loads((REVIEW / "original-52-control-map.json").read_bytes())
if len(control_map["rows"]) != 52 or control_map["counted_52_pass_claim"]:
    raise ValueError("Original control accounting differs")
if (audit["clean_actual_host"]["comparisons"] != 21714
        or len(audit["clean_actual_host"]["layouts"]) != 32
        or not audit["separate_blackbox_blocker_closure"]["identity_refused_before_compile"]
        or not audit["separate_blackbox_blocker_closure"]["API_valid_identity_wrong_primary_under_O_refused"]):
    raise ValueError("Required corrected behavior absent")
result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__))], "python_version": sys.version,
    "status": "accepted-scoped-corrected-fixture-envelope-CI-runner",
    "producer": producer_count, "independent": review_count, "runtime_pack": pack_count,
    "producer_seal_sha256": sha(PRODUCER / "seal.json"),
    "independent_seal_sha256": sha(REVIEW / "seal.json"),
    "independent_tree_sha256": tree, "pack_manifest_sha256": sha(pack / "manifest.json"),
    "runner_sha256": sha(ROOT / "scripts/ci/check-analyzer-envelope.py"),
    "tests_sha256": sha(ROOT / "scripts/ci/tests/test_analyzer_envelope_runner.py"),
    "raw_recorded_invocations": runs, "raw_commands_verified": commands, "raw_streams_verified": streams,
    "independent_control_scope": {"parser_normal": 346, "parser_optimized": 346,
                                  "distinct_actual_blocker_refusals": 2,
                                  "synthetic_valid_baselines": 1, "synthetic_expected_refusals": 39,
                                  "invalid_first_fixture_invocations_preserved_excluded": 40},
    "clean_actual_Rust_1_99": {"producer_methods": 78, "independent_methods": 14,
                              "API_positive": 1, "API_expected_negative": 8, "primary_targets": 23,
                              "comparisons": 21714, "layouts": 32,
                              "retained_files": 92, "independent_actual_File_files": 79,
                              "elapsed_seconds": clean["elapsed_seconds"],
                              "receipt_sha256": sha(clean_path)},
    "original_52_control_dispositions": dict(collections.Counter(r["status"] for r in control_map["rows"])),
    "not_52_passed_tests": True,
    "limitations": ["Only actual Rust1.99.0 Apple arm host is presently qualified; Rust1.98.1 actual CI is still required.",
                    "Whole480/60 deadline exhaustion, every timeout class, active-phase interruption and valid local PATH/rustup-symlink variants were not separately forced.",
                    "Prior fault controls are reused only for unchanged runner functions and identical pack bytes; rejected round1 parser results remain rejected.",
                    "Synthetic responses and compiler interposition establish runner refusal behavior, not product semantics or compiler qualification.",
                    "The earlier40 invalid reviewer fixture invocations are preserved and excluded from accepted counts.",
                    "All output paths in later transport manifests are archive members/provenance unless also explicitly selected as ordinary files."],
    "root_acceptance": True, "CI_workflow_wiring_selected": True,
    "CI_1_98_1_envelope_qualified": False, "fullReplayAccepted": False,
    "storedPrefixValidated": False, "semanticMetricsValid": False,
    "native_runtime_or_capture_started": False, "GA_qualified": False,
    "pending": ["Apply exact selected narrow CI workflow patch, commit/push and inspect actual1.98.1 results",
                "Semantic replay/real adapters/custody and live VM/CLI/target integration",
                "Native, phone, signing/store, immutable published FieldLog, customer/operational and accountable GA evidence"],
}
path = OUT / "corrected-runner-acceptance.json"
if path.exists():
    raise ValueError("Acceptance already recorded")
path.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "producer": producer_count, "review": review_count,
                  "commands": commands, "streams": streams, "acceptance_sha256": sha(path)}, indent=2))
