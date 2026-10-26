#!/usr/bin/env python3
"""Finite source/mathematical accounting only; never compiles or runs Rust."""
from __future__ import annotations

import datetime
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
C3 = ROOT / 'verification/swift-cache-state-implementation/correction-3'
PRIOR = ROOT / 'verification/swift-cache-state-byte-index-proposal'
BASE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
INPUTS = {
    C3 / 'candidate-repo-seal.json': '7044a00eef658d8c729e7301c0923ed193ec405c6c6009989a964b3159bad12f',
    C3 / 'source/library/cache_state.rs': BASE_SHA,
    PRIOR / 'seal.json': 'd4cad24a902d5a8551fa51a93b445382be59027e129ac2f65408bd22666ae736',
    ROOT / 'verification/swift-cache-state-g6-complete/seal.json': 'c806b2967e37978403641c0172f3d70013b1e74c0d28128236f26fb618812597',
    ROOT / 'verification/swift-cache-state-g6-complete/ledger.py': 'df296baa8a6115489d2bf59d9822edc7215cefe014a4aaf3f799ab61f24a75ee',
    ROOT / 'verification/swift-cache-state-g6-complete-independent/seal.json': '2813d055b2350902dd3b5deeab8c3a34a662d30d5ecdf25974fc13c624c44c73',
    ROOT / 'verification/swift-cache-state-byte-index-independent/seal.json': 'c4162bea405595b62fcb576ed616a5ff75ab6c6401c56092e7f0b3946a857883',
    ROOT / 'verification/swift-cache-state-byte-index-independent/ownership-addendum-seal.json': '9c2f5373e6e7f583db69c66cdf252d7029242351f249b639fca55c42b78ece67',
}


def digest(b):
    return hashlib.sha256(b).hexdigest()


def dump(name, data):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def info(p):
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': digest(b)}


# These are authored operation templates, using the selected Trace.e component
# units. They are not a compiler interpreter or libstd machine-work estimate.
def scalar(*names):
    return [{'kind': 'scalar', 'operation': x, 'bytes': 0} for x in names]


def copy(name, width):
    assert 0 < width <= 128
    return [{'kind': 'copy', 'operation': name, 'bytes': width}]


def value(name, target):
    return scalar(f'{name} value source -> {target}')


def literal(name, target):
    return scalar(f'literal {name} source -> {target}')


def field(name, target):
    return scalar(f'{name} owner pointer -> field projection operand',
                  f'{name} field address projection', f'{name} field source -> {target}')


def store_address(name):
    return scalar(f'{name} owner pointer -> destination field projection operand',
                  f'{name} destination field address projection')


def binary(op, left, right, target):
    return left + right + scalar(f'primitive {op}', f'{op} result source -> {target}')


def cast(op, operand, target):
    return operand + scalar(f'primitive cast {op}', f'{op} result source -> {target}')


def guard(expr):
    return expr + scalar('condition result source -> if predicate', 'if control branch')


def index(base, index_expr, target, array=False):
    # The selected scalar fixed-array Index template is20 plus the index
    # expression. This slice receiver also transfers its actual length field.
    # A projected slice field must first form its address (the selected dot-base
    # pair). Width1 scaling is deliberately retained.
    ops = scalar(f'{base} parent pointer -> field projection',
                 f'{base} slice field address projection') + index_expr
    ops += scalar(f'{base} Index receiver borrow', f'{base} data -> Index received receiver.data',
                  f'{base} len -> Index received receiver.len', 'Index entry control',
                  'received index -> upper predicate left', 'received len -> upper predicate right',
                  'index<len predicate', 'index check branch', 'received data -> address operand',
                  'received index -> scaling operand', f'element width{8 if array else 1} -> scaling operand',
                  'index*width', 'scaled offset -> pointer-add operand', 'received data -> pointer-add operand',
                  'element address formation', 'element address -> returned reference source',
                  'indexed reference loan creation', 'returned reference -> caller received reference',
                  'Index return control')
    if array:
        ops += scalar('received array reference -> dereference address operand',
                      'dereferenced array source address projection')
        ops += copy(f'{base} complete indexed array8 -> from_le_bytes received argument8', 8)
    else:
        ops += scalar('received reference dereference -> byte value source',
                      f'indexed byte source -> {target}')
    return ops


