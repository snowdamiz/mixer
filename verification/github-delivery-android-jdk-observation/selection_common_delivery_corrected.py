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
BASE = 'df0d15f90f2bc5e702127bdf6ab79f3d8e3d0cce'
TREE = '470173cc89658f13b3a94320569b44e7f56fffd3'
SELECTION = 'verification/android-jdk-data-observation-selection-2026-10-29/selection.json'
SELECTION_SHA = '1ddf37b0e7a2ca13c7d8d8b9755a5c8013eb9958020b053ed8c7285e5f2e0d03'
SELECTION_BYTES = 23108
SELECTED_COUNT = 74
HELPER_SHA = 'b7b4a4fab5ca699ded6efd65259c9e499babbe37786a108d7307dfc0d29ab043'
raw_helper = (OUT / 'owned.py').read_bytes()
assert hashlib.sha256(raw_helper).hexdigest() == HELPER_SHA
spec = importlib.util.spec_from_file_location('android_jdk_selected_owned', OUT / 'owned.py')
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
assert S['manualHost']['dispatches'] == 1 and S['manualHost']['retries'] == 0
assert S['manualHost']['dispatchNonce'] == 'fda6cf6bedfd7897f576df54eac07bec4c80884e209647c84081124d11950cca'
assert S['manualHost']['workflow'] == '.github/workflows/android-view-api-jdk-data-observation.yml'
assert S['manualHost']['workflowSHA256'] == '18a7451271c17ca9fdbaae74091a859a7e49337e93d5f6a3277699f4159d6f0a'
assert S['manualHost']['sourceManifestSHA256'] == 'f865a86fb102646eb2c25e8fab00e13651de4f950e474e7faae4561516e69fb0'
assert S['manualHost']['diagnosticOnly'] is True
assert S['manualHost']['attempt'] == 1 and S['manualHost']['expectedJobs'] == 1
assert S['manualHost']['expectedOwnedJavaCommands'] == 0 and S['manualHost']['expectedOwnedChildCommands'] == 0
assert S['manualHost']['actualDispatched'] is False
assert S['manualHost']['bindDeliveredSHAThenEnableSelection'] is True
assert S['manualHost']['consumeAllowanceBeforeDispatch'] is True
assert S['manualHost']['unknownOutcomeReplay'] is False
assert S['manualHost']['workflowName'] == 'Android JDK file data observation DRAFT'
assert S['manualHost']['expectedJobName'] == 'jdk-data'
assert S['manualHost']['oldFocusedAllowanceConsumed'] is True
assert S['manualHost']['exactSelectionDelta'] == ['dispatch_selected', 'delivered_head', 'admit_ambient_ubuntu_python_checkout_upload']
assert S['rootReviewSHA256'] == '5d7cd6f5417ba2f1b45c2393d8146f0567786259138e9cc280e616b6563aeed5'


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
assert not any(value.startswith(('.wrangler', str(OUT.relative_to(ROOT)) + '/')) for value in SELECTED)
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
    for expected in ROWS:
        assert selected_row(expected) == expected
    for expected in PROTECTED:
        assert row(ROOT / expected['path'])['sha256'] == expected['sha256']
    assert row(ROOT / S['ordinaryHost']['workflow'])['sha256'] == S['ordinaryHost']['workflowSHA256']
    assert_absent('hosted/lib/mixer_hosted/artifacts/store.ex')
    helper_binding = S['deliveryHelper']
    assert helper_binding['path'] == str((OUT / 'owned.py').relative_to(ROOT))
    assert helper_binding['sha256'] == HELPER_SHA
    assert helper_binding['baselineRepinEvidence'] == {'path':'verification/github-delivery-android-jdk-observation/preparation.json','bytes':3960,'sha256':'21a6670fafaab357176dcf87fa7f56b4909c9b087d7b24866e5b1a8160ef2e9d'}
    assert helper_binding['priorHelper'] == {'path': 'verification/github-delivery-android-view-api-boundary/owned_corrected.py', 'bytes': 29385, 'sha256': '2c874b49f95fdafaf133a3d8fd02b7a2aa6d7a44ab9e8faff207d14f978d54f2'}
    assert helper_binding['priorCorrectionSeal'] == {'path': 'verification/github-delivery-android-view-api-boundary/preparation-correction-seal.json', 'sha256': 'db9df0c6a412b6ee1047c6abb431941823858f08f42c07d154b5cf405659ffe3'}
    assert helper_binding['independentReviewSeal'] == {'path': 'verification/android-view-api-git-custody-review/review-seal.json', 'sha256': '1c67d7aef5cc9602b6127b4fad4471eab2d2e8081b3214c0689e55646a75ed0a'}
    assert row(ROOT / helper_binding['path'])['sha256'] == HELPER_SHA
    assert row(ROOT / helper_binding['baselineRepinEvidence']['path']) == helper_binding['baselineRepinEvidence']
    assert row(ROOT / helper_binding['priorHelper']['path']) == helper_binding['priorHelper']
    assert row(ROOT / helper_binding['priorCorrectionSeal']['path'])['sha256'] == helper_binding['priorCorrectionSeal']['sha256']
    assert row(ROOT / helper_binding['independentReviewSeal']['path'])['sha256'] == helper_binding['independentReviewSeal']['sha256']
    assert helper_binding['exactArgvApprovalBeforeEveryActualPhase'] is True



