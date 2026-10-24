"""Host-only negative controls. No UIKit, simulator, native input, or device use."""
import copy
import http.client
import json
import pathlib
import tempfile
import threading
import time
import sys
import subprocess
import hashlib
import tarfile
import unittest
from unittest import mock
import bridge
from bridge import Bridge, read_observation, server_for
from oracle import EXPECTED_CHECK_NAMES, geometry_valid, verdict
import harness

def observation():
    state = dict(identity="native-carrier-A", isOn=False, retainedOn=False, enabled=True, allowed=True, rtl=False, panAcceptedCount=0, primaryCount=0, eventCount=0, eventValues=[], scrollOffsetY=0, panActive=False, previewThumbX=None)
    return dict(stage="initial", state=state, events=[dict(sequence=0, reason="initial", state=copy.deepcopy(state))], checks=[], diagnosticTrace=[], diagnosticTraceDropped=0, reference=dict(identity="plain-A", selected=False, primaryCount=0, valueCount=0, primaryValues=[], attachedToWindow=True))

def native_trace(prefix, pan_kind, nested=False):
    values = [dict(kind=prefix+"TouchesBegan", timestamp=1., phase=0, locationInWindow=dict(x=0, y=0)), dict(kind=prefix+"TouchesMoved", timestamp=1.1, phase=1, locationInWindow=dict(x=8, y=0)), dict(kind=prefix+"TouchesCancelled", timestamp=1.2, phase=4, locationInWindow=dict(x=14, y=0))]
    for index, state in enumerate((1, 2, 3)):
        value = dict(kind=pan_kind, uptime=1.2 + index * 0.15)
        gesture={"state":state,"identity":"native-pan-A","translationInWindow":{"x":0 if nested else 8+index*15,"y":-8-index*15 if nested else 0}}
        if nested:value["gesture"]=gesture
        else:value.update(gesture)
        values.append(value)
    for index, value in enumerate(values): value.update(sequence=index+1, uptime=value.get("uptime", value.get("timestamp")))
    return values

def passing_reference():
    b=observation(); a=copy.deepcopy(b); a["diagnosticTrace"]=native_trace("reference", "referencePan")
    return b,a

def passing_authored():
    b=observation(); a=copy.deepcopy(b)
    a["diagnosticTrace"]=native_trace("carrier", "authoredPanCallback")
    a["diagnosticTrace"].append(dict(sequence=7, uptime=1.6, kind="shouldBeginDecision", isAuthoredPan=True, result=True))
    preview=copy.deepcopy(b["state"]); preview.update(panActive=True, previewThumbX=14)
    a["events"].append(dict(sequence=1, reason="panPreview", state=preview))
    a["state"].update(isOn=True, retainedOn=True, panAcceptedCount=1, eventCount=1, eventValues=[True])
    return b,a

