"""Independent, offline review of the released resource binary packet.

No compiler, object tool, native code, network, Git, or subprocess is used.
The producer's code is replayed separately; core results below do not import it.
"""
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import struct
import sys

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
C = R / 'verification/swift-guarded-snapshot-resource-binary-correspondence'
RELEASE = R / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-resource-binary-frozen-release.json'
RELEASE_SHA = 'f01317a2b7d59c719bb16a71a922b6781ceeafe62adb82eeccf3c5389013e91c'
SEAL_SHA = '58f49d3bcc844678bef604bc4989e81b2bfea758b300ca3158b229a510018f1d'
TREE = '690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'
HOST = '027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
DEALLOC = '__RNvMs3_NtCs6zY7rJBZy9D_5alloc7raw_vecNtB5_11RawVecInner10deallocateCsfhX9oYWaTAx_5gimli'
U8 = '__RNvXs1_NtCs6zY7rJBZy9D_5alloc7raw_vecINtB5_6RawVechENtNtNtCsjIpoRzUjyHQ_4core3ops4drop4Drop4dropCsfhX9oYWaTAx_5gimli'
SHIM = '__RNvCsdtSMxSA38aw_7___rustc14___rust_dealloc'
OS_TABLE = '__RNvNtNtNtCsjIpoRzUjyHQ_4core2io5error12os_functions12OS_FUNCTIONS'
SETTER = '__RNvNvNtNtNtCsjIpoRzUjyHQ_4core2io5error12os_functions13set_functions19set_functions_inner'
SLOT = 'mixer_vm::experimental_swift_reactor::cache::SwiftSlot'
TYPES = [(SLOT, 136, 8), ('mixer_vm::experimental::cache::decode::Patch', 32, 8),
         ('core::option::Option<mixer_vm::experimental_swift_reactor::cache::ScanPlan>', 56, 8)]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()


def load(path):
    return json.loads(path.read_bytes())


def verified(path, row):
    if 'resolved_path' in row:
        assert str(path.resolve()) == row['resolved_path']
    assert not path.is_symlink() or str(path.resolve()) == row.get('resolved_path')
    b = path.read_bytes()
    assert len(b) == row['bytes'] and sha(b) == row['sha256'], str(path)
    return b


def verify_seal(directory, expected):
    b = (directory / 'seal.json').read_bytes()
    assert sha(b) == expected
    seal = json.loads(b)
    actual = sorted(str(p.relative_to(directory)) for p in directory.rglob('*')
                    if p.is_file() and p.name != 'seal.json' and '__pycache__' not in p.parts)
    assert actual == sorted(row['path'] for row in seal['members'])
    for row in seal['members']:
        verified(directory / row['path'], row)
    total = sum(row['bytes'] for row in seal['members'])
    assert len(actual) == seal['member_count']
    if 'total_bytes' in seal:
        assert total == seal['total_bytes']
    if 'member_bytes' in seal:
        assert total == seal['member_bytes']
    if 'tree_sha256' in seal:
        assert sha(canonical(seal['members'])) == seal['tree_sha256']
    return dict(path=str(directory.relative_to(R)), seal_sha256=expected,
                members=len(actual), bytes=total)


def read_archive(data):
    """BSD ar with strict record boundaries; independent of producer parser."""
    assert data.startswith(b'!<arch>\n')
    offset = 8
    records = []
    while offset < len(data):
        assert offset + 60 <= len(data)
        header = data[offset:offset + 60]
        assert header[58:60] == b'`\n'
        length = int(header[48:58].decode('ascii').strip())
        assert length >= 0 and offset + 60 + length <= len(data)
        start = offset + 60
        name = header[:16].decode('ascii').strip()
        if name.startswith('#1/'):
            n = int(name[3:])
            assert 0 <= n <= length
            name = data[start:start + n].rstrip(b'\0').decode('utf-8')
            start += n
        else:
            name = name.rstrip('/')
        records.append(dict(name=name, offset=start, data=data[start:offset + 60 + length]))
        offset += 60 + length + (length & 1)
    assert offset == len(data)
    return records


