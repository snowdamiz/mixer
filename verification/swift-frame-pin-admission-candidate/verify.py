#!/usr/bin/env python3
"""Audited offline proposal verification; no Rust, Swift, guests or custody probes."""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch  # Load SSL class definitions before socket guards.

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
START = time.monotonic()
READS = set()
CHECKS = []
DENIED = []


def blocked(*args, **kwargs):
    DENIED.append("explicit process/socket/signal/wait guard")
    raise AssertionError("process/socket/signal/wait operation forbidden")


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.chdir",
    }:
        raise AssertionError("pure audit denied " + event)
    if event == "open":
        name, mode, flags = args
        writing = isinstance(mode, str) and any(c in mode for c in "wax+")
        writing |= isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if isinstance(name, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(name)).resolve()
            if writing and not path.is_relative_to(HERE):
                raise AssertionError("write outside candidate lane")
            if not writing and path.is_relative_to(ROOT) and not path.is_relative_to(HERE):
                READS.add(path)
        elif writing:
            raise AssertionError("unbound descriptor write")


sys.addaudithook(audit)
socket.socket = blocked
socket.create_connection = blocked
subprocess.Popen = blocked
for name in ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen"):
    if hasattr(os, name):
        setattr(os, name, blocked)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(data):
    return {"bytes": len(data), "sha256": sha(data)}


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check(label, condition):
    if time.monotonic() - START > 60:
        raise AssertionError("offline verification exceeded 60-second bound")
    CHECKS.append({"check": label, "passed": bool(condition)})
    if not condition:
        raise AssertionError(label)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wasm_name(data, target):
    """Bounded byte parser of optional custom/name/function entries only."""
    check("Wasm magic/version", data[:8] == b"\0asm\x01\0\0\0")
    def uint(at, end):
        value = 0
        for shift in range(0, 35, 7):
            if at >= end:
                raise ValueError("truncated unsigned LEB")
            byte = data[at]
            at += 1
            value |= (byte & 127) << shift
            if not byte & 128:
                if value >= 1 << 32:
                    raise ValueError("u32 overflow")
                return value, at
        raise ValueError("overlong unsigned LEB")
    at, found, custom_names = 8, [], []
    sections = 0
    while at < len(data):
        sections += 1
        if sections > 1000:
            raise ValueError("section bound")
        kind = data[at]
        length, start = uint(at + 1, len(data))
        end = start + length
        if end > len(data):
            raise ValueError("section overflow")
        at = end
        if kind != 0:
            continue
        name_len, content = uint(start, end)
        if content + name_len > end or name_len > 4096:
            raise ValueError("custom name bound")
        name = data[content:content + name_len]
        custom_names.append(name.decode("utf-8", "replace"))
        if name != b"name":
            continue
        pos = content + name_len
        while pos < end:
            subtype = data[pos]
            size, sub = uint(pos + 1, end)
            sub_end = sub + size
            if sub_end > end:
                raise ValueError("subsection overflow")
            pos = sub_end
            if subtype != 1:
                continue
            count, item = uint(sub, sub_end)
            if count > 80000:
                raise ValueError("function name count")
            for _ in range(count):
                index, item = uint(item, sub_end)
                size, item = uint(item, sub_end)
                if item + size > sub_end:
                    raise ValueError("function name overflow")
                if index == target:
                    if size > 4096:
                        raise ValueError("selected name exceeds output bound")
                    found.append(data[item:item + size].decode("utf-8", "strict"))
                item += size
            if item != sub_end:
                raise ValueError("function name trailing bytes")
    return {"function": target, "names": found, "customSections": custom_names,
        "callStackRetained": False, "scope": "optional symbol bytes only; no demangler or guest execution; does not prove caller chain or legitimate recursion"}


