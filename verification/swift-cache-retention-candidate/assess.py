#!/usr/bin/env python3
"""Derive finite measurements from retained stdout; never execute a reactor."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def stdout(name):return (H/'commands'/name/'stdout').read_text()
def rows(name,tag):
    return [json.loads(line.split(tag,1)[1]) for line in stdout(name).splitlines() if tag in line]
def normalized(name):
    return re.sub(r'finished in [0-9.]+s','finished in <elapsed>s',stdout(name))
baseline='baseline-cache-release';candidate='candidate-cache-release-final'
traces={label:{x['case']:x for x in rows(command,'RETENTION_TRACE ')} for label,command in [('baseline',baseline),('candidate',candidate)]}
shapes={label:rows(command,'RETENTION_SHAPE ')[0] for label,command in [('baseline',baseline),('candidate',candidate)]}
hits={label:rows(command,'RETENTION_HIT ')[0] for label,command in [('baseline',baseline),('candidate',candidate)]}
resident={label:rows(command,'RESIDENT_COST ')[0] for label,command in [('baseline',baseline),('candidate',candidate)]}
assert shapes['candidate']['fixedBytes']-shapes['baseline']['fixedBytes']==512
assert shapes['baseline']['payloadBytes']-shapes['candidate']['payloadBytes']==512
assert shapes['candidate']['operationBytes']-shapes['baseline']['operationBytes']==3*2672
assert shapes['candidate']['allocations']==shapes['baseline']['allocations']==5
assert hits['baseline']=={'promotionWork':8,'protectedWork':8,'allocations':0}
assert hits['candidate']=={'promotionWork':22,'protectedWork':9,'allocations':0}
pairs=[('baseline-generic-default','candidate-generic-default-final'),('baseline-generic-integration','candidate-generic-integration-final')]
generic=[]
for a,b in pairs:
    assert normalized(a)==normalized(b),(a,b)
    generic.append({'baseline':a,'candidate':b,'normalizedStdoutSHA256':sha(normalized(a).encode()),'equal':True,'normalization':'elapsed seconds only'})
for n in [baseline,candidate,*[v for pair in pairs for v in pair]]:
    assert json.loads((H/'commands'/n/'receipt.json').read_text())['exitCode']==0
hot='hot16_scan128_four_rounds';cyclic='cyclic65_three_rounds'
bhot=traces['baseline'][hot];chot=traces['candidate'][hot]
bcycle=traces['baseline'][cyclic];ccycle=traces['candidate'][cyclic]
summary={'schema':1,'status':'isolated-finite-candidate-awaiting-independent-review','sourceRevision':'7b6048642b42e4900cccff4e14aa0fe8949ab35e','baselineClosureSHA256':'16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd','selectedFinalCommands':[baseline,candidate,*[v for pair in pairs for v in pair]],'passedMethods':{'baselineSwiftCache':42,'candidateSwiftCache':47,'baselineGenericUnit':5,'candidateGenericUnit':5,'baselineGenericIntegrationAndAllocation':10,'candidateGenericIntegrationAndAllocation':10},'traces':traces,'shapes':shapes,'singleHitCosts':hits,'residentIndexFixture':resident,'genericOutputComparisons':generic,'syntheticHotScan':{'fewerDecodes':bhot['decodes']-chot['decodes'],'fewerTraceCredits':bhot['traceWork']-chot['traceWork'],'traceCreditReductionPercent':100*(bhot['traceWork']-chot['traceWork'])/bhot['traceWork']},'cyclic65':{'noDecodeReduction':bcycle['decodes']==ccycle['decodes'],'additionalTraceCredits':ccycle['traceWork']-bcycle['traceWork'],'traceCreditIncreasePercent':100*(ccycle['traceWork']-bcycle['traceWork'])/bcycle['traceWork']},'cyclic64ResidentHits':{'baselineCredits':resident['baseline']['hit256Work'],'candidateCredits':resident['candidate']['hit256Work'],'ratio':resident['candidate']['hit256Work']/resident['baseline']['hit256Work'],'explanation':'Protected cap48 plus cyclic64 resident hits causes repeated bounded promotion scans; no redecoding is needed to incur this regression.'},'boundaries':{'promotionWorkPrefixes':22,'promotionCancellationChecks':20,'replacementWorkPrefixes':122,'replacementCancellationChecks':62,'capacityCases':8,'equalAgeRebases':2,'memoryEvictions':3,'allPinnedRetentionUnchanged':True,'cleanupReservationsPinsEntriesTicketsZero':True},'originalBudgetsUnchanged':True,'newDependencies':[],'fullSwiftReactorAttempts':0,'nativeAttempts':0,'actualWorkloadBenefitProven':False,'liveIntegrationSelected':False,'gaAccepted':False,'limitations':['Cumulative attribution does not identify hot function identities or establish benefit from this policy.','Synthetic scan improvement coexists with cyclic65 overhead and large cyclic64 resident-hit overhead.','Protected capacity is based on allocated slot count; memory pressure can still require protected evictions.','Host logical named-object accounting is not an RSS or compiler-stack measurement.','Original failed full diagnostic remains authoritative; physical phones, signing, published-package FieldLog and GA are unqualified.']}
(H/'result-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
print(json.dumps({'passed':summary['passedMethods'],'genericOutputsEqual':True,'syntheticReductionPercent':summary['syntheticHotScan']['traceCreditReductionPercent'],'cyclic65IncreasePercent':summary['cyclic65']['traceCreditIncreasePercent'],'cyclic64HitRatio':summary['cyclic64ResidentHits']['ratio']}))
