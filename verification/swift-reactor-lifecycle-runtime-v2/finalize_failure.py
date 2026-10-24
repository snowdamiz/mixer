#!/usr/bin/env python3
"""Seal-facing observed failure receipt; never reruns tests or changes source."""
from pathlib import Path
import datetime,gzip,json
import runtime_support as s

HERE=s.HERE
result=s.read(HERE/'runtime-results.json');assert len(result)==1 and result[0]['exitCode']==101 and result[0]['identitiesPassed']==22
folder=HERE/'runtime-attempts/focused-swift-debug'
identities=s.read(folder/'observed-identities.json');assert len(identities)==23
assert [r['test']for r in identities if r['status']=='failed']==['experimental_swift_reactor::execution::frame_operations::memory_growth_operations::lifecycle::tests::swift_lifecycle_sl13_cumulative_instruction_host_and_cache_usage']
cleanup=s.read(folder/'cleanup.json');assert cleanup['removed']and cleanup['holderCheckEmpty']
ledger=s.read(HERE/'authored-coverage.json')
proof=s.read(HERE/'occurrence-complete-summary.json')
source=s.source_check()
bindings=[]
for path,first,last in [('src/experimental_swift_reactor/cache.rs',1945,1988),('src/experimental/cache/borrowed.rs',644,671),('src/experimental/cache/borrowed.rs',731,853),('src/experimental_swift_reactor/control.rs',978,1048),('src/experimental_swift_reactor/cache.rs',1422,1482)]:
    file=HERE/'candidate'/path
    bindings.append({'path':path,'fileSHA256':s.digest(file),'firstLine':first,'lastLine':last,'text':''.join(file.read_text().splitlines(keepends=True)[first-1:last])})
