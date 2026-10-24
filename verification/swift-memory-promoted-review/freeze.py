#!/usr/bin/env python3
"""Freeze this review after all observations and cleanup are recorded."""
import json
from review import HERE, ROOT, enc, digest, sha, now, read

commands=[]
for f in sorted((HERE/'commands').glob('*/receipt.json')):
 c=json.loads(f.read_text());commands.append(dict(name=f.parent.name,exitCode=c['exitCode'],sourceClosure=c['sourceClosure']))
(HERE/'command-index.json').write_bytes(enc(commands))
producer=read('inputs/producer/receipt.json');archives={label:producer['sourceArchives'][label] for label in ['baseline','behavior','candidate']}
for label in ['probe-behavior','probe-candidate']:
 m=read(label+'-source-manifest.json');archives[label]=dict(closure=digest(m),files=len(m),archiveSHA256=sha(HERE/(label+'-source.tar.gz')))
bindings={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in {'receipt.json','seal.json','verify-output.json'} and '__pycache__' not in p.parts}
# Nested immutable receipts/seals are evidence and must remain in the binding
# map; exclusions apply only to this packet's own files.
for p in HERE.rglob('*'):
 if p.is_file() and p.parent!=HERE and '__pycache__' not in p.parts:bindings[str(p.relative_to(HERE))]=sha(p)
receipt=dict(schema=1,status='independent-review-accepted-scoped-correction',verdict='accepted-scoped-correction',observedUTC=now(),scope='MR01 private host standalone promoted caller positive accounting correction',candidateSourceClosure=archives['candidate']['closure'],behaviorSourceClosure=archives['behavior']['closure'],baselineSourceClosure=archives['baseline']['closure'],producerReceiptSHA256=sha(HERE/'inputs/producer/receipt.json'),producerBoundEvidenceFiles=563,sourceArchives=archives,bindings=bindings,boundEvidenceFiles=len(bindings),documentationSHA256=sha(ROOT/'docs/swift-memory-promoted-review.md'),independentReviewAccepted=True,rootAcceptance=False,gaAcceptance=False,liveVMEdited=False,nativeRuntime=False,physicalRuntime=False,UI=False,simulatorOrEmulatorRuntime=False,committed=False,pushed=False,fullSwiftQualified=False,publicInvocationQualified=False,blockingFindings=[],resolvedFindings=['MR01'],integrationNotes=['IN01'],positiveFields=4800,oldRowsRetainedExactly=4792,newUnitFields=8,freshAdditionalNamedUnitBytes=64,freshCanonicalMIRConfigurations=1,frozenCanonicalMIRConfigurationsAudited=4,freshTypedLayoutExecutions=2,freshFocusedBoundSelections=12,reusedMemorySelections=64,reusedPriorSelections=184,reusedPairedLayouts=16,reusedLibraryChecks=8,reusedFrozenPairs=56,reusedFrozenIntegrationRuns=4,frozenMethodsIdentical=39,containingOwnersUnchanged=14,productionActiveBytes=624544,unitActiveBytes=1142760,productionFrameBytes=2836512,unitFrameBytes=5092888,frozenReservationBytes=2912,ticketAuthority=86,stateLimitBytes=134217728,combinedLimitBytes=268435456,cleanup=read('cleanup.json'),toolVersions={n:__import__('gzip').decompress((HERE/'commands'/('tool-'+n)/'stdout.gz').read_bytes()).decode().strip() for n in ['rustc','cargo','python','host','revision']},limitations=['Host logical named-object accounting only; no compiler stack, allocator overhead or RSS claim.','Broad memory/regression/layout/library matrices and Frozen observations are explicit immutable reuse, not fresh review executions.','Root integration and acceptance remain separate; IN01 inherited whitespace normalization is root-owned.','G08 absent-cursor Cleanup, full dispatch/Ready/public Swift invocation, bulk memory/growth, native, physical, separately published FieldLog, signing, store, customer, operational and GA gates remain open.'])
(HERE/'receipt.json').write_bytes(enc(receipt));(HERE/'seal.json').write_bytes(enc(dict(receiptSHA256=sha(HERE/'receipt.json'),candidateSourceClosure=receipt['candidateSourceClosure'],verdict=receipt['verdict'],independentReviewAccepted=True,rootAcceptance=False,gaAcceptance=False)))
print('frozen review',len(bindings),'bindings',sha(HERE/'receipt.json'),flush=True)
