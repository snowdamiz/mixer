#!/usr/bin/env python3
"""Retain terminal CI observation for one immutable source checkpoint."""
import datetime
import hashlib
import json
import pathlib
import subprocess

OUT = pathlib.Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REVISION = "68910a1e061426654d7e1242ed88f38299d1cd1b"
COMMAND = ["gh", "run", "view", "40070249623", "--repo", "snowdamiz/mixer",
           "--json", "status,conclusion,headSha,jobs,url,createdAt,updatedAt"]


def capture(command, name):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
    (OUT / name).write_bytes(result.stdout)
    if result.stderr:
        (OUT / (name + ".stderr")).write_bytes(result.stderr)
    return result.stdout


run = json.loads(capture(COMMAND, "run.json"))
assert run["headSha"] == REVISION
assert run["status"] == "completed" and run["conclusion"] == "success"
assert {job["name"] for job in run["jobs"]} == {"swift", "vm", "services"}
assert all(job["status"] == "completed" and job["conclusion"] == "success"
           for job in run["jobs"])
assert all(step["conclusion"] == "success"
           for job in run["jobs"] for step in job["steps"])
capture(["gh", "--version"], "gh-version.txt")
capture(["git", "show", REVISION + ":.github/workflows/verify.yml"], "verify.yml")
bindings = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(OUT.iterdir()) if p.is_file() and p.name != "receipt.json"}
receipt = {
    "schema": 1,
    "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": REVISION,
    "command": COMMAND,
    "exit_code": 0,
    "files": bindings,
    "jobs": [{k: job[k] for k in ("name", "conclusion", "url", "completedAt")}
             for job in run["jobs"]],
    "scope": "Terminal GitHub engine workflow/job/step observation at the artifact CBOR checkpoint. Swift, VM and Go service host tests/cross-builds passed. Separate Phoenix Linux qualification is retained under github-ci-68910a1-phoenix. This observation does not qualify native runtime behavior, providers, physical phones or GA gates."
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"source": REVISION, "jobs": [j["name"] for j in receipt["jobs"]],
                  "status": "passed", "bindings": len(bindings)}))
