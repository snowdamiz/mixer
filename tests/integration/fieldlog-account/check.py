#!/usr/bin/env python3
"""Exercise the pinned FieldLog production handler over disposable loopback HTTP."""

import base64
from contextlib import closing, contextmanager
import hashlib
from http.client import HTTPConnection
import importlib.util
import json
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PIN = "afe98bad582e80925fc2ef29457a2d650a797aab"
BASE = "d6119af3714fa16e15f1cd4ed5c3f403daff4613"
AFTERIMAGE = "d942e66c5d46311dbce7e90e7eff5490afea3178"
SUCCESSOR = "b6debbc45f8ab96360d2d494e376d80ea5f6abf7"
BACKEND = "Backend/local_entry_sync.py"
ORDINARY_BACKEND = (
    "d203a1c27027e2ae10bc46deb911cc94b8c28cbb:"
    "verification/receipts/fieldlog-ios-task-conflict-injected-f2865989.patch"
)
PATCH = Path(__file__).with_name("fieldlog-local-account.patch.b64")
INCREMENTAL_PATCH = PATCH.with_name("fieldlog-local-account-confirmation.patch.b64")
ORIGIN = "http://127.0.0.1:8765"
BEGIN = "/v1/auth/attempts"
EXCHANGE = "/v1/auth/exchange"
SESSION = "/v1/account/session"
CONFIRMATION_WINDOW = 60
SESSION_LIFETIME = 8 * 60 * 60


class Clock:
    def __init__(self):
        self.now = 1_800_000_000

    def time(self):
        return self.now


def git(directory, *args, data=None):
    return subprocess.run(["git", "-C", directory, *args], input=data, stdout=subprocess.PIPE,
                          check=True, timeout=10).stdout


def assert_blob(directory, expected):
    actual = git(directory, "hash-object", BACKEND).decode().strip()
    assert actual == expected, (expected, actual)


def apply_exact(directory, patch, before, after, *, reverse=False):
    assert_blob(directory, before)
    options = ["--index", "--whitespace=error-all"]
    if reverse:
        options.append("--reverse")
    data = base64.b64decode(patch.read_bytes())
    git(directory, "apply", "--check", *options, "-", data=data)
    git(directory, "apply", *options, "-", data=data)
    assert_blob(directory, after)


def load(directory, name):
    spec = importlib.util.spec_from_file_location(name, directory / BACKEND)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def listener(backend, database, *args, **kwargs):
    with backend.make_server(database, *args, **kwargs) as server:
        port = server.server_port
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield port
        finally:
            server.shutdown()
            thread.join(timeout=2)
            assert not thread.is_alive()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            raise AssertionError("listener still accepts connections")
    except ConnectionRefusedError:
        pass


def request(port, method, path, status, *, token=None, payload=None, raw=None, headers=None,
            discard_body=False):
    request_headers = dict(headers or {})
    if token is not None:
        request_headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        raw = json.dumps(payload).encode()
    with closing(HTTPConnection("127.0.0.1", port, timeout=2)) as client:
        client.request(method, path, body=raw, headers=request_headers)
        response = client.getresponse()
        assert response.status == status, (method, status, response.status)
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("Set-Cookie") is None
        if discard_body:
            response.close()
            return
        body = response.read(1025)
        assert len(body) <= 1024
        assert response.getheader("Content-Length") == str(len(body))
        return response.getheader("Location"), body


def begin(port, platform):
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    payload = {"platform": platform, "state": state, "challenge": challenge[:-1].decode("ascii")}
    _, body = request(port, "POST", BEGIN, 201, payload=payload)
    url = urlsplit(json.loads(body)["browserURL"])
    assert url.scheme == "http" and url.netloc == "127.0.0.1:8765"
    assert url.path.startswith(BEGIN + "/") and not url.query and not url.fragment
    return url.path, {"platform": platform, "state": state, "verifier": verifier}


def browser_post(port, path, proof, status, origin=ORIGIN):
    return request(port, "POST", path, status, raw=f"proof={proof}", headers={
        "Content-Type": "application/x-www-form-urlencoded", "Origin": origin,
    })


