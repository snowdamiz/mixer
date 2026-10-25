#!/usr/bin/env python3
"""Seal the bounded independent review; performs no new execution."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent
R=H.parent.parent
C=H.parent/'swift-cache-current-attribution-observer'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
dump=lambda p,x:p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
load=lambda p:json.loads(p.read_text())
command=load(H/'command.json');cleanup=load(H/'cleanup.json')
assert command['exitCode']==0 and cleanup['ownedPathsAbsent']
findings={'schema':1,'verdict':'accepted-for-diagnostic-preparation-only','blockingFindings':[],
    'reviewedCandidateSealSHA256':sha(C/'seal.json'),
    'conclusions':['Original checkpoint, debit result, error precedence and publication ordering preserved.',
        'Successful credits exclude rejected requested debits; first rejection is sticky.',
        'All sixteen semantic sites include separate scan/build policy attribution.',
        'Bitmap publication matches original completed IR publication; first/repeated partitions persist through eviction.',
        'Matching-plan-before-completed cannot be reached after an earlier failed build under the original sticky cache/control ownership.',
        'Frozen inherits cfg(test) no-op callbacks; remaining129 source files and original test prefix are exact.',
        'Range/counter/context/output invalidity has no guest Result authority.',
        'Fixed formatter uses integers and closed source-bound enums; no guest string or arbitrary label.'],
    'futureDriverRequirements':['Preserve original guest Result and report telemetry validity separately; never assert or overwrite a guest failure because telemetry is invalid.',
        'Discard the entire partial payload on formatter false; success still requires a zero sticky invalid mask for attribution.',
        'One reset before one fresh original cache/control lifetime; preserve state through final cleanup; no interleaved cache, detached plans or RefCell borrow across cache operation.',
        'Bind lifecycle labels and full output envelope in the separately reviewed driver; value bounds exclude TLS/compiler/process overhead and make no CPU/RSS claim.'],
    'independentControls':['two exact policy rejection sites with incomplete plan and sticky same-identity retry',
        'same and adjacent bitmap words through eviction, first conflict and repeated conflict',
        'clean/context/counter/output modes preserving original WorkExhausted and discarding64 partial bytes'],
    'producerEvidenceMeaning':'integrity-checked existing4 passes/13observations/409work-prefixes/173cancellation-prefixes, not independent reruns',
    'noFullSelection':True,'gaAccepted':False}
dump(H/'findings.json',findings)
receipt={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict':findings['verdict'],'scope':'Independent bounded test-only current Swift cache observer review; diagnostic preparation only.',
    'candidateSealSHA256':sha(C/'seal.json'),'candidateSourceArchiveSHA256':sha(C/'isolated-source.tar.gz'),
    'baselineClosure':'16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd',
    'historicalSourceRevisionContext':'6403eea98031207f6e40a72b55dfd3bd4e7e6ec2',
    'rootProvidedContext':'6b8aba350224ed19f678669bdbea6b359d8de68b',
    'sourceFiles':132,'baselineUnchangedFiles':129,'candidateChangedFiles':3,
    'reviewChangedFiles':1,'reviewSourceManifestSHA256':sha(H/'review-source-manifest.json'),
    'sourceArchiveRetention':'No redundant archive. Reconstruct exact candidate archive plus newline plus independent-controls.rs in existing test file.',
    'finiteTestsPassed':3,'finiteTestsFailed':0,'finiteTestsIgnored':0,'filteredOut':390,'independentFiniteCases':7,
    'finiteElapsedSeconds':command['elapsedSeconds'],'inheritedCompilerWarnings':2,
    'producerTestsRerun':False,'reviewCorrectionsOrRetries':0,
    'guestInstructions':0,'guestInitializeCalls':0,'guestInvokeCalls':0,'fullTargetAttempts':0,'completeVmRegressionRuns':0,
    'productionSourceChanged':False,'productionAlgorithmImplemented':False,'budgetsIncreased':False,
    'gitUsed':False,'liveVmQueried':False,'networkUsed':False,'providerUsed':False,'signingUsed':False,
    'nativeDeviceOrUiUsed':False,'phonesUsed':False,'frozenHostedLanesReadImportedOrExecuted':False,
    'otherProjectsTouched':False,'cleanupComplete':True,'logicalBytesRemoved':cleanup['logicalBytesRemoved'],
    'gaAccepted':False,'blockingFindings':0,
    'limitations':['No real-module validation, full target, guest instantiation, Initialize, invocation/corpus or new full harness.',
        'No complete VM or Frozen regression rerun; independent executable scope is the three selected finite cache controls.',
        'Value/payload bounds exclude RefCell/TLS, compiler temporaries, fixtures, allocator/process and stdout overhead; no CPU/RSS/zero-overhead assertion.',
        'Full diagnostic source/harness/executable/argv selection remains separate root work.',
        'Corpus2, native/public/signed product, immutable published-package FieldLog, final physical phones and specified accountable GA gates remain pending.']}
dump(H/'receipt.json',receipt)
dump(H/'commands.json',{'cwd':str(R),'preparationArgv':['python3','-B','verification/swift-cache-attribution-independent-review/prepare.py'],
    'preparationOutput':'source-audit.json (same JSON content printed by prepare.py)',
    'finiteArgv':['python3','-B','verification/swift-cache-attribution-independent-review/finite.py'],
    'finiteCommand':'command.json','finiteRawStreams':['finite.stdout','finite.stderr'],
    'cleanupArgv':['python3','-B','verification/swift-cache-attribution-independent-review/cleanup.py'],
    'cleanupOutput':'cleanup.json (same JSON content printed by cleanup.py)',
    'readOnlyVerificationArgv':['python3','-B','verification/swift-cache-attribution-independent-review/verify.py'],
    'toolVersionsAndHashes':'tools.json','cleanupBinaryHashes':'cleanup-tools.json'})
seal={'schema':1,'status':'sealed-independent-review-accepted-diagnostic-preparation-only',
    'files':{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='seal.json'},
    'externalFiles':{str(p.relative_to(R)):sha(p) for p in [R/'docs/swift-cache-attribution-independent-review.md',C/'seal.json',C/'isolated-source.tar.gz',C/'copied-source-manifest.json',C/'baseline-manifest.json']}}
dump(H/'seal.json',seal)
print(json.dumps({'sealSHA256':sha(H/'seal.json'),'members':len(seal['files']),'verdict':receipt['verdict']},sort_keys=True))
