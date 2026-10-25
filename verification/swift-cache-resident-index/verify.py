#!/usr/bin/env python3
"""Verify the final isolated candidate and retained finite evidence, never a target."""
from pathlib import Path
import datetime,difflib,hashlib,json,re,sys
H=Path(__file__).resolve().parent;R=H.parent.parent
C='b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11'
if (H/'seal.json').exists():
    sealed=json.loads((H/'seal.json').read_text())
    assert all(hashlib.sha256((H/n).read_bytes()).hexdigest()==v for n,v in sealed['members'].items())
    receipt=json.loads((H/'receipt.json').read_text())
    assert hashlib.sha256((R/'docs/swift-cache-resident-index.md').read_bytes()).hexdigest()==receipt['reportSHA256']
    baseline=json.loads((H/'baseline-manifest.json').read_text())
    assert all(hashlib.sha256((R/'vm'/n).read_bytes()).hexdigest()==v for n,v in baseline.items())
    print(json.dumps({'sealedPacketVerified':True,'memberCount':len(sealed['members']),'candidateClosure':sealed['candidateClosure'],'live132Unchanged':True}))
    sys.exit(0)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(name,value):(H/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def manifest(d):
 ps=[d/'Cargo.toml',d/'Cargo.lock']+[p for top in ('include','src','tests') for p in (d/top).rglob('*') if p.is_file()]
 return {str(p.relative_to(d)):sha(p) for p in sorted(ps)}
def closure(m):return hashlib.sha256((json.dumps(m,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
def command(label):
 d=H/'commands'/label;r=read(d/'receipt.json')
 assert r['passed'] and r['sourceUnchanged'] and r['ownedGroupAbsent'] and all(r['streamEOF'].values()),label
 assert sha(d/'stdout')==r['stdoutSHA256'] and sha(d/'stderr')==r['stderrSHA256']
 assert sha(d/'source-manifest.json')==r['sourceManifestSHA256']
 return d,r
original=read(H/'baseline-manifest.json');assert len(original)==132 and closure(original)==C
assert manifest(R/'vm')==original,'live VM drift'
for n,v in read(H/'input-bindings.json').items():assert sha(R/n)==v['sha256'],n
current=manifest(H/'source');changed=[n for n in original if current[n]!=original[n]]
expected=['src/experimental/cache/borrowed.rs','src/experimental/cache/tests.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/execution_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
assert changed==expected,changed
save('candidate-source-manifest.json',current)
assert sha(H/'baseline-original-cache-tests.rs')==original['src/experimental_swift_reactor/cache_tests.rs']
base=manifest(H/'baseline');assert [n for n in original if base[n]!=original[n]]==['src/experimental_swift_reactor/cache_tests.rs']
# Both independently constructed source copies include the exact same authored finite cost fixture.
needle='#[test]\nfn resident_index_finite_cost_fixture()'
assert (H/'baseline/src/experimental_swift_reactor/cache_tests.rs').read_text().split(needle)[1]==(H/'source/src/experimental_swift_reactor/cache_tests.rs').read_text().split(needle)[1]
final,receipt=command('qualified-all-release-002');assert read(final/'source-manifest.json')==current
assert len(receipt['executedBinaryIdentities'])>=30
summary=[tuple(map(int,x)) for x in re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (final/'stdout').read_text())]
assert tuple(map(sum,zip(*summary)))==(626,0,9)
for label in ('qualified-cache-debug-001','qualified-default-debug-001','qualified-compatibility-debug-001','qualified-clippy-001','qualified-format-check-001'):
 d,r=command(label);assert read(d/'source-manifest.json')==current,label
baseline,_=command('baseline-qualified-cost-001')
assert read(baseline/'source-manifest.json')==base
b=json.loads(re.search(r'RESIDENT_COST (\{[^\n]+\})',(baseline/'stdout').read_text())[1])
a=json.loads(re.search(r'RESIDENT_COST (\{[^\n]+\})',(final/'stdout').read_text())[1])
assert (b['constructorWork'],b['cold64Work'],b['hit256Work'],b['fixedReserved'])==(640,13127,8832,88536)
assert (a['constructorWork'],a['cold64Work'],a['hit256Work'],a['fixedReserved'])==(832,9671,2048,89376)
assert a['slots']==b['slots'] and a['residentBytes']==b['residentBytes']==2600 and a['hitAllocatorRequests']==b['hitAllocatorRequests']==0
frozen,_=command('baseline-qualified-frozen-001')
def trace(s):return s.split('test experimental::cache::tests::frozen_layout_and_trace_observation ... ',1)[1].split('\nok\n',1)[0]
assert trace((frozen/'stdout').read_text())==trace((final/'stdout').read_text())
lru,_=command('baseline-qualified-lru-001')
def lrus(s):
 result=[]
 for x in re.findall(r'ELISION (\{[^\n]+\})',s):
  d=json.loads(x)
  if d['case']=='lru':d.pop('timestamps');result.append(d)
 return result
assert len(lrus((final/'stdout').read_text()))==8
assert lrus((lru/'stdout').read_text())==lrus((final/'stdout').read_text())
bounds,_=command('baseline-qualified-bounds-001')
def bound(s):return list(map(int,re.search(r'bounds cleanup=(\d+) header=(\d+) construction=(\d+) operation=(\d+) foundation=(\d+)',s).groups()))
old_bound=bound((bounds/'stdout').read_text());new_bound=bound((final/'stdout').read_text())
assert new_bound==[62696,63072,57896,88294,269616]
assert 'legacy named simultaneous conservative=8032 unchanged_scratch=9312' in (final/'stdout').read_text()
assert 'full_chain_hit_work=260' in (final/'stdout').read_text()
for victim in (34,178,267):assert f'victim={victim} work_prefixes=130 cancellation_checks=82' in (final/'stdout').read_text()
# Qualify streams and owned group cleanup even for all retained rejected attempts.
commands={}
for p in sorted((H/'commands').glob('*/receipt.json')):
 r=read(p);assert all(r['streamEOF'].values()) and r['ownedGroupAbsent'];commands[str(p.parent.relative_to(H))]={'exitCode':r['exitCode'],'passed':r['passed'],'timedOut':r['timedOut'],'sourceManifestSHA256':r['sourceManifestSHA256'],'stdoutSHA256':r['stdoutSHA256'],'stderrSHA256':r['stderrSHA256']}
invalid={'commands/final-frozen-release-001':'Cargo reused baseline binary in formerly shared target; exit0 is not candidate qualification. Replaced by fresh candidate-only target qualified-all-release-002.'}
patch=[]
for n in changed:
 before=(H/'baseline-original-cache-tests.rs') if n=='src/experimental_swift_reactor/cache_tests.rs' else H/'baseline'/n
 patch.extend(difflib.unified_diff(before.read_text().splitlines(True),(H/'source'/n).read_text().splitlines(True),fromfile='vm/'+n,tofile='vm/'+n))
(H/'candidate.patch').write_text(''.join(patch))
comparison={'baselineCost':b,'candidateCost':a,'hitCreditReductionPercent':100*(b['hit256Work']-a['hit256Work'])/b['hit256Work'],'oldBounds':old_bound,'newBounds':new_bound,'frozenLiteralTraceIdentical':True,'lruComparisons':8,'frozenNamedHelperBytes':8032,'unchangedFrozenReservation':9312,'fixedReservationDelta':840,'exactIndexBytes':192,'headerReservationDelta':new_bound[1]-old_bound[1],'exhaustedCollisionMutationPrefixesPerVictim':130,'cancellationCheckpointsPerVictim':82,'deliberate64CollisionHitCredits':260,'cpuSpeedupClaimed':False}
save('comparison.json',comparison)
result={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'isolated-candidate-ready-for-independent-review','baselineClosure':C,'candidateClosure':closure(current),'sourceMembers':132,'changedFiles':changed,'commands':commands,'invalidatedSourceQualification':invalid,'allFeatureReleasePassed':626,'allFeatureReleaseIgnored':9,'allFeatureReleaseUnitPassed':404,'allFeatureReleaseDocPassed':11,'fullTargetExecuted':False,'fullTargetPassed':False,'nativeOrPhoneRun':False,'newDependencies':False,'productionLimitsChanged':False,'liveVmUnchanged':True,'gaAccepted':False,'independentlyReviewed':False,'patchSHA256':sha(H/'candidate.patch'),'comparisonSHA256':sha(H/'comparison.json')}
if '--seal' in sys.argv:
 cleanup=read(H/'cleanup.json');assert cleanup['ownedScratchRemoved'] and cleanup['holderCheckExitCode']==1 and cleanup['preservedOtherProjects']
 result['cleanupSHA256']=sha(H/'cleanup.json');result['reportSHA256']=sha(R/'docs/swift-cache-resident-index.md');save('receipt.json',result)
 files=[p for p in H.rglob('*') if p.is_file() and 'owned-scratch' not in p.parts and p.name!='seal.json']
 members={str(p.relative_to(H)):sha(p) for p in sorted(files)}
 save('seal.json',{'schema':1,'members':members,'membersSHA256':closure(members),'receiptSHA256':sha(H/'receipt.json'),'candidateClosure':closure(current),'rootSelectionSHA256':sha(R/'verification/swift-cache-resident-index-root-selection/selection.json')})
else:save('pre-cleanup-audit.json',result)
print(json.dumps({'verified':True,'changedFiles':len(changed),'candidateClosure':closure(current),'allFeatureReleasePassed':626,'fixedReserved':a['fixedReserved'],'hit256Credits':a['hit256Work'],'sealed':'--seal' in sys.argv}))
