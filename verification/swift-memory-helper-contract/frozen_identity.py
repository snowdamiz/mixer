#!/usr/bin/env python3
from pathlib import Path
import json,re,difflib,sys
STAGE=sys.argv[1]+"-" if len(sys.argv)>1 else ""
from run import run,SCRATCH,HERE,b
expanded={};maps={}
for label in ['baseline','candidate']:
 p=run(STAGE+'expanded-'+label,['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],SCRATCH/label,{'RUSTC_BOOTSTRAP':'1'});assert p.returncode==0
 full=p.stdout.decode();at=full.index('impl SpanInstance {');span=full[at:];brace=span.index('{');i=brace+1;depth=1
 while depth:depth+=(span[i]=='{')-(span[i]=='}');i+=1
 span=span[:i];names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',span,re.M);assert len(names)==len(set(names))
 maps[label]={name:b.method(span,name) for name in names}
 expanded[label]={n:__import__('hashlib').sha256(v.encode()).hexdigest() for n,v in maps[label].items()}
assert maps['baseline']==maps['candidate'],[n for n in maps['baseline'] if maps['baseline'][n]!=maps['candidate'].get(n)]
changes=[];base=b.manifest(SCRATCH/'baseline');candidate=b.manifest(SCRATCH/'candidate')
for name in sorted(set(base)|set(candidate)):
 if base.get(name)!=candidate.get(name):changes.append(dict(path=name,baselineSHA256=base.get(name),candidateSHA256=candidate.get(name)))
expected={'src/experimental/execution/mod.rs','src/experimental/execution/borrowed.rs','src/experimental_swift_reactor/execution.rs','src/experimental_swift_reactor/frame_operations.rs','src/experimental_swift_reactor/memory_operations.rs'}
assert {x['path'] for x in changes}==expected
# Every accepted containing owner definition is byte-identical. Entire untouched
# proof/cache/control/WASI and other source files also retain exact SHA identity.
def item(text,keyword):
 at=text.index(keyword);brace=text.index('{',at);i=brace+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[at:i]
owners={}
for path,names in {'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState']}.items():
 for name in names:
  parts=[item((SCRATCH/label/path).read_text(),name) for label in ['baseline','candidate']];assert parts[0]==parts[1],name
  owners[name]=dict(unchanged=True,sha256=__import__('hashlib').sha256(parts[0].encode()).hexdigest())
(HERE/'frozen-identity.json').write_bytes(b.enc(dict(status='exact-compiled-expanded-method-identity',methods=expanded['candidate'],count=len(expanded['candidate']),required=['range','load','store','run','copy','fill','grow'],reservationBytes=2912,containingOwners=owners,changedFiles=changes,unchangedAcceptedSourceFiles=len(base)-4,scope='Compiler expansion and source identity only; no memory behavior or allocation qualification')))
patch=''
for change in changes:
 name=change['path'];old=(SCRATCH/'baseline'/name).read_text().splitlines(True) if change['baselineSHA256'] else [];new=(SCRATCH/'candidate'/name).read_text().splitlines(True)
 patch+=''.join(difflib.unified_diff(old,new,fromfile='a/vm/'+name,tofile='b/vm/'+name))
(HERE/'candidate.patch').write_text(patch)
print('Frozen compiled method identity',len(expanded['candidate']),'containing owners',len(owners),flush=True)
