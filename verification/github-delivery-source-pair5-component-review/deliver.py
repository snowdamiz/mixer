"""One-shot root delivery of frozen component reviews and terminal parent CI evidence."""
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
BASE = "a9ea84aa33320cadaed2340fe637324b694a917f"
PROTECTED = {
 ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
 "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
PACKETS = [
 ("android-editor-source-pair5-cli-integration", "87cd2e4e14d0c444d308397dbd59dbe271419261f5d7fa2cd7201af35db18ecf", None),
 ("android-editor-source-pair5-cli-independent", "de7b4d9784e0a5bb61cdf093053f91fc8681a72e83daec5187399eac3c89c143", None),
 ("android-editor-source-pair5-host-integration", "c356544da794b1ae630ec2bb4522f8a9ed93fe1aedb9958676dc84f27188733a", "manifest.json"),
 ("android-editor-source-pair5-host-independent", "f8d209d489e1d56001830e0ddb0e1a065a1c3fc9e7fb5c7e4b9378261f600fc3", "manifest.json"),
 ("android-editor-membership-compiled-boundary-qualification/interface-v2", "cf0b1ffc29297ed5d0a26f6c59c2aaf7cc9c929ebfb308ef22d9d4f28d05e3cd", None),
 ("android-editor-membership-compiled-boundary-qualification/interface-v3", "2941189d35873edceff76e2f4b7ff3bf960632d19a869a5e9faf54e4df7a671f", None),
 ("android-editor-membership-compiled-boundary-qualification/passive-return-probe", "5cdecf5c61bdfe4f5c8f1a071ade202396b509a12577c3f8600c99fa3afb1fc4", None),
 ("android-editor-membership-compiled-boundary-qualification/passive-return-probe-v2", "6f0f76afa6b7ba4ff4bb80552d69db16ecdc9eb9e210dfb24a43fe62e06c05e1", None),
 ("android-editor-membership-compiled-boundary-qualification/passive-return-probe-v2-provenance-addendum", "ee2e8ec503f2ba4ef00470ce39513f33b60e4ac4cee9237f5982ba0594d4e5c5", None),
 ("android-editor-membership-compiled-boundary-qualification/semantic-review-candidate-v1", "361412b6ee2124ace685a2242390ece375d0327b119876b13db27dc95ea3f5e6", None),
 ("android-editor-membership-qualification-independent/execution-scaffolding-finding", "a2f1867b7f25f9dbd5c72fbc1a1560d60ff2b03a304d6df04c5bd00608016422", None),
 ("android-editor-membership-qualification-independent/preaccess", "05a01a2cbc130c9730e9a126102abbdd18245b88f9aa2e5627512b338d76f0d6", None),
 ("android-editor-membership-qualification-independent/derivative-review", "66be37223cd48a57d1fc327c2c25c1c76ef153eb876a90dc97c4a8daa0484ddd", None),
 ("android-editor-membership-qualification-independent/semantic-review", "811afc2e3625cf8070aeae7888cefb159196b8c17ce33ad78be82881c6f2852d", None),
 ("swift-retained-profile-composition-preparation", "c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860", None),
]

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
selected=set(ROOT/p for p in ("PLAN.md","STATUS.md","work-graph.json","gates/ga.json","verification/swift-retained-profile-composition-root-custody.json"))
custody=[]
for name,expected,manifest_name in PACKETS:
 folder=ROOT/"verification"/name
 assert identity(folder/"seal.json")["sha256"]==expected,name
 seal=json.loads((folder/"seal.json").read_bytes());extra={"seal.json"}
 if manifest_name:
  assert identity(folder/manifest_name)==seal["manifest"]
  manifest=json.loads((folder/manifest_name).read_bytes());extra.add(manifest_name)
 else:manifest=seal
 members=manifest["members"];names=set()
 for row in members:
  p=PurePosixPath(row["path"])
  assert not p.is_absolute() and ".." not in p.parts and ".git" not in p.parts and str(p)==row["path"] and row["path"] not in names
  names.add(row["path"]);assert identity(folder/row["path"])=={k:row[k] for k in ("bytes","sha256")},row["path"]
 if name=="swift-retained-profile-composition-preparation":
  assert (folder/"seal.sha256").read_bytes()==(expected+"  seal.json\n").encode();extra.add("seal.sha256")
 actual=set()
 for base,dirs,files in os.walk(folder,followlinks=False):
  for item in dirs+files:assert not (Path(base)/item).is_symlink()
  actual.update(str((Path(base)/x).relative_to(folder)) for x in files)
 assert actual==names|extra,(name,actual-(names|extra),(names|extra)-actual)
 selected.update(folder/x for x in actual)
 custody.append({"packet":name,"seal_sha256":expected,"members_verified":len(members),"member_bytes":sum(x["bytes"] for x in members)})
for folder in (ROOT/"verification/android-editor-boundary-root-review",ROOT/"verification/github-delivery-ci-framing-readiness-repair"):
 for path in folder.rglob("*"):
  assert not path.is_symlink(),path
  if path.is_file():selected.add(path)
selected.add(Path(__file__).resolve())
rows=[{"path":str(p.relative_to(ROOT)),**identity(p)} for p in sorted(selected)]
assert all(row["bytes"]<100*1024*1024 for row in rows)
assert all(not row["path"].startswith("verification/swift-retained-profile-composition-independent/") for row in rows)
save("manifest.json",{"schema":1,"base":BASE,"python":platform.python_version(),"members":rows,"member_count":len(rows),"member_bytes":sum(x["bytes"] for x in rows),"packet_custody":custody,"scope":"Frozen isolated CLI/host components, bounded passive probe selection and unaccepted review proposals; terminal parent CI artifacts; active authored matrix and Swift independent review excluded; no canonical product changes"})
paths=[x["path"] for x in rows]+[str((OUT/"manifest.json").relative_to(ROOT))]
(OUT/"paths.nul").write_bytes(b"".join(x.encode()+b"\0" for x in paths))
command("stage",["git","add","--force","--pathspec-from-file="+str(OUT/"paths.nul"),"--pathspec-file-nul"])
for row in rows:assert identity(ROOT/row["path"])=={k:row[k] for k in ("bytes","sha256")}
index=command("index-selected",["git","diff","--cached","--name-only","-z"]).decode().split("\0");index=[x for x in index if x]
assert set(index)<=set(paths) and {"PLAN.md","STATUS.md","work-graph.json","gates/ga.json"}<=set(index)
# Immutable evidence/diffs/raw logs are kept byte-for-byte. Whitespace-check authored root metadata and source only.
check=[p for p in index if p in {"PLAN.md","STATUS.md","work-graph.json","gates/ga.json"} or (p.startswith("verification/android-editor-boundary-root-review/") and p.endswith((".py",".md"))) or p==str(Path(__file__).relative_to(ROOT))]
command("authored-index-check",["git","diff","--cached","--check","--",*check])
raw=command("staged-object-map",["git","diff","--cached","--raw","--no-abbrev","-z"]).split(b"\0")
for i in range(0,len(raw)-1,2):
 header=raw[i].decode().split();path=raw[i+1].decode();assert len(header)==5 and header[-1] in ("A","M") and header[1] in ("100644","100755"),(header,path)
 data=(ROOT/path).read_bytes();assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==header[3],path
command("commit",["git","commit","-m","Record reviewed source-pair5 components and terminal CI evidence"])
head=command("after-head",["git","rev-parse","HEAD"]).decode().strip();tree=command("tree",["git","rev-parse","HEAD^{tree}"]).decode().strip()
assert command("parent",["git","rev-parse","HEAD^"]).decode().strip()==BASE
actual=command("committed-paths",["git","diff-tree","--no-commit-id","--name-only","-z","-r","HEAD"]).decode().split("\0");assert set(x for x in actual if x)==set(index)
assert not command("index-after",["git","diff","--cached","--name-only"])
command("push",["git","push","origin","HEAD:main"],120)
assert command("remote-after",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==head
for path,sha in PROTECTED.items():assert identity(ROOT/path)["sha256"]==sha
save("receipt.json",{"schema":1,"at":datetime.now(timezone.utc).isoformat(),"commit":head,"tree":tree,"parent":BASE,"manifest_sha256":identity(OUT/"manifest.json")["sha256"],"committed_paths":len(index),"pushed":True,"force":False,"protected_work_unchanged":PROTECTED,"active_authored_lanes_excluded":True,"only_explicitly_released_sealed_subpackets_included":True,"canonical_product_changed":False,"CI_pending":True,"native_OTA_GA_accepted":False})
print(json.dumps({"commit":head,"tree":tree,"paths":len(index),"pushed":True}))
