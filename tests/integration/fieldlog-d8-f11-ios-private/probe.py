"""Cross-compile the pinned F11 SDK and its exact installed exchange call."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
STAGE = "5e43e50a06d8cf17500a9732c9ea111fba5054d4"
STAGE_TREE = "e53d4279b6074f862e38ffe7a0813887e62b1ae6"
F04_BASE = "6c069d95f509e197433118f65b7f39fb3a454412"
F04_TREE = "d7c53c7dba790ba4635efdcda73aea3ad2263e9a"
F04_PATCH_REF = "b9d227c81c1c87b51d40fa55718ffbb18734c258:tests/integration/fieldlog-d8-f04-signed/task-retry-replay.patch"
F04_PATCH_SHA = "851f70692271d0600930e3c51831fcfd68c884bfb6598f6e54a51da13c58110f"
EXCHANGE_BEFORE = "9c42c9cb1f7afbf1587cfefd0cc3ba90ec1799a601958785ecf9a0f2c135a3c0"
EXCHANGE_AFTER = "5631495534b8a9dbffe7db7abf6da9a26bff14dfdf333b85fd72c71d1d98d0c8"
NOTE_SHA = "ef98cc3582cd8521e35e262116399935fa4075e93507c27dfa876325e0e7ea21"
WORKER_SHA = "972d192cf014a4767ac71cf5a68ae248aa9849b318786aa5088ae099ae37af8f"
CRYPTO = "c2cbadd7263439d8015189668f96ff5b5be565ce"
LIMIT_SECONDS = 720
LIMIT_KIB = 1_572_864


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def report(scratch, evidence):
    (scratch / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")


def worker(stage, crypto, scratch):
    evidence = {"stage": STAGE, "stageTree": STAGE_TREE, "f04ExportTree": F04_TREE,
                "swiftCryptoRevision": CRYPTO, "commands": []}

    def run(name, *argv, cwd=scratch, expected=0, stdin=None):
        result = subprocess.run(argv, cwd=cwd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diagnostic = result.stderr.decode(errors="replace")
        row = {"step": name, "argv": [str(arg).replace(str(scratch), "$scratch")
                                      .replace(str(HERE), "$fixture").replace(str(stage), "$stage")
                                      .replace(str(crypto), "$swift_crypto_git") for arg in argv],
               "exit": result.returncode}
        # Swift command lines list the full source set. Preserve a replayable
        # glob and pin the source tree instead of repeating hundreds of paths.
        if name.startswith("emit-"):
            sources = [arg for arg in row["argv"] if arg.endswith(".swift")]
            row["argv"] = [arg for arg in row["argv"] if not arg.endswith(".swift")]
            source_root = "swift-crypto/Sources/Crypto" if name.endswith("-Crypto") else "source/sdk/Sources/" + name.split("-")[-1]
            row["swiftSources"] = {"root": "$scratch/" + source_root, "glob": "**/*.swift",
                                   "count": len(sources), "order": "sorted"}
        if diagnostic:
            row["stderr"] = diagnostic.replace(str(scratch), "$scratch").replace(str(HERE), "$fixture")[-3500:]
        evidence["commands"].append(row)
        report(scratch, evidence)
        require(result.returncode == expected, f"{name}: expected exit {expected}, observed {result.returncode}")
        return result.stdout

    def git(name, repository, *args, **kwargs):
        return run(name, "git", "-C", repository, *args, **kwargs)

    def extract(name, repository, revision, destination, *paths):
        result = git(name, repository, "archive", revision, *paths)
        archive = scratch / "source.tar"
        archive.write_bytes(result)
        with tarfile.open(archive) as stream:
            stream.extractall(destination, filter="data")
        archive.unlink()

    def capture(name, *argv):
        return run(name, *argv).decode().strip()

    evidence["tools"] = {
        "xcode": capture("xcode-version", "/usr/bin/xcodebuild", "-version"),
        "swift": capture("swift-version", "/usr/bin/xcrun", "swiftc", "--version"),
    }
    require(git("stage-tree", stage, "rev-parse", f"{STAGE}^{{tree}}").decode().strip() == STAGE_TREE,
            "Stage tree mismatch")
    patch = git("f04-patch", stage, "show", F04_PATCH_REF)
    require(sha(patch) == F04_PATCH_SHA, "F04 patch digest mismatch")
    source = scratch / "source"
    source.mkdir()
    extract("f04-source", stage, F04_BASE, source, "vm", "sdk", "updates", "capability-activation",
            "runtime-identity", "experimental-capability-runtime", "contracts",
            "tests/integration/fieldlog-d8-f04-signed")
    git("init-export-index", source, "init", "--quiet", "--template=")
    git("index-export", source, "add", "-f", ".")
    git("f04-apply", source, "apply", "--index", "--unidiff-zero", "--whitespace=error", "-", stdin=patch)
    require(git("f04-tree", source, "write-tree").decode().strip() == F04_TREE, "F04 export tree mismatch")
    guest = source / "sdk/Sources/MixerGuest"
    exchange = guest / "GuestUIExchangeV1.swift"
    original = exchange.read_bytes()
    require(sha(original) == EXCHANGE_BEFORE, "F04 exchange digest mismatch")
    f11 = original.replace(b"FieldLogTaskRetry", b"FieldLogNoteFixture").replace(
        b"fieldLogTaskRetry", b"fieldLogNoteFixture")
    require(sha(f11) == EXCHANGE_AFTER, "F11 exchange digest mismatch")
    exchange.write_bytes(f11)
    codec = git("f11-codec", stage, "show", f"{STAGE}:tests/integration/fieldlog-d8-f11-vertical-private/NoteCodec.swift")
    require(sha(codec) == NOTE_SHA, "F11 codec digest mismatch")
    (guest / "GuestUIFieldLogNoteFixture.swift").write_bytes(codec)
    activation_path = "capability-activation/Sources/MixerCapabilityActivation/CapabilityColdStartWorker.swift"
    installed = (source / activation_path).read_bytes().replace(b"FieldLogTaskRetry", b"FieldLogNoteFixture").replace(
        b"fieldLogTaskRetry", b"fieldLogNoteFixture")
    require(sha(installed) == WORKER_SHA, "F11 installed worker digest mismatch")
    probe = (HERE / "ExchangeConstructor.swift").read_bytes()
    require(b"GuestUIExchangeV1(fieldLogNoteFixtureGeneration: generation)" in installed,
            "Installed owner call changed")
    require(b"GuestUIExchangeV1(fieldLogNoteFixtureGeneration: 1)" in probe,
            "Consumer probe call changed")
    evidence["digests"] = {"f04Patch": sha(patch), "f11Exchange": sha(f11), "f11Codec": sha(codec),
                           "f11InstalledWorker": sha(installed), "swiftProbe": sha(probe),
                           "driver": sha(Path(__file__).read_bytes())}

    crypto_root = scratch / "swift-crypto"
    crypto_root.mkdir()
    extract("crypto-source", crypto, CRYPTO, crypto_root, "Sources/Crypto")
    compiler = capture("swift-path", "/usr/bin/xcrun", "--find", "swiftc")
    for name, sdk, triple in [("macOS", "macosx", "arm64-apple-macosx14.0"),
                              ("simulator", "iphonesimulator", "arm64-apple-ios26.0-simulator")]:
        sdk_root = capture(f"{name}-sdk", "/usr/bin/xcrun", "--sdk", sdk, "--show-sdk-path")
        modules = scratch / name
        modules.mkdir()
        flags = ["-target", triple, "-sdk", sdk_root, "-swift-version", "6", "-I", modules,
                 "-module-cache-path", scratch / f"{name}-modules",
                 "-D", "MIXER_PRIVATE_FIELDLOG_EDITOR", "-D", "MIXER_F11_HOST_ACTION_FIXTURE",
                 "-D", "MIXER_F11_IOS_FIXTURE"]
        for module, files in [
            ("Crypto", crypto_root / "Sources/Crypto"),
            ("MixerCore", source / "sdk/Sources/MixerCore"),
            ("MixerUI", source / "sdk/Sources/MixerUI"),
            ("MixerGuest", guest),
        ]:
            options = ["-package-name", "mixer"]
            if module == "Crypto":
                options = ["-package-name", "swift_crypto", "-D", "CRYPTO_IN_SWIFTPM",
                           "-enable-experimental-feature", "CheckImplementationOnly"]
            run(f"emit-{name}-{module}", compiler, *flags, *options, "-parse-as-library", "-emit-module",
                "-module-name", module, "-emit-module-path", modules / f"{module}.swiftmodule",
                *sorted(files.rglob("*.swift")))
        call = HERE / "ExchangeConstructor.swift"
        run(f"{name}-stock-control", compiler, *flags, "-D", "F11_CONTROL_STOCK", "-typecheck", call)
        run(f"{name}-private-call", compiler, *flags, "-typecheck", call,
            expected=1 if name == "simulator" else 0)
        if name == "simulator":
            diagnostic = evidence["commands"][-1].get("stderr", "")
            require("fieldLogNoteFixtureGeneration" in diagnostic and "error:" in diagnostic and
                    ("incorrect argument label" in diagnostic or "extraneous argument label" in diagnostic),
                    "Simulator failure did not isolate the private constructor")
    evidence["status"] = "blocked-at-pinned-sdk-simulator-exchange-constructor"
    commands = evidence.pop("commands")
    evidence["steps"] = {command["step"]: command["exit"] for command in commands}
    evidence["simulatorModuleBuild"] = next(row for row in commands if row["step"] == "emit-simulator-MixerGuest")
    evidence["simulatorPrivateCall"] = commands[-1]
    report(scratch, evidence)


def allocated_kib(scratch):
    blocks = 0
    for path, directories, files in os.walk(scratch):
        for entry in [Path(path), *(Path(path) / file for file in files),
                      *(Path(path) / directory for directory in directories if (Path(path) / directory).is_symlink())]:
            try:
                blocks += entry.lstat().st_blocks
            except FileNotFoundError:
                pass
    return (blocks + 1) // 2


def absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


def retire(process):
    for signum in (None, signal.SIGTERM, signal.SIGKILL):
        if process.poll() is not None and absent(process.pid):
            return
        if signum is None:
            continue
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass
        until = time.monotonic() + 2
        while time.monotonic() < until:
            if process.poll() is not None and absent(process.pid):
                return
            time.sleep(0.05)
    raise RuntimeError("Direct child reaping and group absence were not both established")


def controller(stage, crypto):
    started = time.monotonic()
    scratch = Path(tempfile.mkdtemp(prefix="mixer-f11-ios-compile-", dir="/private/tmp"))
    process = None
    attempted = False
    exit_code = None
    evidence = {}
    peak = 0

    def interrupted(signum, _frame):
        raise RuntimeError(f"Interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        (scratch / "tmp").mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(TMPDIR=str(scratch / "tmp") + "/", CLANG_MODULE_CACHE_PATH=str(scratch / "clang"),
                   GIT_NO_LAZY_FETCH="1", GIT_ALLOW_PROTOCOL="file", GIT_OPTIONAL_LOCKS="0",
                   GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0",
                   PYTHONDONTWRITEBYTECODE="1", LC_ALL="C")
        profile = ("(version 1) (allow default) (deny network*) "
                   f"(deny file-write* (require-not (require-any (subpath {json.dumps(str(scratch))}) (literal \"/dev/null\"))))")
        with (scratch / "worker.log").open("xb") as log:
            attempted = True
            process = subprocess.Popen(
                ["/usr/bin/sandbox-exec", "-p", profile, sys.executable, "-B", __file__, str(stage),
                 str(crypto), "--worker", str(scratch)], cwd=scratch, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=log, start_new_session=True)
            while True:
                peak = max(peak, allocated_kib(scratch))
                require(peak <= LIMIT_KIB and time.monotonic() - started < LIMIT_SECONDS - 8,
                        "Compile probe exceeded its resource budget")
                try:
                    exit_code = process.wait(timeout=0.4)
                    break
                except subprocess.TimeoutExpired:
                    continue
        require(absent(process.pid), "Probe exited with group still present")
        metadata = scratch / "evidence.json"
        if metadata.exists():
            evidence = json.loads(metadata.read_bytes())
        if exit_code:
            evidence["probeError"] = (scratch / "worker.log").read_text().replace(str(scratch), "$scratch")[-2500:]
        else:
            require(evidence.get("status") == "blocked-at-pinned-sdk-simulator-exchange-constructor",
                    "Missing discriminating compile result")
    except (OSError, RuntimeError, ValueError, KeyboardInterrupt) as exc:
        evidence["probeError"] = str(exc)
    finally:
        try:
            if process is not None:
                retire(process)
            elif attempted:
                raise RuntimeError("Launch attempted without an observed worker identity")
        except (RuntimeError, OSError) as exc:
            evidence["hold"] = {"reason": str(exc), "scratch": str(scratch), "pgid": process.pid if process else None}
        if "hold" not in evidence:
            shutil.rmtree(scratch)
    evidence["run"] = {"seconds": round(time.monotonic() - started, 2), "limitSeconds": LIMIT_SECONDS,
                       "peakAllocatedKiB": peak, "limitAllocatedKiB": LIMIT_KIB, "network": "denied",
                       "workerPGID": process.pid if process else None, "workerExit": exit_code,
                       "workerGroupAbsent": "hold" not in evidence and process is not None,
                       "scratchRemoved": "hold" not in evidence}
    print(json.dumps(evidence, indent=2))
    return int("probeError" in evidence or "hold" in evidence)


def existing_path(value):
    return Path(value).resolve(strict=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=existing_path)
    parser.add_argument("crypto_git", type=existing_path)
    parser.add_argument("--worker", type=existing_path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        worker(args.stage, args.crypto_git, args.worker)
    else:
        raise SystemExit(controller(args.stage, args.crypto_git))
