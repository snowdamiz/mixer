"""Closed finite old/corrected replay and fault matrix; no outside writes."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
WITNESSES=("test_closed_retained_wrapper_cannot_reauthorize_reused_descriptor","test_close_failure_still_accounts_for_and_closes_remaining_owned_descriptors","test_preclose_error_does_not_forget_known_open_descriptor")


def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as file:
        buffer=bytearray(4096)
        while (n:=file.readinto(buffer)):h.update(memoryview(buffer)[:n])
    return h.hexdigest()


def dump(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")


def run(command,cwd,stem,expected):
    started=time.monotonic()
    with stem.with_suffix(".stdout").open("wb") as out,stem.with_suffix(".stderr").open("wb") as err:
        result=subprocess.run(command,cwd=cwd,stdout=out,stderr=err,timeout=30,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
    record={"command":command,"cwd":str(cwd),"exit_code":result.returncode,"expected_exit":expected,"elapsed_seconds":time.monotonic()-started,"stdout":str(stem.with_suffix('.stdout').relative_to(ROOT)),"stderr":str(stem.with_suffix('.stderr').relative_to(ROOT)),"stdout_sha256":sha(stem.with_suffix('.stdout')),"stderr_sha256":sha(stem.with_suffix('.stderr')),"terminal_reaped":True}
    if result.returncode!=expected:
        dump(ROOT/"incomplete-command.json",record)
        raise RuntimeError("unexpected exit: "+str(command))
    return record


def main():
    (ROOT/"raw-witnesses").mkdir(exist_ok=True)
    (ROOT/"fault-results").mkdir(exist_ok=True)
    (ROOT/"owned-scratch").mkdir(exist_ok=True)
    commands=[];raw=[];producer=[];faults=[]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    source_names=("prototype.py","consumer.py","schema.py","test_preparation.py")
    source_custody=[]
    for variant in ("old","corrected"):
        for name in source_names:
            path=ROOT/variant/"replay"/name
            source_custody.append({"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)})
        assert sha(ROOT/variant/"test_independent.py")==sha(REPO/"verification/swift-retained-profile-composition-independent/test_independent.py")
    for name in source_names:
        assert sha(ROOT/"old"/"replay"/name)==sha(REPO/"verification/swift-retained-profile-composition-preparation"/name)
        if name!="prototype.py":assert sha(ROOT/"corrected"/"replay"/name)==sha(ROOT/"old"/"replay"/name)
    for variant in ("old","corrected"):
        cwd=ROOT/variant/"replay"
        commands.append(run([sys.executable,"-B","test_preparation.py"],cwd,cwd/"producer-replay",0))
        result=json.loads((cwd/"test-results.json").read_text())
        assert result["methods"]==26 and result["failures"]==result["errors"]==result["skips"]==0
        assert any(item.get("snapshot_leaf_mutations")==307 for item in result["observations"])
        producer.append({"variant":variant,"result":result})
        for name in WITNESSES:
            expected=0 if variant=="corrected" and name==WITNESSES[0] else 1
            stem=ROOT/"raw-witnesses"/(variant+"-"+name)
            commands.append(run([sys.executable,"-B",str(ROOT/"run_unchanged_witness.py"),variant,name],ROOT,stem,expected))
            observation=json.loads(stem.with_suffix(".json").read_text())
            if variant=="old":assert observation["failures"]==1 and observation["errors"]==0
            if variant=="corrected" and name==WITNESSES[0]:assert observation["failures"]==observation["errors"]==0
            raw.append(observation)
    cases=[("close-position",mode,str(position)) for mode in ("pre","post") for position in range(65)]
    cases += [("all-positions-uncertain",mode) for mode in ("pre","post")]
    cases += [(name,) for name in ("stale-reuse","closing-access","closing-retained-entry","lease-generation","constructor","composition-failure","composition-success","nonterminal-child-model","quarantined-number-reuse","bounds")]
    for i,case in enumerate(cases):
        stem=ROOT/"fault-results"/(str(i).zfill(3)+"-"+"-".join(case))
        commands.append(run([sys.executable,"-B",str(ROOT/"fault_case.py"),*case],ROOT,stem,0))
        observation=json.loads(stem.with_suffix(".stdout").read_text())
        assert not any(observation["authority"].values())
        assert observation["ownership_at_child_terminal_exit"]["stdio_contexts"]==0
        assert not observation["uncertain_os_close_resolution_qualified"]
        dump(stem.with_suffix(".json"),observation)
        faults.append(observation)
    assert len(faults)==142
    healthy=[x for x in faults if x["cleanup_kind"]=="healthy-zero"]
    uncertain=[x for x in faults if x["cleanup_kind"].startswith("synthetic-known-fault")]
    leased=[x for x in faults if x["case"]=="nonterminal-child-model"]
    assert len(healthy)==5 and len(uncertain)==136 and len(leased)==1
    assert all(x["ownership_at_child_terminal_exit"]["healthy_zero"] for x in healthy)
    assert all(not x["ownership_at_child_terminal_exit"]["healthy_zero"] for x in uncertain+leased)
    assert len(list((ROOT/"owned-scratch").iterdir()))==0
    dump(ROOT/"source-custody.json",{"schema":1,"copies":source_custody,"producer_controls_unchanged":True,"independent_raw_witnesses_unchanged":True,"schema_consumer_unchanged":True,"only_prototype_changed":True})
    dump(ROOT/"command-receipts.json",{"schema":1,"commands":commands})
    dump(ROOT/"results.json",{"schema":1,"producer":producer,"unchanged_raw_witnesses":raw,"fault_cases":faults,"targeted_case_count":len(faults),"healthy_case_count":len(healthy),"synthetic_uncertainty_case_count":len(uncertain),"modeled_child_quarantine_case_count":len(leased),"actual_os_uncertainty_resolution_qualified":False})
    own_sources=sorted(list(ROOT.rglob("*.py"))+[ROOT/"contract.md",ROOT/"control-revisions.md",ROOT/"README.md"])
    entries=[{"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)} for path in own_sources]
    preimage=b"retained-profile-correction-source-v1\n"+b"".join((e["path"]+"\0"+str(e["bytes"])+"\0"+e["sha256"]+"\n").encode() for e in entries)
    git=lambda *args:subprocess.check_output(["git",*args],cwd=REPO,text=True).strip()
    dump(ROOT/"receipt.json",{"schema":1,"at":started,"scope":"isolated host lifecycle/cleanup prototype correction only","command":[sys.executable,"-B","run_evidence.py"],"python":{"executable":os.path.realpath(sys.executable),"sha256":sha(Path(os.path.realpath(sys.executable))),"version":sys.version},"platform":platform.platform(),"git":{"head":git("rev-parse","HEAD"),"committed_tree":git("rev-parse","HEAD^{tree}")},"source_tree_sha256":hashlib.sha256(preimage).hexdigest(),"source_entries":entries,"commands":len(commands),"producer_methods_each":26,"snapshot_leaf_mutations_each":307,"raw_old_required_failures":3,"raw_corrected_r01_pass":True,"raw_corrected_r02_cleanup_protocol_conflicts_preserved":2,"targeted_cases":142,"targeted_cases_pass":142,"healthy_fault_cases_zero":5,"synthetic_cases_retain_uncertainty":136,"modeled_child_quarantine_cases":1,"all_case_children_terminal_reaped":True,"scratch_entries_final":0,"all_uncertainty_cases_healthy_zero_claimed":False,"real_os_uncertain_state_resolved":False,"native_ui_capture_runtime_started":False,"process_inventory_performed":False,"canonical_product_changed":False,"frozen_inputs_changed":False,"commit_push_performed":False,"real_rust_exporter_context_accounting_accepted":False})
    members=[]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in ("seal.json","seal.sha256"):
            assert "__pycache__" not in path.parts
            members.append({"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)})
    dump(ROOT/"seal.json",{"schema":1,"scope":"isolated lifecycle and close-uncertainty correction proposal; no product authority","member_count":len(members),"members":members,"self_seal_metadata":{"path":"seal.sha256","bytes":76,"exact_content":"lowercase SHA256 of seal.json + two ASCII spaces + seal.json + LF"},"real_binding_native_ota_ga_accepted":False})
    seal=sha(ROOT/"seal.json")
    (ROOT/"seal.sha256").write_text(seal+"  seal.json\n")
    print(json.dumps({"members":len(members),"seal_sha256":seal,"source_tree_sha256":hashlib.sha256(preimage).hexdigest(),"commands":len(commands),"producer_methods_each":26,"targeted_cases":142,"raw_old_required_failures":3,"healthy_zero_cases":5,"synthetic_uncertainty_retained_cases":136,"modeled_child_quarantine_cases":1,"scratch_entries_final":0},sort_keys=True))


if __name__=="__main__":main()
