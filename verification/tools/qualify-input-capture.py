#!/usr/bin/env python3
"""Qualify a frozen declared-input capture tool on the host; no device commands."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("qualification", ROOT / "compiler/qualification_support.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.name):
        parser.error("name must use lowercase ASCII letters, numbers and hyphens")
    revision = subprocess.check_output(["git", "rev-parse", args.revision + "^{commit}"], cwd=ROOT, text=True).strip()
    output = ROOT / "verification" / ("input-capture-" + args.name)
    work = ROOT / "verification/local" / ("input-capture-" + args.name)
    output.mkdir(parents=True, exist_ok=False); work.mkdir(parents=True, exist_ok=False)
    commands = []
    record = helper.CommandRecorder(output, commands, ROOT)
    env = helper.clean_environment()
    swift = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    receipt = {"schema": 1, "sourceRevision": revision, "status": "running", "commands": commands,
               "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "runnerSHA256": helper.digest(Path(__file__)), "helperSHA256": helper.digest(ROOT / "compiler/qualification_support.py"),
               "limitations": ["Declared file capture only; no automatic complete graph capture, build consumption or compiler/SDK version attestation",
                               "Snapshot includes a real frozen simulator VM archive as a byte-copy probe; remaining inputs and descriptor are synthetic integration fixtures",
                               "No binary embedding, signing, physical execution, release publication or GA qualification"]}
    def run(name, argv, environment=env):
        result = record.run(name, argv, env=environment, timeout=600)
        print(name + " passed", flush=True)
        return result
    try:
        source = work / "source"; source.mkdir()
        archive = work / "source.tar"
        run("source-export", ["/usr/bin/git", "archive", "--format=tar", "--output=" + str(archive), revision,
                               "runtime-identity", "updates", "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json"])
        with tarfile.open(archive) as stream: stream.extractall(source, filter="data")
        manifest = {str(p.relative_to(source)): helper.digest(p) for p in sorted(source.rglob("*")) if p.is_file()}
        receipt["sourceArchiveSHA256"] = helper.digest(archive)
        receipt["sourceFiles"] = manifest
        receipt["sourceDigest"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        receipt["swiftVersion"] = run("swift-version", [swift, "--version"])
        receipt["pythonVersion"] = run("python-version", [sys.executable, "--version"])
        run("identity-cli-build", [swift, "build", "--package-path", source / "runtime-identity", "--product", "mixer-identity"])
        binary_dir = run("identity-cli-location", [swift, "build", "--package-path", source / "runtime-identity", "--show-bin-path"]).strip()
        tool = Path(binary_dir) / "mixer-identity"
        receipt["identityToolSHA256"] = helper.digest(tool)
        test_env = env | {"MIXER_IDENTITY_TOOL": str(tool)}
        for mode, flags in [("normal", []), ("optimized-python", ["-O"])]:
            run("capture-tests-" + mode, [sys.executable, *flags, "-B", "-m", "unittest", "discover", "-s",
                source / "runtime-identity/build-tools/tests", "-v"], test_env)
        inputs = work / "inputs"; inputs.mkdir()
        native = ROOT / "runtime/.build/native-ios-simulator"
        native_receipt = json.loads((native / "receipt.json").read_text())
        library = native / "lib/libmixer_vm.a"
        if helper.digest(library) != native_receipt["static_library_sha256"]:
            raise ValueError("Original native library changed")
        shutil.copyfile(library, inputs / "libmixer_vm.a")
        (inputs / "fixture.json").write_text('{"fixture":"declared-input-byte-capture-only"}\n')
        descriptor = json.loads((source / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json").read_text())
        descriptor["platform"].update(environment="simulator", target="arm64-apple-ios17.0-simulator")
        descriptor_path = work / "descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor, sort_keys=True) + "\n")
        def pointers(value, path=""):
            result = []
            if isinstance(value, dict):
                for key, item in value.items():
                    result.extend([path + "/" + key] if key.endswith("_sha256") else pointers(item, path + "/" + key))
            elif isinstance(value, list):
                for i, item in enumerate(value): result.extend(pointers(item, path + "/" + str(i)))
            return result
        bindings = []
        for pointer in sorted(pointers(descriptor)):
            name = "libmixer_vm.a" if pointer == "/engine/artifact_sha256" else "fixture.json"
            bindings.append({"pointer": pointer, "kind": "file", "files": [{"name": name, "path": name}]})
        binding_path = work / "bindings.json"
        binding_path.write_text(json.dumps({"schema": 1, "bindings": bindings}) + "\n")
        script = source / "runtime-identity/build-tools/capture.py"
        snapshot = work / "snapshot"
        captured = json.loads(run("native-archive-capture", [sys.executable, "-B", script, "capture", "--descriptor", descriptor_path,
            "--bindings", binding_path, "--input-root", inputs, "--output", snapshot, "--identity-tool", tool]))
        copied = snapshot / "objects" / native_receipt["static_library_sha256"]
        if helper.digest(copied) != helper.digest(library): raise ValueError("Captured archive mismatch")
        run("native-archive-verify", [sys.executable, "-B", script, "verify", "--snapshot", snapshot,
            "--expected-fingerprint", captured["fingerprint"], "--identity-tool", tool])
        (inputs / "libmixer_vm.a").write_bytes(b"original path changed after capture")
        run("verify-after-source-mutation", [sys.executable, "-O", "-B", script, "verify", "--snapshot", snapshot,
            "--expected-fingerprint", captured["fingerprint"], "--identity-tool", tool])
        shutil.copyfile(snapshot / "inputs.json", output / "captured-inputs.json")
        shutil.copyfile(snapshot / "descriptor.json", output / "captured-descriptor.json")
        receipt["nativeArchiveProbe"] = {"sourceRevision": native_receipt["source_revision"],
            "librarySHA256": native_receipt["static_library_sha256"], "capturedArchiveBytes": copied.stat().st_size,
            "result": captured, "verifiedAfterOriginalPathMutation": True,
            "inventorySHA256": helper.digest(output / "captured-inputs.json"),
            "descriptorSHA256": helper.digest(output / "captured-descriptor.json")}
        if any(helper.digest(source / name) != digest for name, digest in manifest.items()): raise ValueError("Frozen source changed")
        receipt["sourceUnchangedDuringRun"] = True
        receipt["testFunctionsPerMode"] = 13
        receipt["status"] = "passed scoped host input-capture qualification"
    except Exception as error:
        receipt["status"] = "failed"; receipt["error"] = str(error)
        raise
    finally:
        receipt["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__": main()
