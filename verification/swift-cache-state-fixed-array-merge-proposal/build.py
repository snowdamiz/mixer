#!/usr/bin/env python3
"""Build a failed source-only necessary-bound packet. Never run/import Rust."""
from __future__ import annotations

import datetime
import difflib
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / 'verification/swift-cache-state-cached-head-proposal'
C3 = ROOT / 'verification/swift-cache-state-implementation/correction-3/source/library/cache_state.rs'
BASE_SHA = '0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8'
PRIOR_SEAL_SHA = '772ee1eab231fad68be582c7c17c794c437dadf1d46ae4ea77d04f9b331f3bdd'
CAPS = {'G2': 2560, 'G3': 2568, 'G4': 768, 'G5': 640}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def info(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


# The selected authored-source component vocabulary, reconstructed here without
# importing or executing another packet's ledger or any Mixer source.
def scalar(*names):
    return [{'kind': 'scalar', 'operation': name, 'bytes': 0} for name in names]


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


def store(name):
    return scalar(f'{name} owner pointer -> destination field projection operand',
                  f'{name} destination field address projection')


def binary(op, left, right, target):
    return left + right + scalar(f'primitive {op}', f'{op} result source -> {target}')


def cast(ty, operand, target):
    return operand + scalar(f'primitive cast {ty}', f'{ty} result source -> {target}')


def guard(ops):
    return ops + scalar('condition result source -> if predicate', 'if control branch')


def index(base, expression, target, array=False):
    # Exact fixed-array Index20. A projected array-reference field still needs
    # both selected address edges. Only the fat receiver.len transfer disappears.
    ops = scalar(f'{base} parent pointer -> field projection',
                 f'{base} array-reference field address projection') + expression
    core = scalar(f'{base} Index receiver borrow',
                  f'{base} thin pointer -> Index received receiver', 'Index entry control',
                  'received index -> upper predicate left', 'fixed length64 -> upper predicate right',
                  'index<length predicate', 'index check branch',
                  'received pointer -> address operand', 'received index -> scaling operand',
                  f'element width{8 if array else 1} -> scaling operand', 'index*width',
                  'scaled offset -> pointer-add operand', 'received pointer -> pointer-add operand',
                  'element address formation', 'element address -> returned reference source',
                  'indexed reference loan creation', 'returned reference -> caller received reference',
                  'Index return control')
    if array:
        core += scalar('received array reference -> dereference address operand',
                       'dereferenced array source address projection')
    else:
        core += scalar('received reference dereference -> byte value source',
                       f'indexed byte source -> {target}')
    assert len(core) == 20
    ops += core
    if array:
        ops += copy(f'{base} complete indexed array8 source -> from_le_bytes received argument8', 8)
    return ops


def head(side, eligible):
    ops = index('s.indices', field(f's.{side}p', 'Index received index'), 'index local binding')
    converted = cast('u16', value('index', 'cast received operand'), f's.{side}i')
    ops += converted[:-1] + store(f's.{side}i') + converted[-1:]
    ops += guard(binary('!=', value('index', '!= left received operand'),
                        literal('u8::MAX', '!= right received operand'), 'condition source'))
    if eligible:
        ops += index('s.timestamps', cast('usize', value('index', 'cast received operand'),
                                         'Index received index'), 'LE received array8', array=True)
        ops += scalar('from_le_bytes entry control', 'u64 from_le_bytes conversion',
                      'converted word source -> from_le_bytes designated return source',
                      'from_le_bytes return control')
        ops += store(f's.{side}t')
        ops += scalar(f'from_le_bytes returned word source -> s.{side}t')
    return ops


def choice(right_tail, left_eligible):
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
    return ops + guard(value('take_left', 'condition source'))


def emit(side):
    # Source-written block: no function receiver/argument/return boundary exists.
    # Its saved local, field projections, cursor arithmetic, exhaustion guard and
    # direct block-result -> array-element edge all remain actual source work.
    ops = cast('u8', field(f's.{side}i', 'cast received operand'), 'out local binding')
    ops += store(f's.{side}p')
    ops += binary('+', field(f's.{side}p', '+ left received operand'),
                  literal('1', '+ right received operand'), f's.{side}p')
    ops += guard(binary('<', field(f's.{side}p', '< left received operand'),
                        field(f's.{side}e', '< right received operand'), 'condition source'))
    return ops


def exhausted(side):
    return store(f's.{side}i') + literal('256', f's.{side}i')


def reset(base, width):
    ops = []
    for name, n in [('lp', base), ('le', base + width), ('rp', base + width), ('re', base + 2 * width)]:
        ops += store('s.' + name) + literal(str(n), 's.' + name)
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
                  'destination view.len -> copy received receiver.len', 'output array address formation',
                  'output array reborrow creation', 'output array address -> slice.data source',
                  'output array length64 -> slice.len source', 'source slice.data -> copy received source.data',
                  'source slice.len -> copy received source.len', 'copy entry control',
                  'copy receiver.len -> equality left', 'copy source.len -> equality right',
                  'source/destination length equality', 'copy length check branch')
    ops += copy('actual output64 received source -> existing Candidate destination64', 64)
    return ops + scalar('copy unit/control returned -> caller', 'unit discard and statement continuation')


