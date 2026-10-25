from pathlib import Path
import datetime,hashlib,json,tarfile
P=Path(__file__).resolve().parent
ROOT=P.parent.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v):(P/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
source=ROOT/'verification/swift-resident-index-grouped-reservation/source'
expected=json.loads((P/'selected-source-manifest.json').read_text())
actual={str(f.relative_to(source)):sha(f) for f in sorted(source.rglob('*')) if f.is_file()}
assert actual==expected and len(actual)==132
assert not (P/'scratch').exists()
with tarfile.open(P/'review-sources.tar.gz') as a:
 members=a.getmembers();assert len(members)==264
 for m in members:
  variant,name=m.name.split('/',1)
  h=json.loads((P/(variant+'-overlay-source-manifest.json')).read_text())[name]
  assert hashlib.sha256(a.extractfile(m).read()).hexdigest()==h
commands=json.loads((P/'command-summary.json').read_text())
doc=ROOT/'docs/swift-resident-index-grouped-reservation-review.md'
receipt={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'decision':'bounded_accept_no_actionable_product_findings','scope':'Independent isolated actual-cache/finite-original-owner review; no integration or full-target/native/GA acceptance','sourceRevisionContext':'be472ce6424a691de5673e3438d2768264827d23','selectedSourceManifestSHA256':'3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f','selectedSourceMembersVerifiedBeforeAndAfter':132,'reconstructedBaselineManifestSHA256':'02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d','reconstructedCleanBaselineMembersVerified':132,'exactProductChangedFiles':['src/experimental_swift_reactor/cache.rs','src/experimental_swift_reactor/cache_tests.rs'],'reviewObserversAndControlsOnlyInOwnedCopies':True,'fixedIndexPayloadAccountedExactlyOnce':True,'headerChargedAtIndexDeallocationAndThroughCallerStorageDrop':True,'constructorAllocations':4,'constructorRequestedPayloadBytes':26304,'constructorIndexPayloadBytes':192,'constructorWork':832,'shorterWorkBudgetsChecked':832,'cancellationOrdinalsChecked':851,'prePartialCancellationRefusalsWithZeroAllocations':1,'workFailuresWithAllocatedIndex':192,'cancellationFailuresWithAllocatedIndex':195,'allocatorFailureOrdinals':[0,1,2,3],'headerRefusalAllocationRequests':0,'actualOriginalOwner':{'baselineConstructedTickets':22,'selectedConstructedTickets':21,'baseline64ResidentTickets':86,'selected64ResidentTickets':85,'realSelectedTicket86Accepted':True,'nextAttempt':87,'unchangedLimit':86,'zeroCombinedTicketsAndSixLiveCategoriesAfterConsumingCleanup':True,'firstTicketInventoryFailurePreserved':True,'cleanupInvariant':None,'diagnosticRequestBytes':0,'finiteSyntheticProbeOnly':True,'priorFullTargetRequestingOwnerObserved':False},'selectedMeasuredBytes':{'owner':1016,'partialOwner':904,'cacheCleanupEnvelope':62576,'cacheHeader':63120,'cacheConstructionEnvelope':57752,'cacheOperationEnvelope':88294,'foundationEnvelope':269424,'fixed':89232,'otherThreeBufferPayload':26112,'composedExecutionHeader':11695392},'finalFocusedTests':{'selectedIndependent':3,'selectedResidentIndexSemantics':6,'selectedAccountingAndOwnership':6,'selectedComposedInventoryPreflightCompletion':3,'selectedFrozen':1,'baselineOwner':1,'baselineFrozen':1},'commands':commands,'allCommandStdoutStderrEOFAndProcessGroupsGone':True,'noTimeoutsOrSignals':True,'retainedReviewFailure':'commands/selected-independent','retainedReviewFailureInterpretation':'Early preparation cancellation has no Partial owner. Observer expected one partial-drop event incorrectly; corrected independent test requires no events and no allocations there, retaining all851 ordinals. No product change.','retainedDiagnosisFailures':['diagnosis-initial-failures/grouped-cache','diagnosis-initial-failures/grouped-cache-final'],'frozenComparisonSHA256':sha(P/'frozen-comparison.json'),'frozenTraceEqualBytes':53784,'sourceArchiveMembersVerified':264,'sourceArchiveSHA256':sha(P/'review-sources.tar.gz'),'cleanupSHA256':sha(P/'cleanup.json'),'ownedScratchAbsent':True,'newDependencies':False,'gitOrLiveEngineMutation':False,'fullTargetNativeUIPhoneHostedSigningPublicationOrCredentials':False,'excludedHostedFrozenSourcesReadOrExecuted':False,'pending':['root live integration decision','fresh original-harness full-target run if independently authorized','native parity','physical phones at final acceptance','immutable published FieldLog from separate repository','signing/stores','operational/customer qualification','GA accountable reviewer'],'reportSHA256':sha(doc)}
write('receipt.json',receipt)
files={str(f.relative_to(P)):sha(f) for f in sorted(P.rglob('*')) if f.is_file() and f.name!='seal.json'}
seal={'schema':1,'files':files,'externalFiles':{'docs/swift-resident-index-grouped-reservation-review.md':sha(doc)},'sourceRevisionContext':receipt['sourceRevisionContext'],'sourceManifestSHA256':receipt['selectedSourceManifestSHA256'],'decision':receipt['decision']}
write('seal.json',seal)
for name,h in files.items():assert sha(P/name)==h
assert sha(doc)==seal['externalFiles']['docs/swift-resident-index-grouped-reservation-review.md']
print(json.dumps({'receiptSHA256':sha(P/'receipt.json'),'sealSHA256':sha(P/'seal.json'),'sealedPacketFiles':len(files),'sealedExternalFiles':1,'decision':receipt['decision']},indent=2))
