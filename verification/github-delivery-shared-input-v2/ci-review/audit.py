"""Offline actual v2 diagnostic audit; source/file work only, no child operations."""
from datetime import datetime,timezone
import hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;OUT=HERE.parent;ROOT=OUT.parents[1]
ARTIFACT=HERE/'artifact';CANDIDATE=ARTIFACT/'verification/cache-fixture-shared-input-candidate-v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_bytes())
def row(p,base=HERE):return {'path':str(p.relative_to(base)),'bytes':p.stat().st_size,'sha256':sha(p)}
def rows(base):return [row(p,base) for p in sorted(base.rglob('*')) if p.is_file()]
def tree(rs):return hashlib.sha256(json.dumps(rs,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
dispatch=load(OUT/'dispatch-receipt.json');acquired=load(HERE/'acquisition.json');selected=load(OUT/'selection.json')
assert dispatch['head']=='28cb1e27ed2eb504e6fb4c6002ad0157efefbeea' and dispatch['tree']=='31259b2657ff92d428e36c8067d5ff1de4e86cff'
assert dispatch['runId']==40793279678 and acquired['attempt']==1 and acquired['runId']==dispatch['runId']
assert sha(HERE/'artifact.zip')==acquired['archiveSHA256']=='723ce9346e124ac3a7a1a4550aea365fba97104591ea321321e3f6a3879e40b3'
assert rows(ARTIFACT)==sorted(acquired['members'],key=lambda r:r['path'])
seal=load(CANDIDATE/'seal.json');assert sha(CANDIDATE/'seal.json')==selected['candidateSealSHA256']
assert len(seal['members'])==29 and tree(seal['members'])==selected['candidateTreeSHA256']
for m in seal['members']:assert row(CANDIDATE/m['path'],CANDIDATE)==m
reviewdir=ARTIFACT/'verification/cache-fixture-shared-input-review';review=load(reviewdir/'seal.json')
assert sha(reviewdir/'seal.json')=='6b5b13ac132044f25c624f83dcf457b3ce39f013bc0a350ccf5da24f2b24acac'
assert tree(review['members'])==review['tree_sha256']
for m in review['members']:assert row(ARTIFACT/m['path'],ARTIFACT)==m
workflow=ARTIFACT/selected['workflow']['destination'];assert sha(workflow)==selected['workflow']['sha256']
assert workflow.read_bytes()==(CANDIDATE/'workflow/cache-fixture-shared-input-controls-v2.yml').read_bytes()
materialized=load(CANDIDATE/'materialized/materialization.json');assert materialized['status']=='passed-exact-materialization' and not materialized['hardlinks_used']
assert len(materialized['copies'])==87 and sum(m['source']=='frozen-base' for m in materialized['copies'])==83
packtrees=[]
for pack in (CANDIDATE/'materialized/pack',CANDIDATE/'runs/ci-40793279678-1/pack'):
    manifest=load(pack/'manifest.json');assert [r for r in rows(pack) if r['path']!='manifest.json']==manifest['members']
    assert len(manifest['members'])==86 and tree(manifest['members'])==manifest['tree_sha256']
    assert sha(pack/'manifest.json')=='e8a74a521ddbc01f0fc1274a32838cab57c60d63ee7924b5b830b56686836c3d'
    assert sha(pack/'source/regression/independent_tests.rs')=='f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141'
    packtrees.append(manifest['tree_sha256'])
assert packtrees==['ac3263770d66a981bc20ee859fb0081bb28d5001ff550163b0a8030a355a505b']*2
assert sha(ARTIFACT/'verification/swift-cache-state-ci/pack/manifest.json')=='d1caf2069e17ac1beff6707d6e084ea49d18382bc959d73d5184ec49cb7886b9'
logs=CANDIDATE/'logs';lines=(logs/'materialization.stdout').read_text().splitlines()
assert lines[:2]==[dispatch['head'],dispatch['tree']]
preflight=json.loads(lines[4]);postflight=load(logs/'candidate-postflight.stdout')
assert preflight==postflight and preflight['inputs']==materialized['inputs']
parse=lambda text:[{'method':m[0],'result':m[1]} for m in re.findall(r'^(test_\w+) \([^\n]+\) \.\.\. (ok|FAIL|ERROR)$',text,re.M)]
runner=parse((logs/'runner-controls.stderr').read_text());materializer=parse((logs/'materializer-controls.stderr').read_text())
assert len(runner)==36 and len(materializer)==9 and all(m['result']=='ok' for m in runner+materializer)
assert any(m['method']=='test_checks_active_under_optimized_python' for m in runner)
run=CANDIDATE/'runs/ci-40793279678-1';receipt=load(run/'receipt.json');command=load(run/'commands/compiler-sysroot.json')
assert receipt['commands']==[command] and command['name']=='compiler-sysroot' and command['exit']==1
assert command['child_returned'] and command['owned_group_gone'] and not command['custody_hold'] and not command['timed_out'] and not command['output_capped']
assert command['argv']==['/Users/runner/.cargo/bin/rustc','--print','sysroot'] and command['new_session']
for stream in ('stdout','stderr'):assert sha(run/('commands/compiler-sysroot.'+stream))==command[stream+'_sha256']
stderr=(run/'commands/compiler-sysroot.stderr').read_text();assert "toolchain '1.98.1-aarch64-apple-darwin' is not installed" in stderr
assert receipt['status']=='failed' and receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned']
assert receipt['postflight'] and all(v['passed'] for v in receipt['postflight'].values())
assert receipt['active_deadline_seconds']==600 and receipt['cleanup_allowance_seconds']==60 and receipt['per_child_seconds']==60
assert receipt['original_full_Debug_timeout_remains_failed'] and not receipt['semanticMetricsValid'] and not receipt['GA_qualified'] and not receipt['fullReplayAccepted']
assert not load(run/'retention.json')['files'] and not list(ARTIFACT.rglob('*custody-hold*'))
descendant=load(logs/'descendant-control/control.json');child=descendant['receipt']['commands'][0]
assert child['child_returned'] and child['owned_group_gone'] and child['owned_group_killed'] and not child['custody_hold']
for stage in ('postflight','retention'):
    d=load(logs/('deadline-'+stage+'-control.json'));assert not d['receipt']['commands'] and d['receipt']['cleanup']['deadline_expired'] and d['scratch_preserved_at_assertion']
report={'schema':1,'reviewedUTC':datetime.now(timezone.utc).isoformat(),'command':['python3','-B','verification/github-delivery-shared-input-v2/ci-review/audit.py'],'python':sys.version,'head':dispatch['head'],'tree':dispatch['tree'],'run':dispatch['runId'],'attempt':1,'scope':'Offline actual artifact/source/custody review; no local compiler/runtime/Git/native/UI/capture/held-process probe','artifact':{'id':acquired['artifact']['id'],'bytes':(HERE/'artifact.zip').stat().st_size,'sha256':sha(HERE/'artifact.zip'),'members':len(acquired['members']),'rawLocalOnly':True},'bindings':{'all29CandidateMembersExact':True,'sourceReviewMembersExact':True,'workflowExact':True,'both86MemberPacksExact':True,'candidatePreflightEqualsPostflight':True,'materializedPackTreeSHA256':packtrees[0],'acceptedRustSourceSHA256':'f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141'},'hostObserved':{'python':lines[2],'os':lines[3]},'controls':{'runner':runner,'materializer':materializer,'optimizedChildPassed':True,'standaloneOptimizedChildCustodyReceiptRetained':False},'fixture':{'invocations':1,'declaredCommands':103,'observedCommands':1,'compilerAvailability':'declared toolchain not installed; compiler identity not established','firstCommand':command,'stderr':stderr,'rustCompilationOrTestsObserved':False,'status':'failed at first compiler-sysroot child','metricsValid':False},'cleanup':{'fixtureChildReapedAndGroupAbsent':True,'fixtureScratchRemoved':True,'postflightPassed':True,'descendantNegativeControlClosed':True,'controlCleanupLimits':'Passing unittest includes teardown; most individual child receipts removed with test scratch. No process discovery performed.','regularFileStreams':'Hashes bound after child wait/group absence; no explicit remote pipe EOF field.'},'acceptance':{'retryInstallFallbackOrDefaultPromotion':False,'compilerAvailableOrFullFixturePassed':False,'nativeReleaseOrGA':False,'allPriorFailuresAndHoldsPreserved':True}}
save(HERE/'review.json',report)
summary={'schema':1,'at':report['reviewedUTC'],'head':dispatch['head'],'tree':dispatch['tree'],'run':dispatch['runId'],'attempt':1,'conclusion':'failure','scope':'Sanitized actual v2 CI result; raw retained locally','artifact':report['artifact'],'sourceBindings':report['bindings'],'controls':{'runnerPassed':36,'runnerTotal':36,'materializerPassed':9,'materializerTotal':9,'realOptimizedPythonControlPassed':True,'standaloneOptimizedChildCustodyReceiptRetained':False},'fixture':{'invocations':1,'declaredCommands':103,'observedCommands':1,'firstCommand':'compiler-sysroot','exit':1,'diagnostic':"toolchain '1.98.1-aarch64-apple-darwin' is not installed",'compilerIdentityEstablished':False,'rustCompilationOrTestsObserved':False,'activeElapsedSeconds':receipt['active_elapsed_seconds'],'cleanupElapsedSeconds':receipt['cleanup_elapsed_seconds'],'status':'failed before compile/list/test commands'},'cleanup':report['cleanup'],'postflightAndArtifactUploadPassed':True,'review':row(HERE/'review.json'),'noRetryInstallFallbackOrDefaultPromotionSelected':True,'runtimeReleaseOrGAAccepted':False,'gateCounts':[8,30,0]}
save(OUT/'diagnostic-result.json',summary)
save(OUT/'diagnostic-result-seal.json',{'schema':1,'at':report['reviewedUTC'],'scope':'Only compact diagnostic-result.json eligible for publication; raw review/artifact local only','member':row(OUT/'diagnostic-result.json',OUT),'head':dispatch['head'],'tree':dispatch['tree'],'run':dispatch['runId'],'attempt':1})
rawmembers=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file()]
save(HERE/'seal.json',{'schema':1,'rawLocalOnly':True,'members':rawmembers,'treeSHA256':tree(rawmembers),'scope':'Immutable raw artifact, acquisition, offline audit source and report; no remote operation performed by audit'})
print(json.dumps({'status':'passed-actual-artifact-review','runnerPassed':36,'materializerPassed':9,'fixtureCommandsObserved':1,'failure':'declared compiler not installed','fixtureChildClosed':True,'scratchRemoved':True,'summarySHA256':sha(OUT/'diagnostic-result.json'),'rawSealSHA256':sha(HERE/'seal.json')}))
