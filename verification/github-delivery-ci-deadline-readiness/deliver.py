"""One-shot root delivery of the independently reviewed test-only cleanup deadline readiness repair."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import stat
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "dee2d199dfbd6396153e1bb951e809b0ee0f8e86"
PROTECTED = {
 ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
 "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
PACKETS = [('swift-cache-state-ci-deadline-readiness', '6e9f2ea669c9653e9ac5829243d95d5cf7216a922bd5672524dfcb8ed5b94849', None, 'seal.json'), ('swift-cache-state-ci-deadline-readiness-independent', '95538d31b8d3d88310cd9eb5271a1a549efd3cdf7407ad4b735f3d7fcf71ce40', None, 'packet-files.json')]
assert len(PACKETS) == 2, "Both frozen reviewed test packets are required"
RELEASED = {"verification/swift-cache-state-ci/test_runner.py": "c754ea8c8cb40d0090c676de61263939e6e58b140f9902e97901126a4287e9ab"}


def identity(path):
 assert stat.S_ISREG(path.lstat().st_mode), path
 data=path.read_bytes()
 return {"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}

def save(name,data):
 with (OUT/name).open("x") as stream:
  json.dump(data,stream,indent=2);stream.write("\n")

def command(name,argv,timeout=60):
 start=time.monotonic()
 with (OUT/(name+".stdout")).open("xb") as stdout,(OUT/(name+".stderr")).open("xb") as stderr:
  result=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=timeout)
 save(name+".command.json",{"argv":argv,"exit":result.returncode,"elapsed_seconds":time.monotonic()-start,"finished":datetime.now(timezone.utc).isoformat(),"stdout":identity(OUT/(name+".stdout")),"stderr":identity(OUT/(name+".stderr"))})
 result.check_returncode()
 return (OUT/(name+".stdout")).read_bytes()

assert __debug__ and not (OUT/"manifest.json").exists(),"One-shot; do not replay"
assert command("branch",["git","branch","--show-current"]).decode().strip()=="main"
assert command("head",["git","rev-parse","HEAD"]).decode().strip()==BASE
assert command("remote",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==BASE
assert not command("index-before",["git","diff","--cached","--name-only"])
for path,sha in PROTECTED.items():assert identity(ROOT/path)["sha256"]==sha
w=json.loads((ROOT/"work-graph.json").read_bytes());g=json.loads((ROOT/"gates/ga.json").read_bytes())
assert len(w["packages"])==18 and len(g["gates"])==38
assert sum(x["status"]=="running" for x in g["gates"])==8 and sum(x["status"]=="planned" for x in g["gates"])==30
assert w["packages"][4]["privateOwnerEffectContractCandidate"]==g["gates"][4]["privateOwnerEffectContractCandidate"]
assert w["packages"][7]["fixtureCacheStateContractCandidate"]==g["gates"][1]["fixtureCacheStateContractCandidate"]
selected=set(ROOT/p for p in ("PLAN.md","STATUS.md","THIRD_PARTY.yml","work-graph.json","gates/ga.json"))
custody=[]
for name,expected,manifest_name,seal_name in PACKETS:
 folder=ROOT/"verification"/name
 assert identity(folder/seal_name)["sha256"]==expected,name
 seal=json.loads((folder/seal_name).read_bytes());extra={seal_name}
 if manifest_name:
  assert identity(folder/manifest_name)==seal["manifest"]
  manifest=json.loads((folder/manifest_name).read_bytes());extra.add(manifest_name)
 else:manifest=seal
 members=manifest["members"];names=set()
 if isinstance(members,dict):members=[{"path":name,**row} for name,row in members.items()]
 for row in members:
  p=PurePosixPath(row["path"])
  assert not p.is_absolute() and ".." not in p.parts and ".git" not in p.parts and str(p)==row["path"] and row["path"] not in names
  names.add(row["path"]);assert identity(folder/row["path"])=={k:row[k] for k in ("bytes","sha256")},row["path"]
 if (folder/"seal.sha256").exists() and "seal.sha256" not in names:
  assert (folder/"seal.sha256").read_bytes()==(expected+"  "+seal_name+"\n").encode();extra.add("seal.sha256")
 actual=set()
 for base,dirs,files in os.walk(folder,followlinks=False):
  for item in dirs+files:assert not (Path(base)/item).is_symlink()
  actual.update(str((Path(base)/x).relative_to(folder)) for x in files)
 assert actual==names|extra,(name,actual-(names|extra),(names|extra)-actual)
 selected.update(folder/x for x in actual)
 custody.append({"packet":name,"seal_sha256":expected,"members_verified":len(members),"member_bytes":sum(x["bytes"] for x in members)})
for folder in (ROOT/"verification/android-editor-boundary-root-review",ROOT/"verification/swift-semantic-adapter-root-review"):
 for path in folder.rglob("*"):
  assert not path.is_symlink(),path
  if path.is_file():selected.add(path)
for rel,sha in RELEASED.items():
 assert identity(ROOT/rel)["sha256"]==sha
 selected.add(ROOT/rel)
previous=ROOT/"verification/github-delivery-android-observation-consistency"
for path in previous.iterdir():
 assert not path.is_symlink()
 if path.is_file():selected.add(path)
selected.add(Path(__file__).resolve())
selected.add(OUT/"preparation.json")
selected.add(OUT/"metadata-validation.json")
selected.add(OUT/"root-acceptance.json")
rows=[{"path":str(p.relative_to(ROOT)),**identity(p)} for p in sorted(selected)]
assert all(row["bytes"]<100*1024*1024 for row in rows)
assert all(not row["path"].startswith(("verification/swift-selected-profile-adoption/","verification/android-editor-membership-compiled-boundary-qualification/full-candidate-v1/","verification/android-editor-membership-compiled-boundary-qualification/state-qualification/","verification/android-editor-membership-qualification-independent/execution-closure-v5", "verification/android-editor-generic-descriptor-joins/", "verification/android-generic-descriptor-join-independent/", "verification/android-editor-generic-descriptor-correction/", "verification/swift-selected-profile-adoption-control-correction/", "verification/swift-selected-profile-adoption-control-correction-independent/")) for row in rows)
save("manifest.json",{"schema":1,"base":BASE,"python":platform.python_version(),"members":rows,"member_count":len(rows),"member_bytes":sum(x["bytes"] for x in rows),"packet_custody":custody,"scope":"Root-accepted test-only stage readiness repair for the closed fixture cleanup deadline controls, original failed CI logs/artifact and independent negative controls. The production runner, fixed limits, closed Rust pack and canonical engine are unchanged. Active Swift adoption/Android descriptor corrections remain excluded. Native and GA evidence unchanged."})
paths=[x["path"] for x in rows]+[str((OUT/"manifest.json").relative_to(ROOT))]
(OUT/"paths.nul").write_bytes(b"".join(x.encode()+b"\0" for x in paths))
command("stage",["git","add","--force","--pathspec-from-file="+str(OUT/"paths.nul"),"--pathspec-file-nul"])
for row in rows:assert identity(ROOT/row["path"])=={k:row[k] for k in ("bytes","sha256")}
index=command("index-selected",["git","diff","--cached","--name-only","-z"]).decode().split("\0");index=[x for x in index if x]
assert set(index)<=set(paths) and {"PLAN.md","STATUS.md","work-graph.json","gates/ga.json","verification/swift-cache-state-ci/test_runner.py"}<=set(index)
# Immutable evidence/diffs/raw logs are kept byte-for-byte. Whitespace-check authored root metadata and source only.
check=[p for p in index if p in {"PLAN.md","STATUS.md","THIRD_PARTY.yml","work-graph.json","gates/ga.json"} or (p.startswith(("verification/android-editor-boundary-root-review/","verification/swift-semantic-adapter-root-review/")) and p.endswith((".py",".md"))) or p==str(Path(__file__).relative_to(ROOT)) or p=="verification/swift-cache-state-ci/test_runner.py"]
command("authored-index-check",["git","diff","--cached","--check","--",*check])
raw=command("staged-object-map",["git","diff","--cached","--raw","--no-abbrev","-z"]).split(b"\0")
for i in range(0,len(raw)-1,2):
 header=raw[i].decode().split();path=raw[i+1].decode();assert len(header)==5 and header[-1] in ("A","M") and header[1] in ("100644","100755"),(header,path)
 data=(ROOT/path).read_bytes();assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==header[3],path
command("commit",["git","commit","-m","Make cleanup deadline controls wait for the tested stage"])
head=command("after-head",["git","rev-parse","HEAD"]).decode().strip();tree=command("tree",["git","rev-parse","HEAD^{tree}"]).decode().strip()
assert command("parent",["git","rev-parse","HEAD^"]).decode().strip()==BASE
actual=command("committed-paths",["git","diff-tree","--no-commit-id","--name-only","-z","-r","HEAD"]).decode().split("\0");assert set(x for x in actual if x)==set(index)
assert not command("index-after",["git","diff","--cached","--name-only"])
command("push",["git","push","origin","HEAD:main"],300)
assert command("remote-after",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==head
for path,sha in PROTECTED.items():assert identity(ROOT/path)["sha256"]==sha
save("receipt.json",{"schema":1,"at":datetime.now(timezone.utc).isoformat(),"commit":head,"tree":tree,"parent":BASE,"manifest_sha256":identity(OUT/"manifest.json")["sha256"],"committed_paths":len(index),"pushed":True,"force":False,"protected_work_unchanged":PROTECTED,"active_authored_lanes_excluded":True,"only_explicitly_released_sealed_subpackets_included":True,"canonical_product_changed":False,"CI_pending":True,"native_OTA_GA_accepted":False})
print(json.dumps({"commit":head,"tree":tree,"paths":len(index),"pushed":True}))
