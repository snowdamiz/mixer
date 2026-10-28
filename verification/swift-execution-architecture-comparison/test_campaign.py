"""Pure source/data and mocked orchestration checks; no real child/process probes."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("architecture_campaign", HERE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
REMOTE_ENV = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted", "GITHUB_RUN_ATTEMPT": "1"}


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.artifact, cls.bindings = campaign.inputs()

    def setUp(self):
        for owner, name in ((campaign.base.subprocess, "Popen"), (campaign.base.os, "wait4"), (campaign.base.os, "killpg")):
            guard = patch.object(owner, name, side_effect=AssertionError("real child/process operation forbidden in pure controls"))
            guard.start()
            self.addCleanup(guard.stop)

    def failure_fixture(self):
        # Mutated historical data tests validation only; never represented as a run.
        result = campaign.historical()
        bounds = campaign.expected_bounds()
        for e in result["events"]:
            if e["event"] in bounds:
                e["payload"] = bounds[e["event"]]
        row = {"pid": 123, "exitCode": 101, "timedOut": False, "processGroupEmpty": True, "cancelled": None}
        campaign.validate_result(result, row)
        return result, row

    def prefix(self, threshold):
        return {"threshold": threshold, "instructions": threshold, "instruction_fuel": threshold,
            "cache_work": threshold, "execution_work": threshold, "host_calls": 1,
            "elapsed_micros": threshold // 100, "function": 123, "offset": 45}

    def parse_prefix(self, rows=None, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "stderr"
            p.write_bytes(data if data is not None else b"unrelated stderr\n" + b"".join(
                b"MIXER_PREFIX " + json.dumps(r).encode() + b"\n" for r in rows))
            return campaign.prefix_records(p)

    def geometry_fixture(self, algorithm):
        plan = {"floor": 1000, "execution_header": 512, "execution_construction": 2000, "frame_operation": 3000,
            "category_ceiling_sum": sum(campaign.expected_bounds()["run_budget"][k] for k in
                ("source_bytes", "metadata_bytes", "cache_bytes", "state_bytes")),
            "wasi_max": 264456, "shared": 1744, "combined_limit": 268435456, "constructed_current": 10000,
            "constructed_peak": 20000, "resident_current": 30000, "resident_peak": 40000, "frame_peak": 50000, "tickets": "277/278"}
        operation = 5000 if algorithm else 4000
        plan["conservative_combined"] = plan["category_ceiling_sum"] + plan["wasi_max"] + plan["shared"] + plan["floor"] + max(
            plan["execution_construction"], plan["frame_operation"] + operation)
        cache = ("DENSE geometry index_bytes=160000 pin_bitmap_bytes=8 header=512 operation=5000 logical_peak=50000" if algorithm else
            "CAMPAIGN geometry residents=256 index_cells=384 index_bytes=768 cycle_bytes=32 plan_bytes=256 tickets=278 cache_fixed=1000 operation_bound=4000 combined_peak=50000")
        # Deliberately synthetic numeric data, only for pure parser negatives.
        return "PLAN_PROFILE " + " ".join(f"{k}={v}" for k, v in plan.items()) + "\n" + cache + "\n" + \
            "PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0\n"

    def parse_geometry(self, text, algorithm):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stdout"
            path.write_text(text)
            return campaign.geometry_record(path, algorithm)

    def remote_run(self, output, profile, prepare=None):
        def default_prepare(name, algorithm, finite_filter, count, original, target, scratch, env, output, record, custody):
            self.assertEqual(record["fullAttempts"], 0)
            record["preparedProfiles"].append({"name": name})
            custody["provenClosedCommands"] += 3  # Mocked build, finite and harness closures.
            return {"profile": (name, algorithm, finite_filter, count)}
        def execute(prepared, target, scratch, output, record, custody):
            self.assertEqual(len(record["preparedProfiles"]), 2)
            return profile(*prepared["profile"], {}, target, scratch, {}, output, record, custody)
        with patch.dict(campaign.os.environ, REMOTE_ENV, clear=True), \
                patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), \
                patch.object(campaign, "check", return_value={"candidateGeneratorSHA256": "fixture", "candidateSourceBindings": {}}), \
                patch.object(campaign.base, "command", return_value={"pid": 123, "exitCode": 0, "timedOut": False, "processGroupEmpty": True}), \
                patch.object(campaign, "prepare_profile", side_effect=prepare or default_prepare), \
                patch.object(campaign, "execute_profile", side_effect=execute):
            campaign.run(output)

    def test_exact_artifact_original_oracle_and_source_harness(self):
        self.assertEqual((len(self.artifact), campaign.sha(self.artifact)), (53_777_114, campaign.base.ARTIFACT_HASH))
        self.assertFalse((HERE / "inputs").exists())
        self.assertEqual(len(json.loads((campaign.base.INPUTS / "native-observation.json").read_text())), 11)
        for _, algorithm, _, _ in campaign.PROFILES:
            source = campaign.prepare_source(self.original, algorithm)
            self.assertEqual(source["src/experimental_swift_reactor/campaign_harness.rs"], (campaign.base.INPUTS / "harness.rs").read_bytes())
        self.assertEqual(campaign.sha((campaign.REVIEW / "seal.json").read_bytes()), campaign.REVIEW_SEAL_SHA)

    def test_both_arms_share_exact_control_harness_and_three_threshold_observer(self):
        control = campaign.prepare_source(self.original, False)
        dense = campaign.prepare_source(self.original, True)
        self.assertEqual({name for name in control if control[name] != dense[name]}, {
            "src/experimental/cache/borrowed.rs", "src/experimental_swift_reactor/cache.rs", "src/experimental_swift_reactor/cache_tests.rs"})
        for name in ("control.rs", "campaign_harness.rs", "lifecycle_tests.rs"):
            path = "src/experimental_swift_reactor/" + name
            self.assertEqual(control[path], dense[path])
        source = control["src/experimental_swift_reactor/control.rs"]
        self.assertEqual(source.count(b"MIXER_PREFIX "), 1)
        self.assertEqual(source.count(b"matches!(self.instructions, 25_000_000 | 50_000_000 | 100_000_000)"), 1)

    def test_complete_bounds_preserve_every_other_ceiling_and_grant(self):
        bounds = campaign.expected_bounds()
        old = campaign.historical()
        normalized = copy.deepcopy(bounds)
        normalized["run_budget"].update(cache_entries=64, cache_work=64_000_000, instruction_fuel=100_000_000,
            execution_work=1_000_000_000, deadline_ms=30_000)
        normalized["wasi_budget"]["deadline_ms"] = 30_000
        self.assertEqual(normalized, {n: campaign.event(old, n) for n in normalized})
        self.assertEqual(bounds["validation_budget"]["deadline_ms"], 120_000)
        self.assertEqual(bounds["run_budget"]["memory_pages"] * 65536, 48 * 1024 * 1024)
        self.assertEqual(bounds["run_budget"]["cache_work"], 768_000_000)
        self.assertTrue(campaign.typed_equal(campaign.candidate_module().expected_bounds(), bounds))

    def test_check_generates_two_source_identities_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = campaign.check(output)
            self.assertEqual(result["maxFullAttempts"], 2)
            self.assertEqual(result["aggregateDriverSeconds"], 2700)
            self.assertLessEqual(result["worstCaseCommandsCleanupAndReceiptSeconds"], result["aggregateDriverSeconds"])
            self.assertEqual(set(result["candidateSourceBindings"]), set(campaign.CANDIDATE_FILES))
            self.assertEqual([p["name"] for p in result["profiles"]], [p[0] for p in campaign.PROFILES])
            self.assertNotEqual(result["profiles"][0]["sourceSHA256"], result["profiles"][1]["sourceSHA256"])
            for row in result["profiles"]:
                saved = json.loads((output / row["name"] / "source.json").read_text())
                self.assertEqual(saved["sha256"], row["sourceSHA256"])
                self.assertEqual(row["bounds"], campaign.expected_bounds())

    def test_source_and_candidate_contract_fail_closed(self):
        source = campaign.prepare_source(self.original, False)
        for changed in (source | {"../escape": b"x"}, source | {"/absolute": b"x"}, source | {"x": "not bytes"},
                {k: v for k, v in source.items() if k != "Cargo.toml"},
                source | {"src/experimental_swift_reactor/campaign_harness.rs": b"changed"},
                source | {"src/experimental_swift_reactor/lifecycle_tests.rs": b"changed"}):
            with self.assertRaises(RuntimeError):
                campaign.validate_source(self.original, changed)
        with self.assertRaisesRegex(RuntimeError, "selected explicitly"):
            campaign.prepare_source(self.original, 1)
        module = Mock(expected_bounds=lambda: {}, parameterize=lambda *args: source)
        with patch.object(campaign, "candidate_module", return_value=module), self.assertRaisesRegex(RuntimeError, "selected bounds"):
            campaign.prepare_source(self.original, False)

    def test_original_failure_and_true_zero_resource_cleanup_remain_separate(self):
        result, _ = self.failure_fixture()
        self.assertTrue(result["originalFinalFailurePreserved"])
        self.assertTrue(campaign.zero_resources(result))
        self.assertFalse(campaign.event(result, "cleanup_empty"))
        self.assertEqual(result["outcome"], "resource-limit-diagnostic")
        self.assertFalse(result["hostFeasibility"])

    def test_bounds_bool_coercion_missing_duplicate_and_extra_fields_rejected(self):
        result, row = self.failure_fixture()
        for name, key, value in (("run_budget", "instruction_fuel", 100_000_000), ("run_budget", "cache_work", 1),
                ("wasi_budget", "deadline_ms", 30_000), ("validation_budget", "deadline_ms", 1), ("wasi_grants", "stdout", 1)):
            variant = copy.deepcopy(result)
            campaign.event(variant, name)[key] = value
            with self.subTest(bound=(name, key)), self.assertRaisesRegex(RuntimeError, "actual budgets/grants"):
                campaign.validate_result(variant, row)
        for mutation in ("missing", "duplicate", "extra"):
            variant = copy.deepcopy(result)
            if mutation == "missing":
                variant["events"] = [e for e in variant["events"] if e["event"] != "run_budget"]
            elif mutation == "duplicate":
                variant["events"].append({"event": "run_budget", "payload": campaign.event(variant, "run_budget")})
            else:
                campaign.event(variant, "run_budget")["new_limit"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(RuntimeError):
                campaign.validate_result(variant, row)

    def test_every_final_resource_current_requires_integer_zero(self):
        result, row = self.failure_fixture()
        final = campaign.event(result, "final_cleanup_usage")
        for group in ("reservations", "live"):
            for key, value in final[group].items():
                if type(value) is not dict:
                    continue
                for nonzero in (1, False):
                    variant = copy.deepcopy(result)
                    campaign.event(variant, "final_cleanup_usage")[group][key]["current"] = nonzero
                    with self.subTest(resource=(group, key, nonzero)), self.assertRaisesRegex(RuntimeError, "cleanup unresolved"):
                        campaign.validate_result(variant, row)
        for mutate in (lambda f: f["reservations"].update(live_tickets=False),
                lambda f: f["reservations"].pop("shared"), lambda f: f["live"].update(new={"current": 0, "peak": 0}),
                lambda f: f.update(cleanup_invariant="invariant")):
            variant = copy.deepcopy(result)
            mutate(campaign.event(variant, "final_cleanup_usage"))
            with self.assertRaisesRegex(RuntimeError, "cleanup unresolved"):
                campaign.validate_result(variant, row)

    def test_first_failure_replacement_nonresource_and_invalid_telemetry_stop(self):
        result, row = self.failure_fixture()
        changed = copy.deepcopy(result)
        campaign.event(changed, "final_failure")["resource"] = "InstructionFuel"
        with self.assertRaisesRegex(RuntimeError, "first failure not preserved"):
            campaign.validate_result(changed, row)
        for kind in ("Invariant", "GuestTrap", "UnsupportedEnvironment", "InvalidBudget", "Wasi", "unknown"):
            changed = copy.deepcopy(result)
            changed["firstFailure"]["payload"]["kind"] = kind
            campaign.event(changed, "final_failure")["kind"] = kind
            with self.subTest(kind=kind), self.assertRaisesRegex(RuntimeError, "non-resource failure"):
                campaign.validate_result(changed, row)
        with self.assertRaisesRegex(RuntimeError, "invalid attribution"):
            campaign.validate_result(result | {"telemetry": {"status": "invalid"}}, row)
        changed = copy.deepcopy(result)
        next(e for e in changed["events"] if e["event"] == "cleanup_empty")["payload"] = True
        with self.assertRaisesRegex(RuntimeError, "cleanup success/failure semantics"):
            campaign.validate_result(changed, row)

    def test_ordinary_resource_limits_are_diagnostics(self):
        result, row = self.failure_fixture()
        for kind in campaign.RESOURCE_FAILURE_KINDS:
            changed = copy.deepcopy(result)
            changed["firstFailure"]["payload"]["kind"] = kind
            campaign.event(changed, "final_failure")["kind"] = kind
            campaign.validate_result(changed, row)
            self.assertEqual(changed["outcome"], "resource-limit-diagnostic")
            self.assertFalse(changed["hostFeasibility"])

    def test_external_timeout_cancellation_invalid_exit_and_group_proof_stop(self):
        result, row = self.failure_fixture()
        for key, value in (("timedOut", True), ("timedOut", 0), ("cancelled", "SIGTERM"),
                ("processGroupEmpty", False), ("processGroupEmpty", 1), ("exitCode", 0), ("exitCode", True), ("exitCode", -9)):
            with self.subTest(field=(key, value)), self.assertRaises(RuntimeError):
                campaign.validate_result(copy.deepcopy(result), row | {key: value})

    def test_base_classifier_rejects_any_original_oracle_field_mismatch(self):
        expected = json.loads((campaign.base.INPUTS / "native-observation.json").read_text())
        for key, value in expected.items():
            changed = expected | {key: (not value if type(value) is bool else value + 1 if type(value) is int else str(value) + "changed")}
            events = [("initialize", {"stdout": ""}), ("corpus_1", {"stdout": json.dumps(changed)}),
                ("guest_output_native_equal", "corpus_1")]
            with self.subTest(field=key), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "stdout"
                p.write_text("".join("MIXER_EXACT " + json.dumps({"event": event, "payload": payload}) + "\n" for event, payload in events))
                with self.assertRaisesRegex(RuntimeError, "complete native oracle mismatch"):
                    campaign.base.classify(p, {"exitCode": 0, "timedOut": False, "processGroupEmpty": True})

    def test_prefix_records_are_separate_bounded_actual_observations(self):
        rows = [self.prefix(n) for n in campaign.PREFIX_THRESHOLDS]
        parsed, raw = self.parse_prefix(rows)
        self.assertEqual(parsed["records"], rows)
        self.assertEqual(parsed["outputBytes"], len(raw))
        self.assertLessEqual(len(raw), 8192)
        self.assertNotIn("success", parsed)
        self.assertNotIn("pass", parsed)
        empty, _ = self.parse_prefix([])
        self.assertEqual(empty["records"], [])

    def test_prefix_schema_order_cursor_budget_and_output_negatives(self):
        row = self.prefix(25_000_000)
        for changed in (row | {"threshold": 50_000_000}, row | {"instructions": 25_000_001}, row | {"function": (1 << 64) - 1},
                row | {"offset": (1 << 64) - 1}, row | {"cache_work": 768_000_001}, row | {"elapsed_micros": False},
                row | {"elapsed_micros": -1}, row | {"elapsed_micros": 1.1}, row | {"extra": 0},
                {k: v for k, v in row.items() if k != "offset"}):
            with self.subTest(row=changed), self.assertRaises((RuntimeError, ValueError)):
                self.parse_prefix([changed])
        for rows in ([row, row], [row, self.prefix(50_000_000) | {"cache_work": 1}],
                [self.prefix(n) for n in campaign.PREFIX_THRESHOLDS] + [row]):
            with self.assertRaises(RuntimeError):
                self.parse_prefix(rows)
        for data in (b"MIXER_PREFIX " + json.dumps(row).encode(), b'MIXER_PREFIX {"threshold":1,"threshold":2}\n',
                b"MIXER_PREFIX " + b" " * 8192 + b"{}\n"):
            with self.assertRaises((RuntimeError, ValueError)):
                self.parse_prefix(data=data)

    def test_prefix_reached_thresholds_bound_to_final_owner_counters(self):
        result, _ = self.failure_fixture()
        parsed, _ = self.parse_prefix([])
        campaign.validate_prefix(result, parsed)
        final = campaign.event(result, "final_cleanup_usage")
        final.update(instructions=25_000_000, instruction_fuel=25_000_000, cache_work=25_000_000,
            execution_work=25_000_000, host_calls=1, elapsed_micros=250_000)
        with self.assertRaisesRegex(RuntimeError, "reached final instruction count"):
            campaign.validate_prefix(result, parsed)
        parsed, _ = self.parse_prefix([self.prefix(25_000_000)])
        campaign.validate_prefix(result, parsed)
        final["host_calls"] = 0
        with self.assertRaisesRegex(RuntimeError, "exceed final owner"):
            campaign.validate_prefix(result, parsed)

    def test_geometry_receipt_requires_bounded_actual_envelope_and_dense_storage(self):
        for algorithm in (False, True):
            parsed = self.parse_geometry(self.geometry_fixture(algorithm), algorithm)
            self.assertEqual(parsed["plan"]["conservative_combined"], parsed["recomputedConservativeCombined"])
            self.assertLessEqual(parsed["recomputedConservativeCombined"], 268435456)
            self.assertIs(parsed["cleanupZero"], True)
            self.assertEqual(parsed["guestInstructions"], 0)
            if algorithm:
                self.assertEqual((parsed["cache"]["index_bytes"], parsed["cache"]["pin_bitmap_bytes"]), (160000, 8))
        text = self.geometry_fixture(True)
        first = text.splitlines()[0] + "\n"
        negatives = (text.replace(first, ""), first + text, text.replace("cleanup_zero=true", "cleanup_zero=false"),
            text + "PLAN_PROFILE cleanup_zero=true guest_instructions=0 initializes=0 invokes=0\n",
            text.replace("combined_limit=268435456", "combined_limit=268435457"), text.replace("floor=1000", "floor=1001"),
            text.replace("floor=1000", "floor=false"), text.replace("floor=1000", "floor=1000 extra=1"),
            text.replace("tickets=277/278", "tickets=277/279"), text.replace("index_bytes=160000", "index_bytes=159999"),
            text.replace("pin_bitmap_bytes=8", "pin_bitmap_bytes=7"))
        for changed in negatives:
            with self.subTest(change=changed), self.assertRaises(RuntimeError):
                self.parse_geometry(changed, True)
        conservative = self.parse_geometry(text, True)["plan"]["conservative_combined"]
        for value in (conservative + 1, 268435457):
            with self.assertRaises(RuntimeError):
                self.parse_geometry(text.replace(f"conservative_combined={conservative}", f"conservative_combined={value}"), True)

    def test_prepared_binary_geometry_manifest_and_input_rechecked_before_full_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            name = campaign.PROFILES[0][0]
            crate, phase, binary, target = output / "vm", output / name, output / "binary", output / "input"
            source = {"a.rs": b"source"}
            campaign.base.materialize(source, crate)
            record, _ = campaign.base.source_record({}, source)
            campaign.save(output / "preflight" / name / "source.json", record)
            campaign.save(phase / "source.json", record)
            (phase / "finite").mkdir()
            (phase / "finite/stdout").write_bytes(b"geometry fixture")
            geometry = {"finiteStdoutSHA256": campaign.sha(b"geometry fixture")}
            campaign.save(phase / "geometry.json", geometry)
            target.write_bytes(b"fixture")
            binary.write_bytes(b"binary fixture")
            prepared = {"name": name, "source": source, "record": record, "crate": crate, "phase": phase,
                "binary": binary, "executable": {"bytes": len(b"binary fixture"), "sha256": campaign.sha(b"binary fixture")},
                "geometry": geometry, "geometrySHA256": campaign.sha((phase / "geometry.json").read_bytes())}
            with patch.object(campaign, "candidate_bindings", return_value={}), patch.object(campaign.base, "ARTIFACT_BYTES", 7), \
                    patch.object(campaign.base, "ARTIFACT_HASH", campaign.sha(b"fixture")):
                campaign.verify_prepared(prepared, target, output, {"candidateSourceBindings": {}})
                for path, contents in ((binary, b"changed"), (target, b"changed"), (phase / "geometry.json", b"changed"),
                        (phase / "source.json", b"{}"), (phase / "finite/stdout", b"changed")):
                    original = path.read_bytes()
                    path.write_bytes(contents)
                    with self.subTest(path=path.name), self.assertRaises(RuntimeError):
                        campaign.verify_prepared(prepared, target, output, {"candidateSourceBindings": {}})
                    path.write_bytes(original)

    def test_unchanged_checks_complete_source_inventory_and_exact_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crate, target = root / "vm", root / "input"
            crate.mkdir()
            source = {"a.rs": b"source"}
            campaign.base.materialize(source, crate)
            target.write_bytes(b"fixture")
            with patch.object(campaign.base, "ARTIFACT_BYTES", 7), patch.object(campaign.base, "ARTIFACT_HASH", campaign.sha(b"fixture")):
                self.assertTrue(campaign.unchanged(crate, source, target))
                (crate / "extra.rs").write_bytes(b"new")
                self.assertFalse(campaign.unchanged(crate, source, target))
                (crate / "extra.rs").unlink()
                (crate / "a.rs").write_bytes(b"changed")
                self.assertFalse(campaign.unchanged(crate, source, target))
                (crate / "a.rs").write_bytes(b"source")
                target.write_bytes(b"changed")
                self.assertFalse(campaign.unchanged(crate, source, target))

    def test_attempts_persist_before_spawn_and_no_refund_or_third_attempt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(campaign.base, "ensure_command_budget"):
            output, record = Path(tmp), {"fullAttempts": 0}
            for expected in (1, 2):
                campaign.reserve_full_attempt(record, output)
                self.assertEqual(json.loads((output / "campaign.json").read_text())["fullAttempts"], expected)
            with self.assertRaisesRegex(RuntimeError, "full attempt cap"):
                campaign.reserve_full_attempt(record, output)
            self.assertEqual(record["fullAttempts"], 2)

    def test_changed_candidate_binding_or_generated_manifest_stops_before_build(self):
        for change in ("binding", "manifest"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp)
                record = {"candidateSourceBindings": {}, "fullAttempts": 0, "preparedProfiles": []}
                campaign.save(output / "preflight" / campaign.PROFILES[0][0] / "source.json", {"changed": True})
                with patch.object(campaign, "candidate_bindings", return_value=({"changed": True} if change == "binding" else {})), \
                        patch.object(campaign, "prepare_source", return_value={"fixture.rs": b"fixture"}), \
                        patch.object(campaign, "guarded_command", side_effect=AssertionError("no build permitted")):
                    with self.assertRaisesRegex(RuntimeError, "changed after preflight" if change == "binding" else "differs from preflight"):
                        campaign.prepare_profile(*campaign.PROFILES[0], {}, output / "input", output / "scratch", {}, output, record, {})

    def test_two_arms_selected_even_when_each_is_an_ordinary_clean_limit(self):
        invoked = []
        def profile(name, algorithm, finite_filter, count, original, target, scratch, env, output, record, custody):
            invoked.append((name, algorithm, finite_filter, count))
            record["fullAttempts"] += 1
            record["profiles"].append({"name": name, "hostFeasibility": False, "outcome": "resource-limit-diagnostic"})
            custody["provenClosedCommands"] += 1  # Mocked full-command closure after both prepared arms.
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            self.remote_run(output, profile)
            saved = json.loads((output / "campaign.json").read_text())
            self.assertEqual(invoked, list(campaign.PROFILES))
            self.assertEqual(saved["fullAttempts"], 2)
            self.assertEqual(saved["status"], "comparison-closed")
            self.assertEqual(saved["milestoneObservedArms"], [])
            self.assertTrue(saved["cleanup"]["ownedScratchRemoved"])
            self.assertFalse(saved["cleanup"]["commandCustodyUnresolved"])

    def test_candidate_finite_failure_leaves_full_attempts_zero(self):
        invoked = []
        def prepare(name, algorithm, finite_filter, count, original, target, scratch, env, output, record, custody):
            invoked.append(name)
            self.assertEqual(record["fullAttempts"], 0)
            if algorithm:
                raise RuntimeError("candidate finite geometry failed")
            record["preparedProfiles"].append({"name": name})
            custody["provenClosedCommands"] += 3
            return {"profile": (name, algorithm, finite_filter, count)}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            with self.assertRaisesRegex(RuntimeError, "candidate finite geometry failed"):
                self.remote_run(output, Mock(side_effect=AssertionError("no full attempt permitted")), prepare)
            saved = json.loads((output / "campaign.json").read_text())
            self.assertEqual(invoked, [p[0] for p in campaign.PROFILES])
            self.assertEqual(saved["fullAttempts"], 0)
            self.assertEqual(len(saved["preparedProfiles"]), 1)
            self.assertNotIn("preparationGate", saved)
            self.assertTrue(saved["cleanup"]["ownedScratchRemoved"])

    def test_both_preparations_close_before_first_full_attempt(self):
        order = []
        def prepare(name, algorithm, finite_filter, count, original, target, scratch, env, output, record, custody):
            order.append(("prepare", name))
            self.assertEqual(record["fullAttempts"], 0)
            record["preparedProfiles"].append({"name": name})
            custody["provenClosedCommands"] += 3
            return {"profile": (name, algorithm, finite_filter, count)}
        def execute(name, algorithm, finite_filter, count, original, target, scratch, env, output, record, custody):
            order.append(("full", name))
            self.assertEqual(record["preparationGate"]["closedPreparationCommands"], 9)
            self.assertEqual(len(record["preparedProfiles"]), 2)
            record["fullAttempts"] += 1
            record["profiles"].append({"name": name, "hostFeasibility": False})
            custody["provenClosedCommands"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            self.remote_run(Path(tmp) / "output", execute, prepare)
        self.assertEqual(order, [("prepare", p[0]) for p in campaign.PROFILES] + [("full", p[0]) for p in campaign.PROFILES])

    def test_strong_failure_stops_without_second_attempt(self):
        invoked = []
        def profile(*args):
            invoked.append(args[0])
            args[-2]["fullAttempts"] += 1
            raise RuntimeError("unexpected invariant")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            with self.assertRaisesRegex(RuntimeError, "unexpected invariant"):
                self.remote_run(output, profile)
            saved = json.loads((output / "campaign.json").read_text())
            self.assertEqual(invoked, [campaign.PROFILES[0][0]])
            self.assertEqual(saved["fullAttempts"], 1)
            self.assertEqual(saved["status"], "stopped")
            self.assertTrue(saved["cleanup"]["ownedScratchRemoved"])

    def test_local_rerun_and_resume_declined_before_child(self):
        for env in ({}, REMOTE_ENV | {"GITHUB_RUN_ATTEMPT": "2"}):
            with tempfile.TemporaryDirectory() as tmp, patch.dict(campaign.os.environ, env, clear=True), \
                    patch.object(campaign.platform, "system", return_value="Linux"):
                out = Path(tmp) / "absent"
                with self.assertRaisesRegex(RuntimeError, "local execution and rerun remain held"):
                    campaign.run(out)
                self.assertFalse(out.exists())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(campaign.os.environ, REMOTE_ENV, clear=True), \
                patch.object(campaign.platform, "system", return_value="Linux"):
            with self.assertRaisesRegex(RuntimeError, "no retries/resume"):
                campaign.run(Path(tmp))

    def test_custody_guard_rejects_invalid_terminal_proof_and_blocks_next(self):
        good = {"pid": 123, "exitCode": 0, "processGroupEmpty": True}
        for bad in (None, {}, good | {"exitCode": -999}, good | {"exitCode": True}, good | {"exitCode": 256},
                good | {"pid": 0}, good | {"pid": True}, good | {"processGroupEmpty": False},
                good | {"processGroupEmpty": 1}, {"pid": 123, "exitCode": 0}):
            with self.subTest(proof=bad), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                custody = {"recordPath": str(path / "custody.json"), "pendingCommand": None, "provenClosedCommands": 0}
                with patch.object(campaign.base, "command", return_value=bad) as helper:
                    with self.assertRaisesRegex(RuntimeError, "proof missing"):
                        campaign.guarded_command(custody, ["fixture"], path, {}, path / "command", 1)
                    with self.assertRaisesRegex(RuntimeError, "previous command custody unresolved"):
                        campaign.guarded_command(custody, ["forbidden next"], path, {}, path / "next", 1)
                    self.assertEqual(helper.call_count, 1)
                self.assertIsNotNone(json.loads((path / "custody.json").read_text())["pendingCommand"])

    def test_proven_reaped_exit_and_group_absence_clear_custody(self):
        for status in (0, 101, -9):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp)
                custody = {"recordPath": str(path / "custody.json"), "pendingCommand": None, "provenClosedCommands": 0}
                returned = {"pid": 123, "exitCode": status, "processGroupEmpty": True}
                def helper(*args):
                    self.assertIsNotNone(json.loads((path / "custody.json").read_text())["pendingCommand"])
                    return returned
                with patch.object(campaign.base, "command", side_effect=helper):
                    self.assertEqual(campaign.guarded_command(custody, ["fixture"], path, {}, path / "command", 1), returned)
                self.assertIsNone(custody["pendingCommand"])
                self.assertEqual(custody["provenClosedCommands"], 1)

    def test_bad_terminal_proof_retains_run_scratch_and_blocks_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            with patch.dict(campaign.os.environ, REMOTE_ENV, clear=True), \
                    patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                    patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), \
                    patch.object(campaign, "check", return_value={"candidateGeneratorSHA256": "fixture", "candidateSourceBindings": {}}), \
                    patch.object(campaign.base, "command", return_value={"pid": 123, "exitCode": -999, "processGroupEmpty": True}) as helper, \
                    patch.object(campaign, "prepare_profile", side_effect=AssertionError("no profile permitted")) as profile:
                with self.assertRaisesRegex(RuntimeError, "proof missing"):
                    campaign.run(output)
            saved = json.loads((output / "campaign.json").read_text())
            self.assertEqual(helper.call_count, 1)
            self.assertEqual(profile.call_count, 0)
            self.assertTrue((output / "scratch/fieldlog-reactor.wasm").exists())
            self.assertEqual(saved["status"], "stopped-unresolved-command-custody")

    def test_success_requires_both_original_complete_observations(self):
        failure, row = self.failure_fixture()
        result = copy.deepcopy(failure)
        result["events"] = [e for e in result["events"] if e["event"] != "runtime_failure"]
        result.update(firstFailure=None, hostFeasibility=True, complete=True, nativeEqualPhases=["corpus_1", "corpus_2"])
        oracle = json.loads((campaign.base.INPUTS / "native-observation.json").read_text())
        result["completeGuestObservations"] = [{"phase": p, "observation": dict(oracle)} for p in ("corpus_1", "corpus_2")]
        for e in result["events"]:
            if e["event"] == "final_failure":
                e["payload"] = None
            if e["event"] == "cleanup_empty":
                e["payload"] = True
        campaign.validate_result(result, row | {"exitCode": 0})
        self.assertEqual(result["outcome"], "host-feasibility-observed")
        for change in ("missing", "phase", "field"):
            variant = copy.deepcopy(result)
            if change == "missing":
                variant["completeGuestObservations"].pop()
            elif change == "phase":
                variant["completeGuestObservations"][1]["phase"] = "corpus_1"
            else:
                variant["completeGuestObservations"][1]["observation"].pop(next(iter(oracle)))
            with self.subTest(change=change), self.assertRaisesRegex(RuntimeError, "oracle"):
                campaign.validate_result(variant, row | {"exitCode": 0})

    def test_helper_exceptions_retain_pending_custody_scratch_and_stop(self):
        for fault in ("post-spawn-receipt", "wait4"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "output"
                child = Mock(pid=12345)
                def fail_save(path, value):
                    if fault == "post-spawn-receipt" and "pid" in value:
                        raise OSError("injected receipt write failure")
                    campaign.save(path, value)
                with patch.dict(campaign.os.environ, REMOTE_ENV, clear=True), \
                        patch.object(campaign.platform, "system", return_value="Linux"), patch.object(campaign.signal, "signal"), \
                        patch.object(campaign, "inputs", return_value=({}, b"fixture", {})), \
                        patch.object(campaign, "check", return_value={"candidateGeneratorSHA256": "fixture", "candidateSourceBindings": {}}), \
                        patch.object(campaign.base, "save", side_effect=fail_save), \
                        patch.object(campaign.base.subprocess, "Popen", return_value=child) as spawn, \
                        patch.object(campaign.base.os, "wait4", side_effect=OSError("injected arbitrary wait4 failure")), \
                        patch.object(campaign, "prepare_profile", side_effect=AssertionError("no subsequent attempt")) as profile:
                    with self.assertRaises(OSError):
                        campaign.run(output)
                saved = json.loads((output / "campaign.json").read_text())
                self.assertEqual(spawn.call_count, 1)
                self.assertEqual(profile.call_count, 0)
                self.assertTrue((output / "scratch/fieldlog-reactor.wasm").exists())
                self.assertEqual(saved["fullAttempts"], 0)
                self.assertTrue(saved["cleanup"]["commandCustodyUnresolved"])
                self.assertFalse(saved["cleanup"]["ownedScratchRemoved"])
                self.assertEqual(saved["status"], "stopped-unresolved-command-custody")

    def test_aggregate_admission_keeps_cleanup_margin_and_cancellation(self):
        with patch.object(campaign.base, "COMMAND_DEADLINE", 1000), patch.object(campaign.base.time, "monotonic", return_value=229):
            campaign.base.ensure_command_budget(750)
        with patch.object(campaign.base, "COMMAND_DEADLINE", 1000), patch.object(campaign.base.time, "monotonic", return_value=230):
            with self.assertRaisesRegex(RuntimeError, "aggregate campaign deadline"):
                campaign.base.ensure_command_budget(750)
        with patch.object(campaign.base, "CANCEL_REQUESTED", "SIGTERM"):
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                campaign.base.ensure_command_budget(750)

    def test_every_command_site_uses_guard_and_reserves_attempt_before_full_spawn(self):
        tree = ast.parse((HERE / "campaign.py").read_text())
        calls = [(f.name, n) for f in tree.body if isinstance(f, ast.FunctionDef)
            for n in ast.walk(f) if isinstance(n, ast.Call)]
        direct = [name for name, n in calls if isinstance(n.func, ast.Attribute)
            and isinstance(n.func.value, ast.Name) and n.func.value.id == "base" and n.func.attr == "command"]
        self.assertEqual(direct, ["guarded_command"])
        execute_profile = next(f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "execute_profile")
        reservation = next(n.lineno for n in ast.walk(execute_profile) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "reserve_full_attempt")
        full = next(n.lineno for n in ast.walk(execute_profile) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name) and n.func.id == "guarded_command" and any(
                isinstance(v, ast.Constant) and v.value == "exact_reactor_target_once" for v in ast.walk(n)))
        self.assertLess(reservation, full)
        workflow = (HERE / "workflow.yml").read_text()
        self.assertIn("timeout-minutes: 55", workflow)
        self.assertIn("timeout-minutes: 46", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
