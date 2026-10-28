#!/usr/bin/env python3
"""Finalize independent source acceptance; read-only inputs, owned output only."""
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def binding(path):
    value = path.read_bytes()
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}

def write(name, value):
    (BASE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

def packet(name, count, expected):
    base = ROOT / "verification" / name
    manifest = json.loads((base / "packet-manifest.json").read_bytes())
    files = manifest["files"]
    assert len(files) == count and canonical(files) == expected == manifest["tree_digest_sha256"]
    for path, row in files.items():
        assert str(Path(path)) == path and not Path(path).is_absolute() and ".." not in Path(path).parts
        assert binding(base / path) == row, path
    actual = {str(path.relative_to(base)) for path in base.rglob("*") if path.is_file()}
    assert actual == set(files) | {"packet-manifest.json"}, name
    return {"path": str(base.relative_to(ROOT)), "files": count, "tree_digest_sha256": expected, "packet_manifest": binding(base / "packet-manifest.json"), "all_files_independently_rehashed": True}

signal.alarm(30)
checks = json.loads((BASE / "checks.json").read_bytes())
for name, row in checks["source"].items():
    assert binding(ROOT / name) == row == binding(BASE / "source" / name), name
assert checks["source_root"] == canonical(checks["source"])
assert checks["results"]["producer"] == {"tests": 111, "errors": 0, "failures": 0, "skips": 0, "passed": True}
assert checks["results"]["independent"] == {"tests": 12, "errors": 0, "failures": 0, "skips": 0, "passed": True}
references = {
    "author": packet("identity-network-binary-export-correction", 33, "f2127ba412ff6e15f7c35e1473656a301dfe4d9c28a14a20411c638f15e1ccec"),
    "prior_runtime": packet("github-delivery-runtime-followup/network-review", 256, "69832104e969c2746dc99edda71c86961b84c05c1576da1368b19a72fa2e3bb1"),
}
write("referenced-seals.json", references)
decision = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "reviewer": {"model": "gpt-6-astra", "reasoning_effort": "xhigh", "role": "fresh independent focused source acceptance"},
    "verdict": "accepted-source-and-pure-controls-for-fresh-actual-network-CI",
    "scope": "checked byte-transparent file export and fixed public bootstrap retention before completed-export host length/SHA512 rejection",
    "source_revision": "fb7c7f20f8a308424ef4b7092d19d3d4de2c7627",
    "source_git_tree": "509093e0fcc9f4c83583f8d0ecd61b8b3c9d83d4",
    "canonical_sources": checks["source"],
    "canonical_source_root": checks["source_root"],
    "references": references,
    "verification": {"producer_controls": 111, "fresh_independent_methods": 12, "total_pure_methods": 123, "failures": 0, "errors": 0, "skips": 0, "prior_test_bodies_preserved": 103, "separate_inert_residual_probe": "exception-probe.json", "exact_pinned_hex_tested_as_inert_bytes": True, "all256_values_present_in_pinned_hex": True},
    "findings": [],
    "nonblocking_residual": "Inherited command() can lose already-buffered stdout if process.wait raises after EOF and before binary_path persistence. In-process fake confirms failed/false completion flags and absent capture/receipt, never a pass. Root explicitly retains this limitation without widening the collector; selected completed-export host size/SHA512 refusals retain exact public bytes.",
    "accepted_properties": ["checked latin1 setopts precedes checked binwrite for every shared export caller", "original paths, timeout, limits, images, environment, helpers, capabilities and mount partitions retained", "new pure bootstrap validation requires exact observed downloaded size and unchanged selected SHA512", "only exact public Hex/Rebar paths gain bounded permanent raw capture", "host size/hash rejection leaves bytes and joined command facts retained", "bounded overflow/nonzero captures remain failed and incomplete", "no new secret/private retention or capture overwrite", "other permitted exports retain existing scratch handling", "all non-selected collector definitions and constants unchanged"],
    "protected_live_sources": {name: binding(ROOT / name) for name in (".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/store.ex", ".github/workflows/identity-network.yml")},
    "commands": [
        {"argv": ["python3", "-B", "verification/identity-network-binary-export-independent/review.py"], "alarm_seconds": 50, "exit_code": 0, "observed_tool_wall_seconds": 0.806717333, "outputs": ["checks.json", "producer.log", "independent.log"]},
        {"argv": ["python3", "-B", "verification/identity-network-binary-export-independent/probe_exception.py"], "alarm_seconds": 15, "exit_code": 0, "output": "exception-probe.json", "actual_external_processes_started": 0},
        {"argv": ["python3", "-B", "verification/identity-network-binary-export-independent/seal.py"], "alarm_seconds": 30, "scope": "local read-only seal verification and owned decision/manifest writes"},
    ],
    "tools": {"python": checks["python"], "git": "git version 2.56.0"},
    "unlocks": "Root delivery and one fresh actual .github/workflows/identity-network.yml attempt of the same frozen workload, followed by independent artifact review",
    "runtime_acceptance": False,
    "product_methods_run": 0,
    "pending": ["corrected actual Hex and Rebar export/hash acceptance", "locked dependencies", "prepared archive transfer/restore", "test/PG creation", "offline compilation", "two unchanged production DNS/TLS methods", "fresh attempt isolation/cleanup and artifact acceptance", "all native/process/custody/provider/customer/release/GA holds"],
    "side_effects": {"canonical_edits": False, "commit_push_dispatch": False, "metadata_status_gate_edits": False, "network_downloads": False, "local_Elixir_Docker_compiler_PG_guest_native_UI_capture": False, "private_FieldLog_sources_read": False, "PID_or_global_process_inventory": False, "old_held_processes_touched": False},
    "cleanup": "Only owned TemporaryDirectories under this review were created; removed. No owned or other-project runtime instance was started or changed.",
}
assert not (BASE / ".scratch").exists()
write("decision.json", decision)
(BASE / "README.md").write_text("""# Independent binary export source acceptance

Accepted for root delivery and a fresh actual identity-network CI attempt.
All 111 producer controls and 12 fresh independent methods pass, with no
failures, errors or skips. These are guarded pure Python controls with inert
transcript transport; no Elixir, Docker, compiler, PG, native or UI runtime ran.
The canonical three-file root is
`0cf7245c95092ec8efb714116660a38bab7b2f22ec8d95384d0be1abe6194bad`.

The shared Elixir literal checks standard IO Latin-1 encoding before checked
binary output. Exact public Hex/Rebar bytes survive completed-export host
length or SHA512 rejection; only those two paths gain permanent captures.
Bounds, selected hashes, other callers and scratch handling remain intact.
The pinned Hex archive contains all 256 byte values; independent inert
transport and validation preserve its exact body. Its historical Latin-1 to
UTF-8 transform reproduces the original observed wrong length and SHA256.
The original failed raw export is unavailable; this remains supporting
source/hash evidence, not a reconstruction of the missing observation.

The author packet's 33 files and prior runtime review's 256 files were each
independently rehashed. The prior execution reached no product methods.
`decision.json` records all exact source hashes, references and commands.
The full 103 previous test method bodies and all non-selected collector
definitions/constants remain identical.

One inherited transport-exception limitation is explicit and nonblocking:
after streams reach EOF, process.wait may raise before command() persists
its buffer. A separate in-process fake confirms that such a path can have
no retained raw capture. It remains failed with false completion flags and
no capture receipt; it grants no pass. Root selected retaining that limitation
without widening command(), since this correction's retention scope is before
completed-export host length/SHA rejection. See `exception-probe.json`.

Actual corrected exports, dependency resolution, archive transfer/restore,
compilation, the two network methods, isolation and cleanup remain pending
the fresh CI execution and independent artifact review. All native, process,
custody, provider, customer, release and GA holds remain active. This review
changed only this directory and cleaned its own temporary directories.
""")
files = {str(path.relative_to(BASE)): binding(path) for path in sorted(BASE.rglob("*")) if path.is_file() and path.name != "packet-manifest.json"}
write("packet-manifest.json", {"schema": 1, "files": files, "tree_digest_sha256": canonical(files), "scope": "independent source acceptance only; actual network runtime pending"})
print(json.dumps({"files": len(files), "tree_digest_sha256": canonical(files), "decision_sha256": binding(BASE / "decision.json")["sha256"], "manifest_sha256": binding(BASE / "packet-manifest.json")["sha256"]}, sort_keys=True))
