#!/usr/bin/env python3
"""Explicit pinned-artifact validation receipt; never executes target Wasm."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
RUST = Path("/opt/homebrew/opt/rustup/bin")
EXPECTED_SIZE = 53_777_114
EXPECTED_SHA = "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"


def digest(path):
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checks", action="store_true", help="Run immutable focused Debug/Release, proof and lint checks")
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite observed evidence.
    local = output / "local"
    local.mkdir()
    env = dict(os.environ, PATH=f"{RUST}:{os.environ.get('PATH', '')}", RUSTUP_AUTO_INSTALL="0")
    commands = []

    def run(label, command):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        record = {"command": list(map(str, command)), "exitCode": result.returncode}
        for name, data in [("stdout", result.stdout), ("stderr", result.stderr)]:
            file = output / f"{label}.{name}"
            file.write_bytes(data)
            record[name] = {"path": file.name, "sha256": digest(file)}
        commands.append(record)
        return result

    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True)
    # Include embedded non-Rust source assets as well as Rust modules. In
    # particular all-features unit builds use existing include_bytes! JSON.
    files = sorted({p for p in ROOT.glob("vm/src/**/*") if p.is_file()} | {p for p in ROOT.glob("vm/tests/**/*") if p.is_file()}
                   | {ROOT / "vm/Cargo.toml", ROOT / "vm/Cargo.lock", Path(__file__).resolve(),
                      ROOT / "verification/swift-reactor-validation/driver.rs"})
    sources = []
    for source in files:
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT)
        destination = local / "source" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        sources.append({"path": str(relative), "sha256": digest(source)})
    source_digest = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = {
        "schema": 1, "scope": "Complete fixed-policy and exact structural ABI validation only; no cache, instantiation, target execution, publication, device or GA qualification.",
        "observedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [sys.executable, *sys.argv], "pythonVersion": sys.version,
        "revision": revision, "dirtyTree": status, "sourceTreeSHA256": source_digest,
        "sources": sources, "artifact": {"path": str(artifact), "bytes": artifact.stat().st_size, "sha256": digest(artifact)},
        "commands": commands, "valid": False, "executed": False,
        "accountingScope": "Internal reservation totals and separately measured caller input Vec capacity; no allocator overhead or RSS measurement.",
        "skipped": ["runtime execution", "published package dogfood", "physical iOS", "physical Android", "GA review"],
    }
    receipt_path = output / "receipt.json"
    try:
        assert receipt["artifact"]["bytes"] == EXPECTED_SIZE
        assert receipt["artifact"]["sha256"] == EXPECTED_SHA
        for tool in ["rustc", "cargo"]:
            result = run(f"{tool}-version", [str(RUST / tool), "--version"])
            assert result.returncode == 0
            resolved = subprocess.check_output([str(RUST / "rustup"), "which", tool], env=env, text=True).strip()
            receipt[f"{tool}Executable"] = {"path": resolved, "sha256": digest(Path(resolved))}
        run("shasum-version", ["/usr/bin/shasum", "--version"])
        # Build against the immutable source capture, independent of concurrently
        # edited workspace files. Only the two approved features are selected.
        manifest = local / "source/vm/Cargo.toml"
        result = run("build", [str(RUST / "cargo"), "build", "--release", "--manifest-path", str(manifest),
                               "--target-dir", str(local / "target"), "--features", "experimental-swift-reactor", "--lib"])
        assert result.returncode == 0
        binary = local / "qualify"
        result = run("driver-build", [str(RUST / "rustc"), "--edition=2021", "-O",
                                      "--extern", f"mixer_vm={local}/target/release/libmixer_vm.rlib",
                                      str(local / "source/verification/swift-reactor-validation/driver.rs"), "-o", str(binary)])
        assert result.returncode == 0
        receipt["driverSHA256"] = digest(binary)
        result = run("validation", [str(binary), str(artifact)])
        receipt["validation"] = json.loads(result.stdout)
        receipt["valid"] = result.returncode == 0 and receipt["validation"]["valid"]
        if not receipt["valid"]:
            receipt["status"] = "first-failing-ceiling-retained-no-proof"
        elif args.checks:
            base = [str(RUST / "cargo")]
            location = ["--manifest-path", str(manifest), "--target-dir", str(local / "target")]
            targets = ["--all-features", "--lib", "--test", "swift_reactor_validation", "--test", "swift_reactor_validation_allocations"]
            checks = [
                ("focused-debug", base + ["test"] + location + targets + ["--", "--nocapture"]),
                ("focused-release", base + ["test", "--release"] + location + targets + ["--", "--nocapture"]),
                ("proof-authority", base + ["test"] + location + ["--all-features", "--doc"]),
                ("focused-lint", base + ["clippy"] + location + targets + ["--test", "swift_reactor_validation_fixture", "--", "-D", "warnings"]),
            ]
            receipt["focusedChecksPassed"] = True
            for label, command in checks:
                if run(label, command).returncode != 0:
                    receipt["focusedChecksPassed"] = False
                    break
            receipt["status"] = "complete-validation-only" if receipt["focusedChecksPassed"] else "validation-passed-focused-check-failed"
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(receipt_path), "valid": receipt["valid"], "validation": receipt.get("validation")}, indent=2))
    return 0 if receipt["valid"] and receipt.get("focusedChecksPassed", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
