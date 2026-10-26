#!/usr/bin/env python3
"""Seal/check exact preaccess directory plus the owned plan; never product code."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / "manifest.json"
SIDECAR = HERE / "manifest.sha256"
PLAN = REPO / "docs/android-private-owner-implementation-review-plan.md"


def record(path):
    b = path.read_bytes()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}


def members():
    return sorted([p for p in HERE.rglob("*") if p.is_file() and p not in (MANIFEST, SIDECAR)] + [PLAN])


def main():
    if sys.argv[1:] == ["--seal"]:
        if MANIFEST.exists() or SIDECAR.exists():
            raise SystemExit("refuse to replace sealed preaccess packet")
        files = {str(p.relative_to(REPO)): record(p) for p in members()}
        value = dict(schema=1, scope="preaccess independent plan/cases/inputmap/commands only; no product execution",
                     members=len(files), bytes=sum(x["bytes"] for x in files.values()), files=files,
                     command=["python3", "-B", "verification/android-private-owner-independent-review/preaccess/seal_preaccess.py", "--seal"],
                     python_version=sys.version,
                     excluded_metadata=["manifest.json", "manifest.sha256"],
                     external_owned_document="docs/android-private-owner-implementation-review-plan.md")
        MANIFEST.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        SIDECAR.write_text(hashlib.sha256(MANIFEST.read_bytes()).hexdigest() + "  manifest.json\n")
    elif sys.argv[1:] != ["--check"]:
        raise SystemExit("expected --seal or --check")
    m = json.loads(MANIFEST.read_text())
    actual = {str(p.relative_to(REPO)): record(p) for p in members()}
    if actual != m["files"]:
        raise SystemExit("preaccess exact member closure or bytes changed")
    digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    if SIDECAR.read_text() != digest + "  manifest.json\n":
        raise SystemExit("sidecar mismatch")
    print(json.dumps(dict(status="sealed-preaccess-exact-closure-verified", members=len(actual),
                          bytes=sum(x["bytes"] for x in actual.values()), manifest_sha256=digest,
                          candidate_access=False, product_tests_run=0), sort_keys=True))


if __name__ == "__main__":
    main()
