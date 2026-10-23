#!/usr/bin/env python3
"""Review only: retain source snapshot, inject original probes, run bounded tests."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "2026-10-23-foundation"
OUT.mkdir(exist_ok=True)
ENV = dict(os.environ, PATH="/opt/homebrew/opt/rustup/bin:" + os.environ["PATH"])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    paths = [ROOT / "vm/Cargo.toml", ROOT / "vm/Cargo.lock"]
    for directory in ("vm/src", "vm/tests"):
        paths.extend(p for p in (ROOT / directory).rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths) if p.exists()}


def output(args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, env=ENV, text=True).strip()


before = manifest()
revision = output(["git", "rev-parse", "HEAD"])
scratch = Path(tempfile.mkdtemp(prefix="mixer-runtime-control-review-"))
snapshot = scratch / "vm"
snapshot.mkdir()
for relative in before:
    destination = scratch / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, destination)
probes = snapshot / "src/experimental_swift_reactor/independent_review.rs"
shutil.copy2(HERE / "probes.rs", probes)
control = snapshot / "src/experimental_swift_reactor/control.rs"
with control.open("a") as target:
    target.write('\n#[cfg(test)]\n#[path = "independent_review.rs"]\nmod independent_review;\n')
snapshot_manifest = {str(p.relative_to(scratch)): digest(p) for p in sorted(snapshot.rglob("*")) if p.is_file()}
archive = OUT / "review-source-snapshot.tar.gz"
with tarfile.open(archive, "w:gz") as target:
    target.add(snapshot, arcname="vm")
target_dir = scratch / "target"
commands = []


def run(label, arguments, expected=0, cwd=snapshot):
    log = OUT / (label + ".log")
    command = ["cargo", arguments[0], "--target-dir", str(target_dir), *arguments[1:]]
    started = time.monotonic()
    with log.open("w") as handle:
        handle.write("$ " + " ".join(command) + "\n")
        handle.flush()
        result = subprocess.run(command, cwd=cwd, env=ENV, stdout=handle, stderr=subprocess.STDOUT)
    item = {"label": label, "command": command, "cwd": str(cwd), "exit_code": result.returncode,
            "expected_exit_code": expected, "passed": result.returncode == expected,
            "elapsed_seconds": time.monotonic() - started, "log": str(log.relative_to(ROOT)), "log_sha256": digest(log)}
    commands.append(item)
    print(json.dumps(item), flush=True)


for mode in ("debug", "release"):
    release = ["--release"] if mode == "release" else []
    run("independent-probes-" + mode, ["test", "--lib", "--all-features", *release, "independent_review", "--", "--test-threads=1"])
    run("narrow-old-routes-" + mode, ["test", "--all-features", *release, "--test", "interpreter", "--test", "span_function_cache", "--test", "span_execution", "--test", "swift_wasi"])
    run("default-interpreter-" + mode, ["test", *release, "--test", "interpreter"])

external = scratch / "external"
(external / "src").mkdir(parents=True)
(external / "Cargo.toml").write_text('[package]\nname="runtime-control-private-probe"\nversion="0.0.0"\nedition="2021"\n[dependencies]\nmixer-vm={path="../vm",features=["experimental-swift-reactor"]}\n')
(external / "src/main.rs").write_text('use mixer_vm::experimental_swift_reactor::control::RuntimeControl;\nfn main() {}\n')
run("private-control-compile-fail", ["check"], expected=101, cwd=external)
private_log = (OUT / "private-control-compile-fail.log").read_text()
private_diagnostic = "module `control` is private" in private_log
after = manifest()
tools = {name: output([name, "--version", "--verbose"] if name == "rustc" else [name, "--version"]) for name in ("rustc", "cargo")}
tool_binaries = {}
for name in ("rustc", "cargo"):
    path = Path(output(["rustup", "which", name]))
    tool_binaries[name] = {"path": str(path), "sha256": digest(path)}
receipt = {
    "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Independent bounded runtime-control foundation review; no full reactor execution or component composition",
    "source_revision": revision, "source_revision_after": output(["git", "rev-parse", "HEAD"]),
    "git_status": output(["git", "status", "--short"]),
    "source_before": before, "source_after": after, "source_stable": before == after,
    "source_manifest_digest": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "snapshot_directory": str(snapshot), "snapshot_manifest": snapshot_manifest,
    "snapshot_archive": str(archive.relative_to(ROOT)), "snapshot_archive_sha256": digest(archive),
    "snapshot_instrumentation": "Append cfg(test) independent_review module to control.rs; all other snapshot inputs exact copies",
    "probe_source_sha256": digest(HERE / "probes.rs"), "collector_sha256": digest(Path(__file__)),
    "tools": tools, "tool_binaries": tool_binaries,
    "platform": output(["uname", "-a"]), "os": output(["sw_vers"]),
    "commands": commands, "private_module_diagnostic_confirmed": private_diagnostic,
    "success": all(item["passed"] for item in commands) and private_diagnostic and before == after,
    "limitations": ["Original synthetic fixed-ABI proof validated only; never instantiated or invoked",
                    "No composed Swift cache/executor/WASI admission or initialization exists in this slice",
                    "Named construction reservation is a conservative model, not compiler stack or RSS evidence",
                    "No physical devices, immutable published consumers, signing, store, production or GA qualification"]
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"receipt": str(OUT / "receipt.json"), "success": receipt["success"]}), flush=True)
