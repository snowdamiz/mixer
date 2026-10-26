"""Commit and push the exact audited source-contract checkpoint."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "69b0c522fa02d05a4f5062686163e36097d9f3bc"
EXPECTED = "813c871e2354b525bb1e7c7d7e40c7f14b9f420303142a679c55da83847321a0"
commands = []


def require(value, message):
    if not value:
        raise ValueError(message)


def run(name, argv):
    p = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(p.stdout)
    (OUT / (name + ".stderr")).write_bytes(p.stderr)
    commands.append({"name": name, "argv": argv, "exit": p.returncode,
                     "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     "stdout_sha256": hashlib.sha256(p.stdout).hexdigest(),
                     "stderr_sha256": hashlib.sha256(p.stderr).hexdigest()})
    (OUT / "delivery-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    require(p.returncode == 0, "Command failed: " + name)
    return p.stdout


require(run("head-before-commit", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE, "HEAD changed")
require(run("branch-before-commit", ["git", "branch", "--show-current"]).decode().strip() == "main", "Wrong branch")
require(run("remote-before-commit", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == BASE, "Remote changed")
raw = (OUT / "manifest.json").read_bytes()
require(hashlib.sha256(raw).hexdigest() == EXPECTED, "Manifest changed")
manifest = json.loads(raw)
names = sorted(manifest)
staged = [name for name in run("paths-before-commit", ["git", "diff", "--cached", "--name-only", "-z"]).decode().split("\0") if name]
require(sorted(staged) == names, "Index selection changed")
p = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT,
                   input="".join(":" + name + "\n" for name in names).encode(),
                   capture_output=True, check=True, timeout=60)
offset = 0
for name in names:
    end = p.stdout.index(b"\n", offset)
    header = p.stdout[offset:end].decode().split()
    require(len(header) == 3 and header[1] == "blob", "Unexpected object")
    size = int(header[2]); offset = end + 1
    data = p.stdout[offset:offset + size]; offset += size + 1
    require({"bytes": size, "sha256": hashlib.sha256(data).hexdigest()} == manifest[name], "Index bytes changed: " + name)
require(offset == len(p.stdout), "Unexpected trailing data")
tree = run("selected-tree", ["git", "write-tree"]).decode().strip()
run("commit", ["git", "commit", "-m", "Seal independent cache-state review preparation"])
head = run("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
require(run("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == tree, "Tree differs")
require(run("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE, "Parent differs")
require(run("index-after-commit", ["git", "diff", "--cached", "--name-only", "-z"]) == b"", "Index not empty")
run("push", ["git", "push", "origin", "HEAD:main"])
require(run("remote-head", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head, "Remote differs")
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "status": "pushed-ci-discovery-pending", "commit": head, "parent": BASE, "tree": tree,
           "paths": len(names), "bytes": sum(row["bytes"] for row in manifest.values()),
           "manifest_sha256": EXPECTED, "remote_head_verified": True, "force_push": False,
           "scope": "Sealed independent cache-state preaccess and execution tooling, root implementation/getter selections, and terminal prior 69b CI evidence. Active product implementation excluded.",
           "all_jobs_and_steps_passed": False, "prior_69b_CI_passed": True,
           "native_runtime_or_capture_started": False, "GA_qualified": False}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
