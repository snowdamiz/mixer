#!/usr/bin/env python3
"""Replay the FieldLog completion calculation edit on macOS."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOCAL = ROOT / "verification/local"
PINS = json.loads((HERE / "inputs.json").read_bytes())
MIXER = PINS["mixer"]
FIELDLOG = PINS["fieldlog"]
TESTS = Path("capability-activation/Tests/MixerCapabilityActivationTests")
RUST = Path(os.environ.get("FIELDLOG_RUST_BIN", Path.home() /
                          ".rustup/toolchains/stable-aarch64-apple-darwin/bin")).resolve()
SWIFT = Path(os.environ.get("FIELDLOG_GUEST_BIN", Path.home() / "Library/Developer/Toolchains" /
                            "swift-6.3.3-RELEASE.xctoolchain/usr/bin")).resolve()
GO = shutil.which("go") or Path.home() / ".local/bin/go"
EXPORTS = ("mixer_guest_ui_start_v1", "mixer_guest_ui_hydrate_v1",
           "mixer_guest_ui_event_v1", "mixer_guest_capability_ready_v1")


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


class Replay:
    def __init__(self, run):
        self.run_directory = run
        self.work = run / "scratch"
        self.source = self.work / "source"
        self.report = {"requirement": "22.2.1", "status": "running", "mixerCommit": MIXER["commit"],
                       "fieldLogCommit": FIELDLOG["commit"], "fieldLogRepository": FIELDLOG["url"],
                       "execution": "macOS host, owned VM and test presentation witness",
                       "nativeOracle": "ordinary FieldLog Workspace.progress(for:) on macOS",
                       "mobile": {"ios": "not_run", "android": "not_run"},
                       "localGatesPassed": [], "gaGatesPassed": [], "commands": [], "inputs": {}}
        self.report["inputs"]["replay.py"] = sha(Path(__file__))
        self.report["inputs"]["inputs.json"] = sha(HERE / "inputs.json")
        (run / "logs").mkdir()
        for path in ("source", "tmp", "lib", "guest", "online/custody", "offline", "checkouts"):
            (self.work / path).mkdir(parents=True)
        work = self.work
        self.env = {key: value for key, value in os.environ.items()
                    if key in {"HOME", "USER", "PATH", "LANG", "TERM"}}
        self.env.update(TMPDIR=str(work / "tmp"), CARGO_HOME=str(work / "cargo-home"),
                        GOCACHE=str(work / "go-cache"), GOMODCACHE=str(work / "go-mod"),
                        GOPROXY="https://proxy.golang.org", GOSUMDB="sum.golang.org",
                        GOENV="off", GOTOOLCHAIN="local", SWIFTCI_USE_LOCAL_DEPS="1",
                        CLANG_MODULE_CACHE_PATH=str(work / "clang-cache"),
                        SWIFTPM_MODULECACHE_OVERRIDE=str(work / "modules"),
                        GIT_TERMINAL_PROMPT="0", GIT_CEILING_DIRECTORIES=str(work), GIT_NO_LAZY_FETCH="1",
                        PATH=str(RUST) + ":" + self.env["PATH"])

    def run(self, name, *args, cwd=None, timeout=90, env=None):
        args = list(map(str, args))
        item = {"name": name, "argv": args, "cwd": str(cwd or self.work), "custody": "UNKNOWN"}
        self.report["commands"].append(item)
        stdout, stderr = [self.run_directory / "logs" / f"{name}.{stream}" for stream in ("stdout", "stderr")]
        with stdout.open("xb") as out, stderr.open("xb") as err:
            child = subprocess.Popen(args, cwd=cwd or self.work, env=env or self.env,
                                     stdout=out, stderr=err, start_new_session=True)
            item["pid"] = child.pid
            item["exit"] = child.wait(timeout=timeout)
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                item["custody"] = "CLOSED"
            else:
                raise RuntimeError(f"{name} process group is still present")
        for stream, path in (("stdout", stdout), ("stderr", stderr)):
            item[stream] = {"sha256": sha(path), "bytes": path.stat().st_size, "path": f"logs/{path.name}"}
        if item["exit"]:
            raise RuntimeError(f"{name} exited {item['exit']}. See {stderr}")
        return stdout.read_text().strip()

    def archive(self, name, repo, rev, dest, *paths):
        tar = self.work / f"{name}.tar"
        self.run(name, "/usr/bin/git", "-C", repo, "archive", "-o", tar, rev, *paths)
        self.report["inputs"][name] = digest = sha(tar)
        if digest != PINS["archivesSHA256"][name]:
            raise ValueError(f"{name} archive does not match its SHA-256 pin")
        dest.mkdir(exist_ok=True)
        with tarfile.open(tar) as data:
            data.extractall(dest, filter="data")
        tar.unlink()

    def checkout(self, name, url, commit):
        repo = self.work / "checkouts" / name
        self.run(f"init-{name}", "/usr/bin/git", "init", "--quiet", repo)
        self.run(f"fetch-{name}", "/usr/bin/git", "-C", repo, "fetch", "--no-tags", "--depth=1", url, commit)
        self.run(f"checkout-{name}", "/usr/bin/git", "-C", repo, "checkout", "--detach", "FETCH_HEAD")
        if self.run(f"commit-{name}", "/usr/bin/git", "-C", repo, "rev-parse", "HEAD") != commit:
            raise ValueError(f"{name} checkout does not match its commit pin")
        return repo

    def prepare(self):
        for relative, expected in PINS["authoredInputsSHA256"].items():
            digest = sha(HERE / relative)
            if digest != expected:
                raise ValueError(f"{relative} does not match its recovered source pin")
            self.report["inputs"][relative] = digest
        self.report["mixerTree"] = self.run(
            "mixer-tree", "/usr/bin/git", "-C", ROOT, "rev-parse", MIXER["commit"] + "^{tree}")
        if self.report["mixerTree"] != MIXER["tree"]:
            raise ValueError("Mixer tree does not match its pin")
        fieldlog = self.checkout("fieldlog", FIELDLOG["url"], FIELDLOG["commit"])
        self.report["fieldLogTree"] = self.run("fieldlog-tree", "/usr/bin/git", "-C", fieldlog, "rev-parse", "HEAD^{tree}")
        if self.report["fieldLogTree"] != FIELDLOG["tree"]:
            raise ValueError("FieldLog tree does not match its pin")
        self.archive("mixer-source", ROOT, MIXER["commit"], self.source,
                     "sdk/Package.swift", "sdk/Package.resolved", "sdk/Sources",
                     "updates/Package.swift", "updates/Sources", "runtime-identity/Package.swift",
                     "runtime-identity/Sources", "experimental-capability-runtime/Package.swift",
                     "experimental-capability-runtime/Sources", "capability-activation/Package.swift",
                     "capability-activation/Sources", TESTS / "Fixtures",
                     TESTS / "FieldLogReleaseV3Child.swift", TESTS / "FieldLogReleaseV3Loopback.swift",
                     "vm/Cargo.toml", "vm/Cargo.lock", "vm/src", "vm/include", "vm/examples", "services")
        self.archive("fieldlog-source", fieldlog, FIELDLOG["commit"], self.source / "fieldlog",
                     "Sources/FieldLogModels", "Sources/FieldLogStorage", "ios/FieldLog/ProjectDetail.swift")
        lock = json.loads((self.source / "sdk/Package.resolved").read_bytes())
        for pin in lock["pins"]:
            name = pin["identity"]
            commit = pin["state"]["revision"]
            repo = self.checkout(name, pin["location"], commit)
            self.archive(name, repo, commit, self.source / name)
        self.report["swiftDependencies"] = lock["pins"]
        for package in ("sdk", "updates"):
            self.replace(self.source / package / "Package.swift",
                         '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")',
                         '.package(path: "../swift-crypto")')
        activation = self.source / "capability-activation"
        for name in ("FieldLogModels", "FieldLogStorage"):
            shutil.copytree(self.source / "fieldlog/Sources" / name, activation / "Sources" / name)
        manifest = activation / "Package.swift"
        self.replace(manifest, "    targets: [", """    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),""")
        self.replace(manifest, 'dependencies: ["MixerCapabilityActivation"], resources:',
                     'dependencies: ["MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage"], resources:')
        self.report["tools"] = {name: self.run(name, *argv) for name, argv in {
            "macOS": ("/usr/bin/sw_vers",), "hostSwift": ("/usr/bin/swift", "--version"),
            "guestSwift": (SWIFT / "swiftc", "--version"), "linker": (SWIFT / "wasm-ld", "--version"),
            "rust": (RUST / "rustc", "--version"), "go": (GO, "version"), "git": ("/usr/bin/git", "--version"),
        }.items()}
        self.report["tools"]["python"] = sys.version.split()[0]

    @staticmethod
    def replace(path, old, new):
        source = path.read_text()
        if source.count(old) != 1:
            raise ValueError(f"Unexpected source at {path}")
        path.write_text(source.replace(old, new))

    def build_vm(self):
        self.run("owned-vm", RUST / "cargo", "build", "--offline", "--locked", "--release", "--lib",
                 "--features", "experimental-capability-native", "--manifest-path", self.source / "vm/Cargo.toml",
                 "--target-dir", self.work / "rust", timeout=150)
        library = self.work / "rust/release/libmixer_vm.a"
        (self.work / "lib/libmixer_vm_capability_experimental.a").symlink_to(library)
        self.report["vmSHA256"] = sha(library)

    def build_service(self):
        executable = self.work / "mixer-service"
        self.run("build-service", GO, "-C", self.source / "services", "build", "-mod=readonly", "-modcacherw",
                 "-o", executable, "./cmd/mixer-service", timeout=150)
        self.report["serviceSHA256"] = sha(executable)

    def patch(self, name, directory):
        patch = HERE / "patches" / (name + ".patch")
        self.run("apply-" + name, "/usr/bin/git", "apply", "--whitespace=error", patch, cwd=directory)

    def build_guests(self):
        guest = self.work / "guest"
        for name in ("Guest.swift", "TaskWire.swift"):
            shutil.copyfile(HERE / "guest" / name, guest / name)
        shutil.copyfile(HERE / "../fieldlog-saved-draft/guest/CapabilityImports.c", guest / "CapabilityImports.c")
        self.patch("row-guest-completion-preview", guest)
        self.run("guest-c", SWIFT / "clang", "--target=wasm32-unknown-none", "-ffreestanding",
                 "-Oz", "-c", "CapabilityImports.c", "-o", "capability.o", cwd=guest)
        self.report["payloads"] = {}
        for name in ("baseline", "reviewed"):
            if name == "reviewed":
                self.patch("completion-fix", guest)
            self.run(name + "-swift", SWIFT / "swiftc", "-target", "wasm32-unknown-none-wasm",
                     "-enable-experimental-feature", "Embedded", "-enable-experimental-feature", "Extern",
                     "-whole-module-optimization", "-Osize", "-parse-as-library",
                     "-Xfrontend", "-disable-stack-protector", "-D", "FIELDLOG_UPDATED",
                     "-module-cache-path", guest / "modules", "-emit-object",
                     "Guest.swift", "TaskWire.swift", "-o", name + ".o", cwd=guest)
            wasm = self.work / f"{name}.wasm"
            self.run(name + "-wasm", SWIFT / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all",
                     "-z", "stack-size=16384", "--max-memory=65536", *(f"--export={e}" for e in EXPORTS),
                     name + ".o", "capability.o", "-o", wasm, cwd=guest)
            self.report["payloads"][name] = {"bytes": wasm.stat().st_size, "sha256": sha(wasm)}

    def test(self):
        tests = self.source / TESTS
        for name in ("RowFixture.swift", "RowStorage.swift", "CompletionTests.swift"):
            shutil.copyfile(HERE / "host" / name, tests / name)
        self.patch("row-host-completion-preview", tests)
        flags = ("--package-path", self.source / "capability-activation", "--scratch-path", self.work / "swiftpm",
                 "--cache-path", self.work / "swift-cache", "--config-path", self.work / "swift-config",
                 "--security-path", self.work / "swift-security", "--disable-dependency-cache",
                 "--jobs", "8", "-Xswiftc", "-gnone",
                 "-Xcc", "-I" + str(self.source / "vm/include"), "-Xlinker", "-L" + str(self.work / "lib"))
        self.run("build-host", "/usr/bin/swift", "build", "--build-tests", *flags, timeout=260)
        products = (self.work / "swiftpm").rglob("MixerCapabilityActivation*Tests.xctest")
        binaries = {candidate.resolve() for product in products
                    if (candidate := product / "Contents/MacOS" / product.stem).is_file()}
        if len(binaries) != 1:
            raise RuntimeError(f"Expected one built activation host executable, found {len(binaries)}")
        binary, = binaries
        self.report["installedBinaryPath"] = str(binary.relative_to(self.work))
        self.report["installedBinarySHA256"] = sha(binary)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        self.report["port"] = port
        env = dict(self.env, FIELDLOG_ROW_RUN=str(self.work), FIELDLOG_ROW_PORT=str(port),
                   FIELDLOG_ROW_VM=self.report["vmSHA256"])
        for phase in ("Online", "Offline"):
            if phase == "Offline":
                with socket.socket() as probe:
                    probe.settimeout(1)
                    if probe.connect_ex(("127.0.0.1", port)) != errno.ECONNREFUSED:
                        raise RuntimeError("Stopped developer origin still accepts connections")
                self.report["offlineListenerRefused"] = True
            self.run(phase.lower() + "-test", "/usr/bin/swift", "test", "--skip-build", *flags,
                     "--filter", "FieldLogCompletionTests/test" + phase, timeout=50, env=env)
            if sha(binary) != self.report["installedBinarySHA256"]:
                raise RuntimeError("Installed host binary changed")
            self.report[phase.lower()] = json.loads((self.work / phase.lower() / "outcome.json").read_bytes())
        if self.report["online"]["pid"] == self.report["offline"]["pid"]:
            raise RuntimeError("Cold reopen did not run in a new process")
        if self.report["online"]["workspace"] != self.report["offline"]["workspace"]:
            raise RuntimeError("Online and offline dataset identities differ")
        if self.report["online"]["runtime"] != self.report["offline"]["runtime"]:
            raise RuntimeError("The cold reopen used a different runtime identity")
        if ((self.work / "online/workspace/workspace.json").read_bytes()
                != (self.work / "online/seed-workspace.json").read_bytes()):
            raise RuntimeError("The cold close changed the saved workspace bytes")
        self.report["byteExactAfterColdClose"] = True

    def finish(self):
        custody = self.work / "online/custody/service.json"
        if custody.exists():
            try:
                self.report["serviceCustody"] = json.loads(custody.read_bytes())
            except (OSError, ValueError) as error:
                self.report["serviceCustody"] = {"state": "UNKNOWN", "error": str(error)}
        service = self.report.get("serviceCustody")
        service_closed = service is None or service.get("state") == "NOT_LAUNCHED" or (
            service.get("state") == "CLOSED" and service.get("directChildReaped") and service.get("ownedGroupAbsent")
        )
        if self.report["status"] == "passed" and (service is None or service.get("state") != "CLOSED"):
            self.report.update(status="failed", error="The release service did not record terminal custody")
        if (any(item["custody"] != "CLOSED" for item in self.report["commands"])
                or not service_closed):
            self.report.update(status="hold", cleanup="Preserved scratch after unresolved custody")
        else:
            try:
                shutil.rmtree(self.work)
            except OSError as error:
                self.report.update(status="failed", cleanup=f"Incomplete scratch cleanup: {error}")
            else:
                self.report["cleanup"] = "Removed disposable checkouts, builds, caches, payloads and stores"
        self.report["observedUTC"] = datetime.now(timezone.utc).isoformat()
        (self.run_directory / "receipt.json").write_text(json.dumps(self.report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Fresh single-component run name")
    args = parser.parse_args()
    if Path(args.name).name != args.name or args.name in ("", ".", "..") or sys.platform != "darwin":
        parser.error("use a fresh single-component name on macOS")
    os.umask(0o077)
    LOCAL.mkdir(parents=True, exist_ok=True)
    run = LOCAL / ("fieldlog-task-calculation-" + args.name)
    run.mkdir()
    case = Replay(run)
    try:
        case.prepare()
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = [pool.submit(build) for build in (case.build_vm, case.build_service, case.build_guests)]
            for job in jobs:
                job.result()
        case.test()
        case.report["status"] = "passed"
    except BaseException as error:
        case.report.update(status="failed", error=str(error))
        raise
    finally:
        case.finish()
    print(run / "receipt.json")
    if case.report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
