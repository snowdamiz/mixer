#!/usr/bin/env python3
"""Bounded HTTPS acquisition only. Never imports a subject analyzer or executes tools."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OWN = Path(__file__).resolve().parent
LIMIT = 256 * 1024 * 1024
SECONDS = 60


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname not in {
            "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"
        }:
            raise RuntimeError("redirect outside official GitHub asset transport")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def main():
    local = OWN / "local"
    local.mkdir(exist_ok=True)
    metadata = json.loads((OWN / "release-metadata.json").read_text())
    receipt = {
        "schema": 1, "scope": "HTTPS data acquisition only; no subject import, install, extraction or execution",
        "python": sys.version, "download_byte_ceiling": LIMIT,
        "consumer_wall_seconds": SECONDS, "blind_retries": 0,
        "connector_metadata": "mcp__codex_apps__github_fetch release endpoint; parsed selected official assets only",
        "retained_setup_failures": [{"operation": "connector fetch published checksum browser URL", "result": "GitHub API 404; connector did not return asset bytes"}],
        "downloads": [],
    }
    previous_receipt = OWN / "acquisition-receipt.json"
    if previous_receipt.exists():
        receipt["prior_attempt"] = json.loads(previous_receipt.read_text())
    opener = urllib.request.build_opener(OfficialRedirects())
    for asset in metadata["assets"]:
        if asset["size"] > LIMIT:
            raise RuntimeError("official metadata exceeds acquisition ceiling")
        start = time.monotonic()
        item = {"name": asset["name"], "canonical_url": asset["browser_download_url"], "expected_bytes": asset["size"], "expected_sha256": asset["digest"].removeprefix("sha256:")}
        receipt["downloads"].append(item)
        destination = local / asset["name"]
        try:
            if destination.exists():
                # Retain and validate a completed file after a downloader bookkeeping
                # failure. Never retry or overwrite incomplete/unknown data.
                existing = hashlib.sha256()
                existing_size = 0
                with destination.open("rb") as stream:
                    for part in iter(lambda: stream.read(1024 * 1024), b""):
                        existing_size += len(part)
                        if existing_size > LIMIT:
                            raise RuntimeError("retained data exceeds acquisition ceiling")
                        existing.update(part)
                if existing_size != asset["size"] or existing.hexdigest() != item["expected_sha256"]:
                    raise RuntimeError("retained data identity missing; no retry")
                item.update(bytes=existing_size, sha256=existing.hexdigest(), status="verified-retained-data", elapsed_seconds=round(time.monotonic() - start, 6))
                continue
            request = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "Mixer-official-archive-data-profile/1", "Accept": "application/octet-stream"})
            with opener.open(request, timeout=SECONDS) as response, destination.open("xb") as target:
                length = response.headers.get("Content-Length")
                if length is not None and (int(length) > LIMIT or int(length) != asset["size"]):
                    raise RuntimeError("content length differs from selected official asset")
                digest = hashlib.sha256()
                total = 0
                while True:
                    remaining = SECONDS - (time.monotonic() - start)
                    if remaining <= 0:
                        raise RuntimeError("consumer deadline exceeded")
                    # urllib exposes the connected transport here. No signed URL is logged or stored.
                    response.fp.raw._sock.settimeout(remaining)
                    chunk = response.read(min(1024 * 1024, LIMIT - total + 1))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > LIMIT or total > asset["size"]:
                        raise RuntimeError("stream exceeds selected asset or acquisition ceiling")
                    target.write(chunk)
                    digest.update(chunk)
                    if total == asset["size"]:
                        break
                if time.monotonic() - start > SECONDS:
                    raise RuntimeError("consumer deadline exceeded")
            item.update(bytes=total, sha256=digest.hexdigest())
            if total != asset["size"] or digest.hexdigest() != item["expected_sha256"]:
                raise RuntimeError("download identity differs from official release metadata")
            item["status"] = "verified-data"
        except Exception as exc:
            # Exceptions from HTTP may contain temporary transport URLs. Retain only type/code.
            item.update(status="failed-retained", error_type=type(exc).__name__)
            if isinstance(exc, urllib.error.HTTPError):
                item["http_status"] = exc.code
            item["elapsed_seconds"] = round(time.monotonic() - start, 6)
            (OWN / "acquisition-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            print(json.dumps({"status": item["status"], "name": item["name"], "error_type": item["error_type"], "http_status": item.get("http_status")}))
            return 1
        item["elapsed_seconds"] = round(time.monotonic() - start, 6)
    receipt["status"] = "verified-data-only"
    (OWN / "acquisition-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "downloads": [{k: v for k, v in row.items() if k in {"name", "bytes", "sha256", "elapsed_seconds", "status"}} for row in receipt["downloads"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
