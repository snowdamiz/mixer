#!/usr/bin/env python3
"""Isolated test-only observer repair qualification; never reads/runs full reactor."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRATCH = HERE / "owned-scratch"
SOURCE = SCRATCH / "vm"
TARGET = SCRATCH / "target"
TEST = "src/experimental_swift_reactor/frame_operations_tests.rs"
FRAME = "src/experimental_swift_reactor/frame_operations.rs"
BASE_CLOSURE = "6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8"
GUARD = "        if hooks.release_mask == 0 {\n            return false;\n        }\n"
ANCHOR = "pub(super) fn before_release(cache: &mut SwiftFunctionCache, function: u32) {\n    let reject = HOOKS.with(|slot| {\n        let mut hooks = slot.get();\n"
PROBE = "\n// Qualification-only ordinary caller; test module must be absent.\n#[allow(dead_code)]\nfn release_observer_cfg_negative() { let _ = tests::Hooks::default(); }\n"
RECEIPTS = []
BASELINE = {}
TOOLS = {}


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def manifest(directory):
    paths = [directory / "Cargo.toml", directory / "Cargo.lock"]
    paths.extend(p for top in ("src", "include", "tests") for p in (directory / top).rglob("*") if p.is_file())
    return {str(p.relative_to(directory)): sha(p) for p in sorted(paths)}


def digest(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, indent=2) + "\n").encode()).hexdigest()


def env():
    value = {k: os.environ[k] for k in ("HOME", "USER", "LOGNAME") if k in os.environ}
    value.update(PATH="/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true",
        CARGO_TARGET_DIR=str(TARGET), TMPDIR=str(SCRATCH / "tmp"))
    return value


def tools():
    result = {"python": {"path": sys.executable, "sha256": sha(sys.executable), "version": sys.version}}
    for name, flags in (("rustc", ["-vV"]), ("cargo", ["-V"])):
        proxy = Path(shutil.which(name, path=env()["PATH"]))
        actual = Path(subprocess.check_output(["rustup", "which", name], env=env(), text=True).strip())
        result[name] = {"proxy": str(proxy), "proxySHA256": sha(proxy), "actual": str(actual), "sha256": sha(actual),
                        "version": subprocess.check_output([str(actual), *flags], env=env(), text=True).strip()}
    sysroot = Path(subprocess.check_output(["rustc", "--print", "sysroot"], env=env(), text=True).strip())
    result["sysroot"] = {"path": str(sysroot), "files": {str(p.relative_to(sysroot)): sha(p)
        for top in ("bin", "lib") for p in sorted((sysroot / top).rglob("*")) if p.is_file()}}
    return result


def command(name, argv, expected=0):
    directory = HERE / "commands" / name
    directory.mkdir(parents=True, exist_ok=False)
    assert manifest(ROOT / "vm") == BASELINE
    before = manifest(SOURCE)
    save(directory / "source-manifest.json", before)
    for path in (TEST, FRAME):
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / path, target)
    shutil.copyfile(HERE / "run.py", directory / "run.py")
    assert tools() == TOOLS
    remaining = 900 - sum(row["durationSeconds"] for row in RECEIPTS)
    assert remaining > 0
    limit = min(180, remaining)
    receipt = {"argv": argv, "cwd": str(SOURCE), "environment": env(), "timeoutSeconds": limit,
        "UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceClosure": digest(before),
        "tools": TOOLS, "expectedExitCode": expected, "timedOut": False, "signals": [], "groupEmpty": False}
    start = time.monotonic()
    with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
        child = subprocess.Popen(argv, cwd=SOURCE, env=env(), stdout=stdout, stderr=stderr, start_new_session=True)
        receipt.update(pid=child.pid, processGroup=child.pid)
        try:
            child.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            receipt["timedOut"] = True
        def alive():
            try:
                os.killpg(child.pid, 0)
                return True
            except ProcessLookupError:
                return False
        receipt["descendantsAfterDirectChild"] = child.returncode is not None and alive()
        if alive():
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                    receipt["signals"].append(sig.name)
                except ProcessLookupError:
                    break
                end = time.monotonic() + 5
                while alive() and time.monotonic() < end:
                    child.poll()
                    time.sleep(0.05)
                if not alive():
                    break
        child.poll()
        receipt.update(exitCode=child.returncode, groupEmpty=not alive(), durationSeconds=time.monotonic() - start)
    receipt.update(stdoutSHA256=sha(directory / "stdout"), stderrSHA256=sha(directory / "stderr"),
        sourcesUnchanged=manifest(SOURCE) == before and manifest(ROOT / "vm") == BASELINE,
        toolsUnchanged=tools() == TOOLS, recorderSHA256=sha(directory / "run.py"))
    receipt["passedExpectedOutcome"] = receipt["exitCode"] == expected and not receipt["timedOut"] and receipt["groupEmpty"] and receipt["sourcesUnchanged"] and receipt["toolsUnchanged"]
    save(directory / "receipt.json", receipt)
    RECEIPTS.append(receipt)
    print(json.dumps({"command": name, "exitCode": receipt["exitCode"], "expected": expected,
                      "seconds": receipt["durationSeconds"]}), flush=True)
    assert receipt["passedExpectedOutcome"], name
    return directory


def archive(binary, name):
    destination = HERE / "binaries" / (name + ".gz")
    destination.parent.mkdir(exist_ok=True)
    with open(binary, "rb") as source, gzip.GzipFile(filename=str(destination), mode="wb", mtime=0) as out:
        shutil.copyfileobj(source, out)
    with gzip.open(destination, "rb") as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == sha(binary)
    info = {"path": str(binary), "bytes": Path(binary).stat().st_size, "sha256": sha(binary),
            "retained": str(destination.relative_to(HERE)), "gzipBytes": destination.stat().st_size, "gzipSHA256": sha(destination)}
    save("binaries/" + name + ".json", info)
    return info


def build(name, feature, release):
    flags = ["--all-features"] if feature == "all" else ["--features", "experimental-swift-reactor"]
    flags += ["--release"] if release else []
    args = ["cargo", "test", "--lib", "--no-run", "--locked", "--offline", "--no-default-features", *flags, "--message-format=json"]
    directory = command(name + "-build", args)
    rows = [json.loads(line) for line in (directory / "stdout").read_text().splitlines() if line.startswith("{")]
    binaries = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact" and row.get("executable") and row.get("profile", {}).get("test")]
    assert len(binaries) == 1
    archive(binaries[0], name)
    return binaries[0], flags


def cleanup():
    info = SCRATCH.stat()
    result = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (HERE / "holders.stdout").write_bytes(result.stdout)
    (HERE / "holders.stderr").write_bytes(result.stderr)
    assert result.returncode == 1 and not result.stdout and not result.stderr
    assert not SCRATCH.is_symlink() and (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino) == (info.st_dev, info.st_ino)
    size = sum(p.stat().st_size for p in SCRATCH.rglob("*") if p.is_file())
    shutil.rmtree(SCRATCH)
    save("cleanup.json", {"holderExitCode": result.returncode, "removed": not SCRATCH.exists(), "logicalBytesRemoved": size,
                           "path": str(SCRATCH), "otherProcessesOrNativeInstancesChanged": False})


def main():
    global BASELINE, TOOLS
    assert not SCRATCH.exists() and not (HERE / "receipt.json").exists()
    BASELINE = json.loads((ROOT / "verification/swift-lifecycle-linux-fixture-repair/candidate-manifest.json").read_bytes())
    assert len(BASELINE) == 132 and digest(BASELINE) == BASE_CLOSURE and manifest(ROOT / "vm") == BASELINE
    SCRATCH.mkdir(mode=0o700)
    (SCRATCH / "tmp").mkdir(mode=0o700)
    for name, expected in BASELINE.items():
        for folder in (SOURCE, HERE / "baseline"):
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "vm" / name, path)
            assert sha(path) == expected
    save("baseline-manifest.json", BASELINE)
    TOOLS = tools()
    save("tools.json", TOOLS)
    regression = (HERE / "regressions.rs").read_bytes()
    original = (SOURCE / TEST).read_bytes()
    assert original.decode().count(ANCHOR) == 1
    (SOURCE / TEST).write_bytes(original + regression)
    save("regression-baseline-manifest.json", manifest(SOURCE))
    outcome = {"schema": 1, "baselineClosure": BASE_CLOSURE, "baselineFiles": 132,
        "system": platform.platform(), "machine": platform.machine(), "fullReactorReadOrRun": False,
        "liveVMChanged": False, "productionBytesChanged": False, "budgetChanges": False,
        "GAaccepted": False, "passed": False}
    failure = None
    try:
        binary, _ = build("baseline-regression", "swift", False)
        output = command("baseline-reproduces-panic", [binary, "swift_release_observer_default_allows_130_actual_serial_releases", "--nocapture", "--test-threads=1"], 101)
        assert "assertion failed: ordinal < 64" in (output / "stderr").read_text()
        assert "OBSERVER default actual_completed_releases=64" in (output / "stdout").read_text()
        outcome["baselinePanicReproduced"] = True
        candidate = original.decode().replace(ANCHOR, ANCHOR + GUARD).encode() + regression
        (SOURCE / TEST).write_bytes(candidate)
        candidate_manifest = manifest(SOURCE)
        assert [k for k in BASELINE if BASELINE[k] != candidate_manifest[k]] == [TEST]
        save("candidate-manifest.json", candidate_manifest)
        (HERE / "candidate").mkdir()
        destination = HERE / "candidate" / TEST
        destination.parent.mkdir(parents=True)
        destination.write_bytes(candidate)
        outcome["candidateClosure"] = digest(candidate_manifest)
        outcome["normalConfigurations"] = []
        for feature, release in (("swift", False), ("swift", True), ("all", False), ("all", True)):
            name = feature + ("-release" if release else "-debug")
            binary, flags = build(name, feature, release)
            listing = command(name + "-list", [binary, "--list"])
            names = sorted(line.removesuffix(": test") for line in (listing / "stdout").read_text().splitlines() if line.endswith(": test"))
            assert len([n for n in names if "swift_release_observer_" in n]) == 3
            save(name + "-test-identities.json", names)
            replay = command(name + "-library", [binary, "--nocapture", "--test-threads=1"])
            text = (replay / "stdout").read_text()
            passed = sorted(re.findall(r"^test (\S+) \.\.\. (?:.*?\n)*?ok$", text, re.M))
            # nocapture can put observer lines between identity and final ok.
            summary = re.search(r"test result: ok\. (\d+) passed; 0 failed; 0 ignored;", text)
            assert summary and int(summary.group(1)) == len(names)
            outcome["normalConfigurations"].append({"name": name, "identities": len(names), "passed": int(summary.group(1)), "ignored": 0})
            command(name + "-production-check", ["cargo", "check", "--lib", "--locked", "--offline", "--no-default-features", *flags])
        frame = (SOURCE / FRAME).read_bytes()
        (SOURCE / FRAME).write_bytes(frame + PROBE.encode())
        outcome["productionCfgNegativeChecks"] = 0
        for feature, release in (("swift", False), ("swift", True), ("all", False), ("all", True)):
            name = feature + ("-release" if release else "-debug")
            flags = ["--all-features"] if feature == "all" else ["--features", "experimental-swift-reactor"]
            flags += ["--release"] if release else []
            negative = command(name + "-cfg-negative", ["cargo", "check", "--lib", "--locked", "--offline", "--no-default-features", *flags], 101)
            text = (negative / "stderr").read_text()
            assert "error[E0433]" in text and "tests" in text and "release_observer_cfg_negative" in text
            outcome["productionCfgNegativeChecks"] += 1
        (SOURCE / FRAME).write_bytes(frame)
        assert manifest(SOURCE) == candidate_manifest
        outcome["normalIdentityExecutions"] = sum(row["passed"] for row in outcome["normalConfigurations"])
        outcome["passed"] = True
    except BaseException as error:
        failure = error
        outcome["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        # Preserve exact unexpected source states and every failed command before cleanup.
        save("final-source-manifest.json", manifest(SOURCE))
        outcome.update(commandCount=len(RECEIPTS), aggregateCommandSeconds=sum(row["durationSeconds"] for row in RECEIPTS),
                       liveVMUnchanged=manifest(ROOT / "vm") == BASELINE, toolsUnchanged=tools() == TOOLS)
        cleanup()
        outcome["cleanup"] = json.loads((HERE / "cleanup.json").read_bytes())
        save("receipt.json", outcome)
    print(json.dumps(outcome), flush=True)


if __name__ == "__main__":
    main()
