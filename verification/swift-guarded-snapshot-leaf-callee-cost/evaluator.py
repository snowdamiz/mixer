"""Conditional logical cost arithmetic, not an operational grant constructor."""
from collections import Counter
from pathlib import Path
import hashlib
MAX=(1<<64)-1
TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
LEAF='10321f6bdadbe8ff193d553063b978e59857f7390e243e63054f0d4e1997cd57'
LAYOUT='f2021a5fa0be89481bc02bdb811ec6ac2fb5e4112900a9f1e831135070be2952'
def unsigned(x):
 if type(x) is not int or not 0<=x<=MAX:raise ValueError('invalid u64')
 return x
def add(*values):
 result=0
 for x in values:
  x=unsigned(x)
  if x>MAX-result:raise ValueError('u64 addition overflow')
  result+=x
 return result
def mul(a,b):
 a=unsigned(a);b=unsigned(b)
 if b and a>MAX//b:raise ValueError('u64 multiplication overflow')
 return a*b

def flatten(ledger,node,active=()):
 if node in active:raise ValueError('recursive authored call graph')
 if node not in ledger['nodes']:raise ValueError('missing authored callee')
 n=ledger['nodes'][node];fixed=add(n['own'],n.get('known_native',0));native=Counter(n.get('missing_native',{}));unsized=Counter(n.get('unsized',{}));payload=Counter(n['payload'])
 for k,v in list(native.items())+list(unsized.items())+list(payload.items()):
  if unsigned(v)==0:raise ValueError('zero coefficient')
 for child,count in n['calls'].items():
  if unsigned(count)==0:raise ValueError('zero call multiplicity')
  f=flatten(ledger,child,active+(node,));fixed=add(fixed,mul(count,f['fixed']))
  for result,source in [(native,f['native']),(unsized,f['unsized']),(payload,f['payload'])]:
   for k,v in source.items():result[k]=add(result[k],mul(count,v))
 return dict(fixed=fixed,native=dict(native),unsized=dict(unsized),payload=dict(payload))

def interface(ledger):
 if ledger['source_tree_sha256']!=TREE:raise ValueError('wrong source146')
 answer={}
 for export,node in ledger['exports'].items():
  row=flatten(ledger,node);row['required_private_primitive_cut']='private_primitive::'+export
  answer[export]=row
 return dict(schema=1,source_tree_sha256=TREE,leaf_seal_sha256=LEAF,layout_seal_sha256=LAYOUT,native_query_roster_sha256=hashlib.sha256((Path(__file__).resolve().parent/'native-query-roster/roster.json').read_bytes()).hexdigest(),exports=answer,unit='accepted abstract logical source/callsite and requested native bytes; actual payload destruction and private native/lowering allowances are positive imports',candidate_only=True,product451814442_reused_as_aggregate=False,product_work_discount=0,complete_host_quote=False,operational_grant=False,actual_product_execution=False,native_or_GA_qualified=False)

def check_route(route):
 expected={'source_tree_sha256':TREE,'leaf_seal_sha256':LEAF,'layout_seal_sha256':LAYOUT,'selected_policy':'SnapshotAdoptionV1','fixed_execution_work':451814442,'authentic_ingress_count':1,'consuming_construct_count':1,'outer_observation_count':1,'consuming_finish_count':1,'intervening_cache_mutations':0,'attached_wasi':False}
 for key,value in expected.items():
  if key not in route or type(route[key]) is not type(value) or route[key]!=value:raise ValueError('unqualified route '+key)
 # These are immutable source maxima, not counts chosen by a caller to reduce
 # payment. The full64/64 and4 upper is always charged in every expression.
 for key,maximum in [('cache_pin_bound',64),('cache_slot_bound',64),('wasi_buffer_bound',4)]:
  if key not in route or type(route[key]) is not int or route[key]!=maximum:raise ValueError('unqualified finite loop bound '+key)

def evaluate(contract,export,route,sizes,unsized,payload,primitives):
 check_route(route)
 if contract['source_tree_sha256']!=TREE or contract['leaf_seal_sha256']!=LEAF or contract['layout_seal_sha256']!=LAYOUT:raise ValueError('contract identity')
 if export not in contract['exports']:raise ValueError('unknown export')
 row=contract['exports'][export];values=[unsigned(row['fixed'])]
 def positive(mapping,key,label):
  if key not in mapping or type(mapping[key]) is not int or mapping[key]<=0:raise ValueError('missing justified positive '+label+' '+key)
  return unsigned(mapping[key])
 for ty,n in row['native'].items():values.append(mul(n,positive(sizes,ty,'actual146 sizeof')))
 for ty,n in row['unsized'].items():values.append(mul(2*n,positive(unsized,ty,'finite unsized bound')))
 for ty,n in row['payload'].items():values.append(mul(n,positive(payload,ty,'typed payload interface')))
 values.append(positive(primitives,row['required_private_primitive_cut'],'private primitive allowance'))
 return add(*values)

