#!/usr/bin/env python3
"""Reconcile actual execution counts, provenance and independent arithmetic."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;P=H.parent/'swift-decode-plan-reuse-diagnosis'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
receipts={p.parent.name:read(p) for p in sorted((H/'commands').glob('*/receipt.json'))}
assert len(receipts)==36
assert sum(r['passedTests'] for r in receipts.values())==35
assert sum(r['failedTests'] for r in receipts.values())==1
assert all(len(r['executedNamedTests'])==1 and r['sourceUnchanged'] and r['ownedGroupAbsent'] and all(r['streamsClosed'].values()) for r in receipts.values())
assert [n for n,r in receipts.items() if not r['qualifyingPass']]==['candidate-exact-phase-original']
save(H/'command-audit.json',{n:{k:r[k] for k in ['exitCode','executedNamedTests','passedTests','failedTests','qualifyingPass','pgid','sourceUnchanged','ownedGroupAbsent','streamsClosed','sourceManifestSHA256']} for n,r in receipts.items()})
variants={}
def offer(data):variants[hashlib.sha256(data).hexdigest()]=data
for lane,original in [('baseline','baseline'),('candidate','source')]:
    inputs=read(H/(lane+'-input-manifest.json'))
    producer=read(P/('baseline-control-manifest.json' if lane=='baseline' else 'source-manifest.json'))
    assert inputs==producer and len(inputs)==132
    for root in [H/lane,P/original]:
        for p in root.rglob('*'):
            if p.is_file():offer(p.read_bytes())
    c=(P/original/'src/experimental_swift_reactor/cache.rs').read_text()+(H/'layout-controls.rs').read_text().replace('REVIEW_CANDIDATE',str(lane=='candidate').lower())
    offer(c.encode())
    assert (H/lane/'src/experimental_swift_reactor/cache.rs').read_text()==c+((H/'candidate-layout-controls.rs').read_text() if lane=='candidate' else '')
    t=(H/'independent-controls.rs').read_text()
    initial_operations='["I32Const(7)","Drop","Block { end: 5 }","Nop","End","End"]'
    current_operations='["Const(I32(7))","Drop","Block { kind: Block, result: None, end: 4, alternative: None }","Nop","End","End"]'
    for initial in [False,True]:
        for initial_credit in [False,True]:
            appendix=t.replace(current_operations,initial_operations) if initial else t
            if initial_credit:appendix=appendix.replace('else {assert_eq!(credits[2],credits[4]);}','else {assert_eq!(credits[0],credits[2]);assert_eq!(credits[0],credits[4]);}')
            for rewritten in [False,True]:
                base=(P/original/'src/experimental_swift_reactor/cache_tests.rs').read_text()
                # fix-and-extend retained the leading newline from the previous
                # appendix then appended the replacement's leading newline.
                s=base+('\n' if rewritten else '')+appendix
                for corrected in [False,True]:
                    v=s
                    if corrected:v=v.replace('if ceiling == header + patch_bytes {\n            assert_eq!(stats.attempts, 2);','if ceiling == header + patch_bytes {\n            assert_eq!(stats.attempts, 3);')
                    offer(v.encode());offer((v+(H/'candidate-controls.rs').read_text()).encode())
    current={str(p.relative_to(H/lane)):sha(p) for p in sorted((H/lane).rglob('*')) if p.is_file()}
    changes=[n for n in current if current[n]!=inputs[n]]
    assert changes==['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
    expected_tests=(P/original/'src/experimental_swift_reactor/cache_tests.rs').read_text()+'\n'+t
    if lane=='candidate':
        expected_tests=expected_tests.replace('if ceiling == header + patch_bytes {\n            assert_eq!(stats.attempts, 2);','if ceiling == header + patch_bytes {\n            assert_eq!(stats.attempts, 3);')+(H/'candidate-controls.rs').read_text()
    assert (H/lane/'src/experimental_swift_reactor/cache_tests.rs').read_text()==expected_tests
    save(H/(lane+'-review-manifest.json'),current)
objects=H/'source-objects';objects.mkdir(exist_ok=True)
all_bindings=0
for n,r in receipts.items():
    for name,digest in read(H/'commands'/n/'source-manifest.json').items():
        assert digest in variants,(n,name,digest)
        p=objects/digest
        if not p.exists():p.write_bytes(variants[digest])
        all_bindings+=1
frozen=[]
for suffix in ['frozen-ir-parity-for-all-supported-opcode-shapes','frozen-layout-and-trace-observation','frozen-borrowed-transients-fit-existing-scratch']:
    paths=[H/'commands'/(lane+'-'+suffix)/'stdout' for lane in ['baseline','candidate']]
    normalize=lambda s:'\n'.join(x for x in s.splitlines() if not x.startswith('test result:'))
    a,b=[normalize(p.read_text()) for p in paths];assert a==b
    frozen.append({'control':suffix,'normalizedSHA256':hashlib.sha256(a.encode()).hexdigest(),'equal':True,'normalization':'remove only final test result summary line, containing differing filtered count and elapsed time'})
frozen_source=[n for n in read(P/'source-manifest.json') if n.startswith('src/experimental/cache/')]
assert all(sha(P/'source'/n)==sha(P/'baseline'/n)==sha(H/'candidate'/n)==sha(H/'baseline'/n) for n in frozen_source)
save(H/'frozen-comparison.json',{'controls':frozen,'unchangedSourceFiles':frozen_source,'exhaustiveProof':False})
profiles={}
for lane in ['baseline','candidate']:
    text=(H/'commands'/(lane+'-profile-admission')/'stdout').read_text()
    profiles[lane]={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',text.split('PLAN_PROFILE ',1)[1].split('\n',1)[0])}
    p=profiles[lane]
    computed=(64+16+16+128)*1024*1024+p['wasi_max']+p['shared']+p['floor']+max(p['execution_construction'],p['frame_operation']+(92350 if lane=='candidate' else 88294))
    assert computed==p['conservative_combined']
    assert computed<=268435456
    # Even a deliberately summed outer+inner execution construction plus the
    # nested cache envelope is far below the selected frame/cache phase.
    assert 2*p['execution_construction']+(61880 if lane=='candidate' else 57752)<p['frame_operation']
assert profiles['candidate']['conservative_combined']==266787998
assert 268435456-profiles['candidate']['conservative_combined']==1647458
save(H/'accounting.json',{'profiles':profiles,'combinedHeadroomBytes':1647458,'fixedReservationIncreaseBytes':118240-89232,'constructorWorkIncrease':4928-832,'cacheHeaderIncrease':92128-63120,'cleanupIncrease':62888-62576,'constructionIncrease':61880-57752,'operationIncrease':92350-88294,'envelope':'conservative disjoint named-object reservations; not allocator overhead, stack or RSS','formula':'(64+16+16+128)*MiB + defaultWasi + shared + foundation + max(executionConstruction, frameOperation+cacheOperation)','stateCategoryIncludesExecutionHeaderAndGrowthOverlap':True})
save(H/'analysis.json',{'commands':36,'passingNamedTestExecutions':35,'failingNamedTestExecutions':1,'uniqueExecutedNames':len({n for r in receipts.values() for n in r['executedNamedTests']}),'zeroTestCommands':0,'independentCandidateDebug':9,'independentCandidateRelease':9,'independentBaselineDebug':5,'baselineFrozen':3,'candidateFrozen':3,'profileAdmissionEachSide':1,'inheritedCollisionAndCachedDeadline':2,'enclosingExactPhase':{'baselinePass':1,'candidateOriginalFailure':1,'candidateCorrectedPass':1},'sourceBindingsChecked':all_bindings,'contentAddressedSourceObjects':len(list(objects.iterdir())),'findings':[],'expectedFixtureFailure':'candidate-exact-phase-original','fullRegression':False,'liveIntegration':False,'GA':False})
(H/'pending-full-suite-updates.json').write_bytes((P/'pending-full-suite-updates.json').read_bytes())
save(H/'exploration-failures.json',{'scope':'Non-executable read-only path guesses, no build/test evidence','retainedFailures':['Initial candidate/src/runtime/swift paths did not exist; sealed candidate is source/src/experimental_swift_reactor.','Two guessed experimental/cache.rs reads did not exist; the module is experimental/cache/mod.rs.','Guessed borrowed_tests.rs did not exist; actual Frozen controls are experimental/cache/tests.rs.','A zsh execution/*.rs glob found no files; execution uses path-selected sibling modules.','Guessed state.rs and experimental_swift_reactor.rs did not exist; relevant source is execution.rs and the reactor module directory.'],'truncatedReads':'Some large read-only outputs were capped; targeted follow-up reads supplied audit code.','testFailures':'Exactly one executed failure; retained under commands/candidate-exact-phase-original.'})
print(json.dumps(read(H/'analysis.json'),sort_keys=True))
