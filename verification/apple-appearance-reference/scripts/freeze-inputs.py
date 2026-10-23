#!/usr/bin/env python3
"""Reproduce/verify the exact Git input set without consulting live SDK sources."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
REVISION = "958998d92f1c2ba205de09a83d957d738b619572"
PATHS = ["sdk", "AGENTS.md", "mixer-product-plan.md", "docs/ui-shared-appearance-contract.md",
    "verification/ui-shared-appearance-contract/v2/foundation-seam.md",
    "cli/Sources/MixerBuild/AppleProject.swift"]
archive = subprocess.check_output(["git", "archive", REVISION, *PATHS], cwd=REPO)
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    for member in source.getmembers():
        if not member.isfile():
            continue
        data = source.extractfile(member).read()
        path = ROOT / "frozen" / member.name
        if path.exists():
            assert path.read_bytes() == data, member.name
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
lock = json.loads((ROOT / "input-lock.json").read_text())
assert lock["sourceRevision"] == REVISION
for entry in lock["sourceFiles"]:
    assert hashlib.sha256((ROOT / "frozen" / entry["path"]).read_bytes()).hexdigest() == entry["sha256"]
print(f"PASS: {len(lock['sourceFiles'])} exact Git inputs; live SDK files were not used.")
