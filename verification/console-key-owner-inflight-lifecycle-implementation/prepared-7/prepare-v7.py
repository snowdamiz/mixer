#!/usr/bin/env python3
"""Offline custody source freeze; no control/native/compiler process is run."""
from pathlib import Path
import ast
import hashlib
import json
import secrets
import subprocess
import sys
import time
import errno
import traceback

START = time.monotonic()
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PRIOR = LANE / "prepared-6"
PREPARED = LANE / "prepared-7"


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def pin(path, relative=None):
    if time.monotonic() - START >= 55:
        raise TimeoutError("offline preparation 55-second limit")
    data = path.read_bytes()
    return {"path": relative or str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(relative, value):
    path = PREPARED / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else encoded(value))


def obj(fields):
    return {"type": "object", "fields": fields}


def string(values=None, maximum=4096):
    return {"type": "string", "max": maximum, **({"enum": values} if values is not None else {})}


def integer(minimum=0, maximum=2**63-1, value=None):
    return {"type": "integer", "min": minimum, "max": maximum, **({"value": value} if value is not None else {})}


def boolean():
    return {"type": "boolean"}


def array(items, maximum, minimum=0):
    return {"type": "array", "items": items, "min": minimum, "max": maximum}


def main():
    prior_seal = json.loads((PRIOR / "freeze.json").read_bytes())
    assert pin(PRIOR / "freeze.json")["sha256"] == "b80c8f9857bdd5245904219075156cecc7ece85941ebcd8ef210a4c974179751"
    for row in prior_seal["files"]:
        assert pin(PRIOR / row["path"], row["path"]) == row
    selection_path = ROOT / "verification/console-session-and-checkout-root-review/inflight-openssl-custody-selection.json"
    assert pin(selection_path)["sha256"] == "d2f458ff628154099d175a7882bf0d37006806eb40298b2066aa374d135d8077"
    selection = json.loads(selection_path.read_bytes())["selection"]
    assert [row["id"] for row in selection["binding_amendments"]] == ["OCR-A1", "OCR-A2", "OCR-A3"]
    review_path = ROOT / "verification/console-key-owner-inflight-lifecycle-independent/custody-controls-terminal-review-1/decision.json"
    assert pin(review_path)["sha256"] == "d6d6d40a5e33c9d175e330ef719ab084c3ef7a60014b3dd734d8f51d72432354"
    review = json.loads(review_path.read_bytes())
    assert [row["id"] for row in review["findings"]] == ["CCT-01", "CCT-02"]
    PREPARED.mkdir(exist_ok=False)
    replaced = {"execution-plan.json", "control-plan.json", "preparation-audit.json", "README.md", "runner.py", "verify.py", "prepare-v6.py",
                "artifact-validation.py", "required-artifact-schemas.json", "bin/openssl", "custody.py", "openssl-custody-wrapper.py",
                "custody-controls.py", "fake-custody-child.py", "control-artifact-schema.json", "custody-artifact-schema.json"}
    for row in prior_seal["files"]:
        target = "inputs/prior-prepared-6/" + row["path"] if row["path"] in replaced else row["path"]
        write(target, (PRIOR / row["path"]).read_bytes())
    write("inputs/prior-prepared-6/freeze.json", (PRIOR / "freeze.json").read_bytes())
    write("inputs/root-review/inflight-openssl-custody-selection.json", selection_path.read_bytes())
    for name in ["contract", "review"]:
        path = ROOT / selection[name]["path"]
        assert pin(path)["sha256"] == selection[name]["sha256"]
        write("inputs/root-review/selected-ownership-" + name + ".json", path.read_bytes())
    write("inputs/root-review/custody-controls-terminal-review-1-decision.json", review_path.read_bytes())
    for role in ["control_report", "root_release", "scratch_provenance"]:
        selected = review[role]
        source = ROOT / selected["path"]
        assert pin(source)["sha256"] == selected["sha256"]
        write("inputs/control-terminal-3/" + role + ".json", source.read_bytes())
    for name in ["custody.py", "openssl-custody-wrapper.py", "custody-controls.py", "fake-custody-child.py", "vm_cleanup.py", "process_authority.py", "permission_controls.py", "prepare-v7.py"]:
        write(name, (LANE / name).read_bytes())
    write("runner.py", (LANE / "runner-v7.py").read_bytes())
    write("artifact-validation.py", (LANE / "artifact-validation-v7.py").read_bytes())
    write("verify.py", (LANE / "verify-v7.py").read_bytes())
    write("README.md", (LANE / "OWNERSHIP-IMPLEMENTATION-v7.md").read_bytes())
    plan = json.loads((PRIOR / "execution-plan.json").read_bytes())
    accepted_updates = {"hosted/mix.lock": "1eada39dcaf4863d02d39f51e218d2bad8908b36a0cba47ff2d16037b7bcf837",
                        "THIRD_PARTY.yml": "cf69c9f95dc06632897d64d9389ea20ee9affa75fc1c8a5a5fa6706106cbb997"}
    canonical = []
    for row in plan["canonical_inputs"]:
        assert row["path"] != "hosted/test/mixer_hosted/identity/key_owner_test.exs"
        current = pin(ROOT / row["path"], row["path"])
        if row["path"] in accepted_updates:
            assert current["sha256"] == accepted_updates[row["path"]]
            write("inputs/prior-prepared-6/" + row["path"], (PREPARED / ("inputs/" + row["path"])).read_bytes())
            write("inputs/" + row["path"], (ROOT / row["path"]).read_bytes())
        else:
            assert current == row, "unselected canonical change: " + row["path"]
        canonical.append(current)
    plan["canonical_inputs"] = canonical
    import re
    dependency_status = []
    lock_text = (ROOT / "hosted/mix.lock").read_text()
    for dep in plan["dependencies"]:
        app = ROOT / "hosted/_build/test/lib" / dep["name"] / "ebin" / (dep["name"] + ".app")
        versions = re.findall(r'\{vsn,\s*"([^"]+)"\}', app.read_text())
        assert versions == [dep["version"]]
        selected = re.findall(r'"' + re.escape(dep["name"]) + r'": \{:hex, :[^,]+, "([^"]+)"', lock_text)
        assert len(selected) == 1
        dependency_status.append({"name": dep["name"], "actual_local_version": versions[0], "canonical_lock_version": selected[0],
                                  "compatible": versions[0] == selected[0], "application_pin": pin(app)})
    assert [row["name"] for row in dependency_status if not row["compatible"]] == ["jose"]
    write("dependency-compatibility.json", {"schema": 1, "source_only": True, "shared_dependencies_changed": False,
          "dependencies": dependency_status, "real_runtime_dependency_closure_compatible": False,
          "scope": "Only the five dependencies actually loaded by this frozen host closure; no compile/runtime or replacement dependency preparation"})
    python = plan["python"]
    wrapper = (LANE / "openssl-custody-wrapper.py").read_bytes().split(b"\n", 1)[1]
    write("bin/openssl", ("#!" + python + " -B\n").encode() + wrapper)
    tools = list(plan["tools"])
    for row in tools:
        assert pin(Path(row["path"])) == row
    known = {row["path"] for row in tools}
    for module in list(sys.modules.values()):
        value = getattr(module, "__file__", None)
        if value and Path(value).is_file() and str(Path(value).resolve()).startswith(str(Path(sys.base_prefix).resolve())):
            path = Path(value).resolve()
            if str(path) not in known:
                tools.append(pin(path))
                known.add(str(path))

    packet = json.loads((PRIOR / "required-artifact-schemas.json").read_bytes())
    recipe_ids = ["version", "fixture-1-ca", "fixture-1-leaf", "fixture-1-sign", "fixture-2-ca", "fixture-2-leaf", "fixture-2-sign"]
    binding = {"run_nonce": string(maximum=128), "phase": string(["test"]), "ordinal": integer(0, 15),
               "recipe_id": string(recipe_ids), "invocation_nonce": string(maximum=128)}
    for key in ["starts", "invocations"]:
        fields = packet["schemas"]["test/openssl-invocations.json"]["fields"][key]["items"]["fields"]
        fields.update({**binding, "registration_sha256": string(maximum=64), "ack_sha256": string(maximum=64), "child_group": integer()})
    process_diagnostic = obj({"source": string(["custodian", "wrapper"]), **binding, "ordinal": integer(-1, 15), "recipe_id": string(maximum=128),
        "wrapper_pid": integer(), "wrapper_pgid": integer(), "wrapper_sid": integer(), "native_pid": integer(),
        "operation": string(maximum=128), "errno": integer(), "errno_name": string(maximum=128), "strerror": string(),
        "exception_type": string(maximum=128), "message": string(), "traceback": string(maximum=65536), "at_ns": integer(), "permission_refused": boolean()})
    process_schema = obj({"permission_refused": boolean(), "operations": array(obj({"operation": string(maximum=128), "attempts": integer(1)}), 16),
                          "diagnostics": array(process_diagnostic, 8)})
    record = obj({**binding, **{key: integer(2) for key in ["wrapper_pid", "wrapper_pgid", "wrapper_sid"]},
        **{key: string(maximum=64) for key in ["request_sha256", "ack_sha256", "completion_sha256"]},
        **{key: boolean() for key in ["ack_issued", "native_started", "child_reaped", "released", "group_absent", "identity_lost", "permission_denied", "authority_closed", "identity_retained", "wrapper_exit_observed"]}, "child_pid": integer(),
        "refusal_completion_sha256": string(maximum=64), "process": process_schema,
        "closure": string(["active", "released-observe", "exited-observe", "lost-observe", "permission-refused", "group-absent"])})
    event = obj({"sequence": integer(0, 127), "event": string(["registered", "ack-intent", "exit-grant-intent", "child", "completion", "group-absent", "identity-lost", "signal", "process-refused"]),
                 "ordinal": integer(-1, 15), "at_ns": integer(), "detail": string(maximum=4096)})
    custody_schema = obj({"schema": integer(value=1), "run_nonce": string(maximum=128), "phase": string(["test"]),
        "grants": integer(0, 7), "launch_latch_open": boolean(), "uncertain": boolean(), "errors": array(string(), 32),
        "records": array(record, 16), "events": array(event, 128), "evidence_diagnostics": array(process_diagnostic, 8), "journal_reconciled": boolean(), "journal_sha256": string(maximum=64)})
    packet["schemas"]["test/custody-result.json"] = custody_schema
    packet["required_artifacts"] = 18
    write("required-artifact-schemas.json", packet)
    case_ids = ["happy", "no-ack", "journal-failure", "cancel-after-ack", "native-timeout", "immutable-and-bindings",
                "out-of-order", "prepublication", "post-spawn-prepublication", "journal-short-write", "journal-zero-write",
                "journal-fsync-failure", "journal-truncation", "completion-acceptance-short-write", "exit-grant-intent-fsync-failure",
                "wrapper-term", "malformed-ack", "replayed-ack"]
    diagnostic_schema = obj({"call": string(), "errno": integer(0, 2**31-1), "errno_name": string(maximum=128),
        "strerror": string(), "exception_type": string(maximum=128), "message": string(), "traceback": string(maximum=65536),
        "pid": integer(2), "pgid": integer(2), "sid": integer(2), "at_ns": integer()})
    helper_schema = obj({"pid": integer(2), "pgid": integer(2), "sid": integer(2),
        **{key: boolean() for key in ["identity_retained", "identity_lost", "permission_denied", "completed_observed", "direct_child_reaped", "group_absent", "uncertain", "returncode_known"]},
        "mode": string(["completed-observe", "running-retirement", "unproven-observe"]),
        "signals": array(integer(1, 31), 2), "returncode": integer(-(2**31), 2**31-1), "diagnostics": array(diagnostic_schema, 32)})
    permission_names = ["custodian-probe-EPERM", "custodian-TERM-EPERM", "wrapper-getpgid-EPERM", "wrapper-terminate-EPERM", "released-observe-only"]
    permission_schema = array(obj({"check": string(permission_names), "injected": {"type": "boolean", "value": True}, "processes_started": integer(value=0),
        "passed": boolean(), "fixture_cleanup": string(["synthetic-no-OS-child"]), "custody_state": string(["unresolved-refused", "unresolved-observe"]),
        "operations_before_refusal": array(string(maximum=128), 32), "operations_after_refusal": array(string(maximum=128), 32),
        "process": process_schema, "custody_record": array(record, 1), "native_wait_known": {"type": "boolean", "value": False}, "clean_custody": {"type": "boolean", "value": False}}), 5)
    control_schema = obj({"schema": integer(value=1), "status": string(["passed", "failed"]),
        "cases": array(obj({"case_id": string(case_ids), **{key: boolean() for key in ["passed", "native_started", "groups_absent", "wrapper_reaped", "uncertain", "scratch_preserved", "journal_reconciled", "signal_delivered", "completion_before_exit", "fault_observed"]}, "grants": integer(0, 1),
             "fault_operation": string(["", "helper", "write-short", "write-zero", "fsync-error", "truncate", "ack-malformed", "ack-replay"]),
             "fault_event": string(maximum=32), "fault_bytes_requested": integer(0, 131072), "fault_bytes_written": integer(0, 131072)}), 18),
        "errors": array(string(maximum=131072), 64), "preserved_scratch": array(string(), 18), "elapsed_ms": integer(0, 55000),
        "vm_cleanup_subchecks": array(obj({"case_id": string(["happy", "native-timeout"]),
            "check": string(["completed-no-signal", "running-timeout"]), "passed": boolean(), "timeout_observed": boolean(), "cleanup": helper_schema}), 2),
        "permission_subchecks": permission_schema,
        "fixture_observations": array(obj({"case_id": string(case_ids), "wrapper_pid": integer(2), "direct_reaped": boolean(),
            "custody_permission_refused": boolean(), "custody_resolution": string(["unresolved-refused", "observed"]), "fixture_group_probe_performed": boolean()}), 17)})
    write("control-artifact-schema.json", control_schema)
    write("custody-artifact-schema.json", custody_schema)
    for path in PREPARED.rglob("*.py"):
        ast.parse(path.read_bytes(), filename=str(path.relative_to(PREPARED)))
    files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    plan.update({"status": "prospective-custody-real-runtime-unexecuted-awaiting-independent-source-review-and-exact-root-release",
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "tools": tools, "prepared_files": files,
        "source_tree_sha256": hashlib.sha256(encoded([row for row in files if row["path"].startswith("inputs/hosted/")])).hexdigest(),
        "openssl_accounting": "Durable pre-native request, retained exact leader/group, journal fsync then immutable ACK; explicit phase/ordinal/recipe. Issued ACK can race cancellation and remains owned. Native child wait, held leader, exit grant and terminal group absence replace the disproved VM-group equality.",
        "known_execution_blockers": ["Independent custody source/control-plan review and separate exact root release; no control has run"],
        "pending": ["Independent source/plan review and separately released fake controls before real-runtime release",
            "Actual nine-method host/production compile and TLS cases; KOL09 adverse outcome remains failed",
            "Bootstrap/leader-loss uncertainty fails and preserves scratch; no universal containment guarantee",
            "Original KOL08 crash adaptation, application/provider/operations/GA; native/UI/capture/phones paused"],
        "custody_amendments": selection["binding_amendments"], "runtime_release_granted": False})
    assert "custody-result.json" in plan["phases"][1]["required_artifacts"]
    assert plan["custody_implementation_corrections"] == ["CIR-01", "CIR-02", "CIR-03"]
    assert plan["direct_VM_cleanup_corrections"] == ["CIR5-01", "CIR5-02"]
    plan["permission_corrections"] = [row["id"] for row in review["findings"]]
    plan["real_runtime_dependency_closure_compatible"] = False
    plan["dependency_compatibility"] = "dependency-compatibility.json"
    plan["permission_policy"] = "Operation-tagged errno/traceback, sticky per-invocation refusal, no later process operation or alternate kill; released/observed-exit wrapper closure is observe-only; fixture-owned reap never clears unresolved custody."
    plan["direct_VM_cleanup_policy"] = "Completed wait/poll means observe-only forever. Active group signals require still-running exact retained leader and PID/PGID/SID recheck. EPERM is sticky, no retry/alternate kill API. Exact call/errno/traceback retained; unresolved cleanup preserves scratch."
    plan["journal_policy"] = "Complete checked writes and file/directory fsync before acceptance; full completion acceptance before immutable exit grant; strict disk/memory/spool terminal reconciliation required before clean cleanup/result."
    plan["known_execution_blockers"] = ["Independent prepared-7 source/plan review and separately released 18 fake controls, including actual wrapper TERM, before real runtime release"]
    plan["pending"].append("No runtime coverage is claimed for output overflow, missing completion, late/partial registration or INT/HUP; those paths remain pending")
    plan["known_execution_blockers"].append("Actual local JOSE1.11.12 is stale against canonical1.11.13; real runner refuses launch until a compatible closure is independently selected in a new packet")
    write("execution-plan.json", plan)
    control = {"schema": 1, "status": "prospective-fake-child-controls-unexecuted-awaiting-independent-review-and-exact-root-release",
        "kind": "custody-controls-no-product-tests", "tools": tools, "prepared_files": files, "python": python,
        "source_revision": plan["source_revision"], "source_tree_sha256": plan["source_tree_sha256"],
        "workspace_root": str(ROOT), "canonical_inputs": plan["canonical_inputs"],
        "cases": case_ids, "maximum_fake_native_grants": 10, "maximum_fake_native_launches": 10, "maximum_custody_fake_native_launches": 8, "actual_OpenSSL_TLS_Elixir_or_product_methods": 0,
        "limits": plan["limits"], "execution_output": "executions/custody-controls-4",
        "command": [python, "-B", str(PREPARED / "custody-controls.py"), "--release", "ABSOLUTE_EXACT_ROOT_RELEASE"],
        "expected_failure_semantics": "Control pass means expected ownership/no-native/uncertainty assertions held; deliberate failures remain failed real-run states with scratch preserved.",
        "runtime_release_granted": False,
        "signal_case": "wrapper-term sends real TERM to the exact direct wrapper while acknowledged native fake child is active; distinct from manager cancellation",
        "journal_fault_cases": {"before_ACK": ["journal-failure", "journal-short-write", "journal-zero-write", "journal-fsync-failure"],
            "after_ACK_no_clean_receipt": ["journal-truncation", "completion-acceptance-short-write", "exit-grant-intent-fsync-failure"]},
        "wrapper_ACK_rejections": ["malformed-ack", "replayed-ack"],
        "pending_unclaimed_control_paths": ["output overflow", "missing completion", "late/partial registration", "INT/HUP delivery"],
        "custody_implementation_corrections": plan["custody_implementation_corrections"],
        "direct_VM_cleanup_corrections": plan["direct_VM_cleanup_corrections"],
        "shared_VM_helper_subchecks": ["happy: completed-no-signal", "native-timeout: running-timeout"],
        "combined_artifact_cap_includes_terminal_control_report": True,
        "EPERM": "sticky authority closure; no retry or alternate kill method; exact syscall/errno/traceback; historical call remains unknown",
        "permission_corrections": plan["permission_corrections"], "synthetic_permission_subchecks": permission_names,
        "synthetic_permission_additional_processes": 0, "dependency_compatibility": "dependency-compatibility.json",
        "historical_control_evidence": {"control_report_sha256": review["control_report"]["sha256"], "actual_cases_passed": 18,
            "actual_VM_helper_checks_passed": 2, "historical_EPERM_syscall": "unknown", "real_runtime_recommended": False}}
    write("control-plan.json", control)
    write("preparation-audit.json", {"schema": 1, "status": "offline-source-custody-preparation-only-passed",
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-implementation/prepare-v7.py",
        "python": sys.version, "canonical_inputs_bound": len(plan["canonical_inputs"]), "unchanged_product_and_other_inputs": len(plan["canonical_inputs"]) - 2,
        "root_selected_metadata_updates": accepted_updates,
        "product_methods_unchanged": 9, "real_required_artifact_schemas": 18, "prospective_control_cases": 18, "prospective_shared_VM_helper_subchecks": 2, "prospective_synthetic_permission_subchecks": 5,
        "new_control_native_compiler_formatter_TLS_or_product_execution": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6)})
    rows = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    freeze = {"schema": 1, "status": "frozen-custody-source-and-separate-prospective-plans-unexecuted",
        "sole_excluded_relative_path": "freeze.json", "files": rows, "tree_sha256": hashlib.sha256(encoded(rows)).hexdigest(),
        "execution_plan_sha256": pin(PREPARED / "execution-plan.json")["sha256"],
        "control_plan_sha256": pin(PREPARED / "control-plan.json")["sha256"],
        "source_tree_sha256": plan["source_tree_sha256"], "runtime_or_control_release_granted": False}
    write("freeze.json", freeze)
    print(json.dumps({"status": "frozen-unexecuted-custody-source-ready-for-independent-review", "files": len(rows),
        "freeze_sha256": pin(PREPARED / "freeze.json")["sha256"], "execution_plan_sha256": freeze["execution_plan_sha256"],
        "control_plan_sha256": freeze["control_plan_sha256"], "canonical_product_sources_unchanged": True, "canonical_metadata_updates": accepted_updates}, indent=2))


if __name__ == "__main__":
    main()
