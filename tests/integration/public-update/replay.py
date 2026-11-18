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
import shutil
import signal
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
parser.add_argument("--postgres", action="store_true", help="use a fresh private PostgreSQL cluster")
parser.add_argument("--restore-after-halt", action="store_true",
                    help="restore the halted PostgreSQL backup into a second disposable database")
args = parser.parse_args()
if args.restore_after_halt and not args.postgres:
    parser.error("--restore-after-halt requires --postgres")
args.evidence = args.evidence.absolute()
base = "/v3/orgs/org-a/projects/project-a"
steps = {"storage_backend": "postgres" if args.postgres else "local"}
tokens = {role: secrets.token_urlsafe(32) for role in ("PUBLISHER", "FOREIGN", "READER")}
environment = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR") if key in os.environ}
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
reason = "--validation regression"
last_output = {}
database_environment = {}
unproven_groups = set()


def require(check, detail):
    if not check:
        raise RuntimeError(detail)


def request(path, status, role=None, *, raw=False):
    headers = {"Authorization": "Bearer " + tokens[role]} if role else {}
    try:
        response = local_http.open(urllib.request.Request(origin + path, headers=headers), timeout=2)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read(1024 * 1024 + 1)
        require(len(body) <= 1024 * 1024, f"{path}: response exceeded fixture bound")
        require(response.code == status, f"{path}: expected {status}, got {response.code}")
        if raw:
            return body
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
    raw = request("/v3/updates?" + query, 204 if sequence is None else 200, raw=True)
    if sequence is None:
        require(raw == b"", "an ineligible offer contained a response body")
        return {"http": 204}
    data = json.loads(raw)
    assignment = data["signed_assignment"]["assignment"]
    require((assignment["sequence"], assignment["artifact_sha256"]) == (sequence, digest), assignment)
    name = assignment_inputs[sequence]
    artifact_url = f"/v3/artifacts/{digest}?organization=org-a&project=project-a"
    signed = (directory / f"{name}.json").read_bytes().removesuffix(b"\n")
    require(data == {"artifact_url": artifact_url, "signed_assignment": json.loads(signed)} and raw.count(signed) == 1,
            f"{bucket}: signed offer bytes differ for sequence {sequence}")

    candidate = directory / ("first" if digest == first else "second")
    manifest = (candidate / "signed-manifest.json").read_bytes().removesuffix(b"\n")
    payload = (candidate / "payload.wasm").read_bytes()
    delivered = request(artifact_url, 200, raw=True)
    expected_artifact = {"signed_manifest": json.loads(manifest), "payload": base64.b64encode(payload).decode()}
    require(json.loads(delivered) == expected_artifact and delivered.count(manifest) == 1,
            f"{bucket}: signed artifact bytes differ for sequence {sequence}")
    return {"http": 200, "sequence": sequence, "artifact_sha256": digest,
            "rollout_basis_points": assignment["rollout_basis_points"], "artifact_url": artifact_url,
            "offer_sha256": hashlib.sha256(raw).hexdigest(),
            "signed_assignment_sha256": hashlib.sha256(signed).hexdigest(),
            "signed_manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "payload_sha256": hashlib.sha256(payload).hexdigest()}


def history():
    return (request(base + "/audit", 200, "READER")["events"],
            request(base + "/outbox", 200, "READER")["work"])


def establish_group_exit(label, pid):
    deadline = time.monotonic() + 2
    while True:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            unproven_groups.remove(pid)
            return
        require(time.monotonic() < deadline, f"{label} group {pid} is still present")
        time.sleep(0.05)


def wait_for_owned_exit(label, process, timeout):
    forced = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        forced = True
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=3)
    establish_group_exit(label, process.pid)
    steps.setdefault(f"{label}_cleanup", []).append({
        "pid": process.pid, "returncode": process.returncode, "direct_child_reaped": True,
        "group_gone": True, "forced_shutdown": forced,
    })
    require(not forced and process.returncode == 0, (label, process.returncode, forced))


