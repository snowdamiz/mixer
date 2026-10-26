"""One bounded, read-only CI snapshot. No workflow retry or other mutation."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SHA = "62db9518c0c108cb44b81455c9be239df4ee00db"
RUN = "40400072603"


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


assert __debug__ and len(sys.argv) == 2 and sys.argv[1].isdigit()
name = "ci-progress-" + sys.argv[1]
assert not (HERE / (name + ".command.json")).exists()
argv = ["gh", "run", "view", RUN, "--repo", "snowdamiz/mixer", "--json", "databaseId,headSha,status,conclusion,attempt,jobs,url"]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=60)
for stream in ("stdout", "stderr"):
    (HERE / (name + "." + stream)).write_bytes(getattr(result, stream))
(HERE / (name + ".command.json")).write_text(json.dumps({
    "started_utc": started, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": argv, "cwd": str(REPO), "exit_code": result.returncode,
    "stdout": digest(result.stdout), "stderr": digest(result.stderr),
    "scope": "Read-only exact run terminal status snapshot; no retry or mutation", "child_timeout_seconds": 60,
}, indent=2) + "\n")
assert result.returncode == 0
row = json.loads(result.stdout)
assert row["databaseId"] == int(RUN) and row["headSha"] == SHA and row["attempt"] == 1
summary = {key: row[key] for key in ("databaseId", "headSha", "status", "conclusion", "attempt", "url")}
summary["jobs"] = [{"name": j["name"], "status": j["status"], "conclusion": j["conclusion"], "steps": len(j["steps"]),
                    "running_steps": [s["name"] for s in j["steps"] if s["status"] == "in_progress"]} for j in row["jobs"]]
print(json.dumps(summary))
