#!/usr/bin/env python3
"""Independent MIR/source/layout reconciliation. Imports no producer collector/parser."""
import collections,gzip,hashlib,json,pathlib,re
from collect import HERE,ROOT,UP,encode,sha,manifest,members

def split_parameters(t):
 out=[];start=0;depth=0
 for i,ch in enumerate(t):
  if ch in '(<[{':depth+=1
  elif ch in ')>]}':depth-=1
  elif ch==',' and depth==0:out.append(t[start:i].strip());start=i+1
 return out+[t[start:].strip()] if t[start:].strip() else out

def mir_functions(text):
 lines=text.splitlines(keepends=True);blocks=[];current=[]
 for ln in lines:
  if ln.startswith(('fn ','const ')):
   if current:blocks.append(''.join(current))
   current=[ln]
  elif current:current.append(ln)
 if current:blocks.append(''.join(current))
 for b in blocks:
  head=b.splitlines()[0]
  if head.startswith('fn '):
   name=head[3:head.index('(')]
   if name=='width' or name.startswith('memory_pinned_caller_prerequisite') or name.startswith('memory_operations::<impl '):yield name,b
  elif head.startswith('const memory_operations::<impl ') and 'memory_preflight::promoted[' in head:
   yield head[6:head.index(': &')],b

def normalized(t,captures):
 for site,payload in captures.items():t=t.replace(site,payload)
 assert '{closure@' not in t,t
 t=re.sub(r"'[A-Za-z_][A-Za-z_0-9]*","'static",t)
 for prefix,path in [('experimental_swift_reactor::','crate::experimental_swift_reactor::'),('experimental_wasi::','crate::experimental_wasi::'),('experimental::','crate::experimental::'),('control::','crate::experimental_swift_reactor::control::')]:t=re.sub(r'(?<![:\w])'+re.escape(prefix),path,t)
 t=re.sub(r"&(?!(?:'|\s*'))","&'static ",t)
 return 'std::convert::Infallible' if t=='!' else t