def canonical_route():
 return dict(source_tree_sha256=TREE,leaf_seal_sha256=LEAF,layout_seal_sha256=LAYOUT,selected_policy='SnapshotAdoptionV1',fixed_execution_work=451814442,authentic_ingress_count=1,consuming_construct_count=1,outer_observation_count=1,consuming_finish_count=1,intervening_cache_mutations=0,attached_wasi=False,cache_pin_bound=64,cache_slot_bound=64,wasi_buffer_bound=4)

# Arbitrary numeric dictionaries are permitted only for explicit synthetic
# arithmetic controls. Qualification uses an immutable root-selected receipt
# digest and exact source/roster binding. No path constructs a runtime grant.
import hashlib,json
from dataclasses import dataclass
@dataclass(frozen=True)
class NativeBinding:
 values:dict
 receipt_sha256:str
 compiler_receipt_sha256:str
 source_tree_sha256:str
 roster_sha256:str

def bind_native(receipt_bytes,selected_receipt_sha256,contract):
 actual=hashlib.sha256(receipt_bytes).hexdigest()
 if type(selected_receipt_sha256) is not str or len(selected_receipt_sha256)!=64 or actual!=selected_receipt_sha256:raise ValueError('native receipt not selected by immutable digest')
 receipt=json.loads(receipt_bytes)
 if receipt['source_tree_sha256']!=TREE or receipt['native_query_roster_sha256']!=contract['native_query_roster_sha256'] or receipt['target']!='aarch64-apple-darwin':raise ValueError('native receipt applicability')
 if receipt['scope']!='compiler-observed-source146-size-and-alignment' or receipt['product_executed'] is not False:raise ValueError('native receipt scope')
 compiler=receipt['compiler_receipt_sha256']
 if type(compiler) is not str or len(compiler)!=64:raise ValueError('missing compiler receipt identity')
 required={k for r in contract['exports'].values() for k in r['native']};values={}
 for row in receipt['observations']:
  key=row['key']
  if key in values or key not in required:raise ValueError('duplicate/unknown native query')
  if row['kind']!='actual-size-and-alignment' or row['source_tree_sha256']!=TREE or not row['compiler_diagnostic_binding_sha256']:raise ValueError('unobserved native size')
  size=unsigned(row['size']);alignment=unsigned(row['alignment'])
  if alignment==0 or alignment&(alignment-1) or size%alignment:raise ValueError('invalid observed native layout')
  values[key]=size
 if set(values)!=required:raise ValueError('incomplete native substitution')
 return NativeBinding(values,actual,compiler,TREE,receipt['native_query_roster_sha256'])

_original_evaluate=evaluate

def evaluate_synthetic(contract,export,route,sizes,unsized,payload,primitives):
 """Synthetic interface exercise only; arbitrary numbers are not qualification."""
 return _original_evaluate(contract,export,route,sizes,unsized,payload,primitives)

def evaluate_bound(contract,export,route,native,unsized,payload,primitives):
 """Use digest-selected native observations; payload/primitive cuts stay explicit.

 This returns a conditional proposal, never accepted host funding or a runtime
 permission. Root must separately qualify each typed resource/payload allowance.
 """
 if not isinstance(native,NativeBinding) or native.source_tree_sha256!=TREE or native.roster_sha256!=contract['native_query_roster_sha256']:raise ValueError('bound native receipt required')
 # An observed zero-sized closure is valid. Replace its arithmetic input with
 # one for the positive-only synthetic engine and subtract exactly its term.
 # Subtraction is checked and is solely the observed ZST's native dimension,
 # never a product-work or payload discount.
 zero={k for k,v in native.values.items() if v==0};safe={k:max(1,v) for k,v in native.values.items()}
 total=_original_evaluate(contract,export,route,safe,unsized,payload,primitives)
 correction=add(*(n for k,n in contract['exports'][export]['native'].items() if k in zero))
 if correction>total:raise ValueError('invalid zero-sized correction')
 return dict(conditional_logical_price=total-correction,native_receipt_sha256=native.receipt_sha256,complete_host_quote=False,operational_grant=False,remaining_payload_and_primitive_receipts_required=True)

# The ambiguous old name is not a qualification entry point.
del evaluate
