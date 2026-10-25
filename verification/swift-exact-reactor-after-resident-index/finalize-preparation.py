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
OLD = ROOT / 'verification/swift-exact-reactor-after-cache'
DOC = ROOT / 'docs/swift-exact-reactor-after-resident-index.md'

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

spec = importlib.util.spec_from_file_location('resident_diagnostic', HERE / 'diagnostic.py')
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
        new_text = new_text.replace('exact real Swift reactor after accepted private cache resident index',
                                    'exact real Swift reactor after accepted private cache reset elision')
    assert old_text == new_text, name
    unchanged.append(name)
assert (HERE / 'verify.py').read_text() == (OLD / 'verify.py').read_text().replace(
    'CLOSURE = "b28da766c84b6353a4511e2fc3fbcb0d4302d5b8a5a74da1ee3d7fb776ca2c11"',
    'CLOSURE = "02fd25a32b05cf8c4b10e0f68df029d8851e14610ccecbec772be09af5073f8d"')
old_command = (OLD / 'proposed-command.json').read_text()
new_command = (HERE / 'proposed-command.json').read_text()
assert new_command == old_command.replace('swift-exact-reactor-after-cache', 'swift-exact-reactor-after-resident-index')
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
    'prepareChanges': 'output directory, accepted integration/source, exact six-file difference, historical result/source and selection binding',
    'proposedCommandChanges': 'owned after-cache path components replaced by after-resident-index only',
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
for action, stem in [('prepare','prepare'), ('build','build'), ('control','control-001'),
                     ('control','control-002'), ('host-controls','host-controls'), ('propose','proposal')]:
    outer.append({'argv': ['python3','-B',str((HERE / 'diagnostic.py').relative_to(ROOT)),action],
                  'cwd': str(ROOT), 'exitCode': 0, 'scope': 'preparation only; no full target execution',
                  'stdout': {'path':stem+'.stdout','sha256':sha(HERE / (stem+'.stdout'))},
                  'stderr': {'path':stem+'.stderr','sha256':sha(HERE / (stem+'.stderr'))}})
