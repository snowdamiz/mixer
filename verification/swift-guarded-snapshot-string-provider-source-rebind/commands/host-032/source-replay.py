"""Replay exact finite identities, typed equations, callbacks and carriers."""
from rebind import *
def current_inputs():
 tables=source_tables();text=mir_texts()[3];blocks,coverage=S.parse_mir(text)
 production=[b for b in blocks if not probe(b,3)]
 # This is a declared lifetime projection backed by source-lineage.json and the
 # complete full-base byte/relocation comparison; unknown namespace types survive.
 projected='\n'.join(project(b,span=False,oldroot=True) for b in production)+'\n'
 src={p:b.decode() for p,b in tables[3].items() if p.endswith('.rs')}
 return tables,blocks,production,projected,src
def function_map(blocks):
 old=[b for b in S.parse_mir(mir_texts()[0])[0] if b.startswith('fn ')]
 cur=[b for b in blocks if b.startswith('fn ') and not probe(b,3)]
 index=collections.defaultdict(list)
 for i,b in enumerate(cur):index[shape(b)].append(i)
 rows=[];used=set()
 for i,a in enumerate(old):
  options=[j for j in index[shape(a)] if j not in used];require(options,'original function semantic body missing:'+a.splitlines()[0])
  j=options[0];used.add(j)
  rows.append({'old':f'f{i:04d}','current':f'f{j:04d}','old_header':a.splitlines()[0],'current_header':cur[j].splitlines()[0],
   'old_raw_sha256':sha(a.encode()),'current_raw_sha256':sha(cur[j].encode()),'semantic_shape_sha256':sha(shape(a).encode())})
 return rows
def stable(value):
 # No literal contents may normalize. Allocation references have a separate
 # full payload/relocation proof; names/types/operands otherwise remain exact.
 if isinstance(value,str):return S.allocation_parts(value)[0]
 if isinstance(value,list):return [stable(v) for v in value]
 if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in ('MIR_sha256','MIR_bytes')}
 return value
def selected_transport(graph,blocks,tables):
 mapping=function_map(blocks);forward={r['old']:r['current'] for r in mapping};reverse={b:a for a,b in forward.items()}
 original_blocks=S.parse_mir(mir_texts()[0])[0]
 oldtext='\n'.join(project(b,span=False,oldroot=True) for b in original_blocks)+'\n'
 oldsource={p:b.decode() for p,b in tables[0].items() if p.endswith('.rs')}
 prior=M.analyze(oldtext,oldsource)
 require(set(graph['nodes'])=={forward[k] for k in prior['nodes']},'exact full conservative selected graph; no early-refusal pruning')
 for key,old in prior['nodes'].items():
  current=graph['nodes'][forward[key]]
  require(stable(old)==stable(current),'selected typed semantic body mismatch:'+key)
 def edges(g,undo):
  return sorted([dict(e,caller=undo.get(e['caller'],e['caller']),callee=undo.get(e['callee'],e['callee'])) for e in g['edges']],key=lambda e:(e['caller'],e['line'],e['kind'],e['callee']))
 require(edges(graph,reverse)==prior['edges'],'every authored/named/closure edge conserved')
 require([reverse[k] for k in graph['roots']]==prior['roots'],'selected roots and actual authored Drop conserved')
 # Bind the normal form to the previously accepted raw graph as well.
 accepted=load(OLD/'graph.json');require(set(accepted['nodes'])==set(prior['nodes']),'accepted original root closure')
 raw_by_hash={sha((b+'\n').encode()):b for b in original_blocks if b.startswith('fn ')}
 for key,body in accepted['nodes'].items():
  require(body['MIR_sha256'] in raw_by_hash,'accepted raw body available:'+key)
  raw=raw_by_hash[body['MIR_sha256']]
  require(sha((raw+'\n').encode())==body['MIR_sha256'],'accepted raw body:'+key)
 return {'all_function_rows':mapping,'selected_rows':[r for r in mapping if r['old'] in prior['nodes']],
  'edges_rebound':edges(graph,reverse),'prior_selected_bodies':len(prior['nodes']),'current_selected_bodies':len(graph['nodes']),
  'current_selected_edges':len(graph['edges']),'potential_success_path_retained':True,'root_keys':graph['roots'],
  'same_body_statement_local_signature_callback_semantics':True,'transport_uses_basename_or_body_hash_waiver':False}