DRIVERS = ['selection_common_delivery_corrected.py', 'deliver_selected_corrected.py', 'bind_ci_selected_corrected.py', 'dispatch_selected_corrected.py']
ORDINARY_NAME = 'Owned engine checks'
ACCEPTED_PREFLIGHT_SEAL = {"path":"verification/github-delivery-android-jdk-observation/preflight-selected.seal.json","bytes":21257,"sha256":"780ac4d21c5409f2d1416ff4ba9f15475d87c152e33bd9fa4ec8bfacd6eb223e"}
ACCEPTED_PREFLIGHT_ROWS = [{"path":"verification/github-delivery-android-jdk-observation/preflight-selected.json","bytes":4758,"sha256":"1d280c4fe8b0d7b9a4a58f2666e3c7044a5163d36e5be670f918547b4bb72adc"},{"path":"verification/github-delivery-android-jdk-observation/preservation-selected-local.json","bytes":785848,"sha256":"a10d39c460c1b4e1bcd7a5f3be60512dfc53ff56366fb419fcb41532a5bca1d1"},{"path":"verification/github-delivery-android-jdk-observation/manifest-selected.json","bytes":18323,"sha256":"c1b52406b7d17e2a8eb373e4efce4b21a9aa90e3a9988b121ba4d00b6cb8f7a8"},{"path":"verification/github-delivery-android-jdk-observation/authority-snapshot-preflight-selected.json","bytes":3202,"sha256":"d91ed906793f065fbae15af58e43a18f690e9c87cbfba782a9e5c3e3f162e8b4"},{"path":"verification/github-delivery-android-jdk-observation/argv-preflight-selected.json","bytes":5130,"sha256":"098541321e0492fd1924b999e96a1819a18828e8c8a5dcbf542ce4b940c7e8ec"}]


def admission_adapter_evidence():
    return {'source': row(OUT / 'selection_common_delivery_corrected.py'),
            'function': 'selected_read_admission_adapter', 'fragmentSHA256': ADAPTER_FRAGMENT_SHA256,
            'exactReadOnlyException': list(PUSH_URL_READ_EXCEPTION),
            'otherVectorsDelegateUnchangedToHelperSHA256': HELPER_SHA,
            'strictRootManifestMatchRequiredBeforeAdapter': True,
            'startupCustodyClosureOrSignalingChanged': False}


def accepted_preflight():
    assert row(ROOT / ACCEPTED_PREFLIGHT_SEAL['path']) == ACCEPTED_PREFLIGHT_SEAL
    seal = json.loads((ROOT / ACCEPTED_PREFLIGHT_SEAL['path']).read_bytes())
    frozen_selection = row(ROOT / SELECTION)
    assert seal['selection'] == frozen_selection
    sealed = {value['path']: value for value in seal['sourcesAndEvidence']}
    for expected in ACCEPTED_PREFLIGHT_ROWS:
        assert sealed[expected['path']] == expected
        assert row(ROOT / expected['path']) == expected
    pre = json.loads((OUT / 'preflight-selected.json').read_bytes())
    preservation = json.loads((OUT / 'preservation-selected-local.json').read_bytes())
    manifest = json.loads((OUT / 'manifest-selected.json').read_bytes())
    assert pre['selection'] == frozen_selection and pre['head'] == BASE and pre['tree'] == TREE
    assert pre['branch'] == 'main' and pre['origin'] == 'https://github.com/snowdamiz/mixer.git' and pre['originMain'] == BASE
    assert pre['selectedPaths'] == SELECTED_COUNT and pre['indexEmpty'] is True and pre['selectedByteModesVerified'] is True
    assert pre['allCommandsAdmittedDirectlyReapedOwnedGroupsAbsentSeparatePipesEOF'] is True
    assert pre['argvManifest'] == sealed[str((OUT / 'argv-preflight-selected.json').relative_to(ROOT))]
    assert pre['authoritySnapshot'] == sealed[str((OUT / 'authority-snapshot-preflight-selected.json').relative_to(ROOT))]
    assert pre['helper']['sha256'] == HELPER_SHA
    assert manifest['selection'] == frozen_selection and manifest['paths'] == SELECTED_COUNT and manifest['members'] == ROWS
    assert preservation['cleanTrackedSnapshot']['head'] == BASE and preservation['cleanTrackedSnapshot']['tree'] == TREE
    assert {value['path'] for value in preservation['tracked']} == {value['path'] for value in PROTECTED}
    assert len(seal['commandClosure']) == 9 and seal['allActualVectorsMatchRootApprovedManifest'] is True
    return pre, preservation


