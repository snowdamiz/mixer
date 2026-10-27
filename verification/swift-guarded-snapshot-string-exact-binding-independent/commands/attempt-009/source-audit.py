"""Independent retained-data lexer, structural equations and source-origin audit.

No producer analysis imports. This is a finite source146 proof, not a Rust
compiler, general trait solver, or fresh compiler/executable correspondence.
"""
import collections,json,re
from common import *
def lexical(line):
 values=[];i=0
 while i<len(line):
  if line[i:i+2]=='//':return line[:i],values
  if line[i]=="'":
   m=re.match(r"'(?:[^'\\]|\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.))'",line[i:])
   if m:i+=len(m[0]);continue
  if line[i]!='"':i+=1;continue
  binary=i>0 and line[i-1]=='b';i+=1;v=[]
  while i<len(line):
   ch=line[i];i+=1
   if ch=='"':break
   if ch!='\\':v.append(ch);continue
   e=line[i];i+=1
   if e in 'nrt0\\\"\'':v.append({'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}[e])
   elif e=='x':v.append(chr(int(line[i:i+2],16)));i+=2
   elif e=='u':need(line[i]=='{','unicode');z=line.index('}',i);v.append(chr(int(line[i+1:z].replace('_',''),16)));i=z+1
   else:raise ValueError('unsupported cooked escape')
  else:raise ValueError('unclosed cooked string')
  if not binary:values.append(''.join(v))
 return line,values
def split(s,separator=','):
 stack=[];start=0;parts=[];quote=False;escape=False
 for i,ch in enumerate(s):
  if quote:
   if escape:escape=False
   elif ch=='\\':escape=True
   elif ch=='"':quote=False
   continue
  if ch=='"':quote=True;continue
  if ch in '<([{':stack.append(ch)
  elif ch in '>)]}':
   if ch=='>' and i>0 and s[i-1]=='-':continue
   need(stack and stack.pop()=={'>':'<',')':'(',']':'[','}':'{'}[ch],'type delimiter:'+s)
  elif ch==separator and not stack:parts.append(s[start:i].strip());start=i+1
 need(not stack and not quote,'type balance:'+s)
 if s[start:].strip():parts.append(s[start:].strip())
 return parts
def header(line):
 need(line.startswith('fn ') and line.endswith(' {'),'header shape')
 level=0;a=None
 for i,ch in enumerate(line[3:],3):
  if ch=='<':level+=1
  elif ch=='>' and line[i-1]!='-':level-=1
  elif ch=='(' and level==0:a=i;break
 need(a is not None,'outer function params');depth=1;z=a+1
 while depth:
  if line[z]=='(':depth+=1
  elif line[z]==')':depth-=1
  z+=1
 need(line[z:z+4]==' -> ','outer result');params={}
 for item in split(line[a+1:z-1]):
  name,t=item.split(': ',1);need(re.fullmatch('_\\d+',name) and name not in params,'parameter identity');params[name]=t;split(t)
 rt=line[z+4:-2];need(len(split(rt))==1,'complete return');return line[3:a],params,rt
def parse(mir):
 rows={};values=[];alloc=[];current=None;lines=[];in_alloc=False
 for line in mir.splitlines():
  if in_alloc:
   if line=='}':in_alloc=False
   continue
  if line.startswith('alloc') and line.endswith('{'):
   m=re.fullmatch(r'(alloc\w+) \(.*?size: (\d+), align: (\d+)\) \{',line);need(m,'allocation header');alloc.append((m[1],int(m[2]),int(m[3])));in_alloc=True;continue
  code,lits=lexical(line);values.extend(lits)
  if line.startswith('fn '):need(current is None,'nested function');current=f'f{len(rows):04d}';lines=[line];continue
  if current is None:continue
  lines.append(line)
  if line!='}':continue
  name,params,rt=header(lines[0]);locals_={};statements=[]
  for n,line in enumerate(lines,1):
   code,_=lexical(line);statement=code.strip()
   if statement.startswith('let '):
    m=re.fullmatch(r'let (?:mut )?(_\d+): (.*);',statement);need(m,'local declaration');locals_[m[1]]=m[2]
   if line.startswith('        ') and statement:statements.append({'line':n,'statement':statement})
  locals_.update(params);locals_.setdefault('_0',rt);body='\n'.join(lines)+'\n'
  rows[current]={'name':name,'header':lines[0],'params':params,'return_type':rt,'local_types':locals_,'typed_statements':statements,'body':body,'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode())};current=None
 need(current is None and not in_alloc,'complete retained data');return rows,values,alloc
def term(t,aliases,special,constants):
 t=t.strip()
 if t.startswith('exact-compiler-constant:'):
  name=t.split(':',1)[1];need(name in constants,'finite constant');t=constants[name]
 if t in special:return term(special[t],aliases,{},constants)
 if t.startswith('&mut '):return ('mutref',term(t[5:],aliases,special,constants))
 if t.startswith('&'):return ('ref',term(t[1:],aliases,special,constants))
 if t.startswith('(') and t.endswith(')'):return ('tuple',tuple(term(x,aliases,special,constants) for x in split(t[1:-1])))
 if t.startswith('[') and t.endswith(']'):
  parts=split(t[1:-1],';');return ('array' if len(parts)==2 else 'slice',tuple(term(x,aliases,special,constants) for x in parts))
 # Associated receiver paths must match an exact reviewed spelling as a whole.
 if t.startswith('<'):
  for key,value in sorted(special.items(),key=lambda x:-len(x[0])):
   if t.startswith(key+'<'):return term(value+t[len(key):],aliases,{},constants)
 a=t.find('<')
 if a>0 and t.endswith('>'):return ('apply',aliases.get(t[:a].strip(),t[:a].strip()),tuple(term(x,aliases,special,constants) for x in split(t[a+1:-1])))
 return ('atom',aliases.get(t,t))
def solve(a,b,bindings):
 if a==b:return
 if a[0]=='atom' and a[1] in ('T','R','N'):
  key=a[1]
  if key in bindings:need(bindings[key]==b,'consistent independent substitution')
  else:bindings[key]=b
  return
 need(a[0]==b[0] and len(a)==len(b),'structural type kind')
 if a[0] in ('ref','mutref'):solve(a[1],b[1],bindings);return
 if a[0] in ('tuple','slice','array'):need(len(a[1])==len(b[1]),'aggregate arity');pairs=zip(a[1],b[1])
 elif a[0]=='apply':need(a[1]==b[1] and len(a[2])==len(b[2]),'generic identity/arity');pairs=zip(a[2],b[2])
 else:raise ValueError('incompatible independent type:'+str((a,b)))
 for x,y in pairs:solve(x,y,bindings)
def explicit_generic_arguments(target):
 stack=[];args=[]
 for i,ch in enumerate(target):
  if ch=='<':stack.append(i)
  elif ch=='>' and target[i-1]!='-':
   need(stack,'target generic close');start=stack.pop();args.extend(split(target[start+1:i]))
 need(not stack,'target generic balance');return args
def nested_carrier_ports(source,nodes):
 declarations=[]
 for path,text in source.items():
  clean='\n'.join(lexical(line)[0] for line in text.splitlines())
  for match in re.finditer(r'\b(struct|enum)\s+(\w+)',clean):
   cursor=match.end();angle=0
   while cursor<len(clean):
    ch=clean[cursor]
    if ch=='<':angle+=1
    elif ch=='>':angle-=1
    elif angle==0 and ch in '{(;':break
    cursor+=1
   need(cursor<len(clean),'declaration end');start=cursor
   if clean[cursor]!=';':
    opener=clean[cursor];closer='}' if opener=='{' else ')';depth=1;cursor+=1;quote=False;escape=False
    while depth and cursor<len(clean):
     ch=clean[cursor]
     if quote:
      if escape:escape=False
      elif ch=='\\':escape=True
      elif ch=='"':quote=False
     elif ch=='"':quote=True
     elif ch==opener:depth+=1
     elif ch==closer:depth-=1
     cursor+=1
    need(depth==0,'declaration body')
   else:cursor+=1
   declarations.append((match[2],set(re.findall(r'\b[A-Za-z_]\w*\b',clean[match.start():cursor]))))
 names={'Policy'}|{n for n,t in declarations if 'str' in t}
 while True:
  new=names|{n for n,t in declarations if t&names}
  if new==names:break
  names=new
 ports={(k,p,t) for k,r in nodes.items() for p,t in r['params'].items() if re.search(r'\bstr\b',t) or set(re.findall(r'\b[A-Za-z_]\w*\b',t))&names or '::Failure' in t}
 return names,ports
def main():
 mir,source=inputs();rows,literals,alloc=parse(mir);g=json.loads((C/'graph.json').read_text());cat=json.loads((C/'authored-contracts.json').read_text());inventory_headers=json.loads((C/'typed-header-inventory.json').read_text())['headers']
 need(len(rows)==2009,'2009 headers')
 for key,row in rows.items():
  for f in ('name','header','params','return_type','local_types'):need(row[f]==inventory_headers[key][f],'fresh complete header:'+key+':'+f)
 for key,row in g['nodes'].items():
  for f in ('name','header','params','return_type','local_types','typed_statements','MIR_sha256','MIR_bytes'):need(rows[key][f]==row[f],'fresh selected parse:'+key+':'+f)
 edge=lambda e:(e['caller'],e['callee'],e['kind'],e['line'],e['target'])
 prior=json.loads((V/'swift-guarded-snapshot-string-provenance-independent/typed-graph.json').read_text());original=json.loads((V/'swift-guarded-snapshot-string-provenance/graph.json').read_text())
 need({edge(e) for e in g['edges']}=={edge(e) for e in prior['edges']} and {edge(e) for e in original['edges']}<={edge(e) for e in g['edges']},'complete independent graph history')
 need(len(g['nodes'])==525 and len(g['edges'])==1908,'graph counts')
 assignments=[];local_call_checks=0
 for k,row in g['nodes'].items():
  for s in rows[k]['typed_statements']:
   m=re.match(r'(_\d+) = (.*);$',s['statement'])
   if m and rows[k]['local_types'].get(m[1]) in ('&str',"&'static str",'&mut str'):
    value=m[2];kind='compiled-literal' if value.startswith('const "') else 'reference-or-field-transfer' if value.startswith(('copy ','move ','no_retag copy ','no_retag move ','&')) else 'callee-return' if ' -> [' in value else 'unclosed'
    need(kind!='unclosed','primitive producer');assignments.append(dict(s,function=k,local=m[1],kind=kind))
  for call in row['calls']:
   for a in call['arguments']:
    operand=re.sub(r'^(?:no_retag )?(?:copy |move )','',a['operand'])
    if operand in rows[k]['local_types']:need(a['type']==rows[k]['local_types'][operand],'call local origin');local_call_checks+=1
    elif re.search(r': (.*)\)$',operand):need(a['type']==re.search(r': (.*)\)$',operand)[1],'call projected origin');local_call_checks+=1
   dest=re.match(r'(_\d+) = ',call['statement'])
   if dest:need(call['result_type']==rows[k]['local_types'][dest[1]],'destination origin');local_call_checks+=1
 need(assignments==g['source_str_assignments'] and len(assignments)==80,'80 full assignments')
 need(collections.Counter(x['kind'] for x in assignments)=={'compiled-literal':24,'reference-or-field-transfer':54,'callee-return':2},'str origins')
 for key,local,line in [('f0279','_35',256),('f1035','_29',203)]:need(any(x['function']==key and x['local']==local and x['line']==line for x in assignments),'nested tuple transfer')
 need(len(literals)==3189 and len(set(literals))==1397 and max(len(v.encode()) for v in literals)==92,'literal pool')
 ids={a[0] for a in alloc};need(len(alloc)==1958 and len(ids)==1464 and max(a[1] for a in alloc)==5080 and not (set(re.findall(r'\balloc\d+\b',mir))-ids),'allocation pool')
 aliases=cat['type_path_aliases'];special=cat['selected_specializations'];constants=cat['constant_types'];ast=lambda t:term(t,aliases,special,constants)
 namespace_files={
  'experimental::account':'src/experimental/account.rs','experimental::validate':'src/experimental/validate.rs','experimental::metadata':'src/experimental/metadata.rs','experimental::cache::decode':'src/experimental/cache/decode.rs','experimental::descriptors':'src/experimental/descriptors.rs','experimental::swift':'src/experimental/swift.rs','experimental::swift::snapshot_encoder_v2':'src/experimental/swift.rs','experimental_wasi':'src/experimental_wasi/mod.rs','experimental_wasi::accounted':'src/experimental_wasi/accounted.rs','experimental_wasi::descriptor':'src/experimental_wasi/descriptor.rs','experimental_swift_reactor::control':'src/experimental_swift_reactor/control.rs','experimental_swift_reactor::retained_profile_loader_v1':'src/experimental_swift_reactor/retained_profile_loader_v1.rs','experimental_swift_reactor::diagnostic_profile':'src/experimental_swift_reactor/diagnostic_profile.rs','experimental_swift_reactor::cache::initial_profile_v1':'src/experimental_swift_reactor/cache/initial_profile_v1.rs','experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1':'src/experimental_swift_reactor/cache/initial_profile_v1.rs','experimental_swift_reactor::cache::initial_profile_v1::trusted_local_host_account_entry_v1::host_account_v1':'src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs'}
 need('mod snapshot_encoder_v2 {' in source['src/experimental/swift.rs'],'inline encoder namespace')
 need('mod trusted_local_host_account_entry_v1 {' in source['src/experimental_swift_reactor/cache/initial_profile_v1.rs'] and 'include!("initial_profile_v1/host_account_v1.rs")' in source['src/experimental_swift_reactor/cache/initial_profile_v1.rs'],'private host namespace')
 std_aliases={'std::option::Option','std::result::Result','std::vec::Vec','std::time::Duration','std::time::Instant','std::alloc::Layout','std::sync::atomic::Atomic'}
 alias_evidence=[]
 for short,full in aliases.items():
  if full.startswith('std::'):need(full in std_aliases,'explicit standard alias');proof={'standard_compiler_path':full}
  else:
   namespace,name=full.rsplit('::',1);need(namespace in namespace_files,'reviewed full source namespace');path=namespace_files[namespace];text=source[path];sites=[]
   for match in re.finditer(r'\b(?:struct|enum|type|trait)\s+'+re.escape(name)+r'\b',text):sites.append({'path':path,'line':text[:match.start()].count('\n')+1,'declaration':text.splitlines()[text[:match.start()].count('\n')]})
   need(sites,'actual source declaration:'+full);proof={'actual_declaration_sites':sites}
  alias_evidence.append({'compiler_alias':short,'canonical_path':full,**proof})
 byname=collections.defaultdict(list)
 for k,r in rows.items():byname[r['name']].append(k)
 origin_evidence=[];signature_equations=0;nonidentical=collections.Counter();substitutions=[]
 for target,c in cat['contracts'].items():
  for name,definition in c['definitions'].items():
   need(name in byname,'actual authored destination')
   for key in byname[name]:
    row=rows[key]
    for f in ('params','return_type'):need(row[f]==definition[f],'actual destination declaration')
    need(row['local_types']['_0']==definition['local_result_type'],'actual destination place')
    loc=re.search(r'owned-work/vm/(src/.+?):(\d+):\d+:',name)
    if loc:
     path,line=loc[1],int(loc[2]);need(source[path].splitlines()[line-1]==definition['owner_source_line'],'source owner binding');origin={'path':path,'line':line,'text':definition['owner_source_line']}
    else:
     debug=re.search(r'owned-work/vm/(src/.+?):(\d+):\d+',row['body']);origin={'path':debug[1],'line':int(debug[2])} if debug else {'constructor_or_compiler_body':name}
    origin_evidence.append({'target':target,'destination':key,'definition':name,'source_origin':origin})
   # Contract signatures share this destination declaration; independently
   # solve the actual positional declarations, including exact closure bodies.
   for sig in c['signatures']:
    row=rows[byname[name][0]];templates=list(row['params'].values())+[row['return_type']];actual=sig['arguments']+[sig['result']];need(len(templates)==len(actual),'independent direct arity');bindings={}
    for template,value in zip(templates,actual):
     signature_equations+=1
     if template!=value:nonidentical[(template,value)]+=1
     if template.startswith('impl Fn'):
      m=re.fullmatch(r'impl (FnOnce|FnMut)\((.*)\) -> (.*)',template);need(m,'selected callable syntax');site=value.removeprefix('{closure@').removesuffix('}');closures=[r for r in rows.values() if list(r['params'].values()) and site in list(r['params'].values())[0]];need(closures,'actual closure origin')
      for closure in closures:
       pars=list(closure['params'].values());expected=value if m[1]=='FnOnce' else '&mut '+value;need(pars[0]==expected,'closure self kind');args=split(m[2]);need(len(args)==len(pars)-1,'closure argument arity')
       for a,b in zip(args,pars[1:]):solve(ast(a),ast(b),bindings)
       rt='std::result::Result<usize, std::io::Error>' if m[3]=='io::Result<usize>' else m[3];solve(ast(rt),ast(closure['return_type']),bindings)
     else:solve(ast(template),ast(value),bindings)
    expected={k:ast(v) for k,v in sig['generic_substitutions'].items()};need(bindings==expected,'independently solved substitutions')
    generic_args=explicit_generic_arguments(target)
    for key,value in bindings.items():need(value in [ast(a) for a in generic_args],'actual target turbofish binding:'+target+':'+key)
    substitutions.append({'target':target,'bindings':bindings,'actual_explicit_target_arguments':generic_args if bindings else []})
 need(len(nonidentical)==323,'323 independently solved type pairs')
 constant_evidence=[]
 for name,t in constants.items():
  if name.startswith('core::num::'):need(name in ('core::num::<impl u64>::MAX','core::num::<impl usize>::MAX'),'platform constant origin');constant_evidence.append({'constant':name,'type':t,'origin':'exact compiler primitive unsigned maximum'});continue
  if name.startswith('<P as '):path='src/experimental_swift_reactor/control.rs';segment='\n'.join(source[path].splitlines()[1908:1922])
  else:
   namespace,member=name.rsplit('::',1);path='src/'+namespace.replace('::','/')+'.rs';segment=source[path]
  member=name.rsplit('::',1)[-1];found=re.search(r'\bconst\s+'+re.escape(member)+r'\s*:\s*([^=;]+)[=;]',segment);need(found,'constant actual declaration:'+name);declared_type=found[1].strip();imports=[]
  if name=='experimental_swift_reactor::cache::initial_profile_v1::CONSTRUCTION_CURSOR_V1':
   need(declared_type=='Cursor' and 'use super::*;' in segment and 'use super::control::*;' in source['src/experimental_swift_reactor/cache.rs'],'exact Cursor import chain')
   declared_type='experimental_swift_reactor::control::Cursor';imports=['initial_profile_v1: use super::*','cache: use super::control::*','control::Cursor actual declaration']
  need(ast(declared_type)==ast(t),'constant actual declared type:'+name)
  constant_evidence.append({'constant':name,'type':t,'source_path':path,'declaration':found[0],'exact_import_chain':imports})
 callback_signatures=0
 for target,c in cat['contracts'].items():
  for sig in c['named_callback_signatures']:
   callback_signatures+=1;m=re.fullmatch(r'fn\((.*?)\) -> (.*)',sig['function_item_type']);need(m,'named callback fn syntax');args=split(m[1]);result=m[2]
   for name in c['definitions']:
    row=rows[byname[name][0]];need(len(args)==len(row['params']),'actual named arity');bindings={}
    for a,b in zip(list(row['params'].values())+[row['return_type']],args+[result]):solve(ast(a),ast(re.sub(r"&'\w+\s+",'&',b)),bindings)
 need(callback_signatures==4,'independent named typed signatures')
 for key,contract in cat['closure_contracts'].items():
  outer,site=key.rsplit(' | ',1)
  occurrences=[c for row in g['nodes'].values() for c in row['calls'] if c['target']==outer and site in c['closures']];need(occurrences,'actual closure invocation origin')
  for call in occurrences:need([a['type'] for a in call['arguments']]==contract['outer_arguments'] and call['result_type']==contract['outer_result'],'actual closure invocation signature')
  for name,definition in contract['definitions'].items():
   for k in byname[name]:
    for f in ('params','return_type'):need(rows[k][f]==definition[f],'fresh closure declaration')
    need(rows[k]['local_types']['_0']==definition['local_result_type'],'fresh closure result place')
    need(site in next(iter(rows[k]['params'].values())),'exact closure environment site')
 # Source-level caller, latches, scalar policy and retirement evidence is
 # independently rebound to original bytes; these are proof preconditions.
 sem=json.loads((C/'source-semantic-review.json').read_text())
 for e in sem['excerpts']:
  need(sha(source[e['path']].encode())==e['source_sha256'] and '\n'.join(source[e['path']].splitlines()[e['start']-1:e['end']])==e['text'],'actual semantic excerpt')
 for k,b in sem['critical_MIR_bodies'].items():need(rows[k]['body']==b['body'],'complete critical MIR')
 ip=source['src/experimental_swift_reactor/cache/initial_profile_v1.rs'];ctrl=source['src/experimental_swift_reactor/control.rs'];host=source['src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs']
 for token in ['let cancellation = Cancellation::default();','load_selected_retained_profile_v1(','Ok(selected) => PrimaryOutcomeV1::Leaf(invoke_loaded_leaf_once_v1(','selected, binding.product_budget, Instant::now(), cancellation.clone(),','run_one_loaded_fixture_v1(selected, budget, started, cancellation, claims, rows, snapshot)']:need(token in ip,'exact caller source')
 for token in ['first_failure: None','cleanup_invariant: None','code: fault.code','self.first_failure = Some(failure)']:need(token in ctrl,'fresh/latch source')
 for token in ['if let Some(owned) = self.owned.take() { drop(owned); }','impl<T> Drop for PrepaidOwnedV1','let owned = action();','pub(super) fn release_destroyed_v1(self)']:need(token in host,'return/drop source')
 need('Self::SwiftReactorExperimentV1' in source['src/experimental/policy.rs'] and 'Policy::swift()' in source['src/experimental/swift.rs'],'selected policy construction')
 named=[e for e in g['edges'] if e['kind']=='named-authored-callback'];need(len(named)==28 and len({(e['caller'],e['line']) for e in named})==22,'named graph')
 need(any(e['caller']=='f1605' and e['callee']=='f1697' for e in g['edges']),'transitive configuration')
 ports=[(k,p,t) for k,r in g['nodes'].items() for p,t in r['params'].items() if re.search(r'\bstr\b',t)];need(len(ports)==9 and all(any(e['callee']==k for e in g['edges']) for k,p,t in ports),'direct ports')
 carriers=json.loads((C/'carrier-induction.json').read_text());need(len(carriers['nested_and_direct_ports'])==257,'nested ports')
 carrier_names,recovered_ports=nested_carrier_ports(source,g['nodes'])
 need(recovered_ports=={(p['function'],p['parameter'],p['type']) for p in carriers['nested_and_direct_ports']} and len(recovered_ports)==257,'independently recovered nested carrier ports')
 for token,path in [('impl ClosedBranchV1 for SnapshotBranchV1','src/experimental_swift_reactor/cache/initial_profile_v1.rs'),('impl SharedControlV1 for SnapshotAccessV1','src/experimental_swift_reactor/cache/initial_profile_v1.rs'),('impl MeterControl for SwiftControl','src/experimental/account.rs'),('impl Declaration for SwiftDeclaration','src/experimental/metadata.rs'),('impl ClosedAdoptionV1 for SnapshotAdoptionV1','src/experimental_swift_reactor/control.rs')]:need(token in source[path],'actual specialization owner')
 historical=[]
 for k,row in rows.items():
  m=re.match(r'^fn (.+?)\((.*?)\) -> (.+?) \{',row['header']);need(m,'historical header parse')
  old=dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',m[2]))
  if old!=row['params'] or m[3]!=row['return_type']:historical.append(k)
 need(set(historical)=={'f0907','f1257','f1258','f1297','f1298','f1299','f1300','f1319','f1405'},'complete historical nine-header discrepancy roster')
 need(len(cat['contracts'])==423 and sum(len(c['signatures']) for c in cat['contracts'].values())==434 and sum(len(c['named_callback_signatures']) for c in cat['contracts'].values())==4 and len(cat['closure_contracts'])==181,'contract census')
 save('origin-and-type-review.json',{'schema':1,'source_tree_sha256':SOURCE,'alias_declaration_evidence':alias_evidence,'authored_destination_origins':origin_evidence,'independent_substitutions':substitutions,'all_positional_equations_solved':signature_equations,'nonidentical_pairs':len(nonidentical),'typed_constant_actual_declarations':constant_evidence,'historical_header_discrepancy_roster':historical,'independently_recovered_conservative_carrier_names':sorted(carrier_names),'specialization_source_preconditions':['SnapshotBranchV1 implements ClosedBranchV1; SnapshotAccessV1 implements SharedControlV1','SwiftControl implements MeterControl; SwiftDeclaration implements Declaration','SnapshotAdoptionV1 implements ClosedAdoptionV1 with Failure=SnapshotPreScopeFailureV1 and Retirement=Result<(),SwiftRunFailure>','only std::fs::File Read specialization, two exact source closures and their actual typed declarations']})
 save('analysis.json',{'schema':1,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'compiled_headers_independently_parsed':len(rows),'selected_bodies':525,'selected_edges':1908,'original_edges_preserved':1879,'named_callback_edges':28,'named_callback_sites':22,'complete_typed_statements_compared':sum(len(r['typed_statements']) for k,r in rows.items() if k in g['nodes']),'actual_local_or_projected_call_types_compared':local_call_checks,'primitive_str_assignments':80,'primitive_str_kinds':{'compiled-literal':24,'reference-or-field-transfer':54,'callee-return':2},'direct_ports':9,'direct_and_nested_ports':257,'authored_exact_targets':423,'direct_signatures':434,'named_callback_signatures':4,'closure_adapter_contracts':181,'nonidentical_structural_pairs_solved':323,'source_aliases_rebound_to_declarations':len(alias_evidence),'literal_occurrences':3189,'literal_unique':1397,'maximum_literal_utf8_bytes':92,'allocation_occurrences':1958,'allocation_unique_ids':1464,'allocation_max_bytes':5080,'unresolved_ids':[],'source_caller_failure_latch_return_drop_preconditions_rebound':True,'full_source_6006_structural_constructs_or_1785_constants_covered':False,'future_changed_outer_scoped_provider_source_covered':False,'general_Rust_solver_claim':False,'L_str_selected':False,'policy_or_operational_grant_or_OTA_or_GA':False})
 print(json.dumps(json.loads((D/'analysis.json').read_text()),sort_keys=True))
if __name__=='__main__':main()
