"""Deliver the exact root-selected staged tree without touching live lanes."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = "b45963c03816112972499bd60073039f36916272"
records = []


def run(name, argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    records.append({"name": name, "argv": argv, "exit": result.returncode,
                    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                    "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
    (OUT / "delivery-commands.json").write_text(json.dumps(records, indent=2) + "\n")
    assert result.returncode == 0, name
    return result.stdout


assert run("head-before-commit", ["git", "rev-parse", "HEAD"]).decode().strip() == BASE
manifest_bytes = (OUT / "manifest.json").read_bytes()
assert hashlib.sha256(manifest_bytes).hexdigest() == "196a47b43803cb15137290e8ba2fa48cd1f2e911653e737be642fc43b98f6f11"
manifest = json.loads(manifest_bytes)
names = sorted(manifest)
staged = run("paths-before-commit", ["git", "diff", "--cached", "--name-only", "-z"]).decode().strip("\0").split("\0")
assert sorted(staged) == names
p = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, input="".join(":" + n + "\n" for n in names).encode(), capture_output=True, check=True, timeout=60)
offset = 0
for name in names:
    end = p.stdout.index(b"\n", offset)
    header = p.stdout[offset:end].decode().split()
    assert header[1] == "blob"
    size = int(header[2]); offset = end + 1
    data = p.stdout[offset:offset + size]; offset += size + 1
    assert {"bytes": size, "sha256": hashlib.sha256(data).hexdigest()} == manifest[name], name
assert offset == len(p.stdout)
tree = run("selected-tree", ["git", "write-tree"]).decode().strip()
run("commit", ["git", "commit", "-m", "Qualify standalone Swift analyzer envelope in CI"])
head = run("committed-head", ["git", "rev-parse", "HEAD"]).decode().strip()
assert run("committed-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == tree
assert run("committed-parent", ["git", "rev-parse", "HEAD^"]).decode().strip() == BASE
assert run("index-after-commit", ["git", "diff", "--cached", "--name-only", "-z"]) == b""
run("push", ["git", "push", "origin", "HEAD:main"])
assert run("remote-head", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "status": "pushed-ci-discovery-pending", "commit": head, "parent": BASE, "tree": tree,
           "paths": len(manifest), "bytes": sum(x["bytes"] for x in manifest.values()),
           "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
           "remote_head_verified": True, "force_push": False,
           "scope": "Accepted standalone fixture envelope and corrected CI runner; exact narrow workflow wiring and preserved rejected and accepted evidence. No semantic replay or target integration.",
           "root_acceptance_sha256": "8c37b18e539f074bda0b55e046c58a446b9eb705e821dab2aa3499474ab5af5a",
           "all_jobs_and_steps_passed": False, "CI_1_98_1_envelope_qualified": False,
           "native_runtime_or_capture_started": False, "GA_qualified": False}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