def head_lines(side, indent):
    p = ' ' * indent
    return [p + f'let index = s.indices[s.{side}p];', p + f's.{side}i = index as u16;',
            p + 'if index != u8::MAX {',
            p + f'    s.{side}t = u64::from_le_bytes(s.timestamps[index as usize]);', p + '}']


def source():
    lines = ['// UNSELECTED, FAILED SOURCE-ONLY FIXED-ARRAY REFINEMENT. Never compiled or run.',
             '// All load/emit blocks are source-written: no helper or macro call boundary.',
             '#[repr(C)]', "struct FixedArrayMergeCursor<'a> {", "    indices: &'a [u8; 64],",
             "    timestamps: &'a [[u8; 8]; 64],", '    lp: usize, le: usize, rp: usize, re: usize,',
             '    li: u16, ri: u16, lt: u64, rt: u64,', '}', 'fn merge(c: &mut Candidate2048) {',
             '    let (time_bytes, indices) = c.split_at_mut(512);',
             '    let (timestamp_chunks, _) = time_bytes.as_chunks::<8>();',
             '    let timestamps: &[[u8; 8]; 64] = timestamp_chunks.first_chunk::<64>().expect("timestamp64");']
    positions = []
    for pass_no in range(6):
        width = 1 << pass_no
        src, dst = (0, 512) if pass_no % 2 == 0 else (512, 0)
        lines += ['    {', '        let output = {',
                  f'            let source: &[u8; 64] = indices[{src}..{src + 64}].first_chunk::<64>().expect("index64");',
                  '            let mut s = FixedArrayMergeCursor {', '                indices: source, timestamps,',
                  f'                lp: 0, le: {width}, rp: {width}, re: {2 * width},',
                  '                li: 256, ri: 256, lt: 0, rt: 0,', '            };',
                  f'            // p{pass_no}: inline initial heads.', '            {']
        lines += head_lines('l', 16) + head_lines('r', 16) + ['            }', '            [']
        for out in range(64):
            lines += ['                {', f'                    // p{pass_no}.out{out}: fully expanded emit expression.']
            if out and out % (2 * width) == 0:
                lines += [f'                    s.lp = {out}; s.le = {out + width};',
                          f'                    s.rp = {out + width}; s.re = {out + 2 * width};', '                    {']
                lines += head_lines('l', 24) + head_lines('r', 24) + ['                    }']
            positions.append({'pass': pass_no, 'out': out, 'first_line': len(lines) + 1})
            lines += ['                    #[cfg(test)]', '                    {',
                      '                        if s.li != 256 && s.ri != 256 {',
                      '                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);',
                      '                        }', '                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);',
                      '                    }', '                    let take_left = if s.ri >= 255 {',
                      '                        s.li != 256', '                    } else {',
                      '                        s.li < 255 && s.lt <= s.rt', '                    };', '                    if take_left {']
            for side in ['l', 'r']:
                if side == 'r':
                    lines += ['                    } else {']
                lines += [f'                        let out = s.{side}i as u8;', f'                        s.{side}p += 1;',
                          f'                        if s.{side}p < s.{side}e {{']
                lines += head_lines(side, 28)
                lines += ['                        } else {', f'                            s.{side}i = 256;',
                          '                        }', '                        out']
            lines += ['                    }', '                },']
        lines += ['            ]', '        };', f'        indices[{dst}..{dst + 64}].copy_from_slice(&output);', '    }']
    lines += ['}']
    return '\n'.join(lines) + '\n', positions


