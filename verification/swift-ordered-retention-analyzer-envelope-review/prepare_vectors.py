#!/usr/bin/env python3
"""Pre-access independently encoded File fixtures; no producer imports or execution."""
import hashlib
import json
from pathlib import Path
import struct
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
MAX = (1 << 64) - 1
FUNCTION = 17
OFFSET = 1234
LENGTH = 31
TYPE = 2
DIGESTS = [bytes([41 + i]) * 32 for i in range(8)]

def pack(words):
    return struct.pack('<' + 'Q' * len(words), *words)

def magic(text):
    return int.from_bytes(text.encode('ascii'), 'little')

def put(raw, index, value):
    struct.pack_into('<Q', raw, index * 8, value)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def context(cap):
    raw = bytearray(8192)
    fields = [magic('MIXFIX01'), 1, 8192, 1, cap, 33, 8192, 3, 3, 4, 1, 32, 8192, 512, 0, 0]
    raw[:128] = pack(fields)
    for index, digest in enumerate(DIGESTS):
        raw[128 + index * 32:160 + index * 32] = digest
    return bytes(raw)

def profile():
    raw = bytearray(512 + 80000 * 32)
    raw[:128] = pack([magic('MIXPRF01'), 1, 512, 32, 80000, 8192, 3, 3, 4, 1, 32, 8192, 512, 0, 0, 0])
    raw[128:160] = DIGESTS[6]
    raw[160:192] = DIGESTS[7]
    raw[224:256] = DIGESTS[1]
    for function in range(80000):
        start = 512 + function * 32
        raw[start:start + 32] = pack([(0xffffffff << 32), MAX, 0, 0])
    start = 512 + FUNCTION * 32
    raw[start:start + 32] = pack([(1 << 32) | TYPE, OFFSET, LENGTH, 0])
    return bytes(raw)

def event(kind, *, phase=0, operation=1, hit=False, function=FUNCTION):
    values = [0, kind, phase, operation, 0, 0, function, OFFSET, LENGTH, TYPE, MAX, MAX, 0, 0, 0, 0]
    if kind == 1:
        values[7:10] = [MAX] * 3
    elif kind == 2:
        values[10] = 1 if hit else MAX
        values[13] = int(hit)
    elif kind == 3:
        values[15] = function & 511
    elif kind == 4:
        values[14] = MAX
        values[15] = function & 511
    elif kind == 5:
        values[13:16] = [64, 32, 8192]
    elif kind in (6, 7, 8):
        values[10] = 1
        values[13] = 64
    elif kind in (9, 10):
        values[13] = 64
    elif kind == 11:
        values[10:16] = [1, 2, 100, 0 if hit else 1, 64, 3]
    elif kind == 12:
        values[3] = 0
        values[8] = MAX
        values[10:16] = [1, 2, 100, 64, 0, 2]
    elif kind == 13:
        values[3] = 0
        values[6:10] = [MAX] * 4
        values[13] = phase
    elif kind == 14:
        values[7:10] = [MAX] * 3
        values[13:16] = [7, 11, 2]
    else:
        raise AssertionError(kind)
    return values

def stream(records, *, cap=False, corrupt_footer=False):
    limit = len(records) if cap else 1024
    header = [0] * 64
    header[:10] = [magic('MIXORDR1'), 1, 512, 128, 512, limit, 80000, 64, 512, 33]
    for slot, digest in ((16, DIGESTS[0]), (20, DIGESTS[1]), (24, DIGESTS[6]), (28, DIGESTS[7])):
        header[slot:slot + 4] = struct.unpack('<4Q', digest)
    last = [0] * 16
    last_operation = 0
    canonical = []
    for index, source in enumerate(records):
        item = list(source)
        item[0] = index + 1
        item[4] = index * 7 + 101
        item[5] = index * 13 + 211
        if item[1] == 1:
            last_operation = item[3]
        canonical.append(item)
        last = item
    footer = [0] * 64
    footer[:16] = [magic('MIXOEND1'), 1, len(records), len(records) + int(cap), int(cap), len(records),
                   last[4], last[5], last_operation, int(cap), last[4], last[5], 0, 0, MAX, 33]
    footer[33:36] = [5, 1, limit]
    footer[36:44] = header[16:24]
    if corrupt_footer:
        footer[63] = 1
    return pack(header) + b''.join(pack(item) for item in canonical) + pack(footer), limit, canonical

