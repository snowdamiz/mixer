"""Record bounded next-slice source selection and returned unexecuted runner."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,copy
ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).with_name("next-lifecycle-and-layout-selection.json")
def read(p):return json.loads(p.read_bytes())
def row(p):
 b=p.read_bytes();return {"path":str(p.relative_to(ROOT)),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
assert not DEST.exists(),"One-shot; do not replay"
lane=ROOT/"verification/console-key-owner-lifecycle-contract"
am=lane/"membership-amendment.json"
assert row(am)["sha256"]=="6291f022b841804797a4431c6d3af9853fac4d11db549975b1386ea664ced5da"
a=read(am)
for r in a["files"]:
 actual=row(lane/r["path"]);assert actual["bytes"]==r["bytes"] and actual["sha256"]==r["sha256"]
assert {str(p.relative_to(lane)) for p in lane.rglob("*") if p.is_file()}=={r["path"] for r in a["files"]}|{am.name}
review=ROOT/"verification/swift-root-bound-work-storage-layout-preaccess"
assert row(review/"review-01-seal.json")["sha256"]=="edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c"
lifecycle={"status":"source-contract-selected-implementation-and-host-tests-pending","contract_amendment":row(am),"contract":row(lane/"contract.md"),"prospective_tests":row(lane/"prospective-tests.json"),"source_packet_members_verified":33,"selected_changes":["shared KeyOwner trap_exit before Admission publication","expected-table and ETS-creator guarded Admission.close/2 under serial registered-owner lifecycle","KOL01-KOL07 socket-free supervisor/restart/ownership regressions"],"implementation_lane":"verification/console-key-owner-lifecycle-implementation","runtime_released":False,"product_implementation_accepted":False,"pending":["exact bounded host compilation and tests","KOL08/KOL09 real flight and TLS drain including worker-supervisor-death","production provider/app/HTTP/browser/session/operational/GA"],"atomic_compare_and_erase_claim":False,"frozen_original_membership_omission_preserved":True,"root_initial_path_resolution_error_corrected":True}
layout={"status":"original-runner-returned-unexecuted-separate-correction-in-preparation","original_plan":row(ROOT/"verification/swift-root-bound-work-storage-layout-probe/plan.json"),"original_seal":row(ROOT/"verification/swift-root-bound-work-storage-layout-probe/seal.json"),"preaccess_seal":row(review/"preaccess-seal.json"),"independent_review_seal":row(review/"review-01-seal.json"),"independent_review":row(review/"REVIEW-01.md"),"blocking_findings":["R01 duplicate JSON keys accepted by producer parser","R02 asynchronous launch and cleanup-entry interruption can lose owned-child cleanup"],"correction_lane":"verification/swift-root-bound-work-storage-layout-probe-v2","compiler_lane_released":False,"compiler_invocations":0,"actual_layouts_or_prices_accepted":False,"GA_accepted":False}
w=read(ROOT/"work-graph.json");g=read(ROOT/"gates/ga.json")
for t in [w["packages"][13],g["gates"][21]]:t["fixedWorkspaceDispatcher"]["key_owner_supervised_lifecycle"]=copy.deepcopy(lifecycle)
c=w["packages"][7]["fixtureCacheStateContractCandidate"];assert c==g["gates"][1]["fixtureCacheStateContractCandidate"]
b=c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["layout_probe"]=layout
g["gates"][1]["fixtureCacheStateContractCandidate"]=copy.deepcopy(c)
text="The next ordinary identity-owner slice selects graceful supervised Admission cleanup with an expected-table/creator guard and seven socket-free lifecycle cases; implementation and runtime acceptance remain pending. Existing forced-death denial and real TLS drain retain separate scope. The first Swift layout runner is returned unexecuted for duplicate-key parsing and asynchronous child-tracking/cleanup defects; a separately versioned correction is in preparation. No layout, price or funding is accepted."
for name in ["PLAN.md","STATUS.md"]:
 p=ROOT/name;t=p.read_text();assert text not in t
 marker="Checkpoint `837e7084`";start=t.index(marker);end=t.index("\n\n",start)
 p.write_text(t[:end]+"\n\n"+text+t[end:])
for name,d in [("work-graph.json",w),("gates/ga.json",g)]: (ROOT/name).write_text(json.dumps(d,indent=2)+"\n")
assert w["packages"][13]["fixedWorkspaceDispatcher"]==g["gates"][21]["fixedWorkspaceDispatcher"]
assert sum(t["status"]=="running" for t in g["gates"])==8 and sum(t["status"]=="planned" for t in g["gates"])==30
with DEST.open("x") as f:json.dump({"schema":1,"at":datetime.now(timezone.utc).isoformat(),"lifecycle":lifecycle,"layout":layout,"GA_verified":0,"metadata_files":[row(ROOT/n) for n in ["PLAN.md","STATUS.md","work-graph.json","gates/ga.json"]]},f,indent=2);f.write("\n")
print(json.dumps({"lifecycle_source_contract_selected":True,"layout_original_runtime":False,"layout_correction_pending":True,"GA_verified":0}))
