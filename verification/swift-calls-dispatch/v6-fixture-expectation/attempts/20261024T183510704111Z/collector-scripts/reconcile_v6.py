"""Exact selected V5→V6 source, runtime MIR, finite and fixture boundary mapping."""
import collect as c
from inventory_v5 import display_index_free
import gzip,json,collections
parent=c.HERE.parent
old=c.read_json(parent/'inventory-v5.json');new=c.read_json(c.HERE/'inventory-v5.json');a={r['field']:r for r in old};b={r['field']:r for r in new};assert set(a)==set(b)and len(a)==89124
mapping=[]
for field in sorted(b):
 x=a[field];y=b[field]
 for key in set(x)|set(y):
  if key=='querySHA256':continue
  assert display_index_free(x.get(key))==display_index_free(y.get(key)),(field,key,'unexpected runtime accounting drift')
 mapping.append({'field':field,'config':y['config'],'oldQuerySHA256':x.get('querySHA256'),'finalQuerySHA256':y.get('querySHA256'),'oldClass':x['ownerClass'],'finalClass':y['ownerClass'],'method':y['method'],'actualIdentity':y.get('actualIdentity'),'body':y.get('body'),'position':y['position'],'oldAndFinalRoleDescriptorsEqual':True})
raw=c.enc(mapping);c.save(c.HERE/'v5-to-v6-all-roles.json.gz',gzip.compress(raw,mtime=0))
x=c.read_json(parent/'finite-numeric-positions-v5.json');y=c.read_json(c.HERE/'finite-numeric-positions-v5.json');ax={r['field']:r for r in x};by={r['field']:r for r in y};assert set(ax)==set(by)and len(ax)==1032
finite=[]
for field in sorted(by):
 o=ax[field];n=by[field]
 assert display_index_free({k:v for k,v in o.items()if k!='querySHA256'})==display_index_free({k:v for k,v in n.items()if k!='querySHA256'}),(field,'finite drift')
 finite.append({'field':field,'old':o,'final':n,'sameExactIdentityLayoutAndRole':True,'sameIntervalAndClass':True,'rootV6SelectionPending':True})
c.save(c.HERE/'v5-to-v6-finite-reconciliation.json',finite)
contexts=[];changed=[]
for cfg,q in c.read_json(c.HERE/'accounting-v5-summary.json')['queryBindings'].items():
 def records(base,q):
  raw=gzip.decompress((base/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256'];return [json.loads(line)for line in raw.decode().splitlines()]
 previous=c.read_json(parent/f'exact-query-{cfg}.json');o=records(parent,previous);n=records(c.HERE,q)
 runtime=lambda rs:{(r['path'],r['promoted']):r for r in rs if r['kind']=='body'}
 ro=runtime(o);rn=runtime(n);assert set(ro)==set(rn)
 for key in ro:assert display_index_free(ro[key])==display_index_free(rn[key]),(cfg,key,'unexpected runtime body drift')
 po={r['path']:r for r in o if r['kind']=='partition-body'};pn={r['path']:r for r in n if r['kind']=='partition-body'};assert set(po)==set(pn)
 diff=[]
 for key in po:
  if po[key]['mir']==pn[key]['mir']:continue
  assert '::tests::af22_frozen_accounting_and_value_phase_reservations_stay_distinct'in key,(cfg,key,'unselected fixture change')
  assert po[key]['partition']==pn[key]['partition']and 'fixture'in pn[key]['partition'],(cfg,key,pn[key]['partition'])
  row={'config':cfg,'body':key,'oldDefPathHash':po[key]['defPathHash'],'finalDefPathHash':pn[key]['defPathHash'],'oldMIRSHA256':c.sha(po[key]['mir'].encode()),'finalMIRSHA256':c.sha(pn[key]['mir'].encode()),'partition':pn[key]['partition'],'oldSpan':po[key]['span'],'finalSpan':pn[key]['span']};diff.append(row);changed.append(row)
 assert bool(diff)==cfg.endswith('-unit')
 # Complete compiler callee inventory emitted from each admitted runtime body.
 calls=[r for r in n if r['kind']=='FnDef'];assert not any('::tests::af22_'in r['calleePath']for r in calls)
 contexts.append({'config':cfg,'oldQuery':previous,'finalQuery':q,'allSelectedRuntimeBodiesByteEqual':True,'runtimeBodies':len(ro),'fixtureOnlyChanges':diff,'runtimeFnDefOperands':len(calls),'noRuntimeCallToCorrectedFixture':True})
for name in ['positive-positions-v5.rs','kind-positions-v5.rs']:
 assert (c.HERE/name).read_bytes()==(parent/name).read_bytes(),name
c.save(c.HERE/'final-generated-declarations-unchanged.json',{'parentSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'generatedDeclarationsByteEqual':{name:c.sha((c.HERE/name).read_bytes())for name in ['positive-positions-v5.rs','kind-positions-v5.rs']},'candidateDeclarationsNeverReinstalledOrChanged':True})
c.save(c.HERE/'v5-to-v6-summary.json',{'oldSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'roles':len(b),'finiteRoles':len(finite),'phaseCounts':dict(collections.Counter(r['ownerClass']for r in new)),'allRoleDescriptorsAndNumericIntervalsUnchanged':True,'allRuntimeMIRByteEqual':True,'contexts':contexts,'fixtureChangedBodies':changed,'completeRoleMap':{'path':'v5-to-v6-all-roles.json.gz','logicalSHA256':c.sha(raw)},'finiteMap':'v5-to-v6-finite-reconciliation.json','fixtureAdmissionBoundary':'Full compiler partition and all runtime FnDef operands exclude the one corrected test fixture; same existing test harness boundary, no product body/closure/hook added.','independentReviewPending':True,'runtimeQualified':False})
print('V5→V6 exact89124roles/1032finite/runtimeMIR unchanged; only4unit fixture MIR bodies changed')
