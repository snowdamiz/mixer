#!/usr/bin/env python3
"""Independent strict read-only audit of the accepted contract packet."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def main():
    started = time.monotonic()
    repo = Path(__file__).resolve().parents[2]
    packet = repo / "verification/console-key-owner-lifecycle-contract"
    expected_amendment = "6291f022b841804797a4431c6d3af9853fac4d11db549975b1386ea664ced5da"
    expected_original = "85f2376f7f8ba7628890336f08e2dc59935dce922da2f8f908b940e08452f752"
    sha = lambda data: hashlib.sha256(data).hexdigest()
    amendment_bytes = (packet / "membership-amendment.json").read_bytes()
    assert sha(amendment_bytes) == expected_amendment
    amendment = json.loads(amendment_bytes, object_pairs_hook=strict_object)
    assert amendment["sole_excluded_packet_relative_path"] == "membership-amendment.json"
    assert amendment["original_freeze_sha256"] == expected_original
    original_bytes = (packet / "freeze.json").read_bytes()
    assert sha(original_bytes) == expected_original
    original = json.loads(original_bytes, object_pairs_hook=strict_object)
    sealed = {}
    for entry in amendment["files"]:
        relative = entry["path"]
        parsed = PurePosixPath(relative)
        assert isinstance(relative, str) and relative and not parsed.is_absolute()
        assert ".." not in parsed.parts and str(parsed) == relative
        assert relative != "membership-amendment.json" and relative not in sealed
        path = packet / relative
        assert path.is_file() and not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == entry["bytes"] and sha(data) == entry["sha256"]
        sealed[relative] = entry
    actual = set()
    for path in packet.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(packet).as_posix() != "membership-amendment.json":
            actual.add(path.relative_to(packet).as_posix())
    assert actual == set(sealed)
    assert len(sealed) == 33
    tree = sha("".join(item["path"] + "\0" + item["sha256"] + "\n" for item in sorted(amendment["files"], key=lambda x: x["path"])).encode())
    assert tree == amendment["packet_tree_sha256"]
    for original_entry in original["files"]:
        assert sealed[original_entry["path"]] == original_entry
    upstream = "inputs/verification/console-dispatcher-default-authority-slice/freeze.json"
    assert sealed[upstream]["sha256"] == "3700d4fd7f89a52de22967e510289745f8ed8aad3bbf7ff7e0a0c2fa88a9fa33"
    assert len(original["files"]) == 28
    assert time.monotonic() - started < 55
    output = {
        "schema": 1,
        "status": "passed-independent-contract-membership-only",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/audit_contract.py",
        "python": sys.version,
        "source_file_sha256": sha(Path(__file__).read_bytes()),
        "accepted_source_revision": amendment["source_revision"],
        "accepted_source_git_tree": amendment["source_git_tree"],
        "accepted_source_tree_sha256": amendment["source_tree_sha256"],
        "amendment_sha256": expected_amendment,
        "original_freeze_sha256": expected_original,
        "membership_count": len(sealed),
        "packet_tree_sha256": tree,
        "checks": {"exact_membership": True, "strict_duplicate_json_keys": True, "canonical_relative_paths": True, "no_symlinks": True, "original_28_members_preserved": True, "original_membership_omission_preserved": True, "copied_upstream_seal_included": True},
        "product_runtime_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "scope": "Read-only accepted contract integrity; no modified canonical product or implementation lane access, no Elixir/runtime/compiler/network/native/UI/process inventory."
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
