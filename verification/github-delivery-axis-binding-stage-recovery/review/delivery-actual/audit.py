"""Independent bounded filesystem/data review; never imports or runs subject code."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
BASE = '2cea1013151ccc38bb635fb4755793cd25a0bd1b'
BASE_TREE = '830e859979d2ea95335d8cb8ea28ac8caaa0614b'
HEAD = '2c751cbbc300efc9aa766b5d4add648610ca0341'
TREE = 'f2df6833ee8e9ce85306210b63dc35d45747fa0d'
REL = 'verification/github-delivery-axis-binding-stage-recovery/'
OUT = ROOT / REL / 'review/delivery-actual'
AUTH = 'afbe03c88abb1bd5e220b338384a33e3facae9d30f7f1f2c0c5e59556f9d5ac6'
OBJECTS = '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd'
SEL = 'verification/android-axis-binding-selection-2026-10-29/selection.json'
reads = {}
checks = []
command_details = []


def check(name, result, detail=None):
    checks.append({'name': name, 'passed': bool(result), **({'detail': detail} if detail is not None else {})})


def raw(path):
    path = str(path)
    p = ROOT / path
    assert not p.is_symlink() and p.is_file(), path
    data = p.read_bytes()
    assert len(data) <= 16 * 1024 * 1024, path
    row = {'path': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if path in reads:
        assert reads[path] == row, ('changed during review', path)
    reads[path] = row
    return data


def load(path):
    return json.loads(raw(path))


def pin(expected):
    data = raw(expected['path'])
    check('pinned-row:' + expected['path'],
          hashlib.sha256(data).hexdigest() == expected['sha256'] and
          ('bytes' not in expected or len(data) == expected['bytes']))
    return data


def when(text):
    return datetime.datetime.fromisoformat(text)


def fp(path, identity=False):
    p = ROOT / path.rstrip('/')
    try:
        s = p.lstat()
    except FileNotFoundError:
        return {'path': path, 'missing': True}
    result = {'path': path, 'mode': stat.S_IMODE(s.st_mode), 'type': stat.S_IFMT(s.st_mode)}
    if identity or stat.S_ISDIR(s.st_mode):
        result.update(inode=s.st_ino, device=s.st_dev)
    elif stat.S_ISREG(s.st_mode):
        data = raw(str(p.relative_to(ROOT)))
        result.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    elif stat.S_ISLNK(s.st_mode):
        result['target'] = os.readlink(p)
    return result


def parse_raw(data):
    parts = data.split(b'\0')
    assert parts[-1] == b'' and len(parts) % 2 == 1
    result = {}
    for meta, path in zip(parts[:-1:2], parts[1:-1:2]):
        fields = meta.decode().split()
        name = path.decode()
        assert len(fields) == 5 and fields[0].startswith(':') and name not in result
        assert fields[4] in ('A', 'M', 'D', 'T')
        assert all(len(x) == 40 and all(c in '0123456789abcdef' for c in x) for x in fields[2:4])
        result[name] = {'oldMode': fields[0][1:], 'mode': fields[1], 'oldOID': fields[2], 'oid': fields[3], 'status': fields[4]}
    return result


def raw_rows(data):
    return [{'path': p, 'gitRaw': ':' + x['oldMode'] + ' ' + x['mode'] + ' ' + x['oldOID'] + ' ' + x['oid'] + ' ' + x['status']}
            for p, x in parse_raw(data).items()]


def parse_index(data):
    parts = data.split(b'\0')
    assert parts[-1] == b''
    result = {}
    for entry in parts[:-1]:
        meta, path = entry.split(b'\t', 1)
        mode, oid, stage = meta.decode().split()
        path = path.decode()
        assert stage == '0' and path not in result
        result[path] = {'mode': mode, 'oid': oid}
    return result


def parse_status(data):
    parts = data.split(b'\0')
    assert parts[-1] == b''
    result = []
    for entry in parts[:-1]:
        text = entry.decode()
        assert len(text) > 3 and text[2] == ' ' and not any(c in text[:2] for c in 'RCU')
        result.append({'status': text[:2], 'path': text[3:]})
    return result


def closed(label, expected_argv, authority, ordinal, exit_code=0, limits=None):
    plan = load(label + '.plan.json')
    start = load(label + '.started.json')
    admission = load(label + '.admission.json')
    command = load(label + '.command.json')
    prefix = label.rsplit('/', 1)[-1]
    check(prefix + ':exact-effective-vectors', all(o['argv'] == expected_argv for o in (plan, admission, command)))
    check(prefix + ':ordinal-and-cwd', plan['ordinal'] == ordinal and plan['cwd'] == str(ROOT))
    pid = command['ownedPID']
    check(prefix + ':admitted-session-identity',
          type(pid) is int and pid > 0 and command['ownedPGID'] == pid and
          command['identity'] == admission['identity'] == dict.fromkeys(('pid', 'pgid', 'sid'), pid) and
          admission['parentObservedPGID'] == admission['parentObservedSID'] == start['ownedPID'] == pid)
    check(prefix + ':admission-before-release', start['targetReleased'] is False and
          plan['targetReleaseAfterPersistedAdmissionOnly'] is True and admission['targetReleasedOnlyAfterPersistedAdmission'] is True)
    true_keys = ['admitted', 'directChildReaped', 'ownedGroupAbsent', 'wnowaitSupported', 'terminalObservedWithoutReap',
                 'signalAuthorityRetired', 'finalReapAttempted', 'implicitPopenReapingDisabled',
                 'unresolvedChildRetainedUntilIsolatedDriverExit', 'interpreterExitIsNotCustodyEvidence',
                 'noSignalAfterFinalReapOrLostAuthority', 'stdoutEOF', 'stderrEOF', 'separateOutputPipes']
    check(prefix + ':exact-kernel-reap-group-and-eof', all(command[k] is True for k in true_keys) and
          command['rawWaitPID'] == pid and command['rawWaitStatus'] == exit_code * 256 and
          command['terminalObservation'] == [1, exit_code] and command['exit'] == exit_code)
    check(prefix + ':retired-once-probed-zero-signals', command['signalAuthorityLost'] is None and
          command['signals'] == [] and command['postReapAbsenceProbeCount'] == 1 and
          command['postReapProbeSuccessOrEPERMHeldWithoutRetry'] is False)
    check(prefix + ':authority-stop-output', command['authoritySHA256'] == authority and
          command['stopReason'] is None and command['failure'] is None and command['sensitiveOutputRejected'] is False)
    check(prefix + ':times-ordered', when(plan['at']) <= when(start['at']) <= when(admission['at']) <= when(command['at']))
    if limits:
        seconds, count = limits
        check(prefix + ':finite-resource-bounds', plan['activeSeconds'] == seconds and plan['admissionSeconds'] == 5 and
              plan['cleanupSeconds'] == admission['cleanupSeconds'] == 6 and plan['streamCapEachBytes'] == admission['streamCapEachBytes'] == 8388608 and
              plan['aggregateCapBytes'] == 33554432 and plan['sessionCommandLimit'] == count and
              plan['freshSessionRequired'] is True and plan['isolatedNoSiteBytecodeDisabled'] is True and
              plan['nativeSIGCHLD']['readOnly'] is True and plan['nativeSIGCHLD']['handler'] is None)
    streams = {}
    for stream in ['stdout', 'stderr']:
        data = pin(command[stream])
        check(prefix + ':' + stream + '-captured-byte-count', len(data) == command[stream + 'ObservedBytes'])
        streams[stream] = data
    command_details.append({'label': prefix, 'ordinal': ordinal, 'argv': expected_argv, 'pid': pid,
                            'exit': exit_code, 'rawWaitStatus': command['rawWaitStatus'],
                            'stdout': command['stdout'], 'stderr': command['stderr'],
                            'authoritySHA256': authority, 'zeroSignals': True, 'onePostReapAbsenceProbe': True})
    return plan, command, streams


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ['AGENTS.md', 'PLAN.md']:
        raw(name)
    authority = load(REL + 'authority-snapshot-stage-recovery-delivery.json')
    check('immutable-exact-delivery-authority', reads[REL + 'authority-snapshot-stage-recovery-delivery.json']['sha256'] == AUTH and
          reads[REL + 'authority-snapshot-stage-recovery-delivery.json']['bytes'] == 6408 and authority['authorized'] is True and
          authority['phase'] == 'stage-recovery-delivery' and authority['phaseLimit'] == 1 and
          authority['stageLimit'] == authority['commitLimit'] == authority['nonforcePushLimit'] == 1 and
          authority['manualWorkflowDispatchLimit'] == 0 and authority['manualWorkflowDispatchLimits'] == {'axis': 0, 'package': 0} and
          authority['retryRerunFallbackAllowed'] is False and authority['originalAttemptReplayAllowed'] is False)
    check('authority-baseline-repository-and-selection-count', authority['baseline'] == {'head': BASE, 'tree': BASE_TREE} and
          authority['repository'] == 'snowdamiz/mixer' and authority['branch'] == 'main' and authority['selectedPathsIncludingSelf'] == 123)
    for expected in authority['driverSources'] + [authority['helper'], authority['inspectionSource'], authority['sourceReview'], authority['selection']]:
        pin(expected)
    for binding in [authority['acceptedPreflight'], authority['acceptedInspection']]:
        pin(binding['seal'])
        for expected in binding['rows']:
            pin(expected)
    source = load(authority['sourceReview']['path'])
    check('accepted-final-source-review', source['decision'] == 'accept-exact-stage-recovery-continuation-source' and source['findings'] == [])
    pin({'path': REL + 'local/continuation-preparation/source-ready.json', 'bytes': 18438,
         'sha256': '0ffa1243be5ae017ffc6104e55ce7c55cfd90a558fd5e06f081307852961a567'})
    approval = authority['argvApprovals']['stage-recovery-delivery']
    pin(approval)
    manifest = load(approval['path'])
    check('manifest-exact-phase-budget', manifest['phase'] == authority['phase'] and manifest['session'] ==
          {'seconds': 240, 'count': 23, 'prefix': 'stage-recovery-delivery-'} and len(manifest['commands']) == 23 and
          manifest['stageCount'] == manifest['commitCount'] == manifest['nonforcePushCount'] == 1 and manifest['manualDispatchCount'] == 0)
    check('typed-commit-binding-only', set(manifest['typedBindings']) == {'COMMITTED_SHA'} and
          [c['name'] for c in manifest['commands'] if '{COMMITTED_SHA}' in json.dumps(c)] == ['committed-objects', 'push'])
    selection = load(SEL)
    selection_pin = authority['selection']
    rows = selection['selectedRows'] + [{**selection_pin, 'mode': '100644'}]
    selected = {r['path'] for r in rows}
    check('exact-123-unique-selected-paths', len(rows) == len(selected) == 123 and selection['includeSelectionItself'] == SEL)
    objects = {}
    bytes_total = 0
    for expected in rows:
        data = pin(expected)
        mode = '100755' if stat.S_IMODE((ROOT / expected['path']).lstat().st_mode) & 0o111 else '100644'
        check('selected-mode:' + expected['path'], mode == expected['mode'])
        objects[expected['path']] = {'oid': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(), 'mode': mode}
        bytes_total += len(data)
    object_rows = [{'path': p, **objects[p]} for p in sorted(objects)]
    digest = hashlib.sha256(json.dumps(object_rows, separators=(',', ':')).encode()).hexdigest()
    check('all-selected-payload-byte-total-and-blob-mode-digest', bytes_total == 4897969 and digest == OBJECTS)
    inputs = load(REL + 'inputs.json')
    check('recovery-expected-objects-and-frozen-selection', inputs['expectedObjects'] == object_rows and inputs['selectedBytes'] == bytes_total and
          inputs['allSelectedObjectDigestSHA256'] == digest and inputs['selection'] == selection_pin)
    for expected in inputs['rows']:
        pin(expected)
    original = ROOT / inputs['originalDirectory']
    historical_labels = set()
    for suffix in ['.plan.json', '.started.json', '.admission.json', '.command.json']:
        historical_labels.update(p.name[:-len(suffix)] for p in original.glob('*' + suffix))
    check('original-17-inventory-no-replay', historical_labels == {c['label'] for c in inputs['originalCommands']} and len(historical_labels) == 17)
    for expected in inputs['originalCommands']:
        for record in expected['records'].values():
            pin(record)
        closed(inputs['originalDirectory'] + '/' + expected['label'], expected['effectiveArgv'], expected['authoritySHA256'], expected['ordinal'], expected['exit'])
    failed = [x for x in inputs['originalCommands'] if x['exit'] != 0]
    check('original-failed-stage-8-exit1-retained', len(failed) == 1 and failed[0]['ordinal'] == 8 and failed[0]['exit'] == 1 and failed[0]['label'] == 'delivery-followup-stage')
    for name in inputs['originalAbsent']:
        check('original-absent-remains:' + name, not (original / name).exists())
    inspection_authority = load(REL + 'authority-exact-inspection.json')
    inspection_manifest = load(REL + 'argv-inspection.json')
    inspection_auth_sha = reads[REL + 'authority-exact-inspection.json']['sha256']
    inspection_receipt = load(REL + 'inspection-receipt.json')
    inspection_data = load(REL + 'inspection-data.json')
    inspection_streams = {}
    for ordinal, expected in enumerate(inspection_manifest['commands'], 1):
        _, _, streams = closed(REL + 'stage-recovery-inspection-' + expected['name'], expected['effectiveArgv'], inspection_auth_sha, ordinal, limits=(25, 10))
        inspection_streams[expected['name']] = streams
    check('inspection-10-read-only-records', len(inspection_receipt['commands']) == len(inspection_manifest['commands']) == 10 and
          all(c['kind'] == 'read' for c in inspection_manifest['commands']))
    inspected_raw = inspection_streams['index-raw']['stdout']
    inspection_index = parse_index(inspection_streams['index-selected']['stdout'])
    check('inspection-66-selected-staged-57-known-ignored-no-unrelated', len(parse_raw(inspected_raw)) == len(inspection_index) == 66 and
          set(inspection_index).issubset(selected) and all(objects[p] == o for p, o in inspection_index.items()) and
          sorted(selected - set(inspection_index)) == inspection_data['remainingSourceIndexPaths'] == sorted(inputs['ignoredSelectedPaths']) and
          inspection_data['unrelatedStagedPaths'] == 0)
    receipt = load(REL + 'stage-recovery-delivery-receipt.json')
    check('receipt-identities', (receipt['head'], receipt['tree'], receipt['parent']) == (HEAD, TREE, BASE) and receipt['selection'] == selection_pin)
    check('receipt-immutable-phase-source-bindings', receipt['authoritySnapshot'] == reads[REL + 'authority-snapshot-stage-recovery-delivery.json'] and
          receipt['argvManifest'] == approval and receipt['acceptedInspectionSeal'] == authority['acceptedInspection']['seal'] and
          receipt['acceptedInspectionRows'] == authority['acceptedInspection']['rows'] and
          receipt['preflightSeal'] == authority['acceptedPreflight']['seal'])
    actual_labels = set()
    for suffix in ['.plan.json', '.started.json', '.admission.json', '.command.json']:
        actual_labels.update(p.name[:-len(suffix)] for p in (ROOT / REL).glob('stage-recovery-delivery-*' + suffix))
    expected_labels = {'stage-recovery-delivery-' + c['name'] for c in manifest['commands']}
    check('exact-23-delivery-command-inventory', actual_labels == expected_labels and len(actual_labels) == 23)
    all_streams = {}
    previous_time = None
    aggregate = 0
    for ordinal, expected in enumerate(manifest['commands'], 1):
        vector = [s.replace('{COMMITTED_SHA}', HEAD) for s in expected['effectiveArgv']]
        plan, command, streams = closed(REL + 'stage-recovery-delivery-' + expected['name'], vector, AUTH, ordinal,
                                        limits=(45 if expected['name'] == 'push' else 25, 23))
        aggregate += len(streams['stdout']) + len(streams['stderr'])
        check(expected['name'] + ':aggregate-output-accounted', command['aggregateOutputBytes'] == aggregate)
        check(expected['name'] + ':phase-order', previous_time is None or previous_time <= when(plan['at']))
        previous_time = when(command['at'])
        all_streams[expected['name']] = streams
        check(expected['name'] + ':receipt-command-summary', receipt['commands'][ordinal - 1] ==
              {'name': 'stage-recovery-delivery-' + expected['name'], 'exit': 0, 'admitted': True, 'stopReason': None,
               'directChildReaped': True, 'ownedGroupAbsent': True, 'stdoutEOF': True, 'stderrEOF': True, 'sensitiveOutputRejected': False})
    check('phase-receipt-after-completion', len(receipt['commands']) == 23 and when(receipt['at']) >= previous_time)
    s = lambda name: all_streams[name]['stdout']
    check('initial-head-tree-branch-and-origin', s('head').decode().splitlines() == [BASE, BASE_TREE] and s('branch') == b'main\n' and
          s('origin') == b'https://github.com/snowdamiz/mixer.git\n')
    check('full-cached-before-byte-equals-inspected', s('index-before') == inspected_raw)
    pathspec = raw(REL + 'paths-stage-recovery.nul')
    check('force-add-exact123-nul-allowlist', pathspec == b''.join(p.encode() + b'\0' for p in sorted(selected)))
    admission = load(REL + 'stage-recovery-pathspec-admission.json')
    check('exact-pathspec-admitted-before-stage', admission['pathspec'] == reads[REL + 'paths-stage-recovery.nul'] and admission['selection'] == selection_pin and
          admission['paths'] == 123 and admission['exactNULAllowlistChecked'] is True and
          when(admission['at']) < when(load(REL + 'stage-recovery-delivery-stage.plan.json')['at']))
    check('finite-selected-index-all123-blob-modes', parse_index(s('index-selected')) == objects)
    for name in ['index-selected', 'authored-check']:
        vector = next(c['argv'] for c in manifest['commands'] if c['name'] == name)
        check(name + ':all-and-only-selected-argv-paths', vector[vector.index('--') + 1:] == sorted(selected))
    check('all123-format-check-success-streams-empty', all_streams['authored-check'] == {'stdout': b'', 'stderr': b''})
    staged = parse_raw(s('staged-objects'))
    committed = parse_raw(s('committed-objects'))
    changed = {p: {'oid': v['oid'], 'mode': v['mode']} for p, v in staged.items()}
    check('changed-subset-exact-staged-and-committed-parent-diff', staged == committed and s('staged-objects') == s('committed-objects') and
          set(staged) == selected and changed == objects and all(x['status'] in ('A', 'M') for x in staged.values()))
    check('direct-parent-head-and-tree-proof', s('committed-head').decode().splitlines() == [HEAD, TREE, BASE] and
          load(REL + 'committed-stage-recovery.json') == {'at': load(REL + 'committed-stage-recovery.json')['at'], 'head': HEAD, 'tree': TREE, 'parent': BASE, 'paths': 123})
    for name in ['staged-stage-recovery-all-index-objects-local.json', 'staged-stage-recovery-changed-objects-local.json', 'committed-stage-recovery-objects.json']:
        check('independent-object-map:' + name, load(REL + name) == objects)
    for field in ['committedChangedObjects', 'selectedIndexObjectsLocal']:
        pin(receipt[field])
    check('all-selected-changed-receipt-counts', receipt['changedSelectedPaths'] == 123 and receipt['unchangedSelectedPaths'] == 0 and
          receipt['selectedIndexBlobModeDigestSHA256'] == OBJECTS and receipt['allSelectedIndexBlobModesVerified'] is True and
          receipt['unchangedSelectedMembersBoundByParentTreeAndExactCommittedDiff'] is True)
    reservations = {}
    for field, name in [('stageReservation', 'stage'), ('commitReservation', 'commit'), ('pushReservation', 'push')]:
        pin(receipt[field])
        reservations[name] = load(receipt[field]['path'])
        check(name + ':separate-reservation-before-command', when(reservations[name]['at']) <
              when(load(REL + 'stage-recovery-delivery-' + name + '.plan.json')['at']))
    check('stage-reservation-exact123-once', reservations['stage']['selection'] == selection_pin and reservations['stage']['pathspec'] == reads[REL + 'paths-stage-recovery.nul'] and
          reservations['stage']['stageLimit'] == 1 and reservations['stage']['retryAllowed'] is False and reservations['stage']['fullSelectedPaths'] == 123)
    check('commit-reservation-parent-and-changed-objects-once', reservations['commit']['selection'] == selection_pin and
          reservations['commit']['parentMustEqual'] == BASE and reservations['commit']['commitLimit'] == 1 and
          reservations['commit']['retryAllowed'] is False and reservations['commit']['changedObjects'] == reads[REL + 'staged-stage-recovery-changed-objects-local.json'])
    check('push-reservation-exact-head-ref-once', reservations['push']['head'] == HEAD and reservations['push']['tree'] == TREE and
          reservations['push']['parent'] == BASE and reservations['push']['remote'] == 'origin' and reservations['push']['ref'] == 'refs/heads/main' and
          reservations['push']['force'] is False and reservations['push']['reservationConsumedBeforeSubmit'] is True and reservations['push']['retryOnUnknownOutcome'] is False)
    once = load(REL + 'stage-recovery-delivery-once.json')
    check('delivery-once-reservation', once['selection'] == selection_pin and once['paths'] == 123 and once['oneCommitNonforcePushAuthorized'] is True and once['retryOnUnknownOutcome'] is False)
    check('one-stage-one-commit-one-nonforce-push-no-dispatch', [c['name'] for c in manifest['commands'] if c['kind'] == 'mutation'] == ['stage', 'commit', 'push'] and
          all(c['argv'][0] == 'git' for c in manifest['commands']))
    for name in ['push-url-before-stage', 'push-url-prepush', 'push-url-postpush']:
        check(name + ':single-exact-push-url', s(name) == b'https://github.com/snowdamiz/mixer.git\n')
    check('remote-main-before-and-prepush-baseline', all(s(n).decode().split() == [BASE, 'refs/heads/main'] for n in ['remote-before', 'remote-prepush']))
    check('postpush-remote-main-exact-new-head', s('remote-postpush').decode().split() == [HEAD, 'refs/heads/main'])
    check('push-acknowledgement-exact-new-head', HEAD.encode() + b' -> main' in all_streams['push']['stderr'] and b'forced update' not in all_streams['push']['stderr'])
    check('postdelivery-index-empty', s('index-after') == b'' and receipt['indexEmpty'] is True)
    preservation = load(authority['acceptedPreflight']['rows'][1]['path'])
    for name in ['before-diff', 'staged-diff', 'after-diff']:
        rows_after = raw_rows(s(name))
        check(name + ':complete-outside-dirty-raw-preserved', [x for x in rows_after if x['path'] not in selected] == preservation['otherDirtyTracked'])
    check('before-diff-inspected-exact', raw_rows(s('before-diff')) == inspection_data['completeWorktreeRawRows'])
    for expected in preservation['tracked'] + preservation['protectedSnapshots']:
        check('outside-selected-byte-mode:' + expected['path'], fp(expected['path']) == expected)
    check('wrangler-identity-untouched', fp('.wrangler') == preservation['wrangler'])
    check('artifact-store-absent', not (ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex').exists())
    for expected in preservation['untrackedCollapsed']:
        check('preexisting-collapsed-identity-mode:' + expected['path'], fp(expected['path'], True) == expected)
    before = inspection_data['collapsedStatus']
    after = parse_status(s('collapsed-status-after'))
    after_local = load(REL + 'preservation-stage-recovery-after-local.json')
    check('retained-after-collapsed-status-exact', after_local['statusCollapsed'] == after)
    outside = lambda rows: [x for x in rows if x['status'] != '??' and x['path'] not in selected]
    check('collapsed-outside-tracked-status-preserved', outside(before) == outside(after))
    prior = [x['path'] for x in before if x['status'] == '??']
    current = [x['path'] for x in after if x['status'] == '??']
    projects_selected = lambda p: any(s == p.rstrip('/') or s.startswith(p.rstrip('/') + '/') for s in selected)
    covers = lambda p, old: p == old or old.endswith('/') and p.startswith(old)
    recovery_identity = inputs['newRecoveryDirectoryIdentity']
    check('collapsed-new-untracked-confined', all(projects_selected(p) or
          (p == recovery_identity['path'] and fp(p, True) == recovery_identity) or any(covers(p, old) for old in prior) for p in current))
    check('collapsed-unrelated-prior-entries-retained', all(projects_selected(old) or any(covers(p, old) or covers(old, p) for p in current) for old in prior))
    check('collapsed-current-identities-and-counts', after_local['untrackedCollapsed'] == [fp(p, True) for p in current] and
          receipt['afterCollapsedUntrackedEntries'] == len(current) == 2410 and receipt['preexistingCollapsedEntryIdentityModesPreserved'] == len(preservation['untrackedCollapsed']) == 2416 and
          receipt['collapsedSelectedTransitions'] == {'removed': len(set(prior)-set(current)), 'added': len(set(current)-set(prior))} == {'removed': 0, 'added': 0})
    expected_proof = {'outsideTrackedStatusUnchanged': True, 'newUntrackedEntriesConfinedToPriorCollapsedScopesOrExactRecoveryDirectory': True,
                      'removedCollapsedEntriesConfinedToSelectedProjections': True, 'newRecoveryDirectoryIdentity': recovery_identity, 'recursiveUntrackedContentProof': False}
    check('collapsed-receipt-truthful-limited-proof', receipt['collapsedStatusProof'] == expected_proof and receipt['allCleanTrackedFilesIndependentlyHashed'] is False and
          receipt['cleanTrackedBoundByBaselineTreeAndCompleteRawDiff'] is True and receipt['outsideSelectionDirtyByteModeSnapshotsPreserved'] == 2)
    check('receipt-no-new-authority-no-held-runtime-or-release-claim', receipt['manualWorkflowDispatchesAuthorized'] == 0 and
          receipt['manualDispatchesPending'] == receipt['separatelySelectedManualDispatchCeiling'] == 1 and receipt['manualHostKeys'] == ['axis'] and
          receipt['allExistingHoldsUntouched'] is True and receipt['runtimeCompilerNativeUICaptureProcessInventoryHeldProbesStarted'] is False and
          receipt['fieldlogRepositoryOperations'] == receipt['canonicalAndroidChanges'] == 0 and receipt['releaseTagOrGAPromotion'] is False and
          receipt['productionDefaultsChanged'] is False and receipt['rawHelperInventoriesCommitted'] is False)
    check('receipt-final-positive-claims-supported', receipt['pushed'] is True and receipt['force'] is False and receipt['selectedPaths'] == 123 and
          receipt['inspectedCachedRawMatchedBeforeForceAdd'] is True and receipt['originalAttemptReplayed'] is False and
          receipt['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True and
          receipt['whitespaceCheckedPaths'] == receipt['unchangedContentAndBlobModeProofPaths'] == 123 and receipt['immutableEvidenceFormattingExclusions'] == [])
    failed_checks = [c for c in checks if not c['passed']]
    report = {
        'schema': 1, 'decision': 'accept-exact-23-command-stage-recovery-delivery-observation' if not failed_checks else 'refuse-unresolved-actual-data-findings',
        'reviewer': 'independent fresh-context actual-data reviewer', 'head': HEAD, 'tree': TREE, 'parent': BASE,
        'scope': 'Pure bounded filesystem/data inspection of immutable selected sources, authority snapshot and retained actual records; no subject/helper import or execution.',
        'authority': reads[REL + 'authority-snapshot-stage-recovery-delivery.json'], 'receipt': reads[REL + 'stage-recovery-delivery-receipt.json'],
        'selection': selection_pin, 'selectedPaths': 123, 'selectedPayloadBytes': bytes_total, 'allSelectedObjectDigestSHA256': digest,
        'originalCommandsPreserved': 17, 'inspectionCommandsReviewed': 10, 'deliveryCommandsReviewed': 23,
        'deliveryOutputBytesRehashed': aggregate, 'changedSelectedPaths': len(changed), 'unchangedSelectedPaths': 123-len(changed),
        'checksPassed': len(checks)-len(failed_checks), 'checksFailed': len(failed_checks), 'findings': failed_checks,
        'checks': checks, 'commandEvidence': command_details,
        'commitPushObservation': {'oneCommit': True, 'oneNonforceOriginMainPush': True, 'exactPostpushRemoteHead': HEAD, 'indexEmpty': True},
        'limitations': ['No later CI or manual workflow phase authority is granted by this review.',
                       'Child custody is assessed from exact retained command records; no live held-process state is inferred.',
                       'Outside clean tracked files are bound by baseline tree and complete raw diff; no independent complete tracked-file byte inventory.',
                       'Untracked preservation is collapsed identity/mode and bounded status projection, not recursive untracked content proof.',
                       'No compiler, native/UI/capture, phone, product-runtime, published FieldLog package, release or GA qualification.'],
        'execution': {'reviewScriptOnly': True, 'subjectHelperGitGhCompilerNetworkProbeSignalNativeUIExecution': False,
                      'currentRecoveryAuthorityRead': 'immutable authority-snapshot-stage-recovery-delivery.json only',
                      'historicalOriginalAuthorityRead': 'only as exact pinned retained original-attempt data',
                      'liveRecoveryAuthorityRead': False, 'laterAuthorityGranted': False, 'allExistingHoldsUntouched': True,
                      'command': 'python3 -I -S -B verification/github-delivery-axis-binding-stage-recovery/review/delivery-actual/audit.py',
                      'cwd': str(ROOT), 'pythonExecutable': sys.executable, 'pythonVersion': sys.version,
                      'flags': {'isolated': sys.flags.isolated, 'noSite': sys.flags.no_site, 'dontWriteBytecode': sys.dont_write_bytecode},
                      'observedByRootOuterDelivery': {'session': 96824, 'exit': 0, 'attribution': 'Root completion message; child closure independently checked from retained records'}},
    }
    write('actual-review.json', report)
    write('read-set.json', {'schema': 1, 'rows': [reads[k] for k in sorted(reads)], 'files': len(reads), 'readBytes': sum(r['bytes'] for r in reads.values())})
    seal_rows = []
    for name in ['audit.py', 'actual-review.json', 'read-set.json']:
        p = OUT / name
        data = p.read_bytes()
        seal_rows.append({'path': str(p.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    write('seal.json', {'schema': 1, 'decision': report['decision'], 'rows': seal_rows, 'checksPassed': report['checksPassed'],
                        'checksFailed': report['checksFailed'], 'subjectExecution': False, 'laterAuthorityGranted': False})
    print(json.dumps({k: report[k] for k in ['decision', 'head', 'tree', 'parent', 'checksPassed', 'checksFailed', 'selectedPayloadBytes', 'deliveryOutputBytesRehashed']}))
    if failed_checks:
        print(json.dumps(failed_checks, indent=2))
        sys.exit(1)


def write(name, obj):
    path = OUT / name
    assert path.parent == OUT
    path.write_text(json.dumps(obj, indent=2) + '\n')


if __name__ == '__main__':
    main()
