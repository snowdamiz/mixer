"""Replay the archived F11 raw workspace checks against the signed host writes."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

stage, work = map(Path, sys.argv[1:])
fixtures = stage / "verification/local"
f11 = fixtures / "fieldlog-f11-ordinary-root/fixture/android_f11.py"
f12 = fixtures / "fieldlog-f12-ordinary-root/fixture/android_f12.py"


def sha(data):
    return hashlib.sha256(data).hexdigest()


observed = json.loads((work / "fixture.json").read_bytes())
assert sha(f11.read_bytes()) == observed["driverSHA256"]
assert sha(f12.read_bytes()) == "38fa8bdbfa7ec8716eb48e0203f14c5a58c9c16ac238096d8e199a0ba1fc1d9d"
validate = runpy.run_path(str(f11))["verify_write"]
raw_members = runpy.run_path(str(f12))["raw_members"]
seed = (work / "guest/seed.json").read_bytes()
saved = (work / "actions/saved.json").read_bytes()
commit = (work / "actions/workspace/workspace.json").read_bytes()
cold = (work / "cold-committed.json").read_text().strip()
action = json.loads((work / "actions.json").read_bytes())["hostActions"]
assert sha(saved) == action["coldDraftSHA256"]
assert sha(commit) == action["commitSHA256"] == cold
validate(seed, saved, commit=False, raw_members=raw_members)
event = validate(saved, commit, commit=True, raw_members=raw_members)
print(json.dumps({"revisions": [1, 2, 3, 3], "linkedEvent": event,
                  "unrelatedRowsByteIdentical": True, "freshProcessCommitSHA256": cold}))
