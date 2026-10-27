"""Unverified finite data grammar model. Never a VM proof or export authority.

All fixtures are synthetic. No file I/O, allocator admission or semantic replay.
"""
import struct

HEADER = 2560
SOURCE_CAP = 64 * 1024 * 1024
METADATA_CAP = 16 * 1024 * 1024
U32 = (1 << 32) - 1
U64 = (1 << 64) - 1
NATIVE_BYTES = [1,12,1,20,12,12,16,16,16]
PROOF_BYTES = 664
# id, name, wire words, maximum logical count. Source is byte-oriented.
SECTIONS = [(0, 'source', 0, SOURCE_CAP), (1, 'signatures', 3, 512),
            (2, 'parameters', 1, 8192), (3, 'imports', 5, 34),
            (4, 'functions', 3, 79966), (5, 'globals', 4, 8192),
            (6, 'exports', 4, 4096), (7, 'data', 4, 4096),
            (8, 'elements', 4, 4096)]
SNAPSHOT_CAP = HEADER + sum(cap if sid == 0 else words * 8 * cap
                            for sid, _, words, cap in SECTIONS)
USAGE = ['input_visible_bytes', 'source_bytes', 'metadata_reserved',
         'scratch_reserved', 'metadata_peak_reserved', 'scratch_peak_reserved',
         'total_peak_reserved', 'work_used', 'elapsed_micros', 'deadline_ms']
OBSERVATIONS = ['types', 'type_parameters', 'imported_functions',
                'defined_functions', 'validated_bodies', 'instructions',
                'globals', 'exports', 'data_segments', 'element_segments',
                'max_parameters_plus_locals', 'max_operand_values',
                'max_control_depth', 'memory_minimum',
                'memory_declared_maximum_present', 'memory_declared_maximum',
                'memory_host_maximum', 'table_minimum',
                'table_declared_maximum_present', 'table_declared_maximum']
RUN_LIMITS = ['source_bytes', 'metadata_bytes', 'cache_bytes', 'cache_entry_bytes',
              'cache_entries', 'active_pins', 'cache_work', 'frames', 'values',
              'controls', 'memory_pages', 'state_bytes', 'combined_bytes',
              'instruction_fuel', 'execution_work', 'host_calls', 'deadline_ms']
VALIDATION_LIMITS = ['source_bytes', 'metadata_bytes', 'scratch_bytes',
                     'work_credits', 'deadline_ms']
WASI_LIMITS = ['calls', 'transfer_bytes', 'work', 'one_transfer_bytes',
               'iovecs', 'log_bytes', 'deadline_ms']
GRANTS = ['secure_random', 'realtime', 'monotonic', 'stdout', 'stderr']
SCALARS = ['source_extent', 'type_count', 'slot_limit', 'pin_limit',
           'initial_nonce', 'cache_base', 'cache_capacity', 'entry_limit']
DIGESTS = ['source', 'manifest', 'build', 'session', 'executable']
RETAINED_VALUES = DIGESTS + ['nonce']  # Nonce is opaque retained bytes, never a digest.
FILE_FIELDS = ['dev', 'inode', 'bytes', 'mode', 'mtime', 'mtime_ns', 'ctime', 'ctime_ns']

class Refused(ValueError):
    pass

def require(condition, code):
    if not condition:
        raise Refused(code)

def words(values):
    require(all(type(n) is int and 0 <= n <= U64 for n in values), 'u64')
    return b''.join(struct.pack('<Q', n) for n in values)

def unpack(data, offset, count):
    require(0 <= offset <= len(data) and count * 8 <= len(data) - offset, 'word extent')
    return list(struct.unpack_from('<' + 'Q' * count, data, offset))

def zero(data, begin, end):
    require(not any(data[begin:end]), 'reserved or absent bytes')

def option(flag, value):
    require(flag in (0, 1), 'option flag')
    require(flag == 1 or value == 0, 'absent option payload')
    require(value <= U32, 'u32 option payload')

