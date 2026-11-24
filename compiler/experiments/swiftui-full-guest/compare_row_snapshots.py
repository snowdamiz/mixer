#!/usr/bin/env python3
"""Compare eager and on-demand S2 row snapshots in the existing owned VM."""

import argparse
import gzip
import json
from pathlib import Path
import re
import shutil
from statistics import median

from build_ios_simulator import TURNS, verify_fixed_refusal, verify_guest_trace
from replay import HERE, ROOT, RUST, SWIFT, WASI, XCODE, check_journey
from qualification_support import CommandRecorder, clean_environment, digest, strict_json


def check_signed_admission(run, work, module, patch, revision):
    package = work / "signed-admission"
    shutil.copytree(ROOT / "updates/Sources", package / "Sources",
                    ignore=shutil.ignore_patterns("MixerUpdateTool"))
    pin_cache = Path.home() / "Library/Caches/org.swift.swiftpm/repositories"
    pins = strict_json((ROOT / "updates/Package.resolved").read_bytes())["pins"]
    for name, cache_name in (("swift-crypto", "swift-crypto-7e0614ea"), ("swift-asn1", "swift-asn1-7065ad2c")):
        pin = next(pin["state"]["revision"] for pin in pins if pin["identity"] == name)
        archive = work / f"{name}.tar"
        run(f"archive-{name}", ["/usr/bin/git", "-C", pin_cache / cache_name, "archive",
                               "--output", archive, pin])
        dependency = work / name
        dependency.mkdir()
        run(f"extract-{name}", ["/usr/bin/tar", "-xf", archive, "-C", dependency])
    target = package / "Sources/CheckSignedAdmission"
    target.mkdir()
    shutil.copyfile(HERE / "CheckSignedAdmission.swift", target / "main.swift")
    (package / "Package.swift").write_text("""// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "S2SignedAdmission", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../swift-crypto")],
    targets: [
        .target(name: "MixerDurableIO"),
        .target(name: "MixerUpdates", dependencies: ["MixerDurableIO", .product(name: "Crypto", package: "swift-crypto")]),
        .executableTarget(name: "CheckSignedAdmission", dependencies: ["MixerUpdates", .product(name: "Crypto", package: "swift-crypto")]),
    ])
""")
    scratch = package / "build"
    run("build-signed-admission", [
        SWIFT / "swift", "build", "--package-path", package, "--scratch-path", scratch,
        "--disable-dependency-cache", "--cache-path", package / "cache",
        "--config-path", package / "config", "--security-path", package / "security",
        "--product", "CheckSignedAdmission",
    ], extra={"SWIFTCI_USE_LOCAL_DEPS": "1", "GIT_NO_LAZY_FETCH": "1"}, timeout=240)
    return run("check-signed-admission", [scratch / "debug/CheckSignedAdmission", module, patch, revision]).splitlines()


