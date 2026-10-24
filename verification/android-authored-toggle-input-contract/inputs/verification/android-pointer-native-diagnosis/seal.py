#!/usr/bin/env python3
"""Seal all owned diagnosis files recursively, including nested receipts."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEAL = HERE / "packet-seal.json"
DOC = ROOT / "docs/android-pointer-native-diagnosis.md"


def binding(path):
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def files():
    return {str(p.relative_to(ROOT)): binding(p) for p in sorted([DOC, *(p for p in HERE.rglob("*") if p.is_file() and p != SEAL)])}


if sys.argv[1:] == ["--verify"]:
    expected = json.loads(SEAL.read_text())
    assert files() == expected["files"], "owned diagnosis seal drift or unexpected file"
    inputs = json.loads((HERE / "analysis-1/input-bindings.json").read_text())
    for name, expected_input in inputs.items():
        assert binding(ROOT / name) == expected_input, "read-only source/evidence changed: " + name
    print(json.dumps({"status": "verified", "ownedFilesIncludingNestedReceipts": len(expected["files"]), "readOnlyInputBindingsRechecked": len(inputs), "sealSHA256": binding(SEAL)["sha256"]}))
elif not sys.argv[1:]:
    assert not SEAL.exists(), "seal is immutable; use --verify"
    final = HERE / "finalization-1"
    final.mkdir(exist_ok=False)
    source = json.loads((HERE / "analysis-1/receipt.json").read_text())
    before = files()
    receipt = {"schema": 1, "status": "sealed-offline-diagnosis", "observedUTC": datetime.now(timezone.utc).isoformat(), "argv": [sys.executable, str(Path(__file__).resolve())], "python": sys.version, "sourceRevision": source["sourceRevision"], "sourceTree": source["sourceTree"], "sourceClosureSHA256": source["sourceClosureSHA256"], "sourceIdentityScope": "frozen candidate, not a live Git query", "ownedInputTreeDigestSHA256": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(), "nativeCommandsExecuted": 0, "physicalTargetsQueried": False, "readOnlyInputBindingsReceipt": "analysis-1/receipt.json", "scope": "diagnosis artifact only; no runtime acceptance or implementation correction"}
    (final / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    result = {"schema": 1, "scope": receipt["scope"], "files": files()}
    SEAL.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "sealed", "ownedFilesIncludingNestedReceipts": len(result["files"]), "sealSHA256": binding(SEAL)["sha256"]}))
else:
    raise SystemExit("usage: seal.py [--verify]")
