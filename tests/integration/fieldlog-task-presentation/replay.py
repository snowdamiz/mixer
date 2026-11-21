#!/usr/bin/env python3
"""Replay the pinned ordinary FieldLog app through the real Swift package split."""
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANDROID_TARGET = "aarch64-unknown-linux-android28"


class Replay:
    def __init__(self, work):
        self.work = work
        self.commands = work / "commands"
        self.commands.mkdir()
        self.pending = False
        self.records = {}

    def run(self, name, deadline, argv):
        if self.pending:
            raise RuntimeError("Previous command custody is unresolved")
        args = [os.fspath(value) for value in argv]
        log = self.commands / f"{name}.log"
        receipt = self.commands / f"{name}.json"
        self.pending = True
        timed_out = False
        started = time.monotonic()
        with log.open("xb") as output:
            child = subprocess.Popen(args, cwd=self.work, stdout=output, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            try:
                status = child.wait(timeout=deadline)
            except subprocess.TimeoutExpired:
                timed_out = True
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(child.pid, sig)
                    except ProcessLookupError:
                        pass
                    try:
                        status = child.wait(timeout=5)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                else:
                    raise RuntimeError(f"{name}: unable to reap owned child {child.pid}")
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                absent = True
            except PermissionError:
                absent = False
            else:
                absent = False
        data = log.read_bytes()
        row = {
            "argv": [arg.replace(str(self.work), "$WORK") for arg in args],
            "ownedPGID": child.pid, "deadlineSeconds": deadline, "exit": status, "timedOut": timed_out,
            "directChildReaped": True, "ownedGroupAbsent": absent,
            "elapsedSeconds": round(time.monotonic() - started, 3),
            "outputSHA256": hashlib.sha256(data).hexdigest(),
        }
        receipt.write_text(json.dumps(row, indent=2) + "\n")
        if not absent:
            raise RuntimeError(f"{name}: owned group {child.pid} has unresolved custody")
        self.pending = False
        self.records[name] = row
        return (124 if timed_out else status), data

    def cleanup(self):
        if self.pending:
            print(f"Retained unresolved replay scratch at {self.work}", file=sys.stderr)
            return False
        shutil.rmtree(self.work)
        return True


def check(status, output):
    if status:
        sys.stderr.buffer.write(output)
        raise RuntimeError(f"Command exited {status}")
    return output


def publish_receipt(result, report):
    fd, temporary = tempfile.mkstemp(dir=result.parent, prefix=f".{result.name}.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    # A hard link publishes the complete file without replacing any directory
    # entry, including one created by another run after the initial check.
    os.link(temporary, result)
    directory = os.open(result.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    os.unlink(temporary)


def build_args(work, package, label, swift, product):
    paths = work / label
    return [
        swift, "build", "--package-path", package,
        "--scratch-path", paths / "build", "--cache-path", paths / "cache",
        "--config-path", paths / "config", "--security-path", paths / "security",
        "--disable-dependency-cache", "--disable-prefetching", "--disable-index-store",
        "--jobs", "8", "--product", product,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mixer", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--android-swift", type=Path)
    parser.add_argument("--android-sdks", type=Path)
    parser.add_argument("--android-developer-dir", type=Path)
    args = parser.parse_args()
    if (args.android_swift is None) != (args.android_sdks is None):
        parser.error("--android-swift and --android-sdks must be passed together")
    work = args.scratch.resolve()
    result = args.receipt.parent.resolve(strict=True) / args.receipt.name
    if result.is_relative_to(work):
        parser.error("Receipt must be outside scratch")
    if os.path.lexists(result):
        parser.error(f"Receipt already exists: {result}")
    work.mkdir()
    replay = Replay(work)
    cleaned = False
    try:
        (work / "tmp").mkdir()
        os.environ.update(
            TMPDIR=str(work / "tmp"), SWIFTCI_USE_LOCAL_DEPS="1",
            SWIFTPM_MODULECACHE_OVERRIDE=str(work / "module-cache"),
            CLANG_MODULE_CACHE_PATH=str(work / "module-cache"),
        )
        # reconstruct.sh owns the subdirectories under "inputs". Its shell and
        # foreground subprocesses remain in this one supervised group.
        inputs = work / "inputs"
        inputs.mkdir()
        # The reconstruction script creates its own package temp directory.
        check(*replay.run("reconstruct", 60, ["/bin/bash", HERE / "reconstruct.sh", args.mixer.resolve(), inputs]))
        for arm in ("baseline", "initial", "candidate"):
            check(*replay.run(arm + "-prepare", 20, [
                sys.executable, "-B", HERE / "prepare.py", inputs, arm, HERE / "Replay.swift",
            ]))
        status, output = replay.run("initial-package-refusal", 110, build_args(
            work, inputs / "initial/App/Platforms/Android", "initial-build", "/usr/bin/swift", "AppAndroid"))
        denied = ["state", "applyEdit", "titleField"]
        error_lines = [line for line in output.decode(errors="replace").splitlines()
                       if "error:" in line and "'package' protection level" in line]
        if status != 1 or not all(any(f"'{member}'" in line for line in error_lines) for member in denied):
            sys.stderr.buffer.write(output)
            raise RuntimeError("Did not reproduce all three initial package-only access errors")
        observations = {}
        for arm in ("baseline", "candidate"):
            label = arm + "-host"
            check(*replay.run(label + "-build", 110, build_args(
                work, inputs / arm / "HostReplay", label, "/usr/bin/swift", "Replay")))
            binary = work / label / "build/out/Products/Debug/Replay"
            observations[arm] = check(*replay.run(label + "-replay", 15, [binary, work / (arm + "-disk")]))
            print(arm + " replay\n" + observations[arm].decode(), end="", flush=True)
        if observations["baseline"] != observations["candidate"]:
            raise RuntimeError("Baseline and candidate replay observations differ")

        host_toolchain = check(*replay.run("host-toolchain-version", 15, ["/usr/bin/swift", "--version"]))
        android = {"status": "not requested"}
        android_exit = 0
        if args.android_swift is not None:
            tool_env = ["/usr/bin/env", f"DEVELOPER_DIR={args.android_developer_dir.resolve()}"] if args.android_developer_dir else []
            version = check(*replay.run("android-toolchain-version", 15, [*tool_env, args.android_swift, "--version"]))
            android_exit, output = replay.run("candidate-android-AppAndroid", 150, [
                *tool_env, *build_args(work, inputs / "candidate/App/Platforms/Android", "android", args.android_swift, "AppAndroid"),
                "--swift-sdks-path", args.android_sdks, "--swift-sdk", ANDROID_TARGET, "-c", "release",
                "-Xlinker", "-z", "-Xlinker", "max-page-size=16384",
            ])
            rows = output.decode(errors="replace").splitlines()
            android = {"target": ANDROID_TARGET, "swift": version.decode().splitlines(),
                       "status": "compile and link pass" if android_exit == 0 else "compile failed",
                       "diagnostics": [line for line in rows if "error:" in line or "Assertion failed" in line][:20],
                       "tail": rows[-8:]}
            if android_exit == 0:
                lib, = (work / "android/build").rglob("libAppAndroid.so")
                with lib.open("rb") as source:
                    header = source.read(20)
                    if header[:6] != b"\x7fELF\x02\x01" or int.from_bytes(header[18:20], "little") != 183:
                        raise RuntimeError("AppAndroid is not arm64 ELF")
                    source.seek(0)
                    android["librarySHA256"] = hashlib.file_digest(source, "sha256").hexdigest()
                android["libraryBytes"] = lib.stat().st_size
            print("Android " + android["status"], flush=True)

        size = check(*replay.run("scratch-size", 10, ["/usr/bin/du", "-sk", work]))
        if replay.pending:
            raise RuntimeError("Cannot publish with unresolved command custody")
        publish_receipt(result, {
            "mixerRevision": "6bc461f4fc7c29771718c7c5ce5a2a39b78f4d2d",
            "mixerTree": "d888b6a1ef9331079b98a0dc21c3a1b8ee482894",
            "fieldlogPublicRevision": "552559d2d3278abb9b1aa7dcf0288102c09a202b",
            "baselineTree": "380e764598c31181d16ef2fbb91c95bf95693375",
            "initialCandidateTree": "1fb23eb6096ce5d3eb170d47808ab4119e3659c4",
            "correctedCandidateTree": "eb08569c13b5f65e25edd0dfde1fe70fc8278ece",
            "patchSHA256": {patch.name: hashlib.sha256(patch.read_bytes()).hexdigest()
                            for patch in HERE.glob("*.patch")},
            "hostSwift": host_toolchain.decode().splitlines(),
            "hostScope": "macOS host surface using the unchanged Android platform and FieldLog package manifests, AppAndroid product, exact ordinary production source recipe and repository",
            "sdkDependencyResolution": "local path override to the digest-checked exact dependency archive; removed the Android platform lock after matching its pins against the SDK lock",
            "initialCandidateAccessErrors": list(dict.fromkeys(line.split("error: ", 1)[1] for line in error_lines)),
            "identicalHostReplay": observations["candidate"].decode().splitlines(),
            "android": android,
            "settledScratchKiB": int(size.split()[0]),
            "commands": replay.records,
            "retainedScratch": str(work) if android_exit else None,
        })
        if android_exit:
            return android_exit if android_exit > 0 else 128 - android_exit
        cleaned = replay.cleanup()
        if cleaned:
            print(f"Removed scratch after terminal process checks: {work}", flush=True)
        return 0
    finally:
        if not cleaned:
            print(f"Retained replay scratch and command logs at {work}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
