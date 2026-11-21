#!/usr/bin/env python3
"""Run one macOS XCTest using the pinned v81 SDK and FieldLog repository sources.

Run from any directory with Python 3.12+, Git and Xcode. The first run fetches
the pinned FieldLog and SwiftPM dependencies. Pass --fieldlog to reuse a Git
repository with the required FieldLog objects. This command emits a JSON report.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MIXER = "abb32b835c79b0d13189dcf78dff50a5db29a12b"
MIXER_TREE = "3efa3f41546affb13e5842e3b811917774fe2767"
RECORDER_SHA256 = "af6a4ea7e22bd67a4b60f14058e834ca1442eb37414f03b71796434b8a98d16b"
GIT = "/usr/bin/git"
SELECTOR = "HistoricalQueueV3Tests/testHistoricalQueueExchangeAndRenderOwnership"
FIELDLOG_MODULES = {
    "FieldLogModels/Workspace.swift": "91615788bea186663fbb8a23231e304802366f8a",
    "FieldLogStorage/WorkspaceRepository.swift": "c3aa7a10eae986efa52c1bdfb28d3c4c61bc8153",
}
INSTALLED_SOURCES = (
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityInstalledExecutionMode.swift",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift",
    "experimental-capability-runtime/Sources/MixerExperimentalCapabilityRuntime/Native.swift",
    "sdk/Sources/MixerGuest/GuestUIExchangeCodec.swift",
    "sdk/Sources/MixerGuest/GuestUIExchangeCore.swift",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git_repository(path):
    dot_git = path / ".git"
    git_dir = dot_git if dot_git.exists() else path
    return (GIT, "-C", str(path), f"--git-dir={git_dir}")


class BootstrapProcess(subprocess.Popen):
    def __del__(self):
        # An unresolved launch must not trigger CPython's implicit child polling.
        pass


def load_recorder(scratch, commands, environment):
    command = [*git_repository(ROOT), "cat-file", "blob", f"{MIXER}:compiler/qualification_support.py"]
    item = {"name": "recorder-bootstrap", "command": command, "cwd": str(ROOT),
            "timeoutSeconds": 10, "exitCode": None, "terminalCustody": "NOT_STARTED"}
    commands.append(item)
    stdout = scratch / "logs/recorder-bootstrap.stdout"
    stderr = scratch / "logs/recorder-bootstrap.stderr"
    started = time.monotonic()
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            item["terminalCustody"] = "UNKNOWN"
            process = BootstrapProcess(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True)
            item["pid"] = item["pgid"] = process.pid
            try:
                item["exitCode"] = process.wait(timeout=item["timeoutSeconds"])
            finally:
                if item["exitCode"] is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    item["exitCode"] = process.wait(timeout=3)
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    item["terminalCustody"] = "TERMINAL"
    finally:
        item["elapsedSeconds"] = round(time.monotonic() - started, 3)
    require(item["terminalCustody"] == "TERMINAL", "Recorder bootstrap process group still present")
    require(item["exitCode"] == 0, "Recorder bootstrap Git command failed")
    require(stdout.stat().st_size <= 32_768, "Recorder bootstrap exceeded its source size limit")
    support = stdout.read_bytes()
    item["stdoutSHA256"] = hashlib.sha256(support).hexdigest()
    require(item["stdoutSHA256"] == RECORDER_SHA256, "Unexpected qualification_support.py digest")
    tools = {}
    exec(compile(support, "pinned qualification_support.py", "exec"), tools)
    return tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fieldlog", type=Path)
    args = parser.parse_args()
    local = ROOT / "verification/local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="fieldlog-f10-headless-v81-", dir=local))
    commands = []
    report = {"status": "failed", "commands": commands}
    try:
        for name in ("logs", "tmp", "run", "cache", "config", "security", "home"):
            (scratch / name).mkdir()
        environment = {
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": str(scratch / "home"),
            "TMPDIR": str(scratch / "tmp") + "/",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        report["bootstrapEnvironment"] = environment.copy()
        tools = load_recorder(scratch, commands, environment)
        recorder = tools["CommandRecorder"](scratch / "logs", commands, ROOT)

        def run(name, *command, timeout=25, **kwargs):
            return recorder.run(name, command, timeout=timeout, env=environment, **kwargs)

        def mixer(name, *command):
            return run(name, *git_repository(ROOT), *command).strip()

        def blob(name, repo, ref):
            return run(name, *git_repository(repo), "rev-parse", ref).strip()

        report["toolchain"] = {
            "os": run("os", "/usr/bin/sw_vers").strip(),
            "swift": run("swift-version", "/usr/bin/swift", "--version").strip(),
            "macOSSDK": run("sdk-version", "/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version").strip(),
            "git": run("git-version", GIT, "--version").strip(),
        }
        tree = mixer("mixer-tree", "rev-parse", f"{MIXER}^{{tree}}")
        require(tree == MIXER_TREE, "Unexpected Mixer tree")
        corpus = json.loads(mixer("corpus", "cat-file", "blob", f"{MIXER}:compiler/experiments/fieldlog-change-corpus/corpus.json"))
        case = next(case for case in corpus["cases"] if case["id"] == "F10")
        pin, introducing, parent = corpus["pin"], case["after"], case["before"]
        repo = args.fieldlog.resolve() if args.fieldlog else scratch / "fieldlog"
        if not args.fieldlog:
            run("fieldlog-init", GIT, "-C", scratch, "init", "--bare", "--template=", repo)
            run("fieldlog-fetch", *git_repository(repo), "fetch", "--no-tags", "--depth=32", corpus["repository"], pin, timeout=60)

        fieldlog_tree = blob("fieldlog-tree", repo, f"{pin}^{{tree}}")
        require(fieldlog_tree == corpus["pinTree"], "Unexpected FieldLog tree")
        require(blob("f10-parent", repo, f"{introducing}^") == parent, "Unexpected F10 parent")
        for index, anchor in enumerate(case["anchors"]):
            path = anchor["path"]
            absent = run(f"anchor-before-{index}", *git_repository(repo), "ls-tree", parent, "--", path)
            require(not absent and anchor["beforeBlob"] is None, "Unexpected pre-F10 anchor")
            for name, revision in (("introduced", introducing), ("pinned", pin)):
                require(blob(f"anchor-{name}-{index}", repo, f"{revision}:{path}") == anchor["afterBlob"],
                        f"Unexpected historical anchor blob: {path}")
            source = run(f"anchor-source-{index}", *git_repository(repo), "cat-file", "blob", f"{introducing}:{path}")
            first, last = anchor["afterLines"]
            digest = hashlib.sha256("".join(source.splitlines(keepends=True)[first - 1:last]).encode()).hexdigest()
            require(digest == anchor["afterLinesSHA256"], f"Unexpected F10 lines: {path}:{first}")

        bundle = scratch / "sdk.tar"
        mixer("sdk-archive", "archive", f"--output={bundle}", MIXER, "sdk/Sources", "sdk/Package.swift", "sdk/Package.resolved")
        with tarfile.open(bundle) as archive:
            archive.extractall(scratch, filter="data")
        sdk = scratch / "sdk"
        for index, (module, expected) in enumerate(FIELDLOG_MODULES.items()):
            path = f"Integrations/GeneratedReport/Sources/{module}"
            for name, revision in (("introduced", introducing), ("pinned", pin)):
                require(blob(f"fieldlog-{name}-{index}", repo, f"{revision}:{path}") == expected,
                        f"Unexpected FieldLog module: {module}")
            target = sdk / "Sources" / module
            target.parent.mkdir()
            target.write_bytes(run(f"fieldlog-module-{index}", *git_repository(repo), "cat-file", "blob", f"{pin}:{path}").encode())
            require(mixer(f"fieldlog-readback-{index}", "hash-object", target) == expected, f"Module copy differs: {module}")

        tests = sdk / "Tests/HistoricalQueueV3Tests"
        tests.mkdir(parents=True)
        test = tests / "HistoricalQueueV3Tests.swift"
        shutil.copyfile(HERE / test.name, test)
        projection = tests / "QueueProjection.swift"
        projection.write_bytes(run("queue-projection", *git_repository(ROOT), "cat-file", "blob",
                                   f"{MIXER}:{HERE.relative_to(ROOT) / projection.name}").encode())
        digest = tools["digest"]
        require(digest(projection) == "2cdb5814407aab0942263bd8fda93af32c9c7e15cf71eb577b92ebf10cc1ef92",
                "Unexpected v81 queue projection")
        manifest = sdk / "Package.swift"
        lines = manifest.read_text().splitlines(keepends=True)
        require(sum(".testTarget(" in line for line in lines) == 4, "Unexpected pinned test targets")
        manifest.write_text("".join(line for line in lines if ".testTarget(" not in line) + """
