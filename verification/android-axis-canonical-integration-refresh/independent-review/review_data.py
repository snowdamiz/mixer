"""Independent data-only review: no product/helper imports or child processes."""
from pathlib import Path
import hashlib
import json
import re
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
BUNDLE = Path('verification/android-axis-canonical-integration-refresh')
OUT = ROOT / BUNDLE / 'independent-review'
PRIOR = Path('verification/github-delivery-axis-expression-followup/local/canonical-next-preparation-broader-rejection')
PRIOR_REVIEW = PRIOR.parent / 'canonical-next-review-broader-rejection'
CAPTURE = {}
CHECKS = []


def identity(value):
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def read(relative):
    relative = Path(relative)
    assert not relative.is_absolute() and '..' not in relative.parts
    file = ROOT / relative
    assert stat.S_ISREG(file.lstat().st_mode), str(relative)
    assert file.stat().st_size <= 2_000_000
    data = file.read_bytes()
    key = relative.as_posix()
    if key in CAPTURE:
        assert CAPTURE[key] == data, key
    else:
        assert len(CAPTURE) < 250
        CAPTURE[key] = data
    return data


def parsed(relative):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            assert key not in result, key
            result[key] = value
        return result
    return json.loads(read(relative), object_pairs_hook=unique)


def check(name, actual, expected):
    CHECKS.append({'name': name, 'actual': actual, 'expected': expected, 'consistent': actual == expected})
    assert actual == expected, name


def rows_digest(rows):
    assert len({r['path'] for r in rows}) == len(rows)
    return hashlib.sha256(b''.join((r['path'] + '\0' + r['sha256'] + '\n').encode('utf-8')
                                  for r in sorted(rows, key=lambda r: r['path']))).hexdigest()


def files_digest(files):
    return rows_digest([{'path': key, **value} for key, value in files.items()])


def policy(data):
    start = data.index(b'Data(#"""\n') + len(b'Data(#"""\n')
    end = data.index(b'\n        """#.utf8)', start)
    return json.loads(data[start:end])


# Independently parse a unified diff into disjoint old/new replacement slices.
# Only compare bytes in memory; never invoke patch or write the transformed files.
def patch_sections(data):
    lines = data.splitlines(keepends=True)
    sections = []
    cursor = 0
    while cursor < len(lines):
        header = re.fullmatch(rb'diff --git a/(\S+) b/(\S+)\n', lines[cursor])
        assert header and header[1] == header[2]
        path = header[1].decode('ascii')
        cursor += 1
        old = lines[cursor]
        assert old in [b'--- /dev/null\n', ('--- a/' + path + '\n').encode()]
        assert lines[cursor + 1] == ('+++ b/' + path + '\n').encode()
        cursor += 2
        hunks = []
        while cursor < len(lines) and not lines[cursor].startswith(b'diff --git '):
            h = re.fullmatch(rb'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', lines[cursor])
            assert h
            a, n, b, m = [int(value) for value in h.groups()]
            cursor += 1
            before, after = [], []
            while cursor < len(lines) and not lines[cursor].startswith((b'@@ ', b'diff --git ')):
                kind, payload = lines[cursor][:1], lines[cursor][1:]
                assert kind in [b' ', b'-', b'+']
                if kind != b'+': before.append(payload)
                if kind != b'-': after.append(payload)
                cursor += 1
            assert len(before) == n and len(after) == m
            hunks.append((a, n, b, m, before, after))
        sections.append((path, old == b'--- /dev/null\n', hunks))
    return sections


def transform(data, hunks, inverse=False):
    source = data.splitlines(keepends=True)
    result = []
    cursor = 0
    for a, n, b, m, before, after in hunks:
        start, count, required, replacement = (b, m, after, before) if inverse else (a, n, before, after)
        index = start - 1 if count else start
        assert cursor <= index <= len(source)
        assert source[index:index + count] == required
        result += source[cursor:index] + replacement
        cursor = index + count
    return b''.join(result + source[cursor:])


