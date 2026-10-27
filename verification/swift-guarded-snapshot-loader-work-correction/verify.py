"""Focused correction/custody/arithmetic controls; no original script replay."""
import ast,copy,datetime,json,sys
from pathlib import Path
from custody import BASE,verify_inputs,sha
from receiver import classify_partial_eq,UnsupportedReceiver
from quote import Geometry,U64,add,mul,Refused
from mir_quote import evaluate
D=Path(__file__).resolve().parent
checks=[]
def check(name,ok):
 if not ok:raise AssertionError(name)
 checks.append(name)
def refuses(name,fn,errors=(ValueError,Refused,KeyError)):
 try:fn()
 except errors:checks.append(name);return
 raise AssertionError('not-refused:'+name)
custody=verify_inputs();check('exact-frozen46-inputs',custody['members_verified']==46)
check('pure-quote-byte-identical',(D/'quote.py').read_bytes()==(BASE/'quote.py').read_bytes())
check('pure-evaluator-byte-identical',(D/'mir_quote.py').read_bytes()==(BASE/'mir_quote.py').read_bytes())
old=json.loads((BASE/'mir-ledger.json').read_text());new=json.loads((D/'mir-ledger.json').read_text());x=json.loads((BASE/'mir-extraction.json').read_text())
check('same219-definitions',set(old['nodes'])==set(new['nodes'])==set(x['functions']) and len(new['nodes'])==219)
for key,value in old.items():
 if key not in ('nodes','standard_targets'):check('unchanged-top-level:'+key,new[key]==value)
changed=[]
for name,oldrow in old['nodes'].items():
 row=new['nodes'][name]
 for field,value in oldrow.items():
  if field not in ('calls','standard_calls','callback_bound'):check('unchanged-node:'+name+':'+field,row[field]==value)
  elif row[field]!=value:changed.append(dict(function=name,owner=row['owner'],field=field))
check('only-equality-related-call-nodes',all(r['owner'] in ('wresolve','vabi','mread','vall') for r in changed))
# Normalize the explanatory prefix while comparing all callee identities and
# multiplicities. Only the two wresolve slice edges may increase.
def normalized_call(call):
 value=copy.deepcopy(call)
 for prefix in ('type-option equality closed callbacks: ','type-slice equality closed callbacks: '):
  if value['target'].startswith(prefix):value['target']=value['target'][len(prefix):]
 return value
numeric=[]
for name,a in old['nodes'].items():
 before=sorted([normalized_call(c) for c in a['calls']],key=lambda c:(c['target'],c['callee'],c['multiplicity']))
 after=sorted([normalized_call(c) for c in new['nodes'][name]['calls']],key=lambda c:(c['target'],c['callee'],c['multiplicity']))
 check('same-call-cardinality:'+name,len(before)==len(after))
 for i,(b,c) in enumerate(zip(before,after)):
  check('same-call-target:'+name+':'+str(i),b['target']==c['target'] and b['callee']==c['callee'])
  if b['multiplicity']!=c['multiplicity']:
   numeric.append(dict(function=name,owner=a['owner'],target=b['target'],callee=b['callee'],old=b['multiplicity'],new=c['multiplicity']))
check('exact-two-numeric-edge-changes',len(numeric)==2 and all(r['owner']=='wresolve' and r['target']=='<&[Type] as PartialEq>::ne' and r['old']==1 and r['new']==128 for r in numeric))
# The original model fails the receiver-specific policy; the corrected one passes.
def requires_wresolve128(ledger):
 vals=[c['multiplicity'] for r in ledger['nodes'].values() if r['owner']=='wresolve' for c in r['calls'] if c['target'].endswith('<&[Type] as PartialEq>::ne')]
 if vals!=[128,128]:raise ValueError('wresolve-slices-not-two-times128')
refuses('original-two-times1-fails',lambda:requires_wresolve128(old))
requires_wresolve128(new);check('corrected-two-times128-passes',True)
wr=next(r for r in new['nodes'].values() if r['owner']=='wresolve' and any(c['target'].endswith('<&[Type] as PartialEq>::ne') for c in r['calls']))
check('wresolve-callback-diagnostic128',wr['callback_bound']==128)
for target,kind,count in [
 ('<Type as PartialEq>::eq','authored-scalar',1),('<Type as PartialEq>::ne','authored-scalar',1),
 ('<Option<Type> as PartialEq>::eq','type-option',1),('<Option<Type> as PartialEq>::ne','type-option',1),
 ('<&[Type] as PartialEq>::eq','type-slice',128),('<&[Type] as PartialEq>::ne','type-slice',128),
 ('<&[Type] as PartialEq<[Type; 1]>>::eq','type-slice',1),
 ('<FileIdentityV1 as PartialEq>::ne','authored-scalar',1),('<Profile as PartialEq>::eq','authored-scalar',1),
 ('<&[u8] as PartialEq>::ne','primitive',0)]:
 d=classify_partial_eq(target);check('receiver:'+target,d.kind==kind and d.callbacks==count and bool(d.reason))
