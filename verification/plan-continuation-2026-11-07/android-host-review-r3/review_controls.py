#!/usr/bin/env python3
"""Read retained host artifacts; never launch a compiler, VM, or process probe.

Writes are confined to this review directory. No subject verifier is imported.
"""
import ast
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
V = ROOT / 'verification/plan-continuation-2026-11-07'
REPAIR = V / 'android-runtime-repair'
FINAL = REPAIR / 'attempt-2'
ARCHIVE = Path('/tmp/mixer-20261107-host-B-r2-02-rollback-focus')
BASE = Path('/tmp/mixer-20261107-baseline/android/android-owner-renderer')
OLD = Path('/tmp/mixer-20261107-host-B-after-fatal-cleanup-fix')
TEST = 'native/android/tests/NativeOwnerV2ConcreteHostTests.java'
MAP = 'native/android/tests/private-owner-barrier-map.json'
ROSTER = 'native/android/tests/private-owner-host-roster.json'
RUNNER = 'native/android/tests/run-private-owner-host.py'
PROBE = 'native/android/tests/NativeOwnerV2ConcreteHostLeaves/dev/mixer/android/ConcreteHostProbe.java'
KINDS = ['clean', 'terminal-at-entry', 'terminal-before-return', 'dirty-at-entry',
         'dirty-before-return', 'ordinary-throw-after-callback', 'fatal-throw-after-callback']
checks = 0


def check(value, message):
    global checks
    checks += 1
    if not value:
        raise AssertionError(message)


def read(p):
    return json.loads(p.read_text())


