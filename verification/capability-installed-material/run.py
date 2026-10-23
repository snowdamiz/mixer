#!/usr/bin/env python3
"""Freeze and qualify installed material only; never constructs adapters or sessions."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXCLUDED = {".build", ".swiftpm", "__pycache__"}
NATIVE = "a015ff65980422dd0b9c5cad2e28741d1e5ba478e0f657dcaedf75477d553b72"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(value, message):
    if not value: raise RuntimeError(message)
def files(directory):
    return [p for p in directory.rglob("*") if p.is_file() and not EXCLUDED.intersection(p.relative_to(directory).parts)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    require(re.fullmatch("[a-z0-9-]+", args.label), "simple label required")
    out = HERE / args.label; out.mkdir(exist_ok=False)
    work = ROOT / "capability-activation/.build" / ("qualification-" + args.label); work.mkdir(exist_ok=False)
    source = work / "source"; source.mkdir()
    inputs = []
    for package in ["capability-activation", "experimental-capability-runtime", "runtime-identity", "updates", "sdk"]:
        inputs += list((ROOT / package).glob("Package.*"))
        inputs += files(ROOT / package / "Sources") + files(ROOT / package / "Tests")
    inputs += [ROOT / "capability-activation/README.md", ROOT / "docs/capability-installed-factory-api-design.md"]
    inputs += files(ROOT / "capabilities/java") + files(ROOT / "capabilities/schema")
    inputs += [ROOT / "capabilities/tools/generate.py", ROOT / "capabilities/tools/export-native-preimage.py"]
    inputs += list((ROOT / "contracts").glob("*.json"))
    inputs += [p for p in files(HERE) if p.suffix in {".py", ".swift"}]
    dependency_receipts = {
        "v3": ROOT / "verification/release-v3-swift/2026-10-23-candidate-1/receipt.json",
        "identity2": ROOT / "verification/runtime-identity-v2/2026-10-23-final-v2-snapshot/receipt.json",
        "bridge": ROOT / "experimental-capability-runtime/verification/2026-10-23-validation-candidate-1/receipt.json",
        "native": ROOT / "experimental-capability-runtime/build-verification/2026-10-23-final-v3/receipt.json",
    }
    inputs += list(dependency_receipts.values())
    records = {}
    for path in sorted(set(inputs)):
        require(not path.is_symlink(), "regular source input required")
        relative = path.relative_to(ROOT).as_posix(); raw = path.read_bytes(); records[relative] = sha(raw)
        target = source / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    for role, key in [("v3", "source_files"), ("identity2", "inputs"), ("bridge", "source")]:
        expected = json.loads(dependency_receipts[role].read_bytes())[key]
        for relative, digest in records.items():
            if "/Sources/" in relative and relative in expected:
                require(digest == expected[relative], "frozen dependency source mismatch " + relative)
    manifest = "".join(d + "  " + p + "\n" for p, d in sorted(records.items())).encode()
    (out / "source-manifest.sha256").write_bytes(manifest)
    native_source = ROOT / "experimental-capability-runtime/build-verification/local/qualified-final-v3/host"
    native = work / "native"; shutil.copytree(native_source, native)
    archive = native / "lib/libmixer_vm_capability_experimental.a"
    require(sha(archive.read_bytes()) == NATIVE, "qualified single archive pin")
    native_records = {str(p.relative_to(native)): sha(p.read_bytes()) for p in files(native)}
    receipt = dict(status="running", started_at=now(), head_at_start=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        source_files=records, source_manifest_sha256=sha(manifest), immutable_source_export=str(source),
        dependency_receipts={role: {"path": str(path.relative_to(ROOT)), "sha256": sha(path.read_bytes())} for role, path in dependency_receipts.items()},
        native_files=native_records, native_copy=str(native), commands=[],
        scope="Installed immutable material only; no updater, adapter/session construction, VM call, task scheduling, host initialization or execution authority",
        limitations=["Known linked SDK implementation/schema binding does not attest arbitrary descriptor build/toolchain/engine/dependency hashes or complete graph consumption/final signed binary",
            "Embedding must supply trusted native application-private container; path privacy is not inspected here",
            "Swift/C-shim TSan only; qualified Rust archive/system frameworks are not instrumented",
            "No physical mobile, published package, signing/store, health/recovery or GA qualification"])
    def save(): (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    def unchanged():
        for relative, digest in records.items():
            require(sha((ROOT / relative).read_bytes()) == digest, "source changed " + relative)
            require(sha((source / relative).read_bytes()) == digest, "export changed " + relative)
        for relative, digest in native_records.items(): require(sha((native / relative).read_bytes()) == digest, "archive/header copy changed")
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    def run(name, argv, scope, expected=0, diagnostic=None, tests=None, timeout=240):
        unchanged(); started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            raw, code = result.stdout, result.returncode
        except subprocess.TimeoutExpired as error: raw, code = (error.stdout or b"") + b"\nqualification timeout\n", 124
        log = out / (name + ".log"); log.write_bytes(raw)
        row = dict(name=name, argv=argv, cwd=str(source), environment={"DEVELOPER_DIR": env["DEVELOPER_DIR"]}, exit_code=code, expected_exit=expected,
                   elapsed_seconds=time.monotonic() - started, log=str(log.relative_to(ROOT)), sha256=sha(raw), scope=scope)
        if tests is not None:
            row["expected_tests"] = tests
            row["observed_xctest_counts"] = [int(n) for n in re.findall(rb"Executed (\d+) tests, with 0 failures", raw)]
        if diagnostic: row["required_diagnostic_fragment"] = diagnostic
        receipt["commands"].append(row); save(); unchanged()
        require(code == expected, name + ": unexpected exit " + str(code))
        if tests is not None: require(row["observed_xctest_counts"] == [tests, tests, tests], name + ": unexpected test count")
        if diagnostic: require(diagnostic.encode() in raw, name + ": unexpected negative compile diagnostic")
        print(name + ": " + str(code), flush=True)
    save(); print("frozen source manifest " + sha(manifest), flush=True)
    try:
        run("swift-version", ["swift", "--version"], "Observed compiler")
        run("xcode-version", ["xcodebuild", "-version"], "Observed host SDK")
        run("python-version", ["python3", "--version"], "Observed helper interpreter")
        run("host-version", ["uname", "-a"], "Observed host environment")
        run("native-preimage-tests", ["python3", str(source / "verification/capability-installed-material/test_native_preimage.py"), "-v"], "Three original helper tests including generator --check, repeat/no-write, copied-input mutations")
        build = work / "build"
        flags = ["-Xcc", "-I" + str(native / "include"), "-Xlinker", "-L" + str(native / "lib")]
        base = ["swift", "test", "--package-path", str(source / "capability-activation"), "--scratch-path", str(build), "-Xswiftc", "-warnings-as-errors"] + flags
        for mode in ["debug", "release"]: run("material-" + mode, base + ["--configuration", mode], "All16 original material tests, actual known native source preimage, immutable dependency export", tests=16)
        products = build / "out/Products/Release"
        require((products / "libMixerCapabilityActivation.a").is_file(), "release static product")
        maps = build / "out/Intermediates.noindex/GeneratedModuleMaps"
        common = ["swiftc", "-swift-version", "6", "-warnings-as-errors", "-I", str(products)]
        for name in ["MixerDurableIO", "MixerCapabilityIO", "CMixerVMCapability"]:
            common += ["-Xcc", "-fmodule-map-file=" + str(maps / (name + ".modulemap"))]
        common += ["-Xcc", "-I" + str(native / "include")]
        client = work / "material-public-client"
        run("public-client-link", common + ["-L", str(products), "-lMixerCapabilityActivation", "-L", str(native / "lib"), "-lmixer_vm_capability_experimental",
            str(source / "verification/capability-installed-material/PublicClient/main.swift"), "-o", str(client)], "External non-testable release product consumer; one experimental native archive")
        receipt["public_client"] = dict(path=str(client), sha256=sha(client.read_bytes()), bytes=client.stat().st_size); save()
        run("public-client-run", [str(client), str(source / "capability-activation/Tests/MixerCapabilityActivationTests/Fixtures")], "Actual public material initializer/fingerprint")
        negatives = source / "verification/capability-installed-material/CompileNegative"
        run("public-positive", common + ["-typecheck", str(negatives / "positive.swift")], "External positive typecheck control")
        for name, fragment in {"private-state": "inaccessible", "create-session": "has no member 'create'", "enable-effects": "has no member 'enableEffects'", "replace-verifier": "extra argument", "replace-adapters": "extra argument"}.items():
            run("reject-" + name, common + ["-typecheck", str(negatives / (name + ".swift"))], "Intentional external compile failure: opaque material does not construct or enable execution", expected=1, diagnostic=fragment)
        run("material-tsan", base + ["--configuration", "debug", "--sanitize", "thread"], "All16 material cases incl32 parallel immutable initializations/value copies; Swift/C shim instrumentation", tests=16)
        unchanged(); receipt.update(status="scoped checks passed; independent review/integration pending", completed_at=now(), source_and_export_unchanged=True)
    except Exception as error:
        receipt.update(status="failed check preserved", completed_at=now(), problem=str(error)); save(); raise
    save(); print(json.dumps({"source_manifest_sha256": sha(manifest), "receipt_sha256": sha((out / "receipt.json").read_bytes())}))


if __name__ == "__main__": main()
