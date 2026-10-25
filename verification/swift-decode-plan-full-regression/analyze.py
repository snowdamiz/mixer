#!/usr/bin/env python3
"""Reconcile actual host commands, source identity, fixture deltas and limitations."""
from pathlib import Path
import difflib, hashlib, json, re, shutil
H=Path(__file__).resolve().parent;R=H.parents[1]
P=H.parent/'swift-decode-plan-reuse-diagnosis'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def read(n):return json.loads((H/n).read_text())
def named(stdout):
    out=[]
    for m in re.finditer(r'^test ([^\n]+?) \.\.\. ([\s\S]*?)(?=^test [^\n]+? \.\.\. |^failures:|^test result:|\Z)',stdout,re.M):
        name,body=m.groups();status=re.search(r'^(ok|FAILED|ignored[^\n]*)\s*$',body,re.M)
        assert status,(name,body[-200:]);out.append({'name':name,'result':status.group(1)})
    return out
rows={}
for p in sorted((H/'commands').glob('*/receipt.json')):
    r=json.loads(p.read_text());label=p.parent.name
    assert r['sourceUnchanged'] and r['ownedGroupAbsent'] and all(r['streamsClosed'].values()) and not r['signals']
    for n in ('stdout','stderr'):assert sha(p.parent/n)==r[n+'SHA256']
    assert sha(p.parent/'source-manifest.json')==r['sourceManifestSHA256']
    m=json.loads((p.parent/'source-manifest.json').read_text())
    for n,v in m.items():assert sha(H/'source-objects'/v)==v
    tests=named((p.parent/'stdout').read_text()) if r['action'] in ('suite','named','observe') else []
    counts={'passed':sum(t['result']=='ok' for t in tests),'failed':sum(t['result']=='FAILED' for t in tests),'ignored':sum(t['result'].startswith('ignored') for t in tests)}
    assert counts=={'passed':r['passedTests'],'failed':r['failedTests'],'ignored':r['ignoredTests']},(label,counts)
    rows[label]={'argv':r['argv'],'context':r['context'],'action':r['action'],'exitCode':r['exitCode'],'qualifyingPass':r['qualifyingPass'],'sourceManifestSHA256':r['sourceManifestSHA256'],'stdoutSHA256':r['stdoutSHA256'],'stderrSHA256':r['stderrSHA256'],'namedTests':tests,**counts,'zeroTestCommandNonqualifying':r['action'] in ('suite','named','observe') and counts['passed']+counts['failed']==0,'streamsClosed':True,'groupAbsent':True,'ignoredNames':[t['name'] for t in tests if t['result'].startswith('ignored')],'failedNames':[t['name'] for t in tests if t['result']=='FAILED']}
save(H/'command-audit.json',rows)
finals={'swift-debug':'final-swift-debug','swift-release':'final-swift-release','full-debug':'corrected-full-debug','full-release':'corrected-full-release'}
finalm={str(p.relative_to(H/'source')):sha(p) for p in sorted((H/'source').rglob('*')) if p.is_file()}
save(H/'final-source-manifest.json',finalm)
expected=read('candidate-input-manifest.json');assert len(finalm)==len(expected)==132
allowed=read('selection.json')['fixtureFilesAllowed']
changed=[n for n in expected if finalm[n]!=expected[n]];assert changed==sorted(allowed)
live=read('live-input-manifest.json');assert all(sha(R/'vm'/n)==v for n,v in live.items())
matrix={}
for context,label in finals.items():
    r=rows[label];assert r['qualifyingPass'] and r['sourceManifestSHA256']==sha(H/'final-source-manifest.json')
    assert r['passed']==(519 if context.startswith('swift') else 638) and r['ignored']==9
    names={t['name'] for t in r['namedTests'] if t['result']=='ok'}
    assert 'experimental_swift_reactor::cache_tests::construction_and_operation_phase_boundaries' in names
    for n in ['plan_reuse_constructor_all_boundaries','plan_reuse_cold_cached_all_boundaries','plan_reuse_collision_publish_boundaries','plan_reuse_cached_deadline_and_precedence','resident_index_inclusive_64_node_chain_and_cycle_bound']:
        assert 'experimental_swift_reactor::cache_tests::'+n in names
    s=(H/'commands'/label/'stdout').read_text()
    assert 'PLAN_CONSTRUCTOR allocation=5 capacity=5 shorter_work=4893 cancellation_checks=1331 cleanup_zero=true' in s
    assert 'PLAN_OPERATION cached=false shorter_work=129 cancellation_checks=74 allocations=3 cleanup_zero=true' in s
    assert 'PLAN_OPERATION cached=true shorter_work=119 cancellation_checks=67 allocations=3 cleanup_zero=true' in s
    assert 'PLAN_COLLISION shorter_work=112 cancellation_checks=56 atomic=true cleanup_zero=true' in s
    assert 'REGRESSION_LIFECYCLE work=[4893, 5061, 5394, 5411] instructions=[0, 6, 18, 30] host_calls=[0, 0, 0, 0] entries=[0, 1, 3, 3] tickets=[21, 22, 24, 24]' in s
    assert 'REGRESSION_EMPTY_INIT start=4893 initialized=5022' in s
    assert 'REGRESSION_INTEGRATED_ALLOCATION ordinal=14 ' in s and 'REGRESSION_INTEGRATED_CAPACITY ordinal=5 ' in s
    matrix[context]={'command':label,'passed':r['passed'],'failed':r['failed'],'ignored':r['ignored'],'ignoredNames':r['ignoredNames'],'namedTests':r['namedTests'],'exactPhaseHelperThroughRealEnclosingTest':True,'sourceManifestSHA256':r['sourceManifestSHA256'],'compilerSourceAccountingControlsIncluded':True,'scope':'complete ordinary local host suite; no full Swift module/workload or native/device qualification'}
