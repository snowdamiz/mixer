#!/usr/bin/env python3
"""Serve the sealed development offers on a loopback-only Android relay."""

import argparse
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID


def read(path):
    return json.loads(path.read_bytes())


def server(packet, phase_file):
    hosts = {label: read(packet / label / "host.json") for label in ("old", "successor")}
    scope = hosts["old"]["scope"]
    runtimes = {label: host["runtime"] for label, host in hosts.items()}
    if (scope != hosts["successor"]["scope"] or scope["platform"] != "android"
            or scope["environment"] != "development" or len(set(runtimes.values())) != 2):
        raise ValueError("Expected distinct Android development runtimes in one scope")
    port = int((packet / "old/Installed/port.txt").read_text())
    if port != int((packet / "successor/Installed/port.txt").read_text()):
        raise ValueError("APK relay ports differ")
    tenant = {key: scope[key] for key in ("organization", "project")}
    common = scope | {"channel": "beta"}
    payload = base64.b64encode((packet / "reviewed.wasm").read_bytes()).decode()
    offers = {}
    artifacts = {}
    for label, runtime, sequence in [
            ("old", runtimes["old"], 2), ("successor", runtimes["successor"], 3), ("refused", runtimes["old"], 3)]:
        assignment = read(packet / label / "assignment.json")
        manifest = read(packet / label / "manifest.json")
        body = assignment["assignment"]
        digest = body["artifact_sha256"]
        if (not re.fullmatch("[0-9a-f]{64}", digest) or body["runtime"] != runtime or body["sequence"] != sequence
                or manifest["manifest"]["runtime"] != runtime or body["scope"] != scope):
            raise ValueError(f"Offer scope differs for {label}")
        path = "/v3/artifacts/" + digest
        offers[label] = {"signed_assignment": assignment, "artifact_url": path + "?" + urlencode(tenant)}
        artifacts[path] = {"signed_manifest": manifest, "payload": payload}
    if len(artifacts) != len(offers):
        raise ValueError("Expected three distinct signed artifact digests")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            target = urlsplit(self.path)
            items = parse_qs(target.query, keep_blank_values=True)
            if any(len(value) != 1 for value in items.values()):
                return self.respond(400)
            query = {key: value[0] for key, value in items.items()}
            if target.path in artifacts and query == tenant:
                return self.respond(200, artifacts[target.path])
            if target.path != "/v3/updates":
                return self.respond(404)
            installation = query.pop("installation", "")
            runtime = query.pop("runtime", "")
            try:
                installation_valid = str(UUID(installation)) == installation
            except ValueError:
                installation_valid = False
            if not installation_valid or query != common or runtime not in runtimes.values():
                return self.respond(204)
            try:
                phase = phase_file.read_text().strip()
            except OSError:
                return self.respond(503)
            if phase not in {"old", "both", "refuse"}:
                return self.respond(503)
            if runtime == runtimes["old"]:
                return self.respond(200, offers["refused" if phase == "refuse" else "old"])
            if phase == "both":
                return self.respond(200, offers["successor"])
            return self.respond(204)

        def respond(self, status, value=None):
            body = b"" if value is None else json.dumps(value, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            if body:
                self.send_header("Content-Type", "application/json")
            self.end_headers()
            if body:
                self.wfile.write(body)

    return HTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("phase_file", type=Path)
    args = parser.parse_args()
    with server(args.packet, args.phase_file) as origin:
        print(origin.server_port, flush=True)
        origin.serve_forever()