def ident(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def snapshot():
    paths = set()
    for directory in [V / 'android-fix', V / 'android-review', V / 'host-runtime-attempts', REPAIR]:
        paths.update(p for p in directory.rglob('*') if p.is_file())
    paths.update(ROOT / p for p in read(FINAL / 'source-map.json'))
    paths.update(ROOT / p for p in ['AGENTS.md', 'PLAN.md', 'STATUS.md', 'work-graph.json',
                                 'gates/ga.json', '.github/workflows/verify.yml'])
    return {str(p.relative_to(ROOT)): ident(p) for p in sorted(paths)}


before = snapshot()
source_map = read(FINAL / 'source-map.json')
mapping = read(ROOT / MAP)
historical = read(ROOT / mapping['historical_map']['path'])
baseline_map = read(BASE / 'source-map.json')
current_roster = read(ROOT / ROSTER)
b = current_roster['closures']['B-concrete-renderer-views']
old_roster = read(BASE / 'inputs' / ROSTER)
check(current_roster['closures']['A-orchestration'] == old_roster['closures']['A-orchestration'], 'A roster drift')
check(b['actual_production_sources'] == old_roster['closures']['B-concrete-renderer-views']['actual_production_sources'], 'product roster drift')
check(len(b['actual_production_sources']) == 15, 'B subject roster excludes separately appended platform subject')
selected = b['actual_production_sources'] + ['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']
for name in selected:
    check(ident(ROOT / name) == baseline_map[name], 'baseline product drift: ' + name)
selected += [s['source'] for s in b['substitutes']] + b['test_support_sources'] + [b['test_source']]
check(len(selected) == len(set(selected)) == 103, 'explicit source count or duplicate')
check(len({s['fqcn'] for s in b['substitutes']}) == len(b['substitutes']), 'duplicate leaf type')
check(set(source_map) == set(selected + [MAP, ROSTER, RUNNER,
      'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json']), 'frozen input set')
for name, expected in source_map.items():
    check(ident(ROOT / name) == expected, 'live input drift: ' + name)
    check(ident(ARCHIVE / 'inputs' / name) == expected, 'archive input drift: ' + name)
old_source_map = read(OLD / 'source-map.json')
changed = sorted(p for p in source_map if source_map[p] != old_source_map[p])
check(changed == sorted([TEST, MAP]), 'R2 modified inputs beyond test/map')
check(ident(ROOT / PROBE) == read(REPAIR / 'receipt.json')['unchanged_probe'] == old_source_map[PROBE], 'probe changed by R2')
old_mapping = read(OLD / 'inputs' / MAP)
expected_mapping = copy.deepcopy(old_mapping)
next(r for r in expected_mapping['records'] if r['baseline'] == 'NativeRenderer:L238:C9:1')['boundary']['return_frame_line'] = 521
check(mapping == expected_mapping, 'R2 map changed beyond 826-to-521')
check(ident(ROOT / mapping['historical_map']['path'])['sha256'] == mapping['historical_map']['sha256'], 'historical map identity')
for name, digest in mapping['source_sha256'].items():
    check(source_map[name]['sha256'] == digest, 'map source hash: ' + name)
records = {r['baseline']: r for r in mapping['records']}
check(len(records) == len(historical['records']) == len(mapping['records']) == 189, 'site identities')
check(sum(s.startswith('introduced:') for s in records) == 5, 'introduced count')
anchors = set()
for old, record in zip(historical['records'], mapping['records']):
    check(old['baseline'] == record['baseline'] and old['required_cases'] == record['required_cases'] == KINDS, 'obligation/case loss')
    check(len(record['candidates']) == 1, 'unbounded invocation choice')
    c = record['candidates'][0]
    text = (ROOT / record['source']).read_text()
    offset = sum(len(line) for line in text.splitlines(keepends=True)[:c['line'] - 1]) + c['column'] - 1
    check(text[offset:].startswith(c['text']), 'stale live anchor: ' + record['baseline'])
    anchor = (record['source'], c['line'], c['column'])
    check(anchor not in anchors, 'duplicate live invocation anchor')
    anchors.add(anchor)
    check('InputConnectionWrapper' not in json.dumps(record['boundary']), 'obsolete wrapper target')
    if record.get('caller_frame'):
        check(record['caller_frame'] == 'innermost-at-anchor' and record['caller_method_prefix'].startswith('lambda$'), 'unbounded caller selector')
check(sum(r['source'].endswith('/NativeEditorConnectionV2.java') for r in records.values()) == 9, 'direct adapter obligation count')

# Validate outputs against commands and their archive copies, including failed runs.
for attempt, archive in [(REPAIR / 'attempt-1', Path('/tmp/mixer-20261107-host-B-r2-01-anchor-trace')), (FINAL, ARCHIVE)]:
    receipt = read(attempt / 'receipt.json')
    check(receipt['closure'] == 'B' and receipt['source_stable'] is True, 'run source stability')
    check(receipt['cleanup'] == {'scratch_removed': True, 'children_reaped': True, 'native_instances_created': False}, 'run cleanup')
    manifest = read(attempt / 'retained-artifacts.json')
    check(Path(manifest['full_input_and_class_archive']) == archive, 'archive reference')
    for name, expected in manifest['artifacts'].items():
        check(ident(attempt / name) == expected == ident(archive / name), 'retained artifact identity: ' + name)
    commands = read(attempt / 'commands.json')
    check([c['label'] for c in commands] == ['javac-version', 'java-version', 'revision', 'compile', 'bytecode', 'host'], 'command sequence')
    for c in commands:
        expected_exit = 1 if attempt.name == 'attempt-1' and c['label'] == 'host' else 0
        check(c['exit'] == expected_exit and c['child_reaped'] and not c['timeout'] and not c['output_limit_exceeded'], 'command outcome: ' + c['label'])
        for stream in ['stdout', 'stderr']:
            name = c['label'] + '.' + stream
            check(ident(archive / name) == c[stream], 'command output hash')
            if (attempt / name).exists():
                check(ident(attempt / name) == c[stream], 'copied command output hash')
    compile_command = next(c for c in commands if c['label'] == 'compile')
    argv = compile_command['argv']
    check(argv[1:7] == ['--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-classpath'], 'strict compile flags')
    check(argv[8] == '-sourcepath' and argv[7] == argv[9] and argv[10] == '-d', 'empty classpath/sourcepath')
    check(argv[12:] == [str(archive.resolve() / 'inputs' / name) for name in selected], 'compile explicit source list')
    scratch = Path(argv[11]).parent
    check(scratch.parent == archive.resolve() and not scratch.exists(), 'owned scratch removed')
    host = next(c for c in commands if c['label'] == 'host')
    check(host['argv'][1:4] == ['-ea', '-Xmx256m', '-cp'] and host['argv'][5] == 'dev.mixer.android.NativeOwnerV2ConcreteHostTests', 'host assertions and class')
    check(host['argv'][-1] == str(archive.resolve() / 'barrier-cases.json') and '--skip-matrix' not in receipt['argv'], 'matrix actually requested')
    check((attempt / 'compile.stderr').stat().st_size == (attempt / 'compile.stdout').stat().st_size == 0, 'strict compile diagnostics')
    if attempt == FINAL:
        check(receipt['status'] == 'passed-host-only', 'final host status')
        check((attempt / 'host.stdout').read_text() == 'PASS concrete actual16 host checks=14655; platform/JNI leaves, native runtime pending\n', 'host check count')
        check((attempt / 'host.stderr').read_bytes() == b'', 'final host stderr')
        check(host['elapsed'] < 300, 'host run bound')
    else:
        check(receipt['status'] == 'failed' and 'missing actual baseline sites [NativeRenderer:L344:C98:1]' in (attempt / 'host.stderr').read_text(), 'retained R2 failure')

class_map = read(FINAL / 'class-map.json')
check(len(class_map) == 343, 'compiled class count')
check(set(class_map) == {str(p.relative_to(ARCHIVE / 'classes')) for p in (ARCHIVE / 'classes').rglob('*.class')}, 'class archive set')
for name, expected in class_map.items():
    check(ident(ARCHIVE / 'classes' / name) == expected, 'class artifact hash: ' + name)


# Parse classfiles as data. Resolve each reported BCI and line without javap/Java.
class Reader:
    def __init__(self, data):
        self.data, self.pos = data, 0
    def take(self, n):
        data = self.data[self.pos:self.pos+n]
        self.pos += n
        if len(data) != n:
            raise ValueError('truncated classfile')
        return data
    def u1(self): return self.take(1)[0]
    def u2(self): return struct.unpack('>H', self.take(2))[0]
    def u4(self): return struct.unpack('>I', self.take(4))[0]


def parse_class(name):
    r = Reader((ARCHIVE / 'classes' / (name.replace('.', '/') + '.class')).read_bytes())
    check(r.u4() == 0xcafebabe, 'classfile magic')
    r.u2()
    check(r.u2() == 61, 'Java17 classfile version')
    pool, count, index = [None], r.u2(), 1
    while index < count:
        tag = r.u1()
        if tag == 1: value = r.take(r.u2()).decode('utf-8', errors='replace')
        elif tag in (3, 4): value = r.take(4)
        elif tag in (5, 6): value = r.take(8)
        elif tag in (7, 8, 16, 19, 20): value = r.u2()
        elif tag in (9, 10, 11, 12, 17, 18): value = (r.u2(), r.u2())
        elif tag == 15: value = (r.u1(), r.u2())
        else: raise ValueError('unknown constant tag ' + str(tag))
        pool.append((tag, value)); index += 1
        if tag in (5, 6): pool.append(None); index += 1
    utf = lambda i: pool[i][1]
    r.take(6)
    r.take(2*r.u2())
    def attrs(reader):
        return [(utf(reader.u2()), reader.take(reader.u4())) for _ in range(reader.u2())]
    for _ in range(r.u2()):
        r.take(6); attrs(r)
    methods = {}
    for _ in range(r.u2()):
        r.u2(); method, descriptor = utf(r.u2()), utf(r.u2())
        for attribute, data in attrs(r):
            if attribute != 'Code': continue
            cr = Reader(data); cr.take(4)
            code = cr.take(cr.u4()); cr.take(8*cr.u2()); lines = []
            for aname, body in attrs(cr):
                if aname == 'LineNumberTable':
                    lr = Reader(body)
                    lines = [(lr.u2(), lr.u2()) for _ in range(lr.u2())]
            methods[(method, descriptor)] = (code, sorted(lines))
    return methods, pool


parsed = {}
resolved = []


def resolve(frame):
    name = frame['class']
    if name not in parsed: parsed[name] = parse_class(name)
    methods, pool = parsed[name]
    check((frame['method'], frame['descriptor']) in methods, 'reported method/descriptor exists')
    code, lines = methods[(frame['method'], frame['descriptor'])]
    bci = frame['bytecodeIndex']
    check(0 <= bci < len(code) and code[bci] in (182, 183, 184, 185, 186), 'reported BCI is invoke instruction')
    check(next(line for start, line in reversed(lines) if start <= bci) == frame['line'], 'reported source line matches classfile')
    constant = pool[struct.unpack('>H', code[bci+1:bci+3])[0]]
    check(constant[0] in (10, 11, 18), 'invoke constant kind')
    owner_index, nt = constant[1]
    called_name, called_descriptor = pool[nt][1]
    owner = None if constant[0] == 18 else pool[pool[owner_index][1]][1]
    return pool[called_name][1], pool[called_descriptor][1], owner


matrix = read(FINAL / 'barrier-cases.json')
rows = matrix['cases']
required = {(r['baseline'], k) for r in records.values() for k in KINDS}
check(matrix['missing'] == [] and matrix['baselineSites'] == 184 and matrix['introducedSites'] == 5, 'matrix completeness summary')
check(len(rows) == len(required) == 1323 and {(r['site'], r['case']) for r in rows} == required, '189-by-7 exact Cartesian coverage')
check(collections.Counter(r['case'] for r in rows) == {k: 189 for k in KINDS}, 'case distribution')
callers = {}
for row in rows:
    record = records[row['site']]
    check(row['hit'] is True and len(row['selectedFrames']) == 1, 'matrix hit/exact caller')
    frame = row['selectedFrames'][0]
    record_class = 'dev.mixer.android.' + record['class']
    check(frame['line'] == record['candidates'][0]['line'] and (frame['class'] == record_class or frame['class'].startswith(record_class + '$')), 'matrix frame/source binding')
    if record.get('caller_frame'):
        check(frame['method'].startswith(record['caller_method_prefix']), 'direct lambda selector')
    key = f"{frame['class']}#{frame['method']}{frame['descriptor']}@{frame['bytecodeIndex']}"
    check(key == row['exactCaller'], 'exact caller serialization')
    callers.setdefault(row['site'], set()).add(key)
    check(row['nativePhase'] == ('entry' if row['case'] == 'clean' or row['case'].endswith('entry') else 'beforeReturn'), 'entry/return injection phase')
    check(row['boundaryMode'] == record['boundary']['mode'] and row['boundaryEquivalence'] == record['boundary']['equivalence'], 'boundary meaning preserved')
    suffix = record['boundary']['entry_native_suffix' if row['nativePhase'] == 'entry' else 'return_native_suffix']
    check(suffix == '*' or row['nativeMethod'] == suffix or row['nativeMethod'].endswith('.' + suffix), 'actual native method matches obligation')
    called = resolve(frame)
    if record['source'].endswith('/NativeEditorConnectionV2.java'):
        source_target = record['candidates'][0]['text'].split('target.', 1)[1].split('(', 1)[0]
        check(called[2] == 'android/view/inputmethod/InputConnection' and called[0] == source_target, 'actual adapter target invocation')
    if row['case'] == 'clean':
        resolved.append({'site': row['site'], 'exactCaller': key, 'invoked_name': called[0], 'invoked_descriptor': called[1], 'invoked_owner': called[2]})
check(all(len(c) == 1 for c in callers.values()) and len({next(iter(c)) for c in callers.values()}) == 189, 'all cases share distinct descriptor/BCI per site')
helpers = [json.loads(line) for line in (FINAL / 'helper-boundaries.jsonl').read_text().splitlines()]
expected_helpers = {r['baseline'] for r in records.values() if 'helper' in r['boundary']['mode'] or 'constructor' in r['boundary']['mode']}
check(len(helpers) == len(expected_helpers) == 15 and {h['site'] for h in helpers} == expected_helpers, 'helper boundary set')
secondary = []
for helper in helpers:
    boundary = records[helper['site']]['boundary']
    clean = next(row for row in rows if row['site'] == helper['site'] and row['case'] == 'clean')
    check(helper['helperNativeSequence'] == clean['helperNativeSequence'] and helper['exactCaller'] == clean['exactCaller'], 'helper trace/matrix equality')
    check(helper['finalAnchorMatches'] is True and helper['helperSequenceEnd'] == 'original invocation frame/operation left', 'helper end observed')
    last = helper['helperNativeSequence'][-1]
    check(last['phase'] == 'beforeReturn' and last['nativeMethod'] == boundary['return_native_suffix'], 'helper final event suffix')
    for actual, expected in [('receiverId', 'return_receiver_id'), ('receiverClass', 'return_receiver_class')]:
        check(boundary[expected] is None or last[actual] == boundary[expected], 'helper final receiver')
    check(any(f"{f['class']}#{f['method']}{f['descriptor']}@{f['bytecodeIndex']}" == helper['exactCaller'] for f in last['productionFrames']), 'helper remains in original exact caller')
    if boundary['return_frame_line'] is not None:
        frames = [f for f in last['productionFrames'] if f['class'] == 'dev.mixer.android.NativeAppearanceViewsV2' and f['line'] == boundary['return_frame_line']]
        check(bool(frames), 'secondary return-frame live anchor')
        for f in frames: resolve(f)
        secondary.append({'site': helper['site'], 'line': boundary['return_frame_line'], 'nativeMethod': last['nativeMethod']})
check(len(secondary) == 2 and {s['line'] for s in secondary} == {521, 719}, 'secondary anchors audited')
focus = [row for row in rows if row['site'] == 'NativeRenderer:L344:C98:1']
check(len(focus) == 7 and all(row['exactCaller'] == 'dev.mixer.android.NativeRenderer#restoreV2(Ldev/mixer/android/NativeRenderer$Candidate;)V@756' for row in focus), 'focus rollback all seven exact bindings')
check(focus == read(REPAIR / 'focus-restoration-cases.json'), 'focus receipt matches actual cases')

# Narrow source controls accompany artifact checks; they confer no native qualification.
tests = (ROOT / TEST).read_text()
runner = (ROOT / RUNNER).read_text(); ast.parse(runner)
check("'-Xlint:all','-Werror','-proc:none'" in runner and "'-sourcepath',empty" in runner, 'strict runner remains')
check("ident(frozen[source])['sha256']!=digest" in runner, 'frozen product-map hash guard')
check('checks+=NativeAndroidFixtureHostTests.run();' in tests, 'fixture groups called by main')
check('record.changing=!state.equals' not in tests and 'changing record forwarded IME edit' in tests, 'no changing-guard bypass')
check('editor.hostNotifyEditorCallbacks=state.equals("successor")' in tests and 'finally{ConcreteHostProbe.hook=previous;editor.hostNotifyEditorCallbacks=true;}' in tests, 'callback isolation restored')
check('new ImeFamily("sendKeyEvent"' not in tests and 'sendKeyEventRefusalControls();' in tests, 'key refusal replaces false success claim')
check('!returned&&!reached[0]' in tests and 'refused key published successor' in tests and 'refused key mutated editor' in tests, 'key refusal outcomes')
check('reached[0]&&escaped==fatal' in tests and 'state.equals("fatal")&&expected==fatal' in tests, 'fatal exact identity and narrow cleanup catch')
check('List.of("controls","navigation","buttonFocus")' in tests and 'rollback did not restore non-editor native focus' in tests and 'rollback native focus restoration boundary not reached' in tests, 'rollback scenarios and outcome/return witnesses')
check('last!=null&&last.phase.equals("beforeReturn")&&barrier.matches(last)' in tests and 'two selected sites collapsed to one actual descriptor/BCI' in tests, 'final helper and uniqueness assertions retained')
check('escaped==matrix.fatal||matrix.fixture.owner.cleanupLedger().firstFatal()==matrix.fatal' in tests, 'matrix fatal retention assertion')
fixture_test = (ROOT / 'native/android/tests/NativeAndroidFixtureHostTests.java').read_text()
for group in ['snapshots', 'replacementCallbacks', 'editorOutput', 'configurationAndLifecycle', 'accessibilityReplacement']:
    check('NativeAndroidFixtureHostTests::' + group in fixture_test, 'fixture group reachable: ' + group)
check('hostNotifyEditorCallbacks=false' in fixture_test and 'finally {editor.hostNotifyEditorCallbacks=true;}' in fixture_test, 'both fixture callback modes tested')
reuse = read(V / 'android-fix/reuse.json')
for item in reuse['files']:
    check(ident(ROOT / item['source']) == {k: item[k] for k in ['bytes', 'sha256']}, 'retained fixture ownership identity')
    if not item['target'].endswith('/android/widget/TextView.java'):
        check((ROOT / item['source']).read_bytes() == (ROOT / item['target']).read_bytes(), 'reused fixture drift')

# Earlier failures and initial review remain frozen evidence, not passed attempts.
initial_review = read(V / 'android-review/receipt.json')
check(initial_review['verdict'] == 'REQUEST_CHANGES', 'sealed initial verdict')
for directory, hashes in initial_review['parent_evidence'].items():
    if directory.startswith('/tmp/'):
        for name, expected in hashes.items():
            check(ident(Path(directory) / name) == expected, 'sealed prior failure artifact drift')
check('63 errors' in (BASE / 'compile.stderr').read_text(), 'original fixture compile failure retained')
check('Fatal: IME beginBatchEdit' in (V / 'host-runtime-attempts/B-initial/host.stderr').read_text(), 'initial fatal failure retained')
check('helper final native return anchor is not final dynamic boundary' in (V / 'host-runtime-attempts/B-retained-fatal-correction/host.stderr').read_text(), 'initial helper failure retained')
check('cases=231 assertions=1250' in (V / 'host-runtime-attempts/A-initial/host.stdout').read_text(), 'separate retained A pass')

# Independent in-memory negative controls: a passing summary alone is insufficient.
check(not any(f['line'] == 826 and f['class'] == 'dev.mixer.android.NativeAppearanceViewsV2'
              for h in helpers if h['site'] == 'NativeRenderer:L238:C9:1'
              for f in h['helperNativeSequence'][-1]['productionFrames']), 'stale selector rejected')
check({(r['site'], r['case']) for r in rows[:-1]} != required, 'removed matrix row rejected')
check(len({next(iter(c)) for c in callers.values()} - {focus[0]['exactCaller']}) == 188, 'collapsed clean caller rejected')
check(snapshot() == before, 'review inputs changed during read-only audit')
save('inputs.json', before)
save('resolved-bytecode-anchors.json', resolved)
save('result.json', {
    'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status': 'passed-independent-retained-evidence-controls', 'checks': checks,
    'python': sys.version, 'command': 'python3 -B verification/plan-continuation-2026-11-07/android-host-review-r3/review_controls.py',
    'revision': read(FINAL / 'receipt.json')['revision'], 'reviewer_script': ident(Path(__file__)),
    'selected_source_map': ident(FINAL / 'source-map.json'), 'selected_sources': len(selected),
    'frozen_inputs': len(source_map), 'compiled_classes_hashed': len(class_map),
    'product_subjects': 16, 'site_count': len(records), 'case_count': len(rows),
    'distinct_descriptor_bci_bindings': len(callers), 'classfile_validated_matrix_frames': len(rows),
    'helper_boundaries': len(helpers), 'secondary_anchors': secondary,
    'r2_changed_inputs': changed, 'final_test': ident(ROOT / TEST), 'final_map': ident(ROOT / MAP),
    'probe': ident(ROOT / PROBE), 'preserved_review_input_files': len(before),
    'reviewer_compiler_vm_native_process_probe_runs': 0,
    'cleanup': {'writes_only_in_review_directory': True, 'scratch_or_native_instances_created': False,
                'held_process_actions': False, 'subject_verifier_imports_or_execution': False,
                'source_trackers_workflow_commits_pushes_delegation': False},
    'scope': 'Closure B on controlled host JVM leaves. Retained execution independently audited; no reviewer VM execution. Fresh ordinary CI and native/GA qualification remain pending.'
})
print(json.dumps({'status': 'PASS', 'checks': checks, 'sites': len(records), 'cases': len(rows),
                  'bytecode_frames': len(rows), 'helper_boundaries': len(helpers)}))
