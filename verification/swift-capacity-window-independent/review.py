#!/usr/bin/env python3
"""Independent source and pure negative review. Never starts a child or compiler."""
import ast
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
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CANDIDATE = HERE.parent / "swift-cachework-128-experiment"
EXPECTED_SEAL = "dce182dba6c4e4bf38738b486276596c7b0cbc17c798e8780ebd19287bced0d0"
EXPECTED_SOURCES = ("8a3759c514cc342c37d89df8ced0525f4c3619f774f9cbbb9a7d3bdf856a331d",
                    "09ac825f108574f626838e0fc54628adb5ed70fa8d8871b527bc1bba4922c0ee")
READS, CHECKS, DENIALS = set(), [], []
START = time.monotonic()
sys.dont_write_bytecode = True


def sha(data):
    return hashlib.sha256(data).hexdigest()


def denied(*args, **kwargs):
    DENIALS.append("explicit process/network/signal/wait guard")
    raise AssertionError("independent review forbids child/socket/signal/wait")


def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "pty.")) or event in {
        "os.system", "os.fork", "os.forkpty", "os.posix_spawn", "os.exec", "os.kill", "os.killpg", "os.chdir"
    }:
        denied()
    if event == "open":
        name, mode, flags = args
        writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
            isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        if isinstance(name, (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(name)).resolve()
            if writing and not path.is_relative_to(HERE):
                raise AssertionError("independent review cannot write outside its lane")
            if not writing and path.is_relative_to(ROOT) and not path.is_relative_to(HERE):
                READS.add(path)
        elif writing:
            raise AssertionError("unowned writable descriptor forbidden")
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.rename", "os.link", "os.symlink"}:
        path = Path(os.fsdecode(args[0]))
        # The only fd-relative cleanup is tempfile/shutil's owned scratch tree.
        local_cleanup = event in {"os.remove", "os.rmdir"} and len(args) > 1 and isinstance(args[1], int) and args[1] >= 0 and len(path.parts) == 1
        if not local_cleanup and not path.resolve().is_relative_to(HERE):
            raise AssertionError("out-of-lane filesystem mutation forbidden")
        if event in {"os.rename", "os.link", "os.symlink"} and not Path(os.fsdecode(args[1])).resolve().is_relative_to(HERE):
            raise AssertionError("out-of-lane mutation destination forbidden")


sys.addaudithook(audit)
for owner, names in (
    (subprocess, ("Popen",)),
    (socket, ("socket", "create_connection", "getaddrinfo")),
    (signal, ("signal", "raise_signal", "pthread_kill", "alarm", "setitimer")),
    (time, ("sleep",)),
    (os, ("system", "fork", "forkpty", "posix_spawn", "posix_spawnp", "execv", "execve", "kill", "killpg", "wait", "waitpid", "wait3", "wait4", "popen")),
):
    for name in names:
        if hasattr(owner, name):
            setattr(owner, name, denied)


def record(data):
    return {"bytes": len(data), "sha256": sha(data)}


def save(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def check(name, truth):
    assert time.monotonic() - START < 60, "review pure work exceeded finite 60-second bound"
    CHECKS.append({"name": name, "passed": bool(truth)})
    assert truth, name


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_packet():
    raw = (CANDIDATE / "seal.json").read_bytes()
    check("exact root-designated frozen candidate seal", sha(raw) == EXPECTED_SEAL)
    seal = json.loads(raw)
    check("frozen inventory count and byte total", len(seal["files"]) == seal["filesCount"] == 29
        and sum(row["bytes"] for row in seal["files"].values()) == seal["totalBytes"] == 483719)
    for name, expected in seal["files"].items():
        assert record((CANDIDATE / name).read_bytes()) == expected, name
    check("all 29 frozen candidate members match", True)
    return seal


frozen_packet()
producer = load("independent_loaded_producer_controls", CANDIDATE / "test_campaign.py")
campaign = producer.campaign
candidate = campaign.candidate_module()
original, artifact, bindings = campaign.inputs()
executed = candidate.prior.parameterize(original, True)
sources = [campaign.prepare_source(original, value) for value in (False, True)]
proposal = json.loads((CANDIDATE / "proposal.json").read_bytes())


class IndependentControls(unittest.TestCase):
    def test_operation_guards_block_before_effect(self):
        for operation in (subprocess.Popen, socket.socket, os.killpg, os.waitpid, signal.signal, time.sleep):
            with self.assertRaisesRegex(AssertionError, "forbids"):
                operation("denied-negative-control")

    def test_actual_oracle_validator_capabilities_owner_and_clock_sources_unchanged(self):
        changed = {"src/experimental/cache/mod.rs", "src/experimental_swift_reactor/cache.rs",
            "src/experimental_swift_reactor/cache_tests.rs", "src/experimental_swift_reactor/control.rs",
            "src/experimental_swift_reactor/control_tests.rs"}
        for source in sources:
            self.assertEqual(set(source), set(executed))
            self.assertTrue(all(source[name] == executed[name] for name in source if name not in changed))
            self.assertEqual(source["src/experimental_swift_reactor/campaign_harness.rs"], (campaign.base.INPUTS / "harness.rs").read_bytes())
        self.assertEqual((len(artifact), sha(artifact)), (53777114, campaign.base.ARTIFACT_HASH))

    def test_exact_source_hashes_and_proposal_bindings(self):
        self.assertEqual([campaign.base.source_record(original, source)[0]["sha256"] for source in sources], list(EXPECTED_SOURCES))
        for item in proposal["profiles"]:
            self.assertTrue(campaign.typed_equal(item["bounds"], campaign.expected_bounds(item["capacity512"])))
        for name, expected in proposal["sourceArtifacts"].items():
            self.assertEqual(record((CANDIDATE / name).read_bytes()), expected)

    def test_only_numerical_defaults_and_observer_thresholds_change_accounting_source(self):
        for selected, source in zip((False, True), sources):
            raw = source["src/experimental_swift_reactor/control.rs"]
            for before, after in ((b"4_000_000_000", b"768_000_000"), (b"2_000_000_000", b"1_000_000_000"),
                (b"16_000_000_000", b"8_000_000_000")):
                self.assertEqual(raw.count(before), 1)
                raw = raw.replace(before, after)
            now = " | ".join(f"{v:_}" for v in campaign.PREFIX_THRESHOLDS).encode()
            self.assertEqual(raw.count(now), 1)
            raw = raw.replace(now, b"25_000_000 | 50_000_000 | 100_000_000")
            if selected:
                raw = raw.replace(b"MAX_RESERVATION_TICKETS: usize = 534;", b"MAX_RESERVATION_TICKETS: usize = 278;")
                raw = raw.replace(b"cache_entries: 512,", b"cache_entries: 256,")
            self.assertEqual(raw, executed["src/experimental_swift_reactor/control.rs"])

    def test_scalar_profile_difference_is_exact_and_all_other_dimensions_identical(self):
        baseline = candidate.prior.expected_bounds()
        for selected in (False, True):
            proposed = campaign.expected_bounds(selected)
            delta = {key: value for key, value in proposed["run_budget"].items() if value != baseline["run_budget"][key]}
            wanted = {"cache_work": 4_000_000_000, "instruction_fuel": 2_000_000_000, "execution_work": 16_000_000_000}
            if selected:
                wanted["cache_entries"] = 512
            self.assertEqual(delta, wanted)
            for key in ("validation_budget", "wasi_budget", "wasi_grants"):
                self.assertEqual(proposed[key], baseline[key])

    def test_dense_walks_and_size_derived_storage_are_unchanged(self):
        small, large = sources
        for name, before, after in (
            ("src/experimental/cache/mod.rs", b"MAX_ENTRIES: usize = 512;", b"MAX_ENTRIES: usize = 256;"),
            ("src/experimental_swift_reactor/cache.rs", b"RESIDENT_LINKS: usize = 512;", b"RESIDENT_LINKS: usize = 256;"),
        ):
            self.assertEqual(large[name].count(before), 1)
            self.assertEqual(large[name].replace(before, after), small[name])
            self.assertEqual(small[name], executed[name])

    def test_expanded_prefix_late_thresholds_and_scalar_bounds(self):
        helper = producer.CampaignTests()
        rows = [helper.prefix(t) for t in campaign.PREFIX_THRESHOLDS]
        parsed, raw = helper.parse_prefix(rows)
        self.assertEqual(len(parsed["records"]), 10)
        self.assertLess(len(raw), 8192)
        for field, maximum in (("instruction_fuel", 2_000_000_000), ("cache_work", 4_000_000_000), ("execution_work", 16_000_000_000)):
            valid = copy.deepcopy(rows)
            valid[-1][field] = maximum
            helper.parse_prefix(valid)
            valid[-1][field] = maximum + 1
            with self.assertRaisesRegex(RuntimeError, "selected bounds"):
                helper.parse_prefix(valid)
        for changed in (rows[:-1] + [rows[-2]], rows + [rows[-1]], [*rows[:8], rows[9], rows[8]]):
            with self.assertRaises(RuntimeError):
                helper.parse_prefix(changed)

    def test_conservative_geometry_uses_category_ceiling_once(self):
        helper = producer.CampaignTests()
        for selected in (False, True):
            fixture = helper.geometry_fixture(selected)
            parsed = helper.parse_geometry(fixture, selected)
            actual = parsed["plan"]["conservative_combined"]
            # Adding already-enclosed frame/pin payloads is a formula mismatch.
            for double_counted in (16, 128 * 16, 128 * 128):
                with self.assertRaisesRegex(RuntimeError, "formula mismatch"):
                    helper.parse_geometry(fixture.replace(f"conservative_combined={actual}", f"conservative_combined={actual + double_counted}"), selected)
            # A finite geometry at the ceiling is admissible; +1 cannot be rescued.
            shift = 268435456 - actual
            at_limit = fixture.replace("floor=1000", f"floor={1000 + shift}").replace(f"conservative_combined={actual}", "conservative_combined=268435456")
            self.assertEqual(helper.parse_geometry(at_limit, selected)["recomputedConservativeCombined"], 268435456)
            with self.assertRaisesRegex(RuntimeError, "unchanged combined envelope"):
                helper.parse_geometry(at_limit.replace("conservative_combined=268435456", "conservative_combined=268435457"), selected)

    def test_actual_second_geometry_failure_stops_run_before_either_full(self):
        helper = producer.CampaignTests()
        calls = []
        def prepare(name, selected, finite_filter, count, original, target, scratch, env, output, state, custody):
            calls.append(name)
            self.assertEqual(state["fullAttempts"], 0)
            fixture = helper.geometry_fixture(selected)
            if selected:
                parsed = helper.parse_geometry(fixture, True)
                fixture = fixture.replace(f"conservative_combined={parsed['plan']['conservative_combined']}", "conservative_combined=268435457")
            helper.parse_geometry(fixture, selected)
            state["preparedProfiles"].append({"name": name})
            custody["provenClosedCommands"] += 3
            return {"profile": (name, selected, finite_filter, count)}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "campaign"
            full = Mock(side_effect=AssertionError("full must not be called"))
            with self.assertRaisesRegex(RuntimeError, "unchanged combined envelope"):
                helper.remote_run(output, full, prepare)
            full.assert_not_called()
            result = json.loads((output / "campaign.json").read_bytes())
            self.assertEqual(result["fullAttempts"], 0)
            self.assertNotIn("preparationGate", result)
            self.assertTrue(result["cleanup"]["ownedScratchRemoved"])
            self.assertEqual(calls, [p[0] for p in campaign.PROFILES])

    def test_preserved_failure_and_cleanup_required_under_both_profiles(self):
        helper = producer.CampaignTests()
        for selected in (False, True):
            result, row = helper.failure_fixture()
            for entry in result["events"]:
                if entry["event"] == "run_budget":
                    entry["payload"]["cache_entries"] = 512 if selected else 256
            campaign.validate_result(result, row, selected)
            for event_name, key, value in (("final_failure", "limit", 1), ("final_cleanup_usage", "cleanup_invariant", "lost owner")):
                bad = copy.deepcopy(result)
                campaign.event(bad, event_name)[key] = value
                with self.assertRaises(RuntimeError):
                    campaign.validate_result(bad, row, selected)
            bad = copy.deepcopy(result)
            campaign.event(bad, "final_cleanup_usage")["reservations"]["live_tickets"] = 1
            with self.assertRaisesRegex(RuntimeError, "cleanup unresolved"):
                campaign.validate_result(bad, row, selected)

    def test_source_negative_controls_exercised_by_selected_finite_filter(self):
        for source in sources:
            methods = []
            for name, data in source.items():
                for line in data.decode().splitlines() if name.endswith(".rs") else []:
                    if line.startswith("fn framepin_campaign_"):
                        methods.append(line)
            self.assertEqual(len(methods), 12)
            text = source["src/experimental_swift_reactor/control_tests.rs"].decode()
            for helper in ("all_seventeen_dimensions_reject_widening_without_allocation_and_drop_real_proof",
                "zero_is_real_in_every_budget_dimension", "init_and_repeated_call_counters_accumulate_and_cannot_refill",
                "work_fuel_host_and_live_overflow_fail_closed_without_counter_commit"):
                self.assertIn(f"fn {helper}(", text)
                self.assertIn(helper + "();", text)
            self.assertIn("(n + 1) as u16", source["src/experimental_swift_reactor/cache_tests.rs"].decode())

    def test_attribution_arithmetic_does_not_imply_timing_or_completion(self):
        evidence = json.loads((CANDIDATE / "attribution-summary.json").read_bytes())
        for arm in evidence["arms"]:
            self.assertEqual(arm["completedDecodes"] - arm["distinctDecodedFunctions"], arm["repeatedCompletedDecodes"])
            self.assertAlmostEqual(arm["buildPercentOfCacheCredits"], 100 * arm["buildCredits"] / arm["cacheWork"])
            for metric in ("cacheWork", "executionWork", "instructionFuel", "instructions"):
                self.assertAlmostEqual(arm["linearExtrapolationTo600SecondsNotBound"][metric], arm[metric] * 600000000 / arm["elapsedMicros"], delta=0.0001)
        self.assertNotEqual(evidence["arms"][0]["instructions"], evidence["arms"][1]["instructions"])
        self.assertIn("no paired workload or speedup comparison", evidence["scope"])

    def test_attribution_matches_exact_bounded_raw_archive_members(self):
        evidence = json.loads((CANDIDATE / "attribution-summary.json").read_bytes())
        basis = ROOT / "verification/github-delivery-frame-pin-128/ci-review"
        self.assertEqual(sha((basis / "seal.json").read_bytes()), "3161abdae5f7ee09a0bd67062d3ae393af17bdb99a5859b20efb3ef404affbb8")
        archive = (basis / "artifact.zip").read_bytes()
        self.assertEqual(len(archive), 164027)
        self.assertEqual(sha(archive), evidence["sourceArtifactSHA256"])
        with zipfile.ZipFile(io.BytesIO(archive)) as members:
            self.assertEqual(len(members.infolist()), 67)
            for arm in evidence["arms"]:
                info = members.getinfo(arm["name"] + "/result.json")
                self.assertLess(info.file_size, 60000)
                raw = members.read(info)
                self.assertEqual(sha(raw), arm["resultMemberSHA256"])
                result = json.loads(raw)
                self.assertEqual(result["telemetry"]["status"], "valid")
                payload = next(row["payload"] for row in result["telemetry"]["snapshots"] if row["lifecycle"] == "before_cleanup")
                for key, field in (("completedDecodes", "completed"), ("distinctDecodedFunctions", "distinct"), ("repeatedCompletedDecodes", "repeated"), ("chargedSiteCredits", "credits")):
                    self.assertEqual(arm[key], payload[field])
                self.assertEqual(arm["buildCredits"], sum(payload["build_credits"]))
                self.assertEqual(arm["repeatedBuildCredits"], payload["build_credits"][1])
                final = campaign.event(result, "final_cleanup_usage")
                for key, field in (("cacheWork", "cache_work"), ("executionWork", "execution_work"), ("instructionFuel", "instruction_fuel"), ("instructions", "instructions"), ("elapsedMicros", "elapsed_micros")):
                    self.assertEqual(arm[key], final[field])
                self.assertEqual(result["completeGuestObservations"], [])
                self.assertFalse(result["hostFeasibility"])


def main():
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    scratch = HERE / "scratch"
    scratch.mkdir(exist_ok=False)
    tempfile.tempdir = str(scratch)
    log = io.StringIO()
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(producer),
                               unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)))
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (HERE / "pure-tests.log").write_text(log.getvalue())
    scratch.rmdir()
    check("43 producer pure controls plus 13 independent methods", result.wasSuccessful() and result.testsRun == 56)
    frozen_packet()
    excerpts = []
    for name in ("src/experimental_swift_reactor/cache.rs", "src/experimental/cache/mod.rs", "src/experimental_swift_reactor/cache_tests.rs", "src/experimental_swift_reactor/control.rs"):
        lines = sources[1][name].decode().splitlines()
        selected = set()
        for i, line in enumerate(lines):
            if any(word in line for word in ("RESIDENT_LINKS", "MAX_ENTRIES", "conservative_combined", "category_ceiling_sum", "deadline_ms", "fn cache_header_bytes", "fn cache_operation_bytes")):
                selected.update(range(max(0, i - 3), min(len(lines), i + 7)))
        excerpts.append(name + "\n" + "\n".join(f"{i + 1}: {lines[i]}" for i in sorted(selected)))
    (HERE / "source-excerpts.txt").write_text("\n\n".join(excerpts) + "\n")
    inputs = {str(path.relative_to(ROOT)): record(path.read_bytes()) for path in sorted(READS) if path.is_file()}
    save("readset.json", inputs)
    save("checks.json", CHECKS)
    save("receipt.json", {"schema": 1, "command": "python3 -B verification/swift-capacity-window-independent/review.py",
        "python": platform.python_version(), "pythonExecutable": sys.executable, "startedAtUTC": started,
        "completedAtUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(), "durationSeconds": time.monotonic() - START,
        "candidateSealSHA256": EXPECTED_SEAL, "sourceClosures": list(EXPECTED_SOURCES),
        "sourceBasisHead": "295f3f18a53459449f22253687bd2d0b2c09a0ed", "sourceBasisTree": "294faafd3be568208a366ea66f85c5538a376ffa",
        "readsetSHA256": sha((HERE / "readset.json").read_bytes()), "allPureChecksPassed": result.wasSuccessful(),
        "producerPureMethods": 43, "independentMethods": 13, "totalPureMethods": result.testsRun,
        "guardNegativeDenials": len(DENIALS), "scratchRemoved": not scratch.exists(),
        "actualChildSocketSignalWaitOrInventoryEffects": 0, "actualCompilerFiniteHarnessFullRuns": 0,
        "sourceAcceptanceOnly": True, "productionOrNativeOrGAAcceptance": False,
        "holdsUntouched": ["20745", "20770", "20780", "20817", "20842", "20851", "20866", "unknown FieldLog fetch", "Unit A", "broad hosted", "native/UI/capture"]})
    print(json.dumps({"testsRun": result.testsRun, "success": result.wasSuccessful(), "checks": len(CHECKS), "durationSeconds": time.monotonic() - START}))
    assert result.wasSuccessful()


if __name__ == "__main__":
    main()
