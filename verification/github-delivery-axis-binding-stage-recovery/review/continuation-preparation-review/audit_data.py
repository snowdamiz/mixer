"""Bounded data audit only. Never import or execute prepared subjects/helpers."""
from pathlib import Path
import hashlib
import json
import stat
import difflib
import sys

ROOT = Path(__file__).resolve().parents[4]
REC = 'verification/github-delivery-axis-binding-stage-recovery'
OLD = 'verification/github-delivery-axis-binding-followup'
PREP = REC + '/local/continuation-preparation'
OUT = ROOT / (REC + '/review/continuation-preparation-review')
GUARD = b'raise SystemExit("UNRUN source-only template; root must independently review and materialize exact final bytes before any authority or execution")\n'
READS = {}
CHECKS = []


def read(path):
    p = ROOT / path
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink() and s.st_size < 5000000, path
    b = p.read_bytes()
    row = {'path': path, 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    if path in READS:
        assert READS[path] == row, ('Changed during review', path)
    READS[path] = row
    return b


def data(path):
    return json.loads(read(path))


def row(path):
    read(path)
    return READS[path]


def pinned(expected):
    assert row(expected['path']) == expected, expected['path']


def check(name, condition):
    assert condition, name
    CHECKS.append(name)


def save(name, value):
    target = OUT / name
    target.write_text(json.dumps(value, indent=2) + '\n')


selection_path = 'verification/android-axis-binding-selection-2026-10-29/selection.json'
selection_row = {'path': selection_path, 'bytes': 36961, 'sha256': '6dda8a7e90a3be9b93cd3683f9038c6767896dcf986bcee5beb47472ff7299fd'}
pinned(selection_row)
selection = data(selection_path)
baseline = {'head': '2cea1013151ccc38bb635fb4755793cd25a0bd1b', 'tree': '830e859979d2ea95335d8cb8ea28ac8caaa0614b'}
check('exact-baseline', selection['baseline'] == {'revision': baseline['head'], 'tree': baseline['tree']})
selected_rows = selection['selectedRows'] + [{**selection_row, 'mode': '100644'}]
check('123-selected-members-4897969-bytes', len(selected_rows) == len({x['path'] for x in selected_rows}) == 123 and sum(x['bytes'] for x in selected_rows) == 4897969)
objects = []
for expected in sorted(selected_rows, key=lambda x: x['path']):
    pinned({k: expected[k] for k in ('path', 'bytes', 'sha256')})
    payload = read(expected['path'])
    mode = stat.S_IMODE((ROOT / expected['path']).stat().st_mode)
    assert expected['mode'] == '100644' and not mode & 0o111
    objects.append({'path': expected['path'], 'oid': hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest(), 'mode': '100644'})
object_digest = hashlib.sha256(json.dumps(objects, separators=(',', ':')).encode()).hexdigest()
check('all-selected-object-digest', object_digest == '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd')
selected_paths = sorted(x['path'] for x in objects)

ready_row = {'path': PREP + '/source-ready.json', 'bytes': 18438, 'sha256': '0ffa1243be5ae017ffc6104e55ce7c55cfd90a558fd5e06f081307852961a567'}
pinned(ready_row)
ready = data(ready_row['path'])
for expected in ready['inventory']:
    pinned(expected)
check('frozen-20-member-inventory-plus-source-ready', len(ready['inventory']) == 20 and ready['selection'] == selection_row and ready['baseline'] == baseline and ready['actualAuthorityCreated'] is False)
review = data(PREP + '/continuation-source-review.template.json')
check('ready-source-and-argv-contract', ready['materializedDriverSources'] == review['driverSources'] and ready['argvApprovals'] == review['argvApprovals'])
check('review-template-does-not-accept-or-authorize', review['decision'] == 'pending-independent-root-review-not-an-acceptance' and review['actualAuthorityCreated'] is False and review['commandsExecuted'] == 0)
expected_names = ['selection_common_axis_binding.py', 'deliver_axis_binding.py', 'bind_engine_ci_axis_binding.py', 'bind_axis_ci_axis_binding.py', 'dispatch_axis_binding.py', 'bind_axis_run_axis_binding.py']
check('six-ordered-driver-sources', [x['path'] for x in review['driverSources']] == [REC + '/' + x for x in expected_names])
original_packet = data(OLD + '/materialized-source-ready.json')
pinned({'path': OLD + '/materialized-source-ready.json', 'bytes': 12738, 'sha256': '3a30bbd24d332a0da4410d73353f47ccf96495eb86b83f5f843240d40f1d543a'})
base_rows = original_packet['postPreflight']['driverSources']
base_sources = {x['path'].rsplit('/', 1)[-1]: x for x in base_rows}
final_bodies = {}
diffs = []
for name, expected in zip(expected_names, review['driverSources']):
    raw = read(PREP + '/' + name + '.template')
    lines = raw.splitlines(keepends=True)
    check(name + '-one-exact-inert-guard', lines[1] == GUARD and raw.count(GUARD) == 1)
    final = b''.join(lines[:1] + lines[2:])
    check(name + '-exact-reconstructed-final-row', expected == {'path': REC + '/' + name, 'bytes': len(final), 'sha256': hashlib.sha256(final).hexdigest()})
    check(name + '-no-unresolved-preparation-placeholder', b'${' not in final)
    pinned(base_sources[name])
    before = read(base_sources[name]['path'])
    diffs.extend(difflib.unified_diff(before.decode().splitlines(True), final.decode().splitlines(True), fromfile=base_sources[name]['path'], tofile=expected['path']))
    final_bodies[name] = final

pinned(review['helper'])
check('unchanged-copied-owned-helper', read(REC + '/owned.py') == read(OLD + '/owned.py') and review['helper']['sha256'] == '34f1991509d7b156f00b5cc50fcd82ebae81fb414da904c19dcdca70c3eeb987')
pinned(review['inspectionSource'])
check('exact-inspection-source', review['inspectionSource'] == {'path': REC + '/inspect_stage_recovery.py', 'bytes': 18195, 'sha256': 'f5bdfa9131eaf1d45c857b6d056153b2fa01ee1c0016e2ede68cc2c8b12bcac8'})

phase_old = {
    'stage-recovery-delivery': 'argv-delivery-axis-binding.json',
    'stage-recovery-engine-ci-binding': 'argv-engine-ci-binding-axis-binding.json',
    'stage-recovery-axis-ci-binding': 'argv-axis-ci-binding-axis-binding.json',
    'stage-recovery-dispatch-axis': 'argv-dispatch-axis-binding.json',
    'stage-recovery-bind-axis-run': 'argv-bind-axis-run-axis-binding.json',
}
expected_counts = [23, 5, 5, 7, 4]
expected_seconds = [240, 180, 180, 210, 120]
old_preflight = data(OLD + '/preflight-followup-root-review.json')
preflight_binding = {'seal': row(OLD + '/preflight-followup-root-review.json'), 'rows': [old_preflight[x] for x in ('receipt', 'preservationSnapshotLocalOnly', 'manifest', 'authority', 'argv')]}
for r in [preflight_binding['seal'], *preflight_binding['rows']]:
    pinned(r)
check('immutable-original-preflight-binding', preflight_binding['seal']['sha256'] == '751059417bbde1d7e83b0b81e370ae018338e059d6c4455bec34915ecfed55f0' and len(preflight_binding['rows']) == 5)
phase_reports = []
for (phase, old_name), count, seconds in zip(phase_old.items(), expected_counts, expected_seconds):
    mpath = PREP + '/argv-' + phase + '.json'
    m = data(mpath)
    old = data(OLD + '/' + old_name)
    expected_manifest_row = {**row(mpath), 'path': REC + '/argv-' + phase + '.json'}
    check(phase + '-exact-manifest-row', review['argvApprovals'][phase] == expected_manifest_row)
    check(phase + '-bounded-phase-session', m['phase'] == phase and m['session'] == {'seconds': seconds, 'count': count, 'prefix': phase + '-'} and len(m['commands']) == count)
    check(phase + '-selection-helper', m['selection'] == selection_row and m['helper'] == {**selection['deliveryHelper'], 'path': review['helper']['path']})
    names = [c['name'] for c in m['commands']]
    check(phase + '-unique-command-names', len(set(names)) == len(names))
    expected_commands = []
    for command in old['commands']:
        c = dict(command)
        if phase == 'stage-recovery-delivery' and c['name'] == 'index-before':
            c['argv'] = ['git', 'diff', '--cached', '--raw', '--no-abbrev', '--no-renames', '-z']
        if phase == 'stage-recovery-delivery' and c['name'] == 'stage':
            c['argv'] = ['git', 'add', '--force', '--pathspec-from-file=' + str(ROOT / REC / 'paths-stage-recovery.nul'), '--pathspec-file-nul']
        c['effectiveArgv'] = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *c['argv'][1:]] if c['argv'][0] == 'git' else c['argv']
        expected_commands.append(c)
        if phase == 'stage-recovery-delivery' and c['name'] == 'remote-postpush':
            new = dict(next(x for x in old['commands'] if x['name'] == 'push-url-prepush'))
            new['name'] = 'push-url-postpush'
            expected_commands.append(new)
    check(phase + '-commands-exact-original-with-only-approved-deltas', m['commands'] == expected_commands)
    for c in m['commands']:
        if c['name'] in ('index-selected', 'authored-check'):
            assert c['argv'][c['argv'].index('--') + 1:] == selected_paths
        if c['argv'][:2] == ['gh', 'api']:
            assert len(c['argv']) == 7 and c['argv'][3:6] == ['--hostname', 'github.com', '--jq']
            assert c['argv'][2].startswith('repos/snowdamiz/mixer/')
    a = data(PREP + '/authority-' + phase + '.template.json')
    delivery, dispatch = phase == 'stage-recovery-delivery', phase == 'stage-recovery-dispatch-axis'
    check(phase + '-authority-inert-and-exact-limits', a['authorized'] is False and a['phase'] == phase and a['phaseLimit'] == 1 and a['stageLimit'] == a['commitLimit'] == a['nonforcePushLimit'] == int(delivery) and a['manualWorkflowDispatchLimit'] == int(dispatch) and a['manualWorkflowDispatchLimits'] == {'axis': int(dispatch), 'package': 0})
    check(phase + '-no-replay', a['retryRerunFallbackAllowed'] is False and a['originalAttemptReplayAllowed'] is False)
    check(phase + '-exact-source-and-argv', a['driverSources'] == review['driverSources'] and a['helper'] == review['helper'] and a['inspectionSource'] == review['inspectionSource'] and a['argvApprovals'] == {phase: expected_manifest_row})
    check(phase + '-original-preflight', a['acceptedPreflight'] == preflight_binding)
    check(phase + '-dynamic-actual-delivery-only', a['acceptedDelivery'] == (None if delivery else {'path': REC + '/stage-recovery-delivery-receipt.json', 'bytes': None, 'sha256': None}))
    check(phase + '-exact-future-review-path', a['sourceReview'] == {'path': REC + '/review/continuation-source-review.json', 'bytes': None, 'sha256': None})
    check(phase + '-exact-inspection-order', a['acceptedInspection'] == {'seal': {'path': REC + '/inspection-root-review.json', 'bytes': None, 'sha256': None}, 'rows': [{'path': REC + '/' + name, 'bytes': None, 'sha256': None} for name in ('inspection-receipt.json', 'inspection-data.json', 'authority-exact-inspection.json')]})
    phase_reports.append({'phase': phase, 'commands': count, 'seconds': seconds, 'argv': expected_manifest_row, 'authorityTemplate': row(PREP + '/authority-' + phase + '.template.json')})