@contextlib.contextmanager
def owned_server(label, command, env, stop_signal):
    with (directory / f"{label}.log").open("ab") as log:
        process = subprocess.Popen(command, cwd=directory, stdout=log, stderr=log,
                                   env=env, start_new_session=True)
    unproven_groups.add(process.pid)
    try:
        yield process
    finally:
        try:
            if process.poll() is None:
                process.send_signal(stop_signal)
        finally:
            wait_for_owned_exit(label, process, 15)


def service_environment():
    return {**environment, "MIXER_SERVICE_CONFIG": str(directory / "service.json")}


@contextlib.contextmanager
def service():
    prior_exits = len(steps.get("origin_cleanup", []))
    try:
        with owned_server("origin", [args.service], {**service_environment(), **database_environment},
                          signal.SIGTERM) as process:
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
        if len(steps.get("origin_cleanup", [])) > prior_exits:
            with socket.socket() as probe:
                require(probe.connect_ex(("127.0.0.1", port)) != 0, "origin still listening after reap")
            steps["origin_cleanup"][-1].update(listener_closed=True, listener_port=port)


class Postgres:
    owner = "mixer_migration_owner"
    runtime = "mixer_test_runtime"

    def __init__(self, sockets):
        self.sockets = sockets
        self.data = directory / "postgres-data"
        self.database = "postgres"
        self.tools = {name: shutil.which(name) for name in ("initdb", "postgres", "psql")}
        require(all(self.tools.values()), "--postgres requires initdb, postgres and psql in PATH")
        if args.restore_after_halt:
            for name in ("pg_dump", "pg_restore"):
                self.tools[name] = shutil.which(name)
                require(self.tools[name], f"--restore-after-halt requires {name} in PATH")
        self.env = {**environment, "LC_ALL": "C", "PGCONNECT_TIMEOUT": "2",
                    "PGOPTIONS": "-c statement_timeout=5000 -c lock_timeout=5000"}

    def sql(self, query):
        return subprocess.run([self.tools["psql"], "-XAtq", "-w", "-v", "ON_ERROR_STOP=1",
                               "-h", self.sockets, "-p", "5432", "-U", self.owner, "-d", self.database,
                               "-c", query], env=self.env, capture_output=True, timeout=7)

    def query(self, query):
        result = self.sql(query)
        require(result.returncode == 0, result.stderr.decode(errors="replace"))
        return result.stdout

    def dsn(self, role):
        return f"host={self.sockets} port=5432 dbname={self.database} user={role} sslmode=disable"

    def configure(self, process):
        deadline = time.monotonic() + 8
        while True:
            require(process.poll() is None and time.monotonic() < deadline, "PostgreSQL startup failed")
            result = self.sql("""
                SELECT json_build_object('version', version(), 'data', current_setting('data_directory'),
                    'listen', current_setting('listen_addresses'), 'fsync', current_setting('fsync'),
                    'full_page_writes', current_setting('full_page_writes'),
                    'synchronous_commit', current_setting('synchronous_commit'))
            """)
            if result.returncode == 0:
                break
            time.sleep(0.05)
        settings = json.loads(result.stdout)
        require(Path(settings.pop("data")).resolve() == self.data.resolve(), "unexpected database directory")
        require(settings["listen"] == "" and all(settings[key] == "on" for key in
                ("fsync", "full_page_writes", "synchronous_commit")), settings)
        steps["postgres"] = settings

        path = directory / "service.json"
        config = json.loads(path.read_bytes())
        del config["data_directory"]
        config.update(storage_backend="postgres", postgres={"connection_string_env": "MIXER_FIXTURE_RUNTIME"})
        path.write_text(json.dumps(config))
        migration = subprocess.run([args.service, "migrate-postgres", "--connection-env", "MIXER_FIXTURE_OWNER"],
                                   env={**service_environment(), "MIXER_FIXTURE_OWNER": self.dsn(self.owner)},
                                   capture_output=True, timeout=12)
        require(migration.returncode == 0, migration.stderr.decode(errors="replace"))
        self.query("""
            CREATE ROLE mixer_test_runtime LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS;
            GRANT mixer_release_runtime TO mixer_test_runtime;
        """)
        database_environment["MIXER_FIXTURE_RUNTIME"] = self.dsn(self.runtime)

    def backup_halt(self):
        archive = directory / "halted.dump"
        subprocess.run([self.tools["pg_dump"], "-w", "--format=custom", "--file", archive,
                        "--dbname", self.dsn(self.owner)], env=self.env, check=True, timeout=15)
        return archive

    def restore_halt(self, archive):
        self.query("CREATE DATABASE mixer_halt_restore TEMPLATE template0")
        self.database = "mixer_halt_restore"
        subprocess.run([self.tools["pg_restore"], "-w", "--single-transaction", "--exit-on-error",
                        "--dbname", self.dsn(self.owner), archive], env=self.env, check=True, timeout=15)
        database_environment["MIXER_FIXTURE_RUNTIME"] = self.dsn(self.runtime)

    def snapshot(self):
        # One independent, read-only SQL snapshot after the HTTP commit.
        return json.loads(self.query("""
            BEGIN READ ONLY;
            SELECT json_build_object(
              'heads', ARRAY(SELECT sequence FROM mixer_release.channel_heads ORDER BY channel_key),
              'assignments', ARRAY(SELECT encode(signed_assignment, 'hex') FROM mixer_release.assignments
                                   ORDER BY sequence),
              'audit', ARRAY(SELECT convert_from(event_body, 'UTF8') FROM mixer_release.audit_events ORDER BY id),
              'outbox', ARRAY(SELECT convert_from(work_body, 'UTF8') FROM mixer_release.outbox ORDER BY id),
              'idempotency', ARRAY(SELECT json_build_array(key, request_hash, status, encode(response_body, 'hex'))
                                     FROM mixer_release.idempotency ORDER BY key),
              'tenant', ARRAY(SELECT json_build_array(organization, project, last_event, audit_hash, state_hash)
                               FROM mixer_release.tenant_heads ORDER BY organization, project));
            COMMIT;
        """))


