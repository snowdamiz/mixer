"""Serve the pinned, compiled console against the ordinary Pair25 HTTP fixture."""
import base64
from contextlib import closing, contextmanager
import hashlib
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
import re
import secrets
import shutil
from threading import Event, Thread
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4

HOST = "127.0.0.1"
STARTERS = "/console-api/v1/source-starters"
INPUTS = "/console-api/v1/build-inputs"
BUILDS = "/console-api/v1/builds"
LOGS = "/console-api/v1/build-logs"
ARTIFACTS = "/console-api/v1/build-artifacts"
GENERAL_LIMIT = 300_000
CHUNK_SIZE = 64 * 1024
DOWNLOAD_TIMEOUT = 8
RESPONSE_HEADERS = {"content-type", "cache-control", "set-cookie", "vary"}
ATTACHMENT_HEADERS = {
    "content-length", "content-disposition", "x-content-type-options", "x-request-id",
    "digest", "content-digest", "etag",
}
SESSION = "/auth/session"
DIRECTORY = ("/console-api/v1/orgs", "/console-api/v1/projects", "/console-api/v1/applications")
SCOPE = ("organization_id", "project_id", "application_id")
PUBLIC = {
    "organization_id": "organizationId", "project_id": "projectId", "application_id": "applicationId",
    "build_id": "buildId", "platform": "platform", "source_input_id": "sourceInputId",
    "source_sha256": "sourceSha256", "toolchain_lock_sha256": "toolchainLockSha256",
    "build_definition_sha256": "buildDefinitionSha256",
}
UUID4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def expect(condition, message):
    if not condition:
        raise RuntimeError(message)


def seed_npm_cache(lock, source, target):
    """Copy only locked tarballs into the run's writable npm cache."""
    prefix = Path("_cacache/content-v2")
    blobs = set()
    for package in json.loads(lock.read_bytes())["packages"].values():
        if "integrity" in package:
            algorithm, encoded = package["integrity"].split("-", 1)
            digest = base64.b64decode(encoded, validate=True).hex()
            relative = prefix / algorithm / digest[:2] / digest[2:4] / digest[4:]
            if (source / relative).is_file():
                blobs.add(relative)
    size = sum((source / name).stat().st_size for name in blobs)
    expect(0 < size <= 64 * 1024 * 1024, "locked npm cache is missing or exceeds 64 MiB")
    for name in blobs:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, destination)
    return size


