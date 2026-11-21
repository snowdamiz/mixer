"""Replay the pinned W07/L03 checklist formatter differential."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import secrets
import shutil
import signal
import sys
import time


FIXTURE = Path(__file__).resolve().parent
PIN = "857e4b4aa7a32cda368257b2be1a63e77106bed8"
PUBLIC = "https://github.com/snowdamiz/mixer.git"
SWIFT = Path.home() / "Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr"
RUST = Path.home() / ".rustup/toolchains/1.99.0-aarch64-apple-darwin/bin"
XCODE = "/Applications/Xcode_26.6.app/Contents/Developer"
GIT_ROOT = Path("/opt/homebrew/Cellar/git/2.56.0")
GIT = GIT_ROOT / "bin/git"
GIT_EXEC = GIT_ROOT / "libexec/git-core"
XCRUN = Path("/usr/bin/xcrun")
SCRATCH_ROOT = Path("/private/tmp")
CAMPAIGN_SECONDS = 240
ORIGINAL_HASHES = {
    "ChecklistFormatter.swift": "1a6febde3c5da9486fe9aab16296c7d166ce8b675edaf6c9b31aed67b9ba57ce",
    "Host.swift": "daf77f30160ee5e627e753275b1ec59f44e3194c9854cbd9475cbef8cff6f591",
    "replay.py": "ff245085d15635e920215ab71414d14120d36c1331830fa64e1560e36db9fe67",
    "setup-receipt.json": "e25bd05ca72aedd6ac88b455b4a633c574abab8a8202e15f2aa732565b2ced0f",
    "producer-receipt.json": "c107dbbc648287fc1f154859082fc81caad934c8f79046c099f8059b3ec48886",
}
SUPPLEMENTAL_TOOLS = {
    "xcrun": {"path": str(XCRUN), "bytes": 199024,
              "sha256": "bbe7671518a3905f9d3fce54312fbc77c2876b0d62aca74a0688fa869d31a8a9"},
    "git-remote-https": {"path": str(GIT_EXEC / "git-remote-http"), "bytes": 2240448,
                         "sha256": "dad955378b314687ae25a263fb8c60d3a3b4ae9cf42367887e3b53fae8cffc40"},
}
SDK_SETTINGS = {"bytes": 7774, "sha256": "f8d005f09381389167f9e0aeaa169bc9e7dff162ef22ca2fd8e98df7ff1acafe"}
SWIFT_FRONTEND = "bin/swift-frontend"
EMBEDDED_MODULE = "lib/swift/embedded/Swift.swiftmodule/wasm32-unknown-none-wasm.swiftmodule"
EMBEDDED_ERROR = ("error: cannot use a value of protocol type 'any ChecklistFormatter' "
                  "in embedded Swift [#EmbeddedRestrictions]")
SOURCE_KEYS = ("revision", "tree", "vmTree", "compilerTree", "cargoLockBlob")
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
EXEC_IN_OWNED_CWD = (
    "import json, os, sys\n"
    "os.chdir(sys.argv[1])\n"
    "os.execve(sys.argv[3], sys.argv[3:], json.loads(sys.argv[2]))"
)


def identity(path):
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"bytes": path.stat().st_size, "sha256": digest}


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_original():
    identities = {name: identity(FIXTURE / "original" / name) for name in ORIGINAL_HASHES}
    require(all(identities[name]["sha256"] == digest for name, digest in ORIGINAL_HASHES.items()),
            "original packet differs from frozen hashes")
    for name in ("ChecklistFormatter.swift", "Host.swift"):
        require(identity(FIXTURE / name) == identities[name], f"changed fixture: {name}")
    return identities, json.loads((FIXTURE / "original/producer-receipt.json").read_text())


def check_identity(path, expected, *, executable=False):
    observed = identity(path)
    if "path" in expected:
        observed["path"] = str(path.resolve(strict=True))
    require(observed == expected, f"identity mismatch: {path}")
    if executable:
        require(path.is_file() and os.access(path, os.X_OK), f"not executable: {path}")
    return observed


def check_cargo_ancestry(cwd):
    for directory in (cwd, *cwd.parents):
        for name in ("config", "config.toml"):
            config = directory / ".cargo" / name
            require(not os.path.lexists(config), f"ambient Cargo configuration: {config}")


def check_embedded_refusal(swift, observation):
    expected_line = f"{swift}:47:32: {EMBEDDED_ERROR}"
    require(observation["compileExit"] == 1
            and expected_line in observation["originalStderr"].splitlines()
            and not observation["linkInvoked"]
            and not observation["objectExistedBefore"] and not observation["wasmExistedBefore"]
            and not observation["objectExistsAfter"] and not observation["wasmExistsAfter"],
            "expected the exact Embedded restriction, exit 1, and absent object and Wasm")


class Receipt:
    def __init__(self, path, data):
        self.path = path
        self.journal_path = path.with_name(path.name + ".journal")
        self.data = data

    def __enter__(self):
        with ExitStack() as opened:
            self.directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            opened.callback(os.close, self.directory)
            self.snapshot = self.open_owned(self.path, "wb", opened)
            self.journal = self.open_owned(self.journal_path, "ab", opened)
            self.save()
            os.fsync(self.directory)
            self.opened = opened.pop_all()
        return self

    def __exit__(self, *exc):
        return self.opened.__exit__(*exc)

    def open_owned(self, path, mode, opened):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = os.open(path.name, flags, 0o600, dir_fd=self.directory)
        try:
            stream = os.fdopen(fd, mode)
        except BaseException:
            os.close(fd)
            raise
        return opened.enter_context(stream)

    def check_paths(self):
        files = ((self.path.parent, self.directory), (self.path, self.snapshot.fileno()),
                 (self.journal_path, self.journal.fileno()))
        for path, fd in files:
            try:
                named = path.stat(follow_symlinks=False)
            except OSError as error:
                raise PublicationError(f"cannot locate owned receipt entry: {path}") from error
            if not os.path.samestat(named, os.fstat(fd)) or named.st_nlink == 0:
                raise PublicationError(f"receipt entry no longer names the owned inode: {path}")

    def record(self):
        # A leading newline separates this record from any interrupted append.
        self.journal.write(("\n" + json.dumps(self.data) + "\n").encode())
        self.journal.flush()
        os.fsync(self.journal.fileno())

    def write_snapshot(self):
        self.snapshot.seek(0)
        self.snapshot.write((json.dumps(self.data, indent=2) + "\n").encode())
        self.snapshot.truncate()
        self.snapshot.flush()
        os.fsync(self.snapshot.fileno())

    def save(self):
        try:
            self.record()
            self.check_paths()
            self.write_snapshot()
            self.check_paths()
        except OSError as error:
            raise PublicationError(str(error)) from error

    def record_completion(self):
        # The last save committed the result through the public name before
        # cleanup. Record cleanup on those same owned inodes.
        self.record()
        self.write_snapshot()


class PublicationError(Exception):
    pass


def write_publication_hold(scratch, result):
    path = scratch / "publication-hold.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class Campaign:
    def __init__(self, scratch, receipt, producer, repo):
        self.scratch = scratch
        self.checkout = scratch / "mixer"
        self.journal = receipt
        self.receipt = receipt.data
        self.producer = producer
        self.repo = repo
        self.active = None
        self.deadline = time.monotonic() + CAMPAIGN_SECONDS
        self.env = {
            "PATH": f"{RUST}:/usr/bin:/bin:/usr/sbin:/sbin",
            "LANG": "C", "DEVELOPER_DIR": XCODE,
            "HOME": str(scratch / "home"), "TMPDIR": str(scratch / "tmp"),
            "CARGO_HOME": str(scratch / "cargo"), "SWIFT_BACKTRACE": "enable=no",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull, "GIT_TERMINAL_PROMPT": "0",
            "GIT_EXEC_PATH": str(GIT_EXEC), "GIT_NO_REPLACE_OBJECTS": "1",
            "RUSTC": str(RUST / "rustc"),
        }
        for key in ("HOME", "TMPDIR", "CARGO_HOME"):
            Path(self.env[key]).mkdir()

    def run(self, label, *args, bound=20, exits=(0,)):
        argv = [str(arg) for arg in args]
        require(self.active is None, "command requires idle campaign")
        stdout, stderr = [self.scratch / f"{label}.{suffix}" for suffix in ("out", "err")]
        actions = [(os.POSIX_SPAWN_OPEN, 0, os.devnull, os.O_RDONLY, 0)]
        actions += [(os.POSIX_SPAWN_OPEN, fd, str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    for fd, path in enumerate((stdout, stderr), 1)]
        end = min(self.deadline, time.monotonic() + bound)
        require(time.monotonic() < end, "campaign deadline reached")
        entry = {"label": label, "argv": argv, "cwd": str(self.scratch),
                 "boundSeconds": bound, "custody": "UNKNOWN", "stage": "prelaunch"}
        self.receipt["commands"].append(entry)
        self.active = entry
        self.receipt["cleanup"]["unknown"] = entry
        self.journal.save()
        # exec keeps the same child and process group for the custody checks.
        launcher = [sys.executable, "-I", "-B", "-c", EXEC_IN_OWNED_CWD,
                    str(self.scratch), json.dumps(self.env), *argv]
        pid = os.posix_spawn(launcher[0], launcher, self.env, setpgroup=0, file_actions=actions)
        entry.update(pidPgid=pid, stage="spawned")
        self.journal.save()
        timed_out = False
        while True:
            child, status = os.waitpid(pid, os.WNOHANG)
            if child:
                entry.update(exit=os.waitstatus_to_exitcode(status), stage="direct-child-reaped")
                self.journal.save()
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
            entry["stage"] = "terminal"
            self.receipt["cleanup"]["unknown"] = None
            self.active = None
            self.journal.save()
        require(self.active is None, f"{label}: group absence unproven")
        entry["stdout"] = identity(stdout)
        entry["stderr"] = identity(stderr)
        for key, path in (("stdoutText", stdout), ("stderrText", stderr)):
            if path.stat().st_size and (key == "stderrText" or label.endswith("-version")):
                entry[key] = path.read_text(errors="replace")[:8192]
        require(not timed_out and entry["exit"] in exits, f"{label}: unexpected exit {entry['exit']}")
        return stdout.read_text(), stderr.read_text(), entry["exit"]

    def verify_sdk_and_tools(self):
        result, expected = self.receipt, self.producer
        commands = [
            ("swift", SWIFT / "bin/swiftc", ("--version",)),
            ("lld", SWIFT / "bin/wasm-ld", ("--version",)),
            ("rustc", RUST / "rustc", ("--version", "--verbose")),
            ("cargo", RUST / "cargo", ("--version", "--verbose")),
            ("git", GIT, ("--version",)), ("xcode", Path("/usr/bin/xcodebuild"), ("-version",)),
            ("macOS", Path("/usr/bin/sw_vers"), ()),
        ]
        tools = result["tools"] = {}
        for name, executable, _ in commands:
            tools[name] = check_identity(executable, expected["tools"][name], executable=True)
        for name, path in (("xcrun", XCRUN), ("git-remote-https", GIT_EXEC / "git-remote-https")):
            tools[name] = check_identity(path, SUPPLEMENTAL_TOOLS[name], executable=True)
        for relative in (SWIFT_FRONTEND, EMBEDDED_MODULE):
            tools[relative] = check_identity(SWIFT / relative, expected["tools"][relative],
                                             executable=(relative == SWIFT_FRONTEND))
        python = expected["tools"]["python"]
        require(sys.executable == python["path"] and sys.version == python["version"],
                "wrong Python executable or version")
        tools["python"] = {"path": sys.executable, "version": sys.version, **check_identity(
            Path(sys.executable), {key: python[key] for key in ("bytes", "sha256")}, executable=True)}
        sdk = Path(expected["nativeSDK"])
        require(sdk.resolve(strict=True) == sdk.with_name("MacOSX.sdk"), "wrong SDK directory target")
        result["nativeSDKSettings"] = check_identity(sdk / "SDKSettings.json", SDK_SETTINGS)

        observed, _, _ = self.run("macos-sdk", XCRUN, "--no-cache", "--sdk", "macosx", "--show-sdk-path")
        require(observed.strip() == str(sdk), "xcrun selected a different SDK")
        result["nativeSDK"] = str(sdk)
        result["versions"] = {}
        for name, executable, flags in commands:
            version, _, _ = self.run(name + "-version", executable, *flags)
            require(version.strip() == expected["versions"][name], f"version mismatch: {name}")
            result["versions"][name] = version.strip()
        return sdk

    def materialize_source(self):
        result, work, run = self.receipt, self.checkout, self.run
        require(self.producer["revision"] == PIN, "wrong producer revision")
        run("init-isolated-worktree", GIT, "init", "--quiet", "--template=", work)
        run("fetch-published-pin", GIT, "-C", work, "fetch", "--no-tags", "--depth=1", "--filter=tree:0",
            "--no-auto-maintenance", "--no-write-commit-graph", "--no-recurse-submodules", PUBLIC, PIN)
        published, _, _ = run("verify-published-pin", GIT, "-C", work, "rev-parse", "--verify",
                              "FETCH_HEAD^{commit}")
        require(published.splitlines() == [PIN], "remote did not deliver the requested commit")
        result["publishedCommit"] = published.strip()

        # Use the local object store for checkout only after GitHub delivered the commit.
        objects, _, _ = run("local-object-store", GIT, "-C", self.repo, "rev-parse",
                            "--path-format=absolute", "--git-path", "objects")
        (work / ".git/objects/info/alternates").write_text(objects)
        run("source-projection", GIT, "-C", work, "sparse-checkout", "set", "--no-cone", "--",
            *("/" + path for path in PINNED_INPUTS), "/vm/src/", "/vm/include/")
        run("checkout-pin", GIT, "-C", work, "checkout", "--detach", PIN)
        refs, _, _ = run("source-pins", GIT, "-C", work, "rev-parse", "HEAD", "HEAD^{tree}", "HEAD:vm",
                         "HEAD:compiler", "HEAD:vm/Cargo.lock")
        require(refs.splitlines() == [self.producer[key] for key in SOURCE_KEYS], "wrong source pins")
        result.update(zip(SOURCE_KEYS, refs.splitlines(), strict=True))
        result["pinnedInputs"] = {path: check_identity(work / path, self.producer["pinnedInputs"][path])
                                  for path in PINNED_INPUTS}

    def execute(self):
        result, work, out, run = self.receipt, self.checkout, self.scratch, self.run
        sdk = self.verify_sdk_and_tools()
        self.materialize_source()
        result["fixture"] = {path: identity(FIXTURE / path) for path in
                             ("ChecklistFormatter.swift", "Host.swift", "replay.py")}

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
                if label == "existential-swift":
                    _, diagnostic, code = run(label, *args, bound=35, exits=(0, 1))
                    observation.update(compileExit=code, originalStderr=diagnostic, linkInvoked=False,
                                       objectExistsAfter=os.path.lexists(obj), wasmExistsAfter=os.path.lexists(wasm))
                    check_embedded_refusal(swift, observation)
                    raise EmbeddedRefusal
                run(label, *args, bound=35)

            try:
                guests[variant] = build_compact_guest(
                    command, SWIFT / "bin", out, variant, [swift, work / PREVIEW],
                    flags=("-swift-version", "6", "-module-name", "ChecklistFormatterGuest",
                           "-module-cache-path", out / "guest-modules", *define))
            except EmbeddedRefusal:
                continue
            else:
                observation.update(compileExit=0, linkInvoked=True,
                                   descriptors=replay_abi.check_descriptors(wasm.read_bytes()))
                require(observation["descriptors"] == self.producer["embedded"]["specialized"]["descriptors"],
                        "specialized Wasm descriptors differ from the producer")
                for path in (obj, wasm):
                    artifacts[path.name] = identity(path)
            observation.update(objectExistsAfter=os.path.lexists(obj), wasmExistsAfter=os.path.lexists(wasm))

        native = [SWIFT / "bin/swiftc", "-swift-version", "6", "-whole-module-optimization", "-O", "-parse-as-library",
                  "-target", "arm64-apple-macosx26.0", "-sdk", sdk,
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
        check_cargo_ancestry(out)
        run("build-owned-vm", RUST / "cargo", "build", "--offline", "--locked", "--release", "--lib", "--jobs", "1",
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
        require(result["readbacks"] == self.producer["readbacks"], "readbacks differ from the exact producer cases")
        result["guestClosedStaleHandleRefusedAndSlotReclaimed"] = sorted(guests)
        run("pinned-worktree-unchanged", GIT, "-C", work, "diff", "--exit-code", "HEAD", "--")
        require(all(identity(work / path) == evidence for path, evidence in result["pinnedInputs"].items()),
                "source projection changed during replay")


class EmbeddedRefusal(Exception):
    pass


def replay(receipt_path, repo):
    receipt_path = receipt_path.parent.resolve(strict=True) / receipt_path.name
    scratch = SCRATCH_ROOT / f"mixer-w07-l03-maintained-{secrets.token_hex(8)}"
    result = {"status": "running", "startedUTC": datetime.now(timezone.utc).isoformat(),
              "publicRepository": PUBLIC, "requestedCommit": PIN,
              "campaignBoundSeconds": CAMPAIGN_SECONDS, "commands": [],
              "cleanup": {"scratch": str(scratch), "state": "planned", "removed": False, "unknown": None},
              "scope": "Single unsigned synthetic Swift formatter. Compact raw frames, 1/1 memory pages, no imports, "
                       "zero host-call budget and 1,000,000 fuel per turn. macOS host and owned Mixer VM only."}
    with Receipt(receipt_path, result) as journal:
        finish_replay(scratch, journal, repo)
    evidence = result.get("publicationHold", result.get("publicationJournal", receipt_path))
    print(f"{result['status']}: {evidence}")
    return result["status"] != "pass"


def finish_replay(scratch, journal, repo):
    result = journal.data
    cleanup = result["cleanup"]
    created = False
    try:
        try:
            result["originalPacket"], producer = verify_original()
            scratch.mkdir(mode=0o700)
            created = True
            cleanup["state"] = "owned"
            journal.save()
            Campaign(scratch, journal, producer, repo).execute()
            result["status"] = "pass"
        except PublicationError:
            raise
        except (Exception, KeyboardInterrupt) as error:
            result["status"] = "held" if cleanup["unknown"] is not None else "incomplete"
            result["failure"] = f"{type(error).__name__}: {error}"
        if cleanup["unknown"] is not None:
            cleanup["state"] = "retained-for-unknown-custody"
        journal.save()
    except (PublicationError, KeyboardInterrupt) as error:
        result["status"] = "held"
        result["publicationError"] = f"{type(error).__name__}: {error}"
        result["publicationJournal"] = str(journal.journal_path)
        result["completedUTC"] = datetime.now(timezone.utc).isoformat()
        if created:
            cleanup["state"] = "retained-for-publication"
            result["publicationHold"] = str(scratch / "publication-hold.json")
            try:
                write_publication_hold(scratch, result)
            except OSError as hold_error:
                del result["publicationHold"]
                result["publicationHoldError"] = str(hold_error)
        # Write held evidence only to the retained journal, even if its name moved.
        try:
            journal.record()
        except OSError as journal_error:
            print(f"cannot record publication failure in journal: {journal_error}", file=sys.stderr)
        print(f"receipt publication failed: {error}", file=sys.stderr)
    else:
        if created and cleanup["unknown"] is None:
            try:
                shutil.rmtree(scratch)
                require(not os.path.lexists(scratch), "owned scratch still exists")
                cleanup.update(state="removed", removed=True)
            except (OSError, ValueError) as error:
                cleanup["error"] = str(error)
                result["status"] = "incomplete"
        result["completedUTC"] = datetime.now(timezone.utc).isoformat()
        journal.record_completion()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path, help="fresh output JSON path in an existing directory")
    parser.add_argument("--repo", type=Path, default=FIXTURE.parents[2],
                        help="local Mixer object store checkout")
    args = parser.parse_args()
    require(sys.flags.isolated, "invoke this replay with the pinned Python in isolated mode (-I -B)")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024**2, 256 * 1024**2))
    sys.dont_write_bytecode = True
    return replay(args.receipt, args.repo.resolve(strict=True))


if __name__ == "__main__":
    sys.exit(main())
