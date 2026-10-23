#!/usr/bin/env python3
"""Original adapter-only build/ABI receipt; never records secure random bytes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "evidence" / "2026-10-23"
SDK = Path("/Users/andreyyurlov/Library/org.swift.swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle/swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1/WASI.sdk")
HEADER = SDK / "include/wasm32-wasip1/wasi/api.h"
ENV = dict(os.environ, PATH="/opt/homebrew/opt/rustup/bin:" + os.environ.get("PATH", ""))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = sorted((ROOT / "vm/src").rglob("*.rs"))
    paths += sorted((ROOT / "vm/tests").glob("swift_wasi*.rs"))
    paths += [ROOT / "vm/Cargo.toml", ROOT / "docs/swift-wasi-adapter-design.md",
              ROOT / "compiler/experiments/fieldlog-reactor/evidence/2026-10-23-qualified/descriptors.json",
              ROOT / "verification/swift-wasi/abi_probe.c", ROOT / "verification/swift-wasi/platform_probe.c",
              Path(__file__).resolve()]
    entries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": digest(p)} for p in paths]
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"sha256": hashlib.sha256(encoded).hexdigest(), "files": entries}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commands = [
        ["git", "rev-parse", "HEAD"], ["git", "status", "--short"],
        ["rustc", "--version", "--verbose"], ["cargo", "--version"], ["cargo", "clippy", "--version"],
        ["python3", "--version"], ["xcrun", "clang", "--version"],
        ["xcrun", "clang", "--target=wasm32-wasip1", "--sysroot=" + str(SDK), "-isystem", str(SDK / "include/wasm32-wasip1"), "-fsyntax-only", "-Wall", "-Werror", "verification/swift-wasi/abi_probe.c"],
        ["xcrun", "clang", "-fsyntax-only", "-Wall", "-Werror", "verification/swift-wasi/platform_probe.c"],
        ["rustfmt", "--edition", "2021", "--check", "vm/src/experimental_wasi/mod.rs", "vm/tests/swift_wasi.rs", "vm/tests/swift_wasi_allocations.rs"],
    ]
    for release in [False, True]:
        base = ["cargo", "test", "--manifest-path", "vm/Cargo.toml", "--features", "experimental-swift-wasi"]
        if release:
            base.append("--release")
        commands += [base + ["--lib", "experimental_wasi", "--", "--nocapture"],
                     base + ["--test", "swift_wasi", "--test", "swift_wasi_allocations", "--", "--nocapture"]]
    commands += [["cargo", "clippy", "--manifest-path", "vm/Cargo.toml", "--features", "experimental-swift-wasi", "--lib", "--test", "swift_wasi", "--test", "swift_wasi_allocations", "--", "-D", "warnings"]]
    receipt = {"scope": "Standalone experimental WASI adapter; no VM admission/routing, full Swift, mobile, GA, publication, or RSS qualification",
               "startedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "sdkHeader": {"path": str(HEADER), "bytes": HEADER.stat().st_size, "sha256": digest(HEADER)},
               "specification": "https://github.com/WebAssembly/WASI/blob/a2b96e81c0586125cc4dc79a5be0b78d9a059925/legacy/preview1/docs.md",
               "sourcesBefore": sources(), "commands": []}
    for number, command in enumerate(commands):
        before = sources()
        completed = subprocess.run(command, cwd=ROOT, env=ENV, text=True, capture_output=True, timeout=180)
        after = sources()
        entry = {"argv": command, "cwd": str(ROOT), "exitCode": completed.returncode,
                 "sourceDigestBefore": before["sha256"], "sourceDigestAfter": after["sha256"],
                 "stdout": completed.stdout, "stderr": completed.stderr}
        receipt["commands"].append(entry)
        (OUT / f"{number:02d}.log").write_text("ARGV: " + json.dumps(command) + "\nEXIT: " + str(completed.returncode) + "\nSTDOUT:\n" + completed.stdout + "\nSTDERR:\n" + completed.stderr)
        (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(f"{number:02d} exit={completed.returncode} " + " ".join(command), flush=True)
        if completed.returncode:
            raise SystemExit("Command failed; exact output retained in receipt")
        if before != after:
            raise SystemExit("Source changed while command ran; receipt does not qualify a stable source tree")
    receipt["sourcesAfter"] = sources()
    receipt["completedUtc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["passed"] = receipt["sourcesBefore"] == receipt["sourcesAfter"]
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not receipt["passed"]:
        raise SystemExit("Source changed across the run")


if __name__ == "__main__":
    main()
