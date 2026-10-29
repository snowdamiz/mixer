"""Package-only continuation from independent root evidence; no axis or CI-read phase."""
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
BASE = '47b62878bae3aa3d4dff5d565b63f4a533e7abde'
TREE = '898ebb228b5d9dbd9dc1cc012479496c468dbee2'
SELECTION = 'verification/android-host-followup-selection-2026-10-29/selection.json'
SELECTION_SHA = '7bb6b03c7250933ec51fd18b8c748135db3fdc418705203f759bed39bd8e8dab'
SELECTION_BYTES = 71593
SELECTED_COUNT = 256
HELPER_SHA = '30519c17fad93ddb4d70f1d217d3033f3890c2ce3b656cb25e424d102e2ddbbf'
raw_helper = (OUT / 'owned.py').read_bytes()
assert hashlib.sha256(raw_helper).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location('android_host_followup_package_continuation_owned', OUT / 'owned.py')
owned = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = owned
spec.loader.exec_module(owned)
ORIGINAL_VALIDATE_ARGV = owned.validate_argv
PUSH_URL_READ_EXCEPTION = ('git', 'remote', 'get-url', '--push', '--all', 'origin')


def selected_read_admission_adapter(argv):
    if isinstance(argv, (list, tuple)) and tuple(argv) == PUSH_URL_READ_EXCEPTION:
        return True
    return ORIGINAL_VALIDATE_ARGV(argv)


owned.validate_argv = selected_read_admission_adapter
ADAPTER_FRAGMENT_SHA256 = '2d88ec37fed744df317fb5c933eb7f5505c852a39434273b1234416f8661a94c'
row, save, now = owned.row, owned.save, owned.now
assert row(ROOT / SELECTION) == {'path': SELECTION, 'bytes': SELECTION_BYTES, 'sha256': SELECTION_SHA}
S = json.loads((ROOT / SELECTION).read_bytes())
assert S['baseline'] == {'revision': BASE, 'tree': TREE}
assert S['repository'] == 'snowdamiz/mixer' and S['branch'] == 'main' and S['remote'] == 'origin'
assert S['includeSelectionItself'] == SELECTION and S['selectedCountIncludingSelf'] == SELECTED_COUNT
assert len(S['selectedRows']) == SELECTED_COUNT - 1
assert set(S['manualHosts']) == {'axis', 'package'}
for source in S['manualHosts'].values():
    assert source['dispatches'] == 1 and source['retries'] == 0 and source['attempt'] == 1
    assert source['actualDispatched'] == 0 and source['expectedJobs'] == 1
    assert source['consumeAllowanceBeforeDispatch'] is True and source['unknownOutcomeReplay'] is False
    assert source['bindDeliveredSHAThenEnableSelection'] is True
assert S['rootReviewSHA256'] == 'cb1082b0449d610c813fb1fc42790af467a8b77192442e491265e26957de6fa7'


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
    assert helper_binding['path'] == str((OUT / 'owned.py').relative_to(ROOT))
    assert helper_binding['sha256'] == HELPER_SHA
    assert helper_binding['baselineRepinEvidence'] == {'path': 'verification/github-delivery-android-host-followup/preparation.json', 'bytes': 4984, 'sha256': '6bdc21383022f1868b5b08690f9ec48affd1e37ca5ae398228351a6970fb0f21', 'mode': '100644'}
    assert helper_binding['priorHelper'] == {'path': 'verification/github-delivery-android-jdk-observation/owned.py', 'bytes': 29385, 'sha256': 'b7b4a4fab5ca699ded6efd65259c9e499babbe37786a108d7307dfc0d29ab043'}
    assert helper_binding['priorCorrectionSeal'] == {'path': 'verification/github-delivery-android-view-api-boundary/preparation-correction-seal.json', 'sha256': 'db9df0c6a412b6ee1047c6abb431941823858f08f42c07d154b5cf405659ffe3'}
    assert helper_binding['independentReviewSeal'] == {'path': 'verification/android-view-api-git-custody-review/review-seal.json', 'sha256': '1c67d7aef5cc9602b6127b4fad4471eab2d2e8081b3214c0689e55646a75ed0a'}
    assert row(ROOT / helper_binding['path'])['sha256'] == HELPER_SHA
    assert selected_row(helper_binding['baselineRepinEvidence']) == helper_binding['baselineRepinEvidence']
    assert row(ROOT / helper_binding['priorHelper']['path']) == helper_binding['priorHelper']
    assert row(ROOT / helper_binding['priorCorrectionSeal']['path'])['sha256'] == helper_binding['priorCorrectionSeal']['sha256']
    assert row(ROOT / helper_binding['independentReviewSeal']['path'])['sha256'] == helper_binding['independentReviewSeal']['sha256']
    assert helper_binding['currentRootReview'] == 'verification/android-host-followup-selection-2026-10-29/helper-review.json'
    assert helper_binding['currentRootReview'] in SELECTED
    assert helper_binding['exactArgvApprovalBeforeEveryActualPhase'] is True
    assert helper_binding['separateWorkflowPhaseAuthorityRequired'] is True


