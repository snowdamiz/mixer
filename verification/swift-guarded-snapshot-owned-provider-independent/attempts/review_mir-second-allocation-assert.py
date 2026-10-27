#!/usr/bin/env python3
"""Independent complete MIR text partition and old-body comparison; no compiler."""
from pathlib import Path
import collections,difflib,gzip,hashlib,json,re,sys,time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];BASE=ROOT/'verification/swift-guarded-snapshot-scoped-binding-source'
INERT=('outer_parent_layout_query_v1','outer_parent_account_layout_query_v1','scoped_result_layout_query_v1','scoped_local_binding_compiles_v1','independent_provider_layout_query_v1')
NEW=('describe_existing_owner_candidate_v1','InputBackingDescriptionV1::')
PREFIXES=(str(BASE/'owned-work/positive/vm'),str(HERE/'owned-work/compiler-metadata-mir/vm'))
def sha(d):return hashlib.sha256(d).hexdigest()
def write(n,o):(HERE/n).write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def strip_comment(line):
 quoted=False;escaped=False
 for i,c in enumerate(line):
  if escaped:escaped=False;continue
  if quoted and c=='\\':escaped=True;continue
  if c=='"':quoted=not quoted;continue
  if not quoted and line[i:i+2]=='//':return line[:i].rstrip()
 return line.rstrip()
def outside(line,fn):
 pieces=re.split(r'("(?:[^"\\]|\\.)*")',line)
 return ''.join(piece if i%2 else fn(piece) for i,piece in enumerate(pieces))
def partition(text):
 lines=text.splitlines();out=[];i=0;covered=0;ignored=0
 while i<len(lines):
  line=lines[i]
  if not line.strip() or line.startswith('//'):ignored+=1;i+=1;continue
  assert not line[0].isspace() and not line.startswith('}'),(i,line)
  start=i;i+=1
  if line.endswith(' {'):
   while i<len(lines) and not lines[i].startswith('}'):i+=1
   assert i<len(lines) and lines[i]=='}',(start,line)
   i+=1
  else:assert line.startswith('const ') and line.endswith(';'),(i,line)
  out.append('\n'.join(lines[start:i]));covered+=i-start
 assert covered+ignored==len(lines)
 return out,{'lines':len(lines),'captured_lines':covered,'blank_or_top_comment_lines':ignored,'complete_partition':True}
def kind(b):
 h=b.split('\n',1)[0]
 return 'fn' if h.startswith('fn ') else 'alloc' if re.match('alloc\\d+ ',h) else 'singleline_const' if '\n' not in b else 'static' if h.startswith('static ') else 'const_or_anonymous'
def tagged(b,names):
 h=b.split('\n',1)[0]
 return any(h.startswith('fn '+n+'(') or h.startswith('fn '+n+'::') or h.startswith('const '+n) or h.startswith(n+'::') for n in names)
def normalize(b,mapping=None):
 def trans(s):
  for p in PREFIXES:s=s.replace(p,'<SOURCE>')
  s=re.sub(r'(?<= at )<SOURCE>/([^\s:]+):\d+:\d+: \d+:\d+',r'<SOURCE>/\1:<SPAN>',s)
  if mapping:s=re.sub(r'\balloc\d+\b',lambda m:mapping.get(m.group(),m.group()),s)
  return s
 return '\n'.join(outside(strip_comment(line),trans) for line in b.splitlines() if strip_comment(line).strip())
def compare(old,new):
 a=[x for x in old if not tagged(x,INERT)];b=[x for x in new if not tagged(x,INERT) and not tagged(x,NEW)]
 aa=[re.match(r'alloc\d+',x).group() for x in a if kind(x)=='alloc'];bb=[re.match(r'alloc\d+',x).group() for x in b if kind(x)=='alloc']
 assert len(aa)==len(bb)==1953
 mapping=dict(zip(bb,aa));assert len(mapping)==len(set(mapping.values()))==1953
 na=[normalize(x) for x in a];nb=[normalize(x,mapping) for x in b]
 diffs=[]
 for i,(x,y) in enumerate(zip(na,nb)):
  if x!=y:diffs.append({'index':i,'before_header':x.split('\n',1)[0],'after_header':y.split('\n',1)[0],'diff':''.join(difflib.unified_diff(x.splitlines(True),y.splitlines(True)))[:5000]})
 return {'equal':len(na)==len(nb) and not diffs,'before_blocks':len(na),'after_blocks':len(nb),'old_kinds':dict(collections.Counter(map(kind,a))),'new_old_scope_kinds':dict(collections.Counter(map(kind,b))),'differences':diffs,'allocation_bijection':mapping,'allocation_deltas':dict(collections.Counter(int(x[5:])-int(y[5:]) for x,y in zip(bb,aa))),'before_normalized_sha256':sha('\n\n'.join(na).encode()),'after_normalized_sha256':sha('\n\n'.join(nb).encode())}
