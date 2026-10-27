"""Enumerate all bounded added owner/caller product source slots from raw MIR."""
from pathlib import Path
import hashlib,json,re
from probe import ROOT,INPUT,sha,save,canonical
RANGES={
 'experimental_swift_reactor/control.rs':[(606,718),(1820,2100)],
 'experimental_swift_reactor/cache/initial_profile_v1.rs':[(125,187),(284,592)],
 'experimental_swift_reactor/cache.rs':[(4868,4915)],
 'experimental_wasi/accounted.rs':[(436,460)],
 'experimental/swift.rs':[(1696,1710)],
 'experimental_swift_reactor/retained_profile_loader_v1.rs':[(156,179)],
}
def split_top(s):
 out=[];at=0;depth=0
 for i,c in enumerate(s):
  if c in '<([{':depth+=1
  elif c in '>)]}':depth-=1
  elif c==',' and depth==0:out.append(s[at:i].strip());at=i+1
 out.append(s[at:].strip());return out
def extract(mir,vm,baseline=False,host=False,strict=True):
 base=str(vm/'src')+'/';out=[]
 for match in re.finditer(r'(?m)^fn .*?\n\}',mir,re.S):
  body=match.group();ret=re.search(r'^    let (?:mut )?_0: (.*?);\s*// return place in scope \d+ at (.*?):(\d+):(\d+): (\d+):(\d+)',body,re.M)
  if not ret or not ret[2].startswith(base):continue
  path=ret[2].removeprefix(base);line=int(ret[3]);header=body.splitlines()[0];fname=header[3:header.index('(')]
  if host:include=fname=='selected_owned_files_v1' and path=='experimental_swift_reactor/cache/initial_profile_v1.rs'
  elif baseline:
   include=(path=='experimental_swift_reactor/control.rs' and (fname.endswith('::adopt_body') or '::adopt_body::' in fname)) or (path=='experimental_swift_reactor/cache/initial_profile_v1.rs' and (fname.startswith('construct_with_initial_profile_v1'))) or (path=='experimental_swift_reactor/retained_profile_loader_v1.rs' and (fname.endswith('::adopt') or '::adopt::{closure#' in fname))
  else:include=(path in RANGES and any(a<=line<=b for a,b in RANGES[path])) or (path=='experimental_swift_reactor/control.rs' and fname.endswith('::end_construction_phase_with_wasi')) or (path=='experimental_swift_reactor/cache.rs' and ('::drop_cleanup_return_storage' in fname or (line==1746 and fname.endswith('::complete'))))
  if not include:continue
  if re.search(r'::(?:clone|fmt|eq|assert_fields_are_eq)\b',fname):continue
  if fname.startswith(('OriginalAccessV1','SnapshotCauseV1::','SnapshotAttemptV1::','SnapshotStopV1::','SnapshotAdmissionErrorV1::','SelectedSnapshotBodyV1')):continue
  identity=fname.replace(base,'source/')
  argtext=header[header.index('(')+1:header.rindex(') ->')]
  declarations={}
  for a in split_top(argtext):
   if a:
    n,t=a.split(': ',1);declarations[n]={'type':t,'argument':True}
  for d in re.finditer(r'^\s+let (?:mut )?(_\d+): (.*?);\s*// (.*)',body,re.M):declarations[d[1]]={'type':d[2],'argument':False,'comment':d[3]}
  names={}
  for d in re.finditer(r'debug ([A-Za-z_][A-Za-z_0-9]*) => (_\d+);',body):names.setdefault(d[2],[]).append(d[1])
  roles=[];source_lines=(vm/'src'/path).read_text().splitlines()
  for local,d in sorted(declarations.items(),key=lambda x:int(x[0][1:])):
   span=re.search(re.escape(base)+r'([^:]+):(\d+):(\d+): (\d+):(\d+)',d.get('comment',''))
   if d['argument']:
    debug=next((b for b in body.splitlines() if any('debug '+n+' => '+local+';' in b for n in names.get(local,[]))),None)
    if debug:span=re.search(re.escape(base)+r'([^:]+):(\d+):(\d+): (\d+):(\d+)',debug)
   src={'path':path,'start_line':int(span[2]) if span else line,'start_column':int(span[3]) if span else int(ret[4]),'end_line':int(span[4]) if span else int(ret[5]),'end_column':int(span[5]) if span else int(ret[6])}
   lines=source_lines[src['start_line']-1:src['end_line']]
   if len(lines)==1:snippet=lines[0][src['start_column']-1:src['end_column']-1]
   else:
    if lines:lines[0]=lines[0][src['start_column']-1:];lines[-1]=lines[-1][:src['end_column']-1]
    snippet='\n'.join(lines)
   kind='return-expression' if local=='_0' else 'parameter' if d['argument'] else 'named-local-or-pattern' if local in names else 'temporary'
   uses=[b.strip().replace(base,'source/') for b in body.splitlines() if re.search(r'(?<![A-Za-z0-9_])'+re.escape(local)+r'(?!\d)',b) and not re.match(r'\s*(let |debug )',b)]
   roles.append({'id':'owner::'+identity+'::'+local,'mir_local':local,'kind':kind,'compiler_type':d['type'].replace(base,'source/'),'source':src,'source_text':snippet,'product_source_span_found':span is not None,'mir_declaration_origin':d.get('comment','actual parameter header; debug span or enclosing function return-span fallback'),'source_member_sha256':sha((vm/'src'/path).read_bytes()),'debug_names':names.get(local,[]),'uses':uses,'multiplicity':1})
  out.append({'id':'owner::'+identity,'name':identity,'header':header.replace(base,'source/'),'source':{'path':path,'return_line':line},'roles':roles,'mir':body.replace(base,'source/')})
 # No compiler-synthesized duplicate constructor source templates.
 if strict:assert len({f['id'] for f in out})==len(out)
 return out
