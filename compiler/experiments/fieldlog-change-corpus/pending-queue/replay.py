#!/usr/bin/env python3
"""Replay the historical ordinary test and the v80 signed F10 host fixture on macOS."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MIXER = "5f4277e12e4872df43483307ec607a65e87dbae1"
MIXER_TREE = "19980da47ccc682b84c15c1e77e81eb5b02a2a5d"
CORPUS = "compiler/experiments/fieldlog-change-corpus/corpus.json"
GENERATED = "Integrations/GeneratedReport"
MODULE_FILES = ("FieldLogModels/Workspace.swift", "FieldLogStorage/WorkspaceRepository.swift")
PROJECTION_FILES = ("QueueProjection.swift", "PendingQueueTests.swift")
EXPORTS = ("mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1",
           "mixer_guest_ui_hydrate_v1", "mixer_guest_capability_ready_v1")


def replace_once(path, before, after):
    source = path.read_text()
    if source.count(before) != 1:
        raise ValueError(f"Unexpected pinned fixture source: {path.name}")
    path.write_text(source.replace(before, after))


def prepare_package(package, generated, after, digest):
    sources = package / "Sources"
    tests = package / "Tests/MixerCapabilityActivationTests"
    for name in MODULE_FILES:
        (sources / name).parent.mkdir()
        shutil.copyfile(generated / "Sources" / name, sources / name)
    for name in PROJECTION_FILES:
        shutil.copyfile(HERE / name, tests / name)
    replace_once(package / "Package.swift",
        '.testTarget(name: "MixerCapabilityActivationTests", dependencies: ["MixerCapabilityActivation"], resources: [.copy("Fixtures")]),',
        '''.target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .testTarget(name: "MixerCapabilityActivationTests",
            dependencies: ["MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage"],
            sources: ["GuestUISignedFixture.swift", "PendingQueueTests.swift", "QueueProjection.swift"],
            resources: [.copy("Fixtures")]),''')
    signer = tests / "GuestUISignedFixture.swift"
    replace_once(signer, 'key = try .init(rawRepresentation: Data(repeating: 0x53, count: 32))', 'key = .init()')
    replace_once(signer, '.text(String(repeating: "5", count: 40))', f'.text("{after}")')
    replace_once(signer, '"fuel": .uint(100_000)', '"fuel": .uint(1_000_000)')
    return {"testPackageSHA256": digest(package / "Package.swift"), "testSignerSHA256": digest(signer)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Fresh directory name under verification/local")
    parser.add_argument("--fieldlog", type=Path, help="Existing separate repository with the pinned history")
    parser.add_argument("--guest-tools", type=Path, default=Path.home() /
                        "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin")
    parser.add_argument("--rust-tools", type=Path, default=Path.home() /
                        ".rustup/toolchains/stable-aarch64-apple-darwin/bin")
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", args.name) or args.jobs < 1:
        parser.error("Expected one safe directory component and a positive job count")

    out = ROOT / "verification/local" / args.name
    out.mkdir(parents=True, exist_ok=False)
    for name in ("logs", "tmp", "cache", "app", "mixer", "ordinary-sdk", "ordinary-workspaces", "signed", "lib"):
        (out / name).mkdir()
    git = shutil.which("git")
    swift = shutil.which("swift")
    support = out / "qualification_support.py"
    support.write_bytes(subprocess.check_output(
        [git, "show", f"{MIXER}:compiler/qualification_support.py"], cwd=ROOT, timeout=10))
    runner = runpy.run_path(str(support))
    digest = runner["digest"]
    commands = []
    report = {"status": "incomplete", "commands": commands}
    recorder = runner["CommandRecorder"](out / "logs", commands, ROOT)
    env = runner["clean_environment"]()
    env.update(TMPDIR=str(out / "tmp"), GIT_TERMINAL_PROMPT="0")
    # The pinned Cargo executable needs its matching rustc in PATH.
    env["PATH"] = str(args.rust_tools) + ":" + env["PATH"]

    def run(name, *argv, extra=None, timeout=120):
        return recorder.run(name, argv, env=env | (extra or {}), timeout=timeout)

    def archive(name, repo, revision, destination, *paths):
        bundle = out / (name + ".tar")
        run(name, git, "-C", repo, "archive", f"--output={bundle}", revision, *paths)
        with tarfile.open(bundle) as files:
            files.extractall(destination, filter="data")
        sha = digest(bundle)
        bundle.unlink()
        return sha

    def oid(name, repo, ref):
        return run(name, git, "-C", repo, "rev-parse", ref).strip()

    try:
        for label, command in {
            "host": ("/usr/bin/sw_vers",), "hostSwift": (swift, "--version"),
            "guestSwift": (args.guest_tools / "swiftc", "--version"),
            "linker": (args.guest_tools / "wasm-ld", "--version"),
            "clang": (args.guest_tools / "clang", "--version"),
            "rust": (args.rust_tools / "rustc", "--version"),
            "git": (git, "--version"),
        }.items():
            report.setdefault("tools", {})[label] = run("version-" + label, *command).strip()

        tree = oid("mixer-tree", ROOT, MIXER + "^{tree}")
        if tree != MIXER_TREE:
            raise ValueError("Mixer pin tree differs")
        corpus = run("corpus", git, "show", f"{MIXER}:{CORPUS}")
        manifest = json.loads(corpus)
        case = next(row for row in manifest["cases"] if row["id"] == "F10")
        pin, after, before = manifest["pin"], case["after"], case["before"]
        repo = args.fieldlog.resolve() if args.fieldlog else out / "fieldlog-git"
        if not args.fieldlog:
            run("fieldlog-clone", git, "clone", "--no-checkout", manifest["repository"], repo)
        pin_tree = oid("fieldlog-tree", repo, pin + "^{tree}")
        if pin_tree != manifest["pinTree"] or oid("f10-parent", repo, after + "^") != before:
            raise ValueError("FieldLog pin or F10 ancestry differs")
        report["inputs"] = {
            "mixer": MIXER, "mixerTree": tree, "fieldlog": pin, "fieldlogTree": pin_tree,
            "corpusSHA256": hashlib.sha256(corpus.encode()).hexdigest(),
            "f10Before": before, "f10After": after, "f10Anchors": case["anchors"],
            "fixtureSHA256": {name: digest(HERE / name)
                              for name in (*PROJECTION_FILES, "Guest.swift", "Imports.c", "replay.py")},
            "custodianSHA256": digest(support),
        }
        for number, anchor in enumerate(case["anchors"]):
            source = anchor["path"]
            absent = run(f"anchor-{number}-before", git, "-C", repo, "ls-tree", before, "--", source)
            if anchor["beforeBlob"] is not None or absent:
                raise ValueError(f"F10 anchor unexpectedly exists in the first parent: {source}")
            if (oid(f"anchor-{number}-introducing", repo, f"{after}:{source}") != anchor["afterBlob"]
                    or oid(f"anchor-{number}-pinned", repo, f"{pin}:{source}") != anchor["afterBlob"]):
                raise ValueError(f"F10 anchor changed: {source}")
            lines = run(f"anchor-{number}-source", git, "-C", repo, "show", f"{after}:{source}").splitlines(keepends=True)
            start, end = anchor["afterLines"]
            sha = hashlib.sha256("".join(lines[start - 1:end]).encode()).hexdigest()
            if sha != anchor["afterLinesSHA256"]:
                raise ValueError(f"F10 excerpt changed: {source}")
        modules = {}
        for number, file in enumerate(MODULE_FILES):
            source = f"{GENERATED}/Sources/{file}"
            introduced = oid(f"app-{number}-introducing", repo, f"{after}:{source}")
            if oid(f"app-{number}-pinned", repo, f"{pin}:{source}") != introduced:
                raise ValueError(f"FieldLog module differs between historical and pinned source: {file}")
            modules[source] = introduced
        report["inputs"]["unchangedAppBlobs"] = modules

        _, sdk_pin = manifest["suitePins"]["generated-pin"]
        report["inputs"]["ordinarySDK"] = sdk_pin
        report["inputs"]["ordinarySDKTree"] = oid("ordinary-sdk-tree", ROOT, sdk_pin + ":sdk")
        generated = out / "app"
        mixer = out / "mixer"
        report["archives"] = {
            "fieldlog": archive("fieldlog-archive", repo, pin + ":" + GENERATED, generated),
            "ordinarySDK": archive("ordinary-sdk-archive", ROOT, sdk_pin + ":sdk", out / "ordinary-sdk"),
            "mixerV80": archive("mixer-v80-archive", ROOT, MIXER, mixer, "capability-activation",
                "experimental-capability-runtime", "runtime-identity", "updates", "sdk", "vm", "contracts"),
        }
        swift_flags = ["--cache-path", out / "cache", "--disable-prefetching", "--jobs", args.jobs]
        ordinary = run("ordinary-historical-test", swift, "test", "--package-path", generated,
            "--scratch-path", out / "ordinary-build", *swift_flags, "--filter",
            "PaginationContractTests/testAllPagesGlobalOrderQueueAndExactUnicodeRecords",
            extra={"FIELDLOG_MIXER_SDK": str(out / "ordinary-sdk"),
                   "FIELDLOG_WORKSPACE": str(out / "ordinary-workspaces")})
        report["ordinaryObservations"] = [line for line in ordinary.splitlines()
                                          if line.startswith(("PAGE outbox:", "PASS pagination:"))]
        if len(report["ordinaryObservations"]) != 4:
            raise ValueError("The original FieldLog test did not produce the expected observations")

        package = mixer / "capability-activation"
        report["inputs"].update(prepare_package(package, generated, after, digest))
        vm = mixer / "vm"
        run("owned-vm-build", args.rust_tools / "cargo", "build", "--offline", "--locked",
            "--release", "--lib", "--features", "experimental-capability-native",
            "--manifest-path", vm / "Cargo.toml", "--target-dir", out / "rust")
        library = out / "rust/release/libmixer_vm.a"
        (out / "lib/libmixer_vm_capability_experimental.a").symlink_to(library)
        report["vmArchiveSHA256"] = digest(library)

        imports = out / "Imports.o"
        run("compile-import-abi", args.guest_tools / "clang", "--target=wasm32-unknown-none-wasm",
            "-Os", "-c", HERE / "Imports.c", "-o", imports, timeout=30)
        report["payloads"] = {}
        for name, flags in (("compact", ()), ("historical", ("-D", "HISTORICAL_QUEUE_LAYOUT"))):
            obj, wasm = out / (name + ".o"), out / (name + ".wasm")
            run(name + "-swift", args.guest_tools / "swiftc", "-target", "wasm32-unknown-none-wasm",
                "-enable-experimental-feature", "Embedded", "-enable-experimental-feature", "Extern",
                "-whole-module-optimization", "-Osize", "-parse-as-library", "-Xfrontend",
                "-disable-stack-protector", *flags, "-emit-object", HERE / "QueueProjection.swift",
                HERE / "Guest.swift", "-o", obj, timeout=30)
            run(name + "-link", args.guest_tools / "wasm-ld", "--fatal-warnings", "--no-entry", "--gc-sections",
                "--strip-all", "-z", "stack-size=8192", "--max-memory=65536",
                *("--export=" + export for export in EXPORTS), obj, imports, "-o", wasm, timeout=30)
            report["payloads"][name] = {"bytes": wasm.stat().st_size, "sha256": digest(wasm)}

        signed = run("signed-installed-test", swift, "test", "--package-path", package,
            "--scratch-path", out / "signed-build", *swift_flags, "--force-resolved-versions",
            "-Xcc", "-I", "-Xcc", vm / "include", "-Xlinker", "-L", "-Xlinker", out / "lib",
            "--filter", "PendingQueueTests/testSignedHistoricalPendingQueue",
            extra={"FIELDLOG_F10_RUN": str(out / "signed")})
        report["signedObservations"] = [line for line in signed.splitlines() if line.startswith("F10 ")]
        if len(report["signedObservations"]) != 8:
            raise ValueError("The signed F10 test did not produce the expected observations")
        report["status"] = "macos-compact-pass-historical-layout-refused"
    finally:
        report["observedUTC"] = datetime.now(timezone.utc).isoformat()
        (out / "run.json").write_text(json.dumps(report, indent=2) + "\n")
        print(out / "run.json")


if __name__ == "__main__":
    main()