class BrowserEvidence:
    def __init__(self, build, receipt):
        self.build = build
        self.scope = {key: build[key] for key in SCOPE}
        self.selection = self.scope | {"starter_id": build["source_input_id"]}
        self.public_scope = {PUBLIC[key]: value for key, value in self.scope.items()}
        self.public_input = {PUBLIC[key]: value for key, value in build.items() if key not in SCOPE}
        self.receipt = receipt
        self.key = None
        self.queued = None
        self.terminal = None

    def exact_selection(self, query):
        if self.queued is None:
            return False
        try:
            values = parse_qs(query, keep_blank_values=True, strict_parsing=True, max_num_fields=len(self.queued))
        except ValueError:
            return False
        return values == {key: [value] for key, value in self.queued.items()}

    def begin_terminal(self, cookie, detail, logs, downloads):
        self.receipt["terminal"] = {"buildId": detail["buildId"], "downloads": {}}
        fields = {"ownerHTTP", "outsiderHTTP", "anonymousHTTP"}
        self.terminal = {
            "cookie": cookie,
            "detail": {key: value for key, value in detail.items() if key not in fields},
            "logs": {
                "buildId": detail["buildId"], "revision": detail["revision"], "state": detail["state"],
                "platform": detail["platform"], "attempt": detail["attempt"], "events": logs["events"],
            },
            "downloads": {f"{ARTIFACTS}/{item['kind']}": item for item in downloads},
        }

    def terminal_complete(self):
        observed = self.receipt["terminal"]
        return (observed.get("detailHTTP") == 200 and observed.get("logsHTTP") == 200
                and len(observed["downloads"]) == len(self.terminal["downloads"]))

    def observe(self, method, path, query, status, payload):
        if (method, path) == ("GET", "/workspace"):
            self.receipt["consoleHTTP"] = status
        if method == "GET" and path.startswith("/assets/") and path.endswith(".js"):
            self.receipt["consoleScriptHTTP"] = status
        if path == SESSION:
            self.receipt["sessionHTTP"] = status
            return
        if path not in (*DIRECTORY, STARTERS, INPUTS, BUILDS, LOGS):
            return
        event = {"method": method, "route": path, "status": status}
        if len(self.receipt["http"]) < 80:
            self.receipt["http"].append(event)
        try:
            data = json.loads(payload)
        except ValueError:
            return
        if status == 200 and method == "GET" and path == STARTERS:
            if data == self.public_scope | {"starter": {"id": self.selection["starter_id"]}}:
                self.receipt["catalogHTTP"] = status
        elif status == 200 and method == "GET" and path == INPUTS:
            page = self.public_scope | {"nextCursor": None}
            if data == page | {"inputs": []} and "selectionHTTP" not in self.receipt:
                self.receipt["emptyInputsHTTP"] = status
            if data == page | {"inputs": [self.public_input]} and "selectionHTTP" in self.receipt:
                self.receipt["admittedInputsHTTP"] = status
        elif status == 200 and method == "POST" and path == STARTERS:
            if data == self.public_scope | self.public_input:
                self.receipt["selectionHTTP"] = status
        elif status == 201 and method == "POST" and path == BUILDS and isinstance(data, dict):
            selection = data.get("selection", {})
            build_id = selection.get("build_id", "")
            expected = {k: v for k, v in self.build.items() if k != "source_input_id"}
            if (re.fullmatch(r"build-[0-9a-f]{64}", build_id)
                    and selection == expected | {"build_id": build_id}
                    and data == {"selection": selection, "outcome": "applied", "state": "queued", "revision": 0}):
                self.queued = selection
                self.receipt["createHTTP"] = status
        elif status == 200 and method == "GET" and path == BUILDS and self.exact_selection(query) and isinstance(data, dict):
            build = data.get("build", {})
            if (build.get("state") == "queued" and build.get("revision") == 0
                    and all(build.get(PUBLIC[key]) == value for key, value in self.queued.items())):
                self.receipt["detailHTTP"] = status
            elif self.terminal and all(build.get(key) == value for key, value in self.terminal["detail"].items()):
                artifacts = build.get("artifacts", [])
                expected = self.terminal["downloads"]
                if (len(artifacts) == len(expected)
                        and all(item["kind"] == artifact["kind"] and item["sha256"] == artifact["sha256"]
                                and item["sizeBytes"] == artifact["sizeBytes"]
                                and artifact["downloadPath"].partition("?")[0] == path
                                and self.exact_selection(artifact["downloadPath"].partition("?")[2])
                                for (path, item), artifact in zip(expected.items(), artifacts, strict=True))):
                    self.receipt["terminal"]["detailHTTP"] = status
        elif status == 200 and path == LOGS and self.terminal and self.exact_selection(query):
            logs = data.get("buildLogs", {})
            if all(logs.get(key) == value for key, value in self.terminal["logs"].items()):
                self.receipt["terminal"]["logsHTTP"] = status

    def verify(self, queue):
        expected = {"consoleHTTP": 200, "consoleScriptHTTP": 200, "sessionHTTP": 200, "catalogHTTP": 200,
                    "emptyInputsHTTP": 200, "selectionHTTP": 200, "admittedInputsHTTP": 200}
        if queue:
            expected.update(createHTTP=201, detailHTTP=200)
        expect(all(self.receipt.get(key) == code for key, code in expected.items()),
               "loopback session, exact selection or queued readback was incomplete")