@contextlib.contextmanager
def postgres():
    # The Unix socket path must fit sockaddr_un even with a long checkout path.
    sockets = Path(tempfile.mkdtemp(prefix="mixer-l05-", dir="/tmp"))
    db = None
    try:
        db = Postgres(sockets)
        with (directory / "initdb.log").open("wb") as log:
            initialize = subprocess.Popen(
                [db.tools["initdb"], "-D", db.data, "-U", db.owner, "--auth-local=trust",
                 "--auth-host=reject", "--no-locale", "--encoding=UTF8"],
                env=db.env, stdout=log, stderr=log, start_new_session=True,
            )
            unproven_groups.add(initialize.pid)
        wait_for_owned_exit("initdb", initialize, 30)
        settings = ["-c", "listen_addresses=", "-c", f"unix_socket_directories={sockets}",
                    "-c", "unix_socket_permissions=0700", "-c", "fsync=on", "-c", "full_page_writes=on",
                    "-c", "synchronous_commit=on"]
        with owned_server("postgres", [db.tools["postgres"], "-D", db.data, "-p", "5432", *settings],
                          db.env, signal.SIGINT) as process:
            db.configure(process)
            yield db
    finally:
        if unproven_groups:
            steps["retained_socket_directory"] = str(sockets)
            print(f"Unproven process groups {sorted(unproven_groups)}; retained private socket at {sockets}")
        else:
            socket_empty = not any(sockets.iterdir())
            pidfile_gone = not db or not (db.data / "postmaster.pid").exists()
            shutil.rmtree(sockets)
            if steps.get("postgres_cleanup"):
                steps["postgres_cleanup"][-1].update(
                    socket_directory=str(sockets), socket_directory_removed=True,
                    socket_closed=socket_empty, pidfile_gone=pidfile_gone,
                )
            require(socket_empty and pidfile_gone, "PostgreSQL left a socket or PID file after shutdown")


def channel_transition(event, current, previous):
    expected = {"scope": coordinates["scope"], "runtime": coordinates["runtime"],
                "channel": coordinates["channel"], "current": current}
    if previous is not None:
        expected["previous"] = previous
    require(event["channel_change"] == expected, event)