def classify(f):
 p=f['source']['path'];line=f['source']['return_line'];name=f['name']
 if p.endswith('control.rs'):
  if '::adopt_body_core_v1' in name:return 'shared-adoption'
  if line<719 or (1820<=line<=1843):return 'common'
 if p.endswith('initial_profile_v1.rs'):
  if name.startswith('construct_profile_core_v1'):return 'shared-constructor'
  if line<133 or (284<=line<=320):return 'common'
  if 421<=line<=515:return 'admitted-only'
 if p.endswith('retained_profile_loader_v1.rs') and line in (165,169):return 'common'
 return 'selected-unconditional'
if __name__=='__main__':
 fs=extract((ROOT/'owned-work/source-slots.mir').read_text(),INPUT/'source/vm')
 oldvm=ROOT.parent/'swift-guarded-snapshot-encoder-implementation/source/vm'
 old=extract((ROOT/'owned-work/inherited-slots.mir').read_text(),oldvm,True)
 host=extract((ROOT/'owned-work/unit-slots.mir').read_text(),INPUT/'source/vm',host=True);assert len(host)==1
 for r in host[0]['roles']:
  src=r['source'];line=src['start_line'];col=src['start_column']
  selected=(r['kind']=='parameter' and r['mir_local'] in ('_1','_3')) or (r['product_source_span_found'] and (604<=line<=615 or 620<=line<=625 or 630<=line<=631 or line==637))
  if line==612 and col>=26:selected=False
  if r['mir_local']=='_2':selected=False
  r['funding_class']='host-caller' if selected else 'external-harness'
  r['exclusion_reason']=None if selected else 'filesystem paths/creation/output, assertion/panic/formatting machinery or external directory argument; explicitly outside product funding'
 for f in fs:f['funding_class']=classify(f)
 (ROOT/'inherited-function-bodies.mir').write_text('\n\n'.join(f['mir'] for f in old)+'\n')
 (ROOT/'function-bodies.mir').write_text('\n\n'.join(f['mir'] for f in fs)+'\n')
 (ROOT/'host-caller.mir').write_text(host[0]['mir']+'\n')
 save(ROOT/'raw-inventory.json',{'schema':1,'functions':[{k:v for k,v in f.items() if k!='mir'} for f in fs], 'baseline_functions':[{k:v for k,v in f.items() if k!='mir'} for f in old], 'host_caller':{k:v for k,v in host[0].items() if k!='mir'}})
 types={}
 for f in fs+old+host:
  for r in f['roles']:types.setdefault(r['compiler_type'],[]).append(r['id'])
 save(ROOT/'type-requests.json',types)
 print(json.dumps({'functions':len(fs),'roles':sum(len(f['roles']) for f in fs),'types':len(types),'baseline_functions':len(old),'by_class':{c:sum(len(f['roles']) for f in fs if f['funding_class']==c) for c in sorted({f['funding_class'] for f in fs})}}))
