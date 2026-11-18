#!/usr/bin/env python3
"""Run the actual public mixer binary against a new disposable v3 origin."""
import argparse
import base64
import contextlib
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("mixer", type=lambda value: Path(value).resolve())
parser.add_argument("service", type=lambda value: Path(value).resolve())
parser.add_argument("signer", type=lambda value: Path(value).resolve())
parser.add_argument("evidence", type=Path)
args = parser.parse_args()
args.evidence = args.evidence.resolve()
base = "/v3/orgs/org-a/projects/project-a"
steps = {}
tokens = {role: secrets.token_urlsafe(32) for role in ("PUBLISHER", "FOREIGN", "READER")}
environment = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR") if key in os.environ}
local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
reason = "--validation regression"
last_output = {}


def require(check, detail):
    if not check:
        raise RuntimeError(detail)


def request(path, status, role=None):
    headers = {"Authorization": "Bearer " + tokens[role]} if role else {}
    try:
        response = local_http.open(urllib.request.Request(origin + path, headers=headers), timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        require(response.code == status, f"{path}: expected {status}, got {response.code}")
        return json.loads(body) if body else None


def call(label, command, expected=None, *, role="PUBLISHER", point=None, proxy=None):
    env = {**environment, "MIXER_RELEASE_ORIGIN": point or origin, "MIXER_RELEASE_TOKEN": tokens[role]}
    if proxy:
        env.update({key: proxy for key in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY",
                                           "all_proxy", "ALL_PROXY")})
    proc = subprocess.run([args.mixer, *command], cwd=directory, env=env,
                          capture_output=True, timeout=40)
    require(all(token.encode() not in proc.stdout + proc.stderr for token in tokens.values()), "credential escaped")
    require(proc.returncode == (1 if expected else 0), (label, proc.returncode, proc.stdout, proc.stderr))
    last_output[label] = proc.stdout
    value = json.loads(proc.stdout)
    if expected:
        require(value["status"] == "error" and value["code"] == expected, (label, value))
    else:
        require(value["status"] == "ok", (label, value))
    steps[label] = value
    return value


def command(action, target, assignment, *flags, organization="org-a", project="project-a"):
    return ["update", action, target, "--assignment", assignment + ".json",
            "--organization", organization, "--project", project, *flags]


def offer(bucket, sequence=None, digest=None):
    query = urllib.parse.urlencode({**coordinates["scope"], "channel": coordinates["channel"],
                                    "runtime": coordinates["runtime"],
                                    "installation": coordinates["installations"][bucket]})
    data = request("/v3/updates?" + query, 204 if sequence is None else 200)
    if sequence is None:
        return {"http": 204}
    assignment = data["signed_assignment"]["assignment"]
    require((assignment["sequence"], assignment["artifact_sha256"]) == (sequence, digest), assignment)
    return {"http": 200, "sequence": sequence, "artifact_sha256": digest,
            "rollout_basis_points": assignment["rollout_basis_points"], "artifact_url": data["artifact_url"]}


def history():
    return (request(base + "/audit", 200, "READER")["events"],
            request(base + "/outbox", 200, "READER")["work"])


@contextlib.contextmanager
def service():
    with (directory / "service.log").open("ab") as log:
        process = subprocess.Popen([args.service], cwd=directory, stdout=log, stderr=log,
                                   env={**environment, "MIXER_SERVICE_CONFIG": str(directory / "service.json")})
        try:
            deadline = time.monotonic() + 5
            while True:
                require(process.poll() is None and time.monotonic() < deadline, "origin startup failed")
                try:
                    health = request("/healthz", 200)
                    require(health == {"mode": "developer", "production_ready": False}, health)
                    # A fresh scoped token distinguishes this server from any port-race winner.
                    request(base + "/audit", 200, "READER")
                    break
                except (urllib.error.URLError, ConnectionError, TimeoutError):
                    time.sleep(0.05)
            yield
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
                raise RuntimeError("origin required forced shutdown")
            require(process.returncode == 0, ("origin exit", process.returncode))
            with socket.socket() as probe:
                require(probe.connect_ex(("127.0.0.1", port)) != 0, "origin still listening after reap")
            steps.setdefault("origin_cleanup", []).append({"returncode": process.returncode, "listener_closed": True})