PINNED = {
    'seal.json': (3100, '75162c55b00b93b3bc4ae93dd5dbdbc6d01bdd486b61031c6248350df11b55eb'),
    'receipt.json': (7247, '9521b37057d9ab4845cb94707f3f359270c362e8be7ca9079f4b9463e254a702'),
    'copy-manifest.json': (19362, '0596f12ffb9fb2535baad07b252eef62db95a296e49098e409ce75d80e312a0d'),
    'application-recipe.json': (15252, 'fd0a118701041163f1040431aca5b44431a981c1321ef0d499f48cdafb79cc8a'),
    'axis-only-proposed.patch': (30411, 'a7633a90a1146c49c2091488672854ba69d22e64ed14a0ba8add547d285fcbff'),
}
for name, (size, digest) in PINNED.items():
    check('root supplied pin: ' + name, identity(read(BUNDLE / name)), {'bytes': size, 'sha256': digest})

seal = parsed(BUNDLE / 'seal.json')
receipt = parsed(BUNDLE / 'receipt.json')
manifest = parsed(BUNDLE / 'copy-manifest.json')
recipe = parsed(BUNDLE / 'application-recipe.json')
evidence = parsed(BUNDLE / 'source-evidence.json')
profile = parsed(BUNDLE / 'proposed-profile.json')
for row in seal['outputs']:
    check('sealed output: ' + row['path'], identity(read(BUNDLE / row['path'])), {k: row[k] for k in ['bytes', 'sha256']})
check('sealed outputs projection', rows_digest(seal['outputs']), seal['outputs_projection_sha256'])
for row in receipt['outputs']:
    check('receipt output: ' + row['path'], identity(read(BUNDLE / row['path'])), {k: row[k] for k in ['bytes', 'sha256']})
check('receipt outputs projection', rows_digest(receipt['outputs']), receipt['outputs_projection_sha256'])
check('96 fresh input rows', len(evidence['inputs']), 96)
for row in evidence['inputs']:
    check('fresh input: ' + row['path'], identity(read(row['path'])), {k: row[k] for k in ['bytes', 'sha256']})
check('fresh input projection', rows_digest(evidence['inputs']), evidence['source_projection_sha256'])
check('manifest fresh projection', manifest['source_projection_sha256'], evidence['source_projection_sha256'])

prior_evidence = parsed(PRIOR / 'source-evidence.json')
check('64 historical dependency rows', len(prior_evidence['rows']), 64)
for row in prior_evidence['rows']:
    check('prior dependency: ' + row['path'], identity(read(row['path'])), {k: row[k] for k in ['bytes', 'sha256']})
check('prior dependencies unchanged report', evidence['dependencies_changed_from_prior64'], [])
check('patch unchanged from corrected review', read(BUNDLE / 'axis-only-proposed.patch'), read(PRIOR / 'axis-only-proposed.patch'))

comparisons = parsed(BUNDLE / 'data-comparisons.json')
check('reported comparison count', len(comparisons['comparisons']), 299)
check('all reported comparisons internally equal', all(row['consistent'] is True and row['actual'] == row['expected'] for row in comparisons['comparisons']), True)
check('reported inconsistencies', comparisons['inconsistent'], [])

TARGETS = [
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/build-tests/test_android_sdk_compatibility.py',
    'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift',
    'native/android/engine/Tests/MixerAndroidRuntimeTests/AndroidTextFieldAxisRefusalTests.swift',
]
check('six exact target paths', [r['target'] for r in manifest['targets']], TARGETS)
check('recipe exact targets', recipe['targets'], manifest['targets'])
check('evidence exact targets', evidence['canonical_before_states'], manifest['targets'])
check('recipe exact copy operations', recipe['application_copy_operations'], [
    {'source': (BUNDLE / target['proposedSource']).as_posix(), 'destination': target['target'],
     'destination_before': target['before'], 'destination_after': target['after'],
     'new_file': target['before'] is None} for target in manifest['targets']])
