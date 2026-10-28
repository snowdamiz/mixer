#!/usr/bin/env python3
"""Snapshot and run pure controls in-process; never spawn a child command."""
import argparse
import contextlib
import datetime
import hashlib
import json
from pathlib import Path
import re
import runpy
import signal
import sys
import time

sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
args = parser.parse_args()
if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", args.label) is None:
    parser.error("label must be a simple owned snapshot name")
packet_root = Path(__file__).resolve().parent
repository = packet_root.parents[1]
snapshot = packet_root / args.label
snapshot.mkdir(exist_ok=False)
inputs = {}
for name in ("test-identity-network.py", "test_identity_network_collector.py"):
    body = (repository / "hosted/scripts" / name).read_bytes()
    (snapshot / name).write_bytes(body)
    inputs[name] = {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
canonical = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
start = time.monotonic()
code = 0
signal.alarm(50)
with (snapshot / "controls.log").open("w") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
    try:
        sys.argv = [str(snapshot / "test_identity_network_collector.py")]
        runpy.run_path(sys.argv[0], run_name="__main__")
    except SystemExit as result:
        code = result.code or 0
signal.alarm(0)
log_bytes = (snapshot / "controls.log").read_bytes()
count = re.search(rb"Ran (\d+) tests", log_bytes)
receipt = {
    "schema": 1,
    "started_utc": started,
    "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "passed-pure-controls" if code == 0 else "failed-pure-controls",
    "exit_code": code,
    "elapsed_seconds": time.monotonic() - start,
    "hard_bound_seconds": 50,
    "test_methods": int(count.group(1)) if count else None,
    "source_inputs": inputs,
    "source_tree_digest_definition": "SHA256 sorted compact JSON path to bytes/sha256 for the two frozen scripts",
    "source_tree_digest_sha256": hashlib.sha256(canonical(inputs)).hexdigest(),
    "snapshot_runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "command": "python3 -B verification/identity-production-network-controls/run-controls.py --label " + args.label,
    "tool": {"python": sys.version, "version_source": "executing interpreter metadata; no version probe"},
    "scope": "Pure stdlib validators and fake orchestration transcripts with in-memory archives and exclusively owned temporary files. No external command launches or Docker/product/socket/native/compiler/version probes.",
    "prepared_archive_fixture_boundary": "Tiny composition fixtures stub source admission and substitute fixed helper/source/Rebar preimages; independent controls separately exercise frozen177path/lock and official bootstrap roots.",
    "runtime_unqualified": ["actual Docker capabilities/isolation/resources", "image and bootstrap artifact execution", "Linux namespace setup", "two real product test methods", "migration state", "OpenSSL fixture execution", "actual cleanup/retention", "held local lanes", "physical devices", "GA"],
    "log_sha256": hashlib.sha256(log_bytes).hexdigest(),
}
(snapshot / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({key: receipt[key] for key in ("status", "test_methods", "elapsed_seconds", "source_tree_digest_sha256")}, indent=2))
raise SystemExit(code)
