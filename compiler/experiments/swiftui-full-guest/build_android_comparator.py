#!/usr/bin/env python3
"""Cross-build and check the private API 28 matched S2b comparator."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

from build_ios_simulator import (
    CommandRecorder, HOST_XCODE, PAYLOAD, PIN, ROOT, RUST_BIN, STAGES, SWIFTC, TURNS, VM_TREE,
    clean_environment, fingerprint, strict_json, verify_fixed_refusal, verify_guest_trace,
    verify_payload,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "fieldlog-guest-benchmark"))
from android_cross_build import inspect_elf

ANDROID_SDK = Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
ANDROID_TARGET = "aarch64-unknown-linux-android28"
RUST_ANDROID_TARGET = "aarch64-linux-android"
DEADLINE_PIN = "66195b5d6cc161f39df6af04cc086f7d0bd1975f"
VARIANTS = {"baseline": (PIN, VM_TREE),
            "deadline-window": (DEADLINE_PIN, "d574c44f519da84895ca3b09d190e0056894d2f3")}
MODES = ("native", "ui256", "fixed34")
EXE = "fieldlog-s2b"


def bounded_log(path):
    if path.stat().st_size > 2_000_000:
        raise ValueError(f"Log exceeds 2 MB: {path}")
    return path.read_text(encoding="utf-8")


def read_run(mode, stdout, stderr, oracle, platform, exit_code):
    frames = [strict_json(line) for line in bounded_log(stdout).splitlines()]
    trace = bounded_log(stderr)
    starts = re.findall(r"^s2b_start=(\w+) pid=(\d+) platform=([\w-]+)$", trace, re.M)
    exits = re.findall(r"^s2b_exit=(\d+) pid=(\d+)$", trace, re.M)
    if len(starts) != 1 or len(exits) != 1 or starts[0] != (mode, exits[0][1], platform):
        raise ValueError(f"{mode}: missing or ambiguous process identity or terminal marker")
    if exit_code != int(exits[0][0]):
        raise ValueError(f"{mode}: process exit and terminal marker disagree")
    samples = re.findall(
        r"^s2b_stage=(\w+) elapsed_us=(\d+) since_main_us=(\d+)"
        r" rss_bytes=(\d+) peak_rss_bytes=(\d+)$", trace, re.M,
    )
    stages = STAGES[mode]
    expected_count = 6
    deadline = mode == "ui256" and exit_code == 20
    if deadline:
        expected_count = len(frames)
        if expected_count >= len(TURNS):
            raise ValueError("Deadline failure must precede the complete oracle")
        stages = ["baseline", "read", "validate", "construct", *TURNS[:expected_count + 1],
                  "consume", "pre_exit"]
    elif mode == "fixed34":
        expected_count = 0
    if (len(frames) != expected_count or
            any(json.dumps(frame, sort_keys=True) != json.dumps(expected, sort_keys=True)
                for frame, expected in zip(frames, oracle))):
        raise ValueError(f"{mode}: unexpected snapshot count or snapshot differs from the oracle")
    if ([stage for stage, *_ in samples] != stages or
            sum(line.startswith("s2b_stage=") for line in trace.splitlines()) != len(samples)):
        raise ValueError(f"{mode}: missing or out-of-order milestones")
    milestones = {
        stage: {"elapsedMicros": int(elapsed), "sinceMainMicros": int(since_main),
                "rssBytes": int(rss), "peakRSSBytes": int(peak)}
        for stage, elapsed, since_main, rss, peak in samples
    }
    for field in ("sinceMainMicros", "peakRSSBytes"):
        values = [sample[field] for sample in milestones.values()]
        if values != sorted(values):
            raise ValueError(f"{mode}: nonmonotonic {field}")
    if any(not sample["rssBytes"] or not sample["peakRSSBytes"] for sample in milestones.values()):
        raise ValueError(f"{mode}: unavailable memory sample")
    if "steady" in milestones and (milestones["steady"]["sinceMainMicros"] -
                                    milestones["reopen"]["sinceMainMicros"] < 990_000):
        raise ValueError(f"{mode}: steady sample preceded the idle interval")

    observation = {"pid": int(starts[0][1]), "exitCode": exit_code, "platform": platform,
                   "oracleSnapshotsMatched": len(frames), "milestones": milestones,
                   "stdout": fingerprint(stdout), "stderr": fingerprint(stderr)}
    if mode == "fixed34":
        verify_fixed_refusal(exit_code, trace)
        observation["refusal"] = "swift_import_count"
    elif mode == "ui256":
        closure_failure = "None"
        if deadline:
            failures = [line.removeprefix("failure=") for line in trace.splitlines()
                        if line.startswith("failure=")]
            if len(failures) != 1 or 'kind: Deadline, code: "swift_run_deadline"' not in failures[0]:
                raise ValueError("Expected a swift_run_deadline failure")
            # Close enriches the original invocation failure with its cleanup usage.
            entries = [line.partition("; failure=")[2] for line in trace.splitlines()
                       if line.startswith("clean=")]
            prefix = f"Some({failures[0].removesuffix(', after_cleanup: None }')}"
            if (not failures[0].endswith(", after_cleanup: None }") or len(entries) != 1
                    or not entries[0].startswith(prefix + ", after_cleanup: Some(SwiftRunUsage {")
                    or not entries[0].endswith(" }) })")):
                raise ValueError("Closing owner did not retain and settle the original deadline failure")
            closure_failure = entries[0]
            observation["deadlineFailureTurn"] = TURNS[expected_count]
        elif exit_code != 0:
            raise ValueError(f"Guest exit {exit_code}")
        verify_guest_trace(trace, closure_failure)
        observation.update(cleanOwner=True, liveReservationBytes=0, liveTickets=0)
    elif exit_code != 0:
        raise ValueError(f"Native exit {exit_code}")
    return observation


def compare(runs):
    if len({run["pid"] for run in runs.values()}) != len(runs):
        raise ValueError("Expected fresh processes for all three modes")
    native = runs["native"]["milestones"]
    guest = runs["ui256"]["milestones"]

    def delta(stage, field):
        return guest[stage][field] - native[stage][field] if stage in guest else None

    startup = (delta("first_snapshot", "sinceMainMicros")
               if runs["ui256"]["oracleSnapshotsMatched"] else None)
    return {"runs": runs, "completePair": runs["ui256"]["exitCode"] == 0,
            "guestMinusNative": {
                "mainToFirstSnapshotMicros": startup,
                "baselineRSSBytes": delta("baseline", "rssBytes"),
                "steadyRSSBytes": delta("steady", "rssBytes"),
                "preExitPeakRSSBytes": delta("pre_exit", "peakRSSBytes"),
            }, "startupSampleLimitMicros": 200_000,
            "withinStartupSampleLimit": startup <= 200_000 if startup is not None else None}


def build(args):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.name):
        raise ValueError("Expected a new ASCII run name under verification/local")
    run_dir = ROOT / "verification/local" / args.name
    run_dir.mkdir(parents=True, mode=0o700)
    scratch, logs, artifacts = (run_dir / part for part in ("scratch", "logs", "artifacts"))
    for directory in (scratch, logs, artifacts, scratch / "tmp"):
        directory.mkdir()
    receipt = {"scope": "Android arm64 API 28 cross-link and macOS replay", "commands": []}
    commands = receipt["commands"]
    env = clean_environment() | {
        "PATH": str(args.rust) + os.pathsep + os.defpath, "TMPDIR": str(scratch / "tmp"),
        "CARGO_HOME": str(scratch / "cargo-home"), "RUSTC": str(args.rust / "rustc"),
        "CLANG_MODULE_CACHE_PATH": str(scratch / "clang-cache"), "DEVELOPER_DIR": str(args.xcode),
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
    }

    def run(label, command, *, extra=None, cwd=ROOT, timeout=30, expected=(0,)):
        recorder = CommandRecorder(logs, commands, cwd, log_limit=2_000_000)
        try:
            return recorder.run(label, command, env=env | (extra or {}), timeout=timeout, expected=expected)
        finally:
            if commands and commands[-1]["name"] == label:
                commands[-1].update(cwd=str(cwd), environment=extra or {})

    fixture, journey, runner, shim, header = [HERE / name for name in (
        "FieldLog.swift", "NativeJourney.swift", "OwnedReactor.rs", "OwnedReactorShell.c", "OwnedReactorShell.h",
    )]
    git = "/usr/bin/git"
    ndk = args.sdk / "android-ndk-r27d"
    toolchain = ndk / "toolchains/llvm/prebuilt/darwin-x86_64"
    tools = toolchain / "bin"
    clang = tools / "aarch64-linux-android28-clang"
    sysroot = args.sdk / "ndk-sysroot"
    resources = args.sdk / "swift-resources/usr/lib/swift-aarch64"
    android_extra = {"CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER": str(clang)}
    android_link = ["-target", ANDROID_TARGET, "-sdk", sysroot, "-resource-dir", resources,
                    "-tools-directory", tools, "-Xclang-linker", "-fuse-ld=lld",
                    "-Xlinker", "-z", "-Xlinker", "max-page-size=16384", "-Xlinker", "--build-id=sha1"]

    class ElfCommands:
        def __init__(self, variant):
            self.variant = variant

        def command(self, label, *argv):
            # The benchmark inspector parses stdout only. Keep NDK diagnostics in stderr.
            return (run(f"{self.variant}-{label.replace('+', '_plus_')}", argv),)

    def link(label, work, android, output, vm_extra):
        target = RUST_ANDROID_TARGET if android else "aarch64-apple-darwin"
        build_dir = work / "cargo"
        extra = {"CARGO_TARGET_DIR": str(build_dir)} | vm_extra
        if android:
            extra |= android_extra
        run(f"{label}-vm", [args.rust / "cargo", "build", "--manifest-path", work / "vm/Cargo.toml",
                            "--offline", "--locked", "--release", "--lib", "--target", target,
                            "--features", "experimental-swift-reactor"], extra=extra, timeout=240)
        archive = work / f"{label}.a"
        rlib = build_dir / target / "release/libmixer_vm.rlib"
        flags = ["--target", target, "--edition=2021", "-O", "--cfg", "s2_matched_shell"]
        run(f"{label}-runner", [args.rust / "rustc", *flags, "--crate-type", "staticlib", "--print",
                                "native-static-libs", "--extern", f"mixer_vm={rlib}", runner, "-o", archive],
            extra=extra, timeout=120)
        libraries = re.findall(r"^note: native-static-libs: (.+)$",
                               bounded_log(logs / f"{label}-runner.stderr"), re.M)
        if len(libraries) != 1:
            raise ValueError(f"{label}: missing Rust native static library dependencies")
        object_path = work / f"{label}.o"
        if android:
            c_flags = [clang]
            swift_flags = android_link
        else:
            c_flags = ["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-target", "arm64-apple-macosx14.0"]
            swift_flags = ["-target", "arm64-apple-macosx14.0", "-sdk", mac_sdk]
        run(f"{label}-shim", [*c_flags, "-O2", "-Wall", "-Wextra", "-Werror", "-c", shim, "-o", object_path])
        linker_flags = [arg for library in libraries[0].split() for arg in ("-Xlinker", library)]
        run(f"{label}-link", [args.swift, *swift_flags, "-module-cache-path", work / "modules",
                            "-module-name", "FieldLogSpike", "-parse-as-library", "-Osize", "-gnone",
                            "-D", "S2_MATCHED_SHELL", "-import-objc-header", header, fixture, journey,
                            object_path, archive, *linker_flags, "-o", output], timeout=120)

    try:
        oracle = verify_payload(args.payload)
        receipt["head"] = run("head", [git, "rev-parse", "HEAD"]).strip()
        blob = run("fixture-pin", [git, "rev-parse", f"{PIN}:{fixture.relative_to(ROOT)}"]).strip()
        if run("fixture-blob", [git, "hash-object", "--no-filters", fixture]).strip() != blob:
            raise ValueError("FieldLog.swift differs from the pinned Wasm fixture")
        receipt["fieldLogGitBlob"] = blob
        receipt["diagnosticSources"] = {path.name: fingerprint(path) for path in (
            fixture, journey, runner, shim, header, Path(__file__), HERE / "build_ios_simulator.py",
            HERE.parent / "fieldlog-guest-benchmark/android_cross_build.py",
        )}
        versions = {name: run(f"{name}-version", argv).strip() for name, argv in {
            "swift": [args.swift, "--version"], "rust": [args.rust / "rustc", "-vV"],
            "cargo": [args.rust / "cargo", "--version"], "ndk-clang": [clang, "--version"],
            "ndk-readelf": [tools / "llvm-readelf", "--version"], "host": ["/usr/bin/sw_vers"],
        }.items()}
        receipt["versions"] = versions
        if ("6.3.3 (swift-6.3.3-RELEASE)" not in versions["swift"] or
                "commit-hash: b940084d7eb6a299eb4bfeb8e34901bc051e7ac4" not in versions["rust"] or
                "Pkg.Revision = 27.3.13750724" not in (ndk / "source.properties").read_text()):
            raise ValueError("Expected Swift 6.3.3, Rust 1.99.0 and Android NDK r27d")
        mac_sdk = run("macos-sdk", ["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"]).strip()
        receipt["packets"] = {}
        closure = None
        for variant in VARIANTS if args.deadline_window else ("baseline",):
            pin, tree = VARIANTS[variant]
            build_env = {"MIXER_SWIFT_UI_DEADLINE_BATCH": "1"} if variant == "deadline-window" else {}
            work = scratch / variant
            packet = artifacts / variant
            for directory in (work, packet, packet / "lib", packet / "evidence"):
                directory.mkdir()
            if run(f"{variant}-vm-tree", [git, "rev-parse", pin + ":vm"]).strip() != tree:
                raise ValueError(f"{variant}: VM tree differs from the pin")
            archive = work / "vm.tar"
            run(f"{variant}-archive", [git, "archive", "--output", archive, pin, "vm"])
            run(f"{variant}-extract", ["/usr/bin/tar", "-xf", archive, "-C", work])
            for name in PAYLOAD:
                shutil.copyfile(args.payload / name, packet / name)
            verify_payload(packet)
            link(variant, work, True, packet / EXE, build_env)
            dependencies, origins, system = inspect_elf(
                ElfCommands(variant), tools, packet / EXE, packet, args.sdk, ndk,
                toolchain / "sysroot/usr/lib/aarch64-linux-android",
            )
            libraries = {name: fingerprint(packet / "lib" / name) for name in sorted(origins)}
            identity = (dependencies[EXE]["needed"], libraries, system)
            if closure is not None and closure != identity:
                raise ValueError("Deadline-window runtime closure differs from baseline")
            closure = identity
            manifest = {"variant": variant, "vmRevision": pin, "vmTree": tree,
                        "compileEnvironment": build_env, "target": ANDROID_TARGET,
                        "ownerDeadlineMillis": 30_000, "executable": fingerprint(packet / EXE),
                        "payload": {name: fingerprint(packet / name) for name in PAYLOAD},
                        "libraries": libraries, "systemLibraries": system, "elf": dependencies}
            (packet / "packet.json").write_text(json.dumps(manifest, indent=2) + "\n")
            receipt["packets"][variant] = manifest
            host = work / "matched-host"
            link(f"{variant}-host", work, False, host, build_env)
            runs = {}
            for mode in MODES:
                label = f"{variant}-host-replay-{mode}"
                run(label, [host, mode], cwd=packet, timeout=160,
                    expected=(0, 10, 11, 20, 74) if mode == "ui256" else (0, 10))
                runs[mode] = read_run(mode, logs / f"{label}.stdout", logs / f"{label}.stderr",
                                      oracle, "macos", commands[-1]["exitCode"])
            result = compare(runs)
            if not result["completePair"]:
                raise ValueError(f"{variant}: macOS did not complete the six-frame replay")
            receipt.setdefault("hostControls", {})[variant] = result
            print(packet, flush=True)
    except Exception as error:
        receipt["error"] = str(error)
        raise
    finally:
        held = any(command["terminalCustody"] == "UNKNOWN" or
                   ("-host-replay-ui256" in command["name"] and command["exitCode"] not in (0, 10, 11, 20))
                   for command in commands)
        if held:
            receipt["cleanup"] = f"Preserved {scratch} and logs with unresolved process or owner custody"
        else:
            shutil.rmtree(scratch)
            receipt["cleanup"] = "Removed owned build scratch after terminal commands"
        (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def check(args):
    packet = args.packet
    manifest = strict_json((packet / "packet.json").read_bytes())
    variant = manifest["variant"]
    if (tuple(VARIANTS[variant]) != (manifest["vmRevision"], manifest["vmTree"]) or
            manifest["ownerDeadlineMillis"] != 30_000 or manifest["target"] != ANDROID_TARGET or
            fingerprint(packet / EXE) != manifest["executable"] or
            {path.name: fingerprint(path) for path in (packet / "lib").iterdir()} != manifest["libraries"]):
        raise ValueError("Packet identity differs from the cross-build receipt")
    oracle = verify_payload(packet)
    runs = {}
    for mode in MODES:
        stdout, stderr, status = getattr(args, mode)
        runs[mode] = read_run(mode, Path(stdout), Path(stderr), oracle, "android-api28", int(status))
    result = compare(runs)
    return {"scope": "One process-cold API 28 offscreen comparison", "variant": variant,
            "executable": manifest["executable"], **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    builder = commands.add_parser("build")
    builder.add_argument("name")
    builder.add_argument("payload", type=Path)
    builder.add_argument("--deadline-window", action="store_true")
    builder.add_argument("--rust", type=Path, default=RUST_BIN)
    builder.add_argument("--swift", type=Path, default=SWIFTC)
    builder.add_argument("--sdk", type=Path, default=ANDROID_SDK)
    builder.add_argument("--xcode", type=Path, default=HOST_XCODE)
    checker = commands.add_parser("check")
    checker.add_argument("packet", type=Path)
    for mode in MODES:
        checker.add_argument("--" + mode, nargs=3, required=True, metavar=("STDOUT", "STDERR", "EXIT"))
    args = parser.parse_args()
    if args.command == "build":
        build(args)
    else:
        print(json.dumps(check(args), indent=2))


if __name__ == "__main__":
    main()
