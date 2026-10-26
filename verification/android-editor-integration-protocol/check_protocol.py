#!/usr/bin/env python3
"""Offline preparation checks. Success never accepts candidate, map, native or release."""
import copy
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATES = {'current', 'successor', 'terminal', 'dirty', 'stale', 'fatal'}
MATRIX_STATES = {'clean', 'terminal-at-entry', 'terminal-before-return', 'dirty-at-entry',
                 'dirty-before-return', 'ordinary-throw-after-callback', 'fatal-throw-after-callback'}
def ident(data): return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
def load(name): return json.loads((HERE / name).read_text())
def projection(files):
    return hashlib.sha256(''.join(p + '\0' + files[p]['sha256'] + '\n' for p in sorted(files)).encode()).hexdigest()
def require(value, message):
    if not value: raise ValueError(message)

def check_certificate(value, expected):
    """Integrity-only synthetic model. Real compiled inventories are separately required."""
    require(value['status'] == 'synthetic-integrity-fixture', 'not a synthetic fixture')
    require(set(value['subjects']) == set(expected['subjects']), 'subject inventory')
    require(len(value['sites']) == len(expected['sites']), 'site inventory')
    by_id = {site['id']: site for site in value['sites']}
    require(len(by_id) == len(value['sites']), 'duplicate IDs')
    require(set(by_id) == {site['id'] for site in expected['sites']}, 'site IDs')
    for original in expected['sites']:
        site = by_id[original['id']]
        for key in ('source', 'source_sha256', 'class', 'class_sha256', 'method', 'descriptor', 'bci', 'opcode', 'target'):
            require(site[key] == original[key], 'compiled identity ' + key)
        require(site['bci'] in site['instruction_boundaries'], 'BCI inside instruction')
        require(set(site['cases']) == MATRIX_STATES, 'state rows')
        for case in site['cases'].values():
            require(case['hit'] and case['caller'] == [site['class'], site['method'], site['descriptor'], site['bci']], 'exact caller/hit')
            require(case['executed'] and not case['source_only'], 'source-only execution claim')
    return True

def fixture():
    sites = []
    for index, subject in enumerate(('NativeRenderer', 'NativeAppearanceViewsV2$NativeField', 'NativeEditorConnectionV2$Base')):
        site = {'id': 'fixture-' + str(index), 'source': subject.split('$')[0] + '.java',
            'source_sha256': 'a' * 64, 'class': 'dev.mixer.android.' + subject, 'class_sha256': 'b' * 64,
            'method': 'fixture', 'descriptor': '(I)Z', 'bci': 6, 'instruction_boundaries': [0, 1, 3, 6, 9],
            'opcode': 'invokeinterface', 'target': 'fixture/Target.fixture:(I)Z', 'cases': {}}
        for state in MATRIX_STATES:
            site['cases'][state] = {'hit': True, 'caller': [site['class'], site['method'], site['descriptor'], site['bci']],
                'executed': True, 'source_only': False}
        sites.append(site)
    return {'status': 'synthetic-integrity-fixture', 'subjects': [site['class'] for site in sites], 'sites': sites}

