"""Exercise the S3 reactor with the reviewed Swift 6.3.3 experimental VM."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from replay import HERE, ROOT, SCRATCH, SDK, SOURCES, TOOLCHAIN

sys.path.insert(0, str(ROOT / "compiler"))
from qualification_support import CommandRecorder, clean_environment, digest

VM_REVISION = "1ee170500c73e3da935e1d1cbb4bbba77d24e8d8"
VM_TREE = "d3f0d6c10bf38c46299314a5aff319f18785dc2c"
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
S2 = "compiler/experiments/swiftui-full-guest"


def check_s2(frames):
    initial, loaded, opened, refused, saved, reopened = map(json.loads, frames)
    if (initial["loadedCount"], loaded["loadedCount"], opened["initialTitle"],
        refused["blankRejected"], saved["observedSave"]) != (0, 1000, "Inspection 527", True, True):
        raise ValueError("Linked S2 intermediate snapshots differ")
    if reopened != dict(initialCount=0, loadedCount=1000, firstRow="Inspection 0 · North yard",
                        lastRow="Inspection 999 · North yard", initialTitle="Inspection 527",
                        saveLabel="Save", blankRejected=True, editedTitle="Pompé inspection 東京",
                        reopenedTitle="Pompé inspection 東京", observedSave=True,
                        id="00000000-0000-4000-8000-00000000020F", created=1790031620):
        raise ValueError("Linked S2 final snapshot differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--link-s2", action="store_true", help="Link and run the real S2 workload alongside S3")
    options = parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="swiftui-s3g-owned-", dir=SCRATCH))
    print(run_dir, flush=True)
    work = run_dir / "work"
    work.mkdir()
    (work / "tmp").mkdir()
    logs = run_dir / "logs"
    logs.mkdir()

    report = {
        "scope": "macOS host experiment with the Rust-only experimental UI validator",
        "vmRevision": VM_REVISION,
        "vmTree": VM_TREE,
        "linkedS2": options.link_s2,
        "commands": [],
    }
    recorder = CommandRecorder(logs, report["commands"], work, log_limit=2_000_000)
    env = clean_environment()
    env.update(
        TMPDIR=str(work / "tmp"), CLANG_MODULE_CACHE_PATH=str(work / "clang-cache"),
        SWIFT_MODULECACHE_PATH=str(work / "swift-cache"),
        CARGO_HOME=str(work / "cargo-home"), CARGO_TARGET_DIR=str(work / "rust-target"),
        RUSTC=str(RUST / "rustc"), PATH=str(RUST) + os.pathsep + env["PATH"],
    )

    def run(label, *argv, expected=(0,), timeout=90):
        return recorder.run(label, argv, env=env, expected=expected, timeout=timeout)

    def exit_code():
        return report["commands"][-1]["exitCode"]

    try:
        swift = TOOLCHAIN / "swiftc"
        node = shutil.which("node")
        if node is None:
            raise ValueError("Node is required for the WASI control and import inventory")
        report["versions"] = {label: run(label, *argv).strip() for label, argv in {
            "revision": ["/usr/bin/git", "-C", ROOT, "rev-parse", "HEAD"],
            "host": ["/usr/bin/sw_vers"],
            "host-swift": ["/usr/bin/swiftc", "--version"],
            "guest-swift": [swift, "--version"],
            "guest-linker": [TOOLCHAIN / "wasm-ld", "--version"],
            "cargo": [RUST / "cargo", "--version"],
            "rustc": [RUST / "rustc", "--version"],
            "node": [node, "--version"],
        }.items()}
        report["sources"] = {path.name: digest(path) for path in
                             [*SOURCES, HERE / "OwnedReplay.rs", HERE / "oracle.mjs", Path(__file__)]}

        tree = run("vm-tree", "/usr/bin/git", "-C", ROOT, "rev-parse", f"{VM_REVISION}:vm").strip()
        if tree != VM_TREE:
            raise ValueError("VM tree differs from the reviewed S2 tree")
        archive = work / "vm.tar"
        run("vm-archive", "/usr/bin/git", "-C", ROOT, "archive", "--output", archive, VM_REVISION, "vm")
        run("vm-extract", "/usr/bin/tar", "-xf", archive)
        run("vm-build", RUST / "cargo", "build", "--manifest-path", work / "vm/Cargo.toml", "--offline",
            "--locked", "--release", "--features", "experimental-swift-reactor", "--lib", timeout=240)
        runner = work / "owned-replay"
        run("runner-build", RUST / "rustc", "--edition=2021", "-O", "--extern",
            f"mixer_vm={work / 'rust-target/release/libmixer_vm.rlib'}", HERE / "OwnedReplay.rs", "-o", runner)

        host = work / "s3-native"
        run("native-build", "/usr/bin/swiftc", "-swift-version", "6", "-parse-as-library",
            "-module-cache-path", work / "native-modules", *SOURCES, "-o", host)
        run("native-trace", host)

        resource = SDK / "swift.xctoolchain/usr/lib/swift_static"
        frontend = ["-swift-version", "6", "-target", "wasm32-unknown-wasip1",
                    "-sdk", SDK / "WASI.sdk", "-resource-dir", resource,
                    "-module-cache-path", work / "wasi-modules", "-parse-as-library", "-Osize", "-gnone"]
        swift_flags = [*frontend, "-static-stdlib", "-Xclang-linker", "-resource-dir",
                       "-Xclang-linker", resource / "clang", "-Xclang-linker", "-mexec-model=reactor",
                       "-Xlinker", "--strip-all"]
        node_guest = work / "s3.wasm"
        run("node-guest-build", swift, *swift_flags, "-DS3_GUEST",
            "-Xlinker", "--export=mixer_s3_replay", *SOURCES, "-o", node_guest)
        run("node-trace", node, "--no-warnings", HERE / "oracle.mjs", node_guest)
        native = (logs / "native-trace.stdout").read_bytes()
        if len(native.splitlines()) != 15 or native != (logs / "node-trace.stdout").read_bytes():
            raise ValueError("Native and Node traces differ or are incomplete")

        guest = work / "s3-owned.wasm"
        exports = [flag for entry in ("start", "event", "ready")
                   for flag in ("-Xlinker", f"--export=mixer_guest_ui_{entry}_v3")]
        linked = []
        if options.link_s2:
            fieldlog, reactor = [run(f"s2-{name}", "/usr/bin/git", "-C", ROOT, "show", f"{VM_REVISION}:{S2}/{name}.swift")
                                 for name in ("FieldLog", "Reactor")]
            (work / "FieldLog.swift").write_text(fieldlog)
            # Keep S2's Swift functions and expose its snapshots through a Swift-only bridge.
            for entry in ("start", "event", "ready"):
                attribute = f'@_cdecl("mixer_guest_ui_{entry}_v3")\n'
                if reactor.count(attribute) != 1:
                    raise ValueError(f"Unexpected S2 {entry} export declaration")
                reactor = reactor.replace(attribute, "")
            (work / "Reactor.swift").write_text(reactor + """
