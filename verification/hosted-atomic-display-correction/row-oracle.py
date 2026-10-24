#!/usr/bin/env python3
"""Stdlib byte/hash reconstruction for fresh original and added captured SQL rows.

Adapted from the prior independent reviewer oracle. This is a captured-row cross-check, not independent acceptance or a proposed arbitrary-input product decoder.
It imports no candidate encoder and reads no database.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def digest(domain, body):
    return hashlib.sha256(domain.encode() + b"\0" + body).digest()


def head(major, number):
    assert type(number) is int and 0 <= number < 1 << 64
    if number < 24:
        return bytes([major * 32 + number])
    for width, tag in [(1, 24), (2, 25), (4, 26), (8, 27)]:
        if number < 1 << (width * 8):
            return bytes([major * 32 + tag]) + number.to_bytes(width, "big")
    raise AssertionError("uint64")


def encode(value):
    if value is None:
        return b"\xf6"
    if type(value) is int:
        return head(0, value)
    if type(value) is bytes:
        return head(2, len(value)) + value
    if type(value) is str:
        body = value.encode("utf-8")
        return head(3, len(body)) + body
    assert type(value) is list
    return head(4, len(value)) + b"".join(encode(x) for x in value)


def uid(value):
    return bytes.fromhex(value.replace("-", ""))


def event(display):
    actor, decision, target = (display[key] for key in ("actor", "decision", "target"))
    return [
        1, int(display["id"]), display["tenant"],
        [uid(actor[0]), actor[1], uid(actor[2]), actor[3], int(actor[4]),
         *[bytes.fromhex(x) for x in actor[5:9]], uid(actor[9]), int(actor[10])],
        [*[int(x) for x in decision[:6]],
         [[uid(member[0]), member[1], int(member[2])] for member in decision[6]]],
        [*target[:5], bytes.fromhex(target[5]), bytes.fromhex(target[6])],
        display["action"], display["reason"], uid(display["request_id"]),
        display["source_ip"], int(display["recorded_at"]),
        *[bytes.fromhex(display[key]) for key in
          ("previous_state", "current_state", "previous_hash", "request_hash")],
    ]


def pg_display(value):
    if type(value) is dict:
        keys = sorted(value, key=lambda key: (len(key.encode()), key.encode()))
        return "{" + ", ".join(pg_display(key) + ": " + pg_display(value[key]) for key in keys) + "}"
    if type(value) is list:
        return "[" + ", ".join(map(pg_display, value)) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def validate_rows(rows):
    previous = None
    for sample in rows:
        row = sample["retained_row"]
        display = row["display_json"]
        raw = {key: bytes.fromhex(value["value"]) for key, value in row.items()
               if type(value) is dict and value.get("encoding") == "hex"}
        assert row["event_id"] == int(display["id"])
        assert [row["organization"], row["project"]] == display["tenant"]
        assert raw["event_cbor"] == encode(event(display))
        assert raw["event_hash"] == digest("mixer.hosted.audit.v1", raw["event_cbor"])
        for key in ("event_hash", "previous_hash", "previous_state", "current_state"):
            assert raw[key].hex() == display["hash" if key == "event_hash" else key]
        assert json.loads(raw["display_bytes"]) == display
        assert raw["display_bytes"] == pg_display(display).encode()
        assert display["reason"].encode().hex() == sample["text_hex"]
        assert sample["sql_row"] and sample["exact_replay"] and sample["elixir_row"] == "accepted"
        assert raw["event_cbor"] and len(raw["event_cbor"]) <= 16_384
        assert len(raw["display_bytes"]) <= 32_768
        if previous is None:
            assert row["event_id"] == 1 and not raw["previous_hash"]
            assert raw["previous_state"] == digest("mixer.hosted.state.v1", encode([1, *display["tenant"]]))
        else:
            assert raw["previous_hash"] == previous["event_hash"]
            assert raw["previous_state"] == previous["current_state"]
        previous = raw


def main():
    import sys
    assert len(sys.argv) == 2, "usage: row-oracle.py run-N"
    target = HERE / sys.argv[1]
    assert target.parent == HERE and target.name.startswith("run-")
    tests = json.loads((target / "tests.json").read_text())
    observations = tests["observations"]
    added = observations["display_correction_uploaded_rows"]["rows"]
    assert len(added) == 56
    validate_rows(added)
    if "independent_uploaded_unicode" in observations:
        original = observations["independent_uploaded_unicode"]
        assert len(original) == 8
        validate_rows(original)
    else:
        original = []
    for sample in observations["display_correction_parity"]["cases"]:
        raw = bytes.fromhex(sample["postgres_display_hex"])
        display = json.loads(raw)
        assert raw == pg_display(display).encode()
        assert display["reason"].encode().hex() == sample["text_hex"]
        assert display["actor"][3] == display["reason"]
        assert sample["exact_parity"]
    print(json.dumps({"verified": True, "actual_retained_rows": len(added)+len(original),
                      "added_retained_rows": len(added), "original_reviewer_rows": len(original),
                      "independent_python_cbor_hash_display_projection_and_adjacent_edges": True,
                      "parity_cases": len(observations["display_correction_parity"]["cases"]),
                      "source": "Prior independent reviewer stdlib CBOR/hash/display oracle, adapted solely to new actual-row captures; imports no candidate encoder",
                      "scope": "captured-local-synthetic-byte-cross-check-only"}))


if __name__ == "__main__":
    main()
