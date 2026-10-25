#!/usr/bin/env python3
"""Verify root-owned admission collection bytes; never starts a database."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
RUN = ROOT / "verification/hosted-build-admission/attempt-2"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    return sha(path.read_bytes())


receipt = json.loads((RUN / "receipt.json").read_text())
assert receipt["status"] == "passed"
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
inputs = receipt["inputs"]
assert all(file_sha(ROOT / path) == digest for path, digest in inputs.items())
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
assert file_sha(RUN / "source.tar.gz") == receipt["source_archive_sha256"]
with tarfile.open(RUN / "source.tar.gz", "r:gz") as archive:
    assert set(archive.getnames()) == set(inputs)
    assert all(sha(archive.extractfile(path).read()) == digest for path, digest in inputs.items())
assert all(file_sha(RUN / command["log"]) == command["sha256"] for command in receipt["commands"])
assert all(command["exit_code"] == command.get("expected_exit_code", 0) for command in receipt["commands"])

test_path = OWN / "independent_test.exs"
names = re.findall(r'^  test "([^"]+)"', test_path.read_text(), re.M)
assert len(names) == 11
output = (RUN / "tests.log").read_text()
section = output.split("MixerHosted.BuildAdmissionReview.Test [", 1)[1].split("\nMixerHosted.Builds.AdmissionTest", 1)[0]
assert all(name in section for name in names)
producer_names = re.findall(r'^  test "([^"]+)"', (ROOT / "hosted/test/mixer_hosted/builds/admission_test.exs").read_text(), re.M)
assert len(producer_names) == 17
assert all(name in output for name in producer_names)
assert "Result: 227 passed, 2 skipped" in output
proof_text = section.split("independent_post_lock_expiry_proof:", 1)[1].split("}", 1)[0]
proof = {key: int(re.search(rf"{key}: (\d+)", proof_text).group(1))
         for key in ("transaction_begun_ms", "fixture_expiry_ms", "before_unlock_ms")}
assert proof["transaction_begun_ms"] < proof["fixture_expiry_ms"] < proof["before_unlock_ms"]
assert (RUN / "postgres-timezone.log").read_text().strip() == "UTC"

result = {
    "schema": 1,
    "status": "accepted-internal-development-slice",
    "source_revision": (RUN / "revision.log").read_text().strip(),
    "source_tree_sha256": receipt["source_tree_sha256"],
    "verified_input_count": len(inputs),
    "root_receipt": str((RUN / "receipt.json").relative_to(ROOT)),
    "root_receipt_sha256": file_sha(RUN / "receipt.json"),
    "source_archive_sha256": receipt["source_archive_sha256"],
    "independent_test_sha256": file_sha(test_path),
    "test_output_sha256": file_sha(RUN / "tests.log"),
    "review_verifier_sha256": file_sha(Path(__file__)),
    "verification_command": "python3 verification/hosted-build-admission-independent-review/verify_receipt.py",
    "review_python_version": sys.version.split()[0],
    "tool_output": {
        "elixir": (RUN / "elixir-version.log").read_text().strip(),
        "postgres": (RUN / "postgres-version.log").read_text().strip(),
        "database_timezone": "UTC"
    },
    "tool_output_sha256": {name: file_sha(RUN / name) for name in ("elixir-version.log", "postgres-version.log", "postgres-timezone.log")},
    "results": {"host_passed": 227, "host_linux_only_skipped": 2, "admission_passed": 17, "independent_passed": 11},
    "post_lock_expiry_database_epoch_ms": proof,
    "checks": {
        "current_inputs_match_collected_closure": True,
        "archive_inputs_match_manifest": True,
        "all_command_output_hashes_match": True,
        "all_command_exits_match_expectations": True,
        "postgres_stopped": True,
        "scratch_removed": True
    },
    "corrected_findings": [
        "Explicit non-NULL SQL CHECK branches close malformed reservation/lease pairs.",
        "Released evidence is validated against replayed matching attempt history before readmission.",
        "Expiry fixture assignments are UTC; observed lease expiry crosses during real lock contention."
    ],
    "prior_attempt": "attempt-1 retained as pre-UTC-fixture-correction evidence; attempt-2 is authoritative",
    "scope": "Independent source review and real local PostgreSQL races, locks, expiry fixtures and atomic Oban intent persistence. Root owns runtime collection and cleanup.",
    "limitations": [
        "Capacity is shared per organization/platform; aggregate organization and provider-fleet quotas remain pending.",
        "Trusted internal Storage remains callable; public authorization, RLS, worker identity, dispatch and external-effect reconciliation remain pending.",
        "Loopback PostgreSQL without TLS is not Neon or Cloudflare operational qualification.",
        "Two existing Linux-only identity tests are skipped on this Mac; runtime migration redefinition warnings are retained in the log.",
        "No native, physical-phone, signing, publication, billing, customer or GA gate is accepted."
    ]
}
(OWN / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("status", "verified_input_count", "results", "post_lock_expiry_database_epoch_ms")}))
