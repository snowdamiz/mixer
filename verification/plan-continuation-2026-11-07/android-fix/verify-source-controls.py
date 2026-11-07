#!/usr/bin/env python3
"""Source/data controls only. This script never launches a compiler or child process."""
import ast
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASELINE = Path('/tmp/mixer-20261107-baseline/android/android-owner-renderer')
checks = 0


def check(value, message):
    global checks
    checks += 1
    if not value:
        raise AssertionError(message)


def identity(path):
    value = path.read_bytes()
    return {'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def read(path):
    return json.loads(path.read_text())


before = read(OUT / 'before.json')
baseline = read(BASELINE / 'source-map.json')
roster_path = 'native/android/tests/private-owner-host-roster.json'
roster = read(ROOT / roster_path)
baseline_roster = read(BASELINE / 'inputs' / roster_path)
check(roster['closures']['A-orchestration'] == baseline_roster['closures']['A-orchestration'], 'closure A roster changed')
old_b = baseline_roster['closures']['B-concrete-renderer-views']
new_b = roster['closures']['B-concrete-renderer-views']
check(new_b['actual_production_sources'] == old_b['actual_production_sources'], 'actual product subjects changed')
check(all(item in new_b['substitutes'] for item in old_b['substitutes']), 'old substitute dropped')
check(len(new_b['substitutes']) == len(old_b['substitutes']) + 6, 'unexpected substitute delta')
selected = new_b['actual_production_sources'] + ['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']
for source in selected:
    check(identity(ROOT / source) == before[source] == baseline[source], 'product source drift: ' + source)
selected += [item['source'] for item in new_b['substitutes']] + new_b['test_support_sources'] + [new_b['test_source']]
check(len(selected) == len(set(selected)) == 103, 'duplicate/missing B source')
check(len({item['fqcn'] for item in new_b['substitutes']}) == len(new_b['substitutes']), 'duplicate substitute type')
for source in selected:
    check((ROOT / source).is_file(), 'missing explicit source: ' + source)
for source, value in before.items():
    if source.startswith(('native/android/app/src/', 'native/android/owner-core/src/', 'native/android/tests/NativeOwnerV2HostLeaves/')):
        check(identity(ROOT / source) == value, 'unowned production/A fixture edit: ' + source)

historical_path = 'verification/android-private-owner-integration-implementation/barrier-map.json'
historical = read(ROOT / historical_path)
check(identity(ROOT / historical_path) == before[historical_path], 'historical map changed')
mapping_path = 'native/android/tests/private-owner-barrier-map.json'
mapping = read(ROOT / mapping_path)
check(mapping['historical_map']['sha256'] == identity(ROOT / historical_path)['sha256'], 'historical map binding')
check(len(mapping['records']) == len(historical['records']) == 189, 'callback obligation count')
seen = set()
for old, new in zip(historical['records'], mapping['records']):
    check(new['baseline'] == old['baseline'] and new['required_cases'] == old['required_cases'], 'obligation removed or weakened')
    check(len(new['required_cases']) == 7, 'missing callback case')
    source = (ROOT / new['source']).read_text()
    candidate = new['candidates'][0]
    offset = sum(len(line) for line in source.splitlines(keepends=True)[:candidate['line'] - 1]) + candidate['column'] - 1
    check(source[offset:].startswith(candidate['text']), 'stale source anchor: ' + new['baseline'])
    anchor = (new['class'], candidate['line'], candidate['column'])
    check(anchor not in seen, 'duplicate source anchor')
    seen.add(anchor)
    check('InputConnectionWrapper' not in json.dumps(new['boundary']), 'obsolete wrapper boundary')
    if new.get('caller_frame'):
        check(new['caller_frame'] == 'innermost-at-anchor' and new['caller_method_prefix'].startswith('lambda$'), 'unbounded caller selector')
for source, digest in mapping['source_sha256'].items():
    check(identity(ROOT / source)['sha256'] == digest, 'unbound current callback map')
check(sum(record['source'].endswith('NativeEditorConnectionV2.java') for record in mapping['records']) == 9, 'direct adapter callback obligations')
runner_path = 'native/android/tests/run-private-owner-host.py'
runner = (ROOT / runner_path).read_text()
ast.parse(runner)
check(mapping_path in runner and historical_path not in runner, 'runner mapping selection')
check("ident(frozen[source])['sha256']!=digest" in runner, 'runner lacks frozen-source map guard')
check("'-Xlint:all','-Werror','-proc:none'" in runner and "'-sourcepath',empty" in runner, 'strict compilation weakened')
probe = (ROOT / 'native/android/tests/NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java').read_text()
check('"NativeEditorConnectionV2"' in probe, 'direct adapter frames omitted')
tests = (ROOT / new_b['test_source']).read_text()
check('new ImeFamily("sendKeyEvent"' not in tests and 'sendKeyEventRefusalControls();' in tests, 'obsolete key success expectation')
check('checks+=NativeAndroidFixtureHostTests.run();' in tests, 'fixture behavior checks not executed by B main')
check('record.changing=!state.equals' not in tests and 'changing record forwarded IME edit' in tests, 'changing admission guard bypass')
check('two selected sites collapsed to one actual descriptor/BCI' in tests and 'missing actual baseline sites' in tests, 'runtime matrix obligations weakened')
for item in read(OUT / 'reuse.json')['files']:
    check(identity(ROOT / item['source']) == {key: item[key] for key in ('bytes', 'sha256')}, 'retained owned fixture changed')
    if not item['target'].endswith('/android/widget/TextView.java'):
        check((ROOT / item['source']).read_bytes() == (ROOT / item['target']).read_bytes(), 'unexpected retained fixture divergence')

changed = sorted(path for path, value in before.items() if path.startswith('native/android/tests/') and identity(ROOT / path) != value)
changed += sorted(str(path.relative_to(ROOT)) for path in (ROOT / 'native/android/tests').rglob('*') if path.is_file() and str(path.relative_to(ROOT)) not in before)
selected += [mapping_path, roster_path, runner_path]
source_map = {path: identity(ROOT / path) for path in sorted(selected)}
(OUT / 'source-map.json').write_text(json.dumps(source_map, indent=2, sort_keys=True) + '\n')
product_receipt_path = 'verification/plan-continuation-2026-11-07/android-product-compile/receipt.json'
product_receipt = read(ROOT / product_receipt_path)
check(product_receipt['status'] == 'passed-crosscompile-only', 'unexpected parent product compilation status')
receipt = {
    'schema': 1,
    'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'passed-source-data-controls; compiler-and-host-runtime-pending',
    'role': {'model': 'gpt-6-astra', 'reasoning': 'xhigh', 'child_agents_started': 0},
    'command': 'python3 -B verification/plan-continuation-2026-11-07/android-fix/verify-source-controls.py',
    'python': sys.version,
    'controls': checks,
    'revision': read(BASELINE / 'receipt.json')['revision'],
    'revision_basis': 'retained CI receipt; current actual product sources byte-equal to its frozen source map',
    'source_map_sha256': identity(OUT / 'source-map.json')['sha256'],
    'verifier': identity(Path(__file__)),
    'changed_paths': changed,
    'baseline': {name: identity(BASELINE / name) for name in ('compile.stderr', 'receipt.json', 'source-map.json')},
    'baseline_result': 'run 40974383080: A 231 cases / 1250 assertions passed; B failed with 63 javac errors before host execution',
    'hypotheses': {
        'incomplete_controlled_fixtures': 'selected; missing Android types/members present in earlier independently owned fixtures; all production subjects preserved',
        'production_integration_defect': 'not supported as explanation of these 63 missing-fixture diagnostics; parent separately compiled actual product against SDK37 and D8 minAPI28',
    },
    'parent_crosscompile': {'path': product_receipt_path, **identity(ROOT / product_receipt_path), 'status': product_receipt['status'], 'scope': product_receipt['scope']},
    'coverage': {
        'B_explicit_java_sources': 103, 'actual_product_subjects': 16,
        'baseline_callback_obligations_retained': 184, 'introduced_obligations_retained': 5,
        'callback_cases_required': 1323, 'callback_cases_executed_here': 0,
        'direct_adapter_target_obligations_rebound': 9, 'API_bridge_obligations_rebound': 5,
        'native_field_continuation_lambda_selectors': 5,
        'new_fixture_behavior_groups_authored': 5, 'key_refusal_states_authored': 6,
        'admission_guard_control': 'record.changing now explicitly refuses; positive IME return checks use a non-notifying controlled native delegate without altering product authority',
        'fixture_delta': '12 retained leaves reused; TextView adds default-on callback-delivery control, tested in both modes; all other reused leaves byte-identical',
        'append_test_setup': 'two helloz assertions now explicitly place cursor at end; replacement fixture correctly initializes selection at zero',
    },
    'pending': ['strict A/B compiler execution', 'new five fixture groups and six key-refusal states', 'complete 189-site/seven-case callback matrix and exact runtime BCI uniqueness', 'native/device behavior and generated-consumer qualification'],
    'known_limits': ['controlled leaves model selected editor behavior only, not the Android framework', 'source anchors and lambda frame selectors need runtime confirmation; source controls are not OTA or GA authorization', 'parent SDK/D8 success is separate from host fixture execution', 'native runtime resumption does not authorize touching historical held processes or frozen lanes'],
    'next_local_B_command': 'python3 -B native/android/tests/run-private-owner-host.py --jdk /opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home --closure B --evidence /tmp/mixer-20261107-host-B-after-source-fix',
    'next_CI_B_command': 'python3 -B native/android/tests/run-private-owner-host.py --jdk "$JAVA_HOME_17_X64" --closure B --evidence "$RUNNER_TEMP/android-owner-renderer"',
    'cleanup': {'compiler_runtime_native_or_capture_processes_started_here': False, 'process_probes_performed_here': False, 'scratch_created_here': False, 'other_projects_touched': False, 'commits_or_pushes': False},
}
(OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(f'PASS {checks} source/data controls; 103 explicit B Java sources; all 189 callback obligations retained; compiler/host runtime pending')
