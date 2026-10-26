"""Stage only the accepted Android export and prior terminal CI evidence."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "05c1ebf0378fb479ba8595d71cde577f447d0025"
commands = []


def run(label, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    commands.append({"label": label, "argv": argv, "exit": result.returncode,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode in allowed, (label, result.stderr.decode(errors="replace"))
    return result.stdout


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert run("empty-index", ["git", "diff", "--cached", "--name-only", "-z"]) == b""
assert run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])
acceptance = json.loads((ROOT / "verification/android-authored-toggle-generated-export-root-review/acceptance.json").read_text())
assert acceptance["status"] == "accepted-scoped-generated-source-export"
assert json.loads((ROOT / "verification/github-delivery-analyzer-rustup-repair/receipt.json").read_text())["all_jobs_and_steps_passed"]

metadata = {}
for name, collection, android, swift in [
    ("work-graph.json", "packages", "W05", "W08"),
    ("gates/ga.json", "gates", "G05", "G02"),
]:
    old = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    live = json.loads((ROOT / name).read_text())
    target = next(x for x in old[collection] if x["id"] == android)
    current = next(x for x in live[collection] if x["id"] == android)
    for key in ["authoredToggleGeneratedExportCandidate", "evidence"]:
        target[key] = current[key]
    if collection == "packages":
        for key in ["currentCheckpoint", "nextImplementation"]:
            target[key] = current[key]
    target = next(x for x in old[collection] if x["id"] == swift)
    current = next(x for x in live[collection] if x["id"] == swift)
    target["orderedRetentionAnalyzerFramingCICandidate"] = current["orderedRetentionAnalyzerFramingCICandidate"]
    metadata[name] = (json.dumps(old, indent=2) + "\n").encode()

for name in ["PLAN.md", "STATUS.md"]:
    old = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    before = "retained artifact is complete; a narrow dispatch repair is in progress."
    assert old.count(before) == 1
    old = old.replace(before, "retained artifact is complete; the repaired checkpoint is recorded below.")
    before = "VM and services pass; subsequent Swift checks were skipped.\n"
    after = before + "Rustup dispatch repair `05c1ebf0` passes all three [Engine CI jobs](https://github.com/snowdamiz/mixer/actions/runs/40247799000).\n"
    assert old.count(before) == 1
    old = old.replace(before, after)
    indent = "   " if name == "PLAN.md" else ""
    before = indent + "and 16 focused controls locally; remote qualification remains pending."
    after = "\n".join(indent + x for x in [
        "and 16 focused controls locally. The repaired macOS CI now passes all 44",
        "methods under Rust 1.98.1; root verifies its 78-member artifact and exact",
        "source bindings. All three Engine CI jobs now pass."])
    assert old.count(before) == 1
    old = old.replace(before, after)
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

paths = {
    "cli/Sources/MixerBuild/AndroidProject.swift",
    "cli/Tests/MixerBuildTests/AndroidProjectTests.swift",
    "docs/android-public-appearance-routing-proposal.md",
    "docs/android-authored-toggle-generated-export.md",
    "docs/android-authored-toggle-generated-export-review.md",
    "docs/swift-ordered-retention-analyzer-framing-ci-rustup-remote.md",
}
for directory in [
    "verification/android-public-appearance-routing-proposal",
    "verification/android-authored-toggle-generated-export",
    "verification/android-authored-toggle-generated-export-review",
    "verification/android-authored-toggle-generated-export-root-review",
    "verification/github-delivery-analyzer-rustup-repair",
    "verification/swift-ordered-retention-analyzer-framing-ci-rustup-remote",
    "verification/swift-ordered-retention-analyzer-framing-ci-rustup-remote-root-review",
]:
    for path in (ROOT / directory).rglob("*"):
        assert not path.is_symlink(), path
        if path.is_file():
            paths.add(path.relative_to(ROOT).as_posix())
assert not any("envelope" in name or "callback" in name or "descriptor-packaging" in name for name in paths)
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
    manifest[name] = digest(data)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "paths.nul").write_bytes(b"".join(x.encode() + b"\0" for x in sorted(paths)))
run("staged-diff-check", ["git", "diff", "--cached", "--check"], (0, 2))
print(json.dumps({"status": "exact-staged-manifest-verified", "paths": len(paths),
                  "bytes": sum(x["bytes"] for x in manifest.values()), "base": BASE}))
