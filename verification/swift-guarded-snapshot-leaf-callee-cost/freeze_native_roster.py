from pathlib import Path
import hashlib,json,re,sys
sys.dont_write_bytecode=True
import layouts
H=Path(__file__).resolve().parent;P=H/'native-query-roster';sha=lambda b:hashlib.sha256(b).hexdigest()
def out(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
if (P/'seal.json').exists():raise SystemExit('already frozen')
P.mkdir(exist_ok=True);ledger=json.loads((H/'callee-ledger.json').read_text());obs=json.loads((H/'native-layout-observations.json').read_text());rows=[]
for index,missing in enumerate(obs['missing']):
 key=missing['key'];roles=[];creations=[]
 for n,node in ledger['nodes'].items():
  for local,r in node.get('roles',{}).items():
   if key in node.get('missing_native',{}):
    from derive import normalize
    if normalize(r['type'])==key:roles.append(dict(node=n,local=local,compiler_type=r['type'],MIR_header=node['MIR_header'],source_binding=ledger['source_bindings'].get(n)))
  for op in node.get('operations',[]):
   if 'roles' not in node:continue
   if '= '+key in op['code']:
    captures=[]
    tail=op['code'].split(key,1)[1]
    for name,local in re.findall(r'(\w+): (?:move|copy) (_\d+)',tail):captures.append(dict(field=name,local=local,compiler_type=node['roles'][local]['type']))
    if not any(x['code']==op['code'] for x in creations):creations.append(dict(node=n,code=op['code'],block=op['block'],line=op['line'],captures=captures))
 row=dict(index=index,key=key,qualified_type=missing['qualified'],role_contexts=roles,creation_contexts=creations,source_tree_sha256=ledger['source_tree_sha256'])
 if key.startswith('{closure@'):
  row.update(strategy='unnameable-local-closure-layout',insertion_file='src/experimental_swift_reactor/control.rs',query='query-only local typecheck transmute::<_,[u8;0]>(actual closed closure value), expected size mismatch diagnostic; alternatively isolated codegen/print-type-size instantiation after root authorization',requires_no_runtime=True,actual_capture_fields=[r['captures'] for r in creations],do_not_substitute_named_capture_proxy_as_exact_layout=True)
 else:
  expression=layouts.qualified(key).replace("'_","'static")
  expression=re.sub(r'\b(experimental_swift_reactor|experimental_wasi|experimental)::',r'crate::\1::',expression)
  if expression.startswith('&['):expression="&'static"+expression[1:]
  row.update(strategy='direct-size-and-alignment-E0308-array-length',insertion_file='src/experimental_swift_reactor/cache/initial_profile_v1.rs',insertion_context='append private const diagnostic module in initial_profile_v1, a child of cache, preserving its access to private parent and own local types',size_expression='std::mem::size_of::<'+expression+'>()',alignment_expression='std::mem::align_of::<'+expression+'>()',concrete_type=expression)
 rows.append(row)
out(P/'roster.json',dict(schema=1,source_tree_sha256=ledger['source_tree_sha256'],released_full_layout_observations_sha256=sha((H/'native-layout-observations.json').read_bytes()),full_layout_binding=obs['compiler_binding'],already_resolved_from_full_source146_data=87,remaining_queries=len(rows),named_queries=sum(r['strategy'].startswith('direct') for r in rows),unnameable_closure_queries=sum(r['strategy'].startswith('unnameable') for r in rows),queries=rows,no_compiler_invoked=True))
(P/'README.md').write_text('Frozen residual source146 callee native-layout query roster. Eight named types and five generic-core closure environments remain after87 exact context-qualified substitutions from released raw compiler data and fixed primitive arrays. This is a compile-only insertion plan, not an executed query or runtime permission. Unnameable closure layouts require their exact local creation/capture context; a named capture proxy is not an exact observed closure layout.\n')
ms=[dict(path=str(p.relative_to(P)),bytes=len(p.read_bytes()),sha256=sha(p.read_bytes())) for p in sorted(P.rglob('*')) if p.is_file()]
out(P/'seal.json',dict(schema=1,member_count=len(ms),members=ms,tree_sha256=sha(json.dumps(ms,sort_keys=True,separators=(',',':')).encode())))
print(json.dumps(dict(path=str(P),seal_sha256=sha((P/'seal.json').read_bytes()),members=len(ms),bytes=sum(m['bytes'] for m in ms))))