def check_receipt(label, action, digest, sequence, rollout):
    require(steps[label] == {"status": "ok", "action": action, "artifact_sha256": digest,
                             "sequence": sequence, "rollout_basis_points": rollout,
                             "delivery": "local_only"}, (label, steps[label]))


@contextlib.contextmanager
def listener(handler):
    with http.server.HTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join(timeout=2)
            require(not thread.is_alive(), "test listener did not stop")


@contextlib.contextmanager
def relay():
    requests = []
    replies = {}

    class Relay(http.server.BaseHTTPRequestHandler):
        timeout = 3

        def do_PUT(self):
            self.do_POST()

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            require(0 < length <= 6 * 1024 * 1024, "unexpected request size")
            body = self.rfile.read(length)
            require(len(body) == length, "incomplete request body")
            reason = self.headers.get("X-Mixer-Reason", "")
            key = self.headers["Idempotency-Key"]
            intent = f"mixer-local-release-v3\0{self.command}\0{self.path}\0{reason}\0".encode()
            require(key == hashlib.sha256(intent + body).hexdigest(), "unexpected idempotency key")
            require(self.headers["Authorization"] == "Bearer " + tokens["PUBLISHER"], "missing scoped bearer")
            requests.append((self.command, self.path, key, hashlib.sha256(body).hexdigest(), reason))
            fault = replies.pop(self.path, None)
            if fault and not fault[2]:
                status, payload, _ = fault
            else:
                upstream = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                try:
                    headers = {name: self.headers[name] for name in
                               ("Content-Type", "Authorization", "Idempotency-Key", "X-Mixer-Reason")
                               if name in self.headers}
                    upstream.request(self.command, self.path, body, headers)
                    response = upstream.getresponse()
                    payload = response.read(4097)
                    require(len(payload) <= 4096, "upstream reply exceeded fixture limit")
                    status = response.status
                finally:
                    upstream.close()
                if fault:
                    require(status == 200, "the origin failed to commit before the interrupted reply")
                    status, payload, _ = fault
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            if status == 307:
                self.send_header("Location", "/credential-sink")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_):
            pass

    with listener(Relay) as endpoint:
        yield endpoint, requests, replies


def check_publish_stages(publish, first):
    upload = base + "/artifacts/" + first
    validate = base + "/releases/validate"
    assign = base + "/channels/production/publish"
    routes = [upload, validate, assign]
    unavailable = (503, b'{"error":{"code":"storage_unavailable"}}', False)

    with relay() as (point, requests, replies):
        for index, (route, stage) in enumerate(zip(routes, ("upload", "validate", "publish"), strict=True)):
            replies[route] = unavailable
            requests.clear()
            failure = call(f"{stage}_unavailable", publish, f"update.{stage}.rejected", point=point)
            require("HTTP 503 (storage_unavailable)" in failure["message"], failure)
            require([row[1] for row in requests] == routes[:index + 1], requests)
            if index == 0:
                request(upload, 404, "READER")
            else:
                request(upload, 200, "READER")
            require(offer("early") == {"http": 204}, "a failed stage advanced the channel")
            audit, work = history()
            require(len(audit) == len(work) == index, "only successful stages write audit and outbox")
            require([event["action"].split(" ", 1)[1] for event in audit] == routes[:index], audit)
            request(f"/v3/artifacts/{first}?organization=org-a&project=project-a", 404)
            steps[f"{stage}_failure_state"] = {
                "committed_stages": [event["action"] for event in audit], "offer_http": 204,
                "publisher_artifact_http": 404 if index == 0 else 200, "public_artifact_http": 404,
            }

        before_retry = requests.copy()
        replies[assign] = (*unavailable[:2], True)
        requests.clear()
        call("publish_interrupted_reply_after_commit", publish, "update.publish.rejected", point=point)
        require(requests == before_retry, "a fresh process changed a publish stage request")
        require(offer("early", 1, first)["http"] == 200, "the origin did not commit")
        committed_history = history()
        requests.clear()
        call("publish", publish, point=point)
        require(requests == before_retry, "same-intent retry changed a publish stage request")
        require(history() == committed_history, "retry duplicated a committed stage")
        steps["publish_stage_keys"] = [row[2] for row in requests]


