#!/usr/bin/env python3
"""Implementer evidence for the strict Swift value codec, not a guest runtime."""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LOGS = OUT / "logs"
FROZEN = "3ba601332dab7c2aba98d7a50d7f0e893b1ea776"
FIXTURES = ROOT / "verification/guest-capability-contract"
CONTRACT = ROOT / "contracts/guest-capability-transport-v1.json"
SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
SDKS = "/Users/andreyyurlov/.swiftpm/swift-sdks"
XENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
JDK = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"
HOST_SCRATCH = "capabilities/.build/guest-transport-host"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def capture(command, environment=None, cwd=ROOT):
    return subprocess.run(command, cwd=cwd, env=os.environ | (environment or {}), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def command(name, arguments, scope, environment=None, cwd=ROOT, expected=0):
    started = now()
    result = capture(arguments, environment, cwd)
    path = LOGS / (name + ".log")
    path.write_bytes(result.stdout)
    record = {"name": name, "command": arguments, "cwd": str(cwd), "environment": environment or {}, "started_at": started, "ended_at": now(), "exit_code": result.returncode, "expected_exit_code": expected, "matched": result.returncode == expected, "output": str(path.relative_to(ROOT)), "output_sha256": sha(result.stdout), "scope": scope}
    print(json.dumps({"command": name, "exit_code": result.returncode, "matched": record["matched"]}), flush=True)
    return record


def frozen_checks():
    paths = ["contracts/guest-capability-transport-v1.json", "verification/guest-capability-contract/cases.json", "capabilities/schema/v1.json", "sdk/Sources/MixerCapabilities/Wire.swift", "sdk/Sources/MixerCapabilities/GeneratedModels.swift", "sdk/Sources/MixerCapabilities/GeneratedHostAdapters.swift", "sdk/Sources/MixerCapabilities/GeneratedGuestAdapters.swift", "capabilities/Probe/main.swift", "capabilities/java/mixer/capabilities/CapabilityModels.java", "capabilities/java/mixer/capabilities/CapabilityCodec.java", "capabilities/java/mixer/capabilities/CapabilityJSON.java", "capabilities/java/mixer/capabilities/CapabilityProbe.java"]
    records = []
    for relative in paths:
        original = capture(["git", "show", FROZEN + ":" + relative])
        assert original.returncode == 0, relative
        actual = (ROOT / relative).read_bytes()
        assert actual == original.stdout, relative
        records.append({"path": relative, "sha256": sha(actual), "matches_frozen_revision": True})
    old_hashes = json.loads(capture(["git", "show", FROZEN + ":capabilities/schema/hashes.json"]).stdout)
    new_hashes = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())
    assert {k: v for k, v in old_hashes.items() if k != "nativeImplementationSHA256"} == {k: v for k, v in new_hashes.items() if k != "nativeImplementationSHA256"}
    assert old_hashes["nativeImplementationSHA256"] != new_hashes["nativeImplementationSHA256"]
    manifest = json.loads((FIXTURES / "cases.json").read_text())
    for case in manifest["cases"]:
        data = (FIXTURES / case["file"]).read_bytes()
        assert sha(data) == case["sha256"] and len(data) == case["bytes"], case["id"]
    return {"revision": FROZEN, "files": records, "frozen_fixture_files": len(manifest["cases"]), "semantic_hashes_unchanged": True, "native_hash_before": old_hashes["nativeImplementationSHA256"], "native_hash_after": new_hashes["nativeImplementationSHA256"]}


def source():
    paths = {CONTRACT, FIXTURES / "cases.json", Path(__file__).resolve(), OUT / "README.md"}
    for folder in (ROOT / "sdk", ROOT / "capabilities"):
        paths.update(p for p in folder.rglob("*") if p.is_file() and not {".build", ".swiftpm", "verification", "__pycache__"}.intersection(p.relative_to(folder).parts))
    manifest = json.loads((FIXTURES / "cases.json").read_text())
    paths.update(FIXTURES / case["file"] for case in manifest["cases"])
    entries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in sorted(paths)]
    return {"algorithm": "SHA256 of canonical sorted path/size/content hash entries", "digest": sha(canonical(entries)), "files": entries}


