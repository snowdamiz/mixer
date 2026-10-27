"""Finite arithmetic/custody/omission controls, never import product code."""
import copy,datetime,gzip,hashlib,json,subprocess,sys
from pathlib import Path
from quote import Geometry,CAPS,U64,add,mul,Refused
from mir_quote import evaluate
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,x):(D/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
checks=[]
def check(name,condition):
 if not condition:raise AssertionError(name)
 checks.append(name)
def refused(name,fn):
 try:fn()
 except (Refused,KeyError,TypeError):checks.append(name);return
 raise AssertionError('not-refused:'+name)
# Exact source selection and original count-only loader change.
m=json.loads((D/'compiler-source-manifest.json').read_text());base=R/'verification/swift-guarded-snapshot-funding-implementation/source/vm';overlay=R/'verification/swift-guarded-snapshot-descriptor-rebinding/overlay/vm'
for row in m['members']:
 p=overlay/row['path'] if (overlay/row['path']).exists() else base/row['path'];b=p.read_bytes()
 check('source145:'+row['path'],len(b)==row['bytes'] and sha(b)==row['sha256'])
check('source145-tree',m['tree_sha256']=='450b6d9b3a05d160e19fa888b68173286b8f6af20ecc7216fdf86283f09b308a' and len(m['members'])==145)
loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
b144=(base/loader).read_bytes();b145=(overlay/loader).read_bytes()
check('loader-only-source-count-change',b144.replace(b'word(b, 32) != 144',b'word(b, 32) != 145')==b145)
receipt=json.loads((D/'compiler-receipt.json').read_text());raw=gzip.decompress((D/'whole-source.mir.gz').read_bytes())
check('raw-MIR-bound',sha(raw)==receipt['mir']['sha256'] and len(raw)==receipt['mir']['bytes'])
check('preopt-library-only',all(s in receipt['argv'] for s in ('-Zmir-opt-level=0','opt-level=0','rlib')) and '--test' not in receipt['argv'])
check('compiler-success-direct-child-reaped',receipt['exit_code']==0 and not receipt['timed_out'] and receipt['direct_child_waited'])
X=json.loads((D/'mir-extraction.json').read_text());selected=gzip.decompress((D/'selected-definitions.mir.gz').read_bytes())
check('selected-MIR-bound',sha(selected)==X['selected_sha256'] and len(selected)==X['selected_bytes'])
check('all129-source-bodies-have-MIR',not X['source_bodies_without_direct_definition'] and len(X['source_owners'])>=129)
L=json.loads((D/'mir-ledger.json').read_text())
check('every-extracted-definition-priced',set(L['nodes'])==set(X['functions']))
check('source/MIR-root-binding',L['source_tree_sha256']==m['tree_sha256'] and L['parent_mir_sha256']==sha(raw))
# Each instruction family's covering rule is checked against this exact MIR.
families=set();standard_seen=set()
for n,f in X['functions'].items():
 check('nonempty-statements:'+n,bool(f['statements']))
 for st in f['statements']:
  if ' = ' in st:family='assignment-or-call'
  else:
   family=next((q for q in ('StorageLive(','StorageDead(','FakeRead(','PlaceMention(','AscribeUserType(','Retag(','Deinit(','SetDiscriminant(','goto ->','switchInt(','assert(','drop(','return;','unreachable;','resume;','terminate(','nop;') if st.startswith(q)),None)
   check('supported-MIR-statement:'+n+':'+st[:45],family is not None)
  families.add(family)
 check('body-fingerprint:'+n,L['nodes'][n]['mir_sha256']==f['sha256'])
# Fully expanded DAG membership and no repeated source leaf omitted.
g=Geometry(**json.loads((D/'cap-geometry.json').read_text()));cap=evaluate(g,L)
check('all219-callees-reached',cap['priced_nodes_visited']==len(L['nodes'])==219)
check('cap-u64-fit',cap['W_loader']<=U64 and cap['W_loader']==add(cap['wrapper_logical_actions'],mul(g.credits+1,cap['validator_acyclic_expanded_ceiling'])))
check('not-credit-equals-action',cap['validator_host_logical_actions']>g.credits and cap['validator_acyclic_expanded_ceiling']>1)
check('raw-credit-preserved',cap['validator_original_credits']==512000000)
check('no-operational-grant',not cap['operational_grant'] and not cap['actual_genuine_fixture_bound'])
for x in (0,1,2,31,32,33,4095,4096,4097,U64-1,U64):
 for y in (0,1,2,U64-1,U64):
  if x+y<=U64:check(f'add:{x}:{y}',add(x,y)==x+y)
  else:refused(f'add-overflow:{x}:{y}',lambda x=x,y=y:add(x,y))
  if x*y<=U64:check(f'mul:{x}:{y}',mul(x,y)==x*y)
  else:refused(f'mul-overflow:{x}:{y}',lambda x=x,y=y:mul(x,y))
for x in (-1,True,None,1.5,'0',U64+1):
 refused('invalid-u64:'+str(x),lambda x=x:add(x,0))
for key,limit in CAPS.items():
 # Geometry source uses distinct validator_source field.
 values=g.__dict__.copy();values[key]=limit+1
 refused('cap-overflow:'+key,lambda values=values:evaluate(Geometry(**values),L))
# B=0 still pays one complete failure-prefix epoch, zero-length take cannot
# make dynamic repetition free; positive credit cuts count the final attempt.
z=Geometry(0,0,0,0,0,0,0,0,0);zero=evaluate(z,L)
check('B0-epoch-present',zero['validator_host_logical_actions']==zero['validator_acyclic_expanded_ceiling']>0)
for B in (0,1,2,3,31,32):
 for attempted in range(B+2):
  successful=min(attempted,B);failed=int(attempted>B)
  check(f'credit-epoch:{B}:{attempted}',successful+failed<=B+1)
# Nested loops share one monotone account, rather than multiplying B counts.
for B in range(6):
 for outer in range(7):
  for inner in range(7):
   count=min(B,outer*inner)
   check(f'nested-credit-cut:{B}:{outer}:{inner}',count+int(outer*inner>B)<=B+1)
check('fixed-resolver34',any(c['multiplicity']==34 and '::find::<' in c['target'] for r in L['nodes'].values() for c in r['calls']))
check('fixed-array-map5',any(c['multiplicity']==5 and '::map::<' in c['target'] for r in L['nodes'].values() for c in r['calls']))
check('fixed-empty-segment-family2',any(r.get('validator_fixed_repeat')==2 and r['owner']=='vsegments' for r in L['nodes'].values()))
check('hex-two-closed-digit-sites',sum(1 for r in L['nodes'].values() if r['owner']=='hex' and r['repeat']==33 for c in r['calls'] if '{closure#' in c['callee'])==2)
# Omissions change the frozen proposal, and malformed/unknown/cyclic models
# are refused, rather than substituting an unpriced0.
for label,mutate in [
 ('missing-local-part',lambda q:q['nodes'][q['roots']['loader']]['parts'].pop('parameter_leaf_fetch_store')),
 ('unknown-callee',lambda q:q['nodes'][q['roots']['loader']]['calls'].append(dict(target='negative control',callee='UNKNOWN',multiplicity=1))),
 ('unclassified-cycle',lambda q:q['nodes'][q['roots']['loader']]['calls'].append(dict(target='negative control',callee=q['roots']['loader'],multiplicity=1))),
 ('overflow-callee',lambda q:q['nodes'][q['roots']['validator']]['calls'].append(dict(target='negative control',callee=next(n for n,r in q['nodes'].items() if r['owner']=='derived_eq'),multiplicity=U64)))] :
 q=copy.deepcopy(L);mutate(q);refused(label,lambda q=q:evaluate(g,q))
for label,predicate,field in [('omit-resolver34',lambda r:r['owner']=='wresolve','calls'),('omit-segment-family2',lambda r:r['owner']=='vsegments','validator_fixed_repeat'),('omit-native-read',lambda r:r['owner']=='read_attempt','native')]:
 q=copy.deepcopy(L);r=next(r for r in q['nodes'].values() if predicate(r));r[field]=[] if field in ('calls','native') else 1
 check(label,evaluate(g,q)['W_loader']!=cap['W_loader'])
write('cap-quote.json',cap)
write('controls.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),controls=len(checks),passed=True,names=checks,instruction_families=sorted(families),scope='pure finite proposal/custody controls; no product behavior/runtime or independent acceptance',python=sys.version))
print(json.dumps(dict(status='pure-controls-pass',controls=len(checks),cap_quote=cap['W_loader'],nodes=219)))
