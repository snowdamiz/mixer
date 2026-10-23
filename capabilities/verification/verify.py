#!/usr/bin/env python3
"""Implementer evidence only; no package/device/VM/OTA acceptance is inferred."""
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "capabilities/verification/logs"
OUT.mkdir(parents=True, exist_ok=True)
JDK = "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"
SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
SDK_PATH = "/Users/andreyyurlov/.swiftpm/swift-sdks"
ANDROID_ENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
JAVA_ENV = {"JAVA_HOME": JDK, "PATH": JDK + "/bin:" + os.environ["PATH"]}
ANDROID_JAR = "/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar"
D8 = "/opt/homebrew/share/android-commandlinetools/build-tools/37.0.0/d8"


def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()


def capture(args, environment=None):
    return subprocess.run(args, cwd=ROOT, env=os.environ | (environment or {}), text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run(name, args, scope, environment=None):
    started = now(); result = capture(args, environment)
    path = OUT / (name + ".log"); path.write_text(result.stdout)
    record = dict(name=name, command=args, cwd=str(ROOT), startedAt=started, endedAt=now(), exitCode=result.returncode,
                  output=str(path.relative_to(ROOT)), outputSHA256=hashlib.sha256(path.read_bytes()).hexdigest(), scope=scope)
    if environment: record["environment"] = environment
    return record


def source():
    files = []
    for folder in [ROOT / "sdk", ROOT / "capabilities"]:
        files += [p for p in folder.rglob("*") if p.is_file() and not {".build", ".swiftpm", "verification", "__pycache__"}.intersection(p.relative_to(folder).parts)]
    entries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
    data = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return dict(algorithm="SHA256 of canonical JSON source entries sorted by path; SDK and capabilities excluding build/verification artifacts", digest=hashlib.sha256(data).hexdigest(), files=entries)


before = source(); base = capture(["git", "rev-parse", "HEAD"]).stdout.strip()
commands = [run("generated-check", ["python3", "capabilities/tools/generate.py", "--check"], "closed-schema generated DTO, host/guest adapter and native identity drift check")]
android = [SWIFT, "build", "--package-path", "capabilities", "--swift-sdks-path", SDK_PATH, "--swift-sdk", "aarch64-unknown-linux-android28"]
jobs = [
    ("capability-tests", ["swift", "test", "--package-path", "capabilities"], "12 macOS host typed lifecycle/storage tests; fixture HTTP transport only", None),
    ("existing-sdk-tests", ["swift", "test", "--package-path", "sdk"], "23 existing Core/UI/Apple tests preserved on macOS", None),
    ("ios-build", ["swift", "build", "--package-path", "sdk", "--target", "MixerCapabilities", "--triple", "arm64-apple-ios17.0", "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk", "--scratch-path", "capabilities/.build/ios"], "iOS arm64 native capability library cross-compilation only", None),
    ("android-build", android + ["--static-swift-stdlib", "-c", "release", "--product", "capability-probe", "--scratch-path", "capabilities/.build/android"], "Android aarch64 API28 static Swift codec probe cross-compilation only", ANDROID_ENV),
    ("android-test-build", android + ["-c", "release", "--build-tests", "-Xswiftc", "-enable-testing", "--scratch-path", "capabilities/.build/android-tests"], "Android dynamic Swift Testing runner cross-compilation only", ANDROID_ENV),
    ("wasi-module-build", [SWIFT, "build", "--package-path", "sdk", "--swift-sdks-path", SDK_PATH, "--swift-sdk", "swift-6.3.3-RELEASE_wasm", "--triple", "wasm32-unknown-wasip1", "-c", "release", "--target", "MixerCapabilities", "--scratch-path", "capabilities/.build/wasm"], "official WASI target module compilation; no linked/validated/executed owned-VM guest", ANDROID_ENV),
    ("java-build", [JDK + "/bin/javac", "--release", "8", "-Xlint:all,-options", "-Werror", "-d", "capabilities/.build/java"] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "capabilities/java").rglob("*.java"))] + ["capabilities/Tests/Java/CapabilityCodecTests.java"], "Java8 typed codec classfiles; suppress only JDK25 obsolete-target option warning", JAVA_ENV),
    ("c-shim", ["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-I", "sdk/Sources/MixerCapabilities/NativeIO/include", "sdk/Sources/MixerCapabilities/NativeIO/lock.c"], "owned flock C11 warnings check", None),
]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    commands += list(executor.map(lambda job: run(*job), jobs))
commands += [run("java-tests", [JDK + "/bin/java", "-cp", "capabilities/.build/java", "mixer.capabilities.CapabilityCodecTests"], "20 Java value/snapshot/ownership/failure regressions", JAVA_ENV),
             run("codec-differential", ["python3", "capabilities/tools/codec-differential.py"], "24 valid and 66 hostile inbound; 38 completion directions; 4 forged completion cases")]