class VerdictControls(unittest.TestCase):
    def test_reference_positive_host_fixture(self):
        b,a=passing_reference(); self.assertTrue(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_cancelled_view_delivery_with_real_pan_translation_is_valid(self):
        b,a=passing_reference(); a["diagnosticTrace"][1]["kind"]="referenceTouchesEnded"
        result=verdict("diagnostic","standalone-pan","reference-pan",b,a)
        self.assertTrue(result["passed"]);self.assertNotIn("referenceTouchesMoved",result["viewTouchObservations"]["kinds"])
    def test_callback_states_without_native_translation_fail(self):
        b,a=passing_reference()
        for entry in a["diagnosticTrace"]:
            if entry["kind"]=="referencePan":entry.pop("translationInWindow")
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_stationary_native_pan_translation_fails(self):
        b,a=passing_reference()
        for entry in a["diagnosticTrace"]:
            if entry["kind"]=="referencePan":entry["translationInWindow"]={"x":10,"y":0}
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_wrong_native_translation_direction_fails(self):
        b,a=passing_reference()
        for entry in a["diagnosticTrace"]:
            if entry["kind"]=="referencePan":entry["translationInWindow"]["x"]*=-1
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_different_pan_identities_fail(self):
        b,a=passing_reference();a["diagnosticTrace"][-1]["identity"]="replacement-pan"
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_submillisecond_delivery_is_failure(self):
        b,a=passing_reference()
        for index,e in enumerate(a["diagnosticTrace"]): e.update(timestamp=1+index*.0001,uptime=1+index*.0001)
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_missing_pan_changed_is_failure(self):
        b,a=passing_reference(); a["diagnosticTrace"][4]["state"]=1
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_trace_overflow_is_failure(self):
        b,a=passing_reference(); a["diagnosticTraceDropped"]=1
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_trace_gap_is_failure(self):
        b,a=passing_reference(); a["diagnosticTrace"][1]["sequence"]=99
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_old_trace_cannot_supply_new_movement(self):
        b,a=passing_reference(); b["diagnosticTrace"]=copy.deepcopy(a["diagnosticTrace"])
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_unchanged_file_cannot_pass(self):
        b,a=passing_reference(); self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a,False)["passed"])
    def test_generation_identity_change_fails(self):
        b,a=passing_reference(); a["state"]["identity"]="replaced"
        self.assertFalse(verdict("diagnostic","standalone-pan","reference-pan",b,a)["passed"])
    def test_scroll_positive_host_fixture(self):
        b=observation();a=copy.deepcopy(b);a["diagnosticTrace"]=native_trace("unused","scrollPanCallback",True);a["state"]["scrollOffsetY"]=80
        self.assertTrue(verdict("diagnostic","blank-scroll","blank-scroll",b,a)["passed"])
    def test_scroll_zero_at_top_is_failure(self):
        b=observation();a=copy.deepcopy(b);a["diagnosticTrace"]=native_trace("unused","scrollPanCallback",True)
        self.assertFalse(verdict("diagnostic","blank-scroll","blank-scroll",b,a)["passed"])
    def test_scroll_offset_without_callbacks_is_failure(self):
        b=observation();a=copy.deepcopy(b);a["state"]["scrollOffsetY"]=80
        self.assertFalse(verdict("diagnostic","blank-scroll","blank-scroll",b,a)["passed"])
    def test_authored_positive_host_fixture(self):
        b,a=passing_authored();self.assertTrue(verdict("diagnostic","ltr-on","authored-pan",b,a)["passed"])
    def test_pan_without_preview_is_failure(self):
        b,a=passing_authored();a["events"]=a["events"][:1]
        self.assertFalse(verdict("diagnostic","ltr-on","authored-pan",b,a)["passed"])
    def test_preview_committing_state_is_failure(self):
        b,a=passing_authored();a["events"][1]["state"]["isOn"]=True
        self.assertFalse(verdict("diagnostic","ltr-on","authored-pan",b,a)["passed"])
    def test_pan_primary_dispatch_is_failure(self):
        b,a=passing_authored();a["state"]["primaryCount"]=1
        self.assertFalse(verdict("diagnostic","ltr-on","authored-pan",b,a)["passed"])
    def test_wrong_directional_initial_state_is_failure(self):
        b,a=passing_authored();self.assertFalse(verdict("diagnostic","ltr-off","authored-pan",b,a)["passed"])
    def test_wrong_rtl_premise_is_failure(self):
        b,a=passing_authored();self.assertFalse(verdict("diagnostic","rtl-on","authored-pan",b,a)["passed"])
    def test_pan_and_scroll_together_is_failure(self):
        b,a=passing_authored();a["state"]["scrollOffsetY"]=30
        self.assertFalse(verdict("diagnostic","ltr-on","authored-pan",b,a)["passed"])
    def test_vacuous_off_state_tap_is_failure(self):
        b=observation();a=copy.deepcopy(b);a["state"].update(primaryCount=1,eventCount=1,eventValues=[False])
        self.assertFalse(verdict("comparator","comparator-taps","authored-tap",b,a)["passed"])
    def test_duplicate_value_tap_is_failure(self):
        b=observation();a=copy.deepcopy(b);a["state"].update(isOn=True,retainedOn=True,primaryCount=1,eventCount=2,eventValues=[True,True])
        self.assertFalse(verdict("comparator","comparator-taps","authored-tap",b,a)["passed"])
    def test_plain_unchanged_selection_is_failure(self):
        b=observation();a=copy.deepcopy(b);a["reference"]["primaryCount"]=1
        self.assertFalse(verdict("diagnostic","plain-taps","plain-tap",b,a)["passed"])
    def test_plain_value_count_observed_without_unsupported_zero_contract(self):
        b=observation();a=copy.deepcopy(b);a["reference"].update(selected=True,primaryCount=1,valueCount=1,primaryValues=[True])
        self.assertTrue(verdict("diagnostic","plain-taps","plain-tap",b,a)["passed"])
    def test_original_eight_false_are_retained_failure(self):
        b=observation();a=copy.deepcopy(b)
        a["checks"]=[{"name":str(i),"pass":i<11} for i in range(19)];a["diagnosticSuiteState"]="complete"
        result=verdict("diagnostic","diagnostic-direct","direct-suite",b,a)
        self.assertFalse(result["passed"]);self.assertEqual(result["originalChecks"],a["checks"])
    def test_partial_suite_cannot_pass(self):
        b=observation();a=copy.deepcopy(b);a["checks"]=[{"name":str(i),"pass":True} for i in range(4)];a["diagnosticSuiteState"]="running"
        self.assertFalse(verdict("diagnostic","diagnostic-direct","direct-suite",b,a)["passed"])
    def test_nineteen_true_without_completion_fails(self):
        b=observation();a=copy.deepcopy(b);a["checks"]=[{"name":str(i),"pass":True} for i in range(19)]
        self.assertFalse(verdict("diagnostic","diagnostic-direct","direct-suite",b,a)["passed"])
    def test_duplicate_check_name_fails(self):
        b=observation();a=copy.deepcopy(b);a["checks"]=[{"name":"same","pass":True} for _ in range(19)];a["diagnosticSuiteState"]="complete"
        self.assertFalse(verdict("diagnostic","diagnostic-direct","direct-suite",b,a)["passed"])
    def test_true_checks_with_different_names_fail(self):
        b=observation();a=copy.deepcopy(b);a["checks"]=[{"name":str(i),"pass":True} for i in range(19)];a["diagnosticSuiteState"]="complete"
        self.assertFalse(verdict("diagnostic","diagnostic-direct","direct-suite",b,a)["passed"])
    def test_all_original_checks_true_positive_host_control(self):
        b=observation();a=copy.deepcopy(b);a["checks"]=[{"name":name,"pass":True} for name in EXPECTED_CHECK_NAMES["diagnostic"]];a["diagnosticSuiteState"]="complete"
        self.assertTrue(verdict("diagnostic","diagnostic-direct","direct-suite",b,a)["passed"])
    def test_unknown_action_fails(self):
        b=observation();self.assertFalse(verdict("diagnostic","standalone-pan","unsupported",b,b)["passed"])

class BridgeControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="mixer-toggle-xctest-host-");self.base=pathlib.Path(self.temp.name).resolve()
        self.docs={key:self.base/key for key in ("diagnostic","comparator")}
        for path in self.docs.values(): path.mkdir()
        self.capability="host-control-secret-never-retain"
        self.bridge=Bridge(self.docs,self.base/"evidence",self.capability,{"udid":"host-only-no-device"})
    def tearDown(self): self.temp.cleanup()
    def write(self,key="diagnostic",value=None):
        path=self.docs[key]/"observations.json";path.write_text(json.dumps(value or observation()));return path
    def begin(self): self.bridge.request("begin",{"candidate":"diagnostic","case":"standalone-pan"})
    def test_unknown_path_endpoint_rejected(self):
        with self.assertRaises(ValueError):self.bridge.request("begin",{"candidate":"/tmp","case":"standalone-pan"})
    def test_case_candidate_crossing_rejected(self):
        with self.assertRaises(ValueError):self.bridge.request("begin",{"candidate":"diagnostic","case":"comparator-taps"})
    def test_closed_extra_field_rejected(self):
        with self.assertRaises(ValueError):self.bridge.request("begin",{"candidate":"diagnostic","case":"standalone-pan","path":"/tmp"})
    def test_ready_cannot_reuse_stale_file(self):
        self.write();self.begin()
        def blocked(predicate,seconds=6):
            value,signature=self.bridge.observe();self.assertFalse(predicate(value,signature));raise TimeoutError()
        with mock.patch.object(self.bridge,"wait",blocked),self.assertRaises(TimeoutError):self.bridge.request("ready",{})
    def test_ready_accepts_new_initial_generation_only(self):
        self.write();self.begin();self.write()
        result=self.bridge.request("ready",{});self.assertEqual(result["generation"],1)
    def test_observation_symlink_rejected(self):
        other=self.base/"elsewhere";other.write_text(json.dumps(observation()));(self.docs["diagnostic"]/"observations.json").symlink_to(other)
        with self.assertRaises(ValueError):read_observation(self.docs["diagnostic"])
    def test_observation_hardlink_rejected(self):
        import os
        other=self.base/"elsewhere";other.write_text(json.dumps(observation()));os.link(other,self.docs["diagnostic"]/"observations.json")
        with self.assertRaises(ValueError):read_observation(self.docs["diagnostic"])
    def test_unknown_command_rejected_before_write(self):
        self.begin();self.write();self.bridge.request("ready",{})
        with self.assertRaises(ValueError):self.bridge.request("command",{"command":"shell:rm"})
        self.assertEqual((self.docs["diagnostic"]/"command.txt").read_text(),"reset")
    def test_case_command_order_rejected(self):
        self.begin();self.write();self.bridge.request("ready",{})
        with self.assertRaises(ValueError):self.bridge.request("command",{"command":"rtl"})
    def test_command_ack_requires_new_event_and_stage(self):
        self.begin();self.write();self.bridge.request("ready",{})
        def blocked(predicate,seconds=6):
            value,signature=self.bridge.observe();value["stage"]="resume";signature[0]+=1
            self.assertFalse(predicate(value,signature));raise TimeoutError()
        with mock.patch.object(self.bridge,"wait",blocked),self.assertRaises(TimeoutError):self.bridge.request("command",{"command":"resume"})
    def test_command_hardlink_not_truncated(self):
        import os
        self.begin();self.write();self.bridge.request("ready",{})
        other=self.base/"important";other.write_text("preserve");(self.docs["diagnostic"]/"command.txt").unlink();os.link(other,self.docs["diagnostic"]/"command.txt")
        with self.assertRaises(ValueError):self.bridge.request("command",{"command":"resume"})
        self.assertEqual(other.read_text(),"preserve")
    def test_same_stage_command_not_acknowledged(self):
        self.begin();self.write(value={**observation(),"stage":"reset"});self.bridge.request("ready",{})
        with self.assertRaises(ValueError):self.bridge.request("command",{"command":"reset"})
    def test_generation_change_rejected(self):
        self.begin();self.write();self.bridge.request("ready",{});value=observation();value["state"]["identity"]="other";self.write(value=value)
        with self.assertRaises(ValueError):self.bridge.request("command",{"command":"reset"})
    def test_geometry_rejects_nonfinite_or_extra_fields(self):
        valid={"app":{"x":0,"y":0,"width":100,"height":200},"target":{"x":1,"y":1,"width":20,"height":20}}
        self.assertTrue(geometry_valid(valid));valid["target"]["x"]=float("nan");self.assertFalse(geometry_valid(valid));valid["target"]["x"]=1;valid["shell"]="command";self.assertFalse(geometry_valid(valid))
    def http(self,path,body,capability=None,extra=None):
        server=server_for(self.bridge);thread=threading.Thread(target=server.serve_forever);thread.start()
        try:
            client=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=3)
            client.request("POST",path,body=body,headers={"Content-Type":"application/json","X-Mixer-Capability":capability or self.capability,**(extra or {})})
            result=client.getresponse();data=result.read();client.close();return result.status,json.loads(data)
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
    def test_http_unauthorized_rejected(self):self.assertEqual(self.http("/begin",b"{}",capability="wrong")[0],400)
    def test_http_unknown_endpoint_rejected(self):self.assertEqual(self.http("/arbitrary",b"{}")[0],400)
    def test_http_oversized_body_rejected(self):self.assertEqual(self.http("/begin",b"x"*8193)[0],400)
    def test_http_duplicate_json_key_rejected(self):self.assertEqual(self.http("/begin",b'{"candidate":"diagnostic","candidate":"comparator","case":"standalone-pan"}')[0],400)
    def test_http_capability_not_saved(self):
        self.assertEqual(self.http("/begin",b'{"candidate":"diagnostic","case":"standalone-pan"}')[0],200)
        self.assertFalse(any(self.capability.encode() in p.read_bytes() for p in (self.base/"evidence").glob("*")))

