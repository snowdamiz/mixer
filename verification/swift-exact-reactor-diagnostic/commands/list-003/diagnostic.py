#!/usr/bin/env python3
"""Bounded copied-source real Swift reactor diagnostic. No live VM writes."""
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRATCH = HERE / "owned-scratch"
SOURCE = SCRATCH / "vm"
TARGET = SCRATCH / "target"
BASELINE = HERE / "baseline"
QUALIFIED = ROOT / "compiler/experiments/fieldlog-reactor"
OLD_ACCEPTANCE = ROOT / "verification/swift-reactor-lifecycle-remaining-root-review/acceptance.json"
MANIFEST = ROOT / "verification/swift-lifecycle-linux-fixture-repair/candidate-manifest.json"
CLOSURE = "6d4b1deed091d6c0f0a2ae0c101c98afbd0e27fdc3c2b2992a999e08565a3fe8"
OLD_CLOSURE = "64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de"
REACTOR = QUALIFIED / "local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm"
REACTOR_HASH = "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
EXPECTED = {"codableRoundTrip": True, "committedEntries": 1, "completionBasisPoints": 5000,
    "emptyTitleRejected": True, "pendingChanges": 1503, "reordered": True,
    "repeatedCommitRejected": True, "reportIncludesEntry": True, "status": "passed",
    "taskCount": 1000, "unicodePreserved": True}
PREFIX = "experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::exact_diagnostic::"
BINARY = HERE / "bin/exact-tests"
APPEND = '\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!(' + json.dumps(str(HERE / "harness.rs")) + ');\n'


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
               CARGO_NET_OFFLINE="true", CARGO_TARGET_DIR=str(TARGET),
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


def assert_baseline():
    bound = read(HERE / "baseline-manifest.json")
    assert closure(bound) == CLOSURE
    assert source_manifest(ROOT / "vm") == bound, "live VM drift: freeze before diagnostic"
    assert source_manifest(BASELINE) == bound
    modified = source_manifest(SOURCE)
    changed = [k for k in bound if modified[k] != bound[k]]
    assert changed == ["src/experimental_swift_reactor/lifecycle_tests.rs"], changed
    test = "src/experimental_swift_reactor/lifecycle_tests.rs"
    assert (SOURCE / test).read_bytes() == (BASELINE / test).read_bytes() + APPEND.encode()
    return modified


def assert_inputs():
    binding = read(HERE / "binding.json")
    for info in binding["inputs"]:
        assert sha(info["path"]) == info["sha256"], info["path"]
        if "snapshot" in info:
            assert sha(HERE / info["snapshot"]) == info["sha256"], info["snapshot"]
    assert sha(REACTOR) == REACTOR_HASH and REACTOR.stat().st_size == 53_777_114