def callback(port, path, exchange, proof, callback_scheme):
    _, form = request(port, "GET", path, 200)
    assert b"method=post" in form and b"name=proof" in form
    location, body = browser_post(port, path, proof, 303)
    assert not body and proof not in location and exchange["verifier"] not in location
    url = urlsplit(location)
    assert (url.scheme, url.netloc, url.path, url.fragment) == (callback_scheme, "account", "/callback", "")
    query = parse_qs(url.query, strict_parsing=True)
    assert set(query) == {"code", "state"} and query["state"] == [exchange["state"]]
    code, = query["code"]
    assert len(code) == 43
    return dict(exchange, code=code)


def exchange_token(port, exchange, account, workspace, project):
    _, data = request(port, "POST", EXCHANGE, 200, payload=exchange)
    session = json.loads(data)
    token = session.pop("token")
    assert len(token) == 43 and token != exchange["code"] and token != exchange["verifier"]
    assert session.keys() == {"accountID", "scopes", "expiresAt"}
    assert session["accountID"] == account
    assert session["scopes"] == [{"workspaceID": workspace, "projectID": project}]
    assert 58 <= session["expiresAt"] - int(time.time()) <= CONFIRMATION_WINDOW
    _, restore = request(port, "GET", SESSION, 200, token=token)
    confirmed = json.loads(restore)
    assert SESSION_LIFETIME - 2 <= confirmed["expiresAt"] - int(time.time()) <= SESSION_LIFETIME
    assert confirmed == dict(session, expiresAt=confirmed["expiresAt"])
    return token, restore


def verify_session_confirmation(backend, directory):
    clock = Clock()
    original_time = backend.time
    backend.time = clock
    try:
        exercise_session_confirmation(backend, directory / "confirmation.sqlite", clock)
    finally:
        backend.time = original_time


def exercise_session_confirmation(backend, database, clock):
    account, workspace, project, task = (str(uuid4()) for _ in range(4))
    backend.init_account_database(database)
    proof = backend.provision_local_account(database, account, workspace, project)
    metadata = {"accountID": account, "scopes": [{"workspaceID": workspace, "projectID": project}]}
    task_url = f"/v1/workspaces/{workspace}/projects/{project}/tasks/{task}"
    entry_url = f"/v1/workspaces/{workspace}/projects/{project}/entries/{uuid4()}"
    backend.provision_task(database, account, workspace, project, task,
                           {"title": "Confirmation", "responsible": "A"})

    def start_sign_in(port):
        path, pending = begin(port, "ios")
        return callback(port, path, pending, proof, "com.fieldlog.dev.ios")

    def exchange(port, pending):
        result = json.loads(request(port, "POST", EXCHANGE, 200, payload=pending)[1])
        token = result.pop("token")
        assert result == dict(metadata, expiresAt=clock.now + CONFIRMATION_WINDOW), result
        return token

    def confirm(port, token):
        return json.loads(request(port, "GET", SESSION, 200, token=token)[1])

    with listener(backend, database, local_accounts=True) as port:
        late = exchange(port, start_sign_in(port))
        request(port, "GET", task_url, 401, token=late)
        request(port, "POST", task_url, 401, token=late, payload={})
        request(port, "POST", entry_url, 401, token=late, payload={})
        clock.now += CONFIRMATION_WINDOW
        request(port, "GET", SESSION, 401, token=late)
        request(port, "DELETE", SESSION, 401, token=late)

        first_expiry = clock.now + SESSION_LIFETIME
        confirmed = []
        for _ in range(31):
            token = exchange(port, start_sign_in(port))
            assert confirm(port, token) == dict(metadata, expiresAt=first_expiry)
            confirmed.append(token)

        lost_proof = start_sign_in(port)
        request(port, "POST", EXCHANGE, 200, payload=lost_proof, discard_body=True)
        lost_expiry = clock.now + CONFIRMATION_WINDOW
        request(port, "POST", EXCHANGE, 401, payload=lost_proof)
        request(port, "POST", EXCHANGE, 429, payload=start_sign_in(port))

    with listener(backend, database, local_accounts=True) as port:
        clock.now = lost_expiry - 1
        assert confirm(port, confirmed[0]) == dict(metadata, expiresAt=first_expiry)
        request(port, "POST", EXCHANGE, 429, payload=start_sign_in(port))
        clock.now = lost_expiry
        request(port, "POST", EXCHANGE, 401, payload=lost_proof)
        revoked = exchange(port, start_sign_in(port))
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("SELECT count(*) FROM local_sessions").fetchone() == (32,)
            assert connection.execute("SELECT count(*) FROM local_sessions WHERE expires_at <= ?",
                                      (clock.now,)).fetchone() == (0,)
        assert json.loads(request(port, "DELETE", SESSION, 200, token=revoked)[1]) == {"signedOut": True}
        request(port, "GET", SESSION, 401, token=revoked)

        fresh = exchange(port, start_sign_in(port))

    with listener(backend, database, local_accounts=True) as port:
        clock.now += CONFIRMATION_WINDOW - 1
        request(port, "GET", task_url, 401, token=fresh)
        fresh_expiry = clock.now + SESSION_LIFETIME
        assert confirm(port, fresh) == dict(metadata, expiresAt=fresh_expiry)
        request(port, "GET", task_url, 200, token=fresh)
        clock.now += CONFIRMATION_WINDOW
        assert confirm(port, fresh) == dict(metadata, expiresAt=fresh_expiry)
        clock.now = first_expiry
        request(port, "GET", SESSION, 401, token=confirmed[0])
        assert confirm(port, fresh) == dict(metadata, expiresAt=fresh_expiry)
        clock.now = fresh_expiry
        request(port, "GET", SESSION, 401, token=fresh)


