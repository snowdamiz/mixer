"""Fail-closed parser for the frozen diagnostic scratch. No compiler/runtime calls."""
import json
import re
from pathlib import Path


class Rejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Rejected(reason)


def point(raw, offset):
    prefix = raw[:offset].decode('utf-8')
    return prefix.count('\n') + 1, len(prefix.rsplit('\n', 1)[-1]) + 1


def checked_span(span, sources):
    """Bind coordinates and every displayed line to frozen physical UTF-8 source."""
    name = span.get('file_name')
    require(name in sources, 'span outside frozen source146: ' + str(name))
    raw = sources[name]
    start, end = span.get('byte_start'), span.get('byte_end')
    require(type(start) is int and type(end) is int and 0 <= start <= end <= len(raw), 'invalid span byte range')
    require(point(raw, start) == (span.get('line_start'), span.get('column_start')), 'span start coordinate mismatch')
    require(point(raw, end) == (span.get('line_end'), span.get('column_end')), 'span end coordinate mismatch')
    lines = raw.decode('utf-8').splitlines()
    displayed = span.get('text')
    require(isinstance(displayed, list) and len(displayed) == span['line_end'] - span['line_start'] + 1, 'missing source lines')
    require([row.get('text') for row in displayed] == lines[span['line_start']-1:span['line_end']], 'displayed source differs from frozen scratch')
    expansion = span.get('expansion')
    if expansion is not None:
        require(isinstance(expansion, dict) and isinstance(expansion.get('span'), dict), 'invalid expansion')
        checked_span(expansion['span'], sources)
        if expansion.get('def_site_span') is not None:
            checked_span(expansion['def_site_span'], sources)
    return name, start, end


def source_map(plan, directory):
    return {str(directory / 'source/vm' / row['path']): (directory / 'source/vm' / row['path']).read_bytes()
            for row in plan['diagnostic_source']['members']}


