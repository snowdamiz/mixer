"""One explicit root-authorized commit and nonforce push; no retries."""
import hashlib
import json
import platform
from owned import Commands, OUT, ROOT, now, row, save

selection = json.loads((OUT / "selection.json").read_bytes())
metadata = json.loads((OUT / "metadata-checkpoint.json").read_bytes())
preflight = json.loads((OUT / "preflight.json").read_bytes())
assert not (OUT / "delivery-once.json").exists(), "one delivery reservation only"
assert not preflight["untrackedSparseFilesRequireDecision"]
assert preflight["allCommandsReapedGroupsAbsentAndEOF"]
commands = Commands(300, 19, "delivery-")
assert commands.run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert commands.run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == selection["base"]
assert commands.run("tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == selection["baseTree"]
assert commands.run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == selection["base"]
assert not commands.run("index-before", ["git", "diff", "--cached", "--name-only", "-z"])
for expected in metadata["after"]:
    assert row(ROOT / expected["path"]) == expected, expected["path"]
for path, expected in metadata["protectedFilesUnchanged"].items():
    assert row(ROOT / path)["sha256"] == expected, path
workflow = ROOT / selection["workflow"]["destination"]
assert row(workflow)["sha256"] == selection["workflow"]["sha256"]
assert workflow.read_bytes() == (ROOT / selection["workflow"]["source"]).read_bytes()
selected = {workflow, *[ROOT / x for x in ("PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json")]}
for packet in metadata["packets"]:
    directory = ROOT / packet["directory"]
    assert row(directory / "seal.json") == packet["seal"]
    seal = json.loads((directory / "seal.json").read_bytes())
    for member, expected in seal["files"].items():
        actual = row(directory / member)
        assert {k: actual[k] for k in ("bytes", "sha256")} == expected, member
        selected.add(directory / member)
    selected.add(directory / "seal.json")
checkpoint = ROOT / "verification/public-host-campaigns-2026-10-28"
seal = json.loads((checkpoint / "seal.json").read_bytes())
for expected in seal["files"]:
    actual = row(checkpoint / expected["path"])
    assert {k: actual[k] for k in ("bytes", "sha256")} == {k: expected[k] for k in ("bytes", "sha256")}
    selected.add(checkpoint / expected["path"])
selected.add(checkpoint / "seal.json")
# Complete explicit owned pre-execution receipt closure. No historical raw CI directories.
owned_names = ["selection.json", "fieldlog-promisor-v2-result.json", "owned.py", "prepare.py", "inspect.py",
    "deliver.py", "dispatch.py", "preparation-stopped.json", "metadata-checkpoint.json", "preflight.json"]
for command in preflight["commands"]:
    owned_names.extend(command["name"] + suffix for suffix in
                       (".started.json", ".command.json", ".stdout", ".stderr"))
selected.update(OUT / name for name in owned_names)
assert len(owned_names) == len(set(owned_names))
assert not set(metadata["protectedFilesUnchanged"]) & {str(p.relative_to(ROOT)) for p in selected}
assert all(".wrangler" not in p.parts and ".codex" not in p.parts and "ci-review" not in p.parts for p in selected)
members = [row(p) for p in sorted(selected)]
selected_bytes = sum(m["bytes"] for m in members)
assert len(members) <= 150 and selected_bytes < 6 * 1024 * 1024
w = json.loads((ROOT / "work-graph.json").read_bytes())
g = json.loads((ROOT / "gates/ga.json").read_bytes())
assert [sum(x["status"] == s for x in g["gates"]) for s in ("running", "planned", "verified")] == [8,30,0]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"] == g["gates"][1]["empiricalCacheDeadlineCampaign"]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"]["architecture_comparison"]["capacity_window_v1"]["selection"] == row(OUT / "selection.json")
save("manifest.json", {"schema": 1, "at": now(), "command": "python3 -B verification/github-delivery-capacity-window/deliver.py",
    "python": platform.python_version(), "base": selection["base"], "baseTree": selection["baseTree"],
    "selection": row(OUT / "selection.json"), "members": members, "selectedBytes": selected_bytes,
    "packetSizeCapBytes": 6 * 1024 * 1024, "maximumOwnedDeliveryCommands": 19, "aggregateSeconds": 300,
    "scope": "Exact selected capacity-window workflow, frozen producer/review, root small closed-result checkpoint, latest small FieldLog result and four metadata files",
    "rawCIFieldLogSourceCacheFixtureCandidatesAndOtherOwnersExcluded": True,
    "runtimeProductionDefaultOrGAAccepted": False})
paths = [m["path"] for m in members] + [str((OUT / "manifest.json").relative_to(ROOT))]
with (OUT / "paths.nul").open("xb") as stream:
    stream.write(b"".join(p.encode() + b"\0" for p in paths))
save("delivery-once.json", {"at": now(), "base": selection["base"], "baseTree": selection["baseTree"],
    "manifest": row(OUT / "manifest.json"), "oneNonforcePushAuthorized": True, "retrySelected": False})
commands.run("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for expected in members:
    assert row(ROOT / expected["path"]) == expected, expected["path"]
index = set(filter(None, commands.run("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and selection["workflow"]["destination"] in index
commands.run("authored-check", ["git", "diff", "--cached", "--check", "--", selection["workflow"]["destination"],
    "PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json", *[str((OUT / p).relative_to(ROOT)) for p in owned_names]])
raw = commands.run("staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
assert len(raw) % 2 == 1
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split()
    path = raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    assert path in paths and path not in metadata["protectedFilesUnchanged"]
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3], path
commands.run("commit", ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
    "commit", "-m", "Select bounded cache capacity observation window"])
head = commands.run("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = commands.run("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert commands.run("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == selection["base"]
committed = set(filter(None, commands.run("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not commands.run("index-after", ["git", "diff", "--cached", "--name-only", "-z"])
for path, expected in metadata["protectedFilesUnchanged"].items():
    assert row(ROOT / path)["sha256"] == expected
commands.run("push", ["git", "-c", "core.hooksPath=/dev/null", "-c", "pack.window=0",
    "push", "origin", "HEAD:refs/heads/main"], seconds=120)
assert commands.run("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, expected in metadata["protectedFilesUnchanged"].items():
    assert row(ROOT / path)["sha256"] == expected
save("receipt.json", {"schema": 1, "at": now(), "commit": head, "tree": tree,
    "parent": selection["base"], "committedPaths": len(index), "selectedFiles": len(members),
    "selectedBytes": selected_bytes, "manifest": row(OUT / "manifest.json"),
    "sourceSelection": row(OUT / "selection.json"), "workflow": row(workflow),
    "pushed": True, "force": False, "allNewCommands": commands.records,
    "allNewCommandsReapedGroupsAbsentAndEOF": True, "protectedWorkUnchanged": metadata["protectedFilesUnchanged"],
    "wranglerAndOtherOwnersUntouched": True, "runtimeResults": "pending one selected manual dispatch",
    "runtimeProductionDefaultOrGAAccepted": False})
print(json.dumps({"commit": head, "tree": tree, "committedPaths": len(index), "selectedBytes": selected_bytes,
    "pushed": True, "ownedCommands": len(commands.records), "cleanupVerified": True}))