def head_load(side, eligible):
    # Source: let index=s.indices[s.lp]; s.li=index as u16;
    # if index!=u8::MAX { s.lt=from_le_bytes(s.timestamps[index as usize]); }
    ops = index('s.indices', field('s.' + side + 'p', 'Index received index'), 'local index')
    rhs = cast('u16', value('index', 'cast received operand'), 's.' + side + 'i')
    ops += rhs[:-1] + store_address('s.' + side + 'i') + rhs[-1:]
    ops += guard(binary('!=', value('index', '!= left received operand'),
                        literal('u8::MAX', '!= right received operand'), 'if condition source'))
    if eligible:
        ops += index('s.timestamps', cast('usize', value('index', 'cast received operand'),
                                         'Index received index'), 'LE received array', array=True)
        ops += scalar('from_le_bytes entry control', 'u64 from_le_bytes conversion',
                      'converted word source -> from_le_bytes designated return source',
                      'from_le_bytes return control')
        ops += store_address('s.' + side + 't')
        ops += scalar('from_le_bytes returned word source -> s.' + side + 't')
    return ops


def select(right_tail, left_eligible):
    ops = guard(binary('>=', field('s.ri', '>= left received operand'),
                       literal('255', '>= right received operand'), 'condition source'))
    if right_tail:
        ops += binary('!=', field('s.li', '!= left received operand'),
                      literal('256', '!= right received operand'), 'take_left binding')
    else:
        ops += binary('<', field('s.li', '< left received operand'),
                      literal('255', '< right received operand'), 'and left source')
        ops += scalar('and short-circuit branch')
        if left_eligible:
            ops += binary('<=', field('s.lt', '<= left received operand'),
                          field('s.rt', '<= right received operand'), 'take_left binding')
        else:
            ops += scalar('short-circuited false and-left source -> take_left binding')
    # Source's if take_left is a head-selection decision (G3), not an output
    # byte store. This is an explicit proposed classification, not spare credit.
    ops += guard(value('take_left', 'condition source'))
    return ops


def output_kernel(side, phase='all'):
    # Output source local is saved before advancing its head. No byte IndexMut.
    entry = scalar('emit exclusive cursor reborrow', 'cursor pointer source -> emit received s',
                   'emit entry control')
    ops = cast('u8', field('s.' + side + 'i', 'cast received operand'), 'out local binding')
    ops += store_address('s.' + side + 'p')
    ops += binary('+', field('s.' + side + 'p', '+ left received operand'),
                  literal('1', '+ right received operand'), 's.' + side + 'p')
    ops += guard(binary('<', field('s.' + side + 'p', '< left received operand'),
                        field('s.' + side + 'e', '< right received operand'), 'condition source'))
    returned = value('out', 'emit designated scalar return source')
    returned += scalar('emit return control', 'emit returned byte source -> output array constructor element')
    return {'entry': entry, 'body': ops, 'return': returned, 'all': entry + ops + returned}[phase]


def exhausted(side):
    return store_address('s.' + side + 'i') + literal('256', 's.' + side + 'i')


def load_heads_boundary(phase='all'):
    entry = scalar('load_heads exclusive cursor reborrow', 'cursor pointer source -> load_heads received s',
                   'load_heads entry control')
    returned = scalar('load_heads implicit unit source construction',
                      'load_heads unit/control return -> caller', 'load_heads unit discard and caller continuation')
    return {'entry': entry, 'return': returned, 'all': entry + returned}[phase]


def reset_positions(base, width):
    ops = []
    for name, number in [('lp', base), ('le', base + width), ('rp', base + width), ('re', base + 2 * width)]:
        ops += store_address('s.' + name) + literal(str(number), 's.' + name)
    return ops


def rangeview(base, start, end, exclusive=False):
    return literal(str(start), 'Range.start source') + literal(str(end), 'Range.end source') + scalar(
        'Range.start -> Index received start', 'Range.end -> Index received end',
        f'{base} Index receiver borrow creation', f'{base} data -> Index received receiver.data',
        f'{base} len -> Index received receiver.len', 'Index entry control',
        'start -> ordered predicate left', 'end -> ordered predicate right',
        'start<=end predicate', 'ordered branch', 'end -> upper predicate left',
        'received len -> upper predicate right', 'end<=len predicate', 'upper branch',
        'base data -> address operand', 'start -> address operand', 'view address formation',
        'end -> length subtraction left', 'start -> length subtraction right', 'length=end-start',
        'address result -> returned view.data', 'length result -> returned view.len',
        f'projected {"exclusive" if exclusive else "shared"} view loan creation',
        'returned view.data -> caller received view.data', 'returned view.len -> caller received view.len',
        'Index return control')


