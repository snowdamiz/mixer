"""Fresh v2 exact-source preflight and compact status reconciliation."""
import copy, hashlib, json, platform, runpy, sys
from owned import Commands, OUT, ROOT, now, row, save
s=json.loads((OUT/'selection.json').read_bytes())
c=Commands(150,10,'preflight-')
versions={k:c.run(k+'-version',[k,'--version']).decode().strip().splitlines()[0] for k in ('git','gh')}
assert c.run('branch',['git','branch','--show-current']).decode().strip()=='main'
assert c.run('head',['git','rev-parse','HEAD','HEAD^{tree}']).decode().splitlines()==[s['base'],s['baseTree']]
assert not c.run('index-empty',['git','diff','--cached','--name-only','-z'])
assert c.run('remote',['git','ls-remote','origin','refs/heads/main']).decode().split()[0]==s['base']
raw=c.run('dependency-index',['git','ls-files','--stage','-z','--','verification/swift-cache-state-ci','verification/cache-fixture-shared-input-review','verification/cache-fixture-shared-input-candidate'])
index={}
for record in filter(None,raw.split(b'\0')):
    h,path=record.split(b'\t',1);mode,oid,stage=h.decode().split();assert stage=='0';index[path.decode()]={'mode':mode,'oid':oid}
required=[]
base=ROOT/'verification/swift-cache-state-ci'
manifest=json.loads((base/'pack/manifest.json').read_bytes())
required.extend(base/'pack'/m['path'] for m in manifest['members'])
required.extend(base/x for x in ('pack/manifest.json','check_cache_state.py','test_runner.py'))
for directory,relative in [('verification/cache-fixture-shared-input-review',True),('verification/cache-fixture-shared-input-candidate',False)]:
    d=ROOT/directory;seal=json.loads((d/'seal.json').read_bytes());required.append(d/'seal.json')
    for m in seal['members']:
        p=ROOT/m['path'] if relative else d/m['path'];r=row(p);assert all(r[k]==m[k] for k in ('bytes','sha256'));required.append(p)
closure=[]
for p in sorted(set(required)):
    r=row(p);b=p.read_bytes();oid=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert r['path'] in index and index[r['path']]['oid']==oid and index[r['path']]['mode'] in ('100644','100755'),r['path']
    closure.append({**r,'indexOID':oid})