def parse_object(data):
    """Decode only retained 64-bit little endian ARM64 relocatable objects."""
    assert len(data) >= 32
    magic, cpu, subtype, filetype, ncmd, cmdbytes, flags, reserved = struct.unpack_from('<8I', data)
    assert (magic, cpu, filetype) == (0xfeedfacf, 0x100000c, 1)
    assert 32 + cmdbytes <= len(data)
    offset = 32
    sections = []
    symtab = None
    for _ in range(ncmd):
        cmd, size = struct.unpack_from('<II', data, offset)
        assert size >= 8 and offset + size <= 32 + cmdbytes
        if cmd == 0x19:
            assert size >= 72
            section_count = struct.unpack_from('<I', data, offset + 64)[0]
            assert size == 72 + 80 * section_count
            for i in range(section_count):
                row = struct.unpack_from('<16s16sQQ8I', data, offset + 72 + 80 * i)
                name, segment, address, length, fileoff, align, reloff, nrel, secflags, _, _, _ = row
                if fileoff:
                    assert fileoff + length <= len(data)
                assert reloff + nrel * 8 <= len(data)
                sections.append(dict(index=len(sections) + 1,
                                     name=name.rstrip(b'\0').decode(),
                                     segment=segment.rstrip(b'\0').decode(),
                                     address=address, size=length, offset=fileoff,
                                     reloff=reloff, nrel=nrel))
        elif cmd == 2:
            assert size == 24 and symtab is None
            symtab = struct.unpack_from('<4I', data, offset + 8)
        offset += size
    assert offset == 32 + cmdbytes and symtab is not None
    symboloff, nsym, stringoff, stringlen = symtab
    assert symboloff + nsym * 16 <= len(data) and stringoff + stringlen <= len(data)
    strings = data[stringoff:stringoff + stringlen]
    symbols = []
    for i in range(nsym):
        nameoff, typ, section, desc, value = struct.unpack_from('<IBBHQ', data, symboloff + 16 * i)
        assert nameoff < len(strings) and section <= len(sections)
        end = strings.index(0, nameoff)
        symbols.append(dict(name=strings[nameoff:end].decode(), type=typ, section=section,
                            value=value, index=i))
    relocations = []
    for section in sections:
        for i in range(section['nrel']):
            address, bits = struct.unpack_from('<iI', data, section['reloff'] + 8 * i)
            assert address >= 0
            index, kind = bits & 0xffffff, bits >> 28
            external = bool(bits & (1 << 27))
            if kind == 10:
                assert not external
                target = 'addend:' + str(index - (1 << 24) if index & (1 << 23) else index)
            elif external:
                assert index < len(symbols)
                target = symbols[index]['name']
            elif index == 0:
                target = 'absolute'
            else:
                assert index <= len(sections)
                target = sections[index - 1]['name']
            relocations.append(dict(section=section['index'], address=address,
                                    type=kind, target=target, external=external,
                                    pc_relative=bool(bits & (1 << 24)), width_power=(bits >> 25) & 3,
                                    record_offset=section['reloff'] + 8 * i))
    return dict(sections=sections, symbols=symbols, relocations=relocations, data=data)


def bytes_at(obj, address, count):
    rows = [s for s in obj['sections'] if s['offset'] and s['address'] <= address
            and address + count <= s['address'] + s['size']]
    assert len(rows) == 1
    row = rows[0]
    off = row['offset'] + address - row['address']
    return obj['data'][off:off + count], off, row


def symbol(obj, name):
    matches = [s for s in obj['symbols'] if s['name'] == name]
    assert len(matches) == 1
    return matches[0]


def uncomment(line):
    """LLVM ; comments, respecting quoted names and strings."""
    quoted = False
    escaped = False
    for i, char in enumerate(line):
        if char == ';' and not quoted:
            return line[:i].strip()
        if char == '"' and not escaped:
            quoted = not quoted
        escaped = char == '\\' and not escaped
    return line.strip()


def active(body):
    return [s for line in body.splitlines() if (s := uncomment(line))]


def call_symbols(body):
    return [m[1] for line in active(body)
            if (m := re.search(r'\b(?:call|invoke)\b[^@\n]*@([^ (]+)\(', line))]


def blocks(body):
    result = {}
    current = None
    for line in active(body):
        if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*:', line):
            current = line[:-1]
            assert current not in result
            result[current] = []
        elif current and line != '}':
            result[current].append(line)
    return result