def actual_native_hash(root, omit_transport=False):
    files = {}
    for folder in (root / "sdk/Sources/MixerCapabilities", root / "capabilities/java/mixer/capabilities"):
        for path in folder.rglob("*"):
            if path.is_file() and path.name not in {"GeneratedIdentity.swift", "CapabilityNativeIdentity.java", "CapabilityProbe.java"}:
                if omit_transport and path.name == "GeneratedGuestTransport.swift":
                    continue
                files[str(path.relative_to(root))] = path.read_bytes()
    files["capabilities/schema/v1.json"] = canonical(json.loads((root / "capabilities/schema/v1.json").read_text()))
    return sha(canonical([{"path": path, "sha256": sha(data)} for path, data in sorted(files.items())]))


def first_generation_identity():
    # Isolated owned-source reproduction: remove the new generated file only in a
    # temporary snapshot, then compare first generation, repeat generation and check.
    with tempfile.TemporaryDirectory(prefix="mixer-guest-codec-generation-") as temporary:
        copy = Path(temporary)
        for relative in ("sdk/Sources/MixerCapabilities", "capabilities/java/mixer/capabilities"):
            shutil.copytree(ROOT / relative, copy / relative)
        for relative in ("capabilities/tools/generate.py", "capabilities/schema/v1.json"):
            (copy / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, copy / relative)
        generated = copy / "sdk/Sources/MixerCapabilities/GeneratedGuestTransport.swift"
        generated.unlink()
        records = [command("generator-first-absent-file", ["python3", str(copy / "capabilities/tools/generate.py")], "First generation with new output absent in private source snapshot", cwd=copy)]
        initial = json.loads((copy / "capabilities/schema/hashes.json").read_text())["nativeImplementationSHA256"]
        assert generated.exists()
        assert initial == actual_native_hash(copy)
        assert initial != actual_native_hash(copy, omit_transport=True)
        before = {str(p.relative_to(copy)): sha(p.read_bytes()) for p in copy.rglob("*") if p.is_file()}
        records.append(command("generator-repeat", ["python3", str(copy / "capabilities/tools/generate.py")], "Repeat generation must preserve every output byte and native identity", cwd=copy))
        after = {str(p.relative_to(copy)): sha(p.read_bytes()) for p in copy.rglob("*") if p.is_file()}
        assert before == after
        records.append(command("generator-copy-check", ["python3", str(copy / "capabilities/tools/generate.py"), "--check"], "Generated output check in private snapshot", cwd=copy))
        current = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())["nativeImplementationSHA256"]
        assert initial == current == actual_native_hash(ROOT)
        return {"commands": records, "first_and_repeat_identical": True, "new_output_included_on_first_generation": True, "native_hash": initial, "hash_with_new_output_omitted": actual_native_hash(copy, omit_transport=True), "private_copy_destroyed_after_run": True}