class LifecycleControls(unittest.TestCase):
    def fixture(self):
        before={"devices":{"baseline-runtime":[dict(udid="baseline",state="Booted",name="Other project")]}}
        owned=dict(udid="owned",state="Booted",name="unique",deviceTypeIdentifier=harness.DEVICE_TYPE)
        current={"devices":{**before["devices"],harness.RUNTIME:[owned]}}
        lifecycle=dict(ownedSimulator="owned",ownedName="unique",before=before)
        return lifecycle,current
    def test_baseline_ownership_refused(self):
        lifecycle,current=self.fixture();lifecycle["ownedSimulator"]="baseline"
        with self.assertRaises(ValueError):harness.owned_device(lifecycle,current)
    def test_owned_runtime_identity_required(self):
        lifecycle,current=self.fixture();current["devices"]["different"]=current["devices"].pop(harness.RUNTIME)
        with self.assertRaises(ValueError):harness.owned_device(lifecycle,current)
    def test_owned_name_identity_required(self):
        lifecycle,current=self.fixture();current["devices"][harness.RUNTIME][0]["name"]="other"
        with self.assertRaises(ValueError):harness.owned_device(lifecycle,current)
    def test_absent_owned_allowed_for_cleanup(self):
        lifecycle,_=self.fixture();self.assertIsNone(harness.owned_device(lifecycle,lifecycle["before"]))
    def test_exact_owned_identity_accepted(self):
        lifecycle,current=self.fixture();self.assertEqual(harness.owned_device(lifecycle,current)["udid"],"owned")
    def test_unrelated_container_rejected(self):
        with self.assertRaises(ValueError): harness.validate_container("/tmp", "owned", data=True)
    def test_lost_create_response_exact_fresh_identity_reconciled(self):
        lifecycle,current=self.fixture();lifecycle["ownedSimulator"]=None
        self.assertEqual(harness.reconcile_creation(lifecycle,current)["udid"],"owned")
    def test_reconciliation_never_takes_baseline_same_name(self):
        lifecycle,current=self.fixture();lifecycle["ownedSimulator"]=None
        lifecycle["before"]=copy.deepcopy(current)
        self.assertIsNone(harness.reconcile_creation(lifecycle,current))
    def test_reconciliation_rejects_ambiguous_fresh_instances(self):
        lifecycle,current=self.fixture();lifecycle["ownedSimulator"]=None
        extra=copy.deepcopy(current["devices"][harness.RUNTIME][0]);extra["udid"]="second"
        current["devices"][harness.RUNTIME].append(extra)
        with self.assertRaises(ValueError):harness.reconcile_creation(lifecycle,current)
    def test_reconciliation_never_takes_other_runtime(self):
        lifecycle,current=self.fixture();lifecycle["ownedSimulator"]=None;current["devices"]["different"]=current["devices"].pop(harness.RUNTIME)
        self.assertIsNone(harness.reconcile_creation(lifecycle,current))
    def test_resource_failure_does_not_skip_later_cleanup(self):
        observed=[]
        def fail():observed.append("failed");raise RuntimeError("owned failure")
        def succeed():observed.append("succeeded")
        result=harness.cleanup_independently([("server",fail),("simulator",succeed)])
        self.assertEqual(observed,["failed","succeeded"]);self.assertEqual([row["passed"] for row in result],[False,True])
    def test_cleanup_targets_only_recorded_owned_identity(self):
        lifecycle,current=self.fixture();observed=[]
        class Commands:
            def simctl(self,*args):
                observed.append(args)
                if args[:2]==("list","devices"):return json.dumps(current)
                self_id=next(iter(current["devices"][harness.RUNTIME]),{}).get("udid")
                if args[0]=="shutdown":
                    if args[1]!=self_id:raise AssertionError("Wrong device")
                    current["devices"][harness.RUNTIME][0]["state"]="Shutdown"
                elif args[0]=="delete":
                    if args[1]!=self_id:raise AssertionError("Wrong device")
                    current["devices"][harness.RUNTIME]=[]
            def run(self,*args,**kwargs):return 0,"",""
        with tempfile.TemporaryDirectory(prefix="mixer-toggle-cleanup-host-") as directory,mock.patch.object(harness,"RUN_DIR",pathlib.Path(directory)):
            harness.cleanup(lifecycle,Commands())
        self.assertIn(("shutdown","owned"),observed);self.assertIn(("delete","owned"),observed);self.assertTrue(lifecycle["baselineStatesPreserved"])
    def test_interrupted_owned_host_command_output_preserved(self):
        with tempfile.TemporaryDirectory(prefix="mixer-toggle-command-host-") as directory:
            commands=harness.Commands(pathlib.Path(directory)/"commands.json")
            with self.assertRaises(subprocess.TimeoutExpired):commands.run([sys.executable,"-c","import time;print('owned-control-start',flush=True);time.sleep(10)"],timeout=.1)
            self.assertIn("owned-control-start",commands.events[-1]["stdout"])
            self.assertEqual(commands.events[-1]["kind"],"command-interrupted")

