#!/usr/bin/env python3
"""Seal this independent review; execute only its source/model and packet checks."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs/android-api28-v2-support-prerequisite-review.md"


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


receipt = json.loads((HERE / "receipt.json").read_text())
receipt["commands"] = []
commands = [
    [sys.executable, str(HERE / "check_review.py")],
    [sys.executable, str(ROOT / "verification/android-api28-v2-support-prerequisite/check_packet.py"), "--manifest"],
]
for number, command in enumerate(commands, 1):
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    for stream in ("stdout", "stderr"):
        (HERE / f"command-{number}.{stream}.txt").write_text(getattr(completed, stream))
    receipt["commands"].append({"argv": command, "cwd": str(ROOT), "exit_code": completed.returncode,
                                "stdout": f"command-{number}.stdout.txt", "stderr": f"command-{number}.stderr.txt"})
    if completed.returncode:
        write_json(HERE / "receipt.json", receipt)
        raise SystemExit("review check failed: " + str(command))

parsed = []
for path in sorted(HERE.glob("*.py")):
    ast.parse(path.read_text(), filename=str(path))
    parsed.append(str(path.relative_to(ROOT)))
for path in [DOC, *HERE.glob("*.py")]:
    raw = path.read_bytes()
    assert raw.endswith(b"\n"), str(path)
    assert all(line.rstrip(b" \t") == line for line in raw.splitlines()), str(path)

receipt.update({
    "at_utc": datetime.now(timezone.utc).isoformat(),
    "seal_command": [sys.executable, str(Path(__file__).resolve())],
    "tools": {"python": sys.version, "python_executable": sys.executable, "platform": platform.platform()},
    "AST_parse": {"paths": parsed, "scope": "Python source syntax only"},
    "checks": {"source_contract": "passed", "producer_manifest": "passed", "nine_sdk_rows": 9,
               "official_sdk_symbols": 34, "independent_model_rejections": 55, "independent_model_positives": 4},
    "web_evidence": "official-reference-review.json",
    "decision": "accepted-prerequisite-contract-for-root-selection-of-bounded-A",
})
write_json(HERE / "receipt.json", receipt)

write_json(HERE / "acceptance.json", {
    "schema": 1,
    "decision": "accepted-prerequisite-contract-for-root-selection-of-bounded-A",
    "blocking_findings": [],
    "candidate_manifest_sha256": "7a006a00ed71e014efb9e854fe36b7fcacc09dd5bccae101a193d042407323ad",
    "candidate_sealed_members": 46,
    "candidate_frozen_sources": 28,
    "source_map_sha256": "276bdb5d0285cd77ecbd5306efa4eacf4fc72798768210c17662816deda709b3",
    "report": {"path": str(DOC.relative_to(ROOT)), **identity(DOC)},
    "conditions": [
        "Retain both API36 guards and V1 Activity routing; add zero admitted contexts.",
        "API28-safe base types with separate guarded API30/31/34/36 adapters; no linkage proof inferred.",
        "Only KNOWN has a value; select stricter exact observation rules and preserve fatal precedence.",
        "Allocate exact-target listener handle before add can reenter or throw; retain eight-slot observer ownership.",
        "Preserve capture authority, second complete read, lifecycle and successful commit-to-finish interval.",
        "Root selects final immutable source-pair/profile identity and final bytes receive independent implementation review.",
        "Native/compiler/runtime/public/FieldLog/OTA/store/operations/GA gates remain pending as specified.",
    ],
    "product_implementation_accepted": False,
    "root_source_profile_selected": False,
    "public_V2_selected": False,
    "new_rendering_contexts_admitted": False,
    "native_qualification": False,
    "GA_qualified": False,
    "OTA_authorized": False,
})

members = sorted(p for p in HERE.rglob("*") if p.is_file() and p.name != "manifest.json") + [DOC]
manifest = {"schema": 1, "scope": "Independent source/contract review only; no native authority.",
            "files": {str(p.relative_to(ROOT)): identity(p) for p in members}}
write_json(HERE / "manifest.json", manifest)
for relative, expected in manifest["files"].items():
    assert identity(ROOT / relative) == expected, relative
print(json.dumps({"status": "sealed-independent-source-contract-review", "members": len(members),
                  "manifest": identity(HERE / "manifest.json"),
                  "decision": "accepted-prerequisite-contract-for-root-selection-of-bounded-A",
                  "native_product_execution_or_qualification": False}, indent=2, sort_keys=True))
