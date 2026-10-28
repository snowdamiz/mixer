#!/usr/bin/env python3
"""Audited pure correction verification; no compiler, guest, socket or custody action."""
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(event, args):
    if event.startswith(("subprocess.", "socket.")) or event in {
            "os.system", "os.fork", "os.forkpty", "os.exec", "os.posix_spawn", "os.kill", "os.killpg", "pty.spawn"}:
        raise AssertionError("pure verification forbids process/socket/custody operation: " + event)
    if event == "open":
        path, mode, flags = args
        write = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if write:
            assert not isinstance(path, int) and Path(path).resolve().is_relative_to(HERE), "write outside correction packet"


def verify_readset(readset):
    for name, record in readset["files"].items():
        data = (ROOT / name).read_bytes()
        assert len(data) == record["bytes"] and digest(data) == record["sha256"], "readset changed: " + name


def verify_packet(path, expected):
    data = (path / "seal.json").read_bytes()
    assert digest(data) == expected, "predecessor seal changed"
    seal = json.loads(data)
    assert {str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()} == set(seal["files"]) | {"seal.json"}
    for name, record in seal["files"].items():
        item = (path / name).read_bytes()
        assert len(item) == record["bytes"] and digest(item) == record["sha256"], name
    assert len(seal["files"]) == seal["fileCount"]
    assert sum(r["bytes"] for r in seal["files"].values()) == seal["totalBytes"]
    return {"sealSHA256": expected, "fileCount": seal["fileCount"], "totalBytes": seal["totalBytes"], "byteExact": True}


def outcome(call):
    try:
        call()
    except RuntimeError as error:
        return {"accepted": False, "reason": str(error)}
    return {"accepted": True}


def differential_reproductions(campaign, supplied, scratch):
    original = load("uncorrected_architecture_campaign", HERE.parent / "swift-execution-architecture-comparison/campaign.py")
    fixture = supplied.CampaignTests()
    command = {"pid": 123, "exitCode": 101, "timedOut": False, "cancelled": None, "processGroupEmpty": True}
    failure = {"kind": "Allocation", "code": "swift_run_unexpected_capacity", "resource": "ExactCapacity",
        "attempted": 160000, "limit": 160000, "observed_capacity": 160002}
    log = scratch / "synthetic.stdout"
    fixture.write_failure_log(log, failure)
    parsed = campaign.base.classify(log, command)
    old, corrected = copy.deepcopy(parsed), copy.deepcopy(parsed)
    before = outcome(lambda: original.validate_result(old, command))
    after = outcome(lambda: campaign.validate_result(corrected, command))
    assert before["accepted"] and not after["accepted"] and "unexpected allocation capacity" in after["reason"]
    r1 = {"failure": failure, "original": before, "corrected": after,
        "syntheticLogSHA256": digest(log.read_bytes()), "telemetryStatus": parsed["telemetry"]["status"],
        "originalFinalFailurePreserved": corrected["originalFinalFailurePreserved"],
        "consumingCleanup": corrected["consumingCleanup"], "zeroResources": campaign.zero_resources(corrected),
        "secondArmStopControl": "test_unexpected_capacity_real_execute_stops_run_before_second_attempt",
        "mockedFullAttempts": 1, "mockedClosedCommands": 10, "mockedSecondArmAdmitted": False}
    log.unlink()
    r2 = []
    cases = (("absolute-prefix", [fixture.prefix(25_000_000) | {"instruction_fuel": 0}], None),
        ("interval-prefix", [fixture.prefix(25_000_000) | {"instruction_fuel": 100_000_000},
                             fixture.prefix(50_000_000) | {"instruction_fuel": 100_000_000}], None),
        ("final-interval", [fixture.prefix(25_000_000) | {"instruction_fuel": 100_000_000}],
                           {"instructions": 30_000_000, "instruction_fuel": 100_000_000}),
        ("empty-prefix-final-absolute", [], {"instructions": 1, "instruction_fuel": 0}))
    for name, rows, final_change in cases:
        path = scratch / "synthetic.stderr"
        path.write_text("".join("MIXER_PREFIX " + json.dumps(row) + "\n" for row in rows))
        result = copy.deepcopy(parsed)
        final = campaign.event(result, "final_cleanup_usage")
        if rows:
            final.update(rows[-1])
        if final_change:
            final.update(final_change)
        before_parser = outcome(lambda: original.prefix_records(path))
        after_parser = outcome(lambda: campaign.prefix_records(path))
        before_join = outcome(lambda: original.validate_prefix(result, {"records": rows}))
        after_join = outcome(lambda: campaign.validate_prefix(result, {"records": rows}))
        assert before_parser["accepted"] and before_join["accepted"] and not after_join["accepted"]
        assert after_parser["accepted"] is (final_change is not None)
        r2.append({"case": name, "records": rows,
            "final": {k: final[k] for k in ("instructions", "instruction_fuel")},
            "originalParser": before_parser, "correctedParser": after_parser,
            "originalFinalJoin": before_join, "correctedFinalJoin": after_join})
        path.unlink()
    return {"scope": "synthetic historical-log and prefix fixtures; no runtime execution", "R1": r1, "R2": r2}


