#!/usr/bin/env python3
"""Independently link small probes to retained owner products; no SPM graph."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENV = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
PIN = "05041d1b1658fc348152cf6b1173ca138770e9c4286568a5b4f035c111c2b197"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "2026-10-23-candidate-1"
    owner = ROOT / (sys.argv[2] if len(sys.argv) > 2 else "verification/guest-ui-sdk/2026-10-23-candidate-1/receipt.json")
    products_root = ROOT / (sys.argv[3] if len(sys.argv) > 3 else "sdk/.build/out/Products")
    out = HERE / name
    out.mkdir(exist_ok=False)
    product_root = out / ".build"
    product_root.mkdir()
    receipt = {
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "owner_receipt": str(owner.relative_to(ROOT)), "owner_receipt_sha256": sha(owner),
        "retained_product_root": str(products_root.relative_to(ROOT)),
        "independent_driver_sha256": sha(__file__),
        "probe_sources": {str(p.relative_to(ROOT)): sha(p) for p in HERE.glob("*.swift")},
        "commands": [], "retained_inputs": {},
        "scope": "Independent SDK adversarial standalone probes linked to retained owner Core/UI/Guest host objects. No new SPM graph, activation compilation, device discovery/run, native display receipt, publication, or GA qualification.",
    }
    if owner.name == "receipt.json" and "candidate-1" in str(owner):
        assert sha(owner) == PIN, "original sealed owner receipt changed"
    owner_data = json.loads(owner.read_text())
    receipt["owner_source_manifest_sha256"] = owner_data["source_manifest_sha256"]
    receipt["source_hashes_at_start"] = {p: sha(ROOT / p) for p in owner_data["source_files"]}
    receipt["owner_sources_match_at_start"] = receipt["source_hashes_at_start"] == owner_data["source_files"]
    def save():
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def run(label, argv, timeout=90):
        start = time.monotonic()
        result = subprocess.run([str(p) for p in argv], cwd=ROOT, env=ENV, timeout=timeout,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = out / (label + ".log")
        log.write_bytes(result.stdout)
        receipt["commands"].append({"name": label, "argv": [str(p) for p in argv],
            "cwd": str(ROOT), "environment_overrides": {"DEVELOPER_DIR": ENV["DEVELOPER_DIR"]},
            "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - start,
            "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)})
        save()
        print(label + ": " + str(result.returncode), flush=True)
        return result
    run("swift-version", ["swiftc", "--version"])
    run("platform", ["uname", "-a"])
    # Copy a few MiB so a coordinated owner rebuild cannot change our inputs
    # between compilation and execution. Modules and objects are hash-sealed.
    for configuration in ["Release", "Debug"]:
        source = products_root / configuration
        destination = product_root / configuration
        destination.mkdir()
        for module in ["MixerCore", "MixerUI", "MixerGuest"]:
            shutil.copy2(source / (module + ".o"), destination / (module + ".o"))
            shutil.copytree(source / (module + ".swiftmodule"), destination / (module + ".swiftmodule"))
        for path in sorted(destination.rglob("*")):
            if path.is_file():
                original = source / path.relative_to(destination)
                assert sha(original) == sha(path), "retained product changed during copy"
                receipt["retained_inputs"][str(original.relative_to(ROOT))] = {
                    "sha256": sha(path), "bytes": path.stat().st_size,
                    "snapshot": str(path.relative_to(ROOT))}
    save()
    for configuration in ["Release", "Debug"]:
        products = product_root / configuration
        objects = [products / (module + ".o") for module in ["MixerGuest", "MixerUI", "MixerCore"]]
        flags = ["-O"] if configuration == "Release" else ["-Onone", "-sanitize=thread", "-D", "REVIEW_INTERNALS"]
        for filename in ["ExchangeAdversarialProbe", "UnicodeSnapshotProbe"]:
            executable = product_root / (filename + "-" + configuration)
            result = run(configuration.lower() + "-compile-" + filename,
                ["swiftc", "-swift-version", "6", "-warnings-as-errors", "-parse-as-library", "-I", products]
                + flags + [HERE / (filename + ".swift")] + objects + ["-o", executable])
            if result.returncode == 0:
                run(configuration.lower() + "-run-" + filename, [executable])
                receipt.setdefault("executables", {})[str(executable.relative_to(ROOT))] = sha(executable)
    receipt["source_hashes_at_end"] = {p: sha(ROOT / p) for p in owner_data["source_files"]}
    receipt["owner_sources_match_at_end"] = receipt["source_hashes_at_end"] == owner_data["source_files"]
    receipt["retained_snapshot_inputs_unchanged"] = all(sha(ROOT / row["snapshot"]) == row["sha256"]
                                                     for row in receipt["retained_inputs"].values())
    receipt["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["command_failures"] = sum(row["exit_code"] != 0 for row in receipt["commands"])
    passed = receipt["command_failures"] == 0 and receipt["retained_snapshot_inputs_unchanged"]
    receipt["status"] = "scoped independent SDK probes passed" if passed else "scoped independent SDK probes failed; preserved logs"
    save()
    print("receipt_sha256=" + sha(out / "receipt.json"))
    if not passed:
        sys.exit(1)

if __name__ == "__main__":
    main()
