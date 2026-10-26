#!/usr/bin/env python3
"""Independent finite mathematics and necessary source-work accounting only.

Reads frozen source/data; imports no producer, Mixer, compiler or old harness.
The finite oracle supplements, and does not replace, source-proof.md's induction.
"""
import copy
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MAX = (1 << 64) - 1
BASE_SHA = 'a43397ec7cbbec398502acae5911394fced7ed8d220fee096589940eafb49fb1'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def write(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + '\n')


def expected_merge():
    # Exact full source geometry, including both arms, all literals, counters,
    # all 320 output sites and every run reset. This string is never compiled.
    lines = ['fn merge(c: &mut Candidate2048) {',
             '    let eligibility = ld(c, 640);',
             '    let (time_bytes, indices) = c.split_at_mut(512);',
             '    let (timestamp_chunks, _) = time_bytes.as_chunks::<8>();',
             '    let timestamps: &[[u8; 8]; 64] = timestamp_chunks.first_chunk::<64>().expect("timestamp64");',
             '    {', '        let output = {', '            let mut second = u8::MAX;', '            [']
    for i in range(0, 64, 2):
        lines += ['                {', f'                    // width1 pair{i//2}; literals are actual source operands.',
                  f'                    let left = if eligibility & 0x{1<<i:016x}u64 != 0 {{ {i}u8 }} else {{ u8::MAX }};',
                  f'                    let right = if eligibility & 0x{1<<(i+1):016x}u64 != 0 {{ {i+1}u8 }} else {{ u8::MAX }};',
                  f'                    let lt = u64::from_le_bytes(timestamps[{i}usize]);',
                  f'                    let rt = u64::from_le_bytes(timestamps[{i+1}usize]);',
                  '                    let take_left = if right == u8::MAX { true } else { left != u8::MAX && lt <= rt };',
                  '                    if take_left { second = right; left } else { second = left; right }',
                  '                },', '                { second },']
    lines += ['            ]', '        };', '        indices[512..576].copy_from_slice(&output);', '    }']

    def heads(side, spaces):
        p = ' ' * spaces
        return [p + f'let index = s.indices[s.{side}p];', p + f's.{side}i = index as u16;',
                p + 'if index != u8::MAX {',
                p + f'    s.{side}t = u64::from_le_bytes(s.timestamps[index as usize]);', p + '}']

    for p in range(1, 6):
        width = 1 << p
        src, dst = (512, 0) if p % 2 else (0, 512)
        lines += ['    {', '        let output = {',
                  f'            let source: &[u8; 64] = indices[{src}..{src+64}].first_chunk::<64>().expect("index64");',
                  '            let mut s = FixedArrayMergeCursor {', '                indices: source, timestamps,',
                  f'                lp: 0, le: {width}, rp: {width}, re: {2*width},',
                  '                li: 256, ri: 256, lt: 0, rt: 0,', '            };',
                  f'            // p{p}: inline initial heads.', '            {']
        lines += heads('l', 16) + heads('r', 16) + ['            }', '            [']
        for out in range(64):
            lines += ['                {', f'                    // p{p}.out{out}: fully expanded emit expression.']
            if out and out % (2*width) == 0:
                lines += [f'                    s.lp = {out}; s.le = {out+width};',
                          f'                    s.rp = {out+width}; s.re = {out+2*width};', '                    {']
                lines += heads('l', 24) + heads('r', 24) + ['                    }']
            lines += ['                    #[cfg(test)]', '                    {',
                      '                        if s.li != 256 && s.ri != 256 {',
                      '                            SORT_COMPARISONS.fetch_add(1, std::sync::atomic::Ordering::Relaxed);',
                      '                        }', '                        SORT_MOVES.fetch_add(1, std::sync::atomic::Ordering::Relaxed);',
                      '                    }', '                    let take_left = if s.ri >= 255 {',
                      '                        s.li != 256', '                    } else {',
                      '                        s.li < 255 && s.lt <= s.rt', '                    };', '                    if take_left {']
            for side in ('l', 'r'):
                if side == 'r':
                    lines += ['                    } else {']
                lines += [f'                        let out = s.{side}i as u8;', f'                        s.{side}p += 1;',
                          f'                        if s.{side}p < s.{side}e {{']
                lines += heads(side, 28)
                lines += ['                        } else {', f'                            s.{side}i = 256;',
                          '                        }', '                        out']
            lines += ['                    }', '                },']
        lines += ['            ]', '        };', f'        indices[{dst}..{dst+64}].copy_from_slice(&output);', '    }']
    return '\n'.join(lines + ['}']) + '\n'


