#!/usr/bin/env python3
import hashlib
import io
import json
from pathlib import Path
import subprocess as sp
import sys
import tarfile

mixer = Path(sys.argv[1]).resolve()
work = Path(sys.argv[2]).resolve()
review = "062aaf116b"
receipt = "verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-iphoneos-corrected.json"
ref = json.loads(sp.check_output(["git", "-C", mixer, "show", f"{review}:{receipt}"]))
app = work / "fieldlog"

def git(root, *args, stdin=None):
    return sp.check_output(["git", "-C", root, *args], input=stdin).strip()

def checkout(root, url, commit, tree):
    root.mkdir()
    git(root, "init", "-q")
    git(root, "fetch", "-q", "--no-tags", "--depth=1", url, commit)
    git(root, "checkout", "-q", "--detach", "FETCH_HEAD")
    assert git(root, "rev-parse", "HEAD").decode() == commit
    assert git(root, "write-tree").decode() == tree

field = ref["fieldLog"]
checkout(app, field["publicURL"], field["publicCommit"], field["publicTree"])
public_paths = git(app, "ls-files").decode().splitlines()
print("public repository blobs", flush=True)
for path in public_paths:
    if path.endswith("/WorkspaceRepository.swift"):
        src = (app / path).read_bytes()
        print(path, git(app, "hash-object", path).decode(), hashlib.sha256(src).hexdigest(), src.count(b"\n"), flush=True)
for material in field["orderedMaterial"]:
    path = material["path"]
    source = review if path.startswith("verification/") else field["patchReviewMixerCommit"]
    data = sp.check_output(["git", "-C", mixer, "show", f"{source}:{path}"])
    assert hashlib.sha256(data).hexdigest() == material["sha256"], path
    if "resultingTree" not in material:
        assert path.endswith("/EntrySaveDecision.swift"), path
        destination = "Integrations/GeneratedReport/Sources/FieldLogFeatures/EntrySaveDecision.swift"
        (app / destination).write_bytes(data)
        git(app, "add", "--", destination)
        continue
    git(app, "apply", "--index", "--whitespace=nowarn", "-", stdin=data)
    actual = git(app, "write-tree").decode()
    assert actual == material["resultingTree"], (path, actual)
    print(path, actual, flush=True)
assert actual == field["candidateTree"]
for path in git(app, "ls-files").decode().splitlines():
    if path.endswith("/WorkspaceRepository.swift"):
        src = (app / path).read_bytes()
        print("reviewed", path, git(app, "hash-object", path).decode(), hashlib.sha256(src).hexdigest(), src.count(b"\n"), flush=True)
sdk = ref["mixer"]
assert git(mixer, "rev-parse", sdk["commit"] + "^{tree}").decode() == sdk["tree"]
sdk_path = work / "mixer"
sdk_path.mkdir()
archive = sp.check_output(["git", "-C", mixer, "archive", sdk["commit"], *sdk["exportPaths"]])
with tarfile.open(fileobj=io.BytesIO(archive)) as exported:
    exported.extractall(sdk_path, filter="data")
print("Mixer", sdk["commit"], sdk["tree"], flush=True)