def type_equations(graph,projected,src):
 functions,byname,bybase=M.parse_functions(projected,src);rows=[];named=[];closures=[]
 for key,body in graph['nodes'].items():
  for call in body['calls']:
   destinations=M.resolve(call['target'],functions,byname,bybase)
   for dest in destinations:
    decl=functions[dest];bindings={};eq=[]
    for template,actual in zip(list(decl['params'].values())+[decl['return_type']],[a['type'] for a in call['arguments']]+[call['result_type']]):
     if template.startswith('impl Fn'):T.unify_closure(template,actual,bindings,functions)
     else:T.unify(template,actual,bindings)
     eq.append({'template':template,'actual':actual,'bindings_after':dict(bindings)})
    rows.append({'caller':key,'callee':dest,'line':call['line'],'target':call['target'],'equations':eq,'substitutions':bindings})
   for item in call['named_callbacks']:
    targets=M.resolve(item,functions,byname,bybase)
    if targets:named.append({'caller':key,'line':call['line'],'callback':item,'contract':M.validate_named_callback(item,call['target'],targets,functions)})
   for site in call['closures']:
    targets=[k for k,v in functions.items() if v['closure_site']==site]
    closures.append({'caller':key,'line':call['line'],'site':site,'contract':M.validate_closure_callback(site,call,targets,functions)})
 return {'schema':1,'equations':rows,'named_callback_sites':named,'closure_sites':closures,'source_aliases':T.ALIASES,
  'finite_specializations':T.SPECIALIZATIONS,'finite_constant_types':T.CONSTANT_TYPES,'all_compiled_headers':{k:{n:v[n] for n in ('name','params','return_type','local_types')} for k,v in functions.items()}}
def carriers(graph,src):
 induction=module(OLD/'induction.py','string_induction');decls=induction.source_declarations(src)
 names={d['name'] for d in decls if 'str' in d['tokens']}|{'Policy'}
 while True:
  expanded=names|{d['name'] for d in decls if set(d['tokens'])&names}
  if expanded==names:break
  names=expanded
 def carrier(ty):return bool(re.search(r'\bstr\b',ty) or set(re.findall(r'\b[A-Za-z_]\w*\b',ty))&names or '::Failure' in ty)
 inbound=collections.defaultdict(list)
 for e in graph['edges']:
  call=next(c for c in graph['nodes'][e['caller']]['calls'] if c['line']==e['line'])
  inbound[e['callee']].append(dict(e,arguments=call['arguments'],statement=call['statement']))
 ports=[];operations=[]
 for key,b in graph['nodes'].items():
  locals_={k:v for k,v in b['local_types'].items() if carrier(v)}
  for p,ty in b['params'].items():
   if carrier(ty):ports.append({'function':key,'parameter':p,'type':ty,'incoming':inbound[key]})
  for s in b['typed_statements']:
   refs=set(re.findall(r'\b_\d+\b',s['statement']));uses={p:locals_[p] for p in sorted(refs&locals_.keys())}
   if uses or any(n in s['statement'] for n in names):operations.append(dict(s,function=key,carrier_locals=uses))
 return {'schema':1,'declarations':decls,'carrier_names':sorted(names),'incoming_ports':ports,'carrier_operations':operations,
  'all_str_assignments':graph['source_str_assignments'],'direct_ports':graph['direct_str_parameters'],
  'failure_latch_return_retirement_Drop':'Complete selected MIR statement correspondence plus exact current source excerpts preserve literal/code forwards, first-failure latching, typed failure and returned-original retention, original payload retirement, PrepaidOwned Drop and leak-on-unwind behavior. Native backing stays separately priced.'}
def excerpts(tables):
 source=tables[3];oldreview=load(OLD/'source-semantic-review.json');rows=[]
 for x in oldreview['excerpts']:
  current='\n'.join(source[x['path']].decode().splitlines()[x['start']-1:x['end']])
  require(S.source_projection(current).startswith(S.source_projection(x['text'])),'current exact source semantic excerpt:'+x['path']+':'+str(x['start']))
  rows.append(dict(x,current_text=current,current_source_sha256=sha(source[x['path']]),reviewed_lifetime_only_projection=True))
 return rows
def main(check=False):
 tables,blocks,production,projected,src=current_inputs();graph=M.analyze(projected,src)
 transport=selected_transport(graph,blocks,tables);types=type_equations(graph,projected,src);carrier=carriers(graph,src)
 rawmir='\n'.join(production)+'\n';rawfuncs=M.parse_functions(rawmir,src)[0]
 rawheaders={k:{n:r[n] for n in ('name','header','params','return_type','local_types')} for k,r in rawfuncs.items()}
 for name,obj in [('selected-graph.json',graph),('raw-current-typed-headers.json',rawheaders),('definition-role-map.json',transport),('typed-equations.json',types),('carrier-induction.json',carrier),('source-semantic-rebind.json',{'excerpts':excerpts(tables),'failure_route_contract':load(OLD/'failure-routes.json'),'caller_preconditions':load(OLD/'caller-contract.json')})]:save(name,obj,check)
 summary={'compiled_production_functions':graph['compiled_function_bodies'],'selected_bodies':len(graph['nodes']),'selected_edges':len(graph['edges']),'str_assignments':len(graph['source_str_assignments']),'direct_ports':len(graph['direct_str_parameters']),'carrier_ports':len(carrier['incoming_ports']),'named_edges':sum(e['kind']=='named-authored-callback' for e in graph['edges']),'named_sites':len(types['named_callback_sites']),'closure_sites':len(types['closure_sites']),'distinct_exact_closure_contracts':len({c['site']+' | '+str(c['contract']['outer_identity']) for c in types['closure_sites']}),'type_equation_edges':len(types['equations']),'conditional_envelope':graph['L_str_source_candidate'],'selected_success_runtime_qualified':False}
 save('replay-summary.json',summary,check);print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main('--check' in sys.argv)
