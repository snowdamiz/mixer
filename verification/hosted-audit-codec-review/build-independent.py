#!/usr/bin/env python3
"""Independent schema specimens: no producer encoder/oracle/fixture import."""
import copy
import hashlib
import json
import pathlib
import uuid

HERE = pathlib.Path(__file__).resolve().parent


def cbor(value):
    if value is None:
        return b"\xf6"
    if type(value) is int:
        major, size, payload = 0, value, b""
    elif type(value) in (bytes, str):
        payload = value if type(value) is bytes else value.encode("utf-8")
        major, size = (2 if type(value) is bytes else 3), len(payload)
    elif type(value) is list:
        major, size, payload = 4, len(value), b"".join(map(cbor, value))
    else:
        raise TypeError(type(value))
    assert 0 <= size < 2**64
    if size <= 23:
        header = bytes([(major << 5) | size])
    else:
        width = next(n for n in (1, 2, 4, 8) if size < 1 << (8 * n))
        header = bytes([(major << 5) | {1: 24, 2: 25, 4: 26, 8: 27}[width]]) + size.to_bytes(width, "big")
    return header + payload


def domain(name, value):
    return hashlib.sha256(name.encode("ascii") + b"\x00" + value).digest()


def pg(value):
    if isinstance(value, dict):
        keys = sorted(value, key=lambda k: (len(k.encode()), k.encode()))
        return "{" + ", ".join(pg(k) + ": " + pg(value[k]) for k in keys) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(map(pg, value)) + "]"
    return json.dumps(value, ensure_ascii=False)


def new_event(organization="review-org", project="review-project"):
    # Build a typed event first; display is a projection, never an encoder input.
    state = domain("mixer.hosted.state.v1", cbor([1, organization, project]))
    return [1, 1, [organization, project],
            [uuid.UUID(int=0xA1).bytes, "human", uuid.UUID(int=0xB2).bytes,
             "independent\nprofile", 1, bytes(range(32)), bytes(reversed(range(32))),
             b"\x33" * 32, b"\x44" * 32, uuid.UUID(int=0xC3).bytes, 100],
            [100, 1, 2, 3, 4, 5, [[uuid.UUID(int=0xD4).bytes, "developer", 6]]],
            [organization, project, "review-app", "production", "android", b"\x55" * 32, b"\x66" * 32],
            "artifact.upload", "\b\t\n\f\r\x01\x1f\\\"é水😀/\u2028\u2029", uuid.UUID(int=0xE5).bytes,
            None, 100, state, b"\x77" * 32, b"", b"\x88" * 32]


def display(event):
    a, q, t = event[3:6]
    return {"audit_schema": event[0], "id": str(event[1]), "tenant": event[2],
            "actor": [str(uuid.UUID(bytes=a[0])), a[1], str(uuid.UUID(bytes=a[2])), a[3], str(a[4]),
                      *[x.hex() for x in a[5:9]], str(uuid.UUID(bytes=a[9])), str(a[10])],
            "decision": [*[str(x) for x in q[:6]], [[str(uuid.UUID(bytes=m[0])), m[1], str(m[2])] for m in q[6]]],
            "target": [*t[:5], t[5].hex(), t[6].hex()], "action": event[6], "reason": event[7],
            "request_id": str(uuid.UUID(bytes=event[8])), "source_ip": event[9], "recorded_at": str(event[10]),
            "previous_state": event[11].hex(), "current_state": event[12].hex(), "previous_hash": event[13].hex(),
            "request_hash": event[14].hex(), "hash": domain("mixer.hosted.audit.v1", cbor(event)).hex()}


def row(event, d):
    return {"organization": event[2][0], "project": event[2][1], "event_id": event[1],
            "event_cbor": cbor(event).hex(), "event_hash": domain("mixer.hosted.audit.v1", cbor(event)).hex(), "previous_hash": event[13].hex(),
            "previous_state": event[11].hex(), "current_state": event[12].hex(), "display_json": d,
            "display_bytes": pg(d).encode().hex()}