def parse(raw, plan, sources):
    require(len(raw) <= plan['bounds']['maximum_stderr_bytes'], 'stderr cap exceeded')
    messages = []
    for line in raw.decode('utf-8', errors='strict').splitlines():
        require(bool(line), 'blank diagnostic line')
        obj = json.loads(line)
        require(isinstance(obj, dict) and obj.get('$message_type') == 'diagnostic', 'non-diagnostic JSON output')
        messages.append(obj)
    expected = plan['diagnostics']
    named = {}
    closure = {}
    summaries = []
    all_primary = []
    for obj in messages:
        code = (obj.get('code') or {}).get('code')
        level = obj.get('level')
        if code is None:
            require((level, obj.get('message')) in [tuple(x) for x in expected['allowed_summary_messages']], 'unexpected uncoded diagnostic')
            require(not obj.get('spans') and not obj.get('children'), 'summary has unexpected spans/children')
            key = (level, obj['message'])
            require(key not in summaries, 'duplicate summary')
            summaries.append(key)
            continue
        require(level == 'error' and code in ('E0308', 'E0512'), 'unexpected coded diagnostic: ' + str(code))
        primaries = [span for span in obj.get('spans', []) if span.get('is_primary')]
        require(len(primaries) == 1, 'missing/ambiguous primary span')
        for span in obj['spans']:
            checked_span(span, sources)
        primary = primaries[0]
        identity = checked_span(primary, sources)
        all_primary.append(code)
        if code == 'E0308':
            require(obj.get('message') == 'mismatched types', 'unexpected E0308 message')
            matches = []
            for query in expected['named_queries']:
                for kind in ('size', 'alignment'):
                    macro = query['macro_expressions'][kind]
                    if identity != (query['file'], macro['byte_start'], macro['byte_end']):
                        continue
                    expansion = primary.get('expansion')
                    if expansion is None or expansion.get('macro_decl_name') != 'pair!':
                        continue
                    call = expansion['span']
                    invoke = query['invocation']
                    if (call['file_name'], call['byte_start'], call['byte_end']) != (query['file'], invoke['byte_start'], invoke['byte_end']):
                        continue
                    require(call.get('expansion') is None, 'unexpected nested query expansion')
                    matches.append((query['index'], kind))
            require(len(matches) == 1, 'named diagnostic missing exact macro expression/invocation binding')
            key = matches[0]
            require(key not in named, 'duplicate named diagnostic')
            match = re.fullmatch(r'expected an array with a size of 0, found one with a size of ([0-9]+)', primary.get('label') or '')
            require(match is not None, 'non-concrete/ambiguous named array size')
            named[key] = int(match[1])
            for child in obj.get('children', []):
                require(child.get('code') is None and child.get('level') == 'help' and child.get('message') == 'consider specifying the actual array length'
                        and not child.get('children'), 'unexpected named child diagnostic')
                for span in child.get('spans', []): checked_span(span, sources)
        else:
            require(obj.get('message') == 'cannot transmute between types of different sizes, or dependently-sized types', 'unexpected E0512 message')
            require(primary.get('expansion') is None, 'actual closure query unexpectedly expanded')
            matches = [kind for kind, loc in expected['actual_closure']['queries'].items()
                       if identity[0] == expected['actual_closure']['file'] and loc['byte_start'] <= identity[1] < identity[2] <= loc['byte_end']]
            require(len(matches) == 1, 'closure diagnostic not inside exact transmute source expression')
            kind = matches[0]
            require(kind not in closure, 'duplicate actual closure diagnostic')
            children = obj.get('children')
            require(isinstance(children, list) and len(children) == 2, 'closure source/target notes missing or ambiguous')
            notes = []
            for child in children:
                require(child.get('level') == 'note' and child.get('code') is None and not child.get('spans') and not child.get('children'), 'unexpected closure note shape')
                notes.append(child.get('message'))
            source_notes = [note for note in notes if isinstance(note, str) and note.startswith('source type: ')]
            target_notes = [note for note in notes if note == 'target type: `[u8; 0]` (0 bits)']
            require(len(source_notes) == len(target_notes) == 1, 'closure source/target type mismatch')
            match = re.fullmatch(r'source type: `(.+)` \(([0-9]+) bits\)', source_notes[0])
            require(match is not None, 'closure source is missing concrete bit size')
            shape, bits = match[1], int(match[2])
            wrapper = 'ClosureAlignmentProbeV1<' if kind == 'alignment_wrapper' else ''
            require(shape.startswith(wrapper), 'closure source type wrapper mismatch')
            if wrapper:
                require(shape.endswith('>'), 'closure wrapper missing terminator')
                shape = shape[len(wrapper):-1]
            require(shape.startswith('MaybeUninit<') or shape.startswith('std::mem::MaybeUninit<'), 'not actual MaybeUninit closure shape')
            inner = shape.split('MaybeUninit<', 1)[1]
            require(inner.endswith('>'), 'invalid MaybeUninit source type')
            identity_text = inner[:-1]
            loc = expected['actual_closure']['identity_span']
            exact_identity = '{closure@' + expected['actual_closure']['file'] + ':' + str(loc['line_start']) + ':' + str(loc['column_start']) + ': ' + str(loc['line_end']) + ':' + str(loc['column_end']) + '}'
            require(identity_text == exact_identity, 'wrong actual closure exact pipe-span source identity')
            closure[kind] = {'bits': bits, 'identity': identity_text, 'source_type': match[1], 'primary': identity}
    require(len(all_primary) == 58 and all_primary.count('E0308') == 56 and all_primary.count('E0512') == 2, 'primary diagnostic cardinality differs')
    require(set(named) == {(i, k) for i in range(28) for k in ('size', 'alignment')}, 'missing named query')
    require(set(closure) == {'size', 'alignment_wrapper'}, 'missing actual closure query')
    require(closure['size']['identity'] == closure['alignment_wrapper']['identity'], 'closure identities differ')
    rows = []
    for query in expected['named_queries']:
        size, alignment = named[(query['index'], 'size')], named[(query['index'], 'alignment')]
        require(alignment > 0 and alignment & (alignment - 1) == 0 and size % alignment == 0, 'invalid named size/alignment pair')
        rows.append({'type': query['type'], 'size': size, 'alignment': alignment})
    size_bits, wrapper_bits = closure['size']['bits'], closure['alignment_wrapper']['bits']
    require(size_bits > 0 and size_bits % 8 == 0 and wrapper_bits % 8 == 0, 'nonpositive or non-byte closure size')
    size, alignment = size_bits // 8, (wrapper_bits - size_bits) // 8
    require(alignment > 0 and alignment & (alignment - 1) == 0 and size % alignment == 0, 'invalid actual closure inferred alignment')
    return {'named': rows, 'actual_closure': {'size': size, 'alignment': alignment, 'diagnostics': closure},
            'primary_E0308': 56, 'primary_E0512': 2, 'summaries': summaries,
            'scope': 'Only concrete diagnostic source representations; no work/storage pricing, backing, peak, funding, runtime, ownership or GA authority.'}