def main():
    name = sys.argv[1]
    assert name.startswith('run-') and name[4:].isdigit()
    output = BASE / 'pre-access-vectors' / name
    output.mkdir(parents=True)
    profile_bytes = profile()
    (output / 'profile.bin').write_bytes(profile_bytes)
    records = []

    def add(label, items, expected, **options):
        raw, cap, canonical = stream(items, **options)
        (output / (label + '.stream.bin')).write_bytes(raw)
        context_bytes = context(cap)
        (output / (label + '.context.bin')).write_bytes(context_bytes)
        records.append(dict(id=label, stream_sha256=sha(raw), context_sha256=sha(context_bytes),
                            records=canonical, expected=expected,
                            cap=bool(options.get('cap')), footer_corrupted=bool(options.get('corrupt_footer'))))

    begin = [event(1)]
    hit = begin + [event(2, hit=True)]
    miss = begin + [event(2)]
    scan = miss + [event(3)]
    plan = scan + [event(4)]
    ready = plan + [event(5)]
    evict_begin = ready + [event(6)]
    evict_taken = evict_begin + [event(7)]
    build = ready + [event(9)]
    built = build + [event(10)]
    closed_hit = hit + [event(11, hit=True), event(12), event(13, phase=5)]
    closed_build = evict_taken + [event(8), event(9), event(10), event(11), event(12), event(13, phase=5)]
    add('closed-hit', closed_hit, dict(framing=True, boundary='Closed', fixture_coordinate=5))
    add('closed-build-eviction', closed_build, dict(framing=True, boundary='Closed', fixture_coordinate=13))
    add('pin-failure-cursor-absent', begin + [event(14, function=MAX), event(12), event(14, operation=0, function=31), event(13, phase=5)],
        dict(framing=True, boundary='Closed', fixture_coordinate=5))
    add('pin-failure-cursor-different', begin + [event(14, function=31), event(12), event(13, phase=5)],
        dict(framing=True, boundary='Closed', fixture_coordinate=4))
    add('terminal-failure-release', [event(14, operation=0, function=MAX), event(12), event(13, phase=5)],
        dict(framing=True, boundary='Closed', fixture_coordinate=3))
    add('old-framing-arbitrary-stage', begin + [event(10), event(13, phase=5)],
        dict(framing=True, envelope='Refused', fixture_coordinate=1, reason='Stage'))
    add('refused-then-valid-framing', begin + [event(14), event(1, operation=2), event(10, operation=2), event(13, phase=5)],
        dict(framing=True, envelope='Refused', fixture_coordinate=2, reason='ForbiddenResume'))
    add('late-footer-after-closed', closed_hit, dict(framing=False, envelope='UnavailableAfterFramingRefusal'), corrupt_footer=True)
    add('late-footer-after-refused', begin + [event(10), event(13, phase=5)],
        dict(framing=False, envelope='UnavailableAfterFramingRefusal'), corrupt_footer=True)
    for label, prefix, state in [('idle', [event(12)], 0), ('acquire', begin, 1), ('hit', hit, 2), ('miss', miss, 3),
                                 ('scan', scan, 4), ('plan', plan, 5), ('ready', ready, 6),
                                 ('evict-begin', evict_begin, 7), ('evict-taken', evict_taken, 8),
                                 ('build', build, 9), ('built', built, 10)]:
        add('cap-' + label, prefix, dict(framing=True, boundary='CapCutUnknownTail', state=state,
                                       fixture_coordinate=len(prefix)), cap=True)
    for kind in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]:
        extra = event(kind, phase=5, operation=2 if kind == 1 else 1, hit=kind in (2, 11))
        if kind == 14:
            extra[3] = 0
        add('phase5-followed-by-' + str(kind), closed_hit + [extra],
            dict(framing=True, envelope='Refused', fixture_coordinate=5, reason='TerminalPhase'))
    manifest = dict(schema=1, status='independently-authored-before-proposal-access-not-product-executed',
                    generator_sha256=sha(Path(__file__).read_bytes()), profile_sha256=sha(profile_bytes),
                    fixture_count=len(records), vectors=records,
                    authority=dict(storedPrefixValidated=False, fullReplayAccepted=False, semanticMetricsValid=False))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    (output / 'executed-generator.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(fixtures=len(records), manifest_sha256=sha((output / 'manifest.json').read_bytes()),
                         path=str(output.relative_to(ROOT)))))

if __name__ == '__main__':
    main()
