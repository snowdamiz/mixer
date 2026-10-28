#!/usr/bin/env python3
"""Seal only the owned read-only CI review packet."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name):
    return json.loads((ROOT / name).read_text())


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


argv = [sys.executable, str(ROOT / "review.py")]
started = datetime.datetime.now(datetime.timezone.utc)
result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=45)
(ROOT / "review.stdout").write_bytes(result.stdout)
(ROOT / "review.stderr").write_bytes(result.stderr)
save("review.command.json", {
    "argv": argv, "cwd": str(REPO), "timeout_seconds": 45,
    "started_at": started.isoformat(),
    "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "exit_code": result.returncode, "python_version": sys.version,
    "script_sha256": sha(ROOT / "review.py"),
    "stdout_sha256": sha(ROOT / "review.stdout"), "stderr_sha256": sha(ROOT / "review.stderr"),
    "scope": "Offline metadata, archive, source and log validation only; no product/native/CI execution.",
})
assert result.returncode == 0
review = load("review.json")
source = load("source-bindings.json")
runtime = load("runtime-evidence.json")
sparse = load("sparse-readset.json")
archive = load("source-archive-manifest.json")
assert review["status"] == "verified_exact_commit_ordinary_phoenix_host_ci_success"
assert review["artifact_expanded_bytes"] + archive["expanded_bytes"] <= 64 * 1024 * 1024
assert not review["historical_receipts_present"]
assert len(runtime["lifecycle_completed_methods"]) == 9
assert len(runtime["http2_completed_methods"]) == 5 and len(runtime["http2_wire_cases"]) == 7
assert len(runtime["K07_f_g_h_completed"]) == 3 and len(runtime["skipped_methods"]) == 2
assert sparse["required_readset_exactly_covered"] and sparse["selected_files"] == 194
report = f"""Independently verified ordinary Phoenix host CI success for run 40730443899,
job 122964997776, commit {review['source_revision']}
(Git tree {review['source_tree']}). All 13 recorded job steps succeeded.

- Retained artifact 12834743027: 856,990 bytes, SHA-256
  4a625faba2e0a1f523d428bd8bb0a493b7c80c1ded434c7147be5b09fde63f43.
  All 150 ZIP entries (1,531,671 expanded bytes) pass traversal/link/duplicate/
  encryption/CRC and byte-cap validation. Nested source archive contains all
  181 receipt inputs; its hashes and each exact committed blob match. Combined
  expansion is {review['artifact_expanded_bytes'] + archive['expanded_bytes']:,} bytes,
  below the 64 MiB cap. No signed download URL was echoed or persisted.
- Foundation: 697 passed, 2 skipped, zero reported failures; ExUnit reports
  131.6 seconds. Exact source maps match for foundation (181), protocol (14),
  storage (13) and migration (23). The preceding receipts report protocol
  45 passed, storage 24 passed, migration 1 passed. Every foundation command log,
  migration command log and migration receipt output hash matches retained bytes.
  The expected release-missing-config command exits 1 and rejects missing
  MIXER_HOSTED_ROLE; other foundation commands exit 0.
- All nine KeyOwner lifecycle methods complete, including KOL08-GRACEFUL and
  KOL09-KILL. K07f/g/h also complete. Named fixture observations show four slots
  until connection cleanup, five accepted/five closed handshake connections,
  and old controllers/workers/raw ports down before crash restart. Lifecycle
  observation fields retain branch-specific false values; the packet does not
  generalize every field into a universal property.
- Five HTTP/2 test methods produce seven passed wire cases (B1, B2, B3, D1
  SETTINGS/WINDOW_UPDATE, D2 SETTINGS/WINDOW_UPDATE). Each wire receipt records
  complete cleanup. The packaged production release passes fixture export/init,
  raw-capture, transport helper-atom and modeled build-worker exclusion checks;
  transport role/listener remain inactive during that inspection.
