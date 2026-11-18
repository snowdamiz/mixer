#!/usr/bin/env python3
"""Exercise the fixture and ordinary mixer binaries through their public CLI.

Arguments: FIXTURE_BINARY DEFAULT_BINARY INPUTS_JSON NEW_OUTPUT_DIRECTORY.
INPUTS_JSON maps ios and android to {artifact, artifactSHA256, identity}.
Identity holds provider, applicationID and either appID/buildID or track/versionCode.
Use closed development artifact inputs and a build compiled with
-Xswiftc -DMIXER_LOCAL_STORE_FIXTURE. The fixture has a private HTTP resource per
provider target. GET reads the accepted receipt, PUT creates it once using
If-None-Match: *, and 422 means rejection before any acceptance.
"""

from contextlib import closing, contextmanager
from hashlib import file_digest
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import uuid


TOKEN = "l05-local-fixture-token"
PREFIX = "/mixer-store-fixture/v1/submissions"


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def load_records(database):
    with closing(sqlite3.connect(database)) as db:
        return {path: json.loads(value) for path, value in db.execute(
            "SELECT path, receipt FROM submissions ORDER BY path"
        )}


class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.serve()

    def do_PUT(self):
        self.serve()

    def serve(self):
        server = self.server
        entry = {
            "method": self.command,
            "path": self.path,
            "host": self.headers.get("Host"),
            "fixtureAuthorization": self.headers.get("Authorization") == "Bearer " + TOKEN,
            "accept": self.headers.get("Accept"),
            "ifNoneMatch": self.headers.get("If-None-Match"),
            "contentType": self.headers.get("Content-Type"),
            "bodyBytes": int(self.headers.get("Content-Length", "0")),
            "transferEncoding": self.headers.get("Transfer-Encoding"),
        }
        server.trace.append(entry)
        if (self.path != server.target or not entry["fixtureAuthorization"]
                or entry["transferEncoding"] is not None or entry["bodyBytes"] > 4096):
            return self.reply(entry, 400)
        value = self.rfile.read(entry["bodyBytes"])
        mode = server.mode
        if self.command == "GET":
            if value:
                return self.reply(entry, 400)
            if mode == "lookup-failure":
                return self.reply(entry, 503)
            record = load_records(server.database).get(self.path)
            if record is None:
                return self.reply(entry, 404)
            if mode == "wrong-identity":
                record["submission"]["identity"]["applicationID"] = "com.example.foreign"
            return self.reply(entry, 200, record)

        content = json.loads(value)
        entry["body"] = content
        if entry["ifNoneMatch"] != "*" or content != server.expected:
            return self.reply(entry, 400)
        if mode == "reject":
            return self.reply(entry, 422)
        if mode == "redirect":
            return self.reply(entry, 307, location="/unexpected")
        receipt = {"submission": content, "submissionID": str(uuid.uuid4()).upper()}
        with closing(sqlite3.connect(server.database)) as db:
            db.execute("PRAGMA synchronous=FULL")
            result = db.execute("INSERT OR IGNORE INTO submissions VALUES (?, ?)",
                                (self.path, json.dumps(receipt)))
            db.commit()
            if result.rowcount == 0:
                return self.reply(entry, 412)
        entry["durablyAccepted"] = receipt["submissionID"]
        if mode == "lost-ack":
            entry["response"] = "connection-closed-before-ack"
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        if mode == "race":
            # Simulate a competing creator committing before this PUT's decision.
            return self.reply(entry, 412)
        return self.reply(entry, 201, receipt)

    def reply(self, entry, status, value=None, location=None):
        entry["response"] = status
        body = json.dumps(value).encode() if value is not None else b""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if location is not None:
            self.send_header("Location", location)
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def listener(database):
    server = HTTPServer(("127.0.0.1", 0), Fixture)
    server.database = database
    server.trace = []
    runner = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    runner.start()
    try:
        yield server
    finally:
        server.shutdown()
        runner.join(timeout=3)
        server.server_close()
        assert not runner.is_alive()
        with closing(socket.socket()) as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", server.server_port))


