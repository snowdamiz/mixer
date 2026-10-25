#!/usr/bin/env python3
"""Root-approved bounded four-thread library continuation after serial timeout."""
import json
from pathlib import Path
import re
import shutil
import run as R


def main():
    assert not R.SCRATCH.exists()
    prior = json.loads((R.HERE / "serial-attempt/receipt.json").read_bytes())
    assert not prior["passed"] and prior["cleanup"]["removed"]
    assert not (R.HERE / "serial-attempt/post-failure-known-group-446.txt").read_text()
    R.BASELINE = json.loads((R.HERE / "baseline-manifest.json").read_bytes())
    candidate = json.loads((R.HERE / "candidate-manifest.json").read_bytes())
    R.TOOLS = json.loads((R.HERE / "tools.json").read_bytes())
    R.RECEIPTS = [json.loads(p.read_bytes()) for p in sorted((R.HERE / "commands").glob("*/receipt.json"))]
    R.RECEIPTS.append({"aggregateBudgetChargeSeconds": 190, "durationSeconds": None,
                       "scope": "conservative charge for incomplete serial timeout plus finite TERM/KILL cleanup"})
    R.SCRATCH.mkdir(mode=0o700)
    (R.SCRATCH / "tmp").mkdir(mode=0o700)
    for name in R.BASELINE:
        source = R.HERE / ("candidate" if name == R.TEST else "baseline") / name
        destination = R.SOURCE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    assert R.manifest(R.SOURCE) == candidate and R.manifest(R.ROOT / "vm") == R.BASELINE
    assert R.tools() == R.TOOLS
    outcome = {k: v for k, v in prior.items() if k not in ("failure", "cleanup", "commandCount", "aggregateCommandSeconds", "normalConfigurations")}
    outcome.update(passed=False, normalConfigurations=[], continuationThreads=4,
        priorSerialTimeoutAndCollectorFailurePreserved=True, serialTerminalReceiptIncomplete=True,
        serialActualDurationUnknown=True, serialConservativeBudgetChargeSeconds=190,
        productionCfgNegativeChecks=0, fullReactorReadOrRun=False)
    try:
        for feature, release in (("swift", False), ("swift", True), ("all", False), ("all", True)):
            name = "resume-" + feature + ("-release" if release else "-debug")
            binary, flags = R.build(name, feature, release)
            listed = R.command(name + "-list", [binary, "--list"])
            names = sorted(line.removesuffix(": test") for line in (listed / "stdout").read_text().splitlines() if line.endswith(": test"))
            assert len([n for n in names if "swift_release_observer_" in n]) == 3
            R.save(name + "-test-identities.json", names)
            replay = R.command(name + "-library", [binary, "--nocapture", "--test-threads=4"])
            text = (replay / "stdout").read_text()
            summary = re.search(r"test result: ok\. (\d+) passed; 0 failed; 0 ignored;", text)
            assert summary and int(summary.group(1)) == len(names)
            outcome["normalConfigurations"].append({"name": name, "identities": len(names), "passed": int(summary.group(1)), "ignored": 0})
            R.command(name + "-production-check", ["cargo", "check", "--lib", "--locked", "--offline", "--no-default-features", *flags])
        frame = (R.SOURCE / R.FRAME).read_bytes()
        (R.SOURCE / R.FRAME).write_bytes(frame + R.PROBE.encode())
        for feature, release in (("swift", False), ("swift", True), ("all", False), ("all", True)):
            name = "resume-" + feature + ("-release" if release else "-debug")
            flags = ["--all-features"] if feature == "all" else ["--features", "experimental-swift-reactor"]
            flags += ["--release"] if release else []
            negative = R.command(name + "-cfg-negative", ["cargo", "check", "--lib", "--locked", "--offline", "--no-default-features", *flags], 101)
            text = (negative / "stderr").read_text()
            assert "error[E0433]" in text and "tests" in text and "release_observer_cfg_negative" in text
            outcome["productionCfgNegativeChecks"] += 1
        (R.SOURCE / R.FRAME).write_bytes(frame)
        assert R.manifest(R.SOURCE) == candidate
        outcome["normalIdentityExecutions"] = sum(row["passed"] for row in outcome["normalConfigurations"])
        outcome["passed"] = True
    except BaseException as error:
        outcome["failure"] = {"type": type(error).__name__, "message": str(error)}
        raise
    finally:
        R.save("final-source-manifest.json", R.manifest(R.SOURCE))
        R.cleanup()
        charges = sum(row.get("aggregateBudgetChargeSeconds", row.get("durationSeconds", 0)) for row in R.RECEIPTS)
        outcome.update(commandCount=len(list((R.HERE / "commands").glob("*/receipt.json"))),
            aggregateCommandSecondsKnown=sum(row["durationSeconds"] for row in R.RECEIPTS if row.get("durationSeconds") is not None),
            aggregateBudgetChargedSeconds=charges, aggregateCommandBudgetSeconds=900,
            liveVMUnchanged=R.manifest(R.ROOT / "vm") == R.BASELINE, toolsUnchanged=R.tools() == R.TOOLS,
            cleanup=json.loads((R.HERE / "cleanup.json").read_bytes()))
        R.save("receipt.json", outcome)
    print(json.dumps(outcome), flush=True)


if __name__ == "__main__":
    main()
