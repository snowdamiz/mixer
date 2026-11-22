#!/usr/bin/env python3
"""Replay the pinned FieldLog deletion patch with synthetic accounts and isolated loopback."""

import base64
from contextlib import closing
import hashlib
from http.client import RemoteDisconnected
import importlib.util
import json
from pathlib import Path
import secrets
import signal
import sqlite3
import subprocess
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
PIN = "41d1b96fe4a0ddf67b5e7aa0ff4ea1cf473645c1"
RECOVERY = "tests/integration/fieldlog-account-recovery"
INPUT = "4d487e779c213b387cd2eee89fe0f48033a0b029"
RESULT = "535c33c727f8c0c630c444e180a754ec5625edea"
PATCH_SHA256 = "44aab1c0a6083b8495bb4e29777595570decab31760f43280ccb25466f7b6c43"
DELETION = "/v1/account/deletion"
RECEIPTS = "local_account_deletions"
OWNED_TABLES = (
    "local_accounts", "local_sessions", "local_auth_attempts", "local_recovery_codes",
    "task_heads", "task_events", "entry_events", "entry_photos",
)


def load_recovery(work):
    work.mkdir()
    for name in ("check.py", "fieldlog-local-recovery.patch.b64"):
        data = subprocess.check_output(
            ["git", "show", f"{PIN}:{RECOVERY}/{name}"], cwd=ROOT, timeout=10,
        )
        (work / name).write_bytes(data)
    spec = importlib.util.spec_from_file_location("pinned_recovery_check", work / "check.py")
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    recovery.ROOT = ROOT
    return recovery


def apply_deletion(recovery, suite, work):
    candidate = work / "candidate"
    data = base64.b64decode(Path(__file__).with_name("fieldlog-local-account-deletion.patch.b64").read_bytes())
    assert hashlib.sha256(data).hexdigest() == PATCH_SHA256
    suite.assert_blob(candidate, INPUT)
    for reverse, expected in ((False, RESULT), (True, INPUT), (False, RESULT)):
        options = ["--index", "--whitespace=error-all", *(["--reverse"] if reverse else [])]
        suite.git(candidate, "apply", "--check", *options, "-", data=data)
        suite.git(candidate, "apply", *options, "-", data=data)
        suite.assert_blob(candidate, expected)
    source = candidate / recovery.BACKEND
    print(f"PASS deletion patch strict apply/reverse {INPUT} <-> {RESULT}", flush=True)
    return recovery.load_from_file(source, "deletion_backend"), source


def snapshot(database):
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        return {
            table: set(connection.execute(f"SELECT account_id, * FROM {table}"))
            for table in OWNED_TABLES
        } | {RECEIPTS: set(connection.execute(f"SELECT * FROM {RECEIPTS}"))}


