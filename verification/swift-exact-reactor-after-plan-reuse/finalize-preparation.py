#!/usr/bin/env python3
"""Seal this preparation packet after finite controls and compiler-target cleanup."""
import ast
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'verification/swift-exact-reactor-after-grouped-index'
DOC=ROOT/'docs/swift-exact-reactor-after-plan-reuse.md'

def sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): value.update(chunk)
    return value.hexdigest()

def read(path): return json.loads(Path(path).read_bytes())
def save(name,value): (HERE/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

spec=importlib.util.spec_from_file_location('plan_reuse_diagnostic',HERE/'diagnostic.py')
driver=importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
assert not (HERE/'prepared-seal.json').exists(),'seal once; preserve failures'
assert not (HERE/'target-attempt-started.json').exists()
assert not (HERE/'commands/target-once').exists()
assert not (HERE/'root-selection.json').exists()
driver.assert_baseline()
driver.assert_inputs()
assert (HERE/'harness.rs').read_bytes()==(OLD/'harness.rs').read_bytes()
assert (HERE/'test_driver.py').read_bytes()==(OLD/'test_driver.py').read_bytes()
assert (HERE/'run-preparation-step.py').read_bytes()==(OLD/'run-preparation-step.py').read_bytes()
old=(OLD/'diagnostic.py').read_text()
new=(HERE/'diagnostic.py').read_text()
old_functions={n.name:n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef)}
new_functions={n.name:n for n in ast.parse(new).body if isinstance(n,ast.FunctionDef)}
assert set(old_functions)==set(new_functions)
unchanged=[]
for name in old_functions:
    if name=='prepare': continue
    a=ast.get_source_segment(old,old_functions[name])
    b=ast.get_source_segment(new,new_functions[name])
    if name=='execute':
        b=b.replace('exact real Swift reactor after accepted private decode plan reuse',
                    'exact real Swift reactor after accepted private grouped index reservation')
    assert a==b,name
    unchanged.append(name)
assert (HERE/'verify.py').read_text()==(OLD/'verify.py').read_text().replace(driver.HISTORICAL_CLOSURE,driver.CLOSURE)
assert (HERE/'proposed-command.json').read_text()==(OLD/'proposed-command.json').read_text().replace(
    'swift-exact-reactor-after-grouped-index','swift-exact-reactor-after-plan-reuse')
control_cleanup=[]
for name in ('control-001','control-002'):
    events=read(HERE/(name+'-events.json'))
    previous=read(OLD/(name+'-events.json'))
    for event in ('validation_budget','run_budget','wasi_budget','wasi_grants'):
        assert [e for e in events if e['event']==event]==[e for e in previous if e['event']==event]
    assert next(e['payload'] for e in events if e['event']=='cleanup_reservations_and_live_empty') is True
    usage=next(e['payload'] for e in events if e['event']=='final_cleanup_usage')
    assert usage['cleanup_invariant'] is None
    for field,value in usage['reservations'].items():
        assert value['current']==0 if isinstance(value,dict) else field=='peak_tickets' or value==0
    assert all(v['current']==0 for v in usage['live'].values())
    result=read(HERE/(name+'-result.json'))
    assert result['commandPassed'] and result['diagnosticCompleted'] and result['ownedCleanupEmpty']
    assert result['firstFailure'] is None and result['targetAttempted'] is False
    control_cleanup.append({'name':name,'finalUsage':usage,'fullTargetMeasurement':False})
save('contract-audit.json',{'schema':1,'status':'same-approved-harness-and-diagnostic-contract',
    'originalHarnessSHA256':sha(OLD/'harness.rs'),'newHarnessSHA256':sha(HERE/'harness.rs'),
    'hostControlBytesIdentical':True,'preparationLauncherBytesIdentical':True,
    'unchangedDriverFunctions':unchanged,'executeOnlyChange':'human-readable accepted decode-plan source label',
    'prepareChanges':'accepted four-file source closure; root integration acceptance and regression bindings; prior sealed CacheWork result and root selection; observed contract snapshots and root-supplied revision context',
    'proposedCommandChanges':'owned packet path components only',
    'validationRunWasiBudgetsAndGrantsIdentical':True,'syntheticFinalConsumingReservationsAndLiveZero':True,
    'syntheticCleanup':control_cleanup,'historicalDriverCompilerNativeAndNodeExecuted':False,
    'fullTargetAttempted':False,'sourceClosure':driver.CLOSURE,
    'literalComparisonScope':'contract preservation only; no static analysis authorizes a release or predicts full-target completion'})
