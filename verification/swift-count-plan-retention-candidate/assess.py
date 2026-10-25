#!/usr/bin/env python3
"""Strictly derive the finite decision from retained raw engine outputs."""
import ast,hashlib,json,pathlib,re
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def raw(name):return (OUT/'commands'/name/'stdout').read_text()
def lines(s,prefix):return re.findall(re.escape(prefix)+r'[^\n]*',s)
def jsons(s,prefix):return [json.loads(x[len(prefix):]) for x in lines(s,prefix)]
def traces(s):return {r['case']:r for r in jsons(s,'COST_TRACE ')}
b,c=raw('baseline-expanded-2'),raw('candidate-expanded')
generic_b,generic_c=lines(b,'GENERIC_'),lines(c,'GENERIC_')
assert generic_b==generic_c
write(OUT/'generic-differential.json',{'recordsCompared':len(generic_b),'baselineAndCandidateExactlyEqual':True,
  'baselineSHA256':sha(('\n'.join(generic_b)+'\n').encode()),'candidateSHA256':sha(('\n'.join(generic_c)+'\n').encode()),
  'layout':jsons(b,'GENERIC_LAYOUT ')[0], 'scope':'Actual FrozenMode owner/fields/meter/scratch/associated-scan layouts, success IR/state/nonce/pins/statistics, every finite miss work prefix, cancellation'})
hit=[]
for text in [b,c]:
    hit.append([dict((k,int(v)) for k,v in re.findall(r'(\w+): (\d+)',l)) for l in lines(text,'COUNT_HIT_CHECKPOINT ')])
assert len(hit[0])==len(hit[1])==11
ledger=[]
for i,(old,new) in enumerate(zip(*hit)):
    for key in ['work','cache','tickets','pins','entries','step']:assert old[key]==new[key]
    delta=0 if i==0 else 20472
    assert new['construction']-old['construction']==new['combined']-old['combined']==delta
    ledger.append({'checkpoint':i,'baseline':old,'candidate':new,'reservationDelta':delta})
assert jsons(b,'COUNT_HIT ')[0]['work256']==jsons(c,'COUNT_HIT ')[0]['work256']==2048
write(OUT/'hit-ledger-differential.json',{'workParity':True,'allocationRequestAndByteParity':True,'hitByteParity':False,
  'baseline256':jsons(b,'COUNT_HIT ')[0],'candidate256':jsons(c,'COUNT_HIT ')[0], 'checkpoints':ledger})
old_shape=ast.literal_eval(lines(b,'COUNT_SHAPE ')[0][len('COUNT_SHAPE '):])
new_shape=ast.literal_eval(lines(c,'COUNT_SHAPE ')[0][len('COUNT_SHAPE '):])
assert new_shape[9]-old_shape[9]==20472
assert old_shape[:9]+old_shape[10:]==new_shape[:9]+new_shape[10:]
fields=jsons(c,'COUNT_FIELD ');assert len(fields)==25
spans=sorted((f['offset'],f['offset']+f['bytes']) for f in fields)
for previous,next_span in zip(spans,spans[1:]):assert previous[1]<=next_span[0]
assert sum(f['bytes'] for f in fields)==6820 and spans[-1][1]==6820
write(OUT/'inventory-fields.json',{'outcomeBytes':32,'resultBytes':1096,'inventoryBytes':6824,'namedFieldBytes':6820,'paddingBytes':4,
  'copies':3,'dedicatedBytes':20472,'DeltaExisting':0,'oldShape':old_shape,'newShape':new_shape,'fields':fields,
  'shapeOrder':['PlanInventory','OperationScalarInventory','OperationBorrowChainInventory','ConstructionScalarInventory',
  'ConstructionBorrowChainInventory','SwiftSlot','SwiftResident','header','construction','operation','cleanup','Result<Counts,SwiftRunFailure>']})
