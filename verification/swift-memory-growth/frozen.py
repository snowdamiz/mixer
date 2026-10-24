#!/usr/bin/env python3
"""Actual compiler-expanded identity and fresh bounded Frozen differentials."""
import difflib,gzip,hashlib,json,re,shutil
from run import HERE,SCRATCH,run,manifest,enc,sha,digest

def item(text,keyword):
 a=text.index(keyword);i=text.index('{',a)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[a:i]
def method(text,name):return item(text,'fn '+name+'(')
maps={}
for label in['baseline','candidate']:
 p=run('isolated-expanded-'+label,['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],SCRATCH/label/'vm',{'RUSTC_BOOTSTRAP':'1'});assert p.returncode==0
 impl=item(p.stdout.decode(),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',impl,re.M);assert len(names)==39
 maps[label]={name:sha(method(impl,name).encode())for name in names}
assert maps['baseline']==maps['candidate'],[name for name in maps['baseline']if maps['baseline'][name]!=maps['candidate'].get(name)]
owners={}
for path,names in {'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState']}.items():
 for name in names:
  a,b=[item((SCRATCH/label/'vm'/path).read_text(),name)for label in['baseline','candidate']];assert a==b;owners[name]=sha(a.encode())
# The complete accepted old accounting tails are immutable, not reused credit.
for filename in['memory_operations.rs','bulk_memory_operations.rs']:
 a,b=[(SCRATCH/label/'vm/src/experimental_swift_reactor'/filename).read_text().split('// ACCOUNTING_START')[1]for label in['baseline','candidate']];assert a==b
for path in['src/experimental_swift_reactor/control.rs','src/experimental_swift_reactor/cache.rs','src/experimental_wasi/accounted.rs']:
 assert(SCRATCH/'baseline/vm'/path).read_bytes()==(SCRATCH/'candidate/vm'/path).read_bytes()
(HERE/'frozen-identity.json').write_bytes(enc(dict(methods=maps['candidate'],containingOwners=owners,reservationBytes=2912,acceptedMemoryFields=4800,acceptedBulkFields=4324,unchangedController=True)))
base=manifest(SCRATCH/'baseline/vm');candidate=manifest(SCRATCH/'candidate/vm');patch='';changes=[]
for path in sorted(set(base)|set(candidate)):
 if base.get(path)==candidate.get(path):continue
 changes.append(dict(path=path,baselineSHA256=base.get(path),candidateSHA256=candidate.get(path)))
 old=(SCRATCH/'baseline/vm'/path).read_text().splitlines(True)if path in base else[];new=(SCRATCH/'candidate/vm'/path).read_text().splitlines(True)
 patch+=''.join(difflib.unified_diff(old,new,fromfile='a/vm/'+path,tofile='b/vm/'+path))
(HERE/'candidate.patch').write_text(patch);(HERE/'changed-source-files.json').write_bytes(enc(changes))
results=[]
for label in['baseline','candidate']:
 vm=SCRATCH/('isolated-frozen-'+label)/'vm';shutil.copytree(SCRATCH/label/'vm',vm)
 p=vm/'src/experimental/execution/mod.rs';p.write_text(p.read_text()+'\n#[cfg(all(test,feature="experimental-span-execution",feature="experimental-swift-reactor"))]\n#[path="growth_differential.rs"]\nmod growth_differential;\n')
 (p.parent/'growth_differential.rs').write_text((HERE/'frozen_growth.rs').read_text())
 for profile in['debug','release']:
  flags=['--release']if profile=='release'else[];name='isolated-frozen-differential-'+label+'-'+profile
  p=run(name,['cargo','test','--lib','--all-features','--locked','--offline',*flags,'growth_differential::frozen_growth_differential','--','--nocapture','--test-threads=1'],vm);assert p.returncode==0
  lines=[line[line.index('FROZEN_GROWTH '):]for line in p.stdout.decode().splitlines()if'FROZEN_GROWTH 'in line];assert len(lines)==10
  results.append(dict(label=label,profile=profile,observations=lines))
for profile in['debug','release']:
 pair=[r['observations']for r in results if r['profile']==profile];assert pair[0]==pair[1]
(HERE/'frozen-differentials.json').write_bytes(enc(results));print('39 exact expanded methods,14 owners,40 executed Frozen cases =20 exact differential pairs',flush=True)