def set_path(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def main():
    # Literal small golden encodings independently check all integer-width branches.
    for value, expected in [(0, "00"), (23, "17"), (24, "1818"), (255, "18ff"),
                            (256, "190100"), (65535, "19ffff"), (65536, "1a00010000"),
                            (2**32, "1b0000000100000000"), (2**64 - 1, "1bffffffffffffffff")]:
        assert cbor(value).hex() == expected
    assert cbor([None, b"x", "x"]).hex() == "83f641786178"
    cases = []

    def add(label, event=None, accepted=True, row_accepted=None, display_mutation=None):
        event = copy.deepcopy(event if event is not None else new_event())
        d = display(event)
        if display_mutation:
            set_path(d, display_mutation[0], display_mutation[1])
        cases.append({"label": label, "accepted": accepted,
                      "row_accepted": accepted if row_accepted is None else row_accepted,
                      "row": row(event, d)})

    def change(label, path, value, accepted=True, row_accepted=None):
        event = new_event()
        set_path(event, path, value)
        add(label, event, accepted, row_accepted)

    add("independent escaping and typed-byte golden")
    for n in (23, 24, 255, 256, 65535, 65536, 2**32 - 1, 2**32, 2**64 - 1):
        e = new_event(); e[1] = n; e[13] = b"\x99" * 32
        add("uint header transition " + str(n), e)
    for n in (0, 30, 45, 2**53 - 1):
        e = new_event(); e[3][10] = n; e[4][0] = n; e[10] = n
        add("safe time boundary " + str(n), e)
    for delta in (-46, -45, 30, 31):
        change("authentication tolerance " + str(delta), [3, 10], 100 + delta, delta in (-45, 30))
    change("recorded before decision", [10], 99, False)
    change("recorded may precede completion", [3, 10], 130)
    for role in ("owner", "administrator", "developer", "release_manager", "billing_manager", "viewer"):
        e = new_event()
        e[4][6] = [[uuid.UUID(int=1).bytes, "developer", 1], [uuid.UUID(int=2).bytes, role, 2**63 - 1]]
        add("role vocabulary with independent uploader " + role, e)
    for count in (0, 1, 64, 65):
        e = new_event(); e[4][6] = [[uuid.UUID(int=n + 1).bytes, "developer", 1] for n in range(count)]
        add("unique ordered memberships " + str(count), e, count in (1, 64))
    for index in range(1, 6):
        change("revision maximum " + str(index), [4, index], 2**63 - 1)
        change("revision overflow " + str(index), [4, index], 2**63, False)
    for length in (0, 128, 129):
        change("profile byte limit " + str(length), [3, 3], "x" * length, length == 128)
    change("profile multibyte maximum", [3, 3], "😀" * 32)
    change("profile multibyte overflow", [3, 3], "😀" * 33, False)
    for length in (0, 512, 513):
        change("reason byte limit " + str(length), [7], "\x01" * length, length <= 512)
    change("reason multibyte maximum", [7], "😀" * 128)
    change("reason multibyte overflow", [7], "😀" * 129, False)
    for value in ("127.0.0.1", "0.0.0.0", "255.255.255.255", "::", "::1", "2001:db8::abcd"):
        change("canonical ip " + value, [9], value)
    for value in ("127.1", "0177.0.0.1", "2001:0db8::abcd", "2001:DB8::abcd", "::1%lo0", "::1/128"):
        change("noncanonical ip " + value, [9], value, False)
    for index in (0, 1, 2, 3):
        e = new_event(); e[5][index] = "A_.-09" * 21 + "AB"
        if index < 2: e[2][index] = e[5][index]; e[11] = domain("mixer.hosted.state.v1", cbor([1, *e[2]]))
        add("ValidID exact 128 bytes " + str(index), e)
        e[5][index] += "x"
        if index < 2: e[2][index] = e[5][index]
        add("ValidID 129 bytes " + str(index), e, False)
    for value in ("", "x/y", "x\n", "é", "x "):
        change("invalid app identifier " + repr(value), [5, 2], value, False)
    change("tenant mismatch coherent hash", [5, 1], "other-project", False)
    change("initial wrong state decode only", [11], b"\xaa" * 32, True, False)
    change("initial nonempty previous hash", [13], b"\xbb" * 32, False)
    e = new_event(); e[1] = 2
    add("later empty previous hash", e, False)
    for path in (("id",), ("actor", 4), ("actor", 10), ("decision", 0), ("decision", 6, 0, 2), ("recorded_at",)):
        d = display(new_event()); v = d
        for key in path: v = v[key]
        for alternate in ("0" + v, "+" + v, v + "\n"):
            add("same typed integer alternate " + repr(path) + repr(alternate), accepted=False, display_mutation=(path, alternate))
    for path in (("actor", 0), ("actor", 2), ("actor", 9), ("request_id",), ("decision", 6, 0, 0)):
        d = display(new_event()); v = d
        for key in path: v = v[key]
        assert v.upper() != v
        add("same UUID uppercase " + repr(path), accepted=False, display_mutation=(path, v.upper()))
    for path in (("actor", 5), ("actor", 6), ("target", 5), ("request_hash",), ("hash",)):
        e = new_event()
        # Ensure nontrivial letters in every displayed digest.
        d = display(e); v = d
        for key in path: v = v[key]
        if v.upper() == v:
            if path[0] == "actor": e[3][path[1]] = b"\xab" * 32
            elif path[0] == "target": e[5][path[1]] = b"\xab" * 32
            elif path[0] == "request_hash": e[14] = b"\xab" * 32
            d = display(e); v = d
            for key in path: v = v[key]
        add("same digest uppercase " + repr(path), e, False, display_mutation=(path, v.upper()))

    a = new_event(); b = copy.deepcopy(a)
    b[1] = 2; b[13] = domain("mixer.hosted.audit.v1", cbor(a)); b[11] = a[12]; b[12] = b"\x90" * 32
    c = copy.deepcopy(b); c[1] = 3; c[13] = domain("mixer.hosted.audit.v1", cbor(b)); c[11] = b[12]
    foreign = new_event("foreign-org", "foreign-project")
    wrong_hash = copy.deepcopy(b); wrong_hash[13] = b"\xab" * 32
    wrong_state = copy.deepcopy(b); wrong_state[11] = b"\xbc" * 32
    foreign_linked = copy.deepcopy(b); foreign_linked[13] = domain("mixer.hosted.audit.v1", cbor(foreign)); foreign_linked[11] = foreign[12]
    edges = []
    for label, current, previous, accepted in [
        ("initial null", a, None, True), ("initial nonnull", a, a, False),
        ("adjacent", b, a, True), ("missing", b, None, False), ("skip", c, a, False),
        ("wrong hash but both rows valid", wrong_hash, a, False),
        ("wrong state but both rows valid", wrong_state, a, False),
        ("foreign tenant with matching hash and state", foreign_linked, foreign, False)]:
        edges.append({"label": label, "accepted": accepted, "current": row(current, display(current)),
                      "previous": None if previous is None else row(previous, display(previous))})
    result = {"schema": 1, "cases": cases, "edges": edges,
              "independence": "Typed-first stdlib fixtures; no producer source/oracle/fixture imports."}
    (HERE / "independent-vectors.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"cases": len(cases), "accepted": sum(c["accepted"] for c in cases),
                      "rejected": sum(not c["accepted"] for c in cases), "edges": len(edges)}))


if __name__ == "__main__":
    main()
