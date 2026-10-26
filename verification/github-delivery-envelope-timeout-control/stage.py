"""Stage and verify only the frozen accepted documentation/evidence selection."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
EXPECTED_SELECTION = "00fd64b11e73cc26571d30a76b633c14a7fc9d423a287fb7e959a34acc7b48ea"
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
    (OUT / "stage-commands.json").write_text(json.dumps(records, indent=2) + "\n")
    require(result.returncode in allowed, "Command failed: " + name)
    return result.stdout


raw = (OUT / "selection.json").read_bytes()
require(ident(raw)["sha256"] == EXPECTED_SELECTION, "Selection changed")
selection = json.loads(raw)
require(run("stage-head", ["git", "rev-parse", "HEAD"]).decode().strip() == selection["base"], "HEAD changed")
require(run("stage-index-before", ["git", "diff", "--cached", "--name-only", "-z"]) == b"", "Index changed")
require(run("object-format", ["git", "rev-parse", "--show-object-format"]).strip() == b"sha1", "Unexpected object format")
expected = {}
for name, identity in selection["ordinary_manifest"].items():
    data = (ROOT / name).read_bytes()
    require(ident(data) == identity, "Selected input changed: " + name)
    expected[name] = data
for name, identity in selection["metadata_manifest"].items():
    data = (OUT / "metadata-snapshots" / name).read_bytes()
    require(ident(data) == identity, "Selected metadata changed")
    expected[name] = data
base = {}
for entry in run("base-tree", ["git", "ls-tree", "-r", "-z", selection["base"]]).split(b"\0"):
    if not entry:
        continue
    header, name = entry.split(b"\t", 1)
    base[name.decode()] = header.decode().split()
changed = {name for name, data in expected.items()
           if base.get(name, ["", "", ""])[2] != hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()}
run("stage-ordinary", ["git", "add", "--force", "--pathspec-from-file=" + str(OUT / "non-metadata-paths.nul"), "--pathspec-file-nul"])
for name in selection["metadata_manifest"]:
    blob = run("metadata-blob-" + name.replace("/", "-"), ["git", "hash-object", "-w", str(OUT / "metadata-snapshots" / name)]).decode().strip()
    run("metadata-stage-" + name.replace("/", "-"), ["git", "update-index", "--add", "--cacheinfo", "100644," + blob + "," + name])
actual = {name for name in run("staged-paths", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0") if name}
require(actual == changed, "Staged set differs: " + repr({"extra": sorted(actual - changed), "missing": sorted(changed - actual)}))
ordered = sorted(actual)
result = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
                        input="".join(":" + name + "\n" for name in ordered).encode(),
                        capture_output=True, check=True, timeout=60)
offset = 0
manifest = {}
for name in ordered:
    end = result.stdout.index(b"\n", offset)
    header = result.stdout[offset:end].decode().split()
    require(len(header) == 3 and header[1] == "blob", "Unexpected index object")
    size = int(header[2]); offset = end + 1
    data = result.stdout[offset:offset + size]; offset += size + 1
    require(data == expected[name], "Index bytes differ: " + name)
    manifest[name] = ident(data)
require(offset == len(result.stdout), "Trailing batch data")
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
run("diff-check", ["git", "diff", "--cached", "--check"], (0, 2))
run("authored-diff-check", ["git", "diff", "--cached", "--check", "--"] + [name for name in ordered if not name.startswith("verification/")])
run("diff-stat", ["git", "diff", "--cached", "--stat"])
print(json.dumps({"status": "exact-staged-manifest-verified", "paths": len(manifest),
                  "bytes": sum(row["bytes"] for row in manifest.values()),
                  "manifest_sha256": ident((OUT / "manifest.json").read_bytes())["sha256"]}))
