#!/usr/bin/env python3
"""Bind independently reviewed sources, finite results and exact accounting."""
from pathlib import Path
import hashlib,json,re,subprocess,tarfile
H=Path(__file__).resolve().parent;ROOT=H.parent.parent;P=ROOT/'verification/swift-cache-retention-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=lambda p,d:p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
verification=subprocess.run(['python3',str(P/'verify.py')],cwd=ROOT,capture_output=True,text=True,check=True)
assert json.loads(verification.stdout)['liveVMStillMatchesOriginal']
source=json.loads((P/'candidate-manifest.json').read_text())
final=json.loads((H/'commands/independent-swift-corrected/source-manifest.json').read_text())
assert [n for n in source if source[n]!=final[n]]==['src/experimental/cache/tests.rs','src/experimental_swift_reactor/cache_tests.rs']
assert json.loads((H/'commands/independent-generic-corrected/source-manifest.json').read_text())==final
for name,count in [('independent-swift-corrected',5),('independent-generic-corrected',1)]:
    d=H/'commands'/name;r=json.loads((d/'receipt.json').read_text())
    assert r['exitCode']==0 and f'test result: ok. {count} passed; 0 failed; 0 ignored' in (d/'stdout').read_text()
    assert r['sourceManifestSHA256']==sha(d/'source-manifest.json')
    assert r['stdoutSHA256']==sha(d/'stdout') and r['stderrSHA256']==sha(d/'stderr')
with tarfile.open(P/'baseline-source.tar.gz','r:gz')as archive:baseline=archive.extractfile('src/experimental/cache/borrowed.rs').read().decode()
candidate=(P/'overlay/src/experimental/cache/borrowed.rs').read_text()
old=baseline[baseline.index('            let mut oldest: Option<usize> = None;'):baseline.index('            let victim = oldest')]
new=candidate[candidate.index('        let mut oldest: Option<usize> = None;'):candidate.index('        Ok(oldest)')]
normalized=lambda s:'\n'.join(line.strip()for line in s.replace('parts.slots','slots').splitlines()).strip()
assert normalized(old)==normalized(new)
swift=(P/'overlay/src/experimental_swift_reactor/cache.rs').read_text()
inventory=swift[swift.index('struct RetentionInventory {'):swift.index('\nfn protected_capacity')]
fields=re.findall(r'^    ([a-z_]+):',inventory,re.M)
assert len(fields)==40
write(H/'accounting-audit.json',{
  'schema':1,'status':'accepted-within-authored-named-object-model','productClosureUnchangedByReview':True,
  'frozenDefaultVictimMatchesOriginalLiteralLoop':True,'normalizedLiteralSHA256':hashlib.sha256(normalized(old).encode()).hexdigest(),
  'frozenDefaultHookEffects':{'HitPlanBytes':0,'prepareWork':0,'commitWork':0,'prepareMutation':False,'commitMutation':False},
  'fixedOwner':{'baselineSlotBytes':136,'candidateSlotBytes':144,'additionalBytesPerSlot':8,'slotsAtDefault':64,'additionalFixedBytes':512,'baselineFixedBytes':118240,'candidateFixedBytes':118752,'payloadReductionBytes':512,'preadmission':'complete entries*size_of::<SwiftSlot>() ticket before reserve::<SwiftSlot>()'},
  'operation':{'inventoryBytes':2672,'copies':3,'additionalReservedBytes':8016,'baselineBytes':92350,'candidateBytes':100366,'fields':fields,'noOwnerOrOtherPhaseReuse':True,'coverage':{'plans':['caller_plan','prepared_plan','returned_plan','commit_plan'],'promotion':['hit_slots','hit_index','hit_meter','capacity_slots','capacity_return','protected_capacity','protected_count','oldest_protected','hit_search','hit_candidate','hit_slot','hit_age','hit_older','hit_oldest_reborrow','hit_age_capture','hit_map_argument','hit_demote','hit_write_credits'],'publication':['commit_slots','commit_index','commit_demote','commit_victim'],'victim':['victim_slots','victim_selected','victim_meter','oldest','victim_search','victim_index','victim_slot','victim_rank','victim_older','victim_oldest_reborrow','victim_rank_capture','victim_map_argument','victim_return','victim_mapped']}},
  'additionalWork':{'constructor':'one per allocated resident slot','successfulMissPublication':'one resident tier reset','victimScan':'one per occupied unpinned unselected slot per planning scan','residentHit':'one tier read always; if probationary and protected capacity>0, also 2*slots + protected_count + 1 + (protected_count==protected_capacity) credits','precharge':'all reads before observation; all writes admitted before infallible commit','fourSlotPromotion':{'originalIndexedPath':8,'additionalTierWork':14,'total':22},'fiveSlotPromotionWithHeldHandle':{'originalIndexedPath':9,'additionalTierWork':16,'total':25},'protectedHitWithoutHeldHandle':9,'constructorAt64':4992},
  'constructionEnvelope':{'bytes':61880,'unchangedAuthoredNamedBindingShapes':True,'newAuthoredConstructorBinding':False,'limitation':'Existing unnamed SwiftSlot literal is passed to opaque std Vec::push. Payload grows by measured slot size; authored named-value model excludes opaque std-library internals and compiler-stack placement.'},
  'identityAndMutationAudit':{'immutableProofAndIRUntouchedByProductDiff':True,'residentIndexValidatesActualFunction':True,'hitPreparationReadOnly':True,'commitAfterLastFallibleOperation':True,'missPlanLeavesTiersUnchanged':True,'demotionDoesNotTouchPinsOrLiveness':True,'selectedVictimsExcludedFromLaterScans':True,'tiesUseFirstSlot':True,'protectedCapacityAtMost48':True},
  'context':{n:sha(ROOT/n)for n in ['docs/swift-cache-candidate3-acceptance.md','docs/swift-cache-foundation-phase-addendum.md','docs/swift-cache-stage-contract.md']},
  'logicalAccountingOnly':True,'compilerStackOrRSSMeasured':False,
})
write(H/'source-and-evidence-audit.json',{'schema':1,'candidateSealSHA256':sha(P/'seal.json'),'candidateManifestSHA256':sha(P/'candidate-manifest.json'),'baselineClosureSHA256':sha(P/'baseline-manifest.json'),'headAtAudit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'producerReadOnlyVerification':json.loads(verification.stdout),'independentFinalManifestSHA256':sha(H/'commands/independent-swift-corrected/source-manifest.json'),'reviewOnlyChangedExtractedFiles':['src/experimental/cache/tests.rs','src/experimental_swift_reactor/cache_tests.rs'],'producerCleanupReceipt':json.loads((P/'cleanup.json').read_text()),'producerRetiredPathsAbsent':all(not Path(p).exists()for p in json.loads((P/'cleanup.json').read_text())['removed']),'producerArchivesPreserved':all((P/n).is_file()for n in ['baseline-source.tar.gz','candidate-source.tar.gz'])})
print(json.dumps({'audited':True,'inventoryFields':len(fields),'sourceCount':len(source),'reviewOnlyTestChanges':True,'liveVMStillOriginal':True}))
