"""Exact frozen selection, preservation and root-reviewed argv only. No top-level commands."""
import sys
sys.dont_write_bytecode = True
assert sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.flags.optimize == 0
import hashlib
import importlib.util
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
assert OUT == ROOT / "verification/github-delivery-axis-binding-stage-recovery"
OLD = ROOT / 'verification/github-delivery-axis-binding-followup'
BASE = '2cea1013151ccc38bb635fb4755793cd25a0bd1b'
TREE = '830e859979d2ea95335d8cb8ea28ac8caaa0614b'
SELECTION = 'verification/android-axis-binding-selection-2026-10-29/selection.json'
SELECTION_SHA = '6dda8a7e90a3be9b93cd3683f9038c6767896dcf986bcee5beb47472ff7299fd'
SELECTION_BYTES = 36961
SELECTED_COUNT = 123
HELPER_SHA = '34f1991509d7b156f00b5cc50fcd82ebae81fb414da904c19dcdca70c3eeb987'
raw_helper = (OUT / 'owned.py').read_bytes()
assert hashlib.sha256(raw_helper).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location('axis_binding_delivery_owned', OUT / 'owned.py')
owned = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = owned
spec.loader.exec_module(owned)
assert owned.OUT == OUT and owned.ROOT == ROOT
ORIGINAL_VALIDATE_ARGV = owned.validate_argv
PUSH_URL_READ_EXCEPTION = ('git', 'remote', 'get-url', '--push', '--all', 'origin')


def selected_read_admission_adapter(argv):
    if isinstance(argv, (list, tuple)) and tuple(argv) == PUSH_URL_READ_EXCEPTION:
        return True
    return ORIGINAL_VALIDATE_ARGV(argv)


owned.validate_argv = selected_read_admission_adapter
ADAPTER_FRAGMENT_SHA256 = '2d88ec37fed744df317fb5c933eb7f5505c852a39434273b1234416f8661a94c'
row, save, now = owned.row, owned.save, owned.now

INSPECTION_SOURCE = {"path":"verification/github-delivery-axis-binding-stage-recovery/inspect_stage_recovery.py","bytes":18195,"sha256":"f5bdfa9131eaf1d45c857b6d056153b2fa01ee1c0016e2ede68cc2c8b12bcac8"}
RECOVERY_INPUTS_ROW = {"path":"verification/github-delivery-axis-binding-stage-recovery/inputs.json","bytes":68698,"sha256":"347f021a32fe4243d0f4cd8f6d3a5b6011d23273b2a96599e4a11548a37b3e15"}
INSPECTION_ARGV_ROW = {"path":"verification/github-delivery-axis-binding-stage-recovery/argv-inspection.json","bytes":27686,"sha256":"5ce2d87212340532eceeff653b233aeb156046723ff7824fa0c8297e0956a9f9"}
assert row(ROOT / INSPECTION_SOURCE['path']) == INSPECTION_SOURCE
spec = importlib.util.spec_from_file_location('axis_stage_recovery_inspection_data', ROOT / INSPECTION_SOURCE['path'])
inspection = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = inspection
spec.loader.exec_module(inspection)
assert inspection.OUT == OUT and inspection.ROOT == ROOT
assert row(ROOT / RECOVERY_INPUTS_ROW['path']) == RECOVERY_INPUTS_ROW
RECOVERY_INPUTS = json.loads((ROOT / RECOVERY_INPUTS_ROW['path']).read_bytes())
ORIGINAL_PRESERVATION = json.loads((OLD / 'preservation-followup-local.json').read_bytes())
OBJECT_SHA = '8c59481511bc90e907c76f6b18cbfc41b12568706c60d47b9f507c51347554bd'

assert row(ROOT / SELECTION) == {'path': SELECTION, 'bytes': SELECTION_BYTES, 'sha256': SELECTION_SHA}
S = json.loads((ROOT / SELECTION).read_bytes())
assert S['baseline'] == {'revision': BASE, 'tree': TREE}
assert S['repository'] == 'snowdamiz/mixer' and S['branch'] == 'main' and S['remote'] == 'origin'
assert S['includeSelectionItself'] == SELECTION and S['selectedCountIncludingSelf'] == SELECTED_COUNT
assert len(S['selectedRows']) == SELECTED_COUNT - 1
assert set(S['manualHosts']) == {'axis'}
for source in S['manualHosts'].values():
    assert source['dispatches'] == 1 and source['retries'] == 0 and source['attempt'] == 1
    assert source['actualDispatched'] == 0 and source['expectedJobs'] == 1
    assert source['consumeAllowanceBeforeDispatch'] is True and source['unknownOutcomeReplay'] is False
    assert source['bindDeliveredSHAThenEnableSelection'] is True
ROOT_REVIEW_SHA256 = '1da1a158f232ce2b586a5f12ce96d00e4e1de5e739a4e47cfc75e4e2a5b167b4'
assert S['rootReviewSHA256'] == ROOT_REVIEW_SHA256
assert type(ROOT_REVIEW_SHA256) is str and len(ROOT_REVIEW_SHA256) == 64


def assert_absent(value):
    try:
        (ROOT / value).lstat()
    except FileNotFoundError:
        return
    raise AssertionError('Required absence failed: ' + value)


def safe(value):
    p = PurePosixPath(value)
    assert value and not p.is_absolute() and '..' not in p.parts and '.' not in p.parts and '\\' not in value
    assert str(p) == value
    assert all(not parent.is_symlink() for parent in (ROOT / value).parents)


def selected_row(value):
    safe(value['path'])
    p = ROOT / value['path']
    actual = row(p)
    st = p.lstat()
    actual['mode'] = '100755' if stat.S_IMODE(st.st_mode) & 0o111 else '100644'
    assert actual == value, value['path']
    return actual