dex = ROOT / "capabilities/.build/dex"; dex.mkdir(parents=True, exist_ok=True)
commands += [run("android-dex-build", [D8, "--min-api", "28", "--lib", ANDROID_JAR, "--output", str(dex.relative_to(ROOT))] + [str(p.relative_to(ROOT)) for p in sorted((ROOT / "capabilities/.build/java").rglob("*.class"))], "official D8 API28 conversion only; no Android runtime/JNI execution", JAVA_ENV)]
after = source()
receipt = dict(schemaVersion=1, createdAt=now(), repositoryHeadAtRun=base,
    implementer=dict(model="gpt-6.1-sol", reasoningEffort="xhigh", independentReview=False), source=before,
    sourceUnchangedDuringRun=before == after, commands=commands, devicePolicy="New physical checks pending: phones disconnected per user instruction; no device runs attempted",
    environment=dict(host=platform.platform(), python=sys.version, swift=capture(["swift", "--version"]).stdout.strip(),
        xcode=capture(["xcodebuild", "-version"]).stdout.strip(), androidSwift=capture([SWIFT, "--version"], ANDROID_ENV).stdout.strip(),
        androidManifestHostXcode=capture(["xcodebuild", "-version"], ANDROID_ENV).stdout.strip(), javac=capture([JDK+"/bin/javac", "-version"]).stdout.strip(), d8=capture([D8,"--version"], JAVA_ENV).stdout.strip()),
    contracts=json.loads((ROOT / "capabilities/schema/hashes.json").read_text()),
    findings=[dict(id="CAP-IMPL-01", status="fixed before initial commit", severity="P1",
        description="Direct logical ASCII namespace/key filenames aliased case-distinct grant identities on case-insensitive filesystems",
        initialCommand=["swift", "test", "--package-path", "capabilities", "--filter", "privateStorageIdentityCannotAliasOnCaseInsensitiveFilesystems"],
        initialExitCode=1, initialOutput="capabilities/verification/logs/initial-case-alias-regression.log",
        preFixNativeImplementationSHA256="0cbc39dcb8edc1d5796501121f8209b93c954ddbe279e6c5dfb074bdea3403ca",
        fix="Canonical lowercase base32 physical components of exact ASCII bytes, strict reverse inventory validation, and namespace/key case isolation regression")],
    assertions=dict(typedClosedDispatch=True, rawDecodesSnapshotAndPreflight=True, noReflectiveNativeLookup=True,
        noNativePointersInWire=True, manifestGrantsCannotExpandInstalledPolicy=True, generationWrapRetires=True,
        oneTerminalResponsePerSubmittedCall=True, cancellationKeepsLeaseUntilAdapterExit=True, storageAtomicQuotaBounded=True,
        bundledProductionHTTPAdapter=False, linkedGuestValidatedInOwnedVM=False, guestExecuted=False, deviceReceipt=False,
        privateCredentialsUsed=False, thirdPartyEngineUsed=False, W06Accepted=False),
    unqualified=["independent adversarial review", "signed manifest grant contract/verifier integration (release-v1 currently carries capability hashes only)",
        "complete installed native fingerprint/permissions/configuration and custom adapter identity integration", "real bounded OS HTTP/TLS adapter including credential/redirect policy",
        "actual guest reserve/invoke/cancel imports, owned-VM execution and JNI transport", "physical iOS/Android lifecycle/permission and minimum-OS matrix",
        "physical storage power-loss, fault injection and storage migrations/database/files/secrets families", "all other Section9 capability families and plugin publication trust workflow",
        "immutable published-package FieldLog plugin consumption", "external security review, operational observability/runbooks, W06/W09/GA"])
receipt["scopedChecksPassed"] = before == after and all(c["exitCode"] == 0 for c in commands)
(ROOT / "capabilities/verification/receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(dict(sourceDigest=before["digest"], checksPassed=receipt["scopedChecksPassed"], commands=[dict(name=c["name"],exitCode=c["exitCode"]) for c in commands]), indent=2))
sys.exit(0 if receipt["scopedChecksPassed"] else 1)