def check_ir_semantics(selected):
    """Active operations and connected operands, rather than body substrings."""
    def body(name):
        return selected[name]['body']
    def sym(name):
        return selected[name]['symbol']
    for ty, size, align in TYPES:
        rv = 'alloc::raw_vec::RawVec<' + ty + '>'
        vec = 'alloc::vec::Vec<' + ty + '>'
        rawdrop = '<' + rv + ' as core::ops::drop::Drop>::drop'
        lines = active(body(rawdrop))
        assert [s for s in lines if ' call ' in ' ' + s] == [
            'call void @' + DEALLOC[1:] + f'(ptr align 8 %self, i64 {align}, i64 {size})']
        assert lines[-2:] == ['ret void', '}']
        vd = '<' + vec + ' as core::ops::drop::Drop>::drop'
        vl = active(body(vd))
        assert '%0 = getelementptr inbounds i8, ptr %self, i64 8' in vl
        assert '%_5 = load ptr, ptr %0, align 8' in vl
        assert '%1 = getelementptr inbounds i8, ptr %self, i64 16' in vl
        assert '%len = load i64, ptr %1, align 8' in vl
        glue = body('core::ptr::drop_glue::<' + vec + '>')
        assert sym(vd) in call_symbols(glue)
        rvglue = 'core::ptr::drop_glue::<' + rv + '>'
        assert sym(rvglue) in call_symbols(glue)
        assert call_symbols(body(rvglue)) == [sym(rawdrop)]
        if ty == SLOT:
            sl = 'core::ptr::drop_glue::<[' + ty + ']>'
            assert call_symbols(body(vd)) == [sym(sl)]
            assert ('call void @' + sym(sl) + '(ptr align 8 %_5, i64 %len)') in vl
            lines = active(body(sl))
            for expected in ['store i64 0, ptr %_3, align 8', '%_7 = icmp eq i64 %1, %_1.1',
                             'br i1 %_7, label %bb1, label %bb5', '%4 = add i64 %3, 1',
                             'store i64 %4, ptr %_3, align 8', '%_5 = icmp eq i64 %5, %_1.1',
                             'br i1 %_5, label %bb2, label %bb3', '%12 = add i64 %11, 1',
                             'store i64 %12, ptr %_3, align 8',
                             'to label %bb6 unwind label %cleanup',
                             'to label %bb4 unwind label %terminate']:
                assert expected in lines, expected
            sb = blocks(body(sl))
            assert sb['start'][-1] == 'br label %bb6'
            assert sb['bb6'] == ['%1 = load i64, ptr %_3, align 8',
                                  '%_7 = icmp eq i64 %1, %_1.1',
                                  'br i1 %_7, label %bb1, label %bb5']
            assert sb['bb4'] == ['%5 = load i64, ptr %_3, align 8',
                                  '%_5 = icmp eq i64 %5, %_1.1',
                                  'br i1 %_5, label %bb2, label %bb3']
            assert sb['bb1'] == ['ret void']
            assert sb['bb5'][-1] == 'to label %bb6 unwind label %cleanup'
            assert sb['cleanup'][-1] == 'br label %bb4'
            assert sb['bb3'][-1] == 'to label %bb4 unwind label %terminate'
            assert sb['bb2'][-1].startswith('resume ')
            assert sb['terminate'][-1] == 'unreachable'
            assert sum('getelementptr inbounds nuw %"experimental_swift_reactor::cache::SwiftSlot"' in s
                       for s in lines) == 2
            for suffix in ['%2', '%10']:
                assert any(s.endswith('ptr %_1.0, i64 ' + suffix) for s in lines)
            # Independently walk active drop-glue edges, including exceptional edges.
            bysymbol = {r['symbol']: n for n, r in selected.items()}
            todo = [sym('core::ptr::drop_glue::<' + ty + '>')]
            seen = set()
            while todo:
                s = todo.pop()
                if s in seen or s not in bysymbol:
                    continue
                seen.add(s)
                n = bysymbol[s]
                if n.startswith('core::ptr::drop_glue::<'):
                    todo += call_symbols(body(n))
            for nested in ['mixer_vm::Type', 'mixer_vm::experimental::cache::DecodedInstruction', 'u32']:
                assert sym('core::ptr::drop_glue::<alloc::vec::Vec<' + nested + '>>') in seen
        else:
            assert call_symbols(body(vd)) == []
    chain = ['std::fs::File', 'std::sys::fs::unix::File', 'std::sys::fd::unix::FileDesc',
             'std::os::fd::owned::OwnedFd']
    for a, b in zip(chain, chain[1:]):
        assert call_symbols(body('core::ptr::drop_glue::<' + a + '>')) == [
            sym('core::ptr::drop_glue::<' + b + '>')]
    owned = '<std::os::fd::owned::OwnedFd as core::ops::drop::Drop>::drop'
    assert call_symbols(body('core::ptr::drop_glue::<' + chain[-1] + '>')) == [sym(owned)]
    pre = 'std::sys::fs::unix::debug_assert_fd_is_open'
    assert call_symbols(body(owned)) == [sym(pre), 'close']
    ol = active(body(owned))
    assert '%self1 = load i32, ptr %self, align 4' in ol
    assert 'call void @' + sym(pre) + '(i32 %self1) #29' in ol
    assert '%self2 = load i32, ptr %self, align 4' in ol
    assert '%_5 = call i32 @close(i32 %self2) #36' in ol
    assert not any('%_5' in s for s in ol if not s.startswith('%_5 ='))
    pl = active(body(pre))
    expected = ['%_2 = call i32 (i32, i32, ...) @fcntl(i32 %fd, i32 1) #36',
                '%0 = icmp eq i32 %_2, -1', 'br i1 %0, label %bb3, label %bb8',
                '%_9 = call ptr @__error() #36', '%_3 = load i32, ptr %_9, align 4',
                '%1 = icmp eq i32 %_3, 9', 'br i1 %1, label %bb4, label %bb7',
                'call void @_RNvNtCs1SSuMAdGM58_3std7process5abort() #34', 'unreachable']
    assert all(s in pl for s in expected)
    pb = blocks(body(pre))
    assert pb['start'][-1] == 'br label %bb1'
    assert pb['bb1'] == expected[:3]
    assert pb['bb3'] == expected[3:7]
    assert pb['bb4'][-2:] == expected[7:]
    assert pb['bb8'] == ['br label %bb9'] and pb['bb7'] == ['br label %bb9']
    assert pb['bb9'] == ['br label %bb10'] and pb['bb10'] == ['ret void']
    assert len([s for s in call_symbols(body(pre)) if s == 'fcntl']) == 1
    assert len([s for s in call_symbols(body(pre)) if s == '__error']) == 1
    # Retain rather than hide the formatting/drop work on the abort branch.
    assert any('write_fmt' in s for s in call_symbols(body(pre)))
    assert any('drop_glue' in s for s in call_symbols(body(pre)))
    return dict(selected_functions=len(selected), vector_layouts=[dict(type=t, size=s, alignment=a) for t, s, a in TYPES],
                File_precheck_format_and_Result_drop_edges_are_also_present=True,
                live_slice_normal_and_unwind=True, close_result_ignored=True)


