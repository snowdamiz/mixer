"""Exercise the pinned stock release wire, or advance it on request from XCTest."""
import argparse
from base64 import b64decode, b64encode
from hashlib import sha256
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
from hmac import compare_digest
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlencode

from issue import PHASES

PROJECT = "/v3/orgs/mixer-local/projects/fieldlog"
INSTALLATION = "fieldlog-f11-ios-private"
TOOL_HASHES = {
    "stock-mixer-service": "f759e2f60670bd39d8aa52cfa54b58b9c3011ebf4740dabbc272df07cf082dcb",
    "mixer": "337d054c7f16dd38f3c9b4befeeba6e821d3f6697045d602cfd6af7ddf2c0a08",
}


def digest(value):
    return sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def encode(value):
    return json.dumps(value, separators=(",", ":")).encode()


def read(path):
    return json.loads(path.read_bytes())


def http(port, path, *, method="GET", data=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        headers.update({"Content-Type": "application/json", "Idempotency-Key": secrets.token_hex(16)})
    client = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        client.request(method, path, body=data, headers=headers)
        with client.getresponse() as response:
            return response.status, response.read(65_537)
    finally:
        client.close()


class Origin:
    def __init__(self, tools, releases, work):
        self.tools, self.releases, self.work = tools, releases, work
        self.host = read(releases / "host.json")
        self.token = secrets.token_urlsafe(32)
        self.audit = []
        self.report = {"tools": TOOL_HASHES, "host": self.host, "phases": {}, "negative": {}}
        self.process = None
        self.port = None
        self.hold = False
        self.env = dict(PATH="/usr/bin:/bin:/usr/sbin:/sbin", HOME=str(work), TMPDIR=str(work),
                        NO_PROXY="127.0.0.1")
        for name, value in TOOL_HASHES.items():
            require(digest((tools / name).read_bytes()) == value, f"Unexpected stock tool {name}")

    def spawn(self, name, argv, env):
        with (self.work / (name + ".log")).open("xb") as log:
            try:
                return subprocess.Popen(argv, cwd=self.work, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, start_new_session=True)
            except OSError:
                self.hold = True
                raise

    def stop(self, process):
        try:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                return
            raise RuntimeError(f"Unresolved process group {process.pid}")
        except BaseException:
            self.hold = True
            raise

    def start(self):
        with socket.socket() as lease:
            lease.bind(("127.0.0.1", 0))
            self.port = lease.getsockname()[1]
        config = self.work / "origin.json"
        config.write_bytes(encode(dict(developer_mode=True, listen=f"127.0.0.1:{self.port}",
            data_directory=str(self.work / "store"), hosts=[self.host], roots=read(self.releases / "roots.json"),
            tokens=[dict(organization="mixer-local", project="fieldlog", actor="f11-ios-witness",
                         role="publisher", sha256=digest(self.token.encode()))])))
        self.process = self.spawn("origin", [self.tools / "stock-mixer-service"],
                                  dict(self.env, MIXER_SERVICE_CONFIG=str(config)))
        deadline = time.monotonic() + 4
        while self.process.poll() is None and time.monotonic() < deadline:
            try:
                status, raw = http(self.port, "/healthz")
                require(status == 200 and json.loads(raw)["mode"] == "developer", "Wrong origin mode")
                require(http(self.port, self.query()) == (204, b""), "Origin must start without an offer")
                return
            except ConnectionRefusedError:
                time.sleep(0.04)
        raise RuntimeError("Stock origin failed readiness")

    def query(self, **changes):
        fields = dict(self.host["scope"], runtime=self.host["runtime"], channel="beta", installation=INSTALLATION)
        return "/v3/updates?" + urlencode(fields | changes)

    def negative_uploads(self):
        cases = {
            "wrong-runtime": (422, "unknown_runtime", "no registered host contract"),
            "wrong-app": (422, "unknown_runtime", "no registered host contract"),
            "wrong-ui-schema": (422, "artifact_invalid", "unsupported v3 schema, protocol, guest ABI or UI schema"),
            "excess-memory": (422, "artifact_invalid", "v3 resource limit outside installed execution profile"),
            "tampered-payload": (422, "artifact_invalid", "payload size or hash mismatch"),
        }
        for phase, expected in cases.items():
            folder = self.releases / ("successor" if phase == "tampered-payload" else phase)
            artifact = read(folder / "assignment.json")["assignment"]["artifact_sha256"]
            payload = (folder / "payload.wasm").read_bytes()
            if phase == "tampered-payload":
                payload = bytes([payload[0] ^ 1]) + payload[1:]
            data = encode(dict(signed_manifest=read(folder / "signed-manifest.json"),
                               payload=b64encode(payload).decode()))
            status, raw = http(self.port, f"{PROJECT}/artifacts/{artifact}", method="PUT", data=data, token=self.token)
            error = json.loads(raw)
            self.report["negative"][phase] = dict(status=status, response=error)
            serialized = raw.decode()
            require(status == expected[0] and all(part in serialized for part in expected[1:]),
                    f"Unexpected {phase} rejection: {status} {serialized}")
            require(http(self.port, self.query()) == (204, b""), f"{phase} changed public offer")

    def publish(self, phase):
        folder = self.releases / phase
        signed = read(folder / "assignment.json")
        assignment = signed["assignment"]
        artifact = assignment["artifact_sha256"]
        rollback = phase == "rollback"
        verb = "rollback" if rollback else "publish"
        target = artifact if rollback else folder
        options = ["--reason", "F11 local fixture restores read-only release"] if rollback else ["--rollout", "100"]
        argv = [self.tools / "mixer", "update", verb, target, "--channel", "beta", *options,
                "--assignment", folder / "assignment.json", "--organization", "mixer-local", "--project", "fieldlog"]
        process = self.spawn(phase, argv, dict(self.env, MIXER_RELEASE_ORIGIN=f"http://127.0.0.1:{self.port}",
                                               MIXER_RELEASE_TOKEN=self.token))
        try:
            code = process.wait(timeout=12)
        finally:
            self.stop(process)
        log = (self.work / (phase + ".log")).read_bytes()
        require(code == 0, f"First stock CLI rejection at {phase} (exit {code}): {log.decode(errors='replace')}")
        result = json.loads(log)
        require(result == dict(status="ok", action=verb, artifact_sha256=artifact, sequence=assignment["sequence"],
                               rollout_basis_points=10_000, delivery="local_only"), f"Unexpected {phase} CLI receipt")
        path = f"/v3/artifacts/{artifact}?organization=mixer-local&project=fieldlog"
        status, offer = http(self.port, self.query())
        require(status == 200 and json.loads(offer) == dict(signed_assignment=signed, artifact_url=path),
                "Stock offer differs from the intended signed assignment")
        status, envelope = http(self.port, path)
        body = json.loads(envelope)
        payload = b64decode(body["payload"], validate=True)
        require(status == 200 and set(body) == {"signed_manifest", "payload"}
                and body["signed_manifest"] == read(folder / "signed-manifest.json")
                and payload == (folder / "payload.wasm").read_bytes(), "Stock envelope differs from signed input bytes")
        for changes in (dict(runtime="0" * 64), dict(app="fieldlog-f11-unregistered"), dict(platform="android")):
            require(http(self.port, self.query(**changes)) == (204, b""), "Unregistered scope got an offer")
        require(http(self.port, path.replace("organization=mixer-local", "organization=unregistered"))[0] == 404,
                "Artifact escaped its tenant")
        if not rollback:
            self.audit += [f"PUT {PROJECT}/artifacts/{artifact}", f"POST {PROJECT}/releases/validate"]
        self.audit.append(f"POST {PROJECT}/channels/beta/{verb}")
        evidence = dict(offerSHA256=digest(offer), envelopeSHA256=digest(envelope), payloadSHA256=digest(payload),
                        payloadBytes=len(payload), artifact=artifact, sequence=assignment["sequence"])
        self.report["phases"][phase] = evidence
        return evidence

    def finish(self):
        status, raw = http(self.port, f"{PROJECT}/audit", token=self.token)
        actual = [item["action"] for item in json.loads(raw)["events"]]
        require(status == 200 and actual == self.audit, f"Unexpected publication audit: {actual}")
        self.report["audit"] = actual
        self.close()

    def close(self):
        if self.process is None:
            return
        process = self.process
        self.process = None
        self.stop(process)
        with socket.socket() as lease:
            lease.settimeout(1)
            try:
                lease.connect(("127.0.0.1", self.port))
            except ConnectionRefusedError:
                self.report["originCleanup"] = dict(exit=process.returncode, groupAbsent=True, portRefused=True)
                return
        self.hold = True
        raise RuntimeError("Stock origin listener remained reachable")


def serve(origin, expected):
    """Accept only one ordered, explicit journey from the local XCTest runner."""
    steps = iter((*PHASES, "offline"))
    next_phase = next(steps)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            nonlocal next_phase
            if not compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
                self.send_error(403)
                return
            if self.path != "/" + next_phase:
                self.send_error(409)
                return
            if next_phase == "offline":
                origin.finish()
                value = b"{}"
            else:
                actual = origin.publish(next_phase)
                require(actual == expected[next_phase], f"Served {next_phase} changed from the probe")
                value = encode(dict(port=origin.port))
            self.send_response(200)
            self.send_header("Content-Length", str(len(value)))
            self.end_headers()
            self.wfile.write(value)
            next_phase = next(steps, None)

        def handle(self):
            self.request.settimeout(15)
            super().handle()

    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        server.timeout = 1
        def failed_request(*_):
            raise RuntimeError("F11 control request failed") from sys.exc_info()[1]

        server.handle_error = failed_request
        lease = origin.work / "control.json"
        pending = lease.with_suffix(".pending")
        pending.write_bytes(encode(dict(port=server.server_port, token=token)))
        pending.rename(lease)
        deadline = time.monotonic() + 360
        while next_phase is not None:
            require(time.monotonic() < deadline, f"XCTest did not request {next_phase}")
            server.handle_request()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("probe", "serve"))
    for name in ("tools", "releases", "work", "delivery"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    args = parser.parse_args()
    os.umask(0o077)
    args.work.mkdir()
    origin = Origin(args.tools, args.releases, args.work)
    try:
        origin.start()
        if args.mode == "probe":
            origin.negative_uploads()
            phases = {phase: origin.publish(phase) for phase in PHASES}
            require(phases["prior"]["artifact"] == phases["rollback"]["artifact"] != phases["successor"]["artifact"]
                    and phases["prior"]["envelopeSHA256"] == phases["rollback"]["envelopeSHA256"]
                    and phases["prior"]["offerSHA256"] != phases["rollback"]["offerSHA256"], "Rollback lineage")
            origin.finish()
            args.delivery.write_bytes(encode(phases))
        else:
            serve(origin, read(args.delivery))
        origin.report["status"] = "passed"
    except BaseException as error:
        origin.report.update(status="failed", failure=str(error))
        raise
    finally:
        try:
            origin.close()
        finally:
            origin.report["hold"] = origin.hold
            (args.work / "receipt.json").write_bytes(encode(origin.report))


if __name__ == "__main__":
    main()
