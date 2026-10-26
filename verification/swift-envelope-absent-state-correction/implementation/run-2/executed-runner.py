#!/usr/bin/env python3
"""New bounded host qualification; frozen producer collectors are never run."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/"verification/swift-ordered-retention-analyzer-envelope-correction"
PROPOSAL=HERE.parent/"proposal-1"
RUST=Path("/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc")
SELECT=ROOT/"verification/swift-ordered-retention-analyzer-envelope-root-review/absence-correction-selection.json"
ACCOUNT=ROOT/"verification/swift-envelope-absent-state-accounting-review/seal.json"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def desc(p,base=ROOT):
    return {"path":str(p.relative_to(base)),"bytes":p.stat().st_size,"sha256":sha(p)}
def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":")).encode()
def verified_seal(p,expected):
    assert sha(p)==expected,str(p)
    data=json.loads(p.read_text())
    for m in data["members"]:
        assert desc(ROOT/m["path"])==m,m["path"]
    return {**desc(p),"members":len(data["members"]),"member_bytes":sum(m["bytes"] for m in data["members"])}
def admitted_refs():
    admitted=json.loads((OLD/"seal.json").read_text())
    assert sha(OLD/"seal.json")=="4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1"
    named={m["path"]:m for m in admitted["members"]}
    files=[OLD/"tests"/n for n in ["fixture_tests.rs","independent_tests.rs","private_io_tests.rs",
        "envelope_tests.rs","correction_tests.rs","selected_tests.rs"]]
    files += [OLD/"inputs"/n for n in ["fsm-model-425.py","oracle-425.json","oracle-425.bin","oracle-budget-425.bin"]]
    files += sorted(q for q in (OLD/"inputs/historical").iterdir() if q.is_file())
    refs=[]
    for p in files:
        row=desc(p); assert named[row["path"]]==row,row["path"];refs.append(row)
    return refs

def main():
    tag=sys.argv[1]; assert re.fullmatch(r"run-[1-9][0-9]*",tag)
    focused_resume=len(sys.argv)==3 and sys.argv[2]=="focused-resume"
    assert len(sys.argv)==2 or focused_resume
    run=HERE/tag; run.mkdir(exist_ok=False)
    scratch=run/"owned-scratch"; scratch.mkdir()
    commands=run/"commands"; commands.mkdir()
    shutil.copy2(__file__,run/"executed-runner.py")
    receipt={"schema":1,"status":"running","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "invocation":[sys.executable,"-B",str(Path(__file__).resolve()),*sys.argv[1:]],
        "runner_sha256":sha(run/"executed-runner.py"),"commands":[],
        "scope":"Fresh exact selected source; unchanged70 host method bodies plus8 focused methods. Reused immutable425 oracle expected inputs, not a new Python oracle evaluation.",
        "selection_sha256":sha(SELECT),"candidate_source_sha256":sha(PROPOSAL/"src/envelope.rs"),
        "parent_source_sha256":sha(PROPOSAL/"src/analyzer.rs"),
        "native_UI_capture_device_process_discovery":False,"forbidden_hosted_or_old_collector_execution":False}
    if focused_resume:
        receipt["scope"]="Fresh focused8/API qualification after one test expectation repair. Valid unchanged70/21714 oracle/32 layout results execute this identical selected source in preserved run-1; they are directly referenced, not rerun."
        receipt["regression_references"]=[]
    active=None; binaries=[]; temporary_links=[]; owned_source_inputs=[]
    def save():
        (run/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    def command(name,argv,deadline=60,env=None,expect_success=True):
        nonlocal active
        assert active is None
        immediate_inputs=[]
        for value in argv:
            text=str(value)
            if text.startswith("mixer_absence="):text=text.split("=",1)[1]
            p=Path(text)
            if p.is_absolute() and p.is_file() and (p.suffix in {".rs",".rlib"} or p==Path(argv[0])):
                immediate_inputs.append(p)
        row={"name":name,"argv":[str(a) for a in argv],"cwd":str(ROOT),
            "deadline_seconds":deadline,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "dedicated_owned_process_group":True,"stdout":str((commands/(name+".stdout")).relative_to(run)),
            "stderr":str((commands/(name+".stderr")).relative_to(run)),"expected_success":expect_success,
            "immediate_inputs_before":[desc(q) if q.is_relative_to(ROOT) else {"path":str(q),"bytes":q.stat().st_size,"sha256":sha(q)} for q in immediate_inputs]}
        receipt["commands"].append(row); save(); started=time.monotonic()
        stdout=run/row["stdout"]; stderr=run/row["stderr"]
        with stdout.open("wb") as out,stderr.open("wb") as err:
            active=subprocess.Popen(row["argv"],cwd=ROOT,stdin=subprocess.DEVNULL,
                stdout=out,stderr=err,start_new_session=True,env=env)
            row["owned_child_pid"]=active.pid; save(); timed=False
            try: code=active.wait(timeout=deadline)
            except subprocess.TimeoutExpired:
                timed=True;os.killpg(active.pid,signal.SIGTERM)
                try:code=active.wait(timeout=2)
                except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);code=active.wait(timeout=5)
            assert active.poll() is not None;active=None
        row.update(returncode=code,timed_out=timed,child_reaped=True,
            elapsed_seconds=round(time.monotonic()-started,6),
            stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),
            stdout_bytes=stdout.stat().st_size,stderr_bytes=stderr.stat().st_size,
            immediate_inputs_after=[desc(q) if q.is_relative_to(ROOT) else {"path":str(q),"bytes":q.stat().st_size,"sha256":sha(q)} for q in immediate_inputs])
        assert row["immediate_inputs_before"]==row["immediate_inputs_after"]
        save()
        print(json.dumps({"command":name,"returncode":code,"timed_out":timed,"seconds":row["elapsed_seconds"]}),flush=True)
        if timed or (expect_success and code!=0):
            raise RuntimeError(name+" failed; first streams and exact source snapshots preserved")
        return stdout.read_text(),stderr.read_text(),code
    def regression_command(name,argv,deadline,env):
        if not focused_resume:return command(name,argv,deadline,env)
        prior=HERE/"run-1";value=json.loads((prior/"receipt.json").read_text())
        assert value["source_and_frozen_inputs_preserved"] and value["all_children_reaped"]
        assert value["candidate_source_sha256"]==receipt["candidate_source_sha256"]
        assert value["parent_source_sha256"]==receipt["parent_source_sha256"]
        assert value["direct_immutable_inputs_after"]==receipt["direct_immutable_inputs_before"]
        selected=next(c for c in value["commands"] if c["name"]==name)
        assert selected["returncode"]==0 and not selected["timed_out"] and selected["child_reaped"]
        stdout=prior/selected["stdout"];stderr=prior/selected["stderr"]
        assert sha(stdout)==selected["stdout_sha256"] and sha(stderr)==selected["stderr_sha256"]
        receipt["regression_references"].append({"name":name,"prior_receipt":desc(prior/"receipt.json"),
            "stdout":desc(stdout),"stderr":desc(stderr),"execution":"preserved run-1 result, not rerun in this attempt",
            "source_sha256":value["candidate_source_sha256"]})
        save()
        return stdout.read_text(),stderr.read_text(),0
    try:
        assert sha(SELECT)=="ae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0"
        receipt["proposal_before"]=verified_seal(PROPOSAL/"seal.json","3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c")
        receipt["accounting_before"]=verified_seal(ACCOUNT,"c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4")
        assert receipt["candidate_source_sha256"]=="2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
        assert receipt["parent_source_sha256"]=="1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"
        receipt["direct_immutable_inputs_before"]=admitted_refs(); save()
        command("git-version",["/usr/bin/git","--version"],10)
        command("revision",["/usr/bin/git","rev-parse","HEAD"],10)
        command("python-version",[sys.executable,"--version"],10)
        rust_version,_,_=command("rust-version",[RUST,"--version","--verbose"],10)
        receipt["tools"]=[{"requested_path":str(p),"resolved_path":str(p.resolve()),"bytes":p.stat().st_size,"sha256":sha(p)}
            for p in [Path(sys.executable),RUST,Path("/usr/bin/git")]]
        receipt["rust_version"]=rust_version
        src=run/"src";src.mkdir()
        for n in ["analyzer.rs","envelope.rs"]:shutil.copy2(PROPOSAL/"src"/n,src/n)
        focused=run/"focused_controls.rs";shutil.copy2(HERE/"focused_controls.rs",focused)
        build=run/"build";(build/"inputs").mkdir(parents=True);(build/"tests").mkdir()
        shutil.copy2(OLD/"tests/independent_tests.rs",build/"independent_tests.rs")
        private_io=OLD/"tests/private_io_tests.rs"
        parent_bytes=(src/"analyzer.rs").read_bytes()
        trailer=("\ninclude!("+json.dumps(str(private_io))+");\n").encode()
        (build/"inputs/framing.rs").write_bytes(parent_bytes+trailer)
        shutil.copy2(src/"envelope.rs",build/"inputs/envelope.rs")
        wrappers=[]
        for name in ["fixture_tests.rs","envelope_tests.rs","correction_tests.rs","selected_tests.rs"]:
            body="include!("+json.dumps(str(OLD/"tests"/name))+");\n"
            if name=="envelope_tests.rs":
                body+="\n#[path = "+json.dumps(str(focused))+"]\nmod absence_controls;\n"
            q=build/"tests"/name;q.write_text(body);wrappers.append(desc(q))
        for name in ["oracle-425.bin","oracle-budget-425.bin"]:
            q=build/"inputs"/name;q.symlink_to(OLD/"inputs"/name);temporary_links.append(q)
        owned_source_inputs=[q for q in sorted(run.rglob("*")) if q.is_file() and q.suffix in {".rs",".py"} and not q.is_symlink()]
        receipt["compiled_owned_inputs_before"]=[desc(q) for q in owned_source_inputs]
        receipt["test_only_parent_shim"]={"parent_prefix_bytes":len(parent_bytes),"parent_prefix_sha256":hashlib.sha256(parent_bytes).hexdigest(),
            "appended_text":trailer.decode(),"immutable_private_IO_input":desc(private_io),
            "shim":desc(build/"inputs/framing.rs"),"product_parent_source_changed":False}
        receipt["test_wrappers"]=wrappers
        receipt["unchanged70_test_bodies"]="6 original sealed test sources are directly included unchanged; new8 controls attach as a child test module in an owned wrapper, not in product source"
        receipt["temporary_oracle_links"]=[{"owned_path":str(q.relative_to(ROOT)),"target":str(q.readlink()),"target_identity":desc(q.resolve())} for q in temporary_links]
        compiled=receipt["compiled_owned_inputs_before"]+receipt["direct_immutable_inputs_before"]+[desc(SELECT),desc(PROPOSAL/"seal.json"),desc(ACCOUNT)]
        receipt["compiled_input_tree_sha256"]=hashlib.sha256(canonical(sorted(compiled,key=lambda d:d["path"]))).hexdigest()
        (run/"compiled-input-manifest.json").write_text(json.dumps({"schema":1,"members":compiled,
            "sha256":receipt["compiled_input_tree_sha256"],
            "oracle_note":"16170 complete +5544 threshold expected cases reused as immutable selected425 inputs; all comparisons execute the new source.",
            "model_executed":False},indent=2,sort_keys=True)+"\n")
        save()
        lib=run/"libmixer_absence.rlib";binaries.append(lib)
        command("compile-library",[RUST,"--edition=2024","--crate-name","mixer_absence","--crate-type=rlib","-Dwarnings",src/"analyzer.rs","-o",lib],60)
        binary=run/"absence-tests";binaries.append(binary)
        command("compile-tests",[RUST,"--edition=2024","--test","-Dwarnings",build/"independent_tests.rs","-o",binary],60)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",
            MIXER_REVIEW_SCRATCH=str(scratch/"review"),
            MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch/"framing"),
            MIXER_ENVELOPE_SCRATCH=str(scratch/"envelope"),
            MIXER_ANALYZER_LIBRARY_HISTORICAL=str(OLD/"inputs/historical"))
        for n in ["review","framing","envelope"]:(scratch/n).mkdir()
        receipt["test_environment"]={k:v for k,v in env.items() if k.startswith("MIXER_") or k=="PYTHONDONTWRITEBYTECODE"}
        listing,_,_=command("list-tests",[binary,"--list"],10,env)
        count=sum(l.endswith(": test") for l in listing.splitlines());assert count==78,count
        receipt["listed_test_methods"]=count
        raw,_,_=regression_command("unchanged-framing44",[binary,"--test-threads=1","--nocapture","--skip","product::fixture_envelope::"],180,env)
        assert "44 passed; 0 failed" in raw
        receipt["unchanged_framing_methods_passed"]=44;save()
        raw,_,_=regression_command("unchanged-envelope26",[binary,"product::fixture_envelope::","--test-threads=1","--nocapture","--skip","absence_controls::"],180,env)
        assert "26 passed; 0 failed" in raw
        assert "ENVELOPE_ORACLE_CASES=16170" in raw and "CORRECTED_FINITE_BUDGET_CASES=5544" in raw
        marker="CORRECTED_ACTUAL_COMPLETE_LAYOUTS="
        assert raw.count(marker)==1
        layout_text=raw.split(marker,1)[1].split("\n",1)[0]
        actual_layouts=json.loads(layout_text)
        expected_layouts=[40,40,40,40,64,80,80,232,232,128,144,128,16,16,2048,8,16,16,16,16,8,16,16,8,24,80,48,72,32,104,144,152]
        assert actual_layouts==expected_layouts
        receipt["unchanged_envelope_methods_passed"]=26
        receipt["fresh_candidate_oracle_comparisons"]={"complete":16170,"threshold":5544,"total":21714,"fresh_model_evaluation":False}
        labels=json.loads((OLD/"actual-complete-layouts.json").read_text())["layouts"]
        assert len(labels)==len(actual_layouts)==32
        (run/"actual-complete-layouts.json").write_text(json.dumps({"schema":1,
            "source_sha256":receipt["candidate_source_sha256"],
            "compiled_input_tree_sha256":receipt["compiled_input_tree_sha256"],
            "raw_command_output":desc((HERE/"run-1/commands/unchanged-envelope26.stdout") if focused_resume else (commands/"unchanged-envelope26.stdout")),
            "fresh_in_this_attempt":not focused_resume,
            "layouts":[{"type":row["type"],"bytes":size} for row,size in zip(labels,actual_layouts,strict=True)],
            "physical_stack_RSS_CPU_qualification":False},indent=2,sort_keys=True)+"\n")
        save()
        raw,_,_=command("focused-absence8",[binary,"absence_controls::","--test-threads=1","--nocapture"],120,env)
        assert "8 passed; 0 failed" in raw
        markers={"absent_cases":("ABSENT_STATE_CONTROLS=15",15),
            "present_underfunded_cases":("PRESENT_UNDERFUNDED_CONTROLS=1700",1700),
            "normal_funded_cases":("NORMAL_FUNDED425_CONTROLS=2",2),
            "invalid_entry_spent_cases":("INVALID_ENTRY_SPENT_CONTROLS=125",125),
            "poststate_matrix_cases":("POSTSTATE_DEBIT_MATRIX_CASES=18144",18144),
            "guard_dispatch_cases":("ACTUAL_GUARD_DISPATCH_CONTROLS=6",6),
            "caller_rejection_and_poison_cases":("CALLER_ZERO_REJECTION_AND_PAID_POISON_MARKER_CONTROLS=12",12),
            "actual_public_counter_cases":("ACTUAL_PUBLIC_COUNTER_CONTROLS=3",3)}
        for marker,_ in markers.values():assert marker in raw,marker
        receipt["focused_methods_passed"]=8
        receipt["focused_control_counts"]={k:n for k,(_,n) in markers.items()}
        save()
        api=run/"api";api.mkdir()
        positive="""use mixer_absence::*;