ROWS = [selected_row(value) for value in S['selectedRows']]
selfrow = row(ROOT / SELECTION)
selfrow['mode'] = '100755' if stat.S_IMODE((ROOT / SELECTION).stat().st_mode) & 0o111 else '100644'
ROWS.append(selfrow)
SELECTED = {value['path'] for value in ROWS}
assert len(SELECTED) == SELECTED_COUNT
assert not any(value.startswith(('vm/', 'android/', 'sdk/')) for value in SELECTED)
assert not any(value.startswith('.wrangler') for value in SELECTED)
PROTECTED = S['preservation']['protected']
assert not any(value['path'] in SELECTED for value in PROTECTED)


def fingerprint(value):
    p = ROOT / value.rstrip('/')
    try:
        st = p.lstat()
    except FileNotFoundError:
        return {'path': value, 'missing': True}
    result = {'path': value, 'mode': stat.S_IMODE(st.st_mode), 'type': stat.S_IFMT(st.st_mode)}
    if stat.S_ISREG(st.st_mode):
        h = hashlib.sha256()
        with p.open('rb') as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b''):
                h.update(block)
        result.update(bytes=st.st_size, sha256=h.hexdigest())
    elif stat.S_ISLNK(st.st_mode):
        result['target'] = os.readlink(p)
    else:
        result.update(inode=st.st_ino, device=st.st_dev)
    return result


def preserved_entry(value):
    st = (ROOT / value.rstrip('/')).lstat()
    return {'path': value, 'mode': stat.S_IMODE(st.st_mode), 'type': stat.S_IFMT(st.st_mode),
            'inode': st.st_ino, 'device': st.st_dev}


def raw_rows(raw):
    parts = raw.split(b'\0')
    assert len(parts) % 2 == 1
    result = []
    for index in range(0, len(parts) - 1, 2):
        meta, value = parts[index].decode(), parts[index + 1].decode()
        fields = meta.split()
        assert len(fields) == 5 and fields[-1] in ('M', 'D', 'T', 'A')
        safe(value)
        result.append({'path': value, 'gitRaw': meta})
    return result


def collapsed(raw):
    result = []
    for value in raw.split(b'\0'):
        if not value:
            continue
        decoded = value.decode()
        assert len(decoded) > 3 and decoded[2] == ' ' and not any(c in decoded[:2] for c in 'RC')
        result.append({'status': decoded[:2], 'path': decoded[3:]})
    return result


def check_sources():
    assert row(ROOT / SELECTION) == {'path': SELECTION, 'bytes': SELECTION_BYTES, 'sha256': SELECTION_SHA}
    for expected in ROWS:
        assert selected_row(expected) == expected
    for expected in PROTECTED:
        assert row(ROOT / expected['path'])['sha256'] == expected['sha256']
    assert row(ROOT / S['ordinaryHost']['workflow'])['sha256'] == S['ordinaryHost']['workflowSHA256']
    assert_absent('hosted/lib/mixer_hosted/artifacts/store.ex')
    for source in S['manualHosts'].values():
        assert source['workflow'] in SELECTED and source['selectionTemplate'] in SELECTED
        assert row(ROOT / source['workflow'])['sha256'] == source['workflowSHA256']
    helper_binding = S['deliveryHelper']
    assert helper_binding['path'] == str((OLD / 'owned.py').relative_to(ROOT))
    assert helper_binding['sha256'] == HELPER_SHA
    assert helper_binding['priorHelper'] == {'path': 'verification/github-delivery-axis-expression-followup/owned.py', 'bytes': 29385, 'sha256': '5ea93ef940f854c6510b19cc2c36df39183212b5026f725ee416f2a3cac48e59'}
    assert helper_binding['priorCorrectionSeal'] == {'path': 'verification/github-delivery-android-view-api-boundary/preparation-correction-seal.json', 'sha256': 'db9df0c6a412b6ee1047c6abb431941823858f08f42c07d154b5cf405659ffe3'}
    assert helper_binding['independentReviewSeal'] == {'path': 'verification/android-view-api-git-custody-review/review-seal.json', 'sha256': '1c67d7aef5cc9602b6127b4fad4471eab2d2e8081b3214c0689e55646a75ed0a'}
    assert row(ROOT / helper_binding['path'])['sha256'] == HELPER_SHA
    assert helper_binding['guardedControlsInherited'] == 44
    assert selected_row(helper_binding['baselineRepinEvidence']) == helper_binding['baselineRepinEvidence']
    assert row(ROOT / helper_binding['priorHelper']['path']) == helper_binding['priorHelper']
    assert row(ROOT / helper_binding['priorCorrectionSeal']['path'])['sha256'] == helper_binding['priorCorrectionSeal']['sha256']
    assert row(ROOT / helper_binding['independentReviewSeal']['path'])['sha256'] == helper_binding['independentReviewSeal']['sha256']
    assert helper_binding['currentRootReview'] == 'verification/android-axis-binding-selection-2026-10-29/helper-review.json'
    assert helper_binding['currentRootReview'] in SELECTED
    assert helper_binding['exactArgvApprovalBeforeEveryActualPhase'] is True
    assert helper_binding['separateWorkflowPhaseAuthorityRequired'] is True
    assert row(OUT / 'owned.py')['sha256'] == HELPER_SHA
    assert row(ROOT / INSPECTION_SOURCE['path']) == INSPECTION_SOURCE
    assert row(ROOT / RECOVERY_INPUTS_ROW['path']) == RECOVERY_INPUTS_ROW
    assert row(ROOT / INSPECTION_ARGV_ROW['path']) == INSPECTION_ARGV_ROW
    inspection.historical_closure(RECOVERY_INPUTS)
    assert inspection.frozen_sources(RECOVERY_INPUTS, ORIGINAL_PRESERVATION) == {
        value['path']: {'oid': value['oid'], 'mode': value['mode']}
        for value in RECOVERY_INPUTS['expectedObjects']}



