#!/usr/bin/env python3
"""Serve the three sealed Android calculation assignments from an owned loopback port."""
import argparse
import base64
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delivery", type=Path)
    parser.add_argument("sequence_file", type=Path)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    delivery = args.delivery.resolve(strict=True)
    materials = delivery.parent / "materials.sha256.json"
    pins = json.loads(materials.read_bytes())
    observed = {}
    for member in delivery.rglob("*"):
        relative = member.relative_to(delivery.parent).as_posix()
        if member.is_symlink():
            raise ValueError(f"Unexpected delivery symlink: {relative}")
        if member.is_file():
            observed[relative] = sha256(member.read_bytes()).hexdigest()
    if observed != pins:
        raise ValueError("Delivery inventory differs from materials.sha256.json")
    host = json.loads((delivery / "host.json").read_bytes())
    scope = host["scope"]
    if scope["platform"] != "android" or scope["environment"] != "development":
        raise ValueError("Android development material required")
    tenant = {key: scope[key] for key in ("organization", "project")}
    match = tenant | {key: scope[key] for key in ("app", "environment", "platform")}
    match |= {"channel": "beta", "runtime": host["runtime"]}
    packages = {}
    assignments = {}
    for seq, variant in enumerate(("baseline", "reviewed", "baseline"), 1):
        assignment = json.loads((delivery / f"sequence-{seq}.assignment.json").read_bytes())
        manifest = json.loads((delivery / f"{variant}.manifest.json").read_bytes())
        wasm = (delivery / f"{variant}.wasm").read_bytes()
        digest = assignment["assignment"]["artifact_sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Invalid artifact digest")
        path = "/v3/artifacts/" + digest
        assignments[seq] = {"signed_assignment": assignment, "artifact_url": path + "?" + urlencode(tenant)}
        packages[path] = {"signed_manifest": manifest, "payload": base64.b64encode(wasm).decode("ascii")}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            target = urlsplit(self.path)
            items = parse_qs(target.query, keep_blank_values=True)
            if any(len(values) != 1 for values in items.values()):
                return self.respond(400)
            query = {key: values[0] for key, values in items.items()}
            if target.path in packages and query == tenant:
                return self.respond(200, packages[target.path])
            if target.path != "/v3/updates":
                return self.respond(404)
            try:
                installation = query.pop("installation", "")
                if str(UUID(installation)) != installation or query != match:
                    return self.respond(204)
                sequence = int(args.sequence_file.read_text().strip())
            except (OSError, ValueError):
                return self.respond(503)
            offer = assignments.get(sequence)
            return self.respond(204) if offer is None else self.respond(200, offer)

        def respond(self, status, value=None):
            body = b"" if value is None else json.dumps(value, separators=(",", ":")).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            if body:
                self.send_header("Content-Type", "application/json")
            self.end_headers()
            if body:
                self.wfile.write(body)

    with HTTPServer(("127.0.0.1", args.port), Handler) as server:
        print(server.server_port, flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
