#!/usr/bin/env python3
"""Run the Swift account owner against disposable loopback SQLite."""

from contextlib import closing
import importlib.util
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
from uuid import uuid4


def snapshot(database):
    with closing(sqlite3.connect(database)) as connection:
        return (
            connection.execute("SELECT * FROM entry_events ORDER BY 1, 2, 3, 4").fetchall(),
            connection.execute("SELECT * FROM entry_photos ORDER BY 1, 2, 3, 4").fetchall(),
            connection.execute("SELECT * FROM task_heads ORDER BY 1, 2, 3, 4").fetchall(),
            connection.execute("SELECT * FROM task_events ORDER BY 1, 2, 3, 4, 5").fetchall(),
            connection.execute(
                "SELECT account_id, workspace_id, project_id FROM local_accounts ORDER BY 1"
            ).fetchall(),
        )


def main():
    app, binary, scratch = map(lambda value: Path(value).resolve(), sys.argv[1:])
    spec = importlib.util.spec_from_file_location("local_entry_sync", app / "Backend/local_entry_sync.py")
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    spec.loader.exec_module(backend)
    database = scratch / "accounts.sqlite"
    backend.init_account_database(database)
    account, workspace, project, peer, peer_workspace, peer_project, task, event, entry, photo = (
        str(uuid4()) for _ in range(10)
    )
    scope = (account, workspace, project)
    old_proof = backend.provision_local_account(database, *scope)
    backend.provision_local_account(database, peer, peer_workspace, peer_project)
    backend.provision_task(database, *scope, task, {"title": "Synced task", "responsible": "Field worker"})
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("INSERT INTO entry_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (*scope, event, entry, "{}", '{"title":"Existing entry"}'))
        connection.execute("INSERT INTO entry_photos VALUES (?, ?, ?, ?, ?, ?)",
                           (*scope, event, photo, b"\xff\xd8\xff\x00\xff\xd9"))
    fixture = {
        "oldProof": old_proof,
        "recoveryCode": backend.provision_local_recovery(database, account),
        "peerRecoveryCode": backend.provision_local_recovery(database, peer),
        "peerID": peer,
        "peerScope": {"workspaceID": peer_workspace, "projectID": peer_project},
        "taskID": task,
    }
    before = snapshot(database)
    with backend.make_server(database, local_accounts=True) as server:
        listener = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        listener.start()
        try:
            subprocess.run([binary, scratch], input=json.dumps(fixture).encode(), check=True, timeout=65)
        finally:
            server.shutdown()
            listener.join(2)
            assert not listener.is_alive()
    assert snapshot(database) == before, "recovery changed backend data rows or scope IDs"
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", 8765))
    print("PASS backend account/scope, task, entry and photo snapshots and loopback release")


if __name__ == "__main__":
    main()
