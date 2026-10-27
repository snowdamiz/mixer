"""Write-once, read-only observations of CI for this exact pushed checkpoint."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
COMMIT = "9905f5a91704e20f10c166343d17ab491199b534"
name = sys.argv[1]
assert name.startswith(("ci-runs-", "ci-jobs-")) and name.rsplit("-", 1)[1].isdigit()
assert not (OUT / (name + ".stdout")).exists()
if name.startswith("ci-runs-"):
    argv = ["gh", "run", "list", "--repo", "snowdamiz/mixer", "--commit", COMMIT,
            "--limit", "5", "--json", "databaseId,headSha,status,conclusion,url,name"]
else:
    run = sys.argv[2]
    assert run.isdigit()
    argv = ["gh", "run", "view", run, "--repo", "snowdamiz/mixer", "--json",
            "databaseId,headSha,status,conclusion,url,jobs,attempt"]
start = time.monotonic()
child = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed = False
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    os.killpg(child.pid, signal.SIGTERM)
    try:
        stdout, stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=5)
try:
    os.killpg(child.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
for suffix, data in (("stdout", stdout), ("stderr", stderr)):
    with (OUT / (name + "." + suffix)).open("xb") as stream:
        stream.write(data)
receipt = {"argv": argv, "exit": child.returncode, "timed_out": timed,
           "elapsed_seconds": time.monotonic() - start, "at": datetime.now(timezone.utc).isoformat(),
           "source_commit": COMMIT, "owned_child_reaped": True, "owned_group_absent": absent,
           "python": sys.version, "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
           "stderr_sha256": hashlib.sha256(stderr).hexdigest()}
with (OUT / (name + ".command.json")).open("x") as stream:
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
assert not timed and absent and child.returncode == 0
data = json.loads(stdout)
if isinstance(data, list):
    assert all(row["headSha"] == COMMIT for row in data)
    print(json.dumps(data))
else:
    assert data["headSha"] == COMMIT and str(data["databaseId"]) == run
    print(json.dumps({"status": data["status"], "conclusion": data["conclusion"],
                      "attempt": data["attempt"], "jobs": [
                          {"name": job["name"], "status": job["status"], "conclusion": job["conclusion"],
                           "steps": len(job["steps"])} for job in data["jobs"]]}))
