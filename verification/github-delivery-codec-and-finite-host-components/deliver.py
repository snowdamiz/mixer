"""One-shot root delivery of isolated typed codec, finite host components and terminal parent CI evidence."""
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
BASE = "6450104dc3b02d0f4d4e572c6b05ad7fdc6657b2"
PROTECTED = {
 ".github/workflows/hosted.yml": "fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57",
 "hosted/lib/mixer_hosted/browser_auth/store.ex": "8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299",
}
PACKETS = [('android-finite-ledger-controls', 'f90c7fd6240fd8fc63c3c16ac01997e673747d222136271764e1e657ad447a0b', None), ('android-renderer-finite-membership-controls', 'e901741635c6827b0d14b70c51248ea64a5a4071defd0d8a4c58c9fbdb904f93', None), ('android-renderer-finite-membership-independent', 'af43bfee836562f3d8925bb3904d9ea7b4703e96e76ea2db9cfb316380096f92', None), ('android-renderer-finite-ledger-constructor', '43ee31803039e416efa224e8ae67654b27d073035587da11c66a3d6b8adf9fd6', None), ('android-renderer-state-journal-constructor-controls', 'd134612993dd5d2071c55e2f63c2ee93fbaea503f5123e146a839ee89354a279', None), ('android-renderer-state-journal-constructor-independent', 'f2944a1ebbe2969e290efd65a09f70d1a98b9b1df6da0acb5c287773fc0da733', None), ('android-field-preservation-replacement-finite-controls', '309dc0fe8b70849fd95df09b673577cbbb74dbeeac02c4aee9b01870306a9626', None), ('android-field-preservation-replacement-independent', 'd1d18c25ecebacecdba20d8c117a36f9dd01a082d14c394f86b8e08874e314a1', None), ('android-renderer-semantic-policy-preparation', '35e5cf5d97652a76829bfd10c967898d1d32d7315104a592ab1a34c26c560c9b', None), ('android-editor-membership-compiled-boundary-qualification/passive-return-probe-v3', '04b282dbe16898d0a417286303c87a587b97da1153a3efaf3b564a895a16d8b7', None), ('android-editor-membership-qualification-independent/derivative-v3-review', 'af7f2152fe4833617787832f936ef09145848221086211ed485d9d0ccc4773ab', None), ('android-editor-membership-compiled-boundary-qualification/passive-return-probe-v4', '8501bfa60dbae4c3d90be181e8d4fe1e858d1f59908328c4c9855fe7bc99eff8', None), ('android-passive-return-probe-v4-independent', '0fe83fe8b99336534145203f735d4c200a34bec0390ed31a870b653f74a4e2af', None), ('android-editor-membership-compiled-boundary-qualification/state-replay-candidate-v2', '997ffefd7eaad9ba8e0f6ddb0aa8654a5cee37304be8f49927874229e3f73a30', None), ('android-editor-membership-qualification-independent/v1-positive-preparation', 'd982305bafe8abcfc6945ea37ca8ff908aa748f00dfcad7e303517b327d74c8f', None), ('android-source-pair5-coherent-integration-preparation', '0dc913d88d4ee7d1e6583bdf00e1e407cc6b446ac7c7aaf6180a36a45b021e9b', None), ('android-source-pair5-coherent-integration-independent', 'dbf74af4bc44cd1ed10228f68bfe59e75f91365aaa803e069385c8d05002dd28', None), ('android-source-pair5-return-v4-overlay-preparation', 'b09db09b88f68ae1b4d92f7aac14c65d5c94983c0ee2c4e6bbe16213776e6d02', None), ('swift-retained-profile-composition-independent', 'ce7f9d15730411060284df6659ed7d5c3278a7f3b543142cd31b8d3dfa2091c1', None), ('swift-retained-profile-composition-correction', '57591c504fadfb0c22e44e37d6333cab53b8d62e39da14e97f0cdfd2fed455f1', None), ('swift-retained-profile-composition-correction-independent', '108faabdd9e9fdb0037f0fd59863a9782073effaea956753d0c76fed7698b6d3', None), ('swift-retained-profile-composition-stdio-correction', '01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2', None), ('swift-retained-profile-composition-stdio-independent', 'af9f20a00000cdbac6f772e19088e0c9ce078530386cb62d41d693954b832040', None), ('swift-retained-profile-stdio-read-boundary-correction', 'c79bd64dc0019c17f03b17df0a6bd5dc8879334d64fbf74f92507d75a5e81f54', None), ('swift-retained-profile-stdio-read-boundary-independent', 'a10b46f06b54e3bd3e940c7cf403cac7f80faed4814347f2c38616ab447006e1', None), ('swift-retained-profile-real-binding-preparation', 'e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01', None), ('swift-retained-profile-real-binding-contract-review', '2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e', None), ('swift-typed-result-codec-implementation', '4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86', None), ('swift-typed-result-codec-independent', '8f22a9842cb609027d6f6cbe808eefb13d56cd52b68ef6cddec9a9926f5fc16b', None), ('github-delivery-source-pair5-component-review/fixture-artifact-audit', '49047410739f2150bfb9ab8132ffefc28ec6427f81622c5d522c69b9edf33a3b', None), ('github-delivery-source-pair5-component-review/terminal-artifact-audit', 'b06bcc3a19dd352916ba6c95a444b2a2e804e5aeb685a1a762dd82dbf2d1c383', None)]

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
selected=set(ROOT/p for p in ("PLAN.md","STATUS.md","work-graph.json","gates/ga.json","verification/swift-retained-profile-composition-root-custody.json","verification/swift-retained-profile-composition-stdio-correction-root-custody.json","verification/swift-retained-profile-composition-stdio-independent-root-custody.json"))
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
 if isinstance(members,dict):members=[{"path":name,**row} for name,row in members.items()]
 for row in members:
  p=PurePosixPath(row["path"])
  assert not p.is_absolute() and ".." not in p.parts and ".git" not in p.parts and str(p)==row["path"] and row["path"] not in names
  names.add(row["path"]);assert identity(folder/row["path"])=={k:row[k] for k in ("bytes","sha256")},row["path"]
 if (folder/"seal.sha256").exists() and "seal.sha256" not in names:
  assert (folder/"seal.sha256").read_bytes()==(expected+"  seal.json\n").encode();extra.add("seal.sha256")
 actual=set()
 for base,dirs,files in os.walk(folder,followlinks=False):
  for item in dirs+files:assert not (Path(base)/item).is_symlink()
  actual.update(str((Path(base)/x).relative_to(folder)) for x in files)
 assert actual==names|extra,(name,actual-(names|extra),(names|extra)-actual)
 selected.update(folder/x for x in actual)
 custody.append({"packet":name,"seal_sha256":expected,"members_verified":len(members),"member_bytes":sum(x["bytes"] for x in members)})
