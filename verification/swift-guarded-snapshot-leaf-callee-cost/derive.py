#!/usr/bin/env python3
"""Offline exact-source callee expansion. Never invokes a compiler or product."""
from pathlib import Path
import collections,gzip,hashlib,json,re,sys
sys.dont_write_bytecode=True
import shapes
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1];V=ROOT/'verification'
TREE='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm';OVER=V/'swift-guarded-snapshot-host-composition/overlay/vm'
sha=lambda x:hashlib.sha256(x).hexdigest()
canon=lambda x:json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def out(name,value):(HERE/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def extract(text,marker,occurrence=0):
 start=-1
 for _ in range(occurrence+1):start=text.index(marker,start+1)
 opening=text.index('{',start);depth=0;i=opening
 while i<len(text):
  if text.startswith('//',i):i=text.index('\n',i);continue
  if text.startswith('/*',i):i=text.index('*/',i+2)+2;continue
  if text[i]=='"':
   i+=1
   while text[i]!='"':i+=2 if text[i]=='\\' else 1
   i+=1;continue
  if text[i]=='{':depth+=1
  elif text[i]=='}':
   depth-=1
   if not depth:return text[start:i+1]
  i+=1
 raise ValueError('unfinished body')
def type146(t):
 t=re.sub(r'<P as (?:[A-Za-z_]\w*::)*ClosedAdoptionV1>::Failure','SnapshotPreScopeFailureV1',t)
 t=re.sub(r'<P as (?:[A-Za-z_]\w*::)*ClosedAdoptionV1>::Retirement','Result<(), SwiftRunFailure>',t)
 return re.sub(r'\bT\b','Option<SwiftFunctionCache>',t)
def normalize(t):return shapes.canonical_type(type146(t))
def check_seal(folder,digest):
 raw=(folder/'seal.json').read_bytes()
 if sha(raw)!=digest:raise ValueError('changed input seal')
 seal=json.loads(raw)
 for row in seal['members']:
  b=(folder/row['path']).read_bytes()
  if (len(b),sha(b))!=(row['bytes'],row['sha256']):raise ValueError('changed input member '+row['path'])
 return dict(path=str(folder.relative_to(ROOT)),seal_sha256=digest,members=len(seal['members']),bytes=sum(r['bytes'] for r in seal['members']))
def functions(text):
 result=[]
 for m in re.finditer(r'^fn .*$',text,re.M):
  end=re.compile(r'^}\n',re.M).search(text,m.start())
  if end is None:raise ValueError('unfinished MIR')
  result.append(text[m.start():end.end()])
 return result

def sccs(blocks):
 graph={n:sorted(set(re.findall(r'\bbb\d+\b',r['lines'][-1][1]))) for n,r in blocks.items()}
 if any(t not in blocks for ts in graph.values() for t in ts):raise ValueError('missing CFG target')
 index={};low={};stack=[];on=set();result=[]
 def visit(n):
  index[n]=low[n]=len(index);stack.append(n);on.add(n)
  for t in graph[n]:
   if t not in index:visit(t);low[n]=min(low[n],low[t])
   elif t in on:low[n]=min(low[n],index[t])
  if low[n]==index[n]:
   c=[]
   while True:
    t=stack.pop();on.remove(t);c.append(t)
    if t==n:break
   if len(c)>1 or n in graph[n]:result.append(sorted(c,key=lambda x:int(x[2:])))
 for n in graph:
  if n not in index:visit(n)
 return graph,result

REUSE={
 'control::RuntimeControl::check':'check','control::RuntimeControl::check_budget':'check_budget',
 'control::RuntimeControl::check_with_wasi':'check_with_wasi','control::RuntimeControl::usage':'usage',
 'control::RuntimeControl::fail':'fail','control::RuntimeControl::admit':'admit',
 'control::RuntimeControl::refund_with_wasi':'refund_with_wasi','control::RuntimeControl::refund':'refund',
 'control::RuntimeControl::cleanup_fault_with_wasi':'cleanup_fault',
 'control::Fault::new':'fault','control::Fault::limit':'fault_limit',
 'control::SwiftReservations::category':'category','control::SwiftReservations::category_mut':'category_mut',
 'control::Cursor::adoption':'cursor','AdoptionBodyV1::proof':'proof',
 'swift::ValidatedSwiftReactor::usage':'validation_usage','execute::Cancellation::requested_backing_layout':'backing_layout',
 '<control::SwiftLiveUsage as Default>::default':'live_default','<control::SwiftReservations as Default>::default':'reservations_default',
 'accounted_header_bytes':'accounted_header_bytes','WasiContext::usage':'wasi_context_usage',
 'accounted::AccountedWasi::usage':'wasi_usage','control::RuntimeControl::finish_owned_cleanup':'finish_owned_cleanup',
}
ROOT_SELECT={
 'core':('adopt_body_core_v1','_1: AdoptionBodyV1'),
 'drop_proof':('drop_proof_with_wasi','_2: control::AdoptedProof'),
 'outer_retire':('retire_v1','_1: SnapshotOuterV1'),
 'construct_forward':('construct_snapshot_in_scope_v1',None),
 'construct_owned':('construct_snapshot_owned_v1',None),
 'wasi_pair':('snapshot_pair_v1','_1: &accounted::AccountedWasi'),
 'cache_cleanup':('cleanup','_1: &mut Option<experimental_swift_reactor::cache::SwiftFunctionCache>'),
 'cache_complete':('complete',"_1: experimental_swift_reactor::cache::CacheCleanupTail<'_>"),
 'drop_cleanup_storage':('drop_cleanup_return_storage','cache::CacheCleanupTail'),
 'snapshot_ticket':('snapshot_ticket_v1',None),'snapshot_ticket_identity':('snapshot_ticket_identity_v1',None),
}
NEW_MAP={
 'control::RuntimeControl::drop_proof_with_wasi':'drop_proof',
 'construct_snapshot_owned_v1':'construct_owned',
 'experimental_swift_reactor::cache::drop_cleanup_return_storage':'drop_cleanup_storage',
 'control::RuntimeControl::snapshot_ticket_v1':'snapshot_ticket',
 'control::RuntimeControl::snapshot_ticket_identity_v1':'snapshot_ticket_identity',
}

def derive(write=True):
 inputs={}
 def read(p):
  b=p.read_bytes();inputs[str(p.relative_to(ROOT))]=dict(bytes=len(b),sha256=sha(b));return b
 def load(p):return json.loads(read(p))
 seals=[check_seal(V/'swift-guarded-snapshot-leaf-shell-cost','10321f6bdadbe8ff193d553063b978e59857f7390e243e63054f0d4e1997cd57'),check_seal(V/'swift-guarded-snapshot-source146-leaf-payload-layouts','f2021a5fa0be89481bc02bdb811ec6ac2fb5e4112900a9f1e831135070be2952')]
 for s in seals:read(ROOT/s['path']/'seal.json')
 manifest=load(V/'swift-guarded-snapshot-leaf-shell-cost/source-manifest.json')
 if manifest['tree_sha256']!=TREE or len(manifest['members'])!=146 or sha(canon(manifest['members']))!=TREE:raise ValueError('source146 manifest')
 src={}
 for row in manifest['members']:
  p=OVER/row['path'];p=p if p.exists() else BASE/row['path'];b=read(p)
  if (len(b),sha(b))!=(row['bytes'],row['sha256']):raise ValueError('source146 member')
  src[row['path']]=b.decode()
 source_shapes=shapes.SourceShapes({p:s.encode() for p,s in src.items()})
 raw=gzip.decompress(read(V/'swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz'))
 if sha(raw)!='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2':raise ValueError('MIR identity')
 fs=functions(raw.decode())
 old=load(V/'swift-guarded-snapshot-ingress-work/ledger.json')
 full=load(V/'swift-semantic-adapter-root-review/guarded-snapshot-full-work-host-acceptance.json')
 if full['status']!='accepted-bounded-logical-work-interface-for-closed-source144-route':raise ValueError('prior acceptance')
 check_seal(V/'swift-guarded-snapshot-ingress-work','75775a7df0048888ab95b40d58831d22e05ea2e3935781904e9a83b57f556561')
 check_seal(V/'swift-guarded-snapshot-complete-work-plan','7198ae0748ce0c8c576afc953aef8f3827b0a0d925ea246225245ba4cf000a27')
 priorplan=load(V/'swift-guarded-snapshot-complete-work-plan/ledger.json')
 layouts={}
 for t,n in load(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')['actual_type_sizes'].items():layouts[normalize(t)]=n
 for r in load(V/'swift-guarded-snapshot-source146-leaf-payload-layouts/results.json')['queries']:layouts[r['key']]=r['size']
 layouts.update({'()':0,'bool':1,'u8':1,'u16':2,'u32':4,'u64':8,'u128':16,'i8':1,'i16':2,'i32':4,'i64':8,'i128':16,'usize':8,'isize':8,'f32':4,'f64':8,'char':4})
 nodes={};mrs={};pending=[];rebinding=[]
 def add_old(n):
  key='accepted::'+n
  if key in nodes:return key
  r=old['rows'][n];b=old['source_bindings'][r['binding']]
  if b['source'] not in src[b['path']]:
   if n=='foundation':
    actual=extract(src[b['path']],'fn foundation_construction_bytes(')
    if actual!='fn foundation_construction_bytes() -> Option<usize> {\n    COMMON_FOUNDATION_CONSTRUCTION_BYTES_V1\n}':raise ValueError('foundation changed complexity')
    nodes[key]=dict(kind='source-derived-constant-getter',own=3,calls={},payload={},primitive={},parts={'enter_return':2,'actual_precomputed_Option_fetch':1},binding=dict(path=b['path'],source=actual,sha256=sha(actual.encode())),native_policy='accepted logical callsite unit; separately imported library/native/backing allowance')
    rebinding.append(dict(row=n,status='new-concrete-getter3-not-claimed-byte-identical',source_sha256=sha(actual.encode())))
    return key
   raise ValueError('accepted body mismatch '+n)
  nodes[key]=dict(kind='accepted-specific-row-own-actions',own=r['own_actions'],parts=r['parts'],calls={},payload={},primitive={},binding=dict(path=b['path'],source=b['source'],sha256=b['sha256']),source_loops=r['loops'],native_policy='accepted requested native byte/callsite convention retained, private native lowering separately imported')
  rebinding.append(dict(row=n,status='byte-identical-body-and-recursively-rebound-explicit-callees',source_sha256=b['sha256']))
  nodes[key]['calls']={add_old(child):count for child,count in r['calls'].items()}
  return key
 def select(name,contains=None,context=None):
  pat=r'(?:::|^fn )'+re.escape(name)+r'(?:<[^\n]*>)?\('
  candidates=[b for b in fs if re.search(pat,b.splitlines()[0]) and (contains is None or contains in b.splitlines()[0])]
  if context and len(candidates)>1:
   tag='experimental_swift_reactor/cache.rs:' if 'cache.rs:' in context else 'experimental_swift_reactor/control.rs:' if 'control.rs:' in context else 'experimental_wasi/accounted.rs:'
   module='fn experimental_swift_reactor::cache::' if 'cache.rs:' in context else 'fn control::' if 'control.rs:' in context else 'fn accounted::'
   filtered=[b for b in candidates if tag in b.splitlines()[0] or b.startswith(module)]
   if filtered:candidates=filtered
  if len(candidates)!=1:raise ValueError('ambiguous MIR '+name+' '+str([b.splitlines()[0] for b in candidates]))
  return candidates[0]
 def add_new(key,body=None):
  if key in nodes:return key
  if body is None:
   name,contains=ROOT_SELECT[key];body=select(name,contains)
  nodes[key]={'kind':'MIR-all-written-block-upper'};mrs[key]=body;pending.append(key);return key
 for key in ROOT_SELECT:add_new(key)
 def callback(callee):
  spans=set(re.findall(r'\{closure@[^}]+\}',callee));result=[]
  for span in spans:
   cand=[b for b in fs if span in b.splitlines()[0] and re.search(r'::\{closure#\d+\}\(',b.splitlines()[0])]
   if len(cand)!=1:raise ValueError('missing/ambiguous closed callback '+span)
   k='closure::'+sha(cand[0].splitlines()[0].encode())[:20];add_new(k,cand[0]);result.append(k)
  return result
 def payload(ty):return 'payload::'+normalize(ty)
 def edge(callee,caller):
  if callee in REUSE:return [('call',add_old(REUSE[callee]))]
  for base,target in NEW_MAP.items():
   if callee==base or callee.startswith(base+'::<'):return [('call',add_new(target))]
  if callee.startswith('control::RuntimeControl::drop_reserved_with_wasi::<'):
   t=callee.split('::<',1)[1][:-1];return [('call',add_old('drop_reserved_with_wasi')),('payload',payload(t))]
  if callee.startswith('std::mem::drop::<'):
   return [('payload',payload(callee.split('::<',1)[1][:-1]))]
  if callee=='foundation_construction_bytes':return [('call',add_old('foundation'))]
  if callee=='<P as ClosedAdoptionV1>::foundation':return [('call',add_new('policy_foundation',select('foundation','control.rs:1909:1:',caller)))]
  if callee=='<P as ClosedAdoptionV1>::failure':return [('call',add_new('policy_failure',select('failure','-> SnapshotPreScopeFailureV1',caller)))]
  if callee=='<P as ClosedAdoptionV1>::retire_tickets':return [('call',add_new('policy_retire',select('retire_tickets','-> Result<(), control::SwiftRunFailure>',caller)))]
  if callee.startswith('construct_profile_core_v1::<'):return [('call','accepted_constructor_region')]
  # These are exact authored function/method calls, never an unresolved primitive.
  product=not(callee.startswith(('<','Option::','Result::','Vec::','std::','core::','Atomic::','Duration::','Instant::','Layout::','ptr::')))
  if product:
   name=re.search(r'(\w+)(?:::<.*>)?$',callee)[1]
   body=select(name,context=caller);key='authored::'+sha(body.splitlines()[0].encode())[:20]
   return [('call',add_new(key,body))]
  callbacks=[('call',k) for k in callback(callee)]
  if 'AccountedWasi::usage}' in callee:callbacks.append(('call',add_old('wasi_usage')))
  # Closed standard adapter/primitive source event once, with operand/return
  # scalar and native transfer surfaces already charged at this exact callsite.
  # Private std implementation, panic/unwind and retries remain external.
  return [('closed-primitive',callee)]+callbacks
 # Named accepted constructor subset, once at its actual concrete callsite.
 # All eleven original rows are conservatively prepaid. No finish/outer/ingress
 # aggregate is assigned to any other caller; no subtraction/discount is made.
 constructor_terms={r['name']:r['total'] for r in priorplan['original_added_rows']}
 constructor_terms.update(original_rows=priorplan['original_row_source_and_requested_IO'],layout_tail=priorplan['layout_tail_delta']['total'],proof_delegation=15,core_guard=15,branch_early=7,branch_begin=2,branch_export=13,refusal_copy=306,branch_finish=14,owned_getter=4,begin_predebit=2871,planning=16384,completion_envelope=priorplan['extra_snapshot_completion_envelope'])
 nodes['accepted_constructor_region']=dict(kind='accepted-named-constructor-contained-region',own=sum(constructor_terms.values()),parts=constructor_terms,calls={},payload={},primitive={},requires_route='one-authentic-ingress/no-intervening-mutation/no-WASI/one-consuming-construct',source_only=True,native_policy='accepted requested native/IO unit; private lowering/backing and payload external')
 # Semantic source rebind of changed concrete owned-constructor closure is
 # checked later in constructor applicability; successful export is unreachable.
 while pending:
  key=pending.pop(0);body=mrs[key];h=body.splitlines()[0];arg=h.split('(',1)[1].rsplit(') -> ',1)[0]
  rawroles=re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',arg)+re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$',body,re.M)
  rs={}
  for n,ty in rawroles:
   ty=type146(ty)
   try:scalars=source_shapes.n(ty);pt,pts,unsized=shapes.pointees(ty,source_shapes)
   except Exception as e:source_shapes.active=[];raise ValueError(key+' '+ty+': '+str(e)) from e
   rs[n]=dict(type=ty,scalars=scalars,pointee_scalars=pt,pointee_types=dict(pts),unsized=dict(unsized))
  # Every concrete captured projection is also charged, so a closure pointer
  # cannot erase the control/proof/validation payload behind its environment.
  captured=[]
  for mm in re.finditer(r'_\d+\)?\.\d+: ',body):
   start=mm.end();depth=0;i=start
   while i<len(body):
    ch=body[i]
    if ch in '<[(':depth+=1
    elif ch in '>])':
     if ch==')' and depth==0:break
     depth-=1
    i+=1
   ty=type146(body[start:i]);captured.append(ty)
  closure_n=0;closure_pts=collections.Counter();closure_unsized=collections.Counter()
  for ty in set(captured):
   nn=source_shapes.n(ty);p,ts,us=shapes.pointees(ty,source_shapes);closure_n+=nn+p;closure_pts.update(ts);closure_pts[normalize(ty)]+=1;closure_unsized.update(us)
  for n,r in rs.items():
   if '{closure@' in r['type']:
    r['pointee_scalars']+=closure_n
    for t,c in closure_pts.items():r['pointee_types'][t]=r['pointee_types'].get(t,0)+c
    for t,c in closure_unsized.items():r['unsized'][t]=r['unsized'].get(t,0)+c
  graph,cycles=sccs(shapes.mir_blocks(body));blocks=shapes.mir_blocks(body);mult={n:1 for n in blocks};looprows=[]
  if cycles:
   if key=='cache_cleanup':bound=64;expected=2;proof='fresh selected constructor has at most64 pin records and64 slots; no intervening cache mutation'
   elif key=='wasi_pair':bound=4;expected=2;proof='two distinct buffers[4] iterations, identity and zip capacities[4]'
   else:raise ValueError('unselected cyclic authored body '+key)
   if len(cycles)!=expected:raise ValueError('changed loop SCC count '+key)
   for c in cycles:
    for n in c:mult[n]=bound+1
    looprows.append(dict(blocks=c,max_iterations=bound,block_visits_upper=bound+1,proof=proof))
  own=0;sizes=collections.Counter();us=collections.Counter();calls=collections.Counter();drops=collections.Counter();prims=collections.Counter();ops=[];known=0
  for bid,block in blocks.items():
   for no,code in block['lines']:
    weight=mult[bid];mentions=re.findall(r'\b_\d+\b',code)
    if code=='return;':mentions+=['_0']
    if set(mentions)-set(rs):raise ValueError('missing role')
    constants=[]
    for cm in re.finditer(r'\bconst\s+"(?:\\.|[^"\\])*"',code):constants.append(json.loads(cm[0].split('const ',1)[1]))
    scalar=2*sum(rs[x]['scalars']+rs[x]['pointee_scalars'] for x in mentions)+2*sum(1+len(x.encode()) for x in constants)
    base=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code))
    # Every nonstring constant occurrence is one scalar event. Its requested
    # native width remains explicitly covered by the lowering/native allowance.
    scalar+=2*(len(re.findall(r'\bconst\s+',code))-len(constants))
    action=base+scalar;own+=weight*action;opdict=dict(block=bid,line=no,weight=weight,code=code,source=action,mentions=mentions,edges=[])
    for x in mentions:
     r=rs[x];sizes[normalize(r['type'])]+=2*weight
     sizes.update({t:2*c*weight for t,c in r['pointee_types'].items()});us.update({t:2*c*weight for t,c in r['unsized'].items()})
    op_native=collections.Counter();op_unsized=collections.Counter()
    for x in mentions:
     rr=rs[x];op_native[normalize(rr['type'])]+=2
     op_native.update({t:2*c for t,c in rr['pointee_types'].items()});op_unsized.update({t:2*c for t,c in rr['unsized'].items()})
    opdict.update(native=dict(op_native),unsized=dict(op_unsized),known_constant_bytes=2*sum(len(x.encode()) for x in constants))
    known+=2*weight*sum(len(x.encode()) for x in constants)
    if ' -> [' in code and not code.startswith(('switchInt(','assert(')):
     if code.startswith('drop('):
      local=re.search(r'\b_\d+\b',code)[0];edges=[('payload',payload(rs[local]['type']))]
     else:
      expression=code.split(' = ',1)[1].split(' -> [',1)[0];callee=expression[:expression.rfind('(')];edges=edge(callee,h)
     for kind,target in edges:
      if kind=='call':calls[target]+=weight
      elif kind=='payload':drops[target]+=weight
      else:prims[target]+=weight;own+=weight
      opdict['edges'].append(dict(kind=kind,target=target))
    ops.append(opdict)
  known+=sum(c*layouts[t] for t,c in sizes.items() if t in layouts)
  for t in sizes:
   if t.startswith('&') and not re.search(r'&(?:mut )?(?:str|\[[^;]*\])$',t):layouts.setdefault(t,8)
  known=sum(c*layouts[t] for t,c in sizes.items() if t in layouts)+sum(o['weight']*o['known_constant_bytes'] for o in ops)
  missing={t:c for t,c in sizes.items() if t not in layouts}
  nodes[key].update(own=own,roles=rs,loops=looprows,graph=graph,operations=ops,calls=dict(calls),payload=dict(drops),primitive=dict(prims),known_native=known,missing_native=missing,unsized=dict(us),MIR_sha256=sha(body.encode()),MIR_header=h,captured_projection_types=sorted(set(captured)))
 # Additional typed destructor imports beyond accepted abstract drop callsites.
 for n,terms in {'wasi_cleanup':{'Vec<u8>':8,'AccountedWasi':2},'finish_owned_cleanup':{'RuntimeControl':2}}.items():
  k=add_old(n);nodes[k]['payload'].update({payload(t):c for t,c in terms.items()})
 exports={
  'core_before_fixed_store':'core_before_fixed_store','core_fixed_store_and_after':'core_fixed_store_and_after',
  'callee::SnapshotOuterV1::retire_v1':'outer_retire','callee::accounted::AccountedWasi::cleanup':add_old('wasi_cleanup'),
  'callee::accounted::AccountedWasi::snapshot_pair_v1':'wasi_pair','callee::accounted::AccountedWasi::usage':add_old('wasi_usage'),
  'callee::construct_snapshot_in_scope_v1':'construct_forward','callee::control::RuntimeControl::drop_proof_with_wasi':'drop_proof',
  'callee::control::RuntimeControl::finish_owned_cleanup':add_old('finish_owned_cleanup'),
  "callee::experimental_swift_reactor::cache::CacheCleanupTail::<'_>::complete::<Option<experimental_swift_reactor::cache::SwiftFunctionCache>>":'cache_complete',
  'callee::experimental_swift_reactor::cache::SwiftFunctionCache::cleanup':'cache_cleanup',
 }
 return dict(schema=1,source_tree_sha256=TREE,source_members=146,nodes=nodes,exports=exports,accepted_rebindings=rebinding,input_bindings=inputs,input_seals=seals,layouts=layouts,source=src,mir=mrs,priorplan=priorplan)