def parse_sample(log):
    verify_guest_trace(log)
    milestones = re.findall(r"^s2_host=(\w+); wall_us=(\d+); cpu_us=(\d+)$", log, re.M)
    if [stage for stage, _, _ in milestones] != ["read", "validate", "construct", *TURNS, "consume"]:
        raise ValueError("Incomplete owned milestone sequence")
    usage = re.findall(r"^step=(\d+); .*?instruction_fuel: (\d+), instructions: (\d+), host_calls: (\d+),", log, re.M)
    if [int(step) for step, *_ in usage] != list(range(len(TURNS))):
        raise ValueError("Incomplete owned execution counters")
    samples = {stage: {"wallMicros": int(wall), "threadCPUMicros": int(cpu)}
               for stage, wall, cpu in milestones}
    for stage, (_, fuel, instructions, calls) in zip(TURNS, usage):
        samples[stage].update(fuel=int(fuel), instructions=int(instructions), hostCalls=int(calls))
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.name):
        parser.error("Use a fresh ASCII run name")
    run_dir = ROOT / "verification/local" / args.name
    run_dir.mkdir(parents=True, mode=0o700)
    work, logs = run_dir / "work", run_dir / "logs"
    work.mkdir()
    logs.mkdir()
    tmp = work / "tmp"
    tmp.mkdir()
    report = {"scope": "macOS offscreen owned VM with original exact-32 UI256 profile",
              "commands": [], "samples": [], "artifacts": {}}
    recorder = CommandRecorder(logs, report["commands"], ROOT, log_limit=2_000_000)
    env = clean_environment()
    env.update(TMPDIR=str(tmp), DEVELOPER_DIR=str(XCODE),
               CLANG_MODULE_CACHE_PATH=str(work / "clang-cache"), RUSTC=str(RUST / "rustc"),
               CARGO_HOME=str(work / "cargo-home"), CARGO_TARGET_DIR=str(work / "rust-target"),
               MACOSX_DEPLOYMENT_TARGET="14.0")
    swift = SWIFT / "swiftc"
    resource = WASI / "swift.xctoolchain/usr/lib/swift_static"

    def run(label, command, *, extra=None, cwd=ROOT, **options):
        command_recorder = recorder if cwd == ROOT else CommandRecorder(logs, report["commands"], cwd)
        return command_recorder.run(label, command, env=env | (extra or {}), **options)

    def trace(label):
        return (logs / (label + ".stderr")).read_text()

    def run_reactor(label, wasm, *flags, **options):
        commands = report["commands"]
        command_index = len(commands)
        try:
            return run(label, [owned, wasm, *flags], **options)
        finally:
            if len(commands) > command_index and commands[command_index]["exitCode"] == 74:
                report["frozenOwner"] = True

    def run_owner(label, wasm, expected, variant="base"):
        frames = run_reactor(label, wasm, "--swift-6.3.3-ui256", expected=(0, 74), timeout=45)
        if report.get("frozenOwner"):
            raise RuntimeError("Owner closure unresolved")
        if expected != frames or len(frames.splitlines()) != 6:
            raise ValueError(f"{label} differed from the six exact Node frames")
        check_journey(frames.splitlines()[-1], variant)
        return parse_sample(trace(label))

    def build_wasm(label, fixture, entry, flags):
        wasm = work / f"{label}.wasm"
        run(f"build-{label}", [
            swift, "-target", "wasm32-unknown-wasip1", "-sdk", WASI / "WASI.sdk",
            "-resource-dir", resource, "-Xclang-linker", "-resource-dir", "-Xclang-linker",
            resource / "clang", "-static-stdlib", "-module-name", "FieldLogSpike",
            "-Osize", "-gnone", "-parse-as-library", "-module-cache-path", work / "wasi-modules",
            "-Xlinker", "--strip-all", *flags, fixture, HERE / entry, "-o", wasm,
        ])
        return wasm

    def build_reactor(label, fixture, defines=()):
        wasm = build_wasm(label, fixture, "Reactor.swift", [
            "-Xclang-linker", "-mexec-model=reactor",
            "-Xlinker", "--export=mixer_guest_ui_start_v3",
            "-Xlinker", "--export=mixer_guest_ui_event_v3",
            "-Xlinker", "--export=mixer_guest_ui_ready_v3",
            *defines,
        ])
        artifact = wasm.read_bytes()
        report["artifacts"][label] = {"sha256": digest(wasm), "rawBytes": len(artifact),
                                      "gzip9Bytes": len(gzip.compress(artifact, 9, mtime=0))}
        return wasm

    try:
        node, zstd = shutil.which("node"), shutil.which("zstd")
        if not node or not zstd:
            raise ValueError("Node and Zstandard are required")
        report["versions"] = {label: run(label, command).strip() for label, command in {
            "revision": ["/usr/bin/git", "rev-parse", "HEAD"],
            "vm-tree": ["/usr/bin/git", "rev-parse", "HEAD:vm"],
            "updates-tree": ["/usr/bin/git", "rev-parse", "HEAD:updates"],
            "host": ["/usr/bin/sw_vers"],
            "swift": [swift, "--version"],
            "rust": [RUST / "rustc", "--version"],
            "node": [node, "--version"],
            "zstd": [zstd, "--version"],
            "load-before": ["/usr/bin/uptime"],
            "logical-cpus": ["/usr/sbin/sysctl", "-n", "hw.logicalcpu"],
        }.items()}
        report["sources"] = {name: digest(HERE / name) for name in
                             ("FieldLog.swift", "Reactor.swift", "OwnedReactor.rs",
                              "RowSnapshotCheck.swift", "deferred-rows.patch", "oracle.mjs",
                              "CheckSignedAdmission.swift", "compare_row_snapshots.py")}
        sdk = run("macos-sdk", ["/usr/bin/xcrun", "--no-cache", "--sdk", "macosx", "--show-sdk-path"]).strip()
        eager = HERE / "FieldLog.swift"
        deferred = work / "FieldLog.swift"
        shutil.copyfile(eager, deferred)
        run("apply-deferred-rows", ["/usr/bin/patch", "-F", "0", "-p1", "-i", HERE / "deferred-rows.patch"], cwd=work)
        report["deferredSourceSHA256"] = digest(deferred)
        arms = {"eager": eager, "deferred": deferred}
        paths = {}
        oracles = {}
        for label, fixture in arms.items():
            paths[label] = build_reactor(label, fixture)
            oracles[label] = run(f"node-{label}", [node, "--no-warnings", HERE / "oracle.mjs", "reactor", paths[label]])
            check = work / f"rows-{label}"
            run(f"build-rows-{label}", [
                swift, "-target", "arm64-apple-macosx14.0", "-sdk", sdk, "-Osize",
                "-parse-as-library", "-module-cache-path", work / "macos-modules",
                fixture, HERE / "RowSnapshotCheck.swift", "-o", check,
            ])
            native_rows = run(f"check-rows-{label}", [check]).strip()
            wasm_check = build_wasm(f"rows-{label}-wasi", fixture, "RowSnapshotCheck.swift", [])
            wasi_rows = run(f"check-rows-{label}-wasi", [
                node, "--no-warnings", HERE / "oracle.mjs", "command", wasm_check,
            ]).strip()
            if not native_rows or native_rows != wasi_rows:
                raise ValueError(f"{label}: native and WASI row checks differ")
            report[f"{label}RowCheck"] = {"native": native_rows, "wasi": wasi_rows}
        if oracles["eager"] != oracles["deferred"]:
            raise ValueError("Node reactor output changed")

        run("build-vm", [
            RUST / "cargo", "build", "--manifest-path", ROOT / "vm/Cargo.toml", "--offline",
            "--locked", "--release", "--lib", "--features", "experimental-swift-reactor",
        ], timeout=180)
        owned = work / "owned-reactor"
        run("build-owner", [
            RUST / "rustc", "--edition=2021", "-O", "--cfg", "s2_host_benchmark",
            "--extern", f"mixer_vm={work / 'rust-target/release/libmixer_vm.rlib'}",
            HERE / "OwnedReactor.rs", "-o", owned,
        ])
        for label, path in paths.items():
            fixed = f"fixed34-{label}"
            stdout = run_reactor(fixed, path, expected=(10,))
            verify_fixed_refusal(report["commands"][-1]["exitCode"], stdout + trace(fixed))

        for pair in range(5):
            order = list(arms) if pair % 2 == 0 else list(reversed(arms))
            report["samples"].append({label: run_owner(f"{label}-{pair + 1}", paths[label], oracles[label])
                                      for label in order})
        for key in ("wallMicros", "threadCPUMicros", "instructions"):
            changes = [pair["deferred"]["load"][key] - pair["eager"]["load"][key]
                       for pair in report["samples"]]
            report.setdefault("firstUsableListPaired", {})[key] = {
                "medianDelta": median(changes), "range": [min(changes), max(changes)],
                "deferredFasterPairs": sum(delta < 0 for delta in changes),
            }
        report["loadAfter"] = run("load-after", ["/usr/bin/uptime"]).strip()

        update = build_reactor("deferred-update", deferred, ["-D", "UPDATE"])
        patch = work / "deferred-update.zst"
        reconstructed = work / "reconstructed.wasm"
        base_flag = f"--patch-from={paths['deferred']}"
        run("compress-update", [zstd, "--single-thread", "-9", base_flag, update, "-o", patch])
        run("reconstruct-update", [zstd, "-d", base_flag, patch, "-o", reconstructed])
        if reconstructed.read_bytes() != update.read_bytes():
            raise ValueError("Update diff did not reproduce the compiled update")
        oracle_update = run("node-update", [node, "--no-warnings", HERE / "oracle.mjs", "reactor", update])
        if strict_json(oracle_update.splitlines()[3])["blankRejected"] is not True:
            raise ValueError("Updated guest did not reject whitespace-only Save")
        report["update"] = {"compressedBytes": patch.stat().st_size, "sha256": digest(patch),
                            "byteExactReconstruction": True,
                            "guest": run_owner("reconstructed-update", reconstructed, oracle_update, "update")}
        report["signedAdmission"] = check_signed_admission(run, work, reconstructed, patch,
                                                          report["versions"]["revision"])
        handoff = run_dir / "handoff"
        handoff.mkdir()
        for name, path in (("reactor-base.wasm", paths["deferred"]), ("reactor-update.wasm", update),
                           ("reactor-update.zst", patch)):
            shutil.copyfile(path, handoff / name)
        for name, oracle in (("oracle.json", oracles["deferred"]), ("update-oracle.json", oracle_update)):
            frames = [strict_json(line) for line in oracle.splitlines()]
            (handoff / name).write_text(json.dumps(frames, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["handoff"] = {path.name: digest(path) for path in sorted(handoff.iterdir())}
        report["completed"] = True
    except Exception as error:
        report.update(completed=False, error=str(error))
        raise
    finally:
        if (all(item["terminalCustody"] in ("TERMINAL", "NOT_STARTED") for item in report["commands"])
                and not report.get("frozenOwner")):
            shutil.rmtree(work)
            report["cleanup"] = "Terminal command groups observed. Disposable work removed."
        else:
            report["cleanup"] = "Unresolved custody. Preserve run directory."
        (run_dir / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print(run_dir / "receipt.json")


if __name__ == "__main__":
    main()
