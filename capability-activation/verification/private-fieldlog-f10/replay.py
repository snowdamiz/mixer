#!/usr/bin/env python3
"""Run the isolated macOS signed FieldLog F10 smoke from a committed draft."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RECORDER_SHA256 = "af6a4ea7e22bd67a4b60f14058e834ca1442eb37414f03b71796434b8a98d16b"

BASE = "baed0bf0b2862f699b861baf15636bc3b668b508"
FINGERPRINT_FIX = "b350a633729dec244b500f2ad3e6b8bb8371ab30"
PUBLIC = "e1202816e8bb5bbeb3583c0d458918923b895426"
CAUSAL = "24efc0854e6a95226e4da0db7c64f71489acea56"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
FIELDLOG_TREE = "1b62520f35c7e57a01b568291078686574f627c4"
FIELDLOG_SOURCES = {
    "FieldLogModels/Workspace.swift": "91615788bea186663fbb8a23231e304802366f8a",
    "FieldLogStorage/WorkspaceRepository.swift": "c3aa7a10eae986efa52c1bdfb28d3c4c61bc8153",
}
FIXTURE = HERE.relative_to(ROOT)
QUEUE = Path("compiler/experiments/fieldlog-change-corpus/pending-queue")
REGRESSION = ("testInstalledApplicationStorageGrantDenialAndColdReadback|"
              "testSignedCommitFactsReadUsesAcceptedEventOnceAndRetiresWithOwner|"
              "testEarlyInstalledMilestonesWakeAutomaticHealthAndStartupAloneDoesNot")
INPUTS = ("capabilities", "capability-activation", "experimental-capability-runtime", "runtime-identity",
          "sdk", "updates", "vm", QUEUE / "QueueProjection.swift", QUEUE / "Imports.c")
PACKAGE_ADDITION = """
package.targets += [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
]
package.targets.first { $0.name == "MixerCapabilityActivationTests" }!.dependencies += ["FieldLogModels", "FieldLogStorage"]
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True, help="Full committed Mixer draft revision")
    parser.add_argument("--cargo", required=True, type=Path)
    parser.add_argument("--guest-tools", required=True, type=Path, help="Swift 6.3.3 toolchain bin directory")
    parser.add_argument("--fieldlog", type=Path, help="Read an existing Git object store instead of fetching the pin")
    args = parser.parse_args()
    require(sys.platform == "darwin", "The private FieldLog smoke requires macOS")
    require(len(args.revision) == 40 and all(c in "0123456789abcdef" for c in args.revision),
            "Use an exact full commit ID")
    compiler = ROOT / "compiler"
    require(sha256((compiler / "qualification_support.py").read_bytes()).hexdigest() == RECORDER_SHA256,
            "Run from a checkout with the reviewed command recorder")
    sys.path.insert(0, str(compiler))
    from qualification_support import CommandRecorder, clean_environment, digest

    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="fieldlog-f10-signed-replay-", dir=local))
    commands = []
    report = {"status": "failed", "startedUTC": datetime.now(timezone.utc).isoformat(),
              "architecture": platform.machine(), "reviewedBase": BASE, "publishedV82": PUBLIC,
              "fingerprintFix": FINGERPRINT_FIX,
              "headlessCausalCheckpoint": CAUSAL, "sourceRevision": args.revision,
              "commandRecorderSHA256": RECORDER_SHA256,
              "commands": commands}
    try:
        for name in ("logs", "tmp", "lib", "config", "security", "cache", "source"):
            (scratch / name).mkdir()
        environment = clean_environment()
        environment.update({
            "PATH": f"{args.cargo.resolve().parent}:/usr/bin:/bin:/usr/sbin:/sbin",
            "TMPDIR": str(scratch / "tmp") + "/",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_ASKPASS": "/usr/bin/false",
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "MIXER_F10_RUN": str(scratch),
        })
        recorder = CommandRecorder(scratch / "logs", commands, scratch / "source")

        def run(name, *command, timeout=40):
            try:
                return recorder.run(name, command, timeout=timeout, env=environment)
            finally:
                if commands and commands[-1]["name"] == name:
                    commands[-1]["timeoutSeconds"] = timeout

        def mixer(name, *command, timeout=40):
            return run(name, "/usr/bin/git", "-C", ROOT, *command, timeout=timeout).strip()

        report["toolchain"] = {
            "macOS": run("macos", "/usr/bin/sw_vers").strip(),
            "xcode": run("xcode", "/usr/bin/xcodebuild", "-version").strip(),
            "swift": run("swift", "/usr/bin/swift", "--version").strip(),
            "cargo": run("cargo", args.cargo, "--version").strip(),
            "guestSwift": run("guest-swift", args.guest_tools / "swiftc", "--version").strip(),
            "guestLinker": run("guest-linker", args.guest_tools / "wasm-ld", "--version").strip(),
        }
        require("Swift version 6.3.3" in report["toolchain"]["guestSwift"], "Expected pinned Swift 6.3.3 guest tools")
        mixer("reviewed-base", "merge-base", "--is-ancestor", BASE, args.revision)
        report["sourceTree"] = mixer("source-tree", "rev-parse", f"{args.revision}^{{tree}}")
        archive = scratch / "source.tar"
        mixer("source-archive", "archive", f"--output={archive}", args.revision, *INPUTS)
        report["sourceArchiveSHA256"] = digest(archive)
        environment["MIXER_F10_SOURCE_SHA256"] = report["sourceArchiveSHA256"]
        source = scratch / "source"
        with tarfile.open(archive) as bundle:
            bundle.extractall(source, filter="data")
        report["generatedCapabilityIdentity"] = json.loads(run(
            "native-capability-fingerprint", sys.executable, "-B", source / "capabilities/tools/generate.py", "--check"))
        require(report["generatedCapabilityIdentity"]["nativeImplementationSHA256"] ==
                "5d467c65cf58917ab499840226bb5ae577fbae3cd063577985555141d131e92a",
                "Expected the corrected installed capability fingerprint")

        private = source / FIXTURE
        report["inputSHA256"] = {name: digest(private / name) for name in
                                 ("Guest.swift", "PrivateFieldLogF10Tests.swift", "feature-wire.txt", "mui3-header.txt", "replay.py")}
        projection = source / QUEUE / "QueueProjection.swift"
        report["inputSHA256"]["QueueProjection.swift"] = digest(projection)
        require(report["inputSHA256"]["QueueProjection.swift"] ==
                "2cdb5814407aab0942263bd8fda93af32c9c7e15cf71eb577b92ebf10cc1ef92",
                "Historical F10 projection differs from the causal fixture")

        repo = args.fieldlog.resolve() if args.fieldlog else scratch / "fieldlog"
        if not args.fieldlog:
            run("fieldlog-init", "/usr/bin/git", "init", "--bare", "--template=", repo)
            run("fieldlog-fetch", "/usr/bin/git", "-C", repo, "-c", "credential.helper=", "fetch", "--no-tags", "--depth=1",
                "https://github.com/snowdamiz/fieldlog.git", FIELDLOG, timeout=60)

        def fieldlog(name, *command):
            return run(name, "/usr/bin/git", "-C", repo, *command)

        require(fieldlog("fieldlog-tree", "rev-parse", f"{FIELDLOG}^{{tree}}").strip() == FIELDLOG_TREE,
                "Unexpected exact FieldLog tree")
        report["fieldlog"] = {"commit": FIELDLOG, "tree": FIELDLOG_TREE, "blobs": FIELDLOG_SOURCES}
        package = source / "capability-activation"
        for index, (relative, oid) in enumerate(FIELDLOG_SOURCES.items()):
            ref = f"{FIELDLOG}:Integrations/GeneratedReport/Sources/{relative}"
            require(fieldlog(f"fieldlog-blob-{index}", "rev-parse", ref).strip() == oid, "FieldLog source blob differs")
            target = package / "Sources" / relative
            target.parent.mkdir()
            fieldlog(f"fieldlog-source-{index}", "cat-file", "blob", ref)
            shutil.copyfile(scratch / "logs" / f"fieldlog-source-{index}.stdout", target)
            require(mixer(f"fieldlog-readback-{index}", "hash-object", target) == oid, "FieldLog source copy differs")

        run("guest-imports", args.guest_tools / "clang", "--target=wasm32-unknown-none-wasm", "-Os", "-c",
            source / QUEUE / "Imports.c", "-o", scratch / "imports.o")
        report["wasmSHA256"] = {}
        for name, flags in (("good", ()), ("wrong-document", ("-D", "F10_WRONG_DOCUMENT")),
                            ("wrong-request", ("-D", "F10_WRONG_REQUEST"))):
            obj, wasm = scratch / f"{name}.o", scratch / f"{name}.wasm"
            run(f"compile-{name}", args.guest_tools / "swiftc", "-target", "wasm32-unknown-none-wasm",
                "-enable-experimental-feature", "Embedded", "-enable-experimental-feature", "Extern",
                "-whole-module-optimization", "-Osize", "-parse-as-library", "-Xfrontend",
                "-disable-stack-protector", *flags, "-emit-object", projection, private / "Guest.swift", "-o", obj)
            run(f"link-{name}", args.guest_tools / "wasm-ld", "--fatal-warnings", "--no-entry", "--gc-sections",
                "--strip-all", "-z", "stack-size=8192", "--max-memory=1310720",
                "--export=mixer_guest_ui_start_v3", "--export=mixer_guest_ui_event_v3",
                "--export=mixer_guest_ui_ready_v3", obj, scratch / "imports.o", "-o", wasm)
            report["wasmSHA256"][name] = digest(wasm)

        run("build-private-vm", args.cargo, "build", "--offline", "--locked", "--release", "--lib",
            "--features", "private-fieldlog-f10", "--manifest-path", source / "vm/Cargo.toml",
            "--target-dir", scratch / "rust", timeout=90)
        vm = scratch / "rust/release/libmixer_vm.a"
        report["nativeArchiveSHA256"] = digest(vm)
        (scratch / "lib/libmixer_vm_capability_experimental.a").symlink_to(vm)

        with (package / "Package.swift").open("a") as manifest:
            manifest.write(PACKAGE_ADDITION)
        shutil.copyfile(private / "PrivateFieldLogF10Tests.swift",
                        package / "Tests/MixerCapabilityActivationTests/PrivateFieldLogF10Tests.swift")
        swift = ("/usr/bin/swift", "test", "--build-system", "native", "--package-path", package,
                 "--cache-path", scratch / "cache", "--config-path", scratch / "config", "--security-path",
                 scratch / "security", "--force-resolved-versions", "--disable-index-store", "--no-parallel",
                 "--disable-swift-testing", "--jobs", "8", "-Xcc", f"-I{source / 'vm/include'}")
        private_output = run("private-xctest", *swift, "--scratch-path", scratch / "swift-private",
                             "-Xswiftc", "-DMIXER_PRIVATE_F10", "-Xcc", "-DMIXER_PRIVATE_F10",
                             "-Xlinker", f"-L{scratch / 'lib'}",
                             "--filter", f"(PrivateFieldLogF10Tests|{REGRESSION})", timeout=180)
        report["privateObservations"] = [line for line in private_output.splitlines() if line.startswith(("F10 ", "W09 "))]
        require(len(report["privateObservations"]) == 9, "Missing the F10 or W09 observations")
        shutil.rmtree(scratch / "swift-private")

        run("build-standard-vm", args.cargo, "build", "--offline", "--locked", "--release", "--lib",
            "--features", "experimental-capability-native", "--manifest-path", source / "vm/Cargo.toml",
            "--target-dir", scratch / "rust", timeout=90)
        report["standardArchiveSHA256"] = digest(vm)
        standard_output = run("standard-xctest", *swift, "--scratch-path", scratch / "swift-standard",
                              "-Xlinker", f"-L{scratch / 'lib'}", "--filter", f"({REGRESSION})", timeout=180)
        report["standardObservations"] = [line for line in standard_output.splitlines() if line.startswith(("W09 ", "Test Case "))]
        require("W09 signed storage retirement confirmed" in report["standardObservations"], "Missing the standard W09 observation")
        report["status"] = "passed"
    except (ValueError, RuntimeError, OSError) as error:
        report["error"] = str(error)
        if commands and commands[-1].get("terminalCustody") == "TERMINAL":
            last = commands[-1]["name"]
            for stream in ("stdout", "stderr"):
                log = scratch / "logs" / f"{last}.{stream}"
                if log.is_file():
                    with log.open("rb") as output:
                        if stream == "stdout":
                            lines = output.read(2_000_000).decode(errors="replace").splitlines()
                            report["testFailures"] = [line for line in lines if ": error: " in line][:30]
                        output.seek(max(0, log.stat().st_size - 12_000))
                        report[f"last{stream.title()}"] = output.read().decode(errors="replace").splitlines()[-30:]
    finally:
        held = [item["name"] for item in commands if item.get("terminalCustody", "UNKNOWN") == "UNKNOWN"]
        if held:
            report["cleanup"] = {"preserved": str(scratch), "unresolvedCommands": held}
        else:
            shutil.rmtree(scratch)
            report["cleanup"] = {"scratchRemoved": not scratch.exists(), "commandGroupsResolved": True}
        print(json.dumps(report, indent=2, default=str))
    return 0 if report["status"] == "passed" and report["cleanup"].get("scratchRemoved") else 1


if __name__ == "__main__":
    raise SystemExit(main())
