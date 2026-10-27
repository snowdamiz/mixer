#!/usr/bin/env python3
"""Exact146 compile-data derivation; no source/runtime/compiler invocation."""
from pathlib import Path
import collections, gzip, hashlib, json, platform, re, sys
sys.dont_write_bytecode = True
import model
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
V=ROOT/'verification'
COMPOSE=V/'swift-guarded-snapshot-host-composition'
BASE=V/'swift-guarded-snapshot-funding-implementation/source/vm'
LOADER=V/'swift-guarded-snapshot-loader-work-source146'
SOURCE146='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':')).encode()
inputs={}
def read(p):
 b=p.read_bytes();inputs[str(p.relative_to(ROOT))]={'sha256':sha(b),'bytes':len(b)};return b
def load(p):return json.loads(read(p))
def output(n,d):
 (HERE/n).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
def checked(p,digest):
 raw=read(p)
 if sha(raw)!=digest:raise ValueError('changed frozen input '+str(p))
 return json.loads(raw)
def source():
 manifest=load(COMPOSE/'source-manifest.json')
 if manifest['tree_sha256']!=SOURCE146 or sha(canon(manifest['members']))!=SOURCE146 or len(manifest['members'])!=146:raise ValueError('source identity')
 answer={}
 for row in manifest['members']:
  path=row['path'];over=COMPOSE/'overlay/vm'/path
  b=read(over if over.exists() else BASE/path)
  if len(b)!=row['bytes'] or sha(b)!=row['sha256']:raise ValueError('member '+path)
  answer[path]=b
 return answer

def functions(raw):
 result={}
 # compiler output also has const/global/promoted definitions between functions.
 for m in re.finditer(r'^fn .*$',raw,re.M):
  head=m[0]
  name=None
  if head.startswith('fn run_one_loaded_fixture_v1('):name='leaf'
  elif 'retained_profile_loader_v1::<impl' in head:
   if '>::into_snapshot_scope_v1(' in head:name='into_scope'
   elif '>::into_adoption_body_v1(_1: SelectedValidatedProfileV1)' in head:name='selected_into_body'
   elif '>::into_adoption_body_v1(_1: SelectedSnapshotBodyV1)' in head:name='snapshot_into_body'
  elif 'control::<impl' in head:
   for key,n in [('adopt_snapshot_body_v1','adopt_snapshot'),('construct_v1','construct'),('outer_v1','outer'),('finish_v1','finish')]:
    if '>::'+key+'(' in head:name=n
  if name:
   end=re.compile(r'^}\n',re.M).search(raw,m.start())
   if not end:raise ValueError('unterminated MIR')
   body=raw[m.start():end.end()]
   if name in result:raise ValueError('ambiguous function '+name)
   result[name]=body
 if set(result)!={'leaf','into_scope','selected_into_body','snapshot_into_body','adopt_snapshot','construct','outer','finish'}:raise ValueError('missing function')
 return result

