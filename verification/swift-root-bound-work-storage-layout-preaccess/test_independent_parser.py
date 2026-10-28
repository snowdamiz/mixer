#!/usr/bin/env python3
"""Synthetic finite diagnostics only; never compiler/product observations."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import independent_diagnostic_parser as P

HERE = Path(__file__).resolve().parent


def span(file, expected, label=None, expansion=None):
    text = P.BINDINGS['staged_two_sources'][file]
    lines = text.splitlines()
    snippets = []
    for line in range(expected['line_start'], expected['line_end'] + 1):
        actual = lines[line - 1]
        snippets.append({'text': actual,
                         'highlight_start': expected['column_start'] if line == expected['line_start'] else 1,
                         'highlight_end': expected['column_end'] if line == expected['line_end'] else len(actual) + 1})
    return {'file_name': file, **{key: expected[key] for key in ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end')},
            'is_primary': True, 'text': snippets, 'label': label, 'expansion': expansion}


def diagnostic(code, message, spans=None, children=None, level='error'):
    return {'$message_type': 'diagnostic', 'message': message, 'level': level,
            'code': {'code': code, 'explanation': None} if code else None,
            'spans': spans or [], 'children': children or [], 'rendered': None}


def synthetic():
    records = []
    for row in P.BINDINGS['named_queries']:
        value = ((row['id'] // 2) + 1) * 8 if row['operation'] == 'size' else 8
        expansion = {'macro_decl_name': 'pair!',
                     'span': span(row['file'], row['invocation']),
                     'def_site_span': span(row['file'], row['macro_definition'])}
        primary = span(row['file'], row['query_rhs'],
                       'expected an array with a size of 0, found one with a size of ' + str(value), expansion)
        records.append(diagnostic('E0308', 'mismatched types', [primary]))
    for row in P.BINDINGS['closure_queries']:
        source_type = 'MaybeUninit<' + P.closure_spelling() + '>'
        bits = 24 * 8
        if row['operation'] == 'alignment':
            source_type = 'ClosureAlignmentProbeV1<' + source_type + '>'
            bits = 32 * 8
        notes = [{'message': 'source type: `' + source_type + '` (' + str(bits) + ' bits)', 'level': 'note', 'spans': [], 'children': []},
                 {'message': 'target type: `[u8; 0]` (0 bits)', 'level': 'note', 'spans': [], 'children': []}]
        records.append(diagnostic('E0512', 'cannot transmute between types of different sizes, or dependently-sized types',
                                  [span(P.BINDINGS['closure_file'], row['expression'])], notes))
    records.extend([
        diagnostic(None, 'aborting due to 58 previous errors'),
        diagnostic(None, 'Some errors have detailed explanations: E0308, E0512.', level='failure-note'),
        diagnostic(None, 'For more information about an error, try `rustc --explain E0308`.', level='failure-note')])
    return records


def encode(records):
    return ''.join(json.dumps(row, sort_keys=True) + '\n' for row in records).encode()


def main():
    original = synthetic()
    result = P.parse_diagnostics(encode(original))
    assert result['primary_E0308'] == 56 and result['primary_E0512'] == 2
    assert result['actual_closure'] == {'size': 24, 'align': 8, 'source_bits': 192, 'wrapper_bits': 256}
    controls = []

    def reject(label, mutate=None, **overrides):
        rows = copy.deepcopy(original)
        if mutate:
            mutate(rows)
        try:
            P.parse_diagnostics(overrides.pop('stderr', encode(rows)), **overrides)
        except P.Refusal as error:
            controls.append({'name': label, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('accepted adverse diagnostic: ' + label)

    reject('missing-named-diagnostic', lambda rows: rows.pop(0))
    reject('duplicate-named-diagnostic', lambda rows: rows.append(copy.deepcopy(rows[0])))
    reject('missing-actual-closure-wrapper', lambda rows: rows.pop(57))
    reject('duplicate-actual-closure-size', lambda rows: rows.append(copy.deepcopy(rows[56])))
    reject('unexpected-primary-code', lambda rows: rows[0]['code'].__setitem__('code', 'E0999'))
    reject('unexpected-warning', lambda rows: rows.append(diagnostic(None, 'unused variable', level='warning')))
    reject('ambiguous-primary-spans', lambda rows: rows[0]['spans'].append(copy.deepcopy(rows[0]['spans'][0])))
    reject('wrong-pair-invocation', lambda rows: rows[0]['spans'][0]['expansion'].__setitem__('span', copy.deepcopy(rows[2]['spans'][0]['expansion']['span'])))
    reject('wrong-size-align-primary', lambda rows: rows[0]['spans'].__setitem__(0, copy.deepcopy(rows[1]['spans'][0])))
    reject('wrong-source-file', lambda rows: rows[0]['spans'][0].__setitem__('file_name', '/different/retained_profile_loader_v1.rs'))
    reject('wrong-source-byte-boundary', lambda rows: rows[0]['spans'][0].__setitem__('byte_start', rows[0]['spans'][0]['byte_start'] + 1))
    reject('wrong-source-excerpt', lambda rows: rows[0]['spans'][0]['text'][0].__setitem__('text', 'proxy source'))
    reject('missing-pair-expansion', lambda rows: rows[0]['spans'][0].__setitem__('expansion', None))
    reject('nonconcrete-named-array', lambda rows: rows[0]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of N'))
    reject('zero-named-size', lambda rows: rows[0]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 0'))
    reject('nonpower2-named-align', lambda rows: rows[1]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 3'))
    reject('wrong-closure-identity', lambda rows: rows[56]['children'][0].__setitem__('message', rows[56]['children'][0]['message'].replace(P.closure_spelling(), '{closure@/different:1:1: 1:3}')))
    reject('capture-proxy-instead-of-actual-closure', lambda rows: rows[56]['children'][0].__setitem__('message', 'source type: `MaybeUninit<CaptureProxyV1>` (192 bits)'))
    reject('dependent-closure-bits', lambda rows: rows[56]['children'][0].__setitem__('message', rows[56]['children'][0]['message'].replace('192 bits', 'dependently-sized')))
    reject('wrapper-with-different-closure', lambda rows: rows[57]['children'][0].__setitem__('message', rows[57]['children'][0]['message'].replace(P.closure_spelling(), '{closure@/different:1:1: 1:3}')))
    reject('wrapper-not-leading-byte-probe', lambda rows: rows[57]['children'][0].__setitem__('message', rows[57]['children'][0]['message'].replace('ClosureAlignmentProbeV1', 'CaptureSum')))
    reject('ambiguous-closure-source-notes', lambda rows: rows[56]['children'].append(copy.deepcopy(rows[56]['children'][0])))
    reject('nonzero-closure-target', lambda rows: rows[56]['children'][1].__setitem__('message', 'target type: `[u8; 1]` (8 bits)'))
    reject('missing-terminal-summary', lambda rows: rows.pop(58))
    reject('malformed-json-stream', stderr=b'not-json\n')
    reject('duplicate-json-key', stderr=b'{"$message_type":"diagnostic","$message_type":"artifact"}\n')
    reject('nonempty-stdout', stdout=b'unexpected\n')
    reject('successful-compiler-exit', exit_code=0)
    for source, wrapper in [(0, 8), (192, 192), (192, 184), (192, 216), (192, 193), (200, 264)]:
        try:
            P.concrete_alignment(source, wrapper)
        except P.Refusal as error:
            controls.append({'name': 'invalid-S-P-' + str(source) + '-' + str(wrapper), 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('accepted invalid S/P')
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'status': 'PASS_SYNTHETIC_PREACCESS_DIAGNOSTIC_CONTROLS_ONLY',
              'command': [sys.executable, '-B', str(Path(__file__).relative_to(HERE.parents[1]))],
              'python': sys.version, 'positive_synthetic_streams': 1, 'adverse_controls': controls,
              'adverse_controls_passed': len(controls), 'compiler_invocations': 0,
              'actual_product_sizes_observed': False, 'new_producer_packet_accessed': False,
              'strategy_qualified': False, 'layouts_prices_backing_peak_funding_ownership_GA_accepted': False,
              'source_files': [{'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                               for path in [Path(__file__), HERE / 'independent_diagnostic_parser.py', HERE / 'preaccess-oracle.json', HERE / 'diagnostic-bindings.json', HERE / 'preaccess-oracle-correction.json', HERE / 'diagnostic-bindings-corrected.json']]}
    with (HERE / 'synthetic-parser-controls.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'adverse_controls_passed': len(controls),
                      'compiler_invocations': 0, 'strategy_qualified': False}))


if __name__ == '__main__':
    main()
