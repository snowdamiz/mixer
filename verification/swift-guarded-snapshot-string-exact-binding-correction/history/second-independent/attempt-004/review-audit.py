#!/usr/bin/env python3
"""Fresh local/statement/origin census. No producer analysis imports.

Graph selection is cross-checked against the earlier immutable independent
fixed point; this script does not claim a newly implemented Rust MIR solver.
Semantic conclusions use the explicit reviewed source/MIR paths below.
"""
import collections,gzip,hashlib,json,re,sys
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1];V=R/'verification';C=V/'swift-guarded-snapshot-string-provenance-correction'
def sha(b):return hashlib.sha256(b).hexdigest()
def need(v,m):
 if not v:raise ValueError(m)
def save(n,j):
 s=json.dumps(j,indent=2,sort_keys=True)+'\n'
 if '--check' in sys.argv:need((D/n).read_text()==s,'rederived:'+n)
 else:(D/n).write_text(s)
def char_end(s,i):
 if s[i]!="'":return None
 j=i+1
 if j>=len(s):return None
 if s[j]=='\\':
  j+=1
  if j>=len(s):return None
  if s[j]=='u':
   e=s.find('}',j+1)
   if e<0:return None
   j=e+1
  elif s[j]=='x':j+=3
  else:j+=1
 else:j+=1
 return j+1 if j<len(s) and s[j]=="'" else None
def lexical(s):
 """Return code before comment and all compiler cooked str values."""
 out=[];i=0
 while i<len(s):
  if s.startswith('//',i):return s[:i],out
  if s[i]=="'":
   e=char_end(s,i)
   if e is not None:i=e;continue
  if s[i]!='"':i+=1;continue
  binary=i>0 and s[i-1]=='b';i+=1;v=[]
  while i<len(s):
   c=s[i];i+=1
   if c=='"':break
   if c!='\\':v.append(c);continue
   e=s[i];i+=1
   maps={'n':'\n','r':'\r','t':'\t','0':'\0','\\':'\\','"':'"',"'":"'"}
   if e in maps:v.append(maps[e])
   elif e=='x':v.append(chr(int(s[i:i+2],16)));i+=2
   elif e=='u':
    need(s[i]=='{','unicode-open');end=s.index('}',i);v.append(chr(int(s[i+1:end].replace('_',''),16)));i=end+1
   else:raise ValueError('unsupported escape:'+e)
  else:raise ValueError('unclosed string')
  if not binary:out.append(''.join(v))
 return s,out
def parse(mir):
 bodies={};current=None;lines=[];literals=[];allocations=[];inalloc=False
 for line in mir.splitlines():
  if inalloc:
   if line=='}':inalloc=False
   continue
  if line.startswith('alloc') and line.endswith('{'):
   m=re.match(r'(alloc\w+) \(.*?size: (\d+), align: (\d+)\) \{',line);need(m is not None,'allocation-header');allocations.append({'id':m[1],'bytes':int(m[2]),'alignment':int(m[3])});inalloc=True;continue
  code,ls=lexical(line);literals.extend(ls)
  if line.startswith('fn '):need(current is None,'nested top-level body');current=f'f{len(bodies):04d}';lines=[line];continue
  if current is None:continue
  lines.append(line)
  if line!='}':continue
  body='\n'.join(lines)+'\n';header=lines[0];a=header.index('(');depth=1;i=a+1
  while depth:
   if header[i]=='(':depth+=1
   if header[i]==')':depth-=1
   i+=1
  need(header[i:i+4]==' -> ','header result');name=header[3:a];rt=header[i+4:].removesuffix(' {');paramtext=header[a+1:i-1]
  params=dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',paramtext));local={};statements=[];assignments=[]
  for n,line in enumerate(lines,1):
   code,_=lexical(line)
   s=code.strip()
   if s.startswith('let '):
    match=re.fullmatch(r'let (?:mut )?(_\d+): (.*);',s)
    need(match is not None,'local-declaration:'+s);local[match[1]]=match[2]
   if line.startswith('        ') and s:statements.append({'line':n,'statement':s})
  local.update(params);local.setdefault('_0',rt)
  for s in statements:
   m=re.match(r'(_\d+) = (.*);$',s['statement'])
   if m and local.get(m[1]) in ('&str',"&'static str",'&mut str'):
    value=m[2];kind='compiled-literal' if value.startswith('const "') else 'reference-or-field-transfer' if value.startswith(('copy ','move ','no_retag copy ','no_retag move ','&')) else 'callee-return' if ' -> [' in value else 'unknown'
    need(kind!='unknown','primitive str instruction');assignments.append(dict(s,local=m[1],kind=kind,function=current))
  bodies[current]={'name':name,'body':body,'MIR_sha256':sha(body.encode()),'MIR_bytes':len(body.encode()),'local_types':local,'params':params,'return_type':rt,'typed_statements':statements,'assignments':assignments};current=None
 need(current is None and not inalloc,'complete body/allocation balance')
 return bodies,literals,allocations