- Exact committed workflow equals the root-selected candidate and differs from
  its parent only by 19 added checkout-input lines. Its 16 non-cone patterns
  cover exactly the 194-file required ordinary readset ({sparse['selected_logical_bytes']:,}
  logical source bytes): complete hosted inputs, manifest/protocol/storage files,
  TypeScript client imports/packages, Node driver, and both golden files. The
  runner logs blob:none fetch, sparse checkout activation and the exact commit.
  Upload inventory contains exactly four current receipts and no historical
  copied attempt receipts. This is static readset coverage plus successful
  runtime consumers, not a complete runner filesystem inventory.
- Observed checkout interval: 16:53:53.928170Z to next action
  16:53:57.344930Z, 3.416760 seconds (upper bound); fetch 0.863347 seconds;
  ref checkout to branch switch 1.926994 seconds. Foundation step to emitted
  passing receipt: 174.972721 seconds. The configured job limit remains 15
  minutes. These are this runner's measurements, with no future timing,
  transfer-byte, cost or latency guarantee.
- Foundation records PostgreSQL stopped and owned scratch removed. Protocol,
  storage and migration receipts record their own cleanup; all nine lifecycle
  observations and seven HTTP/2 receipts record named resource cleanup. Runner
  logs its orphan-cleanup phase without any orphan termination event. This
  proves only the recorded fixture resource scope, not universal process absence.

The two skipped tests remain pending: K03 production resolver/classifier public
peer pinning under rebinding, and IS04/IS05 configured startup public-DNS/TLS
admission/lifecycle. No configured-provider, Neon, Cloudflare, deployed operation,
native/physical device, customer, store or GA acceptance is established.

This review applies only to the exact ordinary committed workflow. It does not
accept held UnitA/frozen source or its separate workflow/readset. The live dirty
workflow was not read, staged or changed. No product/local database/container/
native/UI/capture/process inventory, CI rerun/dispatch, canonical/Git/index/
metadata/memory mutation or write outside this packet occurred.

Reproduce the offline review with `python3 {ROOT / 'review.py'}`. Recorded command,
Python/Git versions, hashes, readset, timing, source/log bindings, exact method/
wire-case evidence, skipped tests and limits accompany this report.
"""
(ROOT / "report.md").write_text(report)
for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix not in {".zip", ".gz"}:
        data = path.read_bytes()
        assert not re.search(rb"https://[A-Za-z0-9.-]+\.oaiusercontent\.com/", data)
        assert not re.search(rb"[?&]X-Amz-Signature=", data)
files = []
for path in sorted(ROOT.rglob("*")):
    if path.is_file() and path not in {ROOT / "packet-manifest.json", ROOT / "receipt.json"}:
        files.append({"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha(path)})
save("packet-manifest.json", {"entries": files, "scope": "Every retained file except this manifest and its binding receipt, including all extracted receipts."})
save("receipt.json", {
    "schema": 1, "status": "sealed_verified_exact_commit_ordinary_phoenix_host_ci_success",
    "sealed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": review["source_revision"], "source_tree": review["source_tree"],
    "run_id": review["run_id"], "job_id": review["job_id"], "artifact_id": review["artifact_id"],
    "command": "python3 verification/github-delivery-identity-network-transfer/phoenix-review/seal.py",
    "python_version": sys.version, "git_version": source["git_version"],
    "connector_tool_versions": "Not exposed by connector; names recorded in acquisition.json.",
    "seal_script_sha256": sha(ROOT / "seal.py"), "review_script_sha256": sha(ROOT / "review.py"),
    "manifest_sha256": sha(ROOT / "packet-manifest.json"), "files_in_manifest": len(files),
    "held_UnitA_or_live_dirty_workflow_accepted": False,
    "native_product_runtime_or_ci_started": False,
    "signed_download_url_echoed_or_persisted": False,
    "scope": "Exact ordinary hosted Ubuntu CI evidence, with two explicit skips and scoped cleanup. No deployment/native/customer/GA qualification.",
})
print(json.dumps({"status": "sealed_verified_exact_commit_ordinary_phoenix_host_ci_success",
                  "files_in_manifest": len(files), "manifest_sha256": sha(ROOT / "packet-manifest.json")}, indent=2))