def sign(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def rawvec_machine(obj, start, cap, size, align, ptr=0x2000, changed=None, relchanged=None):
    """Small fail-closed ARM64 byte interpreter. No native execution."""
    changed, relchanged = changed or {}, relchanged or {}
    regs = [0] * 31
    regs[:3] = [0x1000, align, size]
    sp = 0x10000
    mem = {0x1000: cap, 0x1008: ptr}
    pc = symbol(obj, start)['value']
    branch = {obj['sections'][r['section'] - 1]['address'] + r['address']: r['target']
              for r in obj['relocations'] if r['type'] == 2}
    branch.update(relchanged)
    trace = []
    def readreg(n, stack=False):
        return (sp if stack else 0) if n == 31 else regs[n]
    for _ in range(64):
        word = changed.get(pc, int.from_bytes(bytes_at(obj, pc, 4)[0], 'little'))
        trace.append(pc)
        rd, rn, rm = word & 31, (word >> 5) & 31, (word >> 16) & 31
        if word == 0xd65f03c0:
            return dict(request=None, trace=trace)
        if word & 0xff800000 in (0x91000000, 0xd1000000):
            assert not (word & (1 << 22))
            imm = (word >> 10) & 0xfff
            v = readreg(rn, True) + (-imm if word & (1 << 30) else imm)
            if rd == 31:
                sp = v
            else:
                regs[rd] = v & ((1 << 64) - 1)
        elif word & 0xffc00000 in (0xf9400000, 0xf9000000):
            address = readreg(rn, True) + ((word >> 10) & 0xfff) * 8
            if word & (1 << 22):
                value = mem[address]
                if rd != 31:
                    regs[rd] = value
            else:
                mem[address] = readreg(rd)
        elif word & 0xffe0fc00 == 0x9b007c00:
            if rd != 31:
                regs[rd] = (readreg(rn) * readreg(rm)) & ((1 << 64) - 1)
        elif word & 0x7f800000 == 0x52800000:
            assert not ((word >> 21) & 3)
            if rd != 31:
                regs[rd] = (word >> 5) & 0xffff
        elif word & 0xff000000 == 0xb4000000:
            if readreg(rd) == 0:
                pc += sign((word >> 5) & 0x7ffff, 19) * 4
                continue
        elif word & 0xfc000000 == 0x14000000:
            target = branch.get(pc)
            if target == SHIM:
                return dict(request=regs[:3], trace=trace)
            if target is not None:
                assert target == DEALLOC
                pc = symbol(obj, target)['value']
            else:
                pc += sign(word & 0x3ffffff, 26) * 4
            continue
        else:
            raise AssertionError('unsupported ARM64 word ' + hex(word))
        pc += 4
    raise AssertionError('more than 64 steps')


def os_constructor_words(row):
    """Decode the actual errno load + TAG_OS + ORR shifted-register operands."""
    instructions = row['instructions']
    candidates = [i for i, r in enumerate(instructions) if r['word'] == 0x52800048]
    assert len(candidates) == 1
    i = candidates[0]
    assert i + 1 < len(instructions)
    w = instructions[i + 1]['word']
    # ORR Xd, X8, Xerrno, LSL #32 (not a textual assembly annotation).
    assert w & 0xffe0fc00 == 0xaa008000
    assert (w >> 5) & 31 == 8
    errno_reg = (w >> 16) & 31
    errno_loads = [r for r in instructions[:i] if r['word'] & 0xffffffe0 == 0xb9800000]
    assert len(errno_loads) == 1 and errno_loads[0]['word'] & 31 == errno_reg
    assert errno_reg in (19, 20) and (w & 31) in (0, 1, 9)
    return dict(tag=2, tag_register=8, errno_register=errno_reg,
                result_register=w & 31, shift=32,
                tag_address=instructions[i]['address'], orr_address=instructions[i + 1]['address'])


def main():
    assert sha(RELEASE.read_bytes()) == RELEASE_SHA
    released = load(RELEASE)
    assert released['seal_sha256'] == SEAL_SHA and not released['acceptance']
    custody = verify_seal(C, SEAL_SHA)
    assert (custody['members'], custody['bytes']) == (116, 2151908)
    report = load(C / 'correspondence.json')
    manifest = load(C / 'compiled-manifest.json')
    original = manifest['source_manifest']['members']
    assert len(original) == 146 and sha(canonical(original)) == TREE
    source_ref = manifest['source_reference_map']
    assert [(r['path'], r['bytes'], r['sha256']) for r in source_ref] == [
        (r['path'], r['bytes'], r['sha256']) for r in original]
    compiled = {r['path']: r for r in manifest['compiled_source_members']}
    assert len(compiled) == 146 and set(compiled) == {r['path'] for r in original}
    assert sha(canonical(manifest['compiled_source_members'])) == manifest['compiled_tree_sha256']
    changed = []
    for row in source_ref:
        b = verified(R / row['source'], row)
        if row['path'] in manifest['additions']:
            extra = verified(C / (Path(row['path']).stem + '-append.inc.rs'), manifest['additions'][row['path']])
            assert extra.startswith(b'\n')
            b += extra
            changed.append(row['path'])
        assert len(b) == compiled[row['path']]['bytes'] and sha(b) == compiled[row['path']]['sha256']
    assert len(changed) == 2
    appends = (C / 'cache-append.inc.rs').read_text() + (C / 'decode-append.inc.rs').read_text()
    assert appends.count('#[used]') == 4 and appends.count('static RESOURCE_BINARY_DROP_') == 4
    assert appends.count('#[cfg(mixer_bootstrap_one_fixture_v1)]') == 4
    host = manifest['host_support']
    assert len(host['members']) == 11 and sha(canonical(host['members'])) == HOST
    for row in host['members']:
        verified(R / 'verification/swift-real-profile-loader-binding/host' / row['path'], row)
    binding = load(C / 'binding.json')
    receipt = load(C / 'compiler-receipt.json')
    assert binding['source_tree_sha256'] == TREE and binding['host_tree_sha256'] == HOST
    def counted(data):
        n, = struct.unpack_from('<Q', data)
        assert n <= 64
        offset, values = 8, []
        for _ in range(n):
            length, = struct.unpack_from('<Q', data, offset)
            offset += 8
            assert length < 4096 and offset + length <= len(data)
            value = data[offset:offset + length]
            assert b'\0' not in value
            values.append(value.decode())
            offset += length
        assert offset == len(data)
        return values
    assert counted((C / 'argv.bin').read_bytes()) == receipt['argv']
    assert dict(s.split('=', 1) for s in counted((C / 'environment.bin').read_bytes())) == {
        k: v for k, v in receipt['environment'].items() if k not in binding['compile_identity_keys']}
    identities = binding['compile_identity_keys']
    for key, name in [('MIXER_LOADER_COMMAND_SHA256', 'argv.bin'), ('MIXER_LOADER_COMPILE_ENV_SHA256', 'environment.bin'),
                      ('MIXER_LOADER_MANIFEST_SHA256', 'compiled-manifest.json'), ('MIXER_LOADER_COMPILER_VERSION_SHA256', 'compiler-version.stdout')]:
        assert sha((C / name).read_bytes()) == identities[key] == receipt['environment'][key]
    assert sha(Path(receipt['argv'][0]).read_bytes()) == identities['MIXER_LOADER_COMPILER_SHA256']
    assert [s for s in receipt['argv'] if s.startswith('--emit=')] == [
        '--emit=llvm-ir=' + str(C / 'compiler-owned-work/source146.ll')]
    assert all(flag in receipt['argv'] for flag in ['opt-level=0', 'codegen-units=1', 'overflow-checks=yes', 'panic=unwind', '-Zmir-opt-level=0', 'aarch64-apple-darwin'])
    assert receipt['exit_code'] == 0 and receipt['direct_child_waited'] and receipt['owned_group_absent']
    assert not receipt['timed_out'] and receipt['elapsed_seconds'] < 60
    assert not (C / 'compiler-owned-work').exists()
    source_bindings = load(C / 'source-bindings.json')
    inherited = source_bindings['inherited_source_semantic_review']
    verified(R / inherited['path'], inherited)
    for row in source_bindings['proof_spans']:
        b = (R / row['path']).read_bytes()
        assert sha(b) == row['file_sha256']
        assert ''.join(b.decode().splitlines(keepends=True)[row['start'] - 1:row['end']]) == row['source']
    acceptance_path = R / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-resource-cost-host-acceptance.json'
    assert sha(acceptance_path.read_bytes()) == '854c90f7824676cec2483571d5de4fce27965758e7e583186fa2361d965a118f'
    acceptance = load(acceptance_path)
    dependencies = []
    for row in report['packets'] + [acceptance['producer']]:
        dependencies.append(verify_seal(R / row['path'], row['seal_sha256']))
        assert dependencies[-1]['members'] == row['members'] and dependencies[-1]['bytes'] == row['bytes']
    verified(R / acceptance['selected_review']['path'], acceptance['selected_review'])
    assert load(C / 'review.json')['inherited_prices_unchanged'] == acceptance['accepted_prices']
    llvm = gzip.decompress((C / 'source146.ll.gz').read_bytes())
    arch = load(C / 'source146.ll-archive.json')
    assert len(llvm) == arch['raw_bytes'] and sha(llvm) == arch['raw_sha256']
    lines = llvm.decode().splitlines(keepends=True)
    ir = report['LLVM_functions']
    for name, row in ir.items():
        excerpt = ''.join(lines[row['start_line'] - 1:row['end_line']])
        assert excerpt == row['body'] and sha(excerpt.encode()) == row['sha256']
        definitions = [s for s in excerpt.splitlines() if s.startswith('define ')]
        assert len(definitions) == 1 and ('@' + row['symbol'] + '(') in definitions[0]
    assert len(ir) == 29
    ir_result = check_ir_semantics(ir)
    # Tie all four append-only #[used] pointers to emitted retention globals and
    # their std::mem::drop bodies, not merely to a source comment or declaration.
    retention = {}
    for line in lines:
        m = re.fullmatch(r'@([^ ]*RESOURCE_BINARY_DROP_[^ ]*) = constant ptr @([^,]+), align 8, !guid ![0-9]+\n', line)
        if m:
            assert m[1] not in retention
            retention[m[1]] = m[2]
    assert len(retention) == 4
    used = [line for line in lines if line.startswith('@llvm.used =')]
    assert len(used) == 1 and '[4 x ptr]' in used[0]
    assert set(re.findall(r'ptr @([^,\] ]+)', used[0])) == set(retention)
    pointer_edges = []
    expected_drops = ['core::ptr::drop_glue::<std::fs::File>'] + [
        'core::ptr::drop_glue::<alloc::vec::Vec<' + t + '>>' for t, _, _ in TYPES]
    for global_name, target in retention.items():
        start = next(i for i, line in enumerate(lines) if line.startswith('define ') and '@' + target + '(' in line)
        end = next(i for i in range(start + 1, len(lines)) if lines[i] == '}\n')
        emitted_calls = call_symbols(''.join(lines[start:end + 1]))
        matched = [name for name in expected_drops if ir[name]['symbol'] in emitted_calls]
        assert len(matched) == 1
        pointer_edges.append(dict(global_name=global_name, std_mem_drop_symbol=target, target_glue=matched[0]))
    assert set(row['target_glue'] for row in pointer_edges) == set(expected_drops)
    archives = load(C / 'installed-inputs.json')['archives'] | load(C / 'additional-installed-inputs.json')['archives']
    parsed, archive_results = {}, {}
    for name, row in archives.items():
        data = verified(Path(row['path']), row)
        objects = [r for r in read_archive(data) if r['name'].endswith('.o')]
        assert len(objects) == 1
        obj = objects[0]
        parsed[name] = parse_object(obj['data'])
        archive_results[name] = dict(archive_sha256=sha(data), member=obj['name'],
                                     member_offset=obj['offset'], member_sha256=sha(obj['data']))
    native = report['native_functions']
    instruction_count, relocation_count, padding_nops = 0, 0, 0
    native_results = []
    for name, row in native.items():
        obj = parsed[row['archive']]
        s = symbol(obj, name)
        assert s['value'] == row['address']
        assert row['archive_member_sha256'] == archive_results[row['archive']]['member_sha256']
        ins = row['instructions']
        assert [i['address'] for i in ins] == list(range(row['address'], ins[-1]['address'] + 4, 4))
        raw = b''.join(bytes_at(obj, i['address'], 4)[0] for i in ins)
        assert raw.hex() == row['instruction_bytes_hex'] and sha(raw) == row['instruction_bytes_sha256']
        for i in ins:
            b, off, section = bytes_at(obj, i['address'], 4)
            assert int.from_bytes(b, 'little') == i['word'] and off == i['object_offset']
            assert section['index'] == s['section']
            instruction_count += 1
            padding_nops += i['word'] == 0xd503201f
        for rel in row['relocations']:
            matches = [r for r in obj['relocations'] if r['record_offset'] == rel['record_offset']]
            assert len(matches) == 1 and all(rel[k] == v for k, v in matches[0].items())
            sec = obj['sections'][rel['section'] - 1]
            assert rel['instruction_address'] == sec['address'] + rel['address']
            assert ins[0]['address'] <= rel['instruction_address'] <= ins[-1]['address']
            relocation_count += 1
        # The report must include every relocation in the emitted instruction interval.
        complete = [r['record_offset'] for r in obj['relocations'] if r['section'] == s['section']
                    and ins[0]['address'] <= obj['sections'][s['section'] - 1]['address'] + r['address'] <= ins[-1]['address']]
        assert sorted(complete) == sorted(r['record_offset'] for r in row['relocations'])
        # Retained objdump output is independently checked for instruction/relocation census.
        output = gzip.decompress((C / row['output']).read_bytes()).decode()
        header = format(row['address'], 'x') + ' <' + name + '>:'
        # llvm emits padded address widths; compare numerical block headers instead.
        match = next(m for m in re.finditer(r'^([0-9a-f]+) <([^>]+)>:\n', output, re.M)
                     if int(m[1], 16) == row['address'] and m[2] == name)
        nexthead = re.search(r'^([0-9a-f]+) <([^>]+)>:\n', output[match.end():], re.M)
        block = output[match.end():match.end() + nexthead.start()] if nexthead else output[match.end():]
        emitted = [(int(m[1], 16), int(m[2], 16)) for m in re.finditer(r'^\s*([0-9a-f]+): ([0-9a-f]{8})\s+', block, re.M)]
        assert emitted == [(i['address'], i['word']) for i in ins]
        assert len(re.findall(r'ARM64_RELOC_[A-Z0-9_]+', block)) == len(row['relocations'])
        native_results.append(dict(symbol=name, archive=row['archive'], instructions=len(ins), relocations=len(row['relocations'])))
    assert len(native) == 16 and instruction_count + relocation_count == 539
    assert symbol(parsed['gimli'], DEALLOC)['section'] != 0 and symbol(parsed['gimli'], U8)['section'] != 0
    assert any(('declare ' in line and '@' + DEALLOC[1:] + '(' in line) for line in lines)
    assert any(('declare ' in line and '@' + U8[1:] + '(' in line) for line in lines)
    cases = []
    for size, align in [(0, 1), (1, 1), (4, 4), (32, 8), (40, 8), (56, 8), (136, 8)]:
        for cap in [0, 1, 2, 7, 64, 65536]:
            got = rawvec_machine(parsed['gimli'], DEALLOC, cap, size, align)
            expect = [0x2000, cap * size, align] if cap and size else None
            assert got['request'] == expect
            cases.append(dict(capacity=cap, element_size=size, alignment=align, expected=expect, **got))
    for cap in [0, 1, 17, 65536]:
        got = rawvec_machine(parsed['gimli'], U8, cap, 999, 999)
        assert got['request'] == ([0x2000, cap, 1] if cap else None)
        cases.append(dict(capacity=cap, source='u8 wrapper', **got))
    # Additional finite probes within valid nonoverflowing layouts, varying the data pointer.
    additional = []
    for size, align in [(136, 8), (56, 8), (32, 8), (4, 4), (1, 1)]:
        for cap in [3, 19, 255, 4095, ((1 << 63) - 1) // size]:
            for ptr in [0x8000, 0x12000]:
                got = rawvec_machine(parsed['gimli'], DEALLOC, cap, size, align, ptr)
                assert got['request'] == [ptr, cap * size, align]
                additional.append(dict(capacity=cap, element_size=size, alignment=align, **got))
    close = next(r for n, r in native.items() if 'drop_glue' in n and 'FileDesc' in n)
    assert [i['word'] for i in close['instructions']] == [0xb9400000, 0x14000000]
    assert [r['target'] for r in close['relocations']] == ['_close']
    os_results = []
    for name, row in native.items():
        if row['archive'] == 'std' and any(s in name for s in ['4File4read', 'Read4read', '4File8read_buf', '4File8metadata', 'Write5write', 'Seek15stream_position']):
            edges = [r['target'] for r in row['relocations']]
            assert '___error' in edges and OS_TABLE in edges and SETTER in edges
            assert not any('alloc' in s or 'Custom' in s for s in edges)
            os_results.append(dict(symbol=name, **os_constructor_words(row)))
    assert len(os_results) == 6
    setter = native[SETTER]
    assert [i['word'] for i in setter['instructions']] == [0x90000008, 0xf9000100, 0xd65f03c0]
    assert [r['target'] for r in setter['relocations']] == [OS_TABLE, OS_TABLE]
    for fragment, target in [('std7process5abort', 'abort_internal'), ('abort_internal', '_abort')]:
        row = next(r for n, r in native.items() if fragment in n)
        assert any(target in rel['target'] for rel in row['relocations'])
    static = report['static_File_error']
    obj = parsed['std']
    static_symbol = symbol(obj, static['symbol']['name'])
    data, off, section = bytes_at(obj, static_symbol['value'], 24)
    ptrslot, length, kind = struct.unpack('<3Q', data)
    assert ptrslot == 0 and (length, kind) == (42, 20) and static_symbol['value'] & 3 == 0
    relocation = [r for r in obj['relocations'] if r['section'] == section['index']
                  and r['address'] == static_symbol['value'] - section['address']]
    assert len(relocation) == 1 and relocation[0]['target'] == static['message_symbol']
    assert relocation[0]['external'] and relocation[0]['type'] == 0 and relocation[0]['width_power'] == 3
    msgsym = symbol(obj, static['message_symbol'])
    message = bytes_at(obj, msgsym['value'], length)[0]
    assert message == b'file name contained an unexpected NUL byte'
    helper = next(r for n, r in native.items() if 'small_c_string24run_with_cstr_allocating' in n)
    hi = {i['address']: i['word'] for i in helper['instructions']}
    hrefs = [r for r in helper['relocations'] if r['target'] == static_symbol['name']]
    assert len(hrefs) == 2 and [r['type'] for r in hrefs] == [3, 4]
    base = hrefs[0]['instruction_address']
    assert [hi[base + j] for j in [0, 4, 8, 12, 16]] == [0x90000008, 0x91000108, 0xf90006c8, 0x52800028, 0xb90002c8]
    # Result discriminant 1 and Error pointer tag 0 are distinct representations.
    static_result = dict(message=message.decode(), pointer_tag=static_symbol['value'] & 3,
                         Result_discriminant=1, ErrorKind_discriminant=kind,
                         callback_path_not_closed=True)
    return dict(schema=1, status='supports-selected-frozen-correspondence-with-explicit-pending-clauses',
                custody=custody, dependencies=dependencies, source_tree_sha256=TREE, host_tree_sha256=HOST,
                compiled_tree_sha256=manifest['compiled_tree_sha256'], source_members=146,
                append_only_members=changed, used_drop_pointers=4, retained_pointer_edges=pointer_edges,
                compiler_identity=identities, compiler_context='aarch64-apple-darwin opt0/codegen1 LLVM-only query; no link/run',
                compiler_replay_performed=False, LLVM=ir_result, native_archives=archive_results,
                native_functions=native_results, instruction_records=instruction_count,
                relocation_records=relocation_count, combined_checks=instruction_count + relocation_count,
                nop_instruction_records=padding_nops, dataflow_cases=cases, additional_dataflow_cases=additional,
                native_Os_constructors=os_results, static_error=static_result,
                source_prices=acceptance['accepted_prices'], prices_changed=False,
                acceptance_selected_here=False, compiled_std_correspondence_complete=False,
                actual_caller_build_session_executable_bound=False,
                generic_File_open_options_stack_path_closure_complete=False,
                unit='Inherited source/aggregate/destructor interface plus native/requested-backing bytes.',
                no_private_allocator_kernel_CPU_RSS_time_stack_or_successful_cleanup_claim=True,
                native_UI_capture_simulator_emulator_runtime='paused; none started',
                product_runtime_or_OTA_or_GA=False), dict(ir=ir, native=native, parsed=parsed)


if __name__ == '__main__':
    result, _ = main()
    if '--write' in sys.argv:
        (D / 'audit.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    else:
        assert result == load(D / 'audit.json')
    print(json.dumps(dict(status='passed', source_members=146, LLVM_functions=result['LLVM']['selected_functions'],
                          native_functions=len(result['native_functions']), native_checks=result['combined_checks'],
                          dataflow_cases=len(result['dataflow_cases']), additional_cases=len(result['additional_dataflow_cases']))))