def run_cli(argv, env, root, label):
    with (root / (label + ".stdout")).open("xb") as out, (root / (label + ".stderr")).open("xb") as err:
        child = subprocess.Popen(argv, env=env, cwd=root, stdout=out, stderr=err,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
        meta = {"argv": [str(arg) for arg in argv], "pid": child.pid, "pgid": child.pid}
        path = root / (label + ".json")
        try:
            meta["exit"] = child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            meta["timedOut"] = True
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            meta["exit"] = child.wait(timeout=3)
        finally:
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                meta["groupAbsent"] = True
            finally:
                path.write_text(json.dumps(meta, indent=2))
    assert meta.get("groupAbsent") and not meta.get("timedOut"), meta
    raw = (root / (label + ".stdout")).read_bytes()
    assert (root / (label + ".stderr")).stat().st_size == 0
    assert TOKEN.encode() not in raw and b"wrong-synthetic-token" not in raw
    return meta["exit"], json.loads(raw)


def suite(fixture_binary, default_binary, inputs, root):
    root.mkdir(mode=0o700)
    for name in ("home", "tmp", "commands"):
        (root / name).mkdir(mode=0o700)
    cases, ports, counts = [], [], {}
    env = {"PATH": "/usr/bin:/bin", "HOME": str(root / "home"), "TMPDIR": str(root / "tmp")}

    for platform in ("ios", "android"):
        data = inputs[platform]
        artifact = Path(data["artifact"])
        assert digest(artifact) == data["artifactSHA256"]
        base = data["identity"]
        assert base["provider"] == ("app-store-connect" if platform == "ios" else "play")
        project = root / platform
        project.mkdir(mode=0o700)
        config = {
            "schema": 1, "name": "StoreFixture", "application": base["applicationID"],
            "language": "swift", "targets": [platform], "toolchainLock": "mixer.lock", "capabilities": [],
            "updates": {"activation": "cold-start", "compatibility": "exact-runtime-fingerprint",
                        "requireArtifactSignature": True, "requireAssignmentSignature": True},
        }
        (project / "mixer.yml").write_text(json.dumps(config))
        stale = root / (platform + "-stale-artifact")
        stale.write_bytes(b"Synthetic different development artifact for stale digest control.\n")
        database = root / (platform + ".sqlite")
        with closing(sqlite3.connect(database)) as db:
            db.execute("CREATE TABLE submissions (path TEXT PRIMARY KEY, receipt TEXT NOT NULL)")
            db.commit()

        def check(server, label, action, expected_exit, status, methods, *, code=None,
                  variant="", mode="", binary=fixture_binary, file=artifact, extra_env=None,
                  omit_port=False, writes=0):
            identity = dict(base)
            options = ["--provider", identity["provider"], "--directory", project, "--artifact", file]
            if platform == "ios":
                identity["buildID"] += variant
                options += ["--app-id", identity["appID"], "--build-id", identity["buildID"]]
                suffix = f"/ios/{identity['appID']}/{identity['buildID']}"
            else:
                identity["track"] += variant
                options += ["--track", identity["track"], "--version-code", str(identity["versionCode"])]
                suffix = f"/android/{identity['applicationID']}/{identity['track']}/{identity['versionCode']}"
            server.target = PREFIX + suffix
            server.expected = {"schema": 1, "identity": identity, "artifactSHA256": digest(file)}
            server.mode = mode
            port = server.server_port
            policy = root / f"loopback-{port}.sb"
            policy.write_text(f'(version 1)\n(allow default)\n(deny network*)\n'
                              f'(allow network-outbound (remote ip "localhost:{port}"))\n')
            child_env = env | (extra_env or {})
            if not omit_port:
                child_env["MIXER_LOCAL_STORE_FIXTURE_PORT"] = str(port)
            start = len(server.trace)
            before = load_records(database)
            label = f"{platform}-{label}"
            argv = ["/usr/bin/sandbox-exec", "-f", policy, binary, "submit", action, *options]
            result, report = run_cli(argv, child_env, root / "commands", label)
            requests = server.trace[start:]
            after = load_records(database)
            case = {"case": label, "exit": result, "report": report, "requests": requests,
                    "durableCountBefore": len(before), "durableCountAfter": len(after)}
            cases.append(case)
            (root / "cases.json").write_text(json.dumps(cases, indent=2))
            assert result == expected_exit and report["status"] == status, case
            assert report.get("code") == code, case
            assert [x["method"] for x in requests] == methods, case
            for event in requests:
                assert event["path"] == server.target and event["host"] == f"127.0.0.1:{port}", case
                assert event["fixtureAuthorization"] and event["transferEncoding"] is None, case
                assert event["accept"] == "application/json", case
                if event["method"] == "PUT":
                    assert event["body"] == server.expected and event["ifNoneMatch"] == "*", case
                    assert event["contentType"] == "application/json" and event["bodyBytes"] < 1024, case
                else:
                    assert event["bodyBytes"] == 0, case
            assert len(after) == len(before) + writes, case
            assert all(after[k] == v for k, v in before.items()), case
            if writes:
                assert after[server.target]["submission"] == server.expected
            if status == "accepted":
                assert report["qualification"] == "local-provider-fixture-only" and report["exitCode"] == 0
                assert report["submission"] == server.expected
                assert report["submissionID"] == after[server.target]["submissionID"]
                return report["submissionID"]
            assert "submissionID" not in report
            return after.get(server.target, {}).get("submissionID")

        with listener(database) as server:
            ports.append(server.server_port)
            check(server, "missing-port", "request", 1, "error", [], omit_port=True,
                  code="store.fixture-configuration")
            check(server, "wrong-token", "request", 1, "error", [],
                  extra_env={"MIXER_ASC_BEARER_TOKEN": "wrong-synthetic-token"},
                  code="store.fixture-configuration")
            default_code = "workflow.not-qualified" if platform == "ios" else "play.invalid-request"
            for action in ("request", "reconcile"):
                check(server, "default-" + action, action, 1, "error", [],
                      binary=default_binary, code=default_code)
            check(server, "absent-reconcile", "reconcile", 2, "not-observed", ["GET"])
            direct = check(server, "accepted", "request", 0, "accepted", ["GET", "PUT"], writes=1)
            assert check(server, "accepted-replay", "request", 0, "accepted", ["GET"]) == direct
            check(server, "stale", "request", 1, "unresolved", ["GET"], file=stale,
                  code="store.fixture-stale-artifact")
            check(server, "wrong-identity", "request", 1, "unresolved", ["GET"], mode="wrong-identity",
                  code="store.fixture-identity-mismatch")
            check(server, "lookup-failure", "request", 1, "unresolved", ["GET"], mode="lookup-failure",
                  variant="-failure", code="store.fixture-provider-error")
            check(server, "rejection", "request", 1, "rejected", ["GET", "PUT"], mode="reject",
                  variant="-failure", code="store.fixture-rejected")
            check(server, "rejected-remains-absent", "reconcile", 2, "not-observed", ["GET"],
                  variant="-failure")
            check(server, "redirect", "request", 1, "unresolved", ["GET", "PUT"], mode="redirect",
                  variant="-failure", code="store.fixture-redirect")
            check(server, "conditional-race", "request", 0, "accepted", ["GET", "PUT", "GET"],
                  mode="race", variant="-race", writes=1)
            lost = check(server, "lost-ack", "request", 1, "unresolved", ["GET", "PUT"],
                         mode="lost-ack", variant="-lost", code="store.fixture-transport", writes=1)
        # Destroy the listener and use the same durable database with a new listener.
        with listener(database) as server:
            ports.append(server.server_port)
            assert check(server, "lost-ack-reconcile", "reconcile", 0, "accepted",
                         ["GET"], variant="-lost") == lost
            assert check(server, "lost-ack-replay", "request", 0, "accepted",
                         ["GET"], variant="-lost") == lost
        counts[platform] = len(load_records(database))
        assert counts[platform] == 3
        assert not (project / ".mixer").exists()

    return {"status": "pass", "cases": cases, "inputs": inputs,
            "fixtureBinarySHA256": digest(fixture_binary), "defaultBinarySHA256": digest(default_binary),
            "durableRows": counts, "closedAndReboundPorts": ports,
            "allDirectChildrenReapedAndGroupsAbsent": True}


if __name__ == "__main__":
    fixture, default, inputs_json, output = map(lambda p: Path(p).resolve(), sys.argv[1:])
    receipt = suite(fixture, default, json.loads(inputs_json.read_text()), output)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"{len(receipt['cases'])} CLI controls passed")