class RunnerArchiveControls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="mixer-toggle-archive-host-");self.base=pathlib.Path(self.temp.name).resolve()
        self.products=self.base/"Products";self.products.mkdir();(self.products/"Runner.app").mkdir();(self.products/"Runner.app/binary").write_bytes(b"host-fixture-only")
        self.archive=self.base/"products.tar.gz"
        self.patch1=mock.patch.object(harness,"PRODUCTS",self.products);self.patch1.start()
        self.patch2=mock.patch.object(harness,"PRODUCT_ARCHIVE",self.archive);self.patch2.start()
        entries=harness.tree(self.products);digest=harness.archive_products(entries)
        self.manifest={"products":entries,"productArchiveSHA256":digest}
    def tearDown(self):self.patch2.stop();self.patch1.stop();self.temp.cleanup()
    def test_exact_regular_runner_payload_validates(self):self.assertEqual(harness.product_archive_payload(self.manifest),{"Runner.app/binary":b"host-fixture-only"})
    def test_changed_runner_archive_rejected(self):
        self.archive.write_bytes(self.archive.read_bytes()+b"changed")
        with self.assertRaises(ValueError):harness.product_archive_payload(self.manifest)
    def test_extra_runner_path_rejected_even_with_matching_outer_digest(self):
        with tarfile.open(self.archive,"w:gz") as archive:archive.addfile(tarfile.TarInfo("../outside"))
        self.manifest["productArchiveSHA256"]=harness.sha(self.archive)
        with self.assertRaises(ValueError):harness.product_archive_payload(self.manifest)
    def test_runner_archive_missing_entry_rejected(self):
        with tarfile.open(self.archive,"w:gz"):pass
        self.manifest["productArchiveSHA256"]=harness.sha(self.archive)
        with self.assertRaises(ValueError):harness.product_archive_payload(self.manifest)

if __name__ == "__main__": unittest.main(verbosity=2)