def verify_deletion(recovery, suite, previous, backend, work):
    database = work / "deletion.sqlite"
    a, b, wa, wb, project, task, event = (str(uuid4()) for _ in range(7))
    previous.init_account_database(database)
    proof_a = previous.provision_local_account(database, a, wa, project)
    proof_b = previous.provision_local_account(database, b, wb, project)
    recovery_a = previous.provision_local_recovery(database, a)
    recovery_b = previous.provision_local_recovery(database, b)
    key = secrets.token_urlsafe(32)
    scope = {"accountID": a, "workspaceID": wa, "projectID": project}
    request = dict(scope, intent="delete", deletionKey=key)
    receipt = dict(scope, deleted=True)

    static_token = "fixture-static-a"
    with suite.listener(backend, work / "deletion-static.sqlite", {static_token: (a, {(wa, project)})}) as port:
        suite.request(port, "POST", DELETION, 404, token=static_token, payload=request)

    def sign_in(port, proof, account, workspace):
        return suite.exchange_token(
            port, recovery.sign_in_callback(suite, port, proof), account, workspace, project,
        )

    with suite.listener(previous, database, local_accounts=True) as port:
        token_a, session_a = sign_in(port, proof_a, a, wa)
        token_b, session_b = sign_in(port, proof_b, b, wb)
        second_a, _ = sign_in(port, proof_a, a, wa)
        expired_a, _ = sign_in(port, proof_a, a, wa)
        pending_a = json.loads(suite.request(
            port, "POST", suite.EXCHANGE, 200, payload=recovery.sign_in_callback(suite, port, proof_a),
        )[1])["token"]
        callback_a = recovery.sign_in_callback(suite, port, proof_a)
        callback_b = recovery.sign_in_callback(suite, port, proof_b)
        approved_a = recovery.approve(suite, port, *recovery.begin_recovery(suite, port), recovery_a)
        approved_b = recovery.approve(suite, port, *recovery.begin_recovery(suite, port), recovery_b)
        row_a, row_b = suite.seed_and_compare(previous, database, port, [
            (a, wa, token_a, {"title": "Task A", "responsible": "A"},
             suite.upload(project, event, b"\xff\xd8\xffsynthetic photo A")),
            (b, wb, token_b, {"title": "Task B", "responsible": "B"},
             suite.upload(project, event, b"\xff\xd8\xffsynthetic photo B")),
        ], task, project, event)
        suite.request(port, "POST", DELETION, 404, token=token_a, payload=request)

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE local_sessions SET expires_at = 0 WHERE token_digest = ?",
                           (hashlib.sha256(expired_a.encode()).digest(),))

    with suite.listener(backend, database, local_accounts=True) as port:
        before = snapshot(database)
        for table in OWNED_TABLES:
            assert {a, b} <= {row[0] for row in before[table]}, table
        assert not before[RECEIPTS]

        def delete(status, token=token_a, payload=request, **kwargs):
            return suite.request(port, "POST", DELETION, status, token=token, payload=payload, **kwargs)

        suite.request(port, "GET", DELETION, 404, token=token_a)
        suite.request(port, "DELETE", DELETION, 404, token=token_a)
        delete(400, payload={name: value for name, value in request.items() if name != "intent"})
        delete(400, payload=dict(request, intent="sign_out"))
        delete(400, payload=dict(request, accountID=a.upper()))
        delete(400, payload=dict(request, deletionKey="short"))
        delete(413, payload=dict(request, deletionKey="x" * 1024))
        delete(400, headers={"Host": "localhost:8765"})
        for unauthorized in (None, secrets.token_urlsafe(32), pending_a, expired_a):
            delete(401, token=unauthorized)
        delete(404, token=token_b)
        for mismatch in (dict(accountID=b), dict(workspaceID=wb), dict(projectID=str(uuid4()))):
            delete(404, payload=dict(request, **mismatch))
        assert snapshot(database) == before

        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute(f"""
                CREATE TRIGGER fail_deletion BEFORE INSERT ON {RECEIPTS}
                BEGIN SELECT RAISE(ABORT, 'synthetic receipt write failure'); END
            """)
        delete(503)
        assert snapshot(database) == before
        assert suite.request(port, "GET", suite.SESSION, 200, token=token_a)[1] == session_a
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("DROP TRIGGER fail_deletion")

        discarded = []

        def drop_before_write(handler, status, body):
            assert handler.path == DELETION and status == 200 and body == receipt
            discarded.append(True)
            handler.close_connection = True

        with patch.object(backend.EntrySyncHandler, "send_receipt", drop_before_write):
            try:
                delete(200)
            except RemoteDisconnected:
                pass
            else:
                raise AssertionError("client unexpectedly received the deletion response")
        assert discarded == [True]
        after = snapshot(database)
        for table in OWNED_TABLES:
            assert after[table] == {row for row in before[table] if row[0] != a}, table
        assert len(after[RECEIPTS]) == 1
        assert all(len(digest) == 32 for digest in next(iter(after[RECEIPTS])))

    with suite.listener(backend, database, local_accounts=True) as port:
        assert json.loads(delete(200)[1]) == receipt
        for wrong_token in (None, second_a, token_b):
            delete(401, token=wrong_token)
        for changed in (dict(accountID=b), dict(workspaceID=wb), dict(projectID=str(uuid4())),
                        dict(deletionKey=secrets.token_urlsafe(32))):
            delete(401, payload=dict(request, **changed))
        for revoked in (token_a, second_a, expired_a, pending_a):
            suite.request(port, "GET", suite.SESSION, 401, token=revoked)
            suite.replay(port, row_a, revoked, 401)
        suite.request(port, "DELETE", suite.SESSION, 401, token=token_a)
        suite.request(port, "POST", suite.EXCHANGE, 401, payload=callback_a)
        fresh_proof = secrets.token_urlsafe(32)
        suite.request(port, "POST", recovery.RECOVERY_EXCHANGE, 401,
                      payload=dict(approved_a, newProof=fresh_proof))
        suite.browser_post(port, suite.begin(port, "ios")[0], proof_a, 401)
        recovery.submit(suite, port, recovery.begin_recovery(suite, port)[0], recovery_a, 401)
        assert suite.request(port, "GET", suite.SESSION, 200, token=token_b)[1] == session_b
        suite.replay(port, row_b, token_b, 200)
        replayed = snapshot(database)
        assert replayed[RECEIPTS] == after[RECEIPTS]
        for table in OWNED_TABLES:
            assert {row for row in replayed[table] if row[0] is not None} == after[table], table
        suite.exchange_token(port, callback_b, b, wb, project)
        suite.request(port, "POST", recovery.RECOVERY_EXCHANGE, 200,
                      payload=dict(approved_b, newProof=fresh_proof))

        reprovisioned = backend.provision_local_account(database, a, wa, project)
        new_token, new_session = sign_in(port, reprovisioned, a, wa)
        delete(401, token=new_token)
        assert json.loads(delete(200)[1]) == receipt
        assert suite.request(port, "GET", suite.SESSION, 200, token=new_token)[1] == new_session

    for secret in (proof_a, recovery_a, token_a, pending_a, key):
        assert secret.encode() not in database.read_bytes()
    print("PASS explicit intent, confirmed account/scope, transactional rollback, scoped erasure, "
          "other account equality, lost response, restart, receipt-only replay and reprovisioning",
          flush=True)


