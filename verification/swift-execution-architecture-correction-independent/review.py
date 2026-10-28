#!/usr/bin/env python3
"""Independent, audited source/pure-data correction review. No real child runs."""
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
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKET = HERE.parent / "swift-execution-architecture-correction"
SEALS = {
    "swift-execution-architecture-correction": "4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2",
    "swift-execution-architecture-comparison": "b20440be09778e3209de5c1e6dae941e0580b8737fe28ed35be53777e3292f70",
    "swift-execution-architecture-independent": "c1ecb422803c2e43dc69206b28e6f51e2b023b9b8fab13054e20ecc7976a7486",
}
READSET_SHA = "8fa269fba7e152771339bc80f03ad31371fce245bef74cebb108d88d41a8fa59"
SOURCES = {False: "af58b29a605384f3ac3ac2d3a3b513533e0da4f140f0e5d2c22807eb78bcb2f7",
           True: "3db26064abc07200219b62c9637850f50868f470bb2d0ca7598223131c2033d4"}
CHECKS = []


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def check(name, value):
    assert value, name
    CHECKS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit(event, args):
    if event.startswith(("subprocess.", "socket.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.exec", "os.posix_spawn", "os.kill", "os.killpg", "pty.spawn"
    }:
        raise AssertionError("independent pure review forbids process/socket/custody operation: " + event)
    if event == "open":
        path, mode, flags = args
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND))
        if writing:
            assert not isinstance(path, int) and Path(path).resolve().is_relative_to(HERE), "write outside independent packet"


def verify_inputs(label):
    bindings = {}
    for name, expected in SEALS.items():
        path = HERE.parent / name
        raw = (path / "seal.json").read_bytes()
        check(label + " seal " + name, digest(raw) == expected)
        seal = json.loads(raw)
        check(label + " exact inventory " + name,
            {str(p.relative_to(path)) for p in path.rglob("*") if p.is_file()} == set(seal["files"]) | {"seal.json"})
        for member, entry in seal["files"].items():
            data = (path / member).read_bytes()
            check(label + " sealed member " + name + "/" + member,
                len(data) == entry["bytes"] and digest(data) == entry["sha256"])
        check(label + " count/bytes " + name, len(seal["files"]) == seal["fileCount"] and
            sum(x["bytes"] for x in seal["files"].values()) == seal["totalBytes"])
        bindings[name] = {"sealSHA256": expected, "fileCount": seal["fileCount"], "totalBytes": seal["totalBytes"]}
    raw = (PACKET / "readset.json").read_bytes()
    check(label + " readset identity", digest(raw) == READSET_SHA)
    readset = json.loads(raw)
    for name, entry in readset["files"].items():
        data = (ROOT / name).read_bytes()
        check(label + " readset member " + name, len(data) == entry["bytes"] and digest(data) == entry["sha256"])
    return bindings, readset


def outcome(call):
    try:
        call()
    except RuntimeError as error:
        return {"accepted": False, "reason": str(error)}
    return {"accepted": True}


def failure_log(campaign, failure):
    """Only fixture data changes; the real immutable parser handles this text."""
    text = (campaign.base.INPUTS / "historical-attribution.stdout").read_text()
    bounds, rows = campaign.expected_bounds(), []
    for line in text.splitlines():
        marker = next((m for m in ("MIXER_EXACT ", "MIXER_ATTRIBUTION ") if m in line), None)
        if marker is None:
            rows.append(line)
            continue
        pre, raw = line.split(marker, 1)
        row = json.loads(raw)
        if marker == "MIXER_EXACT ":
            if row["event"] in bounds:
                row["payload"] = bounds[row["event"]]
            if row["event"] in ("runtime_failure", "final_failure"):
                row["payload"].update(failure)
        elif row.get("payload"):
            row["payload"]["first_rejection"] = None
        rows.append(pre + marker + json.dumps(row, separators=(",", ":")))
    return "\n".join(rows) + "\n"


