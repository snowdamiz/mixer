#!/usr/bin/env python3
"""Bounded independent host controls. Does not invoke producer scripts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
RUSTC=Path("/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc")
RUN=OUT/"runs"/os.environ.get("REVIEW_RUN_ID","run-3")
SCRATCH=OUT/"scratch"/os.environ.get("REVIEW_RUN_ID","run-3")

def info(p):
 b=p.read_bytes();return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def js(p,v): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def group_exists(pid):
 try: os.killpg(pid,0);return True
 except ProcessLookupError:return False
def run(name,argv,deadline=120,expected=0,extra=None):
 d=RUN/name;d.mkdir(parents=True,exist_ok=False);started=datetime.now(timezone.utc).isoformat();t=time.monotonic()
 env=os.environ.copy();env["REVIEW_SCRATCH"]=str(SCRATCH/"fixtures"/name);env["LC_ALL"]="C"
 if extra:env.update(extra)
 with (d/"stdout.bin").open("wb") as out,(d/"stderr.bin").open("wb") as err:
  child=subprocess.Popen([str(a) for a in argv],cwd=ROOT,env=env,stdout=out,stderr=err,start_new_session=True)
  timeout=False
  try:code=child.wait(timeout=deadline)
  except subprocess.TimeoutExpired:
   timeout=True;os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=10)
  remains=group_exists(child.pid)
  if remains:
   os.killpg(child.pid,signal.SIGKILL)
   for _ in range(20):
    if not group_exists(child.pid):break
    time.sleep(.01)
  remains=group_exists(child.pid)
 bindings={str(p.relative_to(OUT)):info(p) for p in [OUT/"source/analyzer.rs",OUT/"source/envelope.rs",OUT/"tests/envelope_tests.rs",OUT/"tests/caller_cases.rs",OUT/"run_review.py"] if p.exists()}
 receipt={"input_bindings":bindings,"schema":1,"argv":[str(a) for a in argv],"cwd":str(ROOT),"at":started,"deadline_seconds":deadline,"elapsed_seconds":time.monotonic()-t,"pid":child.pid,"owned_process_group":child.pid,"returncode":code,"timed_out":timeout,"direct_child_reaped":child.returncode is not None,"owned_group_absent":not remains,"stdout":info(d/"stdout.bin"),"stderr":info(d/"stderr.bin"),"expected":expected}
 js(d/"receipt.json",receipt);print(json.dumps({"command":name,"returncode":code,"timed_out":timeout,"group_absent":not remains}),flush=True)
 assert not remains,name
 if expected=="timeout":assert timeout,name
 elif expected=="nonzero":assert code!=0 and not timeout,name
 else:assert code==expected and not timeout,(name,code)
 return receipt

def prepare_counter():
 source=OUT/"source/envelope.rs";data=source.read_text();old="let received = observe_fixture_envelope_v1(&mut arena.bytes, &mut candidate, &record, &mut steps);"
 new="let received = independent_counted_leaf(&mut arena.bytes, &mut candidate, &record, &mut steps);"
 assert data.count(old)==1
 suffix='''
// Independent test-only interposition: one dispatch callsite delegates unchanged.
#[cfg(test)]
static INDEPENDENT_DISPATCH: std::sync::atomic::AtomicUsize = std::sync::atomic::AtomicUsize::new(0);
#[cfg(test)]
fn independent_counted_leaf(a:&mut[u8],c:&mut Candidate2048,r:&FixtureDecodedRecordV1<'_>,s:&mut StepBudget)->FixtureEnvelopeReplyV1 {
 INDEPENDENT_DISPATCH.fetch_add(1,std::sync::atomic::Ordering::SeqCst);
 observe_fixture_envelope_v1(a,c,r,s)
}
#[cfg(test)]
#[path="../tests/counter_tests.rs"]
mod independent_counted;
'''
 dest=OUT/"instrumented"; (dest/"source").mkdir(parents=True);(dest/"tests").mkdir()
 (dest/"source/analyzer.rs").write_bytes((OUT/"source/analyzer.rs").read_bytes())
 (dest/"source/envelope.rs").write_text(data.replace(old,new)+suffix)
 own=(OUT/"tests/envelope_tests.rs").read_text().replace("#[test]", "// test registration omitted in interposition build")
 for name in ["prior","initialized","phase_record","progress","scratch","files","stream","phases","profile_bytes","context","open"]:
  own=own.replace("\nfn "+name+"(","\npub(super) fn "+name+"(")
 (dest/"tests/envelope_tests.rs").write_text(own)
 for name in ["fixture_tests.rs","correction_tests.rs","caller_cases.rs"]:shutil.copyfile(OUT/"tests"/name,dest/"tests"/name)
 shutil.copyfile(OUT/"counter_tests.rs",dest/"tests/counter_tests.rs")
 js(OUT/"instrumentation-binding.json",{"schema":1,"scope":"independent test-only interposition; not exact selected source runtime claim","selected_source":info(source),"derivative_source":info(dest/"source/envelope.rs"),"single_replacement":{"from":old,"to":new,"count":1},"appended_suffix":suffix,"leaf_body_unchanged":True,"producer_tests_used":False})

def api_probes():
 api=OUT/"api";api.mkdir(exist_ok=True)
 probes={
 "positive":('use independent_selected::*;use std::fs::File; fn main(){let _:fn(&mut File,&mut File,&mut File,&mut File)->Result<FixtureEnvelopeOutcomeV1,AnalyzerError>=analyze_fixture_envelope_v1;let _=FixtureEnvelopeObservationV1::envelope_debit;let _=FixtureEnvelopeObservationV1::full_replay_accepted;let _=FixtureEnvelopeOutcomeV1::framing;}',None,None),
 "private-record":('use independent_selected::fixture_envelope::FixtureDecodedRecordV1;fn main(){}','E0603','private'),
 "private-leaf":('fn main(){let _=independent_selected::fixture_envelope::observe_fixture_envelope_v1;}','E0603','private'),
 "private-field":('use independent_selected::*;fn probe(x:FixtureEnvelopeObservationV1){let _=x.state;}fn main(){}','E0616','state'),
 "no-Copy":('use independent_selected::*;fn require<T:Copy>(){} fn main(){require::<FixtureEnvelopeObservationV1>();}','E0277','Copy'),
 "no-Clone":('use independent_selected::*;fn require<T:Clone>(){} fn main(){require::<FixtureEnvelopeObservationV1>();}','E0277','Clone'),
 "no-word-trust-constructor":('use independent_selected::*;fn main(){let _=FixtureEnvelopeObservationV1::from_words_and_trust([0u64;16],true);}','E0599','from_words_and_trust'),
 "no-serializer":('use independent_selected::*;fn probe(x:FixtureEnvelopeObservationV1){let _=x.to_words();}fn main(){}','E0599','to_words'),
 "no-descriptor-authority-entry":('fn main(){let _=independent_selected::analyze_fixture_envelope_from_descriptor;}','E0425','analyze_fixture_envelope_from_descriptor'),
 }
 results=[]
 for name,(text,code,fragment) in probes.items():
  p=api/(name+".rs");p.write_text(text+"\n")
  run("api-"+name,[RUSTC,"--edition=2021","--crate-name","probe",p,"--extern","independent_selected="+str(SCRATCH/"libindependent_selected.rlib"),"--emit=metadata","-o",SCRATCH/(name+".rmeta")],expected="nonzero" if code else 0)
  stderr=(RUN/("api-"+name)/"stderr.bin").read_text()
  intended=(code in stderr and fragment in stderr) if code else True
  assert intended,(name,stderr)
  results.append({"name":name,"intended_error_code":code,"intended_fragment":fragment,"intended_reason_verified":intended,"probe":info(p)})
 js(OUT/"api-results.json",{"positive":1,"expected_negative":8,"results":results})

def cleanup():
 manifest=[];reports=OUT/"reports"
 if SCRATCH.exists():
  for p in sorted(SCRATCH.rglob("*")):
   if p.is_file():
    row={"scratch_path":str(p.relative_to(OUT)),**info(p)}
    if p.suffix==".report":
     dest=reports/p.relative_to(SCRATCH);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);row["retained_report"]=str(dest.relative_to(OUT))
    manifest.append(row)
  shutil.rmtree(SCRATCH)
 js(RUN/"cleanup.json",{"schema":1,"all_command_receipts_require_reaped_child_and_absent_owned_group":True,"scratch_removed":not SCRATCH.exists(),"scratch_files_hashed_before_removal":manifest,"no_process_discovery":True,"no_native_capture_UI_started":True,"other_projects_untouched":True})
 shutil.copyfile(RUN/"cleanup.json",OUT/"cleanup.json")

def main():
 assert not RUN.exists() and not SCRATCH.exists(),"run namespace must be fresh"
 SCRATCH.mkdir(parents=True)
 result={"status":"not-complete"}
 try:
  run("prepare",[sys.executable,"-B",OUT/"prepare.py"])
  run("rust-version",[RUSTC,"--version","--verbose"],deadline=30)
  run("python-version",[sys.executable,"--version"],deadline=30)
  run("revision",["git","rev-parse","HEAD"],deadline=30)
  run("runner-timeout-qualification",[sys.executable,"-u","-c","import time; print('independent partial marker',flush=True); time.sleep(2)"],deadline=.2,expected="timeout")
  assert b"independent partial marker" in (RUN/"runner-timeout-qualification/stdout.bin").read_bytes()
  run("compile-tests",[RUSTC,"--edition=2021","-O","--test",OUT/"source/analyzer.rs","--crate-name","independent_review","-o",SCRATCH/"tests"])
  run("list-tests",[SCRATCH/"tests","--list"],deadline=30)
  test_receipt=run("independent-tests",[SCRATCH/"tests","--nocapture","--test-threads=1"],deadline=120)
  run("compile-library",[RUSTC,"--edition=2021","-O","--crate-type=rlib","--crate-name","independent_selected",OUT/"source/analyzer.rs","-o",SCRATCH/"libindependent_selected.rlib"])
  api_probes()
  prepare_counter()
  run("compile-counter",[RUSTC,"--edition=2021","-O","--test",OUT/"instrumented/source/analyzer.rs","--crate-name","independent_counted_review","-o",SCRATCH/"counter-tests"])
  run("counter-tests",[SCRATCH/"counter-tests","--nocapture","--test-threads=1"],deadline=120)
  result={"status":"commands-complete","exact_source":info(OUT/"source/envelope.rs"),"parent_source":info(OUT/"source/analyzer.rs"),"rustc":info(RUSTC),"rustc_invoked_path":str(RUSTC),"python":sys.version,"run_review_script":info(Path(__file__)),"producer_scripts_tests_executed":False,"context_revision":(RUN/"revision/stdout.bin").read_text().strip(),"test_receipt":test_receipt}
 finally:
  cleanup();js(OUT/"execution-receipt.json",result)

if __name__=="__main__":main()
