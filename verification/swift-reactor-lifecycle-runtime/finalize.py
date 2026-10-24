#!/usr/bin/env python3
"""Write the failed-run receipt and full remaining-coverage document."""
from pathlib import Path
import datetime, gzip, hashlib, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
def enc(value): return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(path): return json.loads(path.read_bytes())
def save(name,value): (HERE/name).write_bytes(enc(value))

results = read(HERE/'results.json')
assert len(results)==1 and results[0]['context']=='swift-debug' and results[0]['executionExitCode']==101
names = read(HERE/'attempts/swift-debug/exact-tests.json')
stdout = gzip.decompress((HERE/'attempts/swift-debug/execute-stdout.gz').read_bytes()).decode()
statuses = []
for name in names:
    status = 'passed' if 'test '+name+' ... ok' in stdout else 'failed' if 'test '+name+' ... FAILED' in stdout else 'unobserved'
    assert status!='unobserved'
    statuses.append({'test':name,'status':status,'fullPlannedSLRowComplete':False})
assert [sum(r['status']==s for r in statuses)for s in ['passed','failed']]==[21,2]
ledger = read(HERE/'authored-coverage.json')
traces = read(HERE/'independent-source-traces.json')
clean = read(HERE/'attempts/swift-debug/cleanup.json')
assert clean['removed'] and clean['holderCheckEmpty']
receipt = {
    'schema':'mixer.swift-lifecycle.runtime-failure-receipt.1',
    'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext':'06147f0ef6c704a08b6fac7561ad98bcc5165d46',
    'candidateClosure':'0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f',
    'candidateFiles':132,'sourceBytes':sum(p.stat().st_size for p in (HERE/'candidate').rglob('*') if p.is_file()),
    'runtimeSelectionSHA256':sha((HERE/'runtime-selection.json').read_bytes()),
    'accountingSealSHA256':sha((HERE/'accounting-seal.json').read_bytes()),
    'sourceAndLogicalAccountingAcceptedByRoot':True,'runtimeSelected':True,'runtimeAccepted':False,'fullPlannedSLRowsComplete':False,'gaAccepted':False,
    'observedHostScope':'macOS aarch64-apple-darwin; independently authored small strict-ABI synthetic modules against original owners',
    'observedRuntime':{'contextsRun':['swift-debug'],'testBodiesExecuted':23,'passedTests':21,'failedTests':2,'ignoredTests':0,'filteredOutExistingTests':312,'exitCode':101,'identityResults':statuses,'actualGuestVMInvocationsCounted':False},
    'matrixStoppedAfterFirstFailure':True,'unchangedFailureReruns':0,'unrunFocusedContexts':['swift-release','all-debug','all-release'],
    'unrunBroaderRegressions':['Frozen39','Swift/all Debug/Release full library','default Debug/Release','span Debug/Release and seven integration targets'],
    'failureDiagnosis':{'SL09':'Zero original lifetime execution-work budget rejects the original state constructor before Initialize. The test helper incorrectly unwraps that expected construction failure. Exact phase budget proposal uses independently derived constructor cost, not a budget reset.','SL13':'Warm hits legitimately charge lookup and both searches. Independent source-derived cold and warm traces predict 605→1803→4196→4206; original equality assertion incorrectly excludes the warm10 credits.'},
    'sourceTraceSHA256':sha((HERE/'independent-source-traces.json').read_bytes()),
    'repairProposalSHA256':sha((HERE/'repair-proposal.md').read_bytes()),
    'repairSelectedOrImplemented':False,'sourceChanged':False,
    'remainingCoverageLedger':ledger,'remainingCoverageLedgerSHA256':sha((HERE/'authored-coverage.json').read_bytes()),
    'originalMatrixSHA256':sha((HERE/'planned-matrix-unchanged.json').read_bytes()),
    'SL09Scope':'Original assertions check only a broad failure family. No exact per-dimension qualification; the failing work case also prevented later dimensions in that loop and host case from running.',
    'SL12Scope':'Authored memory/global persistence, original table identity/content preservation and repeated indirect reads passed in Swift Debug. Guest table mutation remains unsupported, unimplemented and unrun.',
    'inheritedPrecondition':'control.as_mut().expect("constructed control") remains an unchanged constructor invariant; no fabricated diagnostic/authority.',
    'tools':'Every actual launch rechecked exact qualified compiler bin/lib closure and Rust/Cargo/rustfmt executable hashes. Stored versions are qualified version metadata bound to these same exact bytes. Python/Node executable and macOS version-file hashes are retained. No Node oracle or broader regression ran; a fresh full dyld-cache check was therefore not performed here.',
    'commands':[read(HERE/'attempts/swift-debug'/f'{name}.json')for name in ['build','list','execute']],
    'exactBinary':read(HERE/'attempts/swift-debug/cargo-artifact.json'),
    'cleanup':clean,'allOwnedScratchRemoved':True,
    'originalLimits':{'State':134217728,'Combined':268435456,'tickets':86,'Frozen':2912},
    'full53MBTargetReadHashedOrRun':False,'nativeInstancesCreated':0,'liveVMModified':False,'gitUsed':False,'networkUsed':False,
    'physicalPhones':'disconnected-deferred',
    'pending':'Root must review this sealed failed-run diagnosis and select any new isolated test repair plus fresh accounting impact before changed-candidate runtime. Full product scope, all original matrix gaps, physical acceptance and FieldLog immutable separate-repository release remain pending.',
}
save('observed-identities.json',statuses)

