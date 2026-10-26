#!/usr/bin/env python3
"""File-backed, owned-deadline custody for the offline finalizer."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
out=HERE/"finalization-command";out.mkdir(exist_ok=False)
source=HERE/"finalize_implementation.py"
shutil.copy2(source,out/"executed-finalizer.py")
shutil.copy2(__file__,out/"executed-runner.py")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
argv=[sys.executable,"-B",str(source)]
start=time.monotonic();timed=False
record={"schema":1,"argv":argv,"cwd":str(ROOT),"python":sys.version,
    "finalizer_sha256_before":sha(source),"deadline_seconds":45,
    "started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "dedicated_owned_process_group":True,"scope":"offline custody/hash/arithmetic finalization only"}
with (out/"stdout.bin").open("wb") as stdout,(out/"stderr.bin").open("wb") as stderr:
    child=subprocess.Popen(argv,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
    try:code=child.wait(timeout=45)
    except subprocess.TimeoutExpired:
        timed=True;os.killpg(child.pid,signal.SIGKILL);code=child.wait(timeout=5)
record.update(returncode=code,timed_out=timed,child_reaped=child.poll() is not None,
    elapsed_seconds=round(time.monotonic()-start,6),finalizer_sha256_after=sha(source),
    stdout_sha256=sha(out/"stdout.bin"),stderr_sha256=sha(out/"stderr.bin"))
(out/"receipt.json").write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
print((out/"stdout.bin").read_text(),end="")
print((out/"stderr.bin").read_text(),end="",file=sys.stderr)
assert record["finalizer_sha256_before"]==record["finalizer_sha256_after"]
sys.exit(0 if code==0 and not timed else 1)
