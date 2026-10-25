#!/usr/bin/env python3
"""Hash selected producer seals without importing or executing their inputs."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "producer-seal-audit.json"
if OUTPUT.exists():
    raise SystemExit("preserve prior audit; choose a new explicit output before rerunning")
records = []
for name in ["seal.json", "correction-seal.json"]:
    source = ROOT / "verification/hosted-customer-authorization-postgres" / name
    data = json.loads(source.read_text())
    mismatches = []
    for relative, expected in data["files"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            raise SystemExit("seal contains an out-of-workspace path")
        if not (relative.startswith("verification/hosted-customer-authorization-postgres/")
                or relative.startswith("docs/hosted-customer-authorization-postgres")):
            raise SystemExit("seal contains an unselected source path: " + relative)
        observed = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if observed != expected:
            mismatches.append({"path": relative, "expected": expected, "observed": observed})
    manifest_digest = hashlib.sha256(json.dumps(data["files"], sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest()
    records.append({
        "path": str(source.relative_to(ROOT)),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "file_count": len(data["files"]),
        "mismatches": mismatches,
        "manifest_sha256": manifest_digest,
        "manifest_matches": manifest_digest == data["manifest_sha256"],
        "live_input_bindings": data.get("live_input_bindings", {}),
        "live_binding_note": "Historical seal bindings describe that source freeze; later coordinated integration edits are reviewed separately."
    })
    target = HERE / "producer-seals" / name
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, target)
passed = all(not record["mismatches"] and record["manifest_matches"] for record in records)
OUTPUT.write_text(json.dumps({
    "status": "passed" if passed else "failed",
    "command": ["python3", str(Path(__file__).resolve())],
    "records": records,
    "scope": "Archived baseline and correction seal contents only; no source or database execution and no claim that historical source bindings equal later integration edits."
}, indent=2) + "\n")
print(json.dumps({"status": "passed" if passed else "failed",
                  "file_counts": [record["file_count"] for record in records],
                  "mismatch_counts": [len(record["mismatches"]) for record in records],
                  "manifest_matches": [record["manifest_matches"] for record in records]}))
raise SystemExit(0 if passed else 1)
