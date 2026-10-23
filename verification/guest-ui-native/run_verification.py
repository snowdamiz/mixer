#!/usr/bin/env python3
"""Original bounded host verification recorder; run from any directory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
VM = ROOT / "vm"
TARGET = VM / "target/stream-validation-verification"
ENV = dict(os.environ)
ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV["PATH"]
ENV["CARGO_TARGET_DIR"] = str(TARGET)
FEATURES = "experimental-stream-validation,experimental-function-cache,experimental-capability-native"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    source_paths = [*VM.joinpath("src").rglob("*.rs"), *VM.joinpath("include").glob("*.h"),
                    *VM.joinpath("tests").rglob("*.rs"), VM/"Cargo.toml", VM/"Cargo.lock",
                    OUT/"native_client.c", Path(__file__).resolve()]
    source_paths = sorted(p for p in source_paths if p.is_file())
    manifest = {str(p.relative_to(ROOT)): sha(p) for p in source_paths}
    source_bytes = (json.dumps(manifest, indent=2, sort_keys=True)+"\n").encode()
    (OUT/"source-manifest.json").write_bytes(source_bytes)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    receipt = {"schema": 1, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "source_revision": revision, "source_manifest_sha256": hashlib.sha256(source_bytes).hexdigest(),
               "scope": "macOS host native validate-only ABI. No Swift/UI, device, release or GA qualification.",
               "commands": [], "first_failure": None,
               "earlier_attempt": {"receipt": "verification/guest-ui-native/attempt-1/receipt.json",
                   "sha256": sha(OUT/"attempt-1/receipt.json"),
                   "first_failure": "Apple nm cannot read newer LLVM23 attributes in Rust standard-library archive objects. Debug tests and C link/run had passed. Inspect linked Mach-O symbols instead."},
               "limitations": ["Allocation probe measures caller-thread requested sizes, not heap/RSS.",
                               "Existing core allocator abort boundaries remain.",
                               "Phones disconnected; no new physical-device checks attempted.",
                               "Native ABI cannot validate runtime UI header/document content."]}
    def run(label, args, cwd=VM):
        result = subprocess.run(args, cwd=cwd, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = OUT/(label+".log")
        log.write_bytes(result.stdout)
        item = {"label": label, "argv": args, "cwd": str(cwd), "exit_status": result.returncode,
                "log": str(log.relative_to(ROOT)), "log_sha256": sha(log)}
        receipt["commands"].append(item)
        if result.returncode and receipt["first_failure"] is None: receipt["first_failure"] = item
        (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(label+": "+str(result.returncode), flush=True)
        if result.returncode:
            print(result.stdout[-4000:].decode(errors="replace"), flush=True)
            raise SystemExit(result.returncode)
    for label,args in [("rustc-version",["rustc","-Vv"]), ("cargo-version",["cargo","-V"]),
                       ("clang-version",["clang","--version"]), ("host-version",["uname","-a"])]: run(label,args)
    tests = ["experimental_guest_ui_validation", "experimental_guest_ui_allocations", "capability_ffi_public",
             "capability_ffi_allocations", "capability_registry", "experimental_capability_guest", "experimental_capability_guest_allocations"]
    for profile in ["debug","release"]:
        release = ["--release"] if profile=="release" else []
        args = ["cargo","test",*release,"--features",FEATURES,"--lib"]
        for test in tests: args.extend(["--test",test])
        args.extend(["--","--nocapture"])
        run(profile+"-rust-tests",args)
        run(profile+"-archive-build",["cargo","build",*release,"--features",FEATURES,"--lib"])
        archive = TARGET/profile/"libmixer_vm.a"
        binary = TARGET/profile/"guest-ui-native-client"
        run(profile+"-c-build",["clang","-std=c11","-Wall","-Wextra","-Werror","-I",str(VM/"include"),str(OUT/"native_client.c"),str(archive),"-o",str(binary)])
        run(profile+"-c-run",[str(binary)])
        run(profile+"-symbols",["nm","-gU",str(binary)])
        symbols = (OUT/(profile+"-symbols.log")).read_text()
        for symbol in ["mixer_vm_capability_guest_ui_validate_v1", "mixer_vm_capability_validate_v1", "mixer_vm_session_create_v1"]:
            assert "_"+symbol in symbols, "missing linked public symbol "+symbol
        receipt.setdefault("artifacts",{})[profile] = {"archive": str(archive), "archive_sha256":sha(archive),
            "binary":str(binary),"binary_sha256":sha(binary),"features":FEATURES}
    freeze = json.loads((ROOT/"verification/guest-ui-contract-freeze-2026-10-23.json").read_text())
    preserved = {**freeze["normative_contracts"], **freeze["preserved_old_contracts"], **freeze["preserved_old_headers"]}
    actual = {path:sha(ROOT/path) for path in preserved}
    assert actual==preserved, "frozen contract/header preservation mismatch"
    receipt["preserved_contracts_and_headers"] = actual
    final_manifest = {str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    assert manifest==final_manifest, "native verification source changed during run"
    receipt["completed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["result"] = "passed"
    (OUT/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("host verification passed; sources stable; frozen contracts/headers preserved", flush=True)

if __name__=="__main__": main()
