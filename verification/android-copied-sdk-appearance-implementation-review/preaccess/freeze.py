#!/usr/bin/env python3
"""Seal the review baseline; never replace a sealed preaccess plan."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[2]


def identity(data: bytes) -> dict:
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main() -> None:
    target = PACKET / "seal.json"
    if target.exists():
        raise SystemExit("baseline already sealed; refuse overwrite")
    doc = ROOT / "docs/android-copied-sdk-appearance-implementation-review.md"
    shutil.copyfile(doc, PACKET / "plan.md")
    baseline = json.loads((PACKET / "input-manifest.json").read_text())
    for path, expected in baseline["accepted_source_files"].items():
        assert identity((PACKET / "accepted-source" / path).read_bytes()) == expected, path
    for path, expected in baseline["selected_contracts"].items():
        assert identity((PACKET / "selected-inputs" / path).read_bytes()) == expected, path
    receipt = {
        "schema": 1, "at": datetime.now(timezone.utc).isoformat(),
        "status": "preaccess-control-plan-and-accepted-baseline-frozen-awaiting-root-handoff",
        "selection_sha256": "cb191b996f00752c4cad3a4c1df7314bcfe72b00b1f75be29a2f6e4301821917",
        "accepted_source_revision": baseline["accepted_source_revision"],
        "accepted_source_tree": baseline["accepted_source_tree"],
        "accepted_source_files": len(baseline["accepted_source_files"]),
        "plan": identity((PACKET / "plan.md").read_bytes()),
        "candidate_accessed": False, "candidate_execution_started": False,
        "native_or_capture_or_ui_started": False, "process_discovery_performed": False,
        "product_edited": False, "compiler_started": False,
        "implementation_accepted": False, "GA_qualified": False,
        "pending_controls": [f"P{i:02d}" for i in range(1,17)],
        "command": ["python3", "-B", str(Path(__file__).relative_to(ROOT))],
        "failures_preserved": ["preparation-failures.json", "failed-attempt-1/"],
        "cleanup": "No owned runtime/scratch or child remains; only copied immutable inputs and evidence files created."
    }
    (PACKET / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    files = {}
    for path in sorted(PACKET.rglob("*")):
        if path.is_file():
            files[str(path.relative_to(ROOT))] = identity(path.read_bytes())
    seal = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
            "scope": "immutable preaccess plan and accepted Git baseline only",
            "files": files}
    target.write_text(json.dumps(seal, indent=2) + "\n")
    print(json.dumps({"seal": str(target.relative_to(ROOT)), "seal_identity": identity(target.read_bytes()),
                      "members": len(files), "bytes": sum(item["bytes"] for item in files.values()),
                      "plan": receipt["plan"], "candidate_accessed": False}, indent=2))


if __name__ == "__main__":
    main()
