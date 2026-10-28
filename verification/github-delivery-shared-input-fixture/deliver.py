"""Commit and push only the selected fixture diagnostic and compact evidence."""
import hashlib,json,platform
from owned import Commands,OUT,ROOT,now,row,save
selection=json.loads((OUT/"selection.json").read_bytes());pre=json.loads((OUT/"preflight.json").read_bytes())
assert not (OUT/"delivery-once.json").exists(),"one delivery reservation; no automatic retry"
commands=Commands(240,19,"delivery-")
assert commands.run("branch",["git","branch","--show-current"]).decode().strip()=="main"
assert commands.run("base",["git","rev-parse","HEAD","HEAD^{tree}"]).decode().splitlines()==[selection["base"],selection["baseTree"]]
assert commands.run("remote-before",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==selection["base"]
assert not commands.run("index-before",["git","diff","--cached","--name-only","-z"])
for r in pre["metadataAfter"]:assert row(ROOT/r["path"])==r,r["path"]
for path,h in pre["protectedFilesUnchanged"].items():assert row(ROOT/path)["sha256"]==h,path
selected={ROOT/f for f in ("PLAN.md","STATUS.md","work-graph.json","gates/ga.json",selection["workflow"]["destination"])}
for p in pre["packets"]:
    d=ROOT/p["directory"];assert row(d/"seal.json")==p["seal"]
    seal=json.loads((d/"seal.json").read_bytes())
    for m in seal["members"]:
        f=ROOT/m["path"] if p["membersRepositoryRelative"] else d/m["path"]
        assert all(row(f)[k]==m[k] for k in ("bytes","sha256"));selected.add(f)
    selected.add(d/"seal.json")
owned=["selection.json","fieldlog-app-read-result.json","capacity-run-observation.json","preflight.json","owned.py","prepare.py","deliver.py","dispatch.py","README.md","candidate-verification.json","local-command-custody.json","metadata-integrity.json"]
selected.update(OUT/f for f in owned)
assert row(ROOT/selection["workflow"]["destination"])["sha256"]==selection["workflow"]["sha256"]
assert (ROOT/selection["workflow"]["destination"]).read_bytes()==(ROOT/selection["workflow"]["source"]).read_bytes()
members=[row(p) for p in sorted(selected)];total=sum(r["bytes"] for r in members)
assert len(members)<=100 and total<6*1024*1024,(len(members),total)
assert not any(p["path"] in pre["protectedFilesUnchanged"] or ".wrangler" in p["path"] or "local-command-receipts" in p["path"] for p in members)
g=json.loads((ROOT/"gates/ga.json").read_bytes());assert [sum(x["status"]==s for x in g["gates"]) for s in ("running","planned","verified")]==[8,30,0]
save("manifest.json",{"schema":1,"at":now(),"base":selection["base"],"baseTree":selection["baseTree"],"members":members,"selectedBytesExcludingManifest":total,"packetSizeCapBytes":6*1024*1024,"selection":row(OUT/"selection.json"),"candidateVerification":row(OUT/"candidate-verification.json"),"requiredTrackedSparseMembers":pre["requiredTrackedSparseMembers"],"sourceReviewAllFourMembersPlusSealIncluded":True,"frozenPackDuplicationIncluded":False,"rawCIOrInvestigationIncluded":False,"otherOwnersAndProtectedFilesIncluded":False,"localCompilerRuntimeNativeUICaptureOrHeldProbesStarted":False,"python":platform.python_version(),"runtimeReleaseOrGAAccepted":False})
paths=[r["path"] for r in members]+[str((OUT/"manifest.json").relative_to(ROOT))]
assert total+(OUT/"manifest.json").stat().st_size<6*1024*1024
with (OUT/"paths.nul").open("xb") as f:f.write(b"".join(p.encode()+b"\0" for p in paths))
save("delivery-once.json",{"at":now(),"base":selection["base"],"manifest":row(OUT/"manifest.json"),"oneNonforcePushAuthorized":True,"retrySelected":False})
commands.run("stage",["git","add","--force","--pathspec-from-file="+str(OUT/"paths.nul"),"--pathspec-file-nul"])
for r in members:assert row(ROOT/r["path"])==r,r["path"]
index=set(filter(None,commands.run("index-selected",["git","diff","--cached","--name-only","-z"]).decode().split("\0")))
assert index==set(paths),(index-set(paths),set(paths)-index)
commands.run("authored-check",["git","diff","--cached","--check","--",selection["workflow"]["destination"],"PLAN.md","STATUS.md","work-graph.json","gates/ga.json",*[str((OUT/f).relative_to(ROOT)) for f in owned]])
raw=commands.run("staged-objects",["git","diff","--cached","--raw","--no-abbrev","-z"]).split(b"\0");assert len(raw)%2==1
for i in range(0,len(raw)-1,2):
    h=raw[i].decode().split();path=raw[i+1].decode();assert len(h)==5 and h[-1] in ("A","M") and h[1] in ("100644","100755") and path in paths
    b=(ROOT/path).read_bytes();assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==h[3],path
commands.run("commit",["git","-c","core.hooksPath=/dev/null","-c","commit.gpgsign=false","commit","-m","Select shared-input cache fixture diagnostic"])
head,tree=commands.run("committed-head",["git","rev-parse","HEAD","HEAD^{tree}"]).decode().splitlines()
committed=set(filter(None,commands.run("committed-paths",["git","diff-tree","--no-commit-id","--name-only","-r","-z","HEAD"]).decode().split("\0")));assert committed==set(paths)
assert commands.run("remote-prepush",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==selection["base"]
commands.run("push",["git","push","origin","HEAD:refs/heads/main"],seconds=45)
assert commands.run("remote-postpush",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==head
assert not commands.run("index-after",["git","diff","--cached","--name-only","-z"])
for path,h in pre["protectedFilesUnchanged"].items():assert row(ROOT/path)["sha256"]==h
save("receipt.json",{"schema":1,"at":now(),"commit":head,"tree":tree,"base":selection["base"],"pushed":True,"force":False,"manifest":row(OUT/"manifest.json"),"selectedMembersIncludingManifest":len(paths),"selectedBytesIncludingManifest":total+(OUT/"manifest.json").stat().st_size,"workflow":row(ROOT/selection["workflow"]["destination"]),"allCommands":commands.records,"allNewCommandsReapedGroupsAbsentAndEOF":True,"protectedFilesPreserved":True,"wranglerUntouched":True,"noLocalCompilerRuntimeNativeUICaptureOrHeldProbe":True,"dispatchPending":True,"runtimeReleaseOrGAAccepted":False})
print(json.dumps({"head":head,"tree":tree,"pushed":True,"force":False,"selectedFiles":len(paths),"selectedBytes":total+(OUT/"manifest.json").stat().st_size,"ownedCommands":len(commands.records)}))
