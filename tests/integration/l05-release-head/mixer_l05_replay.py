#!/usr/bin/env python3
"""Replay the pinned release fixture against the built console in an owned browser tab."""

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import platform
import secrets
import shutil
import signal
import socket
import subprocess
import tarfile
import tempfile
from threading import Lock, Thread
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

PIN = "71e6ffa51e857d5a1eda3f74c26941996ed275de"
ROOT = Path(__file__).resolve().parents[3]
FIXTURE = "test/mixer_hosted/releases/browser_publication_test.exs"
STATUS = {
    "anonymous": "Sign in to view this release.",
    "empty": "No release has been published to this target.",
    "first_publish": "Published release",
    "second_publish": "Published release",
    "rollback": "Published release",
    "denied": "You cannot access this release target.",
    "wrong_target": "You cannot access this release target.",
}
TARGET_FIELDS = {
    "Organization ID": "organizationId", "Project ID": "projectId",
    "Application ID": "applicationId", "Environment ID": "environmentId",
    "Platform": "platform", "Runtime fingerprint": "runtimeFingerprint", "Channel": "channel",
}
RELEASE_FIELDS = {
    "Release ID": "releaseId", "Sequence": "sequence",
    "Rollout basis points": "rolloutBasisPoints",
    "Manifest SHA-256": "manifestSha256", "Payload SHA-256": "payloadSha256",
}
HEAD = "/console-api/v1/release-head"


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], text=True).strip()


def write_json(path, value):
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(value, indent=2) + "\n")
    pending.replace(path)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def instrument(source, details=False):
    def insert_once(before, after):
        nonlocal source
        require(source.count(before) == 1, "Pinned fixture anchor changed")
        source = source.replace(before, before + "\n" + after)

    insert_once('Code.require_file("../browser_auth/storage_fixture.exs", __DIR__)',
                'Code.require_file("mixer_l05_checkpoint.exs", __DIR__)')
    insert_once('  alias MixerHosted.Test.StockReleaseCLI',
                '  alias MixerHosted.Test.ReleaseHeadBrowserCheckpoint, as: Checkpoint')
    insert_once('    assert %{"kind" => "empty"} = read!(c, owner, target)', """
    other = login(c, :other_tenant)
    :ok = GenServer.call(c.provider, {:mode, :ok})
    Checkpoint.wait!(:empty, c, path(target), read!(c, owner, target))""")
    insert_once('''    {offer, artifact} =
      assert_delivery(c, offer_path, first_path, signed_first, first_envelope, config)''', """
    read = read!(c, owner, target)
    Checkpoint.published!(read, first, Base.decode64!(fixture["payload"]))
    Checkpoint.wait!(:first_publish, c, path(target), read)""")
    insert_once('    assert_delivery(c, offer_path, second_path, signed_second, second_envelope, config)', """
    read = read!(c, owner, target)
    Checkpoint.published!(read, second, Base.decode64!(fixture["payload"]))
    Checkpoint.wait!(:second_publish, c, path(target), read)""")
    insert_once('      assert_delivery(restarted, offer_path, first_path, signed_rollback, first_envelope, config)', """
      read = read!(restarted, owner, target)
      Checkpoint.published!(read, rollback, Base.decode64!(fixture["payload"]))
      assert_status(restarted, other, target, 404)
      denied = http(restarted, path(target), other)
      assert response_header(denied, "cache-control") == ["no-store"]
      Checkpoint.wait!(:rollback, restarted, path(target), read, Jason.decode!(denied.body))""")
    insert_once('    assert %{"state" => "authenticated"} = Jason.decode!(session.body)',
                '    Checkpoint.capture_cookie(mode, response, &response_header/2)')
    if details:
        source = source.replace("path(target), read)", "path(target), read!(c, owner, target, :details))")
        source = source.replace("path(target), read!(c, owner, target))",
                                "path(target), read!(c, owner, target, :details))")
        before = "Checkpoint.wait!(:rollback, restarted, path(target), read, Jason.decode!(denied.body))"
        require(source.count(before) == 1, "Pinned rollback checkpoint changed")
        source = source.replace(before, """wrong_target = %{target | channel: "stable"}
      wrong = http(restarted, path(wrong_target, :details), owner)
      denied = http(restarted, path(target, :details), other)
      assert wrong.status == 404 and denied.status == 404
      assert response_header(wrong, "cache-control") == ["no-store"]
      assert response_header(denied, "cache-control") == ["no-store"]
      assert Jason.decode!(wrong.body) == Jason.decode!(denied.body)
      Checkpoint.wait!(:rollback, restarted, path(target), read!(restarted, owner, target, :details), Jason.decode!(denied.body))""")
    return source


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    return False


