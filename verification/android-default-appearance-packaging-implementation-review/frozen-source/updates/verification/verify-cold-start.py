#!/usr/bin/env python3
"""Reproduce scoped implementer evidence; this does not qualify device activation."""
import base64
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
OUT = ROOT / "updates/verification/cold-start-store"
ANDROID_SWIFT = "/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
ANDROID_ENV = {"DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
OUT.mkdir(parents=True, exist_ok=True)


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def source():
    files = [ROOT / "contracts/release-v1.json"]
    files += [p for p in (ROOT / "updates").rglob("*") if p.is_file()
              and not {".build", "verification"}.intersection(p.relative_to(ROOT / "updates").parts)]
    entries = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)]
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {"algorithm": "SHA256 of canonical JSON source file entries sorted by path",
            "digest": hashlib.sha256(canonical).hexdigest(), "files": entries}


def capture(command, environment=None):
    return subprocess.run(command, cwd=ROOT, env=os.environ | (environment or {}),
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run(name, command, scope, environment=None):
    started = timestamp()
    result = capture(command, environment)
    log = OUT / (name + ".log")
    log.write_text(result.stdout)
    record = {"name": name, "command": command, "cwd": str(ROOT), "startedAt": started,
              "endedAt": timestamp(), "exitCode": result.returncode, "scope": scope,
              "output": str(log.relative_to(ROOT)), "outputSHA256": hashlib.sha256(log.read_bytes()).hexdigest()}
    if environment:
        record["environment"] = environment
    return record


before = source()
base = capture(["git", "rev-parse", "HEAD"]).stdout.strip()
jobs = [
    ("host-tests", ["swift", "test", "--package-path", "updates"],
     "macOS unit tests, 16 store test functions including 15 interruption cases, plus 12 verifier tests", None),
    ("ios-build", ["swift", "build", "--package-path", "updates", "--target", "MixerUpdates", "--triple",
                   "arm64-apple-ios17.0", "--sdk", "/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.1.sdk",
                   "--scratch-path", "updates/.build/ios"], "unsigned iOS arm64 library cross-compilation only", None),
    ("android-build", [ANDROID_SWIFT, "build", "--package-path", "updates", "--swift-sdks-path",
                       "/Users/andreyyurlov/.swiftpm/swift-sdks", "--swift-sdk", "aarch64-unknown-linux-android28",
                       "--static-swift-stdlib", "-c", "release", "--product", "mixer-update", "--scratch-path", "updates/.build/android"],
     "Android aarch64 API28 release CLI cross-compilation only; store source compiled but not invoked", ANDROID_ENV),
    ("owned-c-shim", ["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-fsyntax-only",
                      "-I", "updates/Sources/MixerDurableIO/include", "updates/Sources/MixerDurableIO/lock.c"],
     "first-party flock shim C11 warnings check", None),
    ("android-test-runner-build", [ANDROID_SWIFT, "build", "--package-path", "updates", "--swift-sdks-path",
                                 "/Users/andreyyurlov/.swiftpm/swift-sdks", "--swift-sdk", "aarch64-unknown-linux-android28",
                                 "-c", "release", "--build-tests", "-Xswiftc", "-enable-testing", "--scratch-path", "updates/.build/android-tests"],
     "Android dynamic-Swift Testing executable cross-compilation only; not run on a device", ANDROID_ENV),
]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    commands = list(executor.map(lambda job: run(*job), jobs))

fixture = json.loads((ROOT / "updates/Tests/MixerUpdatesTests/Fixtures/signed-release-v1.json").read_text())
inputs = ROOT / "updates/.build/cold-start-inputs"
inputs.mkdir(parents=True, exist_ok=True)
for name, value in [("manifest", fixture["signed_manifest"]), ("assignment", fixture["signed_assignment"]),
                    ("host", fixture["host"]), ("roots", fixture["roots"])]:
    (inputs / (name + ".json")).write_text(json.dumps(value, separators=(",", ":")))
(inputs / "payload.fixture").write_bytes(base64.b64decode(fixture["payload"]))
cli = ["swift", "run", "--package-path", "updates", "-c", "release", "mixer-update", "verify"]
for flag, file in [("manifest", "manifest.json"), ("payload", "payload.fixture"), ("host", "host.json"),
                   ("roots", "roots.json"), ("assignment", "assignment.json")]:
    cli += ["--" + flag, str((inputs / file).relative_to(ROOT))]
cli += ["--channel", "beta", "--installation", fixture["installation"], "--last-sequence", str(fixture["last_sequence"]),
        "--now", str(fixture["verification_time_unix"])]
commands.append(run("cli-vector", cli, "host release CLI exact Go protocol vector, explicit no execution/activation flags"))
text = (OUT / "cli-vector.log").read_text()
try:
    report = json.loads(text[text.index("{"):])
except (ValueError, json.JSONDecodeError):
    report = {}
assertions = {"artifactIdentity": report.get("artifactSHA256") == fixture["artifact_sha256"],
              "sequence": report.get("assignmentSequence") == 7, "cohort": report.get("cohortBucket") == fixture["cohort_bucket"],
              "noVMClaim": report.get("executableProfileVerified") is False, "noActivation": report.get("activated") is False,
              "noPolicyClaim": report.get("policyApproved") is False}
after = source()
receipt = {
    "schemaVersion": 1, "createdAt": timestamp(), "repositoryHeadAtRun": base,
    "verifierReviewCommit": "1cea2c2fcf7bd8b3bd2f3d25bda1e24631d32a8e",
    "implementer": {"model": "gpt-6.1-sol", "reasoningEffort": "xhigh", "independentReview": False},
    "source": before, "sourceUnchangedDuringRun": before == after,
    "environment": {"host": platform.platform(), "swift": capture(["swift", "--version"]).stdout.strip(),
                    "xcode": capture(["xcodebuild", "-version"]).stdout.strip(),
                    "androidSwift": capture([ANDROID_SWIFT, "--version"], ANDROID_ENV).stdout.strip(),
                    "androidManifestHostXcode": capture(["xcodebuild", "-version"], ANDROID_ENV).stdout.strip(),
                    "clang": capture(["clang", "--version"]).stdout.strip(), "python": sys.version},
    "commands": commands, "cliAssertions": assertions,
    "storeCoverage": ["sequence-before-download, cancellation and replay after interruption",
                      "bounded exact-offset resumed chunks, SHA-256 and mandatory host policy before staging",
                      "five journal and five payload write/sync/rename fault boundaries",
                      "five interrupted healthy-journal cases, commit uncertainty and required reopen",
                      "process-local monotonic observation, backward clock, wall jumps and milestones",
                      "deterministic trap quarantine versus unknown kill/native crash/user quit",
                      "immutable Data selection despite cache mutation and later health refusal",
                      "missing/corrupt/symlink cached files and two-generation/native fallback",
                      "healthy offline retained-key signatures versus current staged/new signing authority",
                      "disk reserve, exclusive lock, bounded metadata/history, orphan pruning and missing replay journal"],
    "resolvedIntegrationIssues": ["Android provides the Android C module instead of Glibc; platform-specific import/descriptor wrappers added",
                                  "Darwin flock name collides with imported struct; minimal owned C wrapper used",
                                  "Android SDK Testing is dynamic only; test runner uses dynamic Swift and explicit release -enable-testing"],
    "persistsSignedSequence": True, "selectsImmutableVerifiedBytes": True, "executesGuest": False,
    "authorizesOTAByItself": False, "privateSigningMaterialPersisted": False,
    "unqualified": ["independent review of this durable-store implementation", "physical iOS/Android cold-start integration of this tree",
                    "physical power-loss/filesystem recovery", "actual owned Swift/Wasm executable validator and guest activation integration",
                    "malicious local metadata/backup rollback resistance or secure hardware counter", "automatic journal/app-data migration",
                    "background/network transfer and operational key-rotation qualification", "external security/cryptographic audit and continuous fuzzing",
                    "immutable published-package FieldLog release and GA acceptance"],
}
receipt["scopedChecksPassed"] = before == after and all(c["exitCode"] == 0 for c in commands) and all(assertions.values())
(ROOT / "updates/verification/cold-start-store.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"sourceDigest": before["digest"], "checksPassed": receipt["scopedChecksPassed"],
                  "commands": [{"name": c["name"], "exitCode": c["exitCode"]} for c in commands]}, indent=2))
sys.exit(0 if receipt["scopedChecksPassed"] else 1)
