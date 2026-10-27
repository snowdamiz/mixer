"""Retain one fresh data-only collection invocation and its outputs."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


assert __debug__ and len(sys.argv) == 2 and sys.argv[1] == "collection"
name = "collection"
script = "collect-and-review.py"
assert not (HERE / (name + ".command.json")).exists()
preparation = json.loads((HERE / "preparation.json").read_bytes())
for item in preparation["scripts"]:
    assert digest((REPO / item["target"]).read_bytes()) == item["adapted_digest"]
argv = [sys.executable, "-B", str(HERE / script)]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
timed_out = False
try:
    result = subprocess.run(argv, cwd=REPO, capture_output=True, timeout=60)
    stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
except subprocess.TimeoutExpired as failure:
    stdout, stderr, exit_code = failure.stdout or b"", failure.stderr or b"", None
    timed_out = True
for stream, payload in (("stdout", stdout), ("stderr", stderr)):
    (HERE / (name + "." + stream)).write_bytes(payload)
(HERE / (name + ".command.json")).write_text(json.dumps({
    "started_utc": started, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": argv, "cwd": str(REPO), "exit_code": exit_code,
    "stdout": digest(stdout), "stderr": digest(stderr), "python": sys.version,
    "timed_out": timed_out, "child_timeout_seconds": 60,
    "scope": "New reviewed data-only auditor child; no artifact source imported or executed; no retry, Git or network mutation",
}, indent=2) + "\n")
print(json.dumps({"invocation": name, "exit_code": exit_code, "timed_out": timed_out,
                  "stdout": digest(stdout), "stderr": digest(stderr)}))
if exit_code != 0 or timed_out:
    raise SystemExit(1)
