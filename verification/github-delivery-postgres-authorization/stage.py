#!/usr/bin/env python3
"""Stage only the frozen allowlist and this delivery's explicit check files."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / "selection.json").read_text())
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == manifest["baseRevision"]
assert not subprocess.check_output(["git", "diff", "--cached", "--name-only"], cwd=ROOT).strip()
for name, expected in manifest["files"].items():
    data = (ROOT / name).read_bytes()
    assert len(data) == expected["bytes"] and hashlib.sha256(data).hexdigest() == expected["sha256"]
subprocess.run(["git", "add", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"], cwd=ROOT, check=True)
commands = []
for label, argv in [
    ("all-diff-check", ["git", "diff", "--cached", "--check"]),
    ("source-diff-check", ["git", "diff", "--cached", "--check", "--", "hosted", "docs", "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]),
]:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    commands.append({"argv": argv, "exitCode": result.returncode,
        "stdoutSHA256": hashlib.sha256(result.stdout).hexdigest(), "stderrSHA256": hashlib.sha256(result.stderr).hexdigest()})
    if label == "source-diff-check":
        assert result.returncode == 0, result.stdout.decode()

extra = ["stage.py", "all-diff-check.stdout", "all-diff-check.stderr", "source-diff-check.stdout", "source-diff-check.stderr"]
extra_paths = [str((OUT / name).relative_to(ROOT)) for name in extra]
subprocess.run(["git", "add", "--", *extra_paths], cwd=ROOT, check=True)
selected = set(manifest["files"]) | {str((OUT / "selection.json").relative_to(ROOT))} | set(extra_paths)
changed = set(subprocess.check_output(["git", "diff", "--cached", "--name-only", "-z"], cwd=ROOT).decode().rstrip("\0").split("\0"))
assert changed <= selected
index = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)
verified = 0
for row in index.split(b"\0"):
    if not row:
        continue
    metadata, name = row.split(b"\t", 1)
    name = os.fsdecode(name)
    if name in selected:
        _, oid, stage = metadata.split()
        assert stage == b"0"
        data = (ROOT / name).read_bytes()
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest().encode() == oid
        verified += 1
assert verified == len(selected)
receipt = {"schema": 1, "baseRevision": manifest["baseRevision"], "selectedPaths": len(selected),
    "changedPaths": len(changed), "allSelectedIndexBlobsMatch": True, "commands": commands,
    "extraAllowedPaths": extra_paths + [str((OUT / "staged-check.json").relative_to(ROOT))],
    "rawEvidenceWhitespace": "Preserved immutable historical output and patch bytes; only current source/document diff must be whitespace clean."}
(OUT / "staged-check.json").write_text(json.dumps(receipt, indent=2) + "\n")
subprocess.run(["git", "add", "--", str((OUT / "staged-check.json").relative_to(ROOT))], cwd=ROOT, check=True)
print(json.dumps({"changedPaths": len(changed) + 1, "verifiedSelectedBlobs": verified,
    "rawEvidenceWhitespaceExit": commands[0]["exitCode"], "sourceWhitespaceExit": commands[1]["exitCode"]}))
