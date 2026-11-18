#!/usr/bin/env python3
"""Replay the FieldLog On device queue against the committed local backend."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hmac
import http.client
import json
import os
from pathlib import Path
import plistlib
import secrets
import shutil
import subprocess
import sys
from threading import Event, Lock
import time
from uuid import UUID


TEST_CASE = "FieldLogUITests/EntrySyncResumeUITests/testCancelAndResumeSelectedJPEG"
APP_BUNDLE = "dev.mixer.fieldlog"
READINESS_ROUTE = "/_fixture/second-chunk"


def native_test_spec(products):
    runs = sorted(path for path in products.glob("*.xctestrun")
                  if path.name != "FieldLog-local-resume.xctestrun")
    if len(runs) != 1:
        raise RuntimeError("Expected one generated FieldLog XCTest run.")
    document = plistlib.loads(runs[0].read_bytes())
    if "TestConfigurations" in document:
        targets = [target for configuration in document["TestConfigurations"]
                   if configuration.get("IsEnabled", True) for target in configuration["TestTargets"]
                   if target.get("IsEnabled", True)]
    else:
        targets = [document.get("FieldLogUITests", {})]
    matches = [target for target in targets if target.get("BlueprintName") == "FieldLogUITests"
               and target.get("IsUITestBundle") is True]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one enabled FieldLog UI XCTest target.")
    target, = matches
    paths = {}
    for key in ("UITargetAppPath", "TestHostPath", "TestBundlePath"):
        relative = target[key].removeprefix("__TESTROOT__/")
        host = paths.get("TestHostPath")
        if relative.startswith("__TESTHOST__/") and host:
            resolved = host / relative.removeprefix("__TESTHOST__/")
        else:
            resolved = products / relative
        resolved = resolved.resolve(strict=True)
        if not resolved.is_relative_to(products) or not resolved.is_dir():
            raise RuntimeError(f"Unexpected {key} in the generated FieldLog XCTest run.")
        paths[key] = resolved
    app_info = plistlib.loads((paths["UITargetAppPath"] / "Info.plist").read_bytes())
    if (app_info.get("CFBundleIdentifier") != APP_BUNDLE or
        paths["UITargetAppPath"].name != "FieldLog.app" or
        paths["TestBundlePath"].name != "FieldLogUITests.xctest"):
        raise RuntimeError("Unexpected FieldLog app or test bundle identity.")
    return runs[0], document, target, paths


def app_container(public, simulator):
    container = Path(public.run(
        "xcrun", "simctl", "get_app_container", simulator, APP_BUNDLE, "data", timeout=15,
    ).decode().strip()).resolve(strict=True)
    public.require(container.parts[-5:-1] == ("data", "Containers", "Data", "Application") and
                   container.parents[4].name.upper() == simulator,
                   "FieldLog app data is outside the selected Simulator.")
    return container


def run_native(public, scratch, simulator, env, workspace, result):
    products = scratch / "derived/Build/Products"
    _, document, target, _ = native_test_spec(products)
    container = app_container(public, simulator)
    support = container / "Library/Application Support"
    support.mkdir(parents=True, exist_ok=True)
    seeded = support / workspace.name
    public.require(not seeded.exists() and not seeded.is_symlink(), "The target workspace must be absent.")
    target.setdefault("EnvironmentVariables", {}).update(env)
    private_run = products / "FieldLog-local-resume.xctestrun"
    with private_run.open("xb") as stream:
        plistlib.dump(document, stream)
    retain = False
    marker = ".queue-replay-" + secrets.token_hex(16)
    try:
        shutil.copytree(workspace, seeded)
        (seeded / marker).touch(exist_ok=False)
        try:
            output = public.run(
                "xcodebuild", "test-without-building", "-xctestrun", private_run,
                "-destination", f"platform=iOS Simulator,id={simulator}",
                "-parallel-testing-enabled", "NO", "-only-testing:" + TEST_CASE,
                "-test-timeouts-enabled", "YES", "-maximum-test-execution-time-allowance", "90",
                "-resultBundlePath", scratch / "native.xcresult", cwd=scratch,
                env=os.environ | {"TMPDIR": str(scratch / "tmp") + "/"}, timeout=180,
            ).decode(errors="replace")
        except (public.UnknownCustody, subprocess.TimeoutExpired):
            retain = True
            raise public.UnknownCustody(f"Native custody requires root review. Retained {private_run} and {seeded}.") from None
        except RuntimeError as error:
            (scratch / "native.log").write_text(str(error).replace(env["FIELDLOG_ENTRY_SYNC_TOKEN"], "[redacted]"))
            raise RuntimeError("Native XCTest command failed. See native.log.") from None
        (scratch / "native.log").write_text(output.replace(env["FIELDLOG_ENTRY_SYNC_TOKEN"], "[redacted]"))
        public.require("** TEST EXECUTE SUCCEEDED **" in output, "Missing native XCTest success. See native.log.")
        current = app_container(public, simulator)
        result["native"] = {"exitCode": 0, "case": TEST_CASE, "simulator": simulator,
                            "containerBefore": container.name, "containerAfter": current.name}
        seeded = current / "Library/Application Support" / workspace.name
        public.require((seeded / marker).is_file(), "The current app container does not contain this run's seed.")
        return snapshot(seeded)
    finally:
        if not retain:
            private_run.unlink()
            if (seeded / marker).is_file():
                shutil.rmtree(seeded)


def snapshot(workspace):
    return (json.loads((workspace / "workspace.json").read_bytes()),
            {photo.name: photo.read_bytes() for photo in (workspace / "photos").iterdir()})


def check_readiness(port, token, expected):
    with closing(http.client.HTTPConnection("127.0.0.1", port, timeout=3)) as client:
        client.request("GET", READINESS_ROUTE, headers={"Authorization": f"Bearer {token}"})
        with client.getresponse() as response:
            if response.status != expected or response.read():
                raise RuntimeError(f"Unexpected fixture readiness response {response.status}, expected {expected}.")


def exercise(public, scratch, root, simulator, late, result, token):
    require = public.require
    chunk_bytes = public.CHUNK_BYTES
    binary = scratch / "host-build/debug/QueueJourney"
    backend = public.load_module("fieldlog_local_backend", scratch / "app/Backend/local_entry_sync.py")
    workspace = root / "FieldLogLocalEntrySync"
    database = root / "backend.sqlite3"
    env = {key: value for key, value in os.environ.items() if not key.startswith("FIELDLOG_ENTRY_SYNC_")}
    result["swift"]["offline"] = public.run(binary, "offline", root, env=env).decode().strip()
    fixture = json.loads((root / "fixture.json").read_bytes())
    ids = {key: str(UUID(fixture[key])) for key in ("workspace", "project", "event", "entry", "photo", "otherEvent")}
    initial, original_photos = snapshot(workspace)
    jpeg = original_photos[ids["photo"] + ".jpg"]
    require(len(jpeg) == fixture["photoBytes"] and len(jpeg) > 3 * chunk_bytes and jpeg.startswith(b"\xff\xd8\xff"),
            "Expected an ordinary saved JPEG spanning at least four chunks.")
    key = (public.ACCOUNT, ids["workspace"], ids["project"], ids["event"])
    saved_event, = [item for item in initial["outbox"] if str(UUID(item["id"])) == ids["event"]]
    saved_entry, = [item for item in initial["entries"] if str(UUID(item["id"])) == ids["entry"]]
    manifest_seen = Event()
    second_ready = Event()
    original_chunk_committed = Event()
    next_resume = Event()
    pause_again = not simulator and not late
    requests = {"manifest": [], "chunk": [], "receipt": [], "statuses": []}
    result["http"] = requests
    lock = Lock()
    raw_chunks = {}
    chunk_receipts = {}
    chunks = 0
    hold_seconds = 35 if simulator else 12

    def verify_stage(offset):
        events, photos, stages = public.read_database(database)
        require(not events and not photos and len(stages) == 1 and
                stages[0][:5] == (*key, ids["entry"]) and stages[0][7] == ids["photo"] and
                stages[0][-1] == jpeg[:offset], f"SQLite stage did not match {offset} bytes.")
        return events, photos, stages

    def wait_marker(name):
        deadline = time.monotonic() + 4
        while not (root / name).is_file():
            require(time.monotonic() < deadline, f"The SwiftUI row did not observe {name}.")
            time.sleep(0.01)

    class InterruptedTransfer(backend.EntrySyncHandler):
        def do_GET(self):
            if self.path != READINESS_ROUTE:
                status = 404
            elif not hmac.compare_digest(self.headers.get("Authorization", "").encode(), b"Bearer " + token.encode()):
                status = 401
            else:
                status = 204 if second_ready.is_set() else 425
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def send_response(self, code, message=None):
            if self.command == "POST":
                with lock:
                    requests["statuses"].append(int(code))
            super().send_response(code, message)

        def do_POST(self):
            nonlocal chunks
            self.chunk_number = 0
            try:
                if self.path.endswith("/photo/chunks"):
                    with lock:
                        chunks += 1
                        self.chunk_number = chunks
                    if late and self.chunk_number == 3:
                        require(original_chunk_committed.wait(4), "Cancelled request never committed its in-flight chunk.")
                        self.before_duplicate = verify_stage(2 * chunk_bytes)
                super().do_POST()
            except Exception as error:
                with lock:
                    result["errors"].append(f"Backend handler {type(error).__name__}: {error}")
                self.close_connection = True

        def _read_body(self, maximum):
            body = super()._read_body(maximum)
            if late and self.chunk_number in (2, 3):
                raw_chunks[self.chunk_number] = json.loads(body)
            if late and self.chunk_number == 2:
                verify_stage(chunk_bytes)
                second_ready.set()
                (root / "held-second-receipt").touch(exist_ok=False)
                require(manifest_seen.wait(hold_seconds), "Resume did not query before the cancelled request committed.")
            return body

        def send_photo_progress(self, status, receipt):
            offset = receipt["offset"]
            if self.chunk_number == 0:
                requests["manifest"].append(offset)
                if len(requests["manifest"]) == 2:
                    cancel_offset = chunk_bytes if late else 2 * chunk_bytes
                    require(offset == cancel_offset, "Resume did not query the exact durable prefix.")
                    verify_stage(cancel_offset)
                    if not simulator:
                        require(snapshot(workspace) == (initial, original_photos),
                                "Cancellation changed the persisted workspace before retry.")
                    result["sqlite"]["atResumeQuery"] = {"stagedBytes": offset, "events": 0, "photos": 0}
                    manifest_seen.set()
                    if pause_again:
                        (root / "held-resume-receipt").touch(exist_ok=False)
                        require(next_resume.wait(12), "The second cancellation did not unblock Resume.")
                        self.close_connection = True
                        return
                elif len(requests["manifest"]) == 3:
                    next_resume.set()
            else:
                requests["chunk"].append(offset)
                if self.chunk_number == 2:
                    verify_stage(2 * chunk_bytes)
                    chunk_receipts[2] = (int(status), receipt)
                    original_chunk_committed.set()
                    if not late:
                        second_ready.set()
                        (root / "held-second-receipt").touch(exist_ok=False)
                        require(manifest_seen.wait(hold_seconds), "Cancel did not unblock the UI for Resume.")
                    self.close_connection = True
                    return
                if late and self.chunk_number == 3:
                    expected = {
                        f"{name}ID": ids[name] for name in ("workspace", "project", "event", "entry", "photo")
                    }
                    expected.update(byteCount=len(jpeg), sha256=public.digest(jpeg), offset=2 * chunk_bytes,
                                    prefixSHA256=public.digest(jpeg[:2 * chunk_bytes]))
                    require(raw_chunks[3] == raw_chunks[2] and raw_chunks[3]["offset"] == chunk_bytes,
                            "Resume did not replay the exact cancelled chunk.")
                    require((status, receipt) == chunk_receipts[2] == (200, expected),
                            "The late duplicate did not return the immutable chunk-end receipt.")
                    require(public.read_database(database) == self.before_duplicate,
                            "The late duplicate changed SQLite.")
                    result["lateDuplicate"] = {"requestOffset": chunk_bytes, "status": int(status),
                                               "receiptOffset": offset, "prefixSHA256": receipt["prefixSHA256"],
                                               "sameRequest": True, "sqliteUnchanged": True}
                if offset == 3 * chunk_bytes and not simulator:
                    wait_marker("resume-progress-observed")
            super().send_photo_progress(status, receipt)

        def send_receipt(self, status, receipt):
            requests["receipt"].append(int(status))
            if not simulator:
                (root / "held-final-receipt").touch(exist_ok=False)
                wait_marker("final-progress-observed")
            super().send_receipt(status, receipt)

    accounts = {token: (public.ACCOUNT, {(ids["workspace"], ids["project"])})}
    used_ports = []
    with public.listener(backend, database, accounts, InterruptedTransfer, used_ports, set()) as port:
        try:
            check_readiness(port, "invalid", 401)
            check_readiness(port, token, 425)
            session = {
                "FIELDLOG_ENTRY_SYNC_PORT": str(port),
                "FIELDLOG_ENTRY_SYNC_TOKEN": token,
                "FIELDLOG_ENTRY_SYNC_WORKSPACE_ID": ids["workspace"],
                "FIELDLOG_ENTRY_SYNC_PROJECT_ID": ids["project"],
            }
            if simulator:
                session.update(FIELDLOG_ENTRY_SYNC_TEST_EVENT_ID=ids["event"],
                               FIELDLOG_ENTRY_SYNC_TEST_OTHER_EVENT_ID=ids["otherEvent"],
                               FIELDLOG_ENTRY_SYNC_TEST_PHOTO_BYTES=str(len(jpeg)))
                final, final_photos = run_native(public, scratch, simulator, session, workspace, result)
            else:
                if pause_again:
                    env["FIELDLOG_ENTRY_SYNC_TEST_PAUSE_AGAIN"] = "1"
                result["swift"]["online"] = public.run(binary, "online", root, env=env | session, timeout=30).decode().strip()
                final, final_photos = snapshot(workspace)
            check_readiness(port, token, 204)
        finally:
            manifest_seen.set()
            original_chunk_committed.set()
            next_resume.set()
    result["cleanup"] = {"listenerAndRequestThreadsClosed": True, "portRebound": True, "port": used_ports[0]}
    result["readinessHTTP"] = [401, 425, 204]

    manifests = [0, chunk_bytes if late else 2 * chunk_bytes]
    if pause_again:
        manifests.append(2 * chunk_bytes)
    require(requests["manifest"] == manifests and requests["receipt"] == [201],
            "Unexpected manifest offsets or final receipt.")
    offsets = list(range(chunk_bytes, len(jpeg), chunk_bytes)) + [len(jpeg)]
    if late:
        offsets.insert(2, 2 * chunk_bytes)
        require("lateDuplicate" in result, "Missing late duplicate receipt evidence.")
    require(requests["chunk"] == offsets, "Unexpected JPEG chunk receipts.")
    # No HTTP status was sent for the cancelled chunk or the interrupted second manifest.
    ok_count = len(manifests) + len(offsets) - 1 - int(pause_again)
    require(sorted(requests["statuses"]) == [200] * ok_count + [201], "Unexpected backend HTTP statuses.")
    events, photos, stages = public.read_database(database)
    require(len(events) == 1 and not stages, "Final SQLite event count or staging is incorrect.")
    require(events[0][:5] == (*key, ids["entry"]) and json.loads(events[0][5]) == saved_event and
            json.loads(events[0][6]) == saved_entry, "Committed metadata differs from the selected entry.")
    require(photos == [(*key, ids["photo"], jpeg)], "SQLite committed a different JPEG.")
    expected = dict(initial, revision=initial["revision"] + 1,
                    outbox=[event for event in initial["outbox"] if event != saved_event])
    require(final == expected and original_photos == final_photos,
            "The acknowledgment changed more than the selected event and revision.")
    result["sqlite"]["final"] = {"events": 1, "photos": 1, "staged": 0, "exactJPEG": True,
                                 "jpegBytes": len(jpeg), "jpegSHA256": public.digest(jpeg)}
    result["unrelatedEventsPreserved"] = len(expected["outbox"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scratch", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--simulator", type=UUID, help="Exact owned booted Simulator UUID with the prepared app installed.")
    group.add_argument("--inspect-native", action="store_true", help="Read the prepared bundles and test spec without devices.")
    args = parser.parse_args()
    os.umask(0o077)
    scratch = args.scratch.resolve(strict=True)
    if args.inspect_native:
        run, document, _, paths = native_test_spec(scratch / "derived/Build/Products")
        print(json.dumps({"xctestrun": str(run), "format": document["__xctestrun_metadata__"]["FormatVersion"],
                          "testCase": TEST_CASE, **{key: str(path) for key, path in paths.items()}}, indent=2))
        return 0

    sys.path.insert(0, str(scratch / "public-mixer/tests/integration/fieldlog-entry-sync"))
    import resume as public

    simulator = str(args.simulator).upper() if args.simulator else None
    cases = ["native-fixture"] if simulator else ["committed-chunk", "late-duplicate"]
    failed = False
    for name in cases:
        root = scratch / name
        root.mkdir(mode=0o700)
        token = secrets.token_urlsafe(32)
        result = {"case": name, "recordedAt": datetime.now(timezone.utc).isoformat(), "swift": {},
                  "sqlite": {}, "cleanup": {}, "errors": []}
        try:
            exercise(public, scratch, root, simulator, name == "late-duplicate", result, token)
        except public.UnknownCustody as error:
            result["custody"] = "unknown"
            result["errors"].append(str(error))
        except Exception as error:
            result["errors"].append(f"{type(error).__name__}: {error}")
        result["status"] = "failed" if result["errors"] else "passed"
        failed |= bool(result["errors"])
        print(json.dumps(result, separators=(",", ":")).replace(token, "[redacted]"), flush=True)
        if result.get("custody") == "unknown":
            return 74
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
