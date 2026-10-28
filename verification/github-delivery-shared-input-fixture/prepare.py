"""Prepare exact selected source delivery; no compiler or runtime execution."""
import hashlib,json,platform
from owned import Commands,OUT,ROOT,now,row,save
selection=json.loads((OUT/"selection.json").read_bytes())
commands=Commands(120,8,"preflight-")
assert commands.run("branch",["git","branch","--show-current"]).decode().strip()=="main"
assert commands.run("head",["git","rev-parse","HEAD"]).decode().strip()==selection["base"]
assert commands.run("tree",["git","rev-parse","HEAD^{tree}"]).decode().strip()==selection["baseTree"]
assert not commands.run("index-empty",["git","diff","--cached","--name-only","-z"])
assert commands.run("remote",["git","ls-remote","origin","refs/heads/main"]).decode().split()[0]==selection["base"]
raw=commands.run("sparse-index",["git","ls-files","--stage","-z","--","verification/swift-cache-state-ci"])
index={}
for record in filter(None,raw.split(b"\0")):
    h,path=record.split(b"\t",1);mode,oid,stage=h.decode().split();assert stage=="0"
    index[path.decode()]={"mode":mode,"oid":oid}
manifest=json.loads((ROOT/"verification/swift-cache-state-ci/pack/manifest.json").read_bytes())
required=["verification/swift-cache-state-ci/pack/"+m["path"] for m in manifest["members"]]+["verification/swift-cache-state-ci/pack/manifest.json","verification/swift-cache-state-ci/check_cache_state.py","verification/swift-cache-state-ci/test_runner.py"]
closure=[]
for path in sorted(required):
    p=ROOT/path;b=p.read_bytes();assert not p.is_symlink()
    oid=hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    assert path in index and index[path]["oid"]==oid and index[path]["mode"] in ("100644","100755"),path
    closure.append({**row(p),"indexOID":oid})
assert not commands.run("frozen-diff",["git","diff","--name-only","--","verification/swift-cache-state-ci"])
packets=[]
for directory,expected,absolute in [("verification/cache-fixture-shared-input-candidate",selection["candidateSealSHA256"],False),("verification/cache-fixture-shared-input-review",selection["sourceReviewSealSHA256"],True),("verification/cache-fixture-overlay-independent",selection["integrationReviewSealSHA256"],False)]:
    d=ROOT/directory;seal=json.loads((d/"seal.json").read_bytes());assert row(d/"seal.json")["sha256"]==expected
    assert len(seal["members"])==seal["member_count"]
    for member in seal["members"]:
        p=ROOT/member["path"] if absolute else d/member["path"];r=row(p)
        assert all(r[k]==member[k] for k in ("bytes","sha256")),str(p)
    packets.append({"directory":directory,"seal":row(d/"seal.json"),"memberCount":seal["member_count"],"treeSHA256":seal["tree_sha256"],"membersRepositoryRelative":absolute})