@contextmanager
def bridge(dist, auth, evidence, queue):
    nonce = secrets.token_urlsafe(32)
    terminal_nonce = secrets.token_urlsafe(32)
    used = set()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            self.request.settimeout(2)
            super().setup()

        def log_message(self, *_args):
            # Request targets can contain the one-use handoff.
            pass

        def do_GET(self):
            if self.headers.get("Host") != f"localhost:{self.server.server_port}":
                return self.reply(403)
            path = urlsplit(self.path)
            if path.scheme or path.netloc or path.fragment:
                return self.reply(404)
            if path.path == "/__fixture_session":
                if not path.query.isascii():
                    return self.reply(404)
                if secrets.compare_digest(path.query, nonce):
                    cookie, handoff = auth["cookie"], "session"
                elif evidence.terminal and secrets.compare_digest(path.query, terminal_nonce):
                    cookie, handoff = evidence.terminal["cookie"], "terminal-session"
                else:
                    return self.reply(404)
                if handoff in used:
                    return self.reply(410)
                used.add(handoff)
                return self.reply(303, [
                    ("Set-Cookie", "__Host-mixer-session=" + cookie + "; Path=/; Secure; HttpOnly; SameSite=Lax"),
                    ("Location", "/workspace"), ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                ])
            if path.path == ARTIFACTS or path.path.startswith(ARTIFACTS + "/"):
                terminal = evidence.terminal
                attachment = terminal and terminal["downloads"].get(path.path)
                if not attachment or not evidence.exact_selection(path.query):
                    return self.reply(404)
                return self.forward(path, None, attachment)
            if path.path == LOGS and not evidence.exact_selection(path.query):
                return self.reply(404)
            if path.path == SESSION or path.path.startswith("/console-api/v1/"):
                if "%" in path.path or any(part in ("", ".", "..") for part in path.path[1:].split("/")):
                    return self.reply(404)
                return self.forward(path, None)
            asset = dist / "index.html" if path.path in ("/", "/workspace", "/builds", "/releases") else (
                dist / path.path.lstrip("/")).resolve()
            if not asset.is_relative_to(dist) or not asset.is_file():
                return self.reply(404)
            content_type = mimetypes.guess_type(asset)[0] or "application/octet-stream"
            body = asset.read_bytes()
            evidence.observe("GET", path.path, path.query, 200, body)
            self.reply(200, [("Content-Type", content_type)], body)

        def do_POST(self):
            host = f"localhost:{self.server.server_port}"
            if self.headers.get("Host") != host or self.headers.get("Origin") != f"http://{host}":
                return self.reply(403)
            if self.path != STARTERS and (self.path != BUILDS or not queue):
                return self.reply(404)
            if self.path in used:
                return self.reply(409)
            length = self.headers.get("Content-Length", "")
            if not re.fullmatch(r"[1-9][0-9]{0,3}", length) or int(length) > 4096:
                return self.reply(400)
            body = self.rfile.read(int(length))
            try:
                data = json.loads(body)
            except ValueError:
                return self.reply(400)
            if self.path == STARTERS:
                if (data != evidence.selection or evidence.receipt.get("emptyInputsHTTP") != 200
                        or evidence.receipt.get("catalogHTTP") != 200):
                    return self.reply(409)
            else:
                key = self.headers.get("Idempotency-Key", "")
                if (data != evidence.build or evidence.receipt.get("admittedInputsHTTP") != 200
                        or not UUID4.fullmatch(key)):
                    return self.reply(409)
                evidence.key = key
                evidence.receipt["createAttempts"] += 1
            used.add(self.path)
            self.forward(urlsplit(self.path), body)

        def forward(self, path, body, attachment=None):
            allowed = {"accept", "cookie", "content-type", "idempotency-key", "x-mixer-csrf"}
            headers = {name: value for name, value in self.headers.items() if name.lower() in allowed}
            if body is not None:
                headers["Origin"] = auth["origin"]
            try:
                with closing(HTTPConnection(HOST, auth["port"], timeout=5)) as backend:
                    backend.request(self.command, self.path, body, headers)
                    with backend.getresponse() as response:
                        status = response.status
                        if status == 200 and attachment is not None:
                            return self.stream_attachment(response, attachment)
                        headers = [(name, value) for name, value in response.getheaders()
                                   if name.lower() in RESPONSE_HEADERS]
                        payload = response.read(GENERAL_LIMIT + 1)
                if len(payload) > GENERAL_LIMIT:
                    return self.reply(502)
                evidence.observe(self.command, path.path, path.query, status, payload)
                self.reply(status, headers, payload)
            except (OSError, HTTPException):
                self.reply(502)

        def stream_attachment(self, response, expected):
            headers = [(name, value) for name, value in response.getheaders()
                       if name.lower() in RESPONSE_HEADERS | ATTACHMENT_HEADERS]
            size = expected["sizeBytes"]
            if (response.chunked or response.getheader("Content-Encoding") is not None
                    or response.headers.get_all("Content-Length") != [str(size)]
                    or response.getheader("Content-Type") != expected["contentType"]
                    or response.getheader("Content-Disposition") != expected["contentDisposition"]
                    or response.getheader("Cache-Control") != "no-store"
                    or response.getheader("X-Content-Type-Options") != "nosniff"):
                return self.reply(502)

            digest = hashlib.sha256()
            remaining = size
            deadline = time.monotonic() + DOWNLOAD_TIMEOUT
            try:
                self.reply_headers(200, headers, size=None)
                while remaining and time.monotonic() < deadline:
                    chunk = response.read1(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        return
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
                    digest.update(chunk)
            except (OSError, HTTPException):
                return
            if remaining == 0 and digest.hexdigest() == expected["sha256"]:
                evidence.receipt["terminal"]["downloads"][expected["kind"]] = {
                    "http": 200, "sizeBytes": size, "sha256": digest.hexdigest(),
                }

        def reply_headers(self, status, headers, size):
            self.send_response(status)
            for name, value in headers:
                self.send_header(name, value)
            if size is not None:
                self.send_header("Content-Length", str(size))
            self.end_headers()

        def reply(self, status, headers=(), body=b""):
            try:
                self.reply_headers(status, headers, len(body))
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass

    class Loopback(HTTPServer):
        def handle_error(self, *_args):
            evidence.receipt["bridgeHandlerFailed"] = True

    with Loopback((HOST, 0), Handler) as server:
        server.timeout = 0.2
        stop = Event()

        def serve():
            while not stop.is_set():
                server.handle_request()

        thread = Thread(target=serve, daemon=True)
        thread.start()
        try:
            url = f"http://localhost:{server.server_port}/__fixture_session?"
            yield server.server_port, url + nonce, url + terminal_nonce
        finally:
            stop.set()
            thread.join(timeout=DOWNLOAD_TIMEOUT + 9)
            expect(not thread.is_alive(), "loopback bridge did not stop within its teardown budget")
            expect(not evidence.receipt.get("bridgeHandlerFailed"), "loopback bridge handler failed")


def smoke_client(port):
    def request(path, status, *, headers=None, body=None):
        headers = {"Host": f"localhost:{port}", **(headers or {})}
        with closing(HTTPConnection(HOST, port, timeout=8)) as client:
            client.request("POST" if body is not None else "GET", path, body, headers)
            with client.getresponse() as response:
                expect(response.status == status, f"loopback HTTP smoke expected {status}, got {response.status}")
                return dict(response.getheaders()), response.read(GENERAL_LIMIT + 1)
    return request


def smoke_session(request, handoff_url):
    url = urlsplit(handoff_url)
    path = f"{url.path}?{url.query}"
    headers, _ = request(path, 303)
    expect(headers["Location"] == "/workspace", "loopback HTTP handoff redirected to the wrong route")
    cookie = headers["Set-Cookie"].split(";", 1)[0]
    request(path, 410)
    return {"Cookie": cookie}


def smoke(port, handoff_url, scope):
    """Drive the loopback wire contract only. This does not execute the console JavaScript."""
    request = smoke_client(port)
    auth = smoke_session(request, handoff_url)
    _, page = request("/workspace", 200)
    bundle = re.search(rb'<script[^>]+src="(/assets/[^"]+\.js)"', page)
    expect(bundle is not None, "compiled console module was missing")
    request(bundle[1].decode(), 200)
    _, session = request(SESSION, 200, headers=auth)
    post = auth | {"Origin": f"http://localhost:{port}", "Content-Type": "application/json",
                   "X-Mixer-CSRF": json.loads(session)["csrf_token"]}
    query = "?" + urlencode(scope)
    request(INPUTS + query, 200, headers=auth)
    _, catalog = request(STARTERS + query, 200, headers=auth)
    starter_id = json.loads(catalog)["starter"]["id"]
    request(STARTERS, 200, headers=post, body=json.dumps(scope | {"starter_id": starter_id}))
    _, admitted = request(INPUTS + query, 200, headers=auth)
    [row] = json.loads(admitted)["inputs"]
    build = scope | {key: row[value] for key, value in PUBLIC.items() if value in row}
    _, created = request(BUILDS, 201, headers=post | {"Idempotency-Key": str(uuid4())}, body=json.dumps(build))
    request(BUILDS + "?" + urlencode(json.loads(created)["selection"]), 200, headers=auth)


def terminal_smoke(port, handoff_url, evidence):
    request = smoke_client(port)
    auth = smoke_session(request, handoff_url)
    request(SESSION, 200, headers=auth)
    query = "?" + urlencode(evidence.queued)
    for path in (BUILDS, LOGS, *evidence.terminal["downloads"]):
        request(path + query, 200, headers=auth)
