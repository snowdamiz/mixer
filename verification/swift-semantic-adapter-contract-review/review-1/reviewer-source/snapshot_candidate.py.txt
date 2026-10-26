#!/usr/bin/env python3
"""Copy and verify the root-authorized exact candidate without executing it."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "verification/swift-semantic-adapter-contract-review"
EXPECTED = "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba"
SEAL = ROOT / "verification/swift-semantic-adapter-prerequisite/seal.json"
DEST = OWNED / "candidate-1"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    raw = SEAL.read_bytes()
    if sha(raw) != EXPECTED:
        raise SystemExit("authorized candidate seal differs")
    seal = json.loads(raw)
    if seal["member_count"] != 152 or seal["member_bytes"] != 1_465_347:
        raise SystemExit("authorized candidate extent differs")
    DEST.mkdir(parents=True, exist_ok=False)
    (DEST / "seal.json").write_bytes(raw)
    excluded_hash = (SEAL.parent / "seal.sha256").read_bytes()
    (DEST / "seal.sha256").write_bytes(excluded_hash)
    seen = set()
    total = 0
    for item in seal["members"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or item["path"] in seen:
            raise SystemExit("invalid member path")
        if not (item["path"] == "docs/swift-semantic-adapter-prerequisite.md"
                or item["path"].startswith("verification/swift-semantic-adapter-prerequisite/")):
            raise SystemExit("member outside authorized candidate")
        seen.add(item["path"])
        source = ROOT / item["path"]
        if source.is_symlink():
            raise SystemExit("candidate symlink refused")
        data = source.read_bytes()
        if len(data) != item["bytes"] or sha(data) != item["sha256"]:
            raise SystemExit(f"candidate member mismatch: {item['path']}")
        output = DEST / "members" / item["path"]
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        if output.read_bytes() != data:
            raise SystemExit("snapshot copy mismatch")
        total += len(data)
    if len(seen) != 152 or total != 1_465_347:
        raise SystemExit("candidate totals differ")
    admission_path = ROOT / "verification/swift-semantic-adapter-root-review/preaccess-admission.json"
    admission = admission_path.read_bytes()
    (DEST / "root-preaccess-admission.json").write_bytes(admission)
    result = {"schema": 1, "at_utc": datetime.now(timezone.utc).isoformat(),
              "command": "python3 verification/swift-semantic-adapter-contract-review/snapshot_candidate.py",
              "candidate_seal_sha256": EXPECTED, "members": len(seen), "bytes": total,
              "root_admission_sha256": sha(admission), "scope": "exact source-only snapshot; no candidate helper execution",
              "preaccess_seal_sha256": "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9",
              "candidate_helpers_executed": False, "tests_executed": 0,
              "native_capture_processes_started_or_queried": False}
    (OWNED / "candidate-snapshot-receipt.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