def prepare():
    assert not (HERE / "binding.json").exists()
    assert not SCRATCH.exists() and not BASELINE.exists()
    old = read(OLD_ACCEPTANCE)
    assert old["candidateClosure"] == OLD_CLOSURE and old["productionBytesChanged"] is False
    baseline = read(MANIFEST)
    assert len(baseline) == 132 and closure(baseline) == CLOSURE
    current = source_manifest(ROOT / "vm")
    assert current == baseline
    # Preserve the original pre-copy mismatch and root-selected accepted resolution.
    original = read(ROOT / "verification/swift-reactor-lifecycle-remaining-root-review/integrated-manifest.json")
    drift = {k: {"old": original[k], "current": current[k]} for k in original if original[k] != current[k]}
    assert set(drift) == {"src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/lifecycle_tests.rs"}
    save("initial-preflight-drift.json", {"attemptedBaselineClosure": OLD_CLOSURE, "matched": False,
         "sourceCopiedOrBuiltBeforeResolution": False, "differences": drift,
         "resolution": "Root selected committed accepted Linux test-only deadline fixture repair; current closure rebound before copying.",
         "rootSelectedRevisionContext": "50f70a798fea43e1e77b1d95faa1bbda3fc029e0"})
    SCRATCH.mkdir(mode=0o700)
    (SCRATCH / "tmp").mkdir(mode=0o700)
    for name, expected in baseline.items():
        src = ROOT / "vm" / name
        assert sha(src) == expected
        for destination in (BASELINE / name, SOURCE / name):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, destination)
            assert sha(destination) == expected
    test = SOURCE / "src/experimental_swift_reactor/lifecycle_tests.rs"
    with test.open("ab") as stream:
        stream.write(APPEND.encode())
    save("baseline-manifest.json", baseline)
    evidence = QUALIFIED / "evidence/2026-10-23-qualified"
    prior = read(evidence / "receipt.json")
    assert prior["fullSwiftSDK"] is True and prior["embeddedSwift"] is False
    assert prior["expectedObservation"] == EXPECTED and prior["native"]["observation"] == EXPECTED
    assert prior["candidateArtifactsBeforeOracle"]["reactor"]["sha256"] == REACTOR_HASH
    bound = []
    def retain(path, expected=None):
        path = Path(path)
        if expected is not None:
            assert sha(path) == expected, str(path)
        relative = path.relative_to(ROOT)
        destination = HERE / "inputs" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        info = identity(path)
        assert sha(destination) == info["sha256"]
        info["snapshot"] = str(destination.relative_to(HERE))
        bound.append(info)
    references = [ROOT / "AGENTS.md", ROOT / "mixer-product-plan.md", ROOT / "PLAN.md",
        ROOT / "docs/swift-reactor-lifecycle-remaining-checkpoint.md",
        ROOT / "docs/swift-reactor-lifecycle-v3-integration.md",
        ROOT / "docs/swift-guest-execution-next.md", ROOT / "docs/swift-reactor-lifecycle-contract.md",
        ROOT / "docs/swift-lifecycle-linux-fixture-repair.md", ROOT / "docs/swift-lifecycle-linux-fixture-independent-review.md",
        OLD_ACCEPTANCE, ROOT / "verification/swift-reactor-lifecycle-remaining-root-review/integrated-manifest.json",
        ROOT / "verification/swift-reactor-lifecycle-remaining-root-review/live-receipt.json", MANIFEST,
        ROOT / "verification/swift-lifecycle-linux-fixture-repair/receipt.json",
        ROOT / "verification/swift-lifecycle-linux-fixture-independent-review/receipt.json",
        ROOT / "verification/swift-exact-reactor-root-selection/baseline.json",
        ROOT / "verification/swift-exact-reactor-root-selection/bind_baseline.py",
        evidence / "receipt.json", evidence / "native-command-run.stdout", evidence / "descriptors.json",
        evidence / "structure.json"]
    for path in references:
        retain(path)
    for name, expected in prior["sourceManifest"].items():
        retain(QUALIFIED / "local/2026-10-23-qualified/diagnostic-sources" / name, expected)
    for key, info in prior["inputs"].items():
        retain(info["path"], info["sha256"])
    for info in prior["native"].values():
        if isinstance(info, dict) and "path" in info:
            assert sha(info["path"]) == info["sha256"]
            bound.append(identity(info["path"]))
    assert REACTOR.stat().st_size == 53_777_114 and sha(REACTOR) == REACTOR_HASH
    native_output = (evidence / "native-command-run.stdout").read_text()
    assert strict_json(native_output) == EXPECTED
    save("binding.json", {"schema": 1, "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baselineClosure": CLOSURE, "priorAcceptedClosure": OLD_CLOSURE, "inputs": bound,
        "target": identity(REACTOR), "expectedObservation": EXPECTED,
        "selectedPhases": ["complete validation", "adoption", "construct original owner", "Initialize35", "Corpus62", "Corpus62", "consuming cleanup"],
        "targetExecutionSelectedByRoot": False, "productionBytesChanged": False,
        "hostDiagnosticOnly": True, "productionCallerStackOrAccountingCredit": False,
        "historicalNativeAndNodeOnlyDataReferences": True, "nativePhysicalOrEmulatorRun": False,
        "compilerTools": tools()})
    save("copied-build-manifest.json", assert_baseline())
    print(json.dumps({"prepared": True, "files": 132, "closure": CLOSURE, "targetExecuted": False}))


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
    receipt = {"argv": argv, "cwd": str(cwd or SOURCE), "environment": env,
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
        try:
            child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            receipt["timedOut"] = True
        def group_alive():
            try:
                os.killpg(child.pid, 0)
                return True
            except ProcessLookupError:
                return False
        # A compiler may leave an owned descendant after the direct child exits.
        # The same finite TERM/KILL grace retires that group before terminal evidence.
        receipt["ownedGroupSurvivedDirectChild"] = child.returncode is not None and group_alive()
        if group_alive():
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(child.pid, sig)
                    receipt["signalSent"].append(sig.name)
                except ProcessLookupError:
                    break
                grace_ends = time.monotonic() + 5
                while group_alive() and time.monotonic() < grace_ends:
                    child.poll()
                    time.sleep(min(0.05, max(0, grace_ends - time.monotonic())))
                if not group_alive():
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
    receipt["allBoundInputsUnchanged"] = True
    receipt["harnessUnchanged"] = sha(HERE / "harness.rs") == sha(snapshot)
    receipt["driverUnchanged"] = sha(HERE / "diagnostic.py") == sha(directory / "diagnostic.py")
    receipt["processGroupEmpty"] = not group_alive()
    receipt["passed"] = child.returncode == 0 and not receipt["timedOut"] and receipt["sourceUnchanged"] and receipt["toolsUnchanged"] and receipt["processGroupEmpty"] and receipt["harnessUnchanged"] and receipt["driverUnchanged"]
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
        assert selection["exactCommandSelected"] and selection["baselineClosure"] == CLOSURE
        assert selection["harnessSHA256"] == sha(HERE / "harness.rs")
        assert selection["driverSHA256"] == sha(HERE / "diagnostic.py")
        assert selection["binarySHA256"] == sha(BINARY)
        assert not (HERE / "target-attempt-started.json").exists(), "one target attempt only"
        assert REACTOR.stat().st_size == 53_777_114 and sha(REACTOR) == REACTOR_HASH
        target_copy = SCRATCH / "fieldlog-reactor.wasm"
        shutil.copyfile(REACTOR, target_copy)
        assert sha(target_copy) == REACTOR_HASH
        env["MIXER_EXACT_REACTOR_INPUT"] = str(target_copy)
        save("target-attempt-started.json", {"targetOriginal": identity(REACTOR), "boundInputCopy": identity(target_copy),
             "baselineClosure": CLOSURE, "binary": identity(BINARY), "rootSelection": identity(HERE / "root-selection.json"),
             "outerDeadlineSeconds": 170, "terminationGraceSeconds": 5, "killWaitSeconds": 5})
    control_count = len(list((HERE / "commands").glob("control-*"))) + 1
    name = "target-once" if target else f"control-{control_count:03}"
    argv = [str(BINARY), PREFIX + ("exact_reactor_target_once" if target else "exact_reactor_harness_control"),
            "--exact", "--nocapture", "--test-threads=1"]
    if target:
        assert argv == selection["argv"]
    receipt, stdout, _ = record_command(name, argv, 170 if target else 60, env=env)
    observed = events(stdout)
    save(name + "-events.json", observed)
    result = {"schema": 1, "scope": "exact real Swift reactor" if target else "small independent synthetic harness wiring only",
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "build", "control", "target", "cleanup"))
    action = parser.parse_args().action
    return {"prepare": prepare, "build": build, "control": lambda: execute(False),
            "target": lambda: execute(True), "cleanup": cleanup}[action]() or 0


if __name__ == "__main__":
    sys.exit(main())
