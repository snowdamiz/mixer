#!/usr/bin/env python3
"""Read the two existing CI handles; never dispatch or retry a workflow."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
HEAD = "c4e1f5717c9d912ffa5b18942d088078b0c766f7"
observation = OUT / sys.argv[1]
observation.mkdir(exist_ok=False)
commands = []
rows = []
for name, run in [("console", "40195410847"), ("engine", "40195410870")]:
    argv = ["gh", "run", "view", run, "--repo", "snowdamiz/mixer", "--json",
            "status,conclusion,jobs,headSha,url"]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=45)
    (observation / f"{name}.json").write_bytes(result.stdout)
    (observation / f"{name}.stderr").write_bytes(result.stderr)
    commands.append({"argv": argv, "exitCode": result.returncode,
                     "stdoutSHA256": hashlib.sha256(result.stdout).hexdigest(),
                     "stderrSHA256": hashlib.sha256(result.stderr).hexdigest()})
    assert result.returncode == 0
    value = json.loads(result.stdout)
    assert value["headSha"] == HEAD
    rows.append({"workflow": name, "run": run, "url": value["url"],
                 "status": value["status"], "conclusion": value["conclusion"],
                 "jobs": [{"name": job["name"], "status": job["status"],
                           "conclusion": job["conclusion"], "steps": len(job["steps"]),
                           "skippedSteps": sum(step["conclusion"] == "skipped" for step in job["steps"])}
                          for job in value["jobs"]]})
receipt = {"observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "sourceRevision": HEAD, "commands": commands, "workflows": rows,
           "ghVersion": subprocess.check_output(["gh", "--version"], text=True).strip(),
           "scope": "Existing hosted CI only; no workflow dispatch, native, provider or GA qualification."}
(observation / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(rows))
