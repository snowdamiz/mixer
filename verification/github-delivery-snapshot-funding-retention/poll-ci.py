"""Read-only exact-commit CI snapshots; each named observation is write-once."""
from pathlib import Path
import datetime, hashlib, json, os, signal, subprocess, sys, time
OUT=Path(__file__).resolve().parent
COMMIT="32b5075a5f203cb25ae357492b70f0f724f3ea19"
RUN="40482914167"
name=sys.argv[1]
assert name.startswith("ci-jobs-") and name[8:].isdigit()
assert not (OUT/(name+".stdout")).exists()
argv=["gh","run","view",RUN,"--repo","snowdamiz/mixer","--json","databaseId,headSha,status,conclusion,url,jobs,attempt"]
started=time.monotonic()
child=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed=False
try:
 stdout,stderr=child.communicate(timeout=45)
except subprocess.TimeoutExpired:
 timed=True
 os.killpg(child.pid,signal.SIGTERM)
 try: stdout,stderr=child.communicate(timeout=5)
 except subprocess.TimeoutExpired:
  os.killpg(child.pid,signal.SIGKILL)
  stdout,stderr=child.communicate(timeout=5)
try:
 os.killpg(child.pid,0)
 absent=False
except ProcessLookupError: absent=True
for suffix,data in (("stdout",stdout),("stderr",stderr)):
 with (OUT/(name+"."+suffix)).open("xb") as f:f.write(data)
receipt={"argv":argv,"exit":child.returncode,"timed_out":timed,"elapsed_seconds":time.monotonic()-started,"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":COMMIT,"owned_child_reaped":True,"owned_group_absent":absent,"python":sys.version,"stdout_sha256":hashlib.sha256(stdout).hexdigest(),"stderr_sha256":hashlib.sha256(stderr).hexdigest()}
with (OUT/(name+".command.json")).open("x") as f:json.dump(receipt,f,indent=2);f.write("\n")
assert not timed and absent and child.returncode==0
j=json.loads(stdout);assert j["headSha"]==COMMIT and str(j["databaseId"])==RUN
print(json.dumps({"status":j["status"],"conclusion":j["conclusion"],"attempt":j["attempt"],"jobs":[{"name":x["name"],"status":x["status"],"conclusion":x["conclusion"],"steps":len(x["steps"])} for x in j["jobs"]]}))
