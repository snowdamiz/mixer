#!/usr/bin/env python3
"""Independent source and pure-data review. Never starts a compiler or guest."""
import contextlib
import copy
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / "swift-execution-architecture-comparison"
SEAL = "b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70"
SOURCES = {False: "af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7",
           True: "3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    checks = []
    findings = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    check("producer seal identity", digest((PACKET / "seal.json").read_bytes()) == SEAL)
    seal = json.loads((PACKET / "seal.json").read_text())
    check("exact producer sealed inventory", {str(p.relative_to(PACKET)) for p in PACKET.rglob("*") if p.is_file()}
          == set(seal["files"]) | {"seal.json"})
    for name, record in seal["files"].items():
        data = (PACKET / name).read_bytes()
        check("producer binding: " + name, len(data) == record["bytes"] and digest(data) == record["sha256"])
    check("producer count and bytes", len(seal["files"]) == seal["fileCount"] == 26
          and sum(r["bytes"] for r in seal["files"].values()) == seal["totalBytes"] == 309831)

    campaign = load("independent_campaign", PACKET / "campaign.py")
    scratch = HERE / "scratch"
    scratch.mkdir(exist_ok=True)
    tempfile.tempdir = str(scratch)
    guards = contextlib.ExitStack()
    with guards:
        for owner, name in ((campaign.base.subprocess, "Popen"), (campaign.base.os, "wait4"), (campaign.base.os, "killpg")):
            guards.enter_context(patch.object(owner, name, side_effect=AssertionError("process operation forbidden")))
        original, artifact, bindings = campaign.inputs()
        check("exact original wasm bytes and hash", len(artifact) == 53_777_114
              and digest(artifact) == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994")
        del artifact
        source = {}
        for arm in (False, True):
            source[arm] = campaign.prepare_source(original, arm)
            record, _ = campaign.base.source_record(original, source[arm])
            check("generated source identity: " + str(arm), record["sha256"] == SOURCES[arm])
        check("only three algorithm files differ", {p for p in source[False] if source[False][p] != source[True][p]} == {
            "src/experimental/cache/borrowed.rs", "src/experimental_swift_reactor/cache.rs",
            "src/experimental_swift_reactor/cache_tests.rs"})
        check("original harness identical in both arms", all(source[a]["src/experimental_swift_reactor/campaign_harness.rs"]
              == (campaign.base.INPUTS / "harness.rs").read_bytes() for a in source))
        check("frozen generic test bodies unchanged except visibility", source[True]["src/experimental/cache/tests.rs"]
              .replace(b"pub(super) fn frozen_ir_parity_for_all_supported_opcode_shapes", b"fn frozen_ir_parity_for_all_supported_opcode_shapes")
              .replace(b"pub(super) fn stale_token_nonce_and_owner_exhaustion_fail_closed", b"fn stale_token_nonce_and_owner_exhaustion_fail_closed")
              == original["src/experimental/cache/tests.rs"])
        check("literal exact-capacity defect source present", b'SwiftRunFailureKind::Allocation,\n                "swift_run_unexpected_capacity"' in source[True]["src/experimental_swift_reactor/control.rs"]
              and b"SwiftRunResource::ExactCapacity" in source[True]["src/experimental_swift_reactor/control.rs"])
        check("instruction charge precedes increment", source[True]["src/experimental_swift_reactor/control.rs"].index(b"self.charge_fuel_with_wasi(1, cursor, wasi)?;")
              < source[True]["src/experimental_swift_reactor/control.rs"].index(b"self.instructions = self.instructions.checked_add(1)"))

        # Run the supplied suite in this Python process. Its process operations
        # are separately patched; temporary files live only in our owned scratch.
        supplied = load("independent_supplied_tests", PACKET / "test_campaign.py")
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            run = unittest.TextTestRunner(stream=error, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(supplied))
        (HERE / "supplied-tests.stdout").write_text(output.getvalue())
        (HERE / "supplied-tests.stderr").write_text(error.getvalue())
        check("supplied 32 pure controls", run.wasSuccessful() and run.testsRun == 32)

        # Re-parse actual sealed historical log bytes after explicit pure-fixture
        # mutations. These are NOT new runtime receipts or a feasibility claim.
        baseline = (campaign.base.INPUTS / "historical-attribution.stdout").read_text()
        bounds = campaign.expected_bounds()
        rows = []
        for line in baseline.splitlines():
            marker = "MIXER_EXACT " if "MIXER_EXACT " in line else "MIXER_ATTRIBUTION " if "MIXER_ATTRIBUTION " in line else None
            if marker is None:
                rows.append(line)
                continue
            before, value = line.split(marker, 1)
            row = json.loads(value)
            if marker == "MIXER_EXACT ":
                if row["event"] in bounds:
                    row["payload"] = bounds[row["event"]]
                if row["event"] in ("runtime_failure", "final_failure"):
                    row["payload"].update(kind="Allocation", code="swift_run_unexpected_capacity", resource="ExactCapacity",
                        attempted=160000, limit=160000, observed_capacity=160002)
            elif row.get("payload"):
                row["payload"]["first_rejection"] = None
            rows.append(before + marker + json.dumps(row, separators=(",", ":")))
        log = scratch / "synthetic-unexpected-capacity.stdout"
        log.write_text("\n".join(rows) + "\n")
        command = {"pid": 123, "exitCode": 101, "timedOut": False, "cancelled": None, "processGroupEmpty": True}
        result = campaign.base.classify(log, command)
        campaign.validate_result(result, command)
        check("reproduction: unexpected capacity accepted", result["outcome"] == "resource-limit-diagnostic"
              and result["telemetry"]["status"] == "valid" and result["originalFinalFailurePreserved"])
        save(HERE / "unexpected-capacity-reproduction.json", {"scope": "pure synthetic log mutation; no runtime execution",
            "inputHistoricalSHA256": digest(baseline.encode()), "syntheticLogSHA256": digest(log.read_bytes()),
            "mutations": {"profile": bounds, "failure": {k: result["firstFailure"]["payload"][k] for k in
                ("kind", "code", "resource", "attempted", "limit", "observed_capacity")}, "attributionRejection": None},
            "acceptedOutcome": result["outcome"], "telemetryStatus": result["telemetry"]["status"],
            "originalFinalFailurePreserved": result["originalFinalFailurePreserved"]})
        findings.append({"id": "R1", "priority": 1, "blocking": True,
            "title": "Unexpected exact allocation capacity is admitted as an ordinary resource stop",
            "file": "campaign.py", "lines": [205, 209], "evidence": "unexpected-capacity-reproduction.json"})

        # Preserve independent rejection checks for real terminal invariants.
        for kind in ("Invariant", "DecoderMismatch", "Cancelled", "Wasi", "GuestTrap", "InvalidBudget"):
            changed = copy.deepcopy(result)
            changed["firstFailure"]["payload"]["kind"] = kind
            campaign.event(changed, "final_failure")["kind"] = kind
            try:
                campaign.validate_result(changed, command)
            except RuntimeError:
                check("reject terminal kind " + kind, True)
            else:
                raise AssertionError("accepted terminal kind " + kind)

        prefix = {"threshold": 25_000_000, "instructions": 25_000_000, "instruction_fuel": 0,
            "cache_work": 1, "execution_work": 1, "host_calls": 0, "elapsed_micros": 1, "function": 34, "offset": 100}
        path = scratch / "synthetic-impossible-prefix.stderr"
        path.write_text("MIXER_PREFIX " + json.dumps(prefix) + "\n")
        parsed, _ = campaign.prefix_records(path)
        changed = copy.deepcopy(result)
        final = campaign.event(changed, "final_cleanup_usage")
        final["instructions"] = 25_000_000
        final["instruction_fuel"] = 25_000_000
        campaign.validate_prefix(changed, parsed)
        check("reproduction: impossible prefix fuel accepted", parsed["records"][0]["instruction_fuel"] < parsed["records"][0]["instructions"])
        prefix_case = {"record": prefix, "acceptedByPrefixParser": True, "acceptedByFinalUsageJoin": True}
        repeated_fuel = [prefix | {"instruction_fuel": 100_000_000},
            prefix | {"threshold": 50_000_000, "instructions": 50_000_000, "instruction_fuel": 100_000_000}]
        path.write_text("".join("MIXER_PREFIX " + json.dumps(p) + "\n" for p in repeated_fuel))
        parsed, _ = campaign.prefix_records(path)
        final.update(instructions=50_000_000, instruction_fuel=100_000_000)
        campaign.validate_prefix(changed, parsed)
        check("reproduction: 25M additional instructions with no additional fuel accepted", parsed["records"] == repeated_fuel)
        save(HERE / "impossible-prefix-reproduction.json", {"scope": "pure synthetic prefix fixture; no runtime execution",
            "zeroFuelCase": prefix_case, "nonincreasingExtraFuelCase": {"records": repeated_fuel,
                "acceptedByPrefixParser": True, "acceptedByFinalUsageJoin": True},
            "violatedInvariant": "instruction_fuel - instructions >= 0 and is nondecreasing from owner start through prefixes to final usage"})
        findings.append({"id": "R2", "priority": 2, "blocking": True,
            "title": "Prefix validation admits impossible instruction and fuel accounting",
            "file": "campaign.py", "lines": [229, 251], "evidence": "impossible-prefix-reproduction.json"})

        # The command guard must keep unresolved custody and never refund it.
        for bad in ({"pid": 0, "exitCode": 0, "processGroupEmpty": True},
                    {"pid": 123, "exitCode": -999, "processGroupEmpty": True},
                    {"pid": 123, "exitCode": 0, "processGroupEmpty": False}):
            custody = {"pendingCommand": None, "provenClosedCommands": 0, "recordPath": str(scratch / "synthetic-custody.json")}
            with patch.object(campaign.base, "command", return_value=bad):
                try:
                    campaign.guarded_command(custody, ["never-run"], scratch, {}, scratch / "not-created", 1)
                except RuntimeError:
                    check("retain unresolved custody " + str(bad), custody["pendingCommand"] is not None and custody["provenClosedCommands"] == 0)
                else:
                    raise AssertionError("accepted unresolved custody")

    shutil.rmtree(scratch)
    check("owned inspection and synthetic scratch removed", not scratch.exists())
    save(HERE / "checks.json", {"schema": 1, "recordedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(), "sourceRevisionObserved": "56ff14c925168284761c5aca4f0bd4129cf3c995",
        "scope": "independent source inspection and pure data/mocked orchestration; no compiler, guest, native, CI, custody probe",
        "reviewedSealSHA256": SEAL, "sourceSHA256": {"control-original256": SOURCES[False], "candidate-dense": SOURCES[True]},
        "checks": checks, "checksPassed": len(checks), "suppliedTestsPassed": 32, "findings": findings,
        "decision": "changes-required-before-dispatch", "runtimeAttempts": 0, "candidateCompiled": False,
        "cleanup": {"ownedScratchRemoved": True, "compilerGuestNativeCaptureProcessesStarted": False, "heldActorsProbed": False},
        "hostFeasibilityAccepted": False, "defaultPromotionAuthorized": False})
    print(json.dumps({"checksPassed": len(checks), "suppliedTestsPassed": 32, "blockingFindings": len(findings)}))


if __name__ == "__main__":
    main()
