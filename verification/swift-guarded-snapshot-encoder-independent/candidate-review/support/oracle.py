"""Independent finite MIXSNB02 oracle, authored before encoder candidate access.

This deliberately allocates small complete synthetic images for host assertions.
It is neither a production encoder nor a validator/provenance/ownership issuer.
No producer implementation, model, orchestration, or fixture is imported.
"""
import struct

HEADER = 2560
BLOCK = 4096
MAX_IMAGE = 69_765_152
NATIVE = (1, 12, 1, 20, 12, 12, 16, 16, 16)
WORDS = (0, 3, 1, 5, 3, 4, 4, 4, 4)
CAPS = (67_108_864, 512, 8192, 34, 79_966, 8192, 4096, 4096, 4096)
VALIDATION_CEILINGS = (67_108_864, 16_777_216, 1_048_576, 512_000_000, 120_000)
RUN_CEILINGS = (67_108_864, 16_777_216, 16_777_216, 8_388_608, 64, 64,
                64_000_000, 64, 16_384, 4096, 768, 134_217_728, 268_435_456,
                100_000_000, 1_000_000_000, 32_768, 30_000)
WASI_CEILINGS = (32_768, 4_194_304, 32_000_000, 65_536, 64, 65_536, 30_000)
WASI_IDS = (
    'ArgsGet', 'ArgsSizesGet', 'EnvironGet', 'EnvironSizesGet', 'ClockResGet',
    'ClockTimeGet', 'FdClose', 'FdFdstatGet', 'FdFdstatSetFlags', 'FdFilestatGet',
    'FdFilestatSetSize', 'FdFilestatSetTimes', 'FdPread', 'FdPrestatGet',
    'FdPrestatDirName', 'FdRead', 'FdReaddir', 'FdSeek', 'FdSync', 'FdTell',
    'FdWrite', 'PathCreateDirectory', 'PathFilestatGet', 'PathFilestatSetTimes',
    'PathLink', 'PathOpen', 'PathReadlink', 'PathRemoveDirectory', 'PathRename',
    'PathSymlink', 'PathUnlinkFile', 'PollOneoff', 'ProcExit', 'RandomGet')


