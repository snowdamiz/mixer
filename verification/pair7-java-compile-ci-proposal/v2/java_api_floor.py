"""Read-only Java/javax DEX API-floor data inspection proposal. No subject import."""
from pathlib import Path
import hashlib
import struct
import xml.etree.ElementTree as ET
import zlib
CHECK = lambda: None

def dex_refs(path):
    """Read DEX IDs, not a text grep over Java. No code is executed by this parser."""
    CHECK()
    data = path.read_bytes()
    assert data[:4] == b'dex\n'
    def u4(offset):
        CHECK()
        return struct.unpack_from('<I', data, offset)[0]
    def u2(offset):
        CHECK()
        return struct.unpack_from('<H', data, offset)[0]
    decoded = 0
    def string(offset):
        nonlocal decoded
        CHECK()
        steps = 0
        while data[offset] & 128:
            steps += 1
            if steps > 4: raise ValueError("DEX string length bound")
            offset += 1
        offset += 1
        end = data.index(0,offset,min(len(data),offset+65537))
        decoded += end-offset
        if decoded > 16777216: raise ValueError("DEX decoded string byte bound")
        return data[offset:end].decode('utf-8', errors='replace')
    strings = [string(u4(u4(60) + 4*i)) for i in range(u4(56))]
    types = [strings[u4(u4(68) + 4*i)] for i in range(u4(64))]
    prototypes = []
    prototype_characters = 0
    for i in range(u4(72)):
        offset = u4(76) + 12*i
        args = u4(offset+8)
        count = 0 if not args else u4(args)
        if count > 255: raise ValueError('DEX prototype parameter bound')
        argument_types = [] if not args else [types[u2(args+4+2*j)] for j in range(count)]
        returned = types[u4(offset+4)]
        characters = 2 + len(returned) + sum(len(value) for value in argument_types)
        prototype_characters += characters
        if characters > 65536 or prototype_characters > 16777216:
            raise ValueError('DEX decoded prototype byte bound')
        prototypes.append('(' + ''.join(argument_types) + ')' + returned)
    methods = []
    for i in range(u4(88)):
        offset = u4(92) + 8*i
        owner = types[u2(offset)]
        if owner.startswith('Ljava/') or owner.startswith('Ljavax/'):
            methods.append((owner[1:-1], strings[u4(offset+4)] + prototypes[u2(offset+2)]))
    fields = []
    for i in range(u4(80)):
        offset = u4(84) + 8*i
        owner = types[u2(offset)]
        if owner.startswith('Ljava/') or owner.startswith('Ljavax/'):
            fields.append((owner[1:-1], strings[u4(offset+4)]))
    return {'methods': sorted(set(methods)), 'fields': sorted(set(fields)),
            'types': sorted(set(t.lstrip('[')[1:-1] for t in types if t.lstrip('[').startswith('Ljava/') or t.lstrip('[').startswith('Ljavax/')))}

def api_lookup(classes, owner, name, kind, visited=()):
    CHECK()
    if len(visited) > 256: raise ValueError('API inheritance traversal bound')
    if owner in visited: return None
    node = classes.get(owner)
    if node is None: return None
    floor = int(node.get('since', '1'))
    for member in node.findall(kind):
        if member.get('name') == name:
            return {'declared_owner': owner, 'api': max(floor,int(member.get('since',str(floor))))}
    if name.startswith('<init>'): return None
    for tag in ('extends','implements'):
        for parent in node.findall(tag):
            found = api_lookup(classes,parent.get('name'),name,kind,visited+(owner,))
            if found: return dict(found, api=max(found['api'],floor,int(parent.get('since','1'))))
    return None

def inspect(dex_file, api_xml, emitted_classes):
    CHECK()
    dex_file = Path(dex_file)
    if not emitted_classes or len(emitted_classes) > 1024:
        raise ValueError("Emitted class map required within bound")
    if not 112 <= dex_file.stat().st_size <= 67108864:
        raise ValueError("DEX byte bound")
    data = dex_file.read_bytes()
    CHECK()
    if data[:8] not in (b"dex\n035\0", b"dex\n037\0", b"dex\n038\0", b"dex\n039\0", b"dex\n040\0"):
        raise ValueError("Unsupported DEX version")
    if struct.unpack_from("<III", data, 32) != (len(data),112,0x12345678):
        raise ValueError("DEX header identity")
    if data[12:32] != hashlib.sha1(data[32:]).digest() or struct.unpack_from("<I",data,8)[0] != zlib.adler32(data[12:]):
        raise ValueError("DEX checksums")
    for offset, width in ((56,4),(64,4),(72,12),(80,8),(88,8),(96,32)):
        count, start = struct.unpack_from("<II",data,offset)
        if count > 200000 or start + count * width > len(data) or (count and start < 112):
            raise ValueError("DEX table bound")
    refs = dex_refs(dex_file)
    CHECK()
    tree = ET.parse(api_xml).getroot()
    CHECK()
    if tree.tag != "api":
        raise ValueError("Official API metadata root")
    classes = {node.get("name"):node for node in tree.findall("class")}
    rows, unresolved, above = [], [], []
    for kind in ("methods", "fields"):
        for owner, name in refs[kind]:
            CHECK()
            if not (owner + name).isascii():
                raise ValueError("Non-ASCII Java library ID")
            floor = api_lookup(classes,owner,name,kind[:-1])
            row = {"kind":kind[:-1],"owner":owner,"name":name,"official_sdk":floor}
            rows.append(row)
            if floor is None: unresolved.append(row)
            elif floor["api"] > 28: above.append(row)
    type_rows = []
    for owner in refs["types"]:
        CHECK()
        node = classes.get(owner)
        row = {"owner":owner,"api":None if node is None else int(node.get("since","1"))}
        type_rows.append(row)
        if row["api"] is None: unresolved.append(row)
        elif row["api"] > 28: above.append(row)
    if any(name.startswith("java/util/stream/") for name in refs["types"]) or "java/lang/Record" in refs["types"]:
        raise ValueError("Unlowered stream/Record library reference")
    def u4(offset):
        CHECK()
        return struct.unpack_from("<I",data,offset)[0]
    def text_at(offset):
        CHECK()
        steps = 0
        while data[offset] & 128:
            steps += 1
            if steps > 4: raise ValueError("DEX type length bound")
            offset += 1
        offset += 1
        return data[offset:data.index(0,offset,min(len(data),offset+65537))].decode("utf8",errors="strict")
    string_offsets = [u4(u4(60)+4*i) for i in range(u4(56))]
    types = [text_at(string_offsets[u4(u4(68)+4*i)]) for i in range(u4(64))]
    definitions = {types[u4(u4(100)+32*i)] for i in range(u4(96))}
    expected = {"L" + row["path"][:-6] + ";" for row in emitted_classes}
    if not expected.issubset(definitions):
        raise ValueError("DEX omitted an emitted class")
    return {"schema":1,"accepted":not unresolved and not above,
            "scope":"Fresh Java/javax library type/member floors only. Android references/guards and runtime linkage are outside this reader.",
            "dex_sha256":hashlib.sha256(data).hexdigest(),"java_reference_ids":refs,
            "members":rows,"types":type_rows,"unresolved":unresolved,"above28":above,
            "emitted_class_count":len(expected),"dex_definition_count":len(definitions),
            "all_emitted_classes_present":True,"runtime_accepted":False}