def check_release_event(event, work):
    require(event["actor"] == "local-publisher" and event["organization"] == "org-a" and
            event["project"] == "project-a" and event["previous"] != event["current"], event)
    require((work["event_id"], work["request_id"], work["kind"], work["status"]) ==
            (event["id"], event["request_id"], event["action"], "pending_local_only"), work)


def check_committed(db, label, sequence, artifact, rollout, count, previous, reason_text, *, action=None):
    audit, outbox = history()
    current = {"sequence": sequence, "artifact_sha256": artifact, "rollout_basis_points": rollout}
    event = audit[-1]
    channel_transition(event, current, previous)
    action = action or label
    require((event["id"], event["actor"], event["action"], event["reason"]) ==
            (count, "local-publisher", f"POST {base}/channels/production/{action}", reason_text), event)
    require(event["source_ip"] == "127.0.0.1" and event["request_id"], event)
    require(len(audit) == len(outbox) == count, "wrong audit or outbox count")
    require([row["id"] for row in audit] == list(range(1, count + 1)), "audit IDs are not contiguous")
    check_release_event(event, outbox[-1])
    if not db:
        return current, None
    snapshot = db.snapshot()
    require(snapshot["heads"] == [sequence], snapshot["heads"])
    expected_assignments = [(directory / f"{assignment_inputs[index]}.json").read_bytes().removesuffix(b"\n").hex()
                            for index in range(1, sequence + 1)]
    require(snapshot["assignments"] == expected_assignments, "persisted signed assignment history differs")
    require(list(map(json.loads, snapshot["audit"])) == audit, "SQL audit differs from operator readback")
    require(list(map(json.loads, snapshot["outbox"])) == outbox, "SQL outbox differs from operator readback")
    require(snapshot["tenant"] == [["org-a", "project-a", count, event["hash"], event["current"]]],
            "tenant high-water differs from the latest audit event")
    require(len(snapshot["idempotency"]) == count, "wrong committed idempotency count")
    previous_hash = ""
    for row, body in zip(audit, snapshot["audit"], strict=True):
        digest = row["hash"]
        unsigned = body.replace(f'"hash":"{digest}"', '"hash":""', 1)
        require(row["previous_hash"] == previous_hash and hashlib.sha256(unsigned.encode()).hexdigest() == digest,
                "invalid committed audit hash chain")
        previous_hash = digest
    steps.setdefault("committed_transitions", {})[label] = {
        "event_id": count, "request_id": event["request_id"], "event_hash": event["hash"],
        "actor": event["actor"], "reason": event["reason"], "source_ip": event["source_ip"],
        "channel_change": event["channel_change"], "audit_outbox_idempotency_rows_each": count,
    }
    return current, snapshot


def check_receipt(label, action, digest, sequence, rollout, *, health=None):
    expected = {"status": "ok", "action": action, "artifact_sha256": digest,
                "sequence": sequence, "rollout_basis_points": rollout, "delivery": "local_only"}
    if health is not None:
        expected["health"] = health
    require(steps[label] == expected, (label, steps[label]))


def halted_offers():
    return {bucket: offer(bucket) for bucket in ("early", "expansion", "outside")}


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
        if unproven_groups:
            (directory / "HOLD.json").write_text(json.dumps({
                "unproven_process_groups": sorted(unproven_groups), "fixture": str(directory),
                "socket_directory": steps.get("retained_socket_directory"),
            }, indent=2) + "\n")
        print(f"Preserved failed fixture at {directory}")
        raise
    else:
        shutil.rmtree(directory)


def interrupted(signum, _frame):
    raise SystemExit(128 + signum)


if args.postgres:
    signal.signal(signal.SIGTERM, interrupted)

require(not os.path.lexists(args.evidence), f"evidence path already exists: {args.evidence}")