def main():
    manifest = load('input-manifest.json')
    for path, identity in manifest.items():
        require(ident((HERE / 'inputs' / path).read_bytes()) == {k: identity[k] for k in ('bytes', 'sha256')}, 'input identity ' + path)
    current = load('current-profile4.json')
    proposed = load('proposed-profile5.json')
    require(current['id'] == 'mixer.android-source-pair.4', 'current profile ID')
    require(len(current['sdk_files']) == 22 and len(current['adapter_files']) == 23, 'current source counts')
    for kind in ('sdk', 'adapter'):
        require(projection(current[kind + '_files']) == current[kind + '_compatibility_sha256'], 'current projection')
        for relative, identity in current[kind + '_files'].items():
            repository = ('sdk/' if kind == 'sdk' else 'native/android/' + ('engine/' if relative.startswith('Sources/') else '')) + relative
            require(ident((HERE / 'inputs/repo' / repository).read_bytes()) == identity, 'profile source ' + repository)
    require(proposed['root_acceptance'] is None and proposed['candidate_binding']['acceptance'].startswith('pending'), 'proposal silently accepted')
    require(proposed['id'] == 'mixer.android-source-pair.5', 'proposed ID')
    require(proposed['sdk_files'] == current['sdk_files'] and proposed['sdk_compatibility_sha256'] == current['sdk_compatibility_sha256'], 'SDK drift')
    require(proposed['default_descriptor'] == current['default_descriptor'] and proposed['wire'] == current['wire'], 'descriptor/wire drift')
    require(len(proposed['adapter_files']) == 24, 'proposed adapter count')
    require(sum(path.endswith('.java') for path in proposed['adapter_files']) == 18, 'export Java count')
    require(set(proposed['adapter_files']) - set(current['adapter_files']) == {'app/src/dev/mixer/android/NativeEditorConnectionV2.java'}, 'new adapter subject')
    require(not (set(current['adapter_files']) - set(proposed['adapter_files'])), 'old adapter dropped')
    changed = {p for p in current['adapter_files'] if current['adapter_files'][p] != proposed['adapter_files'][p]}
    require(changed == {'app/src/dev/mixer/android/' + n for n in ('NativeAppearanceViewsV2.java', 'NativeCoordinatorV2.java', 'NativeRenderer.java')}, 'unexpected source delta')
    require(projection(proposed['adapter_files']) == proposed['adapter_compatibility_sha256'], 'proposed projection')
    binding = load('released-correction-binding.json')
    require(binding['root_acceptance'] is None and binding['candidate_selection'] is None, 'binding claims acceptance')
    released_seal = load('inputs/released-correction/seal.json')
    released_files = {}
    for member in released_seal['members']:
        if not member['path'].startswith('source/'): continue
        data = (HERE / 'inputs/released-correction' / member['path']).read_bytes()
        identity = ident(data)
        require(identity == {k: member[k] for k in ('bytes', 'sha256')}, 'released source identity')
        name = member['path'].removeprefix('source/')
        require(proposed['adapter_files']['app/src/dev/mixer/android/' + name] == identity, 'proposal source pair')
        released_files[name] = identity
    require(hashlib.sha256(json.dumps(released_files, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == binding['source_tree_sha256'], 'released product tree')
    require(ident((HERE / 'inputs/released-correction/seal.json').read_bytes())['sha256'] == binding['seal_sha256'], 'released seal')
    observer_guard = 'if (Build.VERSION.SDK_INT < 36 || root.getContext() != activity) unsupported();'
    renderer_guard = 'if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);'
    require(observer_guard in (HERE / 'inputs/released-correction/source/NativeEnvironmentV2.java').read_text(), 'observer guard')
    require(renderer_guard in (HERE / 'inputs/released-correction/source/NativeRenderer.java').read_text(), 'renderer guard')
    design = load('family-migration.json')
    require(len(design['families']) == 16 and design['designed_state_rows'] == 96, 'family roster')
    require(len({row['family'] for row in design['families']}) == 16, 'duplicate family')
    for row in design['families']:
        require(set(row['cases']) == STATES, 'missing family state')
        require(not row['watchers_suppressed'] and not row['listener_removed'] and row['new_transport_leaf_mode'] is None, 'suppression mode')
        require(row['ordinary_can_publish_successor'] != row['successor_is_injected_feature_event'], 'natural/injected successor')
    require(design['separate_invalid_entry']['changing'] is True and design['append_contract']['initial_selection'] == [0, 0], 'entry/cursor contract')
    require(not design['sendKeyEvent']['accepted'] and set(design['sendKeyEvent']['all_states']) == STATES, 'sendKey contract')
    lists = load('source-lists.json')
    for label, entry in lists['closures'].items():
        before = entry['current_explicit_product_sources']; after = entry['proposed_explicit_product_sources']
        require(len(before) == (11 if label.startswith('A-') else 15), 'host current roster')
        require(len(after) == len(set(after)) == (11 if label.startswith('A-') else 16), 'host proposed roster')
        require(any(p.endswith('NativeEditorConnectionV2.java') for p in after) == label.startswith('B-'), 'direct adapter closure')
    cross = lists['crosscompile']
    require(len(cross['current_java']) == 23 and len(cross['proposed_java']) == 24 and len(cross['current_swift_c_h']) == 76, 'cross source counts')
    require(len(set(cross['proposed_java'])) == 24, 'duplicate cross source')
    require(any(p.endswith('Package.swift') for p in cross['current_swift_c_h']), 'missing package manifests')

    driver_path = HERE / 'inputs/repo/cli/Sources/MixerBuild/Resources/android-build.py'
    spec = importlib.util.spec_from_file_location('frozen_profile4_driver', driver_path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.SOURCE_PROFILE_HEX = json.dumps(current).encode().hex()
    require(driver.source_profile() == current, 'actual frozen driver profile4 positive')
    negative_results = []
    proposed_policy = {key: proposed[key] for key in current}
    for label, value in [('unrendered', None), ('new-profile5-is-not-currently-admitted', proposed_policy),
                         ('missing-adapter', {**current, 'adapter_files': {}}), ('wrong-sdk-count', {**current, 'sdk_files': {}}),
                         ('projection-drift', {**current, 'adapter_compatibility_sha256': '0' * 64})]:
        driver.SOURCE_PROFILE_HEX = '__MIXER_ANDROID_SOURCE_PROFILE_HEX__' if value is None else json.dumps(value).encode().hex()
        refused = False
        try: driver.source_profile()
        except RuntimeError: refused = True
        require(refused, 'frozen driver negative accepted: ' + label)
        negative_results.append(label)

    expected = fixture()
    require(check_certificate(expected, expected), 'synthetic positive')
    mutations = {
        'foreign-source-hash': lambda v: v['sites'][0].update(source_sha256='c' * 64),
        'foreign-class-hash': lambda v: v['sites'][0].update(class_sha256='c' * 64),
        'wrong-overload': lambda v: v['sites'][0].update(descriptor='(J)Z'),
        'middle-of-instruction': lambda v: v['sites'][0].update(bci=7),
        'wrong-opcode': lambda v: v['sites'][0].update(opcode='invokevirtual'),
        'neighbor-target': lambda v: v['sites'][0].update(target='fixture/Other.fixture:(I)Z'),
        'missing-site': lambda v: v['sites'].pop(),
        'duplicate-id': lambda v: v['sites'][1].update(id=v['sites'][0]['id']),
        'missing-direct-subject': lambda v: v['subjects'].pop(),
        'missing-state': lambda v: v['sites'][0]['cases'].pop('clean'),
        'zero-hit': lambda v: v['sites'][0]['cases']['clean'].update(hit=False),
        'wrong-caller-bci': lambda v: v['sites'][0]['cases']['clean'].update(caller=['foreign', 'fixture', '(I)Z', 6]),
        'source-only-as-executed': lambda v: v['sites'][0]['cases']['clean'].update(source_only=True),
    }
    for label, mutate in mutations.items():
        value = copy.deepcopy(expected); mutate(value); refused = False
        try: check_certificate(value, expected)
        except ValueError: refused = True
        require(refused, 'synthetic integrity mutation accepted: ' + label)
        negative_results.append('synthetic:' + label)
    support = load('support-controls/receipt.json')
    require(support['status'] == 'passed-historical-host-support-only', 'support status')
    require(support['cleanup']['scratch_removed'] and support['cleanup']['children_reaped'], 'support cleanup')
    require(not support['cleanup']['native_ui_capture_processes_queried_or_started'], 'native/capture query')
    output = {'status': 'passed-offline-preparation-only', 'python': platform.python_version(),
        'argv': sys.argv, 'checker': ident(Path(__file__).read_bytes()), 'copied_inputs_checked': len(manifest),
        'input_projection_sha256': projection(manifest), 'source_revision': load('freeze-receipt.json')['commands'][0]['stdout'],
        'profile4_source_entries': 45, 'proposal_profile5_source_entries': 46, 'family_design_rows': 96,
        'actual_historical_support': '9 controls / 61 assertions', 'negative_controls': negative_results,
        'corrected_source_execution': 'not run by this lane', 'real_compiled_map_qualification': 'pending root selection and fresh execution',
        'native_ui_capture_processes_queried_or_started': False, 'acceptance_or_release_authorized': False}
    (HERE / 'offline-check-receipt.json').write_text(json.dumps(output, indent=2, sort_keys=True) + '\n')
    print('PASS offline protocol:', len(manifest), 'copied inputs; 96 designed rows; 5 actual frozen driver refusals; 13 synthetic map-integrity refusals; no candidate acceptance')

if __name__ == '__main__': main()