DRIVERS = ["selection_common_axis_binding.py","deliver_axis_binding.py","bind_engine_ci_axis_binding.py","bind_axis_ci_axis_binding.py","dispatch_axis_binding.py","bind_axis_run_axis_binding.py"]
ORDINARY_NAME = 'Owned engine checks'
PHASE_MANIFEST_FILENAMES = {'stage-recovery-delivery': 'argv-stage-recovery-delivery.json', 'stage-recovery-engine-ci-binding': 'argv-stage-recovery-engine-ci-binding.json', 'stage-recovery-axis-ci-binding': 'argv-stage-recovery-axis-ci-binding.json', 'stage-recovery-dispatch-axis': 'argv-stage-recovery-dispatch-axis.json', 'stage-recovery-bind-axis-run': 'argv-stage-recovery-bind-axis-run.json'}
def read_accepted_preflight_binding():
    # This future receipt binding is supplied only by root's actual phase authority.
    # Its exact hashes cannot be invented during source-only preparation.
    actual_authority = json.loads((OUT / 'authority.json').read_bytes())
    assert actual_authority['schema'] == 1 and actual_authority['authorized'] is True
    assert actual_authority['repository'] == 'snowdamiz/mixer' and actual_authority['branch'] == 'main'
    assert actual_authority['selection'] == row(ROOT / SELECTION)
    assert actual_authority['baseline'] == {'head': BASE, 'tree': TREE}
    binding = actual_authority['acceptedPreflight']
    assert binding == json.loads("{\"seal\":{\"path\":\"verification/github-delivery-axis-binding-followup/preflight-followup-root-review.json\",\"bytes\":8922,\"sha256\":\"751059417bbde1d7e83b0b81e370ae018338e059d6c4455bec34915ecfed55f0\"},\"rows\":[{\"path\":\"verification/github-delivery-axis-binding-followup/preflight-followup.json\",\"bytes\":4844,\"sha256\":\"8a6beb02997134fb4d28746e54b5a9007488f8f0c43ac133cccc3edc92d23d6d\"},{\"path\":\"verification/github-delivery-axis-binding-followup/preservation-followup-local.json\",\"bytes\":796999,\"sha256\":\"3f271725a13e546d28c466c71b58e9119ccae7f38c905c38283235ff327178f1\"},{\"path\":\"verification/github-delivery-axis-binding-followup/manifest-followup.json\",\"bytes\":29998,\"sha256\":\"1f924038ca7765559fc65e155c25ae59550dbb52b2bd8730d34bf54fe6e7a0a5\"},{\"path\":\"verification/github-delivery-axis-binding-followup/authority-snapshot-preflight-followup.json\",\"bytes\":3809,\"sha256\":\"b9d176a8602d700db685d9466f124dadda68a1f18658a37d0f0d0ac083b0054e\"},{\"path\":\"verification/github-delivery-axis-binding-followup/argv-preflight-axis-binding.json\",\"bytes\":5310,\"sha256\":\"9088a044b9d417c61fb48b11effd6718d2741157b15f29f68edb63dd17fe0417\"}]}")
    assert set(binding) == {'seal', 'rows'} and len(binding['rows']) == 5
    assert binding['seal']['path'] == 'verification/github-delivery-axis-binding-followup/preflight-followup-root-review.json'
    assert [value['path'] for value in binding['rows']] == [
        'verification/github-delivery-axis-binding-followup/preflight-followup.json',
        'verification/github-delivery-axis-binding-followup/preservation-followup-local.json',
        'verification/github-delivery-axis-binding-followup/manifest-followup.json',
        'verification/github-delivery-axis-binding-followup/authority-snapshot-preflight-followup.json',
        'verification/github-delivery-axis-binding-followup/argv-preflight-axis-binding.json']
    for expected in [binding['seal'], *binding['rows']]:
        assert set(expected) == {'path', 'bytes', 'sha256'}
        assert type(expected['bytes']) is int and expected['bytes'] > 0
        assert re.fullmatch('[0-9a-f]{64}', expected['sha256'])
        assert row(ROOT / expected['path']) == expected
    return binding


ACCEPTED_PREFLIGHT_BINDING = read_accepted_preflight_binding()
ACCEPTED_PREFLIGHT_SEAL = ACCEPTED_PREFLIGHT_BINDING['seal']
ACCEPTED_PREFLIGHT_ROWS = ACCEPTED_PREFLIGHT_BINDING['rows']

def read_accepted_inspection_binding():
    authority = json.loads((OUT / 'authority.json').read_bytes())
    binding = authority['acceptedInspection']
    assert set(binding) == {'seal', 'rows'} and len(binding['rows']) == 3
    assert binding['seal']['path'] == 'verification/github-delivery-axis-binding-stage-recovery/inspection-root-review.json'
    assert [value['path'] for value in binding['rows']] == [
        'verification/github-delivery-axis-binding-stage-recovery/inspection-receipt.json',
        'verification/github-delivery-axis-binding-stage-recovery/inspection-data.json',
        'verification/github-delivery-axis-binding-stage-recovery/authority-exact-inspection.json']
    for expected in [binding['seal'], *binding['rows']]:
        assert set(expected) == {'path', 'bytes', 'sha256'}
        assert type(expected['bytes']) is int and expected['bytes'] > 0
        assert type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}', expected['sha256'])
        assert row(ROOT / expected['path']) == expected
    return binding


ACCEPTED_INSPECTION_BINDING = read_accepted_inspection_binding()
ACCEPTED_INSPECTION_SEAL = ACCEPTED_INSPECTION_BINDING['seal']
ACCEPTED_INSPECTION_ROWS = ACCEPTED_INSPECTION_BINDING['rows']