s.save(HERE/'independent-ticket-trace.json',{'schema':'mixer.swift-lifecycle.cache-entry-ticket-source-trace.1','sourceClosure':s.SOURCE,'method':'Count actual cold entry admissions retained by SwiftResident; pin release refunds no resident ticket. No new execution.','coldDecodedFunctionsByPhase':{'constructed':[],'initialize':[35],'firstCorpus':[62,36],'secondCorpus':[]},'expectedTicketDeltas':[1,2,0],'expectedLiveCacheEntries':[0,1,3,3],'expectedRelativeTicketTrace':['T0','T0+1','T0+3','T0+3'],'actualObservedFailure':{'secondCorpusTickets':24,'initializedTickets':22},'sourceBindings':bindings})
receipt={'schema':'mixer.swift-lifecycle.runtime-v2-failure-receipt.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':s.read(HERE/'finite-representation-selection.json')['sourceRevisionContext'],'candidateClosure':s.SOURCE,'candidateFiles':132,'onlyChangedBodies':['SL09','SL13'],'allOther131FilesAndHelpersImportsHooks21BodiesExact':True,'preRuntimeFreezeSHA256':s.digest(HERE/'pre-runtime-freeze.json'),'occurrenceSupplementFreezeSHA256':s.digest(HERE/'occurrence-supplement-freeze.json'),'rootRuntimeSelectionSHA256':s.digest(HERE/'finite-representation-selection.json'),'sourceAndLogicalAccountingAcceptedByRoot':True,'finiteRepresentationAcceptedByRoot':True,'fullMacroExpansionChainEquivalenceClaimed':False,'occurrenceCompleteProof':proof,'freshUnitCompilerContexts':4,'freshFrozenMethodsExact':39,'additionalAccountingCredit':0,'observedRuntime':{'contexts':['swift-debug'],'testBodiesExecuted':23,'passed':22,'failed':1,'ignored':0,'exitCode':101,'identityResults':identities},'matrixStopped':True,'unchangedFailedTestReruns':0,'otherFocusedContextsRun':False,'broaderRegressionsRun':False,'runtimeAccepted':False,'gaAccepted':False,'fullPlannedSLRowsComplete':False,'SL09Observed':'Selected explicit zero-lifetime constructor rejection with consuming tail cleanup, original pre-adoption38319823 work boundary and exact fuel/work/frame/value/control/host diagnostics passed in this one Swift Debug context. Full original edge/permutation matrix remains open.','SL13Observed':'Independent full cache-work trace and warm cache hit/resident/ticket checks passed. Inherited second==initialized ticket comparison failed24vs22 after two cold entry tickets. Later deadline assertion and explicit retire were not reached.','failureDiagnosis':'Resident entry tickets survive pin release. Init admits one entry, first corpus admits62and36, warm second adds none: expected relative ticket deltas+1,+2,+0.','nextRepairSelectedOrImplemented':False,'nextRepairProposalSHA256':s.digest(HERE/'ticket-repair-proposal.md'),'independentTicketTraceSHA256':s.digest(HERE/'independent-ticket-trace.json'),'originalCoverageLedger':ledger,'originalCoverageLedgerSHA256':s.digest(HERE/'authored-coverage.json'),'originalMatrixSHA256':s.digest(HERE/'planned-matrix-unchanged.json'),'sourceChangedAfterProofOrRuntime':False,'originalLimits':{'State':134217728,'Combined':268435456,'tickets':86,'Frozen':2912},'allOwnedScratchRemoved':True,'runtimeTargetCleanup':cleanup,'compilerTargetAndPinCleanup':s.read(HERE/'compiler-pin-and-command-cleanup-proof.json'),'metadataToolCleanup':s.read(HERE/'metadata-tool-cleanup.json'),'physicalPhones':'disconnected-deferred','full53MBTargetReadHashedOrRun':False,'nativeInstancesCreated':0,'liveVMModified':False,'gitUsed':False,'networkUsed':False,'preservedProofToolFailures':['initialCTFEcount48vs64','constantAllocationLabelComparison','sourceInfoHygieneIndexDiscovery','rawOccurrenceCount2730vs2744'],'preservedPrelaunchRunnerFailure':'concrete root selection schema mismatch before any scratch/compiler/test launch; then adapted to exact selected schema','proofCoverageCorrection':'Initial dictionary omitted108 constant occurrences; full immutable historical freeze plus independently reviewed occurrence-complete supplement retain defect and correction. No source/compiler/runtime rerun used to repair proof.','toolScope':'Original qualified compiler/sysroot bin/lib exact before each command; reused retained metadata helper. Runtime clean explicit compiler/Node PATH and executable/system-version pins. No Node oracle ran, so no new full dyld-cache verification is claimed.'}
lines=['# Private Swift lifecycle V2 runtime failure','','The first repaired Swift Debug run executed 23 exact authored lifecycle tests:',
'**22 passed, one failed, none ignored; exit101. Runtime acceptance remains false.**',
'The matrix stopped before other feature/profile contexts and all broader regressions.',
'No failed test was rerun. Source remains exactly `'+s.SOURCE+'`.','',
'SL09’s selected constructor cleanup, lifetime work boundary and exact diagnostic',
'assertions passed in this context. SL13’s independent605/1803/4196/4206 cache',
'trace and warm+4/+6, hits+2, unchanged misses/decodes/evictions/resident bytes and',
'second==first ticket checks passed. An inherited second==initialized ticket',
'comparison then failed24vs22. Its later deadline/explicit-retire code was not reached.','',
'The source independently admits one retained Cache ticket per decoded entry.',
'Initialize decodes35; first corpus decodes62and36; second corpus hits both.',
'Pin release retains residents and their tickets. The correct relative ticket',
'deltas are+1,+2,+0, with live cache entries0/1/3/3. The next SL13-only repair',
'proposal is unselected/unimplemented; no engine or accounting change is proposed.','',
'## Source and compiler proof retained','',
'Only SL09/SL13 test bodies differ from the original candidate. All other131files,',
'imports/helpers/hooks/21testbodies and production lifecycle/growth/accounting/Frozen',
'source are exact. Four fresh unit compiler contexts and39Frozen expanded methods',
'passed before runtime. Root accepted the precisely bound allocation/hygiene maps;',
'full macro expansion chains were not queried or claimed.','',
'Root found and corrected a position-proof dictionary collision. The original',
'276-file freeze is unchanged. Its12-file occurrence supplement preserves all2744',
'raw occurrences,11760unit-role joins and1296zero-byte function-item-role joins.',
'The former108omitted constant occurrences, all original failed proof checks and',
'full before/after bodies/types/layouts remain retained. No numeric credit was added.','',
'All five compiler targets, metadata scratch and the failed runtime target were',
'removed after empty-holder/process-group checks. The runtime target contained28',
'files and36,480,293logical bytes. Complete outputs, tools and executable bytes',
'are retained. No Node oracle, full real reactor or native/device run occurred.','',
'## Entire original authored and remaining coverage ledger','',
'This table preserves the original ledger verbatim. Passed identities cover only',
'their authored assertions in this single Swift Debug context; no full planned SL',
'row is complete. SL12 guest table mutation stays unsupported/unimplemented/unrun.','',
'| Row | Original authored subcases | Original remaining gaps | V2 result |','| --- | --- | --- | --- | --- |']
for row in ledger['rows']:
    observed=next(r['status']for r in identities if 'swift_lifecycle_'+row['id'].lower()+'_'in r['test'])
    lines.append('| '+row['id']+' | '+row['authored'].replace('|','\\|')+' | '+row['remaining'].replace('|','\\|')+' | '+observed+'; full row pending |')
lines+=['','The other three focused contexts, Frozen/full-library/default/span runtime',
'regressions, remaining checkpoint/budget/WASI/failure variants, physical phones',
'and immutable separate-repository FieldLog release remain pending. No live',
'integration, full53MBtarget read/hash/run, native, Git, network or shared-tracker',
'operation occurred. No D3/G07/G08/dogfood/store/customer/operational/GA gate passes.','',
'Read-only replay:','', '```sh','python3 -B verification/swift-reactor-lifecycle-runtime-v2/verify_failure.py','```','']
doc=s.ROOT/'docs/swift-reactor-lifecycle-runtime-v2.md';doc.write_text('\n'.join(lines));receipt['documentSHA256']=s.digest(doc)
s.save(HERE/'receipt.json',receipt)
print(json.dumps({'sourceClosure':s.SOURCE,'passed':22,'failed':1,'runtimeAccepted':False,'ownedScratchRemoved':True},sort_keys=True))