public func linkedS2Snapshot(_ step: UInt8) -> UnsafeBufferPointer<UInt8> {
    if step == 0 {
        _ = reactorStart()
    } else {
        input!.pointee = step
        _ = reactorEvent(1)
    }
    return UnsafeBufferPointer(start: frame!, count: Int(header![3]))
}
""")
            s2_object = work / "FieldLogSpike.o"
            run("s2-module-build", swift, *frontend, "-module-name", "FieldLogSpike",
                "-whole-module-optimization", "-emit-module", "-emit-module-path", work / "FieldLogSpike.swiftmodule",
                "-emit-object", work / "FieldLog.swift", work / "Reactor.swift", "-o", s2_object)
            linked = ["-DS3_LINKED_S2", "-I", work, s2_object]
        run("owned-guest-build", swift, *swift_flags, "-DS3_OWNED_VM", *exports, *SOURCES, *linked, "-o", guest)
        report["artifact"] = {"sha256": digest(guest), "bytes": guest.stat().st_size}
        report["inventory"] = json.loads(run("wasm-inventory", node, "-e", """
const module = new WebAssembly.Module(require('node:fs').readFileSync(process.argv[1]));
console.log(JSON.stringify({ imports: WebAssembly.Module.imports(module),
                             exports: WebAssembly.Module.exports(module) }));
""", guest))

        turns = 21 if options.link_s2 else 15
        run("node-ui-trace", node, "--no-warnings", HERE / "oracle.mjs", guest, turns)
        node_ui = (logs / "node-ui-trace.stdout").read_bytes()
        node_frames = node_ui.splitlines(keepends=True)
        if len(node_frames) != turns or b"".join(node_frames[:15]) != native:
            raise ValueError("Node UI reactor differs from the canonical S3 trace")
        report["nodeUITrace"] = {"turns": turns, "sha256": digest(logs / "node-ui-trace.stdout")}
        if options.link_s2:
            check_s2(node_frames[15:])

        run("fixed34", runner, guest, "fixed34", "standalone", expected=(0, 10))
        report["fixed34Exit"] = exit_code()
        fixed34 = (logs / "fixed34.stderr").read_text()
        if report["fixed34Exit"] != 10 or 'code: "swift_import_count"' not in fixed34:
            raise ValueError("Expected the same artifact to fail the fixed34 import count")

        # Screen state remains in one owner. The rollback fixture creates an
        # independent FrameRuntime in every build, so give it a fresh owner.
        suites = ({"screen": node_frames[:14],
                   "rollback": node_frames[:1] + node_frames[14:15],
                   "s2": node_frames[:1] + node_frames[15:]}
                  if options.link_s2 else {"standalone": node_frames})
        report["ownerExits"] = {}
        for suite, frames in suites.items():
            label = f"owned-{suite}"
            run(label, runner, guest, "swift633", suite, expected=(0, 10, 20, 74))
            report["ownerExits"][suite] = status = exit_code()
            if status == 74:
                raise RuntimeError("Frozen UI owner. Preserve this run's scratch.")
            if status != 0:
                raise RuntimeError(f"Swift 6.3.3 reactor stopped. See logs/{label}.stderr.")
            if b"".join(frames) != (logs / f"{label}.stdout").read_bytes():
                raise ValueError(f"Owned VM {suite} trace differs from the Node control")

        if options.link_s2:
            owned_s3 = (logs / "owned-screen.stdout").read_bytes()
            owned_s3 += (logs / "owned-rollback.stdout").read_bytes().splitlines(keepends=True)[-1]
        else:
            owned_s3 = (logs / "owned-standalone.stdout").read_bytes()
        if owned_s3 != native:
            raise ValueError("Owned S3 trace differs from the native and Node controls")
        trace_path = run_dir / "owned-s3.stdout"
        trace_path.write_bytes(owned_s3)
        report["trace"] = {"s3Lines": 15, "sha256": digest(trace_path)}
        report["completed"] = True
        print("Owned VM matched all 15 native and Node trace lines and closed cleanly.")
    except Exception as error:
        report["completed"] = False
        report["error"] = str(error)
        raise
    finally:
        settled = all(item["terminalCustody"] in ("TERMINAL", "NOT_STARTED") for item in report["commands"])
        if settled and 74 not in report.get("ownerExits", {}).values():
            shutil.rmtree(work)
            report["disposableWorkRemoved"] = True
        (run_dir / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
