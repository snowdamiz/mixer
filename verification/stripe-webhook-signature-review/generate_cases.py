"""Independent contract cases; all HMACs come from Python's standard library."""
import collections
import hashlib
import hmac
import json
from pathlib import Path
import random
import sys

OUT = Path(sys.argv[1])
RNG = random.Random(0x20261024)
NOW = 1_792_846_000
MAX_TIME = 253_402_300_799
KEY = b"review_synthetic_endpoint_key_01"
BODY = b'{"review":"raw bytes"}\x00\xff\n'
CASES = []
DEFAULT = object()


def binary(value):
    return {"bytes": value.hex()}


def pack(value):
    if isinstance(value, bytes):
        return binary(value)
    if isinstance(value, list):
        return [pack(x) for x in value]
    return value


def sig(body=BODY, text=str(NOW), key=KEY):
    return hmac.new(key, text.encode("ascii") + b"." + body, hashlib.sha256).hexdigest().encode()


def header(body=BODY, text=str(NOW), key=KEY):
    return b"t=" + text.encode("ascii") + b",v1=" + sig(body, text, key)


def add(category, name, expected, body=BODY, headers=DEFAULT, keys=DEFAULT, now=NOW):
    CASES.append({"category": category, "name": name, "expected": expected,
                  "args": pack([body, [header()] if headers is DEFAULT else headers,
                                [KEY] if keys is DEFAULT else keys, now])})


for index in range(320):
    key_count = 1 + RNG.randrange(2)
    keys = [RNG.randbytes(RNG.choice([16, 17, 31, 32, 64, 128, 255, 256])) for _ in range(key_count)]
    body = RNG.randbytes(RNG.randrange(1, 1025))
    stamp = RNG.choice([0, 1, 299, 300, 301, NOW, MAX_TIME - 300, MAX_TIME])
    clock = max(0, min(MAX_TIME, stamp + RNG.choice([-300, -299, 0, 299, 300])))
    signatures = [RNG.randbytes(32).hex().encode() for _ in range(1 + RNG.randrange(8))]
    signatures[RNG.randrange(len(signatures))] = sig(body, str(stamp), RNG.choice(keys))
    fields = [b"t=" + str(stamp).encode()] + [b"v1=" + s for s in signatures]
    fields += [b"v0=" + sig(body, str(stamp), keys[0]), b"future=a=b", b"x=\tvalue"]
    RNG.shuffle(fields)
    ws = [b"", b" ", b"\t", b" \t ", b"\t \t"]
    value = b",".join(RNG.choice(ws) + field + RNG.choice(ws) for field in fields)
    add("generated-authentic", f"authentic-{index}", "ok", body, [value], keys, clock)
    offset = RNG.randrange(len(body))
    changed = body[:offset] + bytes([body[offset] ^ 1]) + body[offset + 1:]
    add("generated-body-tamper", f"body-{index}", "invalid_signature", changed, [value], keys, clock)
    add("generated-wrong-key", f"key-{index}", "invalid_signature", body, [value], [b"wrong_review_key_00000000000000"], clock)
    other_stamp = stamp - 1 if stamp else 1
    changed_header = value.replace(b"t=" + str(stamp).encode(), b"t=" + str(other_stamp).encode(), 1)
    add("generated-timestamp-tamper", f"timestamp-{index}", "invalid_signature", body, [changed_header], keys, clock)

# Even a valid HMAC over a noncanonical timestamp cannot bypass Mixer parsing.
for text in ["00", "01", "01792846000", "+1792846000", "-0", "1792846000.0", "1e9",
             "253402300800", "9999999999999", " 1792846000", "1792846000 ", "\t1792846000", ""]:
    add("signed-noncanonical-timestamp", repr(text), "invalid_signature", headers=[header(text=text)])

for stamp in [0, 1, NOW, MAX_TIME - 1, MAX_TIME]:
    for delta in [-301, -300, -1, 0, 1, 300, 301]:
        clock = stamp + delta
        if 0 <= clock <= MAX_TIME:
            add("freshness-extremes", f"{stamp}:{clock}", "ok" if abs(delta) <= 300 else "invalid_signature",
                headers=[header(text=str(stamp))], now=clock)

for offset in range(64):
    value = sig()
    changed = value[:offset] + (b"0" if value[offset:offset+1] != b"0" else b"1") + value[offset+1:]
    add("signature-nibble-tamper", str(offset), "invalid_signature", headers=[b"t=" + str(NOW).encode() + b",v1=" + changed])

