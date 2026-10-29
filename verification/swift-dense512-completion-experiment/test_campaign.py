"""Pure rejection and mocked orchestration tests; no real child or VM runs."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


campaign = load("completion_campaign_tests", HERE / "campaign.py")
prior_tests = load("closed_window_safety_tests", HERE.parent / "swift-cachework-128-experiment/test_campaign.py")
prior_tests.campaign = campaign
prior_tests.HERE = HERE
REMOTE_ENV = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1",
    "MIXER_DENSE512_COMPLETION_SELECTION": "dense512-completion-v1"}
prior_tests.REMOTE_ENV = REMOTE_ENV


class CompletionTests(unittest.TestCase):
    def test_actual_phase_and_closed_summary_binding_reject_tampering(self):
        baseline = (HERE / "baseline-summary.json").read_bytes()
        phase = (HERE / "phase-evidence.json").read_bytes()
        for target in ("baseline-summary.json", "phase-evidence.json"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                (directory / "baseline-summary.json").write_bytes(baseline)
                (directory / "phase-evidence.json").write_bytes(phase)
                (directory / target).write_bytes((directory / target).read_bytes() + b" ")
                with patch.object(campaign, "HERE", directory), patch.object(campaign.base, "inputs", side_effect=AssertionError("must stop first")):
                    with self.assertRaisesRegex(RuntimeError, "changed"):
                        campaign.inputs()

    def test_only_one_selected_profile_and_three_budget_differences(self):
        self.assertEqual(campaign.PROFILES, (("dense512-completion", True, "::framepin_campaign_", 12),))
        candidate = campaign.candidate_module()
        old, new = candidate.prior.expected_bounds(True), candidate.expected_bounds(True)
        delta = {(group, key) for group in old for key in old[group] if old[group][key] != new[group][key]}
        self.assertEqual(delta, {("run_budget", "instruction_fuel"), ("run_budget", "deadline_ms"), ("wasi_budget", "deadline_ms")})
        for invalid in (False, 0, 1, None, "dense512"):
            with self.subTest(invalid=invalid), self.assertRaises((ValueError, RuntimeError)):
                candidate.parameterize(self.original, invalid)
        self.assertEqual(new["run_budget"]["cache_work"], 4_000_000_000)
        self.assertEqual(new["run_budget"]["execution_work"], 16_000_000_000)

    def test_current_profile_selection_local_rerun_and_resume_stop(self):
        variants = [REMOTE_ENV | {"MIXER_DENSE512_COMPLETION_SELECTION": value} for value in ("", "capacity-window-v1", "dense512-completion-v1-extra")]
        variants += [REMOTE_ENV | {"GITHUB_RUN_ATTEMPT": "2"}, REMOTE_ENV | {"RUNNER_ENVIRONMENT": "self-hosted"}, {}]
        with patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign, "guarded_command", side_effect=AssertionError("must not spawn")):
            for env in variants:
                with tempfile.TemporaryDirectory() as tmp, patch.dict(campaign.os.environ, env, clear=True):
                    output = Path(tmp) / "missing"
                    with self.assertRaises(RuntimeError):
                        campaign.run(output)
                    self.assertFalse(output.exists())
            with tempfile.TemporaryDirectory() as tmp, patch.dict(campaign.os.environ, REMOTE_ENV, clear=True):
                with self.assertRaisesRegex(RuntimeError, "fresh campaign output"):
                    campaign.run(Path(tmp))

    def test_one_attempt_persists_before_spawn_and_never_refunds(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(campaign.base, "ensure_command_budget") as budget:
            record, output = {"fullAttempts": 0}, Path(tmp)
            campaign.reserve_full_attempt(record, output)
            budget.assert_called_once_with(1350)
            self.assertEqual(json.loads((output / "campaign.json").read_text())["fullAttempts"], 1)
            with self.assertRaisesRegex(RuntimeError, "full attempt cap"):
                campaign.reserve_full_attempt(record, output)

    def test_command_cap_rejects_seventh_before_spawn(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(campaign.base, "command", side_effect=AssertionError("must not spawn")):
            output = Path(tmp)
            custody = {"recordPath": str(output / "custody.json"), "pendingCommand": None, "provenClosedCommands": 6}
            with self.assertRaisesRegex(RuntimeError, "command count cap"):
                campaign.guarded_command(custody, ["forbidden"], output, {}, output / "cmd", 1)

    def mocked_run(self, output, failure=None):
        def prepare(name, capacity, finite_filter, count, original, target, scratch, env, output, record, custody):
            self.assertEqual(custody["provenClosedCommands"], 2)
            self.assertEqual(record["fullAttempts"], 0)
            if failure == "finite":
                raise RuntimeError("finite control failed")
            custody["provenClosedCommands"] += 3
            record["preparedProfiles"].append({"name": name})
            return {"name": name}
        def execute(prepared, target, scratch, output, record, custody):
            self.assertEqual(record["preparationGate"], {"singleArmPrepared": True, "fullAttemptsAtAdmission": 0, "closedPreparationCommands": 5})
            self.assertEqual(custody["provenClosedCommands"], 5)
            campaign.reserve_full_attempt(record, output)
            if failure == "full":
                raise RuntimeError("strong full failure")
            custody["provenClosedCommands"] += 1
            record["profiles"].append({"name": prepared["name"], "hostFeasibility": False})
        with patch.dict(campaign.os.environ, REMOTE_ENV, clear=True), patch.object(campaign.platform, "system", return_value="Linux"), \
                patch.object(campaign.signal, "signal"), patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), \
                patch.object(campaign, "check", return_value={"candidateGeneratorSHA256": "fixture", "candidateSourceBindings": {}}), \
                patch.object(campaign.base, "command", return_value={"pid": 123, "exitCode": 0, "timedOut": False, "processGroupEmpty": True}), \
                patch.object(campaign, "prepare_profile", side_effect=prepare), patch.object(campaign, "execute_profile", side_effect=execute) as full:
            if failure:
                with self.assertRaisesRegex(RuntimeError, "failed|failure"):
                    campaign.run(output)
            else:
                campaign.run(output)
            return json.loads((output / "campaign.json").read_text()), full.call_count

    def test_single_full_only_after_five_closed_preparation_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            result, calls = self.mocked_run(Path(tmp) / "output")
            self.assertEqual((calls, result["fullAttempts"], result["cleanup"]["commandCustody"]["provenClosedCommands"]), (1, 1, 6))
            self.assertEqual(result["status"], "completion-experiment-closed")
            self.assertEqual(result["milestoneObservedArms"], [])
            self.assertTrue(result["cleanup"]["ownedScratchRemoved"])

    def test_finite_failure_and_full_failure_never_retry(self):
        for failure, attempts in (("finite", 0), ("full", 1)):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                result, calls = self.mocked_run(Path(tmp) / "output", failure)
                self.assertEqual((result["fullAttempts"], calls), (attempts, attempts))
                self.assertEqual(result["status"], "stopped")
                self.assertTrue(result["cleanup"]["ownedScratchRemoved"])

    def test_full_admission_requires_exact_single_preparation_gate(self):
        for gate in (None, {"singleArmPrepared": True, "fullAttemptsAtAdmission": 0, "closedPreparationCommands": 4},
                {"bothArmsPrepared": True, "fullAttemptsAtAdmission": 0, "closedPreparationCommands": 9}):
            with self.subTest(gate=gate), patch.object(campaign, "verify_prepared", side_effect=AssertionError("must not admit")):
                with self.assertRaisesRegex(RuntimeError, "preparation required"):
                    campaign.execute_profile({}, None, None, None, {"preparationGate": gate}, {})

    def test_geometry_requires_current_selected_scalar_and_deadline_guards(self):
        text = self.geometry_fixture(True).replace("4000000000,2000000000,16000000000", "4000000000,4000000000,16000000000")
        marker = "COMPLETION deadline_ms=1200000 wasi_deadline_ms=1200000 earliest_absolute=true sticky_expiry=true cleanup_zero=true\n"
        self.assertTrue(self.parse_geometry(text + marker, True)["cleanupZero"])
        for invalid in (text, text + marker + marker, text.replace("4000000000,4000000000", "4000000000,2000000000") + marker,
                (text + marker).replace("1200000", "600000"), (text + marker).replace("conservative_combined=", "unexpected=")):
            with self.subTest(invalid=invalid[-120:]), self.assertRaises(RuntimeError):
                self.parse_geometry(invalid, True)

    def test_source_contract_and_immutable_original_harness(self):
        source = campaign.prepare_source(self.original, True)
        for changed in (source | {"../escape": b"x"}, source | {"/absolute": b"x"}, source | {"x": "not bytes"},
                {k: v for k, v in source.items() if k != "Cargo.toml"},
                source | {"src/experimental_swift_reactor/campaign_harness.rs": b"changed"},
                source | {"src/experimental_swift_reactor/lifecycle_tests.rs": b"changed"}):
            with self.assertRaises(RuntimeError):
                campaign.validate_source(self.original, changed)
        module = Mock(expected_bounds=lambda *args: {}, parameterize=lambda *args: source)
        with patch.object(campaign, "candidate_module", return_value=module), self.assertRaisesRegex(RuntimeError, "selected bounds"):
            campaign.prepare_source(self.original, True)

    def test_full_command_has_aggregate_cleanup_margin_and_cancellation(self):
        with patch.object(campaign.base, "COMMAND_DEADLINE", 2100), patch.object(campaign.base.time, "monotonic", return_value=729):
            campaign.base.ensure_command_budget(1350)
        with patch.object(campaign.base, "COMMAND_DEADLINE", 2100), patch.object(campaign.base.time, "monotonic", return_value=730):
            with self.assertRaisesRegex(RuntimeError, "aggregate campaign deadline"):
                campaign.base.ensure_command_budget(1350)
        with patch.object(campaign.base, "CANCEL_REQUESTED", "SIGTERM"):
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                campaign.base.ensure_command_budget(1350)

    def test_command_sites_and_manual_workflow_remain_bounded(self):
        tree = ast.parse((HERE / "campaign.py").read_text())
        direct = [f.name for f in tree.body if isinstance(f, ast.FunctionDef) for n in ast.walk(f)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "base" and n.func.attr == "command"]
        self.assertEqual(direct, ["guarded_command"])
        workflow = (HERE / "workflow.yml").read_text()
        for expected in ("workflow_dispatch:", "timeout-minutes: 44", "timeout-minutes: 36", "cancel-in-progress: false",
                "group: swift-execution-architecture-comparison", "dense512-completion-v1",
                "python3 -B verification/swift-dense512-completion-experiment/campaign.py run"):
            self.assertIn(expected, workflow)
        self.assertNotIn("push:", workflow)
        self.assertEqual(campaign.CAMPAIGN_SECONDS, 2100)
        self.assertEqual(campaign.MAX_FULL_ATTEMPTS, 1)


# Reuse the frozen rejection bodies against THIS candidate runner, retaining
# their exact failure/classifier/custody semantics without copying 50 KiB.
for name in ("setUpClass", "setUp", "failure_fixture", "write_failure_log", "prefix", "parse_prefix", "geometry_fixture", "parse_geometry"):
    setattr(CompletionTests, name, prior_tests.CampaignTests.__dict__[name])
for name in (
    "test_exact_artifact_original_oracle_and_source_harness",
    "test_original_failure_and_true_zero_resource_cleanup_remain_separate",
    "test_bounds_bool_coercion_missing_duplicate_and_extra_fields_rejected",
    "test_every_final_resource_current_requires_integer_zero",
    "test_first_failure_replacement_nonresource_and_invalid_telemetry_stop",
    "test_ordinary_resource_limits_are_diagnostics",
    "test_capacity_defect_each_identity_stops_after_real_classifier",
    "test_structural_ticket_and_owner_failure_identities_stop",
    "test_external_timeout_cancellation_invalid_exit_and_group_proof_stop",
    "test_base_classifier_rejects_any_original_oracle_field_mismatch",
    "test_prefix_records_are_separate_bounded_actual_observations",
    "test_prefix_schema_order_cursor_budget_and_output_negatives",
    "test_prefix_reached_thresholds_bound_to_final_owner_counters",
    "test_prefix_rejects_absolute_and_interval_fuel_defects_at_both_entrypoints",
    "test_prefix_final_join_checks_fuel_even_without_reached_threshold",
    "test_prefix_accepts_nondecreasing_bulk_fuel_and_exact_final_interval",
    "test_prepared_binary_geometry_manifest_and_input_rechecked_before_full_admission",
    "test_unchanged_checks_complete_source_inventory_and_exact_input",
    "test_changed_candidate_binding_or_generated_manifest_stops_before_build",
    "test_custody_guard_rejects_invalid_terminal_proof_and_blocks_next",
    "test_proven_reaped_exit_and_group_absence_clear_custody",
    "test_bad_terminal_proof_retains_run_scratch_and_blocks_profile",
    "test_success_requires_both_original_complete_observations",
    "test_helper_exceptions_retain_pending_custody_scratch_and_stop",
):
    setattr(CompletionTests, name, prior_tests.CampaignTests.__dict__[name])


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(HERE / "verify.py"), run_name="__main__")
