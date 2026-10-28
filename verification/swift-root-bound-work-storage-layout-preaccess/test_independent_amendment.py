#!/usr/bin/env python3
"""Fresh independent synthetic-only controls before producer-amendment access."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import independent_amended_diagnostic_parser as P
import test_independent_parser as FIXTURE

HERE = Path(__file__).resolve().parent


def synthetic():
    rows = FIXTURE.synthetic()
    # Two source-bound spans per E0308, each with macro expansion/definition:
    # 56*6 + eight exact warning spans + two closure symbols = 346 geometries.
    for row in rows[:56]:
        secondary = copy.deepcopy(row['spans'][0])
        secondary['is_primary'] = False
        secondary['label'] = 'synthetic secondary exact source geometry'
        row['spans'].append(secondary)
    for offset, query in enumerate(P.POLICY['closure_function_spans']):
        rows[56 + offset]['spans'] = [FIXTURE.span(query['file'], query['symbol_span'])]
    rows[58]['message'] = P.POLICY['required_summary']
    result = []
    warnings = {row['record_line'] - 1: copy.deepcopy(row['exact_record']) for row in P.POLICY['whole_exact_warnings']}
    source = iter(rows)
    for index in range(64):
        result.append(warnings[index] if index in warnings else next(source))
    return result


def encode(rows):
    return ''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows).encode()


def symbol_span(start, end):
    file = P.POLICY['closure_function_spans'][0]['file']
    raw = P.ORIGINAL.BINDINGS['staged_two_sources'][file].encode()
    before, selected = raw[:start].decode(), raw[start:end].decode()
    loc = {'byte_start': start, 'byte_end': end, 'line_start': before.count('\n') + 1,
           'line_end': before.count('\n') + selected.count('\n') + 1,
           'column_start': len(before.rsplit('\n', 1)[-1]) + 1,
           'column_end': len((before + selected).rsplit('\n', 1)[-1]) + 1}
    return FIXTURE.span(file, loc)


def main():
    original = synthetic()
    raw = encode(original)
    positive = P.parse_amended(raw)
    assert positive['mode'] == 'synthetic' and positive['original_oracle_accepted'] is False
    assert positive['warning_count'] == 3 and positive['source_geometries_verified'] == 346
    assert len(positive['named_layouts']) == 28
    assert positive['actual_closure'] == {'size': 24, 'align': 8, 'source_bits': 192, 'wrapper_bits': 256}
    controls = []
    def reject(label, mutate=None, **overrides):
        rows = copy.deepcopy(original)
        if mutate:
            mutate(rows)
        stream = overrides.pop('stderr', encode(rows))
        try:
            P.parse_amended(stream, **overrides)
        except P.Refusal as error:
            controls.append({'name': label, 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('adverse synthetic stream accepted: ' + label)
    reject('missing-whole-warning', lambda rows: rows.pop(0))
    reject('duplicate-whole-warning-replaces-named', lambda rows: rows.__setitem__(2, copy.deepcopy(rows[0])))
    reject('fourth-warning', lambda rows: rows.append(copy.deepcopy(rows[0])))
    def swap_warnings(rows):
        rows[0], rows[1] = rows[1], rows[0]
    reject('wrong-warning-order', swap_warnings)
    reject('warning-wrong-code', lambda rows: rows[0]['code'].__setitem__('code', 'unknown_lint'))
    reject('warning-wrong-level', lambda rows: rows[0].__setitem__('level', 'note'))
    reject('warning-message-change', lambda rows: rows[0].__setitem__('message', 'unused import'))
    reject('warning-source-change', lambda rows: rows[0]['spans'][0].__setitem__('file_name', '/unbound/source.rs'))
    reject('warning-coordinate-change', lambda rows: rows[0]['spans'][0].__setitem__('byte_start', 44161))
    reject('warning-excerpt-change', lambda rows: rows[0]['spans'][0]['text'][0].__setitem__('text', 'different source'))
    reject('warning-highlight-change', lambda rows: rows[0]['spans'][0]['text'][0].__setitem__('highlight_end', 78))
    reject('warning-note-change', lambda rows: rows[0]['children'][0].__setitem__('message', 'other lint note'))
    reject('warning-help-suggestion-change', lambda rows: rows[14]['children'][1]['spans'][0].__setitem__('suggested_replacement', 'fetch_add'))
    reject('warning-help-applicability-change', lambda rows: rows[14]['children'][1]['spans'][0].__setitem__('suggestion_applicability', 'MaybeIncorrect'))
    reject('warning-rendering-change', lambda rows: rows[0].__setitem__('rendered', 'warning altered'))
    reject('warning-nullable-field-change', lambda rows: rows[0]['code'].__setitem__('explanation', ''))
    reject('warning-extra-field', lambda rows: rows[0].__setitem__('extra', None))
    reject('warning-child-omitted', lambda rows: rows[0]['children'].pop())
    reject('warning-child-extra', lambda rows: rows[0]['children'].append(copy.deepcopy(rows[0]['children'][0])))
    reject('warning-type-coercion', lambda rows: rows[0]['spans'][0].__setitem__('line_start', 703.0))
    reject('missing-named-query', lambda rows: rows.pop(2))
    reject('duplicate-named-query', lambda rows: rows.__setitem__(3, copy.deepcopy(rows[2])))
    reject('unexpected-error-code', lambda rows: rows[2]['code'].__setitem__('code', 'E0999'))
    reject('named-ambiguous-primary', lambda rows: rows[2]['spans'][1].__setitem__('is_primary', True))
    reject('named-source-byte-change', lambda rows: rows[2]['spans'][0].__setitem__('byte_end', rows[2]['spans'][0]['byte_end'] - 1))
    reject('named-secondary-source-change', lambda rows: rows[2]['spans'][1]['text'][0].__setitem__('text', 'wrong secondary source'))
    reject('named-geometry-omitted', lambda rows: rows[2]['spans'].pop())
    reject('named-geometry-extra', lambda rows: rows[2]['spans'].append(copy.deepcopy(rows[2]['spans'][1])))
    reject('named-wrong-macro', lambda rows: rows[2]['spans'][0]['expansion'].__setitem__('macro_decl_name', 'proxy!'))
    reject('named-wrong-invocation', lambda rows: rows[2]['spans'][0]['expansion'].__setitem__('span', copy.deepcopy(rows[4]['spans'][0]['expansion']['span'])))
    reject('named-macro-definition-change', lambda rows: rows[2]['spans'][0]['expansion']['def_site_span'].__setitem__('line_end', 1))
    reject('named-child-extra', lambda rows: rows[2]['children'].append({'message': 'unqualified note', 'level': 'note', 'spans': [], 'children': []}))
    reject('named-nonconcrete-label', lambda rows: rows[2]['spans'][0].__setitem__('label', 'expected size N'))
    reject('named-zero-size', lambda rows: rows[2]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 0'))
    reject('named-usize-overflow', lambda rows: rows[2]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 18446744073709551616'))
    reject('named-align-not-power-two', lambda rows: rows[3]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 3'))
    reject('named-size-not-aligned', lambda rows: rows[2]['spans'][0].__setitem__('label', 'expected an array with a size of 0, found one with a size of 9'))
    first = P.POLICY['closure_function_spans'][0]
    full = first['complete_expression_span']
    symbol = first['symbol_span']
    reject('closure-full-expression-span-refused', lambda rows: rows[59]['spans'].__setitem__(0, FIXTURE.span(first['file'], full)))
    reject('closure-shifted-symbol', lambda rows: rows[59]['spans'].__setitem__(0, symbol_span(symbol['byte_start'] + 1, symbol['byte_end'] + 1)))
    reject('closure-shortened-symbol', lambda rows: rows[59]['spans'].__setitem__(0, symbol_span(symbol['byte_start'], symbol['byte_end'] - 1)))
    reject('closure-interior-argument-span', lambda rows: rows[59]['spans'].__setitem__(0, symbol_span(symbol['byte_end'] + 1, symbol['byte_end'] + 5)))
    reject('closure-other-query-symbol', lambda rows: rows[59]['spans'].__setitem__(0, copy.deepcopy(rows[60]['spans'][0])))
    reject('closure-ambiguous-primary', lambda rows: rows[59]['spans'].append(copy.deepcopy(rows[59]['spans'][0])))
    reject('closure-duplicate-size-query', lambda rows: rows.__setitem__(60, copy.deepcopy(rows[59])))
    reject('closure-wrong-actual-identity', lambda rows: rows[59]['children'][0].__setitem__('message', rows[59]['children'][0]['message'].replace(P.POLICY['actual_closure_pipe_identity'], '{closure@/other:1:1: 1:3}')))
    reject('closure-capture-proxy', lambda rows: rows[59]['children'][0].__setitem__('message', 'source type: `MaybeUninit<CaptureProxy>` (192 bits)'))
    reject('closure-dependent-bits', lambda rows: rows[59]['children'][0].__setitem__('message', rows[59]['children'][0]['message'].replace('192 bits', 'size can vary')))
    reject('closure-wrong-leading-byte-wrapper', lambda rows: rows[60]['children'][0].__setitem__('message', rows[60]['children'][0]['message'].replace('ClosureAlignmentProbeV1', 'CaptureFieldSum')))
    reject('closure-wrapper-other-identity', lambda rows: rows[60]['children'][0].__setitem__('message', rows[60]['children'][0]['message'].replace(P.POLICY['actual_closure_pipe_identity'], '{closure@/other:1:1: 1:3}')))
    reject('closure-nonzero-target', lambda rows: rows[59]['children'][1].__setitem__('message', 'target type: `[u8; 1]` (8 bits)'))
    reject('closure-extra-note', lambda rows: rows[59]['children'].append(copy.deepcopy(rows[59]['children'][0])))
    reject('closure-missing-note', lambda rows: rows[59]['children'].pop())
    reject('closure-note-nesting', lambda rows: rows[59]['children'][0]['children'].append({'message': 'extra', 'level': 'note', 'spans': [], 'children': []}))
    reject('closure-note-wrong-level', lambda rows: rows[59]['children'][0].__setitem__('level', 'help'))
    reject('summary-old-warning-free-message', lambda rows: rows[61].__setitem__('message', 'aborting due to 58 previous errors'))
    reject('summary-wrong-error-count', lambda rows: rows[61].__setitem__('message', 'aborting due to 57 previous errors; 3 warnings emitted'))
    reject('summary-wrong-warning-count', lambda rows: rows[61].__setitem__('message', 'aborting due to 58 previous errors; 2 warnings emitted'))
    reject('summary-missing', lambda rows: rows.pop(61))
    reject('summary-duplicate', lambda rows: rows.__setitem__(62, copy.deepcopy(rows[61])))
    reject('summary-unexpected-child', lambda rows: rows[61]['children'].append({'message': 'extra', 'level': 'note', 'spans': [], 'children': []}))
    reject('failure-note-missing', lambda rows: rows.pop(62))
    reject('failure-note-duplicate', lambda rows: rows.__setitem__(63, copy.deepcopy(rows[62])))
    reject('failure-note-message-change', lambda rows: rows[63].__setitem__('message', 'another compiler note'))
    reject('malformed-json', stderr=b'not-json\n')
    reject('nonUTF8-json', stderr=b'\xff\n')
    reject('duplicate-top-level-key', stderr=raw.replace(b'"level": "error"', b'"level": "warning", "level": "error"', 1))
    reject('duplicate-nested-key', stderr=raw.replace(b'"code": "E0308"', b'"code": "E0999", "code": "E0308"', 1))
    reject('nonfinite-json-constant', stderr=raw.replace(b'"explanation": null', b'"explanation": NaN', 1))
    reject('nonempty-stdout', stdout=b'unexpected\n')
    reject('successful-compiler-exit', exit_code=0)
    reject('unknown-mode', mode='unreviewed')
    reject('synthetic-bytes-not-saved-raw', mode='saved-raw-root-released')
    for source, wrapper in [(0, 8), (192, 192), (192, 184), (192, 216), (192, 193), (200, 264)]:
        try:
            P.ORIGINAL.concrete_alignment(source, wrapper)
        except P.Refusal as error:
            controls.append({'name': 'invalid-original-S-P-' + str(source) + '-' + str(wrapper), 'rejected': True, 'reason': str(error)})
        else:
            raise AssertionError('invalid original closure arithmetic accepted')
    report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
              'status': 'FROZEN_INDEPENDENT_AMENDMENT_SYNTHETIC_CONTROLS_PASS_BEFORE_PRODUCER_ACCESS',
              'command': [sys.executable, '-B', str(Path(__file__).relative_to(HERE.parents[1]))], 'python': sys.version,
              'positive_synthetic_streams': 1, 'positive_synthetic_source_geometries': 346,
              'positive_synthetic_stream_sha256': hashlib.sha256(raw).hexdigest(),
              'fixture_scope': 'Constructed E0308/E0512 geometry and arbitrary numbers plus exact fixed warning policy records; no actual saved raw parse.',
              'adverse_controls': controls, 'adverse_controls_passed': len(controls),
              'producer_amendment_accessed': False, 'actual_amended_saved_raw_parse_calls': 0,
              'compiler_runtime_version_native_ui_capture_process_queries': 0,
              'original_oracle_accepted': False, 'amended_actual_observation_accepted': False,
              'all_prices_backing_peak_funding_ownership_native_FieldLog_OTA_GA_pending': True,
              'source_files': [{'path': path.name, 'bytes': len(path.read_bytes()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                  for path in [Path(__file__), HERE / 'independent_amended_diagnostic_parser.py', HERE / 'amendment-independent-policy.json',
                               HERE / 'independent_diagnostic_parser.py', HERE / 'diagnostic-bindings-corrected.json']]}
    with (HERE / 'independent-amendment-synthetic-controls.json').open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'adverse_controls_passed', 'positive_synthetic_source_geometries',
          'producer_amendment_accessed', 'actual_amended_saved_raw_parse_calls')}))


if __name__ == '__main__':
    main()