DRIVERS = ["selection_common_package_continuation.py","dispatch_package_continuation.py","bind_package_run_continuation.py"]
ACCEPTED_PREFLIGHT_SEAL = {"path":"verification/github-delivery-android-host-followup/preflight-followup-root-review.json","bytes":7969,"sha256":"d9bcb597aebb1ffd887a396021bdad49687a3ef4654a9cb220b93698981dfc35"}
ACCEPTED_PREFLIGHT_ROWS = [{"path":"verification/github-delivery-android-host-followup/preflight-followup.json","bytes":4856,"sha256":"e05e75171ed595c68c7b682b908c74da22165d06b406f2718776257d5329c0f5"},{"path":"verification/github-delivery-android-host-followup/preservation-followup-local.json","bytes":789962,"sha256":"79511da7418f96e6f9ff3bfa31f8238d4a49d3d7f13b3cc32464a36fb9d23ef3"},{"path":"verification/github-delivery-android-host-followup/manifest-followup.json","bytes":64342,"sha256":"1812c6f95f96d18111084736f0e1ad7fb20416976674c810c25690bbbf094f24"},{"path":"verification/github-delivery-android-host-followup/authority-snapshot-preflight-followup.json","bytes":3243,"sha256":"b9cd9ccebe067f47f816b034aa910526995f74484b5ec411882dce7be4249bb8"},{"path":"verification/github-delivery-android-host-followup/argv-preflight-followup.json","bytes":5599,"sha256":"5580efa81da86c7bb3201ce1abf2aca5b406348c30b4771a6bdd59300bff4dad"}]
PHASE_SCHEMA = json.loads("{\"dispatch-package-followup\":{\"session\":{\"seconds\":210,\"count\":7,\"prefix\":\"dispatch-package-followup-\"},\"commands\":[\"head\",\"package-workflow-content\",\"package-workflow-registration\",\"package-before-runs\",\"remote-predispatch\",\"dispatch\",\"package-after-runs\"],\"manualKey\":\"package\"},\"bind-package-run-followup\":{\"session\":{\"seconds\":120,\"count\":4,\"prefix\":\"bind-package-run-followup-\"},\"commands\":[\"head\",\"remote-main\",\"package-workflow-registration\",\"package-runs\"],\"manualKey\":\"package\"}}")
PACKAGE_BINDING_ROW = {"path":"verification/github-delivery-android-host-followup/independent-package-binding.json","bytes":12343,"sha256":"e3445b1e315e350e9483b9cd1a573468976d5626ca85bbb918448e27b98a301b"}
DELIVERY_RECEIPT_ROW = {"path":"verification/github-delivery-android-host-followup/delivery-followup-receipt.json","bytes":13955,"sha256":"95272f2d96ca57755cf6a6fee61f8c8e1b22768bb0e8dd6c256743a197e9be20"}
PACKAGE_REFUSAL_ROW = {"path":"verification/github-delivery-android-host-followup/ci-binding-followup-refusal.json","bytes":7924,"sha256":"1ffff0fe44bc2c0a39cb4ff383c5ddc5c116267ca01e2c8e6c4305a009c88e01"}
PACKAGE_RUN_OBSERVATION_ROW = {"path":"verification/github-delivery-android-host-followup/connector-run-observation-followup.json","bytes":1325,"sha256":"abd10f179e41a15e81cf4b784303efaf8abe6c45e0dc7c6db64a960a2f548d17"}
DELIVERED_HEAD = 'c89b4d1657fc46581d8788169f9c961a2413c4f4'
DELIVERED_TREE = '507ff501dbb8130ce37632eb3b207f5990f3689c'
PACKAGE_MANIFESTS = {"dispatch-package-followup":{"path":"verification/github-delivery-android-host-followup/argv-dispatch-package-followup.json","bytes":9958,"sha256":"827621b9eb2569091c0dca3af40d7098726ddcdf05dfd03c69f11ca0bcc7de5f"},"bind-package-run-followup":{"path":"verification/github-delivery-android-host-followup/argv-bind-package-run-followup.json","bytes":7544,"sha256":"f510988193da3a900dca0dc86245386e20ed7675bb9b72d2eff767d67d7b9c0e"}}