def check_source(proposed):
    assembly = read('source-assembly.json')
    base = (ROOT / assembly['predecessor_path']).read_bytes()
    need(sha(base) == BASE_SHA, 'predecessor source')
    old = b'''                    let Some(next) = remaining.checked_sub(bytes) else {
                        return reject(13);
                    };
                    remaining = next;
'''
    new = b'                    remaining -= bytes;\n'
    need(base.count(old) == 1, 'one old site')
    start = base.index(old)
    need(proposed == base[:start] + new + base[start+len(old):], 'only permitted source edit')
    need(sha(proposed) == assembly['proposed_sha256'], 'source binding')
    need(sha(base[:start]) == assembly['unchanged_prefix_sha256'], 'prefix hash')
    need(sha(base[start+len(old):]) == assembly['unchanged_suffix_sha256'], 'suffix hash')
    text = proposed.decode()
    lo = text.index('fn merge(')
    hi = text.index('#[cfg(test)]\nstatic COMMIT_FAULT', lo)
    merge = text[lo:hi]
    need(merge == expected_merge(), 'full merge source/received/control geometry')
    need(text.count('remaining -= bytes;') == 1, 'one ordinary subtraction')
    return text, merge


def cursor_merge(times, mask, observer=None):
    need(len(times) == 64 and 0 <= mask <= MAX and all(0 <= t <= MAX for t in times), 'merge input domain')
    a = []
    for i in range(0, 64, 2):
        left = i if mask & (1 << i) else 255
        right = i+1 if mask & (1 << (i+1)) else 255
        take = right == 255 or (left != 255 and times[i] <= times[i+1])
        a.extend((left, right) if take else (right, left))
    for p, width in enumerate((2, 4, 8, 16, 32), 1):
        output = []
        for base in range(0, 64, 2*width):
            pos = {'l': base, 'r': base+width}
            end = {'l': base+width, 'r': base+2*width}
            h = {}; stamp = {'l': 0, 'r': 0}

            def load(side, site):
                h[side] = a[pos[side]]
                if h[side] != 255:
                    stamp[side] = times[h[side]]
                if observer:
                    observer('head', p, site, side, h[side])

            load('l', ('initial', base)); load('r', ('initial', base))
            for j in range(2*width):
                take = h['l'] != 256 if h['r'] >= 255 else h['l'] < 255 and stamp['l'] <= stamp['r']
                if observer:
                    observer('choice', p, base+j, h['r'] >= 255, h['l'] < 255)
                side = 'l' if take else 'r'
                need(h[side] != 256, 'exhausted256 emitted')
                output.append(h[side])
                pos[side] += 1
                if pos[side] < end[side]:
                    load(side, ('output', base+j))
                else:
                    h[side] = 256
                    if observer:
                        observer('exhaustion', p, base+j, side, 256)
        a = output
    return a


def reference_order(times, mask):
    # Independent oracle has no cursor/sentinel/exhaustion decisions.
    chosen = [slot for slot in range(64) if mask & (1 << slot)]
    return sorted(chosen, key=lambda slot: (times[slot], slot)) + [255] * (64-len(chosen))


def permutation_check(order, mask):
    chosen = [i for i in range(64) if mask & (1 << i)]
    need(len(order) == 64, 'output capacity')
    need(order[:len(chosen)] and mask or not chosen, 'eligible prefix absent')
    need(set(order[:len(chosen)]) == set(chosen) and len(set(order[:len(chosen)])) == len(chosen), 'eligible permutation')
    need(order[len(chosen):] == [255] * (64-len(chosen)), 'sentinel suffix')


