#!/usr/bin/env python3
"""Independent stdlib byte/hash reconstruction for the eight captured SQL rows.

This is a counterexample oracle, not a proposed arbitrary-input product decoder.
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


def main():
    data = json.loads((HERE / "retained-row-counterexamples.json").read_text())
    previous = None
    for sample in data["rows"]:
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
        assert sample["sql_row"] and sample["exact_replay"]
        assert raw["event_cbor"] and len(raw["event_cbor"]) <= 16_384
        assert len(raw["display_bytes"]) <= 32_768
        if previous is None:
            assert row["event_id"] == 1 and not raw["previous_hash"]
            assert raw["previous_state"] == digest("mixer.hosted.state.v1", encode([1, *display["tenant"]]))
        else:
            assert raw["previous_hash"] == previous["event_hash"]
            assert raw["previous_state"] == previous["current_state"]
        previous = raw
    rejected = [sample["text_hex"] for sample in data["rows"] if sample["elixir_row"] == "rejected"]
    assert rejected == ["0b", "0e", "1f"]
    print(json.dumps({"verified": True, "actual_retained_rows": len(data["rows"]),
                      "independent_python_cbor_hash_display_projection_and_adjacent_edges": True,
                      "valid_rows_falsely_rejected_by_elixir": rejected,
                      "scope": "captured-counterexample-byte-oracle-only"}))


if __name__ == "__main__":
    main()
