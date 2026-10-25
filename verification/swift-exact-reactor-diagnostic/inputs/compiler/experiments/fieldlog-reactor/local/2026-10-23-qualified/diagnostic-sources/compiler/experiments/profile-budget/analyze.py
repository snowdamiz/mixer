"""Original bounded, non-authorizing Wasm/link-map measurements for this experiment."""
import collections
import hashlib
import re


class Reader:
    def __init__(self, data, base=0):
        self.data, self.position, self.base = memoryview(data), 0, base

    def take(self, count):
        if count < 0 or self.position + count > len(self.data):
            raise ValueError('measurement exceeds input')
        result = self.data[self.position:self.position + count]
        self.position += count
        return result

    def byte(self):
        return self.take(1)[0]

    def uint(self):
        value = 0
        for shift in range(0, 35, 7):
            byte = self.byte()
            if shift == 28 and byte & 0xf0:
                raise ValueError('u32 overflow')
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('unterminated u32')

    def count(self):
        count = self.uint()
        if count > 1_000_000:
            raise ValueError('measurement vector exceeds ceiling')
        return count

    def offset(self):
        if self.byte() != 0x41:
            raise ValueError('only i32.const offsets measured')
        value = 0
        for shift in range(0, 35, 7):
            byte = self.byte()
            payload = byte & 127
            if shift == 28 and 7 < payload < 0x78:
                raise ValueError('i32 overflow')
            value |= payload << shift
            if byte < 128:
                if self.byte() != 0x0b:
                    raise ValueError('extended offset expression not measured')
                return value & 0xffff_ffff
        raise ValueError('unterminated i32')

    def limits(self):
        flags = self.byte()
        if flags > 1:
            raise ValueError('only unshared i32-addressed limits measured')
        return {'minimum': self.uint(), 'maximum': self.uint() if flags else None}

    def end(self):
        if self.position != len(self.data):
            raise ValueError('trailing measured bytes')


def wasm(data):
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('measurement byte ceiling exceeded')
    reader = Reader(data)
    if reader.take(8) != b'\0asm\x01\0\0\0':
        raise ValueError('not Wasm version one')
    result = {'authorization': False, 'sections': [], 'memories': [], 'tables': [],
              'elements': [], 'data': [], 'largest_function_bodies': []}
    bodies = []
    seen = set()
    last = 0
    while reader.position < len(data):
        section_id = reader.byte()
        length = reader.uint()
        section = Reader(reader.take(length), reader.position - length)
        if section_id > 11 or (section_id and (section_id in seen or section_id < last)):
            raise ValueError('unknown, duplicate or unordered measured section')
        seen.add(section_id)
        if section_id:
            last = section_id
        entry = {'id': section_id, 'payload_bytes': length}
        result['sections'].append(entry)
        if section_id == 0:
            name_length = section.uint()
            if name_length > 4096:
                raise ValueError('custom name exceeds measurement ceiling')
            entry['name'] = bytes(section.take(name_length)).decode('utf8')
        elif section_id in (1, 2, 3, 6, 7):
            key = {1: 'types', 2: 'imports', 3: 'defined_functions', 6: 'globals', 7: 'exports'}[section_id]
            result[key] = section.count()
        elif section_id in (4, 5):
            for _ in range(section.count()):
                if section_id == 4:
                    if section.byte() != 0x70:
                        raise ValueError('only funcref table measured')
                    result['tables'].append({'element_type': 'funcref', **section.limits()})
                else:
                    result['memories'].append(section.limits())
            section.end()
        elif section_id in (9, 11):
            for _ in range(section.count()):
                flags = section.uint()
                if flags not in (0, 2):
                    raise ValueError('only active index/data segments measured')
                index = section.uint() if flags == 2 else 0
                offset = section.offset()
                if section_id == 9:
                    if flags == 2 and section.byte() != 0:
                        raise ValueError('only function-index elements measured')
                    count = section.count()
                    for _ in range(count):
                        section.uint()
                    result['elements'].append({'flags': flags, 'table': index, 'offset': offset, 'entries': count})
                else:
                    count = section.uint()
                    file_offset = section.base + section.position
                    payload = section.take(count)
                    result['data'].append({'flags': flags, 'memory': index, 'offset': offset,
                        'bytes': count, 'file_offset': file_offset,
                        'sha256': hashlib.sha256(payload).hexdigest()})
            section.end()
        elif section_id == 10:
            count = section.count()
            result['code_bodies'] = count
            for index in range(count):
                size = section.uint()
                bodies.append({'defined_function': index, 'body_bytes': size})
                section.take(size)
            section.end()
    result['largest_function_bodies'] = sorted(bodies, key=lambda item: item['body_bytes'], reverse=True)[:20]
    result['function_body_bytes'] = sum(item['body_bytes'] for item in bodies)
    result['active_data_bytes'] = sum(item['bytes'] for item in result['data'])
    result['active_data_max_end'] = max((item['offset'] + item['bytes'] for item in result['data']), default=0)
    result['initial_linear_memory_bytes'] = sum(item['minimum'] * 65536 for item in result['memories'])
    return result