def admission_adapter_evidence():
    return {'source': row(OUT / 'selection_common_package_continuation.py'),
            'function': 'selected_read_admission_adapter', 'fragmentSHA256': ADAPTER_FRAGMENT_SHA256,
            'exactReadOnlyException': list(PUSH_URL_READ_EXCEPTION),
            'otherVectorsDelegateUnchangedToHelperSHA256': HELPER_SHA,
            'strictRootManifestMatchRequiredBeforeAdapter': True,
            'startupCustodyClosureOrSignalingChanged': False}


def accepted_preflight():
    assert row(ROOT / ACCEPTED_PREFLIGHT_SEAL['path']) == ACCEPTED_PREFLIGHT_SEAL
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
    pre = json.loads((OUT / 'preflight-followup.json').read_bytes())
    preservation = json.loads((OUT / 'preservation-followup-local.json').read_bytes())
    manifest = json.loads((OUT / 'manifest-followup.json').read_bytes())
    assert pre['selection'] == row(ROOT / SELECTION) and pre['head'] == BASE and pre['tree'] == TREE
    assert pre['branch'] == 'main' and pre['origin'] == 'https://github.com/snowdamiz/mixer.git' and pre['originMain'] == BASE
    assert pre['selectedPaths'] == SELECTED_COUNT and pre['indexEmpty'] is True and pre['selectedByteModesVerified'] is True
    assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True
    assert pre['argvManifest'] == ACCEPTED_PREFLIGHT_ROWS[4] and pre['authoritySnapshot'] == ACCEPTED_PREFLIGHT_ROWS[3]
    assert pre['helper']['sha256'] == HELPER_SHA and pre['manualHostKeysReadOnly'] == ['axis', 'package']
    assert manifest['selection'] == row(ROOT / SELECTION) and manifest['paths'] == SELECTED_COUNT and manifest['members'] == ROWS
    assert preservation['cleanTrackedSnapshot']['head'] == BASE and preservation['cleanTrackedSnapshot']['tree'] == TREE
    assert {value['path'] for value in preservation['tracked']} == {value['path'] for value in PROTECTED}
    return pre, preservation


def check_driver_sources(authority):
    expected = authority['driverSources']
    assert {value['path'] for value in expected} == {str((OUT / name).relative_to(ROOT)) for name in DRIVERS}
    for value in expected:
        assert row(ROOT / value['path']) == value


def bound_context():
    assert row(ROOT / DELIVERY_RECEIPT_ROW['path']) == DELIVERY_RECEIPT_ROW
    value = json.loads((ROOT / DELIVERY_RECEIPT_ROW['path']).read_bytes())
    assert value['head'] == DELIVERED_HEAD and value['tree'] == DELIVERED_TREE
    assert value['pushed'] is True and value['indexEmpty'] is True and value['selectedPaths'] == SELECTED_COUNT and value['force'] is False
    assert value['selection'] == row(ROOT / SELECTION) and value['parent'] == BASE
    assert value['preflightSeal'] == ACCEPTED_PREFLIGHT_SEAL and value['preflight'] == ACCEPTED_PREFLIGHT_ROWS[0]
    assert value['preservationBefore'] == ACCEPTED_PREFLIGHT_ROWS[1]
    assert re.fullmatch('[0-9a-f]{40}', value['head']) and re.fullmatch('[0-9a-f]{40}', value['tree'])
    return {'DELIVERED_SHA': value['head']}