def main():
 base=V/'swift-guarded-snapshot-loader-work-source146';mir=gzip.decompress((base/'whole-source146.mir.gz').read_bytes()).decode();bodies,literals,alloc=parse(mir)
 g=json.loads((C/'graph.json').read_text());old=json.loads((V/'swift-guarded-snapshot-string-provenance-independent/typed-graph.json').read_text());original=json.loads((V/'swift-guarded-snapshot-string-provenance/graph.json').read_text());ind=json.loads((C/'carrier-induction.json').read_text())
 need(len(bodies)==2009,'all-compiled-bodies');need(set(g['nodes'])==set(old['nodes']),'independent-fixed-point-membership')
 for k,row in g['nodes'].items():
  for field in ('name','MIR_sha256','MIR_bytes','params','return_type','local_types','typed_statements'):
   need(bodies[k][field]==row[field],'fresh-parse:'+k+':'+field)
  need(bodies[k]['MIR_sha256']==old['nodes'][k]['MIR_sha256'],'old-independent-body:'+k)
 edgekey=lambda e:(e['caller'],e['callee'],e['kind'],e['line'],e['target'])
 ge={edgekey(e) for e in g['edges']};oe={edgekey(e) for e in old['edges']};pe={edgekey(e) for e in original['edges']};need(ge==oe and pe<=ge,'complete-edge-set')
 assignments=[a for k in g['nodes'] for a in bodies[k]['assignments']];need(assignments==g['source_str_assignments'],'complete-primitive-assignments')
 for k,local,line in [('f0279','_35',256),('f1035','_29',203)]:need(any(a['function']==k and a['local']==local and a['line']==line for a in assignments),'missing-transfer')
 need(len(assignments)==80,'80 assignments');need(collections.Counter(a['kind'] for a in assignments)=={'compiled-literal':24,'reference-or-field-transfer':54,'callee-return':2},'primitive-kinds')
 values=sorted(set(literals));need(len(literals)==3189 and len(values)==1397 and max(len(v.encode()) for v in values)==92,'literal-census');need(values==g['literal_pool']['values'],'every-cooked-literal')
 ids={a['id'] for a in alloc};unresolved=set(re.findall(r'\balloc\d+\b',mir))-ids
 need(len(alloc)==1958 and len(ids)==1464 and not unresolved and max(a['bytes'] for a in alloc)==5080,'allocation-census')
 named=[e for e in g['edges'] if e['kind']=='named-authored-callback'];need(len(named)==28 and len({(e['caller'],e['line']) for e in named})==22,'named-callback-census')
 need(any(e['caller']=='f1605' and e['callee']=='f1697' for e in g['edges']),'new-transitive-edge')
 for k in ['f1899','f1900','f1927','f1928']:need(any(e['callee']==k for e in named),'duplicate-constructor')
 ports=[]
 for k,r in g['nodes'].items():
  for param,typ in bodies[k]['params'].items():
   if re.search(r'\bstr\b',typ):
    incoming=[dict(e,call=next(c for c in g['nodes'][e['caller']]['calls'] if c['line']==e['line'])) for e in g['edges'] if e['callee']==k]
    need(incoming,'unclosed-direct-port');ports.append({'function':k,'parameter':param,'type':typ,'incoming':incoming})
 need(len(ports)==9,'nine-direct-ports')
 # Recheck the actual read-only external frontier against full target identity
 # and argument/result pairs. This is custody/coverage; semantic reasons are
 # reviewed by interface family below, not inferred from catalog membership.
 contracts=json.loads((C/'external-contracts.json').read_text())['contracts'];ext=0;families=collections.Counter()
 for f in g['external_frontier']:
  c=contracts[f['target']];families[c['conservation']]+=1
  for site in f['sites']:
   call=next(x for x in g['nodes'][site['caller']]['calls'] if x['line']==site['line']);need(call['target']==f['target'],'exact-external-target');need({'arguments':[a['type'] for a in call['arguments']],'result':call['result_type']} in c['signatures'],'exact-external-signature');ext+=1
 need(ext==3209 and len(contracts)==1127 and sum(len(c['signatures']) for c in contracts.values())==1130,'external-census')
 # Exact source paths reviewed here. These are original frozen source bytes,
 # with complete selected MIR bodies retained separately for the critical chain.
 ref=json.loads((base/'source-reference-map.json').read_text());source={m['path']:(R/m['source']).read_text() for m in ref['members'] if m['path'].endswith('.rs')}
 ranges=[('src/experimental_swift_reactor/cache/initial_profile_v1.rs',659,676),('src/experimental_swift_reactor/cache/initial_profile_v1.rs',703,746),('src/experimental_swift_reactor/cache/initial_profile_v1.rs',796,836),('src/experimental_swift_reactor/control.rs',216,232),('src/experimental_swift_reactor/control.rs',255,283),('src/experimental_swift_reactor/control.rs',657,687),('src/experimental_swift_reactor/control.rs',983,1010),('src/experimental_swift_reactor/control.rs',1775,1799),('src/experimental/reader.rs',1,34),('src/experimental/account.rs',90,128),('src/experimental/validate.rs',21,36),('src/experimental/swift.rs',153,164),('src/experimental/swift.rs',322,354),('src/experimental/swift.rs',409,420),('src/experimental/policy.rs',1,12),('src/experimental/policy.rs',132,139),('src/lib.rs',117,132),('src/experimental_swift_reactor/retained_profile_loader_v1.rs',24,37),('src/experimental_swift_reactor/retained_profile_loader_v1.rs',136,190),('src/experimental_swift_reactor/cache/initial_profile_v1/host_account_v1.rs',132,189),('src/experimental_wasi/accounted.rs',432,432),('src/experimental_wasi/mod.rs',638,638)]
 excerpts=[{'path':p,'start':a,'end':z,'source_sha256':sha(source[p].encode()),'text':'\n'.join(source[p].splitlines()[a-1:z])} for p,a,z in ranges]
 need('pub code: &\'static str' in source['src/experimental_swift_reactor/control.rs'],'arbitrary-public-port')
 limits='\n'.join(source['src/lib.rs'].splitlines()[117:132]);need('str' not in limits.replace('struct',''),'Limits scalar fields')
 libprofile=re.search(r'pub enum Profile \{(.*?)\n\}',source['src/lib.rs'],re.S);need(libprofile is not None and not any(c in libprofile[1] for c in '({'),'Profile fieldless discriminants')
 # Every full typed statement and origin is covered by the independent parser;
 # raw-byte/pointer operations below are reviewed in their actual byte types.
 manufacture=[{'function':k,'statement':s} for k,row in g['nodes'].items() for s in row['manufacture_review']]
 need(all((' as *const [u8] (BoxDerefTransmute)' in x['statement']) or (' as usize (Transmute)' in x['statement']) for x in manufacture),'no additional string manufacture operations')
 critical=['f0116','f0203','f0205','f0245','f0279','f0331','f0888','f0910','f0912','f0913','f0914','f0915','f0918','f0982','f1011','f1035','f1063','f1064','f1079','f1506','f1605','f1697','f1899','f1900','f1927','f1928'];critical=[k for k in critical if k in g['nodes']]
 sem={'schema':1,'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','excerpts':excerpts,'critical_MIR_bodies':{k:{field:bodies[k][field] for field in ('name','MIR_sha256','MIR_bytes','body')} for k in critical},'direct_str_ports':ports,'raw_byte_operations':manufacture,'Profile_declaration':libprofile[0],'Limits_declaration':limits,
 'reasoning':[
 'The private FrozenFixture input has paths, byte digest claims and scalar budgets. run_prepaid_fixture constructs cancellation, calls the selected loader, forwards only its Ok(selected) unchanged to invoke_loaded_leaf; no caller failure, Fault, custom callback or proof mutation enters this route.',
 'The validator constructs Policy::swift, which produces SwiftReactorExperimentV1; policy_identity returns a fixed compiled literal on that branch. Frozen(&Limits) contains scalar/profile limits and is a control dependency; the alternative branch panics. A substituted policy is outside the selected contract.',
 'Meter/Reader/BodyState error functions forward their supplied static code reference into experimental::Failure. All nine direct code ports have retained typed incoming callers. Swift validation mapping copies raw.code; Fault::new stores code; RuntimeControl::fail either returns its existing first failure or copies fault.code into a fresh failure and latches it.',
 'The selected adoption builds first_failure=None and cleanup_invariant=None. Cleanup forwards its supplied code through Fault::new and annotates usage without constructing a string. Nested Result/Option/enums, fields, returns, retirement wrappers and Drop move/drop existing values. Added Runtime/Stop constructors wrap existing failures; added configuration callbacks copy numeric budget/grants.',
 'Standard exact interfaces use container moves/borrows/projections, Option/Result residual/branch operations, scalar calculations, and explicitly expanded callbacks. These semantics conserve existing string references; typed memory-size/drop operations introduce no str, and byte/pointer transmute operations remain [u8] or usize. The finite catalog is necessary coverage, not sufficient semantic proof and not a wildcard interface grant.',
 'All selected primitive str assignments are 24 compiled literals, 54 reference/field transfers and two authored policy_identity returns. Aggregate constants/promotions/option_env strings are covered by the entire compiler allocation pool, including relocations. Thus 5080 remains a conditional source-origin envelope, not a public static-str bound. Actual executable/compiler/session binding and complete binary correspondence remain pending.',
 'Path/OsStr bytes and native io::Error private backing remain separate native allowances. Public SwiftRunFailure.code and lower Reader/Meter/Fault/cleanup code inputs admit arbitrary static strings on alternate routes; they cannot be closed by lifetime, pointer width or caller length claims.'
 ],'scope':'offline human source/MIR path review plus independent full local/statement/origin census; old sealed independent fixed point cross-check; no compiler/runtime/native tests','source_closure_accepted':False,'L_str_selected':False,'operational_grant':False}
 save('source-semantic-review.json',sem)
 result={'schema':1,'parser_imports_producer_analysis':False,'compiled_bodies':len(bodies),'selected_bodies':len(g['nodes']),'all_typed_locals_and_statements_independently_compared':True,'edges_crosschecked_against_old_frozen_independent':len(ge),'original_edges_preserved':len(pe),'named_authored_sites':22,'named_authored_edges':28,'duplicate_enum_constructors_retained':True,'standard_option_predicates':g['standard_named_callbacks'],'primitive_str_assignments':len(assignments),'primitive_str_kinds':dict(collections.Counter(a['kind'] for a in assignments)),'direct_str_ports':len(ports),'candidate_nested_ports_retained':len(ind['nested_and_direct_ports']),'literal_occurrences':len(literals),'literal_unique':len(values),'literal_max_utf8_bytes':92,'allocations':len(alloc),'allocation_unique_ids':len(ids),'allocation_max_bytes':5080,'unresolved_allocation_ids':sorted(unresolved),'external_targets':len(contracts),'external_sites':ext,'external_typed_signatures':1130,'external_semantic_families':dict(families),'conservative_candidate_extent':5080,'candidate_extent_selected':False,'scope':'full census and path review; candidate must still return for resolver identity/signature correction','operational_grant':False}
 save('analysis.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