def parse_loader(data):
    require(len(data) == 576 and data[:8] == b'MIXLPR01', 'loader provenance envelope')
    require(unpack(data, 8, 2) == [1, 576], 'loader provenance version')
    require(unpack(data, 24, 1)[0] <= SOURCE_CAP, 'loader source cap')
    limits = unpack(data, 32, 5)
    require(limits[0] <= SOURCE_CAP and limits[1] <= METADATA_CAP
            and limits[2] <= 1024 * 1024 and limits[3] <= 512000000
            and limits[4] <= 120000, 'validation ceiling')
    # Five digests, one opaque nonce and four identities are data, never authority.
    require(len(data[72:264]) == 6 * 32 and len(data[264:520]) == 4 * 64, 'provenance fields')
    zero(data, 520, 576)
    return limits

def parse_runtime(data):
    require(len(data) == 512 and data[:8] == b'MIXRTB01', 'runtime envelope')
    require(unpack(data, 8, 2) == [1, 512], 'runtime version')
    flag = unpack(data, 24, 1)[0]
    require(flag in (0, 1), 'WASI presence')
    require(unpack(data, 32, 1)[0] != 0, 'owner zero')
    run = unpack(data, 40, 17)
    maxima = [SOURCE_CAP, METADATA_CAP, 16*1024*1024, 8*1024*1024, 64, 64,
              64000000, 64, 16384, 4096, 768, 128*1024*1024,
              256*1024*1024, 100000000, 1000000000, 32768, 30000]
    require(all(n <= cap for n, cap in zip(run, maxima)), 'run ceiling')
    wb = unpack(data, 176, 7)
    require(all(n <= cap for n, cap in zip(wb, [32768, 4194304, 32000000, 65536, 64, 65536, 30000])), 'WASI ceiling')
    grants = unpack(data, 232, 5)
    require(all(n in (0, 1) for n in grants), 'grant boolean')
    if flag == 0:
        zero(data, 176, 272)
    s = unpack(data, 272, 8)
    require(s[0] <= SOURCE_CAP and s[1] <= U32 and 1 <= s[2] <= 64
            and 1 <= s[3] <= 64 and s[4] == 1 and s[5] <= s[6], 'initial scalars')
    zero(data, 336, 512)
    return run, s

