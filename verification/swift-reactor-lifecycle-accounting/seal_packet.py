#!/usr/bin/env python3
"""Create the review seal once; never compile or run candidate code."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    destination = HERE / "seal.json"
    assert not destination.exists(), "packet is already sealed"
    receipt = json.loads((HERE / "receipt.json").read_bytes())
    files = {
        str(path.relative_to(HERE)): sha(path.read_bytes())
        for path in sorted(HERE.rglob("*"))
        if path.is_file()
    }
    value = {
        "schema": "mixer.swift-lifecycle.accounting-seal.1",
        "candidateClosure": receipt["candidateClosure"],
        "accountingAccepted": False,
        "runtimeSelected": False,
        "testBodiesExecuted": 0,
        "vmExecutions": 0,
        "closureSHA256": sha(encode(files)),
        "files": files,
    }
    destination.write_bytes(encode(value))
    print(json.dumps({"sealSHA256": sha(destination.read_bytes()),
                      "closureSHA256": value["closureSHA256"],
                      "fileCount": len(files),
                      "candidateClosure": value["candidateClosure"]},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