def check_stage_pathspec():
    path = OUT / 'paths-selected-corrected.nul'
    assert path.is_file() and not path.is_symlink()
    expected = b''.join(value.encode() + b'\0' for value in sorted(SELECTED))
    assert path.read_bytes() == expected, 'Generated stage pathspec differs from frozen exact selection'
    return row(path)


def check_driver_sources(authority):
    expected = authority['driverSources']
    assert {value['path'] for value in expected} == {str((OUT / name).relative_to(ROOT)) for name in DRIVERS}
    for value in expected:
        assert row(ROOT / value['path']) == value


def bound_context():
    value = json.loads((OUT / 'delivery-selected-corrected-receipt.json').read_bytes())
    assert value['pushed'] and value['indexEmpty'] and value['selectedPaths'] == SELECTED_COUNT and not value['force']
    assert value['selection'] == row(ROOT / SELECTION) and value['parent'] == BASE
    assert value['preflightSeal'] == ACCEPTED_PREFLIGHT_SEAL
    assert value['preflight'] == ACCEPTED_PREFLIGHT_ROWS[0]
    assert value['preservationBefore'] == ACCEPTED_PREFLIGHT_ROWS[1]
    assert re.fullmatch('[0-9a-f]{40}', value['head']) and re.fullmatch('[0-9a-f]{40}', value['tree'])
    return {'DELIVERED_SHA': value['head']}


def dispatch_input(head):
    assert re.fullmatch('[0-9a-f]{40}', head)
    template_path = ROOT / S['manualHost']['selectionTemplate']
    assert S['manualHost']['selectionTemplate'] == 'verification/android-view-api-focused-actual-review/jdk-observation-preparation/root-selection-template.json'
    assert row(template_path)['sha256'] == 'e95ce176c29b990be77d3d3f110e1252dce3d9874b7a3ab41ed8b129219668fa'
    before = json.loads(template_path.read_bytes())
    assert before['dispatch_selected'] is False and before['delivered_head'] is None
    assert before['admit_ambient_ubuntu_python_checkout_upload'] is False
    assert before['dispatch_nonce'] == S['manualHost']['dispatchNonce']
    assert before['workflow_path'] == '.github/workflows/android-view-api-jdk-data-observation.yml'
    assert before['workflow_sha256'] == '18a7451271c17ca9fdbaae74091a859a7e49337e93d5f6a3277699f4159d6f0a'
    assert before['source_manifest_sha256'] == 'f865a86fb102646eb2c25e8fab00e13651de4f950e474e7faae4561516e69fb0'
    assert before['child_commands'] == [] and before['run_attempt'] == 1
    assert before['allowance'] == {'new_diagnostic_runs': 1, 'attempts': 1, 'old_focused_allowance_reused': False}
    after = {**before, 'dispatch_selected': True, 'delivered_head': head, 'admit_ambient_ubuntu_python_checkout_upload': True}
    assert set(after) == set(before)
    assert {key for key in before if before[key] != after[key]} == {'dispatch_selected', 'delivered_head', 'admit_ambient_ubuntu_python_checkout_upload'}
    return json.dumps(after, sort_keys=True, separators=(',', ':'))


def reject_gh_read_flags(argv):
    if argv[:2] == ['gh', 'api']:
        assert len(argv) == 7 and argv[3:6] == ['--hostname', 'github.com', '--jq']
        assert argv[2].startswith('repos/snowdamiz/mixer/') and not argv[2].startswith('-')
        blocked = ('--method', '--input', '--field', '--raw-field', '-X', '-f', '-F')
        assert not any(arg.startswith(blocked) for arg in argv[2:]), 'Read-call method/input/field forms forbidden'
    elif argv[0] == 'gh' and argv[1] != 'workflow':
        assert argv == ['gh', '--version']