def finish(result):
 nodes=result['nodes'];src=result.pop('source');mir=result.pop('mir');layouts=result['layouts']
 # The exact store is isolated inside the closed generic callback. The full
 # outer frame is prepaid on the before side, including return/refusal/unwind
 # scaffolding which may run later. Shared callback tails are conservatively
 # charged on both sides; the counter-store operation appears only after.
 core=nodes['core']; ck=next(k for k in core['calls'] if k.startswith('closure::'))
 callback=nodes[ck]; stores=[o for o in callback['operations'] if re.fullmatch(r'\(\(\*_\d+\)\.10: u64\) = const <P as experimental_swift_reactor::control::ClosedAdoptionV1>::FIXED_EXECUTION_WORK_V1;',o['code'])]
 if len(stores)!=1:raise ValueError('exact fixed-counter store missing')
 store=stores[0]
 def reachable(start,stop=None):
  done=set();todo=[start]
  while todo:
   b=todo.pop()
   if b in done or b==stop:continue
   done.add(b);todo.extend(callback['graph'][b])
  return done
 # Selected policy has fixed451814442>0. Its zero-policy bypass is not
 # admitted. Preserve the generic MIR separately but prune only this proven
 # constant branch when selecting the concrete pre-store interval.
 fixed_test=[o for o in callback['operations'] if o['code'].startswith('_38 = Ne(const <P as ')]
 if len(fixed_test)!=1 or callback['graph']['bb16']!=['bb19','bb20']:raise ValueError('selected-policy branch shape changed')
 callback['graph']=dict(callback['graph']);callback['graph']['bb16']=['bb19']
 before=reachable('bb0',store['block']);after=reachable(store['block'])
 if store['block'] in before:raise ValueError('store leaked before cut')
 def portion(name,chosen):
  own=0;calls=collections.Counter();payload=collections.Counter();primitive=collections.Counter();native=collections.Counter();unsized=collections.Counter();constant=0
  for op in chosen:
   w=op['weight'];own+=w*op['source'];native.update({t:w*n for t,n in op['native'].items()});unsized.update({t:w*n for t,n in op['unsized'].items()});constant+=w*op['known_constant_bytes']
   for e in op['edges']:
    if e['kind']=='call':calls[e['target']]+=w
    elif e['kind']=='payload':payload[e['target']]+=w
    else:primitive[e['target']]+=w;own+=w
  return dict(kind='exact-MIR-phase-upper',own=own,calls=dict(calls),payload=dict(payload),primitive=dict(primitive),known_native=constant+sum(n*layouts[t] for t,n in native.items() if t in layouts),missing_native={t:n for t,n in native.items() if t not in layouts},unsized=dict(unsized),operations=chosen,source_parent='core',phase=name)
 bp=portion('before-fixed-store',[o for o in callback['operations'] if o['block'] in before]);ap=portion('fixed-store-and-after',[o for o in callback['operations'] if o['block'] in after])
 nodes['core_callback_before']=bp;nodes['core_fixed_store_and_after']=ap
 pre=dict(core);pre['calls']=dict(core['calls']);pre['calls'].pop(ck);pre['calls']['core_callback_before']=1;pre['kind']='outer-core-frame-prepaid-with-before-callback'
 nodes['core_before_fixed_store']=pre
 # Give each new MIR body a concrete source parent, never a lexical trait
 # declaration. The compiler header resolves the impl interval; exact146 source
 # custody and full MIR custody establish the body/call/cleanup graph together.
 sourcebindings={}
 for key,b in mir.items():
  head=b.splitlines()[0];hm=re.search(r'(?:^fn |>::|::)([A-Za-z_]\w*)(?=(?:::\{closure#\d+\})*\()',head)
  if not hm:raise ValueError('unbound source function '+head)
  name=hm[1];location=re.search(r'/src/([^:]+\.rs):(\d+):\d+:',head)
  candidates=[]
  for p,text in src.items():
   if not p.endswith('.rs') or '/tests/' in p or p.endswith('_tests.rs'):continue
   if location and p!='src/'+location[1]:continue
   if not location and head.startswith('fn experimental_swift_reactor::cache::') and p!='src/experimental_swift_reactor/cache.rs':continue
   for match in re.finditer(r'\bfn '+re.escape(name)+r'\b',text):
    # A trait-only semicolon before the opening body is ineligible.
    opening=text.find('{',match.end());semicolon=text.find(';',match.end())
    if semicolon!=-1 and semicolon<opening:continue
    line=text[:match.start()].count('\n')+1
    closure_parent='::{closure#' in head and '<impl at ' not in head
    if location and ((closure_parent and line>int(location[2])) or (not closure_parent and line<int(location[2]))):continue
    fragment=extract(text,'fn '+name,text[:match.start()].count('fn '+name))
    candidates.append((line,p,fragment))
  if location and candidates:candidates=[max(candidates) if ('::{closure#' in head and '<impl at ' not in head) else min(candidates)]
  if len(candidates)!=1:raise ValueError('ambiguous source body '+key+' '+str([(a,p) for a,p,_ in candidates]))
  line,p,fragment=candidates[0];sourcebindings[key]=dict(path=p,line=line,function=name,source=fragment,sha256=sha(fragment.encode()),bytes=len(fragment.encode()),MIR_sha256=sha(b.encode()))
 # Close Copy/primitive destructor adapters; actual resource payloads remain
 # positive imported interfaces owned by the separate payload lane.
 adapters={}
 for n in nodes.values():
  for term in list(n['payload']):
   ty=term[len('payload::'):];count=n['payload'][term]
   if ty in ('()','Result<(), SwiftRunFailure>') or ty.startswith('Zip<'):
    n['own']+=count;n['payload'].pop(term);adapters[term]=dict(logical_drop_events=1,actual_payload=False,reason='Copy/closed standard iterator over borrowed references and usize array; no owned resource payload')
   elif ty=='(Option<SwiftFunctionCache>, Option<SwiftRunFailure>)':
    n['own']+=count;n['payload'].pop(term);n['payload']['payload::Option<SwiftFunctionCache>']=n['payload'].get('payload::Option<SwiftFunctionCache>',0)+count;adapters[term]=dict(logical_drop_events=1,actual_payload='payload::Option<SwiftFunctionCache>',reason='tuple forwarding plus Copy Option<SwiftRunFailure>; resource destruction remains imported')
 # Remaining direct standard callees from the frozen eight-body leaf interface.
 leaf=json.loads((V/'swift-guarded-snapshot-leaf-shell-cost/cost-interface.json').read_text())
 for term in leaf['required_nonzero_callee_drop_and_backing_cuts']:
  if term in result['exports'] or not term.startswith('callee::'):continue
  name='adapter::'+sha(term.encode())[:20]
  if 'std::mem::drop::' in term:
   nodes[name]=dict(kind='closed-standard-drop-adapter',own=1,calls={},payload={'payload::Option<SwiftFunctionCache>':1},primitive={})
  else:nodes[name]=dict(kind='closed-standard-logical-adapter',own=1,calls={},payload={},primitive={},proof='one closed Option/Result/Try tag/payload transfer event; caller already charges complete operand/result scalar/native occurrences; private std and panic/unwind allowance is mandatory')
  result['exports'][term]=name
 result['source_bindings']=sourcebindings
 result['typed_inline_drop_adapters']=adapters
 result['core_phase_binding']=dict(source=sourcebindings['core'],counter_store=store,pre_callback_blocks=sorted(before),post_callback_blocks=sorted(after),overlap_blocks=sorted(before&after),outer_frame_charged_before_once=True,all_shared_exit_scaffolding_prepaid_before=True,store_charged_only_after=True,ordinary_zero_policy_refused_by_evaluator=True)
 # Source144 constructor reuse is a contained region of the individually named
 # original rows plus applicable wrapper/begin/phase envelopes, paid only at
 # construct_profile_core_v1. It is not the product451814442 aggregate.
 oldbase=V/'swift-guarded-snapshot-scope-authority-correction/source/vm'; reb=[]
 for p in ['src/experimental_swift_reactor/cache.rs','src/experimental_wasi/accounted.rs','src/experimental_swift_reactor/diagnostic_profile.rs','src/experimental_swift_reactor/cache/initial_profile_v1/header.rs','src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs']:
  a=(oldbase/p).read_bytes();b=src[p].encode()
  if a!=b:raise ValueError('constructor inherited whole-file mismatch '+p)
  reb.append(dict(path=p,bytes=len(b),sha256=sha(b),relationship='byte-identical-accepted-source144-to-source146'))
 p='src/experimental_swift_reactor/cache/initial_profile_v1.rs';a=(oldbase/p).read_text();b=src[p]
 # Appended host/leaf declarations are outside the constructor. The only
 # earlier source changes are exact retained-bound identifier forwarding,
 # an unused additive module declaration and a compile-time size constant.
 a=a.replace('previous:usize','retained:usize').replace('control,previous,wasi','control,retained,wasi').replace('storage,previous,wasi','storage,retained,wasi').replace('let previous=control.snapshot_commit_storage_v1','let retained=control.snapshot_commit_storage_v1').replace('((previous,shape,planning,emission))','((retained,shape,planning,emission))').replace('Ok((previous,shape,planning,emission))','Ok((retained,shape,planning,emission))')
 a=a.replace('fn proposed_emission_work_v1','// Additive unused candidate; WorkAuditPending below is unchanged.\nmod emission_bound_v1;\n\nfn proposed_emission_work_v1').replace('const SNAPSHOT_PHASE_PLACES_V1:usize=size_of::<SnapshotPhasePlacesV1<\'static>>();','const SNAPSHOT_PHASE_PLACES_V1:usize=super::super::control::SNAPSHOT_ADMITTED_SOURCE_EXTRA_BYTES_V1;')
 if not b.startswith(a.rstrip('\n')):raise ValueError('constructor initial-profile semantic source rebind changed')
 refusal=extract(b,'fn proposed_emission_work_v1(')
 if 'Err(AError::WorkAuditPending)' not in refusal or 'Ok(' in refusal:raise ValueError('writer suffix became reachable')
 control=src['src/experimental_swift_reactor/control.rs'];oldcontrol=(oldbase/'src/experimental_swift_reactor/control.rs').read_text()
 # Every unchanged helper named by the accepted plan and every concrete
 # snapshot_* operation before the refusal is bound individually. The changed
 # snapshot_commit_storage is after an unconditional Err and is not entered.
 helpers=['check_budget','check_with_wasi','usage','fail','admit','admit_with_wasi','end_construction_phase_with_wasi','refund_with_wasi','finish_owned_cleanup','record_cleanup','cleanup_fault_with_wasi','snapshot_existing_v1','snapshot_owner_v1','snapshot_ticket_v1','snapshot_ticket_identity_v1','snapshot_adopted_pair_v1','snapshot_foundation_pair_v1','snapshot_totals_v1','snapshot_storage_preflight_v1','snapshot_debit_v1','snapshot_observe_stop_v1']
 for name in helpers:
  try:aa=extract(oldcontrol,'fn '+name+'(');bb=extract(control,'fn '+name+'(')
  except ValueError:
   # Generic end_construction_phase uses a bounded generic marker.
   if name=='end_construction_phase_with_wasi':aa=extract(oldcontrol,'fn '+name+'<');bb=extract(control,'fn '+name+'<')
   else:raise
  if aa!=bb:raise ValueError('constructor helper source rebind '+name)
  reb.append(dict(path='src/experimental_swift_reactor/control.rs',function=name,sha256=sha(bb.encode()),bytes=len(bb.encode()),relationship='byte-identical-source144-body'))
 result['constructor_applicability']=dict(named_price=nodes['accepted_constructor_region']['own'],terms=nodes['accepted_constructor_region']['parts'],source_rebindings=reb,initial_profile_normalization='exact retained identifier forwarding, unused module and const-only430175 replacement; old entire body prefix otherwise identical',unconditional_refusal_body=refusal,writer_encoder_initializer_entered=False,changed_snapshot_commit_storage_entered=False,scope='only current one-shot selected constructor, fixed original row helper625 blocks/20000 IO calls; no cache execution/pin/mutation between construction and cleanup',product451814442_transferred=False,product_work_discount=0,cleanup_wrappers_reserved_separately_without_credit=True,actual_payload_destructors_separately_imported=True)
 constructor_payload={'Partial':5,'Vec<SwiftSlot>':2,'Vec<PinRecord>':2,'Vec<Patch>':2,'Vec<u8>':2,'Vec<Option<ScanPlan>>':2,'AdoptedProof':4,'AdoptionBodyV1':1,'CacheConstructionFailure':1,'Option<Result<SwiftFunctionCache, CacheConstructionFailure>>':1,'InitialProfileConstructionOutcomeV1':1,'SnapshotAttemptV1':2}
 nodes['accepted_constructor_region']['payload']={'payload::'+t:n for t,n in constructor_payload.items()}
 result['constructor_applicability']['typed_internal_destructor_cuts']=constructor_payload
 result['constructor_applicability']['typed_internal_destructor_multiplicity']='all written normal+unwind sites in once-only Partial.cleanup, phase.construct and construct_profile_core; three cleanup drop_reserved Vec calls and one Partial self call included; no simultaneous-owner inference'
 result['constructor_applicability']['inline_only_phase_storage_drop']='SnapshotPhaseStorage plan/transfer/refusal and borrow-only SnapshotAccess/SnapshotBranch contain no owned resource payload; source primitives only'
 oldmanifest=json.loads((V/'swift-guarded-snapshot-scope-authority-correction/source-manifest.json').read_text())
 if oldmanifest['source_tree_sha256']!='575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896':raise ValueError('old source144 identity')
 for row in oldmanifest['members']:
  raw=(oldbase/row['path']).read_bytes()
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('old source144 member')
  result['input_bindings'][str((oldbase/row['path']).relative_to(ROOT))]=dict(bytes=len(raw),sha256=sha(raw))
 manifestpath=V/'swift-guarded-snapshot-scope-authority-correction/source-manifest.json';manifestbytes=manifestpath.read_bytes();result['input_bindings'][str(manifestpath.relative_to(ROOT))]=dict(bytes=len(manifestbytes),sha256=sha(manifestbytes))
 releasepath=V/'swift-semantic-adapter-root-review/guarded-snapshot-leaf-shell-cost-independent-release.json';releasebytes=releasepath.read_bytes();result['input_bindings'][str(releasepath.relative_to(ROOT))]=dict(bytes=len(releasebytes),sha256=sha(releasebytes))
 result.pop('priorplan')
 return result

if __name__=='__main__':
 if (HERE/'seal.json').exists():raise SystemExit('frozen packet: use verify.py')
 result=finish(derive());out('callee-ledger.json',result);print(len(result['nodes']),'nodes',len(result['exports']),'exports')
