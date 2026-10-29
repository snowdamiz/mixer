"""One separately authorized ten-read inspection after the closed stage failure."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
assert sys.flags.dont_write_bytecode == 1
import hashlib
import importlib.util
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
assert OUT == ROOT / 'verification/github-delivery-axis-binding-stage-recovery'
OLD = ROOT / 'verification/github-delivery-axis-binding-followup'
BASE = '2cea1013151ccc38bb635fb4755793cd25a0bd1b'
TREE = '830e859979d2ea95335d8cb8ea28ac8caaa0614b'
HELPER_SHA = '34f1991509d7b156f00b5cc50fcd82ebae81fb414da904c19dcdca70c3eeb987'
INPUT_SHA = '347f021a32fe4243d0f4cd8f6d3a5b6011d23273b2a96599e4a11548a37b3e15'
ARGV_SHA = '5ce2d87212340532eceeff653b233aeb156046723ff7824fa0c8297e0956a9f9'
OBJECT_SHA = '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd'
PUSH_URL_READ = ('git', 'remote', 'get-url', '--push', '--all', 'origin')
NAMES = ['git-version', 'head', 'branch', 'origin', 'push-url', 'remote-main',
         'index-raw', 'index-selected', 'worktree-raw', 'collapsed-status']


def safe(value):
    p = PurePosixPath(value)
    assert value and not p.is_absolute() and str(p) == value
    assert not any(c in value for c in '\\*?[]\0') and not value.startswith(('-', ':'))
    assert '..' not in p.parts and '.' not in p.parts
    assert all(not p.is_symlink() for p in (ROOT / value).parents)
    return ROOT / value


def row(p):
    p = safe(str(p.relative_to(ROOT)))
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b),
            'sha256': hashlib.sha256(b).hexdigest()}


def equal_row(expected):
    assert set(expected) == {'path', 'bytes', 'sha256'}
    assert row(ROOT / expected['path']) == expected, expected['path']


def absent(p):
    try:
        p.lstat()
    except FileNotFoundError:
        return
    raise AssertionError('Required absence: ' + str(p))


def fingerprint(value, identity_only=False):
    p = ROOT / value.rstrip('/')
    s = p.lstat()
    result = {'path': value, 'mode': stat.S_IMODE(s.st_mode), 'type': stat.S_IFMT(s.st_mode)}
    if identity_only or not stat.S_ISREG(s.st_mode) and not stat.S_ISLNK(s.st_mode):
        result.update(inode=s.st_ino, device=s.st_dev)
    elif stat.S_ISREG(s.st_mode):
        b = p.read_bytes()
        result.update(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
    else:
        result['target'] = os.readlink(p)
    return result


def raw_rows(payload):
    parts = payload.split(b'\0')
    assert parts[-1] == b'' and len(parts) % 2 == 1
    result = []
    seen = set()
    for i in range(0, len(parts) - 1, 2):
        meta, value = parts[i].decode(), parts[i + 1].decode()
        safe(value)
        fields = meta.split()
        assert len(fields) == 5 and re.fullmatch(':[0-7]{6}', fields[0])
        assert re.fullmatch('[0-7]{6}', fields[1])
        assert all(re.fullmatch('[0-9a-f]{40}', x) for x in fields[2:4])
        assert fields[4] in ('A', 'M', 'D', 'T') and value not in seen
        seen.add(value)
        result.append({'path': value, 'gitRaw': meta})
    return result


def index_rows(payload, selected):
    parts = payload.split(b'\0')
    assert parts[-1] == b''
    objects = {}
    for entry in parts[:-1]:
        meta, value = entry.split(b'\t', 1)
        fields, value = meta.decode().split(), value.decode()
        assert len(fields) == 3 and fields[2] == '0'
        assert re.fullmatch('[0-7]{6}', fields[0]) and re.fullmatch('[0-9a-f]{40}', fields[1])
        assert value in selected and value not in objects
        objects[value] = {'oid': fields[1], 'mode': fields[0]}
    return objects


def collapsed(payload):
    parts = payload.split(b'\0')
    assert parts[-1] == b''
    result = []
    for entry in parts[:-1]:
        text = entry.decode()
        assert len(text) > 3 and text[2] == ' ' and not any(c in text[:2] for c in 'RCU')
        value = text[3:]
        safe(value.rstrip('/'))
        result.append({'status': text[:2], 'path': value})
    return result


def compare_collapsed(before, after, selected, recovery_identity):
    def selected_projection(value):
        value = value.rstrip('/')
        return any(p == value or p.startswith(value + '/') for p in selected)

    def covered_by(value, prior):
        return value == prior or prior.endswith('/') and value.startswith(prior)

    def outside_tracked(rows):
        return [r for r in rows if r['status'] != '??' and r['path'] not in selected]

    assert outside_tracked(after) == outside_tracked(before), 'Outside-selected tracked status changed'
    prior = [r['path'] for r in before if r['status'] == '??']
    current = [r['path'] for r in after if r['status'] == '??']
    for value in current:
        if selected_projection(value):
            continue
        if value == recovery_identity['path']:
            assert fingerprint(value, identity_only=True) == recovery_identity
            continue
        assert any(covered_by(value, old) for old in prior), ('New unrelated collapsed entry', value)
    for old in prior:
        if selected_projection(old):
            continue
        assert any(covered_by(value, old) or covered_by(old, value) for value in current), (
            'Missing unrelated collapsed entry', old)
    return {'outsideTrackedStatusUnchanged': True,
            'newUntrackedEntriesConfinedToPriorCollapsedScopesOrExactRecoveryDirectory': True,
            'removedCollapsedEntriesConfinedToSelectedProjections': True,
            'newRecoveryDirectoryIdentity': recovery_identity,
            'recursiveUntrackedContentProof': False}


def historical_closure(inputs):
    for expected in inputs['rows']:
        equal_row(expected)
    labels = set()
    for suffix in ('.plan.json', '.started.json', '.admission.json', '.command.json'):
        labels.update(p.name[:-len(suffix)] for p in OLD.glob('*' + suffix))
    assert labels == {x['label'] for x in inputs['originalCommands']} and len(labels) == 17
    for expected in inputs['originalCommands']:
        for record in expected['records'].values():
            equal_row(record)
        command = json.loads((OLD / (expected['label'] + '.command.json')).read_bytes())
        assert command['argv'] == expected['effectiveArgv']
        assert command['authoritySHA256'] == expected['authoritySHA256']
        assert command['exit'] == expected['exit']
        assert command['rawWaitStatus'] == expected['exit'] * 256
        assert command['rawWaitPID'] == command['ownedPID'] == command['ownedPGID']
        assert command['identity'] == dict.fromkeys(('pid', 'pgid', 'sid'), command['ownedPID'])
        for key in ('admitted', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF',
                    'signalAuthorityRetired', 'separateOutputPipes', 'finalReapAttempted',
                    'implicitPopenReapingDisabled', 'noSignalAfterFinalReapOrLostAuthority'):
            assert command[key] is True, (expected['label'], key)
        assert command['postReapAbsenceProbeCount'] == 1 and command['signals'] == []
        assert command['signalAuthorityLost'] is None and command['stopReason'] is None
        assert command['failure'] is None and command['sensitiveOutputRejected'] is False
        for stream in ('stdout', 'stderr'):
            assert command[stream] == expected['records'][stream]
    for name in inputs['originalAbsent']:
        absent(OLD / name)
    seal = json.loads((ROOT / inputs['failedReviewSeal']['path']).read_bytes())
    assert seal['decision'] == 'accept-failed-delivery-prefix-evidence-no-completion-or-retry'
    assert seal['report'] == inputs['failedReviewReport'] and seal['noRetryOrRecoveryAuthorityGranted'] is True
    failed = json.loads((ROOT / inputs['failedReviewReport']['path']).read_bytes())
    assert failed['attemptedCommands'] == 8 and failed['successfulCommands'] == 7
    assert failed['failure']['ignoredSelectedPaths'] == inputs['ignoredSelectedPaths']
    assert failed['commitPushDispatchObserved'] == {'commit': False, 'push': False, 'dispatch': False}


def frozen_sources(inputs, preservation):
    assert fingerprint(inputs['newRecoveryDirectoryIdentity']['path'], identity_only=True) == inputs['newRecoveryDirectoryIdentity']
    equal_row(inputs['selection'])
    selection = json.loads((ROOT / inputs['selection']['path']).read_bytes())
    assert selection['baseline'] == {'revision': BASE, 'tree': TREE}
    assert selection['selectedCountIncludingSelf'] == 123
    assert selection['formatting']['excludeImmutablePaths'] == []
    assert selection['formatting']['allContentModeAndObjectProofRetained'] is True
    rows = selection['selectedRows'] + [{**inputs['selection'], 'mode': '100644'}]
    assert len(rows) == len({x['path'] for x in rows}) == 123
    assert sum(x['bytes'] for x in rows) == 4897969
    objects = []
    for expected in sorted(rows, key=lambda x: x['path']):
        equal_row({k: expected[k] for k in ('path', 'bytes', 'sha256')})
        p = ROOT / expected['path']
        assert expected['mode'] == '100644' and not stat.S_IMODE(p.stat().st_mode) & 0o111
        payload = p.read_bytes()
        objects.append({'path': expected['path'], 'oid': hashlib.sha1(
            b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest(), 'mode': '100644'})
    assert objects == inputs['expectedObjects']
    assert hashlib.sha256(json.dumps(objects, separators=(',', ':')).encode()).hexdigest() == OBJECT_SHA
    for expected in preservation['tracked'] + preservation['protectedSnapshots']:
        assert fingerprint(expected['path']) == expected
    assert fingerprint('.wrangler') == preservation['wrangler']
    absent(ROOT / 'hosted/lib/mixer_hosted/artifacts/store.ex')
    for expected in preservation['untrackedCollapsed']:
        assert fingerprint(expected['path'], identity_only=True) == expected
    return {x['path']: {'oid': x['oid'], 'mode': x['mode']} for x in objects}


def main():
    assert len(sys.argv) == 1
    assert row(OUT / 'inputs.json')['sha256'] == INPUT_SHA
    assert row(OUT / 'argv-inspection.json')['sha256'] == ARGV_SHA
    assert row(OUT / 'owned.py')['sha256'] == HELPER_SHA
    inputs = json.loads((OUT / 'inputs.json').read_bytes())
    manifest = json.loads((OUT / 'argv-inspection.json').read_bytes())
    preservation = json.loads((OLD / 'preservation-followup-local.json').read_bytes())
    historical_closure(inputs)
    expected_objects = frozen_sources(inputs, preservation)
    selected = set(expected_objects)
    assert manifest['phase'] == 'stage-recovery-inspection'
    assert [x['name'] for x in manifest['commands']] == NAMES
    assert manifest['session'] == {'seconds': 240, 'count': 10, 'prefix': 'stage-recovery-inspection-'}
    for x in manifest['commands']:
        assert x['kind'] == 'read' and x['effectiveArgv'] == ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *x['argv'][1:]]
    assert manifest['commands'][7]['argv'] == ['git', 'ls-files', '--stage', '-z', '--', *sorted(selected)]
    raw_authority = (OUT / 'authority.json').read_bytes()
    authority = json.loads(raw_authority)
    assert authority['schema'] == 1 and authority['authorized'] is True
    assert authority['purpose'] == 'fresh-stage-recovery-inspection-only'
    assert authority['repository'] == 'snowdamiz/mixer' and authority['branch'] == 'main'
    assert authority['selection'] == inputs['selection']
    assert authority['baseline'] == {'head': BASE, 'tree': TREE}
    assert authority['stageLimit'] == authority['commitLimit'] == authority['nonforcePushLimit'] == authority['manualWorkflowDispatchLimit'] == 0
    assert authority['phaseLimit'] == 1 and authority['originalAttemptReplayAllowed'] is False
    assert authority['inputs'] == row(OUT / 'inputs.json')
    assert authority['argvApproval'] == row(OUT / 'argv-inspection.json')
    assert authority['source'] == row(Path(__file__).resolve())
    assert authority['helper'] == row(OUT / 'owned.py')
    assert authority['failedAttemptReviewSeal'] == inputs['failedReviewSeal']
    equal_row(authority['sourceReview'])
    review = json.loads((ROOT / authority['sourceReview']['path']).read_bytes())
    assert review['decision'] == 'accept-exact-stage-recovery-inspection-source'
    assert all(review[k] == authority[k] for k in ('source', 'helper', 'inputs', 'argvApproval'))
    assert authority['readOnlyPushURLException'] == list(PUSH_URL_READ)
    absent(OUT / 'inspection-once.json')
    spec = importlib.util.spec_from_file_location('stage_recovery_owned', OUT / 'owned.py')
    owned = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = owned
    spec.loader.exec_module(owned)
    assert owned.OUT == OUT and owned.ROOT == ROOT
    original_validate_argv = owned.validate_argv

    def selected_read_admission_adapter(argv):
        if isinstance(argv, (list, tuple)) and tuple(argv) == PUSH_URL_READ:
            return True
        return original_validate_argv(argv)

    owned.validate_argv = selected_read_admission_adapter
    # Preserve the exact root authority bytes before consuming this inspection.
    with (OUT / 'authority-exact-inspection.json').open('xb') as handle:
        handle.write(raw_authority)
        handle.flush()
        os.fsync(handle.fileno())
    owned.save('inspection-once.json', {'phase': manifest['phase'], 'source': authority['source'],
        'authority': row(OUT / 'authority-exact-inspection.json'), 'retryAllowed': False,
        'originalAttemptReplayed': False, 'commandLimit': 10})
    commands = owned.Commands(240, 10, 'stage-recovery-inspection-')
    used = []

    def run(name):
        assert name == NAMES[len(used)]
        assert (OUT / 'authority.json').read_bytes() == raw_authority
        for key in ('source', 'helper', 'inputs', 'argvApproval', 'sourceReview'):
            equal_row(authority[key])
        historical_closure(inputs)
        assert frozen_sources(inputs, preservation) == expected_objects
        command = manifest['commands'][len(used)]
        # Exact root-reviewed manifest match precedes the sole read adapter.
        assert command['name'] == name and command['kind'] == 'read'
        used.append(name)
        return commands.run(name, list(command['argv']), seconds=25)

    version = run('git-version').decode().strip()
    head = run('head').decode().splitlines()
    assert len(head) == 3 and head[:2] == [BASE, TREE] and re.fullmatch('[0-9a-f]{40}', head[2])
    assert run('branch').decode().strip() == 'main'
    assert run('origin').decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
    assert run('push-url').decode().splitlines() == ['https://github.com/snowdamiz/mixer.git']
    assert run('remote-main').decode().split() == [BASE, 'refs/heads/main']
    cached = raw_rows(run('index-raw'))
    index = index_rows(run('index-selected'), selected)
    pending = {}
    for entry in cached:
        value, fields = entry['path'], entry['gitRaw'].split()
        assert value in selected and fields[4] in ('A', 'M')
        actual = {'oid': fields[3], 'mode': fields[1]}
        assert actual == expected_objects[value] == index[value]
        pending[value] = actual
    worktree = raw_rows(run('worktree-raw'))
    assert [x for x in worktree if x['path'] not in selected] == preservation['otherDirtyTracked']
    status = collapsed(run('collapsed-status'))
    status_proof = compare_collapsed(preservation['statusCollapsed'], status, selected, inputs['newRecoveryDirectoryIdentity'])
    assert used == NAMES and len(commands.records) == 10
    historical_closure(inputs)
    assert frozen_sources(inputs, preservation) == expected_objects
    matching = sorted(value for value in index if index[value] == expected_objects[value])
    remaining = sorted(selected - set(matching))
    owned.save('inspection-data.json', {'head': head[0], 'tree': head[1], 'parent': head[2],
        'cachedRawRows': cached, 'selectedIndexObjects': index, 'pendingChangedObjects': pending,
        'matchingSourceIndexPaths': matching, 'remainingSourceIndexPaths': remaining,
        'completeWorktreeRawRows': worktree, 'collapsedStatus': status, 'collapsedStatusProof': status_proof,
        'originalPreservation': row(OLD / 'preservation-followup-local.json'),
        'allSelectedObjectDigestSHA256': OBJECT_SHA, 'selectedPaths': 123,
        'allSourceBytesModesUnchanged': True, 'unrelatedStagedPaths': 0,
        'remainingConfinedToKnownIgnored57': set(remaining).issubset(set(inputs['ignoredSelectedPaths'])),
        'allCleanTrackedFilesIndependentlyHashed': False,
        'untrackedScope': 'preexisting collapsed entry identities and modes only; no recursive inventory'})
    owned.save('inspection-receipt.json', {'schema': 1, 'decision': 'ten-read-inspection-complete-pending-independent-actual-review',
        'selection': inputs['selection'], 'source': authority['source'], 'helper': authority['helper'],
        'argv': authority['argvApproval'], 'inputs': authority['inputs'],
        'authority': row(OUT / 'authority-exact-inspection.json'),
        'failedAttemptReviewSeal': inputs['failedReviewSeal'], 'data': row(OUT / 'inspection-data.json'),
        'commands': commands.records, 'pendingChangedPaths': len(pending),
        'matchingSourceIndexPaths': len(matching), 'remainingSourceIndexPaths': len(remaining),
        'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
        'stageCommitPushDispatchPerformed': False, 'originalAttemptReplayed': False,
        'continuationAuthorized': False, 'allExistingHoldsUntouched': True,
        'tools': {'git': version, 'python': sys.version, 'interpreter': sys.executable}})
    print(json.dumps({'inspection': 'complete-pending-independent-actual-review',
        'closedCommands': 10, 'pendingChangedPaths': len(pending), 'remainingSourceIndexPaths': len(remaining),
        'stageCommitPushDispatchPerformed': False}))


if __name__ == '__main__':
    main()
