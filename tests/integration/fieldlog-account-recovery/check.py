#!/usr/bin/env python3
"""Replay the pinned account checks and test recovery with synthetic loopback accounts."""

import argparse
import base64
from contextlib import closing, contextmanager, nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PIN = "fa6367ab3ccac4cdacc8fe5da39f3c0d0fcc9bb0"
SOURCE = "tests/integration/fieldlog-account"
BACKEND = "Backend/local_entry_sync.py"
BASELINE = "b6debbc45f8ab96360d2d494e376d80ea5f6abf7"
RESULT = "4d487e779c213b387cd2eee89fe0f48033a0b029"
RECOVERY_PATCH = Path(__file__).with_name("fieldlog-local-recovery.patch.b64")
PATCH_SHA256 = "29e4b5af4b06e89027f82367319fbb0ade7a25cd5695096896b3b9c0db09d3f6"
RECOVERY_BEGIN = "/v1/account/recovery/attempts"
RECOVERY_EXCHANGE = "/v1/account/recovery/exchange"


def load_regression(work):
    for name in ("check.py", "fieldlog-local-account.patch.b64",
                 "fieldlog-local-account-confirmation.patch.b64"):
        data = subprocess.check_output(["git", "show", f"{PIN}:{SOURCE}/{name}"],
                                       cwd=ROOT, timeout=10)
        (work / name).write_bytes(data)
    suite = load_from_file(work / "check.py", "pinned_account_check")
    suite.ROOT = ROOT
    return suite


@contextmanager
def isolated_transport(suite):
    listener = suite.listener
    request = suite.request
    account_port = None

    @contextmanager
    def listen(backend, database, *args, **kwargs):
        nonlocal account_port
        if not kwargs.get("local_accounts"):
            with listener(backend, database, *args, **kwargs) as port:
                yield port
            return
        bind = backend._EntrySyncServer.server_bind

        def bind_ephemeral(server):
            assert server.server_address == ("127.0.0.1", 8765)
            server.server_address = ("127.0.0.1", 0)
            bind(server)

        with patch.object(backend._EntrySyncServer, "server_bind", bind_ephemeral):
            with listener(backend, database, *args, **kwargs) as account_port:
                try:
                    yield 8765
                finally:
                    account_port = None

    def send(port, *args, headers=None, **kwargs):
        if port == 8765:
            assert account_port is not None
            headers = dict(headers or {})
            headers.setdefault("Host", "127.0.0.1:8765")
            port = account_port
        return request(port, *args, headers=headers, **kwargs)

    with patch.object(suite, "listener", listen), patch.object(suite, "request", send):
        yield


def compose(suite, work):
    candidate = work / "candidate"
    (candidate / BACKEND).parent.mkdir(parents=True)
    load = suite.load

    def preserve_baseline(directory, name):
        if name == "patched":
            data = (directory / BACKEND).read_bytes()
            (work / "baseline.py").write_bytes(data)
            (candidate / BACKEND).write_bytes(data)
        return load(directory, name)

    baseline_check = work / "baseline-check"
    baseline_check.mkdir()
    with patch.object(suite, "load", side_effect=preserve_baseline):
        suite.verify(baseline_check)
    suite.git(candidate, "init", "-q")
    suite.assert_blob(candidate, BASELINE)
    suite.git(candidate, "add", BACKEND)
    data = base64.b64decode(RECOVERY_PATCH.read_bytes())
    assert hashlib.sha256(data).hexdigest() == PATCH_SHA256
    for reverse, expected in ((False, RESULT), (True, BASELINE), (False, RESULT)):
        options = ["--index", "--whitespace=error-all"]
        if reverse:
            options.append("--reverse")
        suite.git(candidate, "apply", "--check", *options, "-", data=data)
        suite.git(candidate, "apply", *options, "-", data=data)
        suite.assert_blob(candidate, expected)
    print(f"PASS recovery patch apply/reverse {BASELINE} <-> {RESULT}", flush=True)

    backend = load(candidate, "recovery_backend")
    ordinary = work / "ordinary-with-recovery"
    ordinary.mkdir()
    with patch.object(suite, "load",
                      side_effect=lambda folder, name: backend if name == "patched" else load(folder, name)):
        suite.verify(ordinary)
    print("PASS pinned ordinary account and static regression on recovery backend", flush=True)
    return load_from_file(work / "baseline.py", "preserved_baseline"), backend, candidate / BACKEND