def prefix(order, occupied, sizes, total, headroom, first_empty, checked):
    remaining, mask, destination = total, 0, first_empty
    reads = []
    for i in range(64):
        if remaining <= headroom and destination != MAX:
            break
        reads.append(('candidate', 512+i))
        slot = order[i]
        if slot == 255:
            break
        need(0 <= slot < 64, 'prefix slot bound')
        reads.append(('resident', slot, 2))
        size = sizes[slot]
        if checked and remaining < size:
            return {'reason': 13, 'reads': reads}
        need(remaining >= size, 'ordinary subtraction underflow')
        remaining -= size
        mask |= 1 << slot
        destination = slot
    return {'reason': 0, 'remaining': remaining, 'mask': mask, 'destination': destination,
            'feasible': destination != MAX and remaining <= headroom, 'reads': reads}


def finite_semantics():
    cases = 0
    # Every mask and every representative weak-order rank vector through n=5.
    # MAX is a genuine eligible timestamp, independently distinguished from255.
    for n in range(6):
        for keys in itertools.product((0, 1, MAX), repeat=n):
            times = list(keys) + [0]*(64-n)
            for mask in range(1 << n):
                out = cursor_merge(times, mask)
                need(out == reference_order(times, mask), 'finite weak-order oracle')
                permutation_check(out, mask)
                cases += 1
    rng = random.Random(0x6d69786572)
    masks = [0, MAX, 1, 1 << 63, 0xaaaaaaaaaaaaaaaa, 0x5555555555555555]
    masks += [(1 << n)-1 for n in range(65)]
    masks += [rng.getrandbits(64) for _ in range(64)]
    families = [[0]*64, [MAX]*64, list(range(64)), list(reversed(range(64))),
                [int(f'{i:06b}'[::-1], 2) for i in range(64)],
                [MAX if i % 2 else 0 for i in range(64)],
                [rng.getrandbits(64) for _ in range(64)]]
    prefix_cases = 0
    for times in families:
        for mask in masks:
            out = cursor_merge(times, mask)
            need(out == reference_order(times, mask), '64-slot timestamp oracle')
            permutation_check(out, mask)
            cases += 1
            # Occupancy may strictly contain eligibility (pinned residents).
            occupied = mask | 0x8421084210842108
            for scheme in (0, 1, 2):
                slots = [i for i in range(64) if occupied & (1 << i)]
                sizes = [0]*64
                for rank, i in enumerate(slots):
                    sizes[i] = 1 if scheme == 0 else (rank+1 if scheme == 1 else MAX//len(slots))
                total = sum(sizes)
                need(total <= MAX, 'G2 admitted occupied total')
                first_empty = next((i for i in range(64) if not occupied & (1 << i)), MAX)
                for headroom in (0, total//2, total, MAX):
                    old = prefix(out, occupied, sizes, total, headroom, first_empty, True)
                    new = prefix(out, occupied, sizes, total, headroom, first_empty, False)
                    need(old == new and old['reason'] == 0, 'prefix value/refusal/read-order equivalence')
                    prefix_cases += 1
    # All 64 eligibility positions, empty/pinned exclusion and MAX-sized row.
    for slot in range(64):
        sizes = [0]*64; sizes[slot] = MAX
        out = cursor_merge([MAX]*64, 1 << slot)
        need(prefix(out, 1 << slot, sizes, MAX, 0, MAX, True) ==
             prefix(out, 1 << slot, sizes, MAX, 0, MAX, False), 'MAX byte scalar boundary')
        prefix_cases += 1
    return {'merge_cases': cases, 'prefix_cases': prefix_cases,
            'all_u64_and_all_masks_universal_claim_basis': 'source-proof.md induction, not finite enumeration'}


class Ledger:
    def __init__(self):
        self.events = []

    def s(self, site, *names):
        for name in names:
            self.events.append({'id': f'G3.{len(self.events):06}', 'owner': 'G3', 'site': site,
                                'kind': 'scalar', 'bytes': 0, 'operation': name})

    def c(self, site, size, name):
        self.events.append({'id': f'G3.{len(self.events):06}', 'owner': 'G3', 'site': site,
                            'kind': 'copy', 'bytes': size, 'operation': name})

    def value(self, site, name, target):
        self.s(site, f'{name} source -> {target}')

    def field(self, site, name, target):
        self.s(site, f'{name} owner pointer -> projection operand', f'{name} field address projection', f'{name} source -> {target}')

    def binary(self, site, op, left, right, target):
        left(op+' left'); right(op+' right')
        self.s(site, f'primitive {op}', f'{op} result source -> {target}')

    def fixed_index(self, site, base, expression, target, width, projected=False):
        if projected:
            self.s(site, f'{base} owner pointer -> field projection', f'{base} array-reference field address projection')
        expression('Index received index')
        self.s(site, f'{base} Index receiver borrow', f'{base} pointer -> Index received receiver',
               'Index entry control', 'received index -> bound left', 'fixed length -> bound right',
               'index<length predicate', 'bounds branch', 'received pointer -> address operand',
               'received index -> scale operand', f'width{width} -> scale operand', 'index*width',
               'scaled offset -> pointer-add operand', 'received pointer -> pointer-add operand',
               'element address formation', 'element address -> returned reference source',
               'element loan creation', 'returned reference -> caller received reference', 'Index return control',
               'received reference -> dereference operand', f'dereferenced source -> {target}')

    def guard(self, site):
        self.s(site, 'condition source -> if predicate', 'if branch')

    def cast(self, site, ty, source, target):
        source('cast operand'); self.s(site, f'cast {ty}', f'cast result source -> {target}')

    def destination(self, site, name):
        self.s(site, f'{name} owner pointer -> destination projection', f'{name} destination field address projection')

    def head(self, site, side):
        self.fixed_index(site, 's.indices', lambda d: self.field(site, 's.'+side+'p', d), 'index binding', 1, True)
        self.value(site, 'index', 'cast u16 operand'); self.s(site, 'cast u16')
        self.destination(site, 's.'+side+'i'); self.s(site, 'cast result source -> cached index destination')
        self.binary(site, '!=', lambda d: self.value(site, 'index', d), lambda d: self.value(site, 'u8::MAX', d), 'condition')
        self.guard(site)
        self.fixed_index(site, 's.timestamps', lambda d: self.cast(site, 'usize', lambda e: self.value(site, 'index', e), d), 'array8 source', 8, True)
        self.c(site, 8, 'indexed complete array8 -> from_le_bytes received array8')
        self.s(site, 'from_le_bytes entry', 'LE conversion', 'scalar -> designated return', 'from_le_bytes return')
        self.destination(site, 's.'+side+'t'); self.s(site, 'returned scalar -> cached timestamp destination')

    def head_controls(self, site, side):
        # Three actual source statements; these are NOT value projections,
        # arithmetic, API return, branch decision, or load/result transfers.
        self.s(site, f's.{side}i assignment expression unit construction',
               f's.{side}i semicolon unit discard and statement continuation',
               f's.{side}t assignment expression unit construction',
               f's.{side}t semicolon unit discard and statement continuation',
               'timestamp-if completed implicit unit construction',
               'timestamp-if unit discard and statement continuation')

    def choice(self, site, right_tail, left_eligible):
        self.binary(site, '>=', lambda d: self.field(site, 's.ri', d), lambda d: self.value(site, '255', d), 'condition'); self.guard(site)
        if right_tail:
            self.binary(site, '!=', lambda d: self.field(site, 's.li', d), lambda d: self.value(site, '256', d), 'take_left binding')
        else:
            self.binary(site, '<', lambda d: self.field(site, 's.li', d), lambda d: self.value(site, '255', d), 'and left')
            self.s(site, 'and short-circuit branch')
            if left_eligible:
                self.binary(site, '<=', lambda d: self.field(site, 's.lt', d), lambda d: self.field(site, 's.rt', d), 'take_left binding')
            else:
                self.s(site, 'short-circuited false -> take_left binding')
        self.value(site, 'take_left', 'if condition'); self.guard(site)


def necessary_trace(text):
    t = Ledger()
    times = [int(f'{i:06b}'[::-1], 2) for i in range(64)]
    head_sites = []; pair_blocks = []; counts = {'head': 0, 'choice': 0, 'exhaustion': 0}
    # Exact width1 arithmetic, same selected FixedIndex20 grammar.
    for slot in range(64):
        site = f'width1.head{slot}'
        t.binary(site, '&', lambda d: t.value(site, 'eligibility', d), lambda d: t.value(site, hex(1 << slot), d), '!= left')
        t.value(site, '0', '!= right'); t.s(site, 'primitive !=', '!= result -> condition'); t.guard(site)
        t.value(site, str(slot), 'left/right binding')
        t.fixed_index(site, 'timestamps', lambda d: t.value(site, str(slot), d), 'array8 source', 8)
        t.c(site, 8, 'complete indexed array8 -> from_le_bytes received array8')
        t.s(site, 'from_le_bytes entry', 'LE conversion', 'scalar -> designated return', 'from_le_bytes return', 'returned scalar -> lt/rt binding')
    for pair in range(32):
        site = f'width1.choice{pair}'
        t.binary(site, '==', lambda d: t.value(site, 'right', d), lambda d: t.value(site, 'u8::MAX', d), 'condition'); t.guard(site)
        t.binary(site, '!=', lambda d: t.value(site, 'left', d), lambda d: t.value(site, 'u8::MAX', d), 'and left'); t.s(site, 'and short-circuit branch')
        t.binary(site, '<=', lambda d: t.value(site, 'lt', d), lambda d: t.value(site, 'rt', d), 'take_left binding')
        t.value(site, 'take_left', 'if condition'); t.guard(site)
    width1_events = len(t.events)

    def observer(kind, p, location, side, index):
        if kind == 'head':
            need(index < 64, 'all-eligible witness head')
            if location[0] == 'initial':
                base = location[1]
                marker = f'// p{p}: inline initial heads.' if base == 0 else f'// p{p}.out{base}: fully expanded emit expression.'
            else:
                marker = f'// p{p}.out{location[1]}: fully expanded emit expression.'
            at = text.index(marker)
            if location[0] == 'output':
                # A run-boundary output contains both initial loads AND its
                # later selected-arm reload. Do not label the latter with the
                # initial load's source site.
                at = text.index(f'let out = s.{side}i as u8;', at)
            line = text.index(f'let index = s.indices[s.{side}p];', at)
            # For later output loads select its actual selected branch, not a
            # following unrelated run-reset head. Full merge identity checks it.
            site = f'p{p}.{location[0]}{location[1]}.{side}.line{text[:line].count(chr(10))+1}'
            before = len(t.events); t.head(site, side)
            need(sum(e['kind'] == 'scalar' for e in t.events[before:]) == 68, 'head68 arithmetic')
            source_line = text[:line].count('\n')+1
            head_sites.append({'site': site, 'line': source_line, 'side': side,
                               'index_assignment_statement_line': source_line+1,
                               'timestamp_assignment_statement_line': source_line+3,
                               'completed_timestamp_if_line': source_line+4})
            counts['head'] += 1
            if location[0] == 'initial' and side == 'r':
                pair_blocks.append(site)
        elif kind == 'choice':
            t.choice(f'p{p}.out{location}.choice', side, index); counts['choice'] += 1
        else:
            site = f'p{p}.out{location}.exhaustion'
            t.destination(site, 's.'+side+'i'); t.value(site, '256', 'exhausted head destination'); counts['exhaustion'] += 1

    out = cursor_merge(times, MAX, observer)
    need(out == reference_order(times, MAX), 'necessary witness order')
    baseline = [dict(e) for e in t.events]
    scalars = sum(e['kind'] == 'scalar' for e in baseline)
    copies = sum(e['kind'] == 'copy' for e in baseline)
    need((scalars, copies) == (32929, 384), 'independent baseline count')
    for item in head_sites:
        t.head_controls(item['site'], item['side'])
    for site in pair_blocks:
        t.s(site+'.two-head-block', 'completed explicit two-head block implicit unit construction',
            'two-head block unit discard and statement continuation')
    # Deliberately only a necessary part of ld(c,640), with no first_chunk,
    # expect, conversion, array payload or subsequent view setup credit.
    site = 'merge.eligibility.ld'
    t.s(site, 'c array address formation', 'c array reborrow', 'c array address -> source slice.data',
        'c array capacity2048 -> source slice.len', 'source slice.data -> ld received b.data',
        'source slice.len -> ld received b.len', 'literal640 -> ld received at', 'ld entry control')
    # Actual b[at..at+8] slice Index; fixed fields are NOT implicit.
    t.value(site, 'ld.at', 'Range.start source')
    t.binary(site, '+', lambda d: t.value(site, 'ld.at', d), lambda d: t.value(site, '8', d), 'Range.end source')
    t.s(site, 'Range.start -> Index received start', 'Range.end -> Index received end',
        'b slice receiver reborrow', 'b pointer -> Index received receiver.data', 'b length -> Index received receiver.len',
        'Index entry', 'start -> ordered left', 'end -> ordered right', 'start<=end predicate', 'ordered branch',
        'end -> upper left', 'received length -> upper right', 'end<=length predicate', 'upper branch',
        'received data -> address operand', 'received start -> address operand', 'view address formation',
        'end -> length subtraction left', 'start -> length subtraction right', 'view length=end-start',
        'view address -> return source.data', 'view length -> return source.len', 'view loan creation',
        'return source.data -> caller received view.data', 'return source.len -> caller received view.len', 'Index return control')
    need(counts == {'head': 320, 'choice': 320, 'exhaustion': 62}, 'later-pass witness counts')
    need(len(pair_blocks) == 31, 'initial/reset two-head block count')
    summary = {'baseline_scalars': scalars, 'baseline_copies': copies,
               'eligible_later_heads': len(head_sites), 'extra_head_statement_controls': 6*len(head_sites),
               'completed_two_head_blocks': len(pair_blocks), 'extra_block_controls': 2*len(pair_blocks),
               'counted_ld_prefix_scalars': 39, 'all_other_positive_source_work_omitted': True,
               'all_eligible_timestamps': times, 'output': out,
               'public_File_reachability_proved': False, 'source_G2_miss_admitted_witness': True}
    summary['source_state'] = {
        'fixture': {'slots': 64, 'pins': 1, 'base': 0, 'capacity': 64, 'entry': 64},
        'resident_rows': [[1, i, 1, 0, times[i], 1, 0, 0] for i in range(64)],
        'pin_rows': [[MAX, 0, 0, 0, 0, 0] for _ in range(64)],
        'progress': {'latch': 0, 'calls': 1000, 'q': [1000, 1, 1, 5, 1, 64, 64, 64, 0, 65, 0, 0, 0, MAX, MAX, 0]},
        'record_words': [1001, 5, 0, 1, 2, 2, 64, 7, 8, 9, MAX, MAX, MAX, 64, 0, 64],
        'requested_function_defined': 1, 'requested_plan': [64, 7, 8, 9, 0],
        'budget': {'remaining': 7680, 'spent': 0}, 'arena_bytes': 8388608,
    }
    need(len({s['line'] for s in head_sites}) == 320, 'each executed head actual source site distinct')
    actual_ld = sum(e['kind'] == 'scalar' and e['site'] == site for e in t.events)
    summary['counted_ld_prefix_scalars'] = actual_ld
    return t.events, summary, head_sites


def pack(events):
    scalars = [e for e in events if e['kind'] == 'scalar']
    copies = [e for e in events if e['kind'] == 'copy']
    return ([{'kind': 'scalar', 'events': scalars[i:i+16]} for i in range(0, len(scalars), 16)] +
            [{'kind': 'copy', 'events': [e]} for e in copies])


def validate(groups, expected):
    ids = []; actual = []
    for g in groups:
        need(g['kind'] in ('scalar', 'copy'), 'group kind')
        if g['kind'] == 'scalar':
            need(0 < len(g['events']) <= 16, 'scalar group maximum16')
            need(all(e['kind'] == 'scalar' and e['bytes'] == 0 for e in g['events']), 'scalar payload grammar')
        else:
            need(len(g['events']) == 1 and g['events'][0]['kind'] == 'copy' and 0 < g['events'][0]['bytes'] <= 128, 'full separate bounded copy')
        actual.extend(g['events']); ids.extend(e['id'] for e in g['events'])
    need(len(ids) == len(set(ids)), 'duplicate source event')
    need({e['id']: e for e in actual} == {e['id']: e for e in expected}, 'required source/control edge changed or absent')
    s = sum(e['kind'] == 'scalar' for e in actual)
    c = sum(e['kind'] == 'copy' for e in actual)
    return {'scalars': s, 'copies': c, 'scalar_groups': (s+15)//16, 'groups': (s+15)//16+c, 'cap': 2568}


def rejection(name, fn):
    try:
        fn()
    except (ValueError, IndexError, KeyError, TypeError):
        return {'name': name, 'rejected': True}
    raise ValueError('negative control accepted: '+name)


def main():
    bindings = read('input-bindings.json')
    for item in bindings['files']:
        path = HERE / item['frozen_packet_path'] if 'frozen_packet_path' in item else ROOT / item['path']
        data = path.read_bytes()
        need(len(data) == item['bytes'] and sha(data) == item['sha256'], 'input custody '+item['path'])
    data = (HERE / 'source/cache_state.rs.txt').read_bytes()
    text, merge = check_source(data)
    semantics = finite_semantics()
    events, witness, sites = necessary_trace(text)
    groups = pack(events)
    totals = validate(groups, events)
    need(totals['groups'] > totals['cap'], 'necessary obstruction absent')
    controls = []
    controls.append(rejection('source subtraction changes unrelated byte', lambda: check_source(data.replace(b'let mut mask = 0;', b'let mut mask = 1;', 1))))
    bad = expected_merge().replace('s.lp += 1;', 's.lp += 0;', 1)
    controls.append(rejection('exact unrolled merge advance mutation', lambda: need(bad == merge, 'merge source geometry')))
    order = reference_order([0]*64, MAX); order[1] = order[0]
    controls.append(rejection('duplicate eligible index', lambda: permutation_check(order, MAX)))
    order = reference_order([MAX]*64, 1); order[0] = 255
    controls.append(rejection('eligible MAX confused with absent sentinel', lambda: permutation_check(order, 1)))
    order = reference_order([0]*64, 1); order[0] = 64
    controls.append(rejection('out of range output', lambda: permutation_check(order, 1)))
    sizes = [1]*64; sizes[0] = 65
    controls.append(rejection('stale postG2 byte increase violates invariant', lambda: prefix(list(range(64)), MAX, sizes, 64, 0, MAX, False)))
    bad = copy.deepcopy(groups); bad[0]['events'].append(bad[1]['events'].pop())
    controls.append(rejection('17 scalar group', lambda: validate(bad, events)))
    bad = copy.deepcopy(groups); bad[-1]['events'][0]['bytes'] = 129
    controls.append(rejection('129 byte copy', lambda: validate(bad, events)))
    bad = copy.deepcopy(groups); bad[-1]['events'][0]['bytes'] = 1
    controls.append(rejection('incomplete array8 copy', lambda: validate(bad, events)))
    bad = copy.deepcopy(groups)
    for g in bad:
        for i, e in enumerate(g['events']):
            if e['operation'].endswith('semicolon unit discard and statement continuation'):
                del g['events'][i]; break
        else:
            continue
        break
    controls.append(rejection('omitted actual assignment statement continuation', lambda: validate(bad, events)))
    raw = json.dumps({'schema': 1, 'groups': groups}, sort_keys=True, separators=(',', ':')).encode()
    (HERE / 'necessary-G3-ledger.json.gz').write_bytes(gzip.compress(raw, mtime=0))
    write('necessary-G3-witness.json', witness)
    write('necessary-G3-sites.json', sites)
    write('necessary-G3-obstruction.json', {
        'schema': 1, 'source_sha256': sha(data), 'status': 'necessary source trace exceeds unchanged G3 cap; stop',
        'totals': totals, 'over_cap': totals['groups']-totals['cap'],
        'ledger_uncompressed_bytes': len(raw), 'ledger_uncompressed_sha256': sha(raw),
        'complete_G3_G4_G5_uppers': False, 'whole_changed_lifetime_accepted': False,
        'new_ordinary_subtraction_does_not_change_merge_bytes': True,
        'implementation_accepted': False, 'public_File_reachability_proved': False,
    })
    result = {'schema': 1, 'python': sys.version, 'source_sha256': sha(data),
              'input_tree_digest': bindings['input_tree_digest'], 'finite_semantics': semantics,
              'necessary_G3': totals, 'negative_controls': controls,
              'source_edit_universal_argument': 'source-proof.md; component preconditions only',
              'compiler_product_native_UI_capture_or_process_inventory_executed': False,
              'complete_accounting_fit_implementation_or_GA_accepted': False}
    write('check-result-optimized.json' if sys.flags.optimize else 'check-result.json', result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
