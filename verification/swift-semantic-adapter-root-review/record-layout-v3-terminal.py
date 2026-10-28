"""Record the one actual query rejection and confirmed cleanup without accepting layouts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,copy
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent
DEST=OUT/"root-bound-work-storage-layout-v3-terminal.json"
def read(p):return json.loads(p.read_bytes())
def row(p):
 b=p.read_bytes();return {"path":str(p.relative_to(ROOT)),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
assert not DEST.exists(),"One-shot; do not replay"
lane=ROOT/"verification/swift-root-bound-work-storage-layout-probe-v3"
r=read(lane/"command/receipt.json")
assert r["compiler_invocations"]==1 and r["compiler_exit_code"]==1 and not r["accepted_diagnostic_observation"]
assert r["posthashes_verified"] and r["ownership"]["child_reaped"] and r["ownership"]["exact_pid_absent"] and r["ownership"]["exact_group_absent"]
assert r["build_cleanup"]["removed"] and not r["build_cleanup"]["inventory"]
assert row(lane/"command/stderr")["sha256"]=="05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635"
raw=[json.loads(x) for x in (lane/"command/stderr").read_text().splitlines()]
codes={c:sum((x.get("code") or {}).get("code")==c for x in raw) for c in ["E0308","E0512","unused_imports","deprecated",None]}
assert codes=={"E0308":56,"E0512":2,"unused_imports":2,"deprecated":1,None:3}
info={"status":"single-v3-compiler-query-rejected-by-frozen-warning-policy-cleanup-confirmed","compiler_invocations":1,"compiler_exit":1,"elapsed_seconds":r["elapsed_seconds_including_cleanup_posthashes"],"v3_plan":row(lane/"plan.json"),"v3_seal":row(lane/"seal.json"),"execution_release":row(OUT/"root-bound-work-storage-layout-release.json"),"execution_receipt":row(lane/"command/receipt.json"),"execution_members":[row(p) for p in sorted((lane/"command").rglob("*")) if p.is_file()],"raw_diagnostic_counts":codes,"frozen_policy_rejection":r["failures"],"cleanup":r["ownership"],"build_cleanup":r["build_cleanup"],"all_source_tool_posthashes_verified":True,"compiler_lane_free":True,"automatic_retries":0,"original_v1_v2_never_executed":True,"independent_terminal_review_pending":True,"actual_layouts_prices_backing_peaks_funding_ownership_GA_accepted":False}
w=read(ROOT/"work-graph.json");g=read(ROOT/"gates/ga.json")
c=w["packages"][7]["fixtureCacheStateContractCandidate"];assert c==g["gates"][1]["fixtureCacheStateContractCandidate"]
b=c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
l=b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]
l.update({"status":info["status"],"compiler_invocations":1,"compiler_lane_released":False,"v3_execution":copy.deepcopy(info),"v2_review":row(ROOT/"verification/swift-root-bound-work-storage-layout-preaccess/review-02-seal.json"),"v3_review":row(ROOT/"verification/swift-root-bound-work-storage-layout-preaccess/review-03-seal.json"),"correction_lane":"verification/swift-root-bound-work-storage-layout-probe-v3","actual_layouts_or_prices_accepted":False})
g["gates"][1]["fixtureCacheStateContractCandidate"]=copy.deepcopy(c)
old="The first Swift layout runner is returned unexecuted for duplicate-key parsing and asynchronous child-tracking/cleanup defects; a separately versioned correction is in preparation. No layout, price or funding is accepted."
new="The original and second Swift layout runners remain unexecuted after parsing, cleanup and final-publication review findings. The independently reviewed third runner completed one compiler-only query in 2.26 seconds with confirmed child/group and build cleanup, but its frozen policy rejects two unused-import and one deprecation warnings. The raw 58 intended errors and three warnings are preserved for separate offline classification; no compiler retry, layout, price or funding is accepted."
for name in ["PLAN.md","STATUS.md"]:
 p=ROOT/name;t=p.read_text();assert t.count(old)==1;p.write_text(t.replace(old,new))
for name,d in [("work-graph.json",w),("gates/ga.json",g)]: (ROOT/name).write_text(json.dumps(d,indent=2)+"\n")
assert sum(t["status"]=="running" for t in g["gates"])==8 and sum(t["status"]=="planned" for t in g["gates"])==30
with DEST.open("x") as f:json.dump({"schema":1,"at":datetime.now(timezone.utc).isoformat(),"query":info,"GA_verified":0,"metadata_files":[row(ROOT/n) for n in ["PLAN.md","STATUS.md","work-graph.json","gates/ga.json"]]},f,indent=2);f.write("\n")
print(json.dumps({"one_compiler_query":"rejected-warning-policy","cleanup_confirmed":True,"compiler_lane_free":True,"GA_verified":0}))