def verify_prior_database(previous, backend, directory):
    database = directory / "previous.sqlite"
    account, workspace, project, task = (str(uuid4()) for _ in range(4))
    previous.init_account_database(database)
    proof = previous.provision_local_account(database, account, workspace, project)
    previous.provision_task(database, account, workspace, project, task,
                            {"title": "Previous account", "responsible": "A"})
    task_url = f"/v1/workspaces/{workspace}/projects/{project}/tasks/{task}"
    with listener(previous, database, local_accounts=True) as port:
        path, pending = begin(port, "ios")
        pending = callback(port, path, pending, proof, "com.fieldlog.dev.ios")
        old_session = json.loads(request(port, "POST", EXCHANGE, 200, payload=pending)[1])
        token = old_session.pop("token")
        request(port, "GET", task_url, 200, token=token)

    for _ in range(2):
        with listener(backend, database, local_accounts=True) as port:
            assert json.loads(request(port, "GET", SESSION, 200, token=token)[1]) == old_session
            request(port, "GET", task_url, 200, token=token)


def upload(project, event, jpeg):
    entry, photo = (str(uuid4()).upper() for _ in range(2))
    return {
        "event": {"id": event.upper(), "kind": "entrySaved", "recordID": entry,
                  "revision": 1, "createdAt": 0},
        "entry": {"id": entry, "projectID": project.upper(), "title": "Synthetic entry",
                  "note": "Offline first", "category": "observation", "occurredAt": 0,
                  "attachmentIDs": [photo], "savedAt": 0},
        "photo": {"id": photo, "jpeg": base64.b64encode(jpeg).decode()},
    }


def seed_and_compare(backend, database, port, rows, task, project, event):
    wire = []
    for account, workspace, token, text, entry in rows:
        prefix = f"/v1/workspaces/{workspace}/projects/{project}"
        task_url = f"{prefix}/tasks/{task}"
        entry_url = f"{prefix}/entries/{event}"
        backend.provision_task(database, account, workspace, project, task, text)
        _, head_bytes = request(port, "GET", task_url, 200, token=token)
        head = json.loads(head_bytes)
        assert head["text"] == text
        head["scope"] = {key: value.upper() for key, value in head["scope"].items()}
        proposal = {"eventID": event.upper(), "base": head,
                    "text": dict(text, title=text["title"] + " saved")}
        _, task_receipt = request(port, "POST", task_url, 201, token=token, payload=proposal)
        _, entry_receipt = request(port, "POST", entry_url, 201, token=token, payload=entry)
        wire.append((task_url, entry_url, proposal, entry, head_bytes, task_receipt, entry_receipt))
    return wire


def replay(port, row, token, status):
    task_url, entry_url, proposal, entry, _, task_receipt, entry_receipt = row
    _, task = request(port, "POST", task_url, status, token=token, payload=proposal)
    _, photo = request(port, "POST", entry_url, status, token=token, payload=entry)
    if status == 200:
        assert (task, photo) == (task_receipt, entry_receipt)


