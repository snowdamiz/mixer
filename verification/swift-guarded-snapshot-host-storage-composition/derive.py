"""Read immutable evidence; derive storage slots, never execute source/runtime."""
from pathlib import Path
import collections, hashlib, json, re, sys
from layouts import catalog,resolve,generic_binding
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V=ROOT/'verification'
SOURCE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(v): return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def read(p):
 p=Path(p)
 assert p.is_file() and not p.is_symlink() and p.resolve()==p.absolute(),p
 return p.read_bytes()
def js(p):return json.loads(read(p))
def save(n,v):
 assert not (HERE/'seal.json').exists(),'frozen'
 (HERE/n).write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def tidy(t):
 # Type-key spelling only; never source or ownership authorization.
 return re.sub(r'(?:[A-Za-z_]\w*::)+','',t).replace("'static","'_")
def inputs():
 b=js(HERE/'input-bindings.json'); out=[]
 for row in b['files']:
  data=read(ROOT/row['path']); assert len(data)==row['bytes'] and sha(data)==row['sha256'],row['path']
  out.append(row)
 for row in b['packets']:
  p=ROOT/row['path']; seal=read(p/'seal.json'); assert sha(seal)==row['seal_sha256']
  j=json.loads(seal); members=j['members'];assert len(members)==j['member_count']
  assert len({x['path'] for x in members})==len(members)
  for x in members:
   assert not Path(x['path']).is_absolute() and '..' not in Path(x['path']).parts
   d=read(p/x['path']);assert len(d)==x['bytes'] and sha(d)==x['sha256'],(p,x['path'])
 source=js(V/'swift-guarded-snapshot-host-composition/source-manifest.json')
 assert source['member_count']==146 and source['tree_sha256']==SOURCE and sha(canonical(source['members']))==SOURCE
 for x in source['members']:
  p=V/'swift-guarded-snapshot-host-composition/overlay/vm'/x['path']
  if not p.exists():p=V/'swift-guarded-snapshot-funding-implementation/source/vm'/x['path']
  data=read(p);assert len(data)==x['bytes'] and sha(data)==x['sha256'],p
 hosts=js(V/'swift-guarded-snapshot-host-composition/host-support-manifest.json')
 assert hosts['member_count']==11 and hosts['tree_sha256']==HOST and sha(canonical(hosts['members']))==HOST
 for x in hosts['members']:
  data=read(V/'swift-real-profile-loader-binding/host'/x['path']);assert len(data)==x['bytes'] and sha(data)==x['sha256'],x['path']
 return {'files_verified':len(out),'packets_verified':len(b['packets']),'source_members':146,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST}
