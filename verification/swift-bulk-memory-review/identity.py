from run import *
def item(text,needle):
 at=text.index(needle);i=text.index('{',at)+1;depth=1
 while depth:depth+=(text[i]=='{')-(text[i]=='}');i+=1
 return text[at:i]
def method(text,name):return item(text,'fn '+name+'(')
expanded={}
for label in['baseline','candidate']:
 p=run('fresh-expanded-'+label,['cargo','rustc','--lib','--all-features','--locked','--offline','--','-Zunpretty=expanded'],SCRATCH/label,{'RUSTC_BOOTSTRAP':'1','CARGO_TARGET_DIR':str(SCRATCH/'target-expansion')});assert p.returncode==0
 span=item(p.stdout.decode(),'impl SpanInstance {');names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',span,re.M);assert len(names)==39 and len(set(names))==39
 expanded[label]={n:hashlib.sha256(method(span,n).encode()).hexdigest()for n in names}
assert expanded['baseline']==expanded['candidate']==json.loads((PACKET/'frozen-identity.json').read_text())['methods']
owners={}
for path,names in{'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState']}.items():
 for name in names:
  old=item((SCRATCH/'baseline'/path).read_text(),name);new=item((SCRATCH/'candidate'/path).read_text(),name);assert old==new
  owners[name]=hashlib.sha256(old.encode()).hexdigest()
p='src/experimental_swift_reactor/memory_operations.rs';assert (SCRATCH/'baseline'/p).read_text().split('// ACCOUNTING_START')[1]==(SCRATCH/'candidate'/p).read_text().split('// ACCOUNTING_START')[1]
(HERE/'identity-results.json').write_bytes(enc(dict(methods=expanded['candidate'],owners=owners,methodsCount=39,ownerCount=14,retainedMemoryAccountingBytesIdentical=True)))
print('PASS fresh Frozen expansion39, original owner declarations14, retained memory suffix')
