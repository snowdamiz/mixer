#!/usr/bin/env python3
"""Record the one-shot build driver's complete invocation and terminal streams."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

B = Path(__file__).resolve().parent
R = B.parents[1]
assert not (B / "driver-command.json").exists()
argv = [str(Path(sys.executable).resolve()), "-B", str(B / "build.py")]
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
stamp = time.monotonic()
p = subprocess.Popen(argv, cwd=R, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timedout = False
signals = []
try:
    out, err = p.communicate(timeout=420)
except subprocess.TimeoutExpired:
    timedout = True
    os.killpg(p.pid, signal.SIGTERM)
    signals.append("SIGTERM")
    try:
        out, err = p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        signals.append("SIGKILL")
        out, err = p.communicate(timeout=10)
(B / "driver.stdout").write_bytes(out)
(B / "driver.stderr").write_bytes(err)
ps = subprocess.run(["/bin/ps", "-axo", "pid=,pgid="], capture_output=True, timeout=10, check=True)
members = [int(line.split()[0]) for line in ps.stdout.decode().splitlines() if int(line.split()[1]) == p.pid]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
receipt = dict(schema=1, argv=argv, cwd=str(R), startedUTC=started, elapsedSeconds=time.monotonic()-stamp, exitCode=p.returncode, timeoutSeconds=420, timedOut=timedout, signalsSent=signals, ownedPID=p.pid, ownedPGID=p.pid, processGroupAbsent=not members, survivingPIDs=members, stdoutEOF=True, stderrEOF=True, stdoutSHA256=sha(out), stderrSHA256=sha(err), pythonSHA256=sha(Path(argv[0]).read_bytes()), pythonVersion=sys.version)
(B / "driver-command.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
print(json.dumps(receipt, sort_keys=True))
sys.exit(p.returncode if not timedout and not members else 1)
