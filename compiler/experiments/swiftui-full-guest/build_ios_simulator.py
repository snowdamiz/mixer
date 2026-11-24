#!/usr/bin/env python3
"""Build and check the matched S2a offscreen Simulator comparator."""

import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

PIN = "1ee170500c73e3da935e1d1cbb4bbba77d24e8d8"
S2B_PIN = "22db0ade934c383c6ca154830568388d844ac26b"
VM_TREE = "d3f0d6c10bf38c46299314a5aff319f18785dc2c"
PAYLOAD = {
    "reactor-base.wasm": (12718666, "02ae07b9d4d89f4715ba5438b56be4e25b308725fb9cbb1a509686097d642be6"),
    "oracle.json": (2104, "091333b185cfeca819ae5117876c8f1c60ddc1c3bdd355118c1a786c034cb1a1"),
}
TARGET = "aarch64-apple-ios-sim"
MIN_OS = "17.0"
APP_NAME = "FieldLogS2a"
BUNDLE_ID = "com.mixer.diagnostics.fieldlog-s2a-comparator"
RUST_BIN = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
SWIFTC = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swiftc"
HOST_XCODE = Path("/Applications/Xcode_26.6.app/Contents/Developer")
XCRUN = "/usr/bin/xcrun"
TURNS = ["first_snapshot", "load", "open", "blank_save", "save", "reopen"]
STAGES = {
    "fixed34": ["baseline", "read", "validation_refused", "pre_exit"],
    "ui256": ["baseline", "read", "validate", "construct", *TURNS, "steady", "consume", "pre_exit"],
    "native": ["baseline", *TURNS, "steady", "pre_exit"],
}


def fingerprint(path):
    return {"bytes": path.stat().st_size, "sha256": digest(path)}


def verify_payload(directory):
    for name, (size, sha256) in PAYLOAD.items():
        if fingerprint(directory / name) != {"bytes": size, "sha256": sha256}:
            raise ValueError(f"{name} differs from the exact S2b payload")
    oracle = strict_json((directory / "oracle.json").read_bytes())
    if not isinstance(oracle, list) or len(oracle) != 6:
        raise ValueError("Expected six oracle snapshots")
    return oracle


def verify_frames(log, oracle):
    frames = [strict_json(line) for line in log.splitlines() if line.startswith("{")]
    if len(frames) != len(oracle):
        raise ValueError(f"Expected six snapshots, got {len(frames)}")
    for stage, frame, expected in zip(TURNS, frames, oracle):
        if json.dumps(frame, sort_keys=True) != json.dumps(expected, sort_keys=True):
            raise ValueError(f"{stage} differs from the oracle")
    return len(frames)


def verify_fixed_refusal(fixed_code, fixed_log):
    refusal = [line for line in fixed_log.splitlines() if line.startswith("validation=")]
    if (fixed_code != 10 or len(refusal) != 1
            or 'kind: AbiShape, code: "swift_import_count"' not in refusal[0]
            or any(line.startswith(("{", "clean=", "step=")) for line in fixed_log.splitlines())):
        raise ValueError("Fixed-34 control did not refuse 32 imports before acquiring an owner")


def verify_guest_trace(replay_log, failure="None"):
    lines = replay_log.splitlines()
    admission = [line for line in lines if line.startswith("policy=")]
    if (len(admission) != 1 or not admission[0].startswith("policy=swift-6.3.3-wasi-ui-diagnostic-v1;")
            or "imported_functions: 32," not in admission[0]):
        raise ValueError("Missing exact-32 admission observation")
    budgets = [line for line in lines if line.startswith("run_budget=")]
    owner = re.match(r"^run_budget=SwiftRunBudget \{ ([^{}]+) \};", budgets[0]) if len(budgets) == 1 else None
    expected = {"cache_entries": "256", "active_pins": "256", "frames": "256", "deadline_ms": "30000"}
    if not owner or any(
        re.findall(rf"(?:^|, ){name}: (\d+)(?=, |$)", owner[1]) != [value]
        for name, value in expected.items()
    ):
        raise ValueError("Missing original UI256 geometry or deadline evidence")
    closures = [line for line in lines if line.startswith("clean=")]
    closing_ledger, separator, closing_failure = (closures[0] if len(closures) == 1 else "").partition("; failure=")
    reservation_fields = ("retained_source", "retained_metadata", "cache", "state", "wasi",
                          "shared", "construction", "combined")
    live_fields = ("cache_entries", "active_pins", "frames", "values", "controls", "memory_pages")

    def zero_counters(names):
        counter = r"SwiftReservationUsage \{ current: 0, peak: \d+ \}"
        return ", ".join(f"{name}: {counter}" for name in names)

    reservation_ledger = zero_counters(reservation_fields)
    live_ledger = zero_counters(live_fields)
    outer = re.match(
        rf"^clean=SwiftRunUsage \{{ reservations: SwiftReservations \{{ {reservation_ledger}, "
        rf"live_tickets: 0, peak_tickets: \d+ \}}, live: SwiftLiveUsage \{{ {live_ledger} \}}, ",
        closing_ledger,
    )
    if (not separator or closing_failure != failure
            or not outer or "cleanup_invariant: None," not in closing_ledger
            or not re.search(r", deadline_ms: 30000, deadline_origin:", closing_ledger)):
        raise ValueError("Missing clean owner closure; see owner trace")