inspection_seal = data(REC + '/inspection-root-review.json')
pinned({'path': REC + '/inspection-root-review.json', 'bytes': 8105, 'sha256': 'e4f7b2def4466c92ff9b5f312059e6a054a43f7749e6c708049052d4313bdeee'})
inspection_expected = [
    {'path': REC + '/inspection-receipt.json', 'bytes': 5232, 'sha256': '44d916387c020d0d8fde26727d2d375cded35e7112d4b49870dfeb852e67dd48'},
    {'path': REC + '/inspection-data.json', 'bytes': 371597, 'sha256': '18b5301118e0d79d6221d5ca410a7ae4c029a2f7965eff2a88959cee4c4ece5c'},
    {'path': REC + '/authority-exact-inspection.json', 'bytes': 2569, 'sha256': '3501509455e9d92d8694eded31788c895032236b6ce969bb0809929132e72ba8'},
]
for expected in inspection_expected:
    pinned(expected)
check('root-inspection-exact-evidence-order', [inspection_seal[x] for x in ('receipt', 'data', 'authority')] == inspection_expected)
check('root-inspection-exact-decision-and-no-continuation', inspection_seal['decision'] == 'accept-exact-ten-read-stage-recovery-inspection-result' and inspection_seal['continuationAuthorized'] is False and inspection_seal['pendingChangedPaths'] == 66 and inspection_seal['remainingSourceIndexPaths'] == 57 and inspection_seal['unrelatedStagedPaths'] == 0 and inspection_seal['stageCommitPushDispatchPerformed'] is False)
pinned(inspection_seal['independentActualReview'])
inspected = data(REC + '/inspection-receipt.json')
inspection_argv = data(REC + '/argv-inspection.json')
expected_wrappers = []
for summary, command in zip(inspected['commands'], inspection_argv['commands']):
    termrow = row(REC + '/' + summary['name'] + '.command.json')
    term = data(termrow['path'])
    assert term['argv'] == command['effectiveArgv'] and term['exit'] == term['rawWaitStatus'] == 0
    assert term['rawWaitPID'] == term['ownedPID'] == term['ownedPGID']
    for flag in ('admitted', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF', 'signalAuthorityRetired'):
        assert term[flag] is True
    assert term['signals'] == [] and term['authoritySHA256'] == inspection_expected[2]['sha256']
    for stream in ('stdout', 'stderr'):
        pinned(term[stream])
    expected_wrappers.append({'name': command['name'], 'command': termrow, 'exactArgv': True, 'exit': 0, 'admitted': True, 'exactKernelReap': True, 'groupAbsent': True, 'stdoutEOF': True, 'stderrEOF': True, 'signals': 0, 'authorityRetired': True})
check('root-inspection-wrapper-contract', len(expected_wrappers) == 10 and inspection_seal['commands'] == expected_wrappers)

common = final_bodies['selection_common_axis_binding.py'].decode()
delivery = final_bodies['deliver_axis_binding.py'].decode()
check('source-fixed-final-review-path', "assert review_row['path'] == '" + REC + "/review/continuation-source-review.json'" in common)
check('source-prior-closure-and-frozen-source-recheck', 'inspection.historical_closure(RECOVERY_INPUTS)' in common and 'inspection.frozen_sources(RECOVERY_INPUTS, ORIGINAL_PRESERVATION)' in common)
check('source-before-every-command-rechecks', "        check_driver_sources(self.authority)\n        check_sources()\n        accepted_preflight()\n        accepted_inspection()\n        expected = self.vector(name)" in common)
check('delivery-full-cache-before-forceadd', "== inspected_cached_raw, 'Full cached diff changed after accepted inspection'" in delivery)
check('delivery-distinct-once-markers', all(x in delivery for x in ('stage-recovery-stage-once.json', 'stage-recovery-commit-once.json', 'stage-recovery-push-once.json')))
check('delivery-complete-object-and-parent-diff-proof', '== OBJECT_SHA' in delivery and "assert parent == BASE" in delivery and "assert committed_objects == changed_objects" in delivery)
check('delivery-newnamespace-collapsed-status-proof', 'inspection.compare_collapsed(inspection_data' in delivery and "RECOVERY_INPUTS['newRecoveryDirectoryIdentity']" in delivery)
check('engine-and-axis-readonly-independent-binding', "'axisRegistrationRequired': False" in final_bodies['bind_engine_ci_axis_binding.py'].decode() and "'engineOutcomeRequired': False" in final_bodies['bind_axis_ci_axis_binding.py'].decode())

for path in tuple(READS):
    read(path)
save('source-diff.txt', {'unifiedDiff': ''.join(diffs)})
save('read-set.json', {'schema': 1, 'rows': [READS[k] for k in sorted(READS)]})
result = {'schema': 1, 'decision': 'accept-exact-stage-recovery-continuation-preparation-pending-final-file-readback', 'selection': selection_row, 'baseline': baseline, 'driverSources': review['driverSources'], 'helper': review['helper'], 'inspectionSource': review['inspectionSource'], 'argvApprovals': review['argvApprovals'], 'inspectionRootSeal': READS[REC + '/inspection-root-review.json'], 'acceptedInspectionRows': inspection_expected, 'acceptedPreflight': preflight_binding, 'selectedPaths': 123, 'selectedPayloadBytes': 4897969, 'selectedObjectDigestSHA256': object_digest, 'phases': phase_reports, 'dataChecks': CHECKS, 'dataCheckCount': len(CHECKS), 'readSet': {'path': str((OUT / 'read-set.json').relative_to(ROOT)), 'bytes': (OUT / 'read-set.json').stat().st_size, 'sha256': hashlib.sha256((OUT / 'read-set.json').read_bytes()).hexdigest()}, 'sourceExecution': 0, 'helperExecution': 0, 'controlExecution': 0, 'gitGhCompilerNetworkProbeSignalNativeUIActions': 0, 'actualAuthorityCreated': False, 'continuationAuthorizedByThisReview': False, 'finalFilesMaterializedByThisReviewer': False, 'limitations': ['Source and JSON data review only; Python syntax, runtime behavior and helper controls were not executed.', 'Final driver and argv files must be materialized and independently rehashed before the final runtime source review seal.', 'Every actual phase still needs root authority and actual result review; all existing holds remain.'], 'reviewInterpreter': sys.version}
save('preparation-review.json', result)
print(json.dumps({'decision': result['decision'], 'dataChecks': len(CHECKS), 'filesRead': len(READS), 'driverSources': review['driverSources']}, separators=(',', ':')))
