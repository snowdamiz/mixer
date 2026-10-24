#!/usr/bin/env python3
"""One-shot exact selected integration and bounded live host verification."""
from pathlib import Path
import datetime
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / "verification/swift-reactor-lifecycle-runtime-v3"
ACCEPTANCE = ROOT / "verification/swift-reactor-lifecycle-runtime-v3-root-review/runtime-acceptance.json"
ACCEPTANCE_SHA = "4ab6960d7e0bf99d94db569bc8d29a7a62bab53a9f3bd8d9fcef6c8799222c2e"
CLOSURE = "93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38"
FINAL_SEAL_SHA = "027d3895f69f3f6c92638c44e7304fa2f65e34075f564e388c8751e3ea133d27"
EXPLICIT_PATH = "/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def enc(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def save(name, value):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else enc(value))


def read(path):
    return json.loads(Path(path).read_bytes())


def manifest(tree):
    # The complete accepted scope: both Cargo files and every include/src/tests
    # file. VM tools and transient targets were never in the candidate scope.
    return {
        str(path.relative_to(tree)): digest(path)
        for name in ["Cargo.lock", "Cargo.toml", "include", "src", "tests"]
        for path in ([tree / name] if (tree / name).is_file() else sorted((tree / name).rglob("*")))
        if path.is_file()
    }


def source_check():
    current = manifest(ROOT / "vm")
    assert current == read(PRIOR / "candidate-manifest.json"), "live VM source differs from accepted candidate"
    assert sha(enc(current)) == CLOSURE
    return current


def group_members(group):
    raw = subprocess.check_output(["/bin/ps", "-axo", "pid=,pgid=,command="], text=True)
    return [line for line in raw.splitlines() if len(line.split(None, 2)) >= 2 and line.split(None, 2)[1] == str(group)]


