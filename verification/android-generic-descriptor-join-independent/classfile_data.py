"""Minimal independent class-file data reader; no JVM execution or acceptance policy."""
class Reader:
    def __init__(self, data):
        self.data, self.at = data, 0

    def take(self, size):
        result = self.data[self.at:self.at + size]
        assert len(result) == size
        self.at += size
        return result

    def number(self, size):
        return int.from_bytes(self.take(size), "big")


def parse(data):
    r = Reader(data)
    assert r.take(4) == b"\xca\xfe\xba\xbe"
    minor, major = r.number(2), r.number(2)
    cp = [None] * r.number(2)
    index = 1
    while index < len(cp):
        tag = r.number(1)
        if tag == 1:
            cp[index] = (tag, r.take(r.number(2)).decode("utf-8", "surrogateescape"))
        elif tag in (3, 4):
            cp[index] = (tag, r.take(4))
        elif tag in (5, 6):
            cp[index] = (tag, r.take(8))
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            cp[index] = (tag, r.number(2))
        elif tag in (9, 10, 11, 12, 17, 18):
            cp[index] = (tag, r.number(2), r.number(2))
        elif tag == 15:
            cp[index] = (tag, r.number(1), r.number(2))
        else:
            raise AssertionError(("unknown constant-pool tag", tag))
        index += 1

    def utf(index):
        assert cp[index][0] == 1
        return cp[index][1]

    def cls(index):
        assert cp[index][0] == 7
        return utf(cp[index][1])

    def attrs(reader):
        return [(utf(reader.number(2)), reader.take(reader.number(4))) for _ in range(reader.number(2))]

    access, name, super_index = r.number(2), cls(r.number(2)), r.number(2)
    interfaces = [cls(r.number(2)) for _ in range(r.number(2))]
    for _ in range(r.number(2)):
        r.take(6)
        attrs(r)
    methods = []
    for _ in range(r.number(2)):
        flags, method, descriptor = r.number(2), utf(r.number(2)), utf(r.number(2))
        code = None
        for key, value in attrs(r):
            if key == "Code":
                cr = Reader(value)
                cr.take(4)
                code = cr.take(cr.number(4))
        methods.append({"name": method, "descriptor": descriptor, "access": flags, "code": code})
    attrs(r)
    assert r.at == len(data)
    return {"name": name, "super": cls(super_index) if super_index else None, "interfaces": interfaces,
            "access": access, "major": major, "minor": minor, "methods": methods, "cp": cp}


def invocation_at(parsed, method, descriptor, bci):
    selected = [m for m in parsed["methods"] if m["name"] == method and m["descriptor"] == descriptor]
    assert len(selected) == 1 and selected[0]["code"] is not None
    code = selected[0]["code"]
    assert type(bci) is int and 0 <= bci < len(code)
    opcode = code[bci]
    assert opcode in (0xb6, 0xb7, 0xb8, 0xb9), ("not invocation byte", opcode, bci)
    cp = parsed["cp"]
    ref = cp[int.from_bytes(code[bci + 1:bci + 3], "big")]
    assert ref[0] in (10, 11)
    owner = cp[cp[ref[1]][1]][1]
    pair = cp[ref[2]]
    assert pair[0] == 12
    return {"opcode": opcode, "owner": owner, "name": cp[pair[1]][1], "descriptor": cp[pair[2]][1],
            "bci_bytes": code[max(0, bci - 2):bci + 5].hex()}
