#!/usr/bin/env python3
import datetime,hashlib,json,stat,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
DOCS=["hosted-worker-pending-registry-schema-guard", "hosted-worker-pending-registry-corrections-review", "hosted-worker-pending-registry-components-integration", "hosted-worker-pending-registry-engine", "hosted-worker-pending-registry-engine-review", "swift-cache-work-attribution", "swift-cache-work-attribution-result", "swift-cache-resident-index-contract"]
DIRS=["hosted-worker-pending-registry-schema-guard", "hosted-worker-pending-registry-corrections-review", "hosted-worker-pending-registry-components-root-integration", "hosted-worker-pending-registry-engine", "hosted-worker-pending-registry-engine-review", "swift-cache-work-attribution", "swift-cache-work-attribution-root-selection", "swift-cache-resident-index-root-selection", "github-delivery-29b33e40"]
LIVE=["build.mjs", "src/pending-audit.ts", "src/pending-registry.ts", "src/pending-types.ts", "src/public-contract.ts", "src/registry-schema.sql"]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (OUT/n).write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def run(n,argv):
 r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
 (OUT/(n+".stdout")).write_bytes(r.stdout);(OUT/(n+".stderr")).write_bytes(r.stderr)
 row={"argv":argv,"exitCode":r.returncode,"stdoutSHA256":sha(OUT/(n+".stdout")),"stderrSHA256":sha(OUT/(n+".stderr"))}
 assert r.returncode==0,row
 return row
assert subprocess.check_output(["git","diff","--cached","--name-only"],cwd=ROOT)==b""
commands=[run("attribution-verify",["python3","-B","verification/swift-cache-work-attribution-root-selection/verify_result.py"]),run("component-review-verify",["node","verification/hosted-worker-pending-registry-corrections-review/verify-packet.mjs"])]
a=json.loads((ROOT/"verification/hosted-worker-pending-registry-components-root-integration/acceptance.json").read_text())
for n,h in a["sourceManifest"].items():assert sha(ROOT/n)==h,n
assert sha(ROOT/"hosted-worker-controller/build.mjs")==a["buildScriptSHA256"]
assert a["liveControllerGroupsPassed"]==71 and a["identityControlsPassed"]==20
assert not a["operationEngineIntegration"] and not a["scheduledEntryIntegration"]
gates=json.loads((ROOT/"gates/ga.json").read_text())["gates"]
assert [v["id"] for v in gates]==[f"G{i:02}" for i in range(1,39)]
assert all(v["evidence"] and v["reviewer"] for v in gates if v["status"]=="passed")
assert [v["id"] for v in json.loads((ROOT/"work-graph.json").read_text())["packages"]]==[f"W{i:02}" for i in range(1,19)]
assert [v["id"] for v in json.loads((ROOT/"dogfood/receipts/milestones.json").read_text())["milestones"]]==[f"D{i}" for i in range(9)]
files=[ROOT/n for n in ["PLAN.md","STATUS.md","gates/ga.json","work-graph.json"]]+[ROOT/"docs"/(n+".md") for n in DOCS]+[ROOT/"hosted-worker-controller"/n for n in LIVE]
for d in DIRS:
 for p in sorted((ROOT/"verification"/d).rglob("*")):
  assert not p.is_symlink(),p
  if p.is_file():files.append(p)
for p in files:
 assert p.is_file() and stat.S_ISREG(p.lstat().st_mode) and p.lstat().st_nlink==1,p
 assert p.stat().st_size<50000000,p
 assert not {"node_modules","owned-build","owned-source","owned-review","target","tmp"}.intersection(p.relative_to(ROOT).parts),p
save("verification.json",{"schema":1,"observedUTC":datetime.datetime.now(datetime.timezone.utc).isoformat(),"parentRevision":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"commands":commands,"componentSourceBindings":len(a["sourceManifest"]),"liveGroups":71,"identityControls":20,"scope":"Exact completed registry/audit component integration and retained cache attribution; active engine correction, resident-index implementation and native runtime lanes excluded.","gaAccepted":False})
files.extend(OUT.iterdir())
names=sorted({str(p.relative_to(ROOT)) for p in files}|{str(OUT.relative_to(ROOT)/"selected-files.json")})
save("selected-files.json",names)
save("selected-source-hashes.json",{n:sha(ROOT/n) for n in names})
names.append(str(OUT.relative_to(ROOT)/"selected-source-hashes.json"));names.sort();save("selected-files.json",names)
# The list changes once to include its hash record; its own hash is deliberately excluded.
hashes={n:sha(ROOT/n) for n in names if n not in {str(OUT.relative_to(ROOT)/"selected-files.json"),str(OUT.relative_to(ROOT)/"selected-source-hashes.json")}}
save("selected-source-hashes.json",hashes)
print(json.dumps({"selected":len(names),"bytes":sum((ROOT/n).stat().st_size for n in names),"sourceHashes":len(hashes)}))
