#!/usr/bin/env python3
"""Finalize observed finite preparation evidence; no guest or native execution."""
from pathlib import Path
import datetime,hashlib,json
H=Path(__file__).resolve().parent;R=H.parent.parent
load=lambda n:json.loads((H/n).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
commands=['build-001','list-001','control-001','control-002','adapter-controls','driver-observation-controls']
assert all(load('commands/'+n+'/receipt.json')['passed'] for n in commands)
assert not (H/'owned-scratch').exists() and not (H/'bin/exact-tests').exists()
assert not (H/'root-selection.json').exists() and not (H/'target-attempt-started.json').exists()
cleanup=load('cleanup.json')
receipt={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'prepared-awaiting-independent-and-root-exact-selection',
    'sourceRevisionContext':'6b8aba350224ed19f678669bdbea6b359d8de68b','baselineClosure':sha(H/'baseline-manifest.json'),
    'sourceRevisionMeaning':'root supplied context; exact source content closure authoritative; no Git query',
    'sourceFiles':132,'copiedSourceManifestSHA256':sha(H/'copied-build-manifest.json'),'acceptedObserverSealSHA256':'e4a520641fbad904381bc7438feb0baee4dfca7d716806262da80ac4b20f0305',
    'independentReviewSealSHA256':'9f7d6c2357f0464d09932c4632cba543ecf8a20073ea6a3d9f07030de4175ce4','previousFullResultSealSHA256':'8f04098c444d63e9d638c32e22297eccdad346222241529ef710c524473e7526',
    'deltaFromAcceptedObserverFiles':2,'remainingObserverFilesUnchanged':130,'builds':1,'buildPassed':True,'buildNoRun':True,
    'finiteRustTestExecutionsPassed':5,'finiteRustTestsFailed':0,'finiteRustTestsIgnored':0,'originalTinyHarnessWiringExecutions':2,
    'directActualCacheAdapterTests':3,'hostControlsPassed':14,'inheritedProcessControlsPassed':10,'newTelemetryParserControlsPassed':4,
    'tinySyntheticValidations':2,'tinySyntheticInitializeCalls':2,'tinySyntheticCorpusCalls':4,'tinySyntheticGuestInstructions':10,
    'directAdapterGuestInstructions':0,'finiteTelemetryStatuses':['valid','valid'],'finiteTelemetrySnapshotCounts':[6,6],'finiteTelemetryLifetimeBytes':[3716,3716],
    'maximumTelemetryEnvelopeBytes':4608,'maximumTelemetryLifetimeBytes':27648,'allOriginalLimitsPreserved':True,
    'fullTargetAttempts':0,'realTargetValidations':0,'realTargetInitializeCalls':0,'realTargetCorpusCalls':0,'completeVmRegressions':0,
    'originalResultAlwaysAuthoritative':True,'telemetryValiditySeparate':True,'failedFormatterPartialPayloadDiscarded':True,'trueFormatterStickyInvalidityChecked':True,
    'rootExactSelectionPending':True,'preparedSelectionSHA256':sha(H/'prepared-selection.json'),'proposedCommandSHA256':sha(H/'proposed-command.json'),
    'executable':load('binary.json')['retained'],'retainedExecutableGzip':cleanup['retainedExecutable']['gzip'],
    'ownedCommandGroupsAbsent':True,'ownedScratchAbsent':True,'holderChecksEmpty':True,'originalCleanupDeviceInodeCheckPassed':True,
    'logicalBytesRemoved':cleanup['logicalBytesRemoved'],'signalsSent':[],'sourceArchiveDuplicated':False,
    'productionSourceChanged':False,'productionAlgorithmImplemented':False,'nativeExecuted':False,'uiOrPhoneQueried':False,'gitUsed':False,'liveVmQueried':False,
    'networkUsed':False,'providerUsed':False,'frozenHostedLanesUsed':False,'rootIndexesWritten':False,'gaAccepted':False,
    'limitations':['No real workload attribution or successful full reactor evidence.','Observer CPU time consumes unchanged real deadlines; external telemetry storage is not product reservations, RSS or whole-process peak evidence.','Finite tiny synthetic instruction execution is not production, native, physical-device or FieldLog published-package qualification.','Source/executable restoration and independent root exact selection are still pending before any full attempt.','Corpus2, native/public/signed behavior, immutable FieldLog packages, physical phones and all accountable GA gates remain pending.'],
    'commands':[str(Path('commands')/n/'receipt.json') for n in commands],'cleanup':'cleanup.json','contract':'output-contract.json'}
save('receipt.json',receipt)
files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='prepared-seal.json'}
assert not any(n.startswith('owned-scratch/') for n in files)
save('prepared-seal.json',{'schema':1,'status':'prepared-awaiting-independent-and-root-exact-selection; no full target selected','files':files,'externalFiles':{'docs/swift-current-attribution-full-preparation.md':sha(R/'docs/swift-current-attribution-full-preparation.md')},'targetAttempts':0})
print(json.dumps({'sealedMembers':len(files),'preparedSealSHA256':sha(H/'prepared-seal.json'),'targetAttempts':0}))
