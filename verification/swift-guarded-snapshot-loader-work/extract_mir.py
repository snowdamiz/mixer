"""Extract complete compiler definitions selected by frozen source spans."""
import collections,gzip,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[1];PREFIX=str(D/'owned-work/vm')+'/'
def sha(x):return hashlib.sha256(x).hexdigest()
def put(n,x):(D/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
s=gzip.decompress((D/'whole-source.mir.gz').read_bytes()).decode();ledger=json.loads((D/'source-body-ledger.json').read_text())
starts=[m.start() for m in re.finditer(r'^fn ',s,re.M)];defs={}
for start in starts:
 end=s.index('\n}\n',start)+3;v=s[start:end];head=v.splitlines()[0];name=head[3:head.index('(')]
 declared_name=name
 if name in defs:name=name+'::duplicate#'+str(len(defs))
 defs[name]=dict(text=v,start=start,end=end,head=head,declared_name=declared_name)
selected={}
for name,f in defs.items():
 spans=re.findall(re.escape(PREFIX)+r'([^:]+):(\d+):\d+',f['text'].split('\n',1)[1])
 paths={p for p,n in spans}
 if len(paths)!=1:continue
 p=next(iter(paths));lines=[int(n) for q,n in spans if q==p]
 candidates=[(key,r['source']) for key,r in ledger['nodes'].items() if r['source']['path'].endswith('/'+p) and r['source']['line']<=min(lines) and max(lines)<=r['source']['end_line']]
 if candidates:
  key,row=min(candidates,key=lambda k:k[1]['end_line']-k[1]['line'])
  selected[name]=dict(f,owner=key,source_path=p,first_source_line=min(lines),last_source_line=max(lines))
# Derived PartialEq for product types really invoked by selected primitives.
eqtypes=['Type','Profile','BlockKind','WasiFunction','descriptor::WasiFunction','FileIdentityV1','swift::SwiftValidationBudget']
for name,f in defs.items():
 if f['declared_name'].endswith('::eq') and any(re.search(r'_1: &'+re.escape(t)+r'[,)]',f['head']) for t in eqtypes):
  selected[name]=dict(f,owner='derived_eq',source_path='compiler-generated-from-source-derive',first_source_line=0,last_source_line=0)
# Standard Default/PartialEq may dispatch these authored derive bodies. Include
# the exact generated definitions rather than treating that dispatch as free.
for name,f in defs.items():
 if f['declared_name'].endswith('::default') and any((' -> '+t+' {') in f['head'] for t in ('Cursor','experimental::account::Cursor','experimental::Usage','account::BodyObservations','BodyObservations','metadata::SwiftDeclaration','SwiftDeclaration','retained_profile_loader_v1::LoaderUsageV1','experimental::metadata::Span')):
  selected[name]=dict(f,owner='derived_default',source_path='compiler-generated-from-source-derive',first_source_line=0,last_source_line=0)
 if f['declared_name'].endswith('::floats') and '_1: Profile' in f['head']:
  selected[name]=dict(f,owner='profile_floats',source_path='src/lib.rs',first_source_line=0,last_source_line=0)
for name,f in defs.items():
 if any(f['declared_name'].endswith('::'+method) for method in ('memory','table')) and 'SwiftDeclaration' in f['head']:
  selected[name]=dict(f,owner='declaration_setter',source_path='src/experimental/metadata.rs',first_source_line=0,last_source_line=0)
# Compilation contains generic vvalidate and concrete public entry. No source
# method silently absent is accepted: dump the missing span roster explicitly.
owners=collections.Counter(f['owner'] for f in selected.values())
missing=[n for n in ledger['nodes'] if not owners[n]]
joined='\n\n'.join(f['text'] for f in selected.values())+'\n';packed=gzip.compress(joined.encode(),mtime=0);(D/'selected-definitions.mir.gz').write_bytes(packed)
# Parse whole-line locals/parameters and statement/call lists without truncation.
for name,f in selected.items():
 locals_=dict(re.findall(r'^\s*let (?:mut )?(_\d+): (.+?);(?:\s*//|$)',f['text'],re.M))
 sig=f['head'][f['head'].index('(')+1:]
 # Parameter types may contain nested tuples/functions: read _N: separators.
 for m in re.finditer(r'(_\d+): ',sig):
  at=m.end();depth=0;end=at
  while end<len(sig):
   c=sig[end]
   if c in '<[(':depth+=1
   elif c in '>])':
    if depth==0:break
    depth-=1
   elif c==',' and depth==0:break
   end+=1
  locals_[m.group(1)]=sig[at:end]
 statements=[];block=False
 for line in f['text'].splitlines():
  if re.match(r'    bb\d+(?: \(cleanup\))?: \{',line):block=True;continue
  if block and line=='    }':block=False;continue
  if block:
   code=line.split(' // ',1)[0].strip()
   if code:statements.append(code)
 f['locals']=locals_;f['statements']=statements
 f['calls']=[x for x in statements if ' = ' in x and ') -> [' in x]
 # Complete definitions, including compiler-only closure functions and derives.
 f['sha256']=sha(f['text'].encode())
put('mir-extraction.json',dict(schema=1,parent_mir_sha256=sha(s.encode()),selected_bytes=len(joined.encode()),selected_sha256=sha(joined.encode()),selected_gzip_sha256=sha(packed),function_count=len(selected),source_owners=dict(owners),source_bodies_without_direct_definition=missing,functions={n:{k:v for k,v in f.items() if k!='text'} for n,f in selected.items()}))
print(json.dumps(dict(functions=len(selected),missing=missing,selected_bytes=len(joined.encode()))))
