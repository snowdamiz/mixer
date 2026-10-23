#!/usr/bin/env python3
"""Bounded isolated CLI file-kind race reproduction; never changes trust/source."""
import argparse
import datetime
import errno
import hashlib
import json
from pathlib import Path
import os
import subprocess
import tempfile
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument("--tool", required=True)
parser.add_argument("--vectors", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--revision", required=True)
args = parser.parse_args()
vector = json.loads(Path(args.vectors).read_text())[0]
data = json.dumps(vector["descriptor"], sort_keys=True, separators=(",", ":")).encode()
record = dict(scope="isolated regular-file/FIFO path replacement; stream read is byte bounded but must not admit a special file",
              revision=args.revision, createdAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              command=[args.tool, "inspect", "<private temporary raced path>"], descriptorSHA256=hashlib.sha256(data).hexdigest(),
              sourceToolSHA256=hashlib.sha256(Path(args.tool).read_bytes()).hexdigest(), attempts=0,
              confirmedFIFOAccepted=False, unconfirmedTimeout=False, threadError=None, executedCommands=[])
with tempfile.TemporaryDirectory(prefix="mixer-identity-fifo-review-") as temporary:
    directory = Path(temporary)
    path = directory / "descriptor.json"
    path.write_bytes(data)
    stop = threading.Event()

    def flip():
        try:
            for index in range(2000):
                if stop.is_set(): return
                regular = directory / "regular-staging"
                regular.write_bytes(data)
                os.replace(regular, path)
                time.sleep(0.0001)
                fifo = directory / ("fifo-" + str(index))
                os.mkfifo(fifo, 0o600)
                link = directory / "fifo-staging"
                os.link(fifo, link)
                os.replace(link, path)
                time.sleep(0.0001)
        except Exception as error:
            record["threadError"] = repr(error)

    thread = threading.Thread(target=flip, daemon=True)
    thread.start()
    try:
        for attempt in range(80):
            record["attempts"] = attempt + 1
            process = subprocess.Popen([args.tool, "inspect", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            executed = dict(command=process.args)
            record["executedCommands"].append(executed)
            try:
                stdout, stderr = process.communicate(timeout=0.25)
                executed.update(exitCode=process.returncode, stdoutSHA256=hashlib.sha256(stdout).hexdigest(), stderrSHA256=hashlib.sha256(stderr).hexdigest())
            except subprocess.TimeoutExpired:
                executed["blockedBeforeRescue"] = True
                stop.set(); thread.join(timeout=2)
                # Preserve FIFO master links. Opening its writer nonblocking is
                # possible only if this private CLI has a waiting/active reader.
                rescued = False
                for fifo in sorted(directory.glob("fifo-*")):
                    try: descriptor = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
                    except OSError as error:
                        if error.errno in [errno.ENXIO, errno.ENOENT]: continue
                        raise
                    try: os.write(descriptor, data)
                    finally: os.close(descriptor)
                    rescued = True
                    record["rescueFIFO"] = fifo.name
                    break
                try:
                    stdout, stderr = process.communicate(timeout=2)
                    record.update(rescuedReader=rescued, rescuedExitCode=process.returncode,
                                  rescuedOutput=stdout.decode(errors="replace"), rescuedError=stderr.decode(errors="replace"))
                    if rescued and process.returncode == 0:
                        record["confirmedFIFOAccepted"] = json.loads(stdout)["fingerprint"] == vector["fingerprint"]
                except subprocess.TimeoutExpired:
                    process.kill(); process.communicate()
                    record["unconfirmedTimeout"] = True
                break
    finally:
        stop.set(); thread.join(timeout=2)
    record["threadStopped"] = not thread.is_alive()
Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
