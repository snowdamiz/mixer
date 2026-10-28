"""One bounded root-authorized delivery, without force push or unrelated files."""
import hashlib
import json
import platform
from pathlib import Path
from owned import Commands, OUT, ROOT, now, row, save

BASE = "5efcb6a2bcf3b076c9a4452926a842209302e56b"
TREE = "18f204207b0c7dd8f331e0cd947c10b41a663770"
WORKFLOW = ".github/workflows/swift-frame-pin-admission.yml"
METADATA = ["PLAN.md", "STATUS.md", "work-graph.json", "gates/ga.json"]
PREEXECUTION = ["owned.py", "prepare.py", "deliver.py", "dispatch.py", "selection.json",
                "prior-comparison-summary.json", "metadata-checkpoint.json", "update-observations.py",
                "public-summary-candidate.json", "public-summary-seal.json", "current-observations.json", "preparation-error.json", "delivery-preflight-error.json", "deliver-attempt2.py", "cap-correction-authorization.json"]


def read(path):
    return json.loads(path.read_bytes())


assert (OUT / "delivery-preflight-error.json").exists() and not (OUT / "stage.started.json").exists()
assert not (OUT / "delivery-attempt2-once.json").exists(), "one corrected attempt only"
save("delivery-attempt2-once.json", {"at": now(), "base": BASE, "tree": TREE, "oneNonforcePushAuthorized": True})
commands = Commands(300, prefix="delivery2-")
assert commands.run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert commands.run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert commands.run("base-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == TREE
assert commands.run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
assert not commands.run("index-before", ["git", "diff", "--cached", "--name-only", "-z"])
commands.run("git-version", ["git", "--version"])
selection = read(OUT / "selection.json")
assert selection["basisRevision"] == BASE and selection["basisTree"] == TREE
assert selection["profile"] == "paired-128-v1" and selection["dispatchesAuthorized"] == 1
assert selection["newActualFullAttempts"] == 0 and not selection["feasibilityAccepted"]
assert row(ROOT / WORKFLOW) == selection["workflow"]
assert (ROOT / WORKFLOW).read_bytes() == (ROOT / "verification/swift-frame-pin-admission-candidate/workflow.yml").read_bytes()
for path, expected in selection["protectedDirtyPathsExcluded"].items():
    assert row(ROOT / path)["sha256"] == expected, path
for expected in read(OUT / "metadata-checkpoint.json")["after"]:
    assert row(ROOT / expected["path"]) == expected
selected = {ROOT / path for path in [WORKFLOW, *METADATA]}
for item in selection["verifiedPackets"]:
    directory = ROOT / "verification" / item["lane"]
    assert row(directory / "seal.json")["sha256"] == item["sealSHA256"]
    packet = read(directory / "seal.json")
    for name, expected in packet["files"].items():
        actual = row(directory / name)
        assert {k: actual[k] for k in ("bytes", "sha256")} == expected
        selected.add(directory / name)
    selected.add(directory / "seal.json")
prior = ROOT / "verification/github-delivery-architecture-comparison/ci-review/seal.json"
assert row(prior)["sha256"] == "6965fd62339bedddc735068068fead314abd79dea56ee466b06cccb565b0cea4"
selected.add(prior)
selected.update(OUT / name for name in PREEXECUTION)
# The exact reviewed sparse checkout depends on complete sealed correction and v1 inputs.
text = (ROOT / WORKFLOW).read_text()
prefixes = [line.strip().strip("/") for line in text.splitlines() if line.strip().startswith("/verification/")]
assert len(prefixes) == 9
tracked = set(filter(None, commands.run("sparse-tracked", ["git", "ls-files", "-z", "--", *prefixes]).decode().split("\0")))
tracked_blobs = {}
for entry in commands.run("sparse-tracked-blobs", ["git", "ls-files", "--stage", "-z", "--", *prefixes]).split(b"\0"):
    if entry:
        header, path = entry.decode().split("\t", 1)
        mode, oid, stage = header.split()
        assert stage == "0" and mode in ("100644", "100755")
        tracked_blobs[path] = oid
assert set(tracked_blobs) == tracked
delivered = {str(path.relative_to(ROOT)) for path in selected}
sparse_rows = []
for prefix in prefixes:
    path = ROOT / prefix
    files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
    assert files, prefix
    for p in files:
        relative = str(p.relative_to(ROOT))
        # Local caches or unsealed evidence are excluded from the sparse runtime dependency closure.
        if "__pycache__" in p.parts:
            continue
        assert relative in tracked or relative in delivered, "undelivered sparse dependency: " + relative
        if relative in tracked and relative not in delivered:
            data = p.read_bytes()
            assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == tracked_blobs[relative], relative
        sparse_rows.append(row(p))
for name in ("verification/swift-execution-architecture-correction/seal.json",):
    directory = (ROOT / name).parent
    for member, expected in read(ROOT / name)["files"].items():
        actual = row(directory / member)
        assert {k: actual[k] for k in ("bytes", "sha256")} == expected
        assert actual["path"] in tracked, "correction seal member missing from HEAD"
save("sparse-dependencies-attempt2.json", {"schema": 1, "at": now(), "workflow": row(ROOT / WORKFLOW),
     "prefixes": prefixes, "files": sparse_rows, "allFilesTrackedAtBaseOrWhitelistedForDelivery": True,
     "scope": "complete reviewed sparse directories and exact singleton files; no source generation, compiler or guest"})
selected.add(OUT / "sparse-dependencies-attempt2.json")
review = OUT / "delivery-review"
if (review / "seal.json").exists():
    review_seal = read(review / "seal.json")
    assert read(review / "receipt.json")["accepted"] is True
    for name, expected in review_seal["files"].items():
        actual = row(review / name)
        assert {k: actual[k] for k in ("bytes", "sha256")} == expected
        selected.add(review / name)
    selected.add(review / "seal.json")
w, g = read(ROOT / "work-graph.json"), read(ROOT / "gates/ga.json")
assert [sum(x["status"] == s for x in g["gates"]) for s in ("running", "planned", "verified")] == [8,30,0]
assert w["packages"][7]["empiricalCacheDeadlineCampaign"] == g["gates"][1]["empiricalCacheDeadlineCampaign"]
assert not set(selection["protectedDirtyPathsExcluded"]) & {str(p.relative_to(ROOT)) for p in selected}
assert all(".wrangler" not in p.parts and ".codex" not in p.parts for p in selected)
assert all("/ci-review/" not in str(p) or p == prior for p in selected)
members = [row(p) for p in sorted(selected)]
assert len(members) <= 150 and sum(p["bytes"] for p in members) < 6 * 1024 * 1024
save("manifest.json", {"schema": 1, "at": now(), "command": "python3 -B verification/github-delivery-frame-pin-128/deliver-attempt2.py",
     "python": platform.python_version(), "base": BASE, "baseTree": TREE, "members": members,
     "scope": "Exact reviewed paired-128 workflow, two sealed source/review packets, singleton prior review seal, root selection and metadata",
     "activeFieldLogCacheOptimizationRawCIEvidenceAndUnreviewedWorkExcluded": True, "GA_accepted": False})
paths = [member["path"] for member in members] + [str((OUT / "manifest.json").relative_to(ROOT))]
with (OUT / "paths.nul").open("xb") as stream:
    stream.write(b"".join(path.encode() + b"\0" for path in paths))
commands.run("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "paths.nul"), "--pathspec-file-nul"])
for expected in members:
    assert row(ROOT / expected["path"]) == expected
index = set(filter(None, commands.run("index-selected", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0")))
assert index <= set(paths) and WORKFLOW in index
commands.run("authored-check", ["git", "diff", "--cached", "--check", "--", WORKFLOW, *METADATA,
                              *[str((OUT / name).relative_to(ROOT)) for name in PREEXECUTION]])
raw = commands.run("staged-objects", ["git", "diff", "--cached", "--raw", "--no-abbrev", "-z"]).split(b"\0")
for offset in range(0, len(raw) - 1, 2):
    header = raw[offset].decode().split()
    path = raw[offset + 1].decode()
    assert len(header) == 5 and header[-1] in ("A", "M") and header[1] in ("100644", "100755")
    data = (ROOT / path).read_bytes()
    assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == header[3]
commands.run("commit", ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-m", "Select bounded 128-frame and pin comparison"])
head = commands.run("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
tree = commands.run("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip()
assert commands.run("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
committed = set(filter(None, commands.run("committed-paths", ["git", "diff-tree", "--no-commit-id", "--name-only", "-z", "-r", "HEAD"]).decode().split("\0")))
assert committed == index
assert not commands.run("index-after", ["git", "diff", "--cached", "--name-only", "-z"])
for path, expected in selection["protectedDirtyPathsExcluded"].items():
    assert row(ROOT / path)["sha256"] == expected
commands.run("push", ["git", "-c", "core.hooksPath=/dev/null", "-c", "pack.window=0", "push", "origin", "HEAD:refs/heads/main"], cap=120)
assert commands.run("remote-after", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
for path, expected in selection["protectedDirtyPathsExcluded"].items():
    assert row(ROOT / path)["sha256"] == expected
save("receipt.json", {"schema": 1, "at": now(), "commit": head, "tree": tree, "parent": BASE,
     "committedPaths": len(index), "selectedFiles": len(members), "selectedBytes": sum(p["bytes"] for p in members),
     "manifest": row(OUT / "manifest.json"), "pushed": True, "force": False, "CI_pending": True,
     "allNewCommands": commands.records, "allNewCommandsReapedAndOwnedGroupsAbsent": True,
     "protectedWorkUnchanged": selection["protectedDirtyPathsExcluded"], "wranglerUntouched": True,
     "activeFieldLogRawCIEvidenceAndUnreviewedWorkExcluded": True, "GA_accepted": False})
print(json.dumps({"commit": head, "tree": tree, "committedPaths": len(index), "commands": len(commands.records), "pushed": True, "cleanupVerified": True}))