def bitmap_checks():
    full = (1 << 64) - 1
    for length in range(129):
        permitted = [min((1 << length) - 1, full), (1 << max(0, length - 64)) - 1]
        free = permitted.copy()
        records = [0] * length
        for selected in range(length):
            word = int(free[0] == 0)
            low = free[word] & -free[word]
            slot = word * 64 + low.bit_length() - 1
            if slot != selected or records[slot] != 0:
                raise AssertionError("bitmap allocation order")
            records[slot] = selected + 1
            free[slot // 64] &= ~(1 << (slot % 64))
            if sum(x.bit_count() for x in free) + selected + 1 != length:
                raise AssertionError("bitmap live agreement")
        for selected in reversed(range(length)):
            records[selected] = 0
            free[selected // 64] |= 1 << (selected % 64)
        check("two-word bit arithmetic length " + str(length), free == permitted and not any(records))
    # A Python arithmetic model is not an executed Rust ownership test.
    return {"lengths": 129, "scope": "independent two-word arithmetic checks; actual Rust owner tests pending"}


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    campaign = load("framepin_campaign", HERE / "campaign.py")
    candidate = campaign.candidate_module()
    original, artifact, _ = campaign.inputs()
    review_path = ROOT / "verification/github-delivery-architecture-comparison/ci-review"
    review_raw = (review_path / "review.json").read_bytes()
    review_seal = json.loads((review_path / "seal.json").read_bytes())
    check("actual comparison review bound to selected seal", record(review_raw) == review_seal["files"]["review.json"])
    reviewed = json.loads(review_raw)
    check("actual baseline both attempted frame 65", all(a["firstFailure"]["code"] == "swift_frame_depth" and a["firstFailure"]["attempted"] == 65 and a["firstFailure"]["limit"] == 64 for a in reviewed["arms"]))
    bound = candidate.expected_bounds()
    before_bound = candidate.prior.expected_bounds()
    changes = {k for k in bound["run_budget"] if bound["run_budget"][k] != before_bound["run_budget"][k]}
    check("only frame and pin budgets change", changes == {"frames", "active_pins"})
    check("all non-run budgets and grants unchanged", all(bound[k] == before_bound[k] for k in bound if k != "run_budget"))
    profiles = campaign.check(HERE / "source-check")
    for name, algorithm, _, count in campaign.PROFILES:
        prior = candidate.prior.parameterize(original, algorithm)
        source = candidate.parameterize(original, algorithm)
        prior_record, _ = campaign.base.source_record(original, prior)
        check(name + " exact prior source closure", prior_record["sha256"] == reviewed["arms"][int(algorithm)]["sourceClosureSHA256"])
        delta, patch = campaign.base.source_record(prior, source)
        campaign.save(HERE / "source-check" / name / "delta-source.json", delta)
        (HERE / "source-check" / name / "from-actual.patch").write_text(patch)
        changed = {key for key in source if source[key] != prior[key]}
        permitted = {"control.rs", "frame_operations.rs", "cache_tests.rs", "frame_operations_tests.rs", "execution_tests.rs"}
        if algorithm:
            permitted.add("cache.rs")
        check(name + " bounded file delta", changed == {"src/experimental_swift_reactor/" + n for n in permitted})
        tests = sum(data.count(b"fn framepin_campaign_") for data in source.values())
        check(name + " exact selected finite test count", tests == count)
        check(name + " frame clamp lifted in copied source", b"budget().frames.min(128)" in source["src/experimental_swift_reactor/frame_operations.rs"])
        check(name + " harness exact", source["src/experimental_swift_reactor/campaign_harness.rs"] == prior["src/experimental_swift_reactor/campaign_harness.rs"])
        check(name + " identity and pin publication core unchanged", source["src/experimental/cache/borrowed.rs"] == prior["src/experimental/cache/borrowed.rs"])
        check(name + " ticket count unchanged", b"MAX_RESERVATION_TICKETS: usize = 278;" in source["src/experimental_swift_reactor/control.rs"])
        if algorithm:
            cache = source["src/experimental_swift_reactor/cache.rs"].decode()
            check("two-word inventory present in all three envelopes", cache.count("(3, size_of::<DensePinInventory>())") == 3)
            check("two-word owners and borrow", cache.count("free_pins: [u64; 2]") == 2 and "free_pins: &'a mut [u64; 2]" in cache)
            check("dense owner inventory covers widened masks and word selector", "mask: [u64; 2], permitted: [u64; 2], word: usize" in cache)
    save("function-name.json", wasm_name(artifact, 24126))
    arithmetic = bitmap_checks()
    scratch = HERE / "pure-scratch"
    scratch.mkdir(exist_ok=False)
    previous, tempfile.tempdir = tempfile.tempdir, str(scratch)
    try:
        suite = load("framepin_runner_tests", HERE / "test_campaign.py")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(suite))
        (HERE / "pure-check.stdout").write_text(stdout.getvalue())
        (HERE / "pure-check.stderr").write_text(stderr.getvalue())
        check("corrected runner controls", result.wasSuccessful() and result.testsRun == 39)
    finally:
        tempfile.tempdir = previous
        scratch.rmdir()
    candidate.bound_prior()
    readset = {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(READS) if p.is_file()}
    save("readset.json", {"files": readset, "sourceBasisRun": 40768719255, "sourceBasisHead": "dfd0e3196543cc1749c9cc924cc7accf28c9dc25"})
    save("checks.json", CHECKS)
    save("receipt.json", {"schema": 1, "startedAtUTC": started,
        "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/swift-frame-pin-admission-candidate/verify.py",
        "python": platform.python_version(), "pythonExecutable": sys.executable,
        "model": "gpt-6-astra", "reasoningEffort": "xhigh", "freshContext": True,
        "sourceTreeDigest": sha((HERE / "readset.json").read_bytes()),
        "sourceTreeDigestScope": "all repository inputs read by audited verifier, including frozen archive and generators; not a live checkout revision",
        "profiles": profiles["profiles"], "arithmeticChecks": arithmetic, "structuralChecks": len(CHECKS),
        "runnerPureTests": result.testsRun, "allChecksPassed": True,
        "guards": "audit denies child process/socket/signal operations and out-of-lane writes; explicit process/wait/network guards; no probes",
        "newCompilations": 0, "newActualFiniteOrHarnessRuns": 0, "newActualFullAttempts": 0,
        "ownedScratchRemoved": not scratch.exists(), "noNativeCaptureOrCustodyProcessesStarted": True,
        "heldActorGroupsUnchanged": [20745, 20770, 20780, 20817, 20842, 20851, 20866],
        "unitAHostedFieldLogCompilerHoldsUnchanged": True, "rootSelection": "pending independent review",
        "scope": "source and pure structural proposal only; actual Rust compilation, geometry, finite owner controls and full two-corpus attempts remain pending"})
    print(f"{len(CHECKS)} structural/arithmetic checks and {result.testsRun} pure runner tests passed; no runtime attempts")


if __name__ == "__main__":
    main()
