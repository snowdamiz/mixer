#!/usr/bin/env python3
"""Bounded, audited pure verification; never compiles or starts a child."""
import ast
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import offline

offline.install()
HERE, ROOT = offline.HERE, offline.ROOT
CHECKS = []


def record(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


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
    campaign = load("completion_verify_campaign", HERE / "campaign.py")
    candidate = campaign.candidate_module()
    original, artifact, _ = campaign.inputs()
    prior = candidate.prior.parameterize(original, True)
    prior_record, _ = campaign.base.source_record(original, prior)
    check("exact previously executed dense512 source closure", prior_record["sha256"] == "09ac825f108574f626838e0fc54628adb5ed70fa8d8871b527bc1bba4922c0ee")
    evidence = json.loads((HERE / "phase-evidence.json").read_bytes())
    check("actual phase extrapolation is explicit and cumulative", evidence["twoCorpusHypothesis"] == {
        k: 2 * evidence["corpus1Cumulative"][k] - value for k, value in evidence["initialize"].items()})
    check("1200 second observation window follows finite rounding rule", 1_200_000 ==
        ((evidence["twoCorpusHypothesis"]["elapsed_micros"] * 14 + 600_000_000 - 1) // 600_000_000) * 60_000)
    check("fuel clears observed two-corpus hypothesis and existing work ceilings remain sufficient", 
        2_000_000_000 < evidence["twoCorpusHypothesis"]["instruction_fuel"] < 4_000_000_000
        and evidence["twoCorpusHypothesis"]["execution_work"] < 16_000_000_000
        and evidence["twoCorpusHypothesis"]["cache_work"] < 4_000_000_000)
    profiles = campaign.check(HERE / "source-check")
    source = candidate.parameterize(original, True)
    check("only fuel deadline defaults and finite guard expectations differ", {n for n in source if source[n] != prior[n]} == {
        "src/experimental_swift_reactor/control.rs", "src/experimental_swift_reactor/cache_tests.rs",
        "src/experimental_swift_reactor/control_tests.rs", "src/experimental_wasi/mod.rs"})
    check("exact twelve finite methods", sum(b.count(b"fn framepin_campaign_") for b in source.values()) == 12)
    control = source["src/experimental_swift_reactor/control.rs"].decode()
    control = candidate.replace(control, "instruction_fuel: 4_000_000_000,", "instruction_fuel: 2_000_000_000,")
    control = candidate.replace(control, "deadline_ms: 1_200_000,", "deadline_ms: 600_000,")
    check("original accounting owner failure and capability behavior byte identical", control.encode() == prior["src/experimental_swift_reactor/control.rs"])
    wasi = candidate.replace(source["src/experimental_wasi/mod.rs"].decode(), "deadline_ms: 1_200_000,", "deadline_ms: 600_000,")
    check("WASI policy implementation identical except one default duration", wasi.encode() == prior["src/experimental_wasi/mod.rs"])
    tests = candidate.replace(source["src/experimental_swift_reactor/control_tests.rs"].decode(),
        (HERE / "scalar-guards.rs").read_text(), (candidate.PRIOR / "scalar-guards.rs").read_text())
    check("original control test bodies preserved", tests.encode() == prior["src/experimental_swift_reactor/control_tests.rs"])
    for name in ("campaign_harness.rs", "lifecycle_tests.rs", "cache.rs", "execution.rs", "frame_operations.rs"):
        path = "src/experimental_swift_reactor/" + name
        check(name + " unchanged from executed dense512 closure", source[path] == prior[path])
    check("bounded original diagnostic prefix observer unchanged", candidate.THRESHOLDS == campaign.PREFIX_THRESHOLDS and campaign.PREFIX_MAX_BYTES == 8192)
    delta, diff = campaign.base.source_record(prior, source)
    campaign.save(HERE / "source-check/dense512-completion/from-actual-source.json", delta)
    (HERE / "source-check/dense512-completion/from-actual.patch").write_text(diff)
    for name in ("candidate.py", "campaign.py", "test_campaign.py", "offline.py", "verify.py"):
        ast.parse((HERE / name).read_text())
        check(name + " parses", True)
    check("finite command plan leaves driver reserve", 2 * 15 + 180 + 90 + 90 + 1350 + 6 * 10 + 10 == 1810 < 2100)
    check("full command permits unchanged validation then runtime then shutdown margin", 120 + 1200 + 30 == 1350)
    scratch = HERE / "pure-scratch"
    scratch.mkdir(exist_ok=False)
    previous, tempfile.tempdir = tempfile.tempdir, str(scratch)
    try:
        suite = load("completion_controls", HERE / "test_campaign.py")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = unittest.TextTestRunner(stream=err, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(suite))
        (HERE / "pure-check.stdout").write_text(out.getvalue())
        (HERE / "pure-check.stderr").write_text(err.getvalue())
        check("pure rejection and orchestration controls", result.wasSuccessful() and result.testsRun == 36)
    finally:
        tempfile.tempdir = previous
        scratch.rmdir()
    save("readset.json", {"sourceBasisRun": 40788458735, "sourceBasisTree": "89a9344ecf974105b7ad7df30394485bade6e284",
        "files": {str(p.relative_to(ROOT)): record(p.read_bytes()) for p in sorted(offline.READS) if p.is_file()}})
    save("checks.json", CHECKS)
    save("receipt.json", {"schema": 1, "startedAtUTC": start, "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/swift-dense512-completion-experiment/verify.py", "python": platform.python_version(),
        "pythonExecutable": sys.executable, "model": "gpt-6-astra", "reasoningEffort": "xhigh", "freshContext": True,
        "sourceTreeDigest": record((HERE / "readset.json").read_bytes())["sha256"], "sourceTreeDigestScope": "audited read source closure, not mutable live HEAD",
        "profiles": profiles["profiles"], "sourceChecks": len(CHECKS), "pureTests": result.testsRun, "allChecksPassed": True,
        "newCompilations": 0, "newActualFiniteOrHarnessRuns": 0, "newActualFullAttempts": 0,
        "nativeCaptureProcessInventorySignalWaitNetworkCalls": 0, "ownedScratchRemoved": not scratch.exists(),
        "heldActorGroupsUnchanged": [20745,20770,20780,20817,20842,20851,20866], "unitAHostedFieldLogHoldsUnchanged": True,
        "selection": "pending independent root review", "scope": "pure candidate verification; actual Rust build, finite controls, geometry and original full two-corpus completion remain pending"})
    print(f"{len(CHECKS)} source checks and {result.testsRun} pure tests passed; actual compilation and execution pending")


if __name__ == "__main__":
    main()
