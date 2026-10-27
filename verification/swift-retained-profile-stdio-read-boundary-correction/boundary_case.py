"""Real owned raw-file read boundaries; each case runs in a fresh bounded child."""
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

D = Path(__file__).resolve().parent
variant, name = sys.argv[1:]
assert variant in ("old", "new")
sys.path.insert(0, str(D / variant / "replay/corrected/replay"))
import prototype as p

# request size, actual file payload, maximum actual bytes per call, EINTR prefix,
# expected outcome and exact number of calls. Oracles specify the public boundary.
CASES = {
    "zero": (0, b"abc", 1, 0, b"", 0),
    "one": (1, b"abc", 1, 0, b"a", 1),
    "chunks31": (31, b"a" * 31, 1, 0, b"a" * 31, 31),
    "chunks32": (32, b"a" * 32, 1, 0, b"a" * 32, 32),
    "cap512-at32": (512, b"a" * 512, 16, 0, b"a" * 512, 32),
    "unfinished33": (33, b"a" * 33, 1, 0, "stdio-read-attempts", 32),
    "eintr31-complete32": (32, b"a" * 32, 32, 31, b"a" * 32, 32),
    "eintr32": (32, b"a" * 32, 32, 32, "stdio-read-attempts", 32),
    "eintr30-data-eof32": (512, b"abc", 512, 30, b"abc", 32),
    "eintr31-eof32": (512, b"", 512, 31, b"", 32),
    "eintr30-complete31": (32, b"a" * 32, 32, 30, b"a" * 32, 31),
    "eintr31-short32": (512, b"abc", 512, 31, "stdio-read-attempts", 32),
    "invalid-negative": (-1, b"abc", 1, 0, "stdio-read-cap", 0),
    "invalid-overcap": (513, b"abc", 1, 0, "stdio-read-cap", 0),
    "invalid-bool": (True, b"abc", 1, 0, "stdio-read-cap", 0),
    "invalid-float": (1.0, b"abc", 1, 0, "stdio-read-cap", 0),
}
size, payload, chunk, interrupts, expected, expected_calls = CASES[name]
scratch = D / "owned-scratch"
scratch.mkdir(exist_ok=True)
calls, actual_reads, requested_bytes = [], [], []
original = os.read
with tempfile.TemporaryDirectory(prefix="read-boundary-", dir=scratch) as directory:
    owner = p.RawStdio(directory)
    number = owner.fileno()
    assert os.write(number, payload) == len(payload)
    owner.seek(0)

    def bounded_read(fd, count):
        assert fd == owner.fileno() == number
        calls.append(len(calls) + 1)
        requested_bytes.append(count)
        assert len(calls) <= 32, "no 33rd attempt is allowed"
        if len(calls) <= interrupts:
            raise InterruptedError("controlled interrupted attempt")
        value = original(fd, min(count, chunk))
        actual_reads.append(len(value))
        return value

    result, error = None, None
    try:
        with patch.object(p.os, "read", bounded_read):
            result = owner.read(size)
    except p.Refusal as caught:
        error = caught.code
    finally:
        # The current successfully-opened owner alone closes its known capability.
        owner.close()
    healthy = p.ownership_snapshot()["healthy_zero"]
    assert healthy
    observed = error if error is not None else result
    passed = observed == expected and len(calls) == expected_calls
    record = {"variant": variant, "case": name, "request": size,
              "expected": expected.hex() if isinstance(expected, bytes) else expected,
              "actual": result.hex() if result is not None else error,
              "actual_kind": "bytes" if result is not None else "refusal",
              "attempts": len(calls), "expected_attempts": expected_calls,
              "actual_OS_read_lengths": actual_reads, "original_requested_bytes": requested_bytes,
              "controlled_EINTR_count": min(len(calls), interrupts),
              "required_behavior_pass": passed, "healthy_zero": healthy,
              "native_or_real_OS_ambiguity_qualification": False}
assert not list(scratch.iterdir())
print(json.dumps(record, sort_keys=True))
raise SystemExit(0 if passed else 1)
