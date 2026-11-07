#!/usr/bin/env python3
"""Read frozen parent evidence; write reviewer evidence here only. No subprocesses."""
import ast
import datetime
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN1 = Path('/tmp/mixer-20261107-host-B-after-source-fix')
RUN2 = Path('/tmp/mixer-20261107-host-B-after-fatal-cleanup-fix')
INPUTS = RUN2 / 'inputs'
BASELINE = Path('/tmp/mixer-20261107-baseline/android/android-owner-renderer')
checks = []


def read(path):
    return json.loads(path.read_text())


def ident(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def check(ok, label):
    if not ok:
        raise AssertionError(label)
    checks.append(label)


source_map = read(RUN2 / 'source-map.json')
for name, identity in source_map.items():
    check(ident(INPUTS / name) == identity, 'frozen identity: ' + name)
roster = read(INPUTS / 'native/android/tests/private-owner-host-roster.json')
b = roster['closures']['B-concrete-renderer-views']
baseline_roster = read(BASELINE / 'roster.json')
check(b['actual_production_sources'] == baseline_roster['actual_production_sources'], 'production subject roster retained')
for name in b['actual_production_sources'] + ['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']:
    baseline = read(BASELINE / 'source-map.json')
    check(source_map[name] == baseline[name], 'production subject unchanged: ' + name)

map_name = 'native/android/tests/private-owner-barrier-map.json'
mapping = read(INPUTS / map_name)
historical_path = ROOT / mapping['historical_map']['path']
check(ident(historical_path)['sha256'] == mapping['historical_map']['sha256'], 'historical map digest')
historical = read(historical_path)
check(len(mapping['records']) == len(historical['records']) == 189, '189 obligations retained')
anchors = set()
for old, new in zip(historical['records'], mapping['records']):
    check(old['baseline'] == new['baseline'] and old['required_cases'] == new['required_cases'] and len(new['required_cases']) == 7,
          'obligation/cases retained: ' + new['baseline'])
    candidate = new['candidates'][0]
    source = (INPUTS / new['source']).read_text()
    offset = sum(len(line) for line in source.splitlines(keepends=True)[:candidate['line'] - 1]) + candidate['column'] - 1
    check(source[offset:].startswith(candidate['text']), 'real invocation anchor: ' + new['baseline'])
    anchor = (new['source'], candidate['line'], candidate['column'])
    check(anchor not in anchors, 'distinct invocation anchor: ' + new['baseline'])
    anchors.add(anchor)
    check('InputConnectionWrapper' not in json.dumps(new['boundary']), 'no obsolete wrapper boundary: ' + new['baseline'])
for name, digest in mapping['source_sha256'].items():
    check(source_map[name]['sha256'] == digest, 'map source digest: ' + name)
adapters = [record for record in mapping['records'] if record['source'].endswith('/NativeEditorConnectionV2.java')]
check(len(adapters) == 9, 'nine direct adapter target obligations')
for record in adapters:
    check(record['candidates'][0]['text'].startswith('target.') and record['caller_frame'] == 'innermost-at-anchor'
          and record['caller_method_prefix'].startswith('lambda$'), 'bounded direct target selection: ' + record['baseline'])

reuse = read(ROOT / 'verification/plan-continuation-2026-11-07/android-fix/reuse.json')
for item in reuse['files']:
    check(ident(ROOT / item['source']) == {key: item[key] for key in ('bytes', 'sha256')}, 'reuse origin identity: ' + item['source'])
    if not item['target'].endswith('/TextView.java'):
        check((INPUTS / item['target']).read_bytes() == (ROOT / item['source']).read_bytes(), 'unchanged reused fixture: ' + item['target'])

tests = (INPUTS / b['test_source']).read_text()
probe = (INPUTS / 'native/android/tests/NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java').read_text()
runner = (INPUTS / 'native/android/tests/run-private-owner-host.py').read_text()
ast.parse(runner)
check('"NativeEditorConnectionV2"' in probe, 'adapter production frames included')
check("'-Xlint:all','-Werror','-proc:none'" in runner and "'-sourcepath',empty" in runner, 'strict compiler flags retained')
check(map_name in runner and "ident(frozen[source])['sha256']!=digest" in runner, 'runner selects and binds current map')
check('new ImeFamily("sendKeyEvent"' not in tests and 'sendKeyEventRefusalControls();' in tests, 'key event no longer expects forwarding')
check('record.changing=!state.equals' not in tests and 'changing record forwarded IME edit' in tests, 'changing guard remains live')
check('hostNotifyEditorCallbacks=true' in (INPUTS / 'native/android/tests/NativeOwnerV2ConcreteHostLeaves/android/widget/TextView.java').read_text(), 'fixture callback delivery defaults on')
check('checks+=NativeAndroidFixtureHostTests.run();' in tests, 'five fixture groups run before product scenarios')
check('state.equals("fatal")&&expected==fatal' in tests and 'reached[0]&&escaped==fatal' in tests, 'fatal cleanup correction retains state/identity and inner assertion')
check('two selected sites collapsed to one actual descriptor/BCI' in tests and 'helper final native return anchor is not final dynamic boundary' in tests,
      'matrix runtime uniqueness and helper suffix checks retained')

for run in (RUN1, RUN2):
    receipt = read(run / 'receipt.json')
    commands = read(run / 'commands.json')
    check(receipt['source_stable'] and receipt['cleanup']['children_reaped'] and receipt['cleanup']['scratch_removed'], 'parent run stable/clean: ' + run.name)
    check(next(command for command in commands if command['label'] == 'compile')['exit'] == 0, 'parent strict B compilation succeeded: ' + run.name)
    host = next(command for command in commands if command['label'] == 'host')
    check(host['exit'] == 1 and not host['timeout'] and not host['output_limit_exceeded'], 'parent B fails without timeout: ' + run.name)
check('Fatal: IME beginBatchEdit' in (RUN1 / 'host.stderr').read_text(), 'first fatal lifecycle failure preserved')
check('runMatrix(NativeOwnerV2ConcreteHostTests.java:689)' in (RUN2 / 'host.stderr').read_text(), 'second run reached matrix after fatal correction')

measure = next(record for record in mapping['records'] if record['baseline'] == 'NativeRenderer:L238:C9:1')
views = (INPUTS / 'native/android/app/src/dev/mixer/android/NativeAppearanceViewsV2.java').read_text().splitlines()
stale_line = measure['boundary']['return_frame_line']
check(stale_line == 826 and 'this.original=original;' in views[stale_line - 1], 'confirmed unrelated historical helper return selector')
check('text.measure(' in views[520], 'observed final return belongs to actual measure call at 521')
check('View.measure/beforeReturn@dev.mixer.android.NativeAppearanceViewsV2:521:measure' in (RUN2 / 'host.stderr').read_text(), 'runtime evidence identifies real final native return')

evidence = {}
for run in (RUN1, RUN2):
    evidence[str(run)] = {name: ident(run / name) for name in ('receipt.json', 'source-map.json', 'commands.json', 'host.stderr', 'host.stdout', 'compile.stderr', 'compile.stdout', 'javac-version.stdout', 'java-version.stderr')}
for name in ('receipt.json', 'source-map.json', 'verify-source-controls.py'):
    evidence['historical-initial-astra/' + name] = ident(ROOT / 'verification/plan-continuation-2026-11-07/android-fix' / name)
(OUT / 'source-map.json').write_text(json.dumps(source_map, indent=2, sort_keys=True) + '\n')
report = {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict': 'REQUEST_CHANGES', 'scope': 'Independent frozen source/data review; no reviewer compiler/runtime execution or GA claim',
    'frozen_inputs': str(INPUTS), 'revision': read(RUN2 / 'receipt.json')['revision'],
    'source_map_identity': ident(OUT / 'source-map.json'), 'python': sys.version,
    'command': 'python3 -B verification/plan-continuation-2026-11-07/android-review/review_controls.py',
    'controls': len(checks), 'reviewer_script': ident(Path(__file__)),
    'controls_summary': ['Frozen input identities; unchanged production roster and bytes',
                         '189 obligations, seven cases each, real unique invocation anchors',
                         'Direct adapter frames/targets; 11 reused fixture identities',
                         'Strict runner; changing refusal; default-on callbacks; fatal identity assertions',
                         'Parent exit/cleanup evidence and stale helper selector failure'],
    'findings': [{'priority': 'P1', 'id': 'R1', 'site': measure['baseline'], 'map_line': 97,
                  'problem': 'Return-frame selector 826 is an EditorLease constructor assignment; real final measurement callback is line 521. B stops at retained helper suffix assertion (test line 689).',
                  'required': 'Rebind to real final callback frame; preserve helper final-event, seven-case, and exact runtime-site checks. Full B must pass before slice acceptance.'}],
    'resolved_prior_failure': 'Initial fatal beginBatchEdit escaped Fixture.close; narrow state/identity catch is present in frozen run2, whose execution reaches runMatrix.',
    'source_coverage': {'baseline_obligations': 184, 'introduced_obligations': 5, 'authored_case_combinations': 1323,
                        'completed_matrix': False, 'direct_adapter_sites': 9, 'identical_reused_leaves': 11},
    'historical_receipt': 'Initial Astra receipt/source-map predates fatal cleanup correction; read only and not rerun or overwritten.',
    'parent_evidence': evidence,
    'limitations': ['All parent execution facts are read from retained artifacts; no duplicate tests launched.',
                    'Run2 reaches matrix only; it does not prove all 1323 cases or missing-site emptiness.',
                    'Controlled fixtures cover selected behavior; Android framework/emulator/physical-device/GA qualification not established.',
                    'R2 changing sources excluded; reviewed identity is frozen run2.'],
    'cleanup': {'writes_only_here': True, 'source_edits': False, 'compiler_or_runtime_runs': False,
                'child_agents': 0, 'commits_or_pushes': False, 'native_processes_probed': False},
}
(OUT / 'receipt.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'controls': len(checks), 'verdict': report['verdict'], 'blocker': 'R1: stale helper return_frame_line=826; actual measure return at 521',
                  'frozen_source_map_sha256': report['source_map_identity']['sha256']}))