def manual_binding(key):
    assert key == 'package'
    source = S['manualHosts'][key]
    return {'key': key, 'descriptor': source, 'template': row(ROOT / source['selectionTemplate'])}


def dispatch_input(key, head):
    assert key == 'package' and re.fullmatch('[0-9a-f]{40}', head)
    source = S['manualHosts']['package']
    binding = manual_binding(key)
    before = json.loads((ROOT / source['selectionTemplate']).read_bytes())
    assert binding['template'] == {k: v for k, v in next(value for value in ROWS if value['path'] == source['selectionTemplate']).items() if k != 'mode'}
    assert source['inputJSONField'] == 'root_selection_json' and source['additionalInputs'] == {}
    assert before['dispatch_selected'] is False
    expected = source['exactSelectionBindings']
    assert set(expected) == set(before) and expected['github_sha'] == '<delivered SHA>'
    assert re.fullmatch('[0-9a-f]{64}', source['dispatchNonce']) and expected['dispatch_nonce'] == source['dispatchNonce']
    assert expected['workflow_relative_path'] == source['workflow'] and expected['installed_workflow_sha256'] == source['workflowSHA256']
    assert source['oldFocusedAllowanceConsumed'] is True and source['oldDataObservationAllowanceConsumed'] is True
    after = {**expected, 'github_sha': head}
    assert after['dispatch_selected'] is True and after['dispatch_nonce'] == source['dispatchNonce']
    for name in ('purpose', 'candidate_freeze_sha256', 'inspector_seal_sha256', 'workflow_relative_path'):
        assert after[name] == before[name]
    return json.dumps(after, sort_keys=True, separators=(',', ':'))


def expected_dispatch_vector(key, head):
    assert key == 'package'
    source = S['manualHosts']['package']
    return ['gh', 'workflow', 'run', source['workflow'].rsplit('/', 1)[1], '--repo', 'github.com/snowdamiz/mixer', '--ref', 'main', '--raw-field', source['inputJSONField'] + '=' + dispatch_input(key, head)]


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
        self.phase = phase
        self.schema = PHASE_SCHEMA[phase]
        self.manifest_name = 'argv-' + phase + '.json'
        self.manifest_row = row(OUT / self.manifest_name)
        assert self.manifest_row == PACKAGE_MANIFESTS[phase]
        self.manifest = json.loads((OUT / self.manifest_name).read_bytes())
        assert self.manifest['phase'] == phase and self.manifest['selection'] == row(ROOT / SELECTION)
        raw_authority = (OUT / 'authority.json').read_bytes()
        self.authority = json.loads(raw_authority)
        assert self.authority['schema'] == 1 and self.authority['authorized'] is True
        assert self.authority['repository'] == 'snowdamiz/mixer' and self.authority['branch'] == 'main'
        assert self.authority['selection'] == row(ROOT / SELECTION)
        assert self.authority['baseline'] == {'head': BASE, 'tree': TREE}
        assert self.authority['selectedPathsIncludingSelf'] == SELECTED_COUNT
        assert self.authority['argvApprovals'][phase] == self.manifest_row
        assert self.authority['independentPackageBinding'] == PACKAGE_BINDING_ROW
        assert set(self.authority['argvApprovals']).issubset(PHASE_SCHEMA)
        assert set(self.authority['manualHostPhaseBindings']).issubset(PHASE_SCHEMA)
        check_driver_sources(self.authority)
        self.admission_adapter = admission_adapter_evidence()
        assert self.authority['admissionAdapter'] == self.admission_adapter
        key = self.schema['manualKey']
        if key is not None:
            assert self.manifest['manualHostBinding'] == manual_binding(key)
            assert self.authority['manualHostPhaseBindings'][phase] == manual_binding(key)
        self.context = dict(context or {})
        expected_context = {'DELIVERED_SHA'}
        if phase.startswith('dispatch-'):
            expected_context.add('PACKAGE_DISPATCH_JSON')
        assert set(self.context) == expected_context
        for name, value in self.context.items():
            if name == 'DELIVERED_SHA':
                assert re.fullmatch('[0-9a-f]{40}', value)
            else:
                assert name == ('PACKAGE_DISPATCH_JSON')
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

    @property
    def records(self):
        return self.commands.records

    def vector(self, name):
        result = []
        for token in self.expected[name]['argv']:
            for key, value in self.context.items():
                token = token.replace('{' + key + '}', value)
            assert not re.search(r'\{(?:DELIVERED_SHA|PACKAGE_DISPATCH_JSON)\}', token)
            result.append(token)
        reject_gh_read_flags(result)
        if result[:2] == ['gh', 'workflow']:
            key = self.schema['manualKey']
            assert self.phase == 'dispatch-' + key + '-followup' and name == 'dispatch'
            assert result == expected_dispatch_vector(key, self.context['DELIVERED_SHA'])
        return result

    def run(self, name, argv=None, seconds=25):
        assert name not in self.used
        assert row(OUT / self.manifest_name) == self.manifest_row
        assert json.loads((OUT / 'authority.json').read_bytes()) == self.authority
        check_driver_sources(self.authority)
        check_sources()
        accepted_preflight()
        assert row(ROOT / PACKAGE_BINDING_ROW['path']) == PACKAGE_BINDING_ROW
        expected = self.vector(name)
        if argv is not None:
            assert argv == expected, 'Unapproved command vector'
        self.used.add(name)
        return self.commands.run(name, expected, seconds)

    def complete(self):
        assert self.used == set(self.expected) and len(self.records) == len(self.expected)


