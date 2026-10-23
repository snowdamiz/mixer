#!/usr/bin/env python3
"""Independent native/header seam probe using the retained bridge graph."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRIDGE = ROOT / "experimental-capability-runtime/.build/guest-ui-release/out/Products/Release"
MAPS = ROOT / "experimental-capability-runtime/.build/guest-ui-release/out/Intermediates.noindex/GeneratedModuleMaps"
ENV = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="2026-10-23-bridge-seams-1")
    parser.add_argument("--sdk-products", default="verification/guest-ui-exchange-review/2026-10-23-fixed-2/.build/Release")
    parser.add_argument("--archive", default="experimental-capability-runtime/.build/guest-ui-native/libmixer_vm_capability_experimental.a")
    parser.add_argument("--headers", default="vm/include")
    parser.add_argument("--native-qualification")
    parser.add_argument("--native-audit")
    args = parser.parse_args()
    OUT = HERE / args.run
    SDK = ROOT / args.sdk_products
    ARCHIVE = ROOT / args.archive
    HEADERS = ROOT / args.headers
    OUT.mkdir(exist_ok=False)
    (OUT / ".build").mkdir()
    owner = ROOT / "verification/guest-ui-bridge/receipt.json"
    assert sha(owner) == "08035b9ea818c6ff60170848177aa38e45df0a3d10e9a73d676ca0e645e1d8e6"
    final = json.loads((ROOT / "verification/guest-ui-bridge/release-handoff.json").read_text())
    sources = {p: sha(ROOT / p) for p in final["sourceSHA256Before"]
               if p.startswith("experimental-capability-runtime/")}
    assert all(sources[p] == final["sourceSHA256Before"][p] for p in sources)
    objects = [SDK / (module + ".o") for module in ["MixerGuest", "MixerUI", "MixerCore"]]
    objects += [BRIDGE / (module + ".o") for module in ["MixerExperimentalCapabilityRuntime", "MixerCapabilities", "MixerCapabilityIO", "CMixerVMCapability"]]
    inputs = objects + [ARCHIVE, HERE / "BridgeSeamProbe.swift"]
    inputs += [HEADERS / name for name in ["mixer_vm.h", "mixer_vm_capability.h", "mixer_vm_guest_ui.h"]]
    inputs += [p for folder in [SDK, BRIDGE] for p in folder.rglob("*.swiftmodule") if p.is_file()]
    inputs += [MAPS / (module + ".modulemap") for module in ["CMixerVMCapability", "MixerCapabilityIO"]]
    receipt = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "owner_receipt_sha256": sha(owner), "bridge_sources": sources,
        "independent_driver_sha256": sha(__file__),
        "inputs": {str(p.relative_to(ROOT)): sha(p) for p in inputs}, "commands": [],
        "scope": "Independent original Wasm/header/native diagnostics probes; retained bridge Release objects linked against the explicitly selected SDK snapshot with unchanged SPI. Native Mac only; no activation compilation, signed selection, native renderer, I/O-effect admission claim, device, publication, or GA qualification.",
        "selected_native_archive": {"path": str(ARCHIVE.relative_to(ROOT)), "sha256": sha(ARCHIVE)},
        "selected_sdk_products": str(SDK.relative_to(ROOT))}
    for name, relative in [("native_qualification", args.native_qualification), ("native_binding_audit", args.native_audit)]:
        if relative:
            path = ROOT / relative
            receipt[name] = {"path": relative, "sha256": sha(path)}
    def save():
        (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def run(label, argv):
        start = time.monotonic()
        result = subprocess.run([str(p) for p in argv], cwd=ROOT, env=ENV, timeout=120,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT / (label + ".log"); log.write_bytes(result.stdout)
        receipt["commands"].append({"name": label, "argv": [str(p) for p in argv],
            "cwd": str(ROOT), "environment_overrides": {"DEVELOPER_DIR": ENV["DEVELOPER_DIR"]},
            "exit_code": result.returncode, "elapsed_seconds": time.monotonic() - start,
            "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)})
        save(); print(label + ": " + str(result.returncode), flush=True)
        return result
    run("swift-version", ["swiftc", "--version"])
    executable = OUT / ".build/bridge-seam-probe"
    flags = ["-I", SDK, "-I", BRIDGE, "-module-cache-path", OUT / ".build/cache"]
    for module in ["CMixerVMCapability", "MixerCapabilityIO"]:
        flags += ["-Xcc", "-fmodule-map-file=" + str(MAPS / (module + ".modulemap"))]
    flags += ["-Xcc", "-I" + str(HEADERS)]
    compiled = run("compile", ["swiftc", "-swift-version", "6", "-warnings-as-errors", "-parse-as-library", "-O"]
        + flags + [HERE / "BridgeSeamProbe.swift"] + objects + [ARCHIVE, "-o", executable])
    if compiled.returncode == 0:
        run("run", [executable]); receipt["executable_sha256"] = sha(executable)
    receipt["inputs_unchanged"] = receipt["inputs"] == {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    receipt["bridge_sources_unchanged"] = sources == {p: sha(ROOT / p) for p in sources}
    receipt["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["command_failures"] = sum(row["exit_code"] != 0 for row in receipt["commands"])
    receipt["status"] = "scoped native bridge seams passed" if receipt["command_failures"] == 0 and receipt["inputs_unchanged"] and receipt["bridge_sources_unchanged"] else "scoped native bridge seams failed"
    save(); print("receipt_sha256=" + sha(OUT / "receipt.json"))
    if receipt["status"] != "scoped native bridge seams passed":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
