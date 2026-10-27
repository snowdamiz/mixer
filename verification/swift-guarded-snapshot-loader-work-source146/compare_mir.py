"""Compare complete raw-preopt selected definitions, never execute engine code."""
import collections,difflib,gzip,json,re
from pathlib import Path
from prepare import D,R,OLD,FIX,COMP,IND,sha,put
PREFIXES=[str(p) for p in (OLD/'owned-work/vm',D/'owned-work/vm',COMP/'owned-work/production-metadata/vm',IND/'owned-work/exact146-metadata-mir/vm')]
def norm_paths(s):
 for p in PREFIXES:s=s.replace(p,'<VM>')
 return s
def norm_bookkeeping(s):
 # Only the numeric DefId crate/index pair in compiler comment lines changes;
 # its symbolic authored path and crate hash remain intact.
 return '\n'.join(re.sub(r'DefId\(\d+:\d+ ~','DefId(<compiler-index> ~',line) if line.lstrip().startswith('//') else line for line in norm_paths(s).splitlines())
def functions(s):
 result=collections.defaultdict(list)
 for m in re.finditer(r'^fn ',s,re.M):
  start=m.start();end=s.index('\n}\n',start)+3;text=s[start:end];head=text.splitlines()[0];name=head[3:head.index('(')]
  result[norm_paths(name)].append(dict(name=name,text=text,start=start,end=end,head=head))
 return result

def parsed(f):
 text=f['text'];local=dict(re.findall(r'^\s*let (?:mut )?(_\d+): (.+?);(?:\s*//|$)',text,re.M));sig=f['head'][f['head'].index('(')+1:]
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
  local[m[1]]=sig[at:end]
 statements=[];block=False
 for line in text.splitlines():
  if re.match(r'    bb\d+(?: \(cleanup\))?: \{',line):block=True;continue
  if block and line=='    }':block=False;continue
  if block:
   code=line.split(' // ',1)[0].strip()
   if code:statements.append(code)
 return local,statements,[s for s in statements if ' = ' in s and ') -> [' in s]
def const_compiled(s):
 ms=list(re.finditer(r'^const COMPILED: \[Option<&str>; 5\] = \{',s,re.M));assert len(ms)==1
 start=ms[0].start();text=s[start:s.index('\n}\n',start)+3]
 values=re.findall(r'= const "([0-9a-f]{64})";',text);assert len(values)==5
 return text,values