def checked_ci_binding(head):
    # This is the independently reviewed package-only binding, not an 11-read completion.
    assert head == DELIVERED_HEAD
    assert row(ROOT / DELIVERY_RECEIPT_ROW['path']) == DELIVERY_RECEIPT_ROW
    assert row(ROOT / PACKAGE_BINDING_ROW['path']) == PACKAGE_BINDING_ROW
    r = json.loads((ROOT / DELIVERY_RECEIPT_ROW['path']).read_bytes())
    b = json.loads((ROOT / PACKAGE_BINDING_ROW['path']).read_bytes())
    assert b['schema'] == 1 and b['status'] == 'root-independent-package-only-binding-observed'
    assert b['head'] == head and b['tree'] == r['tree'] == DELIVERED_TREE
    assert b['selection'] == row(ROOT / SELECTION) and b['delivery'] == DELIVERY_RECEIPT_ROW
    assert b['eligibleManualWorkflowKeys'] == ['package'] and set(b['manuals']) == {'package'}
    assert set(b['contents']) == {'engine', 'package'} and set(b['registrations']) == {'engine', 'package'}
    assert b['completedPriorReadCommands'] == 8 and b['plannedFailedPhaseReadCommands'] == 11 and b['failedPhaseCompleted'] is False
    assert b['allEightSavedReadCommandsAdmittedReapedGroupsAbsentSeparateEOF'] is True and len(b['commands']) == 8
    assert b['axisWorkflowValidationAccepted'] is False and b['axisManualDispatchAuthorized'] is False
    assert b['manualDispatchesPerformed'] == 0 and b['manualReservationsCreated'] == 0 and b['dispatchAuthorityCreated'] is False
    assert b['requiresFreshPackageDispatchHeadRemoteContentRegistrationAndEmptyBeforeList'] is True
    assert b['oldFocusedAndDiagnosticAllowanceRemaining'] == 0 and b['runtimeResultsAccepted'] is False
    assert b['failedTwoWorkflowBinding'] == PACKAGE_REFUSAL_ROW and b['connectorRunObservation'] == PACKAGE_RUN_OBSERVATION_ROW
    for expected in (PACKAGE_REFUSAL_ROW, PACKAGE_RUN_OBSERVATION_ROW):
        assert row(ROOT / expected['path']) == expected
    refusal = json.loads((ROOT / PACKAGE_REFUSAL_ROW['path']).read_bytes())
    assert refusal['head'] == head and refusal['tree'] == DELIVERED_TREE
    assert refusal['closedCommands'] == 8 and refusal['plannedCommands'] == 11 and refusal['completedBindingReceiptExists'] is False
    assert refusal['manualDispatches'] == 0 and refusal['manualReservations'] == 0
    observed = json.loads((ROOT / PACKAGE_RUN_OBSERVATION_ROW['path']).read_bytes())
    assert observed['total_count'] == len(observed['runs']) == 2
    assert {value['id'] for value in observed['runs']} == {40883834822, 40883832500}
    assert all(value['head_sha'] == head and value['event'] == 'push' and value['run_attempt'] == 1 for value in observed['runs'])
    for command in b['commands']:
        assert row(ROOT / command['command']['path']) == command['command']
        assert command['exactArgv'] is True and command['admitted'] is True and command['exit'] == 0
        assert command['exactKernelReap'] is True and command['ownedGroupAbsent'] is True and command['postReapAbsenceProbeCount'] == 1
        assert command['stdoutEOF'] is True and command['stderrEOF'] is True and command['signalAuthorityRetired'] is True and command['signals'] == []
    source = S['manualHosts']['package']
    payload = (ROOT / source['workflow']).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == source['workflowSHA256']
    oid = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    assert b['contents']['package'] == {'path': source['workflow'], 'sha': oid, 'size': len(payload), 'type': 'file'}
    registration = b['registrations']['package']
    assert type(registration['id']) is int and registration['id'] > 0
    assert registration['path'] == source['workflow'] and registration['name'] == source['workflowName'] and registration['state'] == 'active'
    assert b['manuals']['package']['beforeCount'] == 0 and b['manuals']['package']['binding'] == manual_binding('package')
    return r, b


