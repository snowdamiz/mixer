#!/usr/bin/env python3
"""Seal only the owned independent review; never mutates producer inputs."""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()
stable = lambda value: (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
assert not (HERE / "handoff.json").exists()
assert not (HERE / ".owned-typecheck").exists() and not list(HERE.rglob("__pycache__"))
paths = [ROOT / "docs/apple-focus-system-observation-review.md"]
paths += sorted(path for path in HERE.rglob("*") if path.is_file())
assert all(not path.is_symlink() for path in paths)
members = {}
for path in paths:
    data = path.read_bytes()
    path.chmod(0o444)
    members[str(path.relative_to(ROOT))] = {"bytes": len(data), "sha256": sha(data), "mode": 0o444}
receipt = json.loads((HERE / "receipt.json").read_bytes())
handoff = {"schema": 1, "scope": "Independent finite source/host review; no runtime selection",
           "status": "changes-required", "openFindings": ["F1", "F2"],
           "sourceHostAccepted": False, "nativeAccepted": False, "gaAccepted": False,
           "producerHandoffSHA256": receipt["producerHandoffSHA256"],
           "candidateArchiveSHA256": receipt["candidateArchiveSHA256"], "members": members}
raw = stable(handoff)
(HERE / "handoff.json").write_bytes(raw)
(HERE / "handoff.sha256").write_text(sha(raw) + "\n")
(HERE / "handoff.json").chmod(0o444)
(HERE / "handoff.sha256").chmod(0o444)
print(json.dumps({"handoffSHA256": sha(raw), "members": len(members), "status": "changes-required"}, sort_keys=True))
