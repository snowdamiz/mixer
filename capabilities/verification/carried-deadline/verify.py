#!/usr/bin/env python3
"""Scoped implementer evidence; no native bridge, device or release qualification."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
SDKS = "/Users/andreyyurlov/.swiftpm/swift-sdks"
XENV = {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}
AENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
JDK = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"
OWNED = {
    "sdk/Sources/MixerCapabilities/Host.swift",
    "sdk/Sources/MixerCapabilities/GeneratedIdentity.swift",
    "capabilities/java/mixer/capabilities/CapabilityNativeIdentity.java",
    "capabilities/schema/hashes.json",
    "capabilities/Tests/MixerCapabilitiesTests/CarriedDeadlineTests.swift",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def files():
    result = {}
    for folder in ["sdk", "capabilities", "contracts"]:
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and not {".build", ".swiftpm", "verification", "__pycache__"}.intersection(path.relative_to(ROOT / folder).parts):
                result[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    return dict(sorted(result.items()))


def run(name, argv, scope="", environment=None):
    started = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=os.environ | (environment or XENV), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    path = OUT / (name + ".log")
    if path.exists() and path.read_bytes() != result.stdout:
        suffix = 1
        while path.with_name(path.stem + ".previous-" + str(suffix) + ".log").exists():
            suffix += 1
        path.rename(path.with_name(path.stem + ".previous-" + str(suffix) + ".log"))
    path.write_bytes(result.stdout)
    record = {"name": name, "command": argv, "cwd": str(ROOT), "environment": environment or XENV,
              "exitCode": result.returncode, "elapsedSeconds": round(time.monotonic() - started, 3),
              "output": str(path.relative_to(ROOT)), "outputSHA256": sha(result.stdout), "scope": scope}
    print(name + ": exit " + str(result.returncode), flush=True)
    return record


receipt_path = OUT / "receipt.json"
if receipt_path.exists():
    suffix = 1
    while (OUT / ("receipt.previous-" + str(suffix) + ".json")).exists():
        suffix += 1
    receipt_path.rename(OUT / ("receipt.previous-" + str(suffix) + ".json"))

base = git("rev-parse", "HEAD").decode().strip()
baseline = files()
semantic_before = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())
commands = [run("identity-generation", ["python3", "-B", "capabilities/tools/generate.py"], "Regenerate only native identity outputs; every codec and contract byte checked unchanged")]
after_generation = files()
changed = sorted(p for p in baseline if baseline[p] != after_generation[p])
assert set(changed).issubset(OWNED), changed
assert set(baseline) == set(after_generation)
semantic_after = json.loads((ROOT / "capabilities/schema/hashes.json").read_text())
for field in ["capabilities", "contractSHA256"]:
    assert semantic_before[field] == semantic_after[field], field
source = after_generation
manifest = "".join(digest + "  " + name + "\n" for name, digest in source.items())
(OUT / "source-manifest.sha256").write_text(manifest)
receipt = {"schemaVersion": 1, "status": "running", "startedAt": now(), "repositoryHeadAtRun": base,
           "sourceManifestSHA256": sha(manifest.encode()), "source": source,
           "nativeIdentityBefore": semantic_before["nativeImplementationSHA256"],
           "nativeIdentityAfter": semantic_after["nativeImplementationSHA256"],
           "nativeIdentityAtBase": json.loads(git("show", base + ":capabilities/schema/hashes.json"))["nativeImplementationSHA256"],
           "semanticHashesUnchanged": True, "generatorChangedPaths": changed,
           "preservedFromBase": {}, "commands": commands,
           "implementerEvidenceOnly": True, "independentReview": False,
           "scope": "SDK absolute deadline propagation for observed concrete installed adapters; host runtime tests, native TSan, iOS/Android/WASI compilation only. No guest bridge, C, VM, registry, executor, activation, identity-v2, release-v3, publication, device or GA qualification.",
           "limitations": ["Public tests use bounded test-only isolated storage actor and delivery gates; production clocks/adapters are unchanged", "No claim of durable-effect rollback or no side effects if a task suspends after the pre-invoke check", "System frameworks are not sanitizer-instrumented", "Phones disconnected; no physical-device commands"],
           "driverSHA256": sha(Path(__file__).read_bytes())}
for path, digest in source.items():
    if path not in OWNED:
        try:
            old = git("show", base + ":" + path)
        except subprocess.CalledProcessError:
            continue
        assert sha(old) == digest, path + " changed outside owned scope"
        receipt["preservedFromBase"][path] = digest


def save():
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")


save()
for name, argv, env in [
    ("swift-version", ["swift", "--version"], XENV),
    ("xcode-version", ["xcodebuild", "-version"], XENV),
    ("official-swift-version", [SWIFT, "--version"], AENV),
    ("android-manifest-xcode-version", ["xcodebuild", "-version"], AENV),
    ("host-version", ["uname", "-a"], XENV),
    ("python-version", ["python3", "--version"], XENV),
]:
    commands.append(run(name, argv, environment=env)); save()
commands.append(run("generator-check", ["python3", "-B", "capabilities/tools/generate.py", "--check"], "Generated output drift check")); save()
android = [SWIFT, "build", "--package-path", "capabilities", "--swift-sdks-path", SDKS, "--swift-sdk", "aarch64-unknown-linux-android28"]
jobs = [
    ("capability-debug", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-debug", "-Xswiftc", "-warnings-as-errors"], "Full capability suite with six public carried-deadline regressions", XENV),
    ("capability-release", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-release", "-c", "release", "-Xswiftc", "-warnings-as-errors"], "Full capability suite under optimization", XENV),
    ("native-deadline-tsan", ["swift", "test", "--package-path", "capabilities", "--scratch-path", "capabilities/.build/exit-tsan", "--sanitize", "thread", "--filter", "NativeCapabilityExitTests|NativeHTTPTransportTests|CapabilityHostDeadlineTests|CapabilityCarriedDeadlineTests"], "Owned native HTTP, exit join and both deadline suites under Thread Sanitizer", XENV),
    ("ios-cross-build", ["swift", "build", "--package-path", "sdk", "--target", "MixerCapabilities", "--triple", "arm64-apple-ios17.0", "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk", "--scratch-path", "capabilities/.build/ios", "-Xswiftc", "-warnings-as-errors"], "iOS arm64 library compilation only", XENV),
    ("android-cross-build", android + ["--static-swift-stdlib", "-c", "release", "--product", "guest-transport-probe", "--scratch-path", "capabilities/.build/android", "-Xlinker", "-lssl", "-Xlinker", "-lcrypto", "-Xlinker", "-lz"], "Official Android aarch64 API28 static Swift public codec probe link only", AENV),
    ("wasi-module-build", [SWIFT, "build", "--package-path", "sdk", "--swift-sdks-path", SDKS, "--swift-sdk", "swift-6.3.3-RELEASE_wasm", "--triple", "wasm32-unknown-wasip1", "-c", "release", "--target", "MixerCapabilities", "--scratch-path", "capabilities/.build/wasm"], "Official WASI module compilation; observed installed adapter overload is native-only", AENV),
    ("java-identity-build", [JDK + "/bin/javac", "--release", "8", "-Xlint:all,-options", "-Werror", "-d", "capabilities/.build/java"] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "capabilities/java").rglob("*.java"))] + ["capabilities/Tests/Java/CapabilityCodecTests.java"], "Java codec sources and regenerated native identity compile", {"JAVA_HOME": JDK, "PATH": JDK + "/bin:" + os.environ["PATH"]}),
]
with ThreadPoolExecutor(max_workers=3) as executor:
    for result in executor.map(lambda job: run(*job), jobs):
        commands.append(result); save()
receipt["sourceUnchangedDuringRun"] = files() == source
assert receipt["sourceUnchangedDuringRun"]
for record in commands:
    if record["name"] in ["capability-debug", "capability-release", "native-deadline-tsan"] and record["exitCode"] == 0:
        output = (ROOT / record["output"]).read_text()
        matches = re.findall(r"Test run with (\d+) tests in \d+ suites passed", output)
        assert len(matches) == 1, record["name"]
        record["passedTests"] = int(matches[0])
receipt["completedAt"] = now()
receipt["status"] = "scoped_checks_passed" if all(c["exitCode"] == 0 for c in commands) else "failed_check_preserved"
save()
if receipt["status"] != "scoped_checks_passed":
    raise SystemExit(1)
