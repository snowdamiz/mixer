"""Pure source/data checks. No compiler, child, native or custody probe."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("campaign", HERE / "campaign.py")
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)


class CampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.artifact, cls.bindings = campaign.inputs()

    def test_exact_artifact_and_original_harness(self):
        self.assertEqual(len(self.artifact), 53_777_114)
        self.assertEqual(campaign.sha(self.artifact), campaign.ARTIFACT_HASH)
        self.assertEqual(self.bindings["harness.rs"]["sha256"], "8c7730239b38250671f7dc23cc46859ffd5b4b9253f1eabaf34f161c061ec078")
        self.assertEqual(len(json.loads((HERE / "inputs/native-observation.json").read_text())), 11)

    def test_four_profiles_retain_all_other_run_budget_fields(self):
        name = "src/experimental_swift_reactor/control.rs"
        original = self.source[name].decode()
        for label, n, work in campaign.PRIMARY:
            with self.subTest(label=label):
                transformed = campaign.parameterize(self.source, n, work)
                control = transformed[name].decode()
                restored = control.replace(f"MAX_RESERVATION_TICKETS: usize = {n + 22};", "MAX_RESERVATION_TICKETS: usize = 86;")
                restored = restored.replace(f"cache_entries: {n},", "cache_entries: 64,")
                restored = restored.replace(f"cache_work: {work},", "cache_work: 64_000_000,")
                self.assertEqual(restored, original)
                # All charged generic walks, scan/build debit sites, and all
                # validation/execution/cleanup files remain original bytes.
                self.assertEqual(transformed["src/experimental/cache/borrowed.rs"], self.source["src/experimental/cache/borrowed.rs"])
                self.assertEqual(transformed["src/experimental/cache/decode.rs"], self.source["src/experimental/cache/decode.rs"])
                self.assertEqual(transformed["src/experimental_swift_reactor/lifecycle.rs"], self.source["src/experimental_swift_reactor/lifecycle.rs"])
                self.assertEqual(transformed["src/experimental_swift_reactor/campaign_harness.rs"], (HERE / "inputs/harness.rs").read_bytes())

    def test_high_capacity_representations_and_accounting_are_coupled(self):
        for n in (64, 128, 256):
            data = campaign.parameterize(self.source, n, 64_000_000)
            s = data["src/experimental_swift_reactor/cache.rs"].decode()
            self.assertIn(f"const RESIDENT_LINKS: usize = {n};", s)
            self.assertIn("RESIDENT_INDEX_CELLS * size_of::<u16>()", s)
            self.assertIn("seen: [u64; RESIDENT_LINKS / 64]", s)
            self.assertIn("let mut seen = [0u64; RESIDENT_LINKS / 64];", s)
            self.assertIn("size_of::<[bool; RESIDENT_LINKS]>()", s)
            self.assertIn("(slot + 1) as u16", s)
            self.assertNotIn("(slot + 1) as u8", s)
            self.assertIn(f"const MAX_ENTRIES: usize = {n};", data["src/experimental/cache/mod.rs"].decode())
            # Work debits in the index/cache itself are byte-identical lines.
            debits = lambda b: [x.strip() for x in b.decode().splitlines() if ".work(" in x]
            self.assertEqual(debits(data["src/experimental_swift_reactor/cache.rs"]), debits(self.source["src/experimental_swift_reactor/cache.rs"]))

    def test_changed_anchor_and_unsupported_profile_fail_closed(self):
        with self.assertRaises(RuntimeError):
            campaign.replace("changed", "missing", "replacement")
        with self.assertRaises(RuntimeError):
            campaign.parameterize(self.source, 512, 64_000_000)
        with self.assertRaises(RuntimeError):
            campaign.parameterize(self.source, 64, 256_000_000)

    def test_local_run_rejected_before_any_child_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "must-not-exist"
            with patch.dict(campaign.os.environ, {}, clear=True), patch.object(campaign.subprocess, "Popen", side_effect=AssertionError("child forbidden")):
                with self.assertRaisesRegex(RuntimeError, "local execution remains held"):
                    campaign.run(out, False)
            self.assertFalse(out.exists())

    def test_aggregate_deadline_and_cancellation_decline_new_commands(self):
        with patch.object(campaign, "COMMAND_DEADLINE", 1_000), patch.object(campaign.time, "monotonic", return_value=900):
            campaign.ensure_command_budget(79)
            with self.assertRaisesRegex(RuntimeError, "aggregate campaign deadline"):
                campaign.ensure_command_budget(80)
        with patch.object(campaign, "CANCEL_REQUESTED", "SIGTERM"):
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                campaign.ensure_command_budget(1)

    def test_duplicate_phase_event_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stdout"
            row = {"event": "final_cleanup_usage", "payload": None}
            path.write_text(("MIXER_EXACT " + json.dumps(row) + "\n") * 2)
            with self.assertRaisesRegex(RuntimeError, "duplicate lifecycle event"):
                campaign.classify(path, {})

    def test_preserved_actual_failure_and_consuming_cleanup_classification(self):
        result = campaign.classify(HERE / "inputs/historical-attribution.stdout",
                                   {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})
        self.assertEqual(result["events"][0]["event"], "validation_budget")
        self.assertEqual(result["firstFailure"]["payload"]["resource"], "CacheWork")
        self.assertEqual(result["firstFailure"]["payload"]["attempted"], 64_000_001)
        self.assertEqual(result["firstFailure"]["payload"]["at_failure"]["instructions"], 23_358_291)
        self.assertTrue(result["consumingCleanup"])
        self.assertFalse(result["hostFeasibility"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["completeGuestObservations"], [])
        self.assertEqual(result["telemetry"]["status"], "valid")
        self.assertEqual(result["phaseOrder"], ["validation", "initialize", "corpus_1"])

    def test_corpus_oracle_suffix_begins_after_initialize_stdout(self):
        native = (HERE / "inputs/native-observation.json").read_text()
        template = campaign.classify(HERE / "inputs/historical-attribution.stdout",
                                      {"exitCode": 101, "timedOut": False, "processGroupEmpty": True})
        initialize = next(e["payload"] for e in template["events"] if e["event"] == "initialize")
        events = [{"event": "initialize", "payload": initialize | {"stdout": "initialization log\n"}}]
        for i, phase in enumerate(("corpus_1", "corpus_2"), 1):
            events.append({"event": phase, "payload": initialize | {"stdout": "initialization log\n" + native * i}})
            events.append({"event": "guest_output_native_equal", "payload": phase})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stdout"
            path.write_text("".join("MIXER_EXACT " + json.dumps(e) + "\n" for e in events))
            result = campaign.classify(path, {"exitCode": 0, "timedOut": False, "processGroupEmpty": True})
            self.assertEqual([r["rawSuffix"] for r in result["completeGuestObservations"]], [native, native])
            self.assertFalse(result["hostFeasibility"], "oracle suffix fixture has no consuming cleanup or real full result")


if __name__ == "__main__":
    unittest.main()
