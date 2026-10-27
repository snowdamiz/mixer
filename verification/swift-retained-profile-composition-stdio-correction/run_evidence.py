"""Finite C01 correction evidence, preserving old/raw incompatibilities."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]


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
    for name in ("logs","regression-results","stdio-results","owned-scratch"):(ROOT/name).mkdir(exist_ok=True)
    commands=[];producer=[];independent=[];regression=[];stdio=[]
    at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    source_custody=[]
    frozen=REPO/"verification/swift-retained-profile-composition-correction/corrected/replay"
    witness=REPO/"verification/swift-retained-profile-composition-correction-independent/independent_case.py"
    for variant in ("old","new"):
        for name in ("prototype.py","schema.py","consumer.py","test_preparation.py"):
            path=ROOT/variant/"replay/corrected/replay"/name
            if variant=="old" or name!="prototype.py":assert sha(path)==sha(frozen/name)
            source_custody.append({"path":str(path.relative_to(ROOT)),"sha256":sha(path),"bytes":path.stat().st_size})
        assert sha(ROOT/variant/"independent_case.py")==sha(witness)
        assert sha(ROOT/variant/"replay/fault_case.py")==sha(REPO/"verification/swift-retained-profile-composition-correction/fault_case.py")
        cwd=ROOT/variant/"replay/corrected/replay"
        commands.append(run([sys.executable,"-B","test_preparation.py"],cwd,ROOT/"logs"/(variant+"-producer"),0))
        result=json.loads((cwd/"test-results.json").read_text())
        assert result["methods"]==26 and result["failures"]==result["errors"]==result["skips"]==0
        assert any(x.get("snapshot_leaf_mutations")==307 for x in result["observations"])
        producer.append({"variant":variant,"result":result})
        for case in ("lifecycle","multi-close","nested-primary","nested-result","number-reuse","stdio-close"):
            stem=ROOT/"logs"/(variant+"-independent-"+case)
            commands.append(run([sys.executable,"-B",str(ROOT/variant/"independent_case.py"),case],ROOT,stem,1 if case=="stdio-close" else 0))
            streams=stem.with_suffix(".stdout").read_text()
            if case=="stdio-close":
                if variant=="old":
                    old=json.loads(streams)
                    assert old["known_owned_stream_remains_open"] and old["snapshot"]["healthy_zero"] and not old["primary_is_preserved_as_aggregate_primary"]
                else:
                    assert streams=="" and "IndexError" in stem.with_suffix(".stderr").read_text()
            independent.append({"variant":variant,"case":case,"classification":"required-old-C01-failure" if variant=="old" and case=="stdio-close" else "unchanged-TemporaryFile-injection-not-reached; not-behavior-pass" if case=="stdio-close" else "pass"})
    cases=[("close-position",mode,str(i)) for mode in ("pre","post") for i in range(65)]
    cases += [("all-positions-uncertain",mode) for mode in ("pre","post")]
    cases += [(name,) for name in ("stale-reuse","closing-access","closing-retained-entry","lease-generation","constructor","composition-failure","composition-success","nonterminal-child-model","quarantined-number-reuse","bounds")]
    for i,case in enumerate(cases):
        stem=ROOT/"regression-results"/(str(i).zfill(3)+"-"+"-".join(case))
        commands.append(run([sys.executable,"-B",str(ROOT/"new/replay/fault_case.py"),*case],ROOT,stem,0))
        result=json.loads(stem.with_suffix(".stdout").read_text());dump(stem.with_suffix(".json"),result);regression.append(result)
    stdcases=[("healthy",),("reuse-uncertain",)]
    stdcases += [("close",pattern,body) for pattern in ("p-","q-","-p","-q","pp","pq","qp","qq") for body in ("primary","result")]
    stdcases += [("close","pq","both")]
    stdcases += [("acquire",str(index),stage,mode) for index in (0,1) for stage in ("before","post-acquire","pre-prepare","post-prepare","unlink-pre","unlink-post") for mode in ("-","p","q") if not(index==0 and stage=="before" and mode!="-")]
    stdcases += [("child",body,mix) for body in ("primary","result") for mix in ("stdio","mixed")]
    assert len(stdcases)==57
    for i,case in enumerate(stdcases):
        stem=ROOT/"stdio-results"/(str(i).zfill(3)+"-"+"-".join(case))
        commands.append(run([sys.executable,"-B",str(ROOT/"stdio_case.py"),*case],ROOT,stem,0))
        result=json.loads(stem.with_suffix(".stdout").read_text());dump(stem.with_suffix(".json"),result);stdio.append(result)
        assert not any(result["authority"].values()) and not result["real_OS_ambiguity_resolved"]
        assert result["ownership_at_process_exit"]["healthy_zero"]==(result["cleanup_kind"]=="healthy-zero")
    assert len(regression)==142 and len(stdio)==57
    assert sum(x["cleanup_kind"]=="healthy-zero" for x in stdio)==5
    assert all(not list(path.iterdir()) for path in ROOT.rglob("owned-scratch"))
    sources=sorted(list(ROOT.rglob("*.py"))+[ROOT/"contract.md",ROOT/"control-adaptations.md",ROOT/"README.md"])
    entries=[{"path":str(x.relative_to(ROOT)),"bytes":x.stat().st_size,"sha256":sha(x)} for x in sources]
    preimage=b"retained-profile-stdio-correction-source-v1\n"+b"".join((e["path"]+"\0"+str(e["bytes"])+"\0"+e["sha256"]+"\n").encode() for e in entries)
    dump(ROOT/"source-custody.json",{"schema":1,"copies":source_custody,"unchanged_producer_methods_schema_consumer_independent_witnesses":True,"only_replayed_prototype_changed":True})
    dump(ROOT/"command-receipts.json",{"schema":1,"commands":commands})
    dump(ROOT/"results.json",{"schema":1,"producer":producer,"independent":independent,"regression":regression,"stdio":stdio})
    git=lambda *args:subprocess.check_output(["git",*args],cwd=REPO,text=True).strip()
    dump(ROOT/"receipt.json",{"schema":1,"at":at,"command":[sys.executable,"-B","run_evidence.py"],"cwd":str(ROOT),"scope":"isolated explicit raw-stdio lifecycle correction only","python":{"executable":os.path.realpath(sys.executable),"executable_sha256":sha(Path(os.path.realpath(sys.executable))),"version":sys.version,"tempfile_source":tempfile.__file__,"tempfile_source_sha256":sha(Path(tempfile.__file__))},"platform":platform.platform(),"git":{"head":git("rev-parse","HEAD"),"committed_tree":git("rev-parse","HEAD^{tree}")},"source_tree_sha256":hashlib.sha256(preimage).hexdigest(),"source_entries":entries,"commands":len(commands),"producer_methods_each":26,"snapshot_mutations_each":307,"fresh_previous_independent_positive_each":5,"old_raw_C01_required_failure_preserved":True,"new_raw_C01_mechanism_mismatch_not_pass":True,"unchanged_lifecycle_fault_cases_pass":142,"new_stdio_cases_pass":57,"new_stdio_healthy_zero_cases":5,"new_stdio_unresolved_cases":52,"case_children_terminal_reaped":True,"owned_scratch_entries_final":0,"uncertain_saved_numbers_retried":False,"owning_python_FileIO_BufferedRandom_objects_created_for_stdio":False,"real_OS_ambiguity_or_quarantine_retirement_accepted":False,"canonical_or_frozen_packet_changed":False,"native_UI_capture_runtime_or_process_inventory":False,"commits_or_pushes":False,"real_Rust_binding_context_accounting_or_release_accepted":False})
    members=[]
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name not in ("seal.json","seal.sha256"):
            assert "__pycache__" not in path.parts
            members.append({"path":str(path.relative_to(ROOT)),"bytes":path.stat().st_size,"sha256":sha(path)})
    dump(ROOT/"seal.json",{"schema":1,"scope":"raw stdio ownership/lifecycle correction proposal; no product binding authority","members":members,"member_count":len(members),"self_seal_metadata":{"path":"seal.sha256","bytes":76,"exact_content":"lowercase sha256 of seal.json + two ASCII spaces + seal.json + LF"},"real_Rust_binding_native_OTA_GA_accepted":False})
    seal=sha(ROOT/"seal.json");(ROOT/"seal.sha256").write_text(seal+"  seal.json\n")
    print(json.dumps({"members":len(members),"seal_sha256":seal,"source_tree_sha256":hashlib.sha256(preimage).hexdigest(),"commands":len(commands),"producer_methods_each":26,"unchanged_regression_cases":142,"new_stdio_cases":57,"new_stdio_healthy_zero":5,"new_stdio_uncertainty_retained":52,"owned_scratch_entries_final":0},sort_keys=True))


if __name__=="__main__":main()