package.targets += [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .testTarget(name: "HistoricalQueueV3Tests", dependencies: ["FieldLogModels", "FieldLogStorage", "MixerApple", "MixerGuest", "MixerUI"]),
]
""")
        report["inputs"] = {
            "mixerCommit": MIXER, "mixerTree": tree, "sdkTree": mixer("sdk-tree", "rev-parse", f"{MIXER}:sdk"),
            "fieldlogCommit": pin, "fieldlogTree": fieldlog_tree, "f10IntroducingCommit": introducing,
            "f10Parent": parent, "anchors": case["anchors"], "fieldlogBlobs": FIELDLOG_MODULES,
            "installedSourceBlobs": {path: mixer(f"installed-source-{index}", "rev-parse", f"{MIXER}:{path}")
                                     for index, path in enumerate(INSTALLED_SOURCES)},
            "sha256": {file.name: digest(file) for file in (test, projection, manifest, sdk / "Package.resolved", Path(__file__))},
            "commandRecorderSHA256": RECORDER_SHA256,
        }
        environment["FIELDLOG_F10_RUN"] = str(scratch / "run")
        stdout = run("headless-xctest", "/usr/bin/swift", "test", "--package-path", sdk,
                     "--scratch-path", scratch / "build", "--cache-path", scratch / "cache",
                     "--config-path", scratch / "config", "--security-path", scratch / "security", "--manifest-cache", "local",
                     "--disable-prefetching", "--skip-update", "--force-resolved-versions", "--jobs", "8",
                     "--filter", SELECTOR, timeout=240, expected=(0, 1))
        report["testOutput"] = [line for line in stdout.splitlines()
                                if line.startswith(("F10 ", "Test Case ", "\t Executed "))]
        if commands[-1]["exitCode"] != 0:
            report["compilerDiagnostics"] = [line for line in (scratch / "logs/headless-xctest.stderr").read_text().splitlines()
                                             if "error:" in line][-20:]
        require(commands[-1]["exitCode"] == 0 and "Executed 1 test, with 0 failures" in stdout,
                "The selected XCTest did not pass")
        report["status"] = "passed"
    except Exception as error:
        report["error"] = str(error)
    finally:
        report["observedUTC"] = datetime.now(timezone.utc).isoformat()
        if any(command["terminalCustody"] == "UNKNOWN" for command in commands):
            report["heldScratch"] = str(scratch)
        else:
            shutil.rmtree(scratch)
            report["scratchRemoved"] = not scratch.exists()
        print(json.dumps(report, indent=2).replace(str(scratch), "<scratch>")
              if "heldScratch" not in report else json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