def independent_campaign(campaign, name, failure, scratch, bad_custody=False):
    """Execute real run, execute_profile, reserve, guard, classifier and validators.

    Only source preparation/identity and child execution are substituted. Every
    one of the nine mocked preparation commands goes through guarded_command.
    """
    output = scratch / name
    commands, preparations, fulls = [], [], []
    fixture = failure_log(campaign, failure)

    def child(argv, cwd, env, directory, seconds):
        directory.mkdir(parents=True, exist_ok=True)
        full = directory.name == "full"
        commands.append({"argv": argv, "full": full, "directory": str(directory.relative_to(output))})
        if full:
            state = json.loads((output / "campaign.json").read_text())
            check(name + " attempt persisted before mocked command " + str(len(fulls)), state["fullAttempts"] == len(fulls) + 1)
            check(name + " both preparations before full " + str(len(fulls)), preparations == [p[0] for p in campaign.PROFILES])
            fulls.append(directory.parent.name)
            (directory / "stdout").write_text(fixture)
            (directory / "stderr").write_text("")
        return {"pid": 321, "exitCode": 101 if full else 0, "timedOut": False, "cancelled": None,
            "processGroupEmpty": not (full and bad_custody), "wallSeconds": 0.001, "userSeconds": 0.0,
            "systemSeconds": 0.0, "peakRSSBytes": 0}

    def prepare(arm, algorithm, finite_filter, count, original, target, working, env, out, state, custody):
        check(name + " zero attempts while preparing " + arm, state["fullAttempts"] == 0)
        phase, crate = out / arm, working / arm
        phase.mkdir()
        crate.mkdir()
        for part in ("build", "finite", "harness-control"):
            campaign.guarded_command(custody, ["mocked-" + part, arm], crate, {}, phase / part, 1)
        preparations.append(arm)
        state["preparedProfiles"].append({"name": arm})
        return {"name": arm, "algorithm": algorithm, "source": {}, "record": {"sha256": "pure-fixture"},
            "crate": crate, "childEnv": {}, "phase": phase, "binary": crate / "mocked-binary", "executable": {}}

    with contextlib.ExitStack() as guards:
        guards.enter_context(patch.dict(campaign.os.environ,
            {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}, clear=True))
        guards.enter_context(patch.object(campaign.platform, "system", return_value="Linux"))
        guards.enter_context(patch.object(campaign.signal, "signal"))
        guards.enter_context(patch.object(campaign, "inputs", return_value=({}, b"pure-fixture", {})))
        guards.enter_context(patch.object(campaign, "check", return_value={"candidateGeneratorSHA256": "pure-fixture", "candidateSourceBindings": {}}))
        guards.enter_context(patch.object(campaign, "prepare_profile", side_effect=prepare))
        guards.enter_context(patch.object(campaign, "verify_prepared"))
        guards.enter_context(patch.object(campaign, "unchanged", return_value=True))
        guards.enter_context(patch.object(campaign.base, "command", side_effect=child))
        decision = outcome(lambda: campaign.run(output))
    state = json.loads((output / "campaign.json").read_text())
    result_path = output / campaign.PROFILES[0][0] / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    evidence = {"decision": decision, "campaign": state, "mockedCommands": commands,
        "fullArmNames": fulls, "firstResult": result, "syntheticLogSHA256": digest(fixture.encode()),
        "scope": "pure mocked child commands; actual classifier and campaign control flow; no runtime result"}
    save(HERE / "campaign-evidence" / (name + ".json"), evidence)
    if name == "ordinary-allocation":
        check(name + " closes both diagnostic arms", decision["accepted"] and state["status"] == "comparison-closed"
            and state["fullAttempts"] == 2 and len(commands) == 11 and len(fulls) == 2
            and state["cleanup"]["commandCustody"]["provenClosedCommands"] == 11
            and state["milestoneObservedArms"] == [])
    elif bad_custody:
        check(name + " preserves unresolved custody and scratch", not decision["accepted"]
            and state["status"] == "stopped-unresolved-command-custody" and state["fullAttempts"] == 1
            and len(commands) == 10 and len(fulls) == 1 and not state["cleanup"]["ownedScratchRemoved"]
            and state["cleanup"]["commandCustody"]["provenClosedCommands"] == 9
            and state["cleanup"]["commandCustodyUnresolved"])
    else:
        check(name + " stops after first full command", not decision["accepted"] and state["status"] == "stopped"
            and state["fullAttempts"] == 1 and len(commands) == 10 and len(fulls) == 1
            and not state["profiles"] and state["cleanup"]["commandCustody"]["provenClosedCommands"] == 10
            and state["cleanup"]["ownedScratchRemoved"] and not state["cleanup"]["commandCustodyUnresolved"])
        check(name + " actual classifier retains valid telemetry and cleanup", result["telemetry"]["status"] == "valid"
            and result["consumingCleanup"] and campaign.zero_resources(result))
        check(name + " actual classifier preserves original final failure", campaign.typed_equal(
            campaign.event(result, "final_failure") | {"after_cleanup": None}, result["firstFailure"]["payload"]))
    shutil.rmtree(output)  # All commands above are mocks, including unresolved-custody fixture.
    return {"name": name, "decision": decision, "fullAttempts": state["fullAttempts"],
        "closedCommands": state["cleanup"]["commandCustody"]["provenClosedCommands"], "fullArms": fulls}