def verify_guest(replay_code, replay_log, oracle):
    if replay_code != 0:
        raise ValueError(f"Replay exit {replay_code}; see owner trace")
    verify_guest_trace(replay_log)
    return {"ui256Exit": replay_code, "oracleSnapshotsMatched": verify_frames(replay_log, oracle),
            "cleanOwner": True, "liveReservationBytes": 0, "liveTickets": 0}


def read_console(mode, path):
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"{mode}: console log exceeds 2 MB")
    log = path.read_text(encoding="utf-8")
    starts = re.findall(r"^s2a_start=(\w+) pid=(\d+) ios=([\d.]+)$", log, re.MULTILINE)
    exits = re.findall(r"^s2a_exit=(\d+) pid=(\d+)$", log, re.MULTILINE)
    if len(starts) != 1 or len(exits) != 1 or starts[0][:2] != (mode, exits[0][1]):
        raise ValueError(f"{mode}: app start or terminal marker missing or ambiguous; see {path}")
    samples = re.findall(
        r"^s2a_stage=(\w+) elapsed_us=(\d+) since_main_us=(\d+)"
        r" rss_bytes=(\d+) peak_rss_bytes=(\d+)$", log, re.MULTILINE,
    )
    if [stage for stage, *_ in samples] != STAGES[mode]:
        raise ValueError(f"{mode}: missing, unavailable or out-of-order milestone evidence")
    milestones = {
        stage: {"elapsedMicros": int(elapsed), "sinceMainMicros": int(since_main),
                "rssBytes": int(rss), "peakRSSBytes": int(peak)}
        for stage, elapsed, since_main, rss, peak in samples
    }
    times = [sample["sinceMainMicros"] for sample in milestones.values()]
    peaks = [sample["peakRSSBytes"] for sample in milestones.values()]
    if times != sorted(times) or peaks != sorted(peaks):
        raise ValueError(f"{mode}: nonmonotonic timestamps or peak RSS")
    if "steady" in milestones:
        idle = milestones["steady"]["sinceMainMicros"] - milestones["reopen"]["sinceMainMicros"]
        if idle < 990_000:
            raise ValueError(f"{mode}: steady milestone preceded the idle interval")
    return log, {"exitCode": int(exits[0][0]), "pid": int(starts[0][1]), "ios": starts[0][2],
                 "milestones": milestones, "console": fingerprint(path)}


def verify_pair(first, second):
    if first["pid"] == second["pid"] or first["ios"] != second["ios"]:
        raise ValueError("Expected distinct process IDs and matching iOS versions")


def check_console(app, fixed_log, replay_log):
    fixed, fixed_run = read_console("fixed34", fixed_log)
    guest, guest_run = read_console("ui256", replay_log)
    verify_pair(fixed_run, guest_run)
    verify_fixed_refusal(fixed_run["exitCode"], fixed)
    return {"fixed34Exit": fixed_run["exitCode"],
            **verify_guest(guest_run["exitCode"], guest, verify_payload(app)),
            "fixed34": fixed_run, "ui256": guest_run}


