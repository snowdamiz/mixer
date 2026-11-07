#!/usr/bin/env python3
"""Check retained JVM matrix output against every frozen callback obligation."""
import collections
import hashlib
import json
import pathlib
import sys

evidence = pathlib.Path(sys.argv[1]).resolve()
root = pathlib.Path(__file__).resolve().parents[3]
mapping_path = 'native/android/tests/private-owner-barrier-map.json'
mapping = json.loads((evidence / 'inputs' / mapping_path).read_text())
sources = json.loads((evidence / 'source-map.json').read_text())
receipt = json.loads((evidence / 'receipt.json').read_text())
commands = json.loads((evidence / 'commands.json').read_text())

def identity(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

assert receipt['closure'] == 'B'
assert receipt['status'] == 'passed-host-only', receipt
assert receipt['source_stable'] is True
assert receipt['cleanup'] == {'scratch_removed': True, 'children_reaped': True,
                              'native_instances_created': False}
assert [c['label'] for c in commands] == ['javac-version', 'java-version', 'revision',
                                       'compile', 'bytecode', 'host']
for command in commands:
    assert command['exit'] == 0 and command['child_reaped'] is True
    assert not command['timeout'] and not command['output_limit_exceeded']
    for stream in ('stdout', 'stderr'):
        assert identity(evidence / (command['label'] + '.' + stream)) == command[stream]
for path, expected in sources.items():
    assert identity(evidence / 'inputs' / path) == expected, path
    assert identity(root / path) == expected, 'current source changed: ' + path
for path, digest in mapping['source_sha256'].items():
    assert sources[path]['sha256'] == digest

historical = json.loads((root / 'verification/android-private-owner-integration-implementation/barrier-map.json').read_text())
assert len(mapping['records']) == len(historical['records']) == 189
for old, current in zip(historical['records'], mapping['records']):
    assert (old['baseline'], old['required_cases']) == (current['baseline'], current['required_cases'])
required = {(r['baseline'], case) for r in mapping['records'] for case in r['required_cases']}
assert len(required) == 189 * 7
matrix = json.loads((evidence / 'barrier-cases.json').read_text())
assert matrix['missing'] == []
assert matrix['baselineSites'] == 184 and matrix['introducedSites'] == 5
assert len(matrix['cases']) == len(required)
assert {(r['site'], r['case']) for r in matrix['cases']} == required
distinct = {}
for row in matrix['cases']:
    assert row['hit'] is True
    assert len(row['selectedFrames']) == 1
    frame = row['selectedFrames'][0]
    assert frame['descriptor'].startswith('(') and frame['bytecodeIndex'] >= 0
    exact = f"{frame['class']}#{frame['method']}{frame['descriptor']}@{frame['bytecodeIndex']}"
    assert exact == row['exactCaller']
    assert row['nativePhase'] == ('entry' if row['case'] == 'clean' or row['case'].endswith('entry') else 'beforeReturn')
    if row['case'] == 'clean':
        assert exact not in distinct, (exact, distinct.get(exact), row['site'])
        distinct[exact] = row['site']
assert len(distinct) == 189

helpers = [json.loads(line) for line in (evidence / 'helper-boundaries.jsonl').read_text().splitlines()]
expected_helpers = {r['baseline']: r for r in mapping['records']
                    if 'helper' in r['boundary']['mode'] or 'constructor' in r['boundary']['mode']}
assert len(helpers) == len(expected_helpers)
assert {r['site'] for r in helpers} == set(expected_helpers)
for helper in helpers:
    assert helper['finalAnchorMatches'] is True
    assert helper['helperSequenceEnd'] is not None
    last = helper['helperNativeSequence'][-1]
    assert last['phase'] == 'beforeReturn'
    boundary = expected_helpers[helper['site']]['boundary']
    assert last['nativeMethod'] == boundary['return_native_suffix']
    for actual, expected in [('receiverId', 'return_receiver_id'), ('receiverClass', 'return_receiver_class')]:
        if boundary[expected] is not None:
            assert last[actual] == boundary[expected]
    if boundary['return_frame_line'] is not None:
        assert any(f['class'] == 'dev.mixer.android.NativeAppearanceViewsV2'
                   and f['line'] == boundary['return_frame_line'] for f in last['productionFrames'])
    assert any(f"{f['class']}#{f['method']}{f['descriptor']}@{f['bytecodeIndex']}" == helper['exactCaller']
               for f in last['productionFrames'])

print(json.dumps({'status': 'verified-retained-host-evidence', 'sites': len(distinct),
                  'cases': len(required), 'cases_by_kind': dict(collections.Counter(r['case'] for r in matrix['cases'])),
                  'helper_boundaries': len(helpers), 'sources': len(sources),
                  'host_stdout': (evidence / 'host.stdout').read_text().strip(),
                  'scope': 'controlled JVM leaves; no Android native runtime qualification'}, indent=2))
