#!/usr/bin/env python3
"""Verify retained collector evidence without starting Elixir, PostgreSQL or a service."""
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "verification/hosted-build-storage/attempt-1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


receipt_bytes = (RUN / "receipt.json").read_bytes()
receipt = json.loads(receipt_bytes)
assert receipt["status"] == "passed"
inputs = receipt["inputs"]
assert len(inputs) == 83
assert sha(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()) == receipt["source_tree_sha256"]
archive_path = RUN / "source.tar.gz"
assert sha(archive_path.read_bytes()) == receipt["source_archive_sha256"]
with tarfile.open(archive_path, "r:gz") as archive:
    archived = {m.name: sha(archive.extractfile(m).read()) for m in archive.getmembers() if m.isfile()}
assert archived == inputs

commands = []
for command in receipt["commands"]:
    assert sha((RUN / command["log"]).read_bytes()) == command["sha256"], command["label"]
    assert command["exit_code"] == command.get("expected_exit_code", 0), command["label"]
    commands.append(command["label"])
assert {"format", "compile", "release-build", "release-missing-config", "tests", "postgres-stop"} <= set(commands)
assert receipt["cleanup"] == {"postgres_stopped": True, "scratch_removed": True}

live_paths = [
    "hosted/lib/mixer_hosted/builds/lifecycle.ex",
    "hosted/lib/mixer_hosted/builds/journal.ex",
    "hosted/lib/mixer_hosted/builds/storage.ex",
    "hosted/lib/mixer_hosted/builds/record.ex",
    "hosted/priv/repo/migrations/20261025000000_add_build_journals.exs",
    "hosted/test/mixer_hosted/builds/storage_test.exs",
    "hosted/test/support/build_intent_worker.ex",
    "hosted/test/foundation_integration_test.exs",
    "hosted/scripts/test-local.py",
    "verification/hosted-build-storage-independent-review/independent_test.exs",
]
live = {name: sha((ROOT / name).read_bytes()) for name in live_paths}
assert all(inputs[name] == digest for name, digest in live.items())

log = (RUN / "tests.log").read_bytes().decode("utf-8")
assert re.search(r"Result: 208 passed, 2 skipped\s*\Z", log)
modules = {}
current = None
skips = []
for line in log.splitlines():
    match = re.match(r"^([A-Za-z0-9_.]+) \[", line)
    if match:
        current = match[1]
    if "(skipped)" in line:
        skips.append({"module": current, "test": line.strip()})
    elif re.search(r"\([0-9.]+ms\) \[L#\d+\]$", line):
        modules[current] = modules.get(current, 0) + 1
assert modules["MixerHosted.BuildStorageReview.Test"] == 9
assert modules["MixerHosted.Builds.StorageTest"] == 15
assert modules["MixerHosted.Builds.JournalTest"] == 14
assert len(skips) == 2
assert {item["module"] for item in skips} == {
    "MixerHosted.Identity.KeyOwnerLinuxNetworkTest",
    "MixerHosted.Identity.StartupLinuxNetworkTest",
}

result = {
    "schema": 1,
    "verdict": "passed_for_internal_development_storage_slice",
    "unresolved_actionable_findings": [],
    "collector_receipt": str((RUN / "receipt.json").relative_to(ROOT)),
    "collector_receipt_sha256": sha(receipt_bytes),
    "source_revision": (RUN / "revision.log").read_text().strip(),
    "source_tree_sha256": receipt["source_tree_sha256"],
    "archived_inputs_verified": len(archived),
    "command_logs_verified": len(commands),
    "live_review_inputs_verified": live,
    "full_suite": {"passed": 208, "skipped": 2},
    "review_controls_passed": 9,
    "producer_storage_tests_passed": 15,
    "journal_tests_passed": 14,
    "skips": skips,
    "execution_owner": "Root collector ran the independent controls together with the full suite; reviewer inspected and rehashed retained evidence without rerunning the DB.",
    "cleanup": receipt["cleanup"],
    "limitations": [
        "Synthetic loopback PostgreSQL uses migration-owner fixture access without TLS; this does not qualify authoritative tenant authorization, FORCE RLS or production runtime role checks.",
        "Job factory is trusted BEAM code and must not perform external effects; changeset normalization is not an application sandbox.",
        "No public build endpoint, authenticated worker gateway, production coordinator, external worker, coordinator lease, global quota, signing, artifact publication or billing execution exists in this slice.",
        "No Neon, Cloudflare wake/failover/restore, real identity provider, Linux-only network rerun, native/device or GA gate is qualified by this receipt.",
        "Real mixer_builds rows plus real Oban rows are covered; the retained collector's inherited synthetic-domain limitation refers to its separate foundation probe.",
    ],
    "verification_command": "python3 verification/hosted-build-storage-independent-review/verify_evidence.py",
}
(OUT / "review.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"verdict": result["verdict"], "archived_inputs_verified": len(archived), "review_controls_passed": 9, "output": str(OUT / "review.json")}))
