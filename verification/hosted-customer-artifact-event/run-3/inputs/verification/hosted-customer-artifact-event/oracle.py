#!/usr/bin/env python3
"""Independent schema-2 golden array encoder, using only Python's standard library."""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def head(major, value):
    if value < 24:
        return bytes([(major << 5) | value])
    for marker, size in [(24, 1), (25, 2), (26, 4), (27, 8)]:
        if value < 1 << (size * 8):
            return bytes([(major << 5) | marker]) + value.to_bytes(size, "big")
    raise ValueError("uint overflow")


def encode(value):
    if value is True:
        return b"\xf5"
    if value is False:
        return b"\xf4"
    if isinstance(value, int) and value >= 0:
        return head(0, value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return head(3, len(raw)) + raw
    if isinstance(value, list):
        return head(4, len(value)) + b"".join(map(encode, value))
    raise ValueError("unsupported golden type")


def digest(field, raw):
    return sha256(b"mixer.hosted.customer." + field.encode("ascii") + b".v2\0" + raw).hexdigest()


def vectors():
    # RFC 8949 Appendix A primitive/array encodings, independent of the product.
    for value, wire in [(0, "00"), (23, "17"), (24, "1818"), (1000, "1903e8"),
                        (True, "f5"), ([1, [2, 3]], "8201820203"), ("ü", "62c3bc")]:
        assert encode(value).hex() == wire
    target = ["org", "project", "app", "env", "ios", "a" * 64, "b" * 64, "c" * 64]
    envelope = "d" * 64
    genesis = digest("state", encode([2, "org", "project"]))
    actor = ["person", "human", "profile", 1,
             digest("binding_key", encode(["profile", 1, "用户:raw"])),
             digest("issuer", "https://issuer.example/é".encode()),
             digest("subject", "用户:raw".encode()),
             digest("client", "client:ä".encode()),
             digest("credential_ref", "credential:ß".encode()), "family", 80, 1000]
    authorization = [100, 102, [2, True], [3, True], [4, True, 0],
                     [5, True, 50, [950]], [6, True, 40, [960]], 7, 8,
                     "mixer.artifact.upload", [["member-a", "developer", 9, "org",
                                                ["project"], "exact_project", True, 50, [900]]]]
    request = digest("upload.request", encode([2, "artifact.upload", target, envelope, "reason é"]))
    state = digest("state", encode([2, "org", "project", genesis, 1, "b" * 64, envelope, "c" * 64]))
    event = [2, 1, ["org", "project"], actor, authorization, target, "artifact.upload", "created",
             "reason é", "0123456789abcdef0123456789abcdef", ["2001:db8::1"], 102,
             genesis, state, "", request, envelope]
    return event, {"genesis": genesis, "request": request, "state": state,
                   "event": digest("audit", encode(event)),
                   "binding": actor[4], "issuer": actor[5], "subject": actor[6],
                   "client": actor[7], "credential_ref": actor[8]}


if __name__ == "__main__":
    event, hashes = vectors()
    ROOT.joinpath("golden_event.hex").write_text(encode(event).hex() + "\n")
    ROOT.joinpath("golden_hashes.txt").write_text("".join(f"{key}={value}\n" for key, value in hashes.items()))
    print(f"Independent canonical golden: {len(encode(event))} bytes; event={hashes['event']}")