def snapshot(database):
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        tables = ("task_heads", "task_events", "entry_events", "entry_photos")
        return {table: connection.execute(f"SELECT * FROM {table} ORDER BY 1, 2, 3, 4").fetchall()
                for table in tables}


def refuse_start(action):
    try:
        action()
    except (ValueError, FileExistsError, sqlite3.IntegrityError):
        return
    raise AssertionError("unexpected account setup success")


def verify(directory):
    git(directory, "init", "-q")
    for path in ("verification/fieldlog-entry-sync/fieldlog-552559d2-local-backend.patch",
                 "tests/integration/fieldlog-task-sync/fieldlog-saved-task-sync.patch"):
        git(directory, "apply", "--include=" + BACKEND, "-",
            data=git(ROOT, "show", f"{PIN}:{path}"))
    base = load(directory, "base")
    git(directory, "add", BACKEND)
    apply_exact(directory, PATCH, BASE, SUCCESSOR)
    backend = load(directory, "patched")
    apply_exact(directory, INCREMENTAL_PATCH, SUCCESSOR, AFTERIMAGE, reverse=True)
    previous = load(directory, "previous")
    apply_exact(directory, INCREMENTAL_PATCH, AFTERIMAGE, SUCCESSOR)
    verify_session_confirmation(backend, directory)
    verify_prior_database(previous, backend, directory)

    a, b, wa, wb, project, task, event = (str(uuid4()) for _ in range(7))
    texts = ({"title": "Owner A", "responsible": "A"}, {"title": "Owner B", "responsible": "B"})
    # The pinned route admits JPEG-prefixed bytes and stores them verbatim.
    jpegs = (b"\xff\xd8\xffFieldLog owner A\x00", b"\xff\xd8\xffFieldLog owner B\x00")
    entries = [upload(project, event, jpeg) for jpeg in jpegs]
    legacy_tokens = ("fixture-static-a", "fixture-static-b")
    grants = dict(zip(legacy_tokens, ((a, {(wa, project)}), (b, {(wb, project)}))))
    legacy_rows = list(zip((a, b), (wa, wb), legacy_tokens, texts, entries))
    legacy = directory / "baseline.sqlite"
    with listener(base, legacy, grants) as port:
        baseline = seed_and_compare(base, legacy, port, legacy_rows, task, project, event)
    with listener(backend, directory / "static.sqlite", grants) as port:
        assert seed_and_compare(backend, directory / "static.sqlite", port, legacy_rows,
                                task, project, event) == baseline
        replay(port, baseline[0], legacy_tokens[0], 200)
        request(port, "POST", BEGIN, 404, payload={})
        request(port, "GET", SESSION, 404, token=legacy_tokens[0])

    database = directory / "owned.sqlite"
    backend.init_account_database(database)
    refuse_start(lambda: backend.init_account_database(database))
    proof_a = backend.provision_local_account(database, a, wa, project)
    proof_b = backend.provision_local_account(database, b, wb, project)
    refuse_start(lambda: backend.provision_local_account(database, a, wa, project))
    refuse_start(lambda: backend.provision_local_account(database, str(uuid4()), wa, project))
    refuse_start(lambda: backend.make_server(database, grants))
    refuse_start(lambda: backend.make_server(legacy, local_accounts=True))
    refuse_start(lambda: backend.make_server(database, grants, local_accounts=True))

    with listener(backend, database, local_accounts=True) as port:
        assert port == 8765
        request(port, "POST", BEGIN, 400, headers={"Host": "localhost:8765"}, payload={})
        request(port, "POST", BEGIN, 413, payload={"oversized": "x" * 1024})
        request(port, "POST", BEGIN, 400, payload={"platform": "unknown", "state": "s" * 43,
                                                 "challenge": "c" * 43})
        request(port, "POST", BEGIN, 400, payload={"platform": "ios", "state": "s" * 43,
                                                 "challenge": "c" * 43, "redirectURI": ORIGIN})
        path, first = begin(port, "ios")
        browser_post(port, path, proof_a, 403, origin="null")
        browser_post(port, path, secrets.token_urlsafe(32), 401)
        first = callback(port, path, first, proof_a, "com.fieldlog.dev.ios")
        browser_post(port, path, proof_a, 401)
        for key in ("state", "verifier", "code", "platform"):
            wrong = "android" if key == "platform" else secrets.token_urlsafe(32)
            request(port, "POST", EXCHANGE, 401, payload=dict(first, **{key: wrong}))
        token_a, restore_a = exchange_token(port, first, a, wa, project)
        request(port, "POST", EXCHANGE, 401, payload=first)
        path, second = begin(port, "android")
        second = callback(port, path, second, proof_b, "com.fieldlog.dev.android")

    with listener(backend, database, local_accounts=True) as port:
        assert request(port, "GET", SESSION, 200, token=token_a)[1] == restore_a
        request(port, "DELETE", SESSION, 400, token=token_a, raw=b"x")
        token_b, restore_b = exchange_token(port, second, b, wb, project)
        request(port, "POST", EXCHANGE, 401, payload=second)
        rows = list(zip((a, b), (wa, wb), (token_a, token_b), texts, entries))
        wire = seed_and_compare(backend, database, port, rows, task, project, event)
        assert wire == baseline
        assert snapshot(database) == snapshot(legacy)
        request(port, "GET", wire[0][0], 404, token=token_b)
        replay(port, wire[0], token_b, 404)
        replay(port, wire[1], token_a, 404)
        replay(port, wire[0], legacy_tokens[0], 401)

        path, replacement = begin(port, "ios")
        replacement = callback(port, path, replacement, proof_a, "com.fieldlog.dev.ios")
        new_a, _ = exchange_token(port, replacement, a, wa, project)
        assert new_a != token_a
        assert json.loads(request(port, "DELETE", SESSION, 200, token=token_a)[1]) == {"signedOut": True}
        request(port, "DELETE", SESSION, 401, token=token_a)
        request(port, "GET", wire[0][0], 401, token=token_a)
        replay(port, wire[0], token_a, 401)
        replay(port, wire[0], new_a, 200)

        path, expired = begin(port, "ios")
        expired = callback(port, path, expired, proof_a, "com.fieldlog.dev.ios")
        unused_path, _ = begin(port, "ios")

    # Advance deadlines on the owned database while the listener is closed.
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE local_sessions SET expires_at = 0 WHERE account_id = ?", (a,))
        connection.execute("UPDATE local_auth_attempts SET expires_at = 0")
        assert connection.execute("SELECT count(*) FROM local_sessions WHERE account_id = ?", (a,)).fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM local_auth_attempts").fetchone() == (2,)

    with listener(backend, database, local_accounts=True) as port:
        request(port, "GET", SESSION, 401, token=token_a)
        request(port, "GET", SESSION, 401, token=new_a)
        request(port, "GET", wire[0][0], 401, token=new_a)
        replay(port, wire[0], new_a, 401)
        request(port, "GET", unused_path, 401)
        request(port, "POST", EXCHANGE, 401, payload=expired)
        assert request(port, "GET", SESSION, 200, token=token_b)[1] == restore_b
        replay(port, wire[1], token_b, 200)
    assert snapshot(database) == snapshot(legacy)
    for raw_secret in (proof_a, proof_b, token_a, token_b, new_a, first["code"], second["code"]):
        assert raw_secret.encode() not in database.read_bytes()
    apply_exact(directory, PATCH, SUCCESSOR, BASE, reverse=True)
    ordinary = directory / "ordinary-backend"
    ordinary.mkdir()
    git(ordinary, "init", "-q")
    git(ordinary, "apply", "--include=" + BACKEND, "--unidiff-zero", "-",
        data=git(ROOT, "show", ORDINARY_BACKEND))
    git(ordinary, "add", BACKEND)
    apply_exact(ordinary, PATCH, BASE, SUCCESSOR)
    apply_exact(ordinary, PATCH, SUCCESSOR, BASE, reverse=True)
    print(f"PASS strict apply/reverse {BASE} <-> {SUCCESSOR} and {AFTERIMAGE} <-> {SUCCESSOR}")
    print("PASS 31 confirmed sessions, discarded exchange, callback replay, timed slot recovery, "
          "late and duplicate confirmation, pending revocation, restart, and prior account schema")
    print("PASS fixed origins, both callbacks, S256/state, single use, session restart, "
          "expiry, scoped revocation, two owners, legacy wire/SQLite bytes, and listener cleanup")


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run without Python optimization")
    scratch = ROOT / "verification/local"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="fieldlog-account-check.", dir=scratch) as temporary:
        verify(Path(temporary))