def parse(data):
    require(HEADER <= len(data) <= SNAPSHOT_CAP, 'snapshot extent')
    require(data[:8] == b'MIXSNB02', 'snapshot magic')
    require(unpack(data, 8, 6) == [2, HEADER, len(data), 9, 1, 1], 'snapshot header')
    require(unpack(data, 56, 1) == [34], 'resolved import count')
    extent, instructions, word_bytes, proof_bytes = unpack(data, 64, 4)
    require(extent <= SOURCE_CAP and word_bytes == 8 and proof_bytes == PROOF_BYTES, 'source layout scalars')
    for field in unpack(data, 96, 5):
        require(field <= U64, 'validation word')
    zero(data, 136, 144)
    usage = unpack(data, 144, 10)
    obs = unpack(data, 224, 20)
    option(obs[14], obs[15]); option(obs[18], obs[19])
    require(instructions <= 8000000 and obs[10] <= 256 and obs[11] <= 128 and obs[12] <= 512, 'policy observations')
    require(obs[13] <= 768 and obs[15] <= 768 and obs[16] <= 768 and obs[17] <= 65536 and obs[19] <= 65536, 'memory/table ceilings')
    require(all(n <= U32 for n in obs[13:]), 'observation u32')
    meta = unpack(data, 384, 13)
    option(meta[0], meta[1]); require(meta[2] <= U32, 'memory host maximum')
    option(meta[3], meta[4]); require(meta[5] <= U32, 'table host maximum')
    if meta[0] == 0: require(meta[2] == 0, 'absent memory')
    if meta[3] == 0: require(meta[5] == 0, 'absent table')
    option(meta[6], meta[7]); option(meta[8], meta[9])
    require(meta[10] <= extent and meta[11] <= extent and meta[12] == instructions, 'declaration offsets/instructions')
    zero(data, 488, 512)
    limits = parse_loader(data[512:1088])
    require(unpack(data, 96, 5) == limits and unpack(data, 536, 1) == [extent], 'loader/header equality')
    run, scalars = parse_runtime(data[1088:1600])
    # Source-backed direct duplicates: see equality-table.json. This is a finite
    # untrusted grammar, not exact_abi, Wasm validation or owner/custody authority.
    require(meta[0] == 1 and meta[3] == 1, 'accepted memory/table presence')
    require(meta[1] == obs[13] and meta[2] == obs[16], 'memory observation duplicate')
    require(meta[4] == obs[17], 'table observation duplicate')
    require(meta[6:8] == obs[14:16], 'memory declared maximum duplicate')
    require(meta[8:10] == obs[18:20], 'table declared maximum duplicate')
    # metadata::limits supplies the host maximum, including None -> policy cap.
    require(meta[2] == (meta[7] if meta[6] else 768)
            and meta[5] == (meta[9] if meta[8] else 65536), 'resolved host maximum')
    require(meta[1] <= meta[2] and meta[4] <= meta[5], 'minimum exceeds host maximum')
    require(scalars[0] == extent, 'runtime/source equality')
    require(scalars[1] == obs[0], 'runtime type count duplicate')
    require(scalars[2] == min(run[4], obs[3]), 'runtime slot limit derivation')
    require(scalars[3] == run[5], 'runtime pin limit duplicate')
    require(scalars[6] == run[2], 'runtime cache capacity duplicate')
    require(scalars[7] == run[3], 'runtime entry limit duplicate')
    require(unpack(data, 792, 1) == [extent], 'source identity extent duplicate')
    require(usage[9] == limits[4], 'validation deadline duplicate')
    at = HEADER; charged_total = proof_bytes; rows = []
    for sid, name, width, cap in SECTIONS:
        row = unpack(data, 1600 + sid * 64, 8)
        ident, count, capacity, native_bytes, charged, category, offset, nbytes = row
        require(ident == sid and count <= cap and count <= capacity, 'directory identity/count')
        require(native_bytes == NATIVE_BYTES[sid] and capacity <= U64 // native_bytes
                and charged == capacity * native_bytes, 'buffer charged capacity')
        require(category == (1 if sid == 0 else 2), 'buffer category')
        expected = count if sid == 0 else count * width * 8
        require(offset == at and nbytes == expected and nbytes <= len(data) - at, 'section offset/extent')
        require(charged <= (SOURCE_CAP if sid == 0 else METADATA_CAP), 'charged cap')
        if sid == 0:
            require(count == extent and capacity == count and native_bytes == 1, 'source inventory')
        else:
            charged_total += charged
            body = data[at:at+nbytes]
            for offset0 in range(0, nbytes, width*8):
                v = unpack(body, offset0, width)
                # All logical metadata coordinates originate as u32.
                require(all(x <= U32 for x in v), 'metadata u32')
                if sid == 1:
                    require(v[0] + v[1] <= obs[1] and v[2] in range(5), 'signature')
                if sid == 2: require(v[0] in range(1, 5), 'value type')
                if sid in (3, 4):
                    require(v[-1] < obs[0], 'type index')
                if sid == 3:
                    require(v[0]+v[1] <= extent and v[2]+v[3] <= extent, 'import spans')
                if sid in (4, 5, 6, 7, 8):
                    if sid == 4: span = v[:2]
                    elif sid == 5:
                        require(v[0] in range(1,5) and v[1] in (0,1), 'global type/mutability'); span=v[2:]
                    else: span=v[:2]
                    require(sum(span) <= extent, 'metadata span')
                if sid == 6: require(v[2] in range(4), 'export kind')
        rows.append(row); at += nbytes
    require(at == len(data), 'trailing bytes')
    resolved_imports = unpack(data, 2176, 34)
    require(all(1 <= v <= 34 for v in resolved_imports), 'resolved import enum')
    zero(data, 2448, HEADER)
    require(charged_total == usage[2] and charged_total <= limits[1], 'metadata reserved inventory')
    require(usage[0] == extent and usage[1] == extent and extent <= limits[0], 'source usage inventory')
    require([rows[i][1] for i in range(1,9)] == [obs[i] for i in [0,1,2,3,6,7,8,9]], 'observation lengths')
    require(obs[2] == 34 and obs[3] == obs[4] and obs[2]+obs[3] <= 80000
            and obs[5] == instructions, 'observation count relation')
    return {'directory': rows, 'usage': usage, 'observations': obs,
            'source': data[HEADER:HEADER+extent], 'resolved_imports': resolved_imports, 'total': len(data)}

