#!/usr/bin/env python3
"""Audit own evidence and freeze exact bounded review results."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
import prepare

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def info(path):
 b=path.read_bytes();return {"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)}
def js(path,v):path.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")

def main():
 admitted=[]
 for name,expected in prepare.PINS.items():
  p=ROOT/name;assert info(p)["sha256"]==expected,name;seal=json.loads(p.read_text())
  if "members" in seal:
   members=seal["members"]
   if isinstance(members,dict):members=[{"path":k,**v} for k,v in members.items()]
   for m in members:assert info(ROOT/m["path"])=={"sha256":m["sha256"],"bytes":m["bytes"]},m["path"]
   admitted.append({"seal":name,"sha256":expected,"members":len(members),"bytes":sum(m["bytes"] for m in members)})
 assert info(OUT/"source/envelope.rs")["sha256"]=="2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
 assert info(OUT/"source/analyzer.rs")["sha256"]=="1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b"
 old=ROOT/"verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs"
 assert info(old)["sha256"]=="7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1"
 delta="".join(difflib.unified_diff(old.read_text().splitlines(True),(OUT/"source/envelope.rs").read_text().splitlines(True),fromfile="old-7b8237",tofile="selected-2cd286"))
 (OUT/"independent-source-delta.diff").write_text(delta)
 run3=(OUT/"runs/run-3/independent-tests/stdout.bin").read_text();run6=(OUT/"runs/run-6/counter-tests/stdout.bin").read_text()
 assert "12 passed; 0 failed" in run3 and "2 passed; 0 failed" in run6
 exact=[{"method":n,"run":"run-3","selected_source_unchanged":True} for n in re.findall(r"test fixture_envelope::tests::(independent_\w+) ",run3)]
 assert len(exact)==12
 for method in ["independent_setup_finish_admission_retains0_and534_before_cells","independent_allocator_helper_and_early_outer_limit_errors"]:
  raw=(OUT/"runs/run-5"/method/"stdout.bin").read_text();assert "1 passed; 0 failed" in raw;exact.append({"method":method,"run":"run-5","selected_source_unchanged":True})
 layouts=re.findall(r"layout,([^,\n]+),(\d+),(\d+)",run3);assert len(layouts)==32
 js(OUT/"layouts.json",{"scope":"actual host Rust layout observations, not physical stack/RSS/native performance","rows":[{"type":n,"size":int(s),"alignment":int(a)} for n,s,a in layouts]})
 receipts=[]
 for p in sorted((OUT/"runs").glob("run-*/*/receipt.json")):
  r=json.loads(p.read_text());assert r["direct_child_reaped"] and r["owned_group_absent"];assert r["deadline_seconds"]<=120
  for stream in ["stdout","stderr"]:assert info(p.parent/(stream+".bin"))==r[stream]
  receipts.append({"path":str(p.relative_to(OUT)),"returncode":r["returncode"],"timed_out":r["timed_out"],"deadline_seconds":r["deadline_seconds"]})
 assert len(receipts)==41
 assert not list((OUT/"scratch").glob("run-*"))
 api=json.loads((OUT/"api-results.json").read_text());assert api["positive"]==1 and api["expected_negative"]==8 and all(r["intended_reason_verified"] for r in api["results"])
 # Command input bindings point to retained exact earlier test corpora where
 # later narrow controls were appended to the current test source.
 retained_test=OUT/"attempts/run-3-exact-passing/tests/envelope_tests.rs"
 r3=json.loads((OUT/"runs/run-3/compile-tests/receipt.json").read_text())
 assert info(retained_test)==r3["input_bindings"]["tests/envelope_tests.rs"]
 rows=[
  ("absent-boundary",["independent_r2_absent_precedes_all_funding_and_preserves_bytes"],"15 direct private calls; original ten debit zeros; no end-to-end public absent fault"),
  ("readable-underfunding",["independent_readable_underfunded_all425_first_later_valid_malformed"],"1700 direct private calls and complete byte snapshots"),
  ("full-readability-funding",["independent_full_readability_exact425_and426_normal_and_atomic_refusal"],"direct leaf426 accepted; caller paid remaining1 rejected"),
  ("invalid-entry-spent",["independent_invalid_entry_spent_poison_is_unpaid_and_immutable"],"12 private boundary calls; caller incoherent form rejected"),
  ("caller-poststate19",["independent_corrected_caller_poststate_table19"],"no entry-history or general shape certificate"),
  ("canonical-helper-shape",["independent_canonical_helpers_and_malformed_shape_boundary"],"actual helper mapping and direct finalizer checks; no arbitrary corruption latch"),
  ("R1-and-terminal-refusal",["independent_r1_reason15_and_canonical_refusal_terminal_finalization"],"poison priority/zero extent for complete and limited framing"),
  ("G-local-admission",["independent_G_report_reservation_111_112_113_before_selected_cell_mutation"],"local111/112/113, not overall public limits; accounting ownership comes from root selection"),
  ("setup-finish-admission",["independent_setup_finish_admission_retains0_and534_before_cells"],"selected cells/reply validity checked; Reader buffer may change"),
  ("public-File-report",["independent_actual_safe_files_reports_and_paid_decode_footer_suppression"],"seven paired actual Files; phase-only completion/CAP, not hit/build finite matrix"),
  ("zero-call-and-footer",["independent_actual_files_private_limit_zero_call_and_footer_override"],"two actual Files at private limit seam; full arena; debit581"),
  ("outer-output",["independent_outer_output_errors_return_no_aggregate"],"three scripted output errors, no aggregate"),
  ("allocator-and-limit",["independent_allocator_helper_and_early_outer_limit_errors"],"allocator helper + outer zero-limit; no whole-core allocation fault injection"),
  ("host-layout32",["independent_32_complete_host_layouts"],"one method with32 complete host observations; Result232"),
 ]
 coverage={"schema":1,"scope_verdict":"bounded-corrected-controls-pass-root-acceptance-separate","exact_source_unique_methods_passed":14,"exact_source_methods":exact,"rows":[{"control":c,"methods":m,"status":"scoped-host-executed-pass","limitation":l} for c,m,l in rows],"test_only_overlay_methods_passed":2,"overlay_run":"run-6","overlay_binding":"instrumentation-binding.json","overlay_scope":"one dispatch-call interposition and unchanged leaf delegation; private terminal compositions distinct from actual public File5dispatches","API_positive":1,"API_expected_negative":8,"API_intended_reasons_verified":True,"observed_layouts":32,"R2_original_expected_and_actual_debits":[0]*10,"new_candidate_mismatches_found":0,"review_model_errors_preserved":4,"reviewer_execution_errors_preserved":3,"cleanup_retention_gap_disclosed_and_repaired":True,"reused_contracts_not_rerun_results":["global limits and public formula","independent offline accounting352checks121rows108edges","prior18passing/1R2failure and old packet identities"],"not_rerun":["old44","producer70","full finite model","all hit/build/CAP states","all I/O/alias variants"],"implementation_accepted":False,"native_or_capture_started":False,"GA_qualified":False}
 js(OUT/"coverage.json",coverage)
 tool=Path("/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc")
 final={"schema":1,"at":datetime.now(timezone.utc).isoformat(),"command":[sys.executable,"-B",str(Path(__file__).resolve())],"python_version":sys.version,"context_revision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"context_committed_tree":subprocess.check_output(["git","rev-parse","HEAD^{tree}"],cwd=ROOT,text=True).strip(),"tree_scope":"context only; exact reviewed source pair/test hashes bind isolated runtime evidence","selected_source_pair":{n:info(OUT/"source"/n) for n in ["analyzer.rs","envelope.rs"]},"rustc_invoked_path":str(tool),"rustc_binary_at_closure":info(tool),"rustc_version_output":info(OUT/"runs/run-3/rust-version/stdout.bin"),"admitted_packets_after_execution":admitted,"original10members_preserved":True,"commands":receipts,"commands_count":len(receipts),"all_owned_groups_absent":True,"all_direct_children_reaped":True,"candidate_or_compiler_timeouts":0,"deliberate_runner_timeout_controls":3,"all_scratch_run_directories_removed":True,"exact_source_methods_passed":14,"overlay_methods_passed":2,"API_positive":1,"API_expected_negative":8,"candidate_defects_observed_in_scope":0,"reviewer_errors":"original four preaccess errors plus three preserved execution errors; cleanup retention amendment separately disclosed","no_producer_scripts_tests_imported_or_executed":True,"no_process_discovery_native_capture_UI_or_forbidden_hosted_execution":True,"scope_verdict":coverage["scope_verdict"],"implementation_accepted":False,"GA_qualified":False}
 js(OUT/"final-receipt.json",final)
 doc=OUT.parent/"final-review.md"
 members=[doc,*sorted(p for p in OUT.rglob("*") if p.is_file() and p.name!="seal.json")]
 assert not any("__pycache__" in p.parts for p in members)
 seal={"schema":1,"status":"bounded-independent-behavior-review-frozen","members":[{"path":str(p.relative_to(ROOT)),**info(p)} for p in members],"member_count":len(members),"total_bytes":sum(p.stat().st_size for p in members),"selected_source_sha256":"2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef","exact_source_methods_passed":14,"overlay_methods_passed":2,"API_positive":1,"API_expected_negative":8,"implementation_accepted":False,"GA_qualified":False}
 js(OUT/"seal.json",seal)
 print(json.dumps({"status":seal["status"],"seal_sha256":info(OUT/"seal.json")["sha256"],"members":len(members),"bytes":seal["total_bytes"],"exact_source_methods_passed":14,"overlay_methods_passed":2,"API_positive":1,"API_expected_negative":8},sort_keys=True))

if __name__=="__main__":main()
