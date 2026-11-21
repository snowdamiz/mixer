#!/usr/bin/env python3
"""Replay one benign Swift compiler macro at the pinned Mixer revision."""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import sys
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PIN = "98ef14202e14661dcc3532f37068aae20ddb70cc"
TREE = "c5517ea0fad548ef4fc4afa013cb9a823afdb0ba"
VM_TREE = "ec1ddb74b7c6c2eabd91d1f60ed243ffc69ce6f4"
TOOLCHAIN = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr"
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
DEVELOPER = Path("/Applications/Xcode_26.6.app/Contents/Developer")
RUNTIME = "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"
INSTALLED = "compiler/experiments/fieldlog-installed-guest"
HOST_INPUTS = [
    "compiler/experiments/fieldlog-guest-benchmark/MatchedTask.swift",
    f"{INSTALLED}/TaskCompletion.swift",
    *(f"{RUNTIME}/{name}.swift" for name in ("Types", "Failure", "GuestDebugLines")),
]
DESCRIPTORS = [
    f"{INSTALLED}/replay_abi.py",
    "compiler/experiments/fieldlog-reactor/support.py",
    "compiler/experiments/profile-budget/analyze.py",
    "compiler/qualification_support.py",
]
EXPORTS = ("mixer_guest_ui_start_v1", "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1")


def need(condition, message):
    if not condition:
        raise ValueError(message)


def identity(path):
    with path.open("rb") as stream:
        return {"sha256": hashlib.file_digest(stream, "sha256").hexdigest(), "bytes": path.stat().st_size}


