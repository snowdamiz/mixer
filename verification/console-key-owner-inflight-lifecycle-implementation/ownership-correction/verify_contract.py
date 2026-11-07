#!/usr/bin/env python3
"""Read-only byte/membership check for the proposed ownership contract."""
import hashlib
import json
from pathlib import Path


def main():
    packet = Path(__file__).resolve().parent
    digest = lambda data: hashlib.sha256(data).hexdigest()
    encoded = lambda value: (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()
    seal = json.loads((packet / "freeze.json").read_bytes())
    assert seal["sole_excluded_relative_path"] == "freeze.json"
    rows = seal["files"]
    expected = {row["path"] for row in rows}
    assert len(expected) == len(rows)
    actual = set()
    for path in packet.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(packet).as_posix() != "freeze.json":
            actual.add(path.relative_to(packet).as_posix())
    assert actual == expected
    for row in rows:
        assert not Path(row["path"]).is_absolute() and ".." not in Path(row["path"]).parts
        data = (packet / row["path"]).read_bytes()
        assert len(data) == row["bytes"] and digest(data) == row["sha256"], row["path"]
    assert digest(encoded(rows)) == seal["tree_sha256"]
    binding = json.loads((packet / "source-bindings.json").read_bytes())
    source_rows = []
    for row in binding["sources"]:
        data = (packet / row["snapshot"]).read_bytes()
        assert len(data) == row["bytes"] and digest(data) == row["sha256"]
        source_rows.append({"path": row["snapshot"], "bytes": row["bytes"], "sha256": row["sha256"]})
    assert digest(encoded(sorted(source_rows, key=lambda row: row["path"]))) == binding["selected_source_tree_sha256"] == seal["selected_source_tree_sha256"]
    protocol = json.loads((packet / "protocol.json").read_bytes())
    assert protocol["implementation_authorized"] is False and protocol["execution_authorized"] is False
    assert seal["implementation_authorized"] is False and seal["execution_authorized"] is False
    assert protocol["bounds"]["native_grants_max"] == 7 and protocol["bounds"]["receipt_seconds"] == 55
    print(json.dumps({"status": "PASS-offline-source-ownership-contract-integrity-only", "files": len(rows),
        "source_snapshots": len(source_rows), "freeze_sha256": digest((packet / "freeze.json").read_bytes()),
        "implementation_authorized": False, "execution_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
