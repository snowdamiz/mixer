"""Record terminal CI and exact remote dispatcher test input without extending product qualification."""
from pathlib import Path
from datetime import datetime,timezone
import copy,hashlib,json
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
DEST=OUT/"terminal-ci.json"
def read(p):return json.loads(p.read_bytes())
def row(p):
 b=p.read_bytes();return {"path":str(p.relative_to(ROOT)),"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
assert not DEST.exists(),"One-shot; do not replay"
r=read(OUT/"receipt.json");assert r["commit"]=="837e7084a0c6e69a88848b484fa3556563c75a59"
engine=read(OUT/"ci-jobs-14.stdout");phoenix=read(OUT/"ci-jobs-13.stdout")
for run in [engine,phoenix]:
 assert run["headSha"]==r["commit"] and run["status"]=="completed" and run["conclusion"]=="success" and run["attempt"]==1
 assert all(j["status"]=="completed" and j["conclusion"]=="success" for j in run["jobs"])
 assert all(s["status"]=="completed" and s["conclusion"]=="success" for j in run["jobs"] for s in j["steps"])
assert len(engine["jobs"])==6 and sum(len(j["steps"]) for j in engine["jobs"])==64
assert len(phoenix["jobs"])==1 and len(phoenix["jobs"][0]["steps"])==13
art=OUT/"phoenix-remote-artifact";rr=read(art/"receipt.json")
assert rr["status"]=="passed" and rr["cleanup"]=={"postgres_stopped":True,"scratch_removed":True}
assert (art/"revision.log").read_text().strip()==r["commit"]
assert rr["inputs"]["hosted/test/mixer_hosted_web/browser_workspace_dispatcher_test.exs"]=="e03227fde20ef946e538c17ed41b4d7d50d7fba88ef737c50e9caceb7c47e3ea"
assert "Result: 683 passed, 2 skipped" in (art/"tests.log").read_text()
for label in ["format","compile","tests"]:
 c=next(c for c in rr["commands"] if c["label"]==label);assert c["exit_code"]==0 and row(art/c["log"])["sha256"]==c["sha256"]
ci={"status":"Engine-and-Phoenix-passed-attempt-one","commit":r["commit"],"engine":{"run":engine["databaseId"],"url":engine["url"],"jobs_passed":6,"steps_passed":64,"workflow_steps_skipped":0,"observation":row(OUT/"ci-jobs-14.stdout")},"phoenix":{"run":phoenix["databaseId"],"url":phoenix["url"],"steps_passed":13,"workflow_steps_skipped":0,"observation":row(OUT/"ci-jobs-13.stdout"),"ordinary_suite_raw_result":"Result: 683 passed, 2 skipped","tests_passed":683,"tests_skipped":2,"format_and_compile_passed":True,"remote_receipt":row(art/"receipt.json"),"remote_tests":row(art/"tests.log"),"runtime":"Elixir1.20.4 OTP29 erts17.1 PostgreSQL16.15 Ubuntu","cleanup":rr["cleanup"]},"scope":"Remote ordinary CI for delivered dispatcher test-only correction; no independent callback acceptance, new lifecycle implementation, layout query, actual-default fixture replay, native/device/provider/operational/GA qualification","GA_accepted":False}
w=read(ROOT/"work-graph.json");g=read(ROOT/"gates/ga.json")
for t in [w["packages"][13],g["gates"][21]]:
 f=t["fixedWorkspaceDispatcher"]
 for key in ["default_authority_candidate","component_test_correction"]:
  d=f[key]["delivery"];assert d["commit"]==r["commit"];d.update({"status":ci["status"],"terminal_CI":copy.deepcopy(ci),"remote_CI_passed":True})
 f["component_test_correction"]["remote_CI_passed"]=True
 f["component_test_correction"]["remote_CI"]=copy.deepcopy(ci)
c=w["packages"][7]["fixtureCacheStateContractCandidate"];assert c==g["gates"][1]["fixtureCacheStateContractCandidate"]
b=c["scalar_cursor_host_acceptance"]["real_profile_adapter_preparation"]["next_header_preparation"]["retained_profile_composition_preparation"]["real_binding_preparation"]["real_profile_loader_binding"]["next_adoption_lane"]["guarded_snapshot_export_contract_review"]["composition_source_preparation"]["bootstrap_host_boundary"]
d=b["actual_owner_Rust_selection"]["correction"]["IR02_source_repair"]["work_storage_delta"]["delivery"];assert d["commit"]==r["commit"];d.update({"status":ci["status"],"terminal_CI":copy.deepcopy(ci),"remote_CI_passed":True})
g["gates"][1]["fixtureCacheStateContractCandidate"]=copy.deepcopy(c)
for name in ["PLAN.md","STATUS.md"]:
 p=ROOT/name;t=p.read_text();old="Engine and Phoenix CI are running.";assert t.count(old)==1
 t=t.replace(old,"Engine passes all six jobs and 64 steps on attempt one; Phoenix passes all thirteen steps, with 683 ordinary tests passing and two existing tests skipped. The exact remote dispatcher test hash matches the corrected source; remote PostgreSQL and scratch cleanup complete.")
 old="The original six setup failures are reproduced; corrected remote CI remains pending.";assert t.count(old)==1
 t=t.replace(old,"The original six setup failures are reproduced; corrected `837e7084` Phoenix CI passes with 683 tests and two existing skips.")
 p.write_text(t)
for name,data in [("work-graph.json",w),("gates/ga.json",g)]: (ROOT/name).write_text(json.dumps(data,indent=2)+"\n")
assert w["packages"][13]["fixedWorkspaceDispatcher"]==g["gates"][21]["fixedWorkspaceDispatcher"]
assert sum(t["status"]=="running" for t in g["gates"])==8 and sum(t["status"]=="planned" for t in g["gates"])==30
for path,digest in r["protected_work_unchanged"].items(): assert row(ROOT/path)["sha256"]==digest
with DEST.open("x") as f:json.dump({"schema":1,"at":datetime.now(timezone.utc).isoformat(),"CI":ci,"metadata_files":[row(ROOT/n) for n in ["PLAN.md","STATUS.md","work-graph.json","gates/ga.json"]],"GA_verified":0},f,indent=2);f.write("\n")
print(json.dumps({"commit":r["commit"],"Engine_jobs":6,"Engine_steps":64,"Phoenix_steps":13,"Phoenix_tests_passed":683,"Phoenix_tests_skipped":2,"GA_verified":0}))
