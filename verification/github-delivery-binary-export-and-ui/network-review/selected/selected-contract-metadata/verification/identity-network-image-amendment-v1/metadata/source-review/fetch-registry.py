#!/usr/bin/env python3
"""Anonymous official registry index, manifest and config metadata only."""
import datetime
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
import urllib.parse
import urllib.request

BASE = Path(__file__).resolve().parent
CAP = 8 * 1024 * 1024
TOKEN = None

def fetch(path, retained, token=None):
    url = "https://registry-1.docker.io/v2/hexpm/elixir/" + path
    headers = {"Accept": "application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.docker.distribution.manifest.v2+json", "User-Agent": "mixer-image-prerequisite-source-review/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    row = {"url": url, "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "per_request_timeout_seconds": 50, "absolute_request_deadline_seconds": 55, "per_response_cap_bytes": CAP, "purpose": "public registry JSON metadata only; no layers", "python": sys.version}
    started = time.monotonic()
    def expired(_number, _frame):
        raise TimeoutError("absolute request deadline exceeded")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(55)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=50) as response:
            data = response.read(CAP + 1)
            if len(data) > CAP:
                raise ValueError("metadata response cap exceeded")
            digest = hashlib.sha256(data).hexdigest()
            if path.startswith("blobs/sha256:") or path.startswith("manifests/sha256:"):
                if digest != path.rsplit(":", 1)[1]:
                    raise ValueError("registry content digest mismatch")
            parsed = json.loads(data)
            destination = BASE / "inputs" / "official" / retained
            if destination.exists():
                raise ValueError("retained destination already exists")
            destination.write_bytes(data)
            row.update(status=response.status, bytes=len(data), sha256=digest, docker_content_digest=response.headers.get("Docker-Content-Digest"), content_type=response.headers.get("Content-Type"), retained=str(destination.relative_to(BASE)))
    except Exception as error:
        row["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        signal.alarm(0)
        row["elapsed_seconds"] = round(time.monotonic() - started, 6)
        with (BASE / "requests.jsonl").open("a") as output:
            output.write(json.dumps(row, sort_keys=True) + "\n")
        print(json.dumps(row, sort_keys=True))
    return parsed

def main():
    tag = sys.argv[1]
    prefix = sys.argv[2]
    # Public anonymous bearer capability stays only in memory; never retained.
    auth_url = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:hexpm/elixir:pull"
    def expired(_number, _frame):
        raise TimeoutError("absolute public bearer deadline exceeded")
    signal.signal(signal.SIGALRM, expired)
    signal.alarm(55)
    try:
        with urllib.request.urlopen(auth_url, timeout=50) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError("bearer response cap exceeded")
            token = json.loads(raw)["token"]
    finally:
        signal.alarm(0)
    index = fetch("manifests/" + tag, prefix + "-index.json", token)
    children = [m for m in index["manifests"] if m["platform"].get("os") == "linux" and m["platform"].get("architecture") == "amd64"]
    if len(children) != 1:
        raise ValueError("exact one Linux AMD64 child required")
    child = fetch("manifests/" + children[0]["digest"], prefix + "-amd64-manifest.json", token)
    config = fetch("blobs/" + child["config"]["digest"], prefix + "-amd64-config.json", token)
    if config["architecture"] != "amd64" or config["os"] != "linux":
        raise ValueError("config platform mismatch")
    print(json.dumps({"tag": tag, "child": children[0]["digest"], "config": child["config"]["digest"], "layers_count": len(child["layers"]), "compressed_layer_bytes": sum(r["size"] for r in child["layers"]), "layers_downloaded": 0, "anonymous_bearer_persisted": False}, sort_keys=True))

if __name__ == "__main__":
    main()
