#!/usr/bin/env python3
import collect as c
from pathlib import Path
import re,json,difflib,gzip,shutil,sys
BASE_COMMAND=c.command
BASE_TARGET=c.target
c.command=lambda name,*args,**kwargs:BASE_COMMAND("qualified-"+name,*args,**kwargs)
c.target=lambda vm,features,profile,context:BASE_TARGET(vm,features,profile,"qualified-"+context)

def item(text,keyword):
 at=text.index(keyword);brace=text.index('{',at);end=brace+1;depth=1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[at:end]
def identity():
 expanded={}
 for label in['baseline','candidate']:
  vm=c.source(label);t=c.target(vm,'all','debug','expanded');p,_=c.command('expanded-'+label,['cargo','rustc','--lib','--offline','--locked','--all-features','--','-Zunpretty=expanded'],vm,{'CARGO_TARGET_DIR':str(t),'RUSTC_BOOTSTRAP':'1'});body=item(p.stdout.decode(),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M);assert len(names)==39 and len(set(names))==39;expanded[label]={n:c.sha(item(body,'fn '+n+'(').encode())for n in names}
 assert expanded['baseline']==expanded['candidate']
 owner_files={
 'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],
 'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],
 'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState'],
 'src/experimental_wasi/accounted.rs':['pub(crate) struct AccountedWasi'],
 'src/experimental_wasi/mod.rs':['pub struct WasiContext'],
 }
 owners={}
 for file,names in owner_files.items():
  for n in names:
   b=[item((c.source(label)/file).read_text(),n)for label in['baseline','candidate']];assert b[0]==b[1],n;owners[n]=c.sha(b[0].encode())
 original=c.manifest(c.source('baseline'));candidate=c.manifest(c.source('candidate'))
 rows={}
 for stem,count in [('memory_operations',4800),('bulk_memory_operations',4324),('memory_growth_operations',10356)]:
  n='src/experimental_swift_reactor/'+stem+'.rs';assert original[n]==candidate[n];rows[stem]=dict(positions=count,sourceSHA256=original[n],sourceUnchanged=True)
 assert original['src/experimental/execution/mod.rs']==candidate['src/experimental/execution/mod.rs']
 c.save('frozen-identity.json',dict(expandedMethods=expanded['candidate'],methodCount=39,unchangedOwners=owners,originalContainingOwnerCount=14,checkedOwnerCount=16,priorPositions=rows,frozenReservationBytes=2912,frozenReservationSourceUnchanged=True))
 changes={};patch=''
 for n in sorted(set(original)|set(candidate)):
  if original.get(n)!=candidate.get(n):
   changes[n]=dict(before=original.get(n),after=candidate.get(n))
   a=(c.source('baseline')/n).read_text().splitlines(True)if n in original else[];b=(c.source('candidate')/n).read_text().splitlines(True)
   patch+=''.join(difflib.unified_diff(a,b,fromfile='a/vm/'+n,tofile='b/vm/'+n))
 (c.HERE/'candidate.patch').write_text(patch);c.save('changed-files.json',changes)
 print('Frozen39 methods and16 checked owners unchanged; accepted4800/4324/10356 source positions preserved',flush=True)
def closures():
 vm=c.source('candidate');captures=json.loads((c.HERE/'closure-captures.json').read_text());observed={}
 for unit in[False,True]:
  config='unit'if unit else'production';name='qualified-actual-closures-'+config;t=c.target(vm,'all','debug',name);env={'CARGO_TARGET_DIR':str(t),'RUSTC_BOOTSTRAP':'1'}
  if unit:
   env['RUSTFLAGS']='-Zprint-type-sizes';args=['cargo','test','--lib','--no-run','--all-features','--offline','--locked','--message-format=json-render-diagnostics']
  else:args=['cargo','rustc','--lib','--all-features','--offline','--locked','--message-format=json-render-diagnostics','--','-Zprint-type-sizes']
  p,_=c.command(name,args,vm,env);text=(p.stdout+p.stderr).decode();found={}
  for site,size,align in re.findall(r'print-type-size type: `(\{closure@src/experimental_wasi/accounted.rs:[^}]+\})`: (\d+) bytes, alignment: (\d+) bytes',text):
   if site in captures[config]:found[site]=dict(bytes=int(size),alignment=int(align))
  assert len(found)==len(captures[config])==2 and all(v==dict(bytes=8,alignment=8)for v in found.values()),found
  observed[config]=found
  if unit:
   rows=[json.loads(l)for l in p.stdout.decode().splitlines()if l.startswith('{')];a=[x for x in rows if x.get('reason')=='compiler-artifact'and x.get('executable')and x['profile']['test']and x['target']['name']=='mixer_vm'and x['target']['src_path'].endswith('/src/lib.rs')];assert len(a)==1 and a[0]['fresh']is False;c.retain_and_run(name,a[0],vm,env,list_only=True)
 c.save('actual-closure-layouts.json',observed)
def negative():
 snippets={
 'arguments':'''fn forbidden(phase:&mut FrameOperationPhase<'_>){let arguments=&phase.phase.parts.values[..];phase.phase.parts.values.truncate(0);std::hint::black_box(arguments);}''',
 'cache-view':'''fn forbidden(phase:&mut FrameOperationPhase<'_>,slot:&mut Option<Result<(),SwiftRunFailure>>){let frame=phase.phase.parts.frames.last().unwrap();let view=phase.phase.parts.cache.view(&frame.pin,phase.phase.operation.control,Some(&*phase.phase.operation.wasi)).unwrap();let _=phase.host_operation(0,slot);std::hint::black_box(view.instructions.len());}''',
 'cache-phase':'''fn forbidden(phase:&mut FrameOperationPhase<'_>){let cache_phase=phase.phase.parts.cache.prepare_operation(phase.phase.operation.control,Some(&*phase.phase.operation.wasi),phase.phase.operation.cursor).unwrap();let _=phase.phase.operation.wasi.dispatch(phase.phase.operation.control,crate::experimental_wasi::WasiFunction::FdClose,&[],phase.phase.parts.memory,phase.phase.operation.cursor);std::hint::black_box(cache_phase);}'''}
 rows={}
 for name,snippet in snippets.items():
  label='qualified-negative-'+name;vm=c.source(label);shutil.copytree(c.source('candidate'),vm);f=vm/'src/experimental_swift_reactor/frame_operations.rs';f.write_text(f.read_text()+'\nmod rejected_host_borrow {use super::*;\n'+snippet+'\n}\n');tree=c.archive(label);t=c.target(vm,'swift','debug','negative');p,_=c.command(label,['cargo','check','--lib','--offline','--locked','--features','experimental-swift-reactor'],vm,{'CARGO_TARGET_DIR':str(t)},expect=101);codes=sorted(set(re.findall(r'error\[(E\d+)\]',p.stderr.decode())));assert codes and set(codes)<={'E0499','E0502'};rows[name]=dict(errorCodes=codes,sourceTreeSHA256=tree)
 c.save('negative-borrows.json',rows)
def clippy():
 vm=c.source('candidate')
 for features,flags in [('swift',['--features','experimental-swift-reactor']),('all',['--all-features'])]:
  t=c.target(vm,features,'debug','clippy');c.command('clippy-'+features,['cargo','clippy','--lib','--offline','--locked',*flags,'--','-D','warnings'],vm,{'CARGO_TARGET_DIR':str(t)})
if __name__=='__main__':globals()[sys.argv[1]]()
