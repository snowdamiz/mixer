#!/usr/bin/env python3
"""Independent stdlib oracle for actual retained SQL rows and parity captures.

No candidate Elixir/SQL encoder, producer oracle, or live database is imported.
The typed field mapping follows the selected closed audit schema.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def domain_hash(domain, value):
    return hashlib.sha256(domain.encode("ascii") + b"\0" + value).digest()


def number_header(major, number):
    assert type(number) is int and 0 <= number <= 2**64 - 1
    if number < 24:
        return bytes([major * 32 + number])
    for size, marker in [(1, 24), (2, 25), (4, 26), (8, 27)]:
        if number < 2 ** (size * 8):
            return bytes([major * 32 + marker]) + number.to_bytes(size, "big")
    raise AssertionError("uint64 overflow")


def cbor(value):
    if value is None:
        return b"\xf6"
    if type(value) is int:
        return number_header(0, value)
    if type(value) is bytes:
        return number_header(2, len(value)) + value
    if type(value) is str:
        raw = value.encode("utf-8", errors="strict")
        return number_header(3, len(raw)) + raw
    assert type(value) is list
    return number_header(4, len(value)) + b"".join(cbor(x) for x in value)


def pg_json(value):
    if type(value) is dict:
        keys = sorted(value, key=lambda key: (len(key.encode("utf-8")), key.encode("utf-8")))
        return "{" + ", ".join(pg_json(k) + ": " + pg_json(value[k]) for k in keys) + "}"
    if type(value) is list:
        return "[" + ", ".join(pg_json(x) for x in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


def uuid(value):
    assert len(value) == 36
    return bytes.fromhex(value.replace("-", ""))


def typed_event(d):
    a, decision, target = [d[k] for k in ["actor", "decision", "target"]]
    return [1, int(d["id"]), d["tenant"],
            [uuid(a[0]), a[1], uuid(a[2]), a[3], int(a[4]),
             *[bytes.fromhex(value) for value in a[5:9]], uuid(a[9]), int(a[10])],
            [*[int(value) for value in decision[:6]],
             [[uuid(m[0]), m[1], int(m[2])] for m in decision[6]]],
            [*target[:5], bytes.fromhex(target[5]), bytes.fromhex(target[6])],
            d["action"], d["reason"], uuid(d["request_id"]), d["source_ip"], int(d["recorded_at"]),
            *[bytes.fromhex(d[k]) for k in ["previous_state", "current_state", "previous_hash", "request_hash"]]]


def row(sample):
    r = sample["retained_row"]
    d = r["display_json"]
    assert set(r) == {"organization", "project", "event_id", "event_cbor", "event_hash", "previous_hash", "previous_state", "current_state", "display_json", "display_bytes"}
    raw = {k: bytes.fromhex(v["value"]) for k, v in r.items() if type(v) is dict and v.get("encoding") == "hex"}
    assert [r["organization"], r["project"]] == d["tenant"]
    assert str(r["event_id"]) == d["id"]
    encoded = cbor(typed_event(d))
    assert raw["event_cbor"] == encoded
    assert 0 < len(encoded) <= 16384
    assert raw["event_hash"] == domain_hash("mixer.hosted.audit.v1", encoded)
    assert raw["display_bytes"] == pg_json(d).encode("utf-8")
    assert len(raw["display_bytes"]) <= 32768
    assert json.loads(raw["display_bytes"]) == d
    for key in ["event_hash", "previous_hash", "previous_state", "current_state"]:
        assert raw[key].hex() == d["hash" if key == "event_hash" else key]
    if "text_hex" in sample:
        assert d["reason"].encode().hex() == sample["text_hex"]
        assert sample["sql_row"] and sample["exact_replay"] and sample["elixir_row"] == "accepted"
    return r["event_id"], raw


def chain(samples):
    previous = None
    for sample in samples:
        event_id, raw = row(sample)
        if previous is None:
            assert event_id == 1 and raw["previous_hash"] == b""
            assert raw["previous_state"] == domain_hash("mixer.hosted.state.v1", cbor([1, *sample["retained_row"]["display_json"]["tenant"]]))
        else:
            assert event_id == previous[0] + 1
            assert raw["previous_hash"] == previous[1]["event_hash"]
            assert raw["previous_state"] == previous[1]["current_state"]
        previous = event_id, raw
    return len(samples)


def check_run(number):
    run = HERE / f"run-{number}"
    observed = json.loads((run / "tests.json").read_text())["observations"]
    counts = {}
    counts["original_reviewer"] = chain(observed["independent_uploaded_unicode"])
    counts["producer_display_correction"] = chain(observed["display_correction_uploaded_rows"]["rows"])
    for sample in observed["display_correction_parity"]["cases"]:
        display = json.loads(bytes.fromhex(sample["postgres_display_hex"]))
        assert pg_json(display).encode().hex() == sample["postgres_display_hex"]
        assert display["reason"].encode().hex() == sample["text_hex"]
        assert display["actor"][3] == display["reason"]
    if number == 2:
        corpus = json.loads((run / "inputs/probe/review-corpus.json").read_text())
        strings = observed["review_string_parity"]
        assert len(strings) == len(corpus["strings"]) == 407
        for expected, actual in zip(corpus["strings"], strings, strict=True):
            assert expected["label"] == actual["label"]
            assert expected["value"].encode().hex() == actual["text_hex"]
            assert pg_json(expected["value"]).encode().hex() == actual["pg_hex"] == expected["expected_hex"]
        parity = observed["review_object_raw_parity"]
        assert len(parity["objects"]) == 15 and len(parity["raw"]) == 8
        for key, cases in [("objects", corpus["objects"]), ("raw", corpus["raw_inputs"])]:
            for expected, actual in zip(cases, parity[key], strict=True):
                assert expected["label"] == actual["label"]
                assert expected["expected_hex"] == actual["pg_hex"] == pg_json(expected["value"]).encode().hex()
                if key == "raw":
                    assert bytes.fromhex(actual["raw_hex"]).decode() == expected["raw"]
                    assert json.loads(expected["raw"]) == expected["value"]
        counts["new_reviewer_mixed_unicode"] = chain(observed["review_stored_rows"])
        counts["new_reviewer_boundary"] = chain(observed["review_boundary_rows"])
        assert counts["new_reviewer_mixed_unicode"] == 53 and counts["new_reviewer_boundary"] == 4
        for sample in observed["review_boundary_rows"]:
            display = json.loads(bytes.fromhex(sample["pure_display_hex"]))
            assert len(bytes.fromhex(sample["profile_hex"])) == 128
            assert len(bytes.fromhex(sample["text_hex"])) == 512
            assert display["actor"][3].encode().hex() == sample["profile_hex"]
            assert pg_json(display).encode().hex() == sample["pure_display_hex"]
        rejection = observed["review_equivalent_byte_rejection"]
        row({"retained_row": rejection["original"]})
        original = rejection["original"]
        assert len(rejection["variants"]) == 6
        for sample in rejection["variants"]:
            assert sample["both_validators_rejected"] and sample["exact_original_replay"]
            assert sample["alternative_hex"] != original["display_bytes"]["value"]
            assert json.loads(bytes.fromhex(sample["alternative_hex"])) == original["display_json"]
        assert len(observed["review_invalid_utf8_nul"]) == 15
    return {"run": run.name, "rows": sum(counts.values()), "chains": counts}


if __name__ == "__main__":
    results = [check_run(1), check_run(2)]
    print(json.dumps({"verified": True, "runs": results, "actual_chain_rows_cross_checked": sum(x["rows"] for x in results),
                      "additional_exact_byte_corruption_original_row": 1,
                      "candidate_encoder_imported": False, "live_database_read": False,
                      "scope": "local synthetic captured actual-row CBOR hash projections byte display and adjacent-edge verification"}))