def main():
    readset = json.loads((HERE / "readset.json").read_text())
    verify_readset(readset)
    packets = {str(Path(path).parent): verify_packet((ROOT / path).parent, expected)
        for path, expected in readset["basisSeals"].items()}
    scratch = HERE / "pure-scratch"
    scratch.mkdir()
    prior_tempdir, tempfile.tempdir = tempfile.tempdir, str(scratch)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with contextlib.ExitStack() as guards:
            for name in ("wait4", "waitpid", "wait", "kill", "killpg", "system", "fork", "forkpty", "posix_spawn", "posix_spawnp"):
                if hasattr(os, name):
                    guards.enter_context(patch.object(os, name, side_effect=AssertionError("process/custody operation forbidden")))
            guards.enter_context(patch.object(subprocess, "Popen", side_effect=AssertionError("child process forbidden")))
            campaign = load("corrected_architecture_campaign", HERE / "campaign.py")
            for name in campaign.CANDIDATE_FILES:
                assert (HERE / name).read_bytes() == (HERE.parent / "swift-execution-architecture-comparison" / name).read_bytes()
            checked = campaign.check(HERE / "source-check")
            assert {row["name"]: row["sourceSHA256"] for row in checked["profiles"]} == readset["generatedSourceSHA256"]
            supplied = load("corrected_architecture_tests", HERE / "test_campaign.py")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                run = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(supplied))
            (HERE / "pure-check.stdout").write_text(stdout.getvalue())
            (HERE / "pure-check.stderr").write_text(stderr.getvalue())
            assert run.wasSuccessful() and run.testsRun == 38, "corrected pure suite failed"
            save(HERE / "correction-evidence.json", differential_reproductions(campaign, supplied, scratch))
            verify_readset(readset)
            for path, expected in readset["basisSeals"].items():
                verify_packet((ROOT / path).parent, expected)
    finally:
        tempfile.tempdir = prior_tempdir
        scratch.rmdir()  # Refuse to hide an unexpected leftover with recursive removal.
    save(HERE / "receipt.json", {"schema": 1, "startedAtUTC": started,
        "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/swift-execution-architecture-correction/verify.py",
        "python": platform.python_version(), "pythonExecutable": sys.executable,
        "model": "gpt-6-astra", "reasoningEffort": "xhigh", "freshContext": True,
        "checkoutRevisionAtPreparation": readset["checkoutRevisionAtPreparation"],
        "relevantSourceTreeDigest": digest((HERE / "readset.json").read_bytes()),
        "sourceTreeDigestScope": "SHA-256 of readset.json, which binds all relevant correction inputs and frozen dependencies",
        "pureTests": {"run": run.testsRun, "passed": run.wasSuccessful()},
        "basisPacketsBeforeAndAfter": packets, "generatedSourceSHA256": readset["generatedSourceSHA256"],
        "candidateGeneratorAndRustInputsByteExact": True,
        "newActualCompilations": 0, "newActualFiniteOrHarnessRuns": 0, "newActualFullAttempts": 0,
        "guards": {"pythonAuditHook": "process creation, sockets, signals; writes restricted to this correction packet",
            "monkeypatch": "Popen, wait4/waitpid/wait, kill/killpg, system/fork/forkpty/posix_spawn; no probes"},
        "cleanup": {"ownedPureScratchRemoved": not scratch.exists(), "noOwnedNativeOrCaptureProcessesStarted": True},
        "heldActorGroupsUnchanged": [20745, 20770, 20780, 20817, 20842, 20851, 20866],
        "unitAHostedPostgreSQLAndLocalFieldLogCompilerHoldsUnchanged": True,
        "commitPushDispatch": False, "independentCorrectionReview": "pending",
        "scope": "source and pure runner correction only; compiled geometry, finite timing, runtime parity, native, published FieldLog, signed OTA and GA remain unverified"})
    print("38 pure controls passed; both defects rejected; source closures unchanged; no runtime attempts")


if __name__ == "__main__":
    sys.addaudithook(audit)
    main()