@contextmanager
def owned(name, command, cwd, env, scratch, records):
    with (scratch / (name + ".log")).open("wb") as log:
        child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        record = {"name": name, "pid": child.pid, "pgid": child.pid,
                  "command": [str(arg).replace(str(scratch), "<scratch>") for arg in command]}
        records.append(record)
        try:
            yield child
        finally:
            if child.poll() is None:
                # PostgreSQL fast shutdown rolls back open work and reaps its workers.
                child.send_signal(signal.SIGINT if name == "postgres" else signal.SIGTERM)
                try:
                    child.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    pass
            record.update(exit=child.poll(), groupAbsent=group_absent(child.pid))
            if record["exit"] is None or not record["groupAbsent"]:
                write_json(scratch / "HOLD.json", record)
                raise RuntimeError(f"Unknown custody for {name}, PGID {child.pid}")


def build_or_check(name, command, cwd, env, scratch, records, timeout=90):
    with owned(name, command, cwd, env, scratch, records) as child:
        if child.wait(timeout=timeout) != 0:
            tail = (scratch / f"{name}.log").read_text(errors="replace").splitlines()[-24:]
            raise RuntimeError(f"{name} failed\n" + "\n".join(tail))


def await_file(path, child, timeout):
    deadline = time.monotonic() + timeout
    while not path.is_file():
        require(child.poll() is None, "Phoenix fixture exited before " + path.name)
        require(time.monotonic() < deadline, "Timed out waiting for " + path.name)
        time.sleep(.1)
    return json.loads(path.read_text())


