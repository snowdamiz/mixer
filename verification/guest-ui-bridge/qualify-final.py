#!/usr/bin/env python3
"""Qualify frozen SDK4/bridge with one native-only archive and reused graphs."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "experimental-capability-runtime"
STAGE = PACKAGE / "build-verification/local/guest-ui-1adb25c-v2"
ARCHIVE = STAGE / "host/lib/libmixer_vm_capability_experimental.a"
ARCHIVE_SHA = "4d3b6dc36ea034d5604299752d560cbbc0615002b6b5ef4e5c25bbb3cb7c6120"
PIN = "1adb25c48a8723f56ed2649712fe5e357920c53e"
SDK_RECEIPT = ROOT / "verification/guest-ui-sdk/2026-10-23-candidate-4/receipt.json"
SDK_RECEIPT_SHA = "f336e0a822579af8b8e24a08a62323583d4d633051321107430a177adbb60f5b"
NATIVE_RECEIPT = ROOT / "verification/guest-ui-native-package/2026-10-23-native-2/receipt.json"
NATIVE_RECEIPT_SHA = "6e6c64ce24406fccc6842b3a9437557d4f045bbeaab3cb6e2f63dd18cd0a6eaa"
ENV = {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def source_inputs():
    files = [PACKAGE / "Package.swift", ROOT / "sdk/Package.swift", Path(__file__),
             PACKAGE / "verification/with-loopback.py", PACKAGE / "verification/verify.py",
             ROOT / "contracts/guest-ui-event-v1.json", ROOT / "docs/guest-ui-event-integration-design.md"]
    for folder in [PACKAGE / "Sources", PACKAGE / "Tests", ROOT / "sdk/Sources", ROOT / "sdk/Tests"]:
        files.extend(p for p in folder.rglob("*") if p.is_file() and p.name != ".DS_Store")
    files.extend((ROOT / "vm/include").glob("*.h"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(files))}

def native_inputs():
    return {str(p.relative_to(ROOT)): sha(p) for target in ["host", "ios", "ios-simulator", "android"]
            for p in [STAGE / target / "receipt.json", STAGE / target / "lib/libmixer_vm_capability_experimental.a",
                      *sorted((STAGE / target / "include").glob("*.h"))]}

name = sys.argv[1] if len(sys.argv) == 2 else ""
require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name) is not None, "one fresh evidence name required")
OUT = Path(__file__).resolve().parent / name
OUT.mkdir(exist_ok=False)
require(sha(SDK_RECEIPT) == SDK_RECEIPT_SHA, "SDK4 receipt differs from root seal")
require(sha(NATIVE_RECEIPT) == NATIVE_RECEIPT_SHA, "native2 receipt differs from root seal")
require(sha(ARCHIVE) == ARCHIVE_SHA, "wrong selected native host archive")
sdk = json.loads(SDK_RECEIPT.read_text())
require(all(sha(ROOT / p) == digest for p, digest in sdk["source_files"].items()), "SDK4 source tuple changed")
for target in ["host", "ios", "ios-simulator", "android"]:
    native = json.loads((STAGE / target / "receipt.json").read_text())
    require(native["source_revision"] == PIN, "native source pin mismatch")
    require(native["features"] == ["experimental-capability-mailbox", "experimental-capability-guest", "experimental-capability-native"], "native feature set mismatch")
    require(len(native["public_C_symbols"]) == 28 and native["public_C_symbols"].count("mixer_vm_capability_guest_ui_validate_v1") == 1, "native public symbol inventory mismatch")
sources = source_inputs()
artifacts = native_inputs()
manifest = "".join(digest + "  " + path + "\n" for path, digest in sources.items())
(OUT / "source-manifest.sha256").write_text(manifest)
receipt = {
    "status": "running", "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevisionAtStart": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "source": sources, "sourceManifestSHA256": hashlib.sha256(manifest.encode()).hexdigest(),
    "SDK4Receipt": {"path": str(SDK_RECEIPT.relative_to(ROOT)), "sha256": SDK_RECEIPT_SHA},
    "native2Receipt": {"path": str(NATIVE_RECEIPT.relative_to(ROOT)), "sha256": NATIVE_RECEIPT_SHA},
    "nativeRevision": PIN, "selectedNativeHostArchive": {"path": str(ARCHIVE), "sha256": ARCHIVE_SHA},
    "nativeArtifacts": artifacts, "commands": [], "hostLinks": [], "reusedPlatformEvidence": [],
    "scope": "Frozen SDK4 plus bridge against native-only immutable pin; full Debug/Release/Swift-TSan48 suites including actual normal-trust local TLS rejection; existing scratch graphs reused.",
    "limitations": [
        "Implementer Mac verification; no devices, physical execution, renderer, full Swift guest, signing/store/publication/dogfood or GA claim.",
        "Rust archive and system frameworks are not Swift TSan instrumented; no exhaustive race, hard memory or hard latency guarantee.",
        "Platform evidence is composed from previous bridge compile-only checks plus SDK4 portable module checks; this run adds no final iOS/Android native archive consumer link or execution claim.",
        "Loopback test proves normal trust rejects the ephemeral self-signed certificate; no trust/keychain/credential mutation, HTTPS success or external service claim.",
        "Apple Swift6.4/Xcode27.1 host tools are recorded separately from official Swift6.3.3 Android module tools; pinnedCI qualification is separate.",
        "Already admitted effects may commit after stop; no rollback assertion."
    ]
}

def save():
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

def run(label, argv, scope):
    began = time.monotonic()
    log = OUT / (label + ".log")
    with log.open("w") as stream:
        result = subprocess.run(argv, cwd=ROOT, env=os.environ | ENV, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
    text = log.read_text()
    command = {"name": label, "argv": argv, "cwd": str(ROOT), "environment": ENV,
               "exitCode": result.returncode, "elapsedSeconds": time.monotonic() - began,
               "log": log.name, "logSHA256": sha(log), "scope": scope}
    counts = re.findall(r"Test run with (\d+) tests? in \d+ suites? passed", text)
    if counts:
        command["passedTests"] = [int(v) for v in counts]
    receipt["commands"].append(command)
    save()
    print(label + ": exit" + str(result.returncode) + " tests=" + str(command.get("passedTests", [])), flush=True)
    return command

def link_evidence(mode):
    graph = PACKAGE / ".build" / ("guest-ui-" + mode)
    manifests = graph / "out/Intermediates.noindex/XCBuildData"
    manifest = max(manifests.glob("*.xcbuilddata/manifest.json"), key=lambda p: p.stat().st_mtime)
    matches = [v for v in json.loads(manifest.read_text())["commands"].values()
               if v.get("description", "").startswith("Ld ") and "MixerExperimentalCapabilityRuntimeTests.xctest/Contents/MacOS/" in v.get("description", "")]
    require(len(matches) == 1, "expected one actual host test binary linker command")
    link = matches[0]
    argv = link["args"]
    candidates = sorted({(Path(a[2:]) / ARCHIVE.name).resolve() for a in argv
                         if a.startswith("-L") and (Path(a[2:]) / ARCHIVE.name).exists()})
    require(candidates == [ARCHIVE.resolve()], "link can resolve another native archive")
    native_flags = [a for a in argv if "mixer_vm" in a and (a.startswith("-l") or a.endswith(".a"))]
    require(native_flags == ["-lmixer_vm_capability_experimental"], "unexpected mixer native library link flags")
    binary = Path(argv[argv.index("-o") + 1])
    command = run(mode + "-native-symbols", ["nm", "-g", str(binary)], "Inspect actual linked host test binary public native symbol definitions")
    lines = (OUT / command["log"]).read_text().splitlines()
    definitions = [line for line in lines if " T _mixer_vm_" in line]
    ui_count = sum(line.endswith(" _mixer_vm_capability_guest_ui_validate_v1") for line in definitions)
    require(ui_count == 1, "UI validator must have exactly one definition")
    return {"mode": mode, "manifest": str(manifest), "manifestSHA256": sha(manifest),
            "linkCommand": argv, "workingDirectory": link.get("working-directory"),
            "resolvedNativeArchive": str(candidates[0]), "resolvedNativeArchiveSHA256": sha(candidates[0]),
            "onlySelectedNativeLibrary": True, "nativeLibraryFlags": native_flags,
            "binary": str(binary), "binarySHA256": sha(binary), "uiValidatorDefinitionCount": ui_count,
            "definedNativeSymbols": definitions, "symbolCommand": command["name"]}

save()
try:
    for label, argv in [("swift-version", ["swift", "--version"]), ("xcode-version", ["xcodebuild", "-version"]),
                        ("clang-version", ["clang", "--version"]), ("python-version", [sys.executable, "--version"]),
                        ("openssl-version", ["openssl", "version"]), ("disk-before", ["df", "-h", "/System/Volumes/Data"])]:
        require(run(label, argv, "Host tool or capacity observation")["exitCode"] == 0, "tool observation failed")
    for mode, extra in [("debug", []), ("release", ["-c", "release"]), ("tsan", ["--sanitize", "thread"])]:
        scratch = PACKAGE / ".build" / ("guest-ui-" + mode)
        require(scratch.exists(), "refuse a fresh giant scratch graph")
        swift = ["swift", "test", "--package-path", str(PACKAGE), "--scratch-path", str(scratch)] + extra
        swift += ["-Xcc", "-I" + str(STAGE / "host/include"), "-Xlinker", "-L" + str(STAGE / "host/lib"),
                  "-Xswiftc", "-warnings-as-errors", "-Xswiftc", "-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST"]
        command = run(mode + "-full-TLS", [sys.executable, "-B", str(PACKAGE / "verification/with-loopback.py"),
                       "--output", str(OUT / (mode + "-loopback")), "--"] + swift,
                      "Full48 current bridge tests including fixed UI and actual normal-trust loopback TLS rejection")
        command["expectedTests"] = 48
        command["testCountsMatch"] = command.get("passedTests") == [48]
        tls_path = OUT / (mode + "-loopback/receipt.json")
        tls = json.loads(tls_path.read_text())
        command["loopbackReceipt"] = {"path": str(tls_path.relative_to(OUT)), "sha256": sha(tls_path),
                                       "observations": tls["observations"], "serverStopped": tls["server_stopped"]}
        save()
        require(command["exitCode"] == 0 and command["testCountsMatch"] and tls["server_stopped"] and tls["observations"]["application_requests"] == 0,
                "full TLS suite failed; preserve output")
        receipt["hostLinks"].append(link_evidence(mode))
        save()
    for target in ["ios", "android"]:
        old_path = Path(__file__).resolve().parent / (target + "-handoff.json")
        old = json.loads(old_path.read_text())
        changed = [p for p, digest in old["sourceSHA256After"].items() if sha(ROOT / p) != digest]
        require(changed == ["sdk/Sources/MixerGuest/GuestUIExchangeV1.swift"], "platform reuse changed beyond portable SDK4 exchange")
        sdk_checks = [c for c in sdk["commands"] if c["name"].startswith(target + "-Mixer")]
        require(len(sdk_checks) == 3 and all(c["exit_code"] == 0 for c in sdk_checks), "SDK4 mobile module evidence incomplete")
        receipt["reusedPlatformEvidence"].append({"target": target, "priorBridgeReceipt": str(old_path.relative_to(ROOT)),
            "priorBridgeReceiptSHA256": sha(old_path), "changedSourcePaths": changed,
            "SDK4ModuleCheckNames": [c["name"] for c in sdk_checks],
            "claim": "Unchanged bridge module compiled previously; sole changed portable exchange source is covered by SDK4 target module checks. No new final native cross-platform link or execution."})
    require(run("disk-after", ["df", "-h", "/System/Volumes/Data"], "Capacity observation after reusing three graphs")["exitCode"] == 0, "capacity observation failed")
    receipt["sourcesUnchanged"] = source_inputs() == sources
    receipt["nativeArtifactsUnchanged"] = native_inputs() == artifacts
    receipt["SDK4SourceTupleStillExact"] = all(sha(ROOT / p) == digest for p, digest in sdk["source_files"].items())
    require(receipt["sourcesUnchanged"] and receipt["nativeArtifactsUnchanged"] and receipt["SDK4SourceTupleStillExact"], "source or native input changed")
    receipt["status"] = "full48-Debug-Release-SwiftTSan-and-normal-trust-TLS-passed"
except Exception as error:
    receipt["status"] = "failed-preserved"
    receipt["failure"] = str(error)
    raise
finally:
    receipt["completedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    print("receipt " + str(OUT / "receipt.json") + " sha256=" + sha(OUT / "receipt.json"), flush=True)