def load_from_file(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def begin_recovery(suite, port, platform="ios"):
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
    _, body = suite.request(port, "POST", RECOVERY_BEGIN, 201, payload={
        "platform": platform, "state": state, "challenge": challenge[:-1].decode(),
    })
    url = urlsplit(json.loads(body)["browserURL"])
    assert url.scheme == "http" and url.netloc == "127.0.0.1:8765"
    assert url.path.startswith(RECOVERY_BEGIN + "/") and not url.query and not url.fragment
    return url.path, {"platform": platform, "state": state, "verifier": verifier}


def submit(suite, port, path, code, status, *, origin=None, intent=True, discard=False):
    return suite.request(port, "POST", path, status, discard_body=discard, headers={
        "Origin": suite.ORIGIN if origin is None else origin,
        "Content-Type": "application/x-www-form-urlencoded",
    }, raw=f"recoveryCode={code}" + ("&intent=recover" if intent else ""))


def approve(suite, port, path, pending, code):
    location, body = submit(suite, port, path, code, 303)
    assert not body and code not in location and pending["verifier"] not in location
    url = urlsplit(location)
    assert url.scheme == f"com.fieldlog.dev.{pending['platform']}"
    assert (url.netloc, url.path, url.fragment) == ("account", "/callback", "")
    query = parse_qs(url.query, strict_parsing=True)
    assert set(query) == {"code", "state"} and query["state"] == [pending["state"]]
    callback, = query["code"]
    assert len(callback) == 43
    return dict(pending, code=callback)


def sign_in_callback(suite, port, proof):
    path, pending = suite.begin(port, "ios")
    return suite.callback(port, path, pending, proof, "com.fieldlog.dev.ios")


def operator_issue(source, database, account, status=0):
    result = subprocess.run(
        [sys.executable, "-B", str(source), "provision-recovery", str(database), account],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == status, result.stderr
    code = result.stdout.strip()
    if status == 0:
        assert code.startswith("flr_") and len(code) == 47 and not result.stderr
    else:
        assert not code
    return code


def verify_recovery(suite, baseline, backend, source, work):
    database = work / "recovery.sqlite"
    a, b, wa, wb, project, task, event = (str(uuid4()) for _ in range(7))
    baseline.init_account_database(database)
    old_proof = baseline.provision_local_account(database, a, wa, project)
    other_proof = baseline.provision_local_account(database, b, wb, project)
    with suite.listener(baseline, database, local_accounts=True) as port:
        owner, _ = suite.exchange_token(port, sign_in_callback(suite, port, old_proof), a, wa, project)
        other, other_session = suite.exchange_token(
            port, sign_in_callback(suite, port, other_proof), b, wb, project,
        )
        row, other_row = suite.seed_and_compare(baseline, database, port, [
            (a, wa, owner, {"title": "Saved FieldLog task", "responsible": "A"},
             suite.upload(project, event, b"\xff\xd8\xffsynthetic photo A")),
            (b, wb, other, {"title": "Other task", "responsible": "B"},
             suite.upload(project, event, b"\xff\xd8\xffsynthetic photo B")),
        ], task, project, event)
        old_code = sign_in_callback(suite, port, old_proof)
        old_pending = json.loads(suite.request(
            port, "POST", suite.EXCHANGE, 200, payload=sign_in_callback(suite, port, old_proof),
        )[1])["token"]
    snapshots = suite.snapshot(database)

    # Exercise the actual operator entry point against the existing pinned database.
    operator_issue(source, database, str(uuid4()), status=1)
    issued = operator_issue(source, database, a)
    replacement = secrets.token_urlsafe(32)
    clock = suite.Clock()
    clock.now = int(time.time())
    with patch.object(backend, "time", clock):
        with suite.listener(backend, database, local_accounts=True) as port:
            path, pending = begin_recovery(suite, port)
            _, form = suite.request(port, "GET", path, 200)
            assert b"Recover FieldLog account" in form and b"signs out" in form
            assert b"name=recoveryCode" in form and b"name=intent value=recover" in form
            assert issued.encode() not in form
            suite.request(port, "GET", path, 400, headers={"Host": "localhost:8765"})
            suite.request(port, "GET", path.replace(RECOVERY_BEGIN, suite.BEGIN), 401)
            submit(suite, port, path, issued, 403, origin="null")
            submit(suite, port, path, issued, 400, intent=False)
            submit(suite, port, path, "flr_" + secrets.token_urlsafe(32), 401)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=dict(old_code, newProof=replacement))
            cancelled = approve(suite, port, path, pending, issued)
            fresh_code = backend.provision_local_recovery(database, a)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=dict(cancelled, newProof=replacement))

            # A discarded browser redirect leaves the same operator code usable.
            lost_path, _ = begin_recovery(suite, port)
            submit(suite, port, lost_path, issued, 401)
            submit(suite, port, lost_path, fresh_code, 303, discard=True)
            live_path, live_pending = begin_recovery(suite, port)
            approved = approve(suite, port, live_path, live_pending, fresh_code)
            stale_path, stale_pending = begin_recovery(suite, port)
            stale = approve(suite, port, stale_path, stale_pending, fresh_code)
            suite.request(port, "POST", suite.EXCHANGE, 401, payload=approved)
            for key in ("code", "state", "verifier", "platform"):
                wrong = "android" if key == "platform" else secrets.token_urlsafe(32)
                suite.request(port, "POST", RECOVERY_EXCHANGE, 401,
                              payload=dict(dict(approved, newProof=replacement), **{key: wrong}))
            for unsafe in (old_proof, other_proof, fresh_code):
                suite.request(port, "POST", RECOVERY_EXCHANGE, 400, payload=dict(approved, newProof=unsafe))
            suite.request(port, "GET", row[0], 200, token=owner)

            # Fail the last write after rotation and check that SQLite rolled back the transaction.
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("""
                    CREATE TRIGGER fail_session BEFORE INSERT ON local_sessions
                    BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END
                """)
            exchange = dict(approved, newProof=replacement)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 503, payload=exchange)
            suite.request(port, "GET", row[0], 200, token=owner)
            with closing(sqlite3.connect(database)) as connection, connection:
                connection.execute("DROP TRIGGER fail_session")

            result = json.loads(suite.request(port, "POST", RECOVERY_EXCHANGE, 200, payload=exchange)[1])
            token = result.pop("token")
            metadata = {"accountID": a, "scopes": [{"workspaceID": wa, "projectID": project}]}
            assert result == dict(metadata, expiresAt=clock.now + 60) and len(token) == 43
            suite.request(port, "GET", row[0], 401, token=token)
            for revoked in (owner, old_pending):
                suite.request(port, "GET", suite.SESSION, 401, token=revoked)
                suite.replay(port, row, revoked, 401)
            suite.request(port, "POST", suite.EXCHANGE, 401, payload=old_code)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=exchange)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=dict(stale, newProof=replacement))
            submit(suite, port, begin_recovery(suite, port)[0], fresh_code, 401)
            suite.browser_post(port, suite.begin(port, "ios")[0], old_proof, 401)

        with suite.listener(backend, database, local_accounts=True) as port:
            confirmed = dict(metadata, expiresAt=clock.now + 8 * 60 * 60)
            suite.request(port, "GET", suite.SESSION, 200, token=token, discard_body=True)
            clock.now += 1
            assert json.loads(suite.request(port, "GET", suite.SESSION, 200, token=token)[1]) == confirmed
            suite.replay(port, row, token, 200)
            suite.replay(port, other_row, token, 404)
            assert suite.request(port, "GET", suite.SESSION, 200, token=other)[1] == other_session
            suite.replay(port, other_row, other, 200)

            expiring = backend.provision_local_recovery(database, a)
            clock.now += 15 * 60 - 1
            near_path, near_pending = begin_recovery(suite, port)
            expires = approve(suite, port, near_path, near_pending, expiring)
            clock.now += 1
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=dict(expires, newProof=old_proof))
            submit(suite, port, begin_recovery(suite, port)[0], expiring, 401)

            final_code = backend.provision_local_recovery(database, a)
            final_path, final_pending = begin_recovery(suite, port, "android")
            final_exchange = approve(suite, port, final_path, final_pending, final_code)
            final_proof = secrets.token_urlsafe(32)
            final_exchange["newProof"] = final_proof
            suite.request(port, "POST", RECOVERY_EXCHANGE, 200, payload=final_exchange, discard_body=True)
            suite.request(port, "POST", RECOVERY_EXCHANGE, 401, payload=final_exchange)

        with suite.listener(backend, database, local_accounts=True) as port:
            suite.request(port, "GET", suite.SESSION, 401, token=token)
            suite.browser_post(port, suite.begin(port, "ios")[0], replacement, 401)
            pending = sign_in_callback(suite, port, final_proof)
            restore = json.loads(suite.request(port, "POST", suite.EXCHANGE, 200, payload=pending)[1])
            bearer = restore.pop("token")
            assert restore == dict(metadata, expiresAt=clock.now + 60)
            assert json.loads(suite.request(port, "GET", suite.SESSION, 200, token=bearer)[1]) == dict(
                metadata, expiresAt=clock.now + 8 * 60 * 60,
            )
            suite.replay(port, row, bearer, 200)

    assert suite.snapshot(database) == snapshots
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT account_id, workspace_id, project_id FROM local_accounts ORDER BY account_id",
        ).fetchall() == sorted([(a, wa, project), (b, wb, project)])
        assert connection.execute("SELECT count(*) FROM local_recovery_codes").fetchone() == (0,)
    for secret in (issued, fresh_code, final_code, old_proof, replacement, final_proof, token, bearer):
        assert secret.encode() not in database.read_bytes()
    print("PASS recovery issuance, browser intent, callback binding, expiry, rollback, rotation, "
          "session confirmation, response loss, account isolation, and saved row equality", flush=True)


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run without Python optimization")
    start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-loopback", action="store_true",
                        help="use an ephemeral test socket while checking the fixed HTTP origin")
    args = parser.parse_args()
    scratch = ROOT / "verification/local"
    scratch.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="fieldlog-account-recovery-check.", dir=scratch) as temporary:
        work = Path(temporary)
        suite = load_regression(work)
        transport = isolated_transport(suite) if args.isolated_loopback else nullcontext()
        with transport:
            baseline, backend, source = compose(suite, work)
            verify_recovery(suite, baseline, backend, source, work)
        used = sum(path.stat().st_size for path in work.rglob("*") if path.is_file())
        assert used < 1024 ** 3
    assert not work.exists()
    print(f"PASS owned listeners closed and scratch removed ({used} bytes, {time.monotonic() - start:.2f} s)")
