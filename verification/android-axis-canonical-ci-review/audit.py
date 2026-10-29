#!/usr/bin/env python3
"""Offline, data-only CI coverage audit. Never imports product/test subjects."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
HEAD = '3da0d01bd05565a6aad905997beddf6805826241'
TREE = '89297f81773cad23c94ebba1560deccda99c551f'
SELECTION = 'verification/android-axis-canonical-selection-2026-10-29/selection.json'
SELECTION_SHA = '97268470779866b15ee22eea2ffd9e66a01cb266ad9980ef652ca6ade2b8d91b'
BINDING = 'verification/github-delivery-axis-canonical-followup/engine-ci-canonical-binding.json'
BINDING_SHA = '5cf18926f783e344197122793c695ac5ebd61ed209e73950d6ce0216ef7f65cc'
TARGETS = [
    '.github/workflows/verify.yml',
    'cli/Sources/MixerBuild/AndroidSDKCompatibility.swift',
    'cli/Sources/MixerBuild/Resources/android-build.py',
    'cli/Tests/MixerBuildTests/AndroidSDKCompatibilityTests.swift',
    'cli/build-tests/test_android_sdk_compatibility.py',
    'native/android/engine/Sources/MixerAndroidRuntime/DocumentSession.swift',
    'native/android/engine/Tests/MixerAndroidRuntimeTests/AndroidTextFieldAxisRefusalTests.swift',
]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def record(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': digest(data)}


def bounded(path, limit):
    p = ROOT / path
    require(p.is_file() and not p.is_symlink(), 'Non-regular audit input: ' + path)
    require(p.stat().st_size <= limit, 'Oversized audit input: ' + path)
    return p.read_bytes()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


# Authenticate the selected immutable data before reading source text or AST.
selection_bytes = bounded(SELECTION, 73463)
require(len(selection_bytes) == 73463 and digest(selection_bytes) == SELECTION_SHA, 'Selection drift')
selection = json.loads(selection_bytes)
selected = {x['path']: x for x in selection['selectedRows']}
guarded = {}
for path in TARGETS:
    row = selected[path]
    data = bounded(path, row['bytes'])
    require(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Selected source drift: ' + path)
    guarded[path] = data
binding_bytes = bounded(BINDING, 3539)
require(digest(binding_bytes) == BINDING_SHA, 'Root first-push binding drift')
binding = json.loads(binding_bytes)
require(binding['head'] == HEAD and binding['tree'] == TREE, 'Root source binding differs')
require(binding['selection']['sha256'] == SELECTION_SHA, 'Root selection differs')
require(binding['registration']['id'] == 393488255, 'Wrong ordinary Engine workflow')
require(binding['engine']['id'] == 40960463690 and binding['engine']['run_attempt'] == 1, 'Wrong initial run')

capture = json.loads((HERE / 'capture.json').read_text())
run = capture['run']
require(run['head_sha'] == HEAD and run['workflow_id'] == 393488255, 'Live run source/workflow differs')
require(run['id'] == 40960463690 and run['run_attempt'] == 1 and run['event'] == 'push', 'Wrong live run')
require(run['path'] == '.github/workflows/verify.yml', 'Wrong live workflow path')
require(run['status'] == 'completed' and run['conclusion'] == 'success', 'Live run not passed')
jobs = json.loads((HERE / 'jobs.json').read_text())
require(jobs['total_count'] == 6 and len(jobs['jobs']) == 6, 'Incomplete job snapshot')
for job in jobs['jobs']:
    require(job['head_sha'] == HEAD and job['run_attempt'] == 1, 'Job head/attempt differs')
    require(job['status'] == 'completed' and job['conclusion'] == 'success', 'Job did not pass')
    require(all(s['status'] == 'completed' and s['conclusion'] == 'success' for s in job['steps']), 'Non-passing step')

logs = {}
log_metadata = []
for item in json.loads((HERE / 'raw-log-index.json').read_text()):
    chunks = []
    parts = []
    for path in item['parts']:
        require(path.startswith('raw-logs/') and '..' not in Path(path).parts, 'Unexpected raw path')
        data = (HERE / path).read_bytes()
        require(len(data) <= 35000, 'Raw chunk exceeded bound')
        chunks.append(data)
        parts.append(record(path, data))
    data = b''.join(chunks)
    logs[item['name']] = data.decode('utf-8').splitlines()
    log_metadata.append({**item, 'decoded_utf8_bytes': len(data), 'sha256': digest(data),
                         'lines': len(logs[item['name']]), 'parts': parts,
                         'public_raw_log_status': 'ignored by local .gitignore; excluded from public payload'})

swift = logs['swift']


def hits(name, predicate):
    return [{'line': i + 1, 'text': text} for i, text in enumerate(logs[name]) if predicate(text)]


def passing_line(fragment):
    rows = hits('swift', lambda s: fragment in s and ('passed' in s or ' ... ok' in s))
    require(len(rows) == 1, 'Missing/ambiguous passing test: ' + fragment)
    return rows[0]


# AST parsing is inventory only, after exact source guards; no subject import.
py_path = TARGETS[4]
py_tree = ast.parse(guarded[py_path].decode('utf-8'), filename=py_path)
python_methods = [n.name for n in ast.walk(py_tree) if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')]
require(len(python_methods) == 13, 'Unexpected Python source-pair inventory')
python_results = [{'name': n, 'passed': passing_line(n + ' (test_android_sdk_compatibility.')} for n in python_methods]

cli_path = TARGETS[3]
cli_methods = re.findall(r'func (androidCompatibility\w+)\(', guarded[cli_path].decode('utf-8'))
require(len(cli_methods) == 11, 'Unexpected CLI compatibility inventory')
cli_results = []
for name in cli_methods:
    found = passing_line('✔ Test ' + name + '(')
    count = re.search(r'with (\d+) test cases passed', found['text'])
    cli_results.append({'name': name, 'cases': int(count.group(1)) if count else 1, 'passed': found})
require(sum(x['cases'] for x in cli_results) == 70, 'Unexpected CLI case count')

axis_path = TARGETS[6]
axis_methods = re.findall(r'func (test\w+)\(', guarded[axis_path].decode('utf-8'))
require(len(axis_methods) == 8, 'Unexpected canonical axis inventory')
axis_results = [{'name': n, 'passed': passing_line('AndroidTextFieldAxisRefusalTests ' + n + "]'")} for n in axis_methods]
require(any('Executed 8 tests, with 0 failures' in s for s in swift), 'Missing axis suite summary')
require(any('✔ Test run with 16 tests in 3 suites passed' in s for s in swift), 'Missing existing engine summary')

workflow = guarded[TARGETS[0]].decode('utf-8')
for command in ['swift test --package-path cli', 'python3 -B -m unittest discover -s cli/build-tests -v',
                'swift test --package-path native/android/engine', 'mixer build --platform ios']:
    require(command in workflow, 'Expected workflow command absent: ' + command)
consumer = workflow.split('      - name: Generated consumer integration\n', 1)[1].split('      - name:', 1)[0]
require('--platform ios' in consumer and '--platform android' not in consumer, 'Generated consumer scope changed')

# These non-selected unchanged mapping files are hashed as read, not executed.
mapping_paths = ['native/android/engine/Package.swift', 'scripts/ci/check-android-binding.py',
                 'cli/Sources/MixerBuild/ProjectGenerator.swift']
mapping = {p: bounded(p, 100000) for p in mapping_paths}
generator = mapping[mapping_paths[2]].decode('utf-8')
require('platform: String = "ios"' in generator and 'config.targets = platform == "android" ? ["ios", "android"] : ["ios"]' in generator,
        'Default generated consumer platform changed')
binding_script = ast.parse(mapping[mapping_paths[1]].decode('utf-8'))
package_value = next(n.value.value for n in binding_script.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'PACKAGE' for t in n.targets))
require('MixerAndroidRuntime' not in package_value and 'DocumentSession.swift' not in package_value,
        'Stage4 harness now includes canonical Android engine; review scope')
scenario_node = next(n for n in binding_script.body if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'SCENARIOS' for t in n.targets))
scenario_text = scenario_node.value.func.value.value
scenarios = scenario_text.split()
require(len(scenarios) == 39, 'Unexpected Stage4 scenario inventory')
native = logs['swift-capability-native']
for scenario in scenarios:
    require(sum(bool(re.search(r'Z ' + re.escape(scenario) + r' 0$', s)) for s in native) == 3,
            'Missing debug/release/TSan Stage4 result: ' + scenario)
require(sum('Z fresh-build 0' in s for s in native) == 3, 'Missing Stage4 builds')

excerpts = {
    'swift_tools': hits('swift', lambda s: any(x in s for x in ['"xcode":', '"swift":', '"sourceRevision":', '"host":', 'Image: macos-15-arm64', 'Version: 20260907.0337.1'])),
    'cli_compatibility': [x['passed'] for x in cli_results],
    'python_source_pair': [x['passed'] for x in python_results],
    'canonical_axis': [x['passed'] for x in axis_results],
    'suite_summaries': hits('swift', lambda s: 'Executed 8 tests, with 0 failures' in s or '✔ Test run with 16 tests in 3 suites passed' in s or 'Ran 33 tests in' in s),
    'generated_consumer_command': hits('swift', lambda s: 'mixer create VerificationApp' in s or 'mixer test --directory' in s or 'mixer build --platform ios' in s or '"Debug",' in s or '"iphonesimulator",' in s or '"generic/platform=iOS Simulator",' in s),
    'capability_native_stage4': hits('swift-capability-native', lambda s: 'Z fresh-build 0' in s or 'Z cleanup-wrong-facade 0' in s),
    'android_owner_host': hits('android-owner-host', lambda s: 'Z PASS ' in s),
}
require(all(len(x['text']) <= 1500 for rows in excerpts.values() for x in rows), 'Excerpt line too large')
guards = {
    'selection': record(SELECTION, selection_bytes),
    'root_first_push_binding': record(BINDING, binding_bytes),
    'source_commit': HEAD, 'source_tree': TREE,
    'selected_source': [record(p, data) for p, data in guarded.items()],
    'additional_mapping_files': [record(p, data) for p, data in mapping.items()],
    'no_subject_import_or_execution': True,
}
inventory = {'cli': cli_results, 'cli_effective_cases': 70, 'python': python_results,
             'axis': axis_results, 'existing_engine_swift_testing': {'tests': 16, 'suites': 3},
             'stage4': {'modes': ['debug', 'release', 'tsan'], 'scenarios_per_mode': len(scenarios),
                        'scenarios': scenarios, 'includes_canonical_document_session': False}}
review = {
    'schema': 1, 'status': 'sealed-data-only-canonical-host-ci-coverage-review',
    'source_commit': HEAD, 'source_tree': TREE, 'run': run,
    'job_count': 6, 'successful_jobs': 6,
    'successful_steps': sum(len(x['steps']) for x in jobs['jobs']), 'failed_steps': 0, 'skipped_steps': 0,
    'actual_new_head_canonical_checks': {
        'cli_compatibility_declarations': 11, 'cli_compatibility_effective_cases': 70,
        'python_source_pair_methods': 13, 'canonical_axis_xctest_cases': 8,
        'existing_engine_swift_testing_tests': 16, 'existing_engine_swift_testing_suites': 3,
        'outcome': 'passed in ordinary Engine CI at exact delivered head',
    },
    'host_environment': {'os': 'macOS 15.7.9 (24G830)', 'architecture': 'arm64',
                         'runner_image': 'macos-15-arm64 20260907.0337.1',
                         'runner_version': '2.338.0', 'xcode': '26.3 (17C529)',
                         'swift': 'Apple Swift 6.2.4 (swiftlang-6.2.4.1.4 clang-1700.6.4.2)',
                         'ci_python_version': 'not emitted in reviewed decoded logs'},
    'other_host_evidence': {
        'android_owner_host': 'Ubuntu 24.04.5; image ubuntu-24.04 20261025.353.1; JDK17 required, patch not emitted in reviewed log; controlled JVM leaves only',
        'capability_native_stage4': '39 scenarios in each of debug/release/TSan; different host harness, excludes canonical DocumentSession and AndroidTextFieldAxisRefusalTests',
    },
    'consumer_scope': {
        'relocated_exported': 'CLI host test admits relocated and copied exported project and asserts exact canonical DocumentSession bytes; no compiler/tool consumer build in that test',
        'python_relocation': 'admission and pre-tool sentinel only; no Android compilation',
        'generated_consumer': 'create default iOS-only VerificationApp (ProjectGenerator default); host mixer test; unsigned iOS Debug generic simulator cross-build; no Android adapter copied by this step; no runtime instance launched by this reviewer',
    },
    'pending': ['generated Android Debug binary compile at canonical integrated source',
                'generated Android Release binary compile at canonical integrated source',
                'actual relocated Android Debug/Release consumer compile',
                'actual exported Android Debug/Release consumer compile',
                'Android runtime, UI, rendering, performance, physical-phone matrix',
                'immutable published package consumer and separate FieldLog repository qualification',
                'GA acceptance and accountable reviewer evidence'],
    'historical_evidence_policy': 'Prior isolated 19 host methods at base 2c751cbb remain historical and are not relabelled fresh canonical evidence. Canonical engine module now runs 8 new XCTest axis cases plus its broader existing 16-test module suite; this is not a like-for-like count comparison with isolated 11-method module fixtures.',
    'excluded': ['Rust 1.99.1 envelope artifact acquisition/qualification owned by root',
                 'artifact download or artifact content verification', 'OTA release authorization'],
    'local_execution': {'command': 'python3 -B verification/android-axis-canonical-ci-review/audit.py',
                        'python': sys.version, 'scope': 'standard-library data/AST/hash audit only; no subject imports, compiler or product execution',
                        'native_processes_started': 0, 'capture_or_UI_actions': 0},
}
save('source-guards.json', guards)
save('log-metadata.json', log_metadata)
save('excerpts.json', excerpts)
save('test-inventory.json', inventory)
save('review.json', review)
print(json.dumps({'status': review['status'], 'jobs': 6, 'steps': review['successful_steps'],
                  'cli_declarations': 11, 'cli_cases': 70, 'python_methods': 13,
                  'axis_cases': 8, 'existing_engine_tests': 16, 'stage4_scenarios_per_mode': 39}))
