"""Stage only accepted Android observer/profile work and previous terminal CI evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d"
commands = []


def run(name, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    commands.append({"name": name, "argv": argv, "exit": result.returncode,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                     "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert result.returncode in allowed, name
    return result.stdout


def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


accepted = json.loads((ROOT / "verification/android-environment-observer-root-review/implementation-acceptance.json").read_text())
assert accepted["implementation_accepted"] and accepted["status"] == "accepted-scoped-android-observer-host-source-profile"
assert not accepted["public_V2_selected"] and not accepted["GA_qualified"]
assert json.loads((ROOT / "verification/github-delivery-android-owner-core/receipt.json").read_text())["all_jobs_and_steps_passed"]
assert run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
assert run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main"
assert run("index-before", ["git", "diff", "--cached", "--name-only", "-z"]) == b""
assert run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])
metadata = {}
for name, collection, ident in [("work-graph.json", "packages", "W05"), ("gates/ga.json", "gates", "G05")]:
    old = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    live = json.loads((ROOT / name).read_text())
    target = next(x for x in old[collection] if x["id"] == ident)
    current = next(x for x in live[collection] if x["id"] == ident)
    for key in ("environmentObserverLifecycleCandidate", "publicOwnerCoreCandidate", "evidence"):
        target[key] = current[key]
    if collection == "packages":
        for key in ("currentCheckpoint", "nextImplementation"):
            target[key] = current[key]
    metadata[name] = (json.dumps(old, indent=2) + "\n").encode()
ci_line = 'Android host lifecycle core `4e48ac1a` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40267720327) passed all 3 jobs and 40 steps. The new Java suite has local host evidence and is not wired into this existing workflow.\n'
anchor = 'Copied SDK/source-pair compatibility `1f114d8f` is pushed; [Engine CI](https://github.com/snowdamiz/mixer/actions/runs/40263504027) passed all 3 jobs and 40 steps.\n'
for name in ("PLAN.md", "STATUS.md"):
    old = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    assert old.count(anchor) == 1 and ci_line not in old
    old = old.replace(anchor, anchor + ci_line)
    if name == "PLAN.md":
        start, end = "4. **Android and cross-platform UI:**", "5. **Hosted product and console:**"
        old = old[:old.index(start)] + live[live.index(start):live.index(end)] + old[old.index(end):]
    else:
        prior = next(line for line in old.splitlines() if line.startswith("| Android shared UI |"))
        current = next(line for line in live.splitlines() if line.startswith("| Android shared UI |"))
        old = old.replace(prior, current)
    metadata[name] = old.encode()
snapshots = OUT / "metadata-snapshots"
for name, data in metadata.items():
    target = snapshots / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
selection = json.loads((OUT / "selection.json").read_text())
paths = set(selection["product_files"])
paths.update(["docs/android-owner-effect-contract.md", "docs/android-environment-observer-independent-review.md"])
sealed_packets = {
    "verification/android-owner-effect-contract": ("manifest.json", True),
    "verification/android-environment-observer-lifecycle": ("manifest.json", True),
    "verification/android-environment-observer-independent-review": ("final-manifest.json", False),
}
for directory in selection["packet_directories"]:
    if directory in sealed_packets:
        manifest_name, relative = sealed_packets[directory]
        manifest_path = ROOT / directory / manifest_name
        bound = json.loads(manifest_path.read_bytes())["files"]
        for name, row in bound.items():
            path = ROOT / directory / name if relative else ROOT / name
            assert path.is_file() and not path.is_symlink(), path
            assert identity(path.read_bytes()) == row, path
            # Two bytecode files are explicitly producer-sealed historical
            # evidence, never runtime inputs. Preserve those exact bytes.
            paths.add(path.relative_to(ROOT).as_posix())
        paths.add(manifest_path.relative_to(ROOT).as_posix())
        if not relative:
            paths.add(directory + "/final-seal.json")
    else:
        for path in (ROOT / directory).rglob("*"):
            assert not path.is_symlink(), path
            assert "__pycache__" not in path.parts and path.suffix != ".pyc", path
            if path.is_file():
                paths.add(path.relative_to(ROOT).as_posix())
assert not any("swift-envelope" in name or "callback" in name or name.startswith("hosted/") for name in paths)
for name in paths:
    assert (ROOT / name).stat().st_size < 100_000_000
pathspec = OUT / "non-metadata-paths.nul"
pathspec.write_bytes(b"".join(name.encode() + b"\0" for name in sorted(paths)))
run("stage", ["git", "add", "--force", "--pathspec-from-file=" + str(pathspec), "--pathspec-file-nul"])
for name in metadata:
    label = name.replace("/", "-")
    blob = run("metadata-blob-" + label, ["git", "hash-object", "-w", str(snapshots / name)]).decode().strip()
    run("metadata-stage-" + label, ["git", "update-index", "--add", "--cacheinfo", "100644," + blob + "," + name])
paths.update(metadata)
actual = set(run("staged-paths", ["git", "diff", "--cached", "--name-only", "-z"]).decode().strip("\0").split("\0"))
assert actual == paths, {"extra": sorted(actual - paths), "missing": sorted(paths - actual)}
# One cat-file process checks every staged blob without repeated Git startup.
ordered = sorted(paths)
result = subprocess.run(["git", "cat-file", "--batch"], input="".join(":" + name + "\n" for name in ordered).encode(), cwd=ROOT, capture_output=True, check=True, timeout=60)
offset = 0
manifest = {}
for name in ordered:
    end = result.stdout.index(b"\n", offset)
    header = result.stdout[offset:end].decode().split()
    assert len(header) == 3 and header[1] == "blob"
    size = int(header[2]); offset = end + 1
    data = result.stdout[offset:offset + size]; offset += size + 1
    expected = metadata[name] if name in metadata else (ROOT / name).read_bytes()
    assert data == expected, name
    manifest[name] = identity(data)
assert offset == len(result.stdout)
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
(OUT / "paths.nul").write_bytes(b"".join(name.encode() + b"\0" for name in ordered))
run("diff-check", ["git", "diff", "--cached", "--check"], (0, 2))
print(json.dumps({"status": "exact-staged-manifest-verified", "paths": len(paths), "bytes": sum(x["bytes"] for x in manifest.values()), "base": BASE}))