for target in ('<Vec<Type> as PartialEq>::eq','<Option<&Type> as PartialEq>::eq','<Option<Option<Type>> as PartialEq>::eq','<OtherType as PartialEq>::eq','<&[Type] as PartialEq<Type>>::eq','<&[Type] as PartialEq<[Type; N]>>::eq','<&[Type; 128] as PartialEq>::eq','<Type as PartialEq<Option<Type>>>::eq','<Type as NotPartialEq>::eq'):
 refuses('unsupported-ambiguous:'+target,lambda target=target:classify_partial_eq(target),errors=(UnsupportedReceiver,))
# All actual existing PartialEq callsites have explicit supported classifications.
dispatches=json.loads((D/'equality-dispatch.json').read_text())['dispatches']
for row in dispatches:
 d=classify_partial_eq(row['target']);check('actual-dispatch:'+row['function']+':'+row['target'],d.__dict__=={k:row[k] for k in d.__dict__})
check('actual-primitives-explicit-no-authored-callback',all(row['reason'] and (row['kind']!='primitive' or row['callbacks']==0) for row in dispatches))
# The actual adapted pricing function classifies before any scalar-family match.
src=(D/'price_mir.py').read_text();tree=ast.parse(src);resolve=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='resolve')
check('actual-tool-calls-receiver-classifier',any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='classify_partial_eq' for n in ast.walk(resolve)))
check('greedy-substring-equality-removed','any(t in target' not in ast.get_source_segment(src,resolve))
check('all-native-terms-identical',all(old['nodes'][n]['native']==r['native'] for n,r in new['nodes'].items()))
check('old407-roster-growth-explained',len(old['standard_targets'])==403 and len(new['standard_targets'])==407 and set(old['standard_targets']).issubset(new['standard_targets']))
for target in set(new['standard_targets'])-set(old['standard_targets']):
 check('new-standard-wrapper:'+target,classify_partial_eq(target).kind in ('type-slice','type-option'))
g=Geometry(**json.loads((D/'cap-geometry.json').read_text()));a=evaluate(g,old);b=evaluate(g,new)
check('same-wrapper-work',a['wrapper_logical_actions']==b['wrapper_logical_actions']==97394558768720)
check('old-coefficient-retained',a['validator_acyclic_expanded_ceiling']==1747993923)
check('new-coefficient-direct-delta',b['validator_acyclic_expanded_ceiling']==1748020339 and b['validator_acyclic_expanded_ceiling']-a['validator_acyclic_expanded_ceiling']==2*(128-1)*104==26416)
check('exact-positive-W-delta',b['W_loader']-a['W_loader']==mul(g.credits+1,26416)==13524992026416)
check('corrected-cap-W',b['W_loader']==895083809874789059 and b['W_loader']<=U64)
# Downgrade only the corrected callbacks: the exact original scalar returns.
q=copy.deepcopy(new)
for row in q['nodes'].values():
 if row['owner']=='wresolve':
  for call in row['calls']:
   if call['target'].endswith('<&[Type] as PartialEq>::ne'):call['multiplicity']=1
check('two-times1-counterfactual-restores-original-W',evaluate(g,q)['W_loader']==a['W_loader'])
refuses('two-times1-counterfactual-policy-fails',lambda:requires_wresolve128(q))
for B in (0,1,2,32,512000000):
 d=g.__dict__.copy();d['credits']=B;geo=Geometry(**d);before=evaluate(geo,old);after=evaluate(geo,new)
 check('monotonic-credit-grid:'+str(B),after['W_loader']-before['W_loader']==mul(B+1,26416)>0)
for value in (0,1,2,U64-1,U64):
 check('checked-mul-zero:'+str(value),mul(value,0)==0)
 if value>1:refuses('checked-overflow:'+str(value),lambda value=value:mul(value,U64))
refuses('unknown-callee',lambda:evaluate(g,{**new,'roots':{**new['roots'],'loader':'UNKNOWN'}}))
q=copy.deepcopy(new);q['nodes'][q['roots']['validator']]['calls'].append(dict(target='negative cycle',callee=q['roots']['validator'],multiplicity=1))
refuses('unclassified-cycle',lambda:evaluate(g,q))
check('no-grant',not b['operational_grant'] and not b['actual_genuine_fixture_bound'])
(D/'cap-quote.json').write_text(json.dumps(b,sort_keys=True,indent=2)+'\n')
(D/'input-bindings.json').write_text(json.dumps(custody,sort_keys=True,indent=2)+'\n')
(D/'delta.json').write_text(json.dumps(dict(schema=1,old_cap=a,new_cap=b,coefficient_delta=26416,cap_work_delta=13524992026416,numeric_edges=numeric,changed_fields=changed,native_reallocated=False,independent_correction_review_required=True,source146_rebinding_required=True,operational_grant=False),sort_keys=True,indent=2)+'\n')
(D/'controls.json').write_text(json.dumps(dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),passed=True,controls=len(checks),names=checks,python=sys.version,scope='pure correction regression/arithmetic/custody only; no independent source/callsite or runtime acceptance'),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='correction-pure-controls-pass',controls=len(checks),new_W=b['W_loader'],delta=13524992026416)))
