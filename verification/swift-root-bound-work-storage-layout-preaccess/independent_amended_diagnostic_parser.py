#!/usr/bin/env python3
"""Independent retrospective saved-output oracle; no producer imports or writes.

Actual saved-raw invocation is intentionally left to root after separate review.
Synthetic mode rejects the actual saved bytes to prevent an accidental early run.
"""
import hashlib
import json
from pathlib import Path
import re

import independent_diagnostic_parser as ORIGINAL

HERE = Path(__file__).resolve().parent
POLICY = json.loads((HERE / 'amendment-independent-policy.json').read_bytes())
need = ORIGINAL.need
Refusal = ORIGINAL.Refusal


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def spans(value):
    if isinstance(value, list):
        for child in value:
            yield from spans(child)
    elif isinstance(value, dict):
        if all(key in value for key in ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end', 'file_name')):
            yield value
        for child in value.values():
            yield from spans(child)


def closure_observation(record):
    need(record.get('message') == 'cannot transmute between types of different sizes, or dependently-sized types', 'unexpected-E0512-message')
    primary = ORIGINAL.primary(record)
    need(primary.get('expansion') is None, 'unexpected-closure-macro-expansion')
    matches = [row for row in POLICY['closure_function_spans']
               if primary['file_name'] == row['file'] and ORIGINAL.same_range(primary, row['symbol_span'])]
    need(len(matches) == 1, 'unbound-exact-transmute-function-symbol')
    row = matches[0]
    source = ORIGINAL.BINDINGS['staged_two_sources'][row['file']].encode()
    start, end = primary['byte_start'], primary['byte_end']
    need(source[start:end] == b'std::mem::transmute' and end - start == 19 and source[end:end + 1] == b'(', 'transmute-symbol-source-anchor')
    full = row['complete_expression_span']
    need(start == full['byte_start'] and end < full['byte_end'], 'symbol-not-anchored-at-complete-query')
    need(hashlib.sha256(source[full['byte_start']:full['byte_end']]).hexdigest() == row['complete_expression_sha256'], 'complete-query-source-changed')
    token = POLICY['actual_closure_token']
    need(source[token['byte_start']:token['byte_end']] == b'||', 'actual-closure-pipe-source-changed')
    children = record.get('children')
    need(isinstance(children, list) and len(children) == 2, 'closure-type-note-cardinality')
    source_notes = [child for child in children if child.get('message', '').startswith('source type:')]
    target_notes = [child for child in children if child.get('message', '').startswith('target type:')]
    need(len(source_notes) == len(target_notes) == 1, 'closure-type-note-cardinality')
    source_note, target_note = source_notes[0], target_notes[0]
    need(source_note.get('level') == target_note.get('level') == 'note', 'closure-type-not-note')
    need(source_note.get('spans') == target_note.get('spans') == [] and source_note.get('children') == target_note.get('children') == [], 'unexpected-closure-note-nesting')
    need(target_note['message'] == 'target type: `[u8; 0]` (0 bits)', 'nonzero-or-unexpected-closure-target')
    match = re.fullmatch(r'source type: `([^`]+)` \(([0-9]+) bits\)', source_note['message'])
    need(match is not None, 'nonconcrete-source-size-note')
    actual_type, bits = match[1], int(match[2])
    identity = POLICY['actual_closure_pipe_identity']
    maybe = ['MaybeUninit<' + identity + '>', 'std::mem::MaybeUninit<' + identity + '>', 'core::mem::MaybeUninit<' + identity + '>']
    allowed = maybe if row['operation'] == 'size' else ['ClosureAlignmentProbeV1<' + value + '>' for value in maybe]
    need(actual_type in allowed, 'wrong-actual-closure-or-proxy-shape')
    need(bits > 0 and bits % 8 == 0, 'nonpositive-or-nonbyte-closure-size')
    return row['operation'], bits


def parse_amended(stderr, stdout=b'', exit_code=1, *, mode='synthetic'):
    need(mode in ('synthetic', 'saved-raw-root-released'), 'unknown-amendment-mode')
    need(exit_code == 1, 'unexpected-compiler-exit')
    need(stdout == b'', 'unexpected-compiler-stdout')
    need(type(stderr) is bytes and 0 < len(stderr) <= 2097152, 'stderr-bound')
    digest = hashlib.sha256(stderr).hexdigest()
    if mode == 'synthetic':
        need(digest != POLICY['saved_stderr']['sha256'], 'actual-saved-raw-awaits-root-coordination')
    else:
        need(len(stderr) == POLICY['saved_stderr']['bytes'] and digest == POLICY['saved_stderr']['sha256'], 'saved-raw-byte-pin')
    try:
        records = [json.loads(line, object_pairs_hook=ORIGINAL.no_duplicate_keys,
                    parse_constant=lambda value: (_ for _ in ()).throw(Refusal('nonfinite-JSON-constant')))
                   for line in stderr.decode('utf-8').splitlines()]
    except (UnicodeError, json.JSONDecodeError) as error:
        raise Refusal('malformed-JSON-diagnostic-stream') from error
    need(len(records) == POLICY['required_records'], 'total-diagnostic-cardinality')
    geometry_count = 0
    named, closure, warnings, summaries, notes = {}, {}, set(), [], set()
    expected_warnings = {row['record_line']: row for row in POLICY['whole_exact_warnings']}
    for line, record in enumerate(records, 1):
        need(isinstance(record, dict) and record.get('$message_type') == 'diagnostic', 'unexpected-JSON-message-type')
        for span in spans(record):
            ORIGINAL.validate_span(span)
            geometry_count += 1
        level, code = record.get('level'), record.get('code')
        if level == 'warning':
            expected = expected_warnings.get(line)
            need(expected is not None and line not in warnings, 'unexpected-or-duplicate-warning-line')
            need(canonical(record) == canonical(expected['exact_record']), 'warning-not-whole-exact-record')
            warnings.add(line)
        elif level == 'error' and isinstance(code, dict) and code.get('code') == 'E0308':
            row, value = ORIGINAL.named_observation(record)
            need(record.get('children') == [], 'unexpected-named-child-diagnostic')
            need(row['id'] not in named, 'duplicate-named-type-operation')
            named[row['id']] = value
        elif level == 'error' and isinstance(code, dict) and code.get('code') == 'E0512':
            operation, bits = closure_observation(record)
            need(operation not in closure, 'duplicate-closure-operation')
            closure[operation] = bits
        elif level == 'error' and code is None and record.get('message') == POLICY['required_summary']:
            need(record.get('spans') == [] and record.get('children') == [], 'unexpected-summary-content')
            summaries.append(record)
        elif level == 'failure-note' and code is None and record.get('message') in POLICY['required_failure_notes']:
            message = record['message']
            need(message not in notes and record.get('spans') == [] and record.get('children') == [], 'unexpected-failure-note-content')
            notes.add(message)
        else:
            raise Refusal('unexpected-top-level-diagnostic')
    need(warnings == set(expected_warnings), 'whole-warning-cardinality')
    need(geometry_count == POLICY['required_source_geometries'], 'source-geometry-cardinality')
    need(len(named) == 56 and set(named) == {row['id'] for row in ORIGINAL.BINDINGS['named_queries']}, 'named-diagnostic-cardinality')
    need(set(closure) == {'size', 'alignment'} and len(summaries) == 1, 'closure-or-summary-cardinality')
    need(notes == set(POLICY['required_failure_notes']), 'failure-note-cardinality')
    layouts = []
    for index in range(0, 56, 2):
        row = ORIGINAL.BINDINGS['named_queries'][index]
        size, align = named[index], named[index + 1]
        need(align & (align - 1) == 0 and size % align == 0, 'invalid-named-layout-pair')
        layouts.append({'type': row['type'], 'size': size, 'align': align})
    return {'schema': 1, 'status': 'RETROSPECTIVE_AMENDED_FINITE_OBSERVATIONS_PENDING_ROOT_ACCEPTANCE',
            'mode': mode, 'original_oracle_accepted': False,
            'source146_tree': POLICY['source146_tree'], 'diagnostic146_tree': POLICY['diagnostic146_tree'],
            'warning_count': len(warnings), 'source_geometries_verified': geometry_count,
            'named_layouts': layouts, 'actual_closure': ORIGINAL.concrete_alignment(closure['size'], closure['alignment']),
            'amended_policy_sha256': hashlib.sha256((HERE / 'amendment-independent-policy.json').read_bytes()).hexdigest(),
            'compiler_metadata_runtime_prices_backing_peaks_funding_ownership_GA_accepted': False}