def inventory(config):
 text=gzip.decompress((HERE/(config+'.mir.gz')).read_bytes()).decode();functions=list(mir_functions(text));assert len(functions)==20
 captures={};definitions=[];entities=[];projected=[];promoted=[]
 for name,b in functions:
  head=b.splitlines()[0];params={}
  if head.startswith('fn '):
   p=head[head.index('(')+1:];depth=1;i=0
   while depth:depth+=(p[i]=='(')-(p[i]==')');i+=1
   for arg in split_parameters(p[:i-1]):ident,ty=arg.split(': ',1);params[ident]=ty
  locals=dict(re.findall(r'^\s*let (?:mut )?(_\d+): (.+);(?:\s*//.*)?$',b,re.M));decl={**locals,**params};assert '_0' in decl,(name,decl)
  for site in re.findall(r'\{closure@[^}]+\}',head):
   fields={int(ix):ty for ix,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',b)}
   assert not fields or set(fields)==set(range(len(fields)))
   captures[site]='('+','.join(fields[i] for i in sorted(fields))+(',' if len(fields)==1 else '')+')'
  # Record projected debug aliases separately; they refer to the freshly measured
  # closure backing, with no second ownership or runtime-created allocation.
  for alias,expr in re.findall(r'debug (\w+) => ([^;]+);',b):
   if not re.fullmatch(r'_\d+',expr):projected.append({'function':name,'name':alias,'expression':expr})
  definitions.append({'function':name,'localsAndReturn':locals,'arguments':params})
  if '::promoted[' in name:promoted.append({'function':name,'places':decl})
  debug=collections.defaultdict(list)
  for alias,ident in re.findall(r'debug (\w+) => (_\d+);',b):debug[ident].append(alias)
  for ident,ty in decl.items():
   entities.append((name,'canonical',ident,ty,tuple(debug[ident])))
   for alias in debug[ident]:entities.append((name,'authored-alias',alias,ty,(alias,)))
  literals=re.findall(r'\bconst ("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',b)
  for ix,literal in enumerate(literals):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   entities.append((name,'direct-literal','literal_'+str(ix),ty,(literal,)))
 assert len(promoted)==2 and len(captures)==6
 return entities,definitions,captures,projected,promoted

def expanded_methods(label):
 t=gzip.decompress((HERE/'commands'/('expanded-'+label)/'stdout.gz').read_bytes()).decode();a=t.index('impl SpanInstance {');i=t.index('{',a)+1;depth=1
 while depth:depth+=(t[i]=='{')-(t[i]=='}');i+=1
 owner=t[a:i];result={}
 starts=list(re.finditer(r'^    (?:pub )?fn (\w+)\(',owner,re.M))
 for m in starts:
  j=owner.index('{',m.start())+1;d=1
  while d:d+=(owner[j]=='{')-(owner[j]=='}');j+=1
  result[m[1]]=owner[m.start():j]
 return result

def main():
 schema=json.loads((UP/'inventory-schema.json').read_text());grouped=collections.defaultdict(list)
 for row in schema:grouped[row['field'].rsplit('_',1)[0]].append(row)
 assert len(schema)==4688 and len({r['field'] for r in schema})==4688
 for key,rows in grouped.items():assert len(rows)==4 and {r['position'] for r in rows}=={'source','argument','returned','caller'},key
 reports=[]
 for config in ['production','unit']:
  entities,defs,captures,projected,promoted=inventory(config);actual=collections.Counter(entities);expected=collections.Counter((rows[0]['mirFunction'],rows[0]['kind'],rows[0]['binding'],rows[0]['mirType'],tuple(rows[0]['sourceNames'])) for rows in grouped.values() if rows[0]['config']==config);assert actual==expected,(config,actual-expected,expected-actual)
  for rows in grouped.values():
   if rows[0]['config']!=config:continue
   for row in rows:assert normalized(row['mirType'],captures).replace(' ','')==row['rustType'].replace(' ',''),(row,normalized(row['mirType'],captures))
  reports.append({'config':config,'entities':len(entities),'positiveFields':4*len(entities),'definitions':defs,'captures':captures,'projectedDebugAliases':projected,'promotedBodies':promoted})
 (HERE/'independent-mir-inventory.json').write_bytes(encode(reports))
 a=expanded_methods('baseline');b=expanded_methods('candidate');assert a==b and len(a)==39;(HERE/'independent-frozen-identity.json').write_bytes(encode({k:sha(v.encode()) for k,v in a.items()}))
 scratch=pathlib.Path(json.loads((HERE/'session.json').read_text())['scratch']);base=manifest(scratch/'baseline');cand=manifest(scratch/'candidate');changed=sorted(k for k in set(base)|set(cand) if base.get(k)!=cand.get(k));assert changed==['src/experimental/execution/borrowed.rs','src/experimental/execution/mod.rs','src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/memory_operations.rs']
 declarations={}
 # All existing struct/enum declarations in every old Rust source are preserved.
 for path in base:
  if not path.endswith('.rs'):continue
  old=(scratch/'baseline'/path).read_text();new=(scratch/'candidate'/path).read_text()
  if old==new:continue
  for match in re.finditer(r'(?m)^(?:pub(?:\([^\n]*?\))? )?(struct|enum) (\w+)',old):
   start=match.start();end=old.find('{',start);semi=old.find(';',start)
   if semi>=0 and (end<0 or semi<end):decl=old[start:semi+1]
   else:
    depth=1;i=end+1
    while depth:depth+=(old[i]=='{')-(old[i]=='}');i+=1
    decl=old[start:i]
   assert decl in new,(path,match[2]);declarations[path+':'+match[2]]=sha(decl.encode())
 # Exact original width body, only visibility changes.
 old=(scratch/'baseline/src/experimental/execution/mod.rs').read_text();new=(scratch/'candidate/src/experimental/execution/mod.rs').read_text()
 start=old.index('fn width(');end=old.index('\n}',start)+2;assert old[start:end] in new
 layouts=json.loads((HERE/'layouts.json').read_text());assert len(layouts)==16
 comparisons=[]
 for layout in layouts:
  if layout['label']!='candidate':continue
  old=next(x for x in layouts if x['label']=='baseline' and all(x[k]==layout[k] for k in ['feature','profile','unit']));assert old['types']==layout['types'] and old['owners']==layout['owners']
  fields=[x for x in schema if layout['unit'] or x['config']!='unit'];assert set(layout['fields'])=={r['field'] for r in fields};bounds=collections.defaultdict(int)
  for row in sorted(fields,key=lambda x:(x['ownerClass'],layout['fields'][x['field']][0])):
   off,size,alignment=layout['fields'][row['field']];cls=row['ownerClass'];assert off%alignment==0 and off>=bounds[cls];bounds[cls]=off+size;assert bounds[cls]<=layout['classes'][cls][0]
  t=layout['totals'];o=old['totals'];assert all(t[k]==o[k] for k in ['construction','frame_permanent','frame_active','control_permanent','control_active','value','state_limit','combined_limit'])
  assert t['memory_permanent']==121856 and t['memory_active']==(1153832 if layout['unit'] else 618896)
  assert t['header']==o['header']+t['memory_permanent']==(2531040 if layout['unit'] else 1636360)
  assert t['frame']==o['frame']+t['memory_active']==(5103960 if layout['unit'] else 2830864)
  assert t['frame']==t['frame_active']+t['value']+t['control_active']+t['memory_active']
  assert t['state_limit']==128*1024**2 and t['combined_limit']==256*1024**2
  if layout['feature']=='all':assert t['frozen_header']==o['frozen_header']==2912
  comparisons.append({'feature':layout['feature'],'profile':layout['profile'],'unit':layout['unit'],'allOriginalShapesEqual':True,'positiveFields':len(fields),'totals':t})
 (HERE/'source-and-layout-audit.json').write_bytes(encode({'sourceChanges':changed,'unchangedOldDeclarations':declarations,'candidateLayouts':comparisons,'widthBodyUnchanged':True,'frozenMethods':39,'accountingIsLogicalOnly':True}))
 print('PASS: independent fresh compiler/source/layout/MIR prerequisite review: 39 Frozen methods, 20 MIR bodies/configuration, 4688 four-position fields, 8 paired candidate layouts')
if __name__=='__main__':main()
