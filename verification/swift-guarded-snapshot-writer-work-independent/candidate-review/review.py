#!/usr/bin/env python3
"""Independent immutable-source/arithmetic review; never imports producer/product code."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import platform
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREP = ROOT / 'verification/swift-guarded-snapshot-composition-source-preparation'
SRC = PREP / 'source/vm/src'
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-writer-work-audit'
PREACCESS = HERE.parent / 'preaccess'
MAX = (1 << 64) - 1
CAPS = [67108864, 512, 8192, 34, 79966, 8192, 4096, 4096, 4096]
WIDTH = [0, 3, 1, 5, 3, 4, 4, 4, 4]
checks = []


def digest(b):
    return hashlib.sha256(b).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def check(family, condition, **detail):
    require(condition, (family, detail))
    checks.append({'family': family, 'passed': True, **detail})


def exact_file(path, expected):
    raw = path.read_bytes()
    require(digest(raw) == expected, ('input digest', str(path)))
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(raw), 'sha256': digest(raw)}


def verify_members(folder, expected, count):
    reference = exact_file(folder / 'seal.json', expected)
    seal = read(folder / 'seal.json')
    require(len(seal['members']) == count, ('member count', str(folder)))
    for row in seal['members']:
        raw = (folder / row['path']).read_bytes()
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'],
                ('sealed member', str(folder), row['path']))
    return dict(reference, verified_members=count,
                verified_member_bytes=sum(r['bytes'] for r in seal['members']))


def definition(spec):
    """Byte lexer for custody only, never an authority or behavioral verifier."""
    data = (SRC / spec['path']).read_bytes()
    marker = spec['marker'].encode()
    at = -1
    for _ in range(spec['occurrence'] + 1):
        at = data.find(marker, at + 1)
        require(at >= 0, ('missing definition', spec['marker']))
    start = at
    at = data.index(b'{', start)
    depth = 0
    block = 0
    mode = 'code'
    while at < len(data):
        c, pair = data[at:at + 1], data[at:at + 2]
        if mode == 'line':
            if c == b'\n':
                mode = 'code'
        elif mode == 'block':
            if pair == b'/*':
                block += 1
                at += 1
            elif pair == b'*/':
                block -= 1
                at += 1
                if block == 0:
                    mode = 'code'
        elif mode == 'string':
            if c == b'\\':
                at += 1
            elif c == b'"':
                mode = 'code'
        elif pair == b'//':
            mode = 'line'
            at += 1
        elif pair == b'/*':
            mode, block = 'block', 1
            at += 1
        elif c == b'"':
            mode = 'string'
        elif c == b'{':
            depth += 1
        elif c == b'}':
            depth -= 1
            if depth == 0:
                end = at + 1
                if data[end:end + 1] == b'\n':
                    end += 1
                context = data.rfind(b'\n', 0, start) + 1
                while context:
                    prior = data.rfind(b'\n', 0, context - 1) + 1
                    if not data[prior:context].strip().startswith(b'#['):
                        break
                    context = prior
                value = dict(spec, line=data[:start].count(b'\n') + 1,
                             bytes=end - start, sha256=digest(data[start:end]),
                             declaration_context_sha256=digest(data[context:end]))
                return value, data[start:end].decode()
        at += 1
    raise RuntimeError(('unclosed definition', spec))


def checked_add(a, b):
    return a + b if 0 <= a <= MAX and 0 <= b <= MAX - a else None


def checked_mul(a, b):
    return a * b if 0 <= a <= MAX and 0 <= b <= MAX and (not b or a <= MAX // b) else None


def shape(counts):
    if len(counts) != 9 or any(n < 0 or n > c for n, c in zip(counts, CAPS)):
        return None
    words = sum(n * w for n, w in zip(counts, WIDTH))
    extent = 2560 + counts[0] + 8 * words
    return {'records': sum(counts[1:]), 'words': words, 'extent': extent,
            'blocks': (extent + 4095) // 4096}


def main():
    inputs = [
        verify_members(PRODUCER, '1dba5632efbf285f303eddc4c9dcb727d0bfaae9f24400a32de98a8989d292ea', 14),
        verify_members(PREACCESS, '83040c67c1896d30ba6fe88d5e119ef304cb7850edd276832eaa5bb69a48b7cd', 6),
        verify_members(PREP, 'bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751', 495),
    ]
    for name, expected in [
        ('guarded-snapshot-writer-work-independent-release.json', '2c67bc8fe96325eefaeebc6365f2aea7baf76d5995cb0aa1db904ab343305cdd'),
        ('guarded-snapshot-writer-work-independent-preaccess-custody.json', '18e6c1a1e872ff3a57bc32524fe7fb8671340a45e942008ba5bbba0b1f0a2238'),
        ('guarded-snapshot-encoder-work-host-acceptance.json', '757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351'),
    ]:
        inputs.append(exact_file(ROOT / 'verification/swift-semantic-adapter-root-review' / name, expected))
    manifest = read(PREP / 'source-manifest.json')
    require(len(manifest['members']) == 144, 'source roster count')
    require(digest(canonical(manifest['members'])) == '140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395', 'source tree')
    for row in manifest['members']:
        raw = (PREP / 'source/vm' / row['path']).read_bytes()
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'], ('source member', row['path']))
    bindings = read(PRODUCER / 'source-bindings.json')
    actual = []
    bodies = {}
    for spec in bindings['definitions']:
        observed, body = definition(spec)
        require(observed == spec, ('definition custody', spec['marker']))
        actual.append(observed)
        bodies[(spec['path'], spec['marker'])] = body
    require(len(actual) == 121 and digest(canonical(actual)) == bindings['definition_tree_sha256'], '121-definition tree')

    # Actual accepted encoder behavior is recovered byte-for-byte from the frozen
    # composer by removing only its exactly frozen measurement seam.
    old = ROOT / 'verification/swift-guarded-snapshot-encoder-implementation'
    original = old / 'source/vm/src/experimental/swift.rs'
    inputs.append(exact_file(original, 'dedb226175ec45b9c724a6bec6c8a9b43ed02c7de72970ea3f0cb7c5bc0d208f'))
    seam = b'\n' + (PREP / 'implementation/encoder_measurement.rs').read_bytes()
    composer = (SRC / 'experimental/swift.rs').read_bytes()
    require(composer.count(seam) == 1, 'exact measurement seam occurrence')
    recovered = composer.replace(seam, b'', 1)
    require(recovered.startswith(original.read_bytes()), 'accepted encoder behavior drift')

    ledger = read(PRODUCER / 'ledger.json')
    rows = {row['name']: row for row in ledger['rows']}
    check('producer-row-sums-only', all(sum(r['parts'].values()) == r['credits'] for r in rows.values()))
    I = 'experimental_swift_reactor/cache/initial_profile_v1.rs'
    C = 'experimental_swift_reactor/control.rs'
    K = 'experimental_swift_reactor/cache.rs'
    A = 'experimental_wasi/accounted.rs'
    writer = bodies[(I, 'fn write_snapshot_v1(')]
    check('actual-writer-behavior-binding', digest(writer.encode()) == '0de141d7c07db571a576fc343c3d43841614937c9ac07fd4cb64512761373343')
    check('WorkAuditPending-still-present', 'Err(AError::WorkAuditPending)' in bodies[(I, 'fn proposed_emission_work_v1(')])
    check('no-terminal-cursor-call', writer.count('cursor.next_block(transfer)') == 1 and 'if final_block{break;}' in writer)
    check('ack-before-post-stop', writer.index('acknowledged=acknowledged.checked_add') < writer.index('// Acknowledged bytes survive'))
    check('actual-count-binding-omission-reproduced',
          rows['writer_fixed_nonstop_nogetters']['parts']['actual_proof_counts_binding'] == 56 and 1 + 9 + 46 + 1 == 57,
          source_actions={'initial.cache_fetch': 1, 'proof': 9, 'counts': 46, 'actual_binding': 1}, proposed=56, expanded=57)

    # A first identity loop has field borrow/fetch1, setup/termination2,
    # and n*(advance/bind2 + as_ref1 + ok_or2 + Layout1 + ?2 + identity51 + ?2).
    identity_iteration = 2 + 1 + 2 + 1 + 2 + 51 + 2
    for path, row_name, term, n in [
        (K, 'SwiftFunctionCache.snapshot_pair_v1_max_optional_WASI', 'three_identity_loop', 3),
        (A, 'AccountedWasi.snapshot_pair_v1', 'four_identity_loop_with_setup', 4),
    ]:
        check('first-identity-loop-borrow-omission-reproduced',
              'for ticket in &self.buffers {' in bodies[(path, 'fn snapshot_pair_v1(')] and
              rows[row_name]['parts'][term] == 2 + n * identity_iteration,
              path=path, proposed=rows[row_name]['parts'][term], expanded=1 + 2 + n * identity_iteration)

    # Success observe15 has Ok1. Deadline replaces that with origin fetch1,
    # Deadline tag1 and Err1, thus17. This can be terminal only once per call.
    stop = bodies[(C, 'fn snapshot_observe_stop_v1(')]
    check('deadline-tail-actions-omission-reproduced',
          'Err(SnapshotStopV1::Deadline(self.deadline_origin))' in stop and
          rows['snapshot_observe_stop_v1_without_large_Copy']['credits'] == 15 and 15 - 1 + 1 + 1 + 1 == 17,
          success=15, deadline=17, additional_terminal_actions=2)

    # Independent finite adverse traces use monotonically diminishing request
    # lengths. These are arithmetic controls, not a simulated product runtime.
    kinds = ('interrupted', 'positive-short', 'zero', 'overreport', 'io', 'stop')
    for length in (1, 2, 31, 32, 4095, 4096):
        for limit in range(1, 33):
            for kind in kinds:
                acknowledged = 0
                requested = 0
                attempts = 0
                for attempt in range(1, limit + 1):
                    if acknowledged == length:
                        break
                    attempts += 1
                    requested += length - acknowledged
                    if kind == 'positive-short':
                        acknowledged += min(1, length - acknowledged)
                    elif kind == 'stop':
                        acknowledged = length
                    elif kind in ('zero', 'overreport', 'io'):
                        break
                check('independent-attempt-prefix', attempts <= 32 and requested <= 32 * length and acknowledged <= length,
                      length=length, attempt_limit=limit, terminal=kind)
    for source in (0, 1, 1535, 1536, 1537, 4095, 4096, CAPS[0]):
        for counts in ([source] + [0] * 8, [source] + CAPS[1:]):
            s = shape(counts)
            E, B = s['extent'], s['blocks']
            for attempts in (B, 2 * B, 31 * B, 32 * B):
                for positive in (0, attempts // 2, attempts):
                    stops = 12 + 5 * B + 2 * attempts
                    getters = 2 + 3 * B + attempts + positive
                    check('independent-event-envelope', stops <= 12 + 69 * B and getters <= 2 + 67 * B and
                          1214 + 4259 * B + 122 * attempts <= 1214 + 8163 * B)
            check('separate-fill-and-requested-terms', 4096 * B >= E and 32 * E != 4096 * B)
    for index in range(9):
        over = [0] * 9
        over[index] = CAPS[index] + 1
        check('each-cap-refused', shape(over) is None)
    top = shape(CAPS)
    check('maximum-shape', top == {'records': 109184, 'words': 331716, 'extent': 69765152, 'blocks': 17033})
    for a in (0, 1, MAX // 2, MAX - 1, MAX):
        for b in (0, 1, 2, MAX // 2, MAX):
            check('independent-checked-u64', checked_add(a, b) == (a + b if a + b <= MAX else None) and
                  checked_mul(a, b) == (a * b if a * b <= MAX else None))
    check('shape-checked-action-counts', 8 + 8 + 2 + 1 == 19 and 8 + 1 == 9 and
          16 + 9 * 22 + 8 * 28 + 27 + 13 + 23 == 501)
    check('ticket-route-counts', 4 + 4 + 4 + 10 + 3 == 25 and 25 + 3 == 28 and 25 + 6 == 31)
    check('structural-copy-slots', 18 + 12 + 5 + 2 + 2 + 1 + 1 + 10 + 14 == 65 and
          20 + 65 + 66 == 151 and ledger['copy_slots']['SnapshotAdmissionErrorV1'] == 153)
    for calls in (0, 1, 2, 32, 10000):
        check('repeated-wrappers-need-call-count', 16 * calls + (45 if calls else 0) >= 16 * calls and
              ledger['wrappers']['attach_outer_per_call'] == 16 and ledger['wrappers']['outer_getter_per_call'] == 3)
    check('separated-partial-interface', ledger['formula_interface']['partial_emission_consumption_contract'].startswith('F14224 ') and
          '+32E' in ledger['formula_interface']['partial_emission_consumption_contract'] and
          '+4096' in ledger['formula_interface']['partial_emission_consumption_contract'] and
          len(ledger['wrappers']['inherited_dependencies']) == 14)
    predecessor = read(PREACCESS / 'arithmetic-results.json')
    require(predecessor['count'] == 812, 'predecessor result count')
    custody = {'schema': 1, 'inputs': inputs, 'source_members_verified': 144,
               'source_tree_sha256': '140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395',
               'producer_definitions_verified': 121, 'definition_tree_sha256': digest(canonical(actual)),
               'encoder_original_prefix_bytes': len(original.read_bytes()), 'encoder_measurement_seam_sha256': digest(seam),
               'predecessor': {'independent_controls': 812, 'attribution': 'pre-existing independent preaccess packet; not this reviewer execution'},
               'source_revision_reference': '79b948a7b361e537cfdd03285f68ea8c50d1a382 from accepted encoder interface; frozen source tree is actual custody'}
    result = {'schema': 1, 'status': 'ledger-completeness-corrections-required',
              'checks_passed': len(checks), 'families': dict(Counter(c['family'] for c in checks)),
              'all_checks_sha256': digest(canonical(checks)), 'python': sys.version, 'platform': platform.platform(),
              'maximum_shape': top, 'findings': 3, 'numerical_whole_bound_disproven': False,
              'full_operational_work_selected': False, 'scope': 'source custody, manual logical-action review and independent Python finite arithmetic; no product/runtime/native execution'}
    for name, value in [('input-custody.json', custody), ('results.json', result)]:
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        if '--verify' in sys.argv:
            require((HERE / name).read_bytes() == raw, ('deterministic output mismatch', name))
        else:
            (HERE / name).write_bytes(raw)
    print(json.dumps({'status': result['status'], 'checks_passed': len(checks), 'source_members': 144,
                      'definitions': 121, 'numerical_whole_bound_disproven': False}, sort_keys=True))


if __name__ == '__main__':
    main()
