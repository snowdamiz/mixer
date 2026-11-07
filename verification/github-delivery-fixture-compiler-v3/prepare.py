import importlib.util,json,sys
from owned import OUT,ROOT,row,save,now
s=json.loads((OUT/'selection.json').read_bytes());d=ROOT/'verification/cache-fixture-compiler-admission-v3'
sys.path.insert(0,str(d));from offline_guard import install
install(OUT)
from verify_candidate import verify
v=verify(True);save('candidate-verification.json',{'schema':1,'at':now(),'result':v,'scope':'File-only source, frozen dependencies and exact workflow verification; no compiler or fixture run'})
before={p:row(ROOT/p) for p in ('PLAN.md','STATUS.md','work-graph.json','gates/ga.json')}
fixture='''Mixer fixture v2 at `28cb1e27` is closed. [Run 40793279678](https://github.com/snowdamiz/mixer/actions/runs/40793279678) passes all 36 runner and nine materializer controls, including the real optimized-Python probe. Its first fixture child rejects the absent declared Rust `1.98.1-aarch64-apple-darwin` toolchain. No Rust compilation, fixture tests or performance metrics ran. The child was reaped, its group was absent and owned scratch was removed. [Compact result](verification/github-delivery-shared-input-v2/diagnostic-result.json) records the precise custody limits. Root now [selects the sealed v3 compiler admission](verification/github-delivery-fixture-compiler-v3/selection.json) for one manual run: one explicit official Rustup install of that exact compiler in an isolated job-owned home within 120 seconds, followed only on success by one persisted claim and the unchanged v2 fixture. Eighteen pure source controls pass. All 45 v2 controls, 103 commands, 1,003 vectors and original limits remain required. Automatic install, fallback and retry are disabled. Rustup descendant reap and provider disposal are unverified; the toolchain home is retained for provider disposal. Actual provisioning, compiler identity and complete fixture execution remain pending.'''
fieldlog='''FieldLog public `7ded0f57` [run 40794520691](https://github.com/snowdamiz/fieldlog/actions/runs/40794520691) is closed after 19.022 seconds. Public metadata acquisition and all 73 requested blob bodies pass; three registered adapter groups reach inner Git, then SwiftPM probes its absent pre-clone repository path and the adapter fails closed. All 12 recorded outer groups and three registered adapter groups closed and drained, with 32 inner Git children. Persisted events and exact source bind the ownership ACK path; registry work files were not retained. No repository/checkout clone, build or any of the 38 tests ran. The [small result](verification/github-delivery-fixture-compiler-v3/fieldlog-parent-sid-result.json) preserves the actual scope. A source-only absent-probe correction is under preparation; no further FieldLog run is selected. Earlier unknown adapter identities and eight unreceipted local reads remain historical limitations.'''
for name in ('PLAN.md','STATUS.md'):
 p=ROOT/name;text=p.read_text();start=text.index('Mixer fixture v2 at `28cb1e27`');end=text.index('\n\nThe prior VM',start)
 text=text[:start]+fixture+'\n\n'+fieldlog+text[end:];p.write_text(text)
rec={'at':now(),'selection':row(OUT/'selection.json'),'candidateSeal':row(d/'seal.json'),'candidateTreeSHA256':s['candidateTreeSHA256'],'workflow':row(ROOT/s['workflow']['destination']),'pureControlsPassed':18,'sourceOnlyAccepted':True,'dispatchLimit':1,'compiler':s['compiler'],'fixture':s['fixture'],'rustupCustody':s['rustupCustody'],'priorV2Result':s['priorV2Result'],'actualCompilerAndCompleteFixture':'pending sole selected manual dispatch','retryFallbackOrDefaultPromotion':False,'runtimeProductionOrGAAccepted':False}
f=json.loads((OUT/'fieldlog-parent-sid-result.json').read_bytes())
frec={'summary':row(OUT/'fieldlog-parent-sid-result.json'),'commit':f['appRevision'],'tree':f['appTree'],'run':f['runID'],'status':f['status'],'publicBlobBodiesVerified':73,'recordedOuterGroups':12,'registeredAdapterGroups':3,'innerGitChildren':32,'recordedGroupsClosedAndDrained':True,'actualOwnershipACKScope':f['ACKScope'],'registryWorkfilesRetained':False,'repositoryAndCheckoutClones':0,'hostTestsExecuted':0,'authoredTests':38,'next':'Source-only absent pre-clone repository probe correction under preparation; no run selected','nativeDogfoodOrGA':False}
for name in ('work-graph.json','gates/ga.json'):
 p=ROOT/name;j=json.loads(p.read_bytes());j['executionPolicy']['currentFixtureCompilerV3Selection']=rec;j['executionPolicy']['currentFieldLogParentSIDResult']=frec
 j['executionPolicy']['currentSharedInputFixtureV2Selection']['next']='Superseded by selected v3 explicit exact compiler provisioning; prior v2 result preserved'
 j['executionPolicy']['currentFieldLogNestedGroupSelection']['next']='Superseded by parentSID correction actual result; missing pre-clone repository probe correction remains source-only'
 if name=='work-graph.json':j['updated']=now();items=j['packages']
 else:items=j['gates']
 for item in items:
  if 'sharedInputFixtureV2Diagnostic' in item:
   item['fixtureCompilerV3Selection']=rec
   item['sharedInputFixtureV2Diagnostic']['next']='Superseded by selected v3 explicit exact compiler provisioning; prior v2 result preserved'
   if 'verification/github-delivery-fixture-compiler-v3/selection.json' not in item['evidence']:item['evidence'].append('verification/github-delivery-fixture-compiler-v3/selection.json')
  if 'fieldlogNestedGroupSourceSelection' in item:
   item['fieldlogParentSIDResult']=frec
   item['fieldlogNestedGroupSourceSelection']['next']='Superseded by parentSID correction actual result; missing pre-clone repository probe correction remains source-only'
   if 'verification/github-delivery-fixture-compiler-v3/fieldlog-parent-sid-result.json' not in item['evidence']:item['evidence'].append('verification/github-delivery-fixture-compiler-v3/fieldlog-parent-sid-result.json')
   if 'activePublicSDKFlow' in item:item['activePublicSDKFlow']['latestParentSIDResult']=frec
 p.write_text(json.dumps(j,indent=2)+'\n')
g=json.loads((ROOT/'gates/ga.json').read_bytes());assert [sum(x['status']==status for x in g['gates']) for status in ('running','planned','verified')]==[8,30,0]
save('metadata-binding.json',{'schema':1,'at':now(),'before':before,'after':{p:row(ROOT/p) for p in before},'vmStatus':'Preserved exact-base workflow success and pending independent artifact/accounting review; no inferred runtime acceptance','fieldlogLatest':frec,'gates':{'running':8,'planned':30,'verified':0},'sourceOnly':True})
print(json.dumps({'candidateVerification':'passed','metadataUpdated':list(before),'gates':[8,30,0]}))
