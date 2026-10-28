#!/usr/bin/env python3
"""Review saved V3 bytes and run the unchanged independent parser once.

No producer imports/checker, compiler, child, runtime or signal/process query.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'verification/swift-root-bound-work-storage-layout-probe'
V2 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v2'
V3 = ROOT / 'verification/swift-root-bound-work-storage-layout-probe-v3'
COMMAND = V3 / 'command'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, 'duplicate JSON key'
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def hashed(path):
    assert path.is_file() and not path.is_symlink(), path
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        while raw := handle.read(262144):
            digest.update(raw)
            size += len(raw)
    return {'bytes': size, 'sha256': digest.hexdigest()}


def pin(row, base):
    assert hashed(base / row['path']) == {key: row[key] for key in ('bytes', 'sha256')}, row['path']


def sealed(base, name, expected, count, closure=False):
    assert hashed(base / name)['sha256'] == expected
    seal = decode((base / name).read_bytes())
    assert len(seal['members']) == seal['member_count'] == count
    assert sha(canonical(seal['members'])) == seal['tree_sha256']
    for row in seal['members']:
        pin(row, base)
    if closure:
        assert not any(path.is_symlink() for path in base.rglob('*'))
        assert sorted(path.relative_to(base).as_posix() for path in base.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + [name])
    return seal


def main():
    started = time.monotonic()
    sealed(OLD, 'seal.json', 'c0e4da5b92f9fc076db21cb59700876bda60efaa7dc4b3c191124b707436fad9', 173, True)
    sealed(V2, 'seal.json', '76fda3e073db9bb7408275cf5d8eb494cf491e5a9cd0a894ba8cca35171127f8', 16, True)
    sealed(V3, 'seal.json', '898e88217ab2f04505d09571dbd8748b85cabc3b443a0dde12c47f4c800ed72c', 17)
    sealed(HERE, 'preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22)
    sealed(HERE, 'review-01-seal.json', 'edbf7e50d0d8b1847ac75d391d47ba6a16c17e73e6811b153203b8cafe5fc15c', 5)
    sealed(HERE, 'review-02-seal.json', '8409755f4e955a4ccdc2132eeea5b3218aee44fbe87127d288f434360852a0fa', 5)
    sealed(HERE, 'review-03-seal.json', '373f849c3ce8aafa861ca4c9585d9521794cd85f43259df47ef4858fa0bcb753', 5)
    plan = decode((V3 / 'plan.json').read_bytes())
    assert sha((V3 / 'plan.json').read_bytes()) == '95e3ebb57acc3c5ea9e7baac1f657c05ae36ffc957d86b77b38231f4480f958e'
    for field, base in [('original_source', Path(plan['original_source']['directory'])),
                        ('diagnostic_source', OLD / 'source/vm')]:
        rows = plan[field]['members']
        assert len(rows) == 146 and sha(canonical(rows)) == plan[field]['tree_sha256']
        assert not any(path.is_symlink() for path in base.rglob('*'))
        assert sorted(path.relative_to(base).as_posix() for path in base.rglob('*') if path.is_file()) == sorted(row['path'] for row in rows)
        for row in rows:
            pin(row, base)
    tools = decode((OLD / 'toolchain-manifest.json').read_bytes())
    assert sha(canonical(tools['members'])) == tools['tree_sha256']
    for row in tools['members']:
        pin(row, Path(tools['root']))
    pin(plan['compiler'], ROOT)
    pin(plan['python']['tool'], ROOT)
    assert sys.version == plan['python']['version']
    for row in decode((OLD / 'sdk-path-settings.json').read_bytes())['settings']:
        pin(row, ROOT)
    receipt = decode((COMMAND / 'receipt.json').read_bytes())
    run_plan = decode((COMMAND / 'plan.json').read_bytes())
    owned = decode((COMMAND / 'owned-process.json').read_bytes())
    assert receipt['plan_sha256'] == run_plan['plan_sha256'] == sha((V3 / 'plan.json').read_bytes())
    assert run_plan['argv'] == plan['argv'] and run_plan['environment'] == plan['environment'] and run_plan['cwd'] == plan['cwd']
    assert run_plan['bounds'] == plan['bounds'] and run_plan['toolchain_version'] == plan['toolchain_version']
    release_path = ROOT / plan['root_release_required']['path']
    assert hashed(release_path)['sha256'] == receipt['root_release_sha256'] == run_plan['root_release_sha256'] == '10b544451522d3474ecb840098f7dbaba28852b8116ee84539dd4d3168507874'
    release = decode(release_path.read_bytes())
    assert release['compiler_lane_released'] is True and release['compiler_invocations'] == 1
    assert release['plan_sha256'] == receipt['plan_sha256']
    names = ['plan.json', 'plan.json.staged', 'owned-process.json', 'owned-process.json.staged',
             'receipt.json', 'receipt.json.staged', 'stderr', 'stdout']
    assert sorted(path.name for path in COMMAND.iterdir()) == sorted(names)
    assert not any(path.is_symlink() for path in COMMAND.rglob('*'))
    assert sorted(path.relative_to(V3).as_posix() for path in V3.rglob('*') if path.is_file()) == sorted(
        [row['path'] for row in decode((V3 / 'seal.json').read_bytes())['members']] + ['seal.json'] + ['command/' + name for name in names])
    for name in ['plan.json', 'owned-process.json', 'receipt.json']:
        assert (COMMAND / name).read_bytes() == (COMMAND / (name + '.staged')).read_bytes()
    stderr = (COMMAND / 'stderr').read_bytes()
    stdout = (COMMAND / 'stdout').read_bytes()
    assert len(stderr) == 292318 and sha(stderr) == '05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'
    assert stdout == b''
    for name in ('stderr', 'stdout'):
        assert hashed(COMMAND / name) == {key: receipt['outputs'][name][key] for key in ('bytes', 'sha256')}
        assert receipt['captured_output_bytes'][name] == receipt['observed_output_bytes'][name] == receipt['outputs'][name]['bytes']
    assert receipt['compiler_invocations'] == 1 and receipt['compiler_exit_code'] == 1
    assert receipt['accepted_diagnostic_observation'] is False
    assert receipt['posthashes_verified'] is True and receipt['exception'] is None
    assert receipt['elapsed_seconds_including_cleanup_posthashes'] < 55
    assert receipt['ownership'] == {'child_started': True, 'child_reaped': True, 'exact_pid_absent': True,
                                     'exact_group_absent': True, 'exit_code': 1}
    assert owned == {'global_inventory': False, 'new_session': True, 'pgid': 23228, 'pid': 23228}
    assert receipt['launch']['retained_pid'] == owned['pid'] and receipt['launch']['deferred_signals'] == []
    assert receipt['publication_cutoff']['cutoff_reached'] is True and receipt['publication_cutoff']['pre_cutoff_signal_count'] == 0
    assert receipt['build_cleanup'] == {'build_existed': True, 'inventory': [], 'preserved_reason': None, 'removed': True}
    assert not (OLD / 'build').exists() and not (COMMAND / 'diagnostic-observation.json').exists()
    assert receipt['failures'] == [{'classification': 'diagnostic-or-output-rejection',
                                    'detail': 'Rejected: unexpected coded diagnostic: unused_imports'}]
    parser_path = HERE / 'independent_diagnostic_parser.py'
    assert hashed(parser_path)['sha256'] == 'fa5bd75b75f1c06f452a6e45c62b08cb3cbcc7b892f9e7a580a7d2adabcb9dad'
    spec = importlib.util.spec_from_file_location('frozen_terminal_parser_v3', parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    try:
        parser.parse_diagnostics(stderr, stdout, receipt['compiler_exit_code'])
    except parser.Refusal as error:
        refusal = {'type': type(error).__name__, 'message': str(error), 'accepted': False}
        traceback.print_exc(file=sys.stderr)
    else:
        raise AssertionError('frozen parser unexpectedly accepted the original raw stream')
    assert refusal['message'] == 'unexpected-top-level-diagnostic'
    raw_lines = stderr.splitlines()
    records = [decode(line) for line in raw_lines]
    assert len(records) == 64
    bindings = decode((HERE / 'diagnostic-bindings-corrected.json').read_bytes())
    sources = {name: raw.encode() for name, raw in bindings['staged_two_sources'].items()}
    coordinates = ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end')
    def same(actual, expected):
        return all(actual.get(key) == expected[key] for key in coordinates)
    spans_reviewed = []
    def spans(value):
        if isinstance(value, list):
            for child in value:
                yield from spans(child)
        elif isinstance(value, dict):
            if all(key in value for key in coordinates) and 'file_name' in value:
                yield value
            for child in value.values():
                yield from spans(child)
    # Source geometry checking reads saved records only. It changes neither the
    # parser contract nor any record supplied to its single full-stream call.
    for index, record in enumerate(records):
        for span in spans(record):
            token = parser.validate_span(span)
            spans_reviewed.append({'record': index, 'file': span['file_name'],
                                   'range': {key: span[key] for key in coordinates}, 'selected': token})
    named_seen = set()
    closure_evidence = []
    warning_evidence = []
    summaries = []
    counts = {}
    for index, record in enumerate(records):
        assert record.get('$message_type') == 'diagnostic'
        code = record.get('code')
        code = code.get('code') if isinstance(code, dict) else None
        kind = record.get('level') + ':' + str(code)
        counts[kind] = counts.get(kind, 0) + 1
        if code == 'E0308':
            primary = [span for span in record['spans'] if span['is_primary'] is True]
            assert len(primary) == 1
            primary = primary[0]
            expansion = primary['expansion']
            assert expansion['macro_decl_name'] == 'pair!'
            matches = [row for row in bindings['named_queries'] if row['file'] == primary['file_name']
                       and same(primary, row['query_rhs']) and same(expansion['span'], row['invocation'])]
            assert len(matches) == 1 and matches[0]['id'] not in named_seen
            named_seen.add(matches[0]['id'])
        elif code == 'E0512':
            assert record['level'] == 'error' and len(record['spans']) == 1
            primary = record['spans'][0]
            assert primary['is_primary'] is True and primary['expansion'] is None
            candidates = [row for row in bindings['closure_queries']
                          if primary['file_name'] == bindings['closure_file']
                          and primary['byte_start'] == row['expression']['byte_start']]
            assert len(candidates) == 1
            row = candidates[0]
            source = sources[primary['file_name']]
            assert source[primary['byte_start']:primary['byte_end']] == b'std::mem::transmute'
            assert primary['byte_end'] == primary['byte_start'] + len(b'std::mem::transmute')
            assert source[primary['byte_end']:primary['byte_end']+1] == b'('
            assert row['expression']['byte_end'] > primary['byte_end']
            notes = [child['message'] for child in record['children']]
            assert len(notes) == 2 and notes[1] == 'target type: `[u8; 0]` (0 bits)'
            actual = bindings['actual_closure']
            identity = '{closure@' + bindings['closure_file'] + ':' + str(actual['line_start']) + ':' + str(actual['column_start']) + ': ' + str(actual['identity_end_line']) + ':' + str(actual['identity_end_column']) + '}'
            shape = 'MaybeUninit<' + identity + '>'
            if row['operation'] == 'alignment':
                shape = 'ClosureAlignmentProbeV1<' + shape + '>'
            assert notes[0].startswith('source type: `' + shape + '` (')
            closure_evidence.append({'record_index': index, 'operation': row['operation'],
                'observed_symbol_span': {key: primary[key] for key in coordinates},
                'frozen_full_expression_span': row['expression'], 'source_notes': notes,
                'raw_record_sha256': sha(raw_lines[index]),
                'finding': 'Exact anchored function symbol; differs from original required full expression span. No amended acceptance.'})
        elif record['level'] == 'warning':
            assert code in ('unused_imports', 'deprecated')
            warning_evidence.append({'record_index': index, 'code': code, 'message': record['message'],
                'raw_record_sha256': sha(raw_lines[index]), 'canonical_record_sha256': sha(canonical(record)),
                'source_spans': [item for item in spans_reviewed if item['record'] == index],
                'children': record['children'],
                'finding': 'Unexpected under original oracle; exact source-bound classification is a separate proposed amendment.'})
        else:
            summaries.append({'record_index': index, 'level': record['level'], 'message': record['message'],
                              'spans': record['spans'], 'children': record['children'],
                              'raw_record_sha256': sha(raw_lines[index])})
    assert len(named_seen) == 56 and named_seen == {row['id'] for row in bindings['named_queries']}
    assert counts == {'warning:unused_imports': 2, 'warning:deprecated': 1, 'error:E0308': 56, 'error:E0512': 2, 'error:None': 1, 'failure-note:None': 2}
    assert len(closure_evidence) == 2 and {row['operation'] for row in closure_evidence} == {'size', 'alignment'}
    assert len(warning_evidence) == len(summaries) == 3
    assert summaries[0]['message'] == 'aborting due to 58 previous errors; 3 warnings emitted'
    assert all(row['spans'] == [] and row['children'] == [] for row in summaries)
    report = {
        'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
        'status': 'ORIGINAL_FROZEN_CONTRACT_REFUSED_ACTUAL_RAW_OFFLINE_AMENDMENT_ONLY_RECOMMENDED',
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))],
        'python': sys.version, 'script_sha256': sha(Path(__file__).read_bytes()),
        'elapsed_seconds': time.monotonic() - started,
        'frozen_parser_sha256': sha(parser_path.read_bytes()), 'full_raw_parser_calls': 1,
        'frozen_parser_result': refusal, 'original_oracle_accepted': False,
        'producer_accepted_diagnostic_observation': False,
        'saved_command_members': [{'path': name, **hashed(COMMAND / name)} for name in names],
        'saved_stderr': hashed(COMMAND / 'stderr'), 'saved_stdout': hashed(COMMAND / 'stdout'),
        'saved_receipt': hashed(COMMAND / 'receipt.json'),
        'root_release_sha256': receipt['root_release_sha256'], 'plan_sha256': receipt['plan_sha256'],
        'source146_tree': plan['original_source']['tree_sha256'],
        'diagnostic146_tree': plan['diagnostic_source']['tree_sha256'],
        'preparation173_v2_16_v3_17_and_source_toolchain_members_unchanged': True,
        'toolchain_members_verified': len(tools['members']),
        'exact_command_environment_preserved': True,
        'compiler_execution_scope': {'previous_root_invocations': 1, 'new_reviewer_invocations': 0,
            'exit_code': receipt['compiler_exit_code'], 'elapsed_seconds': receipt['elapsed_seconds_including_cleanup_posthashes'],
            'pid': owned['pid'], 'ownership_receipt': receipt['ownership'], 'fresh_process_queries': 0,
            'build_cleanup_receipt': receipt['build_cleanup'], 'build_absence_verified': True},
        'raw_diagnostic_counts': counts, 'all_saved_spans_source_geometry_verified': len(spans_reviewed),
        'named_query_bindings_verified_without_accepting_values': 56,
        'warning_evidence': warning_evidence, 'closure_span_evidence': closure_evidence, 'summaries': summaries,
        'minimum_separate_post_observation_amendment': {
            'input_scope': 'Only these complete saved raw bytes, frozen V3 plan/source/toolchain and terminal command evidence. No compiler rerun or source change.',
            'warnings': 'Exactly these three warning records, exact cardinality/code/message/source tokens/coordinates/excerpts/children/suggestions. No generic warning allowance; preserve their original refusal.',
            'closure_spans': 'Exactly the two 19-byte std::mem::transmute function symbols at each frozen full-expression start, followed by opening parenthesis; pin all coordinates and excerpts. Retain complete expression/actual closure type/zero target identities and all other source checks. No arbitrary contained-span acceptance.',
            'terminal_summary': 'Exactly one abort summary for 58 errors and 3 warnings, plus exactly the two frozen failure notes. Reject count/message or span/child variation.',
            'adverse_controls': ['omitted/duplicate/extra warning', 'wrong warning code/message/level/source/coordinates/excerpt/child/suggestion',
                'unknown or fourth warning', 'shifted/shortened/alternate transmute symbol', 'wrong operation/closure/proxy/wrapper/target type',
                'duplicate/ambiguous closure diagnostic', 'wrong summary error/warning count or extra summary',
                'malformed/duplicate-key/nonfinite JSON', 'all retained original cardinality/source/shape/arithmetic refusals'],
            'approval': 'Separate versioned policy and implementation with independent review before any amended observation is accepted. This review neither relaxes the original oracle nor accepts layouts.'},
        'new_compiler_runtime_native_ui_capture_process_queries': 0,
        'new_producer_checker_or_controls_replay': False,
        'all_actual_layout_prices_backing_peak_funding_ownership_native_FieldLog_OTA_GA_unaccepted': True,
        'cleanup': 'Reviewer started no compiler/native/capture process and created no build artifact. Root receipt closes exact owned child/group and removes empty original build; no new cleanup owed.'}
    with (HERE / 'terminal-v3-review.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'full_raw_parser_calls', 'frozen_parser_result',
          'named_query_bindings_verified_without_accepting_values', 'all_saved_spans_source_geometry_verified',
          'new_compiler_runtime_native_ui_capture_process_queries')}))


if __name__ == '__main__':
    main()