def validate_manual_run(key, manual, b, head):
    source = S['manualHosts'][key]
    assert type(manual['id']) is int and manual['id'] > 0
    assert manual['head_sha'] == head and manual['event'] == 'workflow_dispatch' and manual['run_attempt'] == 1
    assert manual['workflow_id'] == b['registrations'][key]['id'] and manual['path'] == source['workflow']
    assert manual['name'] == source['workflowName'] == b['registrations'][key]['name']


def save_manual_binding(key, manual, c, r, b, observed_later):
    stem = 'manual-' + key + '-followup'
    validate_manual_run(key, manual, b, r['head'])
    check_sources()
    save(stem + '-run-binding.json', {'schema': 1, 'at': now(), 'head': r['head'], 'tree': r['tree'],
         'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False,
         'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
         'input': row(OUT / (stem + '-input.json')),
         'manual': manual, 'dispatches': 1, 'retries': 0, 'attempt': 1, 'observedInLaterReadOnlyPhase': observed_later,
         'expectedJobs': S['manualHosts'][key]['expectedJobs'], 'expectedJobName': S['manualHosts'][key]['expectedJobName'],
         'admissionAdapter': c.admission_adapter, 'authoritySnapshot': c.authority_row,
         'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
         'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True,
         'runtimeResultsAccepted': False, 'artifactDownloaded': False, 'signedArtifactURLsStoredOrPrinted': False,
         'allExistingHoldsUntouched': True})


