#!/usr/bin/env python3
"""Independent, pure Python source/oracle checks; never runs a compiler or child."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE.parent / "swift-cache-capacity-campaign-v1"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


campaign = module("reviewed_campaign", CANDIDATE / "campaign.py")
producer = module("producer_controls", CANDIDATE / "test_campaign.py")
SOURCE, ARTIFACT, BINDINGS = campaign.inputs()
ROW = {"exitCode": 0, "timedOut": False, "processGroupEmpty": True}
HISTORICAL = campaign.classify(CANDIDATE / "inputs/historical-attribution.stdout", ROW | {"exitCode": 101})
NATIVE = (CANDIDATE / "inputs/native-observation.json").read_text()
INITIAL = next(e["payload"] for e in HISTORICAL["events"] if e["event"] == "initialize")


def oracle_events(first, second):
    base = "initializer output\n"
    return [
        {"event": "initialize", "payload": INITIAL | {"stdout": base}},
        {"event": "corpus_1", "payload": INITIAL | {"stdout": base + first}},
        {"event": "guest_output_native_equal", "payload": "corpus_1"},
        {"event": "corpus_2", "payload": INITIAL | {"stdout": base + first + second}},
        {"event": "guest_output_native_equal", "payload": "corpus_2"},
    ]


class IndependentChecks(unittest.TestCase):
    def classify_events(self, events):
        with tempfile.TemporaryDirectory(dir=HERE) as tmp:
            output = Path(tmp) / "stdout"
            output.write_text("".join("MIXER_EXACT " + json.dumps(e) + "\n" for e in events))
            return campaign.classify(output, ROW)

    def test_artifact_and_closed_harness_are_exact_original_bytes(self):
        self.assertEqual(BINDINGS["fieldlog-reactor.wasm.gz"]["bytes"], 18_976_211)
        self.assertEqual(BINDINGS["fieldlog-reactor.wasm.gz"]["sha256"], "e22a8226908ef68170ac94267978b4b436c45764bc591451ef16161d6dbd52ac")
        self.assertEqual(BINDINGS["harness.rs"]["sha256"], "8c7730239b38250671f7dc23cc46859ffd5b4b9253f1eabaf34f161c061ec078")
        self.assertEqual(BINDINGS["source.tar.gz"]["sha256"], "cdbf6b5826a354fa7796d3f4e4573b2fe62a213e4f3f5adf944cc2d2e44fbf18")
        self.assertEqual(HISTORICAL["firstFailure"]["payload"]["limit"], 64_000_000)
        self.assertFalse(HISTORICAL["hostFeasibility"])

    def test_all_unchanged_files_and_fresh_work_control_pair(self):
        allowed = {"src/experimental/cache/mod.rs", "src/experimental_swift_reactor/cache.rs",
                   "src/experimental_swift_reactor/cache_tests.rs", "src/experimental_swift_reactor/control.rs",
                   "src/experimental_swift_reactor/lifecycle_tests.rs", "src/experimental_swift_reactor/campaign_harness.rs"}
        variants = {}
        for label, residents, work in campaign.PRIMARY:
            candidate = campaign.parameterize(SOURCE, residents, work)
            changed = {n for n in candidate if candidate[n] != SOURCE.get(n)}
            self.assertTrue(changed <= allowed, changed - allowed)
            self.assertEqual(set(candidate) - set(SOURCE), {"src/experimental_swift_reactor/campaign_harness.rs"})
            self.assertEqual(set(SOURCE) - set(candidate), set())
            record, _ = campaign.source_record(SOURCE, candidate)
            retained = json.loads((CANDIDATE / "source-check" / label / "source.json").read_text())
            self.assertEqual(record, retained)
            variants[label] = candidate
        delta = {n for n in variants["baseline"] if variants["baseline"][n] != variants["work-only"][n]}
        self.assertEqual(delta, {"src/experimental_swift_reactor/control.rs"})
        baseline = variants["baseline"][next(iter(delta))]
        work_only = variants["work-only"][next(iter(delta))]
        self.assertEqual(work_only.replace(b"cache_work: 128000000,", b"cache_work: 64000000,"), baseline)

    def test_original_harness_preserves_one_owner_two_calls_and_consumption(self):
        harness = (CANDIDATE / "inputs/harness.rs").read_text()
        self.assertEqual(harness.count("Request::Corpus, \"corpus_1\""), 1)
        self.assertEqual(harness.count("Request::Corpus, \"corpus_2\""), 1)
        self.assertEqual(harness.count("full_attribution_begin();"), 1)
        self.assertIn("let success = phase(&mut owner, Request::Initialize", harness)
        self.assertIn("let clean = cleanup(owner);", harness)
        self.assertIn("tail.complete((owned, returned), &mut failure, &mut usage);", harness)
        self.assertIn("success && clean", harness)

    def test_oracle_rejects_labels_without_exact_typed_two_call_output(self):
        observation = json.loads(NATIVE)
        mutations = [
            NATIVE + NATIVE,
            json.dumps(observation | {"taskCount": True}),
            json.dumps(observation | {"taskCount": "1000"}),
            json.dumps(observation | {"extra": 1}),
            json.dumps({k: v for k, v in observation.items() if k != "unicodePreserved"}),
            NATIVE.rstrip()[:-1] + ',"taskCount":1000}',
        ]
        for changed in mutations:
            with self.subTest(changed=changed):
                with self.assertRaises((ValueError, RuntimeError)):
                    self.classify_events(oracle_events(NATIVE, changed))
        valid = self.classify_events(oracle_events(NATIVE, NATIVE))
        self.assertEqual(len(valid["completeGuestObservations"]), 2)
        self.assertFalse(valid["hostFeasibility"], "synthetic oracle-only fixture has no full-workload evidence")

    def test_oracle_rejects_rewritten_cumulative_stdout_and_duplicate_phase(self):
        events = oracle_events(NATIVE, NATIVE)
        events[3]["payload"] = events[3]["payload"] | {"stdout": NATIVE}
        with self.assertRaisesRegex(RuntimeError, "cumulative guest stdout mismatch"):
            self.classify_events(events)
        events = oracle_events(NATIVE, NATIVE)
        events.append(copy.deepcopy(events[1]))
        with self.assertRaisesRegex(RuntimeError, "duplicate lifecycle event"):
            self.classify_events(events)

    def test_self_hosted_and_nonlinux_guard_precedes_any_output_or_child(self):
        for hosted, system in (("self-hosted", "Linux"), ("github-hosted", "Darwin")):
            with self.subTest(hosted=hosted, system=system), tempfile.TemporaryDirectory(dir=HERE) as tmp:
                output = Path(tmp) / "forbidden-output"
                with patch.dict(campaign.os.environ, {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": hosted}, clear=True), \
                     patch.object(campaign.platform, "system", return_value=system), \
                     patch.object(campaign.subprocess, "Popen", side_effect=AssertionError("child forbidden")):
                    with self.assertRaisesRegex(RuntimeError, "local execution remains held"):
                        campaign.run(output, False)
                self.assertFalse(output.exists())


def main():
    start = time.monotonic()
    output = io.StringIO()
    suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromModule(producer),
                               unittest.defaultTestLoader.loadTestsFromTestCase(IndependentChecks)))
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    (HERE / "pure-controls.stdout").write_text(output.getvalue())
    paths = [CANDIDATE / name for name in ("campaign.py", "campaign-controls.rs", "workflow.yml", "test_campaign.py", "README.md")]
    paths += sorted(p for p in (CANDIDATE / "inputs").iterdir() if p.is_file())
    pins = {str(p.relative_to(CANDIDATE)): {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths}
    record = {"model": "gpt-6-astra", "reasoningEffort": "xhigh", "command": "python3 -B verification/swift-cache-capacity-campaign-independent/review.py",
              "policyRevision": "b6410e917fab899731dece2678fe2ade2e854464", "python": sys.version,
              "platform": platform.platform(), "seconds": time.monotonic() - start,
              "testsRun": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "successful": result.wasSuccessful(), "candidatePins": pins,
              "scope": "source/data and adversarial parser checks only; no compiler, guest, native, process inventory, PID or custody tests",
              "cleanup": {"temporaryOracleFilesRemoved": True, "compilerOrRuntimeProcessesStarted": False},
              "profiles": [{"name": label, "residents": n, "cacheWork": work, "sourceSHA256": campaign.source_record(SOURCE, campaign.parameterize(SOURCE, n, work))[0]["sha256"]} for label, n, work in campaign.PRIMARY]}
    (HERE / "receipt.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: record[k] for k in ("testsRun", "failures", "errors", "successful", "seconds")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
