#!/usr/bin/env python3
"""Frozen identity source embedding, host execution and mobile compile checks."""
import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
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
    if not re.fullmatch(r"[a-z0-9-]+", args.name):
        parser.error("name must use lowercase ASCII letters, numbers and hyphens")
    revision = subprocess.check_output(["git", "rev-parse", args.revision + "^{commit}"], cwd=ROOT, text=True).strip()
    output = ROOT / "verification" / ("runtime-embedding-" + args.name)
    work = ROOT / "verification/local" / ("runtime-embedding-" + args.name)
    output.mkdir(parents=True, exist_ok=False)
    work.mkdir(parents=True, exist_ok=False)
    commands = []
    recorder = helper.CommandRecorder(output, commands, ROOT)
    env = helper.clean_environment()
    apple = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    cross = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
    cross_env = env | {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
    receipt = {"schema": 1, "sourceRevision": revision, "status": "running", "commands": commands,
               "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "runnerSHA256": helper.digest(Path(__file__)), "helperSHA256": helper.digest(ROOT / "compiler/qualification_support.py"),
               "limitations": ["Synthetic original declared-input fixture; no complete application graph, compiler label attestation or native linker consumption proof",
                               "Generated source compiled and executed on host; mobile checks compile the source with its dependencies but do not link/install/run an app",
                               "No signed binary/provenance, project-generator integration, physical devices, guest activation, hosted publication or gate closure"]}

    def run(name, argv, environment=env):
        result = recorder.run(name, argv, env=environment, timeout=600)
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
        receipt["swiftVersion"] = run("swift-version", [apple, "--version"])
        receipt["crossSwiftVersion"] = run("cross-swift-version", [cross, "--version"], cross_env)
        receipt["pythonVersion"] = run("python-version", [sys.executable, "--version"])
        run("identity-cli-build", [apple, "build", "--package-path", source / "runtime-identity", "--product", "mixer-identity", "-j", "4"])
        binary = run("identity-cli-location", [apple, "build", "--package-path", source / "runtime-identity", "--show-bin-path"]).strip()
        tool = Path(binary) / "mixer-identity"
        receipt["identityToolSHA256"] = helper.digest(tool)
        test_env = env | {"MIXER_IDENTITY_TOOL": str(tool), "MIXER_SWIFT": apple}
        counts = {}
        for mode, flags in [("normal", []), ("optimized-python", ["-O"])]:
            name = "tests-" + mode
            run(name, [sys.executable, *flags, "-B", "-m", "unittest", "discover", "-s",
                       source / "runtime-identity/build-tools/tests", "-v"], test_env)
            text = (output / (name + ".stderr")).read_text()
            count = re.findall(r"^Ran (\d+) tests in", text, re.MULTILINE)
            if len(count) != 1 or int(count[0]) != 19 or "\nOK\n" not in text:
                raise ValueError("Unexpected or missing unittest result")
            counts[mode] = int(count[0])
        receipt["testFunctions"] = counts
        inputs = work / "inputs"; inputs.mkdir()
        (inputs / "fixture.txt").write_bytes(b"Original compiled-identity development fixture\n")
        descriptor = json.loads((source / "activation/Tests/MixerActivationTests/Fixtures/runtime-identity.json").read_bytes())
        descriptor_path = work / "descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor) + "\n")

        def pointers(value, path=""):
            result = []
            if isinstance(value, dict):
                for key, item in value.items():
                    result.extend([path + "/" + key] if key.endswith("_sha256") else pointers(item, path + "/" + key))
            elif isinstance(value, list):
                for index, item in enumerate(value): result.extend(pointers(item, path + "/" + str(index)))
            return result

        bindings = {"schema": 1, "bindings": [{"pointer": p, "kind": "file", "files": [
            {"name": "fixture.txt", "path": "fixture.txt"}]} for p in sorted(pointers(descriptor))]}
        binding_path = work / "bindings.json"
        binding_path.write_text(json.dumps(bindings) + "\n")
        snapshot = work / "snapshot"
        captured = json.loads(run("capture", [sys.executable, "-B", source / "runtime-identity/build-tools/capture.py", "capture",
            "--descriptor", descriptor_path, "--bindings", binding_path, "--input-root", inputs,
            "--output", snapshot, "--identity-tool", tool]))
        generated = work / "generated"
        emitted = json.loads(run("emit", [sys.executable, "-B", source / "runtime-identity/build-tools/embed.py",
            "--snapshot", snapshot, "--expected-fingerprint", captured["fingerprint"], "--identity-tool", tool, "--output", generated]))
        expected = json.loads(run("inspect", [tool, "inspect", snapshot / "descriptor.json"]))
        shutil.copyfile(snapshot / "descriptor.json", output / "descriptor.json")
        for name in ["embedding.json", "MixerInstalledRuntime.swift"]:
            shutil.copyfile(generated / name, output / name)
        package = work / "consumer"
        library = package / "Sources/EmbeddedIdentity"; library.mkdir(parents=True)
        executable = package / "Sources/EmbeddedConsumer"; executable.mkdir()
        shutil.copyfile(generated / "MixerInstalledRuntime.swift", library / "MixerInstalledRuntime.swift")
        (package / "Package.swift").write_text('''// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "EmbeddedConsumer", platforms: [.macOS(.v14), .iOS(.v17)],
    dependencies: [.package(path: "../source/runtime-identity")], targets: [
    .target(name: "EmbeddedIdentity", dependencies: [.product(name: "MixerRuntimeIdentity", package: "runtime-identity")]),
    .executableTarget(name: "EmbeddedConsumer", dependencies: ["EmbeddedIdentity"])])
''')
        (executable / "main.swift").write_text('''import Foundation
import EmbeddedIdentity
do {
    let identity = try MixerInstalledRuntime.load()
    let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
    print(String(decoding: try encoder.encode(identity.installedRuntime), as: UTF8.self))
} catch {
    FileHandle.standardError.write(Data(String(describing: error).utf8)); exit(3)
}
''')
        receipt["generatedSourceFiles"] = {str(p.relative_to(package)): helper.digest(p) for p in sorted(package.rglob("*")) if p.is_file()}
        # Compilation/execution is independent of all original data paths.
        shutil.rmtree(snapshot); shutil.rmtree(inputs); descriptor_path.unlink()
        run("host-release-build", [apple, "build", "--package-path", package, "-c", "release", "--product", "EmbeddedConsumer", "-j", "4"])
        binary = Path(run("host-release-location", [apple, "build", "--package-path", package, "-c", "release", "--show-bin-path"]).strip()) / "EmbeddedConsumer"
        recovered = json.loads(run("host-release-run", [binary]))
        if recovered != expected["installedRuntime"]: raise ValueError("Compiled installed policy differs")
        receipt["compiledConsumer"] = {"binarySHA256": helper.digest(binary), "fingerprint": recovered["runtime"],
                                       "sourceSnapshotRemovedBeforeBuild": True, "installedPolicyMatches": True}
        run("ios-compile", [apple, "build", "--package-path", package, "--target", "EmbeddedIdentity", "--triple", "arm64-apple-ios17.0",
            "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk",
            "--scratch-path", work / "ios", "-Xswiftc", "-warnings-as-errors", "-j", "4"])
        run("android-compile", [cross, "build", "--package-path", package, "--target", "EmbeddedIdentity",
            "--swift-sdks-path", "/Users/andreyyurlov/.swiftpm/swift-sdks", "--swift-sdk", "aarch64-unknown-linux-android28",
            "--scratch-path", work / "android", "-c", "release", "-j", "4"], cross_env)
        receipt["mobileObjects"] = {str(p.relative_to(work)): helper.digest(p) for target in ["ios", "android"]
                                    for p in (work / target).rglob("MixerInstalledRuntime.swift.o")}
        if len(receipt["mobileObjects"]) != 2: raise ValueError("Missing compiled identity object")
        if any(helper.digest(source / path) != digest for path, digest in manifest.items()): raise ValueError("Frozen source changed")
        receipt["sourceUnchangedDuringRun"] = True
        receipt["emitted"] = emitted
        receipt["status"] = "passed frozen host compiled identity and mobile source compilation"
    except Exception as error:
        receipt["status"] = "failed"; receipt["error"] = str(error)
        raise
    finally:
        receipt["completedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__": main()
