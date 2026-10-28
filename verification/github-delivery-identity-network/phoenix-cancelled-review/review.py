#!/usr/bin/env python3
"""Offline, metadata-only review of the retained cancelled CI artifact."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

PACKET = Path(__file__).resolve().parent
REPOSITORY = PACKET.parents[2]
EXTRACTED = PACKET / "extracted"
SHA = "756695fb9b0f6ec85d978202e2b3c586aa3db16f"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def dump(name, value):
    (PACKET / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(*args, input=None):
    result = subprocess.run(
        ["git", *args], cwd=REPOSITORY, input=input, capture_output=True, timeout=15
    )
    if result.returncode:
        raise RuntimeError("Read-only git command failed: " + args[0])
    return result.stdout


foundation = EXTRACTED / "_temp/phoenix-foundation"
protocol = next(EXTRACTED.glob(
    "mixer/mixer/verification/hosted-browser-auth-protocol/attempts/20261028*/receipt.json"
))
storage = next(EXTRACTED.glob(
    "mixer/mixer/verification/hosted-browser-session-storage/attempts/20261028*/receipt.json"
))
migration = next(EXTRACTED.glob("_temp/browser-migrations/*/receipt.json"))
protocol_receipt, storage_receipt, migration_receipt = map(
    read_json, (protocol, storage, migration)
)
protocol_sources = read_json(protocol.parent / "source-inputs.json")["files"]
storage_manifest = read_json(storage.parent / "source-manifest.json")
source_maps = {
    "protocol": protocol_sources,
    "storage": storage_manifest["sources"],
    "migration": migration_receipt["sources"],
}
archive_sources = {}
with tarfile.open(foundation / "source.tar.gz", "r:gz") as archive:
    for member in archive.getmembers():
        if member.isfile():
            archive_sources[member.name] = digest(archive.extractfile(member).read())
source_maps["foundation_archive"] = archive_sources
all_paths = sorted(set().union(*(set(m) for m in source_maps.values())))
batch_input = "".join(f"{SHA}:{path}\n" for path in all_paths).encode()
batch = git("cat-file", "--batch", input=batch_input)
offset, expected = 0, {}
for path in all_paths:
    end = batch.index(b"\n", offset)
    header = batch[offset:end].decode()
    if header.endswith(" missing"):
        expected[path] = None
        offset = end + 1
        continue
    _, object_type, size = header.split()
    assert object_type == "blob", path
    size = int(size)
    content = batch[end + 1:end + 1 + size]
    assert batch[end + 1 + size:end + 2 + size] == b"\n"
    expected[path] = digest(content)
    offset = end + 2 + size
assert offset == len(batch)
bindings = {}
for label, source_map in source_maps.items():
    mismatches = {
        path: {"retained_sha256": value, "commit_sha256": expected[path]}
        for path, value in source_map.items() if expected[path] != value
    }
    bindings[label] = {
        "files": len(source_map), "all_match_exact_commit": not mismatches,
        "mismatches": mismatches,
        "source_tree_sha256": digest(json.dumps(
            source_map, sort_keys=True, separators=(",", ":")
        ).encode()),
    }
storage_manifest_matches = (
    digest((storage.parent / "source-manifest.json").read_bytes())
    == storage_receipt["source_manifest_sha256"]
)
storage_after_matches = (
    (storage.parent / "source-manifest.json").read_bytes()
    == (storage.parent / "source-manifest-after.json").read_bytes()
)
saved_migration_inputs = {}
for path, value in source_maps["migration"].items():
    saved = migration.parent / "inputs" / path
    saved_migration_inputs[path] = saved.is_file() and digest(saved.read_bytes()) == value
bindings["storage"]["manifest_receipt_hash_matches"] = storage_manifest_matches
bindings["storage"]["before_after_manifests_identical"] = storage_after_matches
bindings["migration"]["retained_inputs_all_match_manifest"] = all(saved_migration_inputs.values())
bindings["migration"]["retained_input_mismatches"] = [
    path for path, okay in saved_migration_inputs.items() if not okay
]
bindings["protocol"]["receipt_tree_matches_inputs_tree"] = (
    protocol_receipt["source_tree_sha256"]
    == read_json(protocol.parent / "source-inputs.json")["tree_sha256"]
)
protocol_output_paths = [
    EXTRACTED / "mixer/mixer" / command[key]
    for command in protocol_receipt["commands"] for key in ("stdout", "stderr")
]
migration_output_mismatches = [
    name for name, value in migration_receipt["outputs_sha256"].items()
    if not (migration.parent / name).is_file()
    or digest((migration.parent / name).read_bytes()) != value
]
migration_command_log_mismatches = []
for command in migration_receipt["commands"]:
    for suffix in ("stdout", "stderr"):
        name = command["name"] + "." + suffix
        path = migration.parent / name
        if not path.is_file() or digest(path.read_bytes()) != command[suffix + "_sha256"]:
            migration_command_log_mismatches.append(name)
log_bindings = {
    "protocol": {
        "command_count": len(protocol_receipt["commands"]),
        "all_recorded_exit_codes_zero": all(c["exit_code"] == 0 for c in protocol_receipt["commands"]),
        "referenced_output_files": len(protocol_output_paths),
        "all_referenced_output_files_preserved": all(p.is_file() for p in protocol_output_paths),
        "receipt_log_hashes": "Not present; ZIP manifest hashes preserve exact retained output bytes.",
    },
    "storage": {
        "command_count": len(storage_receipt["commands"]),
        "all_recorded_exit_codes_zero": all(c["exit_code"] == 0 for c in storage_receipt["commands"]),
        "recorded_command_timeouts": [c["name"] for c in storage_receipt["commands"] if c["timed_out"]],
        "receipt_log_hashes": "Not present; ZIP manifest hashes preserve exact retained output bytes.",
    },
    "migration": {
        "command_count": len(migration_receipt["commands"]),
        "all_recorded_exit_codes_zero": all(c["exit_code"] == 0 for c in migration_receipt["commands"]),
        "recorded_command_timeouts": [c["name"] for c in migration_receipt["commands"] if c["timed_out"]],
        "receipt_output_hash_count": len(migration_receipt["outputs_sha256"]),
        "receipt_output_hash_mismatches": migration_output_mismatches,
        "command_log_hash_mismatches": migration_command_log_mismatches,
    },
    "foundation": {
        "receipt_log_hashes": "Unavailable: no final collector receipt. Retained log bytes are bound by the verified artifact ZIP and zip-manifest.json.",
    },
}
dump("log-bindings.json", log_bindings)
dump("source-bindings.json", {
    "commit": SHA, "commit_tree": git("rev-parse", f"{SHA}^{{tree}}").decode().strip(),
    "read_only_git_version": git("--version").decode().strip(),
    "source_maps": bindings,
    "method": "Read retained manifests; hash each nested archive/input file; compare SHA-256 with exact commit blobs using read-only git cat-file --batch (15s cap). No checkout or index mutation.",
})

job_log = (PACKET / "phoenix-job.log").read_text(encoding="utf-8-sig")
job_lines = job_log.split("\n")


def marker(needle):
    matches = [(i + 1, line) for i, line in enumerate(job_lines) if needle in line]
    assert len(matches) == 1, (needle, len(matches))
    line_number, line = matches[0]
    return {"line": line_number, "timestamp": line.split(" ", 1)[0], "message": line.split(" ", 1)[1]}


def elapsed(first, last):
    def parse(value):
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return round((parse(last["timestamp"]) - parse(first["timestamp"])).total_seconds(), 6)


checkout_start = marker("##[group]Run actions/checkout@v4")
checkout_end = marker("##[group]Run actions/setup-node@v4")
fetch_start = marker("##[group]Fetching the repository")
fetch_end = marker("* [new ref]")
tree_start = marker("##[group]Checking out the ref")
tree_done = marker("Updating files: 100% (338637/338637), done.")
foundation_start = marker("##[group]Run python3 scripts/test-local.py")
cancel = marker("##[error]The operation was canceled.")
timing = {
    "checkout_action_start": checkout_start,
    "checkout_complete_before_next_action": checkout_end,
    "checkout_action_upper_bound_seconds": elapsed(checkout_start, checkout_end),
    "fetch_start": fetch_start, "fetch_new_ref": fetch_end,
    "fetch_observed_seconds": elapsed(fetch_start, fetch_end),
    "worktree_checkout_start": tree_start, "worktree_files_complete": tree_done,
    "worktree_checkout_observed_seconds": elapsed(tree_start, tree_done),
    "foundation_step_start": foundation_start, "cancellation": cancel,
    "foundation_step_to_cancel_seconds": elapsed(foundation_start, cancel),
    "configured_job_timeout_minutes": 15,
    "configured_harness_per_command_timeout_seconds": 300,
    "cancellation_cause": "Not explicit in retained log or API. API conclusion remains cancelled. Long checkout consumed about 11m24s of the configured 15-minute job budget; timing is consistent with budget exhaustion, but this is an inference, not a proven cause or product regression.",
}
dump("timing.json", timing)

test_bytes = (foundation / "tests.log").read_bytes()
test_text = test_bytes.decode()
test_lines = test_text.split("\n")
last_nonempty = [(i + 1, line) for i, line in enumerate(test_lines) if line.strip()][-1]
last_completion = [(i + 1, line.split("\r")[-1]) for i, line in enumerate(test_lines)
                   if re.search(r"\* test .* \([\d.]+ms\) \[L#\d+\]", line)][-1]
last_module = [(i + 1, line) for i, line in enumerate(test_lines)
               if re.match(r"MixerHosted\..* \[test/", line)][-1]
historical = []
for path in EXTRACTED.rglob("receipt.json"):
    if "/20261025" not in str(path):
        continue
    receipt = read_json(path)
    historical.append({
        "path": str(path.relative_to(EXTRACTED)),
        "source_revision": receipt.get("source_revision", receipt.get("head")),
        "status": receipt.get("status"),
        "focused_tests_passed": receipt.get("focused_tests_passed"),
        "excluded_from_current_runtime_verdict": True,
    })
lifecycle = []
for path in sorted((foundation / "identity-lifecycle").glob("*.json")):
    value = read_json(path)
    lifecycle.append({
        "path": str(path.relative_to(EXTRACTED)), "sha256": digest(path.read_bytes()),
        "case_id": value.get("case_id"), "cleanup": value.get("cleanup", value),
        "cleanup_errors": value.get("cleanup_errors"),
        "scope": "Named completed/observed case resources only; does not establish final foundation collector, PostgreSQL, BEAM, or current unfinished test cleanup.",
    })
orphan_lines = [
    {"line": i + 1, "timestamp": line.split(" ", 1)[0], "message": line.split(" ", 1)[1]}
    for i, line in enumerate(job_lines) if "Terminate orphan process:" in line
]
summary = {
    "schema": 1,
    "reviewed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "review_complete_current_run_cancelled",
    "repository": "snowdamiz/mixer", "run_id": 40723227254,
    "job_id": 122939477520, "source_revision": SHA,
    "source_tree": git("rev-parse", f"{SHA}^{{tree}}").decode().strip(),
    "artifact_id": 12831598909,
    "artifact_sha256": digest((PACKET / "artifact.zip").read_bytes()),
    "zip": {k: read_json(PACKET / "zip-manifest.json")[k] for k in ["files", "uncompressed_bytes"]},
    "source_bindings": bindings,
    "log_bindings": log_bindings,
    "current_receipts": {
        "protocol": {"path": str(protocol.relative_to(EXTRACTED)), "status": protocol_receipt["status"], "tests": protocol_receipt["selected_host_tests"], "cleanup": protocol_receipt["cleanup"]},
        "storage": {"path": str(storage.relative_to(EXTRACTED)), "focused_tests_passed": storage_receipt["focused_tests_passed"], "reported_test_result": "24 passed", "cleanup": storage_receipt["cleanup"]},
        "migration": {"path": str(migration.relative_to(EXTRACTED)), "success": migration_receipt["success"], "tests": read_json(migration.parent / "result.json"), "cleanup": migration_receipt["cleanup"]},
    },
    "foundation_runtime_frontier": {
        "test_log_sha256": digest(test_bytes), "test_log_bytes": len(test_bytes),
        "last_module": {"line": last_module[0], "message": last_module[1]},
        "last_completed_trace": {"line": last_completion[0], "message": last_completion[1]},
        "last_entered_trace": {"line": last_nonempty[0], "message": last_nonempty[1]},
        "finished_summary_present": any(re.match(r"^Finished in", line) for line in test_lines),
        "collector_timeout_marker_present": "COLLECTOR: command exceeded 300 seconds" in test_text,
        "foundation_receipt_present": (foundation / "receipt.json").exists(),
        "postgres_stop_log_present": (foundation / "postgres-stop.log").exists(),
        "verdict": "Foundation suite outcome and final source-unchanged check unproven. Last trace entering K08b has no completion line; it does not prove that test failed, hung, or caused cancellation.",
        "earlier_steps": "The collector reached its suite after format, test compilation, production release build/missing-config rejection/export exclusion, disposable PostgreSQL setup and fixture creation. Sequential fail-fast source supports that those preceding commands returned acceptable results; absent final receipt prevents recovering per-command exit/duration manifest.",
    },
    "cleanup": {
        "current_earlier_receipts": "Protocol scratch removal, storage PostgreSQL/scratch removal, migration PostgreSQL/scratch/compile-product removal are recorded true in their exact current receipts.",
        "foundation_owned_cleanup": "Not proven: final receipt and postgres-stop.log absent. Per-case lifecycle resource observations do not prove whole-collector cleanup.",
        "runner_orphan_termination": orphan_lines,
        "runner_cleanup_limit": "Runner reports termination attempts; no exact resource inventory or post-termination absence proof is retained. Do not claim no survivors or graceful collector shutdown.",
        "lifecycle_case_observations": lifecycle,
    },
    "historical_contamination": {
        "count": len(historical), "receipts": historical,
        "cause_supported_by_source": "Committed upload paths recursively include repository verification attempt directories; full checkout materialized tracked historical attempts. No old receipt is accepted as a current pass.",
    },
    "timing": timing,
    "scope_limits": [
        "Offline artifact/log/source review only; no CI rerun, dispatch, product runtime, local Docker/PostgreSQL, native runtime, UI, screen capture, or process inventory.",
        "Writes restricted to this review packet; no Git/index/metadata/memory changes.",
        "Cancelled run is not product, deployed provider/Neon/Cloudflare, native, customer, or GA acceptance.",
        "Connector tool versions are not exposed. Review Python and read-only Git versions are recorded separately.",
        "The first artifact connector response was accidentally emitted in the tool transcript, exposing its temporary signed file-reference URL; no signed URL was persisted into this packet. Subsequent acquisition outputs were sanitized.",
    ],
    "review_command": "python3 verification/github-delivery-identity-network/phoenix-cancelled-review/review.py",
    "review_python": sys.version,
}
dump("review.json", summary)
print(json.dumps({
    "status": summary["status"], "source_revision": SHA,
    "source_bindings_all_match": all(row["all_match_exact_commit"] for row in bindings.values()),
    "historical_receipts_excluded": len(historical),
    "checkout_seconds_upper_bound": timing["checkout_action_upper_bound_seconds"],
    "foundation_step_to_cancel_seconds": timing["foundation_step_to_cancel_seconds"],
    "last_trace": summary["foundation_runtime_frontier"]["last_entered_trace"],
    "foundation_final_receipt_present": summary["foundation_runtime_frontier"]["foundation_receipt_present"],
}, indent=2))
