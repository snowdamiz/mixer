"""Finite, read-only Git binding and required sparse dependency preflight."""
import hashlib
import json
from pathlib import Path
from owned import Commands, OUT, ROOT, now, row, save

selection = json.loads((OUT / "selection.json").read_bytes())
assert not (OUT / "preflight.json").exists()
commands = Commands(180, 9, "inspect-")
commands.run("git-version", ["git", "--version"])
assert commands.run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert commands.run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == selection["base"]
assert commands.run("tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == selection["baseTree"]
assert not commands.run("index", ["git", "diff", "--cached", "--name-only", "-z"])
dirty = set(filter(None, commands.run("tracked-dirty", ["git", "diff", "--name-only", "-z"]).decode().split("\0")))
expected_dirty = {"PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json",
    ".github/workflows/hosted.yml", "hosted/lib/mixer_hosted/browser_auth/store.ex"}
assert dirty <= expected_dirty, "unexpected active tracked work: " + repr(sorted(dirty - expected_dirty))
assert commands.run("remote", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == selection["base"]
workflow = ROOT / selection["workflow"]["destination"]
assert row(workflow)["sha256"] == selection["workflow"]["sha256"]
prefixes = [line.strip().strip("/") for line in workflow.read_text().splitlines()
            if line.strip().startswith("/verification/")]
assert len(prefixes) == 10 and len(set(prefixes)) == 10
entries = commands.run("sparse-index", ["git", "ls-files", "--stage", "-z", "--", *prefixes]).split(b"\0")
tracked = {}
for entry in entries:
    if entry:
        header, path = entry.decode().split("\t", 1)
        mode, oid, stage = header.split()
        assert stage == "0" and mode in ("100644", "100755")
        tracked[path] = oid
producer = ROOT / "verification/swift-cachework-128-experiment"
packet = json.loads((producer / "seal.json").read_bytes())
new_source = {str((producer / p).relative_to(ROOT)) for p in [*packet["files"], "seal.json"]}
bound_files, missing = [], []
for prefix in prefixes:
    target = ROOT / prefix
    assert target.exists(), prefix
    files = sorted(p for p in target.rglob("*") if p.is_file()) if target.is_dir() else [target]
    for path in files:
        if "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(ROOT))
        if relative in new_source:
            bound_files.append(row(path))
        elif relative in tracked:
            data = path.read_bytes()
            assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == tracked[relative], relative
            bound_files.append(row(path))
        else:
            # This report never silently expands delivery ownership.
            missing.append(row(path))
save("preflight.json", {"schema": 1, "at": now(), "base": selection["base"], "baseTree": selection["baseTree"],
    "allTrackedDirtyPaths": sorted(dirty), "indexEmpty": True, "remoteMatchesBase": True,
    "prefixes": prefixes, "sparseBindings": bound_files, "untrackedSparseFilesRequireDecision": missing,
    "commands": commands.records, "allCommandsReapedGroupsAbsentAndEOF": True,
    "scope": "Finite Git/gh delivery only; no compiler, guest, native, inventory or held-group probe"})
print(json.dumps({"trackedDirty": sorted(dirty), "sparseBindings": len(bound_files), "missing": missing,
    "commands": len(commands.records), "cleanupVerified": True}))
