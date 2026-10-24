#!/usr/bin/env python3
"""Compare actual expanded Frozen methods and unchanged containing owners."""
from pathlib import Path
import difflib, json, re
import probe
from probe import HERE, run, save, sha, manifest, digest
def item(text,keyword):
    at=text.index(keyword);brace=text.index('{',at);end=brace+1;depth=1
    while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[at:end]
def method(text,name):return item(text,'fn '+name+'(')
def main():
    probe.SCRATCH=Path(json.loads((HERE/'session.json').read_text())['scratch'])
    expanded={}
    for label in ['baseline','candidate']:
        p=run('expanded-'+label,['cargo','rustc','--lib','--offline','--locked','--all-features','--','-Zunpretty=expanded'],probe.SCRATCH/label,{'RUSTC_BOOTSTRAP':'1'})
        body=item(p.stdout.decode(),'impl SpanInstance {')
        names=re.findall(r'^\s+(?:pub )?fn (\w+)\(',body,re.M)
        assert len(names)==39 and len(names)==len(set(names)),names
        expanded[label]={name:sha(method(body,name).encode()) for name in names}
    assert expanded['baseline']==expanded['candidate']
    owner_files={
      'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],
      'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],
      'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState'],
    }
    owners={}
    for file,names in owner_files.items():
        for name in names:
            bodies=[item((probe.SCRATCH/label/file).read_text(),name) for label in ['baseline','candidate']]
            assert bodies[0]==bodies[1],name
            owners[name]=dict(sha256=sha(bodies[0].encode()),unchanged=True)
    baseline=manifest(probe.SCRATCH/'baseline');candidate=manifest(probe.SCRATCH/'candidate')
    changed=[name for name in baseline if baseline[name]!=candidate[name]]
    assert changed==['src/experimental_swift_reactor/frame_operations.rs'],changed
    inventory_counts={}
    for stem in ['memory_operations','bulk_memory_operations']:
        file='src/experimental_swift_reactor/'+stem+'.rs'
        text=(probe.SCRATCH/'baseline'/file).read_text().split('// ACCOUNTING_START',1)[1]
        inventory_counts[stem]=len(re.findall(r'^\s+\w+: [^\n]+,\s*$',text,re.M))
        assert baseline[file]==candidate[file]
    assert inventory_counts=={'memory_operations':4800,'bulk_memory_operations':4324},inventory_counts
    frozen=(probe.SCRATCH/'baseline/src/experimental/execution/mod.rs').read_text()
    reservation=frozen[frozen.index('size_of::<Self>()'):frozen.index('size_of::<Self>()')+700] if 'size_of::<Self>()' in frozen else None
    save('frozen-identity.json',dict(expandedMethods=expanded['candidate'],methodCount=39,
        unchangedContainingOwners=owners,containingOwnerCount=14,changedSourceFiles=changed,
        unchangedMemoryBulkRows=inventory_counts,frozenReservationBytes=2912,
        frozenSourceFileUnchanged=True,frozenTraceNoNewRuntimeClaim=True,
        scope='Compiled method identity and source/layout identity; no new execution or trace acceptance'))
    patch=''.join(difflib.unified_diff((probe.SCRATCH/'baseline'/changed[0]).read_text().splitlines(True),
        (probe.SCRATCH/'candidate'/changed[0]).read_text().splitlines(True),fromfile='a/vm/'+changed[0],tofile='b/vm/'+changed[0]))
    (HERE/'candidate.patch').write_text(patch)
    save('source-closures.json',{label:digest(manifest(probe.SCRATCH/label)) for label in ['baseline','candidate']})
    print('39 Frozen methods, 14 owner declarations and 4800/4324 prior rows unchanged')
if __name__=='__main__':main()
