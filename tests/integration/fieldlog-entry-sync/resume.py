#!/usr/bin/env python3
"""Run the FieldLog resumable photo HTTP journey from a pinned local Git object."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from threading import Barrier, Thread
import time
import uuid

sys.dont_write_bytecode = True
import run as baseline

HERE = Path(__file__).resolve().parent
RESUME_PATCH = baseline.PATCH_DIR / "fieldlog-552559d2-photo-resume.patch"
CHUNK_BYTES = 32_768
ACCOUNT = "synthetic-owner"
KEY_COLUMNS = "account_id, workspace_id, project_id, event_id"
RECORD_COLUMNS = "entry_id, event_json, entry_json"
PHASES = ("drop-chunk", "invalid-progress", "oversized-progress", "cancel", "drop-final", "replay", "verify")


require, digest = baseline.require, baseline.digest


class UnknownCustody(RuntimeError):
    pass


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*argv, cwd=None, env=None, timeout=20):
    try:
        process = subprocess.Popen(
            argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except BaseException as error:
        raise UnknownCustody(f"Launch did not return an owned process ID for {argv[0]}.") from error

    with process.stdout:
        try:
            output, _ = process.communicate(timeout=timeout)
        except BaseException:
            try:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=5)
            except BaseException as error:
                raise UnknownCustody(f"Could not collect process group {process.pid}.") from error
            require_group_closed(process.pid)
            raise
    require_group_closed(process.pid)
    if process.returncode:
        raise RuntimeError(
            f"{' '.join(map(str, argv))} exited {process.returncode}\n"
            f"{output.decode(errors='replace')}"
        )
    return output


def require_group_closed(group):
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return
    except OSError as error:
        raise UnknownCustody(f"Could not verify closure of process group {group}.") from error
    raise UnknownCustody(f"Process group {group} survived its direct child.")


def prepare(checkout, root):
    paths = [*baseline.PATCHES, RESUME_PATCH]
    require(all(path.is_file() for path in paths), f"Expected the three patches, including {RESUME_PATCH}.")
    tool_env = dict(os.environ)
    temporary = root / "tmp"
    temporary.mkdir()
    tool_env.update(
        TMPDIR=str(temporary),
        CLANG_MODULE_CACHE_PATH=str(root / "clang-cache"),
        SWIFT_MODULE_CACHE_PATH=str(root / "swift-module-cache"),
    )
    git_env = {key: value for key, value in tool_env.items() if not key.startswith("GIT_")}
    git_env.update(GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")
    actual = run("git", "-C", checkout, "rev-parse", f"{baseline.PIN}^{{tree}}", env=git_env).decode().strip()
    require(actual == baseline.TREE, "The local Git object does not have the pinned FieldLog tree.")
    package = root / "package"
    package.mkdir()
    archive = run(
        "git", "-C", checkout, "archive", baseline.PIN, "Sources/FieldLogModels", "Sources/FieldLogStorage",
        "Tests/FieldLogTests/FieldLogTests.swift", env=git_env,
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(package, filter="data")
    run("git", "init", "--quiet", "--template=", cwd=package, env=git_env)
    for patches in (baseline.PATCHES, [RESUME_PATCH]):
        run("git", "apply", "--check", *patches, cwd=package, env=git_env)
        run("git", "apply", *patches, cwd=package, env=git_env)

    target = '        .testTarget(name: "FieldLogTests",'
    require(baseline.MANIFEST.count(target) == 1, "The predecessor package recipe changed.")
    (package / "Package.swift").write_text(baseline.MANIFEST.replace(
        target, '        .executableTarget(name: "FieldLogResumeJourney", '
        'dependencies: ["FieldLogModels", "FieldLogStorage"]),\n' + target,
    ))
    for name, source in (
        ("FieldLogJourney", HERE / "Journey.swift"),
        ("FieldLogResumeJourney", HERE / "ResumeJourney.swift"),
    ):
        directory = package / "Sources" / name
        directory.mkdir()
        shutil.copyfile(source, directory / source.name)

    flags = (
        "--scratch-path", root / "build",
        "--cache-path", root / "cache",
        "--config-path", root / "config",
        "--security-path", root / "security",
        "--disable-dependency-cache",
    )
    tested = run("/usr/bin/swift", "test", *flags, cwd=package, env=tool_env, timeout=120).decode()
    passed = re.findall(r"Test run with (\d+) tests?(?: in \d+ suites?)? passed", tested)
    require(passed == ["13"], f"Expected all 13 pinned repository tests.\n{tested}")
    for name in ("FieldLogJourney", "FieldLogResumeJourney"):
        run("/usr/bin/swift", "build", *flags, "--product", name, cwd=package, env=tool_env, timeout=60)
    binaries = run("/usr/bin/swift", "build", *flags, "--show-bin-path", cwd=package, env=tool_env).decode().strip()
    return package, Path(binaries), tool_env, 13


def read_database(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=3)) as connection:
        connection.execute("BEGIN")
        events = connection.execute(
            f"SELECT {KEY_COLUMNS}, {RECORD_COLUMNS} FROM entry_events ORDER BY {KEY_COLUMNS}"
        ).fetchall()
        photos = connection.execute(
            f"SELECT {KEY_COLUMNS}, photo_id, jpeg FROM entry_photos ORDER BY {KEY_COLUMNS}"
        ).fetchall()
        stages = connection.execute(
            f"SELECT {KEY_COLUMNS}, {RECORD_COLUMNS}, photo_id, byte_count, sha256, chunk_sha256s, jpeg "
            f"FROM entry_photo_uploads ORDER BY {KEY_COLUMNS}"
        ).fetchall()
        require(connection.execute("PRAGMA foreign_key_check").fetchall() == [], "Broken remote photo links.")
        return events, photos, stages


class OfflineFixture:
    def __init__(self, root):
        self.root = root
        self.ids = json.loads((root / "fixture.json").read_bytes())
        self.snapshot_path = root / "workspace" / "workspace.json"
        self.original_snapshot = self.snapshot_path.read_bytes()
        (root / "offline-workspace.json").write_bytes(self.original_snapshot)
        self.workspace = json.loads(self.original_snapshot)
        event = next(event for event in self.workspace["outbox"] if event["id"] == self.ids["event"])
        entry = next(entry for entry in self.workspace["entries"] if entry["id"] == self.ids["entry"])
        self.photo_directory = root / "workspace" / "photos"
        self.photos = {file.name: file.read_bytes() for file in self.photo_directory.iterdir()}
        require(set(self.photos) == {
            self.ids[key].lower() + ".jpg" for key in ("photo", "otherPhoto")
        }, "Expected exactly the two original saved photos.")
        for filename, jpeg in self.photos.items():
            (root / f"offline-{filename}").write_bytes(jpeg)
        self.jpeg = self.photos[self.ids["photo"].lower() + ".jpg"]
        require(len(self.jpeg) > 2 * CHUNK_BYTES and self.jpeg.startswith(b"\xff\xd8\xff"),
                "Expected a valid offline JPEG spanning at least three chunks.")
        self.sha = digest(self.jpeg)
        self.chunk_sha256s = [
            digest(self.jpeg[start:start + CHUNK_BYTES])
            for start in range(0, len(self.jpeg), CHUNK_BYTES)
        ]
        self.manifest = {
            "event": event, "entry": entry,
            "photo": {
                "id": self.ids["photo"], "byteCount": len(self.jpeg), "sha256": self.sha,
                "chunkSHA256s": self.chunk_sha256s,
            },
        }
        self.key = (ACCOUNT, *(self.ids[key].lower() for key in ("workspace", "project", "event")))
        self.route = f"/v1/workspaces/{self.key[1]}/projects/{self.key[2]}/entries/{self.key[3]}"
        self.receipt = {
            f"{key}ID": self.ids[key].lower() for key in ("event", "workspace", "project", "entry", "photo")
        }

    def chunk(self, offset):
        data = self.jpeg[offset:offset + CHUNK_BYTES]
        return {
            "photoID": self.ids["photo"], "sha256": self.sha, "offset": offset,
            "chunk": base64.b64encode(data).decode("ascii"), "chunkSHA256": digest(data),
        }

    def check_event(self, row):
        require(row[:5] == (*self.key, self.ids["entry"].lower()), "SQLite event ownership or identity changed.")
        require(json.loads(row[5]) == self.manifest["event"], "SQLite event metadata changed.")
        require(json.loads(row[6]) == self.manifest["entry"], "SQLite entry metadata changed.")

    def check_staged(self, state, length):
        events, photos, stages = state
        require(not events and not photos and len(stages) == 1, "Expected exactly one stage and no committed event or photo.")
        stage, = stages
        self.check_event(stage)
        expected = (
            self.ids["photo"].lower(), len(self.jpeg), self.sha,
            ",".join(self.chunk_sha256s), self.jpeg[:length],
        )
        require(stage[7:] == expected,
                f"SQLite stage did not contain the exact {length}-byte prefix and manifest.")
        return len(stage[-1])

    def check_committed(self, state):
        events, photos, stages = state
        require(len(events) == len(photos) == 1 and not stages,
                "Expected one committed event, one committed photo, and an empty upload stage.")
        self.check_event(events[0])
        require(photos[0] == (*self.key, self.ids["photo"].lower(), self.jpeg), "SQLite committed photo changed.")

    def check_local(self, acknowledged=False):
        current = self.snapshot_path.read_bytes()
        if acknowledged:
            expected = dict(self.workspace, revision=self.workspace["revision"] + 1)
            expected["outbox"] = [item for item in self.workspace["outbox"] if item["id"] != self.ids["event"]]
            require(any(item["id"] == self.ids["otherEvent"] for item in expected["outbox"]),
                    "The other entry must remain queued.")
            require(json.loads(current) == expected, "The disk acknowledgment changed more than the selected event and revision.")
        else:
            require(current == self.original_snapshot, "The saved workspace changed before the final receipt was accepted.")
        require({file.name: file.read_bytes() for file in self.photo_directory.iterdir()} == self.photos,
                "The selected or unrelated local photo bytes changed.")


@contextmanager
def listener(backend, database, accounts, handler, used_ports, excluded_ports):
    server = backend.make_server(database, accounts, port=0, handler_class=handler)
    port = server.server_port
    try:
        require(server.address_family == socket.AF_INET and server.server_address == ("127.0.0.1", port) and port,
                "Expected an ephemeral IPv4 loopback listener.")
        require(port not in excluded_ports, "The allocator selected an excluded port. No HTTP traffic was sent.")
        used_ports.append(port)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        thread.start()
        try:
            yield port
        finally:
            server.shutdown()
            thread.join(timeout=3)
            if thread.is_alive():
                raise UnknownCustody("The owned listener thread did not stop.")
    finally:
        try:
            server.server_close()
        except BaseException as error:
            raise UnknownCustody(f"Could not close listener and request threads on port {port}.") from error
        if server.socket.fileno() != -1:
            raise UnknownCustody(f"The owned listener did not close its socket on port {port}.")
    with socket.socket() as reuse:
        reuse.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        reuse.bind(("127.0.0.1", port))


def raw_post(port, route, token, body, *, include_body=False):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=5)) as client:
        client.request("POST", route, json.dumps(body).encode(), {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        })
        with client.getresponse() as response:
            data = response.read()
            return (response.status, json.loads(data)) if include_body else response.status


def check_refusals(port, fixture, offset, owner_token, other_token, database, before):
    manifest = fixture.manifest
    divergent_photo = str(uuid.uuid4()).upper()
    chunk = fixture.chunk(offset)
    changed_chunk = bytearray(fixture.jpeg[:CHUNK_BYTES])
    changed_chunk[-1] ^= 1
    changed_next_chunk = bytearray(fixture.jpeg[offset:offset + CHUNK_BYTES])
    changed_next_chunk[-1] ^= 1
    cases = [
        ("bad chunk digest", "/photo/chunks", dict(chunk, chunkSHA256="0" * 64), 400),
        ("negative offset", "/photo/chunks", dict(chunk, offset=-1), 400),
        ("boolean offset", "/photo/chunks", dict(chunk, offset=True), 400),
        ("offset ahead of prefix", "/photo/chunks", fixture.chunk(offset + CHUNK_BYTES), 409),
        ("other JPEG bytes with a valid digest at the current offset", "/photo/chunks", dict(
            chunk, chunk=base64.b64encode(changed_next_chunk).decode(),
            chunkSHA256=digest(changed_next_chunk),
        ), 409),
        ("wrong photo ID on chunk", "/photo/chunks", dict(chunk, photoID=divergent_photo), 409),
        ("conflicting bytes at offset zero", "/photo/chunks", dict(
            chunk, offset=0, chunk=base64.b64encode(changed_chunk).decode(),
            chunkSHA256=digest(changed_chunk),
        ), 409),
        ("divergent entry manifest", "/photo", dict(
            manifest, entry=dict(manifest["entry"], note="Divergent upload"),
        ), 409),
        ("divergent photo digest", "/photo", dict(
            manifest, photo=dict(manifest["photo"], sha256="0" * 64),
        ), 409),
        ("divergent chunk commitment", "/photo", dict(
            manifest, photo=dict(manifest["photo"], chunkSHA256s=["0" * 64, *fixture.chunk_sha256s[1:]]),
        ), 409),
        ("divergent photo identity", "/photo", dict(
            manifest, entry=dict(manifest["entry"], attachmentIDs=[divergent_photo]),
            photo=dict(manifest["photo"], id=divergent_photo),
        ), 409),
        ("manifest photo disagrees with attachment", "/photo", dict(
            manifest, photo=dict(manifest["photo"], id=divergent_photo),
        ), 400),
        ("premature finalization", "", manifest, 409),
    ]
    requests = [(name, fixture.route + path, owner_token, body, status)
                for name, path, body, status in cases]
    other_route = fixture.route.replace(f"/projects/{fixture.key[2]}/", f"/projects/{fixture.ids['otherProject'].lower()}/")
    requests += [
        ("invalid token", fixture.route + "/photo/chunks", secrets.token_urlsafe(32), chunk, 401),
        ("wrong account", fixture.route + "/photo/chunks", other_token, chunk, 404),
        ("wrong project", other_route + "/photo/chunks", owner_token, chunk, 404),
        ("wrong workspace", fixture.route.replace(fixture.key[1], str(uuid.uuid4())) + "/photo/chunks",
         owner_token, chunk, 404),
        ("unstaged event in the same scope", fixture.route.replace(fixture.key[3], str(uuid.uuid4())) + "/photo/chunks",
         owner_token, chunk, 409),
    ]
    results = {}
    for name, route, token, body, expected in requests:
        status = raw_post(port, route, token, body)
        require(status == expected, f"{name} returned HTTP {status}, expected {expected}.")
        require(read_database(database) == before, f"{name} changed the persisted upload or committed rows.")
        results[name] = status
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
        client.putrequest("POST", fixture.route + "/photo/chunks")
        client.putheader("Authorization", f"Bearer {owner_token}")
        client.putheader("Content-Type", "application/json")
        client.putheader("Content-Length", str(48 * 1024 + 1))
        # Headers only prove the server applies the cap before reading the body.
        client.endheaders()
        with client.getresponse() as response:
            response.read()
            require(response.status == 413, "The chunk request cap did not reject before reading.")
            results["oversized chunk request before body read"] = response.status
    require(read_database(database) == before, "The oversized request changed persisted state.")
    body = json.dumps(chunk).encode()
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
        client.putrequest("POST", fixture.route + "/photo/chunks")
        client.putheader("Authorization", f"Bearer {owner_token}")
        client.putheader("Content-Type", "application/json")
        client.putheader("Content-Length", str(len(body)))
        client.endheaders(body[:len(body) // 2])
        client.sock.shutdown(socket.SHUT_WR)
        with client.getresponse() as response:
            require(response.status == 400 and json.loads(response.read()) == {"error": "incomplete_request"},
                    "A chunk cut short in transit did not receive an incomplete-request refusal.")
            results["interrupted chunk request body"] = response.status
    require(read_database(database) == before, "The interrupted request changed persisted state.")
    fixture.check_local()
    return results


def check_duplicate_chunk(port, fixture, token, sent_offset, confirmed_offset):
    route = fixture.route + "/photo/chunks"
    start = Barrier(2, timeout=3)

    def send():
        start.wait()
        return raw_post(port, route, token, fixture.chunk(sent_offset), include_body=True)

    with ThreadPoolExecutor(max_workers=2) as workers:
        attempts = [workers.submit(send) for _ in range(2)]
        responses = [attempt.result() for attempt in attempts]
    expected = dict(
        fixture.receipt, byteCount=len(fixture.jpeg), sha256=fixture.sha,
        offset=confirmed_offset, prefixSHA256=digest(fixture.jpeg[:confirmed_offset]),
    )
    require(responses == [(200, expected)] * 2,
            f"Exact concurrent chunk retries returned {[status for status, _ in responses]} with offsets "
            f"{[body.get('offset') for _, body in responses]}.")
    return [status for status, _ in responses]


def exercise(backend, binaries, env, root, excluded_ports):
    database = root / "backend.sqlite3"
    offline = run(binaries / "FieldLogJourney", "offline", root, env=env).decode().strip()
    require(not database.exists(), "The offline phase unexpectedly created a backend database.")
    fixture = OfflineFixture(root)
    token, other_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    accounts = {
        token: (ACCOUNT, {fixture.key[1:3]}),
        other_token: ("synthetic-other", {(fixture.key[1], fixture.ids["otherProject"].lower())}),
    }
    photo_route = fixture.route + "/photo"
    chunks_route = photo_route + "/chunks"
    used_ports = []
    duplicate_statuses = {}

    def stage(phase, prior, offset, expected_chunks, expected_progress, final_status=None):
        traffic, confirmed, final_receipts, errors = [], [], [], []
        cancellation = []

        class Handler(backend.EntrySyncHandler):
            def do_POST(self):
                try:
                    super().do_POST()
                except Exception as error:
                    errors.append(error)
                    self.close_connection = True

            def _read_body(self, maximum):
                body = super()._read_body(maximum)
                if running_swift:
                    traffic.append((self.path, json.loads(body)))
                return body

            def truncate(self, status, receipt):
                data = json.dumps(receipt).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data[:12])
                self.close_connection = True

            def send_photo_progress(self, status, receipt):
                if not running_swift:
                    super().send_photo_progress(status, receipt)
                    return
                require(status == 200, f"Unexpected HTTP {status} for successful progress.")
                if self.path == photo_route:
                    length = offset
                else:
                    require(self.path == chunks_route, f"Unexpected progress route {self.path}.")
                    length = min(traffic[-1][1]["offset"] + CHUNK_BYTES, len(fixture.jpeg))
                expected = dict(
                    fixture.receipt, byteCount=len(fixture.jpeg), sha256=fixture.sha,
                    offset=length, prefixSHA256=digest(fixture.jpeg[:length]),
                )
                require(receipt == expected, f"Incorrect progress receipt at {length} bytes in {phase}.")
                state = read_database(database)
                if phase == "replay":
                    require(state == prior, "Committed photo query mutated or restaged the event.")
                else:
                    fixture.check_staged(state, length)
                confirmed.append(length)

                if phase == "invalid-progress":
                    receipt = dict(receipt, prefixSHA256="0" * 64)
                elif phase == "oversized-progress":
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b" " * 2049)
                    return
                elif self.path == chunks_route and phase in ("drop-chunk", "cancel"):
                    fixture.check_local()
                    if phase == "drop-chunk":
                        self.truncate(status, receipt)
                    else:
                        (root / "cancel-ready").touch()
                        deadline = time.monotonic() + 8
                        while not (root / "cancel-returned").exists() and time.monotonic() < deadline:
                            time.sleep(0.01)
                        cancellation.append((root / "cancel-returned").exists())
                        self.close_connection = True
                    return
                super().send_photo_progress(status, receipt)

            def send_receipt(self, status, receipt):
                require(status == final_status and receipt == fixture.receipt,
                        f"Unexpected ordinary entry receipt in {phase}: HTTP {status}.")
                fixture.check_local()
                state = read_database(database)
                fixture.check_committed(state)
                final_receipts.append(state)
                if phase == "drop-final":
                    self.truncate(status, receipt)
                else:
                    super().send_receipt(status, receipt)

        running_swift = False
        refusals = {}
        with listener(backend, database, accounts, Handler, used_ports, excluded_ports) as port:
            if prior is not None:
                require(read_database(database) == prior, f"Reopening SQLite changed the state before {phase}.")
            if phase == "invalid-progress":
                refusals = check_refusals(port, fixture, offset, token, other_token, database, prior)
                duplicate_statuses["staged"] = check_duplicate_chunk(port, fixture, token, 0, offset)
                require(read_database(database) == prior, "Exact chunk retries changed the prior staged bytes.")
            if phase == "replay":
                duplicate_statuses["committed"] = check_duplicate_chunk(
                    port, fixture, token, 0, CHUNK_BYTES,
                )
                changed = bytearray(fixture.jpeg[:CHUNK_BYTES])
                changed[-1] ^= 1
                divergent = dict(fixture.chunk(0), chunk=base64.b64encode(changed).decode(),
                                 chunkSHA256=digest(changed))
                refusals["divergent chunk after finalization"] = raw_post(port, chunks_route, token, divergent)
                require(refusals["divergent chunk after finalization"] == 409,
                        "Finalized event accepted a divergent chunk.")
                require(read_database(database) == prior, "Late chunk retries changed the committed bytes.")
            running_swift = True
            try:
                output = run(
                    binaries / "FieldLogResumeJourney", phase, root,
                    env=dict(env, FIELDLOG_TEST_PORT=str(port), FIELDLOG_TEST_OWNER_TOKEN=token),
                )
            except UnknownCustody:
                raise
            except Exception:
                if errors:
                    raise RuntimeError(f"Backend assertion failed in {phase}.") from errors[0]
                raise
        if errors:
            raise RuntimeError(f"Backend assertion failed in {phase}.") from errors[0]
        expected_traffic = [(photo_route, fixture.manifest)]
        expected_traffic += [(chunks_route, fixture.chunk(start)) for start in expected_chunks]
        if final_status is not None:
            expected_traffic.append((fixture.route, fixture.manifest))
        require(traffic == expected_traffic,
                f"{phase} sent unexpected routes or request bodies (routes: {[path for path, _ in traffic]}).")
        require(confirmed == [offset, *(min(start + CHUNK_BYTES, len(fixture.jpeg)) for start in expected_chunks)],
                f"{phase} did not observe every SQLite-backed progress receipt.")
        require(json.loads(output) == [
            {"acceptedBytes": count, "totalBytes": len(fixture.jpeg)} for count in expected_progress
        ], f"{phase} reported unexpected observer progress: {output.decode().strip()}.")
        require(cancellation == ([True] if phase == "cancel" else []),
                "Cancellation did not return while the server was withholding the receipt.")
        fixture.check_local(acknowledged=phase == "replay")
        state = read_database(database)
        if final_status is not None:
            require(final_receipts == [state], f"{phase} did not observe a single durable final receipt.")
        return state, refusals

    dropped, _ = stage("drop-chunk", None, 0, [0], [0])
    first_offset = fixture.check_staged(dropped, CHUNK_BYTES)
    rejected, refusals = stage("invalid-progress", dropped, first_offset, [], [])
    require(rejected == dropped, "Invalid progress changed the first committed prefix.")
    oversized, _ = stage("oversized-progress", dropped, first_offset, [], [])
    require(oversized == dropped, "Oversized progress changed the first committed prefix.")
    cancelled, _ = stage("cancel", dropped, first_offset, [first_offset], [first_offset])
    resume_offset = fixture.check_staged(cancelled, first_offset + CHUNK_BYTES)
    remaining = list(range(resume_offset, len(fixture.jpeg), CHUNK_BYTES))
    complete, _ = stage(
        "drop-final", cancelled, resume_offset, remaining,
        [resume_offset, *(min(start + CHUNK_BYTES, len(fixture.jpeg)) for start in remaining)], 201,
    )
    replayed, late_refusals = stage("replay", complete, len(fixture.jpeg), [], [len(fixture.jpeg)], 200)
    refusals.update(late_refusals)
    require(replayed == complete, "Replaying the lost final receipt changed the committed SQLite state.")
    require(json.loads(run(binaries / "FieldLogResumeJourney", "verify", root, env=env)) == [],
            "Cold local verification unexpectedly observed progress.")
    fixture.check_local(acknowledged=True)
    legacy_database = root / "legacy.sqlite3"
    legacy_body = dict(fixture.manifest, photo={
        "id": fixture.ids["photo"], "jpeg": base64.b64encode(fixture.jpeg).decode("ascii"),
    })
    with listener(backend, legacy_database, accounts, backend.EntrySyncHandler, used_ports, excluded_ports) as port:
        require(raw_post(port, photo_route, token, fixture.manifest) == 200, "Could not start the legacy control stage.")
        fixture.check_staged(read_database(legacy_database), 0)
        duplicate_statuses["firstAppend"] = check_duplicate_chunk(port, fixture, token, 0, CHUNK_BYTES)
        fixture.check_staged(read_database(legacy_database), CHUNK_BYTES)
        legacy_results = [raw_post(port, fixture.route, token, legacy_body, include_body=True) for _ in range(2)]
        require(legacy_results == [(201, fixture.receipt), (200, fixture.receipt)],
                "The predecessor's inline JPEG payload failed against an interrupted stage.")
        fixture.check_committed(read_database(legacy_database))
    return {
        "status": "passed",
        "offline": offline,
        "photoBytes": len(fixture.jpeg),
        "photoSHA256": fixture.sha,
        "eventID": fixture.ids["event"],
        "scopeIDs": fixture.receipt,
        "durableOffsets": {"afterDroppedChunkReceipt": first_offset, "afterInFlightCancellation": resume_offset},
        "resumedChunkOffsets": remaining,
        "invalidProgressRejected": True,
        "oversizedProgressRejected": True,
        "httpRefusalsWithoutMutation": refusals,
        "concurrentExactChunkRetries": duplicate_statuses,
        "ordinaryFinalStatuses": [201, 200],
        "legacyInlineJPEGStatusesAfterPartialUpload": [status for status, _ in legacy_results],
        "committed": {"eventRows": 1, "photoRows": 1, "stageRows": 0},
        "localAcknowledgment": {
            "revisionDelta": 1, "retiredEventCount": 1, "coldReopenVerified": True,
            "unchangedUnrelatedOutbox": True, "unchangedJPEGs": True,
        },
        "cleanup": {
            "listenersClosed": len(used_ports), "ephemeralPorts": used_ports, "portsRebound": True,
            "excludedPorts": sorted(excluded_ports),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fieldlog_checkout", type=Path, help="local Git checkout containing the pinned FieldLog object")
    parser.add_argument("--exclude-port", action="append", type=int, default=[],
                        help="refuse to send traffic if the OS assigns this reserved port")
    parser.add_argument("--receipt", type=Path, help="optional path for the compact JSON receipt")
    args = parser.parse_args()
    require(platform.system() == "Darwin", "The offline fixture uses AppKit JPEG encoding on macOS.")
    root = Path(tempfile.mkdtemp(prefix="fieldlog-photo-resume-")).resolve()
    try:
        package, binaries, env, tests = prepare(args.fieldlog_checkout.resolve(), root)
        backend = load_module("fieldlog_resume_backend", package / "Backend" / "local_entry_sync.py")
        result = exercise(backend, binaries, env, root, set(args.exclude_port))
        result.update(
            recordedAt=datetime.now(timezone.utc).isoformat(),
            fieldlogRevision=baseline.PIN,
            fieldlogTree=baseline.TREE,
            pinnedRepositoryTestsPassed=tests,
            sourceSHA256={
                path.name: digest(path.read_bytes())
                for path in [*baseline.PATCHES, RESUME_PATCH, HERE / "Journey.swift",
                             HERE / "ResumeJourney.swift", Path(__file__)]
            },
            predecessorRunnerSHA256=digest((HERE / "run.py").read_bytes()),
            tools={
                "Git": run("git", "--version", env=env).decode().strip(),
                "Swift": run("/usr/bin/swift", "--version", env=env).decode().strip(),
                "Python": platform.python_version(),
                "SQLite": sqlite3.sqlite_version,
                "macOS": platform.mac_ver()[0],
                "macOSSDK": run("/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version", env=env).decode().strip(),
                "arch": platform.machine(),
            },
            commands=[
                "git archive <pinned FieldLog>", "git apply <predecessors>", "git apply <resumable patch>",
                "swift test", "swift build --product FieldLogJourney",
                "swift build --product FieldLogResumeJourney", "FieldLogJourney offline <owned-scratch>",
                *(f"FieldLogResumeJourney {phase} <owned-scratch>" for phase in PHASES),
            ],
            scope="Mac host processes, FieldLog repository, IPv4 loopback HTTP, and a disposable SQLite file. "
                  "Synthetic owner scopes and one saved JPEG per entry. No mobile or Mixer capability runtime exercised.",
            paymentServiceOrCredentialsRequired=False,
        )
    except UnknownCustody:
        print(f"FieldLog replay could not verify closure. Retained {root}", file=sys.stderr)
        raise
    except BaseException:
        shutil.rmtree(root)
        print(f"FieldLog replay ended with an error. Removed closed scratch {root}", file=sys.stderr)
        raise
    shutil.rmtree(root)
    require(not root.exists(), "Owned test scratch was not removed.")
    result["cleanup"]["scratchRemoved"] = True
    output = json.dumps(result, indent=2) + "\n"
    if args.receipt:
        with args.receipt.open("x") as file:
            file.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
