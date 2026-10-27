#!/usr/bin/env python3
"""Seal independent pre-release requirements, not an active producer packet."""
from pathlib import Path
import datetime
import hashlib
import json

HERE = Path(__file__).resolve().parent


def main():
    seal_path = HERE / "pre-release-seal.json"
    assert not seal_path.exists(), "pre-release seal must not be replaced"
    assert not list(HERE.rglob("__pycache__")), "unexpected Python scratch"
    receipt = json.loads((HERE / "pre-release-receipt.json").read_text())
    assert receipt["all_expectations_met"] and not receipt["producer_read_or_accepted"]
    rows = [{"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size,
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(HERE.rglob("*")) if path.is_file()]
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "scope": "independent requirements and 25 finite model/host File controls before producer release; no Rust behavior/layout acceptance",
            "members": rows, "member_count": len(rows), "bytes": sum(row["bytes"] for row in rows),
            "tree_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    seal_path.write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in seal.items() if key != "members"} | {"seal_sha256": hashlib.sha256(seal_path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