sections = patch_sections(read(BUNDLE / 'axis-only-proposed.patch'))
check('six exact diff targets', [row[0] for row in sections], TARGETS)
target_records = []
for target, section in zip(manifest['targets'], sections):
    path, new, hunks = section
    before = b'' if new else read(path)
    after = read(BUNDLE / target['proposedSource'])
    check(path + ': absent versus replacement', new, target['before'] is None)
    if new:
        check(path + ': current target absent', (ROOT / path).exists() or (ROOT / path).is_symlink(), False)
    else:
        check(path + ': exact canonical preimage', identity(before), target['before'])
        check(path + ': existing mode', stat.S_IMODE((ROOT / path).lstat().st_mode), 0o644)
    check(path + ': candidate mode', stat.S_IMODE((ROOT / BUNDLE / target['proposedSource']).lstat().st_mode), 0o644)
    check(path + ': exact candidate', identity(after), target['after'])
    check(path + ': unchanged corrected candidate', after, read(PRIOR / target['proposedSource']))
    check(path + ': exact forward transformation', identity(transform(before, hunks)), identity(after))
    check(path + ': exact inverse transformation', identity(transform(after, hunks, True)), identity(before))
    summary = [{'oldStart': a, 'oldCount': n, 'newStart': b, 'newCount': m} for a, n, b, m, _, _ in hunks]
    check(path + ': hunk coordinates/counts', summary, target['hunks'])
    target_records.append({'path': path, 'before': None if new else identity(before), 'after': identity(after),
                           'before_mode': None if new else '100644', 'after_mode': '100644',
                           'forward_exact': True, 'inverse_exact': True})

old_policy = policy(read(TARGETS[0]))
new_policy = policy(read(BUNDLE / 'proposed-source' / TARGETS[0]))
check('proposed profile equals compiled Swift literal', new_policy, profile)
check('new pair identity', new_policy['id'], 'mixer.android-source-pair.6')
check('old pair identity', old_policy['id'], 'mixer.android-source-pair.5')
check('SDK22 unchanged', new_policy['sdk_files'], old_policy['sdk_files'])
check('SDK count', len(new_policy['sdk_files']), 22)
check('adapter count', len(new_policy['adapter_files']), 23)
check('adapter file names unchanged', sorted(new_policy['adapter_files']), sorted(old_policy['adapter_files']))
check('SDK projection', files_digest(new_policy['sdk_files']), 'bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0')
check('adapter projection', files_digest(new_policy['adapter_files']), '7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885')
changed = [p for p in old_policy['adapter_files'] if old_policy['adapter_files'][p] != new_policy['adapter_files'][p]]
check('sole changed adapter member', changed, ['Sources/MixerAndroidRuntime/DocumentSession.swift'])
check('wire unchanged', new_policy['wire'], old_policy['wire'])
check('descriptor unchanged', new_policy['default_descriptor'], old_policy['default_descriptor'])
check('descriptor exact pin', new_policy['default_descriptor'], {'bytes': 9587, 'sha256': '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'})
tuple_record = {'id': new_policy['id'], 'sdk_members': len(new_policy['sdk_files']),
                'adapter_members': len(new_policy['adapter_files']),
                'sdk_projection': new_policy['sdk_compatibility_sha256'],
                'adapter_projection': new_policy['adapter_compatibility_sha256'],
                'default_descriptor': new_policy['default_descriptor'], 'wire': new_policy['wire']}
check('recipe exact full proposed tuple', recipe['expected_tuple'], tuple_record)
check('manifest exact full proposed tuple', manifest['proposed'], tuple_record)
fixture = 'verification/android-default-appearance-packaging/run-2/created-descriptor.json'
check('descriptor inert fixture', identity(read(fixture)), new_policy['default_descriptor'])

