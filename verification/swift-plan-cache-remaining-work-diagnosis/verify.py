#!/usr/bin/env python3
"""Read-only sealed packet verification. No compiler, Wasm or native execution."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tarfile
H=Path(__file__).resolve().parent;R=H.parent.parent
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
seal=load(H/'seal.json')
members={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name!='seal.json'}
assert members==set(seal['files'])
for n,d in seal['files'].items():assert sha(H/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
binding=load(H/'input-bindings.json');archived=load(H/'archived-inputs.json')
assert set(binding)==set(archived)
for n,row in archived.items():
    assert row['observedBeforeFiniteSHA256']==binding[n] and sha(H/'inputs'/n)==row['archivedAtSealSHA256'],n
    if row['observedBeforeFiniteSHA256']!=row['archivedAtSealSHA256']:assert n in ('PLAN.md','STATUS.md'),n
baseline=load(H/'baseline-manifest.json');modified=load(H/'copied-source-manifest.json')
assert sha(H/'baseline-manifest.json')=='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
assert len(baseline)==len(modified)==132
assert load(H/'live-source-before.json')==load(H/'live-source-after.json')==baseline
changed=[n for n in baseline if baseline[n]!=modified[n]]
assert changed==['src/experimental/cache/borrowed.rs','src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs']
with tarfile.open(H/'isolated-source.tar.gz','r:gz') as t:
    assert sorted(t.getnames())==sorted(modified)
    copied={n:t.extractfile(n).read() for n in modified}
assert {n:hashlib.sha256(v).hexdigest() for n,v in copied.items()}==modified
for n in changed:assert sha(H/'originals'/n)==baseline[n]
patch=''.join(''.join(difflib.unified_diff((H/'originals'/n).read_text().splitlines(True),copied[n].decode().splitlines(True),fromfile='vm/'+n,tofile='isolated/'+n)) for n in changed)
assert patch==(H/'instrumentation.patch').read_text()
assert copied['src/experimental_swift_reactor/cache_tests.rs'].endswith((H/'finite-hook.rs').read_bytes())
command=load(H/'command.json');assert command['exitCode']==0 and not command['timedOut'] and not command['signalsSent']
assert command['stdoutSHA256']==sha(H/'finite.stdout') and command['stderrSHA256']==sha(H/'finite.stderr')
assert command['sourceManifestSHA256']==sha(H/'copied-source-manifest.json')
assert command['argv'][-5:]==['experimental_swift_reactor::cache_tests::remaining_plan_actual_cache_finite','--','--exact','--nocapture','--test-threads=1']
assert '--offline' in command['argv'] and command['environment']['CARGO_NET_OFFLINE']=='true'
out=(H/'finite.stdout').read_text();assert '1 passed; 0 failed; 0 ignored; 0 measured; 386 filtered out' in out
assert 'cold_prefixes=164 cancellations=3 guest_instructions=0 initializes=0 invokes=0 cleanup_zero=true' in out
rows=load(H/'finite-observations.json')['observations'];assert len(rows)==13
for row in rows:assert sum(row['credits'])==row['work'] and row['rejected'] is None
by={row['case']:row for row in rows}
assert by['flat_cold']['work']==164 and by['nested_cold']['work']==245
assert by['64_cycle_twice']['plans']==[64,0,0,64] and by['65_cycle_twice']['plans']==[65,0,65,65]
assert by['65_cycle_twice']['work']==25629 and by['65_cycle_twice']['completed']==130
assert by['evicted_IR_plan_hit']['work']==229 and by['evicted_IR_plan_hit']['credits'][6]==0
assert by['plan_conflict_546']['work']==by['plan_conflict_34']['work']==238
phases=load(H/'inputs/verification/swift-exact-reactor-after-plan-reuse/phase-counters.json')
cache=phases['snapshots'][2]['cache'];a=load(H/'arithmetic.json')
assert (cache['hits'],cache['misses'],cache['decodes'],cache['evictions'])==(537576,61628,61627,61564)
assert cache['decodes']-cache['evictions']==63 and cache['misses']-cache['evictions']==64
assert a['planningCreditsExact']==128*cache['misses']+64*cache['evictions']==11828480
assert a['planningEmptyAndCountWalksGrossCredits']==7888384 and a['planningVictimWalksCredits']==3940096
assert a['lookupCreditsLowerBound']==8*cache['hits']+4*cache['misses']==4547120
assert a['residentIndexMutationCreditsLowerBound']==9*cache['evictions']+8*cache['decodes']==1047092
assert a['residentIndexMutationCreditsUpperBound']==261*cache['evictions']+264*cache['decodes']==32337732
assert a['scanPlanBuildPolicyCreditsLowerBound']==10*cache['misses']+6*cache['decodes']==986042
assert a['scanPlanBuildPolicyCreditsUpperBound']==64000000-4928-11828480-4547120-1047092==46572380
assert cache['peak_resident_bytes']+cache['peak_construction_bytes']+cache['fixed_reserved']==2457776<16777216
module=load(H/'module-data-inspection.json');body=module['failureBody'];assert body['bodyOffset']==4153760 and body['bodyBytes']==811 and body['failureRelativeOffset']==278 and body['bytesFollowingFailureOffset']==532
cleanup=load(H/'cleanup.json');pre=load(H/'cleanup-preflight.json')
assert cleanup['ownedPathsAbsent'] and cleanup['liveSourceUnchanged'] and not cleanup['signalsSent'] and not cleanup['processGroupMembers']
assert not pre['groupMembers'] and all(q['exitCode']==1 and not q['stdout'] and not q['stderr'] for q in pre['holders'].values())
assert all(not (H/n).exists() for n in ('owned-source','owned-target','owned-tmp'))
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True,timeout=10)
assert not [line for line in ps.splitlines() if len(line.split())>=2 and int(line.split()[1])==command['processGroup']]
proposal=load(H/'observer-proposal.json');assert not proposal['fullTargetExecutedByThisPacket'] and not proposal['productionAlgorithmImplemented'] and not proposal['gaAccepted']
assert not a['currentPlanHitConflictCountsObserved'] and not a['currentRepeatedDecodeCountObserved']
receipt=load(H/'receipt.json');assert receipt['fullTargetAttempts']==0 and receipt['productionSourceChanged']==False and receipt['finiteTestsPassed']==1
print(json.dumps({'integrityVerified':True,'sealedMembers':len(members),'sourceFiles':132,'copiedChangedFiles':3,'finiteTestsPassed':1,'finiteObservations':13,'workPrefixes':164,'cancellationControls':3,'planningCreditsExact':11828480,'failureInsideBuildDecoder':True,'fullTargetAttempts':0,'cleanupComplete':True,'productionAlgorithmImplemented':False,'gaAccepted':False},sort_keys=True))
