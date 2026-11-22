#!/usr/bin/env python3
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import uuid


app, binary, scratch = map(lambda value: Path(value).resolve(), sys.argv[1:])
spec = importlib.util.spec_from_file_location("local_entry_sync", app / "Backend/local_entry_sync.py")
backend = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = backend
spec.loader.exec_module(backend)
database = scratch / "accounts.sqlite"
backend.init_account_database(database)
accounts = [tuple(str(uuid.uuid4()) for _ in range(3)) for _ in range(2)]
proofs = [backend.provision_local_account(database, *identity) for identity in accounts]
task = str(uuid.uuid4())
backend.provision_task(database, *accounts[0], task, {"title": "Synced task", "responsible": "Field worker"})
with backend.make_server(database, local_accounts=True) as server:
    listener = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    listener.start()
    try:
        subprocess.run([binary, scratch], input=json.dumps([*proofs, task]).encode(), check=True, timeout=45)
    finally:
        server.shutdown()
        listener.join(2)
        assert not listener.is_alive()
with socket.socket() as probe:
    probe.settimeout(1)
    assert probe.connect_ex(("127.0.0.1", 8765)) != 0