protected={".github/workflows/hosted.yml":"fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57","hosted/lib/mixer_hosted/browser_auth/store.ex":"8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299"}
for path,h in protected.items():assert row(ROOT/path)["sha256"]==h,path
assert row(ROOT/selection["workflow"]["destination"])["sha256"]==selection["workflow"]["sha256"]
assert row(OUT/"fieldlog-app-read-result.json")["sha256"]=="592dac0ce16438888130c38126174ba0d89454a8ae60276fde4a2c6525759890"
capacity=json.loads((OUT/"local-command-receipts/007-capacity-run.stdout").read_bytes())
assert capacity["head_sha"]==selection["base"] and capacity["run_attempt"]==1
save("capacity-run-observation.json",{"schema":1,"observedAt":now(),**capacity,"scope":"Read-only status; result not reviewed or accepted"})
fixture={"schema":1,"at":now(),"status":"root-selected-source; exact workflow installed; one manual dispatch selected; complete fixture and compiler availability pending","selection":row(OUT/"selection.json"),"candidateSeal":packets[0]["seal"],"candidateTreeSHA256":selection["candidateTreeSHA256"],"sourceReviewSeal":packets[1]["seal"],"sourceReviewTreeSHA256":selection["sourceReviewTreeSHA256"],"integrationReviewSeal":packets[2]["seal"],"workflow":row(ROOT/selection["workflow"]["destination"]),"dispatchLimit":1,"bounds":selection["bounds"],"offlineEvidence":selection["verification"],"completeRemoteRunnerControlsRequired":36,"remoteRealChildOrSignalControlsUnrun":8,"borrowedUnchangedFrozenMembers":83,"materializedPackMembers":86,"originalVectors":1003,"originalAssertionsAndFreshArenasUnchanged":True,"ordinaryFixtureCIRegressed":False,"speedupAccepted":False,"compilerFallbackRetryOrDefaultPromotionSelected":False,"runtimeNativeReleaseOrGAAccepted":False,"holdsUnchanged":True}
fl=json.loads((OUT/"fieldlog-app-read-result.json").read_bytes())
fieldlog={"summary":row(OUT/"fieldlog-app-read-result.json"),"commit":fl["appRevision"],"tree":fl["appTree"],"run":fl["runID"],"status":"public exact 73-blob hydration passed; requested app read admitted; Executor process-group inheritance guard rejected before inner Git child","testsStartedObserved":0,"authoredTests":38,"recordedOuterGroupsClosed":12,"recordedAcquisitionChildrenClosed":29,"rejectedAdapterActualPGIDRecorded":False,"unrecordedDetachedDescendantAbsenceProven":False,"initialLocalReadsWithoutSeparateGroupReceipts":8,"next":"Fresh Astra ownership candidate under preparation; no further FieldLog run selected","nativeDogfoodOrGA":False}
metadata_before=[row(ROOT/f) for f in ("PLAN.md","STATUS.md","work-graph.json","gates/ga.json")]
section="""## Selected shared-input fixture diagnostic

Root selects the exact independently reviewed shared-input fixture harness for one
manual diagnostic. The thin overlay borrows 83 unchanged frozen members into the
complete 86-member pack. It preserves all 1,003 original vectors, assertions and
fresh arenas. Offline evidence passes 28 runner controls, nine materializer groups
and six additional independent integration controls; eight real-child/signal
controls remain unrun locally. Remote CI must pass all 36 runner controls before
one complete 103-command fixture, with 60 seconds per child, 600 active seconds
and 60 cleanup seconds on exact Rust `1.98.1-aarch64-apple-darwin`. Compiler
unavailability is a failure; no retry, compiler fallback or default-pack promotion
is selected. [Selection and immutable seals](verification/github-delivery-shared-input-fixture/selection.json)
bind the source-only acceptance. Current ordinary fixture CI is green; no
regression or speedup is claimed. Actual compiler availability and fixture results
remain pending.

The separate capacity-window run [40788458735](https://github.com/snowdamiz/mixer/actions/runs/40788458735)
at exact Mixer `e5670519` remains in progress at the latest read-only observation.
Its limits and spent prior campaigns remain unchanged.

FieldLog public `496399f8` run [40788707965](https://github.com/snowdamiz/fieldlog/actions/runs/40788707965)
passes exact public 73-blob hydration and the requested app-read allowlist, then
fails the Executor process-group inheritance guard before the inner Git child.
SwiftPM resolve fails; build and all 38 tests are unreached. Cleanup evidence
covers 12 recorded outer groups and 29 acquisition children. The rejected
adapter's actual process group was not recorded, so absence of unrecorded detached
descendants is unproven; eight initial local bounded reads had no separate group
custody receipt. A fresh Astra ownership candidate is under preparation; no
further FieldLog run is selected. The [small latest result](verification/github-delivery-shared-input-fixture/fieldlog-app-read-result.json)
preserves these limitations. Gates stay **8 running, 30 planned, 0 verified**;
all native/UI/capture, phone, local compiler/custody, Unit A and broad hosted
holds remain.

"""
for f in ("PLAN.md","STATUS.md"):
    p=ROOT/f;text=p.read_text();start=text.index("## Selected capacity and observation window");end=text.index("## Closed public host campaigns",start);p.write_text(text[:start]+section+text[end:])
w=json.loads((ROOT/"work-graph.json").read_bytes());g=json.loads((ROOT/"gates/ga.json").read_bytes());w["updated"]=now()
for doc in (w,g):
    doc["executionPolicy"]["currentSharedInputFixtureSelection"]={"selection":row(OUT/"selection.json"),"sourceOnlyAccepted":True,"runtimeProductionOrGAAccepted":False,"fieldlogLatest":row(OUT/"fieldlog-app-read-result.json")}
    doc["executionPolicy"]["currentCapacityWindowSelection"]["latestRunObservation"]=row(OUT/"capacity-run-observation.json")
for item in (w["packages"][7],g["gates"][1]):
    item["sharedInputFixtureDiagnostic"]=fixture
    item["empiricalCacheDeadlineCampaign"]["architecture_comparison"]["capacity_window_v1"]["latestRunObservation"]=row(OUT/"capacity-run-observation.json")
    for path in (str((OUT/"selection.json").relative_to(ROOT)),*[(p["directory"]+"/seal.json") for p in packets]):
        if path not in item["evidence"]:item["evidence"].append(path)
for item in (w["packages"][16],g["gates"][25],g["gates"][26]):
    item["fieldlogAppReadResult"]=fieldlog
    if fieldlog["summary"]["path"] not in item["evidence"]:item["evidence"].append(fieldlog["summary"]["path"])
assert [sum(x["status"]==s for x in g["gates"]) for s in ("running","planned","verified")]==[8,30,0]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"]==g["gates"][1]["empiricalCacheDeadlineCampaign"]
for f,doc in (("work-graph.json",w),("gates/ga.json",g)):(ROOT/f).write_text(json.dumps(doc,indent=2,ensure_ascii=True)+"\n")
save("preflight.json",{"schema":1,"at":now(),"base":selection["base"],"baseTree":selection["baseTree"],"packets":packets,"requiredTrackedSparseClosure":closure,"requiredTrackedSparseMembers":len(closure),"trackedSparseDirectoryMembers":len(index),"sourceReviewAllFourMembersAndSealIncluded":True,"noFrozenBaseDiff":True,"protectedFilesUnchanged":protected,"wranglerUntouched":True,"metadataBefore":metadata_before,"metadataAfter":[row(ROOT/f) for f in ("PLAN.md","STATUS.md","work-graph.json","gates/ga.json")],"commands":commands.records,"allCommandsReapedGroupsAbsentAndEOF":True,"python":platform.python_version(),"gitVersion":"2.56.0","ghVersion":"2.102.0","localCompilerRuntimeNativeUICaptureOrHeldProbesStarted":False})
print(json.dumps({"packets":len(packets),"trackedSparseRequired":len(closure),"trackedSparseAvailable":len(index),"metadataUpdated":4,"gateCounts":[8,30,0],"ownedGitCommands":len(commands.records)}))