lines = ['# Private Swift lifecycle first runtime failure', '',
'The first selected Swift Debug run executed the 23 exact authored lifecycle tests:',
'**21 passed, two failed, none ignored; exit 101. Runtime acceptance is false.**',
'The matrix stopped before Swift Release/all-feature runs and all broader regressions.',
'The source and assertions remain unchanged. No failed test was rerun.', '',
'Candidate closure: `'+receipt['candidateClosure']+'` (132 files).',
'The accepted accounting packet is unchanged; this packet records actual runtime failure.', '',
'SL09 fails before Initialize because its original zero lifetime execution-work budget',
'correctly rejects state construction. The actual first charge is 38,319,741; the',
'test helper unwraps the constructor error. Independent constructor arithmetic gives',
'38,319,823 total successful construction work. The proposed initializer-specific',
'edge sets that original lifetime budget and expects entry work attempt 38,319,824.',
'The exact constructor rejection and retained cleanup tail must also be tested.', '',
'SL13 observes cache work 4,196→4,206, violating its incorrect unchanged-work',
'assertion. Independent lookup, pin-record and resident-slot costs are 4 for the',
'outer warm call plus 6 for its nested warm callee. The full source-derived trace',
'is 605 after cache construction, 1,803 after init, 4,196 after call one, 4,206',
'after call two. These predictions derive from charge sites and literal bodies;',
'they are not substituted observed expectations. See the exact source-bound',
'`independent-source-traces.json` and `repair-proposal.md` in the runtime packet.', '',
'The proposed repair is unselected and unimplemented. It changes only future',
'isolated tests and requires fresh accounting for every changed unit body/carrier.',
'No engine, owner, public API, ceiling or ticket change is proposed.', '',
'All build/list/test outputs and exact executable bytes are retained. The owned',
'target was removed after empty holder and process-group checks: 28 files and',
'36,505,412 logical bytes. No native instance, live integration, Git or network',
'operation occurred. No full reactor target was read, hashed or run.', '',
'## Complete original authored/remaining coverage ledger', '',
'The following original ledger is preserved verbatim in `authored-coverage.json`',
'and the receipt. A passed test identity covers only its authored assertions in',
'this single Swift Debug configuration. **No full planned SL row is complete.**',
'SL09 remains family-level; SL12 guest table mutation remains unsupported/unrun.', '',
'| Row | Original authored subcases | Remaining planned cases/limitations | This run |',
'| --- | --- | --- | --- |']
for row in ledger['rows']:
    match = [r for r in statuses if ('swift_lifecycle_'+row['id'].lower()+'_')in r['test']]
    assert len(match)==1
    lines.append('| '+row['id']+' | '+row['authored'].replace('|','\\|')+' | '+row['remaining'].replace('|','\\|')+' | '+match[0]['status']+'; full row pending |')
lines += ['',
'Frozen/full library/default/span regressions, the other three focused contexts,',
'remaining failure/budget/checkpoint/WASI variants and full original product',
'scope remain pending. Physical phones stay disconnected and deferred to final',
'acceptance. FieldLog still requires immutable packages from a separate repository.',
'No D3, G07/G08, dogfood, store, customer/operations or GA gate is accepted.', '',
'Read-only replay:', '',
'```sh', 'python3 -B verification/swift-reactor-lifecycle-runtime/verify.py --live', '```', '',
'The replay reads retained evidence only. It does not rerun tests or compile code.', '']
document = ROOT/'docs/swift-reactor-lifecycle-runtime.md'
document.write_text('\n'.join(lines))
receipt['documentSHA256'] = sha(document.read_bytes())
save('receipt.json',receipt)
print(json.dumps({'candidateClosure':receipt['candidateClosure'],'testBodiesExecuted':23,'passed':21,'failed':2,'runtimeAccepted':False,'ownedScratchRemoved':True},sort_keys=True))