class Refused(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise Refused(label)


def words(image, offset, count=1):
    require(offset >= 0 and offset + count * 8 <= len(image), 'word extent')
    values = struct.unpack_from('<' + 'Q' * count, image, offset)
    return values[0] if count == 1 else values


def put(image, offset, values):
    for index, value in enumerate(values):
        require(type(value) is int and 0 <= value < 2**64, 'u64')
        struct.pack_into('<Q', image, offset + 8 * index, value)


def expected_image(observed):
    """Encode independently observed semantic fields; preserve independent copies.

    observed is not an authority input to product code. Future actual observations
    must be gathered by independently reviewed host code under the genuine guard.
    Source hex in this test-only mapping is the exact source bytes, not a digest.
    """
    source = observed['source']
    sections = observed['sections']
    require(len(sections) == 8 and len(observed['capacities']) == 8, 'eight metadata')
    header = bytearray(HEADER)
    header[:8] = b'MIXSNB02'
    payloads = [source]
    for index, rows in enumerate(sections, 1):
        out = bytearray(len(rows) * WORDS[index] * 8)
        for row_index, row in enumerate(rows):
            require(len(row) == WORDS[index], 'record arity')
            put(out, row_index * WORDS[index] * 8, row)
        payloads.append(out)
    put(header, 8, (2, HEADER, HEADER + sum(map(len, payloads)), 9, 1, 1, 34))
    put(header, 64, (len(source), observed['instructions'], 8, 664))
    put(header, 96, observed['validation_limits'])
    put(header, 144, observed['usage'])
    put(header, 224, observed['observations'])
    put(header, 384, observed['metadata'])
    header[512:520] = b'MIXLPR01'
    put(header, 520, (1, 576, observed['provenance_extent']))
    put(header, 544, observed['provenance_limits'])
    for index, value in enumerate(observed['retained_values']):
        require(len(value) == 32, 'retained32')
        header[584 + 32 * index:616 + 32 * index] = value
    require(len(observed['retained_values']) == 6, 'five digests plus nonce')
    require(len(observed['identities']) == 4, 'four identities')
    for index, identity in enumerate(observed['identities']):
        require(len(identity) == 8, 'eight identity fields')
        # The caller supplies signed timestamp values; exact two's complement.
        identity = identity[:4] + tuple(n % 2**64 for n in identity[4:])
        put(header, 776 + 64 * index, identity)
    header[1088:1096] = b'MIXRTB01'
    runtime = observed['runtime']
    put(header, 1096, (1, 512, int(runtime['wasi'] is not None), runtime['owner']))
    put(header, 1128, runtime['limits'])
    if runtime['wasi'] is not None:
        put(header, 1264, runtime['wasi'])
    put(header, 1360, runtime['scalars'])
    offset = HEADER
    for index, payload in enumerate(payloads):
        count = len(source) if index == 0 else len(sections[index - 1])
        capacity = len(source) if index == 0 else observed['capacities'][index - 1]
        put(header, 1600 + 64 * index, (index, count, capacity, NATIVE[index],
            capacity * NATIVE[index], 1 if index == 0 else 2, offset, len(payload)))
        offset += len(payload)
    require(len(observed['resolved']) == 34, 'actual resolved array extent')
    put(header, 2176, observed['resolved'])
    return bytes(header) + b''.join(payloads)


def inspect_image(image):
    """Finite grammar and source-derived equations; never revalidates Wasm."""
    require(HEADER <= len(image) <= MAX_IMAGE, 'image cap')
    require(image[:8] == b'MIXSNB02', 'magic')
    require(words(image, 8, 7) == (2, HEADER, len(image), 9, 1, 1, 34), 'fixed header')
    require(words(image, 80, 2) == (8, 664), 'native layout contract')
    require(image[512:520] == b'MIXLPR01' and words(image, 520, 2) == (1, 576), 'loader record')
    require(image[1088:1096] == b'MIXRTB01' and words(image, 1096, 2) == (1, 512), 'runtime record')
    for start, end in ((136, 144), (488, 512), (1032, 1088), (1424, 1600), (2448, 2560)):
        require(not any(image[start:end]), 'reserved')
    limits = words(image, 96, 5)
    require(limits == words(image, 544, 5), 'E02 validation limits')
    require(all(x <= cap for x, cap in zip(limits, VALIDATION_CEILINGS)), 'validation ceilings')
    require(words(image, 128) == words(image, 216) == words(image, 576), 'E03 deadline')
    directories, end = [], HEADER
    for index in range(9):
        entry = words(image, 1600 + 64 * index, 8)
        ident, count, capacity, native, charged, category, offset, extent = entry
        require(ident == index and category == (1 if index == 0 else 2), 'directory identity/category')
        require(native == NATIVE[index] and count <= CAPS[index] and count <= capacity, 'directory bounds')
        require(capacity * native < 2**64 and charged == capacity * native, 'E28 charge')
        require(offset == end and extent == (count if index == 0 else count * WORDS[index] * 8), 'directory extent')
        end += extent
        require(end <= len(image), 'payload bounds')
        directories.append(entry)
    require(end == len(image), 'complete contiguous image')
    source = directories[0][1]
    require(source == directories[0][2] == directories[0][4], 'source exact capacity')
    require(all(words(image, offset) == source for offset in (64, 144, 152, 536, 792, 1360)), 'E01 source')
    require(source <= limits[0], 'source budget')
    require(words(image, 160) == 664 + sum(d[4] for d in directories[1:]), 'E27 metadata inventory')
    require(words(image, 160) <= limits[1], 'metadata budget')
    require(words(image, 72) == words(image, 264) == words(image, 480), 'E04 instructions')
    for section, observation in enumerate((224, 232, 240, 248, 272, 280, 288, 296), 1):
        require(directories[section][1] == words(image, observation), 'E05-E12 logical count')
    require(directories[3][1] == 34 and words(image, 248) == words(image, 256), 'E13 imports/bodies')
    require(words(image, 240) + words(image, 248) <= 80_000, 'E13 total')
    require(words(image, 384) == words(image, 408) == 1, 'E19 memory/table presence')
    require(words(image, 392) == words(image, 328) and words(image, 400) == words(image, 352), 'E14-E15 memory')
    require(words(image, 416) == words(image, 360), 'E17 table minimum')
    for pair, duplicate, host, minimum, ceiling in ((432, 336, 400, 392, 768), (448, 368, 424, 416, 65_536)):
        tag, value = words(image, pair, 2)
        require(tag in (0, 1) and (tag == 1 or value == 0), 'option representation')
        require((tag, value) == words(image, duplicate, 2), 'E16/E18 option duplicate')
        require(value <= ceiling and words(image, host) == (value if tag else ceiling), 'E20 host maximum')
        require(words(image, minimum) <= words(image, host), 'E20 minimum')
    for offset in (392, 400, 416, 424, 440, 456, 328, 344, 352, 360, 376):
        require(words(image, offset) <= 2**32 - 1, 'u32 widening')
    require(words(image, 464) <= source and words(image, 472) <= source, 'declaration source offsets')
    present, owner = words(image, 1112, 2)
    require(present in (0, 1) and owner != 0, 'actual runtime presence/owner')
    runtime = words(image, 1128, 17)
    require(all(n <= cap for n, cap in zip(runtime, RUN_CEILINGS)), 'runtime ceilings')
    wasi = words(image, 1264, 12)
    require(present == 1 or not any(wasi), 'absent WASI zero')
    require(all(n <= cap for n, cap in zip(wasi[:7], WASI_CEILINGS)), 'WASI ceilings')
    require(all(n in (0, 1) for n in wasi[7:]), 'WASI grants')
    require(words(image, 1368) == words(image, 224), 'E21 guard type count')
    require(words(image, 1376) == min(runtime[4], words(image, 248)) and 1 <= words(image, 1376) <= 64, 'E22 slots')
    require(words(image, 1384) == runtime[5] and 1 <= runtime[5] <= 64, 'E23 pins')
    require(words(image, 1392) == 1, 'E24 initial nonce')
    require(words(image, 1408) == runtime[2] and words(image, 1416) == runtime[3], 'E25/E26 cache limits')
    require(words(image, 1400) <= words(image, 1408), 'E29 cache base bound')
    resolved = words(image, 2176, 34)
    require(all(1 <= value <= 34 for value in resolved), 'resolved enum IDs')
    parameters = directories[2][1]
    types = directories[1][1]
    for section in range(1, 9):
        d = directories[section]
        for index in range(d[1]):
            row = words(image, d[6] + index * WORDS[section] * 8, WORDS[section])
            if section == 2:
                row = (row,)
            require(all(n <= 2**32 - 1 for n in row), 'metadata u32 widening')
            if section == 1:
                require(row[0] + row[1] <= parameters and row[2] <= 4, 'signature')
            elif section == 2:
                require(row[0] in (1, 2, 3, 4), 'type enum')
            elif section == 3:
                require(row[4] < types and row[0] + row[1] <= source and row[2] + row[3] <= source, 'import')
            elif section == 4:
                require(row[2] < types and row[0] + row[1] <= source, 'function')
            elif section == 5:
                require(row[0] in (1, 2, 3, 4) and row[1] in (0, 1) and row[2] + row[3] <= source, 'global')
            elif section == 6:
                require(row[0] + row[1] <= source and row[2] <= 3, 'export')
            else:
                require(row[0] + row[1] <= source, 'segment')
    return {'bytes': len(image), 'blocks': (len(image) + BLOCK - 1) // BLOCK,
            'counts': [entry[1] for entry in directories], 'resolved': resolved}


def compare_actual(image, observed):
    summary = inspect_image(image)
    expected = expected_image(observed)
    require(image == expected, 'actual bytes differ from independent semantic observation')
    return summary