def compare(app, native_log, replay_log):
    oracle = verify_payload(app)
    native, native_run = read_console("native", native_log)
    guest, guest_run = read_console("ui256", replay_log)
    verify_pair(native_run, guest_run)
    if native_run["exitCode"] != 0:
        raise ValueError(f"Native exit {native_run['exitCode']}")
    native_run["oracleSnapshotsMatched"] = verify_frames(native, oracle)
    guest_run.update(verify_guest(guest_run["exitCode"], guest, oracle))
    swift, wasm = native_run["milestones"], guest_run["milestones"]
    startup = wasm["first_snapshot"]["sinceMainMicros"] - swift["first_snapshot"]["sinceMainMicros"]
    return {
        "scope": "One same-binary offscreen process pair",
        "executable": fingerprint(app / APP_NAME),
        "native": native_run, "ui256": guest_run,
        "guestMinusNative": {
            "mainToFirstSnapshotMicros": startup,
            "baselineRSSBytes": wasm["baseline"]["rssBytes"] - swift["baseline"]["rssBytes"],
            "steadyRSSBytes": wasm["steady"]["rssBytes"] - swift["steady"]["rssBytes"],
            "preExitPeakRSSBytes": wasm["pre_exit"]["peakRSSBytes"] - swift["pre_exit"]["peakRSSBytes"],
        },
        "startupComparison": {
            "sampleLimitMicros": 200_000,
            "withinSampleLimit": startup <= 200_000,
        },
    }


