#!/usr/bin/env python3
"""Fail-closed ZIP/storage/offset/ELF checks for this private APK packaging contract."""
import hashlib
import io
from pathlib import Path
import struct
import zipfile


def elf_loads(data, name):
    if len(data) < 64 or data[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('unsupported AArch64 ELF identity: ' + name)
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    if h[2] != 183 or h[3] != 1 or h[8] != 64 or h[9] != 56 or not 1 <= h[10] <= 128:
        raise ValueError('unsupported AArch64 ELF headers: ' + name)
    offset, count = h[5], h[10]
    if offset < 64 or offset + count * 56 > len(data):
        raise ValueError('out-of-bounds ELF program headers: ' + name)
    loads = []
    for index in range(count):
        kind, flags, start, vaddr, _, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', data, offset + index * 56)
        if kind == 1:
            if (align < 16384 or align & (align - 1) or start % align != vaddr % align
                    or start + filesz > len(data) or memsz < filesz):
                raise ValueError('native ELF PT_LOAD requires 16KiB-compatible alignment: ' + name)
            loads.append({'fileOffset': start, 'virtualAddress': vaddr, 'fileSize': filesz,
                          'memorySize': memsz, 'alignment': align, 'flags': flags})
    if not loads:
        raise ValueError('native ELF has no PT_LOAD: ' + name)
    return loads


def validate(data):
    """Inspect actual local headers; a central-directory offset is not data offset."""
    if isinstance(data, (str, Path)):
        data = Path(data).read_bytes()
    if not isinstance(data, bytes):
        raise TypeError('exact APK bytes or owned APK path required')
    entries = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) != len({i.filename for i in infos}) or not infos:
            raise ValueError('duplicate or empty ZIP membership')
        for info in infos:
            name = info.filename
            if (info.is_dir() or Path(name).is_absolute() or '..' in Path(name).parts
                    or info.flag_bits & 9 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                raise ValueError('unsupported ZIP entry contract: ' + name)
            start = info.header_offset
            if start < 0 or start + 30 > len(data):
                raise ValueError('local ZIP header out of bounds: ' + name)
            header = struct.unpack_from('<IHHHHHIIIHH', data, start)
            signature, _, flags, method, _, _, crc, compressed, size, name_len, extra_len = header
            offset = start + 30 + name_len + extra_len
            encoding = 'utf-8' if flags & 0x800 else 'cp437'
            local_name = data[start + 30:start + 30 + name_len].decode(encoding)
            if (signature != 0x04034B50 or flags != info.flag_bits or method != info.compress_type
                    or crc != info.CRC or compressed != info.compress_size or size != info.file_size
                    or local_name != name or offset + compressed > len(data)):
                raise ValueError('local/central ZIP metadata mismatch: ' + name)
            if name == 'resources.arsc' and (method != zipfile.ZIP_STORED or offset % 4):
                raise ValueError('resources.arsc must be ZIP_STORED and actual local data offset aligned to 4 bytes')
            if method == zipfile.ZIP_STORED and offset % 4:
                raise ValueError('stored ZIP entry actual local data offset must align to 4 bytes: ' + name)
            native = name.endswith('.so')
            if native and (not name.startswith('lib/arm64-v8a/') or method != zipfile.ZIP_STORED or offset % 16384):
                raise ValueError('native ZIP entry must be stored arm64-v8a with 16KiB local data alignment: ' + name)
            payload = archive.read(info)
            entry = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                'compressionMethod': method, 'compressedBytes': compressed,
                'localHeaderOffset': start, 'localDataOffset': offset,
                'localDataOffsetMod4': offset % 4, 'localDataOffsetMod16384': offset % 16384}
            if native:
                entry['elfLoads'] = elf_loads(payload, name)
            entries[name] = entry
    if 'resources.arsc' not in entries:
        raise ValueError('exact resources.arsc entry required')
    return {'schema': 1, 'status': 'passed-private-APK-ZIP-storage-offset-and-ELF-contract',
        'apkSHA256': hashlib.sha256(data).hexdigest(), 'entries': entries,
        'nativeLibraries': sum(name.endswith('.so') for name in entries),
        'scope': 'packaging guard only; official zipalign/signature checks and native app assertions remain separate'}
