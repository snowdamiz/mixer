"""Exact selected V5→V7 source, runtime MIR, finite and fixture boundary mapping."""
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
raw=c.enc(mapping);c.save(c.HERE/'v5-to-v7-all-roles.json.gz',gzip.compress(raw,mtime=0))
x=c.read_json(parent/'finite-numeric-positions-v5.json');y=c.read_json(c.HERE/'finite-numeric-positions-v5.json');ax={r['field']:r for r in x};by={r['field']:r for r in y};assert set(ax)==set(by)and len(ax)==1032
finite=[]
for field in sorted(by):
 o=ax[field];n=by[field]
 assert display_index_free({k:v for k,v in o.items()if k!='querySHA256'})==display_index_free({k:v for k,v in n.items()if k!='querySHA256'}),(field,'finite drift')
 finite.append({'field':field,'old':o,'final':n,'sameExactIdentityLayoutAndRole':True,'sameIntervalAndClass':True,'rootV6SelectionPending':True})
c.save(c.HERE/'v5-to-v7-finite-reconciliation.json',finite)

import re,difflib
SELECTED=[
 'experimental_swift_reactor::execution::frame_operations::tests::af22_frozen_accounting_and_value_phase_reservations_stay_distinct',
 'experimental_swift_reactor::execution::frame_operations::memory_operations::tests::mm16_accounting_restore',
 'experimental_swift_reactor::execution::frame_operations::bulk_memory_operations::tests::bm16_accounting_restore']
contexts=[];changed=[]
def rawquery(base,q):
 raw=gzip.decompress((base/q['attempt']/'exact-layouts.jsonl.gz').read_bytes());assert c.sha(raw)==q['sha256'];return [json.loads(line)for line in raw.decode().splitlines()]
def full_mir(base,pointer):
 arts=[a for a in c.read_json(base/pointer['attempt']/'artifacts.json')if a['path'].endswith('.mir.gz')];assert len(arts)==1
 raw=gzip.decompress((base/pointer['attempt']/arts[0]['path']).read_bytes());assert c.sha(raw)==arts[0]['sha256'];return raw.decode(),arts[0]
def by_name(text):
 out={}
 for m in re.finditer(r'(?m)^fn ([^\n]*?)\(',text):
  at=m.start();end=text.index('\n}\n',at)+3;out.setdefault(m[1],[]).append(text[at:end])
 return out
