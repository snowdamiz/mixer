"""Prepare exact accepted contract/evidence blobs without staging active lanes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c"
paths = set()
records = []


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def run(name, argv, allowed=(0,)):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    records.append({"name": name, "argv": argv, "exit": result.returncode,
                    "stdout": ident(result.stdout), "stderr": ident(result.stderr),
                    "at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (OUT / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    require(result.returncode in allowed, "Command failed: " + name)
    return result.stdout


def add(path, expected=None):
    relative = Path(path)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path")
    p = ROOT / relative
    require(p.is_file() and not p.is_symlink(), "Nonregular path: " + str(path))
    require("__pycache__" not in p.parts and p.suffix != ".pyc", "Cache path")
    data = p.read_bytes()
    require(len(data) < 100_000_000, "Oversized path")
    if expected is not None:
        require(ident(data) == {k: expected[k] for k in ("bytes", "sha256")}, "Changed member: " + str(path))
    require(str(path).startswith(("docs/", "verification/")), "Product path selected: " + str(path))
    paths.add(relative.as_posix())


def closed_directory(name, exclude=()):
    for p in sorted((ROOT / name).rglob("*")):
        require(not p.is_symlink(), "Symlink in closed directory")
        relative = p.relative_to(ROOT).as_posix()
        if p.is_file() and not relative.startswith(exclude):
            add(relative)


require(run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE, "HEAD changed")
require(run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main", "Wrong branch")
require(run("index-before", ["git", "diff", "--cached", "--name-only", "-z"]) == b"", "Nonempty index")
require(run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE, "Remote advanced")
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])

android_root = ROOT / "verification/android-private-owner-effect-integration-root-review/implementation-selection.json"
require(ident(android_root.read_bytes())["sha256"] == "d698ad2ca8ed0706038a652a5b665bb8818fdc4388ffaf34194a73bec11ab6aa", "Android acceptance changed")
android = json.loads(android_root.read_bytes())
for packet in android["packets"]:
    manifest = ROOT / packet["manifest"]
    require(ident(manifest.read_bytes())["sha256"] == packet["sha256"], "Android seal changed")
    data = json.loads(manifest.read_bytes())
    base = manifest.parent if "/correction-1/preaccess/" in packet["manifest"] else ROOT
    for name, expected in data["files"].items():
        add((base / name).relative_to(ROOT).as_posix(), expected)
    add(packet["manifest"])
    require(len(data["files"]) == packet["members"] and sum(x["bytes"] for x in data["files"].values()) == packet["bytes"], "Android packet totals")

for path, digest in [
    ("verification/android-private-owner-independent-review/preaccess/manifest.json", "3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b"),
    ("verification/android-private-owner-independent-review/leaf-review-1/manifest.json", "a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7"),
]:
    p = ROOT / path
    require(ident(p.read_bytes())["sha256"] == digest, "Independent Android seal changed")
    data = json.loads(p.read_bytes())
    for name, expected in data["files"].items():
        add(name, expected)
    closed_directory(p.parent.relative_to(ROOT).as_posix())
for number, digest in [(1, "f4633dab3fd25713feaf93162b5ffb888b277108683781b7b118a010cf14b79e"),
                       (2, "d58e1c1b8ca942089603c1e5d3a63bec93198935f256e7ab6f92e2b7a31a70f9"),
                       (3, "d772bfae9febf9106b1338be259cb026e4293d8e287fa792939340754ccdda38")]:
    directory = f"verification/android-private-owner-integration-implementation/leaf-candidate-{number}"
    p = ROOT / directory / "manifest.json"
    require(ident(p.read_bytes())["sha256"] == digest, "Leaf seal changed")
    for name, expected in json.loads(p.read_bytes())["files"].items():
        add(directory + "/inputs/" + name, expected)
    closed_directory(directory)

swift_root = ROOT / "verification/swift-semantic-adapter-root-review/combined-contract-acceptance.json"
require(ident(swift_root.read_bytes())["sha256"] == "aac275052af88c802b0594c2d47318898d383b90f20d99a3914a4080c1a76dcc", "Swift acceptance changed")
swift = json.loads(swift_root.read_bytes())
for packet in swift["packets"]:
    p = ROOT / packet["seal"]
    require(ident(p.read_bytes())["sha256"] == packet["sha256"], "Swift seal changed")
    data = json.loads(p.read_bytes())
    base = ROOT if p.parent.name in ("swift-semantic-adapter-prerequisite", "swift-semantic-adapter-terminal-correction") else p.parent
    for row in data["members"]:
        add((base / row["path"]).relative_to(ROOT).as_posix(), row)
    for name in data["excluded"]:
        add((base / name).relative_to(ROOT).as_posix())
add(swift["review_document"])

for directory in [
    "verification/android-private-owner-effect-integration-proposal",
    "verification/android-private-owner-effect-contract-review",
    "verification/android-private-owner-effect-roster-amendment",
    "verification/android-private-owner-effect-roster-review",
    "verification/android-private-owner-effect-integration-root-review",
    "verification/swift-semantic-adapter-prerequisite",
    "verification/swift-semantic-adapter-contract-review",
    "verification/swift-semantic-adapter-terminal-correction",
    "verification/swift-semantic-adapter-terminal-review",
    "verification/swift-semantic-adapter-root-review",
    "verification/github-delivery-android-environment-observer",
    "verification/github-delivery-swift-envelope-ci",
]:
    closed_directory(directory, ("verification/github-delivery-swift-envelope-ci/artifact-attempt-2/output/",))
for document in ["docs/android-private-owner-dirty-transaction-disposition.md",
                 "docs/swift-semantic-adapter-contract-review.md"]:
    add(document)

metadata = {}
scopes = {}
for name, collection, android_id, swift_id in [("work-graph.json", "packages", "W05", "W08"),
                                             ("gates/ga.json", "gates", "G05", "G02")]:
    baseline = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    chosen = json.loads(json.dumps(baseline))
    live = json.loads((ROOT / name).read_bytes())
    fields_by_id = {
        android_id: ["evidence", "environmentObserverLifecycleCandidate", "privateOwnerEffectContractCandidate"],
        swift_id: ["evidence", "orderedRetentionAnalyzerEnvelopeCandidate", "orderedRetentionAnalyzerEnvelopeCI", "fixtureCacheStateContractCandidate"],
    }
    if collection == "packages":
        for fields in fields_by_id.values():
            fields.append("nextImplementation")
    for selected_id, fields in fields_by_id.items():
        target = next(x for x in chosen[collection] if x["id"] == selected_id)
        current = next(x for x in live[collection] if x["id"] == selected_id)
        for field in fields:
            target[field] = current[field]
    for before, after in zip(baseline[collection], chosen[collection]):
        require(before["id"] == after["id"], "Metadata ordering")
        for key in ("state", "status", "reviewer", "accountableReviewer"):
            require(before.get(key) == after.get(key), "Gate promotion")
        if before["id"] not in fields_by_id:
            require(before == after, "Unrelated metadata changed")
    metadata[name] = (json.dumps(chosen, indent=2) + "\n").encode()
    scopes[name] = fields_by_id

for name in ("PLAN.md", "STATUS.md"):
    baseline = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    selected = baseline
    sections = [("1. **Owned Swift interpreter:**", "2. **iOS shared UI:**"),
                ("4. **Android and cross-platform UI:**", "5. **Hosted product and console:**")] if name == "PLAN.md" else [
                ("The new single full Swift reactor attempt", "Independent iOS source review")]
    for start, end in sections:
        selected = selected[:selected.index(start)] + live[live.index(start):live.index(end)] + selected[selected.index(end):]
    if name == "STATUS.md":
        start, end = "The private Android owner contract", "## Customer workspace discovery and console composition"
        selected = selected.replace(end, live[live.index(start):live.index(end)] + end, 1)
    prefix = "Android observer/source-profile repair `b45963c0`"
    oldline = next(line for line in selected.splitlines() if line.startswith(prefix))
    newline = next(line for line in live.splitlines() if line.startswith(prefix))
    swiftline = next(line for line in live.splitlines() if line.startswith("Standalone Swift fixture-envelope CI `0b8e3fd8`"))
    selected = selected.replace(oldline, newline + "\n" + swiftline)
    metadata[name] = selected.encode()

snapshots = OUT / "metadata-snapshots"
for name, data in metadata.items():
    p = snapshots / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
selection = {"schema": 1, "base": BASE, "ordinary_paths": sorted(paths), "metadata_scope": scopes,
             "ordinary_manifest": {name: ident((ROOT / name).read_bytes()) for name in sorted(paths)},
             "metadata_manifest": {name: ident(data) for name, data in metadata.items()},
             "scope": "Accepted source contracts, independently reviewed mechanical leaves and terminal prior-head CI evidence only",
             "active_product_tests_and_new_fixture_preaccess_excluded": True,
             "expanded_remote_artifact_excluded": "artifact-attempt-2/output; immutable ZIP and per-member manifest retained",
             "native_runtime_or_capture_started": False, "GA_qualified": False}
(OUT / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
(OUT / "non-metadata-paths.nul").write_bytes(b"".join(name.encode() + b"\0" for name in sorted(paths)))
print(json.dumps({"status": "prepared-not-staged", "ordinary_paths": len(paths),
                  "bytes": sum(x["bytes"] for x in selection["ordinary_manifest"].values()),
                  "selection_sha256": ident((OUT / "selection.json").read_bytes())["sha256"],
                  "python": sys.version}))
