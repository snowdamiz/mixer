from review import *
import collections
schema=json.loads((PRODUCER/'inventory-schema.json').read_text())
def split_args(s):
 out=[];level=0;start=0
 for i,c in enumerate(s):
  if c in '<([{':level+=1
  elif c in '>)]}':level-=1
  elif c==',' and level==0:out.append(s[start:i].strip());start=i+1
 out.append(s[start:].strip());return [x for x in out if x]
def selected(s):
 return ('memory_operations::' in s or s.startswith('memory_pinned') or s in ['width','experimental::execution::width']) and '::tests::' not in s and '::tests}' not in s

def function_identity(name):
 name=name.removeprefix('experimental_swift_reactor::execution::frame_operations::')
 if name.startswith('memory_operations::memory_pinned'):name=name.removeprefix('memory_operations::')
 return name
def type_identity(ty):
 ty=ty.replace('crate::','')
 return re.sub(r'(?<![:\w])control::','experimental_swift_reactor::control::',ty)

def inspect(text,config):
 found=[];captures={};bodies=[]
 lines=text.splitlines(True);i=0
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
  if not selected(name):continue
  name=function_identity(name)
  decl=[]
  for l in body.splitlines():
   stripped=l.strip()
   if stripped.startswith('let '):
    declaration=stripped[4:].removeprefix('mut ').rsplit(';',1)[0];binding,ty=declaration.split(': ',1);decl.append((binding,type_identity(ty)))
  for a in arguments:
   binding,ty=a.split(': ',1)
   if binding not in dict(decl):decl.append((binding,type_identity(ty)))
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
    fields={int(n):ty for n,ty in re.findall(r'_1\.(\d+): ([^\n]*?)\)',body)}
    assert set(fields)==set(range(len(fields)))
    captures[closure]=[fields[n] for n in range(len(fields))]
  bodies.append(dict(name=name,typedBindings=len(decl),aliases=sum(map(len,aliases.values())),literals=len(literals)))
 expected=collections.defaultdict(list)
 for r in schema:
  if r['config']==config:expected[(function_identity(r['mirFunction']),r['binding'],r['kind'],tuple(r['sourceNames']),type_identity(r['mirType']))].append(r)
 actual=collections.Counter(found)
 expected_counts=collections.Counter({key:len(rows)//4 for key,rows in expected.items()})
 assert not (expected_counts-actual),(config,list((expected_counts-actual).items())[:4])
 missing=actual-expected_counts
 assert (not missing) if config=='production' else (len(missing)==2 and all('memory_pinned_step::promoted[0]'==key[0] and key[1] in ['_0','_1'] and count==1 for key,count in missing.items())),missing
 for key,rows in expected.items():assert collections.Counter(r['position'] for r in rows)=={position:actual[key] for position in ['source','argument','returned','caller']}
 assert len(bodies)==(22 if config=='unit' else 21) and sum('::promoted[' in x['name'] for x in bodies)==(3 if config=='unit' else 2) and len(captures)==5
 assert any(x['name'] in ['width','experimental::execution::width'] for x in bodies)
 if config=='unit':assert any(x['name']=='experimental::execution::width' for x in bodies)
 return dict(config=config,bodies=bodies,captures=captures,roles=len(found),fields=4*len(found),allSchemaRowsReproduced=True,missingPositiveRoles=[dict(function=key[0],binding=key[1],kind=key[2],sourceNames=key[3],mirType=key[4],multiplicity=count,requiredPositions=['source','argument','returned','caller']) for key,count in missing.items()],exactInventory=not bool(missing))
def main():
 results=[]
 for feature,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  for unit in [False,True]:
   config='unit' if unit else 'production';name='mir-'+feature+'-'+config;extra={'RUSTC_BOOTSTRAP':'1'}
   if unit:args=['cargo','test','--lib','--no-run','--locked','--offline',*flags];extra['RUSTFLAGS']='--emit=mir,link -Zmir-include-spans=yes'
   else:args=['cargo','rustc','--lib','--locked','--offline',*flags,'--','--emit=mir','-Zmir-include-spans=yes']
   if not (HERE/(name+'.mir.gz')).exists():
    p=run(name,args,SCRATCH/'candidate/vm',extra);assert p.returncode==0
    files=[p for p in (SCRATCH/('target-'+name)/'debug/deps').glob('*.mir') if '::memory_operation(' in p.read_text()];assert len(files)==1
    (HERE/(name+'.mir.gz')).write_bytes(gzip.compress(files[0].read_bytes(),mtime=0))
   text=gzip.decompress((HERE/(name+'.mir.gz')).read_bytes()).decode();result=inspect(text,config);result.update(feature=feature,mirSHA256=hashlib.sha256(text.encode()).hexdigest(),sourceClosure=digest(manifest(SCRATCH/'candidate/vm')));results.append(result);(HERE/'mir-results.json').write_bytes(enc(results))
 assert len(schema)==4792 and len({r['field'] for r in schema})==4792
 counts=collections.Counter(r['config'] for r in schema);assert counts=={'production':2104,'unit':2156,'source':532}
 assert sum(r['envelope']=='permanent' for r in schema)==52
 (HERE/'inventory-results.json').write_bytes(enc(dict(totalFields=len(schema),configurationFields=dict(counts),authoredActiveFields=480,authoredPermanentFields=52,configurations=4,independentRawMIRRoles=True,compilerStackOrRSS=False,verdict='request-changes',requiredUnitCanonicalFields=2164,requiredTotalFields=4800,missingUnitFields=8)))
 print('four fresh MIR configurations reproduce all schema rows; both unit configurations expose two omitted promoted typed roles requiring eight fresh fields; inventory request-changes',flush=True)

if __name__=='__main__':main()
