"""One-shot root custody audit of two explicitly selected closed host packets."""
import collections
import datetime
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read(path):
    return json.loads((ROOT / path).read_text())


def identity(path):
    data = (ROOT / path).read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def check(path, expected):
    actual = identity(path)
    assert actual["bytes"] == expected["bytes"], (path, "bytes")
    assert actual["sha256"] == expected["sha256"], (path, "sha256")
    return actual


def packet(path, digest, relative=False):
    ident = identity(path)
    assert ident["sha256"] == digest, path
    obj = read(path)
    if relative:
        members = [{"path": str(pathlib.Path(path).parent / name), **info}
                   for name, info in obj["files"].items()]
    else:
        members = obj["members"]
    assert len({r["path"] for r in members}) == len(members)
    for member in members:
        check(member["path"], member)
    return {**ident, "members_verified": len(members),
            "member_bytes_verified": sum(r["bytes"] for r in members)}


def save(path, value):
    out = ROOT / path
    assert not out.exists(), path
    out.write_text(json.dumps(value, indent=2) + "\n")
    return identity(path)


at = datetime.datetime.now(datetime.timezone.utc).isoformat()
common = {"schema": 1, "at": at, "argv": sys.argv, "python": sys.version,
          "script": identity(pathlib.Path(__file__).relative_to(ROOT)),
          "native_runtime_or_capture_started": False, "GA_qualified": False,
          "implementation_accepted": False}
cli_base = pathlib.Path("verification/android-private-owner-profile3-integration/candidate4-qualification")
cli_packet = packet(cli_base / "manifest.json",
                    "ff947ccf16b055e10e3458bd9b8161b597b7744131c5eb8d7f67377736c134a6", True)
assert cli_packet["members_verified"] == 1011
for name, expected in read(cli_base / "source-binding.json")["files"].items():
    check(name, expected)
receipt = read(cli_base / "seal-receipt.json")
for name, expected in receipt["final_five"].items():
    check(name, expected)
source_map = read("verification/android-private-owner-integration-implementation/candidate-4/source-map.json")
assert len(source_map) == 309
for name, expected in source_map.items():
    check(name, expected)
commands = read(cli_base / "commands.json")
assert len(commands) == 101
labels = {r["label"]: r for r in commands}
assert len(labels) == 101
negatives = 0
for command in commands:
    assert command["child_reaped"] and not command["timed_out"], command["label"]
    assert command["exit"] == command["expected_exit"], command["label"]
    if command["expected_exit"] != 0:
        negatives += 1
    assert command["executable"]["sha256"]
assert negatives == 72, negatives
dispositions = read(cli_base / "binary-identity-disposition.json")
for name, disposition in dispositions["dispositions"].items():
    final = disposition["final_after_Swift_test"]
    for label in disposition["actual_consumer_and_refusal_commands"]:
        assert labels[label]["executable"]["sha256"] == final["sha256"], label
        assert labels[label]["executable"]["bytes"] == final["bytes"], label
for name in read(cli_base / "receipt.json")["cleanup"]["owned_scratch_removed"]:
    assert not (ROOT / cli_base / name).exists(), name
cli_result = save("verification/android-private-owner-effect-integration-root-review/candidate-4-CLI-producer-results.json", {
    **common, "status": "closed-producer-packet-custody-verified-independent-CLI-review-active",
    "packet": cli_packet, "current_source_members_verified": 356,
    "current_candidate4_source_members_verified": 309,
    "command_dispositions_verified": 101, "expected_nonzero_commands": negatives,
    "reported_Swift_methods_per_mode": 13, "reported_Python_methods_per_mode": 30,
    "actual_compiler": receipt["resolved_host_swiftc_version"],
    "binary_identity_disposition": identity(cli_base / "binary-identity-disposition.json"),
    "source_tests_and_executable_binding": "Retained producer evidence audited; independent tests and source review remain separate.",
    "complete_Android_owner_review_accepted": False,
    "no_new_product_tests_executed_by_root": True,
})
bulk_path = pathlib.Path("verification/swift-cache-state-independent-review/implementation-review-2/bulk-words-0000-root")
bulk_packet = packet(bulk_path / "bulk-results-seal.json",
                     "6fa4ff335341aa5a05eeedad550b41ed7e55a62cf78a11b40fc526f4774f14ba")
assert bulk_packet["members_verified"] == 1416
bulk = read(bulk_path / "bulk-results-receipt.json")
assert bulk["passed"] == bulk["total_public_cases"] == 192
assert bulk["failed"] == bulk["orchestration_failures"] == bulk["new_private_controls"] == 0
for batch in bulk["batches"]:
    summary = read(batch["summary_path"])
    assert summary["admitted_count"] == summary["executed_count"] == 64
    assert summary["failed_cases"] == 0 and summary["orchestration_failure"] is None
for product in bulk["all_six_returned_owned_binary_products_hashed_then_removed"]:
    assert product["removed"] and not (ROOT / product["path"]).exists()
prior = [packet(p["path"], p["sha256"]) for p in bulk["unchanged_prior_seals_and_candidate_verified"]]
bulk_result = save("verification/swift-semantic-adapter-root-review/bulk-initial-192-results.json", {
    **common, "status": "three-admitted-first64-public-batches-pass-root-custody-verified",
    "packet": bulk_packet, "prior_packets_unchanged": prior,
    "batches": bulk["batches"], "public_cases_passed": 192,
    "private_cases": 0, "new_API_controls": 0, "further_batches_run": 0,
    "returned_hashed_products_removed": 6,
    "parent_timing_limitation": bulk["parent_timing_limitation"],
    "source_budget_or_lifetime_proof_accepted": False,
    "no_new_product_tests_executed_by_root": True,
})
ci_base = pathlib.Path("verification/github-delivery-guard-review-checkpoint")
ci = read(ci_base / "ci-observation-3/stdout.json")
assert ci["headSha"] == "99f8a0a727bc08a15561d8d83b2aed8b9ad96265"
assert ci["status"] == "completed" and ci["conclusion"] == "success"
assert len(ci["jobs"]) == 3 and all(j["conclusion"] == "success" for j in ci["jobs"])
steps = collections.Counter(s["conclusion"] for j in ci["jobs"] for s in j["steps"])
assert steps == {"success": 42}, steps
ci_result = save(ci_base / "ci-terminal.json", {
    **common, "status": "passed", "head": ci["headSha"], "run_id": ci["databaseId"],
    "url": ci["url"], "completed_at": ci["updatedAt"], "jobs": 3,
    "step_conclusions": dict(steps), "skipped_steps": 0,
    "observed_output": identity(ci_base / "ci-observation-3/stdout.json"),
    "observed_command": identity(ci_base / "ci-observation-3/command.json"),
    "scope": "Committed immutable evidence and existing canonical product only; active candidate4/CLI/correction2 excluded.",
})
print(json.dumps({"CLI": cli_result, "bulk": bulk_result, "CI": ci_result}, indent=2))
