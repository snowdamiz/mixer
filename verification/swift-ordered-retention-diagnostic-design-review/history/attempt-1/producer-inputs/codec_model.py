"""Finite synthetic wire/replay oracle; never imports or executes Mixer source.

This is a design model, not the proposed Rust observer or a target driver.
Only tiny caller-owned byte strings are used by the accompanying tests.
"""
import struct

RECORD = struct.Struct('<16Q')
HEADER = struct.Struct('<8sQQQ32s448s')
FOOTER = struct.Struct('<8s18Q360s')
NONE = (1 << 64) - 1
CAP = 4_194_304
KINDS = {'begin': 1, 'lookup': 2, 'plan_begin': 3, 'plan_end': 4,
         'miss_ready': 5, 'evict_begin': 6, 'evict_commit': 7,
         'build_begin': 8, 'build_ready': 9, 'pin': 10,
         'release': 11, 'phase': 12, 'failure': 13, 'evict_taken': 14}
FIELDS = ('seq', 'kind', 'phase', 'op', 'work', 'instructions', 'function',
          'body_offset', 'body_len', 'type_index', 'slot', 'pin_slot',
          'nonce', 'a', 'b', 'c')
FLAGS = 1 | 2 | 4 | 8  # cap, I/O, context, counter overflow


def event(kind, seq, **kw):
    x = dict.fromkeys(FIELDS, 0)
    x.update(kind=KINDS[kind], seq=seq, slot=NONE, pin_slot=NONE)
    x.update(kw)
    return x


def encode_record(x):
    if set(x) != set(FIELDS):
        raise ValueError('closed record fields')
    if any(type(v) is not int or not 0 <= v <= NONE for v in x.values()):
        raise ValueError('u64 fields')
    if x['kind'] not in KINDS.values() or x['phase'] > 5:
        raise ValueError('closed kind/phase')
    if (x['function'] >= 80_000 and not (x['function'] == NONE and x['kind'] == KINDS['failure'])) or x['type_index'] > (1 << 32) - 1:
        raise ValueError('identity range')
    if any(x[k] != NONE and x[k] >= 64 for k in ('slot', 'pin_slot')):
        raise ValueError('slot range')
    return RECORD.pack(*(x[k] for k in FIELDS))


def encode(events, *, cap=CAP, flags=0, terminal_work=None,
           terminal_instructions=None, final=(0, 0, 0, 0), finalized=1,
           context=b'x' * 32):
    """Synthetic list input only. The future writer must stream fixed blocks."""
    if type(cap) is not int or not 0 <= cap <= CAP:
        raise ValueError('cap')
    stored = events[:cap]
    if len(stored) != len(events):
        flags |= 1
    body = b''.join(encode_record(x) for x in stored)
    last = stored[-1] if stored else dict(seq=0, work=0, instructions=0, op=0)
    tw = last['work'] if terminal_work is None else terminal_work
    ti = last['instructions'] if terminal_instructions is None else terminal_instructions
    footer = (1, len(stored), flags, len(events), last['seq'], last['work'],
              last['instructions'], tw, ti, *final, 0, last['op'], 49,
              finalized, 0)
    return HEADER.pack(b'MXORD001', 1, RECORD.size, cap, context, b'\0' * 448) + body + \
        FOOTER.pack(b'MXEND001', *footer, b'\0' * 360)


def decode(data, *, expected_context=b'x' * 32):
    if len(data) < HEADER.size + FOOTER.size:
        raise ValueError('missing header/footer')
    magic, version, width, cap, context, reserved = HEADER.unpack_from(data)
    if (magic, version, width) != (b'MXORD001', 1, 128) or cap > CAP:
        raise ValueError('header')
    if context != expected_context or any(reserved):
        raise ValueError('context/reserved')
    footer = FOOTER.unpack_from(data, len(data) - FOOTER.size)
    if footer[0] != b'MXEND001' or footer[1] != 1 or any(footer[-1]):
        raise ValueError('footer')
    _, _, stored, flags, attempted, seq, work, insns, terminal_work, terminal_insns, \
        combined, tickets, entries, pins, failure, op, lifecycle, finalized, zero, _ = footer
    if flags & ~FLAGS or finalized != 1 or zero or lifecycle != 49:
        raise ValueError('closed footer')
    if stored > cap or len(data) != 1024 + 128 * stored or attempted < stored:
        raise ValueError('file/count bound')
    if bool(flags & 1) != (attempted > stored):
        raise ValueError('cap accounting')
    if any((combined, tickets, entries, pins)):
        raise ValueError('original cleanup not empty')
    records = []
    old_work = old_insns = 0
    for i in range(stored):
        x = dict(zip(FIELDS, RECORD.unpack_from(data, 512 + 128 * i)))
        encode_record(x)
        if x['seq'] != i + 1 or x['work'] < old_work or x['instructions'] < old_insns:
            raise ValueError('gap/duplicate/counter regression')
        records.append(x)
        old_work, old_insns = x['work'], x['instructions']
    last = records[-1] if records else dict(seq=0, work=0, instructions=0, op=0)
    if (seq, work, insns, op) != tuple(last[k] for k in ('seq', 'work', 'instructions', 'op')):
        raise ValueError('last record binding')
    if terminal_work < work or terminal_insns < insns:
        raise ValueError('terminal regression')
    return records, flags