commands=[]
for path in sorted((HERE/'commands').glob('*/receipt.json')):
    command=read(path)
    assert command['passed'] and command['exitCode']==0 and not command['timedOut']
    assert command['signalSent']==[] and command['rawStreamEOFConfirmed']
    assert command['finalGroupObservation']['state']=='absent'
    assert driver.observe_group(command['processGroup'])['state']=='absent'
    for stream in ('stdout','stderr'): assert sha(path.parent/stream)==command[stream]['sha256']
    commands.append(path.parent.name)
assert commands==['build-001','control-001','control-002','driver-observation-controls','list-001']
assert 'Ran 10 tests' in (HERE/'commands/driver-observation-controls/stderr').read_text()
assert (HERE/'commands/driver-observation-controls/stderr').read_text().rstrip().endswith('OK')
outer=[]
for stem in ('prepare','build','control-001','control-002','host-controls','proposal','cleanup-build-target'):
    path=HERE/'outer-preparation-commands'/stem/'receipt.json'
    command=read(path)
    assert command['passed'] and command['exitCode']==0 and not command['timedOut']
    assert command['finalGroupObservation']['state']=='absent' and command['signalsSent']==[]
    assert command['rawStreamEOFConfirmed'] and driver.observe_group(command['processGroup'])['state']=='absent'
    for stream in ('stdout','stderr'): assert sha(HERE/(stem+'.'+stream))==command[stream]['sha256']
    outer.append(command|{'receipt':str(path.relative_to(HERE))})
cleanup=read(HERE/'preparation-products-cleanup.json')
assert cleanup['removedCompilerTarget'] and cleanup['compilerTargetAbsent'] and not driver.TARGET.exists()
assert cleanup['ownedScratchRetained'] and cleanup['holdersEmpty'] and cleanup['deviceInodeStable']
assert cleanup['allEarlierOwnedGroupsAbsent'] and cleanup['noSignalsSent']
assert cleanup['originalAndCompressedBinaryRetained'] and cleanup['sourceUnchanged']
assert cleanup['targetAttempted'] is False and cleanup['otherProjectsTouched'] is False
holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(driver.SCRATCH)],capture_output=True,timeout=30)
(HERE/'preparation-holders.stdout').write_bytes(holders.stdout)
(HERE/'preparation-holders.stderr').write_bytes(holders.stderr)
assert holders.returncode==1 and not holders.stdout and not holders.stderr
save('preparation-cleanup-state.json',{'schema':1,'allOwnedCommandGroupsAbsent':True,'signalsSent':[],
    'holderCommand':['/usr/sbin/lsof','-nP','+D',str(driver.SCRATCH)],'holderExitCode':holders.returncode,
    'holderStdoutSHA256':sha(HERE/'preparation-holders.stdout'),'holderStderrSHA256':sha(HERE/'preparation-holders.stderr'),
    'ownedCompilerTargetRemoved':True,'ownedRuntimePreparationScratchRetained':True,
    'ownedScratchMeaning':'copied source and tmp required by unchanged later driver; no compiler target',
    'fullTargetAttempted':False,'nativeOrSimulatorOrPhoneProcessesTouched':False})