fn inspect(x:&FixtureEnvelopeOutcomeV1)->bool {
    let _=x.framing();let e=x.envelope();
    let _=(e.boundary(),e.reason(),e.observed_records(),e.state(),e.phase(),e.mask(),e.last_operation(),e.active_operation(),e.requested_function(),e.pin_failure(),e.terminal_failure(),e.last_work(),e.last_instructions(),e.envelope_debit());
    x.full_replay_accepted()||e.semantic_metrics_valid()||x.stored_prefix_validated()
}
fn main(){let _f:fn(&mut std::fs::File,&mut std::fs::File,&mut std::fs::File,&mut std::fs::File)->Result<FixtureEnvelopeOutcomeV1,AnalyzerError>=analyze_fixture_envelope_v1;let _i:fn(&FixtureEnvelopeOutcomeV1)->bool=inspect;}
"""
        (api/"positive.rs").write_text(positive);positive_bin=api/"positive";binaries.append(positive_bin)
        command("api-positive",[RUST,"--edition=2024","-Dwarnings",api/"positive.rs","--extern","mixer_absence="+str(lib),"-o",positive_bin],30)
        negatives={
            "private-field":("use mixer_absence::*;pub fn f(x:&mut FixtureEnvelopeObservationV1){x.envelope_debit=0;}fn main(){}","E0616"),
            "no-clone":("use mixer_absence::*;fn need<T:Clone>(){}fn main(){need::<FixtureEnvelopeObservationV1>();}","E0277"),
            "no-copy":("use mixer_absence::*;fn need<T:Copy>(){}fn main(){need::<FixtureEnvelopeOutcomeV1>();}","E0277"),
            "no-record-constructor":("use mixer_absence::FixtureDecodedRecordV1;fn main(){}","E0432"),
            "no-word-or-boolean-entry":("use mixer_absence::*;fn main(){let mut words=[0u64;16];let _=analyze_fixture_envelope_v1(&mut words,true);}","E0061"),
            "no-private-reply":("use mixer_absence::FixtureEnvelopeReplyV1;fn main(){}","E0432"),
            "no-observation-constructor":("use mixer_absence::*;fn main(){let _=FixtureEnvelopeObservationV1{boundary:FixtureEnvelopeBoundaryV1::Unavailable,reason:FixtureEnvelopeReasonV1::EnvelopeUnavailable,observed_records:0,state:0,phase:0,mask:0,last_operation:0,active_operation:0,requested_function:0,pin_failure:0,terminal_failure:0,last_work:0,last_instructions:0,envelope_debit:0,full_replay_accepted:0,stored_prefix_validated:0};}","E0451"),
            "no-raw-serializer":("use mixer_absence::*;pub fn f(x:&FixtureEnvelopeObservationV1){let _=x.to_bytes();}fn main(){}","E0599")}
        receipt["api_controls"]=[]
        for name,(text,expected) in negatives.items():
            q=api/(name+".rs");q.write_text(text);target=api/name;binaries.append(target)
            _,err,code=command("api-negative-"+name,[RUST,"--edition=2024",q,"--extern","mixer_absence="+str(lib),"-o",target],30,expect_success=False)
            assert code!=0 and expected in err,name
            receipt["api_controls"].append({"name":name,"expected_error":expected,"observed_expected_rejection":True,"source":desc(q)})
        receipt["api_positive_compiles"]=1;receipt["api_expected_negative_compiles"]=8
        receipt["methods_passed"]=78
        receipt["methods_executed_this_attempt"]=8 if focused_resume else 78
        receipt["methods_qualified_across_receipts"]=78
        receipt["status"]="passed"
    except BaseException as e:
        receipt["status"]="failed";receipt["error"]=repr(e)
        print(json.dumps({"status":"failed","error":repr(e)}),flush=True)
    finally:
        if active is not None:
            os.killpg(active.pid,signal.SIGTERM)
            try:active.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait(timeout=5)
            active=None
        try:
            receipt["proposal_after"]=verified_seal(PROPOSAL/"seal.json","3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c")
            receipt["accounting_after"]=verified_seal(ACCOUNT,"c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4")
            receipt["direct_immutable_inputs_after"]=admitted_refs()
            assert receipt["proposal_before"]==receipt["proposal_after"]
            assert receipt["accounting_before"]==receipt["accounting_after"]
            assert receipt["direct_immutable_inputs_before"]==receipt["direct_immutable_inputs_after"]
            receipt["compiled_owned_inputs_after"]=[desc(q) for q in owned_source_inputs]
            assert receipt.get("compiled_owned_inputs_before",[])==receipt["compiled_owned_inputs_after"]
            assert sha(SELECT)==receipt["selection_sha256"]
            receipt["source_and_frozen_inputs_preserved"]=True
        except BaseException as e:
            receipt["preservation_error"]=repr(e);receipt["status"]="failed"
        receipt["scratch_files_before_cleanup"]=[desc(q,scratch) for q in sorted(scratch.rglob("*")) if q.is_file()]
        retained=run/"retained-reports"
        for q in sorted(scratch.rglob("*")):
            if q.is_file() and (("report" in q.name and q.stat().st_size<=49152) or receipt["status"]=="failed"):
                target=retained/str(q.relative_to(scratch));target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,target)
        receipt["retained_reports_or_failure_files"]=[desc(q) for q in sorted(retained.rglob("*")) if q.is_file()] if retained.exists() else []
        shutil.rmtree(scratch);receipt["owned_scratch_removed"]=not scratch.exists()
        receipt["binaries_hashed_then_removed"]=[]
        for p in binaries:
            if p.exists():receipt["binaries_hashed_then_removed"].append(desc(p));p.unlink()
        receipt["temporary_owned_links_removed"]=[]
        for p in temporary_links:
            if p.is_symlink():receipt["temporary_owned_links_removed"].append({"path":str(p.relative_to(ROOT)),"target":str(p.readlink())});p.unlink()
        receipt["all_children_reaped"]=True
        receipt["no_unowned_process_changes"]=True
        receipt["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
        print(json.dumps({"status":receipt["status"],"methods_passed":receipt.get("methods_passed"),
            "source_sha256":receipt["candidate_source_sha256"],"compiled_input_tree_sha256":receipt.get("compiled_input_tree_sha256"),
            "all_children_reaped":True,"owned_scratch_removed":receipt["owned_scratch_removed"]}),flush=True)
    if receipt["status"]!="passed":raise SystemExit(1)

if __name__=="__main__":main()
