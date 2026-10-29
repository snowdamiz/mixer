"""Independent, bounded data-only audit. Never import or run a subject helper."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
BASE = 'verification/github-delivery-axis-binding-stage-recovery'
OUT = ROOT / BASE / 'review/postdelivery-actual'
HEAD = '2c751cbbc300efc9aa766b5d4add648610ca0341'
TREE = 'f2df6833ee8e9ce85306210b63dc35d45747fa0d'
PARENT = '2cea1013151ccc38bb635fb4755793cd25a0bd1b'
SELECTION = 'verification/android-axis-binding-selection-2026-10-29/selection.json'
PHASES = [
    ('stage-recovery-engine-ci-binding', 5, 6645, '1b58085f756fbaab45abc1f4d10e6680491a42d444752f897700bb25f86b949c', 'stage-recovery-engine-ci-binding.json', 93330),
    ('stage-recovery-axis-ci-binding', 5, 8425, '1dc4f35b4bfdd48d0152a27c881492525c6216dc74847269470398f3d5315b12', 'stage-recovery-axis-ci-binding.json', 78867),
    ('stage-recovery-dispatch-axis', 7, 8418, 'b270f6b8fbec310e4731460f3296ded8e6d00b41ae5ab8aab39072c89b4babd3', 'manual-axis-stage-recovery-visibility-pending.json', 61454),
    ('stage-recovery-bind-axis-run', 4, 8417, 'ad02b015d0a7914b6bc60a40b448b96ca87b718c7206b9631623e663997eb87e', 'manual-axis-stage-recovery-run-binding.json', 38899),
]
reads = {}
checks = []
commands = []
failures = []


def check(name, actual, expected=True):
    passed = type(actual) is type(expected) and actual == expected
    checks.append({'name': name, 'passed': passed})
    if not passed:
        failures.append({'name': name, 'actual': actual, 'expected': expected})


def read(path):
    rel = str(path)
    parts = PurePosixPath(rel)
    if parts.is_absolute() or '..' in parts.parts:
        raise ValueError('Relative repository file required')
    target = ROOT / rel
    meta = target.lstat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_size > 8 * 1024 * 1024:
        raise ValueError('Regular bounded data required: ' + rel)
    data = target.read_bytes()
    row = {'path': rel, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if rel in reads:
        check('stable-repeated-read:' + rel, row, reads[rel])
    reads[rel] = row
    return data


def load(path):
    return json.loads(read(path))


def row(path):
    read(path)
    return reads[str(path)]


def pinned(source, name):
    actual = row(source['path'])
    check(name + ':sha256', actual['sha256'], source['sha256'])
    if 'bytes' in source:
        check(name + ':bytes', actual['bytes'], source['bytes'])
    return actual


def timestamp(value):
    return datetime.datetime.fromisoformat(value)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def source_mode(path):
    value = (ROOT / path).lstat()
    return '100755' if value.st_mode & 0o111 else '100644'


def write(name, value):
    target = OUT / name
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


agents = read('AGENTS.md').decode()
plan = read('PLAN.md').decode()
for token in ['computer use, screen capture and native', 'runtime tests are paused', 'phones are disconnected', 'Never mark a GA gate verified']:
    check('AGENTS-hold:' + token, token.lower() in agents.lower())
check('PLAN-binding-scope', 'does not narrow or replace that specification' in plan)
check('isolated-review-interpreter', sys.flags.isolated, 1)
check('no-site-review-interpreter', sys.flags.no_site, 1)
check('no-bytecode-review-interpreter', sys.dont_write_bytecode)

delivery_ref = {'path': BASE + '/stage-recovery-delivery-receipt.json', 'bytes': 14032, 'sha256': '0fffafef35ae48e4d6c8ddf72a3870205bc45c0b00cfe2b8faf20f6229bad80c'}
pinned(delivery_ref, 'exact-delivery-receipt')
delivery = load(delivery_ref['path'])
check('delivered-head', delivery['head'], HEAD)
check('delivered-tree', delivery['tree'], TREE)
check('delivered-parent', delivery['parent'], PARENT)
for key, value in {'pushed': True, 'force': False, 'indexEmpty': True, 'allExistingHoldsUntouched': True, 'runtimeCompilerNativeUICaptureProcessInventoryHeldProbesStarted': False, 'releaseTagOrGAPromotion': False}.items():
    check('delivery:' + key, delivery[key], value)
seal_ref = {'path': BASE + '/review/delivery-actual/seal.json', 'bytes': 908, 'sha256': '31193aa02808535f2e9e62b9e7d403d25ad46d772eedb5c31f80981f6d073b61'}
pinned(seal_ref, 'independent-delivery-seal')
prior_seal = load(seal_ref['path'])
for index, item in enumerate(prior_seal['rows']):
    pinned(item, 'independent-delivery-seal-member-' + str(index))
check('independent-delivery-review-clean', prior_seal['checksFailed'], 0)
check('independent-delivery-no-later-authority', prior_seal['laterAuthorityGranted'], False)

selection = load(SELECTION)
pinned(delivery['selection'], 'delivery-selection')
manifest = load(delivery['manifest']['path'])
pinned(delivery['manifest'], '123-file-frozen-manifest')
check('selected-count', len(manifest['members']), 123)
check('selected-payload-bytes', sum(x['bytes'] for x in manifest['members']), 4897969)
selected_objects = {}
for index, item in enumerate(manifest['members']):
    data = read(item['path'])
    pinned(item, 'selected-file-' + str(index))
    check('selected-mode-' + str(index), source_mode(item['path']), item['mode'])
    selected_objects[item['path']] = {'oid': blob(data), 'mode': source_mode(item['path'])}
check('selected-paths-unique', len(selected_objects), 123)
check('selected-manifest-vs-selection', [x for x in manifest['members'] if x['path'] != SELECTION], selection['selectedRows'])
check('selection-self-included', SELECTION in selected_objects)
committed = load(delivery['committedChangedObjects']['path'])
pinned(delivery['committedChangedObjects'], 'committed-selected-objects')
check('123-current-bytes-and-modes-vs-delivered-objects', selected_objects, committed)
inputs = load(BASE + '/inputs.json')
expected_objects = {x['path']: {'oid': x['oid'], 'mode': x['mode']} for x in inputs['expectedObjects']}
check('123-current-objects-vs-frozen-expectation', selected_objects, expected_objects)

preservation = load(delivery['preservationBefore']['path'])
pinned(delivery['preservationBefore'], 'preservation-before')
check('protected-files-count', len(preservation['protectedSnapshots']), 2)
for item in preservation['protectedSnapshots']:
    pinned(item, 'protected-current:' + item['path'])
    meta = (ROOT / item['path']).lstat()
    check('protected-mode:' + item['path'], stat.S_IMODE(meta.st_mode), item['mode'])
    check('protected-type:' + item['path'], stat.S_IFMT(meta.st_mode), item['type'])
wrangler = preservation['wrangler']
meta = (ROOT / wrangler['path']).lstat()
for key, actual in [('mode', stat.S_IMODE(meta.st_mode)), ('type', stat.S_IFMT(meta.st_mode)), ('inode', meta.st_ino), ('device', meta.st_dev)]:
    check('wrangler-' + key, actual, wrangler[key])
absent = ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex'
check('artifacts-store-ex-absent', not absent.exists() and not absent.is_symlink())
check('selection-preserves-old-holds', selection['limits']['allExistingLocalRemoteHoldsUnchanged'])
for key in ['localCompilerProductRuntime', 'heldProcessInventoryOrProbes', 'nativeUICapture', 'phones', 'publishedSDK', 'releaseTags', 'GA', 'heldV5EquivalentStartup', 'canonicalAndroidPromotion']:
    check('selection-no-new-authority:' + key, selection['limits'][key], False)
check('previous-axis-allowance-remains-consumed', selection['previousAxisHost']['remaining'], 0)
check('previous-axis-retry-remains-zero', selection['previousAxisHost']['retries'], 0)
pinned(selection['previousAxisHost']['outcome'], 'previous-failed-axis-outcome-retained')

template_path = 'verification/android-axis-refusal-host-admission-binding-correction/root-selection.template.json'
before = load(template_path)
check('template-false-selected', before['selected'], False)
check('template-false-dispatch', before['dispatch_authorized'], False)
check('template-unbound-revision', before['source_revision'], None)
check('template-unbound-run', before['run_id'], None)
after = dict(before, selected=True, dispatch_authorized=True, source_revision=HEAD)
check('only-three-selection-deltas', sorted(k for k in before if before[k] != after[k]), ['dispatch_authorized', 'selected', 'source_revision'])
wire = canonical(after)
check('wire-bytes', len(wire.encode()), 1563)
check('wire-sha256', hashlib.sha256(wire.encode()).hexdigest(), 'df6d057991d4492ef53129f2b9eb5fdb0928a3192eae0bb27c3309be5d2759a6')
input_ref = {'path': BASE + '/manual-axis-stage-recovery-input.json', 'bytes': 1741, 'sha256': '911d6329434da81559f20320895386b6ed006bc60936c7f921334b416ba80b21'}
pinned(input_ref, 'actual-input')
check('input-object-exact-template-delta', load(input_ref['path']), after)
check('no-nonce-in-input', all('nonce' not in k.lower() for k in after))
check('no-run-id-transported', after['run_id'], None)
once_ref = {'path': BASE + '/manual-axis-stage-recovery-once.json', 'bytes': 2779, 'sha256': '752b92fd2f9139292fc9bf38a0263ab78f85ed9e091a28c24a89ed9370c0a0e7'}
submitted_ref = {'path': BASE + '/manual-axis-stage-recovery-submitted.json', 'bytes': 2593, 'sha256': 'eb559521883e1f47c415ac4cb92ce92dc78566a295e54024ef988596583f2eec'}
pinned(once_ref, 'one-shot-reservation')
pinned(submitted_ref, 'submitted-record')
once = load(once_ref['path'])
submitted = load(submitted_ref['path'])
check('once-consumed-before-submit', once['allowanceConsumedBeforeSubmit'])
for key, value in {'dispatchLimit': 1, 'runAttemptLimit': 1, 'oldAllowancesReused': 0, 'retryRerunFallbackAllowed': False, 'unknownOutcomeMustNeverBeRetried': True, 'dispatchNonce': None}.items():
    check('reservation:' + key, once[key], value)
check('submitted-binds-exact-reservation', submitted['reservation'], once_ref)
check('submitted-retry-refused', submitted['retryAllowed'], False)
check('submitted-binding-pending', submitted['remoteRunBindingPending'])

total_output = 0
last_terminal = None
phase_evidence = []
summary_fields = ['exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF', 'sensitiveOutputRejected']
for phase, count, authority_bytes, authority_sha, summary_name, outer_id in PHASES:
    prefix = BASE + '/' + phase + '-'
    authority_path = BASE + '/authority-snapshot-' + phase + '.json'
    pinned({'path': authority_path, 'bytes': authority_bytes, 'sha256': authority_sha}, phase + ':immutable-authority')
    authority = load(authority_path)
    for key, value in {'authorized': True, 'phase': phase, 'phaseLimit': 1, 'repository': 'snowdamiz/mixer', 'branch': 'main', 'selectedPathsIncludingSelf': 123, 'stageLimit': 0, 'commitLimit': 0, 'nonforcePushLimit': 0, 'retryRerunFallbackAllowed': False, 'originalAttemptReplayAllowed': False, 'allExistingHoldsUntouched': True}.items():
        check(phase + ':authority:' + key, authority[key], value)
    check(phase + ':accepted-delivery', authority['acceptedDelivery'], delivery_ref)
    limit = 1 if phase == 'stage-recovery-dispatch-axis' else 0
    check(phase + ':manual-total-ceiling', authority['manualWorkflowDispatchLimit'], limit)
    check(phase + ':manual-per-key-ceiling', authority['manualWorkflowDispatchLimits'], {'axis': limit, 'package': 0})
    check(phase + ':exact-one-manifest-approval', list(authority['argvApprovals']), [phase])
    argv_ref = authority['argvApprovals'][phase]
    pinned(argv_ref, phase + ':exact-argv-manifest')
    argv_manifest = load(argv_ref['path'])
    check(phase + ':manifest-phase', argv_manifest['phase'], phase)
    check(phase + ':manifest-count', argv_manifest['session']['count'], count)
    check(phase + ':manifest-prefix', argv_manifest['session']['prefix'], phase + '-')
    check(phase + ':manifest-command-count', len(argv_manifest['commands']), count)
    check(phase + ':typed-bindings', sorted(argv_manifest['typedBindings']), ['AXIS_DISPATCH_JSON', 'DELIVERED_SHA'] if limit else ['DELIVERED_SHA'])
    check(phase + ':interpreter-flags', argv_manifest['interpreter']['flags'], ['-I', '-B', '-S'])
    check(phase + ':wrapper-binding', argv_manifest['interpreter']['wrapper'], authority['helper']['path'])
    for key in ['helper', 'inspectionSource', 'sourceReview']:
        pinned(authority[key], phase + ':' + key)
    for index, source in enumerate(authority['driverSources']):
        pinned(source, phase + ':driver-source-' + str(index))
    for group in ['acceptedPreflight', 'acceptedInspection']:
        pinned(authority[group]['seal'], phase + ':' + group + ':seal')
        for index, source in enumerate(authority[group]['rows']):
            pinned(source, phase + ':' + group + ':' + str(index))
    check(phase + ':manifest-selection', argv_manifest['selection'], authority['selection'])
    pinned(authority['selection'], phase + ':frozen-selection')
    summary = load(BASE + '/' + summary_name)
    check(phase + ':summary-authority', summary['authoritySnapshot'], {'path': authority_path, 'bytes': authority_bytes, 'sha256': authority_sha})
    check(phase + ':summary-manifest', summary.get('manifest', summary.get('argvManifest')), argv_ref)
    check(phase + ':summary-no-runtime-acceptance', summary['runtimeResultsAccepted'], False)
    check(phase + ':summary-closed', summary['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'])
    check(phase + ':summary-command-count', len(summary['commands']), count)
    check(phase + ':exact-record-file-set', sorted(p.name for p in (ROOT / BASE).glob(phase + '-*.command.json')), sorted(phase + '-' + x['name'] + '.command.json' for x in argv_manifest['commands']))
    phase_aggregate = 0
    for ordinal, expected in enumerate(argv_manifest['commands'], start=1):
        label = phase + '-' + expected['name']
        stem = BASE + '/' + label
        records = {key: load(stem + '.' + key + '.json') for key in ['plan', 'started', 'admission', 'command']}
        plan_record, started, admission, command = (records[k] for k in ['plan', 'started', 'admission', 'command'])
        expanded = [x.replace('{DELIVERED_SHA}', HEAD).replace('{AXIS_DISPATCH_JSON}', wire) for x in expected['argv']]
        effective = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *expanded[1:]] if expanded[0] == 'git' else expanded
        manifest_effective = [x.replace('{DELIVERED_SHA}', HEAD).replace('{AXIS_DISPATCH_JSON}', wire) for x in expected['effectiveArgv']]
        check(label + ':effective-prefix', manifest_effective, effective)
        for key in ['plan', 'admission', 'command']:
            check(label + ':exact-effective-argv:' + key, records[key]['argv'], effective)
        check(label + ':ordinal', plan_record['ordinal'], ordinal)
        check(label + ':session-limit', plan_record['sessionCommandLimit'], count)
        check(label + ':cwd', plan_record['cwd'], str(ROOT))
        for key in ['freshSessionRequired', 'targetReleaseAfterPersistedAdmissionOnly', 'isolatedNoSiteBytecodeDisabled']:
            check(label + ':plan:' + key, plan_record[key])
        sigchld = plan_record['nativeSIGCHLD']
        check(label + ':sigchld-read-only', sigchld['readOnly'])
        check(label + ':sigchld-no-auto-reap', sigchld['flags'] & sigchld['SA_NOCLDWAIT'], 0)
        check(label + ':started-gate-closed', started['targetReleased'], False)
        check(label + ':persisted-admission-before-release', admission['targetReleasedOnlyAfterPersistedAdmission'])
        pid = command['identity']['pid']
        check(label + ':positive-PID', type(pid) is int and pid > 1)
        check(label + ':command-PID-PGID-SID', command['identity'], {'pid': pid, 'pgid': pid, 'sid': pid})
        check(label + ':admission-PID-PGID-SID', admission['identity'], command['identity'])
        for key in ['parentObservedPGID', 'parentObservedSID']:
            check(label + ':' + key, admission[key], pid)
        check(label + ':started-PID', started['ownedPID'], pid)
        for key in ['ownedPID', 'ownedPGID', 'rawWaitPID']:
            check(label + ':' + key, command[key], pid)
        for key in ['admitted', 'directChildReaped', 'ownedGroupAbsent', 'wnowaitSupported', 'terminalObservedWithoutReap', 'signalAuthorityRetired', 'finalReapAttempted', 'implicitPopenReapingDisabled', 'unresolvedChildRetainedUntilIsolatedDriverExit', 'interpreterExitIsNotCustodyEvidence', 'noSignalAfterFinalReapOrLostAuthority', 'stdoutEOF', 'stderrEOF', 'separateOutputPipes']:
            check(label + ':' + key, command[key])
        for key in ['stopReason', 'failure', 'signalAuthorityLost']:
            check(label + ':' + key, command[key], None)
        check(label + ':terminal-observation', command['terminalObservation'], [1, 0])
        check(label + ':raw-kernel-wait-status', command['rawWaitStatus'], 0)
        check(label + ':raw-status-normal-zero-exit', (command['rawWaitStatus'] & 0x7f) == 0 and ((command['rawWaitStatus'] >> 8) & 0xff) == 0)
        check(label + ':exit', command['exit'], 0)
        check(label + ':one-post-reap-probe', command['postReapAbsenceProbeCount'], 1)
        check(label + ':no-success-or-EPERM-held-case', command['postReapProbeSuccessOrEPERMHeldWithoutRetry'], False)
        check(label + ':zero-signals', command['signals'], [])
        check(label + ':authority', command['authoritySHA256'], authority_sha)
        check(label + ':no-sensitive-rejection', command['sensitiveOutputRejected'], False)
        times = [timestamp(records[k]['at']) for k in ['plan', 'started', 'admission', 'command']]
        check(label + ':plan-start-admit-terminal-order', all(left <= right for left, right in zip(times, times[1:])))
        if last_terminal is not None:
            check(label + ':previous-command-closed-before-plan', last_terminal <= times[0])
        last_terminal = times[-1]
        output = 0
        for stream in ['stdout', 'stderr']:
            pinned(command[stream], label + ':' + stream)
            check(label + ':' + stream + ':exact-path', command[stream]['path'], stem + '.' + stream)
            check(label + ':' + stream + ':observed-bytes', command[stream + 'ObservedBytes'], command[stream]['bytes'])
            check(label + ':' + stream + ':within-cap', command[stream]['bytes'] <= plan_record['streamCapEachBytes'])
            output += command[stream]['bytes']
        total_output += output
        phase_aggregate += output
        check(label + ':cumulative-output-accounting', command['aggregateOutputBytes'], phase_aggregate)
        check(label + ':aggregate-within-cap', phase_aggregate <= plan_record['aggregateCapBytes'])
        check(label + ':summary-derived-from-command', summary['commands'][ordinal - 1], {'name': label, **{k: command[k] for k in summary_fields}})
        if expected['name'] == 'head':
            check(label + ':delivered-head-tree', read(stem + '.stdout').decode().splitlines(), [HEAD, TREE])
        if expected['name'] in ['remote-main', 'remote-predispatch']:
            check(label + ':exact-delivered-remote-main', read(stem + '.stdout').decode(), HEAD + '\trefs/heads/main\n')
        if expanded[:2] == ['gh', 'api']:
            check(label + ':exact-read-only-GET-vector', len(expanded) == 7 and expanded[3:6] == ['--hostname', 'github.com', '--jq'])
            check(label + ':no-mutation-flags', not any(x in expanded for x in ['--method', '--input', '--field', '--raw-field', '-X', '-f', '-F']))
        commands.append({'name': label, 'phase': phase, 'ordinal': ordinal, 'argv': expanded, 'effectiveArgv': effective, 'authoritySHA256': authority_sha, 'pid': pid, 'pgid': pid, 'sid': pid, 'planAt': records['plan']['at'], 'admittedAt': admission['at'], 'terminalAt': command['at'], 'rawWaitPID': command['rawWaitPID'], 'rawWaitStatus': command['rawWaitStatus'], 'onePostReapAbsenceProbe': True, 'signalAuthorityRetired': True, 'ownedGroupAbsent': True, 'separateEOF': True, 'signals': command['signals'], 'stdout': command['stdout'], 'stderr': command['stderr']})
    phase_evidence.append({'phase': phase, 'commands': count, 'authority': {'path': authority_path, 'bytes': authority_bytes, 'sha256': authority_sha}, 'manifest': argv_ref, 'summary': row(BASE + '/' + summary_name), 'outputBytesRehashed': phase_aggregate, 'outerInvocation': {'id': outer_id, 'exit': 0, 'attribution': 'Root completion message; not inferred from isolated interpreter exit'}})

check('exact-21-command-count', len(commands), 21)
check('all-owned-PIDs-distinct', len({x['pid'] for x in commands}), 21)
dispatches = [x for x in commands if x['argv'][:3] == ['gh', 'workflow', 'run']]
check('sole-submission', len(dispatches), 1)
dispatch = dispatches[0]
check('sole-submission-exact-root-selection-wire', dispatch['argv'][-1], 'root_selection=' + wire)
check('sole-submission-exact-public-fields', dispatch['argv'][8:], ['--raw-field', 'profile=axis-refusal-host-v1', '--raw-field', 'root_selection=' + wire])
check('sole-submission-no-nonce-flags', not any('nonce' in x.lower() for x in dispatch['argv']))
check('reservation-argv-hash', once['argvSHA256'], hashlib.sha256(json.dumps(dispatch['argv'], separators=(',', ':')).encode()).hexdigest())
dispatch_plan = load(BASE + '/stage-recovery-dispatch-axis-dispatch.plan.json')
check('marker-consumed-before-submission-plan', timestamp(once['at']) < timestamp(dispatch_plan['at']))
check('submitted-record-after-command-terminal', timestamp(dispatch['terminalAt']) <= timestamp(submitted['at']))
after_plan = load(BASE + '/stage-recovery-dispatch-axis-axis-after-runs.plan.json')
check('submitted-record-before-after-list', timestamp(submitted['at']) <= timestamp(after_plan['at']))
check('submit-returned-bound-URL', read(BASE + '/stage-recovery-dispatch-axis-dispatch.stdout').decode(), 'https://github.com/snowdamiz/mixer/actions/runs/40943215863\n')

workflow_observations = []
for phase, which, path, workflow_id, name in [
    ('stage-recovery-engine-ci-binding', 'engine', '.github/workflows/verify.yml', 393488255, 'Owned engine checks'),
    ('stage-recovery-axis-ci-binding', 'axis', '.github/workflows/android-axis-refusal-host.yml', 400656207, 'Isolated Android axis refusal host test'),
    ('stage-recovery-dispatch-axis', 'axis', '.github/workflows/android-axis-refusal-host.yml', 400656207, 'Isolated Android axis refusal host test'),
]:
    data = read(path)
    content = load(BASE + '/' + phase + '-' + which + '-workflow-content.stdout')
    registration = load(BASE + '/' + phase + '-' + which + '-workflow-registration.stdout')
    check(phase + ':exact-workflow-content', content, {'path': path, 'sha': blob(data), 'size': len(data), 'type': 'file'})
    check(phase + ':exact-workflow-registration', registration, {'id': workflow_id, 'name': name, 'path': path, 'state': 'active'})
    check(phase + ':workflow-source-name', data.decode().splitlines()[0], 'name: ' + name)
    source_sha = selection['ordinaryHost']['workflowSHA256'] if which == 'engine' else selection['manualHosts']['axis']['workflowSHA256']
    check(phase + ':workflow-source-sha256', hashlib.sha256(data).hexdigest(), source_sha)
    workflow_observations.append({'phase': phase, 'source': row(path), 'content': content, 'registration': registration})
later_registration = load(BASE + '/stage-recovery-bind-axis-run-axis-workflow-registration.stdout')
check('later-axis-registration-exact', later_registration, {'id': 400656207, 'name': 'Isolated Android axis refusal host test', 'path': '.github/workflows/android-axis-refusal-host.yml', 'state': 'active'})
engine = load(BASE + '/stage-recovery-engine-ci-binding-engine-run.stdout')
expected_engine = {'conclusion': None, 'event': 'push', 'head_sha': HEAD, 'html_url': 'https://github.com/snowdamiz/mixer/actions/runs/40942282975', 'id': 40942282975, 'name': 'Owned engine checks', 'path': '.github/workflows/verify.yml', 'run_attempt': 1, 'status': 'in_progress', 'workflow_id': 393488255}
check('ordinary-engine-exact-push-run-observation', engine, [expected_engine])
for path in ['stage-recovery-axis-ci-binding-axis-before-runs.stdout', 'stage-recovery-dispatch-axis-axis-before-runs.stdout', 'stage-recovery-dispatch-axis-axis-after-runs.stdout']:
    check('empty-run-list:' + path, load(BASE + '/' + path), [])
pending = load(BASE + '/manual-axis-stage-recovery-visibility-pending.json')
for key, value in {'state': 'submitted-visibility-pending', 'allowanceConsumed': True, 'retryAllowed': False, 'laterBindingReadOnlyAndSeparatelyAuthorized': True, 'runtimeResultsAccepted': False}.items():
    check('visibility-race:' + key, pending[key], value)
check('visibility-pending-reservation', pending['reservation'], once_ref)
check('visibility-pending-submitted', pending['submitted'], submitted_ref)
later = load(BASE + '/stage-recovery-bind-axis-run-axis-runs.stdout')
expected_axis = {'conclusion': 'success', 'event': 'workflow_dispatch', 'head_sha': HEAD, 'html_url': 'https://github.com/snowdamiz/mixer/actions/runs/40943215863', 'id': 40943215863, 'name': 'Isolated Android axis refusal host test', 'path': '.github/workflows/android-axis-refusal-host.yml', 'run_attempt': 1, 'status': 'completed', 'workflow_id': 400656207}
check('later-list-binds-only-exact-axis-run-attempt', later, [expected_axis])
binding = load(BASE + '/manual-axis-stage-recovery-run-binding.json')
check('later-receipt-exact-run-observation', binding['manual'], expected_axis)
for key, value in {'head': HEAD, 'tree': TREE, 'dispatches': 1, 'retries': 0, 'attempt': 1, 'observedInLaterReadOnlyPhase': True, 'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False, 'allExistingHoldsUntouched': True}.items():
    check('later-binding:' + key, binding[key], value)
check('later-binding-input', binding['input'], input_ref)
check('later-binding-reservation', binding['reservation'], once_ref)
check('later-binding-submitted', binding['submitted'], submitted_ref)

# Do not enumerate, compare, or claim preservation of the global untracked set.
# Root reported a separate actual-artifact evidence directory created post-delivery.
limitations = [
    'This accepts 21 retained local Git/gh command observations and source/run bindings only. It grants no dispatch, replay, retry, workflow installation, publication or GA authority.',
    'Kernel wait, group absence, PID/PGID/SID, signal retirement and separate pipe EOF are independently checked against retained command records; no live process probes or signals were performed by this review.',
    'The four outer invocation exit-zero observations are attributed to the root completion message. Child closure is independently supported by retained raw wait records, not interpreter exit.',
    'Engine run 40942282975 was in_progress with null conclusion in these reads. Axis run 40943215863 attempt 1 later has completed/success metadata. Neither observation accepts jobs, artifacts, 19 tests or runtime behavior.',
    'The immediate after-list remained empty after the sole submission. Visibility-pending is retained; the later four reads bind the run without renewing the consumed allowance.',
    'All 123 frozen selected files and modes, two protected files and modes, .wrangler identity and artifacts/store.ex absence are checked at review time. No recursive untracked contents, global untracked-set equality, complete tracked-file byte inventory or current index cleanliness is inferred.',
    'Root reports a new untracked actual-artifact evidence directory created after delivery. These read-only phases do not imply that the global untracked set remained unchanged.',
    'Native/UI/capture, disconnected phones, held processes/custody, canonical Android/source-pair integration, immutable published FieldLog packages, release and GA holds remain. No native or artifact/runtime qualification is made here.',
]
report = {
    'schema': 1,
    'decision': 'accept-exact-21-command-postdelivery-binding-observation' if not failures else 'reject-unresolved-postdelivery-data-findings',
    'reviewedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'head': HEAD, 'tree': TREE, 'parent': PARENT,
    'scope': 'Independent bounded filesystem-data inspection only; no helper/subject import or execution, Git/gh, compiler, network, process probe/signal, native or UI action.',
    'checksPassed': sum(x['passed'] for x in checks), 'checksFailed': len(failures), 'findings': failures,
    'commandsReviewed': len(commands), 'streamsRehashed': 2 * len(commands), 'outputBytesRehashed': total_output,
    'phases': phase_evidence, 'commandEvidence': commands,
    'selectedFilesRehashed': 123, 'selectedPayloadBytes': 4897969,
    'delivery': delivery_ref, 'independentDeliverySeal': seal_ref,
    'workflowBindings': workflow_observations,
    'engineMetadataOnly': expected_engine, 'axisMetadataOnly': expected_axis,
    'dispatchWire': {'bytes': len(wire.encode()), 'sha256': hashlib.sha256(wire.encode()).hexdigest(), 'input': input_ref, 'reservation': once_ref, 'submitted': submitted_ref, 'transportedNonce': False, 'remainingDispatches': 0, 'remainingRetries': 0},
    'limitations': limitations,
    'execution': {'command': 'python3 -I -B -S ' + BASE + '/review/postdelivery-actual/audit.py', 'cwd': str(ROOT), 'pythonExecutable': sys.executable, 'pythonVersion': sys.version, 'isolated': sys.flags.isolated, 'noSite': sys.flags.no_site, 'dontWriteBytecode': sys.dont_write_bytecode, 'subjectExecution': False, 'liveAuthorityRead': False, 'laterAuthorityGranted': False},
}
OUT.mkdir(parents=True, exist_ok=True)
write('actual-review.json', report)
write('read-set.json', {'schema': 1, 'rows': [reads[k] for k in sorted(reads)]})
write('checks.json', {'schema': 1, 'checks': checks})
(OUT / 'REVIEW.md').write_text(
    'Accepted the exact 21 retained post-delivery commands at '
    '`2c751cbbc300efc9aa766b5d4add648610ca0341` / '
    '`f2df6833ee8e9ce85306210b63dc35d45747fa0d`: 5 Engine-binding, '
    '5 axis-binding, 7 dispatch and 4 later-binding commands. '
    f'{report["checksPassed"]:,} independent data checks pass with '
    f'{report["checksFailed"]} findings. All 42 streams, totaling 2,207 bytes, '
    'were rehashed. Exact argv, immutable authority, order, admission, '
    'PID/PGID/SID, raw wait, group absence, separate EOF, one post-reap '
    'probe, retired signal authority and zero signals match the retained records.\n\n'
    'Engine 40942282975 is bound to verify.yml and the delivered push; its '
    'observed state was in_progress. Axis workflow 400656207 matches its frozen '
    'bytes. Initial lists and the immediate post-submit list are empty. The one '
    'marker precedes the sole submission; the 1,563-byte selection wire has only '
    'the authorized three template changes and transports no nonce. Visibility '
    'pending remains preserved. The later four reads bind only run 40943215863, '
    'attempt 1, completed/success, at the same head. The allowance remains consumed.\n\n'
    'All 123 selected byte/mode identities, two protected files, .wrangler '
    'identity and absent artifacts/store.ex remain preserved at review time. '
    'No equality of the global untracked set is claimed: root reports a separate '
    'actual-artifact directory created after delivery. No subject helper, Git/gh, '
    'network, compiler, process probe/signal or native/UI action ran in this review. '
    'No artifact, 19-test, runtime, native, release or GA acceptance, and no new '
    'dispatch authority, is granted. Full retained references and limits are in '
    'actual-review.json, read-set.json and seal.json.\n'
)
seal_rows = []
for name in ['audit.py', 'actual-review.json', 'read-set.json', 'checks.json', 'REVIEW.md']:
    target = OUT / name
    data = target.read_bytes()
    seal_rows.append({'path': str(target.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
write('seal.json', {'schema': 1, 'decision': report['decision'], 'checksPassed': report['checksPassed'], 'checksFailed': report['checksFailed'], 'rows': seal_rows, 'subjectExecution': False, 'laterAuthorityGranted': False})
print(json.dumps({k: report[k] for k in ['decision', 'checksPassed', 'checksFailed', 'findings', 'commandsReviewed', 'streamsRehashed', 'outputBytesRehashed']}))
if failures:
    sys.exit(1)
