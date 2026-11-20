#!/usr/bin/env python3
"""Serve the byte-verified iOS rotation cases over a private loopback origin."""
import argparse
import base64
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import secrets
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Lock, Thread
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID, uuid4

from importlib.util import module_from_spec, spec_from_file_location

HERE = Path(__file__).resolve().parent
spec = spec_from_file_location("host_validation", HERE / "validate-host.py")
validation = module_from_spec(spec)
spec.loader.exec_module(validation)
check, digest, read, request, write = (validation.check, validation.digest, validation.read, validation.request, validation.write)
PHASES = ("baseline", "revoked-artifact", "revoked-assignment", "offline", "replacement", "complete")

def response_body(value):
    return json.dumps(value, separators=(",", ":")).encode() if value is not None else b""

class Server(HTTPServer):
    allow_reuse_address = True

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(3)
        super().setup()

    def log_message(self, *_):
        pass

    def reply(self, status, value=None):
        data = response_body(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.wfile.write(data) != len(data):
            raise OSError("Incomplete HTTP response body write")
        return data

class DataHandler(Handler):
    def do_GET(self):
        origin = self.server.origin
        url = urlsplit(self.path)
        if self.path == "/healthz":
            return self.reply(200, {"mode": "development-rotation-fixture"})
        query = parse_qs(url.query, keep_blank_values=True)
        with origin.lock:
            phase = origin.phase
            offer = origin.offers.get(phase)
            if offer is None:
                return self.reply(409)
            if url.path == "/v3/updates":
                actual = query.pop("installation", [""])
                if query != {k: [v] for k, v in origin.query.items()} or len(actual) != 1:
                    return self.reply(422)
                installation = actual[0]
                try:
                    if str(UUID(installation)) != installation:
                        return self.reply(422)
                except ValueError:
                    return self.reply(422)
                if origin.installation is None and phase == "baseline":
                    origin.installation = installation
                if installation != origin.installation:
                    return self.reply(403)
                body = self.reply(200, offer["wireOffer"])
                return origin.observe("updates", offer, body)
            if self.path == offer["wireOffer"]["artifact_url"]:
                if not origin.saw("updates"):
                    return self.reply(409)
                body = self.reply(200, offer["wireArtifact"])
                return origin.observe("artifact", offer, body)
            return self.reply(404)

class ControlHandler(Handler):
    def do_POST(self):
        origin = self.server.origin
        if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + origin.token):
            return self.reply(403)
        try:
            phase = self.path.removeprefix("/phase/")
            check(self.path == "/phase/" + phase, "Invalid control route")
            reply = origin.advance(phase)
        except (ValueError, RuntimeError, OSError) as error:
            return self.reply(409, {"error": str(error)})
        try:
            self.reply(200, reply)
        finally:
            if phase == "complete":
                origin.done.set()

def listener(handler, port, origin):
    server = Server(("127.0.0.1", port), handler)
    server.origin = origin
    worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    worker.start()
    return server, worker

def refused(port):
    try:
        request(port, "/healthz", 200)
    except ConnectionRefusedError:
        return True
    return False

def close_listener(owned):
    server, worker = owned
    port = server.server_port
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)
    proof = {"socketClosed": server.socket.fileno() == -1, "threadJoined": not worker.is_alive(),
             "connectionRefused": refused(port)}
    check(all(proof.values()), f"Listener closure incomplete on {port}: {proof}")
    return proof

