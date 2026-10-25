#!/usr/bin/env python3
"""Seal the final owned controller slice; never invokes project/provider code."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PROJECT = ROOT / "hosted-worker-controller"

def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()

def record(path, base=ROOT):
    return {"path": str(path.relative_to(base)), "bytes": path.stat().st_size,
            "sha256": sha(path), "mode": oct(path.stat().st_mode & 0o777)}

def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")

def command(argv):
    result = subprocess.run(argv, cwd=PROJECT, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"tool command failed: {argv}")
    return {"argv": argv, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

def main():
    tools = [command(["node", "--version"]), command(["npm", "--version"]),
             command(["node", "node_modules/typescript/bin/tsc", "--version"]),
             command(["elixir", "--version"]), command(["sw_vers"])]
    binary_info = command(["node", "-e", "const w=require('workerd');console.log(JSON.stringify({path:w.default,version:w.version,compatibilityDate:w.compatibilityDate}))"])
    tools.append(binary_info)
    binary = Path(json.loads(binary_info["stdout"])["path"])
    tools.append(command([str(binary), "--version"]))
    ps = command(["/bin/ps", "-axo", "pid=,ppid=,comm="])
    owned = []
    for line in ps["stdout"].splitlines():
        fields = line.strip().split(None, 2)
        if len(fields) == 3 and fields[2] == str(binary):
            owned.append({"pid": int(fields[0]), "ppid": int(fields[1]), "executable": fields[2]})
    if owned:
        raise RuntimeError("this project's workerd binary is still running; no process is killed by collector")

    report = json.loads((HERE / "test-report.json").read_text())
    if report["status"] != "passed" or len(report["results"]) != 28:
        raise RuntimeError("final runtime report is not the selected passing result")
    paths = [item["persist"] for item in report["cleanup"] if "persist" in item]
    if not all(not Path(path).exists() for path in paths):
        raise RuntimeError("owned test storage remains")
    cleanup = {"recorded_cleanup_actions": len(report["cleanup"]), "owned_storage_paths": len(paths),
               "all_owned_storage_absent": True, "matching_workerd_processes": owned,
               "signals": [item for item in report["cleanup"] if "signal" in item],
               "process_scan_command": ps["argv"], "other_processes_modified": False}
    dump("cleanup.json", cleanup)

    locked = json.loads((PROJECT / "package-lock.json").read_text())
    inventory = json.loads((PROJECT / "THIRD_PARTY.yml").read_text())
    if len(inventory["packages"]) != len(locked["packages"]) - 1:
        raise RuntimeError("incomplete dependency inventory")
    if any(not p["license"] or p["installScriptsExecuted"] for p in inventory["packages"]):
        raise RuntimeError("unlicensed or script-enabled dependency")
    dependency_files = []
    node_modules = PROJECT / "node_modules"
    for path in sorted(node_modules.rglob("*")):
        if path.is_file():
            if not path.resolve().is_relative_to(node_modules.resolve()):
                raise RuntimeError("dependency symlink points outside selected installation")
            entry = record(path)
            if path.is_symlink():
                entry["symlink_target"] = str(path.readlink())
            dependency_files.append(entry)
    dump("dependency-files.json", {"scope": "actual-installed-development-toolchain-files", "files": dependency_files})

    source = []
    for directory in [PROJECT / "src", PROJECT / "test"]:
        source.extend(path for path in directory.rglob("*") if path.is_file())
    source.extend(PROJECT / name for name in ["package.json", "package-lock.json", "tsconfig.json", "README.md", ".gitignore", "THIRD_PARTY.yml", "build.mjs", "inventory.mjs", "audit-build.mjs"])
    source.extend([ROOT / "docs/hosted-worker-controller-implementation.md", HERE / "collect.py", HERE / "verify_snapshot.py", HERE / "jason-control-vectors.exs"])
    frozen_inputs = [
        ROOT / "AGENTS.md",
        ROOT / "docs/hosted-worker-controller-contract.md",
        ROOT / "docs/hosted-worker-transport-contract.md",
        ROOT / "docs/hosted-worker-transport-amendment-v2.md",
        ROOT / "docs/hosted-build-coordinator.md",
        ROOT / "verification/hosted-worker-controller-contract/acceptance.mjs",
        ROOT / "verification/hosted-worker-controller-contract/vectors.json",
        ROOT / "verification/hosted-worker-controller-contract/receipt.json",
        ROOT / "verification/hosted-worker-controller-contract/sources.json",
        ROOT / "verification/hosted-worker-controller-root-selection/dependencies.json",
        ROOT / "verification/hosted-worker-transport/cross-runtime-vectors.json",
        ROOT / "verification/hosted-worker-transport/generate_vectors.exs",
        ROOT / "verification/hosted-worker-transport/check_vectors.js",
        ROOT / "verification/hosted-worker-transport/check-vectors.stdout",
        HERE / "jason-control-vectors.json",
    ]
    compiled = [path for path in (PROJECT / "dist").rglob("*") if path.is_file()]
    input_records = [record(path) for path in sorted(set(source + frozen_inputs + compiled))]
    tree_digest = hashlib.sha256(json.dumps(input_records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    dump("source-manifest.json", {"scope": "explicit-final-owned-source-compiled-output-and-frozen-contract-inputs", "tree_sha256": tree_digest, "files": input_records})

    beams = ROOT / "hosted/_build/test/lib/jason/ebin"
    beam_files = sorted(beams.glob("*.beam")) + [beams / "jason.app"]
    dump("jason-beams.json", {"purpose": "approved-Jason-only-byte-probe", "files": [record(path) for path in beam_files], "loaded_mixer_modules": 0})

    archive = HERE / "source-snapshot.tar.gz"
    with archive.open("wb") as target, gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as tar:
            for entry in input_records:
                path = ROOT / entry["path"]
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise RuntimeError("source changed during capture")
                info = tarfile.TarInfo(entry["path"])
                info.size = len(data)
                info.mode = 0o644
                info.mtime = 0
                tar.addfile(info, io.BytesIO(data))

    histories = []
    for name, expected, argv in [
        ("npm-install", 0, ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]),
        ("build-attempt-1", 1, ["npm", "run", "build"]),
        ("build-attempt-2", 0, ["npm", "run", "build"]),
        ("runtime-smoke-attempt-1", 1, ["node", "-e", 'import("./test/acceptance-driver.mjs").then(async({createHarness})=>{const h=await createHarness({fixture:{},nowUs:"1900000000000000",errorUs:"1",clockQualified:true});try{console.log(await h.snapshot())}finally{await h.close()}})']),
        ("runtime-smoke-attempt-2", 0, ["node", "-e", 'import("./test/acceptance-driver.mjs").then(async({createHarness})=>{const h=await createHarness({fixture:{},nowUs:"1900000000000000",errorUs:"1",clockQualified:true});try{console.log(await h.snapshot())}finally{await h.close()}})']),
        ("frozen-acceptance-attempt-1", 0, ["node", "verification/hosted-worker-controller-contract/acceptance.mjs", "--candidate", "hosted-worker-controller/test/acceptance-driver.mjs"]),
        ("test-attempt-1", 0, ["npm", "test"]), ("test-attempt-2", 1, ["npm", "test"]), ("test-attempt-3", 0, ["npm", "test"]),
        ("jason-control-vectors", 0, ["elixir", "-pa", "hosted/_build/test/lib/jason/ebin", "verification/hosted-worker-controller-implementation/jason-control-vectors.exs", "verification/hosted-worker-controller-contract/vectors.json", "verification/hosted-worker-controller-implementation/jason-control-vectors.json"]),
        ("dependency-inventory", 0, ["node", "inventory.mjs"]),
        ("npm-ci", 0, ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]),
        ("build-final", 0, ["npm", "run", "build"]), ("test-final", 0, ["npm", "test"]),
        ("test-final-2", 0, ["npm", "test"]), ("test-freeze", 0, ["npm", "test"]),
        ("production-build-closure", 0, ["node", "audit-build.mjs"]),
    ]:
        histories.append({"argv": argv, "observed_exit_code": expected,
                          "cwd": str(ROOT if name in {"frozen-acceptance-attempt-1", "jason-control-vectors"} else PROJECT),
                          "selected_environment": {"MIXER_CONTROLLER_TEST_REPORT":str(HERE / "test-report.json")} if name=="test-freeze" else {},
                          "stdout": record(HERE / (name + ".stdout")), "stderr": record(HERE / (name + ".stderr"))})
    runtime = []
    for path in [binary, Path(shutil.which("node")).resolve(), Path(shutil.which("npm")).resolve(), Path(shutil.which("elixir")).resolve()]:
        runtime.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)})
    artifacts = [record(path) for path in sorted(HERE.iterdir()) if path.is_file() and path.name not in {"receipt.json", "snapshot-check.json", "collect.stdout", "collect.stderr"}]
    receipt = {
        "schema": 1, "created_at": datetime.now(timezone.utc).isoformat(), "status": "frozen-awaiting-independent-source-review",
        "scope": "per-operation-Worker-SQLite-DO-alarm-development-slice-only", "source_revision": "no Git inspected; exact explicit source tree digest and archive supplied",
        "source_tree_sha256": tree_digest, "source_archive": record(archive), "platform": platform.platform(),
        "requested_model": "gpt-6.1-sol", "requested_reasoning": "xhigh", "root_selection": "verification/hosted-worker-controller-root-selection/dependencies.json",
        "commands_and_outputs": histories, "tool_commands": tools, "runtime_binary_inputs": runtime,
        "source_manifest": record(HERE / "source-manifest.json"), "dependency_manifest": record(HERE / "dependency-files.json"),
        "jason_beams": record(HERE / "jason-beams.json"), "artifacts": artifacts,
        "results": {"reported_groups": 28, "frozen_scenarios": 20, "frozen_fixtures": 5, "original_producer_vectors": 36,
                    "additional_Jason_control_vectors": 24, "owned_cleanup_actions": len(report["cleanup"]), "owned_SIGKILL_cases": len(cleanup["signals"]),
                    "locked_dependency_entries": len(inventory["packages"]), "dependency_install_scripts_executed": 0, "production_module_closure_files": 9},
        "cleanup": cleanup, "historical_attempt_limits": "Numbered logs retained; historical failed source trees were not individually archived at failure. Final source tree is fully sealed.",
        "network": "npm public package retrieval and official documentation reading only; no provider API, account, or credential mutation",
        "not_verified": ["complete-controller", "independent-audit-registry-and-scheduler", "missed-wake-or-exhausted-alarm-retry-recovery", "actual-Cloudflare-ingress-TLS-framing-EOF", "qualified-production-clock",
                         "real-provider-images-sizing-egress-isolation", "external-macOS", "trusted-one-shot-supervisor-and-descendant-proof", "runner-auth-and-private-R2-source-artifacts",
                         "nonrollbackable-restore-authority", "hard-whole-domain-resources", "Neon-Oban-zero-traffic-operations", "signing-store-customer-GA"]
    }
    summary = json.dumps({"status": receipt["status"], "source_tree_sha256": tree_digest, "source_archive_sha256": receipt["source_archive"]["sha256"],
                          "dependency_files": len(dependency_files), "reported_groups": 28, "cleanup_actions": len(report["cleanup"])})
    receipt["collector_command"] = ["python3", "verification/hosted-worker-controller-implementation/collect.py"]
    receipt["collector_stdout_sha256"] = hashlib.sha256((summary + "\n").encode()).hexdigest()
    dump("receipt.json", receipt)
    print(summary)

if __name__ == "__main__":
    main()