def replay(records, *, truncated=False):
    """Independent synthetic state oracle, bounded by 64 resident/pin slots.

    a/b/c meanings implemented here: lookup outcome; pin outcome/bytes/postpins;
    eviction bytes; release postpins. Other event fields are reserved by design.
    Full plan/work attribution is deliberately outside this small model.
    """
    slots, pins, pending = {}, {}, None
    last_op = 0
    terminal = False
    counts = dict(hits=0, misses=0, decodes=0, evictions=0, releases=0)
    for x in records:
        kind = x['kind']
        if kind == KINDS['begin']:
            if terminal or pending is not None or x['op'] != last_op + 1:
                raise ValueError('overlapping/nonmonotonic operation')
            last_op = x['op']
            pending = dict(op=x['op'], function=x['function'], lookup=None, victim=None,
                           taken=False, build=False, ready=False)
        elif kind == KINDS['failure'] and x['op'] == 0:
            if pending is not None or terminal:
                raise ValueError('terminal failure context')
            terminal = True
        elif kind in (KINDS['phase'], KINDS['release']):
            if kind == KINDS['release']:
                key = (x['pin_slot'], x['nonce'])
                if key not in pins or pins[key] != (x['slot'], x['function']):
                    raise ValueError('stale or mismatched release')
                slot = slots[x['slot']]
                if slot['pins'] == 0 or x['a'] != slot['pins'] - 1:
                    raise ValueError('release pin count')
                slot['pins'] -= 1
                del pins[key]
                counts['releases'] += 1
        else:
            if pending is None or (x['op'], x['function']) != (pending['op'], pending['function']):
                raise ValueError('operation context')
            if kind == KINDS['lookup']:
                if pending['lookup'] is not None or x['a'] > 1:
                    raise ValueError('duplicate/outcome lookup')
                actual = next((s for s, v in slots.items() if v['function'] == x['function']), None)
                if (actual is not None) != bool(x['a']) or (actual is not None and actual != x['slot']):
                    raise ValueError('lookup disagrees with residents')
                pending['lookup'] = x['a']
                counts['hits' if x['a'] else 'misses'] += 1
            elif kind == KINDS['evict_begin']:
                slot = slots.get(x['slot'])
                if pending['lookup'] != 0 or pending['victim'] is not None or slot is None or slot['pins']:
                    raise ValueError('invalid/pinned eviction begin')
                if x['a'] != slot['bytes']:
                    raise ValueError('victim bytes')
                pending['victim'] = x['slot']
            elif kind == KINDS['evict_taken']:
                if pending['victim'] is None or pending['victim'] != x['slot'] or pending['taken']:
                    raise ValueError('eviction take without matching begin')
                del slots[x['slot']]
                pending['taken'] = True
            elif kind == KINDS['evict_commit']:
                if pending['victim'] is None or pending['victim'] != x['slot'] or not pending['taken']:
                    raise ValueError('eviction commit without matching begin')
                pending['victim'] = None
                pending['taken'] = False
                counts['evictions'] += 1
            elif kind == KINDS['build_begin']:
                if pending['lookup'] != 0 or pending['build']:
                    raise ValueError('build context')
                pending['build'] = True
            elif kind == KINDS['build_ready']:
                if not pending['build'] or pending['ready']:
                    raise ValueError('build readiness')
                pending['ready'] = True
            elif kind == KINDS['pin']:
                if pending['lookup'] is None or pending['victim'] is not None:
                    raise ValueError('incomplete lookup/eviction')
                if x['slot'] == NONE or x['pin_slot'] == NONE or x['nonce'] == 0:
                    raise ValueError('pin fields')
                if any(k[0] == x['pin_slot'] for k in pins):
                    raise ValueError('duplicate live pin slot')
                if x['a'] != 1 - pending['lookup']:
                    raise ValueError('pin outcome')
                if x['a']:
                    if not pending['ready'] or x['slot'] in slots:
                        raise ValueError('unbuilt/occupied publication')
                    slots[x['slot']] = dict(function=x['function'], bytes=x['b'], pins=0)
                    counts['decodes'] += 1
                slot = slots.get(x['slot'])
                if slot is None or slot['function'] != x['function'] or x['b'] != slot['bytes']:
                    raise ValueError('resident identity/bytes')
                if x['c'] != slot['pins'] + 1:
                    raise ValueError('publication pin count')
                slot['pins'] += 1
                pins[(x['pin_slot'], x['nonce'])] = (x['slot'], x['function'])
                pending = None
            elif kind == KINDS['failure']:
                # Incomplete begin/evict/build is an observed prefix, never rollback.
                pending = None
    if pending is not None and not truncated:
        raise ValueError('unclosed operation without original failure/truncation')
    return dict(**counts, resident_entries=len(slots), active_pins=len(pins),
                resident_bytes=sum(v['bytes'] for v in slots.values()),
                pending_operation=pending is not None, coverage='prefix' if truncated else 'complete-records')
