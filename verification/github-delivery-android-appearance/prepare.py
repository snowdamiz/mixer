"""Stage only an accepted default-appearance slice and prior terminal CI evidence."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "99d6384306ea17643b70c472f93b57418c674f86"
commands = []


def run(label, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    commands.append({"label": label, "argv": argv, "exit": result.returncode,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode in allowed, (label, result.stderr.decode(errors="replace"))
    return result.stdout


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


acceptance = json.loads((ROOT / "verification/android-default-appearance-packaging-root-review/acceptance.json").read_text())
assert acceptance["status"] == "accepted-scoped-default-appearance-packaging"
assert json.loads((ROOT / "verification/github-delivery-android-source-export/receipt.json").read_text())["all_jobs_and_steps_passed"]
assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert run("empty-index", ["git", "diff", "--cached", "--name-only", "-z"]) == b""
assert run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])

metadata = {}
for name, collection, android in [
    ("work-graph.json", "packages", "W05"),
    ("gates/ga.json", "gates", "G05"),
]:
    old = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    live = json.loads((ROOT / name).read_text())
    target = next(x for x in old[collection] if x["id"] == android)
    current = next(x for x in live[collection] if x["id"] == android)
    for key in ["authoredToggleGeneratedExportCandidate", "defaultAppearancePackagingProposal", "evidence"]:
        target[key] = current[key]
    if collection == "packages":
        for key in ["currentCheckpoint", "nextImplementation"]:
            target[key] = current[key]
    metadata[name] = (json.dumps(old, indent=2) + "\n").encode()

ci_line = "Generated Android source-export repair `99d63843` passes all 40 steps across three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40252047362).\n"
anchor = "Rustup dispatch repair `05c1ebf0` passes all three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40247799000).\n"
for name in ["PLAN.md", "STATUS.md"]:
    old = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    assert old.count(anchor) == 1 and ci_line not in old
    old = old.replace(anchor, anchor + ci_line)
    if name == "PLAN.md":
        start = "4. **Android and cross-platform UI:**"
        end = "5. **Hosted product and console:**"
        old = old[:old.index(start)] + live[live.index(start):live.index(end)] + old[old.index(end):]
    else:
        old_row = next(x for x in old.splitlines() if x.startswith("| Android shared UI |"))
        new_row = next(x for x in live.splitlines() if x.startswith("| Android shared UI |"))
        old = old.replace(old_row, new_row)
    metadata[name] = old.encode()

snapshots = OUT / "metadata-snapshots"
snapshots.mkdir(exist_ok=True)
for name, data in metadata.items():
    path = snapshots / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

handoff = json.loads((ROOT / "verification/android-default-appearance-packaging/handoff.json").read_text())
paths = set(handoff["owned_product_files"])
for name, expected in handoff["owned_product_files"].items():
    assert identity((ROOT / name).read_bytes()) == expected, name
paths.update([
    "docs/android-default-appearance-packaging-proposal.md",
    "docs/android-default-appearance-packaging-review.md",
    "docs/android-default-appearance-packaging.md",
    "docs/android-default-appearance-packaging-implementation-review.md",
])
for directory in [
    "verification/android-default-appearance-packaging-proposal",
    "verification/android-default-appearance-packaging-review",
    "verification/android-default-appearance-packaging",
    "verification/android-default-appearance-packaging-implementation-review",
    "verification/android-default-appearance-packaging-root-review",
    "verification/github-delivery-android-source-export",
]:
    for path in (ROOT / directory).rglob("*"):
        assert not path.is_symlink(), path
        if path.is_file():
            paths.add(path.relative_to(ROOT).as_posix())
assert not any("envelope" in name or "callback" in name or "copied-sdk" in name for name in paths)
for name in paths:
    assert (ROOT / name).is_file()
(OUT / "non-metadata-paths.nul").write_bytes(b"".join(x.encode() + b"\0" for x in sorted(paths)))
run("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "non-metadata-paths.nul"), "--pathspec-file-nul"])
for name in metadata:
    label = name.replace("/", "-")
    blob = run("metadata-blob-" + label, ["git", "hash-object", "-w", str(snapshots / name)]).decode().strip()
    run("metadata-stage-" + label, ["git", "update-index", "--add", "--cacheinfo", "100644," + blob + "," + name])
paths.update(metadata)
staged = set(run("staged-paths", ["git", "diff", "--cached", "--name-only", "-z"]).decode().strip("\0").split("\0"))
assert staged == paths, {"extra": sorted(staged - paths), "missing": sorted(paths - staged)}
manifest = {}
for name in sorted(paths):
    data = metadata.get(name, (ROOT / name).read_bytes())
    staged_data = subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
    assert data == staged_data, name
    manifest[name] = identity(data)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "paths.nul").write_bytes(b"".join(x.encode() + b"\0" for x in sorted(paths)))
run("staged-diff-check", ["git", "diff", "--cached", "--check"], (0, 2))
print(json.dumps({"status": "exact-staged-manifest-verified", "paths": len(paths),
                  "bytes": sum(x["bytes"] for x in manifest.values()), "base": BASE}))