def main():
 raw=gzip.decompress((D/'whole-source146.mir.gz').read_bytes()).decode();newall=functions(raw)
 oldraw=gzip.decompress((OLD/'whole-source.mir.gz').read_bytes()).decode();oldselected=gzip.decompress((OLD/'selected-definitions.mir.gz').read_bytes()).decode();oldall=functions(oldselected)
 oldx=json.loads((OLD/'mir-extraction.json').read_text());rows=[];extract={};selected=[];diffs='';unsupported=[]
 for oldname,oldf in oldx['functions'].items():
  key=norm_paths(oldname);assert len(newall[key])==len(oldall[key])==1,key
  nf=newall[key][0];of=oldall[key][0];before=norm_bookkeeping(of['text']);after=norm_bookkeeping(nf['text'])
  allowed=before.replace('const 145_u64','const 146_u64') if oldf['owner']=='build' and '{closure#' not in oldname else before
  if allowed!=after:unsupported.append(key)
  if before!=after:diffs+=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='source145/'+key,tofile='source146/'+key))
  local,statements,calls=parsed(nf)
  oldlocal={k:norm_paths(v) for k,v in oldf['locals'].items()};newlocal={k:norm_paths(v) for k,v in local.items()}
  oldcalls=[norm_paths(v) for v in oldf['calls']];newcalls=[norm_paths(v) for v in calls]
  assert oldlocal==newlocal,('local-type-change',key)
  assert oldcalls==newcalls,('call-closure-change',key)
  oldstat=[norm_paths(v) for v in oldf['statements']];newstat=[norm_paths(v) for v in statements]
  expected=[v.replace('const 145_u64','const 146_u64') for v in oldstat] if oldf['owner']=='build' and '{closure#' not in oldname else oldstat
  assert expected==newstat,('statement-change',key)
  row=dict(identity=key,owner=oldf['owner'],old_sha256=sha(of['text'].encode()),new_sha256=sha(nf['text'].encode()),old_normalized_sha256=sha(before.encode()),new_normalized_sha256=sha(after.encode()),normalized_body_equal=before==after,only_allowed_count_delta=before!=after and allowed==after,local_places=len(local),statements=len(statements),calls=len(calls),local_types_equal=True,call_targets_and_closure_identity_equal=True)
  rows.append(row);selected.append(nf['text'])
  extract[nf['name']]=dict(declared_name=nf['name'],head=nf['head'],start=nf['start'],end=nf['end'],owner=oldf['owner'],source_path=oldf['source_path'],first_source_line=oldf['first_source_line'],last_source_line=oldf['last_source_line'],locals=local,statements=statements,calls=calls,sha256=sha(nf['text'].encode()))
 assert len(rows)==219 and not unsupported,unsupported
 assert sum(not r['normalized_body_equal'] for r in rows)==1
 joined='\n\n'.join(selected)+'\n';packed=gzip.compress(joined.encode(),mtime=0);(D/'selected-definitions146.mir.gz').write_bytes(packed)
 (D/'selected-MIR145-to146.patch').write_text(diffs)
 put('mir-extraction146.json',dict(schema=1,parent_mir_sha256=sha(raw.encode()),selected_bytes=len(joined.encode()),selected_sha256=sha(joined.encode()),selected_gzip_sha256=sha(packed),function_count=219,source_owners=dict(collections.Counter(f['owner'] for f in extract.values())),source_bodies_without_direct_definition=[],functions=extract))
 # Frozen independent source146 account/entry subset overlap. No old account
 # pricing/inventory function is replayed and no19-function proxy substitutes219.
 account=gzip.decompress((IND/'entry-and-account.mir.gz').read_bytes()).decode();accountrows=[]
 for key,items in functions(account).items():
  assert len(items)==len(newall[key])==1,key
  a=norm_bookkeeping(items[0]['text']);b=norm_bookkeeping(newall[key][0]['text'])
  accountrows.append(dict(identity=key,normalized_equal=a==b,old_sha256=sha(items[0]['text'].encode()),new_sha256=sha(newall[key][0]['text'].encode()),old_normalized_sha256=sha(a.encode()),new_normalized_sha256=sha(b.encode())))
 assert len(accountrows)==19 and all(r['normalized_equal'] for r in accountrows)
 oldconst,oldvalues=const_compiled(oldraw);newconst,newvalues=const_compiled(raw)
 oldreceipt=json.loads((OLD/'compiler-receipt.json').read_text());newreceipt=json.loads((D/'compiler-receipt.json').read_text())
 keys=('MIXER_LOADER_MANIFEST_SHA256','MIXER_LOADER_COMMAND_SHA256','MIXER_LOADER_COMPILE_ENV_SHA256','MIXER_LOADER_COMPILER_SHA256','MIXER_LOADER_COMPILER_VERSION_SHA256')
 assert oldvalues==[oldreceipt['environment'][k] for k in keys]
 assert newvalues==[newreceipt['environment'][k] for k in keys]
 # Replacing only the five same-length identity strings yields the same complete
 # compile-time constant body after path/DefId comment normalization.
 cc=norm_bookkeeping(oldconst)
 for a,b in zip(oldvalues,newvalues):cc=cc.replace(a,b)
 assert cc==norm_bookkeeping(newconst)
 put('MIR-comparison.json',dict(schema=1,source145_MIR_sha256=sha(oldraw.encode()),source146_MIR_sha256=sha(raw.encode()),definitions=219,normalized_complete_bodies_equal=218,count_literal_only_bodies=1,all_local_types_and_call_targets_equal=True,functions=rows,unsupported_differences=unsupported,normalization=['only known absolute VM source-root prefixes -> <VM>','only numeric DefId crate/index in compiler comment lines; symbolic path/crate hash retained'],numeric_quote_accepted=False))
 put('account19-overlap.json',dict(schema=1,functions=19,all_normalized_complete_bodies_equal=True,comparison='accepted independent source146 full19 definitions against fresh full source146 MIR',rows=accountrows,work_or_storage_inventory_replayed=False))
 put('compile-constant-comparison.json',dict(schema=1,old_sha256=sha(oldconst.encode()),new_sha256=sha(newconst.encode()),same_normalized_constant_body_after_exact_identity_substitution=True,identities=[dict(key=k,old=a,new=b,bytes_each=64,changed=a!=b) for k,a,b in zip(keys,oldvalues,newvalues)],all_values_valid_64_lowercase_hex=True,all5_Some_branches_preserved=True,source_count_literal=dict(old=145,new=146,same_u64_width=True,same_operation_and_decision_shape=True),constant_construction_executed=False))
 print(json.dumps(dict(status='complete-preopt-source146-comparison-pass',definitions=219,unchanged_bodies=218,count_only_bodies=1,account19_equal=True,unsupported=0)))
if __name__=='__main__':main()
