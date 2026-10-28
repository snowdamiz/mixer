"""Pure source/data and mocked decision checks; no child/compiler/guest/custody probes."""
import copy
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("deadline_campaign", HERE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.artifact, cls.bindings = campaign.inputs()

    def failure_fixture(self):
        # Data mutation only: an eligibility fixture, never a fabricated run receipt.
        result = campaign.historical()
        for e in result["events"]:
            if e["event"] in campaign.expected_bounds(64_000_000):
                e["payload"] = campaign.expected_bounds(64_000_000)[e["event"]]
        row = {"exitCode": 101, "timedOut": False, "processGroupEmpty": True, "cancelled": None}
        campaign.validate_result(result, row, 64_000_000)
        return result, row

    def test_full_artifact_and_sealed_v1_inputs_reused(self):
        self.assertEqual(len(self.artifact), 53_777_114)
        self.assertEqual(campaign.sha(self.artifact), campaign.base.ARTIFACT_HASH)
        self.assertFalse((HERE / "inputs").exists(), "reuse immutable assets without large copies")
        self.assertEqual(len(json.loads((campaign.base.INPUTS / "native-observation.json").read_text())), 11)
        record, _ = campaign.base.source_record(self.original, campaign.base.parameterize(self.original, 256, 64_000_000))
        self.assertEqual(record["sha256"], "204c62d871b05b4b50a6fb7e55ed4251f3c5b664299f7bd410fbdee05e32f05c")

    def test_only_two_deadlines_differ_from_same_v1_capacity_work_profile(self):
        for _, work in campaign.PROFILES:
            v1 = campaign.base.parameterize(self.original, 256, work)
            v2 = campaign.parameterize(self.original, work)
            self.assertEqual({n for n in v2 if v2[n] != v1[n]}, set(campaign.DEADLINE_FILES))
            for n in campaign.DEADLINE_FILES:
                self.assertEqual(v2[n].replace(b"deadline_ms: 60_000,", b"deadline_ms: 30_000,"), v1[n])
            self.assertEqual(v2["src/experimental_swift_reactor/campaign_harness.rs"], (campaign.base.INPUTS / "harness.rs").read_bytes())

    def test_complete_bounds_preserve_all_other_limits_and_grants(self):
        historical = campaign.historical()
        for _, work in campaign.PROFILES:
            bounds = campaign.expected_bounds(work)
            normalized = copy.deepcopy(bounds)
            normalized["run_budget"].update(cache_entries=64, cache_work=64_000_000, deadline_ms=30_000)
            normalized["wasi_budget"]["deadline_ms"] = 30_000
            self.assertEqual(normalized, {n: campaign.event(historical, n) for n in normalized})
            self.assertEqual(bounds["validation_budget"]["deadline_ms"], 120_000)
            self.assertEqual(bounds["run_budget"]["instruction_fuel"], 100_000_000)
            self.assertEqual(bounds["run_budget"]["memory_pages"] * 65536, 48 * 1024 * 1024)

    def test_changed_deadline_anchor_and_unselected_profile_rejected(self):
        source = dict(self.original)
        name = campaign.DEADLINE_FILES[1]
        source[name] = source[name].replace(b"deadline_ms: 30_000,", b"deadline_ms: 31_000,")
        with self.assertRaisesRegex(RuntimeError, "changed source anchor"):
            campaign.parameterize(source, 64_000_000)
        with self.assertRaisesRegex(RuntimeError, "unsupported v2 profile"):
            campaign.parameterize(self.original, 256_000_000)

    def test_original_failure_and_resource_emptiness_are_separate(self):
        result, row = self.failure_fixture()
        self.assertTrue(result["consumingCleanup"])
        self.assertTrue(result["originalFinalFailurePreserved"])
        self.assertFalse(campaign.event(result, "cleanup_empty"))
        self.assertTrue(campaign.conditional_second(result, row, True))
        self.assertFalse(result["hostFeasibility"])

    def test_conditional_trial_rejects_every_other_first_limit(self):
        result, row = self.failure_fixture()
        for field, value in (("kind", "Deadline"), ("resource", "InstructionFuel"), ("resource", "ExecutionWork"),
                             ("kind", "Invariant"), ("resource", "CacheBytes"), ("limit", 128_000_000),
                             ("attempted", 64_000_002), ("code", "changed")):
            variant = copy.deepcopy(result)
            variant["firstFailure"]["payload"][field] = value
            self.assertFalse(campaign.conditional_second(variant, row, True), (field, value))
        for field, value in (("hostFeasibility", True), ("complete", True), ("consumingCleanup", False),
                             ("originalFinalFailurePreserved", False), ("telemetry", {"status": "invalid"}), ("actualBounds", {})):
            self.assertFalse(campaign.conditional_second(result | {field: value}, row, True), field)
        for field, value in (("timedOut", True), ("processGroupEmpty", False), ("exitCode", 0), ("cancelled", "SIGTERM")):
            self.assertFalse(campaign.conditional_second(result, row | {field: value}, True), field)
        self.assertFalse(campaign.conditional_second(result, row, False))

    def test_actual_bound_changes_and_failure_replacement_rejected(self):
        result, row = self.failure_fixture()
        for name, key in (("run_budget", "instruction_fuel"), ("run_budget", "deadline_ms"),
                          ("wasi_budget", "deadline_ms"), ("validation_budget", "deadline_ms"), ("wasi_grants", "stdout")):
            variant = copy.deepcopy(result)
            campaign.event(variant, name)[key] = 1
            with self.assertRaisesRegex(RuntimeError, "actual budgets/grants"):
                campaign.validate_result(variant, row, 64_000_000)
        variant = copy.deepcopy(result)
        campaign.event(variant, "final_failure")["resource"] = "InstructionFuel"
        with self.assertRaisesRegex(RuntimeError, "first failure not preserved"):
            campaign.validate_result(variant, row, 64_000_000)

    def test_nonzero_cleanup_and_duplicate_bound_rejected(self):
        result, row = self.failure_fixture()
        variant = copy.deepcopy(result)
        variant["consumingCleanup"] = False
        with self.assertRaisesRegex(RuntimeError, "cleanup unresolved"):
            campaign.validate_result(variant, row, 64_000_000)
        variant = copy.deepcopy(result)
        variant["events"].append({"event": "run_budget", "payload": campaign.event(variant, "run_budget")})
        with self.assertRaisesRegex(RuntimeError, "duplicate event"):
            campaign.validate_result(variant, row, 64_000_000)

    def test_local_run_and_ci_rerun_declined_before_output_or_child(self):
        for env in ({}, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "2"}):
            with tempfile.TemporaryDirectory() as tmp, patch.dict(campaign.os.environ, env, clear=True), \
                    patch.object(campaign.platform, "system", return_value="Linux"), \
                    patch.object(campaign.base.subprocess, "Popen", side_effect=AssertionError("no child permitted")):
                out = Path(tmp) / "absent"
                with self.assertRaisesRegex(RuntimeError, "local execution and rerun remain held"):
                    campaign.run(out)
                self.assertFalse(out.exists())

    def test_aggregate_admission_reserves_cleanup_and_cancellation_stops(self):
        with patch.object(campaign.base, "COMMAND_DEADLINE", 1000), patch.object(campaign.base.time, "monotonic", return_value=779):
            campaign.base.ensure_command_budget(200)
        with patch.object(campaign.base, "COMMAND_DEADLINE", 1000), patch.object(campaign.base.time, "monotonic", return_value=780):
            with self.assertRaisesRegex(RuntimeError, "aggregate campaign deadline"):
                campaign.base.ensure_command_budget(200)
        with patch.object(campaign.base, "CANCEL_REQUESTED", "SIGTERM"):
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                campaign.base.ensure_command_budget(200)

    def test_orchestration_attempts_once_or_twice_without_primary_replay(self):
        result, row = self.failure_fixture()
        for eligible in (False, True):
            invoked = []
            def fake_profile(name, work, original, target_input, scratch, env, output, record, custody):
                invoked.append((name, work))
                record["fullAttempts"] += 1
                record["profiles"].append({"name": name, "fixtureOnly": True})
                return result, row, True
            with tempfile.TemporaryDirectory() as tmp, \
                    patch.dict(campaign.os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}, clear=True), \
                    patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                    patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), patch.object(campaign, "check"), \
                    patch.object(campaign.base, "command", return_value={"pid": 123, "exitCode": 0, "timedOut": False, "processGroupEmpty": True}), \
                    patch.object(campaign, "run_profile", side_effect=fake_profile), \
                    patch.object(campaign, "conditional_second", return_value=eligible), \
                    patch.object(campaign.base.subprocess, "Popen", side_effect=AssertionError("no child permitted")):
                out = Path(tmp) / "fixture-output"
                campaign.run(out)
                saved = json.loads((out / "campaign.json").read_text())
                self.assertEqual(invoked, list(campaign.PROFILES[:2 if eligible else 1]))
                self.assertEqual(saved["fullAttempts"], len(invoked))
                self.assertTrue(saved["cleanup"]["ownedScratchRemoved"])
                self.assertEqual(saved["status"], "milestone-unmet-campaign-closed")
                self.assertIn("architecture comparison", saved["nextDecision"])

    def test_every_command_site_uses_the_custody_guard(self):
        tree = ast.parse((HERE / "campaign.py").read_text())
        calls = [(f.name, n) for f in tree.body if isinstance(f, ast.FunctionDef)
                 for n in ast.walk(f) if isinstance(n, ast.Call)]
        direct = [name for name, n in calls if isinstance(n.func, ast.Attribute)
                  and isinstance(n.func.value, ast.Name) and n.func.value.id == "base" and n.func.attr == "command"]
        guarded = [name for name, n in calls if isinstance(n.func, ast.Name) and n.func.id == "guarded_command"]
        self.assertEqual(direct, ["guarded_command"])
        self.assertEqual(guarded.count("run_profile"), 3)
        self.assertEqual(guarded.count("run"), 1)

    def test_missing_or_invalid_terminal_proof_stays_pending_and_blocks_next_command(self):
        good = {"pid": 123, "exitCode": 0, "processGroupEmpty": True}
        for bad in (None, {}, good | {"exitCode": -999}, good | {"exitCode": True},
                    good | {"exitCode": 256}, good | {"pid": 0}, good | {"pid": True},
                    good | {"processGroupEmpty": False}, good | {"processGroupEmpty": 1},
                    {"pid": 123, "exitCode": 0}):
            with self.subTest(row=bad), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                custody = {"recordPath": str(path / "custody.json"), "pendingCommand": None, "provenClosedCommands": 0}
                with patch.object(campaign.base, "command", return_value=bad) as helper:
                    with self.assertRaisesRegex(RuntimeError, "proof missing"):
                        campaign.guarded_command(custody, ["fixture"], path, {}, path / "command", 1)
                    self.assertIsNotNone(custody["pendingCommand"])
                    with self.assertRaisesRegex(RuntimeError, "previous command custody unresolved"):
                        campaign.guarded_command(custody, ["forbidden next"], path, {}, path / "next", 1)
                    self.assertEqual(helper.call_count, 1)
                self.assertIsNotNone(json.loads((path / "custody.json").read_text())["pendingCommand"])

    def test_proven_reaped_exit_and_group_absence_clear_pending(self):
        for status in (0, 101, -9):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                custody = {"recordPath": str(path / "custody.json"), "pendingCommand": None, "provenClosedCommands": 0}
                returned = {"pid": 123, "exitCode": status, "processGroupEmpty": True}
                def helper(*args):
                    self.assertIsNotNone(custody["pendingCommand"])
                    self.assertIsNotNone(json.loads((path / "custody.json").read_text())["pendingCommand"])
                    return returned
                with patch.object(campaign.base, "command", side_effect=helper):
                    self.assertEqual(campaign.guarded_command(custody, ["fixture"], path, {}, path / "command", 1), returned)
                self.assertIsNone(custody["pendingCommand"])
                self.assertEqual(custody["provenClosedCommands"], 1)
                self.assertIsNone(json.loads((path / "custody.json").read_text())["pendingCommand"])

    def test_inherited_exception_after_mock_spawn_preserves_scratch_and_stops(self):
        # Real inherited helper logic, but every process operation is mocked.
        for fault in ("post-spawn-receipt", "wait4"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "fixture-output"
                child = unittest.mock.Mock(pid=12345)
                def fail_save(path, value):
                    if fault == "post-spawn-receipt" and "pid" in value:
                        raise OSError("injected receipt write failure")
                    campaign.save(path, value)
                error = "injected receipt write failure" if fault == "post-spawn-receipt" else "injected arbitrary wait4 failure"
                with patch.dict(campaign.os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}, clear=True), \
                        patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                        patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), patch.object(campaign, "check"), \
                        patch.object(campaign.base, "save", side_effect=fail_save), \
                        patch.object(campaign.base.subprocess, "Popen", return_value=child) as spawn, \
                        patch.object(campaign.base.os, "wait4", side_effect=OSError("injected arbitrary wait4 failure")), \
                        patch.object(campaign.base.os, "killpg", side_effect=AssertionError("no process probe allowed")), \
                        patch.object(campaign, "run_profile", side_effect=AssertionError("no subsequent attempt")) as profile:
                    with self.assertRaisesRegex(OSError, error):
                        campaign.run(out)
                saved = json.loads((out / "campaign.json").read_text())
                self.assertEqual(spawn.call_count, 1)
                self.assertEqual(profile.call_count, 0)
                self.assertTrue((out / "scratch/fieldlog-reactor.wasm").exists())
                self.assertEqual(saved["fullAttempts"], 0)
                self.assertTrue(saved["cleanup"]["commandCustodyUnresolved"])
                self.assertFalse(saved["cleanup"]["ownedScratchRemoved"])
                self.assertEqual(saved["status"], "stopped-unresolved-command-custody")
                self.assertIsNotNone(json.loads((out / "custody.json").read_text())["pendingCommand"])

    def test_bad_returned_proof_preserves_scratch_in_run_finally(self):
        for row in ({"pid": 123, "exitCode": -999, "processGroupEmpty": True},
                    {"pid": 123, "exitCode": 0}, {"pid": 123, "exitCode": 0, "processGroupEmpty": False}):
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "fixture-output"
                with patch.dict(campaign.os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}, clear=True), \
                        patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                        patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), patch.object(campaign, "check"), \
                        patch.object(campaign.base, "command", return_value=row) as helper, \
                        patch.object(campaign.base.subprocess, "Popen", side_effect=AssertionError("no child allowed")):
                    with self.assertRaisesRegex(RuntimeError, "proof missing"):
                        campaign.run(out)
                saved = json.loads((out / "campaign.json").read_text())
                self.assertEqual(helper.call_count, 1)
                self.assertTrue((out / "scratch").exists())
                self.assertTrue(saved["cleanup"]["commandCustodyUnresolved"])

    def test_proven_closure_allows_scratch_cleanup_after_later_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fixture-output"
            with patch.dict(campaign.os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}, clear=True), \
                    patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                    patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), patch.object(campaign, "check"), \
                    patch.object(campaign.base, "command", return_value={"pid": 123, "exitCode": 0, "timedOut": False, "processGroupEmpty": True}), \
                    patch.object(campaign, "run_profile", side_effect=OSError("later data failure")), \
                    patch.object(campaign.base.subprocess, "Popen", side_effect=AssertionError("no child allowed")):
                with self.assertRaisesRegex(OSError, "later data failure"):
                    campaign.run(out)
            saved = json.loads((out / "campaign.json").read_text())
            self.assertFalse((out / "scratch").exists())
            self.assertFalse(saved["cleanup"]["commandCustodyUnresolved"])
            self.assertEqual(saved["cleanup"]["commandCustody"]["provenClosedCommands"], 3)


if __name__ == "__main__":
    unittest.main()
