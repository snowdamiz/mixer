#!/usr/bin/env python3
"""Finite fail-closed JSON oracle; no subprocess, producer import or source writes.

This was authored from frozen preaccess bindings. Concrete compiler formatting
and emission remain unqualified until a separately released actual-output review.
"""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
BINDINGS = json.loads((HERE / 'diagnostic-bindings-corrected.json').read_bytes())


class Refusal(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def no_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value, 'duplicate-JSON-key')
        value[key] = item
    return value


def integer(value):
    return type(value) is int


def validate_span(span):
    need(isinstance(span, dict), 'span-not-object')
    file = span.get('file_name')
    need(file in BINDINGS['staged_two_sources'], 'span-source-not-exact-frozen-diagnostic-copy')
    text = BINDINGS['staged_two_sources'][file]
    raw = text.encode()
    start, end = span.get('byte_start'), span.get('byte_end')
    need(integer(start) and integer(end) and 0 <= start < end <= len(raw), 'invalid-span-byte-range')
    try:
        before, selected = raw[:start].decode(), raw[start:end].decode()
    except UnicodeError as error:
        raise Refusal('span-not-character-boundary') from error
    line_start = before.count('\n') + 1
    line_end = line_start + selected.count('\n')
    column_start = len(before.rsplit('\n', 1)[-1]) + 1
    column_end = len((before + selected).rsplit('\n', 1)[-1]) + 1
    for key, value in [('line_start', line_start), ('line_end', line_end),
                       ('column_start', column_start), ('column_end', column_end)]:
        need(type(span.get(key)) is int and span[key] == value, 'span-' + key + '-mismatch')
    lines = text.splitlines()
    snippets = span.get('text')
    need(isinstance(snippets, list) and len(snippets) == line_end - line_start + 1, 'span-excerpt-cardinality')
    for index, snippet in enumerate(snippets):
        source_line = lines[line_start + index - 1]
        need(snippet.get('text') == source_line, 'span-excerpt-source-mismatch')
        first, last = snippet.get('highlight_start'), snippet.get('highlight_end')
        need(integer(first) and integer(last) and 1 <= first <= last <= len(source_line) + 1,
             'span-highlight-range')
        if index == 0:
            need(first == column_start, 'span-highlight-start')
        if index == len(snippets) - 1:
            need(last == column_end, 'span-highlight-end')
    return selected


def same_range(span, expected):
    return all(span.get(key) == expected[key] for key in ('byte_start', 'byte_end', 'line_start', 'line_end', 'column_start', 'column_end'))


def primary(diagnostic):
    spans = diagnostic.get('spans')
    need(isinstance(spans, list), 'missing-spans')
    primaries = [span for span in spans if span.get('is_primary') is True]
    need(len(primaries) == 1, 'primary-span-cardinality')
    span = primaries[0]
    validate_span(span)
    return span


def concrete_alignment(source_bits, wrapper_bits):
    need(integer(source_bits) and integer(wrapper_bits), 'noninteger-bits')
    need(source_bits > 0 and wrapper_bits > 0, 'nonpositive-bits')
    need(source_bits % 8 == 0 and wrapper_bits % 8 == 0, 'nonbyte-bits')
    size = source_bits // 8
    align = (wrapper_bits - source_bits) // 8
    need(align > 0 and align & (align - 1) == 0, 'nonpositive-or-nonpower2-alignment')
    need(size % align == 0, 'size-not-alignment-multiple')
    need(size < 2**64 and align < 2**64, 'target-usize-overflow')
    return {'size': size, 'align': align, 'source_bits': source_bits, 'wrapper_bits': wrapper_bits}


def named_observation(diagnostic):
    need(diagnostic.get('message') == 'mismatched types', 'unexpected-E0308-message')
    span = primary(diagnostic)
    expansion = span.get('expansion')
    need(isinstance(expansion, dict) and expansion.get('macro_decl_name') == 'pair!', 'missing-exact-pair-expansion')
    invocation = expansion.get('span')
    validate_span(invocation)
    need(invocation.get('expansion') is None, 'unexpected-nested-pair-expansion')
    matches = [row for row in BINDINGS['named_queries']
               if row['file'] == span['file_name'] == invocation['file_name']
               and same_range(span, row['query_rhs']) and same_range(invocation, row['invocation'])]
    need(len(matches) == 1, 'unbound-or-ambiguous-type-operation-expansion')
    row = matches[0]
    definition = expansion.get('def_site_span')
    if definition is not None:
        validate_span(definition)
        declaration = row['macro_definition']
        need(definition['file_name'] == row['file'] and definition['line_start'] == declaration['line_start']
             and definition['byte_start'] <= declaration['byte_start'] and definition['byte_end'] >= declaration['byte_end'],
             'wrong-macro-definition')
    label = span.get('label')
    match = re.fullmatch(r'expected an array with a size of 0, found one with a size of ([0-9]+)', label or '')
    need(match is not None, 'nonconcrete-or-unexpected-named-array-label')
    value = int(match[1])
    need(0 < value < 2**64, 'invalid-target-layout-value')
    return row, value


def closure_spelling():
    row = BINDINGS['actual_closure']
    return '{closure@' + BINDINGS['closure_file'] + ':' + str(row['line_start']) + ':' + str(row['column_start']) + ': ' + str(row['identity_end_line']) + ':' + str(row['identity_end_column']) + '}'