expected_new = json.loads(json.dumps(old_policy))
expected_new['id'] = 'mixer.android-source-pair.6'
expected_new['adapter_compatibility_sha256'] = '7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885'
expected_new['adapter_files']['Sources/MixerAndroidRuntime/DocumentSession.swift'] = identity(read(BUNDLE / 'proposed-source' / TARGETS[4]))
check('exact atomic profile delta', new_policy, expected_new)
for kind in ['sdk', 'adapter']:
    members = new_policy[kind + '_files']
    for path, pin in members.items():
        canonical = 'sdk/' + path if kind == 'sdk' else 'native/android/' + ('engine/' if path.startswith('Sources/') else '') + path
        source = BUNDLE / 'proposed-source' / canonical if canonical == TARGETS[4] else canonical
        check('proposed member bytes: ' + canonical, identity(read(source)), pin)
    check(kind + ' declared projection', new_policy[kind + '_compatibility_sha256'], files_digest(members))
check('45 current members', len(evidence['current45_named_members']), 45)
check('45 proposed members', len(evidence['proposed45_named_members']), 45)
check('only one named member changed', [a['path'] for a, b in zip(evidence['current45_named_members'], evidence['proposed45_named_members']) if a != b], [TARGETS[4]])
for key, selected in [('current45_named_members', old_policy), ('proposed45_named_members', new_policy)]:
    expected = []
    for kind in ['sdk', 'adapter']:
        for path, pin in selected[kind + '_files'].items():
            canonical = 'sdk/' + path if kind == 'sdk' else 'native/android/' + ('engine/' if path.startswith('Sources/') else '') + path
            expected.append({'kind': kind, 'path': canonical, 'exportedPath': path, **pin})
    check('exact ' + key + ' maps', sorted(evidence[key], key=lambda r: r['path']), sorted(expected, key=lambda r: r['path']))

old_driver = read(TARGETS[1])
new_driver = read(BUNDLE / 'proposed-source' / TARGETS[1])
check('exact Python template delta', new_driver, old_driver.replace(b"value['id'] != 'mixer.android-source-pair.5'", b"value['id'] != 'mixer.android-source-pair.6'"))
guard = (b"            // Android's native packet decoder does not admit an explicit axis key.\n"
         b'            if node.kind == .textField, node.properties["axis"] != nil { throw AndroidDocumentError.unsupportedUI }\n')
session = read(BUNDLE / 'proposed-source' / TARGETS[4])
check('sole native source delta', session.replace(guard, b''), read(TARGETS[4]))
check('exactly one axis guard', session.count(guard), 1)
check('generic validation precedes axis refusal', session.index(b'UIValidator().validate(document)') < session.index(guard), True)

swift_test = read(BUNDLE / 'proposed-source' / TARGETS[2]).decode()
python_test = read(BUNDLE / 'proposed-source' / TARGETS[3]).decode()
for language, source in [('Swift', swift_test), ('Python', python_test)]:
    for token in ['profile-5-current', 'profile-5-prior', 'broader-6-axis', 'mixed-sdk', 'mixed-adapter',
                  'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e',
                  'android.sdk-profile-mismatch', 'baseline', 'same-size']:
        check(language + ' preserved control source: ' + token, token in source, True)
