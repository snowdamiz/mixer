"""Exercise a compiled GeneratedReport executable and the real local SQLite backend."""
from contextlib import closing
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
from threading import Thread
import time

CHUNK = 32768
ACCOUNT = "synthetic-android-queue"
LOOPBACK = """(version 1)(allow default)
(deny network-outbound (remote ip))
(allow network-outbound (remote ip "localhost:*"))"""


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def read_json(path):
    return json.loads(path.read_text())


def tree_digest(root):
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.swift")):
        if path.parent.name == "QueueJourney":
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(f"{relative}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n".encode())
    return digest.hexdigest()


def command(*args):
    return subprocess.check_output(args, text=True, timeout=8).strip()


def main():
    binary, backend_path, root, receipt_path, candidate, sdk, manifest = map(Path, sys.argv[1:8])
    interruption, = sys.argv[8:]
    require(interruption in {"close", "cancel"}, "select close or cancel")
    root.mkdir()
    spec = importlib.util.spec_from_file_location("local_entry_sync", backend_path)
    backend = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = backend
    spec.loader.exec_module(backend)
    backend_sha = hashlib.sha256(backend_path.read_bytes()).hexdigest()
    result = {
        "status": "failed",
        "scope": "macOS host executable with GeneratedReport Swift C ABI and user-scoped local Python/SQLite; Android JNI, UI and devices unexercised",
        "tools": {"swift": command("swift", "--version"),
                  "python": sys.version.split()[0], "sqlite": sqlite3.sqlite_version,
                  "macOS": command("/usr/bin/sw_vers", "-productVersion")},
        "inputs": {"backendSHA256": backend_sha, "generatedReportSwiftTreeSHA256": tree_digest(candidate / "Sources"),
                   "sdkSwiftTreeSHA256": tree_digest(sdk / "Sources"),
                   "generatedReportManifestSHA256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                   "driverSHA256": hashlib.sha256((candidate / "Sources/QueueJourney/QueueJourney.swift").read_bytes()).hexdigest(),
                   "swiftPMPins": read_json(candidate / "Package.resolved")["pins"]},
        "phases": {},
    }

    def run(phase):
        env = {key: value for key, value in os.environ.items()
               if not key.lower().endswith("_proxy") and not key.startswith("FIELDLOG_ENTRY_SYNC_")}
        call = ["/usr/bin/sandbox-exec", "-p", LOOPBACK, str(binary), phase, str(root)]
        completed = subprocess.run(call, timeout=25, text=True, capture_output=True, env=env)
        require(completed.returncode == 0,
                f"{phase} executable exited {completed.returncode}: {completed.stderr.strip()} {completed.stdout.strip()}")

    try:
        run("seed")
        run("offline")
        result["unconfiguredQueueStayedOffline"] = True
        fixture = read_json(root / "fixture.json")
        baseline = read_json(root / "baseline.json")
        event_id, workspace_id, project_id, entry_id, photo_id = (
            fixture[key].lower() for key in ("event", "workspace", "project", "entry", "photo"))
        expected_path = f"/v1/workspaces/{workspace_id}/projects/{project_id}/entries/{event_id}"
        scope = (ACCOUNT, workspace_id, project_id, event_id)
        workspace = root / "app-storage/FieldLog"
        jpeg = (root / "fixture.jpg").read_bytes()
        require(len(jpeg) == fixture["bytes"] and len(jpeg) > 3 * CHUNK, "JPEG fixture size")
        require((workspace / "photos" / (photo_id + ".jpg")).read_bytes() == jpeg, "seeded JPEG bytes")
        result["fixture"] = {**fixture, "jpegSHA256": hashlib.sha256(jpeg).hexdigest(), "dimensions": [640, 480]}
        database = root / "backend.sqlite3"
        token = "synthetic-" + secrets.token_urlsafe(24)
        phase = ""
        faults = []

        def rows():
            with closing(sqlite3.connect(database)) as conn:
                return {
                    "events": conn.execute(
                        "SELECT account_id, workspace_id, project_id, event_id, entry_id, event_json, entry_json FROM entry_events"
                    ).fetchall(),
                    "photos": conn.execute(
                        "SELECT account_id, workspace_id, project_id, event_id, photo_id, jpeg FROM entry_photos"
                    ).fetchall(),
                    "upload": conn.execute(
                        "SELECT account_id, workspace_id, project_id, event_id, entry_id, photo_id, jpeg FROM entry_photo_uploads"
                    ).fetchall(),
                }

        def verify_staged(size):
            observed = rows()
            require(observed == {"events": [], "photos": [],
                                 "upload": [(*scope, entry_id, photo_id, jpeg[:size])]},
                    f"SQLite staged prefix/rows differ at {size} bytes")
            result["phases"][phase]["sqliteAtHold"] = {"events": 0, "photos": 0, "stagedBytes": size}

        def verify_final():
            observed = rows()
            require(observed["upload"] == [], "SQLite left staged upload")
            require(observed["photos"] == [(*scope, photo_id, jpeg)], "SQLite JPEG bytes/identity/row count differ")
            require(len(observed["events"]) == 1, "SQLite event row count differs")
            *key, stored_event, stored_entry = observed["events"][0]
            require(tuple(key) == (*scope, entry_id), "SQLite event scope/entry ID differs")
            require(json.loads(stored_event) == next(x for x in baseline["outbox"] if x["id"] == fixture["event"]),
                    "SQLite event payload differs")
            require(json.loads(stored_entry) == next(x for x in baseline["entries"] if x["id"] == fixture["entry"]),
                    "SQLite entry payload differs")

        def hold(name):
            (root / (name + ".held")).touch(exist_ok=False)
            release = root / (name + ".release")
            until = time.monotonic() + 10
            while not release.exists() and time.monotonic() < until:
                time.sleep(0.01)
            require(release.exists(), f"replay did not release {name}")

        class Controlled(backend.EntrySyncHandler):
            def do_POST(self):
                self.phase = phase
                self.trace = result["phases"][self.phase]["http"]
                try:
                    require(self.path in (expected_path, expected_path + "/photo", expected_path + "/photo/chunks"),
                            "unexpected HTTP scope/path")
                    super().do_POST()
                except Exception as error:
                    faults.append(f"{self.phase}: {error}")
                    self.close_connection = True

            def _read_body(self, maximum):
                body = super()._read_body(maximum)
                if self.path.endswith("/photo/chunks"):
                    offset = json.loads(body)["offset"]
                    self.trace["chunkOffsets"].append(offset)
                    if self.phase == "lost" and offset == 2 * CHUNK:
                        verify_staged(2 * CHUNK)
                        hold("resume-chunk")
                return body

            def send_photo_progress(self, status, receipt):
                offset = receipt["offset"]
                if self.path.endswith("/photo"):
                    self.trace["manifestOffsets"].append(offset)
                elif self.phase == interruption and offset == 2 * CHUNK:
                    verify_staged(2 * CHUNK)
                    hold("second-chunk")
                    self.close_connection = True
                    return
                super().send_photo_progress(status, receipt)

            def send_receipt(self, status, receipt):
                self.trace["finalStatusAfterSQLiteCommit"].append(int(status))
                verify_final()
                if self.phase == "lost" and status == 201:
                    hold("final-receipt")
                    self.trace["droppedFinalReceipt"] = True
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                super().send_receipt(status, receipt)

        with backend.make_server(database, {token: (ACCOUNT, {(workspace_id, project_id)})},
                                 handler_class=Controlled) as server:
            result["loopback"] = {"address": server.server_address[0], "ephemeralPort": server.server_port}
            config = workspace / "entry-sync.local.json"
            config.write_text(json.dumps({"port": server.server_port, "workspaceID": workspace_id,
                                          "projectID": project_id, "token": token}))
            config.chmod(0o600)
            worker = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
            worker.start()
            try:
                for phase in (interruption, "lost", "reconcile"):
                    trace = {"manifestOffsets": [], "chunkOffsets": [], "finalStatusAfterSQLiteCommit": []}
                    result["phases"][phase] = {"http": trace}
                    run(phase)
                    require(not faults, str(faults))
                    result["phases"][phase]["swift"] = read_json(root / (phase + ".json"))
                    if phase == interruption:
                        verify_staged(2 * CHUNK)
                        require(trace == {"manifestOffsets": [0], "chunkOffsets": [0, CHUNK],
                                          "finalStatusAfterSQLiteCommit": []}, f"cancel HTTP: {trace}")
                    elif phase == "lost":
                        verify_final()
                        require(trace == {"manifestOffsets": [2 * CHUNK],
                                          "chunkOffsets": list(range(2 * CHUNK, len(jpeg), CHUNK)),
                                          "finalStatusAfterSQLiteCommit": [201], "droppedFinalReceipt": True},
                                f"lost acknowledgment HTTP: {trace}")
                        inactive_config = config.with_suffix(".disabled")
                        config.rename(inactive_config)
                        try:
                            run("offline")
                            result["reopenedWithoutConfigurationAfterLostAck"] = True
                        finally:
                            inactive_config.rename(config)
                    else:
                        verify_final()
                        require(trace == {"manifestOffsets": [len(jpeg)], "chunkOffsets": [],
                                          "finalStatusAfterSQLiteCommit": [200]}, f"reconcile HTTP: {trace}")
            finally:
                server.shutdown()
                worker.join(timeout=5)
                require(not worker.is_alive(), "loopback listener did not shut down")
        result["cleanup"] = {"loopbackListenerClosed": True, "handlerFaults": faults}
        with socket.socket() as check:
            check.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            check.bind(("127.0.0.1", result["loopback"]["ephemeralPort"]))
        result["cleanup"]["portRebind"] = True
        require(hashlib.sha256(backend_path.read_bytes()).hexdigest() == backend_sha, "backend changed during run")
        result["sqliteFinal"] = {"eventRows": 1, "photoRows": 1, "stagedRows": 0, "exactJPEG": True,
                                 "scopeAndPayloadMatch": True}
        result["status"] = "pass"
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        receipt_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
