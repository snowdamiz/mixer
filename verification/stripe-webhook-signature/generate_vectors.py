"""Independent standard-library HMAC oracle. All keys are synthetic public fixtures."""
import hashlib
import hmac
import json
from pathlib import Path

KEY = b"whsec_mixer_public_test_only_0001"
CASES = [
    ("json", b'{"id":"evt_mixer_fixture","type":"test"}', 1792846000),
    ("json_newline", b'{"id":"evt_mixer_fixture","type":"test"}\n', 1792846000),
    ("opaque_bytes", bytes(range(256)), 1792846000),
    ("utf8", '{"description":"caf\u00e9 \u2615"}'.encode(), 1792846000),
    ("zero_timestamp", b"x", 0),
    ("maximum_timestamp", b"x", 253402300799),
    ("maximum_body", b"x" * 1048576, 1792846000),
]


def encoded():
    return [{"name": name, "secret_hex": KEY.hex(), "timestamp": stamp,
             "body_hex": None if name == "maximum_body" else body.hex(),
             "body_repeat_x": len(body) if name == "maximum_body" else None,
             "body_sha256": hashlib.sha256(body).hexdigest(),
             "signature": hmac.new(KEY, str(stamp).encode() + b"." + body,
                                   hashlib.sha256).hexdigest()}
            for name, body, stamp in CASES]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = Path(__file__).with_name("vectors.json")
    data = (json.dumps(encoded(), indent=2, ensure_ascii=True) + "\n").encode()
    if args.check:
        assert target.read_bytes() == data, "independent vectors drifted"
        print("PASS: seven Python HMAC vectors reproduce byte-for-byte")
    else:
        assert not target.exists(), "never overwrite retained vectors"
        target.write_bytes(data)