def dispatch_manual(key):
    assert key == 'package'
    stem = 'manual-' + key + '-followup'
    assert not (OUT / (stem + '-once.json')).exists(), 'This workflow allowance is already consumed'
    context = bound_context()
    head = context['DELIVERED_SHA']
    r, b = checked_ci_binding(head)
    token = 'PACKAGE_DISPATCH_JSON'
    context[token] = dispatch_input(key, head)
    c = StrictCommands('dispatch-' + key + '-followup', context)
    assert c.run('head').decode().splitlines() == [head, r['tree']]
    assert json.loads(c.run(key + '-workflow-content')) == b['contents'][key]
    assert json.loads(c.run(key + '-workflow-registration')) == b['registrations'][key]
    assert json.loads(c.run(key + '-before-runs')) == []
    save(stem + '-input.json', json.loads(context[token]))
    assert c.run('remote-predispatch').decode().split() == [head, 'refs/heads/main']
    submit = c.vector('dispatch')
    save(stem + '-once.json', {'schema': 1, 'at': now(), 'head': head, 'selection': row(ROOT / SELECTION),
         'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False,
         'input': row(OUT / (stem + '-input.json')), 'dispatchNonce': S['manualHosts'][key].get('dispatchNonce'),
         'argvSHA256': hashlib.sha256(json.dumps(submit, separators=(',', ':')).encode()).hexdigest(),
         'allowanceConsumedBeforeSubmit': True, 'dispatchLimit': 1, 'runAttemptLimit': 1, 'oldAllowancesReused': 0,
         'retryRerunFallbackAllowed': False, 'unknownOutcomeMustNeverBeRetried': True})
    c.run('dispatch', submit, seconds=45)
    save(stem + '-submitted.json', {'schema': 1, 'at': now(), 'head': head, 'selection': row(ROOT / SELECTION),
         'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False, 'reservation': row(OUT / (stem + '-once.json')),
         'submitTerminal': c.records[-1], 'remoteRunBindingPending': True, 'retryAllowed': False})
    runs = json.loads(c.run(key + '-after-runs'))
    c.complete()
    if runs == []:
        save(stem + '-visibility-pending.json', {'schema': 1, 'at': now(), 'state': 'submitted-visibility-pending',
             'head': head, 'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False,
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'allowanceConsumed': True, 'retryAllowed': False, 'laterBindingReadOnlyAndSeparatelyAuthorized': True,
             'authoritySnapshot': c.authority_row, 'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
             'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True, 'runtimeResultsAccepted': False})
        print(json.dumps({'workflow': key, 'head': head, 'state': 'submitted-visibility-pending', 'allowanceConsumed': True, 'retryAllowed': False, 'closedCommands': len(c.records)}))
        return
    if len(runs) != 1:
        save(stem + '-visibility-ambiguous.json', {'schema': 1, 'at': now(), 'head': head,
             'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False,
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'visibleRuns': runs, 'allowanceConsumed': True, 'retryAllowed': False, 'commands': c.records})
        raise AssertionError('Selected workflow run not unique; allowance consumed; no dispatch retry')
    save_manual_binding(key, runs[0], c, r, b, False)
    print(json.dumps({'workflow': key, 'head': head, 'runID': runs[0]['id'], 'dispatches': 1, 'retries': 0, 'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))


def bind_manual_run(key):
    assert key == 'package'
    stem = 'manual-' + key + '-followup'
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
        assert evidence['independentPackageBinding'] == PACKAGE_BINDING_ROW and evidence['axisManualDispatchAuthorized'] is False
    assert once['allowanceConsumedBeforeSubmit'] is True and once['dispatchLimit'] == 1
    assert submitted['reservation'] == row(OUT / (stem + '-once.json')) and submitted['retryAllowed'] is False
    assert pending['state'] == 'submitted-visibility-pending' and pending['allowanceConsumed'] is True and pending['retryAllowed'] is False
    assert pending['reservation'] == row(OUT / (stem + '-once.json')) and pending['submitted'] == row(OUT / (stem + '-submitted.json'))
    c = StrictCommands('bind-' + key + '-run-followup', context)
    assert c.run('head').decode().splitlines() == [head, r['tree']]
    assert c.run('remote-main').decode().split() == [head, 'refs/heads/main']
    assert json.loads(c.run(key + '-workflow-registration')) == b['registrations'][key]
    runs = json.loads(c.run(key + '-runs'))
    c.complete()
    if runs == []:
        save(stem + '-observation-pending.json', {'schema': 1, 'at': now(), 'state': 'submitted-visibility-pending',
             'head': head, 'selection': row(ROOT / SELECTION), 'manualHostBinding': manual_binding(key), 'independentPackageBinding': PACKAGE_BINDING_ROW, 'axisManualDispatchAuthorized': False,
             'reservation': row(OUT / (stem + '-once.json')), 'submitted': row(OUT / (stem + '-submitted.json')),
             'allowanceConsumed': True, 'retryAllowed': False, 'dispatchesPerformed': 0,
             'authoritySnapshot': c.authority_row, 'argvManifest': row(OUT / c.manifest_name), 'commands': c.records,
             'allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF': True, 'runtimeResultsAccepted': False})
        print(json.dumps({'workflow': key, 'state': 'submitted-visibility-pending', 'dispatchesPerformed': 0, 'retryAllowed': False, 'closedCommands': len(c.records)}))
        return
    assert len(runs) == 1, 'Read-only run binding ambiguous; no dispatch retry'
    save_manual_binding(key, runs[0], c, r, b, True)
    print(json.dumps({'workflow': key, 'head': head, 'runID': runs[0]['id'], 'dispatchesPerformed': 0, 'closedCommands': len(c.records), 'runtimeResultsAccepted': False}))
