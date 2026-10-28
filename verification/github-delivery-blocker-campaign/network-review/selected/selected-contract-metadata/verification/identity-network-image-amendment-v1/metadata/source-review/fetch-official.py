#!/usr/bin/env python3
"""Bounded public-source/JSON-metadata HTTP only; no layers or executable payloads."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent
CAP = 8 * 1024 * 1024
TIMEOUT = 50

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("url")
    args = parser.parse_args()
    target = BASE / "inputs" / "official" / args.name
    if target.exists() or not args.name or Path(args.name).name != args.name:
        raise SystemExit("new basename required")
    request = urllib.request.Request(args.url, headers={"Accept": "application/vnd.github+json", "User-Agent": "mixer-image-prerequisite-source-review/1"})
    started = time.monotonic()
    row = {"url": args.url, "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "per_request_timeout_seconds": TIMEOUT, "per_response_cap_bytes": CAP, "python": sys.version, "purpose": "official public source or metadata inspection only; no layers or binary execution"}
    try:
        def expired(_number, _frame):
            raise TimeoutError("absolute 55 second request deadline exceeded")
        signal.signal(signal.SIGALRM, expired)
        signal.alarm(55)
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            data = response.read(CAP + 1)
            if len(data) > CAP:
                raise ValueError("response cap exceeded")
            row.update(status=response.status, final_url=response.url, content_type=response.headers.get("Content-Type"), bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), retained=str(target.relative_to(BASE)))
            target.write_bytes(data)
    except Exception as error:
        row.update(error=type(error).__name__ + ": " + str(error))
    finally:
        signal.alarm(0)
    row["elapsed_seconds"] = round(time.monotonic() - started, 6)
    with (BASE / "requests.jsonl").open("a") as output:
        output.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(row, sort_keys=True))
    if "error" in row:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
