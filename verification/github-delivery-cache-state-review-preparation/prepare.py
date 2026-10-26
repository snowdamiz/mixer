"""Prepare sealed reviewer evidence and prior terminal CI without active product files."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "69b0c522fa02d05a4f5062686163e36097d9f3bc"
paths = set()
records = []


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def require(value, message):
    if not value:
        raise ValueError(message)


def run(name, argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    records.append({"name": name, "argv": argv, "exit": result.returncode,
                    "stdout": ident(result.stdout), "stderr": ident(result.stderr),
                    "at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    (OUT / "commands.json").write_text(json.dumps(records, indent=2) + "\n")
    require(result.returncode == 0, "Command failed: " + name)
    return result.stdout


def add(name, expected=None):
    relative = Path(name)
    require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe path")
    require(name.startswith(("verification/", "docs/")), "Unexpected path")
    require(not name.startswith("verification/swift-cache-state-implementation/"), "Active product path")
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), "Nonregular path")
    require("__pycache__" not in path.parts and path.suffix != ".pyc", "Cache file")
    data = path.read_bytes()
    require(len(data) < 100_000_000, "Oversized member")
    if expected is not None:
        require(ident(data) == {key: expected[key] for key in ("bytes", "sha256")}, "Member differs: " + name)
    paths.add(name)


require(run("head", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE, "HEAD changed")
require(run("branch", ["git", "branch", "--show-current"]).decode().strip() == "main", "Wrong branch")
require(run("index-before", ["git", "diff", "--cached", "--name-only", "-z"]) == b"", "Nonempty index")
require(run("remote-before", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE, "Remote advanced")
run("git-version", ["git", "--version"])
run("gh-version", ["gh", "--version"])

for name, digest, count, total in [
    ("verification/swift-cache-state-independent-review/preaccess/seal.json", "1cc596fe2a49f082701f2130bccfe8a427054071227e7655d15850e9978b3d1c", 173, 27268876),
    ("verification/swift-cache-state-independent-review/execution-preparation/seal.json", "07ff2daf1527fa459f68a4056b749ef71282b98f5b5a4ea634ba9ef19dae5ad6", 1479, 8158127),
]:
    path = ROOT / name
    require(ident(path.read_bytes())["sha256"] == digest, "Seal differs")
    data = json.loads(path.read_bytes())
    require(len(data["members"]) == data["member_count"] == count, "Count differs")
    require(sum(row["bytes"] for row in data["members"]) == data["member_bytes"] == total, "Bytes differ")
    for row in data["members"]:
        add(row["path"], row)
    for relative in data["excluded"]:
        add(relative)

for name, digest in [
    ("implementation-selection.json", "012ef007459aa8561da2f3542902b6f4193c8ac06c5c325944502042103acad3"),
    ("public-getter-selection.json", "80b8b39365e137f5f4db13f8a8348ca79aa17eb5abadf58ac929e3d25aec92e1"),
    ("execution-preparation-acceptance.json", "e116b5e77c5f2c0c3b1704f1864b45fdca1558d027e59fb41c7384890b286018"),
]:
    relative = "verification/swift-semantic-adapter-root-review/" + name
    require(ident((ROOT / relative).read_bytes())["sha256"] == digest, "Root receipt differs")
    add(relative)
for name in ("select_implementation.py", "accept_execution_preparation.py"):
    add("verification/swift-semantic-adapter-root-review/" + name)

prior = ROOT / "verification/github-delivery-source-contracts"
terminal = json.loads((prior / "ci-terminal.json").read_bytes())
require(ident((prior / "ci-terminal.json").read_bytes())["sha256"] == "aa372c232285a720a9ebc7a1747ee116c1f8db797053508218a97970356e2ba2", "Prior terminal receipt differs")
for path in sorted(prior.rglob("*")):
    require(not path.is_symlink(), "Unexpected prior evidence symlink")
    if path.is_file() and path.name != "base-tree.stdout":
        add(path.relative_to(ROOT).as_posix())

metadata = {}
for name, collection, swift_id, android_id in [("work-graph.json", "packages", "W08", "W05"), ("gates/ga.json", "gates", "G02", "G05")]:
    baseline = json.loads(run("base-" + name.replace("/", "-"), ["git", "show", BASE + ":" + name]))
    chosen = json.loads(json.dumps(baseline))
    live = json.loads((ROOT / name).read_bytes())
    by_id = {entry["id"]: entry for entry in live[collection]}
    for before, after in zip(baseline[collection], chosen[collection]):
        if after["id"] == swift_id:
            after["fixtureCacheStateContractCandidate"] = by_id[swift_id]["fixtureCacheStateContractCandidate"]
        elif after["id"] == android_id:
            after["privateOwnerEffectContractCandidate"]["delivery"] = by_id[android_id]["privateOwnerEffectContractCandidate"]["delivery"]
        else:
            require(before == after, "Unrelated metadata changed")
        for key in ("state", "status", "reviewer", "accountableReviewer"):
            require(before.get(key) == after.get(key), "Gate promotion")
    metadata[name] = (json.dumps(chosen, indent=2) + "\n").encode()

for name in ("PLAN.md", "STATUS.md"):
    selected = run("base-" + name, ["git", "show", BASE + ":" + name]).decode()
    live = (ROOT / name).read_text()
    start = "The fixture cache-state source contract and terminal correction are accepted"
    end = "2. **iOS shared UI:**" if name == "PLAN.md" else "Independent iOS source review"
    selected = selected[:selected.index(start)] + live[live.index(start):live.index(end)] + selected[selected.index(end):]
    prefix = "Reviewed owner/cache-state contracts `69b0c522`"
    current_line = next(line for line in live.splitlines() if line.startswith(prefix))
    matches = [line for line in selected.splitlines() if line.startswith(prefix)]
    if matches:
        selected = selected.replace(matches[0], current_line, 1)
    else:
        preceding = next(line for line in selected.splitlines() if line.startswith("Standalone Swift fixture-envelope CI `0b8e3fd8`"))
        selected = selected.replace(preceding, preceding + "\n" + current_line, 1)
    metadata[name] = selected.encode()

for name, data in metadata.items():
    destination = OUT / "metadata-snapshots" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
selection = {
    "schema": 1, "base": BASE, "ordinary_paths": sorted(paths),
    "ordinary_manifest": {name: ident((ROOT / name).read_bytes()) for name in sorted(paths)},
    "metadata_manifest": {name: ident(data) for name, data in metadata.items()},
    "metadata_scope": "W08/G02 fixture cache-state independent preparation and selection; W05/G05 prior contract delivery only; corresponding PLAN/STATUS paragraph and prior CI line",
    "scope": "Sealed independent preaccess and execution tooling, root implementation/getter selection, completed prior contract CI evidence",
    "active_product_source_and_tests_excluded": True,
    "expanded_prior_tree_inventory_excluded": "base-tree.stdout; exact single-member ZIP and archive recovery note retained",
    "implementation_accepted": False, "native_runtime_or_capture_started": False, "GA_qualified": False,
    "python": sys.version,
}
(OUT / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
(OUT / "non-metadata-paths.nul").write_bytes(b"".join(name.encode() + b"\0" for name in sorted(paths)))
print(json.dumps({"status": "prepared-not-staged", "paths": len(paths), "bytes": sum(row["bytes"] for row in selection["ordinary_manifest"].values()), "selection_sha256": ident((OUT / "selection.json").read_bytes())["sha256"]}))
