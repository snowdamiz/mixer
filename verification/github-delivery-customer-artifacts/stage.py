#!/usr/bin/env python3
"""Stage only the prepared allowlist and verify every selected index blob."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / "selection.json").read_text())
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == manifest["baseRevision"]
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT).strip()
files = dict(manifest["files"])
files[str((OUT / "selection.json").relative_to(ROOT))] = {"sha256": hashlib.sha256((OUT / "selection.json").read_bytes()).hexdigest()}
for name, info in files.items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == info["sha256"], name
subprocess.run(["git", "add", "-f", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"], cwd=ROOT, check=True)
changed = subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT).decode().split("\0")[:-1]
assert set(changed).issubset(files)
for name, info in files.items():
    data = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
    assert hashlib.sha256(data).hexdigest() == info["sha256"], name
source_paths = [name for name in changed if not name.startswith("verification/")]
checks = {}
for label, paths in [("all-whitespace", []), ("source-whitespace", source_paths)]:
    result = subprocess.run(["git", "diff", "--cached", "--check", "--", *paths], cwd=ROOT, capture_output=True)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    checks[label] = result.returncode
assert checks["source-whitespace"] == 0
receipt = {"baseRevision": manifest["baseRevision"], "selectedIndexBlobsVerified": len(files),
           "changedPaths": len(changed), "allChangedPathsAllowlisted": True, "whitespaceChecks": checks,
           "rawEvidenceWhitespace": "Preserved verbatim; not source acceptance."}
(OUT / "staged-check.json").write_text(json.dumps(receipt, indent=2) + "\n")
extra = ["staged-check.json", "all-whitespace.stdout", "all-whitespace.stderr", "source-whitespace.stdout", "source-whitespace.stderr"]
subprocess.run(["git", "add", "-f", *[str(OUT / name) for name in extra]], cwd=ROOT, check=True)
assert set(subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT).decode().split("\0")[:-1]).issubset(set(files) | {str((OUT / name).relative_to(ROOT)) for name in extra})
print(json.dumps(receipt))
