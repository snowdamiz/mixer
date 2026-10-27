#!/usr/bin/env python3
"""Root review of two released packets; never executes their authoring scripts."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
D = Path(__file__).resolve().parent


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def packet(name, expected):
    root = ROOT / "verification" / name
    assert identity(root / "seal.json")["sha256"] == expected
    seal = read(root / "seal.json")
    paths = set()
    total = 0
    for member in seal["members"]:
        relative = Path(member["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        assert relative.as_posix() not in paths
        paths.add(relative.as_posix())
        target = root / relative
        assert not target.is_symlink()
        assert identity(target) == {"bytes": member["bytes"], "sha256": member["sha256"]}
        total += member["bytes"]
    assert len(paths) == seal["member_count"]
    allowed = paths | {"seal.json"}
    if "self_seal_metadata" in seal:
        meta = seal["self_seal_metadata"]
        assert meta == {"bytes": 76, "path": "seal.sha256", "exact_content": "lowercase sha256 of seal.json + two ASCII spaces + seal.json + LF"}
        assert (root / meta["path"]).read_bytes() == (expected + "  seal.json\n").encode()
        allowed.add(meta["path"])
    actual = set()
    for target in root.rglob("*"):
        assert not target.is_symlink()
        if target.is_file():
            actual.add(target.relative_to(root).as_posix())
    assert actual == allowed
    return root, {"path": str(root.relative_to(ROOT)), "seal_sha256": expected,
                  "members_verified": len(paths), "bytes_verified": total,
                  "exact_path_set_verified": True}


def main():
    android, ac = packet("android-finite-ledger-controls", "f90c7fd6240fd8fc63c3c16ac01997e673747d222136271764e1e657ad447a0b")
    swift, sc = packet("swift-retained-profile-composition-stdio-correction", "01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2")
    context = "1b71af17048675296435ca74af284d54f93f2506b9c406517a452a3ce816dbdd"
    source_map = read(android / "inputs/selected-product-source-map.json")
    class_map = read(android / "inputs/selected-product-class-map.json")
    assert len(source_map) == 16 and len(class_map) == 209
    assert hashlib.sha256(json.dumps({"source_map": source_map, "class_map": class_map}, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == context
    for path, expected in source_map.items():
        assert identity(android / "inputs/product" / path) == expected
        assert identity(ROOT / "verification/android-source-pair5-coherent-integration-preparation/source/native/android/app/src/dev/mixer/android" / path) == expected
    for path, expected in class_map.items():
        assert identity(android / "run-3/classes" / path) == expected
    roster = read(android / "inputs/source-roster.json")
    leaves = [row for row in roster if row["role"] == "exact-selected-B-leaf"]
    assert len(leaves) == 87
    for row in leaves:
        assert identity(android / row["path"]) == identity(ROOT / row["origin"]) == {"bytes": row["bytes"], "sha256": row["sha256"]}
    proposal = read(android / "proposal.json")
    originals = {row["id"]: row for row in read(android / "inputs/original-three-subjects.json")["subjects"]}
    result = read(android / "run-3/actual-ledger-results.json")
    assert result["invocations"] == len(result["rows"]) == 87 and result["checks"] == 3823
    expected_inputs = {
        "null-empty": ["null"],
        "ordinary-primary-preserved": ["ordinary-A", "ordinary-B", "null"],
        "ordinary-then-error": ["ordinary-A", "Error-A", "ordinary-B", "Error-B", "null"],
        "error-then-ordinary": ["Error-A", "ordinary-A", "Error-B", "ordinary-B", "null"],
        "repeated-distinct-errors": ["Error-A", "Error-B", "Error-A", "Error-C"],
        "null-then-ordinary-and-error": ["null", "null", "ordinary-A", "Error-A"],
        "retained-fatal-before-primary": ["null", "ordinary-A", "Error-A", "null"],
        "checked-ordinary-then-error": ["checked-A", "Error-A", "checked-B"],
    }
    subjects = []
    for subject in proposal["subjects"]:
        sid = subject["id"]
        original = originals[sid]
        assert subject["categories"] == subject["original_categories"] == original["categories"]
        assert subject["required_semantic_cases"] == subject["original_required_case_ids"]
        assert len(subject["original_case_dispositions"]) == 6
        assert all(row["enclosing_execution_join"] is None for row in subject["original_case_dispositions"])
        assert class_map[subject["class"] + ".class"]["sha256"] == subject["class_sha256"]
        assert subject["source_rationale"]["actual_invocations"] == []
        rows = [row for row in result["rows"] if row["subject_id"] == sid]
        assert len(rows) == 29
        for name, inputs in expected_inputs.items():
            sequence = [row for row in rows if row["sequence"] == name]
            assert [row["input"] for row in sequence] == inputs
            primary, fatal = "null", "Error-C" if name == "retained-fatal-before-primary" else "null"
            for index, row in enumerate(sequence):
                assert row["step"] == index
                assert row["primary_before"] == primary and row["first_fatal_before"] == fatal
                if inputs[index] != "null" and primary == "null":
                    primary = inputs[index]
                if inputs[index] in ("Error-A", "Error-B", "Error-C") and fatal == "null":
                    fatal = inputs[index]
                assert row["primary"] == primary and row["first_fatal"] == fatal
                assert row["class_sha256"] == subject["class_sha256"]
                assert row["typed_result"] == "void-normal-return" and row["leaf_events"] == row["bridge_effects"] == 0
                if "$Observer#" in sid:
                    assert row["diagnostics_after"] is False
                else:
                    assert row["diagnostics_before"] is row["diagnostics_after"] is None
        subjects.append({"id": sid, "class_sha256": subject["class_sha256"], "fresh_producer_invocations": len(rows), "original_case_ids": subject["required_semantic_cases"]})
    commands = read(android / "run-3/commands.json")
    assert len(commands) == 4 and all(row["exit"] == 0 and not row["timeout"] and row["reaped"] for row in commands)
    for command in commands:
        for kind in ("stdout", "stderr"):
            log = command[kind]
            assert identity(android / "run-3" / log["path"]) == {"bytes": log["bytes"], "sha256": log["sha256"]}
    cleanup = read(android / "run-3/cleanup.json")
    assert cleanup["all_started_children_reaped"] and cleanup["scratch_removed"]
    common = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "reviewer": "root", "command": [sys.executable, "-B", str(Path(__file__))],
              "script": identity(Path(__file__)), "python": sys.version, "platform": platform.platform(),
              "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "root_fresh_runtime_execution": False, "canonical_native_OTA_GA_accepted": False}
    save(D / "finite-ledger-root-custody.json", {**common, **ac, "source_context": context,
        "product_sources": 16, "product_classes": 209, "selected_B_leaves": 87, "subjects": subjects,
        "producer_invocations_verified": 87, "producer_identity_state_checks": 3823,
        "root_review": "Read complete finite Java harness and runner; inspect exact three product bodies, original categories/cases, source/class maps, command logs and all actual result rows; independently reconcile first-primary/first-Error identity semantics including Observer null diagnostic invalidation.",
        "producer_cleanup": cleanup})
    acceptance = {**common, "status": "three-finite-method-component-controls-selected",
        "packet": ac, "custody": identity(D / "finite-ledger-root-custody.json"), "source_context": context,
        "subjects": subjects, "scope": "Exact finite remember(Throwable) bodies only. Root source/oracle/result review accepts the 87 producer direct calls for subsequent fresh selected-matrix consumption; no additional runtime replay is claimed.",
        "source_specific_exception": "Observer clears diagnosticsAttached on every call including null. Owner/coordinator null is inert. Primary and first Error reference identities remain independent.",
        "limitations": ["Fixture scalar/held-state seeding is component evidence, not enclosing lifecycle reachability.", "Six original obligations per subject remain; no counted-busy balance, cleanup completion, reentrancy/refusal, target-close or enclosing exception propagation acceptance.", "Final producer reexecution joins, full compiled boundary/applicability/execution closure and canonical integration remain pending.", "Authoring run-1 setup refusal and filename-only listing deviation retained; no unrelated contents executed."]}
    save(D / "finite-ledger-selection.json", acceptance)
    save(ROOT / "verification/swift-retained-profile-composition-stdio-correction-root-custody.json", {**common, **sc,
        "status": "frozen-candidate-custody-verified-independent-behavior-review-active",
        "producer_receipt": identity(swift / "receipt.json"), "producer_commands": 213,
        "producer_unchanged_lifecycle_cases": 142, "producer_new_stdio_cases": 57,
        "new_healthy_zero_cases": 5, "new_unresolved_cases": 52,
        "old_C01_required_failure_retained": True, "raw_new_C01_mechanism_mismatch_is_not_pass": True,
        "candidate_behavior_accepted": False,
        "root_audit_correction": "Initial read-only audit incorrectly treated self_seal_metadata.exact_content as literal bytes. It is a format description; all659 members matched, and this corrected audit verifies the exact76-byte digest sidecar and closed path set."})
    print(json.dumps({"android_members": ac["members_verified"], "android_rows": 87,
                      "android_selection": identity(D / "finite-ledger-selection.json"),
                      "swift_members": sc["members_verified"], "swift_bytes": sc["bytes_verified"]}))


if __name__ == "__main__":
    main()
