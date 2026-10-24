#!/usr/bin/env python3
"""Independent source, raw MIR, positive-position and evidence-reuse audit."""
from pathlib import Path
import ast, collections, difflib, gzip, hashlib, importlib.util, json, re, tarfile
from review import HERE, enc, digest, read, sha
P=HERE/'inputs/producer'

def load(name):return json.loads((P/name).read_text())
def source(label):
 with tarfile.open(P/(label+'-source.tar.gz')) as t:
  items=t.getmembers();assert all(x.isfile() and x.name.startswith('vm/') and '..' not in Path(x.name).parts for x in items)
  d={m.name[3:]:t.extractfile(m).read() for m in items};assert len(d)==len(items)
 m={k:hashlib.sha256(v).hexdigest() for k,v in d.items()};assert m==load(label+'-source-manifest.json')
 return d,m

def split_args(s):
 out=[];level=0;start=0
 for i,c in enumerate(s):
  if c in '<([{':level+=1
  elif c in '>)]}':level-=1
  elif c==',' and level==0:out.append(s[start:i].strip());start=i+1
 out.append(s[start:].strip());return [x for x in out if x]
def selected(s):return ('memory_operations::' in s or s.startswith('memory_pinned') or s in ['width','experimental::execution::width']) and '::tests::' not in s and '::tests}' not in s
def fn_identity(name):
 name=name.removeprefix('experimental_swift_reactor::execution::frame_operations::')
 if name.startswith('memory_operations::memory_pinned'):name=name.removeprefix('memory_operations::')
 return name
