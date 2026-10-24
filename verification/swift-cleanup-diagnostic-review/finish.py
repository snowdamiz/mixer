#!/usr/bin/env python3
"""Seal exact independent evidence and remove only identity-checked owned scratch."""
import gzip,json,pathlib,shutil,sys
sys.dont_write_bytecode=True
import collect as c
from owned_process import members

def main():
    r=c.HERE
    assert [x['passed']for x in json.loads((r/'runtime-results.json').read_text())]==[252,252,282,282]
    assert sum(x['passed']for x in json.loads((r/'frozen-runtime-results.json').read_text()))==64
    assert [x['passed']for x in json.loads((r/'adversarial-results.json').read_text())]==[3,3]
    # Archive lookup binds every command's exact source, including metadata and
    # the adversarial overlay, before any scratch removal.
    manifests={}
    for p in r.glob('*-source-manifest.json'):
        archive=p.with_name(p.name.replace('-source-manifest.json','-source.tar.gz'));assert archive.is_file()
        manifests[c.sha(p.read_bytes())]=dict(manifest=p.name,archive=archive.name,archiveSHA256=c.sha(archive.read_bytes()))
    commands=[]
    for p in sorted((r/'commands').glob('*/receipt.json')):
        x=json.loads(p.read_text());assert x['exitCode']==x['expectedExitCode']and not x['timedOut']and not x['groupCleanup']['after']
        if x['sourceTreeBeforeSHA256']is not None:assert x['sourceTreeBeforeSHA256']in manifests
        assert x['sourceTreeBeforeSHA256']==x['sourceTreeAfterSHA256']and x['sourceUnchanged']
        commands.append(x|{'receipt':str(p.relative_to(r))})
    c.save('command-source-retention.json',dict(sourceArchives=manifests,commandCount=len(commands),allNonNullSourceClosuresRetained=True))
    session=c.session();scratch=c.scratch();st=scratch.stat();assert(st.st_dev,st.st_ino)==(session['scratchDevice'],session['scratchInode'])
    survivors={}
    for x in commands:
        found=members(x['ownedProcessGroup'])
        if found:survivors[str(x['ownedProcessGroup'])]=found
    assert not survivors,survivors
    output,holder=c.command('scratch-holder-check',['lsof','-nP','+D',str(scratch)],expect=1)
    assert not output.stdout and not output.stderr
    files=[p for p in scratch.rglob('*')if p.is_file()];count=len(files);size=sum(p.stat().st_size for p in files)
    shutil.rmtree(scratch);assert not scratch.exists()
    c.save('cleanup.json',dict(schema=1,observedUTC=c.now(),ownedScratch=str(scratch),device=st.st_dev,inode=st.st_ino,files=count,bytes=size,holderCheckArgv=holder['argv'],holderCheckExitCode=holder['exitCode'],holderCheckEmpty=True,ownedCommandGroupsChecked=len(commands)+1,survivingOwnedGroups=survivors,signalsSentAtFinalCleanup=[],ownedScratchRemoved=True,liveSourceModified=False,producerModified=False,trackerModified=False,gitOperation=False,deviceDiscovery=False,nativeInstancesStarted=0,physicalRuns=0,otherProjectProcessesModified=False))
    commands.append(holder|{'receipt':'commands/scratch-holder-check/receipt.json'});commands.sort(key=lambda x:x['startedUTC']);c.save('commands.json',commands)
    c.save('receipt.json',dict(schema=1,observedUTC=c.now(),status='independent-review-recommends-private-host-slice-acceptance',recommendation='accept-exact-candidate-for-root-integration',findings=[],acceptedBaselineSourceSHA256='7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329',candidateSourceSHA256='1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c',producerSealSHA256='19d9040a10275bfc7968966853adc6541fb2b9855201c4448e226d4eeb0488a1',sourceRevisionContext=session['sourceRevisionContext'],sourceFiles=128,sourceBytesAreAuthority=True,newPositivePositions=5516,compilerBodies=32,layoutContexts=16,fullOwnedLayoutPairs=8,originalBlockTypeDeclarationsExact=329,allOriginalDeclarationsIncludingNestedTupleUnitExact=363,legacyMIRBodiesExact=24,frozenExpandedMethodsExact=39,frozenReservationBytes=2912,libraryTestExecutions=1068,selectedDiagnosticExecutions=68,frozenTestExecutions=64,independentAdversarialTests=3,independentAdversarialExecutions=6,independentPinnedFunction=36,independentPinnedWasmOffset=1729,libraryFeatureChecks=10,clippyProductionScopes=['swift','all'],warningsDenied=True,scopedFormattingFragments=5,commandCount=len(commands),freshCompilerRuntimeFailures=[],helperIssues='helper-repair-notes.json',scope='Private aarch64 macOS host contextual-removal development slice; root integrates exact bytes',liveIntegrated=False,g08Accepted=False,nativeAccepted=False,physicalAccepted=False,publicInvocation=False,fullSwiftAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred-no-discovery',publishedFieldLogQualification=False,logicalNamedObjectBoundsOnly=True))
    external=['AGENTS.md','mixer-product-plan.md','docs/swift-cleanup-diagnostic-contract.md','docs/swift-cleanup-diagnostic-implementation.md','docs/swift-cleanup-diagnostic-review.md','verification/swift-cleanup-diagnostic/seal.json','verification/swift-cleanup-diagnostic-root-review/selection.json','verification/swift-cleanup-diagnostic-root-review/host-baseline-direction.json','verification/swift-host-operation-root-integration/acceptance.json']
    files={str(p.relative_to(r)):c.sha(p.read_bytes())for p in sorted(r.rglob('*'))if p.is_file()and p!=r/'seal.json'}
    c.save('seal.json',dict(schema=1,observedUTC=c.now(),status='sealed-independent-review',files=files,externalBindings={p:c.sha((c.ROOT/p).read_bytes())for p in external}))
    print('SEALED',len(files),'files; commands',len(commands),'cleanup bytes',size,'seal SHA256',c.sha((r/'seal.json').read_bytes()),flush=True)

if __name__=='__main__':main()