def main():
 begin=time.monotonic();bp=BASE/'commands/compiler-positive/query.mir.gz';np=HERE/'commands/compiler-metadata-mir/query.mir.gz'
 bo=bp.read_bytes();no=np.read_bytes();br=gzip.decompress(bo);nr=gzip.decompress(no)
 assert sha(bo)=='394400c084d27694f6706026861cf09a414ed1630b7ccdf875d7dd27d1aba8f7'
 assert sha(br)=='9501d7d03a8a1ab793ebc493643828bf049a6e7100bad95a180b6d269251b6a9'
 old,op=partition(br.decode());new,npa=partition(nr.decode());r=compare(old,new)
 r.update(schema=1,baseline_gzip_sha256=sha(bo),baseline_raw_sha256=sha(br),candidate_gzip_sha256=sha(no),candidate_raw_sha256=sha(nr),baseline_partition=op,candidate_partition=npa,excluded_inert_queries=list(INERT),new_scope_prefixes=list(NEW),scope='Every old production function, multiline and singleline const/static/anonymous constant and allocation block; new provider and inert queries separately inventoried; no runtime qualification',elapsed_seconds=time.monotonic()-begin)
 write('mir-comparison.json',r)
 added=[x for x in new if tagged(x,NEW)];(HERE/'provider.mir').write_text('\n\n'.join(added)+'\n')
 query=next(x for x in new if x.startswith('fn independent_provider_layout_query_v1('))
 vals=[int(x) for x in re.findall(r'\[u8; (\d+)\]',query.split('\n',1)[0])];assert len(vals)==20
 from compile_once import TYPES
 layouts=[{'name':n,'type':t,'size':vals[2*i],'align':vals[2*i+1]} for i,(n,t) in enumerate(TYPES)]
 write('layouts.json',{'schema':1,'rows':layouts,'observations':20,'exact_query_header':query.split('\n',1)[0],'scope':'Production cfg type layout observations only; closure capture layout, full frames/caller occurrence/return/move and acquisition backing not priced'})
 roster=[]
 for b in added:
  calls=[strip_comment(x).strip() for x in b.splitlines() if re.search(r' -> \[return:',strip_comment(x))]
  locals=[strip_comment(x).strip() for x in b.splitlines() if re.match(r'\s*let (?:mut )?_\d+:',x)]
  roster.append({'header':b.split('\n',1)[0],'kind':kind(b),'sha256':sha(b.encode()),'locals':locals,'calls':calls})
 write('new-mir-role-call-roster.json',{'schema':1,'blocks':roster,'all_new_function_headers':[x['header'] for x in roster if x['kind']=='fn'],'anonymous_and_then_closure_capture_layout':'pending; actual closure type and local/call roles retained, no guessed layout','provider_runtime_execution':False,'complete_pricing':False})
 # Independent adverse comparator controls include the previously omitted one-line constants.
 controls=[]
 for label,predicate,mutation in [('singleline-const-value',lambda x:kind(x)=='singleline_const',lambda x:x.replace(' = const ',' = const 999999 + ',1)),('old-function-instruction',lambda x:kind(x)=='fn' and not tagged(x,INERT) and not tagged(x,NEW),lambda x:x.replace('return;','unreachable;',1)),('allocation-extent',lambda x:kind(x)=='alloc',lambda x:x.replace('(size: ','(size: 999999',1))]:
  idx=next(i for i,x in enumerate(new) if predicate(x) and mutation(x)!=x);changed=list(new);changed[idx]=mutation(changed[idx]);rr=compare(old,changed);assert not rr['equal'];controls.append({'label':label,'changed_header':new[idx].split('\n',1)[0],'detected':True})
 write('mir-adverse-controls.json',{'schema':1,'controls':controls,'all_detected':True})
 print(json.dumps({'equal':r['equal'],'before_blocks':r['before_blocks'],'after_blocks':r['after_blocks'],'kinds':r['old_kinds'],'differences':len(r['differences']),'new_blocks':len(added),'layouts':len(layouts),'adverse_controls':len(controls),'elapsed_seconds':time.monotonic()-begin}))
 return 0 if r['equal'] else 1
if __name__=='__main__':raise SystemExit(main())