baseline=traces(raw('baseline-common'));candidate=traces(raw('candidate-common'));assert len(baseline)==len(candidate)==6
historical_path=ROOT/'verification/swift-cost-retention-candidate/commands/baseline-common/stdout'
historical=traces(historical_path.read_text());assert baseline==historical
rows=[]
for case,old in baseline.items():
    new=candidate[case];warm=0 if case=='cyclic65_three_rounds' else 16
    for metric in ['fixedBytes','peakTickets','instructions']:assert old[metric]==new[metric]
    rows.append({'case':case,'baseline':old,'candidate':new,'warmupDecodes':warm,
      'intervalBaselineDecodes':old['decodes']-warm,'intervalCandidateDecodes':new['decodes']-warm,
      'deltaWork':new['traceWork']-old['traceWork'],'deltaDecodes':new['decodes']-old['decodes'],
      'workImproves':new['traceWork']<old['traceWork']})
assert sum(r['workImproves'] for r in rows)==3
before=OUT/'.scratch/baseline/src/experimental/cache/borrowed.rs'
after=OUT/'.scratch/candidate/src/experimental/cache/borrowed.rs'
old=before.read_text();new=after.read_text()
old_tail=old[old.index('    let slot = &mut parts.slots[index];'):old.rfind('\n}')]
new_branch=new[new.index('fn pin_acquired<M: CacheMode>'):]
literal_tail='\n'.join('    '+l for l in old_tail.splitlines())
assert literal_tail in new_branch
assert new_branch.index(literal_tail)<new_branch.index('    } else {')
plan=(OUT/'proposed-seam.md').read_bytes();selection=json.loads((OUT/'root-selection.json').read_bytes())
assert selection['proposalSHA256']==sha(plan)
for old_prefix,new_prefix in zip(lines(b,'COUNT_PREFIX '),lines(c,'COUNT_PREFIX ')):
    amount=lambda x:int(re.search(r'work=(\d+)',x)[1])
    assert amount(new_prefix)-amount(old_prefix)==57
summary={'status':'rejected-for-integration-and-full-target','reason':'Three of six actual finite work traces regress; unchanged fixed combined-byte limits reject operation preparation earlier; phase decode regressions remain.',
  'policyRetuned':False,'rootSelectedDebits':[41,16],'successfulMissSourcePolicyCredits':57,
  'originalFrozenModelEstimateUnchanged':8,'actualEngineRows':rows,
  'historicalBaselineExactlyReproduced':{'path':str(historical_path.relative_to(ROOT)),'sha256':sha(historical_path.read_bytes())},
  'hitWorkParity':True,'hitAllocationParity':True,'hitByteParity':False,'operationReservationDelta':20472,
  'originalHitTailLiterallyPreserved':True,'genericDifferentialRecords':len(generic_b),
  'newMethods':{'baseline':8,'candidate':9},'originalSwiftMethods':{'baselinePassed':39,'candidatePassed':37,'candidateFailed':2},
  'originalCandidateFailures':['plan_reuse_observation expected baseline288 decodes, observed225','reset_elision_observation_fixture expected current timestamp, observed cold zero'],
  'preservedFirstFailures':['candidate-original-swift: existing cfg(test) helper required new scan-result adapter', 'baseline-expanded: new probe used nonexistent AllPinned failure-kind name'],
  'realOwnershipControls':{'capacities':65,'oracleTransitionsPerMode':24576,'allMissWorkPrefixes':lines(c,'COUNT_PREFIX '),
     'threeVictimPrefixes':lines(c,'COUNT_MULTIVICTIM '),'memoryAdmission':lines(c,'COUNT_ADMISSION '),
     'phase':lines(c,'COUNT_PHASE '),'collisionPhase':lines(c,'COUNT_COLLISION_PHASE ')},
  'scope':'Selected finite Rust host tests only. No target forecast, live integration, full target, native/UI/capture, signing/store/provider, FieldLog published package or GA evidence.'}
write(OUT/'comparison.json',summary)
print(json.dumps({'decision':summary['status'],'genericRecords':len(generic_b),'sixTraces':len(rows),'workRegressions':3,'hitWorkParity':True,'hitByteParity':False,'DeltaExisting':0},sort_keys=True))
