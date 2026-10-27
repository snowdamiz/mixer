"""Freeze this review after deleting only exact known owned compiler scratch."""
from pathlib import Path
import datetime,hashlib,json,platform,sys

HERE=Path(__file__).resolve().parent
V=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())


def main():
    assert not (HERE/"seal.json").exists(),"frozen review must not be overwritten"
    producer=V/"swift-guarded-snapshot-owner-storage-closure"
    sb=(producer/"seal.json").read_bytes()
    assert sha(sb)=="afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b"
    entries=json.loads(sb)["members"]
    for m in entries:
        b=(producer/m["path"]).read_bytes()
        assert (len(b),sha(b))==(m["bytes"],m["sha256"])
    assert len(entries)==113 and sum(m["bytes"] for m in entries)==31011599
    deleted=[];commands=[]
    for context in ["production","unit","baseline"]:
        r=read(HERE/"commands"/context/"receipt.json")
        assert r["exit_code"]==0 and r["child_reaped"] and r["owned_group_absent"] and not r["timed_out"]
        commands.append({"context":context,"receipt":"commands/"+context+"/receipt.json","output_sha256":r["output_sha256"],"compiler_sha256":r["compiler_sha256"],"source_tree_sha256":r["source_tree_sha256"]})
        path=HERE/"owned-work"/(context+".mir")
        if path.exists():
            b=path.read_bytes();assert (len(b),sha(b))==(r["output_bytes"],r["output_sha256"])
            deleted.append({"path":str(path.relative_to(HERE)),"bytes":len(b),"sha256":sha(b)})
            path.unlink()
    if (HERE/"owned-work").exists():(HERE/"owned-work").rmdir()
    cache=HERE/"__pycache__"
    if cache.exists():
        for p in cache.iterdir():
            assert p.is_file() and p.name.startswith("reconcile.") and p.suffix==".pyc"
            b=p.read_bytes();deleted.append({"path":str(p.relative_to(HERE)),"bytes":len(b),"sha256":sha(b)});p.unlink()
        cache.rmdir()
    (HERE/"cleanup.json").write_text(json.dumps({"schema":1,"known_owned_files_deleted":deleted,"known_owned_compiler_groups_absent_at_reaped_completion":True,"global_process_inventory":False,"other_projects_touched":False},indent=2)+"\n")
    rec=read(HERE/"reconciliation.json");layouts=read(HERE/"layout-provenance.json");legacy=read(HERE/"legacy-reproduction.json")
    review={"schema":1,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"status":"correction-required-original-producer-not-accepted","command":[sys.executable,str(Path(__file__).resolve())],"python_version":platform.python_version(),"producer_seal_sha256":sha(sb),"producer_members_verified":113,"producer_bytes_verified":31011599,"source_revision":"38084d610c3b24d1146aae26f2012b3fb78e0e68","source_revision_provenance":"frozen source authority/preaccess; no Git query or mutation","source_tree_sha256":rec["source_tree_sha256"],"compiler_builds":commands,"functions":rec["functions"],"roles":rec["roles"],"inherited_aliases_examined":357,"affected_current_aliases":29,"receiver_permutations":13,"borrow_or_argument_context_collisions":8,"drop_flag_owner_collisions":7,"new_failure_boundary_unproved_alias_bytes":1096,"truncated_call_targets":rec["truncated_target_displays"],"missing_owned_callback_edges":rec["callback_edges_missing_from_producer"],"complete_calls":627,"independently_reconstructed_graph_acyclic":True,"baseline_roles":legacy["baseline_roles"],"legacy_callee_fingerprints":35,"layout_variants_checked":layouts["actual_generic_role_variants"],"host_product_roles":53,"host_harness_roles":163,"host_bytes_recomputed":81327,"owner_only_proposal_recomputed":rec["owner_only_recomputed"],"emission_helper_overlay_read":False,"correction_lane_read":False,"product_runtime_executions":0,"paused_surface_or_process_inventory_executions":0,"canonical_or_git_mutations":False,"storage_floor_selected":False,"healthy_cleanup_accepted":False,"production_caller_accepted":False,"operational_acceptance":False,"GA_gates_verified":0,"limitations":["Raw producer LLVM layouts independently decoded; fresh compiler reproduction covers exact production/unit/baseline MIR, without executing product functions.","No physical-stack/RSS/ABI/unwind/spill/private-library/external-pointee bound.","WASI pairing error disposition/runtime fault controls, later helper delta, source integration/work/stop policy and genuine execution remain separate pending work."]}
    (HERE/"review.json").write_text(json.dumps(review,indent=2)+"\n")
    members=[]
    for p in sorted(HERE.rglob("*")):
        if p.is_file() and p.name!="seal.json":
            b=p.read_bytes();members.append({"path":str(p.relative_to(HERE)),"bytes":len(b),"sha256":sha(b)})
    seal={"schema":1,"member_count":len(members),"total_bytes":sum(m["bytes"] for m in members),"members":members,"scope":"Independent original owner-storage base review; correction required; no storage/runtime/GA acceptance"}
    (HERE/"seal.json").write_text(json.dumps(seal,indent=2)+"\n")
    print(json.dumps({"status":review["status"],"members":len(members),"bytes":seal["total_bytes"],"seal_sha256":sha((HERE/"seal.json").read_bytes())}))


if __name__=="__main__":main()
