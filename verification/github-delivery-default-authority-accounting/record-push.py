"""Record the delivered scoped evidence and initial remote CI without extending acceptance."""
from datetime import datetime, timezone
import copy, hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = OUT / "post-push-metadata.json"
def read(p): return json.loads(p.read_bytes())
def row(p):
 b=p.read_bytes(); return {"path":str(p.relative_to(ROOT)),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
assert not DEST.exists(), "One-shot; do not replay"
r=read(OUT/"receipt.json")
assert r["commit"]=="837e7084a0c6e69a88848b484fa3556563c75a59" and r["pushed"] and not r["force"]
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True,timeout=10).strip()==r["commit"]
runs=read(OUT/"ci-runs-1.stdout")
assert len(runs)==2 and all(x["headSha"]==r["commit"] for x in runs)
d={"status":"pushed-Engine-and-Phoenix-CI-pending","commit":r["commit"],"tree":r["tree"],"changed_paths":r["committed_paths"],"canonical_paths":r["canonical_paths"],"receipt":row(OUT/"receipt.json"),"manifest":r["manifest"],"initial_CI":row(OUT/"ci-runs-1.stdout"),"runs":runs,"pushed":True,"force":False,"active_layout_lanes_excluded":True,"GA_accepted":False}
w=read(ROOT/"work-graph.json");g=read(ROOT/"gates/ga.json")
for t in [w["packages"][13],g["gates"][21]]:
 f=t["fixedWorkspaceDispatcher"]
 for key in ["default_authority_candidate","component_test_correction"]:
  f[key].update({"delivery_pending":False,"delivery":copy.deepcopy(d)})
c=w["packages"][7]["fixtureCacheStateContractCandidate"]
assert c==g["gates"][1]["fixtureCacheStateContractCandidate"]
b=c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"].update({"delivery_pending":False,"delivery":copy.deepcopy(d)})
g["gates"][1]["fixtureCacheStateContractCandidate"]=copy.deepcopy(c)
paragraph="Checkpoint `837e7084` is pushed with 644 selected paths: the dispatcher test isolation correction, accepted seven-method default-authority host qualification, and independently reviewed finite Swift accounting inventory. Engine and Phoenix CI are running. The sole canonical source change is the dispatcher test setup; active layout preparation and preaccess review were excluded. Supervised provider lifecycle, session/browser integration, numerical work/storage prices, root funding, native qualification and every GA gate remain pending."
for name in ["PLAN.md","STATUS.md"]:
 p=ROOT/name;t=p.read_text();assert paragraph not in t
 if name=="PLAN.md":
  marker="## Resumed checkpoint\n\n";assert t.count(marker)==1;t=t.replace(marker,marker+paragraph+"\n\n",1)
 else:
  pos=t.index("\n\n")+2;t=t[:pos]+paragraph+"\n\n"+t[pos:]
 p.write_text(t)
for name,data in [("work-graph.json",w),("gates/ga.json",g)]: (ROOT/name).write_text(json.dumps(data,indent=2)+"\n")
assert w["packages"][13]["fixedWorkspaceDispatcher"]==g["gates"][21]["fixedWorkspaceDispatcher"]
assert w["packages"][4]["privateOwnerEffectContractCandidate"]==g["gates"][4]["privateOwnerEffectContractCandidate"]
assert sum(x["status"]=="running" for x in g["gates"])==8
assert sum(x["status"]=="planned" for x in g["gates"])==30
for path,digest in r["protected_work_unchanged"].items(): assert row(ROOT/path)["sha256"]==digest
assert not subprocess.check_output(["git","diff","--cached","--name-only"],cwd=ROOT,timeout=10)
subprocess.run(["git","diff","--check","--","PLAN.md","STATUS.md","work-graph.json","gates/ga.json"],cwd=ROOT,check=True,timeout=10)
with DEST.open("x") as f: json.dump({"schema":1,"at":datetime.now(timezone.utc).isoformat(),"delivery":d,"metadata_files":[row(ROOT/n) for n in ["PLAN.md","STATUS.md","work-graph.json","gates/ga.json"]],"packages":18,"gates":38,"GA_verified":0},f,indent=2);f.write("\n")
print(json.dumps({"pushed":r["commit"],"paths":r["committed_paths"],"CI_pending":2,"GA_verified":0}))
