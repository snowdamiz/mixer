"""Host-only controls for narrow replay selection and interrupted evidence."""
import copy
import json
import pathlib
import tempfile
import unittest
from unittest import mock
import bridge
import harness
from test_controls import observation

class DurableBridgeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mixer-origin-host-")
        self.base = pathlib.Path(self.temp.name).resolve()
        self.documents = {name: self.base / name for name in ("diagnostic", "comparator")}
        for path in self.documents.values(): path.mkdir()
        self.capability = "never-retain-this-host-capability"
        self.bridge = bridge.Bridge(self.documents, self.base / "evidence", self.capability,
                                    {"scope": "host-only"}, allowed_cases=harness.SCOPES["interaction"]["cases"])
    def tearDown(self): self.temp.cleanup()
    def summary(self): return json.loads((self.base / "evidence/bridge-summary.json").read_text())
    def begin(self): self.bridge.request("begin", {"candidate": "diagnostic", "case": "standalone-pan"})
    def test_initial_summary_distinguishes_no_observation_from_empty_failures(self):
        result=self.summary(); self.assertFalse(result["lastValidObservationAvailable"]); self.assertEqual(result["failures"], [])
    def test_direct_case_cannot_enter_interaction_scope(self):
        with self.assertRaises(ValueError): self.bridge.request("begin", {"candidate":"diagnostic", "case":"diagnostic-direct"})
        self.assertEqual(len(self.summary()["failures"]), 1)
    def test_unknown_scope_rejected(self):
        with self.assertRaises(ValueError): bridge.Bridge(self.documents,self.base/"bad",self.capability,{},allowed_cases={"arbitrary"})
    def test_request_failure_durable_without_shutdown(self):
        with self.assertRaises(ValueError): self.bridge.request("ready",{})
        result=self.summary(); self.assertEqual(result["failures"][0]["operation"],"ready")
        self.assertEqual(len(list((self.base/"evidence").glob("*-failure-*.json"))),1)
    def test_failure_without_valid_observation_is_unavailable(self):
        self.begin()
        with self.assertRaises(ValueError): self.bridge.request("command",{"command":"resume"})
        result=self.summary(); self.assertFalse(result["lastValidObservationAvailable"])
        receipt=json.loads(next((self.base/"evidence").glob("*-failure-*.json")).read_text())
        self.assertIsNone(receipt["lastValidObservation"])
    def test_last_valid_partial_direct_observation_retained(self):
        self.begin(); value=observation(); value["checks"]=[{"name":"partial-check", "pass":False}]
        (self.documents["diagnostic"]/"observations.json").write_text(json.dumps(value))
        self.bridge.observe()
        with self.assertRaises(ValueError): self.bridge.request("baseline",{})
        receipt=json.loads(next((self.base/"evidence").glob("*-failure-*.json")).read_text())
        self.assertEqual(receipt["lastValidObservation"]["observation"]["checks"],value["checks"])
    def test_capability_redacted_from_error_reason_and_every_file(self):
        self.bridge.record_failure("ready", ValueError(self.capability))
        self.assertFalse(any(self.capability.encode() in path.read_bytes() for path in (self.base/"evidence").iterdir()))
    def test_independent_failures_are_not_overwritten(self):
        for op in ("ready","baseline","evaluate"):
            with self.assertRaises(ValueError): self.bridge.request(op,{})
        self.assertEqual([value["sequence"] for value in self.summary()["failures"]],[1,2,3])
    def test_begin_fresh_generation_discards_previous_last_valid_observation(self):
        self.begin(); (self.documents["diagnostic"]/"observations.json").write_text(json.dumps(observation()))
        self.bridge.observe()
        self.bridge.request("begin",{"candidate":"diagnostic","case":"ltr-on"})
        # begin may safely observe the existing file; it is a prior signature,
        # never a new-launch acknowledgement or a verdict.
        self.assertFalse(self.bridge.current.get("ready",False)); self.assertEqual(self.bridge.verdicts,[])
    def test_observation_invalid_inode_metadata_is_diagnostic(self):
        self.begin(); path=self.documents["diagnostic"]/"observations.json"; path.write_text(json.dumps(observation()))
        import os
        os.link(path,self.documents["diagnostic"]/"hardlink")
        with self.assertRaisesRegex(ValueError,"links=2"):
            self.bridge.observe()