def assemble_unverified_fixture(wasi=False, spare=0):
    """Synthetic data builder. Accepting this data never mints selected provenance."""
    source = bytes(range(64))
    bodies = [source, words([0,1,0]), words([1]),
              words([0,1,1,1,0]) * 34, words([2,2,0]),
              words([1,0,4,1]), words([5,1,0,0]), words([6,2,0,2]), words([8,2,0,2])]
    h = bytearray(HEADER); h[:8] = b'MIXSNB02'
    h[8:96] = words([2,HEADER,HEADER+sum(map(len,bodies)),9,1,1,34,len(source),7,8,PROOF_BYTES])
    limits = [SOURCE_CAP,METADATA_CAP,1048576,512000000,120000]
    h[96:136] = words(limits)
    obs = [1,1,34,1,1,7,1,1,1,1,1,1,1,1,0,0,768,1,1,65536]
    h[224:384] = words(obs)
    h[384:488] = words([1,1,768,1,1,65536,0,0,1,65536,0,0,7])
    h[512:520] = b'MIXLPR01'; h[520:584] = words([1,576,len(source)] + limits)
    for i in range(6): h[584+i*32:616+i*32] = bytes([i]) * 32
    # Four identities, including signed timestamp words encoded as two's complement.
    for i in range(4): h[776+i*64:840+i*64] = words([i+1,i+2,len(source) if i == 0 else i+3,0o100600,U64,0,0,0])
    h[1088:1096] = b'MIXRTB01'
    h[1096:1128] = words([1,512,int(wasi),99])
    h[1128:1264] = words([SOURCE_CAP,METADATA_CAP,16777216,8388608,1,1,64000000,64,16384,4096,768,134217728,268435456,100000000,1000000000,32768,30000])
    if wasi: h[1264:1360] = words([1,1,1,1,1,1,1]+[1,0,1,0,1])
    h[1360:1424] = words([len(source),1,1,1,1,1,16777216,8388608])
    at=HEADER; total=PROOF_BYTES
    for (sid,name,width,cap),body in zip(SECTIONS,bodies):
        count=len(body) if sid==0 else len(body)//(width*8)
        capacity=count if sid==0 else count+spare
        charged=capacity*NATIVE_BYTES[sid]
        h[1600+sid*64:1664+sid*64] = words([sid,count,capacity,NATIVE_BYTES[sid],charged,1 if sid==0 else 2,at,len(body)])
        if sid: total += charged
        at += len(body)
    h[144:224]=words([len(source),len(source),total,0,total,0,total,100,1,120000])
    h[2176:2448] = words(list(range(1,35)))
    data=bytes(h)+b''.join(bodies); parse(data); return data

def model_bounded_write(length, results):
    """Finite write-progress model, no actual output or production I/O claim."""
    require(0 <= length <= SNAPSHOT_CAP, 'model length')
    total=0; attempts=0; script=iter(results)
    while total < length:
        end=min(length,total+4096); calls=0
        while total < end:
            if calls == 32: return ('attempts', total, attempts)
            calls+=1; attempts+=1
            n=next(script, 'interrupted')
            if n == 'interrupted': continue
            if n == 'io': return ('io',total,attempts)
            if n == 0: return ('zero',total,attempts)
            if not isinstance(n,int) or not 0 < n <= end-total: return ('overreported',total,attempts)
            total+=n
    return ('complete',total,attempts)