save(H/'matrix.json',matrix)
assert rows['swift-only-library-clippy']['qualifyingPass']
assert rows['original-swift-debug']['failed']==12
assert rows['admission-next-original-failure']['failed']==1
for n in ('final-full-debug','final-full-release'):
    assert rows[n]['failedNames']==['original_probes_match_development_node_values_traps_and_memory']
    assert 'development Node oracle must be installed' in (H/'commands'/n/'stderr').read_text()
assert all(not r['zeroTestCommandNonqualifying'] for r in rows.values())
save(H/'source-selection.json',{'rootSuppliedRevision':read('selection.json')['rootSuppliedSourceRevision'],'candidateInput132FileClosure':sha(H/'candidate-input-manifest.json'),'final132FileClosure':sha(H/'final-source-manifest.json'),'originalLive132FileClosure':sha(H/'live-input-manifest.json'),'changedFromCandidate':changed,'productionBytesIdenticalToAcceptedCandidate':True,'allOther129FilesIdentical':True,'liveSourceUnchangedByLane':True,'productionCacheSHA256':finalm['src/experimental_swift_reactor/cache.rs'],'budgetDefaultsBytesUnchanged':True,'fixtureDiffSHA256':sha(H/'fixture.patch')})
# Save exact instruction/plan/source-input snapshots rather than binding mutable trackers externally.
drift=[]
for n,v in read('input-bindings.json').items():
    q=H/'input-documents'/n
    if q.exists() and sha(q)==v:
        if sha(R/n)!=v:
            assert n=='PLAN.md'
            later=H/'input-documents-observed-later'/n;later.parent.mkdir(parents=True,exist_ok=True);later.write_bytes((R/n).read_bytes())
            drift.append({'file':n,'initialBoundSHA256':v,'laterObservedSHA256':sha(later),'originalBytesRetained':True,'recovery':'exact root-owned PLAN.history-2026-10-25.md bytes; see plan-provenance-recovery.json','reason':'root consolidated mutable execution tracker during isolated tests; no execution source affected'})
        continue
    if sha(R/n)==v:
        q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/n).read_bytes())
    else:
        assert n=='PLAN.md',(n,'unexpected binding drift')
        q=H/'input-documents-observed-later'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/n).read_bytes())
        drift.append({'file':n,'initialBoundSHA256':v,'laterObservedSHA256':sha(q),'originalBytesRetained':False,'reason':'root-owned mutable execution tracker changed during long host suite; binding product plan and regression contract remain exact; no execution source affected'})
save(H/'input-drift.json',drift)
# Formatting: same command on the baseline, original candidate, final fixture copy.
fmt={}
for label,lane in [('baseline-format-check','baseline'),('original-format-check','source'),('final-format-check','source')]:
    assert rows[label]['exitCode']==1 and not rows[label]['qualifyingPass']
    s=(H/'commands'/label/'stdout').read_text();hunks={}
    for m in re.finditer(r'^Diff in (.*?):(\d+):\n([\s\S]*?)(?=^Diff in |\Z)',s,re.M):
        path,line,body=m.groups();path='src/'+path.split('/src/',1)[1]
        hunks.setdefault(path,[]).append({'line':int(line),'bodySHA256':hashlib.sha256(body.encode()).hexdigest(),'body':body})
    fmt[label]={'exitCode':1,'files':len(hunks),'hunks':sum(len(v) for v in hunks.values()),'byFile':hunks}
