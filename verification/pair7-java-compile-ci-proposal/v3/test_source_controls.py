"""Prepared v3 data controls. Explicit owned fixture root is mandatory.

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
import time

class Refusal(RuntimeError):
    pass

def need(value, message):
    if not value:
        raise Refusal(message)

def stat_identity(value):
    return (value.st_dev,value.st_ino,value.st_mode,value.st_size,value.st_mtime_ns,value.st_ctime_ns)

def bounded_file(path, maximum, check=lambda:None, retain=False):
    """One nofollow, nonblocking descriptor; at most maximum+1 bytes are read."""
    need(type(maximum) is int and maximum >= 0, "Finite nonnegative byte cap required")
    path = Path(path)
    check()
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "Ordinary bounded file required")
    digest,total,chunks = hashlib.sha256(),0,[]
    descriptor = os.open(path,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor,"rb") as stream:
        opened = os.fstat(stream.fileno())
        need(stat.S_ISREG(opened.st_mode) and stat_identity(opened) == stat_identity(before),
             "File changed before nofollow open")
        while True:
            check()
            chunk = stream.read(min(1048576,maximum-total+1))
            if not chunk: break
            total += len(chunk)
            need(total <= maximum,"File grew beyond byte bound")
            digest.update(chunk)
            if retain: chunks.append(chunk)
        check()
        need(stat_identity(os.fstat(stream.fileno())) == stat_identity(before),
             "File descriptor changed during bounded read")
    check()
    need(stat_identity(path.lstat()) == stat_identity(before) and total == before.st_size,
         "File path changed during bounded read")
    return (b"".join(chunks) if retain else None),{"bytes":total,"sha256":digest.hexdigest()}

def file_snapshot(path, maximum, check=lambda:None):
    return bounded_file(path,maximum,check,True)


HERE = Path(__file__).resolve().parent
FIXTURES = None
EXPECTED_GUARD_REFUSALS = 0

def load_pure(name):
    if name not in ("source_contract.py","java_api_floor.py","tool_data.py"):
        raise RuntimeError("Only named sealed pure data modules may load")
    deadline = time.monotonic()+30
    def check():
        if time.monotonic() >= deadline: raise RuntimeError("Control bootstrap deadline exhausted")
    seal_data,_ = file_snapshot(HERE/"seal.json",65536,check)
    seal = json.loads(seal_data)
    row = next(r for r in seal["members"] if r["path"] == name)
    path = HERE/name
    data,identity = file_snapshot(path,524288,check)
    if identity != {k:row[k] for k in ("bytes","sha256")}:
        raise RuntimeError("Pure module changed")
    spec = importlib.util.spec_from_file_location("pair7_v3_control_"+name[:-3],path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(data,str(path),"exec"),module.__dict__)

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
        return floor.inspect(data,xml.encode(),[{"path":owner+".class"}] if classes else [])
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
        (root/"alias").unlink(); os.mkfifo(root/"fifo",0o600)
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
        self.assertEqual(floor.dex_refs(c.file_snapshot(path,67108864)[0])["types"],["java/lang/Later"])
    def test_inherited_member_floor_preserves_later_boundary(self):
        root = ET.fromstring('<api><class name="child" since="1"><extends name="parent" since="1"/></class><class name="parent" since="1"><method name="m()V" since="31"/></class></api>')
        self.assertEqual(floor.api_lookup({r.get("name"):r for r in root},"child","m()V","method"),{"declared_owner":"parent","api":31})
    def test_dex_reader_checkpoint_refuses_expired_active_budget(self):
        clock = Clock(); budget = c.WallBudget(420,60,clock); clock.now = 420
        original = floor.CHECK
        try:
            floor.CHECK = budget.check
            with self.assertRaises(c.Refusal): floor.dex_refs(b"unread")
        finally: floor.CHECK = original

    def test_bootstrap_snapshot_definitions_match_the_contract(self):
        shared = ast.parse((HERE/"source_contract.py").read_text())
        wanted = {n.name:ast.dump(n) for n in shared.body if isinstance(n,ast.FunctionDef)
                  and n.name in ("stat_identity","bounded_file","file_snapshot")}
        for name in ("bind_snapshot_source.py","transport_gate.py","test_source_controls.py","run_data_controls.py"):
            found = {n.name:ast.dump(n) for n in ast.parse((HERE/name).read_text()).body
                     if isinstance(n,ast.FunctionDef) and n.name in wanted}
            self.assertEqual(found,wanted,name)
    def test_every_workflow_cli_has_an_actual_main_dispatch(self):
        bindings = json.loads((HERE/"cli-bindings.json").read_bytes())
        workflow = (HERE/"workflow.DRAFT.yml").read_text()
        for row in bindings["proposal_scripts"]:
            for invocation in row["workflow_invocations"]:
                self.assertIn(invocation,workflow)
            module = ast.parse((HERE/row["file"]).read_text())
            guards = [n for n in module.body if isinstance(n,ast.If)
                      and ast.dump(n.test) == ast.dump(ast.parse('__name__ == "__main__"',mode="eval").body)]
            self.assertEqual(len(guards),1,row["file"])
            calls = [n for n in ast.walk(guards[0]) if isinstance(n,ast.Call)]
            self.assertIn(row["dispatch"],[n.func.id for n in calls if isinstance(n.func,ast.Name)])
            self.assertTrue(any(isinstance(n,ast.FunctionDef) and n.name == row["dispatch"] for n in module.body))
        self.assertIn(bindings["existing_apple_verifier"]["workflow_invocation"],workflow)
    def test_selected_interpreter_symlink_records_both_identities(self):
        area = self.area(); target = area/"python3.12"; target.write_bytes(b"inert interpreter fixture")
        invocation = area/"python3"; invocation.symlink_to(target)
        expected = {"path":str(invocation),"version":[3,12,3],"boundary":"root-admitted-ubuntu-provider-infrastructure"}
        before = tool.CHECK,tool.file_snapshot
        try:
            tool.CHECK,tool.file_snapshot = lambda:None,c.file_snapshot
            result = tool.python_route(str(invocation),expected,(3,12,3),1,1,True)
            self.assertEqual(result["invocation_path"],str(invocation))
            self.assertEqual(result["resolved_path"],str(target))
            self.assertEqual(result["sha256"],hashlib.sha256(b"inert interpreter fixture").hexdigest())
            for path,version,isolated,site,bytecode in ((str(target),(3,12,3),1,1,True),(str(invocation),(3,12,4),1,1,True),(str(invocation),(3,12,3),0,1,True)):
                with self.assertRaises(tool.Refusal): tool.python_route(path,expected,version,isolated,site,bytecode)
        finally: tool.CHECK,tool.file_snapshot = before
    def test_interpreter_target_replacement_during_read_refuses(self):
        area = self.area(); a,b,invocation = area/"a",area/"b",area/"python3"
        a.write_bytes(b"same bytes"); b.write_bytes(b"same bytes"); invocation.symlink_to(a)
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 2:
                invocation.unlink(); invocation.symlink_to(b)
        before = tool.CHECK,tool.file_snapshot
        try:
            tool.CHECK,tool.file_snapshot = check,c.file_snapshot
            with self.assertRaises(tool.Refusal): tool.resolved_snapshot(invocation,1024)
        finally: tool.CHECK,tool.file_snapshot = before
    def test_json_snapshot_growth_is_refused_inside_the_read_cap(self):
        area = self.area(); path = area/"data.json"; path.write_bytes(b"{}")
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 2: path.write_bytes(b"x"*65)
        with self.assertRaisesRegex(c.Refusal,"grew beyond byte bound"): c.read_json(path,64,check)
    def test_json_path_replacement_cannot_change_decoded_snapshot(self):
        area = self.area(); path = area/"data.json"; path.write_bytes(b"{}")
        other = area/"other.json"; other.write_bytes(b'{"changed":true}')
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 3:
                path.unlink(); path.symlink_to(other)
        with self.assertRaises(c.Refusal): c.read_json(path,64,check)
    def test_json_decodes_the_same_bounded_bytes_without_path_read_bytes(self):
        area = self.area(); path = area/"data.json"; path.write_bytes(b'{"value":7}')
        original = Path.read_bytes
        def forbidden(*args,**kwargs): raise AssertionError("Unbounded path reopen")
        try:
            Path.read_bytes = forbidden
            value,identity = c.read_json(path,64)
            self.assertEqual(value,{"value":7}); self.assertEqual(identity["bytes"],11)
        finally: Path.read_bytes = original
    def dex_fixture(self):
        area = self.area(); dex,api = area/"classes.dex",area/"api.xml"
        dex.write_bytes(synthetic_dex()); api.write_bytes(b"<api/>")
        return dex,api,c.file_identity(dex),c.file_identity(api),[{"path":"demo/Example.class"}]
    def test_selected_dex_snapshot_and_postflight_binding_pass(self):
        dex,api,selected,metadata,classes = self.dex_fixture()
        result = c.inspect_selected_dex(floor,dex,api,selected,metadata,classes)
        self.assertEqual(result["dex_sha256"],selected["sha256"])
        self.assertTrue(result["accepted"])
    def test_dex_selected_hash_mismatch_refuses_before_parser(self):
        dex,api,selected,metadata,classes = self.dex_fixture()
        class Never:
            def inspect(self,*args): raise AssertionError("Mismatched DEX reached parser")
        with self.assertRaises(c.Refusal): c.inspect_selected_dex(Never(),dex,api,{**selected,"sha256":"0"*64},metadata,classes)
    def test_dex_returned_parser_hash_must_equal_selected_snapshot(self):
        dex,api,selected,metadata,classes = self.dex_fixture()
        class Wrong:
            def inspect(self,*args):
                result = floor.inspect(*args); result["dex_sha256"] = "0"*64; return result
        with self.assertRaises(c.Refusal): c.inspect_selected_dex(Wrong(),dex,api,selected,metadata,classes)
    def test_dex_replacement_after_parse_refuses_postflight(self):
        dex,api,selected,metadata,classes = self.dex_fixture()
        class Changing:
            def inspect(self,*args):
                result = floor.inspect(*args); dex.write_bytes(synthetic_dex("demo/Other")); return result
        with self.assertRaises(c.Refusal): c.inspect_selected_dex(Changing(),dex,api,selected,metadata,classes)
    def test_dex_parser_accepts_only_immutable_bounded_data(self):
        with self.assertRaises(ValueError): floor.inspect(Path("never-opened"),b"<api/>",[{"path":"demo/Example.class"}])
        with self.assertRaises(ValueError): floor.dex_refs(bytearray(synthetic_dex()))
    def test_fixture_guard_added_capabilities_are_confined(self):
        global EXPECTED_GUARD_REFUSALS
        area = self.area(); file = area/"ordinary"; file.write_bytes(b"fixture")
        alias = area/"alias"; alias.symlink_to(file); alias.unlink()
        empty = area/"empty"; empty.mkdir(); empty.rmdir()
        fifo = area/"fifo"; os.mkfifo(fifo,0o600)
        guard_module = sys.modules["pair7_v3_fixture_guard"]
        def refused(call):
            global EXPECTED_GUARD_REFUSALS
            count = guard_module.DENIED_COUNT
            with self.assertRaises(RuntimeError): call()
            self.assertEqual(guard_module.DENIED_COUNT,count+1)
            EXPECTED_GUARD_REFUSALS += 1
        flags = os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
        refused(lambda: os.open(fifo,flags))
        fifo.unlink()
        refused(lambda: os.open(HERE.parent/"v2"/"source_contract.py",flags))
        refused(lambda: os.fdopen(0,"rb"))
        refused(lambda: os.symlink(HERE/"source_contract.py",area/"escape"))
        refused(lambda: os.symlink(file,HERE/"forbidden-link"))
        refused(lambda: os.remove(HERE/"forbidden-remove"))
        refused(lambda: os.rmdir(HERE))
        refused(lambda: os.mkfifo(HERE/"forbidden-fifo",0o600))
        descriptor = os.open(file,flags)
        try: refused(lambda: os.fdopen(descriptor,"wb"))
        finally: os.close(descriptor)
        descriptor = os.open(file,flags)
        with os.fdopen(descriptor,"rb") as stream: self.assertEqual(stream.read(),b"fixture")

if __name__ == "__main__":
    selected = os.environ.get("MIXER_PAIR7_CONTROL_ROOT")
    if not getattr(sys,"_mixer_pair7_fixture_guard",False):
        raise RuntimeError("Run only through the selected fixture-guard launcher")
    FIXTURES = owned_fixture_root(str(Path(selected)/"cases"))
    FIXTURES.mkdir(exist_ok=False)
    result = unittest.main(verbosity=2,exit=False).result
    observed = sys.modules["pair7_v3_fixture_guard"].DENIED_COUNT
    print(json.dumps({"tests_run":result.testsRun,"successful":result.wasSuccessful(),
                      "guard_refusals":observed,"expected_guard_refusals":EXPECTED_GUARD_REFUSALS,
                      "fixture_root":str(FIXTURES),"fixture_disposition":"retained; no host resources opened"}))
    sys.exit(0 if result.wasSuccessful() and observed == EXPECTED_GUARD_REFUSALS else 1)
