#!/usr/bin/env python3
"""Pure expected-state oracle, independent of Elixir source and producer tests.

This checks the coherence of a finite contract truth table. It does not execute
or validate the product and deliberately models only serial owner transitions.
"""
from dataclasses import dataclass
from itertools import product
import hashlib
import json
from pathlib import Path
import sys
import time


@dataclass(frozen=True)
class Table:
    identity: str
    creator: str
    alive: bool


def expected_close(pointer, expected, caller, tables):
    table = tables.get(expected)
    allowed = pointer == expected and table is not None and table.alive and table.creator == caller
    return (None if allowed else pointer), bool(allowed)


def main():
    start = time.monotonic()
    rows = []
    for pointer_mode, alive, caller_owns in product(("absent", "different", "exact"), (False, True), (False, True)):
        pointer = {"absent": None, "different": "replacement", "exact": "old"}[pointer_mode]
        creator = "caller" if caller_owns else "foreign"
        tables = {"old": Table("old", creator, alive), "replacement": Table("replacement", "replacement_owner", True)}
        after, result = expected_close(pointer, "old", "caller", tables)
        expected_result = pointer_mode == "exact" and alive and caller_owns
        assert result is expected_result
        assert after == (None if expected_result else pointer)
        assert tables["replacement"].alive
        assert tables["old"].alive is alive
        rows.append({"pointer": pointer_mode, "expected_alive": alive, "caller_owns": caller_owns, "result": result, "pointer_after": after})
    for malformed in (None, "not-a-table", 123):
        assert expected_close(malformed, malformed, "caller", {}) == (malformed, False)
    tables = {"old": Table("old", "caller", True)}
    pointer, result = expected_close("old", "old", "caller", tables)
    assert result is True and pointer is None and tables["old"].alive
    assert expected_close(pointer, "old", "caller", tables) == (None, False)

    # Table identity is the first stale-permit fence, before any old-table lookup.
    def permit_valid(permit_table, current_table, lookup):
        if permit_table != current_table:
            return False
        return lookup()

    def forbidden_old_lookup():
        raise AssertionError("stale table must not be inspected after identity mismatch")

    assert permit_valid("old", "replacement", forbidden_old_lookup) is False
    # A stale release addresses its table+nonce only and cannot consume a fresh slot.
    slots = {("replacement", "global", "fresh_nonce"), ("replacement", "profile", "fresh_nonce")}
    slots.difference_update({("old", "global", "old_nonce"), ("old", "profile", "old_nonce")})
    assert slots == {("replacement", "global", "fresh_nonce"), ("replacement", "profile", "fresh_nonce")}
    # The contract requires closure before replies/drain; no real process is run.
    required_order = ["trap_exit", "publish", "close", "waiter_reply", "drain", "owner_down", "restart_publish"]
    assert required_order.index("trap_exit") < required_order.index("publish")
    assert required_order.index("close") < required_order.index("waiter_reply") < required_order.index("drain")
    assert required_order.index("owner_down") < required_order.index("restart_publish")
    assert time.monotonic() - start < 55
    output = {
        "schema": 1,
        "status": "passed-independent-expected-state-oracle-only",
        "python": sys.version,
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/offline_oracle.py",
        "source_file_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "close_truth_table_rows": rows,
        "checks": {"close_combinations": len(rows), "malformed_expected_values": 3, "close_idempotence": True, "stale_lookup_not_called": True, "stale_release_preserves_new_slots": True, "required_order_encoded": True},
        "product_runtime_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - start, 6),
        "limitation": "Contract oracle only; no BEAM, ETS, OTP, producer source/tests, compiler, process, DB, socket, native, UI or GA verification."
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
