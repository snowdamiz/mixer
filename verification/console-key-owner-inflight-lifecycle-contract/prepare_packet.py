#!/usr/bin/env python3
"""Freeze this finite source-only contract. This script starts no product tool."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parent.parent
OLD = "verification/console-key-owner-lifecycle-contract"
PREPARED = "verification/console-key-owner-lifecycle-implementation/prepared-3"
SCOPE = (
    "Offline source reads, snapshots, SHA-256 and JSON/membership checks only; "
    "no compiler, formatter, Elixir/BEAM, product tests, TLS/DNS fixture, network, "
    "DB, product application, global process inventory, native/UI/capture, "
    "central metadata, commit or push."
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=False) + "\n").encode()


def write(relative: str, data: bytes) -> None:
    path = PACKET / relative
    if path.exists():
        raise RuntimeError(f"Refusing to replace packet artifact: {relative}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def tree_digest(rows: list[dict]) -> str:
    return digest(encode(sorted(rows, key=lambda item: item["path"])))


def main() -> None:
    if (PACKET / "freeze.json").exists():
        raise RuntimeError("Packet is already frozen")

    prepared_seal = json.loads((ROOT / PREPARED / "freeze.json").read_bytes())
    prepared_pins = {item["path"]: item for item in prepared_seal["files"]}
    old_seal = json.loads((ROOT / OLD / "membership-amendment.json").read_bytes())
    old_pins = {item["path"]: item for item in old_seal["files"]}
    rows = []

    def snapshot(origin: str, target: str, role: str, ranges: list,
                 pin_kind: str | None = None, pin_path: str | None = None) -> None:
        source = ROOT / origin
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"Source is not an ordinary file: {origin}")
        data = source.read_bytes()
        row = {
            "origin": origin,
            "snapshot": target,
            "role": role,
            "bytes": len(data),
            "sha256": digest(data),
            "line_count": len(data.splitlines()),
            "reviewed_line_ranges": ranges,
        }
        if pin_kind:
            pins = prepared_pins if pin_kind == "prepared-3" else old_pins
            pin = pins[pin_path]
            assert pin["bytes"] == len(data) and pin["sha256"] == digest(data), origin
            row["upstream_pin"] = {
                "manifest_snapshot": "inputs/prepared-3/freeze.json" if pin_kind == "prepared-3"
                else "inputs/existing-contract/membership-amendment.json",
                "manifest_path": pin_path,
                "matched_at_snapshot": True,
            }
        assert source.read_bytes() == data, f"Source changed during snapshot: {origin}"
        write(target, data)
        rows.append(row)

    snapshot("AGENTS.md", "inputs/current-root/AGENTS.md", "binding local execution rules", [[1, 55]])
    snapshot(f"{PREPARED}/freeze.json", "inputs/prepared-3/freeze.json",
             "immutable selected candidate manifest; preparation status only", [])
    snapshot(f"{OLD}/membership-amendment.json", "inputs/existing-contract/membership-amendment.json",
             "complete upstream source-only contract membership seal", [])

    for name in ["contract.md", "prospective-tests.json", "official-docs.json", "membership-amendment.md", "freeze.json"]:
        snapshot(f"{OLD}/{name}", f"inputs/existing-contract/{name}",
                 "prior lifecycle contract or retained documentation/membership evidence", [], "existing-contract", name)
    snapshot(f"{OLD}/inputs/mixer-product-plan.md", "inputs/existing-contract/mixer-product-plan.md",
             "binding product scope excerpts", [[490, 498], [610, 616], [628, 634]],
             "existing-contract", "inputs/mixer-product-plan.md")
    snapshot(f"{PREPARED}/formatting-correction-amendment.json",
             "inputs/prepared-3/formatting-correction-amendment.json",
             "prior formatting failure and immutable candidate preparation provenance", [],
             "prepared-3", "formatting-correction-amendment.json")

    modules = {
        "key_owner.ex": [[12, 17], [43, 96], [112, 179], [299, 377], [428, 498]],
        "admission.ex": [[5, 38], [47, 82]],
        "key_owner_supervisor.ex": [[1, 18]],
        "fetch_flight.ex": [[7, 85], [90, 170], [173, 202]],
        "jwks_transport.ex": [[10, 101], [104, 149]],
        "bounded_tcp.ex": [[8, 43], [86, 124]],
        "dns_resolver.ex": [[5, 39], [82, 95]],
        "global_address.ex": [[6, 46]],
        "manifest.ex": [[17, 25], [51, 58]],
        "configured_verifier.ex": [[13, 61]],
    }
    for name, ranges in modules.items():
        relative = f"inputs/hosted/lib/mixer_hosted/identity/{name}"
        snapshot(f"{PREPARED}/{relative}", f"inputs/prepared-3/{name}",
                 "selected immutable identity source; source conclusions only", ranges,
                 "prepared-3", relative)
    relative = "inputs/hosted/test/mixer_hosted/identity/key_owner_lifecycle_test.exs"
    snapshot(f"{PREPARED}/{relative}", "inputs/prepared-3/key_owner_lifecycle_test.exs",
             "seven finite socket-free lifecycle methods; no execution here", [[1, 167], [169, 419]],
             "prepared-3", relative)

    for name, relative, ranges in [
        ("key_owner_test.exs", "inputs/hosted/test/mixer_hosted/identity/key_owner_test.exs", [[18, 93], [834, 943]]),
        ("startup_lifecycle_test.exs", "inputs/hosted/test/mixer_hosted/identity/startup_lifecycle_test.exs", [[158, 194]]),
        ("identity_component_fixture.ex", "inputs/hosted/test/support/identity_component_fixture.ex", [[1, 19]]),
    ]:
        snapshot(f"{OLD}/{relative}", f"inputs/existing-tests/{name}",
                 "retained existing test/source distinction; not a new run", ranges,
                 "existing-contract", relative)

    for name, ranges in [
        ("identity_tls_fixture.ex", [[7, 19], [124, 161], [171, 263], [265, 289]]),
        ("identity_raw_fixture.ex", [[7, 100]]),
    ]:
        snapshot(f"hosted/test/support/{name}", f"inputs/current-support/{name}",
                 "read-only support inventory; exact current bytes frozen without execution", ranges)

    for name in ["fixture-lifecycle-audit-v5.json", "candidate-4/failure-analysis.json",
                 "candidate-6/execution/exunit-result.json", "candidate-6/execution/component-cleanup.json"]:
        relative = f"inputs/verification/console-dispatcher-default-authority-slice/{name}"
        target_name = name.replace("/execution/", "/")
        snapshot(f"{OLD}/{relative}", f"inputs/existing-evidence/{target_name}",
                 "retained historical scope/cleanup evidence; not new runtime acceptance", [],
                 "existing-contract", relative)

    source_rows = [{"path": row["snapshot"], "bytes": row["bytes"], "sha256": row["sha256"]} for row in rows]
    commands = [
        {"argv": ["git", "--version"], "output": subprocess.check_output(["git", "--version"], cwd=ROOT, text=True).strip()},
        {"argv": ["git", "rev-parse", "HEAD"], "output": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()},
        {"argv": ["git", "rev-parse", "HEAD^{tree}"], "output": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()},
    ]
    write("source-bindings.json", encode({
        "schema": 1,
        "scope": SCOPE,
        "source_revision": commands[1]["output"],
        "committed_git_tree": commands[2]["output"],
        "source_tree_digest_method": "SHA-256 of newline-terminated JSON of sorted path/bytes/sha256 rows, indent=2",
        "selected_source_tree_sha256": tree_digest(source_rows),
        "python_version": sys.version,
        "git_commands": commands,
        "source_review_commands": "Read-only rg, nl -ba, sed and cat; exact reviewed line ranges and source output bytes retained below. No product command executed.",
        "sources": rows,
    }))
    tests = json.loads((PACKET / "prospective-tests.json").read_bytes())
    proposal = json.loads((PACKET / "execution-proposal.json").read_bytes())
    assert tests["execution_authorized_by_this_packet"] is False
    assert [item["id"] for item in tests["tests"]] == ["KOL08-GRACEFUL", "KOL09-KILL"]
    assert tests["finite_method_count"] == 2
    assert proposal["execution_authorized"] is False
    assert proposal["bounds"]["wall_seconds"] == 55
    assert proposal["new_product_or_test_source_implemented"] is False
    for row in rows:
        for start, end in row["reviewed_line_ranges"]:
            assert 1 <= start <= end <= row["line_count"], row["snapshot"]
    output = {
        "schema": 1,
        "status": "source-only-preparation-checks-passed-no-runtime-acceptance",
        "command": ["python3", "-B", str(PACKET.relative_to(ROOT) / "prepare_packet.py")],
        "cwd": str(ROOT),
        "python_version": sys.version,
        "selected_source_files": len(rows),
        "selected_source_tree_sha256": tree_digest(source_rows),
        "all_selected_upstream_pins_match": True,
        "all_source_ranges_in_bounds": True,
        "finite_prospective_method_count": 2,
        "execution_authorized": False,
        "new_product_runtime_or_fixture_processes": 0,
        "scope": SCOPE,
        "output": "Selected source snapshots and prospective contract JSON checked; runtime, syntax, compile, transport and lifecycle behavior remain untested here.",
    }
    write("audit.json", encode(output))
    files = []
    for path in sorted(PACKET.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Symlink forbidden: {path}")
        if path.is_file():
            relative = path.relative_to(PACKET).as_posix()
            assert relative != "freeze.json"
            data = path.read_bytes()
            files.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
    write("freeze.json", encode({
        "schema": 1,
        "status": "frozen-finite-source-only-contract-not-runtime-acceptance",
        "sole_excluded_packet_relative_path": "freeze.json",
        "basename_exclusion": False,
        "files": files,
        "packet_tree_digest_method": "SHA-256 of newline-terminated JSON of sorted path/bytes/sha256 rows, indent=2",
        "packet_tree_sha256": tree_digest(files),
        "selected_source_tree_sha256": tree_digest(source_rows),
        "execution_authorized": False,
        "new_product_runtime_or_fixture_processes": 0,
    }))
    print(json.dumps({"status": output["status"], "selected_source_files": len(rows),
                      "frozen_files": len(files), "selected_source_tree_sha256": tree_digest(source_rows),
                      "packet_tree_sha256": tree_digest(files)}, indent=2))


if __name__ == "__main__":
    main()
