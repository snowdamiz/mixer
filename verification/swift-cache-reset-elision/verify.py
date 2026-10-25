#!/usr/bin/env python3
"""Read-only packet/source bindings. Never compiles, executes guest code or authorizes release."""
from pathlib import Path
import difflib,hashlib,json,re,subprocess
out=Path(__file__).resolve().parent;root=out.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
seal=json.loads((out/'seal.json').read_text())
for relative,expected in seal['files'].items():assert sha(out/relative)==expected,relative
for relative,expected in seal['externalFiles'].items():assert sha(root/relative)==expected,relative
inputs=json.loads((out/'input-bindings.json').read_text())
for relative,expected in inputs.items():assert sha(root/relative)==expected,relative
baseline=json.loads((out/'baseline-manifest.json').read_text());candidate=json.loads((out/'candidate-source-manifest.json').read_text())
assert sha(out/'baseline-manifest.json')=='f2682c6a2fd6f6e74bd00a2394ff32b704aa1e2ed3d2373ef95cdee29fa7eb2c'
assert len(baseline)==len(candidate)==132 and baseline.keys()==candidate.keys()
changed=[relative for relative in baseline if baseline[relative]!=candidate[relative]]
assert changed==['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs']
diffs=[]
for relative in changed:
 mirrored=out/'candidate'/'vm'/relative;assert sha(mirrored)==candidate[relative],relative
 old=subprocess.run(['/usr/bin/git','show','7744c1cc28b24a46f4339b25b38ce4d0cf76cbe8:vm/'+relative],cwd=root,capture_output=True,check=True).stdout
 assert hashlib.sha256(old).hexdigest()==baseline[relative],relative
 diffs.extend(difflib.unified_diff(old.decode().splitlines(True),mirrored.read_text().splitlines(True),fromfile='a/vm/'+relative,tofile='b/vm/'+relative))
assert ''.join(diffs)==(out/'candidate.patch').read_text()
live={relative:sha(root/'vm'/relative) for relative in baseline}
assert live in (baseline,candidate),'Live VM is neither the bound baseline nor exact candidate'
live_kind='baseline' if live==baseline else 'candidate'
for path in out.glob('*.command.json'):
 record=json.loads(path.read_text());stem=path.name.removesuffix('.command.json')
 assert sha(out/(stem+'.stdout'))==record['stdoutSHA256'],path.name
 assert sha(out/(stem+'.stderr'))==record['stderrSHA256'],path.name
 assert sha(out/record['sourceManifestRef'])==record['sourceManifestSHA256'],path.name
 assert len(json.loads((out/record['sourceManifestRef']).read_text()))==132
 assert record['timedOut']==(stem=='matrix-all-features-debug'),path.name
continuation=json.loads((out/'continuation-summary.json').read_text())
assert len(continuation)==6 and all(r['exitCode']==0 and not r['timedOut'] for r in continuation)
assert sum(r['elapsedSeconds'] for r in continuation)<900
assert all(r['elapsedSeconds']<=r['timeoutSeconds']<=450 for r in continuation)
assert [(r['testsPassed'],r['testsIgnored'],r['testsFiltered']) for r in continuation]==[(39,2,0),(6,0,0),(39,2,0),(6,0,0),(299,9,321),(224,9,396)]
required=json.loads((out/'required-controls.json').read_text());assert len(required['originalNamedCacheFunctionsPassedDebugRelease'])==18
for mode in ('debug','release'):
 completed=json.loads((out/f'completed-all-features-{mode}.json').read_text())
 assert set(required['originalNamedCacheFunctionsPassedDebugRelease'])<=set(completed)
 assert len([n for n in completed if n.startswith('experimental_swift_reactor::cache_tests::')])==23
 assert len(required['externalObserved'][mode])==13
receipt=json.loads((out/'receipt.json').read_text())
assert receipt['candidateClosureSHA256']==sha(out/'candidate-source-manifest.json')
assert receipt['requiredExecutionContextsCompleted'] and not receipt['candidateIntegrated']
assert not receipt['targetExecuted'] and not receipt['nativeOrDeviceExecuted'] and not receipt['gaGatePassed']
assert receipt['contexts']['all-features-debug']['passed']==321+299==620
assert receipt['contexts']['all-features-release']['passed']==396+224==620
format_comparison=json.loads((out/'format-comparison.json').read_text())
assert format_comparison['baselineAndFinalCandidateBothFailInheritedFormatting'] and format_comparison['candidateOwnedFilesHaveNoFormatDiff']
assert len(format_comparison['sameAffectedFiles'])==16
legacy=json.loads((out/'legacy-comparison.json').read_text());assert legacy['commonTraceIdenticalAcrossFourContexts'] and legacy['allFeatureAllocationObservationsIdenticalDebugRelease']
assert len({(out/f'legacy-{context}.trace').read_bytes() for context in legacy['contexts']})==1
cleanup=json.loads((out/'cleanup.json').read_text())
assert cleanup['ownedPathsAbsent'] and cleanup['live132SourceHashesUnchanged']
assert cleanup['processGroupMembers']==[] and cleanup['cleanupSignalsSent']==[]
assert all(row['exitCode']==1 and row['stdout']==row['stderr']=='' for row in cleanup['holderChecks'])
assert all(not (out/name).exists() for name in ('scratch','target','tmp','baseline-format'))
print(f"Verified {len(seal['files'])} sealed packet members, {len(inputs)} input references, VM132 {live_kind}, exact3-file candidate patch, completed regression contexts, disclosed inherited formatting and owned cleanup. No execution.")