def output_copy(dst):
    ops = rangeview('indices', dst, dst + 64, True)
    ops += scalar('copy receiver reborrow', 'destination view.data -> copy received receiver.data',
                  'destination view.len -> copy received receiver.len',
                  'output array address formation', 'output array reborrow creation',
                  'output array address -> slice.data source', 'output array length64 -> slice.len source',
                  'source slice.data -> copy received source.data', 'source slice.len -> copy received source.len',
                  'copy entry control', 'copy receiver.len -> equality left', 'copy source.len -> equality right',
                  'source/destination length equality', 'copy length check branch')
    ops += copy('actual output64 received source -> existing Candidate destination64', 64)
    ops += scalar('copy unit/control returned -> caller', 'unit discard and statement continuation')
    return ops


class Trace:
    def __init__(self):
        self.events = []
        self.segments = []

    def add(self, owner, label, operations):
        first = len(self.events)
        for ordinal, op in enumerate(operations):
            self.events.append(dict(op, id=f'{owner}.{len(self.events):06}', owner=owner,
                                    site=label, local_ordinal=ordinal))
        self.segments.append({'owner': owner, 'site': label, 'first': first, 'count': len(operations)})

    def totals(self):
        result = {}
        for owner, cap in [('G3', 2568), ('G4', 768)]:
            scalars = sum(e['owner'] == owner and e['kind'] == 'scalar' for e in self.events)
            copies = sum(e['owner'] == owner and e['kind'] == 'copy' for e in self.events)
            result[owner] = {'scalars': scalars, 'copies': copies, 'scalar_groups': (scalars + 15) // 16,
                             'groups': (scalars + 15) // 16 + copies, 'cap': cap}
        return result


def source():
    # The source is deliberately fully expanded. There is no source macro,
    # hidden loop producing array fields, raw reinterpretation or unsafe code.
    lines = ['// UNSELECTED, FAILED SOURCE-ONLY PROPOSAL. Never compiled or executed.',
             '// All six64-byte constructors and all384 emit calls are explicit.',
             '#[repr(C)]', 'struct CachedMergeCursor<\'a> {',
             '    indices: &\'a [u8],', '    timestamps: &\'a [[u8; 8]],',
             '    lp: usize, le: usize, rp: usize, re: usize,',
             '    li: u16, ri: u16, lt: u64, rt: u64,', '}',
             'fn cached_load_heads(s: &mut CachedMergeCursor<\'_>) {']
    def head(side, indent):
        p = ' ' * indent
        return [p + f'let index = s.indices[s.{side}p];', p + f's.{side}i = index as u16;',
                p + 'if index != u8::MAX {',
                p + f'    s.{side}t = u64::from_le_bytes(s.timestamps[index as usize]);', p + '}']
    lines += head('l', 4) + head('r', 4) + ['}',
        'fn cached_emit(s: &mut CachedMergeCursor<\'_>) -> u8 {',
        '    #[cfg(test)]', '    {', '        if s.li != 256 && s.ri != 256 {',
        '            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);',
        '        }', '        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);', '    }',
        '    //255 is a real tail byte;256 is private exhausted-cursor control.',
        '    let take_left = if s.ri >= 255 {', '        s.li != 256', '    } else {',
        '        s.li < 255 && s.lt <= s.rt', '    };', '    if take_left {']
    for n, side in enumerate(['l', 'r']):
        if n:
            lines += ['    } else {']
        lines += [f'        let out = s.{side}i as u8;', f'        s.{side}p += 1;',
                  f'        if s.{side}p < s.{side}e {{']
        lines += head(side, 12)
        lines += ['        } else {', f'            s.{side}i = 256;', '        }', '        out']
    lines += ['    }', '}', 'fn merge(c: &mut Candidate2048) {',
              '    let (time_bytes, indices) = c.split_at_mut(512);',
              '    let (timestamps, _) = time_bytes.as_chunks::<8>();']
    for pass_no in range(6):
        width = 1 << pass_no
        src, dst = (0, 512) if pass_no % 2 == 0 else (512, 0)
        lines += ['    {', '        let output = {',
                  f'            let source = &indices[{src}..{src + 64}];',
                  '            let mut s = CachedMergeCursor {',
                  '                indices: source, timestamps,',
                  f'                lp: 0, le: {width}, rp: {width}, re: {2 * width},',
                  '                li: 256, ri: 256, lt: 0, rt: 0,',
                  '            };', '            cached_load_heads(&mut s);', '            [']
        for out in range(64):
            if out and out % (2 * width) == 0:
                base = out
                lines += ['                {',
                          f'                    s.lp = {base}; s.le = {base + width};',
                          f'                    s.rp = {base + width}; s.re = {base + 2 * width};',
                          '                    cached_load_heads(&mut s);',
                          '                    cached_emit(&mut s)', '                },']
            else:
                lines += ['                cached_emit(&mut s),']
        lines += ['            ]', '        };',
                  f'        indices[{dst}..{dst + 64}].copy_from_slice(&output);', '    }']
    lines += ['}']
    return '\n'.join(lines) + '\n'


def merge_model(times, eligibility, trace=None):
    a = [i if eligibility[i] else 255 for i in range(64)]
    comparisons = moves = loads = 0
    per_pass = []
    for pass_no in range(6):
        width = 1 << pass_no
        output = []
        pass_comparisons = pass_loads = 0
        if trace:
            src = 0 if pass_no % 2 == 0 else 512
            trace.add('G4', f'p{pass_no}.source-range', rangeview('indices', src, src + 64))
        for base in range(0, 64, 2 * width):
            pos = {'l': base, 'r': base + width}
            end = {'l': base + width, 'r': base + 2 * width}
            head, time = {}, {}
            if trace:
                if base:
                    trace.add('G4', f'p{pass_no}.run{base}.position-reset', reset_positions(base, width))
                trace.add('G3', f'p{pass_no}.run{base}.load-heads-entry', load_heads_boundary('entry'))
            def load(side):
                nonlocal loads, pass_loads
                index_byte = a[pos[side]]
                head[side] = index_byte
                if index_byte != 255:
                    time[side] = times[index_byte]
                loads += 1
                pass_loads += 1
                if trace:
                    trace.add('G3', f'p{pass_no}.out{len(output)}.load-{side}.{pos[side]}',
                              head_load(side, index_byte != 255))
            load('l')
            load('r')
            if trace:
                trace.add('G3', f'p{pass_no}.run{base}.load-heads-return', load_heads_boundary('return'))
            for _ in range(2 * width):
                if trace:
                    trace.add('G4', f'p{pass_no}.out{len(output)}.emit-entry', output_kernel('l', 'entry'))
                both = head['l'] != 256 and head['r'] != 256
                if both:
                    comparisons += 1
                    pass_comparisons += 1
                if head['r'] >= 255:
                    take_left = head['l'] != 256
                else:
                    take_left = head['l'] < 255 and time['l'] <= time['r']
                if trace:
                    trace.add('G3', f'p{pass_no}.out{len(output)}.head-selection',
                              select(head['r'] >= 255, head['l'] < 255))
                side = 'l' if take_left else 'r'
                assert head[side] != 256
                out = head[side]
                pos[side] += 1
                if trace:
                    trace.add('G4', f'p{pass_no}.out{len(output)}.output-body', output_kernel(side, 'body'))
                if pos[side] < end[side]:
                    load(side)
                else:
                    head[side] = 256
                    if trace:
                        trace.add('G3', f'p{pass_no}.out{len(output)}.head-exhausted', exhausted(side))
                if trace:
                    trace.add('G4', f'p{pass_no}.out{len(output)}.emit-return', output_kernel(side, 'return'))
                output.append(out)
                moves += 1
        assert len(output) == 64
        if trace:
            trace.add('G4', f'p{pass_no}.constructor-received',
                      copy('full array constructor64 source -> received output64 binding', 64))
            dst = 512 if pass_no % 2 == 0 else 0
            trace.add('G4', f'p{pass_no}.whole-output-copy', output_copy(dst))
        a = output
        per_pass.append({'width': width, 'comparisons': pass_comparisons, 'loads': pass_loads, 'outputs': 64})
    oracle = sorted((i for i in range(64) if eligibility[i]), key=lambda i: (times[i], i))
    oracle += [255] * (64 - len(oracle))
    assert a == oracle
    assert comparisons <= 321 and moves == 384 and loads == 384
    return {'output': a, 'comparisons': comparisons, 'outputs': moves, 'head_loads': loads, 'passes': per_pass}


def necessary_bound():
    # Every index and timestamp is valid on this one all-eligible witness. The
    # count deliberately excludes helper/view/setup/exhausted-head stores.
    actual_head = head_load('l', True)
    head_s = sum(x['kind'] == 'scalar' for x in actual_head)
    head_c = sum(x['kind'] == 'copy' for x in actual_head)
    pair_s = len(select(False, True))
    tail_s = min(len(select(True, True)), len(select(False, False)))
    scalars = 384 * head_s + 321 * pair_s + 63 * tail_s
    groups = (scalars + 15) // 16 + 384 * head_c
    # Also drop the two actual slice-length receiver transfers per head, using
    # only the still-selected fixed-array Index20 minimum. It STILL fails.
    minimal = scalars - 384 * 2
    return {'head_load_scalars': head_s, 'head_load_copies8': head_c,
            'pair_selection_scalars': pair_s, 'nonpair_selection_minimum_scalars': tail_s,
            'head_loads': 384, 'pair_selections': 321, 'nonpair_selections': 63,
            'necessary_scalars': scalars, 'necessary_copies8': 384,
            'necessary_groups': groups, 'cap': 2568, 'over_cap': groups - 2568,
            'even_omitting_two_slice_length_edges_per_head': {
                'scalars': minimal, 'groups': (minimal + 15) // 16 + 384,
                'over_cap': (minimal + 15) // 16 + 384 - 2568},
            'excluded_positive_work': ['load_heads arguments/entry/unit/return/caller',
                'exhausted-head256 stores', 'one-time split/as_chunks setup and its full source/received places',
                'callee merge implicit unit/return'],
            'G6_four_selected_caller_only_operations_recounted': False,
            'scope': 'Necessary G3 subtrace for this exact source and explicit ownership only; not a universal impossibility proof'}


def outer_g4_floor():
    # Exact selected rangeview/copytail templates, with64 replacing the fixed
    # length of the existing anonymous128 source in array-to-slice coercion.
    # State constructors, callee unit return and block continuations are omitted
    # positive work, so this remains a necessary lower count, not an upper.
    return {'kernel_scalars': 384 * 29 + 57 * 12,
            'six_source_rangeview_scalars': 6 * 28,
            'six_destination_range_and_copy_scalars': 6 * (28 + 3 + 6 + 7),
            'array_constructor64_to_received64_copies': 6,
            'whole_output64_to_existing_candidate64_copies': 6,
            'necessary_scalars': 384 * 29 + 57 * 12 + 6 * 28 + 6 * 44,
            'necessary_copy_groups': 12,
            'necessary_groups': (384 * 29 + 57 * 12 + 6 * 28 + 6 * 44 + 15) // 16 + 12,
            'cap': 768,
            'excluded_positive_work': ['six source/received state88 constructions and their complete moves',
                'initial state field operands/receivers', 'callee merge implicit unit/return', 'outer block continuations'],
            'selected_rangeview_template_scalars': 28,
            'copy_receiver_reborrow_and_data_len_scalars': 3,
            'source_array_to_received_slice_scalars': 6,
            'selected_copytail_scalars': 7,
            'scope': 'Necessary G4 floor for this exact expanded source and ownership; not a universal impossibility proof'}


def main():
    HERE.mkdir(exist_ok=True)
    (HERE / 'source').mkdir(exist_ok=True)
    bindings = []
    for path, expected in INPUTS.items():
        row = info(path)
        assert row['sha256'] == expected, row
        bindings.append(row)
    prior_seal = json.loads((PRIOR / 'seal.json').read_text())
    prior_members = {x['path']: x for x in prior_seal['members']}
    for name in ['source/probes.rs.txt', 'source/prefix.rs.txt']:
        path = PRIOR / name
        row = info(path)
        assert prior_members[row['path']]['sha256'] == row['sha256']
        bindings.append(row)
    dump('input-bindings.json', {'schema': 1, 'inputs': bindings,
         'source_of_truth': 'C3 immutable source; prior byte source fragments are unselected IDEAS only',
         'prior_numeric_grammar_or_bounds_reused': False})

    merge_source = source()
    (HERE / 'source/merge.rs.txt').write_text(merge_source)
    old = (C3 / 'source/library/cache_state.rs').read_text()
    start = old.index('fn merge(')
    end = old.index('#[cfg(test)]\nstatic COMMIT_FAULT', start)
    new = old[:start] + merge_source + old[end:]
    start = new.index('    // Shared one-pass bounded probes;')
    end = new.index('    let body = w[6] as usize;', start)
    new = new[:start] + (PRIOR / 'source/probes.rs.txt').read_text() + new[end:]
    start = new.index('            // The preceding checked base+request guard')
    end = new.index('            sq(c, 10, mask);', start)
    new = new[:start] + (PRIOR / 'source/prefix.rs.txt').read_text() + new[end:]
    (HERE / 'source/cache_state.rs.txt').write_text(new)
    (HERE / 'proposed.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                   fromfile='C3/cache_state.rs', tofile='UNSELECTED_FAILED_CACHED_HEAD/cache_state.rs')))
    cleanup = old[old.index('fn cleanup('):]
    assert cleanup == new[new.index('fn cleanup('):]
    # Apart from the replacement merge definition the G6 staging/commit source
    # between merge(c) and cleanup is identical except the identified G5 prefix.
    old_prefix = old[old.index('            merge(c);'):old.index('            // The preceding checked base+request guard')]
    new_prefix = new[new.index('            merge(c);'):new.index('            // G5.')]
    assert old_prefix == new_prefix
    after_prefix_old = old[old.index('            sq(c, 10, mask);'):]
    after_prefix_new = new[new.index('            sq(c, 10, mask);'):]
    assert after_prefix_old == after_prefix_new
    event_start = '    let body = w[6] as usize;'
    event_end = '            merge(c);'
    assert old[old.index(event_start):old.index(event_end)] == new[new.index(event_start):new.index(event_end)]
    dump('source-assembly.json', {'schema': 1, 'base_sha256': digest(old.encode()),
        'proposed_sha256': digest(new.encode()), 'merge_sha256': digest(merge_source.encode()),
        'cleanup_and_suffix_sha256': digest(cleanup.encode()), 'cleanup_and_suffix_identical': True,
        'G6_after_prefix_suffix_sha256': digest(after_prefix_old.encode()), 'G6_after_prefix_suffix_identical': True,
        'G6_merge_caller_and_headroom_guard_bytes_identical': True,
        'G6_event_staging_before_merge_bytes_identical': True,
        'changed_seams': ['private merge representation/algorithm', 'G2 byte seeds/scoped probe views copied as unselected idea',
                         'G5 byte-to-u64 prefix conversion/scoped arena view copied as unselected idea'],
        'G2_G5_complete_component_recount': 'NOT BUILT: initial G3 necessary-bound failure stops this finite proposal',
        'compiled_or_executed': False})

    templates = {'load-head-eligible': head_load('l', True), 'load-head-tail': head_load('l', False),
                 'selection-pair': select(False, True), 'selection-left-exhausted': select(False, False),
                 'selection-right-tail-or-exhausted': select(True, True), 'output-placement': output_kernel('l'),
                 'exhausted-head-store': exhausted('l'), 'load-heads-boundary': load_heads_boundary(),
                 'run-position-reset': reset_positions(2, 1),
                 'source-range': rangeview('indices', 0, 64), 'whole-output-copy': output_copy(512),
                 'output-constructor64-received': copy('full array64 source -> received output64', 64)}
    dump('component-templates.json', {'schema': 1, 'selected_grammar': 'Trace.e/handle/Index20, all operand/result edges, full actual copies',
         'templates': {k: {'scalars': sum(x['kind'] == 'scalar' for x in v),
                          'copies': sum(x['kind'] == 'copy' for x in v), 'operations': v} for k, v in templates.items()},
         'Index20_slice_delta': 'one actual received len edge; projected s.indices/s.timestamps adds the selected two field-address edges',
         'array8_rule': 'Index reference/dereference edges plus complete8B from_le_bytes argument copy; no scalar payload shortcut'})
    times = [int(f'{i:06b}'[::-1], 2) for i in range(64)]
    trace = Trace()
    witness = merge_model(times, [True] * 64, trace)
    assert witness['comparisons'] == 321
    assert [p['comparisons'] for p in witness['passes']] == [32, 48, 56, 60, 62, 63]
    bound = necessary_bound()
    assert bound['necessary_groups'] > 2568
    assert bound['even_omitting_two_slice_length_edges_per_head']['groups'] > 2568
    dump('necessary-bound.json', bound)
    g4_floor = outer_g4_floor()
    assert g4_floor['necessary_groups'] > g4_floor['cap']
    dump('G4-necessary-bound.json', g4_floor)
    dump('witness.json', {'schema': 1, 'name': 'all64 eligible six-bit reversal timestamps',
         'timestamps': times, 'eligibility': [True] * 64, 'result': witness, 'kernel_totals': trace.totals(),
         'kernel_completeness': 'All load_heads/emit executed non-test bodies/run resets plus G4 outer source/destination ranges and actual output64 copies; excludes state construction and one-time views',
         'whole_G3_or_G4_upper_bound_accepted': False})
    # Keep every event named and assigned exactly once; no omitted scalar is
    # quietly assigned a zero or treated as spare from another group.
    scalar_ord = {'G3': 0, 'G4': 0}
    copy_ord = {'G3': 0, 'G4': 0}
    seen = set()
    for event in trace.events:
        assert event['id'] not in seen
        seen.add(event['id'])
        owner = event['owner']
        if event['kind'] == 'scalar':
            event['group'] = f'{owner}.S{scalar_ord[owner] // 16:05}'
            scalar_ord[owner] += 1
        else:
            event['group'] = f'{owner}.C{copy_ord[owner]:05}'
            copy_ord[owner] += 1
    payload = json.dumps({'events': trace.events, 'segments': trace.segments}, separators=(',', ':')).encode()
    (HERE / 'finite-kernel-ledger.json.gz').write_bytes(gzip.compress(payload, mtime=0))
    dump('kernel-ledger-summary.json', {'schema': 1, 'events': len(trace.events),
        'decompressed_bytes': len(payload), 'decompressed_sha256': digest(payload),
        'totals': trace.totals(), 'every_kernel_event_assigned_once': True, 'scalar_block_max': 16,
        'copy_max_bytes': 64, 'owners_do_not_share_spare': True,
        'G3_kernel_upper_bound_before_outer_setup': {'scalars': 384 * 70 + 384 * 26 + 63 * 6 + 126 * 3,
            'copies': 384, 'note': 'All384 loads/choices at maximum,63 head-loader call boundaries,126 cursor exhaustion stores; deliberately over-approximates mutually exclusive choices'},
        'G4_outer_source_range_and_output_copy_events_included': True,
        'excluded_outer_operations': ['split/as_chunks/returned and received views',
            'six state88 source/received constructions and moves',
            'callee merge implicit unit/return; selected four caller-only G6 edges remain G6'],
        'not_a_complete_new_path_or_lifetime_upper_bound': True})

    cases = 0
    patterns = [list(range(64)), list(reversed(range(64))), [0] * 64,
                [(1 << 64) - 1] * 64, times, [i % 3 for i in range(64)]]
    eligibilities = [[True] * 64, [False] * 64, [i % 2 == 0 for i in range(64)]]
    for row in patterns:
        for eligibility in eligibilities:
            merge_model(row, eligibility)
            cases += 1
    rng = random.Random(0xCA43ED)
    for _ in range(2048):
        row = [rng.choice([0, 1, 2, (1 << 64) - 1, rng.getrandbits(64)]) for _ in range(64)]
        eligibility = [bool(rng.randrange(2)) for _ in range(64)]
        merge_model(row, eligibility)
        cases += 1
    dump('model-results.json', {'schema': 1, 'cases': cases, 'all_passed': True,
        'properties': ['exact independent sorted eligible oracle by(timestamp, original slot)',
            '255 tails only after all eligible indices', 'timestamp u64::MAX remains a valid key',
            'six passes,384 logical outputs,384 head loads,<=321 comparisons',
            'exhausted256 cursor is never narrowed or emitted'],
        'witness_reaches_321': True, 'Rust_or_native_execution': False,
        'exact_source_behavior_qualified': False, 'independent_review': 'pending'})
    dump('run.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command': [sys.executable, '-B', str(HERE / 'build.py')], 'python': sys.version,
        'platform': platform.platform(), 'source_revision': BASE_SHA,
        'scope': 'new source-only failed cached-head proposal; Python mathematical and source-accounting checks only',
        'result': 'Finite candidate rejected: G3 necessary subtrace exceeds cap; stop before G2/G5/outer-view upper ledger',
        'compiler_runtime_native_UI_capture_process_inventory': False,
        'product_mutation_commits_pushes_publication': False})
    print(json.dumps({'status': 'failed candidate rebuilt; verification and freeze required', 'necessary_bound': bound,
                      'witness_kernel_totals': trace.totals(), 'model_cases': cases}, indent=2))


if __name__ == '__main__':
    main()
