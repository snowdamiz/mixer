#!/usr/bin/env python3
"""Independent array-only canonical CBOR oracle; Python standard library only."""
import hashlib
import json
from pathlib import Path
import sys


def encode(value):
    if type(value) is bool:
        return bytes([0xF5 if value else 0xF4])
    if type(value) is int and 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        major, n, suffix = 0, value, b""
    elif type(value) is str:
        suffix = value.encode("utf-8")
        major, n = 3, len(suffix)
    elif type(value) is list:
        major, n = 4, len(value)
        suffix = b"".join(map(encode, value))
    else:
        raise ValueError("unsupported oracle value")
    if n < 24:
        head = bytes([(major << 5) | n])
    else:
        width = next(width for width in (1, 2, 4, 8) if n < 1 << (8 * width))
        head = bytes([(major << 5) | {1: 24, 2: 25, 4: 26, 8: 27}[width]]) + n.to_bytes(width, "big")
    return head + suffix


def sha(value):
    return hashlib.sha256(value).hexdigest()


def domain(name, value):
    return sha(("mixer.hosted.customer." + name + ".v2").encode() + b"\x00" + value)


def main(destination):
    vectors = [
        (0, "00"), (23, "17"), (24, "1818"), (255, "18ff"),
        (256, "190100"), (65535, "19ffff"), (65536, "1a00010000"),
        (4294967295, "1affffffff"), (4294967296, "1b0000000100000000"),
        (9007199254740991, "1b001fffffffffffff"),
        (True, "f5"), (False, "f4"), ([], "80"), ([1, 2, 3], "83010203"),
        ("", "60"), ("ü", "62c3bc"), ([False, [True]], "82f481f5"),
        (list(range(24)), "9818000102030405060708090a0b0c0d0e0f1011121314151617"),
    ]
    for value, expected in vectors:
        assert encode(value).hex() == expected, (value, expected)
    locked, fresh = 1729000000, 1729000005
    raw = {
        "profile_id": "profile\u0000é", "profile_version": 2147483647,
        "issuer": "https://identity.example/路径", "subject": "subject\u0000雪",
        "client_id": "client:✓", "credential_ref": "credential:ß",
        "issued_at": locked - 10, "expires_at": locked + 3600,
    }
    org, project = "org:é", "project:雪"
    target = [org, project, "app/天气", "env release", "android", "1" * 64, "2" * 64, "3" * 64]
    envelope, reason = "4" * 64, "publish ☃\n"
    hashes = {
        "binding_key": domain("binding_key", encode([raw["profile_id"], raw["profile_version"], raw["subject"]])),
        "issuer": domain("issuer", raw["issuer"].encode()),
        "subject": domain("subject", raw["subject"].encode()),
        "client": domain("client", raw["client_id"].encode()),
        "credential_ref": domain("credential_ref", raw["credential_ref"].encode()),
        "genesis": domain("state", encode([2, org, project])),
        "request": domain("upload.request", encode([2, "artifact.upload", target, envelope, reason])),
    }
    hashes["state"] = domain("state", encode([2, org, project, hashes["genesis"], 1, target[6], envelope, target[7]]))
    actor = ["principal:✓", "human", raw["profile_id"], raw["profile_version"],
             *[hashes[k] for k in ("binding_key", "issuer", "subject", "client", "credential_ref")],
             "family/雪", raw["issued_at"], raw["expires_at"]]
    members = [
        ["00-org", "developer", 17, org, [], "all_projects", True, locked - 10, []],
        ["équipe", "owner", 18, org, [project], "exact_project", True, fresh, [fresh + 1]],
    ]
    auth = [locked, fresh, [11, True], [12, True], [13, True, locked - 20],
            [14, True, locked - 15, []], [15, True, locked - 15, [fresh + 100]],
            16, 19, "mixer.artifact.upload", members]
    values = [2, 1, [org, project], actor, auth, target, "artifact.upload", "created", reason,
              "ef" * 16, ["192.0.2.10"], fresh, hashes["genesis"], hashes["state"], "",
              hashes["request"], envelope]
    encoded = encode(values)
    hashes["event"] = domain("audit", encoded)
    bad_hashes = {
        "subject_prehashed": domain("subject", sha(raw["subject"].encode()).encode()),
        "subject_printable_zero": sha(b"mixer.hosted.customer.subject.v2\\0" + raw["subject"].encode()),
        "binding_prehashed": domain("binding_key", encode([raw["profile_id"], raw["profile_version"], sha(raw["subject"].encode())])),
    }
    result = {"raw": raw, "values": values, "event_hex": encoded.hex(), "hashes": hashes,
              "known_wrong_hashes": bad_hashes, "primitive_vectors": len(vectors)}
    Path(destination).write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"primitive_vectors": len(vectors), "event_bytes": len(encoded), "event_sha256": hashes["event"]}))


if __name__ == "__main__":
    main(sys.argv[1])
