#!/usr/bin/env python3
"""Replay the full-Swift command and reactor on macOS and check Mixer VM admission."""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
from statistics import median
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest, strict_json

SWIFT = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
WASI = (
    Path.home() / ".swiftpm/swift-sdks/swift-6.3.3-RELEASE_wasm.artifactbundle"
    / "swift-6.3.3-RELEASE_wasm/wasm32-unknown-wasip1"
)
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
XCODE = Path("/Applications/Xcode_26.6.app/Contents/Developer")
EXPECTED = dict(
    initialCount=0, loadedCount=1000,
    firstRow="Inspection 0 · North yard", lastRow="Inspection 999 · North yard",
    initialTitle="Inspection 527", blankRejected=True,
    editedTitle="Pompé inspection 東京", reopenedTitle="Pompé inspection 東京",
    observedSave=True, id="00000000-0000-4000-8000-00000000020F",
    created=1_790_031_620,
)


def check_journey(stdout, variant):
    value = strict_json(stdout)
    expected = EXPECTED | {"saveLabel": "Save inspection" if variant == "update" else "Save"}
    if value != expected:
        raise ValueError(f"{variant} journey differs: {value}")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="fresh run directory name in verification/local")
    parser.add_argument("--swift", type=Path, default=SWIFT, help="Swift 6.3.3 bin directory")
    parser.add_argument("--wasi", type=Path, default=WASI, help="Swift 6.3.3 wasm32-unknown-wasip1 SDK directory")
    parser.add_argument("--rust", type=Path, default=RUST, help="Rust 1.99.0 bin directory")
    parser.add_argument("--xcode", type=Path, default=XCODE, help="compatible Xcode Developer directory")
    parser.add_argument("--samples", type=int, choices=range(1, 8), default=5)
    parser.add_argument("--owned-ui-only", action="store_true",
                        help="compare both validators on one pinned reactor build and try the owned journey")
    parser.add_argument("--owned-ui-256", action="store_true",
                        help="use the existing 256-frame, 256-pin and 256-entry UI geometry")
    args = parser.parse_args()
    if args.owned_ui_256 and not args.owned_ui_only:
        parser.error("--owned-ui-256 requires --owned-ui-only")
    if not args.name or not all(char.isascii() and (char.isalnum() or char in "-_") for char in args.name):
        parser.error("use an ASCII run name with letters, digits, hyphens, or underscores")

    run_dir = ROOT / "verification/local" / args.name
    run_dir.mkdir(parents=True, mode=0o700)
    work = run_dir / "work"
    logs = run_dir / "logs"
    work.mkdir()
    logs.mkdir()
    tmp = work / "tmp"
    tmp.mkdir()
    report = {"scope": "macOS host diagnostic", "commands": [], "variants": {}}
    recorder = CommandRecorder(logs, report["commands"], ROOT, log_limit=2_000_000)
    env = clean_environment()
    env.update(
        TMPDIR=str(tmp), DEVELOPER_DIR=str(args.xcode), CLANG_MODULE_CACHE_PATH=str(work / "clang-cache"),
        SWIFT_MODULECACHE_PATH=str(work / "swift-cache"), RUSTC=str(args.rust / "rustc"),
        CARGO_HOME=str(work / "cargo-home"), CARGO_TARGET_DIR=str(work / "rust-target"),
        PATH=str(args.rust) + os.pathsep + env["PATH"],
        MACOSX_DEPLOYMENT_TARGET="14.0",
    )

    def run(label, command, *, extra=None, expected=(0,), timeout=120):
        return recorder.run(label, command, env=env | (extra or {}), expected=expected, timeout=timeout)

    def stderr(label):
        return (logs / (label + ".stderr")).read_text()

    try:
        node, zstd = (shutil.which(tool) for tool in ("node", "zstd"))
        if not args.owned_ui_only and (not node or not zstd):
            raise ValueError("node and zstd are required")
        swift, linker, cargo = args.swift / "swiftc", args.swift / "wasm-ld", args.rust / "cargo"
        tools = {
            "revision": ["/usr/bin/git", "rev-parse", "HEAD"],
            "tree": ["/usr/bin/git", "rev-parse", "HEAD^{tree}"],
            "vm-tree": ["/usr/bin/git", "rev-parse", "HEAD:vm"],
            "host": ["/usr/bin/sw_vers"],
            "swift": [swift, "--version"],
            "linker": [linker, "--version"],
            "cargo": [cargo, "--version"],
            "rustc": [args.rust / "rustc", "--version"],
            "load": ["/usr/bin/uptime"],
            "logical-cpus": ["/usr/sbin/sysctl", "-n", "hw.logicalcpu"],
        }
        if not args.owned_ui_only:
            tools.update({"node": [node, "--version"], "zstd": [zstd, "--version"]})
        report["versions"] = {
            label: run(label, command).strip()
            for label, command in tools.items()
        }
        report["sources"] = {p.name: digest(p) for p in HERE.iterdir() if p.is_file()}
        resource = args.wasi / "swift.xctoolchain/usr/lib/swift_static"
        report["sdk"] = {
            str(p.relative_to(args.wasi)): digest(p)
            for p in (args.wasi / "swift-sdk.json", args.wasi / "toolset.json",
                      resource / "wasi/libswiftCore.a", resource / "wasi/libswift_Concurrency.a",
                      resource / "wasi/libswiftObservation.a", resource / "wasi/libFoundationEssentials.a")
        }
        def build_wasm(mode, variant, path):
            link_map = path.with_suffix(".map")
            extra_flags = []
            extra_defines = {"update": ["-D", "UPDATE"], "icu": ["-D", "ICU_CONTROL"]}
            if mode == "reactor":
                extra_flags = ["-Xclang-linker", "-mexec-model=reactor"]
                for entry in ("start", "event", "ready"):
                    extra_flags += ["-Xlinker", f"--export=mixer_guest_ui_{entry}_v3"]
            entry_file = HERE / ("Reactor.swift" if mode == "reactor" else "Command.swift")
            run(f"{mode}-{variant}-wasm-build",
                [swift, "-target", "wasm32-unknown-wasip1", "-sdk", args.wasi / "WASI.sdk",
                 "-resource-dir", resource, "-Xclang-linker", "-resource-dir", "-Xclang-linker",
                 resource / "clang", "-static-stdlib", "-module-name", "FieldLogSpike",
                 "-Osize", "-gnone", "-parse-as-library", "-module-cache-path", work / "wasi-module-cache",
                 "-Xlinker", "--strip-all", "-Xlinker", f"-Map={link_map}", *extra_flags,
                 *extra_defines.get(variant, []), HERE / "FieldLog.swift", entry_file, "-o", path])
            data = path.read_bytes()
            archives = {line.split("/wasi/", 1)[1].split("(", 1)[0]
                        for line in link_map.read_text().splitlines()
                        if "/wasi/" in line and ".a(" in line}
            icu = sorted(archive for archive in archives if
                         "icu" in archive.lower() or "Internationalization" in archive)
            icu_members = sorted({
                line.split("lib_FoundationICU.a(", 1)[1].split(")", 1)[0]
                for line in link_map.read_text().splitlines() if "lib_FoundationICU.a(" in line
            })
            return dict(
                rawBytes=len(data), sha256=digest(path),
                gzip9Bytes=len(gzip.compress(data, compresslevel=9, mtime=0)),
                linkedRuntimeArchives=sorted(archives), icuContributors=icu,
                icuDataMembers=[member for member in icu_members
                                if "icudt" in member.lower() or "icu_packaged_data" in member],
            )

        def check_reactor(stdout, variant):
            lines = stdout.splitlines()
            if len(lines) != 6:
                raise ValueError(f"{variant} reactor returned {len(lines)} frames, expected 6")
            frames = [strict_json(line) for line in lines]
            initial, loaded, opened, refused, saved, _ = frames
            if (initial["initialCount"] != 0 or initial["loadedCount"] != 0
                or loaded["loadedCount"] != 1_000 or loaded["initialTitle"] != ""
                or opened["initialTitle"] != EXPECTED["initialTitle"]
                or not refused["blankRejected"] or refused["editedTitle"] != ""
                or not saved["observedSave"] or saved["reopenedTitle"] != ""):
                raise ValueError(f"{variant} reactor frame sequence differs: {frames}")
            check_journey(lines[-1], variant)
            return frames

        def build_owned_reactor(*cargo_targets):
            run("owned-build", [cargo, "build", "--manifest-path", ROOT / "vm/Cargo.toml", "--offline",
                                "--locked", "--release", "--features", "experimental-swift-reactor",
                                "--lib", *cargo_targets], timeout=240)
            rust_release = work / "rust-target/release"
            owned_reactor = work / "owned-reactor"
            run("owned-reactor-build", [args.rust / "rustc", "--edition=2021", "-O",
                "--extern", f"mixer_vm={rust_release / 'libmixer_vm.rlib'}",
                HERE / "OwnedReactor.rs", "-o", owned_reactor])
            return owned_reactor

        def owned_reactor_result(label, command, variant):
            output = run(label, command, expected=(0, 10, 20, 74))
            exit_code = report["commands"][-1]["exitCode"]
            trace = stderr(label).splitlines()
            if exit_code == 74:
                report["ownedReactorClosureUnknown"] = True
                raise RuntimeError("Owned reactor returned frozen or unobserved closure")
            state = {"exitCode": exit_code, "report": trace}
            if exit_code == 0:
                state["journey"] = check_reactor(output, variant)
            return state

        if args.owned_ui_only:
            owned_reactor = build_owned_reactor()
            wasm = work / "reactor-base.wasm"
            report["artifact"] = build_wasm("reactor", "base", wasm)
            report["fixed34"] = baseline = owned_reactor_result(
                "fixed34-baseline", [owned_reactor, wasm], "base")
            if baseline["exitCode"] != 10 or 'code: "swift_import_count"' not in baseline["report"][0]:
                raise ValueError("Legacy UI validator did not reproduce swift_import_count")
            profile = "--swift-6.3.3-ui256" if args.owned_ui_256 else "--swift-6.3.3"
            report["swift633"] = execution = owned_reactor_result(
                "swift633-owned", ["/usr/bin/time", "-l", owned_reactor, wasm, profile], "base")
            if args.owned_ui_256:
                if execution["exitCode"] != 0:
                    raise ValueError("The 256-frame owned reactor did not complete the verified journey")
            elif execution["exitCode"] != 20 or not any("swift_frame_depth" in line for line in execution["report"]):
                raise ValueError("The 64-frame control did not reproduce the expected depth refusal")
            report["completed"] = True
            return

        def measure_oracle(mode, paths, result):
            for sample in range(args.samples):
                for variant, wasm in paths.items():
                    label = f"{mode}-{variant}-node-{sample + 1}"
                    stdout = run(label, [node, "--no-warnings", HERE / "oracle.mjs", mode, wasm],
                                 expected=(0, 1))
                    state = result["variants"][variant]
                    exit_code = report["commands"][-1]["exitCode"]
                    if exit_code != 0:
                        state.setdefault("oracleErrors", []).append(label)
                        continue
                    output = (check_reactor(stdout, variant) if mode == "reactor"
                              else check_journey(stdout, variant))
                    state["oracleOutput"] = output
                    state.setdefault("oracleSamples", []).append(strict_json(stderr(label)))

            for state in result["variants"].values():
                samples = state.get("oracleSamples", [])
                if not samples:
                    continue
                metrics = ("readAndCompileMs", "instantiateMs", "initialLinearBytes",
                           "finalLinearBytes", "peakProcessRSSBytes")
                values = {metric: [row[metric] for row in samples] for metric in metrics}
                if mode == "reactor":
                    values.update({f"{turn}Ms": [row["turns"][turn] for row in samples]
                                   for turn in samples[0]["turns"]})
                else:
                    values["completeJourneyMs"] = [row["completeJourneyMs"] for row in samples]
                state["oracleSummary"] = {metric: dict(median=median(column), min=min(column), max=max(column))
                                          for metric, column in values.items()}

        def measure_patch(paths):
            base, update = paths["base"], paths["update"]
            patch = update.with_suffix(".zst")
            reconstructed = update.with_suffix(".reconstructed.wasm")
            run(f"{update.stem}-patch-encode",
                [zstd, "--single-thread", "-9", f"--patch-from={base}", update, "-o", patch])
            run(f"{update.stem}-patch-decode", [zstd, "-d", f"--patch-from={base}", patch, "-o", reconstructed])
            if reconstructed.read_bytes() != update.read_bytes():
                raise ValueError("diff reconstruction does not equal the target artifact")
            return dict(compressedBytes=patch.stat().st_size, assetBytes=0, sha256=digest(patch),
                        reconstructsTarget=True, signed=False)

        sdk = run("macos-sdk", ["/usr/bin/xcrun", "--no-cache", "--sdk", "macosx", "--show-sdk-path"]).strip()
        for variant in ("base", "update"):
            native = work / f"{variant}-macos"
            defines = ["-D", "UPDATE"] if variant == "update" else []
            run(f"{variant}-host-build",
                [swift, "-target", "arm64-apple-macosx14.0", "-sdk", sdk,
                 "-module-name", "FieldLogSpike", "-Osize", "-parse-as-library",
                 "-module-cache-path", work / "native-module-cache", *defines,
                 HERE / "FieldLog.swift", HERE / "Command.swift", "-o", native])
            report["variants"][variant] = check_journey(run(f"{variant}-host", [native]), variant)

        owned_reactor = build_owned_reactor("--example", "taskeditor_owned_command")
        owned_command = work / "rust-target/release/examples/taskeditor_owned_command"

        report["approaches"] = {}
        for mode in ("command", "reactor"):
            paths = {variant: work / f"{mode}-{variant}.wasm" for variant in ("base", "update")}
            result = report["approaches"][mode] = {"variants": {}}
            for variant, wasm in paths.items():
                result["variants"][variant] = {"artifact": build_wasm(mode, variant, wasm)}

                guest_stdout = work / f"{variant}-owned.stdout"
                if mode == "command":
                    expected = (0, 10, 20)
                    output = run(f"{mode}-{variant}-owned", [owned_command], expected=expected, extra={
                        "MIXER_R110_MODULE": str(wasm), "MIXER_R110_STDOUT": str(guest_stdout),
                        "MIXER_R110_STDERR": str(work / f"{variant}-owned.stderr"),
                    })
                    trace = output
                else:
                    label = f"{mode}-{variant}-owned"
                    result["variants"][variant]["owned"] = owned_reactor_result(
                        label, [owned_reactor, wasm], variant)
                    continue
                exit_code = report["commands"][-1]["exitCode"]
                state = result["variants"][variant]["owned"] = {"exitCode": exit_code, "report": trace.splitlines()}
                if exit_code == 0:
                    state["journey"] = check_journey(guest_stdout.read_text(), variant)

            result["patch"] = measure_patch(paths)
            measure_oracle(mode, paths, result)

        report["icuControl"] = build_wasm("command", "icu", work / "command-icu.wasm")
        if not report["icuControl"]["icuDataMembers"]:
            raise ValueError("ICU-positive control did not link ICU data")
        if any(state["artifact"]["icuContributors"] for approach in report["approaches"].values()
               for state in approach["variants"].values()):
            raise ValueError("ICU or FoundationInternationalization entered a lean build")
        if any(state.get("oracleErrors") for approach in report["approaches"].values()
               for state in approach["variants"].values()):
            raise ValueError("A command or reactor failed the host oracle")
        report["completed"] = True
    except Exception as exc:
        report["completed"] = False
        report["error"] = str(exc)
        raise
    finally:
        settled = all(item["terminalCustody"] in ("TERMINAL", "NOT_STARTED") for item in report["commands"])
        if settled and not report.get("ownedReactorClosureUnknown"):
            shutil.rmtree(work)
            report["cleanup"] = "Removed work directory after command groups were confirmed terminal."
        else:
            report["cleanup"] = "UNKNOWN custody. Preserve the run directory."
        (run_dir / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
        print(run_dir / "receipt.json")


if __name__ == "__main__":
    main()
