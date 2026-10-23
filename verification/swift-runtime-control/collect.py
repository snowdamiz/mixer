#!/usr/bin/env python3
"""Collect reproducible source-bound foundation evidence; never execute a reactor."""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "2026-10-23-foundation"
ENV = dict(os.environ)
ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV.get("PATH", "")
OUT.mkdir(exist_ok=True)


def digest(path: Path) -> dict:
    contents = path.read_bytes()
    return {"path": str(path), "bytes": len(contents), "sha256": hashlib.sha256(contents).hexdigest()}


def run(label: str, argv: list[str]) -> dict:
    completed = subprocess.run(argv, cwd=ROOT, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout = OUT / (label + ".stdout")
    stderr = OUT / (label + ".stderr")
    stdout.write_bytes(completed.stdout)
    stderr.write_bytes(completed.stderr)
    executable = shutil.which(argv[0], path=ENV["PATH"])
    entry = {
        "label": label,
        "argv": argv,
        "cwd": str(ROOT),
        "exit_code": completed.returncode,
        "executable": digest(Path(executable).resolve()) if executable else None,
        "stdout": digest(stdout),
        "stderr": digest(stderr),
    }
    print(f"{label}: exit={completed.returncode}", flush=True)
    return entry


def source_manifest() -> list[dict]:
    discovered = subprocess.check_output(["rg", "--files", "vm/src", "vm/tests"], cwd=ROOT, env=ENV).decode().splitlines()
    paths = {path for path in discovered if path.endswith(".rs")}
    paths.update([
        "AGENTS.md", "vm/Cargo.toml", "vm/Cargo.lock",
        "docs/swift-reactor-execution-stage-design.md",
        "verification/swift-reactor-execution-contract-acceptance.json",
        "verification/swift-reactor-execution-design-review/review.md",
        "verification/swift-runtime-control/collect.py",
    ])
    return [dict(digest(ROOT / path), path=path) for path in sorted(paths) if (ROOT / path).is_file()]


revision_before = run("revision-before", ["git", "rev-parse", "HEAD"])
dirty_before = run("dirty-before", ["git", "status", "--short"])
before = source_manifest()
(OUT / "source-before.json").write_text(json.dumps(before, indent=2) + "\n")
commands = [revision_before, dirty_before]
for label, argv in [
    ("rustc-version", ["rustc", "--version", "--verbose"]),
    ("cargo-version", ["cargo", "--version"]),
    ("rustfmt-version", ["rustfmt", "--version"]),
    ("clippy-version", ["cargo", "clippy", "--version"]),
    ("python-version", [sys.executable, "--version"]),
    ("host", ["uname", "-a"]),
    ("format", ["rustfmt", "--edition", "2021", "--check", "vm/src/experimental_swift_reactor/control.rs", "vm/src/experimental_swift_reactor/control_tests.rs"]),
    ("swift-debug", ["cargo", "test", "--manifest-path", "vm/Cargo.toml", "--features", "experimental-swift-reactor", "--lib", "experimental_swift_reactor", "--", "--nocapture"]),
    ("swift-release", ["cargo", "test", "--manifest-path", "vm/Cargo.toml", "--release", "--features", "experimental-swift-reactor", "--lib", "experimental_swift_reactor", "--", "--nocapture"]),
    ("all-feature-lib-debug", ["cargo", "test", "--manifest-path", "vm/Cargo.toml", "--all-features", "--lib", "--", "--nocapture"]),
    ("all-feature-lib-release", ["cargo", "test", "--manifest-path", "vm/Cargo.toml", "--release", "--all-features", "--lib", "--", "--nocapture"]),
    ("clippy-all-feature-lib", ["cargo", "clippy", "--manifest-path", "vm/Cargo.toml", "--all-features", "--lib", "--", "-D", "warnings"]),
    ("clippy-swift-lib-tests", ["cargo", "clippy", "--manifest-path", "vm/Cargo.toml", "--features", "experimental-swift-reactor", "--lib", "--tests", "--", "-D", "warnings"]),
]:
    commands.append(run(label, argv))

sysroot = Path(subprocess.check_output(["rustc", "--print", "sysroot"], cwd=ROOT, env=ENV).decode().strip())
toolchain_files = [digest(sysroot / "bin" / binary) for binary in ["rustc", "cargo", "rustfmt", "clippy-driver"] if (sysroot / "bin" / binary).is_file()]
official_arc_source = sysroot / "share/doc/rust/html/src/alloc/sync.rs.html"
arc_provenance = digest(official_arc_source) if official_arc_source.is_file() else None
revision_after = run("revision-after", ["git", "rev-parse", "HEAD"])
commands.append(revision_after)
after = source_manifest()
(OUT / "source-after.json").write_text(json.dumps(after, indent=2) + "\n")
stable = before == after
revision_stable = (OUT / "revision-before.stdout").read_bytes() == (OUT / "revision-after.stdout").read_bytes()
success = stable and revision_stable and all(command["exit_code"] == 0 for command in commands)
receipt = {
    "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Private Swift runtime-control foundation only; ordinary exact-ABI synthetic proof validation, no reactor execution.",
    "success": success,
    "source_stable": stable,
    "revision_stable": revision_stable,
    "source_manifest": digest(OUT / "source-before.json"),
    "source_tree_sha256": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "commands": commands,
    "toolchain_files": toolchain_files,
    "official_arc_layout_source": arc_provenance,
    "verified_scope": [
        "Consumed genuine ordinary-validator exact-ABI proofs, with no alternate proof constructor or fixture policy.",
        "All seventeen independent narrowing/zero dimensions; all five adoption admission boundaries; actual proof/control closure cleanup.",
        "Atomic category/combined debits and checked arithmetic; missing, foreign and underflow ticket charges retained conservatively.",
        "At most86 inline nonClone ticket ownership values; no growing production ticket registry and no per-pin tickets.",
        "Single construction reservation expands before additional phase storage and contracts after its actual storage drop.",
        "Cumulative synthetic initialization/two-call counter sequence, live-count cleanup, real cancellation and carried earliest deadlines.",
        "Sticky first terminal snapshots, separate cleanup invariants and cleanup snapshots; no-allocation diagnostics and cleanup.",
        "Cancellation requested backing layout agrees with native allocator observation on this target/toolchain; clone requests no additional backing.",
        "All-feature library unit regressions in Debug and Release; focused formatting, all-feature library lint and Swift-feature library/tests lint.",
    ],
    "limitations": [
        "This proves the adopted foundation closure and its named transfer/header/scratch reservation model only.",
        "Generic private drop_reserved callers must pass all actual storage covered by a ticket; later composition requires independent ownership tests.",
        "No actual Swift cache, decode, executor, initialization, memory.grow or WASI context dispatch integration exists in this slice.",
        "Synthetic partial allocation/capacity faults and reservation overlap are foundation tests, not allocator-fault evidence for future component constructors.",
        "Control admission failures have wasi=None because no WASI context exists here; None is not zero and exact context observations remain a composition obligation.",
        "Observed unit allocator intervals count synchronous requests/frees, not a general live-pointer ledger.",
        "Named object capacity/layout reservations exclude allocator overhead and make no RSS, compiler-stack or hard-realtime claim.",
        "The full retained reactor was not instantiated, initialized or invoked; target execution still requires separate root approval.",
        "Full external frozen-route integration/compile checks remain root-owned follow-up; library regressions are explicitly scoped.",
        "The preserved attempt-1 broad all-feature integration lint failed on unchanged guest-UI test lints outside this foundation; this does not mark that broader lint as passing.",
        "No physical device, immutable published FieldLog consumer, production, signing, store, customer, operational or GA qualification.",
    ],
    "reactor_executed": False,
    "component_integration": False,
    "physical_device_operations": [],
    "commits_or_pushes": [],
    "root_acceptance": False,
    "prior_attempts": [
        "verification/swift-runtime-control/2026-10-23-foundation-attempt-1/receipt.json",
        "verification/swift-runtime-control/2026-10-23-foundation-attempt-2/receipt.json",
    ],
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"success": success, "source_stable": stable, "receipt": str(OUT / "receipt.json")}))
sys.exit(0 if success else 1)
