#!/usr/bin/env python3
"""Offline preparation only; no Elixir, formatter, fixture or OpenSSL invocation."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import subprocess
import sys
import time


START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PREPARED = LANE / "prepared-1"
PRIOR = ROOT / "verification/console-key-owner-lifecycle-implementation/prepared-3"
CONTRACT = ROOT / "verification/console-key-owner-inflight-lifecycle-contract"
SOURCES = ["hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex",
           "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs"]


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError("offline preparation exceeded 55 seconds")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def pin(path, relative=None):
    budget()
    data = path.read_bytes()
    return {"path": relative or str(path), "bytes": len(data), "sha256": sha(data)}


def write(relative, value):
    path = PREPARED / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if type(value) is bytes else encoded(value)
    path.write_bytes(data)


def copy_checked(source, relative, expected=None):
    data = source.read_bytes()
    if expected is not None:
        assert len(data) == expected["bytes"] and sha(data) == expected["sha256"], str(source)
    write(relative, data)


def boolean(value=None):
    return {"type": "boolean", **({"value": value} if value is not None else {})}


def integer(value=None, minimum=-(2**63), maximum=2**63-1):
    return {"type": "integer", "min": minimum, "max": maximum, **({"value": value} if value is not None else {})}


def string(values=None, maximum=65536):
    return {"type": "string", "max": maximum, **({"enum": values} if values is not None else {})}


def array(item, maximum, minimum=0):
    return {"type": "array", "items": item, "min": minimum, "max": maximum}


def obj(fields):
    return {"type": "object", "fields": fields}


def main():
    PREPARED.mkdir(exist_ok=False)
    prior = json.loads((PRIOR / "execution-plan.json").read_bytes())
    prior_files = {row["path"]: row for row in json.loads((PRIOR / "freeze.json").read_bytes())["files"]}
    selection_path = ROOT / "verification/console-session-and-checkout-root-review/inflight-lifecycle-selection.json"
    selection = json.loads(selection_path.read_bytes())["selection"]
    assert pin(CONTRACT / "freeze.json")["sha256"] == selection["contract"]["sha256"]
    review = ROOT / selection["independent_review"]["path"]
    assert pin(review)["sha256"] == "1929c914b2da1454739ee24da1956e2a6e6829110911b5a8f71d6076ad2268f4"
    assert selection["new_runtime_released"] is False
    before = LANE / "beforeimages/hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex"
    assert pin(before)["sha256"] == selection["canonical_supervisor_before"]["sha256"]

    copy_checked(before, "beforeimages/hosted/lib/mixer_hosted/identity/key_owner_supervisor.ex")
    copy_checked(LANE / "beforeimages.json", "beforeimages.json")
    copy_checked(selection_path, "inputs/root-review/inflight-lifecycle-selection.json")
    copy_checked(review, "inputs/root-review/independent-contract-review-seal.json")
    copy_checked(review.parent / "REVIEW.md", "inputs/root-review/independent-contract-review.md")
    copy_checked(CONTRACT / "freeze.json", "inputs/contract/freeze.json")
    copy_checked(CONTRACT / "contract.md", "inputs/contract/contract.md")
    copy_checked(CONTRACT / "prospective-tests.json", "inputs/contract/prospective-tests.json")

    canonical = []
    for relative in prior["source_roster"]:
        if relative == SOURCES[0]:
            copy_checked(ROOT / relative, "inputs/" + relative)
        else:
            origin = "inputs/" + relative
            copy_checked(PRIOR / origin, origin, prior_files[origin])
        canonical.append(pin(ROOT / relative, relative))
        assert canonical[-1]["sha256"] == pin(PREPARED / "inputs" / relative)["sha256"], relative
    ordinary = "hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"
    copy_checked(PRIOR / "inputs" / ordinary, "inputs/" + ordinary, prior_files["inputs/" + ordinary])
    canonical.append(pin(ROOT / ordinary, ordinary))
    assert canonical[-1]["sha256"] == pin(PREPARED / "inputs" / ordinary)["sha256"]
    copy_checked(ROOT / SOURCES[1], "inputs/" + SOURCES[1])
    canonical.append(pin(ROOT / SOURCES[1], SOURCES[1]))
    support = "hosted/test/support/identity_tls_fixture.ex"
    copy_checked(CONTRACT / "inputs/current-support/identity_tls_fixture.ex", "inputs/" + support)
    canonical.append(pin(ROOT / support, support))
    assert canonical[-1]["sha256"] == pin(PREPARED / "inputs" / support)["sha256"]
    for relative in ["AGENTS.md", "THIRD_PARTY.yml", "hosted/mix.lock", "hosted/.formatter.exs"]:
        copy_checked(ROOT / relative, "inputs/" + relative)
        canonical.append(pin(ROOT / relative, relative))
    for row in prior["prepared_files"]:
        if row["path"].startswith("dependencies/") or row["path"] == "root.pem":
            copy_checked(PRIOR / row["path"], row["path"], row)

    for name in ["runner.py", "artifact-validation.py", "compile-common.exs", "bootstrap-prod.exs",
                 "bootstrap-test.exs", "format-only.exs", "openssl-wrapper.py", "prepare.py", "runner-provenance.json",
                 "README.md", "verify.py"]:
        copy_checked(LANE / name, name)
        if name.endswith(".py"):
            ast.parse((LANE / name).read_bytes(), filename=name)

    python = str(Path(sys.executable).resolve())
    openssl = str(Path(shutil.which("openssl", path=prior["environment"]["PATH"])).resolve())
    wrapper = (LANE / "openssl-wrapper.py").read_bytes().split(b"\n", 1)[1]
    write("bin/openssl", ("#!" + python + " -B\n").encode() + wrapper)
    write("openssl-config.json", {"executable": openssl, "sha256": pin(Path(openssl))["sha256"]})

    tools = list(prior["tools"])
    for tool in tools:
        assert pin(Path(tool["path"])) == tool, "previous tool identity changed: " + tool["path"]
    for path in [Path(openssl), Path(python), Path("/opt/homebrew/Cellar/erlang/29.1.1_2/lib/erlang/lib/ssl-11.7.7/src/ssl_api.hrl")]:
        if str(path) not in {item["path"] for item in tools}:
            tools.append(pin(path))

    schemas = {}
    runtime = {"elixir": string(["1.20.4"]), "otp_release": string(["29"]),
               "node": string(["nonode@nohost"]), "schedulers_online": integer(2),
               "product_application_started": boolean(False)}
    for build in ["prod", "test"]:
        schemas[build + "/runtime.json"] = obj({**runtime, "build": string([build])})
    schemas["prod/production-exclusion.json"] = obj({key: boolean(True) for key in [
        "supervisor_fixture_export_absent", "owner_fixture_export_absent", "transport_fixture_export_absent",
        "fixture_tuple_init_rejected", "ordinary_fixture_option_rejected", "owner_absent", "workers_absent",
        "admission_absent", "loopback_denied", "product_application_not_started"]})
    schemas["test/format-check.json"] = obj({"total": integer(5), "unchanged": boolean(True)})
    schemas["test/openssl-version.json"] = obj({"output": string(maximum=4096), "exit_code": integer(0)})
    schemas["test/exunit-result.json"] = obj({"total": integer(9), "failures": integer(minimum=0, maximum=9),
                                             "skipped": integer(0), "excluded": integer(0)})
    schemas["test/postconditions.json"] = obj({**{key: boolean(True) for key in [
        "test_owners_absent", "test_workers_absent", "test_admission_absent", "default_owner_absent",
        "default_repo_absent", "product_application_not_started"]},
        "ordinary_cleanup_receipts": integer(7), "inflight_observation_receipts": integer(2)})
    old_schemas = json.loads((PRIOR / "required-artifact-schemas.json").read_bytes())

    def convert(fields):
        return obj({key: ({"type": rule["type"], "enum": rule.get("enum", [rule.get("value")])}
                          if rule["type"] == "string" else rule) for key, rule in fields.items()})

    for key in ["KOL04-cleanup.json", "KOL06-cleanup.json"]:
        schemas["test/" + key] = convert(old_schemas["schemas"]["corrected/" + key])
    for path in old_schemas["shared_schema_bindings"]["ordinary_component_cleanup"]:
        schemas[path.replace("corrected/", "test/")] = convert(old_schemas["shared_schemas"]["ordinary_component_cleanup"])
    facts = ["tls_preconditions", "raw_explicit_reply", "fresh_denial", "raw_port_closed_while_held", "parent_stop_pending", "old_resources_down_at_stop",
             "owner_alive_at_raw_reply", "table_alive_at_raw_reply", "pointer_absent_at_raw_reply", "replacement_observed",
             "old_resources_down_before_replacement", "replacement_empty", "old_permit_rejected", "stale_lease_rejected", "public_denial", "callback_clean"]
    cleanup = {**{key: string(maximum=4096) for key in ["resume_result", "component_stop_result", "fixture_stop_result"]},
               **{key: boolean() for key in ["barrier_released", "all_resources_down", "current_admission_absent", "owner_absent",
                   "workers_absent", "old_table_gone", "key_directory_removed", "fixture_peer_closed", "recorder_stopped"]}}
    resource = obj({"role": string(["fixture", "listener_socket", "acceptor", "component", "owner", "workers", "raw_caller",
        "public_caller", "server_handler", "server_socket", "flight", "worker", "controller", "raw_socket", "client_socket", "stop_caller"]),
        "id": string(maximum=128), "down": boolean(), "reason": string(maximum=4096), "down_ms": integer()})
    for case in ["KOL08-GRACEFUL", "KOL09-KILL"]:
        schemas["test/" + case + "-observation.json"] = obj({
            "schema": integer(1), "case_id": string([case]), "stage": string(["created", "completed-tls-pending-jwks",
                "controller-held-trigger-ready", "graceful-drain-held", "graceful-gate-passed", "worker-death-order-witness-retained", "worker-death-resource-gate-passed"]),
            "deadline_margin_ms": integer(minimum=-1, maximum=2000), "tls_protocol": string(["unobserved", "tlsv1.2", "tlsv1.3"]),
            "raw_reply": obj({"kind": string(["unobserved", "reply", "exit"]), "result": string(maximum=16384), "before_deadline": boolean(),
                "observed_at_ms": integer(), "pointer": string(maximum=128), "owner_alive": boolean(), "table_alive": boolean()}),
            "resume_results": array(string(maximum=4096), 8),
            "public_reply": string(maximum=4096), "fault_reason": string(maximum=16384), "cleanup_errors": array(string(maximum=4096), 32),
            "observations": obj({key: boolean() for key in facts}), "cleanup": obj(cleanup), "resources": array(resource, 64),
            "pointer_samples": array(obj({"phase": string(["before-trigger", "raw-reply-observed", "replacement-while-old-controller-held"]),
                "at_ms": integer(), "kind": string(["absent", "old", "current", "other"]), "table": string(maximum=128)}), 8)})
    invocation = obj({"executable": string([openssl]), "args": array(string(maximum=4096), 32, 1),
        **{key: integer(minimum=1) for key in ["wrapper_pid", "child_pid", "parent_pid", "process_group", "started_ns", "finished_ns"]},
        "exit_code": integer(minimum=-255, maximum=255), "output": string(maximum=65536), "output_cap_exceeded": boolean()})
    launch = obj({key: value for key, value in invocation["fields"].items() if key not in ["exit_code", "output", "output_cap_exceeded", "finished_ns"]})
    schemas["test/openssl-invocations.json"] = obj({"starts": array(launch, 7, 7), "invocations": array(invocation, 7, 7)})
    write("required-artifact-schemas.json", {"schema": 1, "required_artifacts": len(schemas), "schemas": schemas,
          "scope": "Exact field/type schemas; failures are retained and clean-gate acceptance is checked separately."})
    format_schema = obj({"files": array(obj({"source": string(SOURCES), "source_sha256": string([pin(ROOT / p)["sha256"] for p in SOURCES]),
        "output": string([Path(p).name for p in SOURCES]), "bytes": integer(minimum=1, maximum=131072),
        "sha256": string(maximum=64), "changed": boolean()}), 2, 2)})
    write("format-artifact-schemas.json", {"schema": 1, "required_artifacts": 1, "schemas": {"format/formatting.json": format_schema}})

    files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    source_rows = [row for row in files if row["path"].startswith("inputs/hosted/")]
    source_tree = sha(encoded(source_rows))
    plan = {
        "schema": 1, "status": "frozen-unexecuted-candidate-needs-separate-format-only-release-first",
        "workspace_root": str(ROOT), "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree_sha256": source_tree, "tools": tools, "canonical_inputs": canonical, "prepared_files": files,
        "elixir": prior["elixir"], "boot": prior["boot"], "python": python, "openssl": openssl,
        "dependencies": prior["dependencies"], "environment": prior["environment"], "source_roster": prior["source_roster"],
        "artifact_schemas": "required-artifact-schemas.json", "limits": {"work_seconds": 40, "cleanup_seconds": 46,
            "post_seconds": 52, "wall_seconds": 55, "phase_output_bytes": 524288, "combined_output_bytes": 1048576,
            "artifact_bytes": 524288, "combined_artifact_bytes": 1048576},
        "phases": [{"id": build, "build": build, "bootstrap": "bootstrap-" + build + ".exs", "source_replacements": {},
                    "required_artifacts": [path.split("/", 1)[1] for path in schemas if path.startswith(build + "/")]} for build in ["prod", "test"]],
        "scope": "Fresh prod/test VMs, production fixture-export/init exclusion and seven unchanged ordinary plus two new completed-TLS/pending-JWKS cases. Exactly one real local TLS fixture at a time. No product app/DB/Repo/endpoint/provider/DNS fixture/native/UI/capture/global inventory.",
        "openssl_accounting": "One explicit version invocation plus exactly three pinned native OpenSSL commands per fixture, two sequential fixtures; wrapper retains exact argv, PIDs, group, output, exit and timing. Native children inherit retained test group; wrapper reaps each exact native child; outer runner confirms retained VM group absent.",
        "warning_policy": "Zero compiler diagnostics. Full stdout/stderr retained with no blanket OTP warning/error suppression. Intentional worker kill reports are distinct from terminate callback exception; callback exception or early replacement fails resource gate.",
        "formatting": "Five-file read-only equality before OpenSSL/TLS. First use separately released formatting-plan.json, review/apply exact two owned formatter outputs, then freeze a new runtime candidate. No canonical source write by either runner.",
        "pending": ["Separate format-only and runtime plan reviews/releases", "Actual nine-method/production-build compilation and execution",
            "Observed KOL09 adverse or clean witness; no speculative product cleanup fix selected", "Original KOL08 ordinary owner-crash adaptation",
            "Production destination/provider/application/HTTP/browser/session/custody/operations/GA", "Native/UI/capture/emulators/phones remain paused"],
    }
    write("execution-plan.json", plan)
    format_plan = {**plan, "status": "frozen-unexecuted-format-only-plan-no-product-compilation-or-tests",
        "artifact_schemas": "format-artifact-schemas.json", "phases": [{"id": "format", "build": "test", "bootstrap": "format-only.exs",
        "source_replacements": {}, "required_artifacts": ["formatting.json"]}],
        "scope": "Two owned source files formatted to run-local outputs only; no product source compilation/loading, no test, TLS or OpenSSL/version process and no canonical writes.",
        "pending": ["Review and apply exact authorized formatter outputs, freeze successor source/runtime plan", "All production/test/TLS lifecycle and GA qualification remains pending"]}
    write("formatting-plan.json", format_plan)
    write("preparation-audit.json", {"schema": 1, "status": "offline-preparation-only-passed-no-runtime-acceptance",
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-implementation/prepare.py", "python": sys.version,
        "source_tree_sha256": source_tree, "new_methods": 2, "retained_ordinary_methods": 7, "future_method_total": 9,
        "source_files": len(source_rows), "tools_pinned": len(tools), "OpenSSL_processes_started": 0,
        "compiler_formatter_runtime_fixture_invocations": 0, "elapsed_seconds": round(time.monotonic() - START, 6)})
    all_files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    write("freeze.json", {"schema": 1, "status": "frozen-source-and-plan-unexecuted-awaiting-review-and-separate-root-release",
        "sole_excluded_relative_path": "freeze.json", "files": all_files, "tree_sha256": sha(encoded(all_files)),
        "execution_plan_sha256": pin(PREPARED / "execution-plan.json")["sha256"],
        "formatting_plan_sha256": pin(PREPARED / "formatting-plan.json")["sha256"], "source_tree_sha256": source_tree,
        "runtime_release_granted": False})
    print(json.dumps({"status": "frozen-unexecuted-ready-for-plan-review-format-only-first", "files": len(all_files),
        "source_tree_sha256": source_tree, "execution_plan_sha256": pin(PREPARED / "execution-plan.json")["sha256"],
        "formatting_plan_sha256": pin(PREPARED / "formatting-plan.json")["sha256"]}, indent=2))


if __name__ == "__main__":
    main()