assert not c.run('dependencies-diff',['git','diff','--name-only','--','verification/swift-cache-state-ci','verification/cache-fixture-shared-input-review','verification/cache-fixture-shared-input-candidate'])
d=ROOT/'verification/cache-fixture-shared-input-candidate-v2';seal=json.loads((d/'seal.json').read_bytes())
assert row(d/'seal.json')['sha256']==s['candidateSealSHA256'] and seal['tree_sha256']==s['candidateTreeSHA256']
assert len(seal['members'])==29 and sum(m['bytes'] for m in seal['members'])==286447
for m in seal['members']:assert all(row(d/m['path'])[k]==m[k] for k in ('bytes','sha256')),m['path']
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for path,h in protected.items():assert row(ROOT/path)['sha256']==h
source=ROOT/s['workflow']['source'];destination=ROOT/s['workflow']['destination']
assert not destination.exists();destination.write_bytes(source.read_bytes())
assert row(destination)['sha256']==s['workflow']['sha256']
assert row(OUT/'capacity-window-result.json')['sha256']==s['smallCapacitySummary']['sha256']
sys.path.insert(0,str(d));module=runpy.run_path(str(d/'verify_candidate.py'),run_name='delivery_candidate_verify')
verification=module['verify'](installed=True)
save('candidate-verification.json',{'schema':1,'at':now(),'python':platform.python_version(),'scope':'file and source closure only; no runtime compiler child or native operations','result':verification})
prior=json.loads((ROOT/'verification/github-delivery-shared-input-fixture/ci-review/handoff.json').read_bytes())
save('prior-diagnostic-summary.json',{'schema':1,'at':now(),'actualDiagnostic':prior['actual_diagnostic'],'engineRun':prior['engine_run'],'rawCILocalOnly':True,'source':row(ROOT/'verification/github-delivery-shared-input-fixture/ci-review/handoff.json')})
before=[row(ROOT/f) for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')]
section='''## Selected shared-input fixture controls v2

Root selects the exact cwd-corrected thin fixture v2 for one bounded manual
diagnostic. Prior run [40790391653](https://github.com/snowdamiz/mixer/actions/runs/40790391653)
passed nine materializer groups and 35 of 36 runner controls, then failed the
optimized-Python import control and skipped the complete fixture. v2 adds only
the control subprocess working directory and required sibling/hash bindings;
accepted Rust, all 1,003 vectors and original assertions remain unchanged. The
[selection](verification/github-delivery-shared-input-v2/selection.json) binds
29 sealed members. Pure evidence passes 28 runner, nine materializer and six
same-agent integration controls plus an in-process optimized differential.
The real 36 controls, declared Rust `1.98.1-aarch64-apple-darwin` and complete
103-command fixture remain pending, with 60 seconds per child, 600 active and
60 cleanup seconds. No fallback, retry or default-pack promotion is selected.
Prior ordinary Engine run 40790385107 passed all six jobs. No fixture speedup,
runtime release or GA result is claimed.

The separate capacity run [40788458735](https://github.com/snowdamiz/mixer/actions/runs/40788458735)
is closed: both arms matched all eleven original Corpus 1 fields and entered
Corpus 2, then reached the unchanged 600-second cumulative Runtime deadline.
All eleven command groups closed; final counters and tickets are zero and
owned scratch was removed. [Small sealed result](verification/github-delivery-shared-input-v2/capacity-window-result.json)
records no endpoint-performance or full two-corpus feasibility claim. Its two
attempts are spent. A separate one-arm dense-512 completion experiment is under
preparation; no run is selected.

FieldLog public `496399f8` run [40788707965](https://github.com/snowdamiz/fieldlog/actions/runs/40788707965)
passed 73-blob public hydration and the app-read allowlist, then failed the
Executor process-group guard before the inner Git child. Build and all 38 tests
remain unreached. Cleanup covers 12 outer groups and 29 acquisition children;
the rejected adapter's actual PGID is unknown, and eight earlier local reads
 lack separate group receipts. The selected two-script nested-group candidate
with corrected final nomination drain is delivered at public FieldLog `3b492947`;
its one host run [40792980271](https://github.com/snowdamiz/fieldlog/actions/runs/40792980271)
awaits actual review. Source evidence passes 19 producer and five acceptance
controls; actual ownership/build and 38 tests remain pending. No FieldLog source or raw CI is
copied here. Gates stay **8 running, 30 planned, 0 verified**; all native/UI/capture,
phone, local compiler/custody, Unit A and broad hosted holds remain.

'''
for f in ('PLAN.md','STATUS.md'):
    p=ROOT/f;text=p.read_text();start=text.index('## Selected shared-input fixture diagnostic');end=text.index('## Closed public host campaigns',start);p.write_text(text[:start]+section+text[end:])
w=json.loads((ROOT/'work-graph.json').read_bytes());g=json.loads((ROOT/'gates/ga.json').read_bytes());w['updated']=now()
selection={'at':now(),'selection':row(OUT/'selection.json'),'candidateSeal':row(d/'seal.json'),'candidateTreeSHA256':s['candidateTreeSHA256'],'workflow':row(destination),'sourceOnlyAccepted':True,'dispatchLimit':1,'bounds':s['limits'],'pureControls':{'runner':28,'materializer':9,'sameAgentIntegration':6,'optimizedDifferential':'in-process-only'},'real36ControlsCompilerAnd103CommandFixture':'pending','compilerFallbackRetryOrDefaultPackPromotion':False,'runtimeProductionOrGAAccepted':False}
capacity={'summary':row(OUT/'capacity-window-result.json'),'run':40788458735,'status':'closed; both Corpus 1 all eleven fields matched; both Corpus 2 RuntimeDeadline at 600 seconds','all11CommandsClosed':True,'finalCountersAndTicketsZero':True,'ownedScratchRemoved':True,'fullAttemptsRemaining':0,'endpointPerformanceOrGAClaim':False,'next':'Separate dense-512 one-arm completion experiment under preparation; no run selected'}
fieldlog={'priorRun':40788707965,'sourceCandidate':'Root selected two-script nested-group candidate with corrected final nomination drain; separate FieldLog delivery owns source','commit':'3b492947afd53dbae82a0275ce14f96ff16f1047','tree':'afd0c5dda09b02dda0e06f33142aff1b330e2850','run':40792980271,'runStatus':'dispatched; actual review pending','pureProducerControls':19,'pureAcceptanceControls':5,'actualOwnershipBuildAnd38Tests':'pending','priorRejectedAdapterActualPGIDKnown':False,'priorOuterGroupsClosed':12,'priorAcquisitionChildrenClosed':29,'initialLocalReadsWithoutSeparateGroupReceipts':8,'productionOrGAAccepted':False}
for doc in (w,g):
    doc['executionPolicy']['currentSharedInputFixtureV2Selection']=copy.deepcopy(selection)
    doc['executionPolicy']['currentCapacityWindowSelection']['closedResult']=copy.deepcopy(capacity)
    doc['executionPolicy']['currentFieldLogNestedGroupSelection']=copy.deepcopy(fieldlog)
for item in (w['packages'][7],g['gates'][1]):
    item['sharedInputFixtureV2Diagnostic']=copy.deepcopy(selection);item['sharedInputFixturePriorDiagnosticResult']=row(OUT/'prior-diagnostic-summary.json')
    item['empiricalCacheDeadlineCampaign']['architecture_comparison']['capacity_window_v1']['closedResult']=copy.deepcopy(capacity)
    for p in (row(OUT/'selection.json')['path'],row(d/'seal.json')['path'],row(OUT/'capacity-window-result.json')['path'],row(OUT/'prior-diagnostic-summary.json')['path']):
        if p not in item['evidence']:item['evidence'].append(p)
for item in (w['packages'][16],g['gates'][25],g['gates'][26]):item['fieldlogNestedGroupSourceSelection']=copy.deepcopy(fieldlog)
assert [sum(x['status']==s for x in g['gates']) for s in ('running','planned','verified')]==[8,30,0]
assert w['packages'][7]['empiricalCacheDeadlineCampaign']==g['gates'][1]['empiricalCacheDeadlineCampaign']
for f,doc in (('work-graph.json',w),('gates/ga.json',g)):(ROOT/f).write_text(json.dumps(doc,indent=2,ensure_ascii=True)+'\n')
save('preflight.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'candidateSeal':row(d/'seal.json'),'dependencyClosure':closure,'requiredTrackedSparseMembers':len(closure),'protectedFilesUnchanged':protected,'metadataBefore':before,'metadataAfter':[row(ROOT/f) for f in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')],'versions':versions,'python':platform.python_version(),'commands':c.records,'allCommandsReapedGroupsAbsentAndEOF':True,'noCompilerRuntimeNativeUICaptureOrHeldProbesStarted':True,'wranglerUntouched':True})
print(json.dumps({'dependencyMembers':len(closure),'v2Members':29,'workflowSHA256':row(destination)['sha256'],'gateCounts':[8,30,0],'ownedCommands':len(c.records),'allReapedGroupsAbsentEOF':True}))