check('Swift appended drift specified', 'candidate + Data("\\n// drift".utf8)' in swift_test, True)
check('Python appended drift specified', "candidate + b'\\n// drift'" in python_test, True)
check('Swift generic lock recomputed before admission', swift_test.index('lock.android?.adapterDigest = try SourceDigest.tree(adapter)', swift_test.index('func androidCompatibilityAxisSessionDrift')) < swift_test.index('allAdmissionEntrypoints(root)', swift_test.index('func androidCompatibilityAxisSessionDrift')), True)
check('Python generic hash/tool/output sentinels', all(v in python_test for v in ['generic hash before admission', 'tools before admission', 'output before admission', "self.assertFalse((self.root / '.mixer').exists())"]), True)
check('Python old rendered driver exact reconstruction pin', "hashlib.sha256(previous_raw.encode()).hexdigest(), '0f13545e610e527fe491314194fde1aa91698e9b458b638df6094f0e789fe4f2'" in python_test, True)
native_test = read(BUNDLE / 'proposed-source' / TARGETS[5]).decode()
check('eight new XCTest specifications', len(re.findall(r'^    func test\w+\(', native_test, re.M)), 8)
check('historical broader parent ID stays suffixed', recipe['historical_broader_parent_id'], 'mixer.android-source-pair.6-editor-view-api29-30-bc03288599ec-8cd611a5b07f')
check('bare .6 broader mismatch pin', recipe['same_bare_6_broader24_must_refuse']['adapter_compatibility_sha256'], 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e')
check('new manual dispatch absent', recipe['test_scope']['new_manual_axis_dispatch_required'], False)
workflow = read('.github/workflows/verify.yml').decode()
for command in recipe['test_scope']['push_commands']:
    check('ordinary workflow contains: ' + command['command'], command['command'] in workflow, True)

# No mutation of inputs is accepted between first observation and result emission.
for path, data in list(CAPTURE.items()):
    check('input preserved at review end: ' + path, identity((ROOT / path).read_bytes()), identity(data))
check('new native test remains absent', (ROOT / TARGETS[5]).exists() or (ROOT / TARGETS[5]).is_symlink(), False)

# Replace large byte-comparison payloads with identity records for compact reporting.
for row in CHECKS:
    for key in ['actual', 'expected']:
        if isinstance(row[key], bytes): row[key] = identity(row[key])
inputs = [{'path': path, **identity(data)} for path, data in sorted(CAPTURE.items())]
result = {
    'schema': 1,
    'status': 'SOURCE_DATA_REVIEW_NO_ACTIONABLE_FINDINGS_CONDITIONAL_ON_SEPARATE_ACTUAL19_ACCEPTANCE',
    'command': 'python3 -B verification/android-axis-canonical-integration-refresh/independent-review/review_data.py',
    'cwd': str(ROOT), 'tool_version': sys.version,
    'source_revision': None,
    'root_reported_source_revision_only': '2c751cbbc300efc9aa766b5d4add648610ca0341',
    'root_reported_tree_only': 'f2df6833ee8e9ce85306210b63dc35d45747fa0d',
    'input_projection_sha256': rows_digest(inputs), 'captured_inputs': len(inputs),
    'data_comparisons': len(CHECKS), 'inconsistent': [r for r in CHECKS if not r['consistent']],
    'targets': target_records, 'findings': [],
    'reviewer_subject_tests_run': 0, 'product_or_helper_code_imported_or_executed': False,
    'canonical_files_written': 0, 'authority_created': False,
    'network_Git_gh_compiler_native_UI_process_probes_signals': 0,
    'inputs_preserved': True,
    'separate_actual19_audit': 'Parent reports one guarded data audit proving19; independent actual-evidence review is separate and not accepted by this source/data review.',
    'ordinary_same_head_CI': 'Parent reports five successes and a Swift analyzer-envelope prerequisite failure under investigation; no all-CI-green claim.',
    'remaining': ['Root acceptance of separate independent actual19 evidence review',
                  'Immediate preapplication rehash of six target states and all45 named source members',
                  'Coherent exact six-file application followed by ordinary verify.yml push CI',
                  'Exact-source Debug and Release generated/relocated/exported CLI consumer evidence',
                  'All paused native/UI/capture/phone and separate product/OTA/FieldLog/store/customer/GA gates'],
}
OUT.mkdir(parents=True, exist_ok=True)
for name, value in [('review.json', result), ('reviewed-inputs.json', {'schema': 1, 'inputs': inputs, 'projection_sha256': rows_digest(inputs)}),
                    ('data-comparisons.json', {'schema': 1, 'scope': 'independent inert source/data comparisons; not subject tests', 'count': len(CHECKS), 'comparisons': CHECKS})]:
    (OUT / name).write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'comparisons': len(CHECKS), 'inconsistent': len(result['inconsistent']),
                  'inputs': len(inputs), 'projection_sha256': result['input_projection_sha256'],
                  'subject_tests_run': 0, 'canonical_writes': 0}, indent=2))