class Origin:
    def __init__(self, work):
        self.work = work
        fixture = HERE / "fixture"
        evidence = read(HERE / "host-validation.json")
        check(evidence["status"] == "passed", "Host validation is missing")
        check(evidence["files"] == {str(p.relative_to(fixture)): digest(p)
                  for p in sorted(fixture.rglob("*")) if p.is_file()}, "Changed fixture files")
        signing = read(fixture / "signing.json")
        check(int(time.time()) + 600 < signing["cutoff"], "Initial root is too near expiry. Regenerate the packet.")
        host = read(fixture / "host.json")
        check(host["runtime"] == evidence["runtime"] == signing["runtime"], "Runtime binding mismatch")
        self.query = {**host["scope"], "runtime": host["runtime"], "channel": "beta"}
        self.offers = {}
        for phase in validation.PHASES:
            folder = fixture / phase
            artifact = signing["artifactDigests"][phase]
            assignment = read(folder / "assignment.json")
            manifest = read(folder / "signed-manifest.json")
            check(assignment["assignment"]["artifact_sha256"] == artifact, "Assignment artifact changed")
            self.offers[phase] = {
                "artifact": artifact,
                "payloadSHA256": manifest["manifest"]["payload_sha256"],
                "sequence": assignment["assignment"]["sequence"],
                "wireOffer": {"signed_assignment": assignment,
                              "artifact_url": f"/v3/artifacts/{artifact}?organization=mixer-local&project=fieldlog"},
                "wireArtifact": {"signed_manifest": manifest,
                                 "payload": base64.b64encode((folder / "payload.wasm").read_bytes()).decode()},
            }
        self.token = secrets.token_urlsafe(32)
        self.phase = None
        self.position = 0
        self.installation = None
        self.lock = Lock()
        self.done = Event()
        self.control = self.data = None
        self.traffic = []
        self.transitions = []

    def start(self):
        self.data = listener(DataHandler, 0, self)
        self.data_port = self.data[0].server_port
        self.control = listener(ControlHandler, 0, self)
        self.control_port = self.control[0].server_port
        (self.work / "control-token").write_text(self.token + "\n")
        ready = {"dataURL": f"http://127.0.0.1:{self.data_port}",
                 "controlURL": f"http://127.0.0.1:{self.control_port}",
                 "fingerprints": {"ios": self.query["runtime"]}}
        write(self.work / "ready.json", ready)

    def saw(self, route):
        return any(row["phase"] == self.phase and row["route"] == route for row in self.traffic)

    def observe(self, route, offer, body):
        row = {"phase": self.phase, "route": route, "installation": self.installation,
               "responseSHA256": sha256(body).hexdigest(),
               **{field: offer[field] for field in ("artifact", "payloadSHA256", "sequence")}}
        with (self.work / "traffic.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        self.traffic.append(row)

    def advance(self, phase):
        response = {"phase": phase, "verified": True}
        with self.lock:
            check(self.position < len(PHASES) and PHASES[self.position] == phase, "Out-of-order phase")
            if self.phase in self.offers:
                check(self.saw("updates") and self.saw("artifact"), "Previous phase was not fully served")
            self.phase = phase
            self.position += 1
        if phase == "offline":
            response["closure"] = close_listener(self.data)
            self.data = None
        elif phase == "replacement":
            self.data = listener(DataHandler, self.data_port, self)
        if phase in self.offers:
            offer = self.offers[phase]
            response["offers"] = [{"platform": "ios",
                                   **{k: offer[k] for k in ("artifact", "payloadSHA256", "sequence")},
                                   "responseDigests": {
                                       route: sha256(response_body(offer[key])).hexdigest()
                                       for route, key in (("updates", "wireOffer"), ("artifact", "wireArtifact"))
                                   }}]
        self.transitions.append(response)
        return response

    def close(self):
        closure = {}
        if self.control is not None:
            closure["control"] = close_listener(self.control)
        if self.data is not None:
            closure["data"] = close_listener(self.data)
        (self.work / "control-token").unlink(missing_ok=True)
        write(self.work / "origin-receipt.json", {"phases": self.transitions, "traffic": self.traffic,
              "installation": self.installation, "completed": self.phase == "complete", "closure": closure})

def smoke(origin):
    from http.client import HTTPConnection
    installation = validation.HOST_INSTALLATION
    def control(phase, status=200, token=origin.token):
        conn = HTTPConnection("127.0.0.1", origin.control_port, timeout=5)
        try:
            conn.request("POST", "/phase/" + phase, headers={"Authorization": "Bearer " + token})
            response = conn.getresponse()
            check(response.status == status, f"{phase}: unexpected control status")
            body = response.read()
            return json.loads(body) if body else None
        finally:
            conn.close()
    control("baseline", 403, token="wrong")
    control("replacement", 409)
    for phase in PHASES:
        response = control(phase)
        check(response["phase"] == phase and response["verified"], "Unexpected control response")
        if phase == "offline":
            check(refused(origin.data_port) and all(response["closure"].values()), "Offline listener still available")
        if phase not in origin.offers:
            continue
        query = origin.query | {"installation": installation}
        url = "/v3/updates?" + urlencode(query)
        port = origin.data_port
        offer = request(port, url, 200)
        artifact = request(port, json.loads(offer)["artifact_url"], 200)
        digests = {route: sha256(body).hexdigest() for route, body in (("updates", offer), ("artifact", artifact))}
        check(response["offers"][0]["responseDigests"] == digests, "Wrong signed response bytes")
        with origin.lock:
            check({row["route"]: row["responseSHA256"] for row in origin.traffic if row["phase"] == phase}
                  == digests, "Origin trace differs from the received bytes")
        request(port, "/v3/updates?" + urlencode(query | {"installation": str(uuid4())}), 403)
        request(port, "/v3/updates?" + urlencode(query | {"platform": "android"}), 422)

def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--seconds", type=int, default=480, choices=range(1, 601), metavar="1-600")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(mode=0o700)
    origin = Origin(work)
    signal.signal(signal.SIGTERM, lambda *_: origin.done.set())
    signal.signal(signal.SIGINT, lambda *_: origin.done.set())
    try:
        origin.start()
        if args.smoke:
            smoke(origin)
        else:
            origin.done.wait(args.seconds)
        check(origin.phase == "complete", "Replay ended before native completion")
    finally:
        origin.close()

if __name__ == "__main__":
    main()
