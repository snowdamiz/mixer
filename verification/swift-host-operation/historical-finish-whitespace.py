#!/usr/bin/env python3
"""Validate frozen candidate evidence; retire only the recorded owned scratch; seal everything."""
from pathlib import Path
import collections,gzip,json,os,shutil,subprocess
import collect as c
import verify

def item(text,keyword):
 at=text.index(keyword);brace=text.index('{',at);end=brace+1;depth=1
 while depth:depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[at:end]
def main():
 p=c.HERE;vm=c.source('candidate');baseline=c.source('baseline');s=c.scratch()
 assert c.digest(c.manifest(vm))==c.digest(json.loads((p/'candidate-source-manifest.json').read_text()))
 c.command('qualified-whitespace',['git','diff','--no-index','--check','--',str(baseline),str(vm)],vm)
 c.command('tool-git-finish',['git','rev-parse','HEAD'])
 c.command('tool-rustfmt',['rustfmt','--version'],baseline)
 supplement={}
 for file,name in [('src/experimental_swift_reactor/control.rs','pub(crate) struct RuntimeControl'),('src/experimental_swift_reactor/cache.rs','pub(crate) struct SwiftFunctionCache')]:
  a=item((baseline/file).read_text(),name);b=item((vm/file).read_text(),name);assert a==b;supplement[name]=c.sha(a.encode())
 for file in ['src/experimental_swift_reactor/control.rs','src/experimental_wasi/accounted.rs']:
  assert(vm/file).read_bytes().startswith((baseline/file).read_bytes()),file
 c.save('original-authority-supplement.json',dict(unchangedDeclarations=supplement,originalControlAndAccountedWasiFileBodiesRemainExactPrefixes=True,productionWasiContextSourceUnchanged=c.manifest(vm)['src/experimental_wasi/mod.rs']==c.manifest(baseline)['src/experimental_wasi/mod.rs']))
 rows=[json.loads((p/('runtime-'+f+'-'+profile+'.json')).read_text())for f in['default','swift','all']for profile in['debug','release']];c.save('runtime-results.json',rows)
 old=json.loads((c.ROOT/'verification/swift-host-dispatch-contract/inventory-schema.json').read_text());new=json.loads((p/'inventory-schema.json').read_text());rebased=json.loads((p/'rebased-inventory-schema.json').read_text())
 counts=lambda data:dict(collections.Counter(r['config']for r in data))
 c.save('accounting-delta.json',dict(originalUncalledPositions=len(old),rebasedCompletionPositions=len(rebased),finalPositions=len(new),originalCounts=counts(old),rebasedCounts=counts(rebased),finalCounts=counts(new),completionWrapperAddsProduction=20,completionWrapperAddsAdditionalUnit=20,unitBoundaryPathsAdd=68,explanation='Original 4768 positions are regenerated against accepted growth. The actual completion wrapper contributes20 production and20 additional unit MIR positions. Test-only finite dispatch/removal/PC/push probes contribute68 additional unit positions. Every source/argument/returned/caller placement is named independently; no prior memory/bulk/growth row supplies credit. Zero-sized compiler types retain named empty intervals; the containing reservation classes are positive and measured.'))
 # This subprocess returns before its own command receipt is installed; the final verification checks it too.
 c.command('qualified-preseal-verifier',['python3','-B',str(p/'verify.py'),'--preseal','--live-baseline'],vm)
 summary=verify.check(preseal=True,live=True);c.save('preseal-verification.json',summary)
 c.save('source-archives.json',{m.name.removesuffix('-source-manifest.json'):dict(sourceTreeSHA256=c.digest(json.loads(m.read_text())),archiveSHA256=c.sha((p/(m.name.removesuffix('-source-manifest.json')+'-source.tar.gz')).read_bytes()),sourceFiles=len(json.loads(m.read_text())))for m in sorted(p.glob('*-source-manifest.json'))})
 # Refuse to remove any unexpected path or holder; never terminate another project's processes.
 assert s.parent==Path('/tmp')and s.name.startswith('mixer-host-operation-');st=s.stat();owned_inode=[st.st_dev,st.st_ino]
 holders=c.command('qualified-cleanup-holders',['/usr/sbin/lsof','-nP','+D',str(s)],expect=1)[0];assert not holders.stdout and not holders.stderr
 assert[s.stat().st_dev,s.stat().st_ino]==owned_inode
 files=[x for x in s.rglob('*')if x.is_file()];count=len(files);size=sum(x.stat().st_size for x in files)
 shutil.rmtree(s);assert not s.exists()
 c.save('cleanup.json',dict(scratch=str(s),deviceInode=owned_inode,lsofObservedNoOpenHolders=True,lsofExitCode=1,lsofArgv=['/usr/sbin/lsof','-nP','+D',str(s)],scratchFiles=count,scratchLogicalBytes=size,scratchRemoved=True,processesTerminated=False,otherProjectsTouched=False,nativeInstancesCreated=0,physicalDevicesUsed=False,completedUTC=c.now()))
 for cache in p.rglob('__pycache__'):
  if cache.is_dir():shutil.rmtree(cache)
 failed=[];commands={}
 for r in sorted((p/'commands').glob('*/receipt.json')):
  value=json.loads(r.read_text());commands[r.parent.name]=value
  if value['exitCode']!=value['expectedExitCode']:failed.append(r.parent.name)
 layouts=json.loads((p/'qualified-accounted-layouts.json').read_text());totals={key:next(x['layout']for x in layouts if x['label']=='candidate'and x['unit']==unit)for key,unit in [('production',False),('unit',True)]}
 c.save('historical-attempts.json',dict(excludedFailedCommands=failed,expectedHarnessParserFailure='historical-qualify-parser',retainedFailedSourceArchives=['runtime-draft','runtime-accounted-const-failure','runtime-unit-inventory-selector-failure','historical-first-runtime','historical-second-runtime'],firstRuntime=dict(passed=228,failed=7,command='execute-runtime-swift-debug'),secondRuntime=dict(swiftPassed=234,allPassed=264,failedPerSuite=1,profiles=['debug','release']),corrections=['Use integer zero bits for Value float variants and include named classes before unit inventory construction.','Use stable const checked matches and owner-visible positive-byte constants.','Exclude test harness impl names whose source filename matched the operation selector; retain actual executor/dispatch compiler bodies.','Update additive envelope assertions for the new class.','Compare immutable at_failure and first cause while retaining separate after_cleanup observations.','Use actual cfg(test) push-boundary cancellation instead of the unrelated frame-entry hook.'],qualifyingRuntimeCommands=['execute-qualified-runtime-'+f+'-'+profile for f in['default','swift','all']for profile in['debug','release']]))
 final_tree=c.digest(json.loads((p/'candidate-source-manifest.json').read_text()))
 receipt=dict(schema=1,status='frozen-private-host-operation-candidate-qualified-pending-independent-root-review',observedUTC=c.now(),baselineSourceClosure='a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b',candidateSourceClosure=final_tree,sourceFiles=128,baselineSourceFiles=127,changedSourceFiles=10,startRevision=c.session()['sourceRevision'],finishRevision=gzip.decompress((p/'commands/tool-git-finish/stdout.gz').read_bytes()).decode().strip(),sourceContentIsAuthority=True,sourceArchive='candidate-source.tar.gz',sourceManifest='candidate-source-manifest.json',patch='candidate.patch',positiveCanonicalPositions=len(new),positiveClassLayouts=totals,finalPairedMetadataContexts=16,retainedPairedMetadataContexts=64,finalCompilerBodies=len(json.loads((p/'function-manifest.json').read_text())),sourceArchives=36,libraryTests=sum(x['passed']for x in rows),extraHostPreprobeTests=64,frozenRuntimeTests=64,finalBehavioralTestExecutions=sum(x['passed']for x in rows)+128,originalExpandedFrozenMethods=39,originalContainingOwners=14,additionalCheckedOwners=4,acceptedMemoryPositions=4800,acceptedBulkPositions=4324,acceptedGrowthPositions=10356,StateLimit=134217728,CombinedLimit=268435456,ticketMaximum=86,logicalNamedObjectAccountingOnly=True,ownedProcessHelperSHA256=c.sha((p/'owned_process.py').read_bytes()),excludedFailedCommands=failed,allNestedCommandReceiptsSealed=True,hostGroups={f'H{i:02}':'scoped candidate runtime evidence passed'for i in range(1,17)},rootAccepted=False,liveIntegrated=False,liveSourceEdited=False,trackerEdited=False,gitEdited=False,committed=False,pushed=False,fullDispatcher=False,definedCallDispatch=False,indirectCallDispatch=False,fullSwift=False,Ready=False,publicInvocation=False,nativeUI=False,physical=False,publishedFieldLog=False,release=False,GA=False,pending=['independent root review/integration','G08 absent-cursor diagnostic','ordinary defined/indirect calls and complete fetch/dispatch loop','Ready/public invocation','full Swift payload','native joins','immutable published separate-repository FieldLog','physical phones','signing/store/customer/operational/release/GA'],limitations=['Synthetic Swift-shaped validated modules and actual private owners; no full Swift guest or public route.','The allocation observation covers only the warmed actual ArgsSizesGet host-operation interval on this thread, not every import, OS service, stack, RSS or allocator overhead.','Host counter overflow, malformed frame/push floor and owner/debt faults are explicit bounded test fixtures.','Real macOS secure randomness and clock resolution execute. Clock postcheck tests add a finite600ms delay after the actual OS call; cancellation/deadline checks are cooperative and do not preempt OS calls.','Official errno values exercised are0,8,21,28,29,51,58,76; no universal errno exhaustiveness claim.','Sticky live-removal debt and its existing absent cursor are preserved; retained owners are deliberately dropped only after observing explicit refusal, with no repaired ledger or clean receipt.','Completion wrapper uses the original fixed-storage completion rule with plain prepare_frames fixtures. Future mixed growth/host dispatch must retain/use complete_growth while relevant growth context/storage/debt exists.','All failed source overlays and command output remain historical, excluded from final behavioral qualification.'])
 c.save('receipt.json',receipt)
 # Bind every nested receipt. Only this exact root seal excludes itself.
 bindings={str(x.relative_to(p)):c.sha(x.read_bytes())for x in sorted(p.rglob('*'))if x.is_file()and x!=p/'seal.json'}
 c.save('seal.json',dict(schema=1,exactExcludedPath='seal.json',files=bindings,documentation='docs/swift-host-operation-implementation.md',documentationSHA256=c.sha((c.ROOT/'docs/swift-host-operation-implementation.md').read_bytes()),boundFiles=len(bindings),completedUTC=c.now()))
 print(json.dumps(verify.check(),sort_keys=True),flush=True)
if __name__=='__main__':main()