def prefix_record(instructions, fuel):
    return {"threshold": instructions, "instructions": instructions, "instruction_fuel": fuel,
        "cache_work": instructions, "execution_work": instructions, "host_calls": 1,
        "elapsed_micros": instructions // 100, "function": 97, "offset": 203}


def prefix_tests(campaign, prior, scratch, result):
    a, b = 25_000_000, 50_000_000
    cases = [
        ("absolute-prefix", [prefix_record(a, 0)], (a, a), False, False),
        ("interval-prefix", [prefix_record(a, 100_000_000), prefix_record(b, 100_000_000)], (b, 100_000_000), False, False),
        ("final-interval", [prefix_record(a, 100_000_000)], (a + 1, 100_000_000), True, False),
        ("empty-final-absolute", [], (1, 0), True, False),
        ("valid-extra-bulk-fuel", [prefix_record(a, 40_000_000), prefix_record(b, 70_000_000)], (b + 10, 70_000_010), True, True),
        ("valid-charge-before-failed-increment", [prefix_record(a, 40_000_000)], (a, 40_000_001), True, True),
        ("valid-empty-owner", [], (0, 0), True, True),
        ("final-instruction-regression", [prefix_record(a, 40_000_000)], (a - 1, 40_000_000), True, False),
        ("final-fuel-regression", [prefix_record(a, 40_000_000)], (a, 39_999_999), True, False),
    ]
    for key in ("instructions", "instruction_fuel"):
        for value in (-1, False, 1 << 64, 1.5, None, "1"):
            pair = {"instructions": 0, "instruction_fuel": 0} | {key: value}
            cases.append(("empty-final-type-" + key + "-" + repr(value), [],
                (pair["instructions"], pair["instruction_fuel"]), True, False))
    evidence = []
    for name, rows, counters, parser_accept, join_accept in cases:
        path = scratch / "prefix.stderr"
        path.write_text("".join("MIXER_PREFIX " + json.dumps(row) + "\n" for row in rows))
        changed = copy.deepcopy(result)
        final = campaign.event(changed, "final_cleanup_usage")
        if rows:
            final.update(rows[-1])
        final.update(instructions=counters[0], instruction_fuel=counters[1])
        parsed = outcome(lambda: campaign.prefix_records(path))
        joined = outcome(lambda: campaign.validate_prefix(changed, {"records": rows}))
        check(name + " parser disposition", parsed["accepted"] is parser_accept)
        check(name + " final-join disposition", joined["accepted"] is join_accept)
        entry = {"name": name, "records": rows, "finalCounters": list(counters), "parser": parsed, "join": joined}
        if name in ("absolute-prefix", "interval-prefix", "final-interval", "empty-final-absolute"):
            entry["originalParser"] = outcome(lambda: prior.prefix_records(path))
            entry["originalJoin"] = outcome(lambda: prior.validate_prefix(changed, {"records": rows}))
            check(name + " original accepts reviewed defect", entry["originalParser"]["accepted"] and entry["originalJoin"]["accepted"])
        evidence.append(entry)
    # Direct interval tests cannot be obscured by threshold or final-domination guards.
    for old, new in (({"instructions": 2, "instruction_fuel": 10}, {"instructions": 1, "instruction_fuel": 10}),
                     ({"instructions": 2, "instruction_fuel": 10}, {"instructions": 3, "instruction_fuel": 9})):
        check("direct monotonic rejection " + repr(new), not outcome(lambda: campaign.validate_instruction_fuel(old, new))["accepted"])
    path.unlink()
    save(HERE / "prefix-evidence.json", {"scope": "synthetic pure-data fixtures", "cases": evidence})
    return len(cases)


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    packets, readset = verify_inputs("before")
    scratch = HERE / "scratch"
    scratch.mkdir()
    old_tempdir, tempfile.tempdir = tempfile.tempdir, str(scratch)
    with contextlib.ExitStack() as guards:
        for method in ("wait4", "waitpid", "wait", "kill", "killpg", "system", "fork", "forkpty", "posix_spawn", "posix_spawnp"):
            if hasattr(os, method):
                guards.enter_context(patch.object(os, method, side_effect=AssertionError("process operation forbidden")))
        guards.enter_context(patch.object(subprocess, "Popen", side_effect=AssertionError("process creation forbidden")))
        campaign = load("independent_corrected_campaign", PACKET / "campaign.py")
        prior = load("independent_prior_campaign", HERE.parent / "swift-execution-architecture-comparison/campaign.py")
        original, artifact, _ = campaign.inputs()
        check("same exact artifact", len(artifact) == 53_777_114 and digest(artifact) == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994")
        del artifact
        for name in campaign.CANDIDATE_FILES:
            check("generator/Rust unchanged " + name, (PACKET / name).read_bytes() == (prior.HERE / name).read_bytes())
        for algorithm, expected in SOURCES.items():
            source = campaign.prepare_source(original, algorithm)
            record, _ = campaign.base.source_record(original, source)
            check("regenerated source closure " + str(algorithm), record["sha256"] == expected)
            control = source["src/experimental_swift_reactor/control.rs"].decode()
            check("original charge before instruction increment " + str(algorithm),
                control.index("self.charge_fuel_with_wasi(1, cursor, wasi)?;") < control.index("self.instructions = self.instructions.checked_add(1)"))
            for marker in ("swift_run_unexpected_capacity", "swift_run_ticket_inventory", "swift_run_owner_exhausted"):
                check("actual producer failure " + marker + " " + str(algorithm), marker in control)
            if algorithm:
                excerpts = {}
                lines = control.splitlines()
                for marker in ("pub(crate) fn instruction_with_wasi", "swift_run_unexpected_capacity", "swift_run_ticket_inventory", "swift_run_owner_exhausted"):
                    index = next(i for i, line in enumerate(lines) if marker in line)
                    excerpts[marker] = {"firstLine": max(1, index - 7), "text": "\n".join(lines[max(0, index - 8):index + 20])}
                save(HERE / "source-assumptions.json", {"sourceSHA256": expected, "controlSHA256": digest(control.encode()), "excerpts": excerpts})
        bounds = campaign.expected_bounds()["run_budget"]
        check("same finite lifetime profile and limits", bounds["instruction_fuel"] == 1_000_000_000
            and bounds["execution_work"] == 8_000_000_000 and bounds["cache_work"] == 768_000_000
            and bounds["deadline_ms"] == 600_000 and bounds["combined_bytes"] == 268_435_456
            and bounds["cache_entries"] == 256 and bounds["active_pins"] == 64
            and campaign.expected_bounds()["wasi_budget"]["deadline_ms"] == 600_000
            and campaign.MAX_FULL_ATTEMPTS == 2 and campaign.MAX_COMMANDS == 11)
        supplied = load("independent_corrected_supplied_tests", PACKET / "test_campaign.py")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            suite = unittest.TextTestRunner(stream=stderr, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(supplied))
        (HERE / "supplied-tests.stdout").write_text(stdout.getvalue())
        (HERE / "supplied-tests.stderr").write_text(stderr.getvalue())
        check("38 supplied pure controls pass independently", suite.wasSuccessful() and suite.testsRun == 38)
        ordinary = {"kind": "Allocation", "code": "swift_execution_allocation", "resource": None,
            "attempted": 160000, "limit": 0, "observed_capacity": None}
        defects = {
            "unexpected-capacity": ordinary | {"code": "swift_run_unexpected_capacity", "resource": "ExactCapacity", "limit": 160000, "observed_capacity": 160002},
            "capacity-code-only": ordinary | {"code": "swift_run_unexpected_capacity"},
            "capacity-resource-only": ordinary | {"resource": "ExactCapacity"},
            "capacity-observation-only": ordinary | {"observed_capacity": 160002},
            "ticket-resource": ordinary | {"kind": "ResourceExhausted", "resource": "TicketInventory"},
            "ticket-code": ordinary | {"kind": "ResourceExhausted", "code": "swift_run_ticket_inventory"},
            "owner-resource": ordinary | {"kind": "ResourceExhausted", "resource": "OwnerIdentity"},
            "owner-code": ordinary | {"kind": "ResourceExhausted", "code": "swift_run_owner_exhausted"},
            "invariant": ordinary | {"kind": "Invariant"},
        }
        campaigns = [independent_campaign(campaign, name, failure, scratch) for name, failure in defects.items()]
        campaigns.append(independent_campaign(campaign, "ordinary-allocation", ordinary, scratch))
        campaigns.append(independent_campaign(campaign, "custody-missing", ordinary, scratch, bad_custody=True))
        path = scratch / "ordinary.stdout"
        path.write_text(failure_log(campaign, ordinary))
        result = campaign.base.classify(path, {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})
        prefix_cases = prefix_tests(campaign, prior, scratch, result)
        path.unlink()
    tempfile.tempdir = old_tempdir
    scratch.rmdir()
    verify_inputs("after")
    save(HERE / "checks.json", {"passed": True, "count": len(CHECKS), "checks": CHECKS})
    save(HERE / "receipt.json", {"schema": 1, "decision": "source-qualified-accept", "startedAtUTC": started,
        "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/swift-execution-architecture-correction-independent/review.py",
        "python": platform.python_version(), "pythonExecutable": sys.executable,
        "basisCheckoutRevision": readset["checkoutRevisionAtPreparation"], "reviewedReadsetSHA256": READSET_SHA,
        "sourceTreeDigestScope": "frozen correction readset and packet seals, not concurrently edited canonical tree",
        "packetsVerifiedBeforeAndAfter": packets, "generatedSourceSHA256": {str(k): v for k, v in SOURCES.items()},
        "independentChecks": len(CHECKS), "suppliedTests": suite.testsRun, "prefixCases": prefix_cases,
        "mockedCampaignCases": campaigns, "guards": {"audit": "deny process creation, sockets, signals and writes outside this packet",
            "patches": "deny Popen, wait/waitpid/wait4, kill/killpg, system/fork/forkpty/posix_spawn"},
        "newActualCompilations": 0, "newActualFiniteOrHarnessRuns": 0, "newActualFullAttempts": 0,
        "commitPushDispatch": False, "ownedScratchRemoved": not scratch.exists(),
        "heldGroupsNotProbed": [20745, 20770, 20780, 20817, 20842, 20851, 20866],
        "pending": ["Rust compilation", "actual finite/harness execution", "compiled envelope", "full runtime parity",
            "real command custody and cleanup", "performance", "native/mobile", "published FieldLog", "signed OTA", "GA"]})
    print(f"Source-qualified accept: {len(CHECKS)} independent checks; 38 supplied tests; {len(campaigns)} mocked campaign cases; {prefix_cases} prefix cases. No runtime attempts.")


if __name__ == "__main__":
    sys.addaudithook(audit)
    main()
