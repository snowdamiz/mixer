#!/usr/bin/env python3
"""Integrate only the reviewed test delta and run one bounded live-tree check."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / "verification/swift-reactor-lifecycle-remaining-matrix"
REVIEW = ROOT / "verification/swift-reactor-lifecycle-remaining-review"
TARGET = HERE / "owned-target"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    assert not TARGET.exists() and not TARGET.is_symlink()
    assert not (HERE / "acceptance.json").exists()
    packets = [(PRODUCER, "90cf6183ffc2d113318cd818631ee98ad436360cdc38acfcda0dcd10fc8e68ce"),
               (REVIEW, "d6122c250cbb17ab425ee365fcbecb51478ea53de83eb7c1c9382a02e6d8c91d")]
    verified = []
    for directory, digest in packets:
        assert sha(directory / "seal.json") == digest
        seal = read(directory / "seal.json")
        for name, expected in seal["files"].items():
            assert sha(directory / name) == expected, name
        for name, expected in seal["externalFiles"].items():
            assert sha(ROOT / name) == expected, name
        verified.append({"path": str(directory.relative_to(ROOT)), "sealSHA256": digest,
                         "files": len(seal["files"]), "externalFiles": len(seal["externalFiles"])})
    independent = read(REVIEW / "receipt.json")
    assert independent["blockingFindings"] == 0 and independent["productionBytesUnchanged"]
    baseline = read(PRODUCER / "baseline-manifest.json")
    candidate = read(PRODUCER / "candidate-manifest.json")
    changed = sorted(name for name in candidate if candidate[name] != baseline[name])
    assert changed == ["src/experimental_swift_reactor/cache_tests.rs",
                       "src/experimental_swift_reactor/lifecycle_tests.rs",
                       "src/experimental_swift_reactor/memory_growth_operations_tests.rs"]
    assert all(sha(ROOT / "vm" / name) == expected for name, expected in baseline.items())
    assert all(sha(PRODUCER / "candidate" / name) == expected for name, expected in candidate.items())
    acceptance = {"schema": 1, "accountableReviewer": "/root",
                  "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "status": "accepted-exact-test-only-subset", "verifiedPackets": verified,
                  "sourceRevisionContext": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "candidateClosure": independent["candidateClosure"], "changedFiles": changed,
                  "productionBytesChanged": False, "producerExecutions": 196,
                  "independentNormalExecutions": 49, "independentControls": 2,
                  "compilerNegativeChecks": 6, "fullSLRowsComplete": 0,
                  "SL24selected": False, "GAaccepted": False}
    save("acceptance.json", acceptance)
    for name in changed:
        (ROOT / "vm" / name).write_bytes((PRODUCER / "candidate" / name).read_bytes())
    assert all(sha(ROOT / "vm" / name) == expected for name, expected in candidate.items())
    save("integrated-manifest.json", candidate)
    environment = {key: os.environ[key] for key in ("HOME", "TMPDIR", "USER", "LOGNAME") if key in os.environ}
    environment.update(PATH="/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                       RUSTUP_TOOLCHAIN="stable-aarch64-apple-darwin", CARGO_TARGET_DIR=str(TARGET),
                       CARGO_INCREMENTAL="0", CARGO_NET_OFFLINE="true")

    def tools():
        result = {}
        for name, args in [("rustc", ["-vV"]), ("cargo", ["-V"])]:
            actual = subprocess.check_output(["rustup", "which", name], env=environment, text=True).strip()
            result[name] = {"path": actual, "sha256": sha(Path(actual)),
                            "version": subprocess.check_output([actual, *args], env=environment, text=True).strip()}
        return result

    argv = ["cargo", "test", "--lib", "--locked", "--offline", "--no-default-features",
            "--features", "experimental-swift-reactor", "swift_lifecycle_", "--", "--test-threads=1"]
    receipt = {"schema": 1, "argv": argv, "cwd": str(ROOT / "vm"), "environment": environment,
               "tools": tools(), "timeoutSeconds": 180, "passed": False,
               "sourceRevisionContext": acceptance["sourceRevisionContext"],
               "candidateClosure": independent["candidateClosure"], "GAaccepted": False}
    TARGET.mkdir(mode=0o700)
    identity = TARGET.stat()
    started = time.monotonic()
    try:
        child = subprocess.Popen(argv, cwd=ROOT / "vm", env=environment,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        receipt["pid"] = child.pid
        try:
            stdout, stderr = child.communicate(timeout=180)
            receipt["timedOut"] = False
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                stdout, stderr = child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                stdout, stderr = child.communicate(timeout=5)
            receipt["timedOut"] = True
        (HERE / "live.stdout").write_bytes(stdout)
        (HERE / "live.stderr").write_bytes(stderr)
        receipt.update(exitCode=child.returncode, durationSeconds=time.monotonic() - started,
                       stdoutSHA256=hashlib.sha256(stdout).hexdigest(), stderrSHA256=hashlib.sha256(stderr).hexdigest())
        assert child.returncode == 0 and not receipt["timedOut"]
        observed = sorted(re.findall(r"^test (\S+) \.\.\. ok$", stdout.decode(), re.M))
        expected = sorted(read(PRODUCER / "configuration-results.json")[0]["listed"])
        assert observed == expected and len(observed) == 49
        assert "test result: ok. 49 passed; 0 failed; 0 ignored;" in stdout.decode()
        receipt.update(passed=True, selectedTests=observed, ignoredTests=0)
    except BaseException as error:
        receipt["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        receipt["toolsUnchanged"] = tools() == receipt["tools"]
        receipt["sourceUnchanged"] = all(sha(ROOT / "vm" / name) == expected for name, expected in candidate.items())
        holders = subprocess.run(["/usr/sbin/lsof", "-nP", "+D", str(TARGET)], capture_output=True, timeout=30)
        (HERE / "holders.stdout").write_bytes(holders.stdout)
        (HERE / "holders.stderr").write_bytes(holders.stderr)
        current = TARGET.stat()
        cleanup = {"path": str(TARGET), "holderExitCode": holders.returncode, "removed": False}
        if holders.returncode == 1 and not holders.stdout and not holders.stderr and not TARGET.is_symlink() and (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
            cleanup["logicalBytes"] = sum(p.stat().st_size for p in TARGET.rglob("*") if p.is_file())
            shutil.rmtree(TARGET)
            cleanup["removed"] = not TARGET.exists()
        receipt["cleanup"] = cleanup
        receipt["passed"] = receipt["passed"] and receipt["toolsUnchanged"] and receipt["sourceUnchanged"] and cleanup["removed"]
        save("live-receipt.json", receipt)
    assert receipt["passed"]
    print(json.dumps({"passed": True, "tests": 49, "productionBytesChanged": False,
                      "sourceClosure": independent["candidateClosure"], "targetRemoved": True}))


if __name__ == "__main__":
    main()