binding=read(HERE/'binding.json')
binary=read(HERE/'binary.json')['retained']
assert driver.identity(HERE/'bin/exact-tests')==binary
archive=HERE/'bin/exact-tests.gz'
with gzip.open(archive,'rb') as stream: uncompressed=stream.read()
assert len(uncompressed)==binary['bytes'] and hashlib.sha256(uncompressed).hexdigest()==binary['sha256']
accepted=read(driver.ACCEPTED/'acceptance.json')
revision=read(HERE/'root-commit-context.json')
assert revision['sourceClosure']==driver.CLOSURE and revision['rootReportsSourceUnchanged']
save('receipt.json',{'schema':1,'status':'prepared-awaiting-root-exact-selection',
    'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext':binding['sourceRevisionContext'],'rootCommitContext':revision,
    'sourceRevisionMeaning':'initial root-supplied context followed by root-reported commit of unchanged accepted closure; no Git query or clean-tree assertion',
    'sourceFiles':132,'sourceManifestSHA256':driver.CLOSURE,
    'acceptedDecodePlanIntegrationAcceptanceSHA256':sha(driver.ACCEPTED/'acceptance.json'),
    'acceptedDecodePlanIntegrationReceiptSHA256':sha(driver.ACCEPTED/'receipt.json'),
    'acceptedIntegrationFocusedTestsPassed':340,'acceptedIntegrationIgnored':0,
    'acceptedFullRegressionNamedPasses':2314,'inheritedIgnoredPerFullRegressionContext':9,
    'acceptedFixedReservationIncreaseBytes':29008,'acceptedFiniteConstructorWorkSteps':4928,
    'unchangedTicketLimit':86,'unchangedResidentLimit':64,'unchangedCacheBytes':16777216,
    'unchangedCacheEntryBytes':8388608,'unchangedCacheWork':64000000,'unchangedCombinedBytes':268435456,
    'binaryBytes':binary['bytes'],'binarySHA256':binary['sha256'],'compressedBinary':driver.identity(archive),
    'driverSHA256':sha(HERE/'diagnostic.py'),'harnessSHA256':sha(HERE/'harness.rs'),
    'inputBindingSHA256':sha(HERE/'binding.json'),'preparedSelectionSHA256':sha(HERE/'prepared-selection.json'),
    'target':binding['target'],'commands':outer,'failedPreparationStepExecutions':0,
    'freshReleaseBuildPassed':True,'buildScope':'--lib --no-run --release; no full-target execution',
    'wiringControlsPassed':2,'hostProcessObservationControlsPassed':10,
    'allOwnedCommandGroupsAbsent':True,'rawStreamEOFConfirmed':True,'signalsSent':[],'targetAttempts':0,
    'fullTargetSelected':False,'nativeExecuted':False,'physicalPhonesAttempted':False,
    'physicalPhones':'disconnected; final acceptance pending','gaAccepted':False,
    'fullSLMatrixAccepted':False,'productionAccountingAccepted':False,
    'productionBaselineModifiedByDiagnostic':False,'budgetWidened':False,'historicalPacketsUsedAsDataOnly':True,
    'consumingCleanupClassification':'causal first failure, copied final_failure.after_cleanup before foundation consumption and final consuming zero ledger are distinct; cleanup_empty/ownedCleanupEmpty also require no retained failure',
    'ownedCompilerTargetRemoved':True,'ownedRuntimePreparationScratchRetained':True,
    'ownedScratchDisposition':'copied runtime source/tmp and original+losslessly compressed executable retained for unchanged root-selected dispatch; compiler target removed after exact group/holder/inode checks',
    'preparationCleanupReceiptSHA256':sha(HERE/'preparation-products-cleanup.json')})
