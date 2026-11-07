"""Prepared v2 data controls. Explicit owned fixture root is mandatory.

No compiler, custody helper, product source, or workflow is imported/executed.
Only sealed pure file/data modules are imported after the active-operation guard.
"""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
def guard(event,args):
    if event.startswith(("subprocess","socket","ctypes")) or event in (
        "os.system","os.posix_spawn","os.posix_spawnp","os.fork","os.forkpty","os.kill","os.killpg","os.exec","pty.spawn"):
        raise RuntimeError("Pure controls denied "+event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("Non-stdlib import denied "+args[0])
sys.addaudithook(guard)
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib
HERE = Path(__file__).resolve().parent
FIXTURES = None

def load_pure(name):
    if name not in ("source_contract.py","java_api_floor.py","tool_data.py"):
        raise RuntimeError("Only named sealed pure data modules may load")
    seal_path = HERE/"seal.json"
    if seal_path.stat().st_size > 65536:
        raise RuntimeError("Bounded v2 seal required")
    seal = json.loads(seal_path.read_bytes())
    row = next(r for r in seal["members"] if r["path"] == name)
    path = HERE/name
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 524288:
        raise RuntimeError("Bounded ordinary pure module required")
    data = path.read_bytes()
    if {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()} != {k:row[k] for k in ("bytes","sha256")}:
        raise RuntimeError("Pure module changed")
    spec = importlib.util.spec_from_file_location("pair7_v2_control_"+name[:-3],path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

c,floor,tool = load_pure("source_contract.py"),load_pure("java_api_floor.py"),load_pure("tool_data.py")

def owned_fixture_root(value):
    if not isinstance(value,str) or not value:
        raise RuntimeError("Explicit MIXER_PAIR7_CONTROL_ROOT required; no tempfile fallback")
    path = Path(value)
    if not path.is_absolute() or path.parent.resolve(strict=True) != path.parent or os.path.lexists(path):
        raise RuntimeError("Fresh owned fixture root with ordinary parent required")
    return path

def synthetic_dex(owner="demo/Example",descriptor=None):
    name = (descriptor or ("L"+owner+";")).encode("ascii")
    data = bytearray(152); data[:8] = b"dex\n035\0"
    struct.pack_into("<II",data,56,1,112); struct.pack_into("<II",data,64,1,116)
    struct.pack_into("<II",data,96,1,120); struct.pack_into("<I",data,112,152)
    struct.pack_into("<I",data,116,0); struct.pack_into("<I",data,120,0)
    data.extend(bytes([len(name)])+name+b"\0")
    struct.pack_into("<III",data,32,len(data),112,0x12345678)
    struct.pack_into("<II",data,104,len(data)-152,152)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I",data,8,zlib.adler32(data[12:]))
    return bytes(data)

class Clock:
    def __init__(self,now=0,step=0): self.now,self.step = now,step
    def __call__(self):
        value = self.now; self.now += self.step
        return value

class PureControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if FIXTURES is None:
            raise RuntimeError("Run this file directly with the selected owned fixture root")
        cls.source = FIXTURES/"source-closure"; (cls.source/"sources").mkdir(parents=True)
        cls.source_blob = b"s"*2779239
        rows = []
        for index in range(142):
            name = "sources/f"+str(index).zfill(3)+".bin"
            data = cls.source_blob if index == 0 else b""
            (cls.source/name).write_bytes(data)
            rows.append({"path":name,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
        cls.manifest = {"count":142,"bytes":2779239,"members":rows,"closed_directories":["sources"],
                        "overlay":{"target":"sources/overlay.swift","sha256":hashlib.sha256(b"overlay").hexdigest()}}
    def area(self,suffix=""):
        path = FIXTURES/(self.id().split(".")[-1]+suffix)
        path.mkdir(exist_ok=False)
        return path
    def inspect_dex(self,data,xml="<api/>",owner="demo/Example",classes=True):
        area = self.area()
        (area/"classes.dex").write_bytes(data); (area/"api.xml").write_text(xml)
        return floor.inspect(area/"classes.dex",area/"api.xml",[{"path":owner+".class"}] if classes else [])
    def snapshot(self):
        root = self.area()
        relative = "app/src/dev/mixer/android/Example.java"
        file = root/"consumer/Generated/MixerAndroid"/relative
        file.parent.mkdir(parents=True); file.write_bytes(b"class Example {}\n")
        generated = [{"path":relative,**c.file_identity(file)}]
        expected = [{"path":"Generated/MixerAndroid/"+relative,**c.file_identity(file)}]
        context = {"repository":"snowdamiz/mixer","source_head":"a"*40,"run_id":"987"}
        digest = hashlib.sha256((relative+"\0"+generated[0]["sha256"]+"\n").encode()).hexdigest()
        producer = {"status":"actual-snapshot-java-source-data-only",**context,"producer_job":"snapshot","run_attempt":1,
                    "source_manifest_sha256":"b"*64,"additional_app_owned_Java":[],"generated_java":expected,
                    "generated_tree":generated,"generated_snapshot_digest":digest}
        started = {"status":"started","source_head":context["source_head"],"source_manifest_sha256":"b"*64}
        self.write_json(root/"snapshot-receipt.json",producer); self.write_json(root/"started.json",started)
        return root,expected,context,producer
    def write_json(self,path,value):
        path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
    def test_python_sources_parse_without_execution(self):
        for name in ("source_contract.py","tool_data.py","bind_snapshot_source.py","transport_gate.py","compile_pair7.py","java_api_floor.py","test_source_controls.py"):
            ast.parse((HERE/name).read_text(),filename=name)
    def test_production_pure_definitions_match_tested_contract_asts(self):
        shared = ast.parse((HERE/"source_contract.py").read_text())
        actual = ast.parse((HERE/"compile_pair7.py").read_text())
        actual_defs = {node.name:node for node in actual.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        for node in shared.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)):
                self.assertEqual(ast.dump(node),ast.dump(actual_defs[node.name]),node.name)
        gate = ast.parse((HERE/"transport_gate.py").read_text())
        gate_defs = {node.name:node for node in gate.body if isinstance(node,ast.FunctionDef)}
        for node in shared.body:
            if isinstance(node,ast.FunctionDef) and node.name in ("transfer_identity","ci_identity","ordinary_root","fresh_download_root"):
                self.assertEqual(ast.dump(node),ast.dump(gate_defs[node.name]),node.name)
    def test_transport_gate_precedes_every_production_helper_import(self):
        module = ast.parse((HERE/"compile_pair7.py").read_text())
        collect = next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name == "collect")
        calls = [n for n in ast.walk(collect) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        gate = next(n.lineno for n in calls if n.func.id == "transfer_identity")
        helper_import = min(n.lineno for n in calls if n.func.id == "load")
        self.assertLess(gate,helper_import)
        workflow = (HERE/"workflow.DRAFT.yml").read_text()
        self.assertLess(workflow.index("transport_gate.py transfer"),workflow.index("uses: actions/download-artifact@"))
    def test_valid_transfer_and_all_missing_or_malformed_values(self):
        self.assertEqual(c.transfer_identity("123456","a"*64),{"artifact_id":"123456","artifact_digest":"a"*64})
        invalid = (None,"","0","01","-1","1,2"," 123","１２３","18446744073709551616")
        for value in invalid:
            with self.subTest(artifact_id=value), self.assertRaises(c.Refusal): c.transfer_identity(value,"a"*64)
        for value in (None,"","a"*63,"g"*64,"A"*64,"a"*64+"\n"):
            with self.subTest(digest=value), self.assertRaises(c.Refusal): c.transfer_identity("123",value)
    def test_exact_job_head_and_attempt_bindings(self):
        env = {"GITHUB_REPOSITORY":"snowdamiz/mixer","GITHUB_EVENT_NAME":"push","GITHUB_JOB":"compile",
               "GITHUB_RUN_ATTEMPT":"1","GITHUB_RUN_ID":"987","GITHUB_SHA":"a"*40}
        self.assertEqual(c.ci_identity(env,"compile")["job"],"compile")
        for key,value in (("GITHUB_JOB",None),("GITHUB_JOB","snapshot"),("GITHUB_RUN_ATTEMPT","2"),("GITHUB_SHA","x"*40),("GITHUB_RUN_ID","")):
            changed = dict(env); changed[key] = value
            with self.subTest(key=key,value=value), self.assertRaises(c.Refusal): c.ci_identity(changed,"compile")
    def test_existing_download_root_refuses_before_fetch(self):
        area = self.area()
        self.assertEqual(c.fresh_download_root(area),area/"pair7-java-snapshot-input")
        (area/"pair7-java-snapshot-input").mkdir()
        with self.assertRaises(c.Refusal): c.fresh_download_root(area)
    def test_fixture_root_requires_explicit_fresh_selected_scope(self):
        with self.assertRaises(RuntimeError): owned_fixture_root(None)
        with self.assertRaises(RuntimeError): owned_fixture_root(str(FIXTURES))
    def test_relative_source_names_refuse_escape_and_normalization(self):
        for name in ("",".","../outside","/absolute","a/../b","a//b","a/./b","a\\b","a/","x\0y"):
            with self.subTest(name=name), self.assertRaises(c.Refusal): c.relative_name(name)
    def test_source_closure_and_real_apple_verifier_pin(self):
        self.assertEqual(c.source_manifest(self.source,self.manifest),{"count":142,"bytes":2779239})
        actual = json.loads((HERE/"snapshot-source-manifest.json").read_bytes())
        rows = [r for r in actual["members"] if r["path"] == "scripts/ci/verify-apple-toolchain.py"]
        self.assertEqual(rows,[{"path":"scripts/ci/verify-apple-toolchain.py","bytes":4855,"sha256":"74a3e0261a8dcd9faa075333a09d33f635e5a96351560c4a4d94d1a90b11c442"}])
    def test_source_duplicate_and_escaped_member_refuse(self):
        for name in (self.manifest["members"][1]["path"],"../outside","/absolute"):
            changed = copy.deepcopy(self.manifest); changed["members"][0]["path"] = name
            with self.subTest(name=name), self.assertRaises(c.Refusal): c.source_manifest(self.source,changed)
    def test_changed_source_bytes_refuse(self):
        path = self.source/"sources/f000.bin"
        try:
            path.write_bytes(b"changed")
            with self.assertRaises(c.Refusal): c.source_manifest(self.source,self.manifest)
        finally: path.write_bytes(self.source_blob)
    def test_source_extra_empty_directory_refuses(self):
        path = self.source/"sources/extra-empty"
        try:
            path.mkdir()
            with self.assertRaises(c.Refusal): c.source_manifest(self.source,self.manifest)
        finally: path.rmdir()
    def test_staged_overlay_is_exact_and_post_only(self):
        path = self.source/"sources/overlay.swift"
        try:
            path.write_bytes(b"overlay")
            with self.assertRaises(c.Refusal): c.source_manifest(self.source,self.manifest,False)
            self.assertEqual(c.source_manifest(self.source,self.manifest,True)["count"],142)
            path.write_bytes(b"drift")
            with self.assertRaises(c.Refusal): c.source_manifest(self.source,self.manifest,True)
        finally: path.unlink()
    def test_symlink_source_ancestor_and_root_refuse(self):
        area = self.area(); (area/"real").mkdir(); (area/"real/file").write_bytes(b"data")
        (area/"alias").symlink_to(area/"real",target_is_directory=True)
        with self.assertRaises(c.Refusal): c.ordinary_file(area,"alias/file")
        with self.assertRaises(c.Refusal): c.ordinary_root(area/"alias")
    def test_snapshot_complete_namespace_and_digest_pass(self):
        root,expected,context,_ = self.snapshot()
        result = c.snapshot_closure(root,expected,context)
        self.assertEqual(result["artifact"]["bytes"],sum(r["bytes"] for r in result["artifact"]["members"]))
        self.assertEqual(result["generated_snapshot_digest"],result["producer"]["generated_snapshot_digest"])
    def test_snapshot_receipt_whitespace_mutation_is_not_inherited(self):
        root,expected,context,_ = self.snapshot(); baseline = c.snapshot_closure(root,expected,context)
        with (root/"snapshot-receipt.json").open("a") as stream: stream.write("\n")
        with self.assertRaises(c.Refusal): c.unchanged_snapshot(root,expected,context,baseline)
    def test_snapshot_changed_source_refuses(self):
        root,expected,context,_ = self.snapshot()
        (root/"consumer/Generated/MixerAndroid/app/src/dev/mixer/android/Example.java").write_bytes(b"changed")
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_snapshot_wrong_tree_digest_refuses(self):
        root,expected,context,producer = self.snapshot(); producer["generated_snapshot_digest"] = "0"*64
        self.write_json(root/"snapshot-receipt.json",producer)
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_snapshot_unselected_artifact_file_refuses(self):
        root,expected,context,_ = self.snapshot(); (root/"outside-closure.txt").write_bytes(b"extra")
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_snapshot_unselected_empty_directory_refuses(self):
        root,expected,context,_ = self.snapshot(); (root/"empty-extra").mkdir()
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_snapshot_wrong_job_or_source_head_refuses(self):
        root,expected,context,producer = self.snapshot()
        for key,value in (("producer_job","compile"),("source_head","b"*40)):
            changed = dict(producer); changed[key] = value
            self.write_json(root/"snapshot-receipt.json",changed)
            with self.subTest(key=key), self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_snapshot_symlink_and_special_nodes_refuse(self):
        root,expected,context,_ = self.snapshot(); (root/"alias").symlink_to(root/"started.json")
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
        (root/"alias").unlink(); os.mkfifo(root/"fifo")
        with self.assertRaises(c.Refusal): c.snapshot_closure(root,expected,context)
    def test_bounded_discovery_counts_directories_and_bytes_before_hash(self):
        area = self.area(); (area/"sub").mkdir(); (area/"sub/file").write_bytes(b"12345678")
        self.assertEqual(c.bounded_tree(area,3,8,8)["nodes"],3)
        for nodes,total,single in ((2,8,8),(3,7,8),(3,8,7)):
            with self.subTest(nodes=nodes,total=total,single=single), self.assertRaises(c.Refusal): c.bounded_tree(area,nodes,total,single)
    def test_output_symlink_is_refused_without_following(self):
        area = self.area(); (area/"target").write_bytes(b"x"); (area/"alias").symlink_to(area/"target")
        with self.assertRaises(c.Refusal): c.bounded_tree(area,4,8,8)
    def test_host_log_inventory_rejects_unselected_files_and_empty_directories(self):
        area = self.area(); (area/"stage.json").write_bytes(b"{}")
        self.assertEqual(c.host_logs_inventory(area)["bytes"],2)
        (area/"extra").mkdir()
        with self.assertRaises(c.Refusal): c.host_logs_inventory(area)
        (area/"extra").rmdir(); (area/"unselected.txt").write_bytes(b"x")
        with self.assertRaises(c.Refusal): c.host_logs_inventory(area)
    def test_active_and_retention_wall_deadlines_are_real_clock_checks(self):
        clock = Clock(); budget = c.WallBudget(420,60,clock)
        clock.now = 421
        with self.assertRaises(c.Refusal): budget.check()
        budget.begin_retention(); self.assertEqual(budget.deadline,480)
        clock.now = 480
        with self.assertRaises(c.Refusal): budget.check()
    def test_child_reservation_preserves_unchanged_full68_second_envelope(self):
        clock = Clock(); budget = c.WallBudget(420,60,clock)
        clock.now = 352; budget.reserve_child()
        clock.now = 353
        with self.assertRaises(c.Refusal): budget.reserve_child()
        budget.begin_retention()
        with self.assertRaises(c.Refusal): budget.reserve_child()
    def test_retention_transition_cannot_restart_or_exceed_total480(self):
        clock = Clock(); budget = c.WallBudget(420,60,clock)
        clock.now = 479; budget.begin_retention(); self.assertEqual(budget.deadline,480)
        with self.assertRaises(c.Refusal): budget.begin_retention()
    def test_chunked_hash_stops_on_active_deadline(self):
        area = self.area(); path = area/"file"; path.write_bytes(b"x"*2097152)
        clock = Clock(step=1); budget = c.WallBudget(3,2,clock)
        with self.assertRaises(c.Refusal): c.file_identity(path,4194304,budget.check)
    def test_tool_file_adapter_uses_the_same_wall_guard(self):
        area = self.area(); path = area/"file"; path.write_bytes(b"x"*2097152)
        clock = Clock(step=1); budget = c.WallBudget(3,2,clock)
        original_check,original_identity = tool.CHECK,tool.file_identity
        try:
            tool.CHECK,tool.file_identity = budget.check,c.file_identity
            with self.assertRaises(c.Refusal): tool.identity(path)
        finally: tool.CHECK,tool.file_identity = original_check,original_identity
    def test_artifact_inventory_requires_retention_and_refuses_expiry(self):
        area = self.area(); (area/"file").write_bytes(b"small")
        clock = Clock(); budget = c.WallBudget(420,60,clock)
        with self.assertRaises(c.Refusal): c.artifact_inventory(area,budget)
        budget.begin_retention(); self.assertEqual(c.artifact_inventory(area,budget)["bytes"],5)
        clock.now = 60
        with self.assertRaises(c.Refusal): c.artifact_inventory(area,budget,True)
    def test_synthetic_header_and_present_class_are_finite_data_only(self):
        result = self.inspect_dex(synthetic_dex()); self.assertTrue(result["accepted"]); self.assertFalse(result["runtime_accepted"])
    def test_empty_emitted_map_refuses(self):
        with self.assertRaises(ValueError): self.inspect_dex(synthetic_dex(),classes=False)
    def test_missing_emitted_class_refuses(self):
        with self.assertRaises(ValueError): self.inspect_dex(synthetic_dex(),owner="demo/Missing")
    def test_bad_checksum_refuses(self):
        data = bytearray(synthetic_dex()); data[-1] ^= 1
        with self.assertRaises(ValueError): self.inspect_dex(bytes(data))
    def test_truncated_dex_refuses(self):
        with self.assertRaises(ValueError): self.inspect_dex(synthetic_dex()[:110])
    def test_unknown_java_type_remains_refused(self):
        result = self.inspect_dex(synthetic_dex("java/lang/Unknown"),owner="java/lang/Unknown")
        self.assertFalse(result["accepted"]); self.assertEqual(len(result["unresolved"]),1)
    def test_later_java_type_remains_refused(self):
        result = self.inspect_dex(synthetic_dex("java/lang/Later"),'<api><class name="java/lang/Later" since="36"/></api>',owner="java/lang/Later")
        self.assertFalse(result["accepted"]); self.assertEqual(result["above28"][0]["api"],36)
    def test_record_reference_refuses(self):
        with self.assertRaises(ValueError): self.inspect_dex(synthetic_dex("java/lang/Record"),'<api><class name="java/lang/Record" since="36"/></api>',owner="java/lang/Record")
    def test_java_array_element_type_is_in_closure(self):
        area = self.area(); path = area/"array.dex"; path.write_bytes(synthetic_dex(descriptor="[[Ljava/lang/Later;"))
        self.assertEqual(floor.dex_refs(path)["types"],["java/lang/Later"])
    def test_inherited_member_floor_preserves_later_boundary(self):
        root = ET.fromstring('<api><class name="child" since="1"><extends name="parent" since="1"/></class><class name="parent" since="1"><method name="m()V" since="31"/></class></api>')
        self.assertEqual(floor.api_lookup({r.get("name"):r for r in root},"child","m()V","method"),{"declared_owner":"parent","api":31})
    def test_dex_reader_checkpoint_refuses_expired_active_budget(self):
        clock = Clock(); budget = c.WallBudget(420,60,clock); clock.now = 420
        original = floor.CHECK
        try:
            floor.CHECK = budget.check
            with self.assertRaises(c.Refusal): floor.dex_refs(self.area()/"unopened.dex")
        finally: floor.CHECK = original

if __name__ == "__main__":
    FIXTURES = owned_fixture_root(os.environ.get("MIXER_PAIR7_CONTROL_ROOT"))
    FIXTURES.mkdir(exist_ok=False)
    unittest.main(verbosity=2)
