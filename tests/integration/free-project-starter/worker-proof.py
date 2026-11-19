#!/usr/bin/env python3
"""Exercise the provisioned worker with a persisted input and no build submission."""
import errno
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
import time

sys.path.insert(0, str(Path(os.environ.get("MIXER_STARTER_WORKER_CODE", "priv/development")).resolve(strict=True)))
from native_artifact_worker import NativeWorker, Refusal, digest, literal, mac, serve


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def send(config, action, request=None):
    body = literal({"worker_id": config["worker_id"], "action": action, "request": request})
    nonce = secrets.token_hex(16)
    packet = literal({"body": body, "nonce": nonce,
                      "mac": mac(config["token"], "request", nonce, body)})
    with socket.create_connection(("127.0.0.1", config["port"]), timeout=2) as connection:
        connection.sendall((packet + "\n").encode())
        with connection.makefile("rb") as stream:
            raw = stream.readline(262_145)
    reply = json.loads(raw)
    check(hmac.compare_digest(reply["mac"], mac(config["token"], "response", nonce, reply["body"])),
          "invalid response authentication")
    return json.loads(reply["body"])


def main():
    startup, pin, db_spec = sys.argv[1:]
    path = Path(startup)
    raw = path.read_bytes()
    check(digest(raw) == pin, "worker startup pin differs")
    config = json.loads(raw)
    spec = json.loads(db_spec)
    state = path.parent / "worker-state"
    build_id = "source-selection-no-build"
    request = {
        "spec": {**spec, "build_id": build_id},
        "ref": {"build_id": build_id, **{
            field: spec[field] for field in ("organization_id", "project_id", "application_id", "platform")
        }},
        "operation_id": secrets.token_hex(32),
        "deadline_ms": time.time_ns() // 1_000_000 + 25_000,
        "guard": {"epoch": 1, "revision": 1, "owner_id": "local-proof",
                  "record_id": "source-selection", "expires_at": time.time_ns() // 1_000_000 + 25_000},
    }
    bad = {**request, "operation_id": secrets.token_hex(32), "spec": {
        **request["spec"], "source": {**spec["source"], "reference": "different-reference"},
    }}
    # The listener and its worker run in this process. Closing the listener and
    # joining its only thread closes their custody, even if this proof fails.
    with ThreadPoolExecutor(max_workers=1) as executor:
        listener = executor.submit(serve, config, state)
        active = False
        try:
            end = time.monotonic() + 4
            while True:
                if listener.done():
                    listener.result()
                    raise RuntimeError("worker exited before query")
                try:
                    reply = send(config, "query", request)
                    active = True
                    break
                except ConnectionRefusedError:
                    if time.monotonic() >= end:
                        raise
                    time.sleep(0.03)
            check(reply == {"status": "absent"}, "worker refused persisted input")
            check(send(config, "query", bad) == {"error": "unavailable"},
                  "worker accepted a different source reference")
        finally:
            if active or not listener.done():
                check(send(config, "shutdown") == {"status": "closed"}, "worker refused shutdown")
            listener.result(timeout=3)

    verifier = NativeWorker(config, state)
    try:
        accepted = verifier.verify(spec)
        check(accepted["cwd"] == config["registration"]["root"], "worker verified the wrong export")
        try:
            verifier.verify(bad["spec"])
        except Refusal:
            pass
        else:
            raise RuntimeError("worker verified the wrong source reference")
    finally:
        verifier.close()
    with sqlite3.connect(state / "operations.sqlite") as ledger:
        rows = ledger.execute("SELECT value FROM operations").fetchall()
    check(len(rows) == 1, "worker stored an unexpected operation")
    operation = json.loads(rows[0][0])
    check(operation["status"] == "absent" and operation["starts"] == 0 and
          operation["binding"]["spec"] == request["spec"], "worker ledger diverged from the source selection")
    with socket.socket() as port:
        check(port.connect_ex(("127.0.0.1", config["port"])) == errno.ECONNREFUSED,
              "worker listener still accepts connections")
    print(literal({"workerId": config["worker_id"], "configurationSha256": pin,
                   "sourceSha256": spec["source"]["sha256"], "status": "absent",
                   "starts": 0, "ledgerMatchesPersistedInput": True, "verifiedRecipe": True,
                   "differentSourceRefused": True, "listenerJoinedAndPortClosed": True}))


if __name__ == "__main__":
    main()
