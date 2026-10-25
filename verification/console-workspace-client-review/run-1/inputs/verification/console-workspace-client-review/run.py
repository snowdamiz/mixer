#!/usr/bin/env python3
"""Independent allowlisted TypeScript client review; no full console/backend build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = "verification/console-workspace-client-review"
SOURCES = [
    "console/src/api/workspace-client.ts",
    "console/src/domain/workspace-directory.ts",
    "console/tests/workspace-client.test.mjs",
    "console/package.json",
    "console/package-lock.json",
    "console/tsconfig.json",
    "docs/console-workspace-client.md",
    "docs/hosted-customer-workspace-contract.md",
    OWN + "/independent.test.mjs",
    OWN + "/run.py",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    evidence = ROOT / OWN
    attempts = [int(p.name[4:]) for p in evidence.glob("run-*") if p.name[4:].isdigit()]
    output = evidence / f"run-{max(attempts, default=0) + 1}"
    output.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="mixer-client-independent-review-"))
    receipt = {"scope": "Independent source review, selected TypeScript compilation, original 12 client methods and new Node probes; no Phoenix join/App/session/browser/native/deployment/GA qualification", "source_revision_context": args.source_revision, "platform": platform.platform(), "commands": [], "started_unix": time.time(), "scratch": str(scratch), "success": False}
    environment = dict(os.environ, TMPDIR=str(scratch / "node-tmp"))
    (scratch / "node-tmp").mkdir()

    def run(label, argv, cwd, timeout=90):
        process = subprocess.Popen([str(a) for a in argv], cwd=cwd, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            (output / (label + ".stdout")).write_bytes(stdout)
            (output / (label + ".stderr")).write_bytes(stderr)
            raise RuntimeError(label + " timed out; owned process group terminated")
        (output / (label + ".stdout")).write_bytes(stdout)
        (output / (label + ".stderr")).write_bytes(stderr)
        receipt["commands"].append({"label": label, "argv": [str(a) for a in argv], "cwd": str(cwd), "exit_code": process.returncode, "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stderr_sha256": hashlib.sha256(stderr).hexdigest()})
        if process.returncode:
            raise RuntimeError(label + " failed; output preserved")
        return stdout.decode("utf-8")

    try:
        manifest = {}
        for name in SOURCES:
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest[name] = digest(target)
        receipt["inputs"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        run("node-version", ["node", "--version"], scratch)
        run("python-version", ["python3", "--version"], scratch)
        compiler = ROOT / "console/node_modules/typescript"
        package = json.loads((compiler / "package.json").read_text())
        assert package["version"] == "5.9.3"
        compile_command = ["node", compiler / "bin/tsc", "src/api/workspace-client.ts", "--outDir", scratch / "emitted", "--target", "ES2022", "--module", "ESNext", "--moduleResolution", "Bundler", "--strict", "--skipLibCheck", "--noUncheckedIndexedAccess", "--exactOptionalPropertyTypes", "--listFiles"]
        listed = run("compile-selected-client", compile_command, output / "inputs/console")
        dependency_files = [compiler / "package.json", compiler / "bin/tsc", compiler / "lib/_tsc.js", compiler / "lib/typescript.js"]
        for line in listed.splitlines():
            path = Path(line)
            if path.is_relative_to(compiler):
                dependency_files.append(path)
            elif not path.is_relative_to(output / "inputs/console/src"):
                raise RuntimeError("unexpected compiler input: " + line)
        dependencies = {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(dependency_files))}
        (output / "dependency-files.json").write_text(json.dumps(dependencies, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependency-files.json")
        emitted = scratch / "emitted"
        (emitted / "package.json").write_text('{"type":"module"}\n')
        compiled = {str(p.relative_to(emitted)): digest(p) for p in emitted.rglob("*") if p.is_file()}
        (output / "compiled-manifest.json").write_text(json.dumps(compiled, indent=2) + "\n")
        # Original tests compile the same live two TS sources themselves. Source
        # hashes before/after bind that replay, and TMPDIR contains its scratch.
        run("original-client-tests", ["node", "--test", "tests/workspace-client.test.mjs"], ROOT / "console")
        receipt["baseline_scratch_remaining"] = [str(p.relative_to(scratch)) for p in (scratch / "node-tmp").iterdir()]
        if receipt["baseline_scratch_remaining"]:
            raise RuntimeError("baseline retained owned temporary compiler output")
        environment["MIXER_REVIEW_CLIENT_JS"] = str(emitted / "api/workspace-client.js")
        run("independent-node-probes", ["node", output / "inputs" / OWN / "independent.test.mjs"], scratch)
        receipt["success"] = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        receipt["live_source_changes"] = [name for name, expected in receipt.get("inputs", {}).items() if digest(ROOT / name) != expected]
        shutil.rmtree(scratch)
        receipt["scratch_removed"] = not scratch.exists()
        receipt["native_or_capture_started"] = False
        receipt["servers"] = "Synthetic baseline listener and two independent redirect listeners only; tests close all connections/listeners in finally blocks"
        receipt["frozen_backend_lanes_or_shared_main_read_or_run"] = False
        receipt["success"] = bool(receipt["success"] and receipt["scratch_removed"] and not receipt["live_source_changes"])
        receipt["finished_unix"] = time.time()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "success": receipt["success"], "source_tree_sha256": receipt.get("source_tree_sha256"), "failure": receipt.get("failure"), "scratch_removed": receipt["scratch_removed"]}, sort_keys=True))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