class Trace:
    def __init__(self):
        self.events = []
        self.segments = []

    def add(self, owner, site, operations):
        first = len(self.events)
        for ordinal, op in enumerate(operations):
            self.events.append(dict(op, id=f'{owner}.{len(self.events):06}', owner=owner,
                                    site=site, local_ordinal=ordinal))
        self.segments.append({'owner': owner, 'site': site, 'first': first, 'count': len(operations)})

    def totals(self):
        result = {}
        for owner in ['G3', 'G4']:
            scalars = sum(e['owner'] == owner and e['kind'] == 'scalar' for e in self.events)
            copies = sum(e['owner'] == owner and e['kind'] == 'copy' for e in self.events)
            result[owner] = {'scalars': scalars, 'copies': copies,
                             'scalar_groups': (scalars + 15) // 16,
                             'groups': (scalars + 15) // 16 + copies, 'cap': CAPS[owner]}
        return result


def witness(trace):
    # Independent finite coordinate execution of only the merge algorithm. It
    # neither imports nor executes the proposed Rust or another packet's model.
    times = [int(f'{i:06b}'[::-1], 2) for i in range(64)]
    indices = list(range(64))
    passes = []
    for pass_no in range(6):
        width = 1 << pass_no
        src, dst = (0, 512) if pass_no % 2 == 0 else (512, 0)
        trace.add('G4', f'p{pass_no}.source-range', rangeview('indices', src, src + 64))
        output = []
        counts = {'width': width, 'comparisons': 0, 'head_loads': 0, 'outputs': 0,
                  'exhaustion_guard_true': 0, 'exhaustion_guard_false': 0}
        for base in range(0, 64, 2 * width):
            if base:
                trace.add('G4', f'p{pass_no}.run{base}.reset', reset(base, width))
            pos, end = {'l': base, 'r': base + width}, {'l': base + width, 'r': base + 2 * width}
            heads, stamps = {}, {}

            def load(side):
                heads[side] = indices[pos[side]]
                stamps[side] = times[heads[side]]
                counts['head_loads'] += 1
                trace.add('G3', f'p{pass_no}.out{len(output)}.load-{side}.{pos[side]}', head(side, True))

            load('l')
            load('r')
            for _ in range(2 * width):
                if heads['l'] != 256 and heads['r'] != 256:
                    counts['comparisons'] += 1
                right_tail, left_eligible = heads['r'] >= 255, heads['l'] < 255
                take_left = heads['l'] != 256 if right_tail else left_eligible and stamps['l'] <= stamps['r']
                trace.add('G3', f'p{pass_no}.out{len(output)}.selection', choice(right_tail, left_eligible))
                side = 'l' if take_left else 'r'
                assert heads[side] != 256
                out = heads[side]
                trace.add('G4', f'p{pass_no}.out{len(output)}.inline-emit-body', emit(side))
                pos[side] += 1
                if pos[side] < end[side]:
                    counts['exhaustion_guard_true'] += 1
                    load(side)
                else:
                    counts['exhaustion_guard_false'] += 1
                    heads[side] = 256
                    trace.add('G3', f'p{pass_no}.out{len(output)}.exhausted', exhausted(side))
                trace.add('G4', f'p{pass_no}.out{len(output)}.block-result',
                          value('out', 'inline expression block result -> output array constructor element'))
                output.append(out)
                counts['outputs'] += 1
        trace.add('G4', f'p{pass_no}.constructor-received',
                  copy('complete array constructor64 source -> received output64 binding', 64))
        trace.add('G4', f'p{pass_no}.copy-output', output_copy(dst))
        indices = output
        passes.append(counts)
    oracle = sorted(range(64), key=lambda slot: (times[slot], slot))
    assert indices == oracle
    return {'name': 'all64 eligible six-bit reversal timestamps', 'timestamps': times,
            'eligibility': [True] * 64, 'output': indices, 'passes': passes,
            'comparisons': sum(p['comparisons'] for p in passes),
            'head_loads': sum(p['head_loads'] for p in passes),
            'outputs': sum(p['outputs'] for p in passes)}


def main():
    assert sha(C3.read_bytes()) == BASE_SHA
    assert sha((PRIOR / 'seal.json').read_bytes()) == PRIOR_SEAL_SHA
    seal = json.loads((PRIOR / 'seal.json').read_text())
    assert seal['member_count'] == 22 and seal['member_bytes'] == 787075
    for member in seal['members']:
        assert info(ROOT / member['path']) == member
    inputs = [C3, PRIOR / 'seal.json', PRIOR / 'component-templates.json',
              PRIOR / 'source/cache_state.rs.txt', PRIOR / 'necessary-bound.json',
              PRIOR / 'G4-necessary-bound.json', PRIOR / 'kernel-ledger-summary.json',
              PRIOR / 'source-assembly.json', ROOT / 'docs/swift-semantic-adapter-prerequisite.md',
              ROOT / 'docs/swift-cache-state-g6-accounting-selection.md',
              ROOT / 'verification/swift-cache-state-g6-complete/ledger.py',
              ROOT / 'verification/swift-cache-state-byte-index-independent/ownership-addendum.json']
    bindings = [info(p) for p in inputs]
    assert bindings[-2]['sha256'] == 'df296baa8a6115489d2bf59d9822edc7215cefe014a4aaf3f799ab61f24a75ee'
    assert bindings[-1]['sha256'] == 'a8a1cab464adca9f830d9fd25507f141bd8e5189cffd342ff794d3808ed5903a'
    dump('input-bindings.json', {'schema': 1, 'inputs': bindings,
         'frozen_prior_all22_members_verified': True,
         'frozen_prior_seal_sha256': PRIOR_SEAL_SHA,
         'input_tree_digest': sha(json.dumps(bindings, sort_keys=True, separators=(',', ':')).encode()),
         'imported_or_executed_input_code': False})

    merge, positions = source()
    (HERE / 'source/merge.rs.txt').write_text(merge)
    original = C3.read_text()
    prior_source = (PRIOR / 'source/cache_state.rs.txt').read_text()
    start = prior_source.index('// UNSELECTED, FAILED SOURCE-ONLY PROPOSAL.')
    end = prior_source.index('#[cfg(test)]\nstatic COMMIT_FAULT', start)
    candidate = prior_source[:start] + merge + prior_source[end:]
    (HERE / 'source/cache_state.rs.txt').write_text(candidate)
    (HERE / 'proposed.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), candidate.splitlines(True),
        fromfile='C3/cache_state.rs', tofile='UNSELECTED_FAILED_FIXED_ARRAY/cache_state.rs')))
    cleanup_old = original[original.index('fn cleanup('):]
    cleanup_new = candidate[candidate.index('fn cleanup('):]
    suffix = '            sq(c, 10, mask);'
    assert cleanup_old == cleanup_new
    assert original[original.index(suffix):] == candidate[candidate.index(suffix):]
    event_start, call = '    let body = w[6] as usize;', '            merge(c);'
    assert original[original.index(event_start):original.index(call)] == candidate[candidate.index(event_start):candidate.index(call)]
    before_prefix = '            // The preceding checked base+request guard'
    assert original[original.index(call):original.index(before_prefix)] == candidate[candidate.index(call):candidate.index('            // G5.')]
    dump('source-assembly.json', {'schema': 1, 'base_sha256': BASE_SHA,
         'proposed_sha256': sha(candidate.encode()), 'merge_sha256': sha(merge.encode()),
         'prior_G2_G5_source_ideas_retained_without_numeric_ledger_reuse': True,
         'cleanup_and_suffix_identical': True, 'cleanup_and_suffix_sha256': sha(cleanup_old.encode()),
         'G6_after_prefix_suffix_identical': True,
         'G6_after_prefix_suffix_sha256': sha(original[original.index(suffix):].encode()),
         'G6_event_staging_before_merge_identical': True,
         'G6_merge_call_and_headroom_guard_identical': True,
         'selected_G6_four_caller_only_operations_reassigned': False,
         'compiled_or_executed': False})
    dump('expansion.json', {'schema': 1, 'strategy': 'source-written equivalent; no macro or load/emit helper',
         'merge_sha256': sha(merge.encode()), 'array64_constructor_count': 6,
         'source_written_emit_blocks': 384, 'initial_head_pair_blocks': 63,
         'thin_index_source_first_chunk_calls': 6, 'thin_timestamp_first_chunk_calls': 1,
         'head_load_syntax_sites_including_both_branch_arms': 894,
         'actual_witness_head_loads': 384, 'emit_places': positions,
         'no_macro_expansion_work_omitted': True,
         'both_branch_arms_retained_in_source': True,
         'no_helper_argument_or_return_edges_for_inline_blocks': True,
         'direct_block_result_to_array_element_edge_retained': True})

    head_ops, pair_ops = head('l', True), choice(False, True)
    head_s = sum(op['kind'] == 'scalar' for op in head_ops)
    assert head_s == 68 and sum(op['kind'] == 'copy' for op in head_ops) == 1
    pair_s = len(pair_ops)
    tail_s = min(len(choice(True, True)), len(choice(False, False)))
    assert pair_s == 26 and tail_s == 17
    necessary_s = 384 * head_s + 321 * pair_s + 63 * tail_s
    necessary_c = 384
    floor = (necessary_s + 15) // 16 + necessary_c
    assert necessary_s == 35529 and floor == 2605 and floor > CAPS['G3']
    dump('component-templates.json', {'schema': 1,
         'grammar': 'selected Trace.e/field/Index20/operand/result/full payload copy model',
         'fixed_array_Index_scalar_core': 20,
         'thin_change': 'one receiver.len transfer removed per actual Index; fixed length predicate operand remains',
         'no_Index_operand_Option_or_LE_primitive_discount': True,
         'complete_Option16_rule': 'Each actual Option<u64>/Option<usize> source->received is a complete16B copy; none occurs in the counted merge subtrace. Outer G2/G5 loops/checked arithmetic remain uncounted positive work.',
         'templates': {'eligible_head': head_ops, 'pair_choice': pair_ops,
                       'right_tail_choice': choice(True, True), 'left_exhausted_choice': choice(False, False),
                       'inline_emit_body': emit('l'),
                       'inline_block_result': value('out', 'inline expression block result -> output array constructor element'),
                       'exhausted_head_store': exhausted('l'), 'reset': reset(2, 1),
                       'source_range': rangeview('indices', 0, 64), 'destination_output_copy': output_copy(512)}})
    excluded = ['one-time split_at_mut/as_chunks/full tuple source/received views',
                'first_chunk/expect complete niche Option<&array>8 source/received and message/receiver/return work',
                'six complete state72 source/received constructors and field operands (layout not compiled)',
                'initial inline head-pair block unit/continuation work',
                'exhausted256 head stores and exact nonpair choices beyond the17 minimum',
                'callee merge implicit unit construction and return (G4)',
                'all affected G2/G5 source work and complete actual Option16 transfers']
    dump('necessary-bound.json', {'schema': 1, 'owner': 'G3', 'cap': CAPS['G3'],
         'head_loads': 384, 'head_load_scalars': head_s, 'head_load_copies8': 1,
         'eligible_head_breakdown_scalars': {'index_byte': 25, 'cache_u16_cast_and_store': 5,
             'index255_guard': 6, 'timestamp_array_Index': 25, 'LE_call_return_and_cache_store': 7},
         'pair_choices': 321, 'pair_choice_scalars': pair_s,
         'nonpair_choices': 63, 'nonpair_minimum_scalars': tail_s,
         'necessary_scalars': necessary_s, 'necessary_copies8': necessary_c,
         'scalar_groups': (necessary_s + 15) // 16, 'necessary_groups': floor,
         'over_cap': floor - CAPS['G3'],
         'old_slice_head_scalars': 70, 'thin_saved_scalars_per_head': 2,
         'helper_calls_already_excluded_by_old_necessary_bound': True,
         'actual_new_source_has_no_load_or_emit_helper_calls': True,
         'excluded_positive_work': excluded,
         'G6_caller_only_operations_reassigned': False,
         'scope': 'necessary source subtrace for this exact fixed-array/source-expanded refinement; not a whole-source upper bound or universal impossibility proof'})

    trace = Trace()
    w = witness(trace)
    assert w['comparisons'] == 321 and w['head_loads'] == 384 and w['outputs'] == 384
    totals = trace.totals()
    assert totals['G3']['scalars'] == 36033 and totals['G3']['groups'] == 2637
    assert totals['G4']['scalars'] == 10332 and totals['G4']['groups'] == 658
    groups = []
    for owner in ['G3', 'G4']:
        scalars = [e['id'] for e in trace.events if e['owner'] == owner and e['kind'] == 'scalar']
        groups += [{'owner': owner, 'kind': 'scalar', 'events': scalars[i:i + 16]} for i in range(0, len(scalars), 16)]
        groups += [{'owner': owner, 'kind': 'copy', 'events': [e['id']], 'bytes': e['bytes']}
                   for e in trace.events if e['owner'] == owner and e['kind'] == 'copy']
    assert sorted(x for g in groups for x in g['events']) == sorted(e['id'] for e in trace.events)
    packet = {'schema': 1, 'scope': 'ordered finite counted subtrace; omitted positive outer work explicit',
              'events': trace.events, 'segments': trace.segments, 'groups': groups, 'totals': totals}
    raw = json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()
    (HERE / 'finite-subtrace-ledger.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    dump('subtrace-summary.json', {'schema': 1, 'totals': totals, 'event_count': len(trace.events),
         'decompressed_bytes': len(raw), 'decompressed_sha256': sha(raw),
         'scalar_group_max': 16, 'copy_max_bytes': 64,
         'every_counted_event_assigned_once': True, 'owners_share_spare': False,
         'not_whole_merge_or_G2_G5_upper_bound': True, 'excluded_positive_work': excluded,
         'all384_exhaustion_guards_including126_false': True,
         'no_loop_Option16_exists_in_source_written_merge': True,
         'source_written_block_statement_units_still_unaccounted_positive': True})
    dump('witness.json', dict(w, schema=1, source_sha256=sha(merge.encode()),
                             counted_subtrace_totals=totals,
                             whole_G3_G4_upper_bound_or_source_behavior_accepted=False))
    dump('run.json', {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'command': [sys.executable, '-B', str(HERE / 'build.py')], 'python': sys.version,
         'platform': platform.platform(), 'source_revision': BASE_SHA,
         'source_tree_identity': 'exact input hashes and input-tree digest in input-bindings.json; no Git queried',
         'scope': 'source assembly/custody/finite arithmetic only; no Rust source imported or executed',
         'result': 'necessary G3 floor2605 exceeds unchanged cap2568; stop',
         'native_or_capture_processes_started': False, 'native_runtime_UI_or_process_inventory': False,
         'compiler_or_product_runtime_executed': False, 'Git_or_hosted_access': False,
         'product_or_old_packet_mutated': False, 'root_metadata_mutated': False,
         'cleanup': 'No compiler/runtime/native/capture/test instance or build directory started; only owned source packet exists.',
         'G2_G5_full_recount': 'NOT BUILT: necessary-bound gate failed',
         'implementation_or_release_authority': False})
    print(json.dumps({'status': 'failed necessary bound; stopped', 'G3_floor': floor,
                      'G3_over_cap': floor - CAPS['G3'], 'finite_subtrace': totals,
                      'source_sha256': sha(candidate.encode()), 'compiler_or_runtime_executed': False}, indent=2))


if __name__ == '__main__':
    main()
