#!/usr/bin/env python3
"""Independent strict finite source-contract audit; no producer execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKET = REPO / "verification/console-key-owner-inflight-lifecycle-contract"
INDEPENDENT = OUT.parent


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            chunk = stream.read(262144)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result, "duplicate JSON key"
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def check(path, row):
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]


def tree(rows):
    return hashlib.sha256((json.dumps(sorted(rows, key=lambda row: row["path"]), indent=2) + "\n").encode()).hexdigest()


def main():
    assert sha(INDEPENDENT / "preaccess-seal.json") == "5eefedd3a222e31c5d580e48bfd22e41de6422ef185744e1cf7ae4f722956d4f"
    preaccess = read(INDEPENDENT / "preaccess-seal.json")
    assert len(preaccess["files"]) == 24
    for row in preaccess["files"]:
        check(INDEPENDENT / row["path"], row)
    assert sha(PACKET / "freeze.json") == "dcf68267fbfe7d495f0cf92de97e2a46f140d1c9bd8f5a353bebacadf66ce276"
    seal = read(PACKET / "freeze.json")
    sealed = set()
    for row in seal["files"]:
        relative = row["path"]
        parsed = PurePosixPath(relative)
        assert relative and str(parsed) == relative and not parsed.is_absolute() and ".." not in parsed.parts
        assert relative not in sealed and relative != "freeze.json"
        sealed.add(relative)
        check(PACKET / relative, row)
    actual = set()
    for path in PACKET.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PACKET).as_posix() != "freeze.json":
            actual.add(path.relative_to(PACKET).as_posix())
    assert sealed == actual and len(sealed) == 39
    assert tree(seal["files"]) == seal["packet_tree_sha256"]
    assert seal["sole_excluded_packet_relative_path"] == "freeze.json" and seal["basename_exclusion"] is False
    sources = read(PACKET / "source-bindings.json")
    rows = []
    seen = set()
    upstream_count = 0
    for source in sources["sources"]:
        assert source["snapshot"] in sealed and source["snapshot"] not in seen
        seen.add(source["snapshot"])
        snapshot = PACKET / source["snapshot"]
        check(snapshot, source)
        check(REPO / source["origin"], source)
        assert len(snapshot.read_bytes().splitlines()) == source["line_count"]
        for first, last in source["reviewed_line_ranges"]:
            assert 1 <= first <= last <= source["line_count"]
        rows.append({"path": source["snapshot"], "bytes": source["bytes"], "sha256": source["sha256"]})
        if "upstream_pin" in source:
            pin = source["upstream_pin"]
            upstream = read(PACKET / pin["manifest_snapshot"])
            matches = [item for item in upstream["files"] if item["path"] == pin["manifest_path"]]
            assert len(matches) == 1 and matches[0]["bytes"] == source["bytes"] and matches[0]["sha256"] == source["sha256"]
            upstream_count += 1
    assert len(rows) == 30
    assert tree(rows) == sources["selected_source_tree_sha256"] == seal["selected_source_tree_sha256"] == "26bcf0c17615df28008abbf93a25f47b88b636c7a75132fedf90564dbeb0a8ae"
    tests = read(PACKET / "prospective-tests.json")
    proposal = read(PACKET / "execution-proposal.json")
    assert [case["id"] for case in tests["tests"]] == ["KOL08-GRACEFUL", "KOL09-KILL"]
    assert tests["finite_method_count"] == 2 and tests["execution_authorized_by_this_packet"] is False
    assert proposal["execution_authorized"] is False and proposal["new_product_or_test_source_implemented"] is False
    assert proposal["bounds"]["wall_seconds"] == 55 and proposal["bounds"]["automatic_retries"] == 0
    assert proposal["network_scope"]["completed_jwks_fetch_claim"] is False
    source_supervisor = PACKET / "inputs/prepared-3/key_owner_supervisor.ex"
    assert "start_fixture" not in source_supervisor.read_text()
    tls = (PACKET / "inputs/current-support/identity_tls_fixture.ex").read_text()
    assert ':ssl.handshake(socket, 3_000)' in tls and 'send(recipient, {:tls_response_ready, self()})' in tls
    result = {
        "schema": 1,
        "status": "passed-independent-source-contract-integrity-runtime-unexecuted",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-independent/review-1/audit_contract.py",
        "python": sys.version,
        "script_sha256": sha(Path(__file__)),
        "preaccess_seal_sha256": sha(INDEPENDENT / "preaccess-seal.json"),
        "producer_freeze_sha256": sha(PACKET / "freeze.json"),
        "source_revision": sources["source_revision"],
        "selected_source_tree_sha256": tree(rows),
        "verified": {"producer_members": len(sealed), "source_inputs": len(rows), "upstream_source_pins": upstream_count, "preaccess_members_unchanged": 24, "all_source_origins_currently_equal_snapshots": True, "exact_membership_includes_copied_upstream_freezes": True, "strict_json_duplicate_nonfinite_rejection": True, "canonical_relative_paths_no_symlinks": True, "two_new_methods_only": True, "constructor_not_yet_implemented": True},
        "root_amendments_for_future_exact_implementation_plan": ["Reuse existing seven KOL01-KOL07 regressions with two new methods: nine executed cases, two new cases", "Both fixture constructor and tuple init dispatch must be unavailable in production builds", "Zero compiler warnings; retain narrowly classified intentional-kill OTP reports; callback exceptions fail cleanup gate"],
        "recommend_narrow_source_implementation": True,
        "runtime_release_recommended_by_source_contract_alone": False,
        "product_runtime_verified": False,
        "producer_code_imported_or_executed": False,
        "runtime_compiler_formatter_fixture_version_processes": 0,
        "global_process_inventory": False,
        "elapsed_seconds": round(time.monotonic() - START, 6),
        "scope": "Source contract acceptance for dependent constructor/tests implementation only; no runtime or product lifecycle acceptance."
    }
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
