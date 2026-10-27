"""Read-only MIR-to-source occurrence projection plus enumerated layout requests."""
from pathlib import Path
import json,re,hashlib
ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent/'swift-guarded-snapshot-composition-source-preparation'
BASE=str(INPUT/'source/vm/src')+'/'
RANGES={
 'experimental/swift.rs':[(766,1374)],
 'experimental/account.rs':[(232,240),(329,333)],
 'experimental_swift_reactor/cache/initial_profile_v1.rs':[(262,283)],
 'experimental_swift_reactor/retained_profile_loader_v1.rs':[(150,154),(215,238),(1399,1413)],
 'experimental_swift_reactor/cache.rs':[(1497,1499)],
 'experimental_swift_reactor/control.rs':[(351,356),(824,826)],
 'experimental_wasi/accounted.rs':[(432,432)],
 'experimental_wasi/mod.rs':[(638,638)],
}
def split_top(s,delimiter=','):
 out=[];at=0;depth=0
 for i,c in enumerate(s):
  if c in '<([{':depth+=1
  elif c in '>)]}':depth-=1
  elif c==delimiter and depth==0:out.append(s[at:i].strip());at=i+1
 out.append(s[at:].strip());return out

def functions():
 s=(ROOT/'owned-work/source-slots.mir').read_text();out=[]
 # MIR bodies end at the first column-zero }. Promoted allocations are separately classified.
 for m in re.finditer(r'(?m)^fn .*?\n\}',s,re.S):
  block=m.group();ret=re.search(r'^    let (?:mut )?_0: (.*?);\s*// return place in scope \d+ at (.*?):(\d+):(\d+): (\d+):(\d+)',block,re.M)
  if not ret:continue
  path=ret[2].removeprefix(BASE);line=int(ret[3])
  if path not in RANGES or not any(lo<=line<=hi for lo,hi in RANGES[path]):continue
  header=block.splitlines()[0]
  # Source declaration identity includes impl header and closure ordinal, retaining eight macro expressions.
  if re.search(r'::(?:as_slice|clone)\(',header):continue
  identity=header[3:header.index('(_') if '(_' in header else header.index('()')]
  identity=identity.replace(str(INPUT/'source/vm/src')+'/','source/')
  fid='encoder::'+identity
  argtext=header[header.index('(')+1:header.rindex(') ->')]
  # impl span does not contain parentheses; the first ( is the argument list.
  args=[]
  for arg in split_top(argtext):
   if not arg:continue
   a,t=arg.split(': ',1);args.append((a,t))
  declarations={a:{'type':t,'argument':True} for a,t in args}
  for d in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*?);\s*// (.*)',block,re.M):
   declarations[d[1]]={'type':d[2],'argument':False,'comment':d[3]}
  debug={}
  for d in re.finditer(r'debug ([A-Za-z_][A-Za-z_0-9]*) => (_\d+);',block):debug.setdefault(d[2],[]).append(d[1])
  roles=[]
  for local,d in sorted(declarations.items(),key=lambda x:int(x[0][1:])):
   spans=re.findall(re.escape(BASE)+r'([^:]+):(\d+):(\d+): (\d+):(\d+)',d.get('comment',''))
   source={'path':path,'start_line':line,'end_line':int(ret[5])} if not spans else {'path':spans[0][0],'start_line':int(spans[0][1]),'start_column':int(spans[0][2]),'end_line':int(spans[0][3]),'end_column':int(spans[0][4])}
   uses=[]
   for b in block.splitlines():
    if re.search(r'(?<![A-Za-z0-9_])'+re.escape(local)+r'(?!\d)',b) and not re.match(r'\s*(let |debug )',b):uses.append(b.strip())
   role='return-expression' if local=='_0' else ('arg.'+','.join(debug.get(local,[local])) if d['argument'] else ('local.'+','.join(debug[local]) if local in debug else 'temporary.'+local))
   roles.append({'id':fid+'::'+role+('::'+local if local!='_0' else ''),'mir_local':local,'kind':'return-expression' if local=='_0' else 'parameter' if d['argument'] else 'named-local-or-pattern' if local in debug else 'temporary','compiler_type':d['type'],'source':source,'debug_names':debug.get(local,[]),'source_uses':uses,'multiplicity':1,'partition':'encoder-callee','lifetime_rule':'one slot per declaration; loop iterations reuse; all disjoint arms conservatively included'})
  out.append({'id':fid,'header':header,'source':{'path':path,'return_line':line},'roles':roles,'mir':block})
 return out
if __name__=='__main__':
 fs=functions();(ROOT/'function-bodies.mir').write_text('\n\n'.join(f['mir'] for f in fs)+'\n')
 compact=[{k:v for k,v in f.items() if k!='mir'} for f in fs]
 (ROOT/'raw-source-occurrences.json').write_text(json.dumps({'schema':1,'functions':compact},indent=2)+'\n')
 types={}
 for f in fs:
  for r in f['roles']:types.setdefault(r['compiler_type'],[]).append(r['id'])
 (ROOT/'type-requests.json').write_text(json.dumps(types,indent=2)+'\n')
 print('functions',len(fs),'roles',sum(len(f['roles']) for f in fs),'unique types',len(types))
 print(*[(f['id'],len(f['roles'])) for f in fs],sep='\n')
