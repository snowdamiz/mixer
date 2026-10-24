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
 def full_mir(base,pointer):
  arts=[a for a in c.read_json(base/pointer['attempt']/'artifacts.json')if a['path'].endswith('.mir.gz')];assert len(arts)==1
  raw=gzip.decompress((base/pointer['attempt']/arts[0]['path']).read_bytes());assert c.sha(raw)==arts[0]['sha256'];return raw.decode(),arts[0]
 oldtext,oldart=full_mir(parent,previous);newtext,newart=full_mir(c.HERE,q)
 def emitted(text,header):
  at=text.index(header+'\n');end=text.index('\n}\n',at)+3;return text[at:end]
 po={r['defPathHash']:r for r in o if r['kind']=='partition-body'};pn={r['defPathHash']:r for r in n if r['kind']=='partition-body'};assert len(pn)==sum(r['kind']=='partition-body'for r in n)and set(po)<=set(pn)
 for key in po:assert po[key]==pn[key],(cfg,key,'prior partition drift')
 diff=[];new_frame=[]
 for key in sorted(set(pn)-set(po)):
  r=pn[key];assert r['partition']=='prior-frame-test-body-preserve-original-classification'
  header=r['mir'].splitlines()[0]
  # Actual function bodies are also checked byte-for-byte against complete
  # emitted MIR. CTFE-only constants remain explicit actual callback records.
  if r['defKind']not in ['Fn','AssocFn','Closure']:
   new_frame.append({'defPathHash':key,'path':r['path'],'defKind':r['defKind'],'classification':'original prior body remains in original accounting; no new exemption','actualMIRSHA256':c.sha(r['mir'].encode()),'ctfeOnlyCallbackBody':True});continue
  prior_body=emitted(oldtext,header);actual=emitted(newtext,header);assert actual==r['mir']
  changed_body=prior_body!=actual
  if changed_body:
   assert r['path']=='experimental_swift_reactor::execution::frame_operations::tests::af22_frozen_accounting_and_value_phase_reservations_stay_distinct'and r['defKind']=='Fn'
   row={'config':cfg,'body':r['path'],'finalDefPathHash':key,'oldEmittedMIRSHA256':c.sha(prior_body.encode()),'finalMIRSHA256':c.sha(actual.encode()),'priorClassificationPreserved':True,'exactSelectedFixtureExpressionOnly':True,'actualSpan':r['span']};diff.append(row);changed.append(row)
  new_frame.append({'defPathHash':key,'path':r['path'],'defKind':r['defKind'],'actualSpan':r['span'],'oldEmittedMIRSHA256':c.sha(prior_body.encode()),'actualMIRSHA256':c.sha(actual.encode()),'byteEqual':not changed_body,'classification':'exact selected af22 fixture expression'if changed_body else'original prior body remains in original accounting; no new exemption'})
 assert len(diff)==(1 if cfg.endswith('-unit')else 0)
 graph=[r for r in n if r['kind']=='scope-graph-body'];uses=[r for r in n if r['kind']=='scope-graph-function-item-use'];g={(r['defPathHash'],r['promoted']):r for r in graph};assert len(g)==len(graph)
 assert all((r['bodyDefPathHash'],r['promoted'])in g for r in uses)
 fixture_graph=[]
 if diff:
  fid=diff[0]['finalDefPathHash'];incoming=[r for r in uses if r['calleeDefPathHash']==fid]
  allowed={diff[0]['body']+'::{closure#0}','experimental_swift_reactor::execution::frame_operations::tests::control_tests::sc11_completion_accounting'}
  assert {r['path']for r in incoming}==allowed
  for edge in incoming:
   owner=g[(edge['bodyDefPathHash'],edge['promoted'])];body=emitted(newtext,owner['header']);fixture_graph.append({'actualEdge':edge,'actualOwner':owner,'ownerEmittedMIRSHA256':c.sha(body.encode()),'sourceBoundToUnchangedFixtureFileOrGeneratedTestHarness':True})
  assert not any(r['calleeDefPathHash']==fid for r in n if r['kind']=='FnDef')
 c.save(c.HERE/f'v6-frame-test-partition-{cfg}.json',{'query':q,'allExistingClassificationPreserved':True,'newRecords':new_frame,'changedExpression':diff,'fullOldMIR':oldart,'fullFinalMIR':newart,'actualWholeCrateGraphBodies':len(graph),'actualWholeCrateFunctionItemUses':len(uses),'exactFixtureIncomingGraph':fixture_graph,'noNamespaceExemption':True})
 # Complete compiler callee inventory emitted from each admitted runtime body.
 calls=[r for r in n if r['kind']=='FnDef'];assert not any('::tests::af22_'in r['calleePath']for r in calls)
 contexts.append({'config':cfg,'oldQuery':previous,'finalQuery':q,'allSelectedRuntimeBodiesByteEqual':True,'runtimeBodies':len(ro),'fixtureOnlyChanges':diff,'wholeCrateGraphBodies':len(graph),'wholeCrateFunctionItemUses':len(uses),'runtimeFnDefOperands':len(calls),'noRuntimeCallToCorrectedFixture':True})
for name in ['positive-positions-v5.rs','kind-positions-v5.rs']:
 assert (c.HERE/name).read_bytes()==(parent/name).read_bytes(),name
c.save(c.HERE/'final-generated-declarations-unchanged.json',{'parentSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'generatedDeclarationsByteEqual':{name:c.sha((c.HERE/name).read_bytes())for name in ['positive-positions-v5.rs','kind-positions-v5.rs']},'candidateDeclarationsNeverReinstalledOrChanged':True})
c.save(c.HERE/'v5-to-v6-summary.json',{'oldSourceClosure':c.read_json(parent/'candidate-final-source.json')['sourceClosure'],'sourceClosure':c.read_json(c.HERE/'candidate-final-source.json')['sourceClosure'],'roles':len(b),'finiteRoles':len(finite),'phaseCounts':dict(collections.Counter(r['ownerClass']for r in new)),'allRoleDescriptorsAndNumericIntervalsUnchanged':True,'allRuntimeMIRByteEqual':True,'contexts':contexts,'fixtureChangedBodies':changed,'completeRoleMap':{'path':'v5-to-v6-all-roles.json.gz','logicalSHA256':c.sha(raw)},'finiteMap':'v5-to-v6-finite-reconciliation.json','fixtureAdmissionBoundary':'Full compiler partition preserves original hooks/classes; exact af22 body changes only its selected expression. Whole-crate actual function-item uses bind ingress to its generated test wrapper and the unchanged sc11 fixture. All selected runtime FnDef operands exclude af22. No namespace exemption or product body/closure/hook added.','independentReviewPending':True,'runtimeQualified':False})
print('V5→V6 exact89124roles/1032finite/runtimeMIR unchanged; only4unit fixture MIR bodies changed')
