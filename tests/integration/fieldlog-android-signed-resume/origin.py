#!/usr/bin/env python3
"""Serve exact signed development offers with one controlled transfer boundary."""

import argparse
import base64
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit
from uuid import UUID


TRANSFER_PREFIX = 1024
PHASES = {
    "baseline": (1, "baseline", "complete"),
    "partial": (2, "reviewed", "truncate"),
    "changed-prefix": (2, "reviewed", "alter"),
    "complete": (2, "reviewed", "complete"),
}


def digest(data):
    return sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def admit_packet(directory):
    root = directory.resolve(strict=True)
    delivery = root / "delivery-android"
    observed = {}
    for member in delivery.rglob("*"):
        require(not member.is_symlink(), "Unexpected symlink in delivery inventory")
        if member.is_file():
            observed[member.relative_to(root).as_posix()] = digest(member.read_bytes())
    require(observed == json.loads((root / "materials.sha256.json").read_bytes()),
            "Delivery inventory differs from its seal")
    host = json.loads((delivery / "host.json").read_bytes())
    scope = host["scope"]
    require((scope["platform"], scope["environment"]) == ("android", "development"),
            "An Android development packet is required")
    tenant = {key: scope[key] for key in ("organization", "project")}
    target = scope | {"runtime": host["runtime"], "channel": "beta"}
    replies = {}
    for sequence, variant in ((1, "baseline"), (2, "reviewed")):
        signed = json.loads((delivery / f"sequence-{sequence}.assignment.json").read_bytes())
        binding = signed["assignment"]
        require(all(binding[key] == value for key, value in target.items() if key not in scope)
                and binding["scope"] == scope and binding["sequence"] == sequence,
                "Signed assignment target differs from the packet")
        artifact = binding["artifact_sha256"]
        require(len(artifact) == 64 and all(char in "0123456789abcdef" for char in artifact),
                "Invalid signed artifact digest")
        path = "/v3/artifacts/" + artifact
        offer = encode({"signed_assignment": signed, "artifact_url": path + "?" + urlencode(tenant)})
        manifest = json.loads((delivery / f"{variant}.manifest.json").read_bytes())
        payload = (delivery / f"{variant}.wasm").read_bytes()
        body = encode({"signed_manifest": manifest, "payload": base64.b64encode(payload).decode("ascii")})
        require(TRANSFER_PREFIX < len(body) <= 65_536, "Delivery envelope exceeds the fixture boundary")
        replies[sequence] = (path, offer, body)
    return tenant, target, replies


def serve(packet, phase_file, receipt, port):
    tenant, target, replies = admit_packet(packet)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            items = parse_qsl(url.query, keep_blank_values=True)
            query = dict(items)
            if len(items) != len(query):
                return self.write_reply(400)
            phase = phase_file.read_text().strip()
            if phase not in PHASES:
                return self.write_reply(503)
            sequence, _, transfer = PHASES[phase]
            path, offer, artifact = replies[sequence]
            if url.path == "/v3/updates":
                installation = query.pop("installation", "")
                try:
                    require(str(UUID(installation)) == installation, "Invalid installation ID")
                except ValueError:
                    return self.write_reply(204)
                if query == target:
                    return self.write_reply(200, offer, phase=phase, kind="offer",
                                            installation_sha=digest(installation.encode()))
                return self.write_reply(204)
            if url.path != path or query != tenant:
                return self.write_reply(404)
            wire = artifact
            if transfer == "truncate":
                wire = artifact[:TRANSFER_PREFIX]
            if transfer == "alter":
                replacement = b"r" if artifact[32:33] != b"r" else b"u"
                wire = artifact[:32] + replacement + artifact[33:]
            return self.write_reply(200, wire, declared=len(artifact), phase=phase, kind="artifact")

        def write_reply(self, status, body=b"", *, declared=None, **metadata):
            declared = len(body) if declared is None else declared
            self.send_response(status)
            self.send_header("Content-Length", str(declared))
            self.send_header("Connection", "close")
            if body:
                self.send_header("Content-Type", "application/json")
            self.end_headers()
            write_completed = True
            if body:
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    write_completed = False
            if metadata:
                row = {"status": status, "declaredBytes": declared, "offeredBytes": len(body),
                       "wireSHA256": digest(body), "writeCompleted": write_completed,
                       "rangeHeaderPresent": self.headers.get("Range") is not None}
                with receipt.open("a") as log:
                    log.write(json.dumps(row | metadata, sort_keys=True) + "\n")
            self.close_connection = True

        def log_message(self, _format, *_args):
            pass

    with HTTPServer(("127.0.0.1", port), Handler) as server:
        print(server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("phase", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    serve(args.packet, args.phase, args.receipt, args.port)


if __name__ == "__main__":
    main()