def tool_check(env):
    expected = read(PRIOR / "runtime-attempts/focused-swift-debug/build-tools.json")["compiler"]
    for name in ["rustc", "cargo", "rustfmt"]:
        pin = expected[name]
        assert shutil.which(name, path=env["PATH"]) == pin["executable"]
        assert digest(pin["executable"]) == pin["executableSHA256"]
    actual = expected["actualCompiler"]
    sysroot = Path(actual["sysroot"])
    files = {str(p.relative_to(sysroot)): digest(p) for name in ["bin", "lib"] for p in sorted((sysroot / name).rglob("*")) if p.is_file()}
    assert files == actual["sysrootCompilerFiles"], "qualified compiler/sysroot drift"
    assert digest(actual["path"]) == actual["sha256"]
    probes = {}
    for name, args in [("rustc", ["-vV"]), ("cargo", ["-V"]), ("cargo", ["clippy", "-V"]), ("rustfmt", ["--version"])]:
        completed = subprocess.run([name, *args], env=env, capture_output=True, cwd=ROOT)
        assert completed.returncode == 0
        probes[" ".join([name, *args])] = {"argv": [name, *args], "exitCode": completed.returncode, "stdout": completed.stdout.decode(), "stderr": completed.stderr.decode()}
    assert probes["rustc -vV"]["stdout"] == expected["rustc"]["stdout"]
    assert probes["cargo -V"]["stdout"] == expected["cargo"]["stdout"]
    assert not {key: value for key, value in env.items() if value and ("DYLD_" in key or key in ["LD_PRELOAD", "LD_LIBRARY_PATH", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER"])}
    return {"compiler": expected, "probes": probes, "qualifiedSysrootFiles": len(files), "explicitPATH": env["PATH"], "python": {"path": sys.executable, "sha256": digest(sys.executable), "version": sys.version}, "system": {"uname": list(os.uname()), "platform": sys.platform}}


def command(name, argv, env, executable=None):
    before = source_check()
    save(name + "-tools.json", tool_check(env))
    row = {"argv": argv, "cwd": str(ROOT), "environment": env, "sourceClosure": CLOSURE, "sourceRevisionContext": read(ACCEPTANCE)["sourceRevisionContext"], "sourceBeforeSHA256": sha(enc(before)), "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "timeoutSeconds": 900, "launched": False}
    if executable is not None:
        assert Path(argv[0]) == executable
        row.update(executableSHA256=digest(executable), executableBytes=executable.stat().st_size)
    save(name + ".json", row)
    child = None
    out = err = b""
    start = time.monotonic()
    try:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        row.update(launched=True, processGroup=child.pid)
        save(name + ".json", row)
        try:
            out, err = child.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            row["timedOut"] = True
            assert child.poll() is None and os.getpgid(child.pid) == child.pid
            os.killpg(child.pid, signal.SIGKILL)
            out, err = child.communicate()
        row["exitCode"] = child.returncode
    except BaseException:
        row["collectionFailure"] = traceback.format_exc()
        raise
    finally:
        if child is not None and child.poll() is None:
            assert os.getpgid(child.pid) == child.pid
            os.killpg(child.pid, signal.SIGKILL)
            moreout, moreerr = child.communicate()
            out += moreout
            err += moreerr
        save(name + "-stdout.gz", gzip.compress(out, mtime=0))
        save(name + "-stderr.gz", gzip.compress(err, mtime=0))
        row.update(stdoutSHA256=sha(out), stderrSHA256=sha(err), durationSeconds=time.monotonic() - start, finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), sourceUnchanged=before == manifest(ROOT / "vm"), remainingGroup=group_members(child.pid) if child is not None else [])
        save(name + ".json", row)
    save(name + "-post-tools.json", tool_check(env))
    assert row["sourceUnchanged"] and not row["remainingGroup"]
    return row, out, err


def cleanup(scratch):
    scan = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(scratch)], capture_output=True)
    save("cleanup-holders.stdout", scan.stdout)
    save("cleanup-holders.stderr", scan.stderr)
    row = {"scratch": str(scratch), "lsofExitCode": scan.returncode, "holderCheckEmpty": scan.returncode == 1 and not scan.stdout and not scan.stderr, "removed": False, "nativeInstancesCreated": 0, "otherProjectProcessesChanged": False}
    save("cleanup.json", row)
    assert row["holderCheckEmpty"], "holder or scan error; preserve owned scratch"
    files = [path for path in scratch.rglob("*") if path.is_file()]
    row.update(filesRemoved=len(files), logicalBytesRemoved=sum(path.stat().st_size for path in files))
    shutil.rmtree(scratch)
    row["removed"] = not scratch.exists()
    save("cleanup.json", row)


def main():
    assert not (HERE / "integration.json").exists(), "one-shot integration already recorded"
    assert digest(ACCEPTANCE) == ACCEPTANCE_SHA
    acceptance = read(ACCEPTANCE)
    assert acceptance["candidateClosure"] == CLOSURE and acceptance["liveIntegrationSelected"] and acceptance["selectedRuntimeSubsetAccepted"]
    assert digest(PRIOR / "runtime-final-seal.json") == FINAL_SEAL_SHA
    final_seal = read(PRIOR / "runtime-final-seal.json")
    assert len(final_seal["files"]) == 978
    for name, expected in final_seal["files"].items():
        assert digest(PRIOR / name) == expected, name
    assert sha(enc(final_seal["files"])) == final_seal["closureSHA256"]
    candidate = manifest(PRIOR / "candidate")
    assert candidate == read(PRIOR / "candidate-manifest.json") and len(candidate) == 132
    assert sha(enc(candidate)) == CLOSURE
    before = manifest(ROOT / "vm")
    expected_before = dict(candidate)
    selected = acceptance["exactSelectedChanges"]
    assert [row["path"] for row in selected] == ["vm/src/experimental_swift_reactor/lifecycle.rs", "vm/src/experimental_swift_reactor/lifecycle_tests.rs", "vm/src/experimental_swift_reactor/memory_growth_operations.rs"]
    for row in selected:
        target = ROOT / row["path"]
        assert (digest(target) if target.exists() else None) == row["beforeSHA256"], row["path"]
        assert digest(ROOT / row["source"]) == row["afterSHA256"], row["source"]
        name = row["path"].removeprefix("vm/")
        if row["beforeSHA256"] is None:
            del expected_before[name]
        else:
            expected_before[name] = row["beforeSHA256"]
    assert before == expected_before, "unselected live VM source drift before integration"
    save("root-runtime-acceptance.json", ACCEPTANCE.read_bytes())
    save("retained-runtime-final-seal.json", (PRIOR / "runtime-final-seal.json").read_bytes())
    save("candidate-manifest.json", candidate)
    save("live-before-manifest.json", before)
    save("retained-evidence.json", {"candidateClosure": CLOSURE, "rootAcceptanceSHA256": ACCEPTANCE_SHA, "runtimeFinalSealSHA256": FINAL_SEAL_SHA, "verifiedFinalPins": len(final_seal["files"]), "observedTotals": acceptance["observedTotals"], "priorMatrixReexecuted": False, "basis": "Exact 132-file source closure and immutable root-selected runtime evidence", "environmentScope": acceptance["environmentScope"], "fullPlannedSLRowsComplete": False})
    # All preimages and every unselected scope byte have been checked before the
    # only production mutations. Never repair the accepted candidate in place.
    for row in selected:
        (ROOT / row["path"]).write_bytes((ROOT / row["source"]).read_bytes())
    after = source_check()
    save("live-after-manifest.json", after)
    save("integration.json", {"schema": "mixer.swift-lifecycle.live-v3-integration.1", "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "rootAcceptanceSHA256": ACCEPTANCE_SHA, "candidateClosure": CLOSURE, "scopeFiles": len(after), "exactSelectedChanges": selected, "allUnselectedScopeBytesUnchanged": True, "liveScopeEqualsCandidate": True, "sourceRevisionContext": acceptance["sourceRevisionContext"], "actualRevisionAtIntegration": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "gitMutated": False, "publicAPIChanged": False, "privateExperimentalOnly": True})
    scratch = Path(tempfile.mkdtemp(prefix="mixer-swift-lifecycle-v3-live-"))
    env = {key: os.environ[key] for key in ["HOME", "TMPDIR", "LANG", "LC_ALL"] if key in os.environ}
    env.update(PATH=EXPLICIT_PATH, RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_TARGET_DIR=str(scratch / "target"), CARGO_INCREMENTAL="0")
    save("owned-scratch.json", {"path": str(scratch), "fresh": True, "environment": env})
    result = {"schema": "mixer.swift-lifecycle.live-v3-host-result.1", "candidateClosure": CLOSURE, "environmentScope": "macOS arm64 host synthetic Rust unit tests and Swift-only Clippy; no native or physical-device run", "focusedTestsPassed": False, "clippyPassed": False, "fullPlannedSLRowsComplete": False}
    try:
        built, out, _ = command("focused-build", ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib", "--features", "experimental-swift-reactor", "--no-run", "--message-format=json-render-diagnostics"], env)
        assert built["exitCode"] == 0, "live focused build failed; preserve accepted candidate"
        artifacts = [json.loads(line) for line in out.decode().splitlines() if line.startswith("{")]
        artifacts = [row for row in artifacts if row.get("reason") == "compiler-artifact" and row.get("executable") and row["target"]["name"] == "mixer_vm" and row["profile"]["test"]]
        assert len(artifacts) == 1 and not artifacts[0]["fresh"]
        save("cargo-artifact.json", artifacts[0])
        executable = Path(artifacts[0]["executable"])
        assert executable.is_relative_to(scratch / "target")
        raw = executable.read_bytes()
        save("focused-executable.gz", gzip.compress(raw, mtime=0))
        save("focused-artifact.json", {"path": "focused-executable.gz", "bytes": len(raw), "sha256": sha(raw), "originalPath": str(executable)})
        listed, out, _ = command("focused-list", [str(executable), "swift_lifecycle_", "--list"], env, executable)
        assert listed["exitCode"] == 0
        names = [line[:-6] for line in out.decode().splitlines() if line.endswith(": test")]
        assert names == read(PRIOR / "runtime-attempts/focused-swift-debug/exact-tests.json") and len(names) == 23
        save("exact-tests.json", names)
        executed, out, _ = command("focused-execute", [str(executable), "swift_lifecycle_", "--nocapture", "--test-threads=1"], env, executable)
        text = out.decode(errors="replace")
        observed = re.findall(r"^test (\S+) \.\.\. (ok|FAILED|ignored)$", text, re.M)
        save("observed-identities.json", [{"test": name, "status": status, "fullPlannedSLRowComplete": False} for name, status in observed])
        result.update(focusedExitCode=executed["exitCode"], focusedTests=len(names), focusedTestsPassed=executed["exitCode"] == 0 and observed == [(name, "ok") for name in names] and "23 passed; 0 failed; 0 ignored;" in text)
        save("host-result.json", result)
        assert result["focusedTestsPassed"], "live focused tests failed; preserve accepted candidate"
        clippy, _, _ = command("swift-clippy", ["cargo", "clippy", "--locked", "--manifest-path", "vm/Cargo.toml", "--lib", "--features", "experimental-swift-reactor", "--", "-D", "warnings"], env)
        result.update(clippyExitCode=clippy["exitCode"], clippyPassed=clippy["exitCode"] == 0, clippyWorkflowPath=".github/workflows/verify.yml", clippyWorkflowSHA256=digest(ROOT / ".github/workflows/verify.yml"))
        save("host-result.json", result)
        assert result["clippyPassed"], "required Swift-only Clippy failed; preserve accepted candidate"
    except BaseException:
        result["failure"] = traceback.format_exc()
        raise
    finally:
        save("host-result.json", result)
        cleanup(scratch)
        save("live-final-manifest.json", source_check())
    print(enc(result).decode())


if __name__ == "__main__":
    main()
