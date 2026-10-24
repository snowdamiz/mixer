"""Observe only this packet's fixed host controls or selected C4 acquisition."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("controls", "acquire"))
    args = parser.parse_args()
    argv = ([sys.executable, "-B", "-m", "unittest", "-v", "test_acquire.py"] if args.phase == "controls"
            else [sys.executable, "-B", "acquire.py", "--execute"])
    maximum = 524288
    paths = {stream: HERE/(args.phase+"."+stream) for stream in ("stdout", "stderr")}
    files = {stream: path.open("xb") for stream, path in paths.items()}
    start = time.monotonic()
    until = start+(10 if args.phase == "controls" else 185)
    counts = {stream: 0 for stream in paths}
    refusal = None
    proc = subprocess.Popen(argv, cwd=HERE, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    monitor = selectors.DefaultSelector()
    monitor.register(proc.stdout, selectors.EVENT_READ, "stdout")
    monitor.register(proc.stderr, selectors.EVENT_READ, "stderr")
    try:
        while monitor.get_map():
            if time.monotonic() >= until:
                refusal = "observer-wall-limit"
                break
            for key, _ in monitor.select(.1):
                data = os.read(key.fd, 65536)
                if not data:
                    monitor.unregister(key.fileobj)
                    continue
                stream = key.data
                kept = data[:max(0, maximum-counts[stream])]
                files[stream].write(kept)
                counts[stream] += len(kept)
                if len(kept) != len(data):
                    refusal = "observer-stream-limit"
                    break
            if refusal:
                break
        if refusal:
            proc.terminate()  # C4's own SIGTERM handler removes its partial.
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)
        monitor.close()
        for pipe in (proc.stdout, proc.stderr):
            pipe.close()
        for stream in files.values():
            stream.close()
        receipt = {"schema": 1, "argv": argv, "cwd": str(HERE), "phase": args.phase,
            "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "elapsedSeconds": time.monotonic()-start, "exitCode": proc.returncode, "refusal": refusal,
            "observerSourceSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "outputs": {stream: {"path": str(path.relative_to(HERE.parents[1])), "bytes": path.stat().st_size,
                                   "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for stream, path in paths.items()}}
        (HERE/(args.phase+"-command.json")).write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"phase": args.phase, "exitCode": proc.returncode, "refusal": refusal,
                      "observedStreamBytes": counts, "elapsedSeconds": time.monotonic()-start}))


if __name__ == "__main__":
    main()