class InterruptedSummaryControls(unittest.TestCase):
    def test_interaction_scope_exactly_ten_methods_thirteen_evaluations(self):
        scope=harness.SCOPES["interaction"]
        self.assertEqual(len(scope["methods"]),10)
        summary=harness.runtime_summary("interaction",None,None,None,None)
        self.assertEqual(sum(summary["expectedCaseEvaluations"].values()),13)
        self.assertEqual(len(scope["cases"]),10)
    def test_direct_scope_exactly_two_original_methods(self):
        scope=harness.SCOPES["direct"]; self.assertEqual(len(scope["methods"]),2)
        self.assertEqual(scope["cases"],{"diagnostic-direct","comparator-direct"})
    def test_no_bridge_or_xctest_evidence_never_becomes_empty_success(self):
        result=harness.runtime_summary("interaction",None,None,{"type":"TimeoutExpired"},[])
        self.assertIsNone(result["bridgeFailures"]); self.assertIsNone(result["nativeUserInteractionVerdicts"])
        self.assertIsNone(result["actualCaseEvaluations"]); self.assertIsNone(result["strictNativeVerdictsPassed"])
        self.assertFalse(result["xcodebuildTerminalResultAvailable"]); self.assertFalse(result["runPassed"])
    def fixture_bridge(self, scope="interaction"):
        class Evidence: pass
        value=Evidence(); value.failures=[]; value.verdicts=[]
        for name in harness.SCOPES[scope]["cases"]:
            for index in range(2 if name.endswith("taps") else 1):
                value.verdicts.append(dict(case=name,passed=True,action="direct-suite" if name.endswith("-direct") else "authored-tap"))
        return value
    def test_complete_actions_do_not_turn_timeout_into_success(self):
        result=harness.runtime_summary("interaction",self.fixture_bridge(),None,{"type":"TimeoutExpired"},[{"passed":True}])
        self.assertTrue(result["completeCaseSet"]); self.assertTrue(result["strictNativeVerdictsPassed"])
        self.assertFalse(result["runPassed"])
    def test_one_missing_evaluation_fails_closed(self):
        value=self.fixture_bridge(); value.verdicts.pop()
        self.assertFalse(harness.runtime_summary("interaction",value,0,None,[{"passed":True}])["runPassed"])
    def test_strict_failure_remains_failure(self):
        value=self.fixture_bridge(); value.verdicts[0]["passed"]=False
        self.assertFalse(harness.runtime_summary("interaction",value,0,None,[{"passed":True}])["runPassed"])
    def test_bridge_failure_remains_failure_even_after_all_actions_pass(self):
        value=self.fixture_bridge(); value.failures=[{"reason":"durable-native-read-failure"}]
        self.assertFalse(harness.runtime_summary("interaction",value,0,None,[{"passed":True}])["runPassed"])
    def test_absent_cleanup_evidence_never_passes(self):
        self.assertFalse(harness.runtime_summary("interaction",self.fixture_bridge(),0,None,None)["runPassed"])
    def test_cleanup_failure_never_passes(self):
        self.assertFalse(harness.runtime_summary("interaction",self.fixture_bridge(),0,None,[{"passed":False}])["runPassed"])
    def test_complete_host_fixture_reports_only_selected_interactions(self):
        result=harness.runtime_summary("interaction",self.fixture_bridge(),0,None,[{"passed":True}])
        self.assertTrue(result["runPassed"])
        self.assertEqual(result["directOriginalScope"],"not-selected-pending-historical-failures-retained")
        self.assertFalse(result["carrierAccepted"])

class RunnerFinallyControls(unittest.TestCase):
    def test_pre_native_failure_writes_final_summary_and_unavailable_fields(self):
        with tempfile.TemporaryDirectory(prefix="mixer-finally-host-") as directory:
            base=pathlib.Path(directory).resolve()
            class FailingCommands:
                def __init__(self,*args): self.events=[]
                def simctl(self,*args,**kwargs): raise TimeoutError("host fault before native creation; no subprocess executed")
                def record(self,*args): self.events.append(args)
                def redact(self,value): return value
            with mock.patch.object(harness,"BASE",base), mock.patch.object(harness,"RUN_DIR",base/"unused"), \
                 mock.patch.object(harness,"verify",return_value={"sealSHA256":"host-reviewed"}), mock.patch.object(harness,"Commands",FailingCommands):
                with self.assertRaises(TimeoutError): harness.run("host-reviewed", "interaction")
            result=json.loads((base/"runtime/runtime-verdict.json").read_text())
            self.assertEqual(result["sessionFailure"]["type"],"TimeoutError")
            self.assertIsNone(result["bridgeFailures"]); self.assertIsNone(result["actualCaseEvaluations"])
            self.assertFalse(result["runPassed"]); self.assertFalse(result["xcodebuildTerminalResultAvailable"])
    def test_direct_runtime_is_separate_and_closed(self):
        self.assertNotEqual(harness.select_runtime_directory("interaction"),harness.select_runtime_directory("direct"))
        with self.assertRaises(ValueError): harness.select_runtime_directory("unknown")

if __name__ == "__main__": unittest.main(verbosity=2)
