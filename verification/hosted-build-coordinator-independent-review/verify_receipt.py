#!/usr/bin/env python3
"""Rehash coordinator runtime evidence without starting databases or services."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUN = ROOT / "verification/hosted-build-coordinator/attempt-5-final"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


receipt_path = RUN / "receipt.json"
receipt = json.loads(receipt_path.read_bytes())
assert receipt["status"] == "passed"
assert receipt["test_selection"] == "repository suite and explicit independent tests"
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}
inputs = receipt["inputs"]
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
assert sha((RUN / "source.tar.gz").read_bytes()) == receipt["source_archive_sha256"]

required = [
    "hosted/lib/mixer_hosted/builds/coordinator.ex",
    "hosted/lib/mixer_hosted/builds/dispatch.ex",
    "hosted/lib/mixer_hosted/builds/admission.ex",
    "verification/hosted-build-coordinator-independent-review/independent_test.exs",
    "verification/hosted-build-coordinator-independent-review/processor_test.exs",
]
assert all(path in inputs for path in required)
with tarfile.open(RUN / "source.tar.gz") as archive:
    entries = archive.getmembers()
    assert len(entries) == len(inputs)
    assert {entry.name for entry in entries} == set(inputs)
    for entry in entries:
        assert entry.isfile()
        assert sha(archive.extractfile(entry).read()) == inputs[entry.name], entry.name
        assert sha((ROOT / entry.name).read_bytes()) == inputs[entry.name], entry.name

for command in receipt["commands"]:
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    assert sha((RUN / command["log"]).read_bytes()) == command["sha256"], command["label"]

log = (RUN / "tests.log").read_text()
assert "Result: 261 passed, 2 skipped" in log
assert not re.search(r"^  \d+\) test ", log, re.MULTILINE)
counts = {}
for name, expected in {
    "MixerHosted.Builds.CoordinatorTest": 19,
    "MixerHosted.BuildCoordinatorReview.Test": 14,
    "MixerHosted.BuildCoordinatorProcessorReview.Test": 1,
    "MixerHosted.BuildAdmissionReview.Test": 11,
}.items():
    section = log.split(name + " [", 1)[1].split("\nMixerHosted.", 1)[0]
    completed = re.findall(r"^  \* test .+ \([\d.]+ms\) \[L#\d+\]$", section, re.MULTILINE)
    assert len(completed) == expected, (name, len(completed))
    counts[name] = len(completed)

assert "mode: :asynchronous_oban_processor" in log
assert "testing: :disabled" in log
assert 'worker: "MixerHosted.Builds.Coordinator"' in log
assert "independent_coordinator_processor_cleanup: owned Oban supervisor stopped; dedicated database rows cleared" in log
assert (RUN / "postgres-timezone.log").read_text().strip() == "UTC"
exclusion = (RUN / "release-test-exclusion.log").read_text()
assert "production_build_coordinator: present; modeled dispatch helpers: absent" in exclusion
exclusion_command = next(command for command in receipt["commands"] if command["label"] == "release-test-exclusion")
assert "MixerHosted.BuildCoordinatorProcessorReview.Adapter" in exclusion_command["argv"][-1]
assert "MixerHosted.BuildCoordinatorProcessorReview.Test" in exclusion_command["argv"][-1]

skips = [line.strip() for line in log.splitlines() if "(skipped)" in line]
assert len(skips) == 2
assert any("K03 production resolver" in line for line in skips)
assert any("IS04 IS05 actual configured startup" in line for line in skips)

result = {
    "schema": "mixer.independent-coordinator-evidence-check.v1",
    "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "passed",
    "command": "python3 verification/hosted-build-coordinator-independent-review/verify_receipt.py",
    "argv": sys.argv,
    "python_version": sys.version,
    "verifier_sha256": sha(Path(__file__).read_bytes()),
    "root_receipt": str(receipt_path.relative_to(ROOT)),
    "root_receipt_sha256": sha(receipt_path.read_bytes()),
    "source_revision": (RUN / "revision.log").read_text().strip(),
    "source_tree_sha256": receipt["source_tree_sha256"],
    "source_archive_sha256": receipt["source_archive_sha256"],
    "verified_current_and_archived_inputs": len(inputs),
    "verified_command_logs": len(receipt["commands"]),
    "scoped_inputs": {path: inputs[path] for path in required},
    "results": {"host_passed": 261, "host_skipped": 2, "selected_tests_included_in_total": counts},
    "skipped_test_lines": skips,
    "tools": {
        "elixir": (RUN / "elixir-version.log").read_text().strip(),
        "postgres": (RUN / "postgres-version.log").read_text().strip(),
        "database_timezone": "UTC",
    },
    "checks": {
        "current_inputs_match_archive": True,
        "all_command_logs_match": True,
        "asynchronous_oban_processor_exercised": True,
        "production_coordinator_present": True,
        "modeled_provider_helpers_absent_from_release": True,
        "owned_oban_supervisor_stopped": True,
        "dedicated_processor_database_rows_cleared": True,
        **receipt["cleanup"],
    },
    "scope": "Real local PostgreSQL and asynchronous Oban processor with a production Coordinator worker; modeled external adapter operations.",
    "limitations": [
        "Synthetic adapter registries do not qualify provider persistence, authentication, hostile-code isolation, billing or exactly-once external execution.",
        "Loopback PostgreSQL without TLS is not Neon, Cloudflare lifecycle, failover, restore or multi-replica operational evidence.",
        "Public authorization/RLS, real build workers, queue estimates, artifact content publication, signing and GA remain pending.",
        "Two existing Linux-only identity controls are skipped on this Mac; no native or physical-phone evidence is supplied.",
    ],
}
# Preserve the sealed review packet on later read-only rechecks. A fresh review
# directory writes its first evidence check; subsequent runs report to stdout.
if not (BASE / "evidence-check.json").exists():
    (BASE / "evidence-check.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