def check_transport(promote, first):
    path = base + "/channels/production/promote"
    valid = json.dumps({"artifact_sha256": first, "sequence": 2, "rollout_basis_points": 2500,
                        "delivery": "local_only"}).encode()
    sink = []

    class ProxySink(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            sink.append(self.path)
            self.send_error(500)

        def log_message(self, *_):
            pass

    with relay() as (point, requests, replies), listener(ProxySink) as proxy:
        cases = [
            ("redirect_refused", 307, b"{}", "rejected"),
            ("unexpected_success_status", 201, valid, "rejected"),
            ("wrong_response_artifact", 200, valid.replace(first.encode(), b"0" * 64), "response"),
        ]
        for label, status, body, code in cases:
            replies[path] = (status, body, False)
            requests.clear()
            call(label, promote, f"update.promote.{code}", point=point, proxy=proxy)
            require([row[1] for row in requests] == [path], requests)
        require(sink == [], "an ambient proxy received a request")
        steps["direct_loopback_with_proxy_environment"] = True


@contextlib.contextmanager
def disposable_directory():
    directory = Path(tempfile.mkdtemp(prefix="local-origin-", dir=args.evidence.parent))
    try:
        yield directory
    except BaseException:
        print(f"Preserved failed fixture at {directory}")
        raise
    else:
        import shutil
        shutil.rmtree(directory)


with disposable_directory() as directory:
    temporary = str(directory)
    with socket.socket() as free:
        free.bind(("127.0.0.1", 0))
        port = free.getsockname()[1]
    bind = f"127.0.0.1:{port}"
    origin = f"http://{bind}"
    sign_env = {**environment, "FIXTURE_DIRECTORY": temporary, "FIXTURE_ADDRESS": bind,
                **{f"FIXTURE_{role}": token for role, token in tokens.items()}}
    subprocess.run([args.signer, "-test.run", "^TestSignInputs$", "-test.timeout=10s"], env=sign_env,
                   cwd=directory, capture_output=True, check=True, timeout=12)
    coordinates = json.loads((directory / "coordinates.json").read_text())
    first, second = coordinates["first"], coordinates["second"]
    publish = command("publish", "first", "publish-first", "--channel", "production", "--rollout", "5")
    promote = command("promote", first, "promote", "--rollout", "25")
    rollback = command("rollback", first, "rollback", "--reason", reason)
    with service():
        steps["before_publish"] = offer("early")
        require(history() == ([], []), "new origin history is nonempty")
        call("wrong_signed_scope", command("publish", "first", "publish-first", "--channel", "production",
                                           "--rollout", "5", project="foreign-project"), "update.scope")
        denied = call("wrong_token_scope", publish, "update.upload.rejected", role="FOREIGN")
        require("HTTP 403 (scope_denied)" in denied["message"], denied)
        call("wrong_signed_rollout", publish[:-1] + ["6"], "update.intent")
        call("wrong_signed_channel", command("publish", "first", "publish-first", "--channel", "beta",
                                             "--rollout", "5"), "update.intent")
        call("wrong_candidate", command("publish", "second", "publish-first", "--channel", "production",
                                         "--rollout", "5"), "update.intent")
        call("remote_origin_refused", publish, "update.origin", point="http://192.0.2.1:12345")
        tampered = directory / "tampered"
        tampered.mkdir()
        (tampered / "signed-manifest.json").write_bytes((directory / "first/signed-manifest.json").read_bytes())
        (tampered / "payload.wasm").write_bytes(b"tampered payload")
        denied = call("tampered_payload", command("publish", "tampered", "publish-first", "--channel",
                                                  "production", "--rollout", "5"), "update.upload.rejected")
        require("HTTP 422 (artifact_invalid)" in denied["message"], denied)
        require(history() == ([], []), "invalid publication wrote audit or outbox")
        request(base + "/artifacts/" + first, 404, "READER")
        require(offer("early") == {"http": 204}, "invalid publish produced offer")

        check_publish_stages(publish, first)
        check_receipt("publish", "publish", first, 1, 500)
        steps["after_publish"] = {"early": offer("early", 1, first), "expansion": offer("expansion"),
                                  "outside": offer("outside")}
        delivered = request(steps["after_publish"]["early"]["artifact_url"], 200)
        require(delivered["signed_manifest"] == json.loads((directory / "first/signed-manifest.json").read_text()),
                "delivered manifest differs")
        payload = base64.b64decode(delivered["payload"], validate=True)
        require(payload == (directory / "first/payload.wasm").read_bytes(), "delivered bytes differ")
        steps["delivered_payload_sha256"] = hashlib.sha256(payload).hexdigest()
        request("/v3/artifacts/" + first + "?organization=org-a&project=foreign-project", 404)
        before_promotion = history()
        denied = call("reader_token", promote, "update.promote.rejected", role="READER")
        require("HTTP 403 (role_denied)" in denied["message"], denied)
        forged = json.loads((directory / "promote.json").read_text())
        forged["signature"] = base64.b64encode(bytes(64)).decode()
        (directory / "forged.json").write_text(json.dumps(forged))
        denied = call("forged_assignment", command("promote", first, "forged", "--rollout", "25"),
                      "update.promote.rejected")
        require("HTTP 409 (assignment_rejected)" in denied["message"], denied)
        require(history() == before_promotion, "denials wrote audit or outbox")
        check_transport(promote, first)
        require(history() == before_promotion, "refused responses changed history")
        call("wrong_promote_channel", promote + ["--channel", "beta"], "update.intent")
        with relay() as (point, requests, _):
            call("promote", promote + ["--channel", "production"], point=point)
            require(len(requests) == 1, requests)
            steps["promote_stage_key"] = requests[0][2]
        check_receipt("promote", "promote", first, 2, 2500)
        steps["after_promote"] = {"early": offer("early", 2, first), "expansion": offer("expansion", 2, first),
                                  "outside": offer("outside")}
        promoted_history = history()
        denied = call("failed_promotion", command("promote", first, "shrink", "--rollout", "5"),
                      "update.promote.rejected")
        require("HTTP 409 (invalid_promotion)" in denied["message"], denied)
        require(history() == promoted_history, "failed promotion wrote audit or outbox")
        steps["after_failed_promotion"] = offer("expansion", 2, first)

        call("publish_replacement", command("publish", "second", "publish-second", "--channel", "production",
                                             "--rollout", "100"))
        check_receipt("publish_replacement", "publish", second, 3, 10000)
        steps["after_replacement"] = offer("outside", 3, second)
        before_rollback = history()
        call("missing_rollback_reason", rollback[:-2], "update.arguments")
        call("invalid_rollback_reason", rollback[:-1] + ["bad\nreason"], "update.reason")
        call("wrong_rollback_target", command("rollback", second, "rollback", "--reason", reason), "update.intent")
        require(history() == before_rollback, "invalid rollback wrote audit or outbox")
        call("wrong_rollback_channel", rollback + ["--channel", "beta"], "update.intent")
        with relay() as (point, requests, _):
            call("rollback", rollback + ["--channel", "production"], point=point)
            original = requests.copy()
            requests.clear()
            call("rollback_same_reason", rollback, point=point)
            require(requests == original, "rollback retry changed the reason or key")
            steps["rollback_stage_key"] = requests[0][2]
        check_receipt("rollback", "rollback", first, 4, 10000)
        steps["after_rollback"] = offer("outside", 4, first)
        audit, outbox = history()
        require(len(audit) == len(outbox) == 8, (audit, outbox))
        expected_routes = [f"PUT {base}/artifacts/{first}", f"POST {base}/releases/validate",
                           f"POST {base}/channels/production/publish", f"POST {base}/channels/production/promote",
                           f"PUT {base}/artifacts/{second}", f"POST {base}/releases/validate",
                           f"POST {base}/channels/production/publish", f"POST {base}/channels/production/rollback"]
        require([event["action"] for event in audit] == expected_routes, audit)
        require([event["reason"] for event in audit] == ["local development operation"] * 7 + [reason], audit)
        for event, work in zip(audit, outbox, strict=True):
            require(event["actor"] == "local-publisher" and event["organization"] == "org-a" and
                    event["project"] == "project-a" and event["previous"] != event["current"], event)
            require((work["event_id"], work["request_id"], work["kind"], work["status"]) ==
                    (event["id"], event["request_id"], event["action"], "pending_local_only"), work)
        heads = [(1, first, 500), (2, first, 2500), (3, second, 10000), (4, first, 10000)]
        previous = None
        for event, (sequence, artifact, rollout) in zip((audit[i] for i in (2, 3, 6, 7)), heads, strict=True):
            head = {"sequence": sequence, "artifact_sha256": artifact, "rollout_basis_points": rollout}
            expected = {"scope": coordinates["scope"], "runtime": coordinates["runtime"],
                        "channel": coordinates["channel"], "current": head}
            if previous is not None:
                expected["previous"] = previous
            require(event["channel_change"] == expected, event)
            previous = head
        steps["audit_channel_sequences"] = [head[0] for head in heads]
        steps["audit"] = [{key: event[key] for key in ("id", "actor", "action", "reason", "hash")} for event in audit]
        steps["outbox_count"] = len(outbox)
    with service():
        with relay() as (point, requests, _):
            for label, original in (("publish", publish), ("promote", promote), ("rollback", rollback)):
                retry = label + "_retry_after_restart"
                call(retry, original, point=point)
                require(last_output[retry] == last_output[label], f"{label} stdout changed across processes")
            require([row[2] for row in requests[:3]] == steps["publish_stage_keys"], "publish keys changed")
            require(requests[-2][2] == steps["promote_stage_key"], "promote key changed")
            require(requests[-1][2] == steps["rollback_stage_key"], "rollback key changed")
        steps["restart_stdout_byte_identical"] = ["publish", "promote", "rollback"]
        require(history() == (audit, outbox), "restart retries duplicated audit or outbox")
        denied = call("changed_rollback_reason", rollback[:-1] + ["different reason"], "update.rollback.rejected")
        require("HTTP 409 (assignment_rejected)" in denied["message"], denied)
        require(history() == (audit, outbox), "changed reason wrote audit or outbox")
        steps["after_restart_retries"] = offer("outside", 4, first)
    version = subprocess.run([args.mixer, "version"], cwd=directory, env=environment,
                             capture_output=True, check=True, timeout=5)
    require(json.loads(version.stdout)["detail"] == "0.1.0-dev", "existing version changed")
    before = subprocess.run([args.mixer, "update", "prepare"], cwd=directory, env=environment,
                            capture_output=True, timeout=5)
    require(before.returncode == 1 and json.loads(before.stdout)["code"] == "workflow.not-qualified",
            "existing unqualified command changed")
    verify = subprocess.run([args.mixer, "update", "verify"], cwd=directory,
                            env={**environment, "MIXER_UPDATE_TOOL": str(directory / "missing")},
                            capture_output=True, timeout=5)
    require(verify.returncode == 1 and json.loads(verify.stdout)["code"] == "update.tools",
            "existing verify dispatch changed")
    steps["existing_entry_points"] = ["version", "update prepare", "update verify"]
require(not directory.exists(), "disposable store remains")
steps["fixture_removed"] = True
args.evidence.write_text(json.dumps(steps, indent=2, sort_keys=True) + "\n")
print(f"PASS: {len(steps)} recorded observations")
