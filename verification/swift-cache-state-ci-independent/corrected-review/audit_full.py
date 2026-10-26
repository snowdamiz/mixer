#!/usr/bin/env python3
"""Independent raw-output/content audit of the one corrected full invocation."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).absolute().parent
RUN = HERE / 'correction-2-copy/runs/independent-rust-1-99-full'
EXPECTED_RUNNER = 'e531311facb7b38967d3b904b26e92ff3f6c4dc7444c856cd799b70a1d91373b'
EXPECTED_REVISION = '8ac624160a2cfff10d201d8063f69cf05f005edb'
APPEND = b'\n#[cfg(test)]\n#[path = "../selected_controls.rs"]\nmod selected_scalar_controls;\n\n#[cfg(test)]\n#[path = "../scalar_cursor_independent.rs"]\nmod scalar_cursor_independent;\n'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def unique(pairs):
    d = {}
    for k, v in pairs:
        assert k not in d
        d[k] = v
    return d

def strict(data):
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))

def main():
    receipt = strict((RUN / 'receipt.json').read_bytes())
    launch = strict((HERE / 'evidence/full-invocation/launch.json').read_bytes())
    assert receipt['status'] == 'passed-host-fixture-check' and receipt['active_checks_completed'] and receipt['errors'] == []
    assert launch['exit'] == 0 and launch['child_returned'] and launch['foreign_directory_unchanged']
    assert receipt['active_elapsed_seconds'] <= 600 and receipt['cleanup_elapsed_seconds'] <= 60 and receipt['elapsed_seconds'] <= 660
    assert receipt['source_revision'] == receipt['source_revision_after'] == EXPECTED_REVISION
    assert receipt['source_tree'] == receipt['source_tree_after'] and re.fullmatch('[0-9a-f]{40}', receipt['source_tree'])
    assert receipt['runner']['sha256'] == sha(RUN / 'executed-runner.py') == EXPECTED_RUNNER
    assert receipt['rustc']['identity']['release'] == '1.99.0' and receipt['rustc']['identity']['host'] == 'aarch64-apple-darwin'
    assert all(v['passed'] for v in receipt['postflight'].values()) and len(receipt['postflight']) == 9
    assert receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned'] and not (RUN / 'scratch').exists()
    assert not any(receipt[k] for k in ['storedPrefixValidated', 'fullReplayAccepted', 'semanticMetricsValid', 'GA_qualified', 'model_imported_or_evaluated'])
    pack = RUN / 'pack'
    assert sha(pack / 'manifest.json') == '6c52eb0ed737530d92011ce63e1eda593159c670b262a5f7bcf8b54b5338d857'
    manifest = strict((pack / 'manifest.json').read_bytes())
    for row in manifest['members']:
        path = pack / row['path']
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    methods = strict((pack / 'inventories/methods.json').read_bytes())
    layouts = strict((pack / 'inventories/layouts.json').read_bytes())
    cases = strict((pack / 'inventories/file-cases.json').read_bytes())
    api = strict((pack / 'inventories/api-contract.json').read_bytes())
    markers = strict((pack / 'inventories/control-markers.json').read_bytes())
    assert api['probes'] == strict((HERE.parent / 'independent-api-contract.json').read_bytes())['probes']
    own = strict((HERE.parent / 'independent-expected-inventory.json').read_bytes())
    assert layouts['layouts'] == own['complete_producer_layouts']
    expected_commands = ['compiler-sysroot', 'compiler-identity', 'source-revision', 'source-tree']
    for mode in ['debug', 'optimized']:
        for lane in ['host', 'producer', 'independent', 'controls']:
            expected_commands += [lane + '-' + mode + '-compile', lane + '-' + mode + '-list']
            groups = methods['producer_debug_partition'] if lane == 'producer' and mode == 'debug' else [{'name': 'all'}]
            expected_commands += [lane + '-' + mode + '-' + g['name'] for g in groups]
        expected_commands.append('library-' + mode)
        for probe in api['probes']:
            name = 'api-' + probe['name'].replace('/', '_') + '-' + mode
            expected_commands.append(name)
            if probe['expected_success']:
                expected_commands.append(name + '-execute')
    expected_commands += ['source-revision-after', 'source-tree-after']
    commands = receipt['commands']
    assert [r['name'] for r in commands] == expected_commands and len(commands) == 103
    by_name = {r['name']: r for r in commands}
    scratch = RUN / 'scratch'
    for row in commands:
        assert strict((RUN / 'commands' / (row['name'] + '.json')).read_bytes()) == row
        assert row['child_returned'] and row['owned_group_gone'] and not row.get('descendants_outlived_child')
        assert not row['timed_out'] and not row['output_capped'] and row['effective_timeout_seconds'] <= 60
        for stream in ['stdout', 'stderr']:
            path = RUN / 'commands' / (row['name'] + '.' + stream)
            assert sha(path) == row[stream + '_sha256'] and path.stat().st_size <= 8 * 1024 * 1024
        temp = row['environment_overrides']
        assert len({temp[k] for k in ['TMPDIR', 'TMP', 'TEMP']}) == 1
        path = Path(temp['TMPDIR'])
        assert path.is_absolute() and '..' not in path.parts and path.is_relative_to(scratch)
    retention = strict((RUN / 'retention.json').read_bytes())
    retained = {r['path']: r for r in retention['files']}
    assert len(retained) == len(retention['files'])
    def content(row):
        path = RUN / row['content']
        assert sha(path) == row['retained_sha256']
        data = gzip.decompress(path.read_bytes()) if row['encoding'] == 'gzip' else path.read_bytes()
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
        return data
    for row in retention['files']:
        content(row)
    products = retention['compiler_products_hashed_before_removal']
    assert products == receipt['cleanup']['products_hashed_before_removal'] and len(products) == 14
    by_product = {p['path']: p for p in products}
    for row in receipt['derivative']['source_rows']:
        data = content(retained['derived/' + row['path']])
        assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
    assert len(receipt['derivative']['source_rows']) == 19
    assert content(retained['derived/library/cache_state.rs']) == (pack / 'source/library/cache_state.rs').read_bytes() + APPEND
    def output(name, stream='stdout'):
        return (RUN / 'commands' / (name + '.' + stream)).read_text()
    def method_output(text, expected, filtered=None):
        if filtered is None:
            actual = [line[:-6] for line in text.splitlines() if line.endswith(': test')]
            assert re.findall(r'^(\d+) tests, (\d+) benchmarks$', text, re.M) == [(str(len(expected)), '0')]
        else:
            actual = re.findall(r'^test (\S+) \.\.\. ', text, re.M)
            assert re.findall(r'^test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored; (\d+) measured; (\d+) filtered out; finished in [^\n]+$', text, re.M) == [(str(len(expected)), '0', '0', '0', str(filtered))]
            assert len(re.findall(r'(?:^|\n)ok$| \.\.\. ok$', text, re.M)) == len(expected)
        assert len(actual) == len(set(actual)) == len(expected) and set(actual) == set(expected)
        return actual
    mode_results = {}
    boundaries = dict(zip(['Unavailable', 'ClosedFixtureObserved', 'CapCutUnknownTail', 'Refused', 'AnalysisLimited', 'InternalPoisoned', 'ApplicabilityUnavailable'], range(7)))
    reasons = dict(zip(['Observed', 'Steps', 'FramingUnavailable', 'FramingInvalid', 'EnvelopeRefused', 'EnvelopeUnavailable', 'Identity', 'Resident', 'Plan', 'Victim', 'Bytes', 'Token', 'Nonce', 'Invariant', 'FailureApplicability', 'IncompleteBoundary', 'InternalPoison', 'OutputUnavailable'], range(18)))
    for mode in ['debug', 'optimized']:
        method_invocations = 0; normalized = set(); complete_capture_cases = 0; API_spans = 0
        for lane in ['host', 'producer', 'independent', 'controls']:
            method_output(output(lane + '-' + mode + '-list'), methods[lane])
            groups = methods['producer_debug_partition'] if lane == 'producer' and mode == 'debug' else [{'name': 'all', 'methods': methods[lane], 'args': []}]
            observed = []
            for group in groups:
                name = lane + '-' + mode + '-' + group['name']
                text = output(name)
                observed += method_output(text, group['methods'], len(methods[lane]) - len(group['methods']))
                assert by_name[name]['exit'] == 0
                assert by_name[name]['argv'][1:] == [*group['args'], '--test-threads=1', '--nocapture']
                if lane in ['host', 'controls']:
                    actual_layouts = [{'type': t, 'bytes': int(n), 'align': int(a)} for t, n, a in re.findall(r'ACCOUNTING_LAYOUT (.+?) size=(\d+) align=(\d+)', text)]
                    assert actual_layouts == layouts['layouts'] and len(actual_layouts) == 23
                    prefix = lane + '-' + mode + '-all/cases/'
                    actual_names = {p[len(prefix):].split('/')[0] for p in retained if p.startswith(prefix)}
                    assert actual_names == {c['case'] for c in cases['cases']}
                    for case in cases['cases']:
                        case_prefix = prefix + case['case'] + '/'
                        assert {p[len(case_prefix):] for p in retained if p.startswith(case_prefix)} == {'input-0.bin', 'input-1.bin', 'input-2.bin', 'report.bin', 'result.txt'}
                        for filename, want in case['raw'].items():
                            actual = retained[case_prefix + filename]
                            assert actual['sha256'] == want['sha256'] and actual['bytes'] == want['bytes']
                        lines = content(retained[case_prefix + 'result.txt']).decode().splitlines()
                        assert len(lines) == 2 and lines[0] == case['result_first_line'] and lines[1].startswith('input_stamps_before_and_after=[')
                        match = re.search(r'cache_state: FixtureCacheStateObservationV1 \{ boundary: (\w+), reason: (\w+), extent: \[([^]]+)\]', lines[0])
                        projection = None
                        if match:
                            boundary, reason, extent = match.groups()
                            projection = [boundaries[boundary], reasons[reason]] + [int(v.strip()) for v in extent.split(',')]
                            assert len(projection) == 32
                        assert projection == case['actual_complete32'] and bool(match) == case['aggregate_present']
                        complete_capture_cases += int(match is not None)
                if lane == 'controls':
                    for key, value in markers.items():
                        assert re.findall(re.escape(key) + r'=([^\n]+)', text) == [value]
            assert len(observed) == len(set(observed)) == len(methods[lane]) and set(observed) == set(methods[lane])
            assert receipt['modes'][mode]['methods'][lane]['names'] == sorted(observed)
            assert receipt['modes'][mode]['methods'][lane]['binary_sha256'] == by_product[lane + '-' + mode]['sha256']
            method_invocations += len(observed)
            normalized |= {n.removeprefix('product::') for n in observed}
        assert method_invocations == 384 and len(normalized) == 132 and complete_capture_cases == 58
        for probe in api['probes']:
            name = 'api-' + probe['name'].replace('/', '_') + '-' + mode
            row = by_name[name]
            assert row['exit'] == (0 if probe['expected_success'] else 1)
            if probe['expected_success']:
                assert by_name[name + '-execute']['exit'] == 0 and name in by_product
                continue
            expected = {(p['byte_start'], p['byte_end']) for p in probe['primary_spans']}; seen = set()
            pending = [strict(line) for line in output(name, 'stderr').splitlines() if line.strip()]
            while pending:
                diagnostic = pending.pop()
                assert isinstance(diagnostic, dict) and isinstance(diagnostic.get('children', []), list)
                pending.extend(diagnostic.get('children', []))
                if diagnostic.get('level') != 'error':
                    continue
                code = diagnostic.get('code')
                if code is None:
                    assert re.fullmatch(r'aborting due to \d+ previous errors?(?:; \d+ warnings? emitted)?', diagnostic['message'])
                    continue
                assert code['code'] == probe['code'] and all(t in diagnostic['message'] for t in probe['message_contains'])
                primary = [s for s in diagnostic['spans'] if s['is_primary']]
                assert primary
                for span in primary:
                    pair = (span['byte_start'], span['byte_end'])
                    assert span['file_name'] == probe['source'] and pair in expected and pair not in seen
                    seen.add(pair)
            assert seen == expected
            API_spans += len(seen)
        assert API_spans == 38
        mode_results[mode] = {'method_invocations': method_invocations, 'distinct_methods': len(normalized),
            'lane_counts': {k: len(methods[k]) for k in ['host', 'producer', 'independent', 'controls']},
            'API_dispositions': 25, 'API_negative': 23, 'API_positive_executions': 2, 'API_primary_spans': API_spans,
            'captured_File_instances': 62, 'captured_complete32_instances': complete_capture_cases,
            'distinct_File_cases': 31, 'public_cases': 29, 'public_complete32': 27, 'public_outer_errors': 2,
            'private_poison_cases': 2, 'complete_accounting_layouts': 23}
    assert all(row['exit'] in [0, 1] for row in commands)
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'script_sha256': sha(Path(__file__)), 'runner_sha256': EXPECTED_RUNNER,
        'runner_receipt_sha256': sha(RUN / 'receipt.json'), 'launch_receipt_sha256': sha(HERE / 'evidence/full-invocation/launch.json'),
        'source_revision': EXPECTED_REVISION, 'source_tree': receipt['source_tree'],
        'compiler': receipt['rustc'], 'commands': 103, 'active_elapsed_seconds': receipt['active_elapsed_seconds'],
        'cleanup_elapsed_seconds': receipt['cleanup_elapsed_seconds'], 'elapsed_seconds': receipt['elapsed_seconds'],
        'max_child_seconds': max(r['elapsed_seconds'] for r in commands), 'modes': mode_results,
        'all103children_owned_TMP': True, 'hostile_inherited_directory_unchanged': True,
        'all_command_outputs_and_retained_bytes_hashed': True, 'retained_files_verified': len(retained),
        'derived_source_files_verified': 19, 'compiler_products_hashed_removed': 14,
        'postflight_checks_passed': len(receipt['postflight']), 'scratch_removed': True,
        'passed': True, 'limits': ['Actual Rust1.99.0 macOS arm64 host fixture closure only',
            'Historical full producer Debug60s timeout remains failed; no performance equivalence',
            'No Rust1.98.1, canonical CI/runtime, general public File, native, signing/store, FieldLog, operations or GA qualification']}
    (HERE / 'full-audit.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'passed': True, 'commands': 103, 'method_invocations_each_mode': 384,
        'distinct_methods_each_mode': 132, 'API_each_mode': 25, 'complete_File_instances_each_mode': 58,
        'elapsed_seconds': receipt['elapsed_seconds'], 'max_child_seconds': report['max_child_seconds']}))

if __name__ == '__main__':
    main()