for folder in (ROOT/"verification/android-editor-boundary-root-review",ROOT/"verification/swift-semantic-adapter-root-review",ROOT/"verification/github-delivery-source-pair5-component-review"):
 for path in folder.rglob("*"):
  assert not path.is_symlink(),path
  if path.is_file():selected.add(path)
selected.add(Path(__file__).resolve())
rows=[{"path":str(p.relative_to(ROOT)),**identity(p)} for p in sorted(selected)]
assert all(row["bytes"]<100*1024*1024 for row in rows)
assert all(not row["path"].startswith(("verification/swift-real-profile-loader-binding/","verification/android-editor-subject-typed-join-validator/","verification/android-editor-membership-compiled-boundary-qualification/state-qualification/","verification/android-editor-membership-qualification-independent/execution-closure-v5")) for row in rows)
save("manifest.json",{"schema":1,"base":BASE,"python":platform.python_version(),"members":rows,"member_count":len(rows),"member_bytes":sum(x["bytes"] for x in rows),"packet_custody":custody,"scope":"Root-accepted isolated Swift pure-data codec and finite Android host facets with scoped independent reviews; retained earlier failures and partial replay data are not full qualification; terminal parent CI artifacts; all three active lanes and stopped v5 reviews excluded; canonical product unchanged"})
paths=[x["path"] for x in rows]+[str((OUT/"manifest.json").relative_to(ROOT))]
(OUT/"paths.nul").write_bytes(b"".join(x.encode()+b"\0" for x in paths))
command("stage",["git","add","--force","--pathspec-from-file="+str(OUT/"paths.nul"),"--pathspec-file-nul"])
for row in rows:assert identity(ROOT/row["path"])=={k:row[k] for k in ("bytes","sha256")}
index=command("index-selected",["git","diff","--cached","--name-only","-z"]).decode().split("\0");index=[x for x in index if x]
assert set(index)<=set(paths) and {"PLAN.md","STATUS.md","work-graph.json","gates/ga.json"}<=set(index)
# Immutable evidence/diffs/raw logs are kept byte-for-byte. Whitespace-check authored root metadata and source only.
check=[p for p in index if p in {"PLAN.md","STATUS.md","work-graph.json","gates/ga.json"} or (p.startswith(("verification/android-editor-boundary-root-review/","verification/swift-semantic-adapter-root-review/")) and p.endswith((".py",".md"))) or p==str(Path(__file__).relative_to(ROOT))]
command("authored-index-check",["git","diff","--cached","--check","--",*check])
raw=command("staged-object-map",["git","diff","--cached","--raw","--no-abbrev","-z"]).split(b"\0")
for i in range(0,len(raw)-1,2):
 header=raw[i].decode().split();path=raw[i+1].decode();assert len(header)==5 and header[-1] in ("A","M") and header[1] in ("100644","100755"),(header,path)
 data=(ROOT/path).read_bytes();assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==header[3],path
command("commit",["git","commit","-m","Add isolated Swift result codec and reviewed Android host controls"])
head=command("after-head",["git","rev-parse","HEAD"]).decode().strip();tree=command("tree",["git","rev-parse","HEAD^{tree}"]).decode().strip()
assert command("parent",["git","rev-parse","HEAD^"]).decode().strip()==BASE
actual=command("committed-paths",["git","diff-tree","--no-commit-id","--name-only","-z","-r","HEAD"]).decode().split("\0");assert set(x for x in actual if x)==set(index)
assert not command("index-after",["git","diff","--cached","--name-only"])
command("push",["git","push","origin","HEAD:main"],120)
assert command("remote-after",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==head
for path,sha in PROTECTED.items():assert identity(ROOT/path)["sha256"]==sha
save("receipt.json",{"schema":1,"at":datetime.now(timezone.utc).isoformat(),"commit":head,"tree":tree,"parent":BASE,"manifest_sha256":identity(OUT/"manifest.json")["sha256"],"committed_paths":len(index),"pushed":True,"force":False,"protected_work_unchanged":PROTECTED,"active_authored_lanes_excluded":True,"only_explicitly_released_sealed_subpackets_included":True,"canonical_product_changed":False,"CI_pending":True,"native_OTA_GA_accepted":False})
print(json.dumps({"commit":head,"tree":tree,"paths":len(index),"pushed":True}))