def accepted_inspection():
    assert read_accepted_inspection_binding() == ACCEPTED_INSPECTION_BINDING
    seal = json.loads((ROOT / ACCEPTED_INSPECTION_SEAL['path']).read_bytes())
    assert seal['decision'] == 'accept-exact-ten-read-stage-recovery-inspection-result'
    assert seal['selection'] == row(ROOT / SELECTION)
    assert seal['baseline'] == {'head': BASE, 'tree': TREE}
    assert [seal['receipt'], seal['data'], seal['authority']] == ACCEPTED_INSPECTION_ROWS
    receipt = json.loads((ROOT / ACCEPTED_INSPECTION_ROWS[0]['path']).read_bytes())
    data = json.loads((ROOT / ACCEPTED_INSPECTION_ROWS[1]['path']).read_bytes())
    authority = json.loads((ROOT / ACCEPTED_INSPECTION_ROWS[2]['path']).read_bytes())
    assert receipt['decision'] == 'ten-read-inspection-complete-pending-independent-actual-review'
    assert receipt['selection'] == row(ROOT / SELECTION)
    assert receipt['source'] == INSPECTION_SOURCE
    assert receipt['helper'] == row(OUT / 'owned.py')
    assert receipt['inputs'] == RECOVERY_INPUTS_ROW
    assert receipt['argv'] == INSPECTION_ARGV_ROW
    assert receipt['authority'] == ACCEPTED_INSPECTION_ROWS[2]
    assert receipt['data'] == ACCEPTED_INSPECTION_ROWS[1]
    assert receipt['failedAttemptReviewSeal'] == RECOVERY_INPUTS['failedReviewSeal']
    assert receipt['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True
    assert receipt['stageCommitPushDispatchPerformed'] is False and receipt['originalAttemptReplayed'] is False
    assert receipt['continuationAuthorized'] is False and receipt['allExistingHoldsUntouched'] is True
    assert authority['purpose'] == 'fresh-stage-recovery-inspection-only' and authority['authorized'] is True
    assert authority['source'] == receipt['source'] and authority['helper'] == receipt['helper']
    assert authority['inputs'] == receipt['inputs'] and authority['argvApproval'] == receipt['argv']
    assert seal['pendingChangedPaths'] == receipt['pendingChangedPaths'] == 66
    assert seal['remainingSourceIndexPaths'] == receipt['remainingSourceIndexPaths'] == 57
    assert seal['unrelatedStagedPaths'] == 0 and seal['stageCommitPushDispatchPerformed'] is False
    assert seal['continuationAuthorized'] is False
    assert row(ROOT / seal['independentActualReview']['path']) == seal['independentActualReview']
    assert authority['stageLimit'] == authority['commitLimit'] == authority['nonforcePushLimit'] == authority['manualWorkflowDispatchLimit'] == 0
    assert authority['originalAttemptReplayAllowed'] is False
    argv = json.loads((ROOT / INSPECTION_ARGV_ROW['path']).read_bytes())
    assert len(receipt['commands']) == len(seal['commands']) == 10
    assert [value['name'] for value in receipt['commands']] == [
        'stage-recovery-inspection-' + name for name in inspection.NAMES]
    command_rows = []
    for summary, command in zip(receipt['commands'], argv['commands']):
        label = summary['name']
        expected_row = row(OUT / (label + '.command.json'))
        command_rows.append({'name': command['name'], 'command': expected_row,
            'exactArgv': True, 'exit': 0, 'admitted': True, 'exactKernelReap': True,
            'groupAbsent': True, 'stdoutEOF': True, 'stderrEOF': True, 'signals': 0, 'authorityRetired': True})
        terminal = json.loads((ROOT / expected_row['path']).read_bytes())
        assert terminal['argv'] == command['effectiveArgv']
        assert terminal['authoritySHA256'] == ACCEPTED_INSPECTION_ROWS[2]['sha256']
        assert terminal['exit'] == 0 and terminal['rawWaitStatus'] == 0
        assert terminal['rawWaitPID'] == terminal['ownedPID'] == terminal['ownedPGID']
        assert terminal['identity'] == dict.fromkeys(('pid', 'pgid', 'sid'), terminal['ownedPID'])
        for name in ('admitted', 'directChildReaped', 'ownedGroupAbsent', 'stdoutEOF', 'stderrEOF',
                     'signalAuthorityRetired', 'separateOutputPipes', 'finalReapAttempted',
                     'implicitPopenReapingDisabled', 'noSignalAfterFinalReapOrLostAuthority'):
            assert terminal[name] is True
        assert terminal['postReapAbsenceProbeCount'] == 1 and terminal['signals'] == []
        assert terminal['signalAuthorityLost'] is None and terminal['stopReason'] is None and terminal['failure'] is None
        assert terminal['sensitiveOutputRejected'] is False
        assert summary == {'name': label, **{name: terminal[name] for name in (
            'exit', 'admitted', 'stopReason', 'directChildReaped', 'ownedGroupAbsent',
            'stdoutEOF', 'stderrEOF', 'sensitiveOutputRejected')}}
        for stream in ('stdout', 'stderr'):
            assert row(ROOT / terminal[stream]['path']) == terminal[stream]
    assert seal['commands'] == command_rows
    assert data['head'] == BASE and data['tree'] == TREE
    assert data['selectedPaths'] == 123 and data['allSelectedObjectDigestSHA256'] == OBJECT_SHA
    assert data['allSourceBytesModesUnchanged'] is True and data['unrelatedStagedPaths'] == 0
    assert data['originalPreservation'] == ACCEPTED_PREFLIGHT_ROWS[1]
    assert data['remainingConfinedToKnownIgnored57'] is True
    cached_raw = (OUT / 'stage-recovery-inspection-index-raw.stdout').read_bytes()
    assert inspection.raw_rows(cached_raw) == data['cachedRawRows']
    assert inspection.index_rows((OUT / 'stage-recovery-inspection-index-selected.stdout').read_bytes(), SELECTED) == data['selectedIndexObjects']
    assert inspection.raw_rows((OUT / 'stage-recovery-inspection-worktree-raw.stdout').read_bytes()) == data['completeWorktreeRawRows']
    assert inspection.collapsed((OUT / 'stage-recovery-inspection-collapsed-status.stdout').read_bytes()) == data['collapsedStatus']
    pending = {}
    expected_objects = {value['path']: {'oid': value['oid'], 'mode': value['mode']} for value in RECOVERY_INPUTS['expectedObjects']}
    for entry in data['cachedRawRows']:
        fields, value = entry['gitRaw'].split(), entry['path']
        assert value in SELECTED and fields[4] in ('A', 'M')
        assert {'oid': fields[3], 'mode': fields[1]} == expected_objects[value] == data['selectedIndexObjects'][value]
        pending[value] = expected_objects[value]
    assert pending == data['pendingChangedObjects']
    return receipt, data, cached_raw


PHASE_SCHEMA = json.loads("{\"stage-recovery-delivery\":{\"session\":{\"seconds\":240,\"count\":23,\"prefix\":\"stage-recovery-delivery-\"},\"commands\":[\"head\",\"branch\",\"origin\",\"push-url-before-stage\",\"remote-before\",\"index-before\",\"before-diff\",\"stage\",\"index-selected\",\"staged-objects\",\"authored-check\",\"staged-diff\",\"commit\",\"committed-head\",\"committed-objects\",\"remote-prepush\",\"push-url-prepush\",\"push\",\"remote-postpush\",\"push-url-postpush\",\"index-after\",\"after-diff\",\"collapsed-status-after\"],\"manualKey\":null},\"stage-recovery-engine-ci-binding\":{\"session\":{\"seconds\":180,\"count\":5,\"prefix\":\"stage-recovery-engine-ci-binding-\"},\"commands\":[\"head\",\"remote-main\",\"engine-workflow-content\",\"engine-workflow-registration\",\"engine-run\"],\"manualKey\":null},\"stage-recovery-axis-ci-binding\":{\"session\":{\"seconds\":180,\"count\":5,\"prefix\":\"stage-recovery-axis-ci-binding-\"},\"commands\":[\"head\",\"remote-main\",\"axis-workflow-content\",\"axis-workflow-registration\",\"axis-before-runs\"],\"manualKey\":\"axis\"},\"stage-recovery-dispatch-axis\":{\"session\":{\"seconds\":210,\"count\":7,\"prefix\":\"stage-recovery-dispatch-axis-\"},\"commands\":[\"head\",\"axis-workflow-content\",\"axis-workflow-registration\",\"axis-before-runs\",\"remote-predispatch\",\"dispatch\",\"axis-after-runs\"],\"manualKey\":\"axis\"},\"stage-recovery-bind-axis-run\":{\"session\":{\"seconds\":120,\"count\":4,\"prefix\":\"stage-recovery-bind-axis-run-\"},\"commands\":[\"head\",\"remote-main\",\"axis-workflow-registration\",\"axis-runs\"],\"manualKey\":\"axis\"}}")


def admission_adapter_evidence():
    return {'source': row(OUT / 'selection_common_axis_binding.py'),
            'function': 'selected_read_admission_adapter', 'fragmentSHA256': ADAPTER_FRAGMENT_SHA256,
            'exactReadOnlyException': list(PUSH_URL_READ_EXCEPTION),
            'otherVectorsDelegateUnchangedToHelperSHA256': HELPER_SHA,
            'strictRootManifestMatchRequiredBeforeAdapter': True,
            'startupCustodyClosureOrSignalingChanged': False}


def accepted_preflight():
    assert row(ROOT / ACCEPTED_PREFLIGHT_SEAL['path']) == ACCEPTED_PREFLIGHT_SEAL
    assert read_accepted_preflight_binding() == ACCEPTED_PREFLIGHT_BINDING
    seal = json.loads((ROOT / ACCEPTED_PREFLIGHT_SEAL['path']).read_bytes())
    assert seal['decision'] == 'accept-exact-nine-command-preflight-result'
    assert seal['selection'] == row(ROOT / SELECTION)
    assert seal['baseline'] == {'head': BASE, 'tree': TREE}
    assert [seal['receipt'], seal['preservationSnapshotLocalOnly'], seal['manifest'], seal['authority'], seal['argv']] == ACCEPTED_PREFLIGHT_ROWS
    for expected in ACCEPTED_PREFLIGHT_ROWS:
        assert row(ROOT / expected['path']) == expected
    assert len(seal['commands']) == 9
    for command in seal['commands']:
        assert row(ROOT / command['command']['path']) == command['command']
        assert command['exactArgv'] is True and command['exit'] == 0 and command['admitted'] is True
        assert command['exactKernelReap'] is True and command['groupAbsent'] is True
        assert command['postReapAbsenceProbeCount'] == 1 and command['signals'] == []
        assert command['stdoutEOF'] is True and command['stderrEOF'] is True and command['signalAuthorityRetired'] is True
        assert command['authoritySHA256'] == ACCEPTED_PREFLIGHT_ROWS[3]['sha256']
    pre = json.loads((OLD / 'preflight-followup.json').read_bytes())
    preservation = json.loads((OLD / 'preservation-followup-local.json').read_bytes())
    manifest = json.loads((OLD / 'manifest-followup.json').read_bytes())
    assert pre['selection'] == row(ROOT / SELECTION) and pre['head'] == BASE and pre['tree'] == TREE
    assert pre['branch'] == 'main' and pre['origin'] == 'https://github.com/snowdamiz/mixer.git' and pre['originMain'] == BASE
    assert pre['selectedPaths'] == SELECTED_COUNT and pre['indexEmpty'] is True and pre['selectedByteModesVerified'] is True
    assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True
    assert pre['argvManifest'] == ACCEPTED_PREFLIGHT_ROWS[4] and pre['authoritySnapshot'] == ACCEPTED_PREFLIGHT_ROWS[3]
    assert pre['helper']['sha256'] == HELPER_SHA and pre['manualHostKeysReadOnly'] == ['axis']
    assert manifest['selection'] == row(ROOT / SELECTION) and manifest['paths'] == SELECTED_COUNT and manifest['members'] == ROWS
    assert preservation['cleanTrackedSnapshot']['head'] == BASE and preservation['cleanTrackedSnapshot']['tree'] == TREE
    assert {value['path'] for value in preservation['tracked']} == {value['path'] for value in PROTECTED}
    return pre, preservation


def check_stage_pathspec():
    path = OUT / 'paths-stage-recovery.nul'
    assert path.is_file() and not path.is_symlink()
    expected = b''.join(value.encode() + b'\0' for value in sorted(SELECTED))
    assert path.read_bytes() == expected, 'Exact frozen selected pathspec required'
    return row(path)


def check_driver_sources(authority):
    expected = authority['driverSources']
    assert {value['path'] for value in expected} == {str((OUT / name).relative_to(ROOT)) for name in DRIVERS}
    for value in expected:
        assert row(ROOT / value['path']) == value
    review_row = authority['sourceReview']
    assert review_row['path'] == 'verification/github-delivery-axis-binding-stage-recovery/review/continuation-source-review.json'
    assert row(ROOT / review_row['path']) == review_row
    review = json.loads((ROOT / review_row['path']).read_bytes())
    assert review['decision'] == 'accept-exact-stage-recovery-continuation-source'
    assert review['driverSources'] == expected
    assert review['helper'] == row(OUT / 'owned.py')
    assert review['inspectionSource'] == INSPECTION_SOURCE
    assert review['argvApprovals'][authority['phase']] == authority['argvApprovals'][authority['phase']]


def bound_context():
    receipt_row = row(OUT / 'stage-recovery-delivery-receipt.json')
    assert json.loads((OUT / 'authority.json').read_bytes())['acceptedDelivery'] == receipt_row
    value = json.loads((OUT / 'stage-recovery-delivery-receipt.json').read_bytes())
    assert value['pushed'] is True and value['indexEmpty'] is True and value['selectedPaths'] == SELECTED_COUNT and value['force'] is False
    assert value['selection'] == row(ROOT / SELECTION) and value['parent'] == BASE
    assert value['preflightSeal'] == ACCEPTED_PREFLIGHT_SEAL and value['preflight'] == ACCEPTED_PREFLIGHT_ROWS[0]
    assert value['preservationBefore'] == ACCEPTED_PREFLIGHT_ROWS[1]
    assert re.fullmatch('[0-9a-f]{40}', value['head']) and re.fullmatch('[0-9a-f]{40}', value['tree'])
    assert value['acceptedInspectionSeal'] == ACCEPTED_INSPECTION_SEAL
    assert value['acceptedInspectionRows'] == ACCEPTED_INSPECTION_ROWS
    assert value['allSelectedIndexBlobModesVerified'] is True
    assert value['selectedIndexBlobModeDigestSHA256'] == OBJECT_SHA
    return {'DELIVERED_SHA': value['head']}


def manual_binding(key):
    assert key in ('axis',)
    source = S['manualHosts'][key]
    return {'key': key, 'descriptor': source, 'template': row(ROOT / source['selectionTemplate'])}


def dispatch_input(key, head):
    assert key in ('axis',) and re.fullmatch('[0-9a-f]{40}', head)
    source = S['manualHosts'][key]
    binding = manual_binding(key)
    before = json.loads((ROOT / source['selectionTemplate']).read_bytes())
    assert binding['template'] == {k: v for k, v in next(value for value in ROWS if value['path'] == source['selectionTemplate']).items() if k != 'mode'}
    assert source['inputJSONField'] == 'root_selection' and source['additionalInputs'] == {'profile': 'axis-refusal-host-v1'}
    assert before['selected'] is False and before['dispatch_authorized'] is False and before['source_revision'] is None and before['run_id'] is None
    assert before['workflow_path'] == source['workflow'] and before['workflow_sha256'] == source['workflowSHA256']
    assert before['max_manual_dispatches'] == 1 and before['max_run_attempt'] == 1
    after = {**before, 'selected': True, 'dispatch_authorized': True, 'source_revision': head}
    assert set(after) == set(before) and after['run_id'] is None
    assert {name for name in before if before[name] != after[name]} == {'selected', 'dispatch_authorized', 'source_revision'}
    return json.dumps(after, sort_keys=True, separators=(',', ':'))


def expected_dispatch_vector(key, head):
    source = S['manualHosts'][key]
    result = ['gh', 'workflow', 'run', source['workflow'].rsplit('/', 1)[1], '--repo', 'github.com/snowdamiz/mixer', '--ref', 'main']
    if key == 'axis':
        result += ['--raw-field', 'profile=axis-refusal-host-v1']
    result += ['--raw-field', source['inputJSONField'] + '=' + dispatch_input(key, head)]
    return result


def reject_gh_read_flags(argv):
    if argv[:2] == ['gh', 'api']:
        assert len(argv) == 7 and argv[3:6] == ['--hostname', 'github.com', '--jq']
        assert argv[2].startswith('repos/snowdamiz/mixer/') and not argv[2].startswith('-')
        blocked = ('--method', '--input', '--field', '--raw-field', '-X', '-f', '-F')
        assert not any(arg.startswith(blocked) for arg in argv[2:]), 'Read-call mutation flags forbidden'
    elif argv[0] == 'gh' and argv[1] != 'workflow':
        assert argv == ['gh', '--version']


class StrictCommands:
    def __init__(self, phase, context=None):
        assert phase in PHASE_SCHEMA
        check_sources()
        accepted_preflight()
        accepted_inspection()
        self.phase = phase
        self.schema = PHASE_SCHEMA[phase]
        self.manifest_name = PHASE_MANIFEST_FILENAMES.get(phase, 'argv-' + phase + '.json')
        self.manifest_row = row(OUT / self.manifest_name)
        self.manifest = json.loads((OUT / self.manifest_name).read_bytes())
        assert self.manifest['phase'] == phase and self.manifest['selection'] == row(ROOT / SELECTION)
        raw_authority = (OUT / 'authority.json').read_bytes()
        self.authority = json.loads(raw_authority)
        assert self.authority['schema'] == 1 and self.authority['authorized'] is True
        assert self.authority['repository'] == 'snowdamiz/mixer' and self.authority['branch'] == 'main'
        assert self.authority['selection'] == row(ROOT / SELECTION)
        assert self.authority['baseline'] == {'head': BASE, 'tree': TREE}
        assert self.authority['selectedPathsIncludingSelf'] == SELECTED_COUNT
        assert self.authority['phase'] == phase and self.authority['phaseLimit'] == 1
        assert self.authority['originalAttemptReplayAllowed'] is False
        delivery = phase == 'stage-recovery-delivery'
        dispatch = phase == 'stage-recovery-dispatch-axis'
        assert self.authority['stageLimit'] == self.authority['commitLimit'] == self.authority['nonforcePushLimit'] == int(delivery)
        assert self.authority['manualWorkflowDispatchLimit'] == int(dispatch)
        assert self.authority['manualWorkflowDispatchLimits'] == {'axis': int(dispatch), 'package': 0}
        assert self.authority['retryRerunFallbackAllowed'] is False
        assert self.authority['helper'] == row(OUT / 'owned.py')
        assert self.authority['inspectionSource'] == INSPECTION_SOURCE
        if delivery:
            assert self.authority['acceptedDelivery'] is None
        else:
            assert self.authority['acceptedDelivery'] == row(OUT / 'stage-recovery-delivery-receipt.json')
        assert self.authority['argvApprovals'][phase] == self.manifest_row
        check_driver_sources(self.authority)
        self.admission_adapter = admission_adapter_evidence()
        assert self.authority['admissionAdapter'] == self.admission_adapter
        key = self.schema['manualKey']
        if key is not None:
            assert self.manifest['manualHostBinding'] == manual_binding(key)
            assert self.authority['manualHostPhaseBindings'][phase] == manual_binding(key)
        self.context = dict(context or {})
        expected_context = set() if phase == 'stage-recovery-delivery' else {'DELIVERED_SHA'}
        if phase.startswith('stage-recovery-dispatch-'):
            expected_context.add('AXIS_DISPATCH_JSON')
        assert set(self.context) == expected_context
        for name, value in self.context.items():
            if name == 'DELIVERED_SHA':
                assert re.fullmatch('[0-9a-f]{40}', value)
            else:
                assert name == ('AXIS_DISPATCH_JSON')
                assert value == dispatch_input(key, self.context['DELIVERED_SHA'])
        self.expected = {value['name']: value for value in self.manifest['commands']}
        assert list(self.expected) == self.schema['commands'] and len(self.expected) == len(self.manifest['commands'])
        for value in self.expected.values():
            effective = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *value['argv'][1:]] if value['argv'][0] == 'git' else value['argv']
            assert value['effectiveArgv'] == effective
        self.used = set()
        limits = self.manifest['session']
        assert limits == self.schema['session']
        snapshot = OUT / ('authority-snapshot-' + phase + '.json')
        with snapshot.open('xb') as handle:
            handle.write(raw_authority)
            handle.flush()
            os.fsync(handle.fileno())
        directory = os.open(OUT, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try: os.fsync(directory)
        finally: os.close(directory)
        self.authority_row = row(snapshot)
        assert self.authority_row['sha256'] == owned.authority()
        self.commands = owned.Commands(limits['seconds'], limits['count'], limits['prefix'])

    def bind_committed_sha(self, head):
        assert self.phase == 'stage-recovery-delivery' and 'COMMITTED_SHA' not in self.context
        assert re.fullmatch('[0-9a-f]{40}', head)
        self.context['COMMITTED_SHA'] = head

    @property
    def records(self):
        return self.commands.records

    def vector(self, name):
        result = []
        for token in self.expected[name]['argv']:
            for key, value in self.context.items():
                token = token.replace('{' + key + '}', value)
            assert not re.search(r'\{(?:DELIVERED_SHA|COMMITTED_SHA|AXIS_DISPATCH_JSON)\}', token)
            result.append(token)
        reject_gh_read_flags(result)
        if result[:2] == ['gh', 'workflow']:
            key = self.schema['manualKey']
            assert self.phase == 'stage-recovery-dispatch-' + key and name == 'dispatch'
            assert result == expected_dispatch_vector(key, self.context['DELIVERED_SHA'])
        return result

    def run(self, name, argv=None, seconds=25):
        assert name not in self.used
        assert row(OUT / self.manifest_name) == self.manifest_row
        assert json.loads((OUT / 'authority.json').read_bytes()) == self.authority
        check_driver_sources(self.authority)
        check_sources()
        accepted_preflight()
        accepted_inspection()
        expected = self.vector(name)
        if argv is not None:
            assert argv == expected, 'Unapproved command vector'
        if name == 'stage':
            assert self.phase == 'stage-recovery-delivery'
            save('stage-recovery-pathspec-admission.json', {'at': now(), 'pathspec': check_stage_pathspec(), 'selection': row(ROOT / SELECTION), 'paths': SELECTED_COUNT, 'exactNULAllowlistChecked': True})
        self.used.add(name)
        return self.commands.run(name, expected, seconds)

    def complete(self):
        assert self.used == set(self.expected) and len(self.records) == len(self.expected)


def checked_ci_binding(head):
    r = json.loads((OUT / 'stage-recovery-delivery-receipt.json').read_bytes())
    b = json.loads((OUT / 'stage-recovery-axis-ci-binding.json').read_bytes())
    assert b['head'] == head and b['tree'] == r['tree']
    assert b['selection'] == row(ROOT / SELECTION) and b['delivery'] == row(OUT / 'stage-recovery-delivery-receipt.json')
    assert b['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True
    assert set(b['manuals']) == {'axis'} and b['manualDispatchesPerformed'] == 0
    for key in ('axis',):
        assert b['manuals'][key]['beforeCount'] == 0 and b['manuals'][key]['binding'] == manual_binding(key)
    return r, b


def validate_manual_run(key, manual, b, head):
    source = S['manualHosts'][key]
    assert type(manual['id']) is int and manual['id'] > 0
    assert manual['head_sha'] == head and manual['event'] == 'workflow_dispatch' and manual['run_attempt'] == 1
    assert manual['workflow_id'] == b['registrations'][key]['id'] and manual['path'] == source['workflow']
    assert manual['name'] == source['workflowName'] == b['registrations'][key]['name']


def save_manual_binding(key, manual, c, r, b, observed_later):
    stem = 'manual-' + key + '-stage-recovery'
    validate_manual_run(key, manual, b, r['head'])
    check_sources()
    save(stem + '-run-binding.json', {'schema': 1, 'at': now(), 'head': r['head'], 'tree': r['tree'],
         'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key),
         'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
         'input': row(OUT / (stem + '-input.json')), 'ciBinding': row(OUT / 'stage-recovery-axis-ci-binding.json'),
         'manual': manual, 'dispatches': 1, 'retries': 0, 'attempt': 1, 'observedInLaterReadOnlyPhase': observed_later,
         'expectedJobs': S['manualHosts'][key]['expectedJobs'], 'expectedJobName': S['manualHosts'][key]['expectedJobName'],
         'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row,
         'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
         'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
         'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False,
         'allExistingHoldsUntouched': True})


def dispatch_manual(key):
    assert key in ('axis',)
    stem = 'manual-' + key + '-stage-recovery'
    assert not (OUT / (stem + '-once.json')).exists(), 'This workflow allowance is already consumed'
    context = bound_context()
    head = context['DELIVERED_SHA']
    r, b = checked_ci_binding(head)
    token = 'AXIS_DISPATCH_JSON'
    context[token] = dispatch_input(key, head)
    c = StrictCommands('stage-recovery-dispatch-' + key, context)
    assert c.run('head').decode().splitlines() == [head, r['tree']]
    assert json.loads(c.run(key + '-workflow-content')) == b['contents'][key]
    assert json.loads(c.run(key + '-workflow-registration')) == b['registrations'][key]
    assert json.loads(c.run(key + '-before-runs')) == []
    save(stem + '-input.json', json.loads(context[token]))
    assert c.run('remote-predispatch').decode().split() == [head, 'refs/heads/main']
    submit = c.vector('dispatch')
    save(stem + '-once.json', {'schema': 1, 'at': now(), 'head': head, 'selection': row(ROOT / SELECTION),
         'manualHostBinding': manual_binding(key), 'ciBinding': row(OUT / 'stage-recovery-axis-ci-binding.json'),
         'input': row(OUT / (stem + '-input.json')), 'dispatchNonce': S['manualHosts'][key].get('dispatchNonce'),
         'argvSHA256': hashlib.sha256(json.dumps(submit, separators=(',', ':')).encode()).hexdigest(),
         'allowanceConsumedBeforeSubmit': True, 'dispatchLimit': 1, 'runAttemptLimit': 1, 'oldAllowancesReused': 0,
         'retryRerunFallbackAllowed': False, 'unknownOutcomeMustNeverBeRetried': True})
    c.run('dispatch', submit, seconds=45)
    save(stem + '-submitted.json', {'schema': 1, 'at': now(), 'head': head, 'selection': row(ROOT / SELECTION),
         'manualHostBinding': manual_binding(key), 'reservation': row(OUT / (stem + '-once.json')),
         'submitTerminal': c.records[-1], 'remoteRunBindingPending': True, 'retryAllowed': False})
    runs = json.loads(c.run(key + '-after-runs'))
    c.complete()
    if runs == []:
        save(stem + '-visibility-pending.json', {'schema': 1, 'at': now(), 'state': 'submitted-visibility-pending',
             'head': head, 'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key),
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'allowanceConsumed': True, 'retryAllowed': False, 'laterBindingReadOnlyAndSeparatelyAuthorized': True,
             'authoritySnapshot': c.authority_row, 'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
             'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True, 'runtimeResultsAccepted': False})
        print(json.dumps({'workflow': key, 'head': head, 'state': 'submitted-visibility-pending', 'allowanceConsumed': True, 'retryAllowed': False, 'closedCommands': len(c.records)}))
        return
    if len(runs) != 1:
        save(stem + '-visibility-ambiguous.json', {'schema': 1, 'at': now(), 'head': head,
             'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key),
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'visibleRuns': runs, 'allowanceConsumed': True, 'retryAllowed': False, 'commands': c.records})
        raise AssertionError('Selected workflow run not unique; allowance consumed; no dispatch retry')
    save_manual_binding(key, runs[0], c, r, b, False)
    print(json.dumps({'workflow': key, 'head': head, 'runID': runs[0]['id'], 'dispatches': 1, 'retries': 0, 'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))


def bind_manual_run(key):
    assert key in ('axis',)
    stem = 'manual-' + key + '-stage-recovery'
    assert not (OUT / (stem + '-run-binding.json')).exists()
    context = bound_context()
    head = context['DELIVERED_SHA']
    r, b = checked_ci_binding(head)
    once = json.loads((OUT / (stem + '-once.json')).read_bytes())
    submitted = json.loads((OUT / (stem + '-submitted.json')).read_bytes())
    pending = json.loads((OUT / (stem + '-visibility-pending.json')).read_bytes())
    for evidence in (once, submitted, pending):
        assert evidence['head'] == head and evidence['selection'] == row(ROOT / SELECTION)
        assert evidence['manualHostBinding'] == manual_binding(key)
    assert once['allowanceConsumedBeforeSubmit'] is True and once['dispatchLimit'] == 1
    assert submitted['reservation'] == row(OUT / (stem + '-once.json')) and submitted['retryAllowed'] is False
    assert pending['state'] == 'submitted-visibility-pending' and pending['allowanceConsumed'] is True and pending['retryAllowed'] is False
    assert pending['reservation'] == row(OUT / (stem + '-once.json')) and pending['submitted'] == row(OUT / (stem + '-submitted.json'))
    c = StrictCommands('stage-recovery-bind-' + key + '-run', context)
    assert c.run('head').decode().splitlines() == [head, r['tree']]
    assert c.run('remote-main').decode().split() == [head, 'refs/heads/main']
    assert json.loads(c.run(key + '-workflow-registration')) == b['registrations'][key]
    runs = json.loads(c.run(key + '-runs'))
    c.complete()
    if runs == []:
        save(stem + '-observation-pending.json', {'schema': 1, 'at': now(), 'state': 'submitted-visibility-pending',
             'head': head, 'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key),
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'allowanceConsumed': True, 'retryAllowed': False, 'dispatchesPerformed': 0,
             'authoritySnapshot': c.authority_row, 'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
             'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True, 'runtimeResultsAccepted': False})
        print(json.dumps({'workflow': key, 'state': 'submitted-visibility-pending', 'dispatchesPerformed': 0, 'retryAllowed': False, 'closedCommands': len(c.records)}))
        return
    assert len(runs) == 1, 'Read-only run binding ambiguous; no dispatch retry'
    save_manual_binding(key, runs[0], c, r, b, True)
    print(json.dumps({'workflow': key, 'head': head, 'runID': runs[0]['id'], 'dispatchesPerformed': 0, 'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))