class Run:
    def __init__(self, scratch, receipt, destination):
        self.scratch = scratch
        self.receipt = receipt
        self.destination = destination
        self.hold = scratch / "HOLD.json"
        self.active = None
        self.peak = 0
        self.deadline = time.monotonic() + 230
        for name in ("home", "tmp", "cargo", "plugin"):
            (scratch / name).mkdir()
        self.env = dict(PATH=f"{RUST}:/usr/bin:/bin:/usr/sbin:/sbin", LANG="C",
                        HOME=str(scratch / "home"), TMPDIR=str(scratch / "tmp"),
                        CARGO_HOME=str(scratch / "cargo"), SWIFT_BACKTRACE="enable=no",
                        DEVELOPER_DIR=str(DEVELOPER), GIT_NO_LAZY_FETCH="1")

    def display(self, text):
        return str(text).replace(str(self.scratch), "$RUN").replace(str(HERE), "$FIXTURE").replace(
            str(ROOT), "$REPO").replace(str(Path.home()), "$USER_HOME")

    def allocated(self):
        allocated = 0
        for path in self.scratch.rglob("*"):
            try:
                allocated += path.lstat().st_blocks * 512
            except FileNotFoundError:
                continue
        self.peak = max(self.peak, allocated)
        return allocated

    def command(self, name, *args, expected=0, seconds=25):
        argv = list(map(str, args))
        directory = self.scratch
        out = directory / (name + ".stdout")
        err = directory / (name + ".stderr")
        row = dict(label=name, argv=list(map(self.display, argv)), custody="launch-unresolved")
        self.receipt["commands"].append(row)
        end = min(self.deadline, time.monotonic() + seconds)
        need(end > time.monotonic(), "campaign deadline")
        actions = [(os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0)]
        actions.extend((os.POSIX_SPAWN_OPEN, fd, str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                       for fd, path in ((1, out), (2, err)))
        # Keep launch evidence even if spawn or final receipt writing fails.
        with self.hold.open("x") as file:
            json.dump(dict(status="HOLD", revision=PIN, scratch=str(self.scratch),
                           receipt=str(self.destination), command=row), file, indent=2)
            file.write("\n")
        self.active = row
        pid = os.posix_spawn(argv[0], argv, self.env, setpgroup=0, file_actions=actions)
        row["pidPgid"] = pid
        stopped = None
        next_scan = 0
        while True:
            child, status, _ = os.wait4(pid, os.WNOHANG)
            if child:
                break
            now = time.monotonic()
            if stopped is None and (now >= end or (now >= next_scan and self.allocated() >= 1024**3)):
                stopped = "deadline" if now >= end else "scratch guard"
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                end = now + 3
            elif stopped is not None and now >= end:
                raise TimeoutError(f"{name}: direct child unreaped")
            if now >= next_scan:
                next_scan = now + 0.25
            time.sleep(0.03)

        row["exit"] = os.waitstatus_to_exitcode(status)
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            row["custody"] = "direct-child-reaped/group-absent"
            self.active = None
            self.hold.unlink()
        need(self.active is None, f"{name}: command group absence unproven")
        need(self.allocated() < 3 * 1024**3, "scratch exceeded 3 GiB")
        if stopped:
            row["stop"] = stopped
        stdout = self.display(out.read_text(errors="replace")) if out.stat().st_size <= 65_536 else ""
        stderr = self.display(err.read_text(errors="replace")) if err.stat().st_size <= 65_536 else ""
        if stderr.strip():
            row["stderr"] = stderr.strip()
        need(stopped is None, f"{name}: {stopped}")
        need(expected is None or row["exit"] == expected, f"{name}: exit {row['exit']}\n{stderr}")
        return row["exit"], stdout.strip(), stderr


def verify_frames(observed, guest):
    turns = observed["native"]
    expected = [(None, None, 1, 0), ("0105", True, 2, 2), ("0208", False, 2, 2),
                ("02", False, 2, 2), ("0207", True, 3, 3), ("0300", True, 4, 0)]
    for turn, (wire, accepted, revision, count) in zip(turns, expected, strict=True):
        node = {"id": "count", "kind": "text", "properties": {"text": f"{count} of 3 complete"},
                "children": [], "actions": []}
        root = {"id": "checklist", "kind": "vStack", "properties": {}, "actions": [], "children": [node]}
        need((turn.get("inputHex"), turn.get("accepted"), json.loads(turn["frame"])) ==
             (wire, accepted, {"schemaVersion": 1, "revision": revision, "root": root}), "native frame oracle")
    if guest:
        need(observed["guestClosedAndStaleHandleRefused"] and observed["guestRegistrySlotReclaimed"], "closure")
        for host, wasm in zip(turns, observed["guest"], strict=True):
            fuel = wasm.pop("fuel", None)
            need(host == wasm, "guest/native frame bytes or outcomes differ")
            if "inputHex" in wasm:
                need(fuel is not None and 0 < fuel <= 1_000_000, "fuel")
                wasm["fuel"] = fuel


def campaign(run):
    out = run.scratch
    report = run.receipt
    call = run.command
    git = ("/usr/bin/git", "-C", ROOT)
    _, pinned_trees, _ = call("pinned-trees", *git, "rev-parse", f"{PIN}^{{tree}}", f"{PIN}:vm")
    need(pinned_trees.splitlines() == [TREE, VM_TREE], "Mixer source trees changed")
    _, published, _ = call("public-ancestry", *git, "for-each-ref", "--contains", PIN, "refs/remotes/origin/main")
    need(published.endswith("refs/remotes/origin/main"), "pin missing from local origin/main ancestry")
    archive = out / "pinned.tar"
    call("source-projection", *git, "archive", "-o", archive, PIN,
         "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include", "vm/examples/taskeditor_owned_command.rs",
         *HOST_INPUTS, *DESCRIPTORS)
    report["projectedArchive"] = identity(archive)
    source = out / "mixer"
    source.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(source, filter="data")
    report["pinnedHarnessInputs"] = {name: identity(source / name) for name in (*HOST_INPUTS, *DESCRIPTORS)}
    report["fixture"] = {path.name: identity(path) for path in sorted(HERE.iterdir())
                         if path.suffix in (".swift", ".py")}

    swift = TOOLCHAIN / "bin/swiftc"
    lld = TOOLCHAIN / "bin/wasm-ld"
    nm = TOOLCHAIN / "bin/llvm-nm"
    server = TOOLCHAIN / "bin/swift-plugin-server"
    host_libs = TOOLCHAIN / "lib/swift/host"
    _, sdk, _ = call("macos-sdk", "/usr/bin/xcrun", "--no-cache", "--sdk", "macosx", "--show-sdk-path")
    report["versions"] = {
        name: call(name, *argv)[1] for name, argv in {
            "macos": ("/usr/bin/sw_vers",),
            "xcode": ("/usr/bin/xcodebuild", "-version"),
            "swift": (swift, "--version"),
            "lld": (lld, "--version"),
            "rustc": (RUST / "rustc", "--version", "--verbose"),
            "cargo": (RUST / "cargo", "--version", "--verbose"),
        }.items()
    }
    need("(swift-6.3.3-RELEASE)" in report["versions"]["swift"], "wrong Swift release")
    need(report["versions"]["rustc"].startswith("rustc 1.99.0 "), "wrong Rust release")
    inputs = [
        swift, TOOLCHAIN / "bin/swift-frontend", lld, nm, server, RUST / "rustc", RUST / "cargo",
        Path(sdk) / "SDKSettings.json",
        TOOLCHAIN / "lib/swift/embedded/Swift.swiftmodule/wasm32-unknown-none-wasm.swiftmodule",
        *sorted(host_libs.glob("*.dylib")),
        *sorted(host_libs.glob("*.swiftmodule/arm64-apple-macos*.swiftinterface")),
    ]
    report["toolchainInputs"] = {run.display(path): identity(path) for path in inputs}
    target = ("-target", "arm64-apple-macosx26.0", "-sdk", sdk, "-module-cache-path", out / "host-modules")
    common = (swift, "-parse-as-library", "-swift-version", "6", "-whole-module-optimization")
    plugin = out / "plugin/libMixerChecklistMacros.dylib"
    call("macro-library", *common, *target, "-O", "-module-name", "MixerChecklistMacros",
         "-I", host_libs, "-L", host_libs, "-Xlinker", "-rpath", "-Xlinker", host_libs,
         "-emit-library", HERE / "ChecklistMacro.swift", "-o", plugin)
    report["pluginLibrary"] = identity(plugin)
    llvm_objdump = TOOLCHAIN / "bin/llvm-objdump"
    report["pluginMachODependencies"] = call("plugin-dependencies", llvm_objdump, "--macho",
                                              "--dylibs-used", plugin)[1].splitlines()[1:]

    consumer = (HERE / "Checklist.swift", HERE / "ChecklistCount.swift")
    macro = ("-external-plugin-path", f"{plugin.parent}#{server}", "-Xfrontend", "-dump-macro-expansions")
    embedded = (*common, "-target", "wasm32-unknown-none-wasm", "-enable-experimental-feature", "Embedded",
                "-Osize", "-Xfrontend", "-disable-stack-protector", "-module-cache-path", out / "guest-modules")
    guest_sources = (*consumer, HERE / "Guest.swift")
    _, refusal, diagnostic = call("embedded-missing-plugin", *embedded, "-emit-object", *guest_sources,
                                  "-o", out / "missing.o", expected=1)
    need(not refusal and not (out / "missing.o").exists(), "missing-plugin control emitted output")
    expected = re.search(r"Checklist\.swift:([0-9]+):([0-9]+): error: external macro implementation type[^\n]+", diagnostic)
    need(expected is not None, "missing-plugin control missing source location")
    line, column = map(int, expected.groups())
    need((HERE / "Checklist.swift").read_text().splitlines()[line - 1][column - 1:].startswith("#checklistCount"),
         "compiler error location is not the invocation")
    report["missingPlugin"] = dict(file="Checklist.swift", line=line, column=column, diagnostic=expected[0])

    guest_obj = out / "guest.o"
    guest_rc, _, guest_expansion = call("embedded-expand-compile", *embedded, *macro,
                                      "-emit-object", *guest_sources, "-o", guest_obj, expected=None)
    rust = out / "rust"
    call("vm-build", RUST / "cargo", "build", "--offline", "--locked", "--release", "--jobs", "1",
         "--features", "experimental-capability-native", "--lib", "--manifest-path", source / "vm/Cargo.toml",
         "--target-dir", rust, seconds=95)
    vm_lib = rust / "release/libmixer_vm.a"
    report["vmStaticLibrary"] = identity(vm_lib)
    header = source / "vm/include/mixer_vm_guest_ui.h"
    (out / "module.modulemap").write_text(f'module CMixerVMCapability {{ header "{header}" export * }}\n')
    host = out / "native"
    _, _, native_expansion = call("native-expand-build", *common, *target, *macro, "-O", "-D",
                                  "SWIFT_SUPPORT_MATRIX", "-I", out, *consumer, HERE / "Host.swift",
                                  *(source / path for path in HOST_INPUTS), vm_lib, "-o", host, seconds=55)
    report["nativeExecutable"] = identity(host)
    need("boundedChecklistCount(mask)" in native_expansion, "native expansion absent")
    report["nativeOnlyReplay"] = json.loads(call("native-run", host)[1])
    verify_frames(report["nativeOnlyReplay"], False)
    need(guest_rc == 0, "Embedded macro compile failed")
    need("boundedChecklistCount(mask)" in guest_expansion, "guest expansion absent")
    report["expansion"] = dict(expression="boundedChecklistCount(mask)", bothCompilerDumps=True,
                               invocation=report["missingPlugin"]["file"] + f":{line}:{column}")
    report["guestObject"] = identity(guest_obj)
    symbols = call("guest-object-symbols", nm, "--demangle", guest_obj)[1]
    report["guestHelperSymbol"] = next(text.strip() for text in symbols.splitlines()
                                       if "boundedChecklistCount" in text)
    wasm = out / "guest.wasm"
    call("wasm-link", lld, "--no-entry", "--gc-sections", "--strip-all", "-z", "stack-size=16384",
         "--max-memory=65536", *(f"--export={name}" for name in EXPORTS), guest_obj, "-o", wasm)
    report["linkedWasm"] = identity(wasm)
    sys.path[:0] = [str(source / f"compiler/experiments/{path}")
                    for path in ("fieldlog-installed-guest", "fieldlog-reactor", "profile-budget")]
    from replay_abi import check_descriptors
    report["wasmAbi"] = check_descriptors(wasm.read_bytes())
    result = json.loads(call("strict-session-replay", host, wasm)[1])
    verify_frames(result, True)
    report["strictSessionReplay"] = result


def main():
    need(len(sys.argv) == 2, "usage: python3 -B replay.py NEW_RECEIPT.json")
    requested = Path(sys.argv[1])
    destination = requested.parent.resolve(strict=True) / requested.name
    report = dict(status="incomplete", revision=PIN, tree=TREE, vmTree=VM_TREE,
                  utcStarted=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), commands=[],
                  limits=dict(allocatedScratchCeilingBytes=3 * 1024**3, sampledGuardBytes=1024**3,
                              maxIndividualFileBytes=256 * 1024**2, campaignSeconds=230,
                              guest="table-memory-v3 / experimental-capability-native", memoryPages=1,
                              fuelPerTurn=1_000_000, hostCallsPerTurn=0),
                  scope="One unsigned synthetic Guest UI V1 fixture and two-byte replay input. Runtime evidence "
                        "covers the strict validator, owned VM session and exact frames. Product UI event codec, "
                        "signing, apps, devices, migration analyzer and wider macro support are outside scope.")
    scratch = None
    run = None
    with destination.open("x") as file:
        try:
            original_directory = Path.cwd()
            parent = ROOT / "verification/local"
            parent.mkdir(exist_ok=True)
            volumes = shutil.disk_usage(parent)
            report["freeBeforeBytes"] = volumes.free
            need(volumes.free >= 3 * 1024**3, "less than 3 GiB free before campaign")
            scratch = Path(tempfile.mkdtemp(prefix="w07-checklist-macro-", dir=parent))
            report["scratch"] = str(scratch)
            run = Run(scratch, report, destination)
            resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
            try:
                os.chdir(scratch)
                campaign(run)
            finally:
                os.chdir(original_directory)
            report["status"] = "pass"
        except Exception as error:
            report["failure"] = run.display(error) if run is not None else str(error)
        finally:
            if run is not None and run.active is not None:
                report["cleanup"] = "HOLD: preserve owned scratch and unproven command custody"
                report["hold"] = str(run.hold)
            elif scratch is not None:
                try:
                    shutil.rmtree(scratch)
                    report["cleanup"] = "owned scratch removed with no unresolved command custody"
                except OSError as error:
                    report["status"] = "incomplete"
                    report["cleanup"] = f"owned scratch cleanup failed: {error}"
            else:
                report["cleanup"] = "no owned scratch allocated"
            report["sampledPeakAllocatedBytes"] = run.peak if run is not None else 0
            try:
                json.dump(report, file, indent=2)
                file.write("\n")
                file.flush()
            finally:
                if "hold" in report:
                    print(f"HOLD: {report['hold']}", file=sys.stderr)
    print(f"{report['status']}: {destination}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
