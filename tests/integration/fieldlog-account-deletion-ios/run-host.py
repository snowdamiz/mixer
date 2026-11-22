#!/usr/bin/env python3
"""Drive the Swift owner through independent process launches on disposable loopback SQLite."""

from contextlib import closing, contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
from unittest.mock import patch
from uuid import uuid4


TABLES = (
    "local_accounts", "local_sessions", "local_recovery_codes",
    "task_heads", "task_events", "entry_events", "entry_photos",
)
PORT = 8765


def require_free_port(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def verify(backend, binary, scratch, scenario):
    root = scratch / scenario
    root.mkdir(mode=0o700)
    database = root / "account.sqlite"
    backend.init_account_database(database)
    target, peer = [tuple(str(uuid4()) for _ in range(3)) for _ in range(2)]
    proof, peer_proof = [backend.provision_local_account(database, *scope) for scope in (target, peer)]
    recovery = backend.provision_local_recovery(database, target[0])
    backend.provision_local_recovery(database, peer[0])
    tasks = []
    for scope in (target, peer):
        task, event, entry, photo = (str(uuid4()) for _ in range(4))
        tasks.append(task)
        backend.provision_task(database, *scope, task, {"title": "Disposable task", "responsible": "Synthetic"})
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("INSERT INTO entry_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (*scope, event, entry, "{}", "{}"))
            connection.execute("INSERT INTO entry_photos VALUES (?, ?, ?, ?, ?, ?)",
                               (*scope, event, photo, b"\xff\xd8\xffsynthetic photo"))

    def binding(scope):
        account, workspace, project = scope
        return {"accountID": account, "scope": {"workspaceID": workspace, "projectID": project}}

    fixture = json.dumps({"target": binding(target), "peer": binding(peer), "proof": proof,
                          "peerProof": peer_proof, "recoveryCode": recovery, "taskID": tasks[0]}).encode()

    port = 0

    def phase(name):
        subprocess.run([binary, root, name, str(port)], input=fixture, check=True, timeout=25)

    def snapshot(scope, tables=TABLES):
        with closing(sqlite3.connect(database)) as connection:
            return [connection.execute(f"SELECT * FROM {table} WHERE account_id = ? ORDER BY 1",
                                       (scope[0],)).fetchall() for table in tables]

    def receipt_count():
        with closing(sqlite3.connect(database)) as connection:
            return connection.execute("SELECT count(*) FROM local_account_deletions").fetchone()[0]

    observed = []
    dropped = []
    exchanged_states = []
    read = backend.EntrySyncHandler._auth_json
    read_body = backend.EntrySyncHandler._read_body

    def capture_body(handler, *args, **kwargs):
        body = read_body(handler, *args, **kwargs)
        if handler.path == "/v1/account/deletion":
            handler.fixture_body_digest = hashlib.sha256(body).digest()
        return body

    def trace(handler, *keys):
        value = read(handler, *keys)
        if handler.path == "/v1/auth/exchange":
            exchanged_states.append(value["state"])
        if handler.path == "/v1/account/deletion":
            journal = json.loads((root / "credentials.json").read_bytes())["deletion"]["_0"]
            assert journal["target"]["accountID"].lower() == target[0]
            assert journal["phase"]["pending"]["key"] == value["deletionKey"]
            assert handler.headers["Authorization"] == "Bearer " + journal["phase"]["pending"]["bearer"]
            assert tuple(value[key] for key in ("accountID", "workspaceID", "projectID")) == target
            observed.append((hashlib.sha256(handler.headers["Authorization"].encode()).digest(),
                             handler.fixture_body_digest))
        return value

    def drop(handler, status, value):
        assert handler.path == "/v1/account/deletion" and status == 200 and value["deleted"]
        assert receipt_count() == 1
        dropped.append(True)
        handler.close_connection = True

    def mismatch(handler):
        assert handler._auth_json("intent", "accountID", "workspaceID", "projectID", "deletionKey")
        handler.send_receipt(200, {"deleted": True, "accountID": peer[0],
                                  "workspaceID": target[1], "projectID": target[2]})

    @contextmanager
    def listener():
        nonlocal port
        bind = backend._EntrySyncServer.server_bind

        def bind_ephemeral(server):
            assert server.server_address == ("127.0.0.1", PORT)
            server.server_address = ("127.0.0.1", 0)
            bind(server)

        with patch.object(backend._EntrySyncServer, "server_bind", bind_ephemeral):
            with backend.make_server(database, local_accounts=True) as server:
                port = server.server_port
                assert port != PORT
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
                thread.start()
                try:
                    yield
                finally:
                    server.shutdown()
                    thread.join(timeout=2)
                    assert not thread.is_alive()
        require_free_port(port)
        port = 0

    peer_before = snapshot(peer)
    with (patch.object(backend.EntrySyncHandler, "_auth_json", trace),
          patch.object(backend.EntrySyncHandler, "_read_body", capture_body)):
        if scenario == "normal":
            with listener():
                phase("normal")
            assert len(observed) == 1
        elif scenario == "lost":
            with listener(), patch.object(backend.EntrySyncHandler, "send_receipt", drop):
                phase("lost")
            assert dropped == [True] and receipt_count() == 1 and not any(snapshot(target))
            with listener(), patch.object(backend.EntrySyncHandler, "_handle_deletion", mismatch):
                phase("mismatch")
            with listener():
                phase("receipt-write")
            with listener():
                phase("retry")
            assert len(observed) == 4 and all(request == observed[0] for request in observed)
            phase("cleanup")
            phase("clear")
        elif scenario in ("reauthorize", "reauthorize-callback-first"):
            with listener():
                phase("stage")
                with closing(sqlite3.connect(database)) as connection, connection:
                    connection.execute("UPDATE local_sessions SET expires_at = 0 WHERE account_id = ?", (target[0],))
                phase(scenario)
            assert len(exchanged_states) == len(set(exchanged_states)) == 3
            assert len(observed) == 2
            assert all(old != new for old, new in zip(*observed))
        elif scenario == "superseded":
            with listener():
                phase("superseded")
            assert len(observed) == 1
        elif scenario == "regression":
            with listener():
                phase("regression")
            assert receipt_count() == 0 and observed == []
            assert snapshot(peer) == peer_before
            return
        else:
            raise AssertionError(scenario)
    assert receipt_count() == 1 and not any(snapshot(target))
    unchanged_peer_tables = tuple(table for table in TABLES if table != "local_sessions")
    assert snapshot(peer, unchanged_peer_tables) == [
        rows for table, rows in zip(TABLES, peer_before) if table != "local_sessions"
    ]
    if scenario == "superseded":
        assert json.loads((root / "credentials.json").read_bytes()) == json.loads(
            (root / "peer-credentials.json").read_bytes()
        )
    else:
        assert not (root / "credentials.json").exists()


def main():
    source, binary, scratch = [Path(argument).resolve(strict=True) for argument in sys.argv[1:]]
    spec = importlib.util.spec_from_file_location("deletion_backend", source)
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    spec.loader.exec_module(backend)
    for scenario in ("normal", "lost", "reauthorize", "reauthorize-callback-first",
                     "superseded", "regression"):
        verify(backend, binary, scratch, scenario)
    print("PASS owned loopback port released, SQLite scope and receipt checks complete")


if __name__ == "__main__":
    main()
