"""Reproduce this source-only refresh using bounded filesystem data.

This file never imports subject code, starts a child, or writes a source target.
Its only writes are deterministic preparation artifacts beside this file.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
OUT_REL = 'verification/android-axis-canonical-integration-refresh'
OUT = ROOT / OUT_REL
BASE_REL = 'verification/github-delivery-axis-expression-followup/local/canonical-next-preparation-broader-rejection'
BASE = ROOT / BASE_REL
REVIEW_REL = 'verification/github-delivery-axis-expression-followup/local/canonical-next-review-broader-rejection'
REVIEW = ROOT / REVIEW_REL
INITIAL_REL = 'verification/github-delivery-axis-expression-followup/local/canonical-next-preparation'
INITIAL_REVIEW_REL = 'verification/github-delivery-axis-expression-followup/local/canonical-next-review'
ALGORITHM = 'SHA256 ordinal sorted path + NUL + lowercase file SHA256 + LF; byte counts checked separately'
CAPTURED = {}
CHECKS = []


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(relative):
    path = ROOT / relative
    assert path.is_relative_to(ROOT) and '..' not in Path(relative).parts
    assert path.is_file() and not path.is_symlink(), relative
    assert path.stat().st_size <= 2_000_000, relative
    if relative not in CAPTURED:
        CAPTURED[relative] = path.read_bytes()
        assert len(CAPTURED) <= 180
    return CAPTURED[relative]


def record(relative):
    return {'path': relative, **identity(read(relative))}


def parsed(relative):
    return json.loads(read(relative))


def compare(name, actual, expected):
    CHECKS.append({'comparison': name, 'consistent': actual == expected,
                   'actual': actual, 'expected': expected})
    assert actual == expected, name


def projection(rows):
    return hashlib.sha256(b''.join((r['path'] + '\0' + r['sha256'] + '\n').encode()
                                  for r in sorted(rows, key=lambda r: r['path']))).hexdigest()


def map_projection(files):
    return projection([{'path': path, **value} for path, value in files.items()])


def policy(data):
    text = data.decode()
    return json.loads(text.split('Data(#"""\n', 1)[1].split('\n        """#.utf8)', 1)[0])


def write(relative, data):
    destination = OUT / relative
    assert destination.is_relative_to(OUT) and '..' not in Path(relative).parts
    assert not destination.is_symlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def write_json(relative, data):
    write(relative, (json.dumps(data, indent=2, ensure_ascii=True) + '\n').encode())


def parse_patch(data):
    sections = []
    lines = data.splitlines(keepends=True)
    i = 0
    while i < len(lines):
        match = re.fullmatch(rb'diff --git a/(\S+) b/(\S+)\n', lines[i])
        assert match and match[1] == match[2]
        target = match[1].decode()
        old_header, new_header = lines[i + 1:i + 3]
        assert old_header in [('--- a/' + target + '\n').encode(), b'--- /dev/null\n']
        assert new_header == ('+++ b/' + target + '\n').encode()
        i += 3
        hunks = []
        while i < len(lines) and not lines[i].startswith(b'diff --git '):
            match = re.fullmatch(rb'@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n', lines[i])
            assert match
            old_start, old_count, new_start, new_count = map(int, match.groups())
            i += 1
            body = []
            while i < len(lines) and not lines[i].startswith((b'@@ ', b'diff --git ')):
                assert lines[i][:1] in [b' ', b'-', b'+']
                body.append(lines[i])
                i += 1
            assert sum(line[:1] != b'+' for line in body) == old_count
            assert sum(line[:1] != b'-' for line in body) == new_count
            hunks.append({'oldStart': old_start, 'oldCount': old_count,
                          'newStart': new_start, 'newCount': new_count, 'body': body})
        sections.append({'target': target, 'newFile': old_header == b'--- /dev/null\n', 'hunks': hunks})
    return sections


def transform(data, section, reverse=False):
    source = data.splitlines(keepends=True)
    output = []
    cursor = 0
    for hunk in section['hunks']:
        start = hunk['newStart'] if reverse else hunk['oldStart']
        position = max(0, start - 1)
        assert cursor <= position <= len(source)
        output.extend(source[cursor:position])
        cursor = position
        for line in hunk['body']:
            action, payload = line[:1], line[1:]
            if reverse:
                action = {b'+': b'-', b'-': b'+', b' ': b' '}[action]
            if action != b'+':
                assert cursor < len(source) and source[cursor] == payload
                cursor += 1
            if action != b'-':
                output.append(payload)
    output.extend(source[cursor:])
    return b''.join(output)


manifest = parsed(BASE_REL + '/copy-manifest.json')
old_evidence = parsed(BASE_REL + '/source-evidence.json')
old_receipt = parsed(BASE_REL + '/receipt.json')
review = parsed(REVIEW_REL + '/review.json')
review_seal = parsed(REVIEW_REL + '/seal.json')
review_inputs = parsed(REVIEW_REL + '/reviewed-inputs.json')
targets = manifest['targets']
compare('exact six-target scope', len(targets), 6)
compare('reviewed patch pin', identity(read(BASE_REL + '/axis-only-proposed.patch')),
        {'bytes': 30411, 'sha256': 'a7633a90a1146c49c2091488672854ba69d22e64ed14a0ba8add547d285fcbff'})
compare('reviewed manifest pin', identity(read(BASE_REL + '/copy-manifest.json')),
        {'bytes': 22894, 'sha256': '1d19a88b5eff949a04263ef603d03f84db350ab7a3fc0687baa17c08846e9f26'})
compare('review markdown pin', identity(read(REVIEW_REL + '/REVIEW.md')),
        {'bytes': 3228, 'sha256': 'a8bc24b6974a72dcf586c15bb46585d192d0caf5a1f50eb219ec99a7232a0a91'})
compare('review json pin', identity(read(REVIEW_REL + '/review.json')),
        {'bytes': 7625, 'sha256': 'a9a3b214cfd7e8ff345441f17385808ad4dbaaf12ce96156aa02496a3fb75cf9'})
compare('corrected independent review findings', review['findings'], [])
compare('corrected independent data comparison count', review['data_comparisons']['count'], 84)

for row in old_evidence['rows']:
    compare('prior dependency preserved: ' + row['path'], identity(read(row['path'])),
            {k: row[k] for k in ['bytes', 'sha256']})
compare('prior64 dependency projection', projection(old_evidence['rows']), old_evidence['source_projection_sha256'])
for row in old_receipt['outputs']:
    compare('corrected preparation preserved: ' + row['path'], identity(read(BASE_REL + '/' + row['path'])),
            {k: row[k] for k in ['bytes', 'sha256']})
for row in review_seal['outputs']:
    compare('independent review preserved: ' + row['path'], identity(read(REVIEW_REL + '/' + row['path'])),
            {k: row[k] for k in ['bytes', 'sha256']})
for row in review_inputs['inputs']:
    compare('independent reviewed input preserved: ' + row['path'], identity(read(row['path'])),
            {k: row[k] for k in ['bytes', 'sha256']})
compare('independent review input projection', projection(review_inputs['inputs']), review_inputs['projection_sha256'])

initial_review = parsed(INITIAL_REVIEW_REL + '/review.json')
read(INITIAL_REVIEW_REL + '/data-comparisons.json')
compare('initial independent comparison count', initial_review['observed_data_comparisons']['count'], 149)

sections = parse_patch(read(BASE_REL + '/axis-only-proposed.patch'))
compare('patch target order', [s['target'] for s in sections], [t['target'] for t in targets])
target_states = []
after_by_path = {}
for target, section in zip(targets, sections):
    path = ROOT / target['target']
    before = None if not path.exists() else identity(read(target['target']))
    compare('current canonical before: ' + target['target'], before, target['before'])
    candidate = read(BASE_REL + '/' + target['proposedSource'])
    compare('reviewed proposed after: ' + target['target'], identity(candidate), target['after'])
    baseline = b'' if before is None else read(target['target'])
    compare('patch reconstruction: ' + target['target'], identity(transform(baseline, section)), identity(candidate))
    compare('patch inverse: ' + target['target'], identity(transform(candidate, section, reverse=True)), identity(baseline))
    compare('new target header: ' + target['target'], section['newFile'], before is None)
    compare('hunk ranges: ' + target['target'],
            [{k: v for k, v in h.items() if k != 'body'} for h in section['hunks']], target['hunks'])
    after_by_path[target['target']] = candidate
    target_states.append({'target': target['target'], 'before': before, 'after': identity(candidate),
                          'proposedSource': target['proposedSource'], 'patch_applies_as_data': True,
                          'hunks': target['hunks']})

profile_source = 'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift'
current_profile = policy(read(profile_source))
proposed_profile = policy(after_by_path[profile_source])
compare('reviewed proposed profile equals compiled literal', proposed_profile, parsed(BASE_REL + '/proposed-profile.json'))
compare('current canonical identity', current_profile['id'], 'mixer.android-source-pair.5')
compare('proposed conditional identity', proposed_profile['id'], 'mixer.android-source-pair.6')
compare('unchanged SDK map', proposed_profile['sdk_files'], current_profile['sdk_files'])
compare('unchanged descriptor', proposed_profile['default_descriptor'], current_profile['default_descriptor'])
compare('unchanged wire', proposed_profile['wire'], current_profile['wire'])
compare('SDK22 member count', len(current_profile['sdk_files']), 22)
compare('adapter23 member count', len(current_profile['adapter_files']), 23)
compare('proposed adapter23 member count', len(proposed_profile['adapter_files']), 23)
current_rows = []
proposed_rows = []
for kind in ['sdk', 'adapter']:
    for exported, pin in current_profile[kind + '_files'].items():
        relative = 'sdk/' + exported if kind == 'sdk' else 'native/android/' + ('engine/' if exported.startswith('Sources/') else '') + exported
        compare('current named member: ' + relative, identity(read(relative)), pin)
        current_rows.append({'kind': kind, 'path': relative, 'exportedPath': exported, **pin})
        after = after_by_path.get(relative, read(relative))
        compare('proposed named member: ' + relative, identity(after), proposed_profile[kind + '_files'][exported])
        proposed_rows.append({'kind': kind, 'path': relative, 'exportedPath': exported, **identity(after)})
    compare('current ' + kind + ' projection', map_projection(current_profile[kind + '_files']), current_profile[kind + '_compatibility_sha256'])
    compare('proposed ' + kind + ' projection', map_projection(proposed_profile[kind + '_files']), proposed_profile[kind + '_compatibility_sha256'])
compare('current45 bytes', sum(r['bytes'] for r in current_rows), 569231)
compare('proposed45 bytes', sum(r['bytes'] for r in proposed_rows), 569431)
changed_adapter = [k for k in current_profile['adapter_files'] if current_profile['adapter_files'][k] != proposed_profile['adapter_files'][k]]
compare('only named adapter change', changed_adapter, ['Sources/MixerAndroidRuntime/DocumentSession.swift'])

broader_rel = old_evidence['broader_tuple_evidence']['manifest']['path']
broader = parsed(broader_rel)
future = broader['future_adapter24']
broader_map = {row['exported_path']: row['identity'] for row in future['adapter_assembly']}
compare('exact broader24 member count', len(broader_map), 24)
compare('exact broader24 projection', map_projection(broader_map), 'ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e')
compare('exact broader24 projection matches manifest', map_projection(broader_map), future['projection'])
compare('broader descriptor', future['default_descriptor_unchanged'], proposed_profile['default_descriptor'])
compare('broader SDK22', future['SDK22_projection_unchanged'], proposed_profile['sdk_compatibility_sha256'])

swift_test = 'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift'
python_test = 'cli/build-tests/test_android_sdk_compatibility.py'
for relative, start, end, argument in [(swift_test, '    case "broader-6-axis":\n', '    case "mixed-sdk":', ', "broader-6-axis"'),
                                      (python_test, "                elif change == 'broader-6-axis':\n", "                elif change == 'mixed-sdk':", ", 'broader-6-axis'")]:
    text = after_by_path[relative].decode()
    compare('one broader24 case: ' + relative, text.count(start), 1)
    begin = text.index(start)
    finish = text.index(end, begin)
    case = text[begin:finish]
    for value in ['mixer.android-source-pair.6', proposed_profile['sdk_compatibility_sha256'], future['projection'],
                  future['default_descriptor_unchanged']['sha256'], '9587']:
        compare('full broader tuple literal ' + value + ': ' + relative, value in case, True)
    reverted = (text[:begin] + text[finish:]).replace(argument, '')
    compare('all earlier refusal controls preserved by exact reversion: ' + relative,
            identity(reverted.encode()), identity(read(INITIAL_REL + '/proposed-source/' + relative)))
for relative in after_by_path:
    if relative not in [swift_test, python_test]:
        compare('other proposed source unchanged from initial: ' + relative,
                identity(after_by_path[relative]), identity(read(INITIAL_REL + '/proposed-source/' + relative)))

driver = 'cli/Sources/MixerBuild/Resources/android-build.py'
compare('old rendered driver source reconstructs exactly',
        identity(after_by_path[driver].replace(b"value['id'] != 'mixer.android-source-pair.6'", b"value['id'] != 'mixer.android-source-pair.5'")),
        identity(read(driver)))
for relative in ['AGENTS.md', 'PLAN.md', 'mixer-product-plan.md', '.github/workflows/verify.yml',
                 '.github/workflows/android-axis-refusal-host.yml', 'Package.swift', 'cli/Package.swift',
                 'native/android/engine/Package.swift', 'scripts/ci/check-sdk-package.py']:
    read(relative)
workflow = read('.github/workflows/verify.yml').decode()
commands = ['python3 scripts/ci/check-sdk-package.py', 'swift test', 'swift test --package-path cli',
            'python3 -B -m unittest discover -s cli/build-tests -v', 'swift test --package-path native/android/engine']
workflow_lines = workflow.splitlines()
command_rows = []
for command in commands:
    matches = [i + 1 for i, line in enumerate(workflow_lines) if line.strip() == command]
    compare('ordinary push workflow command present once: ' + command, len(matches), 1)
    command_rows.append({'command': command, 'line': matches[0], 'executed_by_refresh': False})

for relative, data in CAPTURED.items():
    assert (ROOT / relative).read_bytes() == data, 'input changed during refresh: ' + relative
assert not (ROOT / targets[-1]['target']).exists()
rows = [record(relative) for relative in sorted(CAPTURED)]
source_digest = projection(rows)
status = 'SOURCE_DATA_READY_CONDITIONAL_ACTUAL19_ACCEPTANCE_AND_INDEPENDENT_REFRESH_REVIEW_PENDING'
root_report = {
    'source': 'Parent task message, not independently queried in this filesystem-only refresh',
    'delivered_head': '2c751cbbc300efc9aa766b5d4add648610ca0341',
    'delivered_tree': 'f2df6833ee8e9ce85306210b63dc35d45747fa0d',
    'run': 40943215863, 'attempt': 1, 'job': 123691711035,
    'reported_outcome': 'succeeded', 'archive_bytes': 13968,
    'archive_sha256_prefix_only': '2d30a722',
    'actual19_acceptance': False,
    'notice': 'Successful provider status is not actual19 acceptance. Exact archive DATA audit is in progress. Historical preparation and reviews retain their original failed or pending status.'}
recipe = {
    'schema': 1, 'status': status, 'applied': False, 'authority_created': False,
    'root_reported_host_state': root_report,
    'preconditions': [
        'Root accepts the exact actual19 archive after its DATA audit and independent actual-evidence review.',
        'A fresh independent review accepts this refresh, its unchanged six-file proposal, and the current dependency pins.',
        'Immediately before application, rehash all six target states and the 45 named source members against this bundle. Require the new test path to remain absent.',
        'Require the unchanged reviewed patch, all six candidate after hashes, exact SDK22/adapter23 identity, descriptor, and full tuple. Stop on any mismatch.'],
    'application': [
        'Coordinate one coherent six-file source change with the root. Use the proposed-source copies and exact target mappings below.',
        'Write the five replacement files and add the one absent native test. Do not run tests or commit between those six writes.',
        'Rehash all six targets against the after pins. Recompute both named-map projections as data and require the selected minimal tuple.',
        'Record the integrated source revision, command, tool versions, full stdout and stderr, discovered tests, results, and cleanup for the canonical checks.',
        'Use ordinary verify.yml push CI for canonical SDK, CLI, Python build tests, and Android engine verification. No new axis workflow dispatch is required.',
        'Keep actual Debug and Release generated, relocated, and exported CLI consumer evidence pending until run and reviewed at the integrated source.'],
    'targets': target_states,
    'application_copy_operations': [
        {'source': OUT_REL + '/' + target['proposedSource'], 'destination': target['target'],
         'destination_before': target['before'], 'destination_after': target['after'],
         'new_file': target['before'] is None}
        for target in targets],
    'expected_tuple': manifest['proposed'],
    'historical_canonical_tuple': manifest['current'],
    'same_bare_6_broader24_must_refuse': review['broader_tuple'],
    'historical_broader_parent_id': review['historical_parent_id'],
    'broader_identity_rule': 'The suffixed historical broader proposal is unselected. A future broader24 composition must rebase its identity and integration. Bare .6 is conditional for the minimal axis-only tuple.',
    'test_scope': {
        'ordinary_workflow': record('.github/workflows/verify.yml'),
        'push_commands': command_rows,
        'assertions_required': [
            'All eight added XCTest methods and the eleven existing runtime/transaction Swift Testing methods at actual19 scope.',
            'The complete canonical Android engine package including its C ABI target and linked SDK tests.',
            'Full CLI Swift suite and Python build suite with both historical .5 tuples, mixed pins, and explicit same-bare-.6 broader24 refusal.',
            'Baseline, same-size, and appended DocumentSession source drift refuse after recomputed generic locks. Source and tool precedence sentinels remain intact.',
            'The old rendered driver refuses candidate bytes before tools or output. Matching new copied and exported sources equal the exact candidate.',
            'Actual Debug and Release CLI generated, relocated, and exported consumers at the exact minimal tuple. Existing synthetic host fixtures and old consumer receipts do not qualify this new integration.'],
        'new_manual_axis_dispatch_required': False,
        'new_workflow_or_manual_selection_required': False,
        'local_product_or_compiler_execution': 'Not run by this refresh. Existing local compiler and custody holds persist.',
        'native_simulator_emulator_UI_capture': 'Paused. No instance was started, probed, or signalled.',
        'phones': 'Disconnected. Physical acceptance remains pending.'},
    'scope_limits': [
        'The refresh proves byte identity and patch applicability as bounded data only.',
        'No source pair is integrated, published, signed, or accepted by this bundle.',
        'Public V2, full owner, startup, UnitA, complete-matrix, native, ART, immutable separate-repository FieldLog, OTA, store, customer, and GA evidence remain outside this slice.',
        'Do not retry old one-shot isolated runs or alter their evidence. Keep every process and custody hold.']}

for target in targets:
    write(target['proposedSource'], after_by_path[target['target']])
write('axis-only-proposed.patch', read(BASE_REL + '/axis-only-proposed.patch'))
write('proposed-profile.json', read(BASE_REL + '/proposed-profile.json'))
write_json('copy-manifest.json', {'schema': 1, 'status': status, 'owned_directory': OUT_REL,
    'source_projection_sha256': source_digest, 'projection_algorithm': ALGORITHM,
    'proposal_source': record(BASE_REL + '/copy-manifest.json'),
    'reviewed_patch': record(BASE_REL + '/axis-only-proposed.patch'),
    'targets': target_states, 'current': manifest['current'], 'proposed': manifest['proposed'],
    'unchanged_named_product_members': manifest['unchanged_named_product_members'],
    'canonical_files_written': 0, 'profile_integrated': False, 'profile_published': False,
    'new_manual_axis_dispatch_required': False, 'condition_satisfied': False})
write_json('source-evidence.json', {'schema': 1, 'status': status, 'source_revision_observed': None,
    'source_revision_root_reported_only': root_report['delivered_head'],
    'tree_root_reported_only': root_report['delivered_tree'],
    'projection_algorithm': ALGORITHM, 'source_projection_sha256': source_digest, 'inputs': rows,
    'canonical_before_states': target_states, 'current45_named_members': current_rows,
    'proposed45_named_members': proposed_rows, 'current45_bytes': 569231, 'proposed45_bytes': 569431,
    'dependencies_changed_from_prior64': [], 'root_reported_host_state': root_report,
    'subject_tests_executed': 0, 'actual19_acceptance_inferred': False})
write_json('application-recipe.json', recipe)
write_json('data-comparisons.json', {'schema': 1, 'scope': 'Bounded filesystem/data comparisons, not product tests',
                                   'count': len(CHECKS), 'inconsistent': [], 'comparisons': CHECKS})
readme = '''The refreshed six-file proposal matches the current filesystem. The five existing source targets retain their reviewed preimages. The added native test path remains absent. The reviewed patch and six after copies are unchanged.

This bundle is ready for independent source/data review. Application remains conditional on root acceptance of the exact actual19 archive and review of this refresh. The parent reports that run 40943215863 attempt 1, job 123691711035 succeeded. Its exact archive audit and actual19 acceptance remain pending. This refresh queried no provider and executed no product test.

Use application-recipe.json for the exact six target mappings, before states, after hashes, tuple, preconditions, and canonical test scope. Apply all six as one coherent change after the conditions are met. Rehash immediately before and after application. The ordinary verify.yml push already runs the SDK package check, SDK tests, complete CLI Swift tests, Python build tests, and Android engine package. This integration needs no new manual axis dispatch or workflow.

Canonical .5 remains SDK22 and adapter23, with 45 members and 569231 bytes. The conditional bare mixer.android-source-pair.6 retains SDK22 bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0 and selects adapter23 7765667bc3e4b1d45a58ac122ff61b2fbfd7bcfe09b2172ffced62189fb00885. Its 45 named source members total 569431 bytes. The only named adapter source change is the 4328-byte DocumentSession.swift candidate cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7. The native test is 11870 bytes with SHA256 7d274de5f4de44b9acf2affc7579a8d1a0bd77cc00a5afd1883b86862411553d. The 9587-byte descriptor retains SHA256 1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3.

Both Swift and Python retain explicit same-bare-.6 refusal for the exact broader24 ae18d494f768a280600dbefcad0cd55fb9a4b9b993c6cd441f084a08fbf6e03e tuple. All prior .5, mixed-pin, drift, export, and old-driver controls remain byte-identical to the reviewed proposal. The historical broader ID is mixer.android-source-pair.6-editor-view-api29-30-bc03288599ec-8cd611a5b07f. A future broader integration must rebase its identity.

All 64 previously pinned dependency rows match. The current 45-member map matches its compiled profile. Every patch hunk matches its exact preimage, reconstructs the reviewed after copy, and reverses to the before bytes. These are data comparisons. The initial review's 149 and correction review's 84 comparisons remain separately attributed to their sealed artifacts.

Reproduce the refresh with `python3 -B verification/android-axis-canonical-integration-refresh/refresh.py` from the repository root. The script reads bounded filesystem data, parses literals and patch hunks, and writes only this directory. It imports no subject code and starts no child. source-evidence.json binds every read input. receipt.json records the Python version, command, digest, outputs, and scope.

No canonical source, prior evidence, workflow, authority, or tracking file changed. No Git, gh, compiler, product runtime, Node oracle, network, process probe, signal, native instance, UI, or capture action ran. Local compiler and custody holds remain. Phones are disconnected. Native runtime, immutable published FieldLog packages, OTA, store, customer, and GA acceptance remain pending.
'''
write('README.md', readme.encode())

outputs = []
for path in sorted(OUT.rglob('*')):
    assert not path.is_symlink()
    if path.is_file() and path.name not in ['receipt.json', 'seal.json']:
        outputs.append({'path': str(path.relative_to(OUT)), **identity(path.read_bytes())})
receipt = {'schema': 1, 'status': status, 'owned_directory': OUT_REL,
    'date': '2026-10-29 parent/environment supplied',
    'command': 'python3 -B verification/android-axis-canonical-integration-refresh/refresh.py',
    'cwd': str(ROOT), 'tool': 'Python standard library filesystem, JSON, hashlib, re, and in-memory byte manipulation only',
    'tool_version': sys.version, 'source_revision_observed': None, 'source_revision_root_reported_only': root_report['delivered_head'],
    'tree_root_reported_only': root_report['delivered_tree'], 'source_projection_sha256': source_digest,
    'source_projection_members': len(rows), 'data_comparisons': len(CHECKS), 'inconsistent_data_comparisons': [],
    'current_named_members': 45, 'current_named_bytes': 569231, 'canonical_before_states': 6,
    'patch_forward_and_inverse_files': 6, 'prior64_preserved': True,
    'corrected_patch_unchanged': True, 'corrected_six_candidate_copies_unchanged': True,
    'prior_independent_reviews': {'initial_comparisons': 149,
        'initial_findings': initial_review['findings'],
        'correction_comparisons': 84, 'correction_findings': [],
        'resolved_prior_note': review['resolved_prior_note']},
    'root_reported_host_state': root_report, 'actual19_host_acceptance': False,
    'fresh_independent_refresh_review': 'pending', 'canonical_integration': 'unapplied',
    'subject_tests_compilers_CLIs_Node_oracles_network_Git_gh_executed': 0,
    'process_probes_signals_native_UI_capture_actions': 0, 'canonical_source_writes': 0,
    'prior_evidence_writes': 0, 'authority_selection_tracking_workflow_writes': 0,
    'writes_outside_owned_directory': 0, 'new_manual_axis_dispatch_required': False,
    'inputs_unchanged_during_read': True, 'all_existing_holds_preserved': True,
    'outputs': outputs, 'outputs_projection_sha256': projection(outputs),
    'limitations': recipe['scope_limits']}
write_json('receipt.json', receipt)
seal_outputs = outputs + [{'path': 'receipt.json', **identity((OUT / 'receipt.json').read_bytes())}]
write_json('seal.json', {'schema': 1, 'status': 'SEALED_SOURCE_DATA_REFRESH_ONLY',
                        'outputs': seal_outputs, 'outputs_projection_sha256': projection(seal_outputs),
                        'subject_tests_executed': 0, 'applied': False, 'independent_refresh_review': 'pending'})
print(json.dumps({'status': status, 'inputs': len(rows), 'comparisons': len(CHECKS),
                  'source_projection_sha256': source_digest, 'receipt': identity((OUT / 'receipt.json').read_bytes()),
                  'seal': identity((OUT / 'seal.json').read_bytes()), 'source_writes': 0}, indent=2))