def require_exact_manifest_argv(expected, supplied):
    assert supplied == expected, 'Unapproved command vector'
    return True


class StrictCommands:
    def __init__(self, phase, context=None):
        check_sources()
        accepted_preflight()
        self.manifest_name = 'argv-' + phase + '.json'
        self.manifest_row = row(OUT / self.manifest_name)
        self.manifest = json.loads((OUT / self.manifest_name).read_bytes())
        assert self.manifest['phase'] == phase and self.manifest['selection'] == row(ROOT / SELECTION)
        raw_authority = (OUT / 'authority.json').read_bytes()
        self.authority = json.loads(raw_authority)
        assert self.authority['schema'] == 1 and self.authority['authorized'] is True
        assert self.authority['repository'] == 'snowdamiz/mixer' and self.authority['branch'] == 'main'
        assert self.authority['selection'] == row(ROOT / SELECTION), 'Authority must select the exact frozen selection'
        assert self.authority['baseline'] == {'head': BASE, 'tree': TREE}
        assert self.authority['selectedPathsIncludingSelf'] == SELECTED_COUNT
        assert self.authority['argvApprovals'][phase] == self.manifest_row, 'Root exact argv approval required'
        check_driver_sources(self.authority)
        self.admission_adapter = admission_adapter_evidence()
        assert self.authority['admissionAdapter'] == self.admission_adapter, 'Root-selected exact admission adapter binding required'
        self.context = context or {}
        for key, value in self.context.items():
            if key in ('DELIVERED_SHA', 'COMMITTED_SHA'): assert re.fullmatch('[0-9a-f]{40}', value)
            elif key in ('ENGINE_RUN_ID', 'MANUAL_RUN_ID'): assert re.fullmatch('[1-9][0-9]*', value)
            elif key == 'DISPATCH_JSON': assert value == dispatch_input(self.context['DELIVERED_SHA'])
            else: raise AssertionError('Unknown typed argv binding')
        self.expected = {value['name']: value for value in self.manifest['commands']}
        assert len(self.expected) == len(self.manifest['commands'])
        for value in self.expected.values():
            effective = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', *value['argv'][1:]] if value['argv'][0] == 'git' else value['argv']
            assert value['effectiveArgv'] == effective, 'Manifest effective argv disagrees with frozen helper prefix'
        self.used = set()
        limits = self.manifest['session']
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
        assert self.manifest['phase'] == 'delivery-selected-corrected'
        assert 'COMMITTED_SHA' not in self.context, 'Committed SHA cannot be rebound'
        assert re.fullmatch('[0-9a-f]{40}', head)
        self.context['COMMITTED_SHA'] = head

    @property
    def records(self):
        return self.commands.records

    def vector(self, name):
        value = self.expected[name]
        result = []
        for token in value['argv']:
            for key, bound in self.context.items(): token = token.replace('{' + key + '}', bound)
            assert not re.search(r'\{(?:DELIVERED_SHA|COMMITTED_SHA|ENGINE_RUN_ID|MANUAL_RUN_ID|DISPATCH_JSON)\}', token)
            result.append(token)
        reject_gh_read_flags(result)
        if result[:2] == ['gh', 'workflow']:
            assert self.manifest['phase'] == 'dispatch-selected-corrected' and name == 'dispatch'
            assert result == ['gh', 'workflow', 'run', 'android-view-api-jdk-data-observation.yml', '--repo', 'github.com/snowdamiz/mixer', '--ref', 'main', '--raw-field', 'root_selection_json=' + dispatch_input(self.context['DELIVERED_SHA'])]
        return result

    def run(self, name, argv=None, seconds=25):
        assert name not in self.used, 'One command admission per exact vector label'
        assert row(OUT / self.manifest_name) == self.manifest_row
        assert json.loads((OUT / 'authority.json').read_bytes()) == self.authority
        check_driver_sources(self.authority)
        check_sources()
        accepted_preflight()
        expected = self.vector(name)
        if argv is not None: require_exact_manifest_argv(expected, argv)
        if name == 'stage':
            assert self.manifest['phase'] == 'delivery-selected-corrected'
            pathspec_row = check_stage_pathspec()
            save('stage-selected-corrected-pathspec-admission.json', {'at': now(),
                'pathspec': pathspec_row, 'selection': row(ROOT / SELECTION),
                'paths': SELECTED_COUNT, 'byteForByteNULAllowlistCheckedBeforeStageAdmission': True})
        self.used.add(name)
        return self.commands.run(name, expected, seconds)
