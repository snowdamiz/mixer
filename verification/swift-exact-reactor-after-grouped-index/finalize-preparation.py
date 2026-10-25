#!/usr/bin/env python3
"""Seal prepared host-only evidence; never executes a target or modifies live VM."""
import ast
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-exact-reactor-after-resident-index'
DOC = ROOT / 'docs/swift-exact-reactor-after-grouped-index.md'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

spec = importlib.util.spec_from_file_location('grouped_diagnostic', HERE / 'diagnostic.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
assert not (HERE / 'prepared-seal.json').exists(), 'seal once; preserve failures'
assert not (HERE / 'root-selection.json').exists()
assert not (HERE / 'target-attempt-started.json').exists()
assert not (HERE / 'commands/target-once').exists()
driver.assert_baseline()
driver.assert_inputs()
assert (HERE / 'harness.rs').read_bytes() == (OLD / 'harness.rs').read_bytes()
assert (HERE / 'test_driver.py').read_bytes() == (OLD / 'test_driver.py').read_bytes()
old = (OLD / 'diagnostic.py').read_text()
new = (HERE / 'diagnostic.py').read_text()
# The selected runner, parser, target, cleanup, budgets and argv code stay literal.
old_functions = {n.name: n for n in ast.parse(old).body if isinstance(n, ast.FunctionDef)}
new_functions = {n.name: n for n in ast.parse(new).body if isinstance(n, ast.FunctionDef)}
assert set(old_functions) == set(new_functions)
unchanged = []
for name in old_functions:
    if name == 'prepare':
        continue
    old_text = ast.get_source_segment(old, old_functions[name])
    new_text = ast.get_source_segment(new, new_functions[name])
    if name == 'execute':
        new_text = new_text.replace('exact real Swift reactor after accepted private grouped index reservation',
                                    'exact real Swift reactor after accepted private cache resident index')
    assert old_text == new_text, name
    unchanged.append(name)
assert (HERE / 'verify.py').read_text() == (OLD / 'verify.py').read_text().replace(
    'CLOSURE = "02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d"',
    'CLOSURE = "3ffa1055e462be74c10ee9830bf891bbd196a896dfc7a66dc6befe2a6d9bb70f"')
old_command = (OLD / 'proposed-command.json').read_text()
new_command = (HERE / 'proposed-command.json').read_text()
assert new_command == old_command.replace('swift-exact-reactor-after-resident-index', 'swift-exact-reactor-after-grouped-index')
for name in ('control-001', 'control-002'):
    actual = read(HERE / (name + '-events.json'))
    previous = read(OLD / (name + '-events.json'))
    for event in ('validation_budget', 'run_budget', 'wasi_budget', 'wasi_grants'):
        assert [e for e in actual if e['event'] == event] == [e for e in previous if e['event'] == event]
    assert next(e['payload'] for e in actual if e['event'] == 'cleanup_reservations_and_live_empty') is True
    usage = next(e['payload'] for e in actual if e['event'] == 'final_cleanup_usage')
    assert usage['cleanup_invariant'] is None
    for field, value in usage['reservations'].items():
        assert value['current'] == 0 if isinstance(value, dict) else field == 'peak_tickets' or value == 0
    assert all(v['current'] == 0 for v in usage['live'].values())
    result = read(HERE / (name + '-result.json'))
    assert result['commandPassed'] and result['diagnosticCompleted'] and result['ownedCleanupEmpty']
    assert result['firstFailure'] is None and result['targetAttempted'] is False
save('contract-audit.json', {
    'schema': 1, 'status': 'same-approved-harness-and-diagnostic-contract',
    'originalHarnessSHA256': sha(OLD / 'harness.rs'), 'newHarnessSHA256': sha(HERE / 'harness.rs'),
    'hostControlBytesIdentical': True, 'unchangedDriverFunctions': unchanged,
    'executeOnlyChange': 'human-readable accepted-slice scope label',
    'prepareChanges': 'output directory, accepted integration/source, exact two-file difference, root-supplied revision context without Git, historical result/source and selection binding',
    'proposedCommandChanges': 'owned after-resident-index path components replaced by after-grouped-index only',
    'validationRunWasiBudgetsAndGrantsIdentical': True,
    'syntheticFinalConsumingReservationsAndLiveZero': True,
    'historicalDriverNativeAndNodeExecuted': False, 'fullTargetAttempted': False,
    'sourceRevisionContext': read(HERE / 'binding.json')['sourceRevisionContext'],
    'sourceClosure': driver.CLOSURE})
commands = []
for path in sorted((HERE / 'commands').glob('*/receipt.json')):
    command = read(path)
    assert command['passed'] and command['exitCode'] == 0 and not command['timedOut']
    assert command['signalSent'] == [] and command['rawStreamEOFConfirmed']
    assert command['finalGroupObservation']['state'] == 'absent'
    assert driver.observe_group(command['processGroup'])['state'] == 'absent'
    for stream in ('stdout', 'stderr'):
        assert sha(path.parent / stream) == command[stream]['sha256']
    commands.append(path.parent.name)
assert commands == ['build-001', 'control-001', 'control-002', 'driver-observation-controls', 'list-001']
assert 'Ran 10 tests' in (HERE / 'commands/driver-observation-controls/stderr').read_text()
assert (HERE / 'commands/driver-observation-controls/stderr').read_text().rstrip().endswith('OK')
holders = subprocess.run(['/usr/sbin/lsof', '-nP', '+D', str(HERE / 'owned-scratch')], capture_output=True, timeout=30)
(HERE / 'preparation-holders.stdout').write_bytes(holders.stdout)
(HERE / 'preparation-holders.stderr').write_bytes(holders.stderr)
assert holders.returncode == 1 and not holders.stdout and not holders.stderr
save('preparation-cleanup-state.json', {
    'schema': 1, 'allOwnedCommandGroupsAbsent': True, 'signalsSent': [],
    'holderCommand': ['/usr/sbin/lsof', '-nP', '+D', str(HERE / 'owned-scratch')],
    'holderExitCode': holders.returncode, 'holderStdoutSHA256': sha(HERE / 'preparation-holders.stdout'),
    'holderStderrSHA256': sha(HERE / 'preparation-holders.stderr'), 'ownedScratchRetainedForSelectedTarget': True,
    'ownedScratchRemoved': False, 'fullTargetAttempted': False,
    'nativeOrSimulatorOrPhoneProcessesTouched': False})
selection = read(HERE / 'prepared-selection.json')
binding = read(HERE / 'binding.json')
binary = read(HERE / 'binary.json')['retained']
assert sha(HERE / 'bin/exact-tests') == binary['sha256']
outer = []
for stem in ('prepare','build','control-001','control-002','host-controls','proposal'):
    path = HERE / 'outer-preparation-commands' / stem / 'receipt.json'
    command = read(path)
    assert command['passed'] and command['exitCode'] == 0 and not command['timedOut']
    assert command['finalGroupObservation']['state'] == 'absent'
    assert command['signalsSent'] == [] and command['rawStreamEOFConfirmed']
    assert driver.observe_group(command['processGroup'])['state'] == 'absent'
    for stream in ('stdout','stderr'):
        assert sha(HERE / (stem+'.'+stream)) == command[stream]['sha256']
    outer.append(command | {'receipt': str(path.relative_to(HERE))})
save('receipt.json', {
    'schema': 1, 'status': 'prepared-awaiting-root-exact-selection',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': binding['sourceRevisionContext'],
    'sourceRevisionMeaning': 'root-supplied pre-commit HEAD context; exact source closure includes the accepted two-file private VM delta and does not assert it was already committed; no Git query',
    'sourceFiles': 132, 'sourceManifestSHA256': driver.CLOSURE,
    'acceptedGroupedIndexIntegrationReceiptSHA256': sha(driver.ACCEPTED / 'receipt.json'),
    'acceptedGroupedIndexIntegrationSelectionSHA256': sha(driver.ACCEPTED / 'selection.json'),
    'acceptedIntegrationFocusedTestsPassed': 32, 'acceptedIntegrationOwnedTargetRemoved': True,
    'acceptedIndexPayloadBytes': 192, 'acceptedActualCacheVecAllocations': 4,
    'acceptedFiniteConstructorWorkSteps': 832, 'unchangedTicketLimit': 86,
    'unchangedResidentLimit': 64,
    'binaryBytes': binary['bytes'], 'binarySHA256': binary['sha256'],
    'driverSHA256': sha(HERE / 'diagnostic.py'), 'harnessSHA256': sha(HERE / 'harness.rs'),
    'inputBindingSHA256': sha(HERE / 'binding.json'),
    'preparedSelectionSHA256': sha(HERE / 'prepared-selection.json'),
    'target': binding['target'], 'commands': outer, 'failedPreparationStepExecutions': 0,
    'preservedStaticAssemblyFailures': ['preparation-failures/001-static-assembly'],
    'currentCommitContextSuppliedLaterByRoot': read(HERE / 'root-commit-context.json'),
    'freshReleaseBuildPassed': True, 'wiringControlsPassed': 2,
    'hostProcessObservationControlsPassed': 10, 'allOwnedCommandGroupsAbsent': True,
    'rawStreamEOFConfirmed': True, 'signalsSent': [], 'targetAttempts': 0,
    'fullTargetSelected': False, 'nativeExecuted': False, 'physicalPhonesAttempted': False,
    'physicalPhones': 'disconnected; final acceptance pending', 'gaAccepted': False,
    'fullSLMatrixAccepted': False, 'productionAccountingAccepted': False,
    'productionBaselineModifiedByDiagnostic': False, 'budgetWidened': False,
    'historicalPacketsUsedAsDataOnly': True,
    'consumingCleanupClassification': 'final cleanup_reservations_and_live_empty and final_cleanup_usage current-zero categories/tickets are independent from success-oriented cleanup_empty and ownedCleanupEmpty; failures must retain both observations',
    'ownedScratchDisposition': 'retained for exact root-selected run; only owned scratch deletion after terminal absence and empty holders'})
DOC.write_text(f'''# Exact full Swift reactor after grouped resident-index reservation: preparation

The fresh host packet copies the accepted live 132-file VM closure
`{driver.CLOSURE}`. Root's integration selection is
`{sha(driver.ACCEPTED / 'selection.json')}`; its receipt records 32 fresh tests
passed, complete EOF, absent owned groups and the owned target removed. The only
source changes from the immediate prior packet are private `cache.rs` and
`cache_tests.rs`. The existing 192-byte index payload is charged once through
its header; four actual vector allocation requests and the finite fixture's
832 construction work steps remain. Ticket limit 86, resident limit 64 and all
other production limits remain unchanged. These finite observations predict no
full-reactor outcome. The exact source closure is authoritative. The source
revision context `{binding['sourceRevisionContext']}` was supplied by root before
its commit; this packet queried no Git state and asserts no clean commit.

The packet is `verification/swift-exact-reactor-after-grouped-index/`. The original
harness is byte-identical, SHA-256 `{sha(HERE / 'harness.rs')}`. The selected runner,
parser, child argv, workload, observation and cleanup functions are literal copies
of the immediate prior packet; the execute function changes only its result label.
`driver-changes.diff` and `contract-audit.json` bind the restricted preparation
changes. Only the diagnostic include is appended in the owned build copy of
`lifecycle_tests.rs`; live product sources are read-only.

The exact target remains 53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`, at
`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`.
Original inputs and the eleven-field native oracle are bound as data. The previous
packet's prepared seal and final result seal are retained unchanged as data. Its
sole attempt passed validation and Initialize, then failed TicketInventory 87/86;
the exact requesting owner was unobserved and guest parity did not pass. No
historical driver, compiler, native binary or Node oracle is run here.

The unchanged harness validates the complete module, drops external input before
adoption, constructs its original owner, invokes Initialize (35) once and Corpus
(62) twice through consuming completion barriers. Each Corpus must return i32
zero and emit one complete duplicate-free eleven-field JSON suffix matching
native field types and values. Counters, memory and stdout remain cumulative.
The first failure short circuits dependent phases and remains preserved.

Validation has 120,000 ms; runtime and WASI each retain the original cumulative
30,000 ms deadline. Full-target outer time is 170 seconds, then at most five
seconds TERM grace and five seconds KILL wait for its exact owned group. All
other original resource ceilings, hooks, cancellation and consuming cleanup
contracts are unchanged. Failure evidence and partial raw output are recorded
before process signals. Current-zero consuming reservation/live/ticket evidence
is distinct from success-oriented `cleanup_empty` / `ownedCleanupEmpty`, which
also require no retained failure.

Preparation passed a fresh bounded Release no-run build, two existing finite
synthetic wiring/consuming-cleanup controls and ten existing host-only process
observation controls. The fresh executable is {binary['bytes']:,} bytes, SHA-256
`{binary['sha256']}`. Both synthetic final consuming snapshots have zero current
reservations, live counts and tickets and no cleanup invariant; their shapes are
not measurements of the full reactor. Exact tools, source, commands, PID/PGID,
outputs and EOF are recorded. All owned groups are absent, no cleanup signal was
needed and the recursive scratch holder check is empty. Fresh owned scratch and
binary remain available for root's later selection. Terminal cleanup must retain
the lossless compressed binary and remove only the owned scratch after group,
holder and path/inode checks. Unknown process state cannot pass or authorize
removal.

No full-target attempt has occurred. `prepared-selection.json` and
`proposed-command.json` bind the fresh source, binary, tools, inputs, unchanged
harness, child argv/environment and the proposed command:

```sh
python3 -B verification/swift-exact-reactor-after-grouped-index/diagnostic.py target
```

Root must separately select this exact packet and bind its current commit, seal,
binary, tools, workload and original harness in matching `root-selection.json`.
The unchanged driver rejects absent or mismatched selection and atomically
consumes its one-attempt marker before launch. No automatic retry or widened
budget is authorized. The full target remains pending with no qualification
prediction. Verify preparation read-only, with no build or guest execution:

```sh
python3 -B verification/swift-exact-reactor-after-grouped-index/verify.py
```

[Receipt](../verification/swift-exact-reactor-after-grouped-index/receipt.json),
[contract audit](../verification/swift-exact-reactor-after-grouped-index/contract-audit.json)
and [prepared seal](../verification/swift-exact-reactor-after-grouped-index/prepared-seal.json)
contain the preparation bindings. The failed static driver assembly is preserved in `preparation-failures/001-static-assembly/`;
its function-inventory assertion failed before any preparation child was started,
and the fresh reconstruction passed the literal-function check.
Full-target completion, guest parity, full SL
matrix, guest table mutation, production caller stack/accounting, public/signed/
native execution, memory/size/startup/performance, full app UI/effects/state/async/
actor coverage, debugger, immutable published FieldLog consumed from a separate
repository, store, customer/operational and accountable GA gates remain pending.
Physical phones remain disconnected and deferred. No native/UI/phone, provider,
hosted, credential, publication, other project's process or excluded frozen lane
operation is included.
''')
files = {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
         if p.is_file() and 'owned-scratch' not in p.relative_to(HERE).parts
         and p.name not in ('prepared-seal.json', 'root-selection.json')}
save('prepared-seal.json', {
    'schema': 1, 'status': 'prepared-awaiting-root-exact-selection', 'targetAttempts': 0,
    'excludedOwnedScratch': 'transient build/source working directory; source closure and child outputs bound separately',
    'files': files, 'externalFiles': {str(DOC.relative_to(ROOT)): sha(DOC)}})
print(json.dumps({'preparedSealSHA256': sha(HERE / 'prepared-seal.json'),
    'preparedSelectionSHA256': sha(HERE / 'prepared-selection.json'),
    'receiptSHA256': sha(HERE / 'receipt.json'), 'retainedMembers': len(files),
    'binarySHA256': binary['sha256'], 'targetAttempts': 0, 'rootSelectionRequired': True}))