def closure_observation(diagnostic):
    need(diagnostic.get('message') == 'cannot transmute between types of different sizes, or dependently-sized types',
         'unexpected-E0512-message')
    span = primary(diagnostic)
    need(span.get('expansion') is None, 'unexpected-closure-macro-expansion')
    matches = [row for row in BINDINGS['closure_queries'] if span['file_name'] == BINDINGS['closure_file'] and same_range(span, row['expression'])]
    need(len(matches) == 1, 'unbound-closure-transmute-expression')
    row = matches[0]
    children = diagnostic.get('children')
    need(isinstance(children, list), 'missing-closure-type-notes')
    source_notes = [child for child in children if child.get('message', '').startswith('source type:')]
    target_notes = [child for child in children if child.get('message', '').startswith('target type:')]
    need(len(source_notes) == len(target_notes) == 1, 'closure-type-note-cardinality')
    source, target = source_notes[0], target_notes[0]
    need(source.get('level') == target.get('level') == 'note', 'closure-type-not-note')
    need(target['message'] == 'target type: `[u8; 0]` (0 bits)', 'nonzero-or-unexpected-closure-target')
    match = re.fullmatch(r'source type: `([^`]+)` \(([0-9]+) bits\)', source['message'])
    need(match is not None, 'nonconcrete-source-size-note')
    actual_type, bits = match[1], int(match[2])
    # These finite spellings name the exact frozen actual closure. Arbitrary
    # suffix/path matching would allow an unrelated replacement shape.
    maybe = ['MaybeUninit<' + closure_spelling() + '>',
             'std::mem::MaybeUninit<' + closure_spelling() + '>',
             'core::mem::MaybeUninit<' + closure_spelling() + '>']
    expected = maybe if row['operation'] == 'size' else ['ClosureAlignmentProbeV1<' + item + '>' for item in maybe]
    need(actual_type in expected, 'wrong-actual-closure-or-proxy-shape')
    need(bits > 0 and bits % 8 == 0, 'nonpositive-or-nonbyte-closure-size')
    return row['operation'], bits


def parse_diagnostics(stderr, stdout=b'', exit_code=1):
    need(exit_code == 1, 'unexpected-compiler-exit')
    need(stdout == b'', 'unexpected-compiler-stdout')
    need(type(stderr) is bytes and 0 < len(stderr) <= 2097152, 'stderr-bound')
    try:
        text = stderr.decode('utf-8')
        diagnostics = [json.loads(line, object_pairs_hook=no_duplicate_keys) for line in text.splitlines()]
    except (UnicodeError, json.JSONDecodeError) as error:
        raise Refusal('malformed-JSON-diagnostic-stream') from error
    need(diagnostics, 'empty-diagnostic-stream')
    named, closure, summaries = {}, {}, []
    failure_notes = set()
    for diagnostic in diagnostics:
        need(isinstance(diagnostic, dict) and diagnostic.get('$message_type') == 'diagnostic', 'unexpected-JSON-message-type')
        level = diagnostic.get('level')
        code = diagnostic.get('code')
        if level == 'error' and isinstance(code, dict) and code.get('code') == 'E0308':
            row, value = named_observation(diagnostic)
            need(row['id'] not in named, 'duplicate-named-type-operation')
            named[row['id']] = value
        elif level == 'error' and isinstance(code, dict) and code.get('code') == 'E0512':
            operation, bits = closure_observation(diagnostic)
            need(operation not in closure, 'duplicate-closure-operation')
            closure[operation] = bits
        elif level == 'error' and code is None and diagnostic.get('message') == 'aborting due to 58 previous errors':
            need(diagnostic.get('spans') == [] and diagnostic.get('children') == [], 'unexpected-summary-content')
            summaries.append(diagnostic)
        elif level == 'failure-note' and code is None and diagnostic.get('message') in {
            'Some errors have detailed explanations: E0308, E0512.',
            'For more information about an error, try `rustc --explain E0308`.'}:
            message = diagnostic['message']
            need(message not in failure_notes and diagnostic.get('spans') == [] and diagnostic.get('children') == [], 'unexpected-failure-note-content')
            failure_notes.add(message)
        else:
            raise Refusal('unexpected-top-level-diagnostic')
    need(len(named) == 56 and set(named) == {row['id'] for row in BINDINGS['named_queries']}, 'named-diagnostic-cardinality')
    need(set(closure) == {'size', 'alignment'} and len(summaries) == 1, 'closure-or-summary-cardinality')
    layouts = []
    for index in range(0, 56, 2):
        row = BINDINGS['named_queries'][index]
        size, align = named[index], named[index + 1]
        need(align & (align - 1) == 0 and size % align == 0, 'invalid-named-layout-pair')
        layouts.append({'type': row['type'], 'size': size, 'align': align})
    return {'schema': 1, 'status': 'FINITE_DIAGNOSTIC_OBSERVATIONS_PENDING_ROOT_REVIEW',
            'original_source146_tree': BINDINGS['original_source146_tree'],
            'diagnostic_source146_tree': BINDINGS['diagnostic_source146_tree'],
            'primary_E0308': len(named), 'primary_E0512': len(closure),
            'named_layouts': layouts, 'actual_closure': concrete_alignment(closure['size'], closure['alignment']),
            'all_diagnostics_retained_by_caller_required': True,
            'compiler_metadata_or_runtime_qualified': False, 'prices_backing_peak_funding_ownership_GA_accepted': False}