def link_map(text):
    """Count input contributions once, excluding duplicate symbol alias rows."""
    entries = []
    group = region = None
    pattern = re.compile(r'\s*(-|[0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)( +)(.*)')
    for line in text.splitlines():
        match = pattern.fullmatch(line)
        if not match:
            continue
        address, offset, size, indentation, name = match.groups()
        if len(indentation) == 1:
            if name.isupper() or name.startswith('CUSTOM'):
                group, region = name, None
            elif name.startswith('.'):
                region = name
        elif len(indentation) == 9 and group in ('CODE', 'DATA'):
            entries.append({'group': group, 'region': region, 'address': None if address == '-' else int(address, 16),
                'link_map_file_offset': int(offset, 16), 'bytes': int(size, 16), 'input': name})
    if not entries:
        raise ValueError('link-map format not recognized; do not emit empty attribution')
    archives = collections.defaultdict(lambda: collections.Counter())
    for entry in entries:
        source = entry['input'].split(':(', 1)[0]
        if '.a(' in source:
            source = source.split('.a(', 1)[0] + '.a'
        category = 'code' if entry['group'] == 'CODE' else ('zero_fill' if entry['region'] == '.bss' else 'initialized_data')
        archives[source][category] += entry['bytes']
        archives[source][category + '_input_count'] += 1
    return {
        'scope': 'input contributions, not duplicate symbol aliases; padding/encoding overhead reported by binary sections separately',
        'archives_and_objects': [{'input': key, **value} for key, value in sorted(archives.items(),
             key=lambda item: item[1]['code'] + item[1]['initialized_data'] + item[1]['zero_fill'], reverse=True)],
        'largest_code_inputs': sorted((entry for entry in entries if entry['group'] == 'CODE'), key=lambda x: x['bytes'], reverse=True)[:20],
        'largest_initialized_data_inputs': sorted((entry for entry in entries if entry['group'] == 'DATA' and entry['region'] != '.bss'), key=lambda x: x['bytes'], reverse=True)[:20],
        'largest_zero_fill_inputs': sorted((entry for entry in entries if entry['region'] == '.bss'), key=lambda x: x['bytes'], reverse=True)[:10],
        'input_rows': len(entries),
    }


def initialized_contribution(data, measured, entry):
    """Map a linear-memory address through actual binary data segments.

    Link-map file offsets are diagnostic. The observed lld DATA offsets omit
    five framing bytes, so they must not be used as binary extraction offsets.
    """
    address, size = entry['address'], entry['bytes']
    matching = [segment for segment in measured['data']
                if address is not None and segment['offset'] <= address
                and address + size <= segment['offset'] + segment['bytes']]
    if len(matching) != 1:
        raise ValueError('initialized contribution lacks one containing binary segment')
    segment = matching[0]
    offset = segment['file_offset'] + address - segment['offset']
    payload = data[offset:offset + size]
    if len(payload) != size:
        raise ValueError('initialized contribution exceeds binary bytes')
    return payload, offset


def object_data(data):
    """Measure the official archive member's active data, including DATACOUNT.

    This deliberately does not interpret relocation/linking metadata or validate
    an executable module. The archive/object and final linked byte hashes bind
    the observed data comparison.
    """
    if len(data) > 128 * 1024 * 1024:
        raise ValueError('object measurement byte ceiling exceeded')
    reader = Reader(data)
    if reader.take(8) != b'\0asm\x01\0\0\0':
        raise ValueError('not a Wasm object')
    count = None
    segments = None
    while reader.position < len(data):
        identifier, length = reader.byte(), reader.uint()
        section = Reader(reader.take(length), reader.position - length)
        if identifier not in (0, 2, 11, 12):
            raise ValueError('object form outside measured ICU shape')
        if identifier == 12:
            if count is not None:
                raise ValueError('duplicate object data count')
            count = section.count()
            section.end()
        elif identifier == 11:
            if segments is not None:
                raise ValueError('duplicate object data section')
            segments = []
            for _ in range(section.count()):
                if section.uint() != 0:
                    raise ValueError('only active memory-zero object data measured')
                offset = section.offset()
                size = section.uint()
                file_offset = section.base + section.position
                payload = section.take(size)
                segments.append({'offset': offset, 'file_offset': file_offset, 'bytes': size,
                                 'sha256': hashlib.sha256(payload).hexdigest()})
            section.end()
    if segments is None or count != len(segments):
        raise ValueError('object data count/section mismatch')
    return segments
