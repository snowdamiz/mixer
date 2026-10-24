#!/usr/bin/env python3
import collect as c
from pathlib import Path
import re,json,difflib,gzip,shutil,sys
BASE_COMMAND=c.command
BASE_TARGET=c.target
c.command=lambda name,*args,**kwargs:BASE_COMMAND("final-identity-"+name,*args,**kwargs)
c.target=lambda vm,features,profile,context:BASE_TARGET(vm,features,profile,"final-identity-"+context)

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
 print('Frozen39 methods and16 checked owners unchanged; prior4800/4324/10356 source positions preserved',flush=True)

if __name__=='__main__':identity()
