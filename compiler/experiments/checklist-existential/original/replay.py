"""Run the local Swift value-dispatch differential from the retained fixture directory."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import tempfile
import time


FIXTURE = Path(__file__).resolve().parent
REPO = FIXTURE.parents[2]
PIN = "857e4b4aa7a32cda368257b2be1a63e77106bed8"
PUBLIC = "https://github.com/snowdamiz/mixer.git"
SWIFT = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr"
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
XCODE = "/Applications/Xcode_26.6.app/Contents/Developer"
GIT = Path(shutil.which("git")).resolve()
PREVIEW = "compiler/Fixtures/FeatureProbe/CompactPreviewGuest.swift"
BENCH = "compiler/experiments/fieldlog-guest-benchmark/MatchedTask.swift"
INSTALLED = "compiler/experiments/fieldlog-installed-guest"
RUNTIME = "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime"
HOST_INPUTS = [BENCH, f"{INSTALLED}/TaskCompletion.swift",
               *(f"{RUNTIME}/{name}.swift" for name in ("Types", "Failure", "GuestDebugLines"))]
PINNED_INPUTS = [PREVIEW, *HOST_INPUTS, f"{INSTALLED}/run.py", f"{INSTALLED}/replay_abi.py",
                 "compiler/experiments/fieldlog-reactor/support.py",
                 "compiler/experiments/profile-budget/analyze.py", "compiler/qualification_support.py",
                 "vm/Cargo.toml", "vm/Cargo.lock", "vm/examples/taskeditor_owned_command.rs"]


def identity(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def require(value, message):
    if not value:
        raise ValueError(message)


class Campaign:
    def __init__(self, scratch, receipt):
        self.scratch = scratch
        self.checkout = scratch / "mixer"
        self.receipt = receipt
        self.active = None
        self.deadline = time.monotonic() + 240
        self.env = {
            "PATH": f"{RUST}:/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "C", "DEVELOPER_DIR": XCODE,
            "HOME": str(scratch / "home"), "TMPDIR": str(scratch / "tmp"),
            "CARGO_HOME": str(scratch / "cargo"), "SWIFT_BACKTRACE": "enable=no",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        }
        for key in ("HOME", "TMPDIR", "CARGO_HOME"):
            Path(self.env[key]).mkdir()

    def run(self, label, *args, bound=20, exits=(0,)):
        argv = [str(arg) for arg in args]
        stdout, stderr = [self.scratch / f"{label}.{suffix}" for suffix in ("out", "err")]
        actions = [(os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0)]
        actions += [(os.POSIX_SPAWN_OPEN, fd, str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    for fd, path in enumerate((stdout, stderr), 1)]
        end = min(self.deadline, time.monotonic() + bound)
        require(time.monotonic() < end, "campaign deadline reached")
        entry = {"label": label, "argv": argv, "boundSeconds": bound, "custody": "UNKNOWN"}
        self.receipt["commands"].append(entry)
        self.active = entry
        pid = os.posix_spawn(argv[0], argv, self.env, setpgroup=0, file_actions=actions)
        entry["pidPgid"] = pid
        timed_out = False
        while True:
            child, status = os.waitpid(pid, os.WNOHANG)
            if child:
                entry["exit"] = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() >= end:
                require(not timed_out, f"{label}: no direct reap after deadline")
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                timed_out = True
                end = time.monotonic() + 3
            time.sleep(0.02)
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            entry["custody"] = "direct-child-reaped/group-absent"
            self.active = None
        require(self.active is None, f"{label}: group absence unproven")
        entry["stdout"] = identity(stdout)
        entry["stderr"] = identity(stderr)
        for key, path in (("stdoutText", stdout), ("stderrText", stderr)):
            if path.stat().st_size and (key == "stderrText" or label.endswith("-version")):
                entry[key] = path.read_text(errors="replace")[:8192]
        require(not timed_out and entry["exit"] in exits, f"{label}: unexpected exit {entry['exit']}")
        return stdout.read_text(), stderr.read_text(), entry["exit"]

    def execute(self):
        result, work, out = self.receipt, self.checkout, self.scratch
        run = self.run
        public, _, _ = run("public-head", GIT, "ls-remote", PUBLIC, "HEAD")
        require(public.split() == [PIN, "HEAD"], "public HEAD no longer equals the requested pin")
        result["publicHead"] = public.strip()
        objects, _, _ = run("local-object-store", GIT, "-C", REPO, "rev-parse", "--path-format=absolute",
                            "--git-path", "objects")
        run("init-isolated-worktree", GIT, "init", "--quiet", "--template=", work)
        (work / ".git/objects/info/alternates").write_text(objects)
        run("source-projection", GIT, "-C", work, "sparse-checkout", "set", "--no-cone", "--",
            *("/" + path for path in PINNED_INPUTS), "/vm/src/", "/vm/include/")
        run("checkout-pin", GIT, "-C", work, "checkout", "--detach", PIN)
        refs, _, _ = run("source-pins", GIT, "-C", work, "rev-parse", "HEAD", "HEAD^{tree}", "HEAD:vm",
                         "HEAD:compiler", "HEAD:vm/Cargo.lock")
        for key, value in zip(("revision", "tree", "vmTree", "compilerTree", "cargoLockBlob"),
                              refs.splitlines(), strict=True):
            result[key] = value
        require(result["revision"] == PIN, "wrong checkout commit")
        result["pinnedInputs"] = {path: identity(work / path) for path in PINNED_INPUTS}
        result["fixture"] = {path: identity(FIXTURE / path) for path in
                             ("ChecklistFormatter.swift", "Host.swift", "replay.py")}

        swiftc = SWIFT / "bin/swiftc"
        lld = SWIFT / "bin/wasm-ld"
        rustc, cargo = RUST / "rustc", RUST / "cargo"
        sdk, _, _ = run("macos-sdk", "/usr/bin/xcrun", "--no-cache", "--sdk", "macosx", "--show-sdk-path")
        result["nativeSDK"] = sdk.strip()
        result["versions"] = {}
        result["tools"] = {}
        for name, executable, flags in [
            ("swift", swiftc, ("--version",)), ("lld", lld, ("--version",)),
            ("rustc", rustc, ("--version", "--verbose")), ("cargo", cargo, ("--version", "--verbose")),
            ("git", GIT, ("--version",)), ("xcode", Path("/usr/bin/xcodebuild"), ("-version",)),
            ("macOS", Path("/usr/bin/sw_vers"), ()),
        ]:
            version, _, _ = run(name + "-version", executable, *flags)
            result["versions"][name] = version.strip()
            result["tools"][name] = {"path": str(executable.resolve()), **identity(executable)}
        require("Swift version 6.3.3 (swift-6.3.3-RELEASE)" in result["versions"]["swift"], "wrong Swift")
        require("rustc 1.99.0 " in result["versions"]["rustc"], "wrong Rust")
        for relative in ["bin/swift-frontend", "lib/swift/embedded/Swift.swiftmodule/wasm32-unknown-none-wasm.swiftmodule"]:
            result["tools"][relative] = identity(SWIFT / relative)
        result["tools"]["python"] = {"path": sys.executable, "version": sys.version, **identity(Path(sys.executable))}

        sys.path.insert(0, str(work / INSTALLED))
        from run import build_compact_guest, replay_abi

        swift = FIXTURE / "ChecklistFormatter.swift"
        artifacts = result["artifacts"] = {}
        variants = (("existential", ()), ("specialized", ("-D", "STATIC_FORMATTER")))
        guests = {}
        result["embedded"] = {}
        for variant, define in variants:
            obj, wasm = out / f"{variant}.o", out / f"{variant}.wasm"
            observation = result["embedded"][variant] = {
                "objectExistedBefore": os.path.lexists(obj), "wasmExistedBefore": os.path.lexists(wasm),
            }
            require(not any(observation.values()), "output paths must start absent")

            def command(label, *args):
                allowed = (0, 1) if label == "existential-swift" else (0,)
                _, diagnostic, code = run(label, *args, bound=35, exits=allowed)
                if code != 0:
                    observation.update(compileExit=code, originalStderr=diagnostic)
                    raise EmbeddedRefusal

            try:
                guests[variant] = build_compact_guest(
                    command, SWIFT / "bin", out, variant, [swift, work / PREVIEW],
                    flags=("-swift-version", "6", "-module-name", "ChecklistFormatterGuest",
                           "-module-cache-path", out / "guest-modules", *define))
            except EmbeddedRefusal:
                observation["linkInvoked"] = False
            else:
                observation.update(compileExit=0, linkInvoked=True,
                                   descriptors=replay_abi.check_descriptors(wasm.read_bytes()))
                for path in (obj, wasm):
                    artifacts[path.name] = identity(path)
            observation.update(objectExistsAfter=os.path.lexists(obj), wasmExistsAfter=os.path.lexists(wasm))

        native = [swiftc, "-swift-version", "6", "-whole-module-optimization", "-O", "-parse-as-library",
                  "-target", "arm64-apple-macosx26.0", "-sdk", sdk.strip(),
                  "-module-cache-path", out / "native-modules"]
        sil = out / "native-existential.sil"
        # SILGen retains the formatter before whole-module dead-code elimination.
        run("native-existential-silgen", *native, "-module-name", "ChecklistFormatterNative",
            "-emit-silgen", swift, "-o", sil, bound=35)
        artifacts[sil.name] = identity(sil)
        dispatch = result["nativeUnoptimizedDispatchSIL"] = [
            line.strip() for line in sil.read_text().splitlines()
            if "open_existential_" in line or ("witness_method" in line and "#ChecklistFormatter.mark" in line)
        ]
        require(any("open_existential_" in line for line in dispatch)
                and any("witness_method" in line for line in dispatch),
                "missing native existential dispatch instructions")
        run("build-owned-vm", cargo, "build", "--offline", "--locked", "--release", "--lib", "--jobs", "1",
            "--features", "experimental-capability-native", "--manifest-path", work / "vm/Cargo.toml",
            "--target-dir", out / "rust", bound=110)
        archive = out / "rust/release/libmixer_vm.a"
        artifacts[archive.name] = identity(archive)
        header = work / "vm/include/mixer_vm_guest_ui.h"
        modulemap = out / "module.modulemap"
        modulemap.write_text(f'module CMixerVMCapability {{ header "{header}" export * }}\n')
        artifacts[modulemap.name] = identity(modulemap)
        result["readbacks"] = {}
        for variant, define in variants:
            host = out / f"host-{variant}"
            run(f"build-{host.name}", *native, "-D", "SWIFT_SUPPORT_MATRIX", *define, "-I", out, swift,
                FIXTURE / "Host.swift", *(work / path for path in HOST_INPUTS), archive, "-o", host, bound=35)
            artifacts[host.name] = identity(host)
            output, _, _ = run(f"native-{variant}-replay", host)
            result["readbacks"][f"native-{variant}"] = json.loads(output)
            if variant in guests:
                output, _, _ = run(f"guest-{variant}-replay", host, guests[variant])
                result["readbacks"][f"guest-{variant}"] = json.loads(output)
        plain = result["readbacks"]["native-existential"]
        for rows in result["readbacks"].values():
            require([{k: v for k, v in row.items() if k != "fuel"} for row in rows] == plain,
                    "replayed readbacks differ from the native existential")
        require("guest-specialized" in result["readbacks"], "missing specialized guest replay")
        result["guestClosedStaleHandleRefusedAndSlotReclaimed"] = sorted(guests)
        negative = result["embedded"]["existential"]
        if "existential" not in guests:
            require("ChecklistFormatter.swift:" in negative["originalStderr"]
                    and "existential" in negative["originalStderr"].lower(), "unexpected Embedded diagnostic")
            require(not negative["objectExistsAfter"] and not negative["wasmExistsAfter"],
                    "Embedded refusal published an artifact")
        run("pinned-worktree-unchanged", GIT, "-C", work, "diff", "--exit-code", "HEAD", "--")
        require(all(identity(work / path) == evidence for path, evidence in result["pinnedInputs"].items()),
                "source projection changed during replay")


class EmbeddedRefusal(Exception):
    pass


def main():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    sys.dont_write_bytecode = True
    receipt_path = Path(sys.argv[1]).resolve()
    result = {"status": "incomplete", "startedUTC": datetime.now(timezone.utc).isoformat(),
              "publicRepository": PUBLIC, "campaignBoundSeconds": 240, "commands": [],
              "scope": "Single unsigned synthetic Swift formatter. Compact raw frames, 1/1 memory pages, no imports, "
                       "zero host-call budget and 1,000,000 fuel per turn. macOS host and owned Mixer VM only."}
    if len(sys.argv) == 3:
        setup_path = Path(sys.argv[2]).resolve()
        setup = json.loads(setup_path.read_text())
        require(setup["cleanup"]["removed"] and setup["cleanup"]["unknown"] is None,
                "setup run did not establish terminal custody")
        result["setupCorrection"] = {"receipt": str(setup_path), **identity(setup_path),
                                     "originalFailure": setup["failure"],
                                     "change": "Capture native dispatch with SILGen before dead-code elimination."}
    scratch = Path(tempfile.mkdtemp(prefix="run-", dir=FIXTURE))
    campaign = Campaign(scratch, result)
    try:
        campaign.execute()
        result["status"] = "pass"
    except Exception as error:
        result["failure"] = f"{type(error).__name__}: {error}"
    finally:
        if campaign.active is None:
            shutil.rmtree(scratch)
        result["cleanup"] = {"scratch": str(scratch), "removed": not scratch.exists(),
                             "unknown": campaign.active}
        result["completedUTC"] = datetime.now(timezone.utc).isoformat()
        with receipt_path.open("x") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(f"{result['status']}: {receipt_path}")
    return result["status"] != "pass"


if __name__ == "__main__":
    sys.exit(main())
