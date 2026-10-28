#!/usr/bin/env python3
"""Audited pure source/orchestration verification; no compilation or runtime."""
import ast
import contextlib
import datetime
import difflib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch  # Load SSL subclasses before socket guard.
import offline

offline.install()
HERE, ROOT = offline.HERE, offline.ROOT
CHECKS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(data):
    return {"bytes": len(data), "sha256": sha(data)}


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check(name, passed):
    offline.bounded()
    CHECKS.append({"check": name, "passed": bool(passed)})
    if not passed:
        raise AssertionError(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    campaign = load("window_campaign", HERE / "campaign.py")
    candidate = campaign.candidate_module()
    original, artifact, _ = campaign.inputs()
    prior = candidate.prior.parameterize(original, True)
    prior_record, _ = campaign.base.source_record(original, prior)
    check("exact executed dense 128-frame source closure", prior_record["sha256"] == "e3a4a90378a90d8cc5d22244c5ae345d30e57670cc396098c4370872a9a2284b")
    summary = json.loads((HERE / "baseline-summary.json").read_bytes())
    check("exact failed closed baseline reused, never replayed", summary["run"]["id"] == 40779075333 and summary["fullAttemptsRemaining"] == 0
        and summary["all11CommandGroupsClosed"] and summary["scratchRemoved"]
        and all(a["firstFailure"]["resource"] == "CacheWork" and a["completedOriginalCorpora"] == 0 for a in summary["arms"]))
    profiles = campaign.check(HERE / "source-check")
    current = {}
    for name, capacity, _, count in campaign.PROFILES:
        source = candidate.parameterize(original, capacity)
        current[capacity] = source
        changed = {n for n in source if source[n] != prior[n]}
        permitted = {"src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/control_tests.rs", "src/experimental_swift_reactor/cache_tests.rs"}
        if capacity:
            permitted |= {"src/experimental/cache/mod.rs", "src/experimental_swift_reactor/cache.rs"}
        check(name + " exact bounded delta", changed == permitted)
        check(name + " finite test count", sum(data.count(b"fn framepin_campaign_") for data in source.values()) == count == 12)
        bounds = candidate.expected_bounds(capacity)
        old = candidate.prior.expected_bounds()
        differences = {n for n in bounds["run_budget"] if bounds["run_budget"][n] != old["run_budget"][n]}
        check(name + " only selected numeric bounds changed", differences == ({"cache_work", "instruction_fuel", "execution_work", "cache_entries"} if capacity else {"cache_work", "instruction_fuel", "execution_work"}))
        check(name + " every other complete budget/grant unchanged", all(bounds[n] == old[n] for n in old if n != "run_budget"))
        check(name + " all category bytes frames pins duration unchanged", all(bounds["run_budget"][n] == old["run_budget"][n] for n in old["run_budget"] if n not in differences))
        control = source["src/experimental_swift_reactor/control.rs"].decode()
        for old_text, new_text in (("4_000_000_000", "768_000_000"), ("2_000_000_000", "1_000_000_000"),
            ("16_000_000_000", "8_000_000_000")):
            control = candidate.replace(control, old_text, new_text)
        control = candidate.replace(control, " | ".join(f"{n:_}" for n in candidate.THRESHOLDS), "25_000_000 | 50_000_000 | 100_000_000")
        if capacity:
            control = candidate.replace(control, "MAX_RESERVATION_TICKETS: usize = 534;", "MAX_RESERVATION_TICKETS: usize = 278;")
            control = candidate.replace(control, "cache_entries: 512,", "cache_entries: 256,")
        check(name + " original scalar accounting and denial paths byte identical", control.encode() == prior["src/experimental_swift_reactor/control.rs"])
        cache = source["src/experimental_swift_reactor/cache.rs"]
        shared = source["src/experimental/cache/mod.rs"]
        if capacity:
            cache = candidate.replace(cache.decode(), "RESIDENT_LINKS: usize = 512;", "RESIDENT_LINKS: usize = 256;").encode()
            shared = candidate.replace(shared.decode(), "MAX_ENTRIES: usize = 512;", "MAX_ENTRIES: usize = 256;").encode()
        check(name + " unchanged actual dense cache and debit implementation", cache == prior["src/experimental_swift_reactor/cache.rs"])
        check(name + " unchanged shared eviction and replacement algorithm", shared == prior["src/experimental/cache/mod.rs"])
        delta, diff = campaign.base.source_record(prior, source)
        campaign.save(HERE / "source-check" / name / "delta-source.json", delta)
        (HERE / "source-check" / name / "from-actual.patch").write_text(diff)
    check("one variable between new profiles", {n for n in candidate.expected_bounds(False)["run_budget"] if candidate.expected_bounds(False)["run_budget"][n] != candidate.expected_bounds(True)["run_budget"][n]} == {"cache_entries"})
    check("extended prefix range and byte cap bounded", campaign.PREFIX_THRESHOLDS == candidate.THRESHOLDS and len(candidate.THRESHOLDS) == 10 and campaign.PREFIX_MAX_BYTES == 8192)
    for file in ("candidate.py", "campaign.py", "test_campaign.py", "offline.py", "verify.py"):
        ast.parse((HERE / file).read_text())
        check(file + " Python parse", True)
    scratch = HERE / "pure-scratch"
    scratch.mkdir(exist_ok=False)
    previous, tempfile.tempdir = tempfile.tempdir, str(scratch)
    try:
        suite = load("window_controls", HERE / "test_campaign.py")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = unittest.TextTestRunner(stream=err, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(suite))
        (HERE / "pure-check.stdout").write_text(out.getvalue())
        (HERE / "pure-check.stderr").write_text(err.getvalue())
        check("pure campaign controls", result.wasSuccessful() and result.testsRun >= 39)
    finally:
        tempfile.tempdir = previous
        scratch.rmdir()
    inputs = {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(offline.READS) if p.is_file()}
    save("readset.json", {"sourceBasisRun": 40779075333, "sourceBasisHead": "295f3f18a53459449f22253687bd2d0b2c09a0ed", "files": inputs})
    save("checks.json", CHECKS)
    save("receipt.json", {"schema": 1, "startedAtUTC": start, "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/swift-cachework-128-experiment/verify.py", "python": platform.python_version(), "pythonExecutable": sys.executable,
        "model": "gpt-6-astra", "reasoningEffort": "xhigh", "freshContext": True,
        "sourceTreeDigest": sha((HERE / "readset.json").read_bytes()), "sourceTreeDigestScope": "audited read source closure, not mutable live HEAD",
        "profiles": profiles["profiles"], "structuralChecks": len(CHECKS), "runnerPureTests": result.testsRun,
        "allChecksPassed": True, "newCompilations": 0, "newActualFiniteOrHarnessRuns": 0, "newActualFullAttempts": 0,
        "nativeCaptureProcessInventorySignalWaitNetworkCalls": 0, "ownedScratchRemoved": not scratch.exists(),
        "heldActorGroupsUnchanged": [20745,20770,20780,20817,20842,20851,20866], "unitAHostedFieldLogHoldsUnchanged": True,
        "rootSelection": "pending independent review and selection", "scope": "pure candidate verification; Rust type checking, actual 512 geometry/finite guards and full execution pending"})
    print(f"{len(CHECKS)} source checks and {result.testsRun} pure runner tests passed; no compilation/runtime")


if __name__ == "__main__":
    main()
