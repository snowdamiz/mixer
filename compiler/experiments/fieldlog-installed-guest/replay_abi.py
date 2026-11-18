"""Check the compact replay ABI before running the owned VM validator."""
from support import descriptors
from analyze import Reader, wasm

CAP = 4_194_304
SIGNATURES = {
    'mixer_guest_ui_start_v1': dict(parameters=[], results=['i32']),
    'mixer_guest_ui_event_v1': dict(parameters=['i32'], results=['i32']),
    'mixer_guest_capability_ready_v1': dict(parameters=[], results=[]),
}


def check_descriptors(data):
    if len(data) > CAP:
        raise ValueError('payload exceeds the compact replay ceiling')
    info = descriptors(data)
    if info['imports']:
        raise ValueError('compact guest must have no imports')
    if info['startFunction'] is not None:
        raise ValueError('compact guest must have no start section')
    memory_exports = [row for row in info['exports'] if row['kind'] != 'function']
    if memory_exports != [dict(name='memory', kind='memory', index=0)]:
        raise ValueError('compact guest must export only memory index 0 as memory')
    functions = {row['name']: row['signature'] for row in info['exports'] if row['kind'] == 'function'}
    if functions != SIGNATURES:
        raise ValueError('compact guest function exports differ from the fixed ABI')
    memories = wasm(data)['memories']
    if memories != [dict(minimum=1, maximum=1)]:
        raise ValueError('compact guest must define one memory with limits 1/1 pages')
    return dict(**info, memories=memories)


def uint(value):
    encoded = bytearray()
    while value >= 128:
        encoded.append((value & 127) | 128)
        value >>= 7
    encoded.append(value)
    return bytes(encoded)


def export(name, kind, index):
    name = name.encode('ascii')
    return uint(len(name)) + name + bytes([kind]) + uint(index)


def negative_controls(data, info):
    """Mutate one section per control in memory, using the actual linked guest."""
    reader = Reader(data)
    header = bytes(reader.take(8))
    sections = []
    while reader.position < len(data):
        section_id = reader.byte()
        sections.append((section_id, bytes(reader.take(reader.uint()))))

    def rewrite(section_id, payload):
        kept = [(key, value) for key, value in sections if key != section_id]
        index = next((index for index, (key, _) in enumerate(kept) if key > section_id), len(kept))
        kept.insert(index, (section_id, payload))
        return header + b''.join(bytes([key]) + uint(len(value)) + value for key, value in kept)

    exports = Reader(dict(sections)[7])
    count = exports.uint()
    entries = bytes(exports.take(len(exports.data) - exports.position))
    memory = export('memory', 2, 0)
    ready = next(row for row in info['exports'] if row['name'] == 'mixer_guest_capability_ready_v1')
    start = next(row for row in info['exports'] if row['name'] == 'mixer_guest_ui_start_v1')
    wrong_signature = entries.replace(export(start['name'], 0, start['index']), export(start['name'], 0, ready['index']), 1)
    memory_error = 'compact guest must export only memory index 0 as memory'
    limits_error = 'compact guest must define one memory with limits 1/1 pages'
    functions_error = 'compact guest function exports differ from the fixed ABI'
    controls = [
        ('importedFunction', 2, b'\x01\x01m\x01f\x00' + uint(ready['typeIndex']), 'compact guest must have no imports'),
        ('startSection', 8, uint(ready['index']), 'compact guest must have no start section'),
        ('missingMemoryExport', 7, uint(count - 1) + entries.replace(memory, b'', 1), memory_error),
        ('renamedMemoryExport', 7, uint(count) + entries.replace(memory, export('other', 2, 0), 1), memory_error),
        ('wrongMemoryExportIndex', 7, uint(count) + entries.replace(memory, export('memory', 2, 1), 1), memory_error),
        ('extraMemoryExport', 7, uint(count + 1) + entries + export('other', 2, 0), memory_error),
        ('extraFunctionExport', 7, uint(count + 1) + entries + export('extra', 0, ready['index']), functions_error),
        ('wrongFunctionSignature', 7, uint(count) + wrong_signature, functions_error),
        ('missingMemory', 5, b'\x00', limits_error),
        ('extraMemory', 5, b'\x02\x01\x01\x01\x01\x01\x01', limits_error),
        ('differentMinimum', 5, b'\x01\x01\x00\x01', limits_error),
        ('differentMaximum', 5, b'\x01\x01\x01\x02', limits_error),
        ('unboundedMemory', 5, b'\x01\x00\x01', limits_error),
        ('sharedMemory', 5, b'\x01\x03\x01\x01', 'only unshared i32-addressed limits measured'),
    ]
    rejected = {}
    for name, section_id, payload, reason in controls:
        try:
            check_descriptors(rewrite(section_id, payload))
        except ValueError as error:
            if str(error) != reason:
                raise ValueError(f'{name} rejected for an unexpected reason: {error}') from error
            rejected[name] = reason
        else:
            raise ValueError(f'{name} passed the compact replay guard')
    return rejected