@contextmanager
def serve(dist, hostname, state, lock):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log handoff URLs or session values.

        def respond(self, status, headers=(), body=b""):
            try:
                self.send_response(status)
                for name, value in headers:
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return True
            except (BrokenPipeError, ConnectionResetError):
                return False

        def do_GET(self):
            uri = urlsplit(self.path)
            if self.headers.get("Host") != f"{hostname}:{self.server.server_port}" or uri.netloc:
                return self.respond(400)
            with lock:
                checkpoint = state.get("checkpoint")
                if uri.path == state.get("entry") and not uri.query:
                    state["entry"] = None
                    return self.respond(303, [
                        ("Set-Cookie", checkpoint["cookies"][state["role"]]),
                        ("Location", state["releasePath"]), ("Cache-Control", "no-store"),
                        ("Referrer-Policy", "no-referrer"),
                    ])
                phase = state.get("phase")
            if uri.path in ("/auth/session", HEAD):
                if checkpoint is None:
                    return self.respond(503)
                upstream = HTTPConnection("127.0.0.1", checkpoint["phoenix"], timeout=6)
                try:
                    forwarded = {name: self.headers[name] for name in ("Cookie", "Accept")
                                 if name in self.headers}
                    upstream.request("GET", self.path, headers=forwarded)
                    response = upstream.getresponse()
                    status = response.status
                    headers = [(name, value) for name, value in response.getheaders()
                               if name.lower() not in {"connection", "content-length", "transfer-encoding",
                                                       "server", "date"}]
                    body = response.read(65537)
                    require(len(body) <= 65536, "Unexpected upstream body size")
                except (OSError, RuntimeError):
                    return self.respond(502)
                finally:
                    upstream.close()
                cookie = self.headers.get("Cookie")
                role = next((name for name, issued in checkpoint["cookies"].items()
                             if cookie == issued.split(";", 1)[0]), None)
                delivered = self.respond(status, headers, body)
                with lock:
                    if not delivered:
                        state["clientDisconnects"][uri.path] += 1
                    elif uri.path == HEAD:
                        state["heads"].append((phase, role, sorted(parse_qsl(uri.query)),
                                               status, response.getheader("Cache-Control"),
                                               json.loads(body) if body else None))
                    else:
                        state["sessionStatuses"][(phase, role, status)] += 1
                return

            asset = (dist / uri.path.lstrip("/")).resolve() if uri.path != "/releases" else dist / "index.html"
            if not asset.is_relative_to(dist) or not asset.is_file():
                return self.respond(404)
            self.respond(200, [
                ("Content-Type", mimetypes.guess_type(asset)[0] or "application/octet-stream"),
                ("Cache-Control", "no-store"),
            ], asset.read_bytes())

    class Server(ThreadingHTTPServer):
        daemon_threads = False

        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(8)
            return connection, address

    server = Server(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    try:
        yield server.server_port
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def fields(wire, labels):
    return {label: str(wire[key]) for label, key in labels.items()} if wire else None


def details_dom(expected):
    details = expected.get("release", {}).get("details")
    if details is None:
        return {}
    return {
        "Source commit": details["sourceCommit"],
        "Payload size": f'{details["payloadBytes"]} bytes',
        "Artifact signing key ID": details["artifactKeyId"],
        "Assignment signing key ID": details["assignmentKeyId"],
        "Ledger action": details["action"].capitalize(),
        "Runtime admission": "Compatibility checked when this head was committed.",
    }


def observe(phase, checkpoint, root, origin, child, state, lock, details=False):
    target_path = checkpoint["path"]
    if phase == "wrong_target":
        parts = urlsplit(target_path)
        query = parse_qsl(parts.query)
        require(("channel", "beta") in query, "Expected a beta fixture head")
        target_path = parts.path + "?" + urlencode([(key, "stable" if key == "channel" else value)
                                                   for key, value in query])
    release_path = target_path.removeprefix("/console-api/v1/release-head")
    role = None if phase == "anonymous" else "other" if phase == "denied" else "owner"
    entry = f"/__mixer_l05_{secrets.token_hex(16)}" if phase in ("empty", "denied") else None
    with lock:
        state.update(checkpoint=checkpoint, phase=phase, entry=entry, role=role,
                     releasePath="/releases" + release_path)
    write_json(root / "ready.json", {
        "phase": phase, "url": origin + (entry or state["releasePath"]),
        "expectedStatus": STATUS[phase], "observationFile": str(root / f"dom-{phase}.json"),
    })
    dom = await_file(root / f"dom-{phase}.json", child, 90)
    denied_phase = phase in ("denied", "wrong_target")
    expected = checkpoint["expected"] if phase != "anonymous" and not denied_phase else {}
    release = fields(expected.get("release"), RELEASE_FIELDS)
    expected_dom = {"path": state["releasePath"], "status": STATUS[phase],
                    "target": fields(expected.get("target"), TARGET_FIELDS), "release": release}
    if details:
        expected_dom["capabilities"] = None
        if release is not None:
            release.update(details_dom(expected))
            expected_dom["capabilities"] = expected["release"]["details"]["capabilities"]
    require(dom == expected_dom, f"Rendered {phase} differs from fixture: {dom!r}")
    with lock:
        reads = [row for row in state["heads"] if row[0] == phase]
        sessions = state["sessionStatuses"][(phase, role, 200)]
    require(sessions > 0, f"No ordinary Phoenix session read for {phase}")
    if phase == "anonymous":
        require(not reads, "Anonymous page requested the release head")
    else:
        status = 404 if denied_phase else 200
        body = checkpoint["denied"] if denied_phase else expected
        require(not denied_phase or set(body) == {"error"}, "Unauthorized response leaked data")
        query = parse_qsl(urlsplit(target_path).query)
        if details:
            query.append(("view", "details"))
        query.sort()
        require(reads and all(read == (phase, role, query, status, "no-store", body) for read in reads),
                f"Unexpected Phoenix release-head response for {phase}")
    result = {"status": dom["status"], "target": dom["target"], "release": dom["release"],
              "sessionHTTP200": sessions, "headHTTP": reads[0][3:] if reads else None,
              "headReads": len(reads), "identity": role}
    if details:
        result["capabilities"] = dom["capabilities"]
    return result


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def verify_ports(ports):
    for port in ports:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", port))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--details-commit", help="Exact full revision containing the signed details view")
    args = parser.parse_args()
    pin = args.details_commit or PIN
    if args.details_commit and (len(pin) != 40 or any(char not in "0123456789abcdef" for char in pin)):
        parser.error("--details-commit requires a full lowercase commit SHA")
    details = args.details_commit is not None
    base = ROOT / "verification/local"
    base.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="l05-release-head-", dir=base))
    print(scratch, flush=True)

    env = {key: os.environ[key] for key in ("PATH", "HOME") if key in os.environ}
    for name in ("tmp", "fixture", "hex-cache"):
        (scratch / name).mkdir()
    env.update(LC_ALL="C", MIX_ENV="test", MIXER_L05_REPLAY=str(scratch),
               MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(scratch / "fixture"),
               TMPDIR=str(scratch / "tmp"), HEX_CACHE_HOME=str(scratch / "hex-cache"),
               npm_config_cache=str(scratch / "npm-cache"))
    hosted, console = scratch / "hosted", scratch / "console"
    records, outcomes, ports = [], {}, set()
    state = {"heads": [], "sessionStatuses": Counter(), "clientDisconnects": Counter()}
    lock = Lock()
    result = {
        "schema": 1, "source": {"commit": pin, "tree": git("rev-parse", pin + "^{tree}")},
        "observedUTC": datetime.now(timezone.utc).isoformat(),
        "host": platform.platform(), "tools": {"python": platform.python_version()},
        "browser": "Acid preview, owned incognito tab, unique .localhost HTTP origin",
        "phases": outcomes, "commands": records,
    }

    def run(name, command, cwd=scratch, timeout=90):
        build_or_check(name, command, cwd, env, scratch, records, timeout)

    complete = False
    try:
        archive = scratch / "pin.tar"
        run("git-archive", ["git", "-C", ROOT, "archive", "-o", archive, pin,
                            "hosted", "console", "services/protocol/testdata"])
        with tarfile.open(archive) as snapshot:
            snapshot.extractall(scratch, filter="data")
        archive.unlink()
        for tool, cmd in {
            "elixir": ["elixir", "--version"], "node": ["node", "--version"],
            "npm": ["npm", "--version"], "postgres": ["postgres", "--version"],
        }.items():
            run(tool + "-version", cmd)
            result["tools"][tool] = (scratch / (tool + "-version.log")).read_text().strip()
        run("npm-ci", ["npm", "ci", "--no-audit", "--no-fund", "--cache", "../npm-cache"], console)
        run("console-build", ["npm", "run", "build"], console)
        result["tools"]["vite"] = json.loads((console / "node_modules/vite/package.json").read_text())["version"]
        result["browserAssetsSHA256"] = {
            str(asset.relative_to(console / "dist")): sha256(asset.read_bytes()).hexdigest()
            for asset in sorted((console / "dist").rglob("*")) if asset.is_file()
        }
        packet = scratch / "services/protocol/testdata/signed-release-v3.json"
        result["signedFixtureSHA256"] = sha256(packet.read_bytes()).hexdigest()
        run("mix-deps", ["mix", "deps.get"], hosted)
        run("phoenix-compile", ["mix", "compile", "--warnings-as-errors"], hosted)
        test = hosted / FIXTURE
        source = instrument(test.read_text(), details)
        test.write_text(source)
        shutil.copyfile(Path(__file__).with_name("mixer_l05_checkpoint.exs"),
                        test.with_name("mixer_l05_checkpoint.exs"))
        target = next(i for i, line in enumerate(source.splitlines(), 1)
                      if 'test "shares a head between browser and CLI' in line)
        pg_port = free_port()
        ports.add(pg_port)
        env["MIXER_BROWSER_STORAGE_PORT"] = str(pg_port)
        pgdata = scratch / "pgdata"
        run("initdb", ["initdb", "-D", pgdata, "-U", "browser_admin", "-A", "trust",
                       "--no-locale", "-E", "UTF8"])
        pg = ["postgres", "-D", pgdata, "-h", "127.0.0.1", "-p", str(pg_port),
              "-k", "", "-c", "timezone=UTC"]
        psql = ["psql", "-XAt", "-h", "127.0.0.1", "-p", str(pg_port), "-U", "browser_admin",
                "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        with owned("postgres", pg, scratch, env, scratch, records) as postgres:
            deadline = time.monotonic() + 10
            while True:
                require(postgres.poll() is None and time.monotonic() < deadline,
                        "Owned PostgreSQL did not start")
                with socket.socket() as client:
                    if client.connect_ex(("127.0.0.1", pg_port)) == 0:
                        break
                time.sleep(.1)
            roles = "; ".join("CREATE ROLE " + name + " " + login + " NOSUPERUSER NOBYPASSRLS NOINHERIT"
                              for name, login in [
                                  ("browser_schema_owner", "NOLOGIN"), ("browser_writer", "NOLOGIN"),
                                  ("browser_lifecycle", "LOGIN"), ("browser_ordinary", "LOGIN"),
                                  ("browser_operator", "LOGIN"),
                                  ("mixer_customer_build_catalog_definer_v1", "NOLOGIN"),
                              ])
            run("roles", psql + ["-c", roles])
            cmd = ["mix", "test", "--warnings-as-errors", "--seed", "0", "--trace",
                   "--timeout", "540000", f"{FIXTURE}:{target}"]
            hostname = f"mixer-l05-{secrets.token_hex(8)}.localhost"
            with serve(console / "dist", hostname, state, lock) as port:
                ports.add(port)
                origin = f"http://{hostname}:{port}"
                with owned("phoenix", cmd, hosted, env, scratch, records) as fixture:
                    rollback_phases = ("rollback", "wrong_target", "denied") if details else ("rollback", "denied")
                    for names in [("anonymous", "empty"), ("first_publish",),
                                  ("second_publish",), rollback_phases]:
                        fixture_phase = "empty" if names[0] == "anonymous" else names[0]
                        checkpoint = await_file(scratch / f"{fixture_phase}.json", fixture, 100)
                        ports.update(checkpoint[key] for key in ("phoenix", "provider", "jwks"))
                        for phase in names:
                            outcomes[phase] = observe(phase, checkpoint, scratch, origin, fixture, state, lock, details)
                        (scratch / f"{fixture_phase}.complete").touch()
                    require(fixture.wait(timeout=25) == 0, "Selected ExUnit test failed")
                summary = next((line.strip() for line in (scratch / "phoenix.log").read_text().splitlines()
                                if line.startswith("Result: ")), None)
                require(summary == "Result: 1 passed, 3 excluded", "Unexpected selected ExUnit result")
                result["fixtureTestSummary"] = summary
            run("database-removed", psql + ["-c",
                "SELECT count(*) FROM pg_database WHERE datname='browser_ordinary_installation_r1422'"])
            require((scratch / "database-removed.log").read_text().strip() == "0",
                    "Fixture database still exists")
            result["databaseDropped"] = True
        verify_ports(sorted(ports))
        result["portsRebound"] = sorted(ports)
        complete = True
    except (OSError, RuntimeError, StopIteration, subprocess.TimeoutExpired, ValueError) as error:
        result["error"] = str(error)
        if not (scratch / "HOLD.json").exists():
            for name in ("phoenix", "postgres"):
                log = scratch / f"{name}.log"
                if log.is_file():
                    result[f"{name}Tail"] = "\n".join(log.read_text(errors="replace").splitlines()[-14:])
    finally:
        held = (scratch / "HOLD.json").exists()
        if not held:
            shutil.rmtree(scratch)
        result.update(result="pass" if complete else "fail", scratchRemoved=not held,
                      custodyHold=str(scratch) if held else None,
                      clientDisconnects=dict(state["clientDisconnects"]))
        write_json(args.receipt.resolve(), result)
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
