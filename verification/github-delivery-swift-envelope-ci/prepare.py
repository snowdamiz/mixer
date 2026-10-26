"""Select accepted fixture CI and scoped metadata; preserve other live lanes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "b45963c03816112972499bd60073039f36916272"
commands = []


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def run(name, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    commands.append({"name": name, "argv": argv, "exit": result.returncode,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "stdout": ident(result.stdout), "stderr": ident(result.stderr)})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode in allowed, name
    return result.stdout


assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert run("index-before", ["git", "diff", "--cached", "--name-only", "-z"]) == b""
assert run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])
accepted_path = ROOT / "verification/swift-envelope-ci-root-review/corrected-runner-acceptance.json"
assert ident(accepted_path.read_bytes())["sha256"] == "8c37b18e539f074bda0b55e046c58a446b9eb705e821dab2aa3499474ab5af5a"
accepted = json.loads(accepted_path.read_bytes())
assert accepted["root_acceptance"] and not accepted["GA_qualified"]
for name, key in [("scripts/ci/check-analyzer-envelope.py", "runner_sha256"),
                  ("scripts/ci/tests/test_analyzer_envelope_runner.py", "tests_sha256")]:
    assert ident((ROOT / name).read_bytes())["sha256"] == accepted[key]
assert ident((ROOT / ".github/workflows/verify.yml").read_bytes())["sha256"] == "091461b646342255ba90bdeaff140396ce8ee25f26d97fd78c61c994e1ea612c"

draft = json.loads((OUT / "selection-draft.json").read_bytes())
paths = set(draft["ordinary_files_before_final_review"])
paths.add("docs/swift-envelope-ci-acceptance.md")
for directory in ["verification/swift-envelope-ci-delivery",
                  "verification/swift-envelope-ci-root-review",
                  "verification/github-delivery-android-environment-observer"]:
    for path in (ROOT / directory).rglob("*"):
        assert not path.is_symlink(), path
        if path.is_file():
            paths.add(path.relative_to(ROOT).as_posix())
review = "verification/swift-envelope-ci-independent-review"
for suffix in ["preaccess-seal.json", "test-lint-preaccess-supplement/seal.json",
               "compiler-preaccess-supplement/seal.json", "correction-1-preaccess-supplement/seal.json"]:
    seal = ROOT / review / suffix
    for row in json.loads(seal.read_bytes())["members"]:
        assert ident((ROOT / row["path"]).read_bytes()) == {k: row[k] for k in ("bytes", "sha256")}, row["path"]
        paths.add(row["path"])
    paths.add(seal.relative_to(ROOT).as_posix())
    paths.add(seal.with_suffix(".sha256").relative_to(ROOT).as_posix())
for path in (ROOT / review / "correction-review-1").iterdir():
    if path.is_file():
        paths.add(path.relative_to(ROOT).as_posix())
closure = json.loads((ROOT / "verification/swift-envelope-ci-delivery/accepted-source-closure.json").read_bytes())
for row in closure["members"]:
    assert ident((ROOT / row["path"]).read_bytes()) == {k: row[k] for k in ("bytes", "sha256")}, row["path"]
    paths.add(row["path"])
parts = json.loads((ROOT / "verification/swift-envelope-ci-delivery/correction-independent-parts.json").read_bytes())
assert parts["partitions_disjoint_and_complete"]
for row in parts["parts"]:
    for key in ("archive", "manifest", "selection"):
        assert ident((ROOT / row[key]).read_bytes())["sha256"] == row[key + "_sha256"], row[key]

metadata = {}
scopes = {}
for name, collection, target_id, android_id in [("work-graph.json", "packages", "W08", "W05"),
                                               ("gates/ga.json", "gates", "G02", "G05")]:
    baseline = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    old = json.loads(json.dumps(baseline))
    live = json.loads((ROOT / name).read_bytes())
    target = next(x for x in old[collection] if x["id"] == target_id)
    current = next(x for x in live[collection] if x["id"] == target_id)
    fields = ["evidence", "currentCheckpoint", "orderedRetentionAnalyzerLibraryCandidate",
              "orderedRetentionAnalyzerFSMContractCandidate", "orderedRetentionAnalyzerEnvelopeCandidate",
              "orderedRetentionAnalyzerEnvelopeCI"]
    if collection == "packages":
        fields.append("nextImplementation")
    for key in fields:
        target[key] = current[key]
    android = next(x for x in old[collection] if x["id"] == android_id)
    android_live = next(x for x in live[collection] if x["id"] == android_id)
    android["environmentObserverLifecycleCandidate"]["delivery"] = android_live["environmentObserverLifecycleCandidate"]["delivery"]
    for before, after in zip(baseline[collection], old[collection]):
        assert before["id"] == after["id"]
        for invariant in ["state", "status", "reviewer", "accountableReviewer"]:
            assert before.get(invariant) == after.get(invariant), (name, before["id"], invariant)
        if before["id"] not in (target_id, android_id):
            assert before == after
    metadata[name] = (json.dumps(old, indent=2) + "\n").encode()
    scopes[name] = {target_id: fields, android_id: ["environmentObserverLifecycleCandidate.delivery"]}
for name in ("PLAN.md", "STATUS.md"):
    old = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    if name == "PLAN.md":
        start, end = "1. **Owned Swift interpreter:**", "2. **iOS shared UI:**"
    else:
        start, end = "The new single full Swift reactor attempt", "Independent iOS source review"
    old = old[:old.index(start)] + live[live.index(start):live.index(end)] + old[old.index(end):]
    line = next(x for x in live.splitlines() if x.startswith("Android observer/source-profile repair `b45963c0`"))
    assert line not in old
    anchor = next(x for x in old.splitlines() if x.startswith("Android host lifecycle core `4e48ac1a`"))
    old = old.replace(anchor, anchor + "\n" + line)
    metadata[name] = old.encode()
snapshots = OUT / "metadata-snapshots"
for name, data in metadata.items():
    path = snapshots / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
for name in paths:
    path = ROOT / name
    assert path.is_file() and not path.is_symlink(), name
    assert "__pycache__" not in path.parts and path.suffix != ".pyc", name
    assert path.stat().st_size < 100_000_000, name
    assert not name.startswith(("hosted/", "verification/android-private-owner-effect", ".wrangler/")), name
assert ".github/workflows/hosted.yml" not in paths
(OUT / "selection.json").write_text(json.dumps({"base": BASE, "paths": sorted(paths), "metadata_scope": scopes,
    "accepted_runner_sha256": accepted["runner_sha256"], "preserve_other_lanes": True}, indent=2) + "\n")
pathspec = OUT / "non-metadata-paths.nul"
pathspec.write_bytes(b"".join(x.encode() + b"\0" for x in sorted(paths)))
run("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(pathspec), "--pathspec-file-nul"])
for name in metadata:
    blob = run("metadata-blob-" + name.replace("/", "-"), ["git", "hash-object", "-w", str(snapshots / name)]).decode().strip()
    run("metadata-stage-" + name.replace("/", "-"), ["git", "update-index", "--add", "--cacheinfo", "100644," + blob + "," + name])
expected_changed = set(paths) | set(metadata)
actual = set(run("staged-paths", ["git", "diff", "--cached", "--name-only", "-z"]).decode().strip("\0").split("\0"))
assert actual == expected_changed, {"extra": sorted(actual - expected_changed), "missing": sorted(expected_changed - actual)}
ordered = sorted(actual)
result = subprocess.run(["git", "cat-file", "--batch"], input="".join(":" + n + "\n" for n in ordered).encode(), cwd=ROOT, capture_output=True, check=True, timeout=60)
offset = 0
manifest = {}
for name in ordered:
    end = result.stdout.index(b"\n", offset)
    header = result.stdout[offset:end].decode().split()
    assert len(header) == 3 and header[1] == "blob"
    size = int(header[2]); offset = end + 1
    data = result.stdout[offset:offset + size]; offset += size + 1
    assert data == (metadata[name] if name in metadata else (ROOT / name).read_bytes()), name
    manifest[name] = ident(data)
assert offset == len(result.stdout)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "paths.nul").write_bytes(b"".join(n.encode() + b"\0" for n in ordered))
run("diff-check", ["git", "diff", "--cached", "--check"], (0, 2))
authored = [n for n in ordered if not n.startswith("verification/")]
run("authored-diff-check", ["git", "diff", "--cached", "--check", "--"] + authored)
print(json.dumps({"status": "exact-staged-manifest-verified", "paths": len(manifest),
                  "bytes": sum(x["bytes"] for x in manifest.values()), "base": BASE}))
