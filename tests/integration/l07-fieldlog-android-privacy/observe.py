#!/usr/bin/env python3
"""Observe privacy fields at a private development update origin."""

import argparse
import base64
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import parse_qsl, quote, unquote_plus, urlsplit
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fieldlog-android-signed-resume"))
from origin import admit_packet, digest


def markers(packet):
    workspace = json.loads((packet / "delivery-android/Installed/calculation-seed.json").read_bytes())
    documents = {"workspace.id": workspace["id"]}
    for category, names in (("drafts", ("title", "note", "id")), ("tasks", ("title", "id")),
                            ("projects", ("title", "site", "id"))):
        for i, item in enumerate(workspace[category]):
            for field in names:
                value = item.get(field)
                if isinstance(value, str) and len(value) >= 8:
                    documents[f"{category}[{i}].{field}"] = value
    return {
        label: {item.encode() for item in (value, json.dumps(value)[1:-1], quote(value, safe=""),
                                           base64.b64encode(value.encode()).decode())}
        for label, value in documents.items()
    }


def marker_hits(raw, fixture):
    return sorted(label for label, variants in fixture.items() if any(value in raw for value in variants))


def serve(packet, phase_file, output):
    tenant, target, envelopes = admit_packet(packet)
    private = markers(packet)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            phase = phase_file.read_text().strip()
            if phase not in {"delivery", "failure"}:
                return self.respond(503)
            sequence = 1 if phase == "delivery" else 2
            path, offer, artifact = envelopes[sequence]
            target_url = urlsplit(self.path)
            fields = parse_qsl(target_url.query, keep_blank_values=True)
            query = dict(fields)
            keys = sorted(query)
            raw_request = (
                self.path.encode() + b"\n" + unquote_plus(self.path).encode() + b"\n" + self.headers.as_bytes()
            )
            credential_headers = sorted({name.lower() for name in self.headers} &
                                        {"authorization", "cookie", "proxy-authorization"})
            declared = self.headers.get_all("Content-Length", [])
            bodyless = declared in ([], ["0"]) and "Transfer-Encoding" not in self.headers
            label, installation_sha, status, response = "unexpected", None, 404, b""
            if self.command != "GET":
                status = 405
            elif not bodyless or len(fields) != len(query) or target_url.netloc:
                status = 400
            elif target_url.path == "/v3/updates":
                installation = query.pop("installation", "")
                try:
                    valid_id = str(UUID(installation)) == installation
                except ValueError:
                    valid_id = False
                label, status = "offer", 204
                if valid_id and query == target:
                    status, response = 200, offer
                    installation_sha = digest(installation.encode())
            elif target_url.path == path and query == tenant:
                label = "artifact"
                status, response = (200, artifact) if phase == "delivery" else (503, b"")

            row = {"phase": phase, "requestKind": label, "method": self.command, "queryKeys": keys,
                   "bodyless": bodyless, "credentialHeaders": credential_headers,
                   "markerHits": marker_hits(raw_request, private), "installationSHA256": installation_sha,
                   "status": status, "responseSHA256": digest(response)}
            with output.open("a") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
            self.respond(status, response)

        do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_GET

        def respond(self, status, response=b""):
            self.send_response(status)
            self.send_header("Content-Length", str(len(response)))
            self.send_header("Cache-Control", "no-store")
            if response:
                self.send_header("Content-Type", "application/json")
            self.end_headers()
            if response:
                try:
                    self.wfile.write(response)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        def log_message(self, *_args):
            pass

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        print(server.server_port, flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("phase", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    serve(args.packet, args.phase, args.output)
