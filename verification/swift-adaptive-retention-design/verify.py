#!/usr/bin/env python3
"""Run and retain only this bounded policy model; no Git or product mutation."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = [
    "vm/src/experimental/cache/mod.rs",
    "vm/src/experimental/cache/borrowed.rs",
    "vm/src/experimental_swift_reactor/cache.rs",
    "verification/swift-cost-retention-candidate/common-tests.rs",
    "docs/swift-retention-runtime.md",
    "docs/swift-cost-retention-candidate.md",
]


def manifest():
    return [{"path": p, "bytes": (ROOT / p).stat().st_size,
             "sha256": hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in INPUTS]


def write(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def main():
    before = manifest()
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    argv = [sys.executable, str(HERE / "model.py")]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    (HERE / "stdout.json").write_text(result.stdout)
    (HERE / "stderr.txt").write_text(result.stderr)
    after = manifest()
    write("source-manifest.json", before)
    write("receipt.json", {
        "command": argv,
        "cwd": str(ROOT),
        "started_utc": started,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "python_version": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "exit_code": result.returncode,
        "consulted_inputs_unchanged": before == after,
        "source_revision": {"parent_provided_prefix": "d385adf3", "git_not_invoked": True},
        "source_closure": {"parent_provided_132_file_digest": "16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd", "full_closure_not_recomputed_by_this_lane": True},
        "observed_scope": "Seven finite policy access sequences, including the same six prior traces; 17 model invariant controls. No VM/native/device/full-target/compiler/qualification run.",
        "selection": "Unselected; root explicitly withheld candidate implementation selection.",
    })
    assert result.returncode == 0 and before == after
    output = json.loads(result.stdout)
    assert output["checks_passed"] == 17 and len(output["traces"]) == 7
    write("seal.json", {"members": [
        {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
         "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted([ROOT / "docs/swift-adaptive-retention-design.md", *[p for p in HERE.iterdir() if p.is_file() and p.name != "seal.json"]])
    ]})
    print(json.dumps({"exit_code": result.returncode, "checks_passed": output["checks_passed"],
                      "trace_count": len(output["traces"]), "consulted_inputs_unchanged": before == after,
                      "selection": "unselected"}, sort_keys=True))


if __name__ == "__main__":
    main()
