#!/usr/bin/env python3
"""Independent bounded source/receipt check and reviewer-probe runner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
SOURCE = OUT / ".build/source"
ENV = os.environ.copy()
ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV["PATH"]
ENV["CARGO_TARGET_DIR"] = str(OUT / ".build/target")
RECEIPT = {"baseline": json.loads((OUT / "freeze.json").read_text())["baseline"], "scope": "Independent review of nine frozen private prerequisite overlays only; no cache, executor, target execution, devices or publication", "commands": [], "producer_audit": [], "passed": False}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save():
    (OUT / "receipt.json").write_text(json.dumps(RECEIPT, indent=2) + "\n")

def manifest():
    return {str(p.relative_to(SOURCE)): sha(p) for p in sorted(SOURCE.rglob("*")) if p.is_file()}

def command(label, argv, expected=0, cwd=SOURCE):
    before = manifest()
    started = time.monotonic()
    result = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True)
    stdout = OUT / (label + ".stdout")
    stderr = OUT / (label + ".stderr")
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    item = {"label": label, "argv": argv, "cwd": str(cwd), "environment_overrides": {"CARGO_TARGET_DIR": ENV["CARGO_TARGET_DIR"], "PATH": ENV["PATH"]}, "exit": result.returncode, "expected_exit": expected, "seconds": time.monotonic() - started, "stdout": {"path": stdout.name, "sha256": sha(stdout)}, "stderr": {"path": stderr.name, "sha256": sha(stderr)}, "source_stable": manifest() == before}
    RECEIPT["commands"].append(item)
    save()
    print(label, result.returncode, "source_stable", item["source_stable"], flush=True)
    assert result.returncode == expected, f"{label}: see {stderr}"
    assert item["source_stable"]

frozen = json.loads((OUT / "frozen-source-manifest.json").read_text())
assert manifest() == frozen
for relative in ["verification/swift-execution-descriptors/2026-10-23-host-v2/receipt.json", "verification/swift-cache-control-boundary/isolated-2/receipt.json"]:
    path = ROOT / relative
    data = json.loads(path.read_text())
    verified_logs = 0
    for item in data["commands"]:
        if "stdout" in item:
            for stream in ["stdout", "stderr"]:
                assert sha(path.parent / item[stream]["path"]) == item[stream]["sha256"]
                verified_logs += 1
            assert item["passed"]
        else:
            assert sha(ROOT / item["log"]) == item["sha256"]
            assert item["exit"] == 0 and item["source_stable"]
            verified_logs += 1
    overlays = data.get("overlay") or [{"path": p, "sha256": data["source_files"][p]} for p in data["overlays"]]
    for item in overlays:
        assert frozen[item["path"]] == item["sha256"]
    RECEIPT["producer_audit"].append({"path": relative, "sha256": sha(path), "verified_logs": verified_logs, "overlay_match": True, "producer_passed": data["passed"]})
save()

command("rust-version", ["rustc", "-Vv"])
command("cargo-version", ["cargo", "-V"])
command("python-version", ["python3", "--version"])
command("combined-debug-original", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--all-features", "--lib"])
command("combined-release-original", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--release", "--all-features", "--lib"])

for original, probe in [("experimental_swift_reactor/control_tests.rs", "control_probes.rs"), ("experimental_wasi/accounted_tests.rs", "wasi_probes.rs")]:
    target = SOURCE / "vm/src" / original
    shutil.copyfile(OUT / probe, target.parent / ("reviewer_" + probe))
    with target.open("a") as stream:
        stream.write('\ninclude!("reviewer_' + probe + '");\n')
probes = manifest()
(OUT / "probe-source-manifest.json").write_text(json.dumps(probes, indent=2) + "\n")
RECEIPT["probe_source_manifest_sha256"] = sha(OUT / "probe-source-manifest.json")
RECEIPT["probe_only_differences"] = [key for key in probes if frozen.get(key) != probes[key]]
save()
command("reviewer-debug", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--all-features", "--lib", "reviewer_", "--", "--nocapture"])
command("reviewer-release", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--release", "--all-features", "--lib", "reviewer_", "--", "--nocapture"])
command("old-route-regressions", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--all-features", "--test", "span_execution", "--test", "span_execution_allocations", "--test", "span_function_cache", "--test", "span_function_cache_allocations", "--test", "swift_wasi", "--test", "swift_wasi_allocations"])
command("default-unit", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib"])
command("combined-clippy", ["cargo", "clippy", "--locked", "--manifest-path", "vm/Cargo.toml", "--all-features", "--lib", "--bins", "--", "-D", "warnings"])
with tarfile.open(OUT / "probe-source.tar.gz", "w:gz") as archive:
    for path in sorted(SOURCE.rglob("*")):
        if path.is_file():
            archive.add(path, arcname=str(path.relative_to(SOURCE)))
RECEIPT["probe_source_archive_sha256"] = sha(OUT / "probe-source.tar.gz")
RECEIPT["frozen_source_manifest_sha256"] = sha(OUT / "frozen-source-manifest.json")
RECEIPT["collector_sha256"] = sha(Path(__file__))
RECEIPT["passed"] = True
save()
