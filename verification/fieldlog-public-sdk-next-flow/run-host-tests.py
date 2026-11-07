#!/usr/bin/env python3
"""Run the one root-authorized host command with finite owned-child bounds."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
COMMAND = [
    "swift", "test", "--package-path", "/Users/andreyyurlov/Documents/dev/fieldlog",
    "--scratch-path", "/Users/andreyyurlov/Documents/dev/mixer/verification/local/fieldlog-public-sdk-next-flow-host",
    "--jobs", "2",
]
LOG = ROOT / "host-tests.log"
LIMIT = 32 * 1024 * 1024
started = time.monotonic()
wall_started = datetime.datetime.now(datetime.timezone.utc).isoformat()
process = subprocess.Popen(COMMAND, cwd="/Users/andreyyurlov/Documents/dev/fieldlog",
    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    start_new_session=True)
# Only this freshly created session/group is ever signalled. No process inventory,
# held group, unrelated PID, native runtime or previous experiment is inspected.
selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ)
size = 0
reason = None
eof = False
with LOG.open("wb") as output:
    while time.monotonic() - started < 570:
        for key, _ in selector.select(timeout=0.2):
            block = os.read(key.fileobj.fileno(), 65_536)
            if not block:
                selector.unregister(key.fileobj)
                eof = True
                break
            remaining = LIMIT - size
            output.write(block[:remaining])
            size += min(len(block), remaining)
            if len(block) > remaining:
                reason = "output-limit"
                break
        if reason or (eof and process.poll() is not None):
            break
    else:
        reason = "570-second-execution-limit"
    if reason:
        for sig, maximum in [(signal.SIGTERM, 25), (signal.SIGKILL, 5)]:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=min(maximum, max(0.01, 600 - (time.monotonic() - started))))
                break
            except subprocess.TimeoutExpired:
                pass
    else:
        process.wait(timeout=max(0.01, 600 - (time.monotonic() - started)))
selector.close()
process.stdout.close()
result = {
    "command": COMMAND, "cwd": "/Users/andreyyurlov/Documents/dev/fieldlog",
    "startedAt": wall_started,
    "endedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "wallSeconds": round(time.monotonic() - started, 3),
    "exitCode": process.returncode, "stopReason": reason,
    "outputBytes": LOG.stat().st_size, "outputSHA256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
    "executionSecondsBound": 570, "cleanupSecondsBound": 30,
    "outputBytesBound": LIMIT, "pipeEOFObserved": eof,
    "nativeRuntimeOrDeviceCommands": False,
}
(ROOT / "host-command.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
raise SystemExit(process.returncode if process.returncode is not None and not reason else 124)
