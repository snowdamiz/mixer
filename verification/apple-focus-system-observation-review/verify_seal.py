#!/usr/bin/env python3
"""Read-only independent-review seal verification; no dispatched work."""
import hashlib
import json
import pathlib
import stat

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()
raw = (HERE / "handoff.json").read_bytes()
assert sha(raw) == (HERE / "handoff.sha256").read_text().strip()
handoff = json.loads(raw)
actual = {str(path.relative_to(ROOT)) for path in HERE.rglob("*") if path.is_file()
          and path.name not in ("handoff.json", "handoff.sha256")}
actual.add("docs/apple-focus-system-observation-review.md")
assert actual == set(handoff["members"])
assert all(stat.S_IMODE((HERE / name).stat().st_mode) == 0o444 for name in ("handoff.json", "handoff.sha256"))
for name, item in handoff["members"].items():
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    value = path.read_bytes()
    assert len(value) == item["bytes"] and sha(value) == item["sha256"], name
    assert stat.S_IMODE(path.stat().st_mode) == item["mode"] == 0o444, name
producer = ROOT / "verification/apple-focus-system-observation"
assert sha((producer / "handoff.json").read_bytes()) == handoff["producerHandoffSHA256"]
assert sha((producer / "review-source-package.tar.gz").read_bytes()) == handoff["candidateArchiveSHA256"]
assert not (HERE / ".owned-typecheck").exists()
assert not list(HERE.rglob("__pycache__"))
receipt = json.loads((HERE / "receipt.json").read_bytes())
assert receipt["status"] == "changes-required" and receipt["sourceHostAccepted"] is False
assert len(receipt["findings"]) == 2 and all(f["status"] == "open" for f in receipt["findings"])
assert receipt["nativeAccepted"] is False and receipt["gaAccepted"] is False
print(json.dumps({"schema": 1, "verifiedMembers": len(handoff["members"]),
                  "handoffSHA256": sha(raw), "status": "changes-required", "openFindings": 2,
                  "nativeAccepted": False, "scope": "Read-only independent-review seal verification"}, sort_keys=True))
