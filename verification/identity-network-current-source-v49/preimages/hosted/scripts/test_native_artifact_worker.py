import concurrent.futures
from contextlib import closing, contextmanager, nullcontext
import json
from pathlib import Path
import queue
import secrets
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "priv" / "development"))
from native_artifact_worker import (
    KINDS, BuildUncertainty, LaunchGate, NativeWorker, OwnedBuildProcess, Refusal, build, digest,
    exchange, literal, mac, now_ms, serve,
)


class NativeWorkerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.scope = dict(organization_id="organization", project_id="project",
                          application_id="application", platform="ios")
        self.spec = dict(self.scope, source={"sha256": "b" * 64}, toolchain_lock_sha256="c" * 64,
                         build_definition_sha256="d" * 64)
        self.config = {"worker_id": "native", "token": "test" * 8, "tenant": "organization",
                       "registration": {"spec": self.spec, "files": {}}}
        self.worker = NativeWorker(self.config, str(self.root / "state"))
        self.addCleanup(self.worker.close)
        self.ref = dict(self.scope, build_id="build", fence=1, attempt=1)
        self.request = dict(operation_id="a" * 64, spec=dict(self.spec, build_id="build"),
                            ref=self.ref, deadline_ms=now_ms() + 60_000,
                            guard={"record_id": "record", "epoch": 1, "revision": 1,
                                   "owner_id": "coordinator", "expires_at": now_ms() + 10_000})

    @contextmanager
    def listener(self, config=None):
        config = dict(config or self.config, port=0)
        started = queue.Queue()
        activate = socketserver.TCPServer.server_activate
        errors = []

        def record_listener(server):
            activate(server)
            started.put(server)

        def run():
            try:
                serve(config, str(self.root / "protocol-state"))
            except Exception as error:
                errors.append(error)

        thread = threading.Thread(target=run, daemon=True)
        with patch.object(socketserver.TCPServer, "server_activate", record_listener):
            thread.start()
            server = started.get(timeout=5)
        try:
            yield server.server_address
        finally:
            shutdown = None
            try:
                if not server.closed:
                    shutdown = self.call(server.server_address, "shutdown")
            finally:
                server.closed = True
                thread.join(timeout=5)
            self.assertIn(shutdown, (None, {"status": "closed"}))
            self.assertFalse(thread.is_alive())
            self.assertEqual([], errors)
            self.assertEqual(-1, server.socket.fileno())

    def call(self, address, action, request=None, nonce=None):
        body = literal({"worker_id": "native", "action": action, "request": request})
        nonce = nonce or secrets.token_hex(16)
        envelope = {"body": body, "nonce": nonce,
                    "mac": mac(self.config["token"], "request", nonce, body)}
        with socket.create_connection(address, timeout=5) as conn, conn.makefile("rb") as stream:
            conn.sendall((literal(envelope) + "\n").encode())
            reply = json.loads(stream.readline())
        self.assertEqual(mac(self.config["token"], "response", nonce, reply["body"]), reply["mac"])
        return json.loads(reply["body"])

    def test_protocol_rejects_replay_including_shutdown_across_restart(self):
        query_nonce = secrets.token_hex(16)
        shutdown_nonce = secrets.token_hex(16)
        with self.listener() as address:
            self.assertEqual({"status": "absent"}, self.call(address, "query", self.request, query_nonce))
            duplicate = self.call(address, "query", self.request, query_nonce)
            self.assertEqual({"status": "closed"}, self.call(address, "shutdown", nonce=shutdown_nonce))
        with self.listener() as address:
            replay_query = self.call(address, "query", self.request, query_nonce)
            replay_shutdown = self.call(address, "shutdown", nonce=shutdown_nonce)
        self.assertEqual([{"error": "stale"}] * 3, [duplicate, replay_query, replay_shutdown])

    def test_protocol_refuses_existing_operation_after_registration_changes(self):
        with self.listener() as address:
            stopped = self.call(address, "stop", self.request)
            self.assertEqual("stopped", stopped["status"])
        new_spec = dict(self.spec, build_definition_sha256="e" * 64)
        config = dict(self.config, registration={"spec": new_spec, "files": {}})
        later = dict(self.request, guard=dict(self.request["guard"], revision=2))
        with self.listener(config) as address:
            for action in ("query", "stop", "ensure_started", "artifacts"):
                with self.subTest(action=action):
                    self.assertEqual({"error": "unavailable"}, self.call(address, action, later))
        with self.listener() as address:
            self.assertEqual(stopped, self.call(address, "query", self.request))

    def stopped(self, address):
        deadline = time.monotonic() + 5
        while True:
            reply = self.call(address, "stop", self.request)
            if reply != {"error": "uncertain"} or time.monotonic() >= deadline:
                return reply

    def test_protocol_stop_during_preparation_prevents_final_spawn(self):
        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        open_path = Path.open

        def pause_before_spawn(path, *args, **kwargs):
            if path.name == "stderr" and path.parent.name == self.request["operation_id"]:
                entered.set()
                if not release.wait(5):
                    raise TimeoutError("test did not release preparation")
            return open_path(path, *args, **kwargs)

        def observe_build(*args):
            try:
                return build(*args)
            finally:
                finished.set()

        with (patch.object(NativeWorker, "verify", return_value=self.recipe()),
              patch.object(Path, "open", pause_before_spawn),
              patch("native_artifact_worker.build", side_effect=observe_build),
              patch("native_artifact_worker.OwnedBuildProcess", side_effect=self.fixture_process) as spawn,
              patch("native_artifact_worker.group_absent", return_value=True), self.listener() as address):
            try:
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
                self.assertTrue(entered.wait(5))
                self.assertEqual({"error": "uncertain"}, self.call(address, "stop", self.request))
            finally:
                release.set()
            self.assertTrue(finished.wait(5))
            spawn.assert_not_called()
            stopped = self.stopped(address)
            self.assertEqual("stopped", stopped["status"])
            self.assertEqual(stopped, self.call(address, "ensure_started", self.request))
            proof = self.root / "protocol-state" / "blobs" / stopped["diagnostic_sha256"]
            self.assertEqual({"closed": True, "started": False}, json.loads(proof.read_bytes())["closure"])

    def test_protocol_spawn_wins_then_stop_requires_known_closure(self):
        waiting = threading.Event()
        release = threading.Event()
        shutdown_nonce = secrets.token_hex(16)

        def fixture(*args, **kwargs):
            process = self.fixture_process(*args, **kwargs)

            def wait(timeout):
                waiting.set()
                if not release.wait(5):
                    raise TimeoutError("test did not release the child wait")
                return 0

            process.wait = wait
            return process

        with (patch.object(NativeWorker, "verify", return_value=self.recipe()),
              patch("native_artifact_worker.OwnedBuildProcess", side_effect=fixture) as spawn,
              patch("native_artifact_worker.group_absent", return_value=True), self.listener() as address):
            try:
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
                self.assertTrue(waiting.wait(5))
                self.assertEqual({"error": "uncertain"}, self.call(address, "stop", self.request))
                self.assertEqual({"error": "uncertain"}, self.call(address, "shutdown", nonce=shutdown_nonce))
                exported = self.root / "protocol-state" / ("customer-log-v1-" + self.request["operation_id"])
                self.assertFalse(exported.exists())
            finally:
                release.set()
            stopped = self.stopped(address)
            self.assertEqual("stopped", stopped["status"])
            self.assertEqual({"error": "stale"}, self.call(address, "shutdown", nonce=shutdown_nonce))
            self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.request))
            proof = self.root / "protocol-state" / "blobs" / stopped["diagnostic_sha256"]
            closure = json.loads(proof.read_bytes())["closure"]
            self.assertTrue(closure["cli_reaped"] and closure["cli_group_absent"])
            self.assertEqual(123, closure["pid"])
            self.assertEqual(124, closure["commands"][0]["pid"])
            self.assertEqual(0o400, exported.stat().st_mode & 0o777)
            self.assertEqual({
                "version": 1, "operationId": self.request["operation_id"],
                "sourceSha256": self.spec["source"]["sha256"],
                "toolchainLockSha256": self.spec["toolchain_lock_sha256"],
                "buildDefinitionSha256": self.spec["build_definition_sha256"],
                "cliExitCode": 0, "compiler": {"exitCode": 0, "stdoutBytes": 86,
                                               "stderrBytes": 15, "tailTruncated": False,
                                               "phases": ["compile"]},
            }, json.loads(exported.read_bytes()))
            marker = self.root / "protocol-state" / self.request["operation_id"] / "tmp" / "cancel-requested"
            self.assertEqual(0o600, marker.stat().st_mode & 0o777)
            self.assertEqual(stopped, self.call(address, "stop", self.request))
            spawn.assert_called_once()

    def test_protocol_native_artifacts_survive_authorized_restart_until_stop(self):
        with (patch.object(NativeWorker, "verify", return_value=self.recipe()),
              patch("native_artifact_worker.OwnedBuildProcess", side_effect=self.fixture_process) as spawn,
              patch("native_artifact_worker.group_absent", return_value=True), self.listener() as address):
            self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
            deadline = time.monotonic() + 5
            while True:
                ready = self.call(address, "artifacts", self.request)
                if ready != {"error": "unavailable"} or time.monotonic() >= deadline:
                    break
            self.assertEqual({"status": "native_ready", "artifacts": [
                {"kind": kind, "sha256": digest(kind.encode()), "sizeBytes": len(kind)} for kind in KINDS
            ]}, ready)
            spawn.assert_called_once()
        config = dict(self.config, registration={"spec": dict(self.spec, project_id="other"), "files": {}})
        with self.listener(config) as address:
            self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.request))
        with self.listener() as address:
            self.assertEqual(ready, self.call(address, "artifacts", self.request))
            artifact = ready["artifacts"][0]["sha256"]
            stored = self.root / "protocol-state" / self.request["operation_id"] / "native" / artifact
            stored.unlink()
            stored.write_bytes(b"changed")
            stored.chmod(0o400)
            self.assertEqual({"error": "uncertain"}, self.call(address, "artifacts", self.request))
            self.assertEqual("stopped", self.call(address, "stop", self.request)["status"])
            self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.request))

    def test_protocol_preflight_failure_releases_worker_capacity(self):
        recipe = dict(self.recipe(), argv=["/bin/sh", "-c", '''
printf '%s' mixer-command-receipts-10000000-1000-1000-1000-100000000000 > "$TMPDIR/cli-closed"
exit 23
''', "inert-cli", str(self.root)])
        later = dict(self.request, operation_id="e" * 64)

        def failed(address, request):
            deadline = time.monotonic() + 5
            while True:
                reply = self.call(address, "query", request)
                if reply != {"status": "running"} or time.monotonic() >= deadline:
                    break
            self.assertEqual("preflight_failed", reply.get("status"), reply)
            state = self.root / "protocol-state"
            raw = (state / "blobs" / reply["diagnostic_sha256"]).read_bytes()
            self.assertEqual(reply["diagnostic_sha256"], digest(raw))
            proof = json.loads(raw)
            self.assertEqual(request["operation_id"], proof["operation_id"])
            self.assertEqual(23, proof["closure"]["exit"])
            self.assertEqual([], proof["closure"]["commands"])
            self.assertTrue(proof["closure"]["cli_reaped"] and proof["closure"]["cli_group_absent"])
            self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", request))
            log = json.loads((state / ("customer-log-v1-" + request["operation_id"])).read_bytes())
            self.assertEqual((23, None), (log["cliExitCode"], log["compiler"]))
            return reply

        with patch.object(NativeWorker, "verify", return_value=recipe), self.listener() as address:
            self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
            first = failed(address, self.request)
            self.assertEqual(first, self.call(address, "ensure_started", self.request))
            self.assertEqual({"status": "running"}, self.call(address, "ensure_started", later))
            failed(address, later)
            self.assertEqual({"status": "closed"}, self.call(address, "shutdown"))
        with self.listener() as address:
            self.assertEqual(first, self.call(address, "query", self.request))
            stopped = self.call(address, "stop", self.request)
            self.assertEqual({"status": "stopped", "diagnostic_sha256": first["diagnostic_sha256"]}, stopped)

    def test_preflight_without_definitive_cli_closure_fails_closed(self):
        basename = "mixer-command-receipts-10000000-1000-1000-1000-100000000000"
        for marker, absent, code, nested, reason in (
            (None, True, 23, None, BuildUncertainty.CLI_ACK_MISSING),
            ("malformed", True, 23, None, BuildUncertainty.CLI_ACK_INVALID),
            (basename, False, 23, None, BuildUncertainty.CLI_GROUP_UNCONFIRMED),
            (basename, True, 0, None, BuildUncertainty.CLI_RESULT_UNPROVEN),
            (basename, True, 0, "cancelled", BuildUncertainty.CLI_RESULT_UNPROVEN),
            (basename, True, -15, None, BuildUncertainty.CLI_RESULT_UNPROVEN),
            (basename, True, 23, "hold", BuildUncertainty.NESTED_RECEIPT_INVALID),
            (basename, True, 23, "malformed_receipt", BuildUncertainty.NESTED_RECEIPT_INVALID),
            (basename, True, 23, "dangling_receipt_root", BuildUncertainty.NESTED_RECEIPT_INVALID),
            (basename, True, 23, "multiple_compilers", BuildUncertainty.CLI_RESULT_UNPROVEN),
        ):
            with self.subTest(marker=marker, absent=absent, code=code, nested=nested):
                launch = LaunchGate()

                def fixture(*args, **kwargs):
                    tmp = Path(kwargs["env"]["TMPDIR"])
                    if marker is not None:
                        (tmp / "cli-closed").write_text(marker)
                    if nested == "multiple_compilers":
                        self.fixture_process(*args, **kwargs)
                        second = tmp / basename / "command-second"
                        second.mkdir()
                        receipt = tmp / basename / "command-fixture" / "receipt.json"
                        (second / "receipt.json").write_bytes(receipt.read_bytes())
                    elif nested == "cancelled":
                        launch.cancelled = True
                    elif nested == "dangling_receipt_root":
                        (tmp / basename).symlink_to(tmp / "missing")
                    elif nested:
                        command = tmp / basename / "command-preflight"
                        command.mkdir(parents=True)
                        name = "HOLD.json" if nested == "hold" else "receipt.json"
                        (command / name).write_text("{}")
                    return type("InertProcess", (), {"pid": 123, "wait": lambda self, timeout: code})()

                with (tempfile.TemporaryDirectory(dir=self.root) as directory,
                      patch("native_artifact_worker.OwnedBuildProcess", side_effect=fixture),
                      patch("native_artifact_worker.group_absent", return_value=absent)):
                    result = build(self.recipe(), {}, Path(directory) / "state", self.request, launch)
                    self.assertIs(reason, result)

    def recipe(self):
        return {"cwd": str(self.root), "environment": {}, "argv": ["fixture-cli", str(self.root)],
                "tools": {"fixture-cli": "f" * 64}, "timeout_seconds": 10}

    def fixture_process(self, argv, *, cwd, env, **kwargs):
        store = Path(argv[-1])
        store.mkdir()
        command = ["/usr/bin/xcodebuild", "CODE_SIGNING_ALLOWED=NO", "generic/platform=iOS Simulator"]
        tmp = Path(env["TMPDIR"])
        root = "mixer-command-receipts-10000000-1000-1000-1000-100000000000"
        (tmp / "cli-closed").write_text(root)
        nested = tmp / root / "command-fixture"
        nested.mkdir(parents=True)
        (nested / "receipt.json").write_text(literal(dict.fromkeys(
            ("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF", "descriptorsClosed",
             "ownedGroupAbsent"), True) | {"command": command, "state": "TERMINAL",
                                           "exitCode": 0, "stdoutBytes": 86, "stderrBytes": 15,
                                           "outputTruncated": False,
                                           "pid": 124, "ownedPGID": 124, "ownedSession": 124}))

        def store_owned(name, data):
            path = store / name
            path.write_bytes(data)
            path.chmod(0o400)
            return str(path)

        artifacts = []
        for kind in KINDS:
            data = kind.encode()
            sha = digest(data)
            artifacts.append({"kind": kind, "sha256": sha, "sizeBytes": len(data),
                              "ownedPath": store_owned(sha, data)})
        store_owned("native-build.json", literal({
            "formatVersion": 2, "scope": "unsigned-simulator/local-development",
            "commandResult": {"exitCode": 0, "output": "SwiftCompile /private/raw-input.swift\n"
                                                   "error: EXAMPLE_PRIVATE_ENV_TOKEN=opaque"},
            "binding": {"command": command, "authoritativeSourceDigest": self.spec["source"]["sha256"],
                        "lockSHA256": self.spec["toolchain_lock_sha256"], "cliExecutableSHA256": "f" * 64,
                        "environment": {key: value for key, value in env.items()
                                        if key != "MIXER_WORKER_COMMAND_CONTROL"}, "resourceInventoryPolicy": "retained-app-files-v1"},
            "nativeProduct": {"nativeBinary": artifacts[0], "debugSymbols": artifacts[1]},
            "resourceInventory": artifacts[2],
        }).encode())

        class CompletedBuild:
            pid = 123

            def wait(self, timeout):
                return 0

        return CompletedBuild()

    def test_dropped_process_handle_never_polls_after_unknown(self):
        process = OwnedBuildProcess.__new__(OwnedBuildProcess)
        process._child_created = True
        with patch.object(process, "_internal_poll") as poll:
            process.__del__()
            poll.assert_not_called()

    def test_uncertainty_reason_is_private_and_durable_across_restart(self):
        operation = self.request["operation_id"]

        @contextmanager
        def open_worker(state):
            worker = NativeWorker(self.config, str(state))
            try:
                yield worker
            finally:
                # No OS child exists in these fixtures. Close test resources despite
                # the public shutdown refusal and keep the operation row for restart.
                worker.executor.shutdown()
                worker.db.close()
                worker.lock.close()

        def reply(worker, action, request=None):
            nonce = secrets.token_hex(16)
            body = literal({"worker_id": "native", "action": action, "request": request})
            close, response = exchange(worker, {"body": body, "nonce": nonce,
                                                "mac": mac(self.config["token"], "request", nonce, body)})
            self.assertFalse(close)
            self.assertEqual(mac(self.config["token"], "response", nonce, response["body"]), response["mac"])
            return json.loads(response["body"])

        for reason in ("cli_wait_timeout", "cli_ack_missing", "nested_receipt_invalid", "future_exception",
                       "cli_process_handle_unavailable", "cli_launch_record_failed"):
            with self.subTest(reason=reason):
                state = self.root / reason
                wait = Mock(side_effect=subprocess.TimeoutExpired(["private-fixture-argv"], 1))
                inert_process = Mock(spec=OwnedBuildProcess, pid=2**31 - 1)

                def fixture(*args, **kwargs):
                    if reason == "cli_process_handle_unavailable":
                        raise OSError("private-fixture-constructor-detail")
                    if reason == "cli_launch_record_failed":
                        # A directory at the fresh launch record path makes the real write fail.
                        (Path(kwargs["env"]["TMPDIR"]).parent / "launch.json").mkdir()
                        return inert_process
                    process = self.fixture_process(*args, **kwargs)
                    marker = Path(kwargs["env"]["TMPDIR"]) / "cli-closed"
                    if reason == "cli_wait_timeout":
                        process.wait = wait
                    elif reason == "cli_ack_missing":
                        marker.unlink()
                    else:
                        nested = marker.parent / marker.read_text() / "command-fixture" / "receipt.json"
                        nested.write_text('{"private-fixture-receipt":true}')
                    return process

                launch_failure = reason in ("cli_process_handle_unavailable", "cli_launch_record_failed")
                group_probe = (nullcontext() if launch_failure
                               else patch("native_artifact_worker.group_absent", return_value=True))
                with (patch.object(NativeWorker, "verify", return_value=self.recipe()),
                      patch("native_artifact_worker.OwnedBuildProcess", side_effect=fixture) as spawn,
                      group_probe as probe):
                    with open_worker(state) as worker:
                        if reason == "future_exception":
                            (state / operation).mkdir()  # Fail output creation before the spawn boundary.
                        self.assertEqual({"status": "running"}, reply(worker, "ensure_started", self.request))
                        initial = worker.load(operation)
                        self.assertEqual(1, initial["starts"])
                        self.assertNotIn("uncertainty_reason", initial)
                        self.assertFalse(concurrent.futures.wait([worker.future], timeout=5).not_done)
                        self.assertEqual({"error": "uncertain"}, reply(worker, "query", self.request))

                    ledger = state / "operations.sqlite"
                    self.assertEqual(0o600, ledger.stat().st_mode & 0o777)
                    with closing(sqlite3.connect(ledger)) as db:
                        raw = db.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchone()[0]
                    self.assertFalse((state / ("customer-log-v1-" + operation)).exists())
                    self.assertFalse((state / "blobs").exists())

                    with open_worker(state) as worker:
                        reopened = worker.load(operation)
                        for action in ("query", "ensure_started", "stop"):
                            self.assertEqual({"error": "uncertain"}, reply(worker, action, self.request))
                        later = dict(self.request, guard=dict(self.request["guard"], epoch=2))
                        self.assertEqual({"error": "uncertain"}, reply(worker, "ensure_started", later))
                        stopped = worker.load(operation)
                        self.assertTrue(stopped["tombstone"])
                        self.assertEqual(1, stopped["starts"])
                        self.assertEqual({"error": "unavailable"}, reply(worker, "artifacts", later))
                        other = dict(self.request, operation_id="e" * 64)
                        self.assertEqual({"error": "unavailable"}, reply(worker, "ensure_started", other))
                        self.assertEqual({"error": "uncertain"}, reply(worker, "shutdown"))
                    self.assertEqual(int(reason != "future_exception"), spawn.call_count)
                    if probe is not None:
                        self.assertEqual(int(reason == "nested_receipt_invalid"), probe.call_count)
                    self.assertEqual(int(reason == "cli_wait_timeout"), wait.call_count)
                    self.assertEqual([], inert_process.mock_calls)
                    self.assertEqual(dict(initial, status="uncertain", uncertainty_reason=reason), json.loads(raw))
                    self.assertEqual(reason, reopened["uncertainty_reason"])
                    self.assertEqual(reason, stopped["uncertainty_reason"])

    def test_authentication_precedes_worker_access(self):
        body = literal({"worker_id": "native", "action": "query", "request": self.request})
        nonce = "9" * 32
        envelope = {"body": body, "nonce": nonce,
                    "mac": mac(self.config["token"], "request", nonce, body)}
        with self.assertRaises(Refusal):
            exchange(self.worker, dict(envelope, body=body.replace("query", "stop")))
        self.assertIsNone(self.worker.load(self.request["operation_id"]))
        close, reply = exchange(self.worker, envelope)
        self.assertFalse(close)
        self.assertEqual({"status": "absent"}, json.loads(reply["body"]))
        self.assertEqual(mac(self.config["token"], "response", nonce, reply["body"]), reply["mac"])

    def test_stop_before_start_is_permanent_across_new_lease(self):
        stopped = self.worker.request("stop", self.request)
        self.assertEqual("stopped", stopped["status"])
        later = dict(self.request, guard=dict(self.request["guard"], epoch=2))
        self.assertEqual(stopped, self.worker.request("ensure_started", later))
        with self.assertRaisesRegex(Refusal, "stale"):
            self.worker.request("query", self.request)
        self.assertEqual(0, self.worker.load(self.request["operation_id"])["starts"])

    def test_stop_during_native_work_waits_for_known_closure_and_recovers_failed_proof(self):
        future = concurrent.futures.Future()
        with (patch.object(self.worker, "verify", return_value={}),
              patch.object(self.worker.executor, "submit", return_value=future) as submit):
            self.assertEqual({"status": "running"}, self.worker.request("ensure_started", self.request))
            self.assertEqual({"status": "running"}, self.worker.request("ensure_started", self.request))
            submit.assert_called_once()
        stop = dict(self.request, guard=dict(self.request["guard"], revision=2))
        self.assertEqual({"error": "uncertain"}, self.worker.request("stop", stop))
        with self.assertRaisesRegex(Refusal, "uncertain"):
            self.worker.close()
        future.set_result({"closed": True, "started": True, "exit": 0,
                           "artifacts": [{}], "manifest_sha256": "f" * 64})
        with patch.object(self.worker, "blob", side_effect=OSError("disk fault")):
            with self.assertRaises(OSError):
                self.worker.request("stop", stop)
        self.assertEqual({"status": "running"}, self.worker.request("query", stop))
        with self.assertRaisesRegex(Refusal, "unavailable"):
            self.worker.request("artifacts", stop)
        self.assertEqual("stopped", self.worker.request("stop", stop)["status"])
        self.assertEqual("stopped", self.worker.request("ensure_started", stop)["status"])

    def test_registration_and_operation_binding_refuse_another_scope(self):
        foreign = dict(self.request, ref=dict(self.ref, organization_id="other"),
                       spec=dict(self.request["spec"], organization_id="other"))
        with self.assertRaisesRegex(Refusal, "unavailable"):
            self.worker.request("query", foreign)
        self.assertEqual({"status": "absent"}, self.worker.request("query", self.request))
        with self.assertRaisesRegex(Refusal, "unavailable"):
            self.worker.request("artifacts", dict(self.request, ref=dict(self.ref, fence=2)))


if __name__ == "__main__":
    unittest.main()