def fixture_execution(configuration):
    bin_command = ["swift", "build", "--package-path", "capabilities", "--scratch-path", HOST_SCRATCH, "-c", configuration, "--show-bin-path"]
    result = capture(bin_command)
    assert result.returncode == 0
    probe = Path(result.stdout.decode().strip().splitlines()[-1]) / "guest-transport-probe"
    manifest = json.loads((FIXTURES / "cases.json").read_text())
    bindings = {op["swiftCase"]: op for op in manifest["operations"]}
    records = []
    for case in manifest["cases"]:
        raw = (FIXTURES / case["file"]).read_bytes()
        binding = bindings[case["operation"]]
        if case["phase"] in ("arguments", "payload-boundaries"):
            mode, data = "arguments", raw
        elif case["phase"] == "wrappers":
            mode, data = "completion", raw
        elif case["phase"] == "outcomes":
            metadata = {"abi": 1, "capability": binding["capability"], "schemaHash": binding["schemaHash"], "operation": binding["operation"]}
            mode = "completion"
            data = json.dumps(metadata, separators=(",", ":")).encode()[:-1] + b',"outcome":' + raw + b"}"
        else:
            raise ValueError(case["phase"])
        arguments = [str(probe), mode, str(binding["tag"])]
        observed = subprocess.run(arguments, input=data, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        expected_exit = 0 if case["expected"] == "accept" else 1
        matched = observed.returncode == expected_exit
        if observed.returncode == 0:
            # Semantic comparison only after the actual codec accepted input; no
            # reparsing/repair of hostile bytes before they reach its preflight.
            matched = matched and json.loads(observed.stdout) == json.loads(data)
        bounded = len(observed.stdout) <= 524288 and len(observed.stderr) <= 8192
        records.append({"id": case["id"], "phase": case["phase"], "expected": case["expected"], "command": arguments, "fixture_sha256": case["sha256"], "stdin_sha256": sha(data), "stdin_bytes": len(data), "exit_code": observed.returncode, "matched": matched and bounded, "output_bounded": bounded, "stdout_sha256": sha(observed.stdout), "stderr_sha256": sha(observed.stderr), "stdout_utf8": observed.stdout.decode("utf-8"), "stderr_utf8": observed.stderr.decode("utf-8")})
    path = LOGS / ("fixtures-" + configuration + ".jsonl")
    path.write_text("".join(json.dumps(record, ensure_ascii=True) + "\n" for record in records))
    return {"configuration": configuration, "bin_path_command": bin_command, "probe_sha256": sha(probe.read_bytes()), "total": len(records), "matched": sum(record["matched"] for record in records), "mismatches": [record["id"] for record in records if not record["matched"]], "pending": 0, "raw_outputs": str(path.relative_to(ROOT)), "raw_outputs_sha256": sha(path.read_bytes()), "raw_output_encoding": "Each JSONL record preserves exact stdout/stderr bytes as UTF8 strings; decode JSON then encode those fields as UTF8 to reconstruct; bounded per case."}


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    frozen = frozen_checks()
    before = source()
    base = capture(["git", "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = capture(["git", "rev-parse", "HEAD^{tree}"]).stdout.decode().strip()
    commands = [command("generator-check", ["python3", "capabilities/tools/generate.py", "--check"], "Owned generator output/hash drift check")]
    generation = first_generation_identity()
    commands.extend(generation["commands"])
    # Serial operations share host scratch safely; cross targets reuse their
    # existing compatible caches instead of allocating duplicate full build trees.
    for configuration in ("debug", "release"):
        commands.append(command("capability-tests-" + configuration, ["swift", "test", "--package-path", "capabilities", "--scratch-path", HOST_SCRATCH, "-c", configuration, "-Xswiftc", "-warnings-as-errors"], "macOS existing native/codec tests plus new programmatic transport encoder/bounds/routing tests; no devices"))
    fixture_runs = [fixture_execution(configuration) for configuration in ("debug", "release")]
    ios_sdk = capture(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"])
    assert ios_sdk.returncode == 0
    android = [SWIFT, "build", "--package-path", "capabilities", "--swift-sdks-path", SDKS, "--swift-sdk", "aarch64-unknown-linux-android28"]
    jobs = [
        ("ios-cross-build", ["swift", "build", "--package-path", "sdk", "--target", "MixerCapabilities", "--triple", "arm64-apple-ios17.0", "--sdk", ios_sdk.stdout.decode().strip(), "--scratch-path", "capabilities/.build/ios", "-Xswiftc", "-warnings-as-errors"], "iOS arm64 library source cross-compilation only; no signed app/device execution", None),
        ("android-cross-build", android + ["--static-swift-stdlib", "-c", "release", "--product", "guest-transport-probe", "--scratch-path", "capabilities/.build/android", "-Xlinker", "-lssl", "-Xlinker", "-lcrypto", "-Xlinker", "-lz"], "Android aarch64 API28 separate public codec probe static Swift link only; no runtime/device execution", XENV),
        ("wasi-module-build", [SWIFT, "build", "--package-path", "sdk", "--swift-sdks-path", SDKS, "--swift-sdk", "swift-6.3.3-RELEASE_wasm", "--triple", "wasm32-unknown-wasip1", "-c", "release", "--target", "MixerCapabilities", "--scratch-path", "capabilities/.build/wasm"], "Official WASI value module compilation only; no linked guest/import/owned VM execution", XENV),
        ("existing-sdk-tests", ["swift", "test", "--package-path", "sdk"], "Existing Core/UI/Apple host regressions", None),
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        commands.extend(pool.map(lambda job: command(*job), jobs))
    commands.append(command("legacy-public-probe-build", ["swift", "build", "--package-path", "capabilities", "--product", "capability-probe"], "Rebuild unchanged legacy public consumer against additive SDK"))
    java_sources = [str(path.relative_to(ROOT)) for path in sorted((ROOT / "capabilities/java").rglob("*.java"))]
    commands.append(command("legacy-java-build", [JDK + "/bin/javac", "--release", "8", "-Xlint:all,-options", "-Werror", "-d", "capabilities/.build/java"] + java_sources + ["capabilities/Tests/Java/CapabilityCodecTests.java"], "Unchanged Java codec/model plus regenerated native identity compile", {"JAVA_HOME": JDK}))
    commands.append(command("legacy-java-tests", [JDK + "/bin/java", "-cp", "capabilities/.build/java", "mixer.capabilities.CapabilityCodecTests"], "Existing Java codec regression suite"))
    commands.append(command("legacy-codec-differential", ["python3", "capabilities/tools/codec-differential.py"], "Unchanged Swift/Java old-envelope differential: valid/hostile inputs, completion directions and forged owners"))
    after = source()
    tools = []
    for name, args, env in [("swift", ["swift", "--version"], None), ("cross-swift", [SWIFT, "--version"], XENV), ("xcode", ["xcodebuild", "-version"], None), ("python", ["python3", "--version"], None), ("git", ["git", "--version"], None), ("javac", [JDK + "/bin/javac", "-version"], None), ("host", ["uname", "-sm"], None)]:
        tools.append(command("version-" + name, args, "Observed tool/environment version", env))
    receipt = {"schema": 1, "created_at": now(), "source_revision": base, "source_tree": tree, "source": before, "source_unchanged_during_run": before == after, "frozen_contract": {"revision": FROZEN, "path": str(CONTRACT.relative_to(ROOT)), "sha256": sha(CONTRACT.read_bytes()), "status_remains_historical_development_contract": True}, "frozen_preservation": frozen, "generator_first_generation": generation, "commands": commands, "tools": tools, "fixture_runs": fixture_runs, "scope": "Strict standalone Swift value codec and separate public consumer on macOS; iOS/Android/WASI compilation only. Historical contract/projection evidence is unchanged. No native bridge, VM import admission, C ABI, activation, identity-v2, release-v3, full Swift async, physical device, signed app, publication, FieldLog or GA qualification.", "independent_review": False, "phones_disconnected_no_device_commands": True}
    receipt["scoped_checks_passed"] = before == after and all(item["matched"] for item in commands + tools) and all(item["matched"] == 90 and not item["mismatches"] and item["pending"] == 0 for item in fixture_runs)
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"scoped_checks_passed": receipt["scoped_checks_passed"], "source_digest": before["digest"], "fixture_runs": [{key: item[key] for key in ("configuration", "total", "matched", "pending", "mismatches")} for item in fixture_runs]}, indent=2))
    return 0 if receipt["scoped_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
