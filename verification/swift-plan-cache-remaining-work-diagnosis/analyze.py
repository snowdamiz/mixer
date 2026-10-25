#!/usr/bin/env python3
"""Finite arithmetic and section/body data inspection, never Wasm execution."""
from pathlib import Path
import hashlib,json
H=Path(__file__).resolve().parent;R=H.parent.parent
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,v):(H/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
current=R/'verification/swift-exact-reactor-after-plan-reuse'
phases=load(current/'phase-counters.json');constructed,initialized,terminal=phases['snapshots'];c=terminal['cache']
failure=load(current/'target-once-result.json')['firstFailure']['payload'];f=failure['at_failure']
assert (c['hits'],c['misses'],c['decodes'],c['evictions'])==(537576,61628,61627,61564)
assert terminal['live']['cache_entries']['current']==63 and f['live']['cache_entries']['current']==64
assert failure['resource']=='CacheWork' and failure['function']==23610 and failure['offset']==4154038
assert c['peak_resident_bytes']+c['peak_construction_bytes']+c['fixed_reserved']==2457776<16*1024*1024
assert c['evictions']==c['misses']-64 and c['decodes']-c['evictions']==63
HITS,MISSES,DECODED,EVICTED=[c[k] for k in ('hits','misses','decodes','evictions')];N=HITS+MISSES
planning=128*MISSES+64*EVICTED
lookup_min=8*HITS+4*MISSES
maintenance_min=9*EVICTED+8*DECODED
maintenance_max=261*EVICTED+264*DECODED
decoder_max=64000000-4928-planning-lookup_min-maintenance_min
decoder_min=10*MISSES+6*DECODED
# Inspect section lengths only, as data. No instantiation, Initialize or invoke.
module=R/'compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm'
b=module.read_bytes();assert len(b)==53777114 and b[:8]==b'\0asm\1\0\0\0'
assert sha(module)=='24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994'
def uint(p):
    v=0
    for shift in range(0,35,7):
        x=b[p];p+=1;v|=(x&127)<<shift
        if x<128:return v,p
    raise ValueError('invalid bounded u32')
p=8;body=None
while p<len(b):
    tag=b[p];size,q=uint(p+1);end=q+size;assert end<=len(b)
    if tag==10:
        count,q=uint(q);assert count==79832
        for index in range(count):
            size,start=uint(q);q=start+size;assert q<=end
            if index+34==failure['function']:
                body={'function':index+34,'bodyOffset':start,'bodyBytes':size,'lastBodyOffset':q-1,
                      'failureOffset':failure['offset'],'failureRelativeOffset':failure['offset']-start,
                      'bytesFollowingFailureOffset':q-1-failure['offset']}
        assert q==end
    p=end
assert p==len(b) and body=={'function':23610,'bodyOffset':4153760,'bodyBytes':811,'lastBodyOffset':4154570,'failureOffset':4154038,'failureRelativeOffset':278,'bytesFollowingFailureOffset':532}
save('module-data-inspection.json',{'module':str(module.relative_to(R)),'bytes':len(b),'sha256':sha(module),'definedBodies':79832,'imports':34,'scope':'section/body extents as data only; not opcode validation or execution authority','failureBody':body,'guestExecution':False})
rows=load(H/'finite-observations.json')['observations'];assert len(rows)==13
for row in rows:assert sum(row['credits'])==row['work']
by={row['case']:row for row in rows}
assert by['flat_cold']['work']==164 and by['nested_cold']['work']==245
assert by['64_cycle_twice']['work']==11015 and by['65_cycle_twice']['work']==25629
assert by['evicted_IR_plan_hit']['plans']==[0,0,1,0] and by['evicted_IR_plan_hit']['credits'][6]==0
assert by['plan_conflict_34']['plans']==by['plan_conflict_546']['plans']==[0,1,0,1]
assert by['plan_conflict_34']['credits'][6]==4 and by['plan_conflict_34']['work']==238
assert by['evicted_IR_plan_hit']['work']==229
# Complete valid body cost formulas, excluding resident lookup/planning/index.
def scan(B,I,P=0,G=0,L=0,C=0,A=0,T=0):return 1+P+B+G+L+I+2*C+A+T
def build(B,I,P=0,G=0,L=0,C=0,A=0,T=0):return 1+P+B+G+2*L+2*I+3*C+2*A+2*T
assert (scan(2,1),build(2,1))==(4,5)
assert (scan(17,12,C=3,A=1),build(17,12,C=3,A=1))==(37,53)
assert 4+128+8+(14+scan(2,1))+(1+build(2,1))==by['flat_cold']['work']
assert 4+192+9+8+10+(1+build(2,1))==by['evicted_IR_plan_hit']['work']
save('arithmetic.json',{
 'schema':1,'scope':'source-derived successful-credit bounds, not measured target semantic attribution or CPU time',
 'sourceRevisionContext':'6403eea98031207f6e40a72b55dfd3bd4e7e6ec2','sourceClosure':'16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd',
 'fullResultSealSHA256':sha(current/'result-seal.json'),'authoritativeCounters':'terminal post-drain; do not substitute for causal checkpoint',
 'counters':{'hits':HITS,'misses':MISSES,'completedDecodes':DECODED,'evictions':EVICTED,'terminalResidents':63,'causalFailureLiveCacheEntries':64},
 'countedPins':N,'hitRatio':HITS/N,'cacheWork':64000000,'constructorCredits':4928,
 'planningCreditsExact':planning,'planningFraction':planning/64000000,
 'planningEmptyAndCountWalksGrossCredits':128*MISSES,'planningVictimWalksCredits':64*EVICTED,
 'planningEmptyAndCountWalksGrossFraction':128*MISSES/64000000,
 'lookupCreditsLowerBound':lookup_min,'lookupUnclampedUpperBound':(3+64+4*64)*N,
 'freePinCreditsLowerBound':N,'freePinCreditsUpperBoundSelectedCapacity':64*N,
 'freePinCreditsUpperBoundObservedActivePeak':38*N,
 'residentLookupHashAndChainCreditsLowerBound':2*N+4*HITS,
 'residentIndexMutationCreditsLowerBound':maintenance_min,'residentIndexMutationCreditsUpperBound':maintenance_max,
 'scanPlanBuildPolicyCreditsLowerBound':decoder_min,'scanPlanBuildPolicyCreditsUpperBound':decoder_max,
 'sumOfSeparateCachePeaks':2457776,'cacheLimit':16*1024*1024,
 'lastMissReachedCompletePlanningAndOneCommittedEviction':True,'lastMissFailedInsideBuildDecoder':True,
 'currentPlanHitConflictCountsObserved':False,'currentRepeatedDecodeCountObserved':False,
 'completedDecodeExcessOverDefinedBodies':max(0,DECODED-79832),
 'priorInstructionCheckpoint':15753076,'currentInstructionCheckpoint':23358291,
 'instructionCheckpointRatio':23358291/15753076,'ratioIsCPUSpeedup':False,
 'completeBodyFormulas':{'S':'1+P+B+G+L+I+2C+A+T','K':'1+P+B+G+2L+2I+3C+2A+2T','emptyPlanScanIncludingPolicy':'14+S','conflictingPlanScanIncludingPolicy':'15+S','planHitIncludingPolicy':10,'buildIncludingPolicy':'1+K'},
 'initializeToCorpus1':{'completedDecodes':DECODED-initialized['cache']['decodes'],'cacheCredits':64000000-initialized['work']['cache_work']},
 'productionAlgorithmImplemented':False,'fullTargetRetried':False,'gaAccepted':False})
print(json.dumps({'planningCreditsExact':planning,'planningFraction':planning/64000000,'decoderBound':[decoder_min,decoder_max],'failureBody':body,'finiteObservations':len(rows)}))
