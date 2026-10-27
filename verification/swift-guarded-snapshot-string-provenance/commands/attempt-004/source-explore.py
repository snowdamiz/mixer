import gzip,re,json,collections
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
s=gzip.decompress((R/'verification/swift-guarded-snapshot-loader-work-source146/whole-source146.mir.gz').read_bytes()).decode()
source={m['path']: (R/m['source']).read_text() for m in json.loads((R/'verification/swift-guarded-snapshot-loader-work-source146/source-reference-map.json').read_text())['members'] if m['path'].endswith('.rs')}
fs={}
for m in re.finditer(r'^fn (.+?)\((.*?)\) -> (.+?) \{[^\n]*\n',s,re.M):
 end=s.index('\n}\n',m.end())+3
 name=m[1];body=s[m.start():end];params=m[2];ret=m[3]
 if name in fs:continue
 fs[name]={'body':body,'params':params,'ret':ret,'base':name.rsplit('::',1)[-1], 'calls':[],'closure':None,'owner':''}
 loc=re.search(r'owned-work/vm/(.+?):(\d+):\d+:',name)
 if loc:
  src=source[loc[1]].splitlines()[int(loc[2])-1]
  fs[name]['owner']=src
 cl=re.search(r'\{closure@([^}]+)\}',params)
 if cl:fs[name]['closure']=cl[1]
 for line in body.splitlines():
  if not line.startswith('        '):continue
  if ' -> [' in line or ' -> unwind ' in line or ' -> !' in line:
   st=line.split(' // ',1)[0].strip();rhs=st.split(' = ',1)[-1];level=0;cut=None
   for i,ch in enumerate(rhs):
    if ch=='<':level+=1
    elif ch=='>':level-=1
    elif ch=='(' and level==0:cut=i;break
   if cut is None:continue
   target=rhs[:cut]
   if target not in ('switchInt','assert','drop'):fs[name]['calls'].append((target,st))
bybase=collections.defaultdict(list)
for n,v in fs.items():bybase[v['base']].append(n)
def resolve(t):
 if t in fs:return [t]
 selected=None
 if t.startswith('<B as ClosedBranchV1>::'):selected='SnapshotBranchV1'
 elif 'as SharedControlV1>::shared_control' in t:selected='SnapshotAccessV1'
 elif t.startswith('<P as ClosedAdoptionV1>::'):selected='SnapshotAdoptionV1'
 elif 'as experimental::account::MeterControl>::' in t:selected='SwiftControl'
 elif t.startswith('<D as Declaration>::'):selected='SwiftDeclaration'
 elif t.startswith('<swift::ValidatedSwiftReactor as experimental::cache::borrowed::SnapshotView>::'):selected='ValidatedSwiftReactor'
 if selected:
  base=t.rsplit('::',1)[-1];return [n for n in bybase[base] if re.search(r'\b'+selected+r'\b',fs[n]['owner'])]
 if t.startswith('<') and ' as ' in t:
  receiver=t[1:].split(' as ',1)[0].split('::')[-1].lstrip('&')
  base=t.rsplit('::',1)[-1]
  good=[]
  for n in bybase[base]:
   params=fs[n]['params'];first=params.split('_1: ',1)[-1].split(', _2:',1)[0].lstrip('&').removeprefix('mut ').split('::')[-1]
   if first==receiver or fs[n]['ret'].split('::')[-1]==receiver:good.append(n)
  if good:return good
 # Erase balanced generic arguments without discarding later method paths.
 level=0;chars=[]
 for c in t:
  if c=='<':level+=1
  elif c=='>':level-=1
  elif level==0:chars.append(c)
 plain=''.join(chars).replace('::::','::').strip(':')
 if plain in fs:return [plain]
 base=plain.rsplit('::',1)[-1];candidates=bybase[base]
 owner=plain.rsplit('::',1)[0].rsplit('::',1)[-1] if '::' in plain else ''
 if not owner:return []
 good=[]
 for n in candidates:
  if re.search(r'\b'+re.escape(owner)+r'\b',fs[n]['owner']):good.append(n)
 module=plain.rsplit('::',2)[0] if plain.count('::')>=2 else ''
 if module:
  exact=[n for n in good if n.startswith(module+'::<impl at ')]
  if exact:return exact
 return good

roots=['run_one_fixture_v1','run_prepaid_fixture_v1','run_one_loaded_fixture_v1','destroy_returned_fixture_v1','release_after_retirement_v1']
active=list(roots);seen=set();unresolved=collections.defaultdict(list);ambiguous=collections.defaultdict(list);edges=[]
while active:
 n=active.pop()
 if n in seen:continue
 seen.add(n)
 for t,line in fs[n]['calls']:
  dest=resolve(t)
  if len(dest)==1:edges.append((n,dest[0],t));active+=dest
  elif len(dest)>1:ambiguous[t]=dest
  else:unresolved[t].append((n,line))
  for cl in re.findall(r'\{closure@([^}]+)\}',line):
   candidates=[k for k,v in fs.items() if v['closure']==cl]
   if candidates:
    active+=candidates
    for candidate in candidates:edges.append((n,candidate,'callback'))
print('total',len(fs),'seen',len(seen),'edges',len(edges),'ambiguous',len(ambiguous),'external',len(unresolved))
(D/'exploration.json').write_text(json.dumps({'seen':sorted(seen),'edges':edges,'ambiguous':ambiguous,'external':unresolved},indent=2)+'\n')
print('authored unresolved', [(t,len(v)) for t,v in unresolved.items() if t.startswith(('experimental_', 'control::','swift::','retained_profile_loader_v1::','accounted::','Snapshot','<P as'))])
print('ambiguities',[(k,len(v)) for k,v in ambiguous.items()])
print('root types',fs['run_prepaid_fixture_v1']['params'])

rows=[]
for name in seen:
 body=fs[name]['body'];locals=dict(re.findall(r'^    let (?:mut )?(_\d+): (.*?);',body,re.M))
 # Header arguments are mutable/immutable locals with their own typed surfaces.
 locals.update(dict(re.findall(r'(_\d+): (.*?)(?=, _\d+:|$)',fs[name]['params'])))
 for line in body.splitlines():
  code=line.split(' // ',1)[0].strip();m=re.match(r'(_\d+) = (.*);$',code)
  if m and locals.get(m[1],'') in ('&str',"&'static str",'&mut str'):
   rows.append({'function':name,'local':m[1],'rhs':m[2]})
(D/'string-assignments-exploration.json').write_text(json.dumps(rows,indent=2)+'\n')
print('str assignments',len(rows))
for r in rows:
 if not any(r['rhs'].startswith(x) for x in ('const ', 'copy ', 'move ', '&')):print('OTHER STR',r)