base=fmt['baseline-format-check']['byFile'];candidate=fmt['original-format-check']['byFile']
same=[]
for n in candidate:
    if n.endswith('cache_tests.rs'):continue
    assert (P/'baseline'/n).read_bytes()==(P/'source'/n).read_bytes()
    assert candidate[n]==base[n];same.append(n)
assert len(same)==16 and len(base)==len(candidate)==17
assert 'src/experimental_swift_reactor/cache.rs' not in candidate
fmt.update({'sameReadOnlyCargoFmtCommand':True,'unchangedInheritedFailingPaths':same,'acceptedCandidateProductionCacheHasNoFormattingHunk':True,'candidateOnlyTestFormatting':'plan_reuse_cached_deadline_and_precedence is an additional minified helper hunk; shared profile helper hunk also fails in baseline','regressionOnlyFormatting':'one diagnostic println wrapping hunk and three extra blank-line boundaries before observation appendices; these remain explicit; source not mutated while four host contexts ran','newObservationFragmentsFormattingPass':rows['observation-format-check']['qualifyingPass'],'fullFormattingPass':False})
save(H/'format-comparison.json',fmt)
warnings={}
for label in rows:
    s=(H/'commands'/label/'stderr').read_text()
    warnings[label]=re.findall(r'^warning: (?!`mixer-vm`)([^\n]+)',s,re.M)
for label in finals.values():assert warnings[label]==warnings['original-swift-debug'] or not warnings[label],(label,warnings[label])
save(H/'warnings.json',{'originalInheritedTestWarnings':warnings['original-swift-debug'],'source':'unchanged control_operations_tests.rs lines1619,1643; dropping Copy FrameCompletion values','perCommand':warnings,'swiftOnlyLibraryClippyWarningsDeniedPass':True,'newWarningKinds':[]})
save(H/'observations.json',{'cacheConstructor':{'allocations':5,'capacityFaultOrdinals':list(range(5)),'requestedPayloadBytes':54976,'groupedPlanPayloadBytes':28672,'headerBytes':92128,'fixedCacheBytes':118240,'work64Slots':4928,'work29Slots':4893,'constructorCancellationCheckpoints':1331,'dynamicAllWorkPrefixes':5055,'missCancellationCheckpoints':79},'integratedConstructor':{'allocationOrdinals':list(range(15)),'requestedBytes':39094576,'cleanupDeallocations':25,'stateCapacityOrdinals':list(range(6)),'stateCapacityAllocationAttempts':[10,11,12,13,14,15],'zeroStackAllocations':12,'beforeStateAllocations':9,'categoryAndCombinedAdmissionRequests':[9,12],'allSuccessfulAndInjectedAllocationCleanupCombinedZero':True,'intentionalBadRestore':'original ConstructionBound fixture drains payloads but retains its phase-bound failure/ticket as originally asserted; not reported as zero'},'lifecycle':{'work':[4893,5061,5394,5411],'instructions':[0,6,18,30],'hostCalls':[0,0,0,0],'cacheEntries':[0,1,3,3],'liveTickets':[21,22,24,24],'coldAdditionsPerScan':13,'residentHitCredits':17,'emptyInitExactWorkLimit':5022,'coldCachedResidentDistinguished':True},'coldCachedCollision':{'cold':{'shorterWorkBudgets':129,'cancelCheckpoints':74,'allocationOrdinals':3},'cached':{'shorterWorkBudgets':119,'cancelCheckpoints':67,'allocationOrdinals':3},'collision':{'shorterWorkBudgets':112,'cancelCheckpoints':56,'wholeRecordPublication':True},'cachedDeadlineBoundaries':4,'cancellationDeadlinePrecedencePairs':4},'limitsPreserved':{'cacheBytes':16777216,'entryBytes':8388608,'residents':64,'pins':64,'tickets':86,'cacheWork':64000000,'combinedBytes':268435456,'deadlines':'unchanged production defaults and original test deadlines'},'costTradeoffPreserved':{'tinyRepeatCredits':22056,'baselineTinyRepeatCredits':21594,'tinyRepeatRegressionPercent':(22056/21594-1)*100,'largeRepeatCredits':166440,'baselineLargeRepeatCredits':262234,'fixedCacheIncreaseBytes':29008,'constructorIncreaseCredits':4096,'cpuOrFullTargetClaim':False}})
print(json.dumps({'contexts':{k:{x:v[x] for x in ['passed','failed','ignored']} for k,v in matrix.items()},'source':sha(H/'final-source-manifest.json'),'onlyChanged':changed,'formattingPass':False,'Clippy':True},sort_keys=True))
