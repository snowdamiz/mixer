#!/usr/bin/env python3
"""Read-only finite byte/membership audit. Never invokes a product/runtime tool."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


PACKET = Path(__file__).resolve().parent


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode()


def tree_digest(rows: list[dict]) -> str:
    return digest(encode(sorted(rows, key=lambda item: item["path"])))


def require(condition: bool, explanation: str) -> None:
    if not condition:
        raise ValueError(explanation)


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    require(bool(value) and not path.is_absolute() and ".." not in path.parts,
            f"Escaping path: {value}")
    require(path.as_posix() == value and value != ".", f"Noncanonical path: {value}")
    return value


def load(relative: str) -> dict:
    return json.loads((PACKET / relative).read_bytes())


def main() -> None:
    seal = load("freeze.json")
    require(seal["sole_excluded_packet_relative_path"] == "freeze.json", "Wrong self exclusion")
    require(seal["basename_exclusion"] is False, "Basename exclusion forbidden")
    require(seal["execution_authorized"] is False, "Unexpected runtime authorization")
    require(seal["new_product_runtime_or_fixture_processes"] == 0, "Unexpected runtime claim")
    expected = {}
    for row in seal["files"]:
        relative = safe_relative(row["path"])
        require(relative != "freeze.json" and relative not in expected, f"Duplicate/self path: {relative}")
        expected[relative] = row
    actual = set()
    for path in PACKET.rglob("*"):
        require(not path.is_symlink(), f"Symlink forbidden: {path}")
        if path.is_file():
            relative = path.relative_to(PACKET).as_posix()
            if relative != "freeze.json":
                actual.add(relative)
    require(actual == set(expected), f"Membership mismatch: extra={sorted(actual-set(expected))}, missing={sorted(set(expected)-actual)}")
    for relative, row in expected.items():
        data = (PACKET / relative).read_bytes()
        require(row["bytes"] == len(data) and row["sha256"] == digest(data), f"Byte/hash mismatch: {relative}")
    require(tree_digest(seal["files"]) == seal["packet_tree_sha256"], "Packet tree mismatch")
    sources = load("source-bindings.json")
    source_rows = []
    seen_snapshots = set()
    for row in sources["sources"]:
        relative = safe_relative(row["snapshot"])
        require(relative not in seen_snapshots, f"Duplicate source snapshot: {relative}")
        seen_snapshots.add(relative)
        require(relative in expected, f"Unsealed source snapshot: {relative}")
        data = (PACKET / relative).read_bytes()
        require(row["bytes"] == len(data) and row["sha256"] == digest(data), f"Source pin mismatch: {relative}")
        require(row["line_count"] == len(data.splitlines()), f"Source line-count mismatch: {relative}")
        for start, end in row["reviewed_line_ranges"]:
            require(1 <= start <= end <= row["line_count"], f"Source range invalid: {relative}")
        source_rows.append({"path": relative, "bytes": row["bytes"], "sha256": row["sha256"]})
        if "upstream_pin" in row:
            pin = row["upstream_pin"]
            upstream = load(safe_relative(pin["manifest_snapshot"]))
            matches = [entry for entry in upstream["files"] if entry["path"] == pin["manifest_path"]]
            require(len(matches) == 1, f"Ambiguous/missing upstream pin: {relative}")
            require(matches[0]["bytes"] == row["bytes"] and matches[0]["sha256"] == row["sha256"],
                    f"Upstream pin mismatch: {relative}")
    require(tree_digest(source_rows) == sources["selected_source_tree_sha256"] == seal["selected_source_tree_sha256"], "Selected-source tree mismatch")
    tests = load("prospective-tests.json")
    proposal = load("execution-proposal.json")
    audit = load("audit.json")
    evidence = load("reviewed-evidence.json")
    require(tests["execution_authorized_by_this_packet"] is False, "Tests grant execution")
    require([case["id"] for case in tests["tests"]] == ["KOL08-GRACEFUL", "KOL09-KILL"], "Unexpected prospective methods")
    require(tests["finite_method_count"] == 2 and proposal["prospective_invocation_shape"]["fixed_test_count"] == 2, "Count mismatch")
    require(proposal["execution_authorized"] is False and proposal["new_product_or_test_source_implemented"] is False,
            "Unexpected implementation or release claim")
    require(proposal["bounds"]["wall_seconds"] == 55 and proposal["bounds"]["automatic_retries"] == 0,
            "Unexpected prospective execution bound")
    require(proposal["network_scope"]["dns_fixture"] is False and proposal["network_scope"]["external_provider"] is False,
            "Unexpected network proposal scope")
    require(audit["new_product_runtime_or_fixture_processes"] == 0 and evidence["new_behavioral_tests_run"] == 0,
            "Unexpected local runtime claim")
    print(json.dumps({
        "status": "PASS-source-only-finite-packet-integrity",
        "command": ["python3", "-B", str(PACKET / "verify_packet.py")],
        "python_version": sys.version,
        "sealed_files_excluding_exact_terminal_seal": len(expected),
        "copied_upstream_freeze_files_included": sorted(path for path in expected if path.endswith("/freeze.json")),
        "selected_source_files": len(source_rows),
        "selected_source_tree_sha256": tree_digest(source_rows),
        "packet_tree_sha256": seal["packet_tree_sha256"],
        "freeze_sha256": digest((PACKET / "freeze.json").read_bytes()),
        "runtime_acceptance": False,
        "execution_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
