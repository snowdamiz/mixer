#!/usr/bin/env python3
"""Prepare independent retrospective policy before producer-amendment access.

No amended parsing of saved raw, producer import/replay, compiler or child.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WARNINGS = ROOT / 'verification/swift-root-bound-layout-warning-classification'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def verify(directory, name, digest, count, closure=False):
    assert sha((directory / name).read_bytes()) == digest
    seal = load(directory / name)
    assert len(seal['members']) == count
    if 'tree_sha256' in seal:
        assert sha(canonical(seal['members'])) == seal['tree_sha256']
    for row in seal['members']:
        path = directory / row['path']
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    if closure:
        assert not any(path.is_symlink() for path in directory.rglob('*'))
        assert sorted(path.relative_to(directory).as_posix() for path in directory.rglob('*') if path.is_file()) == sorted([row['path'] for row in seal['members']] + [name])


def main():
    verify(WARNINGS, 'seal.json', '39976085aa6fd3cebf5c12bb6376358c46b11223df8347b8fb70ef12c20be5ab', 9, True)
    verify(HERE, 'preaccess-seal.json', '001ec6fbfb69a6c784083615323df670c9d932ecace8fd598fc68447867d9d67', 22)
    verify(HERE, 'terminal-v3-review-seal.json', '4e42f67ff992fe7f3c9192b638ea9960eee4d3787bf5eeb40443113f5592760e', 5)
    warning = load(WARNINGS / 'warning-classification-proposal.json')
    bindings = load(HERE / 'diagnostic-bindings-corrected.json')
    terminal = load(HERE / 'terminal-v3-review.json')
    assert terminal['original_oracle_accepted'] is False
    assert warning['required_warning_count'] == 3 and warning['required_ordered_record_lines'] == [1, 2, 15]
    assert warning['stream']['sha256'] == terminal['saved_stderr']['sha256'] == '05c526210b4c07779c09c33f1944ffaa06d8012c57a57e3ad05f68ee34106635'
    assert warning['stream']['bytes'] == 292318
    coordinates = ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end')
    file = bindings['closure_file']
    source = bindings['staged_two_sources'][file].encode()
    closure = []
    for row in bindings['closure_queries']:
        expression = row['expression']
        start = expression['byte_start']
        assert source[start:start + 19] == b'std::mem::transmute'
        assert source[start + 19:start + 20] == b'('
        end = start + 19
        before = source[:start].decode()
        selected = source[start:end].decode()
        full = source[start:expression['byte_end']].decode()
        assert full.startswith(selected + '(') and full.endswith(')')
        span = {'byte_start': start, 'byte_end': end, 'line_start': before.count('\n') + 1,
                'line_end': before.count('\n') + 1, 'column_start': len(before.rsplit('\n', 1)[-1]) + 1,
                'column_end': len(before.rsplit('\n', 1)[-1]) + 20}
        assert all(span[key] == expression[key] for key in ('byte_start', 'line_start', 'column_start'))
        closure.append({'operation': row['operation'], 'file': file, 'function_symbol': 'std::mem::transmute',
                        'symbol_span': span, 'complete_expression_span': {key: expression[key] for key in coordinates},
                        'complete_expression_sha256': sha(full.encode()), 'complete_expression': full})
    actual = bindings['actual_closure']
    assert source[actual['byte_start']:actual['byte_start'] + 2] == b'||'
    identity = '{closure@' + file + ':' + str(actual['line_start']) + ':' + str(actual['column_start']) + ': ' + str(actual['identity_end_line']) + ':' + str(actual['identity_end_column']) + '}'
    record = {
        'schema': 1, 'status': 'FROZEN_INDEPENDENT_POST_OBSERVATION_POLICY_BEFORE_PRODUCER_AMENDMENT_ACCESS',
        'at': datetime.now(timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(Path(__file__).relative_to(ROOT))], 'python': sys.version,
        'policy_scope': 'Retrospective saved-raw-only explicit warning/function-symbol/summary amendment. Original oracle and original refusal remain immutable.',
        'original_oracle_sha256': sha((HERE / 'preaccess-oracle.json').read_bytes()),
        'frozen_original_parser_sha256': sha((HERE / 'independent_diagnostic_parser.py').read_bytes()),
        'corrected_bindings_sha256': sha((HERE / 'diagnostic-bindings-corrected.json').read_bytes()),
        'terminal_refusal_seal_sha256': sha((HERE / 'terminal-v3-review-seal.json').read_bytes()),
        'warning_classification_seal_sha256': sha((WARNINGS / 'seal.json').read_bytes()),
        'warning_classification_provenance_scope': 'Frozen source-classification evidence: original production-MIR and independent P01/P02 each have three baseline warnings; Debug/opt2 each six. No warning-free build claim.',
        'saved_stderr': terminal['saved_stderr'], 'saved_stdout': terminal['saved_stdout'],
        'saved_receipt': terminal['saved_receipt'], 'plan_sha256': terminal['plan_sha256'],
        'source146_tree': terminal['source146_tree'], 'diagnostic146_tree': terminal['diagnostic146_tree'],
        'required_records': 64, 'required_source_geometries': 346,
        'required_primary_codes': {'E0308': 56, 'E0512': 2}, 'required_named_bindings': 56,
        'whole_exact_warnings': warning['expected_warnings'],
        'warning_matching': 'Require whole canonical decoded object including all fields, nulls, rendered text, children and suggestions, exactly once at each pinned line. Independently validate every nested source geometry.',
        'closure_function_spans': closure, 'actual_closure_pipe_identity': identity,
        'actual_closure_token': {'file': file, 'byte_start': actual['byte_start'], 'byte_end': actual['byte_start'] + 2,
                                 'line': actual['line_start'], 'column_start': actual['column_start'], 'column_end': actual['identity_end_column']},
        'required_summary': 'aborting due to 58 previous errors; 3 warnings emitted',
        'required_failure_notes': ['Some errors have detailed explanations: E0308, E0512.',
                                   'For more information about an error, try `rustc --explain E0308`.'],
        'numeric_contract': ['All named values are positive target-usize integers; alignment is a power of two and divides size.',
            'Actual closure source/wrapper bits are positive byte multiples; A=(P-S)/8 is positive power of two; (S/8)%A==0; S/8 and A are target-usize values.',
            'Exact actual closure MaybeUninit and leading-u8 repr(C) wrapper identities; exact zero [u8; 0] target; no proxy or capture sums.'],
        'expected_refusals': ['changed raw pin in eventual saved mode', 'wrong exit or nonempty stdout',
            'malformed/nonUTF8/duplicate-key/nonfinite JSON', 'missing/duplicate/extra/wrong-order whole warning',
            'warning code/message/level/source/position/child/suggestion/rendering/nullable/extra field change',
            'any of 346 source geometries/excerpts/highlights differs', 'missing/duplicate/ambiguous/wrong named query or macro expansion',
            'full expression span instead of amended exact function span', 'arbitrary interior/shifted/shortened function span',
            'wrong closure identity/proxy/wrapper/target/notes', 'wrong summary error/warning count or duplicate/missing summary/failure note',
            'invalid original named or closure numeric constraints'],
        'producer_amendment_accessed': False, 'actual_amended_saved_raw_parse_calls': 0,
        'new_compiler_runtime_version_native_ui_capture_or_process_queries': 0,
        'original_oracle_accepted': False, 'amended_actual_observation_accepted': False,
        'all_price_backing_peak_funding_ownership_native_FieldLog_OTA_GA_pending': True}
    with (HERE / 'amendment-independent-policy.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': record['status'], 'warning_members_verified': 9,
                      'producer_amendment_accessed': False, 'actual_amended_saved_raw_parse_calls': 0}))


if __name__ == '__main__':
    main()
