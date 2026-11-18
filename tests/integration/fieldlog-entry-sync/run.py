#!/usr/bin/env python3
"""Run the FieldLog repository/HTTP journey on macOS from a local pinned Git object."""

import argparse
import base64
from contextlib import closing, contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import importlib.util
import io
from pathlib import Path
import json
import os
import platform
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from threading import Thread
import time
import uuid

DELIVERY = Path(__file__).resolve().parent
PIN = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
TREE = "1b62520f35c7e57a01b568291078686574f627c4"
PATCH_DIR = DELIVERY.parents[2] / "verification" / "fieldlog-entry-sync"
PATCHES = [
    PATCH_DIR / "fieldlog-552559d2-entry-sync.patch",
    PATCH_DIR / "fieldlog-552559d2-local-backend.patch",
]
MANIFEST = """// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "FieldLogJourney",
    platforms: [.macOS(.v14)],
    targets: [
        .target(name: "FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
        .executableTarget(name: "FieldLogJourney", dependencies: ["FieldLogModels", "FieldLogStorage"]),
        .testTarget(name: "FieldLogTests", dependencies: ["FieldLogModels", "FieldLogStorage"]),
    ],
    swiftLanguageModes: [.v6]
)
"""


def run(*argv, cwd=None, env=None, timeout=90):
    process = subprocess.run(
        argv, cwd=cwd, env=env, timeout=timeout, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if process.returncode:
        raise RuntimeError(f"{argv[0]} exited {process.returncode}\n{process.stdout.decode(errors='replace')}")
    return process.stdout


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def prepare(checkout, root):
    actual = run("git", "-C", checkout, "rev-parse", f"{PIN}^{{tree}}").decode().strip()
    require(actual == TREE, "Unexpected pinned FieldLog tree.")
    package = root / "package"
    package.mkdir()
    archive = run(
        "git", "-C", checkout, "archive", PIN,
        "Sources/FieldLogModels", "Sources/FieldLogStorage", "Tests/FieldLogTests/FieldLogTests.swift",
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(package, filter="data")
    run("git", "init", "--quiet", cwd=package)
    run("git", "apply", "--check", *PATCHES, cwd=package)
    run("git", "apply", *PATCHES, cwd=package)
    (package / "Package.swift").write_text(MANIFEST)
    target = package / "Sources" / "FieldLogJourney"
    target.mkdir()
    shutil.copyfile(DELIVERY / "Journey.swift", target / "Journey.swift")
    env = dict(os.environ)
    env.update(
        TMPDIR=str(root / "tmp"),
        CLANG_MODULE_CACHE_PATH=str(root / "clang-cache"),
        SWIFT_MODULE_CACHE_PATH=str(root / "swift-module-cache"),
    )
    (root / "tmp").mkdir()
    flags = (
        "--scratch-path", root / "build",
        "--cache-path", root / "cache",
        "--config-path", root / "config",
        "--security-path", root / "security",
        "--disable-dependency-cache",
    )
    test = run("/usr/bin/swift", "test", *flags, cwd=package, env=env).decode()
    summary = [line for line in test.splitlines() if "Test run with " in line and "passed" in line]
    require(len(summary) == 1, "Did not observe the pinned repository regression suite run.")
    run("/usr/bin/swift", "build", *flags, "--product", "FieldLogJourney", cwd=package, env=env)
    binaries = run(
        "/usr/bin/swift", "build", *flags, "--show-bin-path", cwd=package, env=env,
    ).decode().strip()
    return Path(binaries) / "FieldLogJourney", env, summary[0]


def persisted(database):
    with closing(sqlite3.connect(database)) as connection:
        counts = [
            connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("entry_events", "entry_photos")
        ]
        rows = connection.execute("""
            SELECT account_id, workspace_id, project_id, event_id, entry_id,
                   event_json, entry_json, photo_id, jpeg
            FROM entry_events JOIN entry_photos USING (account_id, workspace_id, project_id, event_id)
        """).fetchall()
        require(connection.execute("PRAGMA foreign_key_check").fetchall() == [], "Photo link lost.")
    return counts, rows


@contextmanager
def listener(make_server, database, accounts, handler):
    with make_server(database, accounts, handler_class=handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield server.server_port
        finally:
            server.shutdown()
            thread.join(timeout=3)
            require(not thread.is_alive(), "The owned server thread failed to return.")


def exercise(binary, env, root):
    source = root / "package" / "Backend" / "local_entry_sync.py"
    spec = importlib.util.spec_from_file_location("fieldlog_local_backend", source)
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    database = root / "backend.sqlite3"
    offline = run(binary, "offline", root, env=env, timeout=20).decode().strip()
    require(not database.exists(), "Backend should not have existed in the offline phase.")
    fixture = {key: value.lower() for key, value in json.loads((root / "fixture.json").read_bytes()).items()}
    local_jpeg = (root / "workspace" / "photos" / f"{fixture['photo']}.jpg").read_bytes()
    require(len(local_jpeg) > 48 * 1024, "The JPEG should exercise a realistic request size.")
    workspace_json = json.loads((root / "workspace" / "workspace.json").read_bytes())
    offline_event = next(event for event in workspace_json["outbox"] if event["id"].lower() == fixture["event"])
    offline_entry = next(entry for entry in workspace_json["entries"] if entry["id"].lower() == fixture["entry"])
    owner_token, other_token, invalid_token = (secrets.token_urlsafe(32) for _ in range(3))
    accounts = {
        owner_token: ("synthetic-owner", {(fixture["workspace"], fixture["project"])}),
        other_token: ("synthetic-other", {(str(uuid.uuid4()), str(uuid.uuid4()))}),
    }
    success_statuses, responses, after_commit, cancelled_replay = [], [], [], []

    class InterruptedReceipt(backend.EntrySyncHandler):
        def _send_json(self, status, body):
            responses.append(int(status))
            super()._send_json(status, body)

        def send_receipt(self, status, receipt):
            success_statuses.append(int(status))
            if len(success_statuses) == 1:
                # Query via a second SQLite connection before writing any response.
                after_commit.append(persisted(database))
                data = json.dumps(receipt).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(data[:12])
                self.close_connection = True
                return
            if len(success_statuses) == 2:
                receipt = dict(receipt, photoID=str(uuid.uuid4()))
            if len(success_statuses) == 3:
                require(persisted(database) == after_commit[0], "Cancellation control saw changed records.")
                (root / "cancel-ready").touch()
                deadline = time.monotonic() + 5
                while not (root / "cancel-returned").exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                cancelled_replay.append((root / "cancel-returned").exists())
                self.close_connection = True
                return
            super().send_receipt(status, receipt)

    env.update(
        FIELDLOG_TEST_OWNER_TOKEN=owner_token,
        FIELDLOG_TEST_OTHER_TOKEN=other_token,
        FIELDLOG_TEST_INVALID_TOKEN=invalid_token,
    )
    with listener(backend.make_server, database, accounts, InterruptedReceipt) as port:
        env["FIELDLOG_TEST_PORT"] = str(port)
        online = run(binary, "online", root, env=env, timeout=35).decode().strip()
        require(success_statuses == [201, 200, 200, 200], "Unexpected initial or retry server outcome.")
        require(responses == [401, 404, 404, 200, 200], "Unexpected authorization or local scope traffic.")
        require(cancelled_replay == [True], "The replay returned cancellation before the server released it.")
        final = persisted(database)
        require(final[0] == [1, 1] and after_commit == [final],
                "Retry changed the committed event or its single linked photo.")
        account, workspace, project, event, entry, event_json, entry_json, photo, jpeg = final[1][0]
        require(
            (account, workspace, project, event, entry, photo)
            == ("synthetic-owner", *(fixture[key] for key in ("workspace", "project", "event", "entry", "photo"))),
            "Stored record identity was not the original event, entry or photo.",
        )
        require(jpeg == local_jpeg, "The persisted JPEG differs from the exact offline bytes.")
        saved_event, saved_entry = json.loads(event_json), json.loads(entry_json)
        require(saved_event == offline_event, "Remote event metadata changed.")
        require(saved_entry == offline_entry, "Remote entry fields changed.")

        def replay_with(entry):
            body = {
                "event": saved_event,
                "entry": entry,
                "photo": {"id": photo.upper(), "jpeg": base64.b64encode(jpeg).decode()},
            }
            with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
                client.request(
                    "POST", f"/v1/workspaces/{workspace}/projects/{project}/entries/{event}",
                    json.dumps(body).encode(),
                    {"Content-Type": "application/json", "Authorization": f"Bearer {owner_token}"},
                )
                with client.getresponse() as response:
                    response.read()
                    return response.status

        require(replay_with(dict(saved_entry, note="Divergent replay")) == 409,
                "Divergent replay did not return 409.")
        # U+001C is valid in the app. U+200B alone is blank according to Foundation.
        require(replay_with(dict(saved_entry, title="\u001c")) == 409, "Valid legacy title was rejected.")
        require(replay_with(dict(saved_entry, title="\u200b")) == 400, "Blank title parsed as valid.")
        require(persisted(database) == final, "Rejected or divergent replays changed remote records.")

    with socket.socket() as reuse:
        reuse.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        reuse.bind(("127.0.0.1", port))
    return {
        "output": [offline, *online.splitlines(), "post-commit SQLite readback, divergent replay, and legacy title validation passed"],
        "status": "passed",
        "loopbackHTTP": {"initialAfterCommit": 201, "lostResponseBytes": 12, "replays": [200, 200, 200],
                         "cancelledBeforeSendAndAfterServerReadback": True,
                         "invalidReceiptRejected": True, "denied": [401, 404, 404], "divergentReplay": 409},
        "persistedBeforeResponseAndAfterRetry": {"events": 1, "photos": 1, "photoBytes": len(jpeg),
                                                "photoSHA256": digest(jpeg), "stableEvent": event},
        "cleanup": {"listenerClosed": True, "portRebound": True},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fieldlog_checkout", type=Path, help="local Git checkout containing the pinned object")
    parser.add_argument("--receipt", type=Path, help="optional path for the compact JSON receipt")
    args = parser.parse_args()
    require(platform.system() == "Darwin", "This root test uses macOS to encode the synthetic JPEGs.")
    scratch = Path(tempfile.mkdtemp(prefix="fieldlog-entry-sync-"))
    try:
        binary, env, legacy_tests = prepare(args.fieldlog_checkout.resolve(), scratch)
        result = exercise(binary, env, scratch)
    except BaseException:
        print(f"FieldLog sync replay stopped; retained {scratch}", file=sys.stderr)
        raise
    shutil.rmtree(scratch)
    require(not scratch.exists(), "Owned test scratch was not removed.")
    result["cleanup"]["scratchRemoved"] = True
    result.update(
        recordedAt=datetime.now(timezone.utc).isoformat(),
        fieldlogRevision=PIN,
        fieldlogTree=TREE,
        mixerCapabilityRuntimeExercised=False,
        sourceSHA256={
            path.name: digest(path.read_bytes())
            for path in [*PATCHES, DELIVERY / "Journey.swift", Path(__file__)]
        },
        tools={
            "Swift": run("/usr/bin/swift", "--version").decode().strip(),
            "Python": platform.python_version(),
            "SQLite": sqlite3.sqlite_version,
            "macOSSDK": run("/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-version").decode().strip(),
            "Git": run("git", "--version").decode().strip(),
            "macOS": platform.mac_ver()[0],
            "arch": platform.machine(),
        },
        commands=["swift test", "swift build --product FieldLogJourney",
                  "FieldLogJourney offline <owned-directory>", "FieldLogJourney online <owned-directory>"],
        baselineTests=legacy_tests,
        scope="Mac app-model and repository run through real loopback HTTP and dedicated SQLite. "
              "One JPEG per saved entry, provisioned owner scopes and synthetic tokens. "
              "Mobile UI, Mixer guest capability routing, TLS, sign-in and multi-photo sync require separate runs or implementation.",
        paymentServiceOrCredentialsRequired=False,
    )
    output = json.dumps(result, indent=2) + "\n"
    if args.receipt:
        with args.receipt.open("x") as file:
            file.write(output)
    print(output, end="")


if __name__ == "__main__":
    main()