for byte in range(256):
    if byte < 32 and byte != 9 or byte > 126:
        add("forbidden-header-octets", str(byte), "invalid_signature", headers=[header() + b",future=x" + bytes([byte]) + b"x"])
    for position in [0, 31, 63]:
        if byte not in b"0123456789abcdefABCDEF":
            bad = sig()[:position] + bytes([byte]) + sig()[position+1:]
            add("malformed-v1-amid-valid", f"{byte}:{position}", "invalid_signature", headers=[header() + b",v1=" + bad])

for field in [b"t=", b"t=" + str(NOW).encode(), b"v1=", b"v1=0", b"v1=" + b"0" * 63,
              b"v1=" + b"0" * 65, b"v1=" + sig() + b"=x", b"", b" \t ", b"noequals", b"=x", b"x="]:
    for first in [True, False]:
        fields = [field, header()] if first else [header(), field]
        add("ambiguous-composite", f"{field.hex()}:{first}", "invalid_signature", headers=[b",".join(fields)])

for count in [30, 31]:
    value = header() + b",x=y" * count
    add("field-count-edge", str(count+2), "ok" if count == 30 else "invalid_signature", headers=[value])
for count in [8, 9]:
    value = b"t=" + str(NOW).encode() + b"," + b",".join([b"v1=" + sig()] * count)
    add("signature-count-edge", str(count), "ok" if count == 8 else "invalid_signature", headers=[value])
for length in [4095, 4096, 4097]:
    prefix = header() + b",x="
    value = prefix + b"a" * (length-len(prefix))
    add("header-size-edge", str(length), "ok" if length <= 4096 else "invalid_signature", headers=[value])
for length in [0, 1, 1_048_575, 1_048_576, 1_048_577]:
    body = b"z" * length
    add("body-size-edge", str(length), "ok" if 1 <= length <= 1_048_576 else "invalid_signature",
        body={"repeat": [122, length]}, headers=[header(body)])
for length in [0, 1, 15, 16, 17, 255, 256, 257]:
    key = b"s" * length
    add("secret-size-edge", str(length), "ok" if 16 <= length <= 256 else "verification_unavailable",
        headers=[header(key=key)], keys=[key])

invalid_terms = [None, True, False, 0, -1, 1.5, {}, {"atom": "synthetic"}, {"tuple": []},
                 {"bitstring": 1}, {"improper": [[binary(KEY)], 1]}]
for index, value in enumerate(invalid_terms):
    add("wrong-body-term", str(index), "invalid_signature", body=value)
    add("wrong-header-term", str(index), "invalid_signature", headers=value)
    add("wrong-config-term", str(index), "verification_unavailable", keys=value)
    add("wrong-clock-term", str(index), "invalid_signature" if type(value) is int and value == 0 else "verification_unavailable", now=value)
for value in [[], [KEY, KEY], [KEY, KEY+b"2", KEY+b"3"], [None], [KEY, None], [[KEY]], b"not_a_key_list"]:
    add("wrong-config-shape", repr(value), "verification_unavailable", keys=value)
for value in [[], [header(), header()], [[header()]], b"not_a_header_list", [None],
              {"improper": [[binary(header())], 1]}]:
    add("wrong-header-shape", repr(value), "invalid_signature", headers=value)
for value in [-1, MAX_TIME+1, NOW+0.0, {"bigint": "9" * 2000}]:
    add("clock-boundary", str(value)[:40], "verification_unavailable", now=value)

# Expiration/removal is observed per call; no request selects an endpoint key.
add("config-rotation", "old-key-active", "ok", keys=[KEY, KEY+b"2"])
add("config-rotation", "old-key-removed", "invalid_signature", keys=[KEY+b"2"])
add("config-rotation", "request-extension-cannot-select-secret", "invalid_signature",
    headers=[header()+b",secret="+KEY], keys=[KEY+b"2"])

payload = {"schema": 1, "seed": "0x20261024", "provenance": "synthetic; independent Python stdlib hmac/hashlib",
           "counts": dict(sorted(collections.Counter(x["category"] for x in CASES).items())), "cases": CASES}
OUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
print(json.dumps({"cases": len(CASES), "counts": payload["counts"]}, sort_keys=True))