save('receipt.json', {
    'schema': 1, 'status': 'prepared-awaiting-root-exact-selection',
    'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'sourceRevisionContext': binding['sourceRevisionContext'],
    'sourceRevisionMeaning': 'HEAD context at source freeze; exact source closure includes the accepted six-file working tree integration and does not assert it was already committed',
    'sourceFiles': 132, 'sourceManifestSHA256': driver.CLOSURE,
    'acceptedResidentIntegrationReceiptSHA256': sha(driver.ACCEPTED / 'receipt.json'),
    'acceptedResidentIntegrationSelectionSHA256': sha(driver.ACCEPTED / 'selection.json'),
    'acceptedIntegrationFocusedTestsPassed': 32, 'acceptedIntegrationOwnedTargetRemoved': True,
    'acceptedDefaultFixedReservationBytes': 89376,
    'binaryBytes': binary['bytes'], 'binarySHA256': binary['sha256'],
    'driverSHA256': sha(HERE / 'diagnostic.py'), 'harnessSHA256': sha(HERE / 'harness.rs'),
    'inputBindingSHA256': sha(HERE / 'binding.json'),
    'preparedSelectionSHA256': sha(HERE / 'prepared-selection.json'),
    'target': binding['target'], 'commands': outer,
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
DOC.write_text(f'''# Exact full Swift reactor after private resident index: preparation

The host diagnostic is prepared from the accepted live 132-file VM closure
`{driver.CLOSURE}`. Root's resident-index integration receipt records all 32 fresh
tests passed, complete stream EOF, empty process groups and removal of its owned
target. Its selection SHA-256 is
`601b87b71e666db2469bf31e5b476698ba2a4d883742f90be4c0293a8f1e820d`.
The accepted default cache fixed reservation is 89,376 bytes. Production ceilings
remain unchanged. Source-freeze HEAD context was `{binding['sourceRevisionContext']}`;
that context and the exact source-tree closure are distinct. This preparation
records no claim that the accepted working-tree integration was already committed.

The packet is `verification/swift-exact-reactor-after-resident-index/`. It copies
all 132 accepted source files into private scratch and appends only the original
private diagnostic include to `lifecycle_tests.rs`. The approved original
after-cache harness is byte-identical, SHA-256
`{sha(HERE / 'harness.rs')}`. No attribution instrumentation is included.
`driver-changes.diff` and `contract-audit.json` show that changes bind the fresh
output location, accepted source/integration selection, six-file source difference
and historical packet. The selected runner, parser, argv, observation/cleanup
logic and limits remain literal. The execute function changes only its result's
human-readable slice label. The original failed after-cache result, including its
CacheWork failure and compressed original executable, remains unchanged and bound
as data. Historical driver, compiler, native binary and Node oracle are not run.

The target remains the qualified full Swift SDK reactor at
`compiler/experiments/fieldlog-reactor/local/2026-10-23-qualified/wasm/fieldlog-reactor.wasm`,
53,777,114 bytes, SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
Inputs and the eleven-field native oracle are the original immutable bindings.
The harness validates the whole module, drops the external input before adoption,
constructs the original owner, requests Initialize (35) once and Corpus (62) twice
through consuming completion barriers. Each Corpus must return i32 zero; each
actual stdout suffix must be one complete duplicate-free eleven-field JSON object
with exact native field types and values. Counters, memory and stdout remain
cumulative. Native parity cannot pass on empty, malformed or failed output.

Validation retains 120,000 ms; runtime and WASI retain cumulative 30,000 ms
deadlines and every original resource ceiling, counter, hook and cancellation
contract. The full-target outer limit is 170 seconds, followed by at most five
seconds TERM grace and five seconds KILL wait for the exact owned process group.
The first typed failure, raw output and pre-signal process/failure evidence must
remain preserved; dependent phases short circuit. Original frame/growth cleanup
and consuming owner cleanup remain the in-VM authorities. The final consuming
cleanup's current-zero reservations, live counts and ticket count are reported
separately from success-oriented `cleanup_empty` / `ownedCleanupEmpty`, which also
require no retained failure. A raw false success flag alone does not establish
that consuming cleanup retained resources.

Preparation passes a fresh bounded Release no-run build, two finite synthetic
wiring/consuming-cleanup controls and ten host-only process-observation controls.
The fresh executable is {binary['bytes']:,} bytes, SHA-256
`{binary['sha256']}`. These controls exercise no full reactor or native/device
workload. Both synthetic final consuming snapshots have current-zero reservations,
zero live categories/tickets and no cleanup invariant. Their synthetic module's
shapes do not constitute an actual full-reactor reservation measurement.

All owned command groups are proven absent; no cleanup signal was required. Raw
output handles close and complete hash reads reach EOF. An empty recursive holder
check is recorded. Owned scratch and the fresh executable are retained for the
root-selected run; after terminal completion, the unchanged cleanup command checks
holders and path/inode identity, retains a lossless compressed executable and
removes only owned scratch. Unknown process state cannot pass or authorize removal.
No simulator, emulator, phone or other project's process is touched.

`prepared-selection.json` and `proposed-command.json` bind the exact executable,
source, driver, harness, input closure, child argv/environment and proposed command:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/diagnostic.py target
```

No full-target attempt has occurred. Root must explicitly select the exact packet
and create its matching `root-selection.json` before the sole target attempt. The
driver rejects an absent/mismatched selection and atomically consumes the one-attempt
marker before launch. No retry or budget expansion is selected by preparation.

[Receipt](../verification/swift-exact-reactor-after-resident-index/receipt.json),
[contract audit](../verification/swift-exact-reactor-after-resident-index/contract-audit.json)
and [prepared seal](../verification/swift-exact-reactor-after-resident-index/prepared-seal.json)
bind commands, tools, source/inputs, raw output, EOF, cleanup and this document.
Verify the sealed preparation read-only, without compiling or guest execution:

```sh
python3 -B verification/swift-exact-reactor-after-resident-index/verify.py
```

Full-target completion, full SL matrix, guest table mutation, production caller
stack/accounting, public/signed/native execution, memory/size/startup/performance,
full app UI/effects/state/async/actor coverage, debugger, immutable published
FieldLog packages consumed from a separate repository, physical phones, store,
customer/operational and accountable GA gates remain pending. Phones remain
disconnected. No provider, deployment, publication, credential or frozen hosted
lane is changed.
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