def ty_identity(ty):return re.sub(r'(?<![:\w])control::','experimental_swift_reactor::control::',ty.replace('crate::',''))
def inspect(text,config,schema):
 found=[];captures={};bodies=[];excluded=[];lines=text.splitlines(True);i=0
 while i<len(lines):
  line=lines[i]
  if not (line.startswith('fn ') or (line.startswith('const ') and '::promoted[' in line)):
   i+=1;continue
  body=[]
  while i<len(lines):
   body.append(lines[i]);i+=1
   if body[-1].strip()=='}' and body[-1].startswith('}'):break
  body=''.join(body)
  if line.startswith('fn '):
   head=line[3:].strip();j=head.index('(');name=head[:j];k=j+1;depth=1
   while depth:depth+=(head[k]=='(')-(head[k]==')');k+=1
   arguments=split_args(head[j+1:k-1])
  else:name=line[6:].split(': &',1)[0];arguments=[]
  if not selected(name):
   if '::promoted[' in name and '::tests::' in name:excluded.append(name)
   continue
  name=fn_identity(name);decl=[]
  for l in body.splitlines():
   stripped=l.strip()
   if stripped.startswith('let '):
    declaration=stripped[4:].removeprefix('mut ').rsplit(';',1)[0];binding,ty=declaration.split(': ',1);decl.append((binding,ty_identity(ty)))
  for a in arguments:
   binding,ty=a.split(': ',1)
   if binding not in dict(decl):decl.append((binding,ty_identity(ty)))
  aliases=collections.defaultdict(list)
  for l in body.splitlines():
   m=re.match(r'\s*debug (\w+) => (_\d+);',l)
   if m:aliases[m[2]].append(m[1])
  literals=re.findall(r'\bconst\s+("(?:[^"\\]|\\.)*"|true|false|\d+_(?:u|i)(?:size|8|16|32|64|128))',body)
  for binding,ty in decl:
   found.append((name,binding,'canonical',tuple(aliases[binding]),ty))
   for alias in aliases[binding]:found.append((name,alias,'authored-alias',(alias,),ty))
  for index,literal in enumerate(literals):
   ty="&'static str" if literal.startswith('"') else 'bool' if literal in ['true','false'] else literal.rsplit('_',1)[1]
   found.append((name,'literal_'+str(index),'direct-literal',(literal,),ty))
  for arg in arguments:
   for closure in re.findall(r'\{closure@[^}]+\}',arg):
    fields={int(n):ty for n,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',body)};assert set(fields)==set(range(len(fields)));captures[closure]=[fields[n] for n in range(len(fields))]
  bodies.append(dict(name=name,typedBindings=len(decl),aliases=sum(map(len,aliases.values())),literals=len(literals)))
 expected=collections.defaultdict(list)
 for r in schema:
  if r['config']==config:expected[(fn_identity(r['mirFunction']),r['binding'],r['kind'],tuple(r['sourceNames']),ty_identity(r['mirType']))].append(r)
 actual=collections.Counter(found);expected_counts=collections.Counter({key:len(rows)//4 for key,rows in expected.items()})
 assert actual==expected_counts,dict(missing=list((actual-expected_counts).items())[:5],extra=list((expected_counts-actual).items())[:5])
 for key,rows in expected.items():assert collections.Counter(r['position'] for r in rows)=={position:actual[key] for position in ['source','argument','returned','caller']}
 assert len(bodies)==(22 if config=='unit' else 21) and sum('::promoted[' in x['name'] for x in bodies)==(3 if config=='unit' else 2) and len(captures)==5
 assert any(x['name'] in ['width','experimental::execution::width'] for x in bodies)
 if config=='unit':assert excluded and any(x['name']=='experimental::execution::width' for x in bodies)
 return dict(config=config,bodies=bodies,captures=captures,roles=len(found),fields=4*len(found),excludedTestPromotions=len(excluded),exactInventory=True,missing=[],extra=[])

def main():
 receipt=load('receipt.json');assert sha(P/'receipt.json')=='e261cb8e2f30a013db7803baaf057c10d66bef02155c77b79b9ea37985d5ee16'
 for n,h in receipt['bindings'].items():assert sha(P/n)==h,n
 data={};manifests={}
 for label in ['baseline','behavior','candidate']:data[label],manifests[label]=source(label)
 assert digest(manifests['candidate'])=='a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b' and len(manifests['candidate'])==123
 schema=load('inventory-schema.json');old=load('inputs/behavior-inventory-schema.json');oldnames={r['field'] for r in old};names={r['field']:r for r in schema}
 assert len(names)==len(schema)==4800 and len(old)==4792 and all(names[r['field']]==r for r in old)
 added=[r for r in schema if r['field'] not in oldnames];assert len(added)==8
 assert all(r['config']=='unit' and r['mirFunction']=='memory_pinned_step::promoted[0]' and r['envelope']=='active' for r in added)
 for binding in ['_0','_1']:assert collections.Counter(r['position'] for r in added if r['binding']==binding)==dict(source=1,argument=1,returned=1,caller=1)
 changed=[n for n in manifests['candidate'] if manifests['candidate'][n]!=manifests['behavior'][n]];path='src/experimental_swift_reactor/memory_operations.rs';assert changed==[path]
 before=data['behavior'][path].decode();after=data['candidate'][path].decode();stripped=after
 for r in added:
  declaration='    #[cfg(test)]\n    '+r['field']+': '+r['rustType']+',\n';assert stripped.count(declaration)==1;stripped=stripped.replace(declaration,'',1)
 assert stripped==before and after.split('// ACCOUNTING_START')[0]==before.split('// ACCOUNTING_START')[0]
 assert (P/'correction.patch').read_text()==''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/vm/'+path,tofile='b/vm/'+path))
 for r in schema:
  declaration='    '+r['field']+': '+r['rustType']+',\n';assert after.count(declaration)==1
  if r['config']=='unit':assert after.count('    #[cfg(test)]\n'+declaration)==1
 source_result=dict(candidateClosure=digest(manifests['candidate']),behaviorClosure=digest(manifests['behavior']),changedFiles=changed,allOther122FilesUnchanged=True,exactAddedRows=added,originalRowsRetainedExactly=4792,all4800DeclarationsExistExactlyOnce=True,executablePrefixUnchanged=True,productionSourceUnchanged=True,dependenciesUnchanged=True,noOldOwnerOrFrozenSourceChange=True)
 (HERE/'source-review.json').write_bytes(enc(source_result))
 # Independently collect raw compiler roles, including standalone promotions,
 # rather than invoking the producer's canonical validator.
 results=[]
 for feature in ['swift','all']:
  for config in ['production','unit']:
   p=P/('canonical-'+feature+'-'+config+'.mir.gz');raw=gzip.decompress(p.read_bytes());r=inspect(raw.decode(),config,schema);r.update(feature=feature,mirSHA256=sha(p),uncompressedSHA256=hashlib.sha256(raw).hexdigest(),sourceClosure=digest(manifests['candidate']),fresh=False);results.append(r)
 raw=gzip.decompress((HERE/'fresh-swift-unit.mir.gz').read_bytes());r=inspect(raw.decode(),'unit',schema);r.update(feature='swift',mirSHA256=sha(HERE/'fresh-swift-unit.mir.gz'),uncompressedSHA256=hashlib.sha256(raw).hexdigest(),sourceClosure=digest(manifests['candidate']),fresh=True);results.append(r)
 (HERE/'mir-review.json').write_bytes(enc(results))
 # Verify the actual selector implementation admits this caller and excludes
 # test-module promotions; functions and promotions share selected(name).
 tree=ast.parse((P/'inventory.py').read_text());functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
 for name in ['promoted_constants','canonical']:assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='selected' for n in ast.walk(functions[name]))
 spec=importlib.util.spec_from_file_location('frozen_inventory',P/'inventory.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 assert mod.selected('memory_pinned_step::promoted[0]') and not mod.selected('memory_operations::tests::fixture::promoted[0]')
 collector=dict(sharedSelectorCallVerified=True,standaloneSelected=True,testModuleExcluded=True,independentRawMIRConfigurations=5,producerRegressionExecuted=True,scriptSHA256=sha(P/'inventory.py'))
 (HERE/'collector-review.json').write_bytes(enc(collector))
 # Recheck every measured positive position and disjoint interval independently.
 layouts=load('layouts.json');oldlayouts=load('inputs/behavior-layouts.json');layoutresult=[]
 for l in layouts:
  name='layout-binary-'+l['label']+'-'+l['features']+'-'+l['profile']+('-unit' if l['unit'] else '-production');directory=P/'commands'/name;c=json.loads((directory/'receipt.json').read_text())
  assert c['exitCode']==0 and c['sourceUnchanged'] and c['executables'] and c['sourceTreeSHA256']==receipt['sourceArchives']['metadata-'+l['label']]['closure']
  raw=gzip.decompress((directory/'stdout.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==c['stdoutSHA256'];parsed={k:{} for k in ['types','classes','fields','totals','owners']}
  for line in raw.decode().splitlines():
   if 'MM_' not in line:continue
   kind,name,*values=line[line.index('MM_'):].split();values=list(map(int,values));target={'MM_TYPE':'types','MM_CLASS':'classes','MM_FIELD':'fields','MM_TOTAL':'totals','MM_OWNER':'owners'}[kind];assert name not in parsed[target]
   parsed[target][name]=dict(bytes=values[0],alignment=values[1]) if target in ['types','classes'] else dict(offset=values[0],bytes=values[1],alignment=values[2]) if target=='fields' else values[0]
  assert all(parsed[k]==l[k] for k in parsed)
 for l in [v for v in layouts if v['label']=='candidate']:
  oldl=next(v for v in oldlayouts if v['label']=='candidate' and all(v[k]==l[k] for k in ['features','profile','unit']))
  baseline=next(v for v in layouts if v['label']=='baseline' and all(v[k]==l[k] for k in ['features','profile','unit']))
  assert l['owners']==oldl['owners']==baseline['owners'] and l['types']==oldl['types']==baseline['types']
  rows=[r for r in schema if l['unit'] or r['config']!='unit'];assert set(l['fields'])=={r['field'] for r in rows};ends={}
  for r in sorted(rows,key=lambda r:(r['ownerClass'],l['fields'][r['field']]['offset'])):
   f=l['fields'][r['field']];cls=r['ownerClass'];assert f['offset']>=ends.get(cls,0) and f['offset']%f['alignment']==0;ends[cls]=f['offset']+f['bytes'];assert ends[cls]<=l['classes'][cls]['bytes']
   if r['field'] in oldnames:assert all(f[k]==oldl['fields'][r['field']][k] for k in ['bytes','alignment'])
  delta={k:l['totals'][k]-oldl['totals'][k] for k in oldl['totals']};assert {k:v for k,v in delta.items() if v}==({'memory_active':64,'frame':64} if l['unit'] else {})
  layoutresult.append(dict(features=l['features'],profile=l['profile'],unit=l['unit'],fields=len(rows),disjoint=True,oldOwnersUnchanged=True,oldFieldSizesAlignmentsUnchanged=True,totalsDelta=delta))
 (HERE/'layout-review.json').write_bytes(enc(layoutresult))
 # Bounded validation only: an inherited whitespace issue is not a correction
 # runtime issue, but root must normalize it in a separately bound integration.
 whitespace=[]
 for n in manifests['candidate']:
  if not n.endswith('.rs'):continue
  oldlines=data['baseline'].get(n,b'').decode().splitlines();newlines=data['candidate'][n].decode().splitlines()
  matcher=difflib.SequenceMatcher(a=oldlines,b=newlines,autojunk=False)
  for tag,a,b,c,d in matcher.get_opcodes():
   if tag in ['insert','replace']:
    for index in range(c,d):
     if newlines[index] and newlines[index].rstrip()!=newlines[index]:whitespace.append(dict(path=n,line=index+1,text=repr(newlines[index]),inheritedFromBehavior=data['behavior'].get(n)==data['candidate'][n]))
 (HERE/'integration-notes.json').write_bytes(enc(dict(trailingWhitespace=whitespace,correctionCandidateEdited=False,rootOwnsIntegrationNormalization=True)))
 print('independent audit passed: 4800 rows; 5 raw MIR configurations; 8 disjoint layouts; exact eight unit-only field delta',flush=True)

if __name__=='__main__':main()
