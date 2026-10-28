#!/usr/bin/env python3
"""Re-run only the offline reviewer, verify retained hashes, and seal its packet."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
repo = root.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def save(name, value):
    (root / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


argv = [sys.executable, str(root / "review.py")]
started = datetime.datetime.now(datetime.timezone.utc)
result = subprocess.run(argv, cwd=repo, capture_output=True, timeout=45)
(root / "review.stdout").write_bytes(result.stdout)
(root / "review.stderr").write_bytes(result.stderr)
save("review.command.json", {
    "argv": argv, "cwd": str(repo), "timeout_seconds": 45,
    "started_at": started.isoformat(),
    "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "exit_code": result.returncode, "python_version": sys.version,
    "script_sha256": sha(root / "review.py"),
    "stdout_sha256": sha(root / "review.stdout"),
    "stderr_sha256": sha(root / "review.stderr"),
    "scope": "Offline evidence review; child git commands read exact committed objects only (15s each).",
})
assert result.returncode == 0
review = load(root / "review.json")
run = load(root / "run-metadata.json")
acquisition = load(root / "acquisition.json")
manifest = load(root / "zip-manifest.json")
assert run["status"] == "completed" and run["conclusion"] == "cancelled"
assert run["head_sha"] == review["source_revision"]
assert sha(root / "artifact.zip") == acquisition["sha256"] == manifest["zip_sha256"]
assert (root / "artifact.zip").stat().st_size == 1470518 < acquisition["zip_cap_bytes"]
assert manifest["uncompressed_bytes"] <= acquisition["expanded_cap_bytes"]
for entry in manifest["entries"]:
    path = root / "extracted" / entry["path"]
    assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"]
assert all(row["all_match_exact_commit"] for row in review["source_bindings"].values())
assert review["source_bindings"]["storage"]["manifest_receipt_hash_matches"]
assert review["source_bindings"]["storage"]["before_after_manifests_identical"]
assert review["source_bindings"]["migration"]["retained_inputs_all_match_manifest"]
assert review["source_bindings"]["protocol"]["receipt_tree_matches_inputs_tree"]
logs = review["log_bindings"]
assert not logs["migration"]["command_log_hash_mismatches"]
assert not logs["migration"]["receipt_output_hash_mismatches"]
assert logs["protocol"]["all_referenced_output_files_preserved"]
assert all(logs[label]["all_recorded_exit_codes_zero"] for label in ["protocol", "storage", "migration"])
assert review["historical_contamination"]["count"] == 9
frontier = review["foundation_runtime_frontier"]
assert not frontier["foundation_receipt_present"]
assert not frontier["postgres_stop_log_present"]
assert not frontier["finished_summary_present"]
assert not frontier["collector_timeout_marker_present"]
assert "K08b eight configured profiles" in frontier["last_entered_trace"]["message"]
report = f"""Phoenix run 40723227254 / job 122939477520 remains cancelled at commit
{review['source_revision']} (Git tree {review['source_tree']}).
This packet reviews retained evidence only; it provides no new runtime acceptance.

- Retained artifact 12831598909: 1,470,518 bytes; SHA-256
  23c747645e5b6523411710454d3edfcf149a0987440d5522ca692c1690c50b0a.
  All 273 ZIP entries (3,392,338 expanded bytes) were validated for relative paths,
  no traversal/backslash/duplicate/symlink/encryption, expansion cap and CRC, then
  safely extracted. The nested source archive was independently validated under
  the 64 MiB cap; its 181 files (4,578,681 bytes) all match exact committed blobs.
- Current protocol: 45 passed, no failed/skipped/excluded tests; current storage:
  24 passed; current migration: 1 test, 0 failures/skipped/excluded. Source maps
  of 14, 13 and 23 files respectively match exact committed blobs. Migration
  receipt output hashes (31 files) and command log hashes match retained bytes.
- Last foundation trace: tests.log line 1323 enters KeyOwnerTest K08b,
  “eight configured profiles cannot open a fifth owned flight.” The last completed
  trace is K08 (324.1 ms), line 1322. There is no K08b completion, suite summary,
  source-unchanged result, final foundation receipt, or postgres-stop log. This
  does not prove that K08b failed, hung, or caused cancellation.
- Checkout spans 16:09:54.019536Z to the next action at 16:21:17.898163Z:
  683.878627 seconds (upper bound). Fetch occupied 616.349470 seconds;
  writing 338,637 files occupied 66.461304 seconds. The committed workflow has
  a 15-minute job limit. The foundation step began at 16:22:23.634724Z and was
  cancelled at 16:25:05.864019Z, after 162.229295 seconds. No collector 300-second
  timeout marker exists. Timing supports possible job-budget exhaustion; the
  cause is not explicit and the recorded conclusion remains cancelled.
- Protocol scratch cleanup, storage PostgreSQL/scratch cleanup, and migration
  PostgreSQL/scratch/compile-product cleanup are recorded true in their own
  current receipts. Foundation cleanup is unproven. Runner log lines 564–569
  report orphan termination for Python, PostgreSQL, BEAM, erl_child_setup and
  two inet_gethost processes; those are termination attempts without retained
  post-termination absence evidence. Per-case lifecycle observations apply only
  to their named resources and do not prove whole-collector cleanup.
- Nine historical receipts (2 protocol, 7 storage from October 25) arrived via
  broad recursive upload of tracked attempt directories. They are explicitly
  excluded from the current runtime verdict.

Reproduce only the offline review with `python3 {root / 'review.py'}`.
The recorded command, Python/Git versions, output hashes, exact source bindings,
timing markers, log bindings and limitations are in review.command.json,
source-bindings.json, timing.json, log-bindings.json and review.json.
No rerun/dispatch, product runtime, Docker/PostgreSQL/native/UI/capture/process
inventory or writes outside this packet occurred. No Git/index/metadata/memory
changes were made. No GA or customer acceptance is established.

Acquisition incident: the first connector result was accidentally emitted to the
tool transcript, exposing its temporary signed file-reference URL. The URL was
not persisted in this packet; subsequent acquisition output was sanitized.
"""
(root / "report.md").write_text(report)
entries = []
for path in sorted(root.rglob("*")):
    if path.is_file() and path not in {root / "packet-manifest.json", root / "receipt.json"}:
        entries.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha(path)})
save("packet-manifest.json", {"entries": entries, "scope": "Every retained packet file except this manifest and its binding receipt."})
save("receipt.json", {
    "status": "sealed_offline_review_current_run_cancelled",
    "sealed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": review["source_revision"], "source_tree": review["source_tree"],
    "command": "python3 verification/github-delivery-identity-network/phoenix-cancelled-review/seal.py",
    "python_version": sys.version, "seal_script_sha256": sha(root / "seal.py"),
    "review_script_sha256": sha(root / "review.py"),
    "manifest_sha256": sha(root / "packet-manifest.json"), "files_in_manifest": len(entries),
    "assertions": "Verified ZIP/extracted bytes, exact committed source maps, migration log/output hashes, existing successful preceding receipts, historical exclusions, absent final foundation completion and cleanup receipts; cancellation is preserved.",
    "native_product_runtime_or_ci_started": False,
})
print(json.dumps({"status": "sealed_offline_review_current_run_cancelled", "files_in_manifest": len(entries), "manifest_sha256": sha(root / "packet-manifest.json")}, indent=2))