DOC.write_text(f'''# Exact full Swift reactor after decode-plan reuse: preparation

The packet in `verification/swift-exact-reactor-after-plan-reuse/` is prepared
for root review. No full-target attempt has occurred, and root must separately
select the exact source, binary, tools, inputs and command before dispatch.
The 132-file live VM closure is `{driver.CLOSURE}`.
Root's accepted integration is bound by acceptance SHA-256
`{sha(driver.ACCEPTED/'acceptance.json')}`. It records 340 fresh private host tests
passing with zero failures or ignores, following 2,314 full-regression named passes
and nine inherited ignores per context. Those observations do not establish a
successful full reactor.

The source was frozen with root-supplied revision context
`{binding['sourceRevisionContext']}` plus the accepted uncommitted integration.
Root subsequently reported commit `{revision['currentCommitContext']}` with the
same source closure. This packet queried no Git state; content bindings remain
authoritative. The exact four changed VM files are `cache.rs`, `cache_tests.rs`,
`execution_tests.rs` and `lifecycle_tests.rs` under `src/experimental_swift_reactor/`.
Production cache bytes match the independently reviewed finite candidate. The
512 bounded count-scan plans remain identity checked and every decoded rebuild
still parses and validates the complete body. The fixed cache reservation grows
by 29,008 bytes, reducing payload capacity; construction costs 4,928 credits.
These accepted finite costs predict no full-workload outcome.

The original test-only harness is byte-identical, SHA-256
`{sha(HERE/'harness.rs')}`. Its exact workload, parser, selected child argv,
observation, deadlines, process cleanup and one-attempt guard are preserved.
All twenty driver functions outside preparation are literal copies of the prior
packet after normalizing only the target result's human-readable source label.
`driver-changes.diff` and `contract-audit.json` retain the comparison. The only
build-copy change is the diagnostic include appended to `lifecycle_tests.rs`.
Live product sources are read-only.

The original full Swift module remains 53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`, at
`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`.
Original source/compiler/product receipts, inputs, the eleven-field native oracle,
the prior prepared/result seals and root-selection counterpart are bound as data.
No historical driver, compiler, native executable or Node oracle is run here.
The canonical prior result is `verification/swift-exact-reactor-after-grouped-index/result.md`;
there is no `docs/swift-exact-reactor-after-grouped-index-result.md`.

The previous sole attempt passed validation and Initialize, then failed Corpus 1
at `Cache / WorkExhausted / swift_run_work / CacheWork`, attempted
64,000,001 / 64,000,000, function 3416, byte offset 1077688, after 15,753,076
instructions. Corpus 2 was unrun. The causal first failure, its copied
`final_failure.after_cleanup` before foundation consumption, and the final
consuming zero ledger remain separate observations. The historical copied failure
cleanup still held three foundation tickets and 271,168 combined bytes; the final
consuming cleanup released them all, with no cleanup invariant. Historical
`cleanup_empty=false` and `ownedCleanupEmpty=false` also retain the failure and
are not current-reservation emptiness tests. Original failure evidence is preserved.

The unchanged harness validates the complete module, drops external input before
adoption, constructs the original owner, invokes Initialize (35) once and Corpus
(62) twice through consuming completion barriers. Each Corpus must return i32
zero and emit a complete duplicate-free eleven-field JSON suffix matching native
field types and values. Counters, memory and stdout remain cumulative; the first
failure short circuits dependent phases.

Validation retains 120,000 ms; runtime and WASI retain the original cumulative
30,000 ms deadlines. Cache work remains 64,000,000, tickets 86, residents and
pins 64, cache 16 MiB, entry 8 MiB, combined memory 256 MiB. All other original
budgets, hooks and cancellation contracts are unchanged. The full-target outer
deadline remains 170 seconds, followed by at most five seconds TERM grace and
five seconds KILL wait for its exact owned group. Failure and partial raw streams
are recorded before any signal. Unknown process state cannot pass or authorize
removal.

Preparation passes one fresh bounded Release no-run build, the two existing
small synthetic harness wiring/consuming-cleanup controls and ten existing host
process-observation controls. The fresh executable is {binary['bytes']:,} bytes,
SHA-256 `{binary['sha256']}`; its lossless compressed copy is
{archive.stat().st_size:,} bytes, SHA-256 `{sha(archive)}`.
Both finite controls end with zero current reservations, live counts and tickets,
and no cleanup invariant. These are wiring controls, not surrogate qualification
or measurements of the full reactor. Commands, exact compiler binaries/sysroot,
source and products, PID/PGID, raw streams and complete EOF are retained.

All owned preparation groups are absent and required no signals. Exact path,
device/inode and empty recursive holders were checked before removing the owned
compiler target; {cleanup['logicalBytesToRemove']:,} logical bytes were removed.
The copied runtime source/tmp in `owned-scratch/` and original plus compressed
`bin/exact-tests` remain for the unchanged later dispatch. Retained runtime
preparation scratch is distinct from the removed compiler target. No other
project's processes or data were touched.

The exact proposed command remains guarded and unexecuted:

```sh
python3 -B verification/swift-exact-reactor-after-plan-reuse/diagnostic.py target
```

`prepared-selection.json` and `proposed-command.json` bind source, executable,
tools, inputs, unchanged harness, child argv/environment and all original limits.
Root must create matching `root-selection.json` with its current revision and
prepared seal before the driver atomically consumes its one-attempt marker.
No retry or widened budget is authorized. Verify the preparation read-only,
without build or guest execution:

```sh
python3 -B verification/swift-exact-reactor-after-plan-reuse/verify.py
```

[Receipt](../verification/swift-exact-reactor-after-plan-reuse/receipt.json),
[contract audit](../verification/swift-exact-reactor-after-plan-reuse/contract-audit.json),
[cleanup](../verification/swift-exact-reactor-after-plan-reuse/preparation-products-cleanup.json)
and [seal](../verification/swift-exact-reactor-after-plan-reuse/prepared-seal.json)
retain the preparation boundaries. Full-target completion, guest parity, full SL
matrix, table mutation, production caller stack/accounting, public/signed/native
execution, memory/size/startup/performance, full app UI/effects/state/async/actor
coverage, debugger, immutable published-package FieldLog consumption from a
separate repository, store, customer/operational and accountable GA gates remain
pending. Phones are disconnected and final physical checks remain deferred.
No native/device/UI/phone, provider/network, hosted frozen lane, Git, credential,
publication or release operation is included. The whole product goal remains active.
''')
files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*'))
       if p.is_file() and 'owned-scratch' not in p.relative_to(HERE).parts
       and p.name not in ('prepared-seal.json','root-selection.json')}
save('prepared-seal.json',{'schema':1,'status':'prepared-awaiting-root-exact-selection','targetAttempts':0,
    'excludedOwnedScratch':'retained copied runtime source/tmp; compiler target removed; copied source closure bound separately',
    'files':files,'externalFiles':{str(DOC.relative_to(ROOT)):sha(DOC)}})
print(json.dumps({'preparedSealSHA256':sha(HERE/'prepared-seal.json'),
    'preparedSelectionSHA256':sha(HERE/'prepared-selection.json'),'receiptSHA256':sha(HERE/'receipt.json'),
    'retainedMembers':len(files),'binarySHA256':binary['sha256'],'targetAttempts':0,'rootSelectionRequired':True}))
