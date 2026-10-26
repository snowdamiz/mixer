"""Reconcile exact private Observer/profile evidence before scoped root acceptance."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/android-environment-observer-lifecycle"
REVIEW = ROOT / "verification/android-environment-observer-independent-review"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(path, digest):
    if sha(path) != digest:
        raise ValueError("Selected record changed: " + str(path))
    return json.loads(path.read_bytes())


def verify(base, rows):
    if isinstance(rows, dict):
        rows = [dict(row, path=name) for name, row in rows.items()]
    for row in rows:
        path = base / row["path"]
        if (not path.is_file() or path.is_symlink()
                or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]):
            raise ValueError("Evidence differs: " + str(path))
    return {"members": len(rows), "bytes": sum(row["bytes"] for row in rows)}


producer = selected(PRODUCER / "manifest.json", "12ff1a93d3ea3bfcbac663745759514a72c9db78e7ef43729f697030dc393060")
pcount = verify(PRODUCER, producer["files"])
if pcount != {"members": 946, "bytes": 7811904}:
    raise ValueError("Producer totals differ")
contract_dir = ROOT / "verification/android-owner-effect-contract"
contract = selected(contract_dir / "manifest.json", "1cd715e03b7e0102c44dcc1ff92cc37af5ee8806b04ae2fde50657051dd06380")
ccount = verify(contract_dir, contract["files"])
seal = selected(REVIEW / "final-seal.json", "a2112b3233c5050af0dcb3448caf5d30b7d23fe21f833d977edf75f04471feed")
verify(ROOT, seal["members"])
manifest = selected(REVIEW / "final-manifest.json", "1907530c996913836b9456f94d514a8b4afcf37285459cf493970564e1f86acb")
rcount = verify(ROOT, manifest["files"])
if rcount != {"members": 1907, "bytes": 16480328}:
    raise ValueError("Review totals differ")
proposal = selected(PRODUCER / "candidate-proposal.json", "80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a")
proposal_inputs = verify(ROOT, proposal["files"])
host_inputs = verify(ROOT, json.loads((PRODUCER / "host-source-freeze.json").read_bytes())["files"])
review = json.loads((REVIEW / "review-receipt.json").read_bytes())
if not review["independent_review_recommendation_accept"] or review["actionable_findings_in_selected_scope"]:
    raise ValueError("Independent acceptance absent")
for entry in [review["host"], review["consumer_signature_controls"], *review["preserved_failed_attempts"]]:
    path = REVIEW / entry.get("receipt", entry.get("path"))
    if sha(path) != entry["sha256"]:
        raise ValueError("Review subreceipt differs")
host = json.loads((REVIEW / review["host"]["receipt"]).read_bytes())
for command in host["commands"]:
    if command["exit_code"] != 0 or command["timed_out"]:
        raise ValueError("Incomplete independent host command")
if (host["status"] != "passed-host-modeled-controls" or not host["cleanup"]["removed"]
        or "INDEPENDENT_OBSERVER_SUCCESS cases=287 assertions=24363" not in host["commands"][-1]["stdout"]):
    raise ValueError("Independent host matrix incomplete")
consumer_path = REVIEW / review["consumer_signature_controls"]["receipt"]
consumer = json.loads(consumer_path.read_bytes())
streams = []
for command in consumer["commands"]:
    if (command["exit"] != command["expected_exit"] or command["timed_out"]
            or not command["child_reaped"]):
        raise ValueError("Incomplete consumer command: " + command["label"])
    for stream in ("stdout", "stderr"):
        streams.append(dict(command[stream], path=command["label"] + "." + stream))
verify(consumer_path.parent, streams)
cross = json.loads((PRODUCER / "cross-compilation-1/receipt.json").read_bytes())
if (len(consumer["classes"]) != 160 or consumer["classes"] != cross["classes"]
        or consumer["dex"] != cross["dex"]):
    raise ValueError("Independent SDK class/DEX identities differ")
if not consumer["cleanup"]["owned_scratch_removed"] or not consumer["cleanup"]["owned_children_reaped"]:
    raise ValueError("Independent owned cleanup incomplete")
if len(consumer["commands"]) != 30 or len(host["commands"]) != 4:
    raise ValueError("Independent command inventory differs")
if (ROOT / "docs/android-environment-observer-lifecycle.md").read_bytes() != (PRODUCER / "documentation.md").read_bytes():
    raise ValueError("Producer documentation differs")
result = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__))], "python_version": sys.version,
    "status": "accepted-scoped-android-observer-host-source-profile",
    "packets_verified": {"contract": ccount, "producer": pcount, "independent": rcount},
    "total_packet_members_verified": sum(x["members"] for x in (ccount, pcount, rcount)),
    "total_packet_bytes_verified": sum(x["bytes"] for x in (ccount, pcount, rcount)),
    "current_proposal_inputs_verified": proposal_inputs["members"],
    "current_host_inputs_verified": host_inputs["members"],
    "independent_commands_verified": 34, "independent_file_streams_verified": len(streams),
    "independent_inline_host_streams_bound_by_receipt": 8,
    "producer_manifest_sha256": sha(PRODUCER / "manifest.json"),
    "independent_final_seal_sha256": sha(REVIEW / "final-seal.json"),
    "independent_manifest_sha256": sha(REVIEW / "final-manifest.json"),
    "candidate_observer_sha256": review["candidate_observer_sha256"],
    "candidate_proposal_sha256": review["candidate_proposal_sha256"],
    "source_profile": cross["source_profile"],
    "accepted_scope": "Exact private Observer listener acquisition, retirement and cleanup behavior plus fixed source-pair.2 migration; host modeled lifecycle, real CLI/driver admission and compile-only signature evidence.",
    "producer": {"host_cases": 161, "Swift_admission_functions": 10, "Python_admission_tests": 9,
                 "app_host_tests": 4, "session_host_tests": 3, "java_sources": 14,
                 "classes": 160, "SDK_jar_API": "37.0", "D8_min_api": 28,
                 "app_owned_Swift_Android": "6.3.3", "NDK": "r27d"},
    "independent": {"host_cases": 287, "host_assertions": 24363, "consumer_signature_families": 22,
                    "preset_session_tests": 3, "distinct_factory_reducer_test": 1,
                    "actual_cli_driver_negative_families": 11, "driver_policy_pre_lock_negative_families": 6,
                    "java_sources": 14, "classes": 160, "DEX_bit_identical": True,
                    "app_Swift_JNI": "Producer commands, streams, sources, ELF and symbols audited; expensive cross-build not repeated."},
    "preserved_failed_attempts": review["preserved_failed_attempts"],
    "limitations": ["Host leaves do not establish real platform listener behavior or reclamation.",
                    "CLI preaccess has behavioral/no-output and source-order evidence, not an OS filesystem access trace; driver dynamic hash/tool/output traps were exercised.",
                    "Source-pair.1 locks must be rejected; use the newer first-party CLI and recreate the project explicitly. No automatic lock refresh.",
                    "Insets setter ownership is restricted to the private dedicated V2 root; no general listener composition or public V1 change.",
                    "Java/D8 compile minimum28 does not establish API28-35 runtime support; the private environment remains restricted.",
                    "Counts overlap across producer and independent suites and are not additive product coverage."],
    "pending": review["pending"], "implementation_accepted": True,
    "public_V2_selected": False, "owner_effect_runner_selected": False,
    "native_runtime_or_capture_started": False, "new_dependencies": [], "GA_qualified": False,
}
result["pending"] = [x for x in result["pending"] if x != "root-acceptance-integration-delivery-and-CI"]
result["pending"].insert(0, "scoped-commit-push-and-CI")
destination = OUT / "implementation-acceptance.json"
if destination.exists():
    raise ValueError("Acceptance already recorded")
destination.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"status": result["status"], "members": result["total_packet_members_verified"],
                  "bytes": result["total_packet_bytes_verified"], "acceptance_sha256": sha(destination)}, indent=2))