for cfg,q in c.read_json(c.HERE/'accounting-v5-summary.json')['queryBindings'].items():
 previous=c.read_json(parent/f'exact-query-{cfg}.json');o=rawquery(parent,previous);n=rawquery(c.HERE,q)
 runtime=lambda rs:{(r['path'],r['promoted']):r for r in rs if r['kind']=='body'}
 ro=runtime(o);rn=runtime(n);assert ro==rn,(cfg,'unexpected selected runtime MIR/body drift; no normalization allowed')
 oldtext,oldart=full_mir(parent,previous);newtext,newart=full_mir(c.HERE,q);on=by_name(oldtext);nn=by_name(newtext)
 po={r['defPathHash']:r for r in o if r['kind']=='partition-body'};pn={r['defPathHash']:r for r in n if r['kind']=='partition-body'};assert len(pn)==sum(r['kind']=='partition-body'for r in n)and set(po)<=set(pn)
 for key in po:assert po[key]==pn[key],(cfg,key,'prior selected partition drift')
 additional=[];diff=[]
 for key in sorted(set(pn)-set(po)):
  r=pn[key];assert r['partition']=='prior-selected-test-body-preserve-original-classification'
  record={'defPathHash':key,'path':r['path'],'defKind':r['defKind'],'actualSpan':r['span'],'actualMIRSHA256':c.sha(r['mir'].encode()),'originalClassificationRetained':True,'newAccountingCredit':False}
  if r['defKind']in ['Fn','AssocFn','Closure']:
   header=r['mir'].splitlines()[0];name=header[3:header.index('(')];assert name in on and name in nn;assert sum(body==r['mir']for body in nn[name])==1
   old_candidates=[body for body in on[name]if body.splitlines()[0]==header]
   if not old_candidates:
    assert any(r['path']==x or r['path'].startswith(x+'::')for x in SELECTED);old_candidates=on[name]
   assert len(old_candidates)==1,(cfg,r['path'],'ambiguous old fixture header');prior_body=old_candidates[0];actual=r['mir']
   record['oldEmittedMIRSHA256']=c.sha(prior_body.encode());record['byteEqual']=prior_body==actual
   if not record['byteEqual']:
    # Changes are retained literally for the selected test family; no runtime
    # or prior helper identity/layout is normalized or waived.
    family=next((x for x in SELECTED if r['path']==x or r['path'].startswith(x+'::')),None);assert family is not None,(cfg,r['path'],'unselected original helper drift')
    record['exactSelectedFixtureFamily']=family
    path=c.HERE/'fixture-mir-diffs'/cfg/(c.sha(key.encode())[:16]+'.diff');c.save(path,''.join(difflib.unified_diff(prior_body.splitlines(True),actual.splitlines(True))).encode());record['rawDiff']=str(path.relative_to(c.HERE));diff.append(record);changed.append(dict(config=cfg,**record))
  additional.append(record)
 assert bool(diff)==cfg.endswith('-unit')and (not diff or {r['exactSelectedFixtureFamily']for r in diff}==set(SELECTED))
 graph=[r for r in n if r['kind']=='scope-graph-body'];uses=[r for r in n if r['kind']=='scope-graph-function-item-use'];g={(r['defPathHash'],r['promoted']):r for r in graph};assert len(g)==len(graph)and all((r['bodyDefPathHash'],r['promoted'])in g for r in uses)
 fixture_graph=[];fids=[]
 for path in SELECTED:
  fs=[r for r in pn.values()if r['path']==path and r['defKind']=='Fn'];assert len(fs)==int(cfg.endswith('-unit'))
  for f in fs:
   fids.append(f['defPathHash']);incoming=[r for r in uses if r['calleeDefPathHash']==f['defPathHash']]
   allowed={path+'::{closure#0}'}
   if path==SELECTED[0]:allowed.add('experimental_swift_reactor::execution::frame_operations::tests::control_tests::sc11_completion_accounting')
   assert {r['path']for r in incoming}==allowed,(cfg,path,incoming)
   owners=[]
   for edge in incoming:
    owner=g[(edge['bodyDefPathHash'],edge['promoted'])];owners.append({'actualEdge':edge,'actualOwner':owner})
   fixture_graph.append({'fixture':f,'incomingActualFunctionItemUses':owners,'sourceBoundary':'root-selected exact original test expression; ingress from generated test wrapper and af22 unchanged sc11 fixture, never from admitted product roots'})
 calls=[r for r in n if r['kind']=='FnDef'];assert not any(r['calleeDefPathHash']in fids for r in calls)
 c.save(c.HERE/f'v7-original-test-partition-{cfg}.json',{'query':q,'allExistingClassificationsPreserved':True,'additionalActualRecords':additional,'changedSelectedFamilies':diff,'fullOldMIR':oldart,'fullFinalMIR':newart,'actualWholeCrateGraphBodies':len(graph),'actualWholeCrateFunctionItemUses':len(uses),'actualPromotedGraphBodies':sum(r['promoted']is not None for r in graph),'exactFixtureIncomingGraph':fixture_graph,'noNamespaceExemption':True})
 contexts.append({'config':cfg,'oldQuery':previous,'finalQuery':q,'allSelectedRuntimeBodiesByteEqual':True,'runtimeBodies':len(ro),'changedSelectedFixtureBodies':len(diff),'wholeCrateGraphBodies':len(graph),'wholeCrateFunctionItemUses':len(uses),'runtimeFnDefOperands':len(calls),'noRuntimeCallToCorrectedFixtures':True})
for name in ['positive-positions-v5.rs','kind-positions-v5.rs']:
 assert (c.HERE/name).read_bytes()==(parent/name).read_bytes(),name
c.save(c.HERE/'final-generated-declarations-unchanged.json',{'parentSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'generatedDeclarationsByteEqual':{name:c.sha((c.HERE/name).read_bytes())for name in ['positive-positions-v5.rs','kind-positions-v5.rs']},'candidateDeclarationsNeverReinstalledOrChanged':True})
c.save(c.HERE/'v5-to-v7-summary.json',{'oldSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'roles':len(b),'finiteRoles':len(finite),'phaseCounts':dict(collections.Counter(r['ownerClass']for r in new)),'allRoleDescriptorsAndNumericIntervalsUnchanged':True,'allSelectedRuntimeMIRByteEqual':True,'contexts':contexts,'changedSelectedFixtureBodies':changed,'completeRoleMap':'v5-to-v7-all-roles.json.gz','finiteMap':'v5-to-v7-finite-reconciliation.json','fixtureAdmissionBoundary':'Actual compiler identities/MIR preserve every prior helper/TLS classification. Only the three root-selected test expression families change, with full raw diffs. Whole-crate function-item uses include promoted bodies and exact test-harness/sc11 ingress. All selected runtime FnDef operands exclude corrected fixtures. No namespace exemption or new accounting credit.','independentReviewPending':True,'runtimeQualified':False})
print('V5→V7 exact89124roles/1032finite/selectedruntimeMIR unchanged; selected fixture families explicitly reconciled')
