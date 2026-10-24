#!/usr/bin/env python3
"""Reviewer-authored inputs and stdlib expected bytes; no candidate encoder imports."""
import hashlib
import json
import pathlib
import random

HERE = pathlib.Path(__file__).resolve().parent


def pg(value):
    if type(value) is dict:
        return "{" + ", ".join(pg(k) + ": " + pg(value[k]) for k in sorted(value, key=lambda k: (len(k.encode()), k.encode()))) + "}"
    if type(value) is list:
        return "[" + ", ".join(map(pg, value)) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def case(label, value):
    raw = pg(value).encode()
    return {"label": label, "value": value, "expected_hex": raw.hex(), "expected_sha256": hashlib.sha256(raw).hexdigest()}


def main():
    texts = []
    for c in [*range(1, 32), 127]:
        for count in range(1, 9):
            texts.append((f"control-{c:02x}/slashes-{count}", "\\" * count + "u000B" + chr(c) + "\\" * count + "u000b\"/雪"))
    scalars = [0x80, 0x85, 0x9F, 0xA0, 0x7FF, 0x800, 0xD7FF, 0xE000, 0xFDD0, 0xFFFD,
               0xFFFE, 0xFFFF, 0x10000, 0x1D11E, 0x1F600, 0x10FFFF, 0x2028, 0x2029, 0xFEFF]
    texts += [(f"unicode-{c:x}", "L" + chr(c) + "\\u000B\u000bR") for c in scalars]
    texts += [("nfc", "é"), ("nfd", "e\u0301"), ("html-literals", "</script>&'\\/"),
              ("all-controls", "".join(map(chr, range(1, 32))) + "\\u000B\\u000b")]
    rng = random.Random(0x43523031)
    alphabet = [chr(c) for c in range(1, 32)] + ["\\", '"', "/", "\\u000B", "\\u001F", "é", "e\u0301", "😀", "雪", "\u2028"]
    for i in range(128):
        text = "".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 19)))
        assert 0 < len(text.encode()) <= 128
        texts.append((f"seeded-mix-{i}", text))
    strings = [case(label, value) for label, value in texts]
    keys = ["", "a", "aa", "é", "\x0b", "\\u000B", "\\u000b", "雪", "😀", '"', "\\", "\u2028", "e\u0301", "éa", "ÿ"]
    objects = []
    for shift in range(len(keys)):
        order = keys[shift:] + keys[:shift]
        value = {k: [None, 1, '\"\\\b\f\n\r\t\u001f', {"z": "\\u000B", "é": "雪"}] for k in order}
        objects.append(case(f"utf8-key-order-{shift}", value))
    raw_inputs = [r'"\u000B"', r'"\u000b"', r'"\\u000B"', r'"\\u000b"',
                  r'"\ud83d\ude00"', r'"\uD83D\uDE00"', r'"\u2028\u2029"',
                  r'{"\u000B":"\\u000B","雪":"\ud83d\ude00","aa":"\/"}']
    raw = [{"raw": value, **case(f"raw-{i}", json.loads(value))} for i, value in enumerate(raw_inputs)]
    stored = texts[::8][:32] + texts[256:275] + [("stored-nfd", "e\u0301"), ("stored-nfc", "é")]
    bounds = [
        ("quote-slash", '\\"' * 64, '\\"' * 256),
        ("mixed-controls", ("\x0b\\u000B\n" * 16), ("\x1f\\u001F\t" * 64)),
        ("unicode-max", chr(0x10FFFF) * 32, chr(0x10FFFF) * 128),
        ("decomposed", "e\u0301" * 42 + "xy", "e\u0301" * 170 + "xy"),
    ]
    assert all(len(p.encode()) == 128 and len(r.encode()) == 512 for _, p, r in bounds)
    payload = {"schema": 1, "strings": strings, "objects": objects, "raw_inputs": raw,
               "stored": [{"label": l, "text": t, "text_hex": t.encode().hex()} for l, t in stored],
               "bounds": [{"label": l, "profile": p, "reason": r} for l, p, r in bounds]}
    (HERE / "probe/review-corpus.json").write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
    print(json.dumps({k: len(payload[k]) for k in ["strings", "objects", "raw_inputs", "stored", "bounds"]}))


if __name__ == "__main__":
    main()
