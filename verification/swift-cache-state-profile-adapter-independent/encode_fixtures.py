#!/usr/bin/env python3
"""Independent Wasm fixture encoder/offset oracle; not a product validator."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).absolute().parent
ABI = [
    ('args_get', 'II'), ('args_sizes_get', 'II'), ('environ_get', 'II'), ('environ_sizes_get', 'II'),
    ('clock_res_get', 'II'), ('clock_time_get', 'ILI'), ('fd_close', 'I'), ('fd_fdstat_get', 'II'),
    ('fd_fdstat_set_flags', 'II'), ('fd_filestat_get', 'II'), ('fd_filestat_set_size', 'IL'),
    ('fd_filestat_set_times', 'ILLI'), ('fd_pread', 'IIILI'), ('fd_prestat_get', 'II'),
    ('fd_prestat_dir_name', 'III'), ('fd_read', 'IIII'), ('fd_readdir', 'IIILI'), ('fd_seek', 'ILII'),
    ('fd_sync', 'I'), ('fd_tell', 'II'), ('fd_write', 'IIII'), ('path_create_directory', 'III'),
    ('path_filestat_get', 'IIIII'), ('path_filestat_set_times', 'IIIILLI'), ('path_link', 'IIIIIII'),
    ('path_open', 'IIIIILLII'), ('path_readlink', 'IIIIII'), ('path_remove_directory', 'III'),
    ('path_rename', 'IIIIII'), ('path_symlink', 'IIIII'), ('path_unlink_file', 'III'),
    ('poll_oneoff', 'IIII'), ('proc_exit', 'I'), ('random_get', 'II')]

def leb(n):
    assert 0 <= n <= 0xffffffff
    out = bytearray()
    while True:
        byte = n & 127
        n >>= 7
        out.append(byte | (128 if n else 0))
        if not n:
            return bytes(out)

def name(value):
    return leb(len(value)) + value

def section(identifier, payload):
    return bytes([identifier]) + leb(len(payload)) + payload

def function_type(parameters, result):
    types = {'I': 0x7f, 'L': 0x7e}
    return b'\x60' + leb(len(parameters)) + bytes(types[t] for t in parameters) + leb(len(result)) + bytes(types[t] for t in result)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def build(defined, wide=False, damage=None):
    assert defined >= 29
    types = [function_type(params, '' if label == 'proc_exit' else 'I') for label, params in ABI]
    types += [function_type('', ''), function_type('', 'I')]
    if wide:
        types += [function_type('', '')] * (129 - len(types))
    function_types = [34] * defined
    function_types[28] = 35
    bodies = [b'\x00\x0b'] * defined
    bodies[28] = b'\x00\x41\x00\x0b'
    notable = {'exported_entry': 28}
    if wide:
        assert defined > 95
        bodies[0] = b'\x00\x10' + leb(128) + b'\x0b'
        bodies[2] = b'\x00' + b'\x01' * 125 + b'\x0b'
        bodies[3] = b'\x00' + b'\x01' * 126 + b'\x0b'
        function_types[94] = function_types[95] = 128
        notable.update(call_absolute128=0, body_len127=2, body_len128=3, type128_first=94, type128_repeat=95)
    imports = [(label, index) for index, (label, _) in enumerate(ABI)]
    if damage == 'swapped-import-order':
        imports[0], imports[1] = imports[1], imports[0]
    if damage == 'missing-import':
        imports.pop()
    if damage == 'missing-body-end':
        bodies[0] = b'\x00'
    if damage == 'invalid-type-index':
        function_types[0] = len(types)
    module = bytearray(b'\x00asm\x01\x00\x00\x00')
    custom = name(b'independent.profile.rows.v1') + bytes((i * 37 + 11) & 255 for i in range(127 if not wide else 128))
    module.extend(section(0, custom))
    module.extend(section(1, leb(len(types)) + b''.join(types)))
    imported = bytearray(leb(len(imports)))
    for label, type_index in imports:
        imported.extend(name(b'wasi_snapshot_preview1') + name(label.encode()) + b'\x00' + leb(type_index))
    module.extend(section(2, imported))
    module.extend(section(3, leb(len(function_types)) + b''.join(leb(t) for t in function_types)))
    module.extend(section(4, b'\x01\x70\x01' + leb(46713) + leb(46713)))
    module.extend(section(5, b'\x01\x00' + leb(583 if damage == 'wrong-memory-minimum' else 584)))
    exports = [(b'memory', 2, 0), (b'_initialize', 0, 35), (b'mixer_fieldlog_corpus_v1', 0, 62)]
    module.extend(section(7, leb(len(exports)) + b''.join(name(n) + bytes([kind]) + leb(index) for n, kind, index in exports)))
    code = bytearray(leb(len(bodies)))
    relative_spans = []
    for i, body in enumerate(bodies):
        code.extend(leb(len(body)))
        relative_spans.append((34 + i, function_types[i], len(code), len(body)))
        code.extend(body)
    code_payload_start = len(module) + 1 + len(leb(len(code)))
    module.extend(section(10, code))
    absolute_spans = [(a, t, code_payload_start + offset, length) for a, t, offset, length in relative_spans]
    return bytes(module), absolute_spans, {k: 34 + v for k, v in notable.items()}, len(types)

def decode_leb(data, offset):
    total = 0
    for group in range(5):
        assert offset < len(data)
        byte = data[offset]; offset += 1
        assert group != 4 or byte < 16
        total |= (byte & 127) << (group * 7)
        if byte < 128:
            return total, offset
    raise AssertionError('oversized framing integer')

def frame_functions(data):
    # A deliberately separate framing walk. It validates fixture offsets/counts,
    # not the ABI, instructions, stack typing or semantic Wasm validity.
    assert data[:8] == b'\x00asm\x01\x00\x00\x00'
    cursor = 8; sections = {}
    while cursor < len(data):
        identifier = data[cursor]; cursor += 1
        size, payload = decode_leb(data, cursor)
        end = payload + size
        assert end <= len(data)
        if identifier:
            assert identifier not in sections
            sections[identifier] = (payload, end)
        cursor = end
    assert cursor == len(data)
    start, end = sections[3]
    function_count, cursor = decode_leb(data, start)
    functions = []
    for _ in range(function_count):
        ty, cursor = decode_leb(data, cursor); functions.append(ty)
    assert cursor == end
    start, end = sections[10]
    body_count, cursor = decode_leb(data, start)
    assert body_count == function_count
    result = []
    for ordinal in range(body_count):
        length, cursor = decode_leb(data, cursor)
        assert cursor + length <= end
        result.append((34 + ordinal, functions[ordinal], cursor, length))
        cursor += length
    assert cursor == end
    return result

def expected_rows(spans):
    output = bytearray(struct.pack('<IIQQQ', 0, 0xffffffff, 0xffffffffffffffff, 0, 0) * 80000)
    for absolute, ty, offset, length in spans:
        assert 34 <= absolute < 80000
        output[absolute * 32:(absolute + 1) * 32] = struct.pack('<IIQQQ', 1, ty, offset, length, 0)
    return bytes(output)

def verify_rows(blob, spans, source):
    assert len(blob) == 2560000
    by_absolute = {row[0]: row for row in spans}
    for absolute in range(80000):
        row = struct.unpack_from('<IIQQQ', blob, absolute * 32)
        if absolute in by_absolute:
            _, ty, offset, length = by_absolute[absolute]
            assert row == (1, ty, offset, length, 0) and offset + length <= len(source)
        else:
            assert row == (0, 0xffffffff, 0xffffffffffffffff, 0, 0)

def main():
    output = HERE / 'fixtures'; output.mkdir(exist_ok=False)
    cases = []
    for label, defined, wide in [('minimum-abi29', 29, False), ('offset-leb-type129', 99, True), ('maximum-total80000-candidate', 79966, False)]:
        wasm, spans, notable, type_count = build(defined, wide)
        independently_framed = frame_functions(wasm)
        assert independently_framed == spans
        rows = expected_rows(spans)
        verify_rows(rows, independently_framed, wasm)
        (output / (label + '.wasm')).write_bytes(wasm)
        (output / (label + '.expected-row-body.bin')).write_bytes(rows)
        selected = sorted(set([34, 35, 36, 37, 62, 127, 128, 129, 34 + defined - 1]) | set(notable.values()))
        selected = [n for n in selected if 34 <= n < 34 + defined]
        boundary = [{'absolute': n, 'type_index': spans[n-34][1], 'body_offset': spans[n-34][2], 'body_len': spans[n-34][3], 'body_hex': wasm[spans[n-34][2]:sum(spans[n-34][2:])].hex()} for n in selected]
        cases.append({'id': label, 'expected_real_validator': 'acceptance candidate; not yet executed',
            'defined': defined, 'imports': 34, 'types': type_count, 'source_bytes': len(wasm),
            'wasm': label + '.wasm', 'wasm_sha256': sha(wasm),
            'expected_body': label + '.expected-row-body.bin', 'expected_body_sha256': sha(rows),
            'expected_body_bytes': len(rows), 'notable_absolute_indices': notable,
            'boundary_spans': boundary, 'all_span_tuple_bytes_sha256': sha(b''.join(struct.pack('<4Q', *r) for r in spans)),
            'fixed_policy_maximum_runtime_admission_unverified': defined == 79966})
    for damage in ['swapped-import-order', 'missing-import', 'missing-body-end', 'invalid-type-index', 'wrong-memory-minimum']:
        wasm, spans, notable, type_count = build(29, damage=damage)
        assert frame_functions(wasm) == spans
        path = 'refuse-' + damage + '.wasm'; (output / path).write_bytes(wasm)
        cases.append({'id': 'refuse-' + damage, 'wasm': path, 'wasm_sha256': sha(wasm), 'source_bytes': len(wasm),
            'expected_real_validator': 'Err; no sealed owner; no adapter call or row output',
            'row_oracle_emitted': False, 'semantic_validation_not_run': True})
    manifest = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(), 'argv': sys.argv,
        'python': sys.version, 'encoder_sha256': sha(Path(__file__).read_bytes()),
        'basis': 'Independently authored Wasm byte encoder and separate framing/row oracle; no source import or product execution',
        'ABI_reference_sha256': sha((HERE / 'inputs/validator/wasi-descriptor.rs').read_bytes()),
        'positive_candidates': 3, 'negative_candidates': 5, 'cases': cases,
        'full_row_bytes_independently_checked': 3 * 2560000, 'real_Rust_validator_executed': False,
        'no_producer_lane_access': True, 'product_or_runtime_acceptance_claimed': False}
    (HERE / 'fixture-manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    print('PASS test-support framing only:3positive candidates/5refusal candidates;7,680,000 expected row bytes; real validation pending')

if __name__ == '__main__':
    main()