with disposable_directory() as directory, contextlib.ExitStack() as stack:
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
    assignment_inputs = {1: "publish-first", 2: "promote", 3: "publish-second", 4: "rollback",
                         5: "halt", 6: "resume"}
    publish = command("publish", "first", "publish-first", "--channel", "production", "--rollout", "5")
    promote = command("promote", first, "promote", "--rollout", "25")
    rollback = command("rollback", first, "rollback", "--reason", reason)
    db = stack.enter_context(postgres()) if args.postgres else None
    development_reason = "local development operation"
    with service():
        steps["before_publish"] = offer("early")
        require(history() == ([], []), "new origin history is nonempty")
        if db:
            require(all(not rows for rows in db.snapshot().values()), "new PostgreSQL release tables are nonempty")
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
        steps["delivered_payload_sha256"] = steps["after_publish"]["early"]["payload_sha256"]
        published_head, _ = check_committed(db, "publish", 1, first, 500, 3, None, development_reason)
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
        promoted_head, _ = check_committed(db, "promote", 2, first, 2500, 4, published_head, development_reason)
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
        replacement_head, _ = check_committed(
            db, "publish_replacement", 3, second, 10000, 7, promoted_head, development_reason,
            action="publish",
        )
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
        rollback_head, committed = check_committed(db, "rollback", 4, first, 10000, 8,
                                                   replacement_head, reason)
        audit, outbox = history()
        require(len(audit) == len(outbox) == 8, (audit, outbox))
        expected_routes = [f"PUT {base}/artifacts/{first}", f"POST {base}/releases/validate",
                           f"POST {base}/channels/production/publish", f"POST {base}/channels/production/promote",
                           f"PUT {base}/artifacts/{second}", f"POST {base}/releases/validate",
                           f"POST {base}/channels/production/publish", f"POST {base}/channels/production/rollback"]
        require([event["action"] for event in audit] == expected_routes, audit)
        require([event["reason"] for event in audit] == [development_reason] * 7 + [reason], audit)
        for event, work in zip(audit, outbox, strict=True):
            check_release_event(event, work)
        heads = [(1, first, 500), (2, first, 2500), (3, second, 10000), (4, first, 10000)]
        previous = None
        for event, (sequence, artifact, rollout) in zip((audit[i] for i in (2, 3, 6, 7)), heads, strict=True):
            head = {"sequence": sequence, "artifact_sha256": artifact, "rollout_basis_points": rollout}
            channel_transition(event, head, previous)
            previous = head
        steps["audit_channel_sequences"] = [head[0] for head in heads]
        steps["audit"] = [{key: event[key] for key in ("id", "actor", "action", "reason", "hash")} for event in audit]
        steps["outbox_count"] = len(outbox)
    with service():
        if db:
            require(db.snapshot() == committed and history() == (audit, outbox), "restart changed committed history")
            require(offer("outside", 4, first) == steps["after_rollback"], "restart changed committed offer")
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
        require(steps["after_restart_retries"] == steps["after_rollback"], "replay changed the signed rollback offer")
        if db:
            require(db.snapshot() == committed, "replay changed persisted rows, including idempotency responses")
            steps["postgres_rows_unchanged_on_restart_and_replay"] = True

        health = {"sequence": 4, "activated": 3, "pending": 2, "adverse_signals": 1}
        health_file = directory / "halt-health.json"
        health_file.write_text(json.dumps({**health, "sequence": 3}))
        halt = command("halt", first, "halt", "--channel", "production", "--health", health_file.name)
        denied = call("halt_stale_health", halt, "update.halt.rejected")
        require("HTTP 409 (stale_rollout)" in denied["message"], denied)

        health_file.write_text(json.dumps(health))
        call("halt_missing_channel", command("halt", first, "halt", "--health", health_file.name),
             "update.arguments")
        call("halt_nonzero_assignment", command("halt", first, "resume", "--channel", "production",
                                                "--health", health_file.name), "update.intent")
        require(history() == (audit, outbox), "rejected halt wrote audit or outbox")
        require(offer("outside", 4, first) == steps["after_rollback"], "rejected halt changed the offer")
        if db:
            require(db.snapshot() == committed, "rejected halt changed persisted rows")

        call("halt", halt)
        check_receipt("halt", "halt", first, 5, 0, health=health)
        halt_head, halted_snapshot = check_committed(
            db, "halt", 5, first, 0, 9, rollback_head, development_reason,
        )
        halted_audit, halted_outbox = history()
        require(halted_audit[:-1] == audit and halted_outbox[:-1] == outbox, "halt changed the history prefix")
        expected_halt = {"scope": coordinates["scope"], "runtime": coordinates["runtime"],
                         "channel": coordinates["channel"], "artifact_sha256": first,
                         "halt_sequence": 5, "health": health}
        halt_event = halted_audit[-1]
        require(halt_event["rollout_halt"] == expected_halt, halt_event)
        steps["halt_audit"] = {key: halt_event[key] for key in ("id", "hash", "channel_change", "rollout_halt")}
        steps["after_halt"] = halted_offers()

        call("halt_identical_retry", halt)
        require(last_output["halt_identical_retry"] == last_output["halt"], "halt retry changed stdout")
        health_file.write_text(json.dumps({**health, "activated": 4}))
        denied = call("halt_altered_retry", halt, "update.halt.rejected")
        require("HTTP 409 (stale_rollout)" in denied["message"], denied)
        health_file.write_text(json.dumps(health))
        require(history() == (halted_audit, halted_outbox), "halt retries changed audit or outbox")
        if db:
            require(db.snapshot() == halted_snapshot, "halt retries changed persisted rows")

    with service():
        steps["after_halt_restart"] = halted_offers()
        require(steps["after_halt_restart"] == steps["after_halt"], "restart changed halted offers")
        call("halt_retry_after_restart", halt)
        require(last_output["halt_retry_after_restart"] == last_output["halt"], "halt replay changed stdout")
        require(history() == (halted_audit, halted_outbox), "restart or replay changed halt history")
        if db:
            require(db.snapshot() == halted_snapshot, "restart or replay changed committed halt rows")
            steps["postgres_halt_rows_unchanged_on_restart_and_replay"] = True
            if args.restore_after_halt:
                halted_backup = db.backup_halt()

        call("promote_resume", command("promote", first, "resume", "--channel", "production", "--rollout", "25"))
        check_receipt("promote_resume", "promote", first, 6, 2500)
        check_committed(db, "promote_resume", 6, first, 2500, 10, halt_head, development_reason, action="promote")
        resumed_audit, resumed_outbox = history()
        require(resumed_audit[:-1] == halted_audit and resumed_outbox[:-1] == halted_outbox,
                "resuming changed the halt history")
        steps["resume_audit"] = {key: resumed_audit[-1][key] for key in ("id", "hash", "channel_change")}
        steps["after_resume"] = {"early": offer("early", 6, first), "expansion": offer("expansion", 6, first),
                                 "outside": offer("outside")}
    if args.restore_after_halt:
        require(db.snapshot()["heads"] == [6], "source database did not advance past its backup")
        db.restore_halt(halted_backup)
        with service():
            require(db.snapshot() == halted_snapshot, "restored SQL rows differ from the halted backup")
            require(halted_offers() == steps["after_halt"], "restored rollout served an offer")
            call("restored_halt_retry", halt)
            require(last_output["restored_halt_retry"] == last_output["halt"], "restored halt receipt changed")
            require(db.snapshot() == halted_snapshot and history() == (halted_audit, halted_outbox),
                    "replaying halt changed the restored database")
            call("restored_promotion", command("promote", first, "resume", "--channel", "production", "--rollout", "25"))
            check_receipt("restored_promotion", "promote", first, 6, 2500)
            restored_offer = offer("early", 6, first)
            require(restored_offer == steps["after_resume"]["early"], "restored promotion changed signed bytes")
            check_committed(db, "restored_promotion", 6, first, 2500, 10, halt_head, development_reason, action="promote")
            steps["restored_halt"] = {"archive_sha256": hashlib.sha256(halted_backup.read_bytes()).hexdigest(),
                                      "source_sequence": 6, "restored_sequence": 5,
                                      "offers": steps["after_halt"], "identical_retry": True,
                                      "restored_promotion_offer": restored_offer}

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
with args.evidence.open("x") as evidence:
    evidence.write(json.dumps(steps, indent=2, sort_keys=True) + "\n")
print(f"PASS ({steps['storage_backend']}): {len(steps)} recorded observations")