def roles(body,shapes):
 h=body.splitlines()[0];arg=h.split('(',1)[1].rsplit(') -> ',1)[0]
 rows=[(n,t,'parameter') for n,t in re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',arg)]
 rows += [(n,t,'return' if n=='_0' else 'local') for n,t in re.findall(r'^\s+let (?:mut )?(_\d+): (.*);(?:\s*//[^\n]*)?$',body,re.M)]
 out={}
 for n,t,k in rows:
  try:leaves=shapes.n(t)
  except Exception as e:raise ValueError(f'{h}\n{n} {t}: {e}') from e
  out[n]=dict(compiler_type=t,kind=k,scalar_leaves=leaves)
 return out

INTERNAL={
 'SelectedValidatedProfileV1::into_snapshot_scope_v1':'into_scope',
 'SelectedValidatedProfileV1::into_adoption_body_v1':'selected_into_body',
 'SelectedSnapshotBodyV1::into_adoption_body_v1':'snapshot_into_body',
 'control::RuntimeControl::adopt_snapshot_body_v1':'adopt_snapshot',
 'SnapshotScopeV1::construct_v1':'construct',
 'SnapshotRunV1::outer_v1':'outer',
 'SnapshotRunV1::finish_v1':'finish',
}

def cut(code,rs):
 if ' -> [' not in code or code.startswith('switchInt('):return None
 if code.startswith('drop('):
  operand=code.split(' -> [',1)[0][5:-1]
  local=re.search(r'\b_\d+\b',operand)[0]
  return dict(kind='required-drop-payload',key='drop_payload::'+model.canonical_type(rs[local]['compiler_type']),operand=operand)
 expr=code.split(' = ',1)[1].split(' -> [',1)[0]
 callee=expr[:expr.rfind('(')]
 if callee in INTERNAL:return dict(kind='included-source-body',key=INTERNAL[callee],callee=callee)
 if callee.startswith('control::RuntimeControl::adopt_body_core_v1'):
  return dict(kind='required-core-split',key='adopt_body_core_v1',callee=callee,split=['core_before_fixed_store','core_fixed_store_and_after'])
 return dict(kind='required-callee',key='callee::'+callee,callee=callee)

def constants(code):
 out=[]
 for m in re.finditer(r'\bconst\s+',code):
  rest=code[m.end():]
  if rest.startswith('"'):
   found=re.match(r'"(?:\\.|[^"\\])*"',rest)
   if not found:raise ValueError('unrecognized string constant')
   value=json.loads(found[0]);b=len(value.encode());out.append(dict(text=found[0],scalar_leaves=1+b,native_bytes=None,string_bytes=b))
  else:
   found=re.match(r'true\b|false\b|\(\)',rest)
   if not found:raise ValueError('unrecognized selected constant '+rest)
   out.append(dict(text=found[0],scalar_leaves=1,native_bytes=0 if found[0]=='()' else 1,string_bytes=0))
 return out

def operation(code,rs):
 mentions=re.findall(r'\b_\d+\b',code)
 if code=='return;':mentions+=['_0']
 if set(mentions)-set(rs):raise ValueError('unbound MIR role')
 cs=constants(code)
 base=2+sum(code.count(c) for c in '()[].*&')+len(re.findall(r'\bas\b',code))
 scalar=2*sum(rs[x]['scalar_leaves']+rs[x]['pointee_scalar_leaves'] for x in mentions)+2*sum(c['scalar_leaves'] for c in cs)
 sizes=collections.Counter();unsized=collections.Counter()
 known_bytes=0
 for x in mentions:
  sizes[model.canonical_type(rs[x]['compiler_type'])]+=2
  sizes.update({t:2*n for t,n in rs[x]['pointee_types'].items()})
  unsized.update({t:2*n for t,n in rs[x]['unsized_pointees'].items()})
 for c in cs:
  if c['native_bytes'] is None:
   sizes['&str']+=2;known_bytes+=2*c['string_bytes']
  else:known_bytes+=2*c['native_bytes']
 return dict(code=code,local_mentions=mentions,constants=cs,base_action_units=base,scalar_fetch_store_units=scalar,source_action_units=base+scalar,native_type_coefficients=dict(sizes),known_constant_bytes=known_bytes,unsized_coefficients=dict(unsized),cut=cut(code,rs))

def body_binding(src,path,name,ordinal=0):
 txt=src[path].decode();found=list(re.finditer(r'\bfn '+name+r'\b',txt))
 if ordinal>=len(found):raise ValueError('missing actual source function '+name)
 m=found[ordinal];start=txt.index('{',m.end());end=model.close_brace(txt,start)+1
 fragment=txt[m.start():end]
 return dict(path=path,line_start=txt[:m.start()].count('\n')+1,line_end=txt[:end].count('\n')+1,source_function_sha256=sha(fragment.encode()),source_function_bytes=len(fragment.encode()),signature=fragment.split('{',1)[0].strip())

def frozen_seal(folder,digest,count):
 s=checked(folder/'seal.json',digest)
 if s['member_count']!=count or len(s['members'])!=count:raise ValueError('sealed roster count')
 for row in s['members']:
  raw=read(folder/row['path'])
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('sealed member '+row['path'])
 return dict(path=str(folder.relative_to(ROOT)),seal_sha256=digest,members=count,bytes=sum(r['bytes'] for r in s['members']))

def derive():
 bindings=[]
 for name,digest in [('guarded-snapshot-host-composition-host-acceptance.json','c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8'),('guarded-snapshot-parent-work-source146-host-acceptance.json','596c92d6269fa39854184b2cd97000390b37a7e28357121b2558f6d7aedb34f2')]:
  accepted=checked(V/'swift-semantic-adapter-root-review'/name,digest);bindings.append(dict(path=name,sha256=digest,status=accepted['status']))
 seals=[]
 for name,digest,count in [('swift-guarded-snapshot-host-composition','2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e',152),('swift-guarded-snapshot-host-composition-independent','c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63',96),('swift-guarded-snapshot-loader-work-source146','1aacaaff5795625739811b2502476c22567c2b5a3bcc9fb096e61fa5c147c976',58),('swift-guarded-snapshot-bootstrap-host-boundary','00f5bf754a13317ac18dd9959a1db4a9b025b16c72fc99a9d4cfddfcc7cb4dba',62)]:
  seals.append(frozen_seal(V/name,digest,count))
 src=source();shapes=model.SourceShapes(src)
 archive=read(LOADER/'whole-source146.mir.gz')
 if sha(archive)!='03b5265c5ae85b3a444f847f1b65af8f31e9fee7697845d6f9699ddf2d8e87e7':raise ValueError('archive digest')
 raw=gzip.decompress(archive)
 if len(raw)!=76655228 or sha(raw)!='e54c8b0f2b5a69ad8c34c0b6a1454dcc8b3b04338c14f11048b44e10a24301a2':raise ValueError('raw MIR digest')
 compiler=load(LOADER/'compiler-receipt.json')
 if compiler['source_tree_sha256']!=SOURCE146 or compiler['product_runtime'] or compiler['exit_code']!=0:raise ValueError('compile-only identity')
 fs=functions(raw.decode())
 profile='src/experimental_swift_reactor/cache/initial_profile_v1.rs';control='src/experimental_swift_reactor/control.rs';loader='src/experimental_swift_reactor/retained_profile_loader_v1.rs'
 declarations={
  'leaf':(profile,'run_one_loaded_fixture_v1',0),
  'into_scope':(loader,'into_snapshot_scope_v1',0),
  'selected_into_body':(loader,'into_adoption_body_v1',1),
  'snapshot_into_body':(loader,'into_adoption_body_v1',0),
  'adopt_snapshot':(control,'adopt_snapshot_body_v1',0),
  'construct':(control,'construct_v1',0),
  'outer':(control,'outer_v1',0),
  'finish':(control,'finish_v1',0),
 }
 layouts=load(V/'swift-guarded-snapshot-host-composition-independent/fresh-layout-results.json')['actual_type_sizes']
 known={}
 for ty,n in layouts.items():
  key=model.canonical_type(ty)
  if key in known and known[key]!=n:raise ValueError('ambiguous layout alias '+key)
  known[key]=n
 # Only an actually measured binding is used. Historical leaf30 sizes are data,
 # not fresh146 layout acceptance, and do not populate this map.
 allsizes=collections.Counter();allunsized=collections.Counter();cuts=collections.Counter();all_actions=0;known_constants=0;ledger=[];internal_edges=[]
 for name,body in fs.items():
  rs=roles(body,shapes)
  for local,row in rs.items():
   n,types,unsized=model.pointees(row['compiler_type'],shapes)
   row.update(pointee_scalar_leaves=n,pointee_types=dict(types),unsized_pointees=dict(unsized))
  graph=model.mir_blocks(body);paths=model.paths(graph);blocks={};actions=0;sites=[]
  for bid,block in graph.items():
   lines=[]
   for no,code in block['lines']:
    op=operation(code,rs);op['MIR_body_line']=no;lines.append(op)
    actions+=op['source_action_units'];allsizes.update(op['native_type_coefficients']);allunsized.update(op['unsized_coefficients']);known_constants+=op['known_constant_bytes']
    if op['cut']:
     c=dict(op['cut'],block=bid,MIR_body_line=no,code=code)
     sites.append(c)
     if c['kind']=='included-source-body':internal_edges.append((name,c['key']))
     elif c['kind']=='required-core-split':cuts.update(c['split'])
     else:cuts[c['key']]+=1
   blocks[bid]=dict(cleanup=block['cleanup'],lines=lines,source_action_units=sum(x['source_action_units'] for x in lines))
  all_actions+=actions
  binding=body_binding(src,*declarations[name]);binding.update(MIR_sha256=sha(body.encode()),MIR_header=body.splitlines()[0])
  ledger.append(dict(function=name,binding=binding,roles=rs,blocks=blocks,terminal_paths=paths,terminal_path_count=len(paths),all_blocks_once_source_action_units=actions,maximum_single_CFG_path_source_action_units=max(sum(blocks[b]['source_action_units'] for b in p) for p in paths),callee_and_drop_sites=sites))
 # Each body can occur at most once within the consuming leaf source graph.
 inbound=collections.Counter(b for a,b in internal_edges)
 if inbound!=collections.Counter({n:1 for n in fs if n!='leaf'}):raise ValueError('unreviewed internal multiplicity')
 todo=[('leaf',set())]
 while todo:
  name,past=todo.pop()
  if name in past:raise ValueError('recursive selected call graph')
  todo.extend((b,past|{name}) for a,b in internal_edges if a==name)
 missing={t:n for t,n in sorted(allsizes.items()) if t not in known}
 known_byte=model.checked_sum([known_constants]+[model.checked_product(n,known[t]) for t,n in allsizes.items() if t in known])
 cuts['private_std_compiler_lowering_and_requested_backing_allowance']=1
 # Includes retained proof buffers, vectors, cancellation and resource internals;
 # no body or dynamic backing cost is authorized by a pointer-width measurement.
 cuts['retained_dynamic_resource_backing_and_native_transfer_allowance']=1
 interface=dict(schema=1,component='W_leaf_shell_source146_v1',source_members=146,source_tree_sha256=SOURCE146,
  host_tree_sha256='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
  status='finite-source-specific-component-proposal-pending-independent-review',
  fixed_source_action_units=all_actions,known_native_occurrence_bytes=known_byte,
  missing_native_occurrence_coefficients=missing,unsized_source_and_native_byte_coefficients=dict(sorted(allunsized.items())),
  required_nonzero_callee_drop_and_backing_cuts=dict(sorted(cuts.items())),
  source_bodies=8,source_body_occurrences_each=1,all_blocks_once_not_simultaneous_liveness=True,
  unit='abstract source action plus scalar leaf fetch/store; native occurrence bytes separately added; requested/dynamic backing and actual callee/destructor bodies are positive separate cuts',
  product_work_discount=0,work451814442_reused_as_shell_or_callee_price=False,product_work451814442_unchanged=True,
  complete_host_quote=False,actual_native_layouts_complete=not bool(missing),actual_callees_priced=False,
  source_body_tests_are_runtime_receipts=False,operational_grant=False,actual_writer_or_fixture_execution=False,
  native_OTA_GA_accepted=False,WorkAuditPending=True,
  excludes=['P0 unknown root/caller policy and complete backing','P1 setup and loader','P2 argument creation','P5 OwnedFixtureOutcome destruction','actual callee and typed payload destructor body work until explicit cuts independently priced','physical/native simulator/emulator/UI/capture/computer use','complete P0/six-child host grant and healthy cleanup'])
 core=body_binding(src,control,'adopt_body_core_v1')
 txt=src[control].decode();store='control.execution_work = P::FIXED_EXECUTION_WORK_V1;'
 if txt.count(store)!=1:raise ValueError('ambiguous fixed store')
 core['fixed_store_line']=txt[:txt.index(store)].count('\n')+1
 core['pre_store_source_slice_sha256']=sha(txt[txt.index('fn adopt_body_core_v1'):txt.index(store)].encode())
 core['pre_store_cut']='core_before_fixed_store';core['store_and_after_cut']='core_fixed_store_and_after'
 overlap=dict(schema=1,exact_source_core_boundary=core,claimed_451814442_discount=0,accepted_core_price_transferred=False,reason='Fixed product counter store starts its stated interval after same-counter commit; prior shell/control/arguments/refusal/native/drop work needs external host prepayment. No exact accepted full-source146 callee-work rebind is established by this packet.',authority_construct_surface_overlap='Existing authority delta may cover some construct source operations; this packet conservatively charges the full concrete constructor surface and claims no subtraction.',future_composition='Any core/store-and-after or authority-cut subtraction needs an exact source-function/callee/operation boundary proof and independently accepted cut; never infer coverage from the aggregate product counter.')
 return {
  'source-manifest.json':load(COMPOSE/'source-manifest.json'),
  'input-custody.json':dict(acceptance_bindings=bindings,seals=seals,inputs=inputs,new_compiler=False,new_product_runtime=False,new_process_inventory=False),
  'compiler-data-binding.json':dict(compiler_version=compiler['compiler_version'],compiler_sha256=compiler['compiler_sha256'],source_tree_sha256=SOURCE146,raw_MIR_sha256=sha(raw),archive_MIR_sha256=sha(archive),scope='retained production metadata/MIR only; no new compiler or runtime'),
  'operation-ledger.json':dict(schema=1,functions=ledger,internal_edges=internal_edges,source_actions_total=all_actions),
  'scalar-shapes.json':dict(schema=1,source_tree_sha256=SOURCE146,definitions=shapes.used,opaque_std_carriers=['File','Error','Cancellation','Instant','Duration','Vec','String','Arc','Rc','Box'],opaque_std_backing_price='required positive separate cut; never native pointer-size zero'),
  'native-occurrence-interface.json':dict(schema=1,all_type_occurrence_coefficients=dict(sorted(allsizes.items())),known_actual146_layouts_used={t:known[t] for t in allsizes if t in known},known_constant_bytes=known_constants,missing_actual146_layouts=sorted(missing),historical_leaf30_layouts_reused=False,byte_dimension_is_not_source_action_dimension=True,scope='Logical per-operation occurrence allowance; no stack/RSS/CPU or liveness inference'),
  'cost-interface.json':interface,
  'accepted-core-boundary-map.json':overlap,
  'cleanup.json':dict(compiler_started=False,product_runtime_started=False,native_simulator_emulator_started=False,UI_capture_computer_use=False,global_process_inventory=False,owned_scratch_created=False,cleanup_required=False,other_project_processes_inspected_or_changed=False),
  'selected-boundaries.mir':'\n'.join(fs.values()),
 }

def main():
 if (HERE/'seal.json').exists():raise ValueError('frozen packet is read-only')
 result=derive()
 for name,value in result.items():
  if isinstance(value,str):(HERE/name).write_text(value)
  else:output(name,value)
 x=result['cost-interface.json'];l=result['operation-ledger.json']
 print(json.dumps(dict(status=x['status'],source_actions=x['fixed_source_action_units'],known_native_bytes=x['known_native_occurrence_bytes'],missing_layouts=len(x['missing_native_occurrence_coefficients']),required_positive_cuts=len(x['required_nonzero_callee_drop_and_backing_cuts']),roles=sum(len(f['roles']) for f in l['functions']),written_operations=sum(len(b['lines']) for f in l['functions'] for b in f['blocks'].values()),terminal_paths=sum(f['terminal_path_count'] for f in l['functions']),runtime=False,compiler=False)))
if __name__=='__main__':main()
