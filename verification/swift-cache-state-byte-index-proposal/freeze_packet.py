"""Freeze only this new proposal. Existing packets are read, never written."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
root=Path(__file__).resolve().parent
repo=root.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def save(name,data):(root/name).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
inputs=["AGENTS.md","docs/swift-semantic-adapter-prerequisite.md","docs/swift-cache-state-clear128-selection.md",
 "verification/swift-cache-state-implementation/correction-3/candidate-repo-seal.json",
 "verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs",
 "verification/swift-cache-state-implementation/correction-3/source/library/analyzer.rs",
 "verification/swift-cache-state-implementation/correction-3/source/library/envelope.rs",
 "verification/swift-cache-state-g3-proposal3/seal.json","verification/swift-cache-state-g3-proposal4/seal.json",
 "verification/swift-semantic-adapter-root-review/g3-proposal4-disposition.json"]
save("input-manifest.json",[dict(path=p,bytes=len((repo/p).read_bytes()),sha256=sha((repo/p).read_bytes())) for p in inputs])
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip()
c3=json.loads((repo/inputs[3]).read_text())
context=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),command="python3 -B freeze_packet.py",
 python=sys.version,live_context_revision=head,live_tree_clean_claim=False,
 base_source_tree_digest=c3["source_tree_digest"],base_tree_digest_method=c3["source_tree_digest_method"],
 owned_scope=str(root.relative_to(repo)),product_compiler_runtime_or_native_execution=False,
 git_mutations=False,old_packet_mutations=False)
save("source-context.json",context)
ledger=json.loads((root/"operation-ledger.json").read_text())
models=json.loads((root/"model-results.json").read_text())
attempts=[]
for p in sorted((root/"attempts").iterdir()):
 r=json.loads((p/"result.json").read_text())
 attempts.append(dict(path=str(p.relative_to(root)),exit_code=r["exit_code"],raw_outputs_preserved=True,exact_source_script_preserved=(p/"source_checks.py").exists()))
save("handoff.json",dict(status="unselected exact source-only proposal ready for independent review",
 affected_group_bounds=ledger["totals"],models=models,attempts=attempts,
 source_accounting_accepted=False,compiler_or_runtime_qualified=False,lifetime_29344_union_proved=False,
 G6_owned_elsewhere_and_unchanged=True,independent_accepted=False,root_selected=False,
 candidate_owner_bytes=2048,role_union_proposed_cap=29344,role_reserved_cap=41984,global_transient_cap=65536,
 pending=["Independent model/source review including platform intrinsic boundary","Root contract/layout/source selection","Complete inherited role/lifetime reconciliation and fresh compiler layouts","Rust compilation/borrow checking and host behavior/API/regression qualification","Native runtime/capture remain paused; physical checks pending final acceptance"],
 bounded_fallback="If independent review rejects the finite view primitive boundary, keep byte indices and review an equivalent one-time fixed-array borrowing construction before implementation; do not raise caps or infer universal impossibility."))
members=[]
for p in sorted(root.rglob("*")):
 if p.is_file() and p.name!="seal.json":
  data=p.read_bytes();members.append(dict(path=str(p.relative_to(repo)),bytes=len(data),sha256=sha(data)))
save("seal.json",dict(schema=1,at=context["at"],members=members,member_count=len(members),
 member_bytes=sum(x["bytes"] for x in members),source_model_only=True,source_accounting_accepted=False,
 independent_accepted=False,root_selected=False,compiler_or_runtime_execution=False,
 source_tree_digest=sha(json.dumps([x for x in members if "/source/" in x["path"]],sort_keys=True,separators=(",",":")).encode()),
 source_tree_digest_method="SHA256 compact sorted-key JSON of path-sorted source member rows"))
print(json.dumps(dict(seal_sha256=sha((root/"seal.json").read_bytes()),members=len(members),member_bytes=sum(x["bytes"] for x in members),context=context,affected_group_bounds=ledger["totals"]),indent=2,sort_keys=True))