def build(name, payload, rust, swift, developer_dir, host_developer_dir):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
        raise ValueError("Expected a new ASCII run name in verification/local")
    run_dir = ROOT / "verification/local" / name
    run_dir.mkdir(parents=True, mode=0o700)
    scratch, logs, artifacts = (run_dir / part for part in ("scratch", "logs", "artifacts"))
    for directory in (scratch, logs, artifacts, scratch / "tmp"):
        directory.mkdir()
    report = {"scope": "arm64 iOS Simulator cross-build and macOS controls; no device run", "commands": []}
    recorder = CommandRecorder(logs, report["commands"], ROOT, log_limit=2_000_000)
    env = clean_environment() | {
        "TMPDIR": str(scratch / "tmp"), "CARGO_HOME": str(scratch / "cargo-home"),
        "CARGO_TARGET_DIR": str(scratch / "target"), "RUSTC": str(rust / "rustc"),
        "PATH": str(rust) + os.pathsep + os.defpath,
        "CLANG_MODULE_CACHE_PATH": str(scratch / "clang-cache"),
    }
    if developer_dir is not None:
        env["DEVELOPER_DIR"] = str(developer_dir)

    def run(label, command, *, extra=None, timeout=30, expected=(0,)):
        return recorder.run(label, command, env=env | (extra or {}), timeout=timeout, expected=expected)

    try:
        git = "/usr/bin/git"
        report["worktreeHead"] = run("head", [git, "rev-parse", "HEAD"]).strip()
        report["vmPin"] = PIN
        report["s2bPin"] = S2B_PIN
        trees = run("vm-trees", [git, "rev-parse", PIN + ":vm", S2B_PIN + ":vm"]).splitlines()
        if trees != [VM_TREE, VM_TREE]:
            raise ValueError(f"VM source pin mismatch: {trees}")
        report["vmTree"] = VM_TREE
        runner = HERE / "OwnedReactor.rs"
        shim = HERE / "OwnedReactorSimulator.m"
        header = HERE / "OwnedReactorSimulator.h"
        fixture = HERE / "FieldLog.swift"
        native = HERE / "NativeJourney.swift"
        fieldlog_blob = run("fieldlog-pin", [git, "rev-parse", PIN + ":" + str(fixture.relative_to(ROOT))]).strip()
        if run("fieldlog-blob", [git, "hash-object", "--no-filters", fixture]).strip() != fieldlog_blob:
            raise ValueError("Native FieldLog.swift differs from the pinned guest fixture")
        report["fieldLogGitBlob"] = fieldlog_blob
        report["diagnosticSources"] = {
            path.name: fingerprint(path)
            for path in (runner, shim, header, fixture, native, Path(__file__))
        }
        archive = scratch / "vm.tar"
        run("archive", [git, "archive", "--output", archive, PIN, "vm"])
        report["archiveSha256"] = digest(archive)
        run("extract", ["/usr/bin/tar", "-xf", archive, "-C", scratch])
        app = artifacts / (APP_NAME + ".app")
        app.mkdir()
        for name in PAYLOAD:
            shutil.copyfile(payload / name, app / name)
        oracle = verify_payload(app)
        report["payload"] = {name: fingerprint(app / name) for name in PAYLOAD}
        report["versions"] = {
            "host": run("macos-version", ["/usr/bin/sw_vers"]).strip(),
            "xcode": run("xcode-version", ["/usr/bin/xcodebuild", "-version"]).strip(),
            "rustc": run("rust-version", [rust / "rustc", "-vV"]).strip(),
            "cargo": run("cargo-version", [rust / "cargo", "--version"]).strip(),
            "swift": run("swift-version", [swift, "--version"]).strip(),
        }
        if "6.3.3 (swift-6.3.3-RELEASE)" not in report["versions"]["swift"]:
            raise ValueError("Expected the same Swift 6.3.3 release compiler as the Wasm fixture")
        sdk = run("sdk-path", [XCRUN, "--sdk", "iphonesimulator", "--show-sdk-path"]).strip()
        clang = run("clang-path", [XCRUN, "--sdk", "iphonesimulator", "--find", "clang"]).strip()
        report["sdk"] = sdk
        report["versions"]["clang"] = run("clang-version", [clang, "--version"]).strip()
        base = [rust / "cargo", "build", "--manifest-path", scratch / "vm/Cargo.toml", "--offline",
                "--locked", "--release", "--features", "experimental-swift-reactor", "--lib"]
        ios_env = {"SDKROOT": sdk, "IPHONEOS_DEPLOYMENT_TARGET": MIN_OS,
                   "CARGO_TARGET_AARCH64_APPLE_IOS_SIM_LINKER": clang}
        run("ios-vm", [*base, "--target", TARGET], extra=ios_env, timeout=240)
        staticlib = scratch / "libowned_reactor.a"
        ios_rlib = scratch / "target" / TARGET / "release/libmixer_vm.rlib"
        rust_flags = [rust / "rustc", "--edition=2021", "-O"]
        run("ios-runner", [*rust_flags, "--target", TARGET, "--crate-type", "staticlib",
                           "--print", "native-static-libs", "--extern", f"mixer_vm={ios_rlib}",
                           runner, "-o", staticlib], extra=ios_env, timeout=120)
        executable = app / APP_NAME
        shim_object = scratch / "simulator-shim.o"
        swift_flags = ["-module-name", "FieldLogSpike", "-Osize", "-gnone", "-parse-as-library",
                       "-module-cache-path", scratch / "swift-cache"]
        apple_target = "arm64-apple-ios" + MIN_OS + "-simulator"
        run("ios-shim", [clang, "-target", apple_target, "-isysroot", sdk,
                         "-fobjc-arc", "-O2", "-Wall", "-Wextra", "-Werror", "-c", shim,
                         "-o", shim_object], extra=ios_env, timeout=120)
        run("ios-link", [swift, "-target", apple_target, "-sdk", sdk, *swift_flags,
                          "-import-objc-header", header, fixture, native, shim_object, staticlib,
                          "-framework", "Foundation", "-framework", "UIKit",
                          "-o", executable], extra=ios_env, timeout=120)
        info = app / "Info.plist"
        info.write_bytes(plistlib.dumps({
            "CFBundleIdentifier": BUNDLE_ID, "CFBundleExecutable": APP_NAME, "CFBundleName": APP_NAME,
            "CFBundlePackageType": "APPL", "CFBundleVersion": "1", "CFBundleShortVersionString": "1.0",
            "CFBundleSupportedPlatforms": ["iPhoneSimulator"], "MinimumOSVersion": MIN_OS,
            "UIDeviceFamily": [1, 2], "UILaunchScreen": {},
            "UIApplicationSceneManifest": {"UIApplicationSupportsMultipleScenes": False,
                "UISceneConfigurations": {"UIWindowSceneSessionRoleApplication": [{
                    "UISceneConfigurationName": "S2a diagnostic", "UISceneDelegateClassName": "S2aSceneDelegate",
                }]}},
        }))
        run("plist-lint", ["/usr/bin/plutil", "-lint", info])
        min_plist = run("plist-floor", ["/usr/bin/plutil", "-extract", "MinimumOSVersion", "raw", "-o", "-", info]).strip()
        macho = run("macho-build", [XCRUN, "vtool", "-show-build", executable])
        arch = run("macho-arch", [XCRUN, "lipo", "-archs", executable]).strip()
        imports = run("macho-dylibs", [XCRUN, "otool", "-L", executable])
        if (arch != "arm64" or min_plist != MIN_OS or "LC_BUILD_VERSION" not in macho
                or not re.search(r"^\s*platform\s+IOSSIMULATOR\s*$", macho, re.MULTILINE)
                or not re.search(r"^\s*minos\s+17\.0\s*$", macho, re.MULTILINE)):
            raise ValueError("Expected arm64 iOS Simulator executable and a 17.0 Mach-O and plist minimum")
        run("ad-hoc-sign", ["/usr/bin/codesign", "--force", "--sign", "-", "--timestamp=none", app])
        run("verify-ad-hoc", ["/usr/bin/codesign", "--verify", "--strict", app])
        report["app"] = {"path": str(app), "bundleID": BUNDLE_ID, "architecture": arch,
                         "minimumOSVersion": min_plist, "machoBuild": macho.splitlines()[1:],
                         "linkedLibraries": imports.splitlines()[1:], "signing": "local ad hoc",
                         "executable": fingerprint(executable), "infoPlist": fingerprint(info)}

        host_env = {"DEVELOPER_DIR": str(host_developer_dir)}
        mac_sdk = run("macos-sdk", [XCRUN, "--sdk", "macosx", "--show-sdk-path"], extra=host_env).strip()
        report["hostNativeSDK"] = mac_sdk
        native_host = scratch / "fieldlog-native-host"
        run("host-native-build", [swift, "-target", "arm64-apple-macosx14.0", "-sdk", mac_sdk,
                                  *swift_flags, fixture, native, "-o", native_host], extra=host_env, timeout=120)
        report["hostNativeControls"] = {}
        for label in ("host-native-first-process", "host-native-repeat-process"):
            frames = run(label, [native_host])
            report["hostNativeControls"][label] = verify_frames(frames, oracle)

        run("host-vm", base, timeout=240)
        host_runner = scratch / "owned-reactor-host"
        host_rlib = scratch / "target/release/libmixer_vm.rlib"
        run("host-runner", [*rust_flags, "--extern", f"mixer_vm={host_rlib}", runner,
                            "-o", host_runner], timeout=120)
        wasm = app / "reactor-base.wasm"
        fixed = run("host-fixed34", [host_runner, wasm], expected=(10,), timeout=160)
        fixed += (logs / "host-fixed34.stderr").read_text()
        frames = run("host-ui256", [host_runner, wasm, "--swift-6.3.3-ui256"], expected=(0, 10, 20, 74), timeout=160)
        replay_code = report["commands"][-1]["exitCode"]
        report["ownerClosureUnknown"] = replay_code == 74
        frames += (logs / "host-ui256.stderr").read_text()
        verify_fixed_refusal(10, fixed)
        report["hostControls"] = {"fixed34Exit": 10, **verify_guest(replay_code, frames, oracle)}
        report["completed"] = True
        print(app)
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        held = report.get("ownerClosureUnknown", False) or any(
            command["terminalCustody"] == "UNKNOWN"
            or (command["name"] == "host-ui256" and command["exitCode"] not in (0, 10, 11, 20))
            for command in report["commands"])
        if held:
            report["cleanup"] = "Preserved scratch and output with unresolved process or owner custody"
        else:
            shutil.rmtree(scratch)
            report["cleanup"] = "Removed disposable build scratch after terminal commands"
        (run_dir / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("build")
    builder.add_argument("name")
    builder.add_argument("payload", type=Path, help="exact S2b payload directory")
    builder.add_argument("--rust", type=Path, default=RUST_BIN)
    builder.add_argument("--swift", type=Path, default=SWIFTC)
    builder.add_argument("--xcode", type=Path, help="Developer directory for the Simulator SDK")
    builder.add_argument("--host-xcode", type=Path, default=HOST_XCODE,
                         help="Xcode Developer directory with a Swift 6.3.3-compatible macOS SDK")
    checker = commands.add_parser("check", help="check both root-run console logs")
    checker.add_argument("app", type=Path)
    checker.add_argument("fixed34", type=Path)
    checker.add_argument("ui256", type=Path)
    comparator = commands.add_parser("compare", help="compare one native/guest console pair")
    comparator.add_argument("app", type=Path)
    comparator.add_argument("native", type=Path)
    comparator.add_argument("ui256", type=Path)
    args = parser.parse_args()
    if args.command == "build":
        build(args.name, args.payload, args.rust, args.swift, args.xcode, args.host_xcode)
    elif args.command == "check":
        print(json.dumps(check_console(args.app, args.fixed34, args.ui256), indent=2))
    else:
        print(json.dumps(compare(args.app, args.native, args.ui256), indent=2))


if __name__ == "__main__":
    main()
