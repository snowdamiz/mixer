#!/usr/bin/env python3
"""One bounded isolated retention-candidate exact Swift diagnostic; fresh root selection required."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import signal
import subprocess
import sys
import time
from packetlib import (candidate_payloads, verify_candidate, verify_prepared_seal, accepted_review,
                       CANDIDATE_CLOSURE, LIVE_BASELINE_CLOSURE, CANDIDATE_SEAL)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRATCH = HERE / "owned-scratch"
SOURCE = SCRATCH / "vm"
TARGET = SCRATCH / "target"
QUALIFIED = ROOT / "compiler/experiments/fieldlog-reactor"
CLOSURE = CANDIDATE_CLOSURE
HARNESS_HASH = "d72da7bc7aaf4e31b7093fde497f357226d3a4dd954eb577909209102a0bfb00"
REACTOR = QUALIFIED / "local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm"
REACTOR_HASH = "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
EXPECTED = {"codableRoundTrip": True, "committedEntries": 1, "completionBasisPoints": 5000,
    "emptyTitleRejected": True, "pendingChanges": 1503, "reordered": True,
    "repeatedCommitRejected": True, "reportIncludesEntry": True, "status": "passed",
    "taskCount": 1000, "unicodePreserved": True}
PREFIX = "experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::exact_diagnostic::"
BINARY = HERE / "bin/exact-tests"
APPEND = '\n// Isolated diagnostic only; isolated candidate production bytes are unchanged.\ninclude!(' + json.dumps(str(HERE / "harness.rs")) + ');\n'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = HERE / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(Path(path).read_bytes())


def identity(path):
    path = Path(path)
    return {"path": str(path), "resolvedPath": str(path.resolve()),
            "bytes": path.stat().st_size, "sha256": sha(path)}


def environment():
    env = {k: os.environ[k] for k in ("HOME", "TMPDIR", "USER", "LOGNAME") if k in os.environ}
    env.update(PATH="/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
               RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_INCREMENTAL="0",
               CARGO_NET_OFFLINE="true", CARGO_BUILD_JOBS="2", CARGO_TARGET_DIR=str(TARGET),
               TMPDIR=str(SCRATCH / "tmp"))
    return env


def tools():
    env = environment()
    result = {"python": identity(sys.executable), "pythonVersion": sys.version,
              "system": platform.platform(), "machine": platform.machine()}
    for name, flags in [("rustc", ["-vV"]), ("cargo", ["-V"]), ("rustup", ["-V"])]:
        proxy = Path(shutil.which(name, path=env["PATH"]))
        actual = Path(subprocess.check_output(["rustup", "which", name], env=env, text=True).strip()) if name != "rustup" else proxy.resolve()
        result[name] = {"proxy": identity(proxy), "actual": identity(actual),
                        "version": subprocess.check_output([str(actual), *flags], env=env, text=True, stderr=subprocess.PIPE).strip()}
    sysroot = Path(subprocess.check_output(["rustc", "--print", "sysroot"], env=env, text=True).strip())
    files = {str(p.relative_to(sysroot)): sha(p) for top in ("bin", "lib")
             for p in sorted((sysroot / top).rglob("*")) if p.is_file()}
    result["sysroot"] = {"path": str(sysroot), "files": files}
    return result


def source_manifest(directory):
    paths = [directory / "Cargo.toml", directory / "Cargo.lock"]
    paths += [p for top in ("include", "src", "tests") for p in (directory / top).rglob("*") if p.is_file()]
    return {str(p.relative_to(directory)): sha(p) for p in sorted(paths)}


def closure(manifest):
    return hashlib.sha256((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()).hexdigest()


def reconstructed_source():
    payloads = candidate_payloads()
    test = "src/experimental_swift_reactor/lifecycle_tests.rs"
    payloads[test] += APPEND.encode()
    return payloads


def assert_baseline():
    # This is the selected isolated candidate closure, never the live VM closure.
    bound = read(HERE / "candidate-manifest.json")
    assert len(bound) == 132 and closure(bound) == CANDIDATE_CLOSURE
    expected = read(HERE / "copied-build-manifest.json")
    reconstructed = {name: hashlib.sha256(data).hexdigest()
                     for name, data in reconstructed_source().items()}
    assert reconstructed == expected
    modified = source_manifest(SOURCE)
    assert modified == expected, "isolated source drift"
    assert [name for name in bound if bound[name] != modified[name]] == [
        "src/experimental_swift_reactor/lifecycle_tests.rs"]
    return modified


def assert_inputs():
    binding = read(HERE / "binding.json")
    for info in binding["inputs"]:
        assert sha(info["path"]) == info["sha256"], info["path"]
        if "snapshot" in info:
            assert sha(HERE / info["snapshot"]) == info["sha256"], info["snapshot"]
    assert sha(REACTOR) == REACTOR_HASH and REACTOR.stat().st_size == 53_777_114


def observe_group(pgid, ps_deadline=None):
    """EPERM is unknown unless a complete exact-PGID ps observation proves state."""
    observation = {"processGroup": pgid, "state": "unknown", "method": "killpg-zero"}
    try:
        os.killpg(pgid, 0)
        observation["state"] = "present"
        return observation
    except ProcessLookupError:
        observation["state"] = "absent"
        return observation
    except OSError as error:
        observation["killpgError"] = {"errno": error.errno, "type": type(error).__name__, "message": str(error)}
    ps_timeout = 2 if ps_deadline is None else min(2, max(0, ps_deadline - time.monotonic()))
    if ps_timeout <= 0:
        observation["psError"] = {"type": "ObservationDeadlineExpired", "message": "fixed cleanup envelope exhausted; group remains unknown"}
        return observation
    try:
        query = subprocess.run(["/bin/ps", "-axo", "pid=,ppid=,pgid=,stat=,comm="],
                               capture_output=True, text=True, timeout=ps_timeout)
        observation.update(method="killpg-zero+exact-pgid-ps", psExitCode=query.returncode,
                           psStderr=query.stderr)
        rows = []
        valid = query.returncode == 0 and not query.stderr
        for line in query.stdout.splitlines():
            if not line.strip():
                continue
            fields = line.split(None, 4)
            if len(fields) != 5 or not all(value.isdecimal() for value in fields[:3]):
                valid = False
                continue
            if int(fields[2]) == pgid:
                rows.append(line)
        observation.update(exactGroupRows=rows, psCompleteParse=valid)
        if valid:
            observation["state"] = "present" if rows else "absent"
    except (OSError, subprocess.TimeoutExpired) as error:
        observation["psError"] = {"type": type(error).__name__, "message": str(error)}
    return observation


def record_command(name, argv, timeout, env=None, cwd=None):
    directory = HERE / "commands" / name
    assert not directory.exists(), name
    directory.mkdir(parents=True)
    bound = assert_baseline()
    assert_inputs()
    snapshot = directory / "harness.rs"
    shutil.copyfile(HERE / "harness.rs", snapshot)
    shutil.copyfile(HERE / "diagnostic.py", directory / "diagnostic.py")
    save(directory / "source-manifest.json", bound)
    before_tools = tools()
    binding = read(HERE / "binding.json")
    assert before_tools == binding["compilerTools"], "tool drift"
    env = environment() if env is None else env
    argv_files = [identity(arg) for arg in argv if Path(arg).is_absolute() and Path(arg).is_file()]
    receipt = {"argv": argv, "argvFileIdentities": argv_files, "cwd": str(cwd or SOURCE), "environment": env,
        "timeoutSeconds": timeout, "terminationGraceSeconds": 5, "killWaitSeconds": 5,
        "UTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "sourceClosure": closure(bound),
        "baselineClosure": CLOSURE, "harnessSHA256": sha(snapshot),
        "driverSHA256": sha(directory / "diagnostic.py"), "toolsBefore": before_tools,
        "started": False, "timedOut": False, "signalSent": [], "commandFailurePreserved": True}
    started = time.monotonic()
    stdout = directory / "stdout"
    stderr = directory / "stderr"
    before_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    with stdout.open("wb") as out, stderr.open("wb") as err:
        child = subprocess.Popen(argv, cwd=cwd or SOURCE, env=env, stdout=out, stderr=err, start_new_session=True)
        receipt.update(pid=child.pid, processGroup=child.pid, started=True)
        save(directory / "started.json", receipt)
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            receipt["timedOut"] = True
        cleanup_started = time.monotonic()
        cleanup_deadlines = [cleanup_started + 5, cleanup_started + 10]
        observation = observe_group(child.pid, cleanup_deadlines[0])
        receipt["cleanupEnvelopeSeconds"] = 10
        receipt["groupBeforeCleanup"] = observation
        receipt["ownedGroupSurvivedDirectChild"] = child.returncode is not None and observation["state"] == "present"
        # Capture first failure and partial raw streams before any host cleanup signal.
        if receipt["timedOut"] or child.returncode != 0 or observation["state"] != "absent":
            save(directory / "before-process-cleanup.json", {
                "exitCode": child.returncode, "timedOut": receipt["timedOut"],
                "durationSeconds": time.monotonic() - started, "group": observation,
                "stdout": identity(stdout), "stderr": identity(stderr),
                "failureEvidencePrecedesHostCleanup": True})
        receipt["cleanupObservations"] = []
        if observation["state"] != "absent":
            for sig, grace_ends in zip((signal.SIGTERM, signal.SIGKILL), cleanup_deadlines):
                try:
                    os.killpg(child.pid, sig)
                    receipt["signalSent"].append(sig.name)
                except ProcessLookupError:
                    receipt["cleanupObservations"].append(observe_group(child.pid, grace_ends))
                    break
                except OSError as error:
                    receipt["cleanupObservations"].append({"signal": sig.name, "error": str(error), "errno": error.errno})
                while time.monotonic() < grace_ends:
                    child.poll()
                    observation = observe_group(child.pid, grace_ends)
                    if observation["state"] == "absent":
                        break
                    time.sleep(min(0.05, max(0, grace_ends - time.monotonic())))
                receipt["cleanupObservations"].append(observe_group(child.pid, grace_ends))
                if receipt["cleanupObservations"][-1]["state"] == "absent":
                    break
            child.poll()

    after_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    receipt.update(exitCode=child.returncode, durationSeconds=time.monotonic() - started,
        stdout=identity(stdout), stderr=identity(stderr),
        childUserSeconds=after_usage.ru_utime-before_usage.ru_utime,
        childSystemSeconds=after_usage.ru_stime-before_usage.ru_stime,
        cumulativeChildrenMaxRSS=after_usage.ru_maxrss, maxRSSUnit="bytes on Darwin; cumulative child high water, not per-phase runtime reservations",
        sourceUnchanged=assert_baseline() == bound, toolsUnchanged=tools() == before_tools)
    assert_inputs()
    receipt["argvFilesUnchanged"] = all(identity(info["path"]) == info for info in argv_files)
    receipt["allBoundInputsUnchanged"] = True
    receipt["harnessUnchanged"] = sha(HERE / "harness.rs") == sha(snapshot)
    receipt["driverUnchanged"] = sha(HERE / "diagnostic.py") == sha(directory / "diagnostic.py")
    receipt["finalGroupObservation"] = observe_group(child.pid, cleanup_deadlines[-1])
    receipt["processGroupEmpty"] = receipt["finalGroupObservation"]["state"] == "absent"
    receipt["rawStreamEOFConfirmed"] = receipt["processGroupEmpty"]
    receipt["rawStreamEOFScope"] = "regular output handles closed; complete hash reads reached EOF after owned PGID absence"
    receipt["passed"] = child.returncode == 0 and not receipt["timedOut"] and receipt["sourceUnchanged"] and receipt["toolsUnchanged"] and receipt["processGroupEmpty"] and receipt["harnessUnchanged"] and receipt["driverUnchanged"] and receipt["argvFilesUnchanged"]
    save(directory / "receipt.json", receipt)
    return receipt, stdout, stderr


def build():
    assert (HERE / "binding.json").exists()
    count = len(list((HERE / "commands").glob("build-*"))) + 1
    argv = ["cargo", "test", "--lib", "--no-run", "--release", "--locked", "--offline",
            "--no-default-features", "--features", "experimental-swift-reactor", "--message-format=json"]
    receipt, stdout, _ = record_command(f"build-{count:03}", argv, 180)
    if not receipt["passed"]:
        print(json.dumps({"buildPassed": False, "record": f"commands/build-{count:03}/receipt.json"}))
        return 1
    artifacts = [json.loads(line) for line in stdout.read_text().splitlines() if line.startswith("{")]
    executables = [a["executable"] for a in artifacts if a.get("reason") == "compiler-artifact" and a.get("executable") and a.get("profile", {}).get("test")]
    assert len(executables) == 1
    BINARY.parent.mkdir(exist_ok=True)
    shutil.copyfile(executables[0], BINARY)
    BINARY.chmod(0o700)
    save("binary.json", {"source": identity(executables[0]), "retained": identity(BINARY),
         "buildReceipt": f"commands/build-{count:03}/receipt.json", "harnessSHA256": sha(HERE / "harness.rs"),
         "buildManifest": assert_baseline()})
    listing, output, _ = record_command(f"list-{count:03}", [str(BINARY), "--list"], 30)
    assert listing["passed"]
    tests = [line.removesuffix(": test") for line in output.read_text().splitlines() if line.endswith(": test") and "exact_diagnostic::" in line]
    assert tests == sorted([PREFIX + "exact_reactor_harness_control", PREFIX + "exact_reactor_target_once"]), tests
    save("selected-tests.json", tests)
    print(json.dumps({"buildPassed": True, "binary": identity(BINARY), "targetExecuted": False}))
    return 0


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result, "duplicate JSON key: " + key
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def events(path):
    result = []
    for line in path.read_text().splitlines():
        # libtest may prefix the first line with its test identity.
        at = line.find("MIXER_EXACT ")
        if at >= 0:
            result.append(strict_json(line[at + len("MIXER_EXACT "):]))
    assert result, "no harness events"
    return result


def execute(target=False):
    binary = read(HERE / "binary.json")
    assert identity(BINARY) == binary["retained"] and sha(HERE / "harness.rs") == binary["harnessSHA256"]
    env = environment()
    if target:
        selection = read(HERE / "root-selection.json")
        seal = verify_prepared_seal()
        assert selection["preparedSealSHA256"] == sha(HERE / "prepared-seal.json")
        assert selection["candidateSealSHA256"] == CANDIDATE_SEAL
        assert selection["candidateManifestSHA256"] == CANDIDATE_CLOSURE
        assert selection["liveBaselineClosureSHA256"] == LIVE_BASELINE_CLOSURE
        assert selection["candidateLiveIntegrated"] is False
        assert selection["rootSelectionAuthority"] == "fresh-root-selection-after-accepted-independent-review"
        assert selection["compilerTools"] == tools() == read(HERE / "binding.json")["compilerTools"]
        assert selection["sourceManifestSHA256"] == sha(HERE / "copied-build-manifest.json")
        accepted_review(selection)
        selected_at = datetime.datetime.fromisoformat(selection["selectedUTC"])
        prepared_at = datetime.datetime.fromisoformat(seal["sealedUTC"])
        review_seal = read(selection["reviewSealPath"])
        reviewed_at = datetime.datetime.fromisoformat(review_seal["sealedUTC"])
        assert selected_at.tzinfo is not None and selected_at > max(prepared_at, reviewed_at)
        assert selection["exactCommandSelected"] and selection["baselineClosure"] == CLOSURE
        assert selection["harnessSHA256"] == sha(HERE / "harness.rs")
        assert selection["driverSHA256"] == sha(HERE / "diagnostic.py")
        assert selection["binarySHA256"] == sha(BINARY)
        assert selection["targetBytes"] == REACTOR.stat().st_size == 53_777_114
        assert selection["targetSHA256"] == REACTOR_HASH
        assert selection["inputBindingSHA256"] == sha(HERE / "binding.json")
        assert selection["maxTargetAttempts"] == 1
        assert selection["outerCommand"] == ["python3", "-B", str((HERE / "diagnostic.py").relative_to(ROOT)), "target"]
        for name, digest in selection["boundEvidence"].items():
            assert sha(HERE / name) == digest, name
        assert not (HERE / "target-attempt-started.json").exists(), "one target attempt only"
        assert REACTOR.stat().st_size == 53_777_114 and sha(REACTOR) == REACTOR_HASH
        target_copy = SCRATCH / "fieldlog-reactor.wasm"
        shutil.copyfile(REACTOR, target_copy)
        assert sha(target_copy) == REACTOR_HASH
        env["MIXER_EXACT_REACTOR_INPUT"] = str(target_copy)
        marker = {"targetOriginal": identity(REACTOR), "boundInputCopy": identity(target_copy),
             "baselineClosure": CLOSURE, "binary": identity(BINARY), "rootSelection": identity(HERE / "root-selection.json"),
             "outerDeadlineSeconds": 170, "terminationGraceSeconds": 5, "killWaitSeconds": 5}
        with (HERE / "target-attempt-started.json").open("x") as stream:
            stream.write(json.dumps(marker, indent=2, sort_keys=True) + "\n")
    control_count = len(list((HERE / "commands").glob("control-*"))) + 1
    name = "target-once" if target else f"control-{control_count:03}"
    argv = [str(BINARY), PREFIX + ("exact_reactor_target_once" if target else "exact_reactor_harness_control"),
            "--exact", "--nocapture", "--test-threads=1"]
    if target:
        assert argv == selection["argv"]
    receipt, stdout, _ = record_command(name, argv, 170 if target else 60, env=env)
    observed = events(stdout)
    save(name + "-events.json", observed)
    result = {"schema": 1, "scope": "exact real Swift reactor with isolated retention candidate; no live integration or attribution" if target else "small independent synthetic harness wiring only",
        "commandPassed": receipt["passed"], "targetAttempted": target,
        "diagnosticCompleted": any(e["event"] == "diagnostic_execution_complete" and e["payload"] is True for e in observed),
        "ownedCleanupEmpty": any(e["event"] == "cleanup_empty" and e["payload"] is True for e in observed),
        "firstFailure": next((e for e in observed if e["event"] in ("validation_failure", "adoption_failure", "construction_failure", "runtime_failure", "guest_output_failure", "phase_failed")), None),
        "phasesBegun": [e["payload"] for e in observed if e["event"] == "phase_begin"],
        "nativeParity": False, "fullSLMatrixAccepted": False, "productionAccountingAccepted": False,
        "nativeSignedPublicAccepted": False, "performanceSizeMemoryAccepted": False, "GAaccepted": False}
    if target and result["diagnosticCompleted"]:
        calls = [e["payload"] for e in observed if e["event"] in ("corpus_1", "corpus_2")]
        assert len(calls) == 2
        previous = ""
        outputs = []
        for call in calls:
            text = call["stdout"]
            assert text.startswith(previous)
            suffix = text[len(previous):]
            value = strict_json(suffix)
            assert set(value) == set(EXPECTED) and len(value) == 11
            assert all(type(value[k]) is type(EXPECTED[k]) and value[k] == EXPECTED[k] for k in EXPECTED)
            outputs.append({"rawSuffix": suffix, "observation": value})
            previous = text
        result["nativeParity"] = True
        result["completeGuestOutputs"] = outputs
    if target:
        assert sha(REACTOR) == REACTOR_HASH and sha(Path(env["MIXER_EXACT_REACTOR_INPUT"])) == REACTOR_HASH
        result["targetBytesUnchangedAfterAttempt"] = True
    save(name + "-result.json", result)
    print(json.dumps(result))
    return 0 if result["commandPassed"] else 1


def cleanup():
    for path in (HERE / "commands").glob("*/receipt.json"):
        receipt = read(path)
        assert receipt["processGroupEmpty"], "unknown or live owned group: " + str(path)
        assert observe_group(receipt["processGroup"])["state"] == "absent", "owned PGID not proven absent"
    assert SCRATCH.exists() and not SCRATCH.is_symlink()
    info = SCRATCH.stat()
    holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(SCRATCH)], capture_output=True, timeout=30)
    (HERE / "scratch-holders.stdout").write_bytes(holders.stdout)
    (HERE / "scratch-holders.stderr").write_bytes(holders.stderr)
    result = {"path": str(SCRATCH), "holderExitCode": holders.returncode, "removed": False}
    assert holders.returncode == 1 and not holders.stdout and not holders.stderr, "owned scratch still has holders"
    assert (SCRATCH.stat().st_dev, SCRATCH.stat().st_ino) == (info.st_dev, info.st_ino)
    if BINARY.exists():
        binary = identity(BINARY)
        with BINARY.open("rb") as source, gzip.GzipFile(filename=str(BINARY) + ".gz", mode="wb", mtime=0) as dest:
            shutil.copyfileobj(source, dest)
        result["retainedExecutable"] = {"uncompressed": binary, "gzip": identity(str(BINARY) + ".gz")}
        with gzip.open(str(BINARY) + ".gz", "rb") as stream:
            assert hashlib.sha256(stream.read()).hexdigest() == binary["sha256"]
        own = subprocess.run(["/usr/sbin/lsof", "-nP", str(BINARY)], capture_output=True, timeout=30)
        (HERE / "binary-holders.stdout").write_bytes(own.stdout)
        (HERE / "binary-holders.stderr").write_bytes(own.stderr)
        assert own.returncode == 1 and not own.stdout and not own.stderr
        BINARY.unlink()
    result["logicalBytesRemoved"] = sum(p.stat().st_size for p in SCRATCH.rglob("*") if p.is_file())
    shutil.rmtree(SCRATCH)
    result["removed"] = not SCRATCH.exists()
    save("cleanup.json", result)
    print(json.dumps(result))



def host_controls():
    script = HERE / "test_driver.py"
    name = "driver-observation-controls"
    receipt, stdout, stderr = record_command(name, [sys.executable, "-B", str(script)], 30)
    shutil.copyfile(script, HERE / "commands" / name / "test_driver.py")
    assert receipt["passed"]
    print(json.dumps({"hostProcessObservationControlsPassed": True, "targetExecuted": False}))
    return 0


def propose():
    assert not (HERE / "target-attempt-started.json").exists()
    assert not (HERE / "root-selection.json").exists()
    assert_baseline()
    assert_inputs()
    assert sha(HERE / "harness.rs") == HARNESS_HASH
    assert identity(BINARY) == read(HERE / "binary.json")["retained"]
    commands = ["build-001", "list-001", "control-001", "control-002", "driver-observation-controls"]
    for name in commands:
        command = read(HERE / "commands" / name / "receipt.json")
        assert command["passed"] and command["rawStreamEOFConfirmed"] and command["processGroupEmpty"]
    argv = [str(BINARY), PREFIX + "exact_reactor_target_once", "--exact", "--nocapture", "--test-threads=1"]
    outer = ["python3", "-B", str((HERE / "diagnostic.py").relative_to(ROOT)), "target"]
    command = {"schema": 1, "argv": argv, "outerCommand": outer, "cwd": str(ROOT),
        "childCwd": str(SOURCE), "childEnvironment": environment() | {"MIXER_EXACT_REACTOR_INPUT": str(SCRATCH / "fieldlog-reactor.wasm")},
        "outerDeadlineSeconds": 170, "terminationGraceSeconds": 5, "killWaitSeconds": 5,
        "validationDeadlineMs": 120000, "cumulativeRuntimeDeadlineMs": 30000, "cumulativeWasiDeadlineMs": 30000,
        "allOtherBudgetsCountersHooksAndConsumingCleanup": "byte-identical original selected harness; isolated retention candidate", "maxTargetAttempts": 1}
    save("proposed-command.json", command)
    files = ["candidate-manifest.json", "live-baseline-manifest.json", "copied-build-manifest.json", "binding.json", "harness.rs", "diagnostic.py", "test_driver.py", "binary.json", "selected-tests.json", "proposed-command.json", "driver-changes.diff", "control-001-result.json", "control-002-result.json"]
    files += ["commands/" + name + "/receipt.json" for name in commands]
    save("prepared-selection.json", {"schema": 1, "status": "prepared-awaiting-root-exact-selection", "targetAttempted": False,
        "targetBytes": REACTOR.stat().st_size, "targetSHA256": REACTOR_HASH,
        "baselineClosure": CLOSURE, "binaryBytes": BINARY.stat().st_size, "binarySHA256": sha(BINARY),
        "harnessSHA256": sha(HERE / "harness.rs"), "driverSHA256": sha(HERE / "diagnostic.py"),
        "inputBindingSHA256": sha(HERE / "binding.json"), "argv": argv, "outerCommand": outer,
        "commandSHA256": sha(HERE / "proposed-command.json"),
        "boundEvidence": {name: sha(HERE / name) for name in files},
        "candidateManifestSHA256": CANDIDATE_CLOSURE, "liveBaselineClosureSHA256": LIVE_BASELINE_CLOSURE,
        "candidateLiveIntegrated": False, "candidateSealSHA256": CANDIDATE_SEAL,
        "scope": "host diagnostic only; no public/signed/native/production accounting/full SL/FieldLog published-package/GA acceptance",
        "rootMustCreateSelectionBeforeTarget": True, "maxTargetAttempts": 1})
    print((HERE / "prepared-selection.json").read_text())
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "control", "host-controls", "propose", "target", "cleanup"))
    action = parser.parse_args().action
    return {"build": build, "control": lambda: execute(False),
            "host-controls": host_controls, "propose": propose, "target": lambda: execute(True), "cleanup": cleanup}[action]() or 0


if __name__ == "__main__":
    sys.exit(main())
