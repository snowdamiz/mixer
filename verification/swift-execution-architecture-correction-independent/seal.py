#!/usr/bin/env python3
"""Seal this independent evidence directory; never change a predecessor."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    entries = {}
    for path in sorted(HERE.rglob("*")):
        if path.is_file() and path != HERE / "seal.json":
            data = path.read_bytes()
            entries[str(path.relative_to(HERE))] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    record = {"schema": 1, "decision": "source-qualified-accept", "files": entries,
        "fileCount": len(entries), "totalBytes": sum(row["bytes"] for row in entries.values()),
        "reviewedCorrectionSealSHA256": "4efa21ab9e7bf43cec647c760bdacf6c3e5b2be944976240ec186c738370a6d2",
        "scope": "independent R1/R2 source and pure-runner review; no compile/runtime/dispatch"}
    path = HERE / "seal.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    for name, expected in record["files"].items():
        data = (HERE / name).read_bytes()
        assert len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"]
    print(json.dumps({"sealSHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "fileCount": record["fileCount"], "totalBytes": record["totalBytes"]}))


if __name__ == "__main__":
    main()