def layout_table():
 table=collections.defaultdict(set)
 f=js(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')
 assert f['logical_source_object_bytes']==311071 and f['role_count']==396
 for k,v in f['actual_type_sizes'].items():table[tidy(k)].add(v)
 q=js(V/'swift-guarded-snapshot-source146-leaf-payload-layouts/results.json')
 for row in q['queries']:
  table[tidy(row['key'])].add(row['size']);table[tidy(row['concrete'])].add(row['size'])
 # Primitive values are observed in the accepted actual-type table.
 for k in ['u8','u32','u64','usize','isize','bool','()','!']:
  if k in f['actual_type_sizes']:table[k].add(f['actual_type_sizes'][k])
 return {k:next(iter(v)) for k,v in table.items() if len(v)==1}
def known_extent(t,known):
 if t in known:return known[t]
 # References are inline handles only. No backing is included here.
 if t.startswith('&') or t.startswith('*const ') or t.startswith('*mut '):
  s=t[1:].removeprefix('mut ').strip() if t.startswith('&') else t.split(' ',1)[1]
  if s=='str' or (s.startswith('[') and ';' not in s) or s.startswith('dyn '):return 16
  return 8
 m=re.fullmatch(r'\[(.+); (\d+)\]',t)
 if m:
  e=known_extent(m.group(1),known)
  if e is not None:return e*int(m.group(2))
 return None

def reachable(nodes,root):
 out=set();todo=[root]
 while todo:
  n=todo.pop()
  if n in out:continue
  assert n in nodes,n
  out.add(n);todo.extend(c['callee'] for c in nodes[n]['calls'])
 return out

def acyclic(nodes):
 visiting=set();done=set()
 def visit(n):
  assert n not in visiting,('recursive-author-frame',n)
  if n in done:return
  visiting.add(n)
  for c in nodes[n]['calls']:visit(c['callee'])
  visiting.remove(n);done.add(n)
 for n in nodes:visit(n)
 return len(done)

def derive():
 custody=inputs();known=layout_table();full_layouts,raw_rows=catalog()
 old=js(V/'swift-guarded-snapshot-host-account-entry/caller-inventory.json')
 caller=[]
 for i,f in enumerate(old['functions']):
  for r in f['roles']:
   t=tidy(r['concrete_production_type']);size=known_extent(t,known)
   # Anonymous selected closure has a separately accepted exact 8-byte extent.
   if '{closure@' in t or t=='impl FnOnce() -> T':size=8
   assert size==r['bytes'],(i,r['local'],t,size,r['bytes'])
   caller.append({'id':f'caller19::{i}::{r["local"]}','function':f['header'],'local':r['local'],'type':t,'bytes':size,'phase':f['phase']})
 assert len(caller)==396 and sum(r['bytes'] for r in caller)==311071
 assert sum(r['bytes'] for r in caller if r['phase'].startswith('P0'))==234375
 leafledger=js(V/'swift-guarded-snapshot-leaf-shell-cost/operation-ledger.json')
 leaf=[]
 for f in leafledger['functions']:
  for local,r in f['roles'].items():
   t=tidy(r['compiler_type']);extent=known_extent(t,known)
   assert extent is not None,('missing-leaf-layout',t)
   leaf.append({'id':f'leaf8::{f["function"]}::{local}','function':f['function'],'local':local,'type':t,'bytes':extent})
 assert len(leaf)==205
 p=V/'swift-guarded-snapshot-loader-work-source146'
 extracted=js(p/'mir-extraction146.json');ledger=js(p/'mir-ledger.json')
 assert extracted['function_count']==219 and set(extracted['functions'])==set(ledger['nodes'])
 assert acyclic(ledger['nodes'])==219
 validator=reachable(ledger['nodes'],ledger['roots']['validator'])
 allslots=[];missing=collections.defaultdict(list)
 for fi,(name,f) in enumerate(sorted(extracted['functions'].items())):
  assert f['sha256']==ledger['nodes'][name]['mir_sha256']
  for local,t0 in f['locals'].items():
   t=tidy(t0);bound=resolve(t0,full_layouts) or generic_binding(t0,full_layouts);extent=bound['bytes'] if bound else None
   key=t
   if extent is None:missing[key].append({'function':name,'local':local,'type_original':t0})
   allslots.append({'id':f'loader219::{fi}::{local}','function':name,'function_sha256':f['sha256'],'local':local,'type':t,'known_bytes':extent,'required_layout':None if extent is not None else key,'validator':name in validator,'layout_proof':bound})
 assert len(allslots)==9403 and len(validator)==152 and sum(x['validator'] for x in allslots)==6458
 unresolved=[]
 for t,sites in sorted(missing.items()):
  category='anonymous-capture' if '{closure@' in t else 'generic-specialization' if (t in ['T','D','Bytes<N>','[u8; N]'] or any(s in t for s in ['<T>','<D>',' C>','impl ','Option<T>',' T>'])) else 'concrete-query'
  unresolved.append({'key':t,'category':category,'occurrences':len(sites),'sites':sites,'query_ready':category=='concrete-query','extent_status':'required-positive-bound-not-observed'})
 inv={'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'caller_slots':caller,'leaf_slots':leaf,'loader_slots':allslots,
  'caller_bytes':311071,'P0_caller_bytes':234375,'child_caller_bytes':76696,'leaf_bytes':sum(r['bytes'] for r in leaf),
  'loader_known_bytes':sum(r['known_bytes'] or 0 for r in allslots),'loader_functions':219,'loader_roles':9403,'validator_functions':152,'validator_roles':6458,
  'all_authored_frame_call_graph_acyclic':True,'one_conservative_slot_set_per_authored_function':'all declared locals/parameters/returns once; repeated synchronous calls reuse the same function-slot allowance, no operation/work multiplier',
  'standard_native_frames_outside_this_roster':'required separate bounded backing/temporary interface; no CPU, RSS or compiler stack assertion',
  'loader_named_198960_replaced_not_added':'new 219-function exact-role interface subsumes original observer/loader/read/final-recheck named places; historical named inventory is comparison only',
  'raw_compiler_layout_records':3072,'raw_layout_data_sha256':'6c924c8088173db78afb1f648b284df7d8d139b3389bd090a9552df4130cfe7a','leaf_work_native_occurrence_bytes_used':0,'required_layouts':[r['key'] for r in unresolved]}
 return custody,inv,{'schema':1,'source_tree_sha256':SOURCE,'types':unresolved,'counts':dict(collections.Counter(r['category'] for r in unresolved)),
 'generic_specialization_obligation':'C/MeterControl = SwiftControl; D/Declaration = SwiftDeclaration. Buffer<T>/Vec<T>/Option<T>/T must dominate every actual validator call-site element Type, Option<Type>, Signature, Import, Function, Global, Export, Segment, Control, u32; no unconstrained arbitrary T. Anonymous closures require actual capture-field bounds or concrete compiler observations; source leaf counts are not native bytes.',
 'active_frames':'219-node accepted authored call graph is acyclic including standard callback edges; no recursion multiplier selected; any new unresolved/reentrant edge refuses',
 'compiler_allowed_now':False}

def main():
 custody,inv,queries=derive()
 save('input-custody.json',custody);save('inline-inventory.json',inv);save('pending-layout-roster.json',queries)
 print(json.dumps({'source':SOURCE,'caller':inv['caller_bytes'],'leaf':inv['leaf_bytes'],'loader_roles':inv['loader_roles'],'validator_roles':inv['validator_roles'],'pending':queries['counts']}))
if __name__=='__main__':main()