def run(work):
    recovery = load_recovery(work / "recovery-input")
    suite = recovery.load_regression(work)
    with recovery.isolated_transport(suite):
        ordinary, recovered, recovered_source = recovery.compose(suite, work)
        recovery.verify_recovery(suite, ordinary, recovered, recovered_source, work / "baseline-check")
        backend, source = apply_deletion(recovery, suite, work)
        regression = work / "ordinary-with-deletion"
        regression.mkdir()
        load = suite.load
        with patch.object(suite, "load",
                          side_effect=lambda folder, name: backend if name == "patched" else load(folder, name)):
            suite.verify(regression)
        recovery.verify_recovery(suite, recovered, backend, source, regression)
        print("PASS old sign-in, sign-out, confirmation, static sync and recovery on deletion backend",
              flush=True)
        verify_deletion(recovery, suite, recovered, backend, work)


def deadline(_signal, _frame):
    raise TimeoutError("FieldLog deletion replay exceeded its deadline")


if __name__ == "__main__":
    if not __debug__:
        raise SystemExit("Run without Python optimization")
    start = time.monotonic()
    scratch = ROOT / "verification/local"
    scratch.mkdir(exist_ok=True)
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(660)
    try:
        with TemporaryDirectory(prefix="fieldlog-account-deletion-check.", dir=scratch) as temporary:
            work = Path(temporary)
            run(work)
            used = sum(path.stat().st_size for path in work.rglob("*") if path.is_file())
            assert used < 1024 ** 3
        assert not work.exists()
    finally:
        signal.alarm(0)
    print(f"PASS owned listeners closed and scratch removed ({used} bytes, {time.monotonic() - start:.2f} s)")
