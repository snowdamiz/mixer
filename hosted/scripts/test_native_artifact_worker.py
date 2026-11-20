import concurrent.futures
from contextlib import closing, contextmanager, nullcontext
from dataclasses import asdict
import hmac
import json
import os
from pathlib import Path
import plistlib
import queue
import secrets
import signal
import shutil
import socket
import socketserver
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "priv" / "development"))
import ios_build_custody
import native_artifact_worker
import linux_android_artifact_importer as linux_importer
from linux_android_runner import LinuxAndroidRunnerClient
from native_artifact_worker import (
    ANDROID_DRIVER, ANDROID_MANIFEST, ANDROID_PROFILE, KINDS, BuildUncertainty, LaunchGate, NativeWorker,
    OwnedBuildProcess, Refusal, build, digest, exchange, literal, mac, now_ms, retained_android_report, serve,
)


class InertLinuxRunner:
    """Independently owned inventory that survives the controller's reopen."""

    def __init__(self, store_id, recipe_sha256):
        self.store_id = store_id
        self.recipe_sha256 = recipe_sha256
        self.operations = {}
        self.requests = []
        self.starts = []
        self.observe_intent = lambda request: None
        self.drop_before_start = False
        self.drop_start_reply = True
        self.cleanup_observed = threading.Event()
        self.transform_reply = lambda reply: reply

    def handle(self, request):
        identity = request["identity"]
        if (request["version"] != 1 or identity["store_id"] != self.store_id
                or identity["recipe_sha256"] != self.recipe_sha256):
            raise ValueError("unexpected runner identity")
        action, operation = request["action"], identity["operation_id"]
        self.observe_intent(request)
        self.requests.append(request)
        previous = self.operations.get(operation)
        if previous is not None and previous[0] != identity:
            raise ValueError("changed immutable runner identity")
        status = previous[1] if previous else "absent"
        if action == "ensure_started" and status == "absent":
            if self.drop_before_start:
                self.drop_before_start = False
                return None
            self.starts.append(operation)
            self.operations[operation] = (identity, "running")
            if self.drop_start_reply:
                self.drop_start_reply = False
                return None
            status = "running"
        if action == "stop" and status != "stopped":
            self.operations[operation] = (identity, "stopping")
            status = "stopping"
        if status == "stopping" and self.cleanup_observed.is_set():
            self.operations[operation] = (identity, "stopped")
            status = "stopped"
        reply = {"request": request, "status": status}
        if status == "stopped":
            reply["terminal"] = {"stop_fenced": True, "container_absent": True,
                                 "processes_absent": True, "resources_removed": True}
        return self.transform_reply(reply)


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
    def listener(self, config=None, *, linux_runner=None):
        config = dict(config or self.config, port=0)
        started = queue.Queue()
        activate = socketserver.TCPServer.server_activate
        errors = []

        def record_listener(server):
            activate(server)
            started.put(server)

        def run():
            try:
                serve(config, str(self.root / "protocol-state"), linux_runner=linux_runner)
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
            packet = stream.readline(262_145)
        body = json.loads(packet)["body"]
        signed = f"response\n{nonce}\n{body}".encode()
        response_mac = hmac.digest(self.config["token"].encode(), signed, "sha256").hex()
        self.assertEqual((literal({"body": body, "mac": response_mac}) + "\n").encode(), packet)
        reply = json.loads(body)
        self.assertEqual(literal(reply), body)
        return reply

    @contextmanager
    def linux_runner_listener(self):
        path = self.root / "runner.sock"
        recipe_sha = self.spec["build_definition_sha256"]
        runner = InertLinuxRunner("f" * 64, recipe_sha)
        errors = []

        class Handler(socketserver.StreamRequestHandler):
            timeout = 1

            def handle(self):
                try:
                    packet = self.rfile.readline(4097)
                    if not packet:
                        return
                    if len(packet) > 4096 or not packet.endswith(b"\n"):
                        raise ValueError("invalid fixture request")
                    reply = runner.handle(json.loads(packet))
                    if isinstance(reply, bytes):
                        self.wfile.write(reply)
                    elif reply is not None:
                        self.wfile.write((literal(reply) + "\n").encode())
                except Exception as error:
                    errors.append(error)

        with socketserver.UnixStreamServer(str(path), Handler) as server:
            path.chmod(0o600)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            try:
                yield runner, LinuxAndroidRunnerClient(path, recipe_sha256=recipe_sha, store_id=runner.store_id)
            finally:
                server.shutdown()
                thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
        path.unlink()
        self.assertEqual([], errors)
        self.assertEqual(-1, server.socket.fileno())

    def linux_registration(self):
        spec = dict(self.spec, platform="android")
        return (dict(self.config, registration={"spec": spec, "files": {}}),
                dict(self.request, ref=dict(self.ref, platform="android"), spec=dict(spec, build_id="build")))

    def protocol_row(self, request):
        with closing(sqlite3.connect(self.root / "protocol-state" / "operations.sqlite")) as reader:
            row = reader.execute("SELECT value FROM operations WHERE id=?", (request["operation_id"],)).fetchone()
        return json.loads(row[0]) if row else None

    def test_cli_starts_the_configured_linux_worker(self):
        config, request = self.linux_registration()
        source = Path(native_artifact_worker.__file__)
        state = self.root / "cli-state"
        config_path = self.root / "cli-config.json"
        with self.linux_runner_listener() as (runner, client):
            runner.drop_start_reply = False
            with socket.socket() as reservation:
                reservation.bind(("127.0.0.1", 0))
                address = reservation.getsockname()
            config.update(port=address[1], linux_runner={
                "socket_path": str(client.socket_path), "recipe_sha256": client.recipe_sha256,
                "store_id": client.store_id,
            })
            configuration = literal(config).encode()
            config_path.write_bytes(configuration)
            entry = [sys.executable, "-B"]
            if sys.flags.optimize:
                entry.append("-O")
            entry.extend([str(source), str(config_path)])
            with subprocess.Popen(entry + [digest(configuration), str(state)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                try:
                    deadline = time.monotonic() + 5
                    while True:
                        try:
                            with socket.create_connection(address, timeout=0.1):
                                break
                        except OSError:
                            self.assertIsNone(process.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(0.02)
                    self.assertEqual({"status": "absent"}, self.call(address, "query", request))
                    self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))
                    self.assertEqual([request["operation_id"]], runner.starts)
                    runner.cleanup_observed.set()
                    self.assertEqual("stopped", self.call(address, "stop", request)["status"])
                    self.assertEqual({"status": "closed"}, self.call(address, "shutdown"))
                    stdout, stderr = process.communicate(timeout=3)
                    self.assertEqual((0, b"", b""), (process.returncode, stdout, stderr))
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=3)

            invalid_state = self.root / "invalid-state"
            config["linux_runner"]["recipe_sha256"] = "e" * 64
            configuration = literal(config).encode()
            config_path.write_bytes(configuration)
            result = subprocess.run(entry + [digest(configuration), str(invalid_state)],
                                    capture_output=True, timeout=3, check=False)
            self.assertEqual(1, result.returncode)
            self.assertIn(b"Invalid Linux runner configuration", result.stderr)
            self.assertFalse(invalid_state.exists())
            self.assertEqual([request["operation_id"]], runner.starts)

    def linux_completion_config(self, config, client, request, bundle, inputs):
        identity = asdict(client.operation(request).identity)
        return dict(
            config,
            linux_runner=dict(socket_path=str(client.socket_path), recipe_sha256=client.recipe_sha256,
                              store_id=client.store_id),
            linux_artifact_imports={request["operation_id"]: {
                "identity": identity, "bundle": str(bundle), "inputs": inputs,
            }},
        )

    @staticmethod
    def linux_completion(reply, inputs, readback_sha):
        return {"request": reply["request"], "status": "completed", "terminal": {
            "inputs": inputs, "readback_sha256": readback_sha, "exit_code": 0,
            "start_fenced": True, "container_absent": True, "processes_absent": True, "resources_removed": True,
        }}

    def test_linux_completion_refuses_unbound_and_malformed_results(self):
        config, request = self.linux_registration()
        request = dict(request, guard=dict(request["guard"], expires_at=now_ms() + 60_000))
        operation = self.root / "protocol-state" / request["operation_id"]
        inputs = dict(source_tree_sha256="1" * 64, linux_lock_sha256="2" * 64, rendered_driver_sha256="3" * 64)

        with self.linux_runner_listener() as (runner, client):
            runner.drop_start_reply = False
            config = self.linux_completion_config(config, client, request, self.root / "unused-bundle", inputs)
            with self.listener(config) as address:
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))

                def completed(reply):
                    return self.linux_completion(reply, inputs, "4" * 64)

                def reject_result(transform, error="uncertain"):
                    runner.transform_reply = lambda reply: transform(completed(reply))
                    self.assertEqual({"error": error}, self.call(address, "query", request))
                    self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", request))
                    row = self.protocol_row(request)
                    self.assertEqual("uncertain", row["status"])
                    self.assertNotIn("manifest_sha256", row)
                    self.assertNotIn("artifacts", row)
                    self.assertFalse(operation.exists())

                for field in ("operation_id", "binding_sha256", "recipe_sha256", "store_id"):
                    with self.subTest(identity=field):
                        reject_result(lambda r: dict(r, request=dict(
                            r["request"], identity=dict(r["request"]["identity"], **{field: "0" * 64}),
                        )))
                for field, wrong in {"version": 2, "action": "ensure_started", "deadline_ms": 9}.items():
                    with self.subTest(echo=field):
                        reject_result(lambda r: dict(r, request=dict(r["request"], **{field: wrong})))
                reject_result(lambda r: dict(r, request=dict(r["request"], guard=dict(r["request"]["guard"], epoch=2))))
                reject_result(lambda r: dict(r, bundle="/arbitrary"))
                reject_result(lambda r: {k: v for k, v in r.items() if k != "terminal"})
                reject_result(lambda r: dict(r, terminal=[]))
                reject_result(lambda r: (literal(r)[:-1] + ',"status":"completed"}\n').encode())
                for field, wrong in (
                    ("identity", asdict(client.operation(request).identity)),
                    ("bundle", "/arbitrary"),
                    ("readback_sha256", "F" * 64),
                    ("exit_code", False),
                    ("exit_code", 0.0),
                    ("exit_code", 1),
                    ("start_fenced", 1),
                    ("container_absent", False),
                    ("processes_absent", False),
                    ("resources_removed", False),
                    ("inputs", []),
                    ("inputs", dict(inputs, extra="0" * 64)),
                    ("inputs", dict(inputs, linux_lock_sha256="")),
                    ("inputs", {k: v for k, v in inputs.items() if k != "source_tree_sha256"}),
                ):
                    with self.subTest(terminal=field, wrong=wrong):
                        reject_result(lambda r: dict(r, terminal=dict(r["terminal"], **{field: wrong})))
                for field in inputs:
                    with self.subTest(input_pin=field):
                        reject_result(lambda r: dict(r, terminal=dict(
                            r["terminal"], inputs=dict(inputs, **{field: "0" * 64}),
                        )), "unavailable")

                def expire_guard(reply):
                    clock.return_value = request["guard"]["expires_at"]
                    return completed(reply)

                runner.transform_reply = expire_guard
                with patch.object(native_artifact_worker, "now_ms", return_value=now_ms()) as clock:
                    self.assertEqual({"error": "stale"}, self.call(address, "query", request))
                expired = dict(request, guard=dict(request["guard"], expires_at=now_ms() - 1))
                observed = len(runner.requests)
                self.assertEqual({"error": "stale"}, self.call(address, "artifacts", expired))
                self.assertEqual(observed, len(runner.requests))
                self.assertFalse(operation.exists())

                runner.transform_reply = completed
                self.assertEqual({"error": "uncertain"}, self.call(address, "stop", request))
                self.assertIs(self.protocol_row(request)["tombstone"], True)
                self.assertEqual({"error": "uncertain"}, self.call(address, "query", request))
                self.assertEqual({"error": "uncertain"}, self.call(address, "ensure_started", request))
                self.assertEqual("query", runner.requests[-1]["action"])
                self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", request))
                self.assertFalse(operation.exists())
                runner.transform_reply = lambda reply: reply
                runner.cleanup_observed.set()
                self.assertEqual("stopped", self.call(address, "stop", request)["status"])

    @unittest.skipUnless(os.environ.get("MIXER_PAIR25_BUNDLE"), "requires the operator's retained Pair25 bundle")
    def test_linux_completion_imports_pair25_and_rehashes_across_worker_restart(self):
        from test_linux_android_artifact_importer import RECEIPT, RECEIPT_SHA

        payload = RECEIPT.read_bytes()
        self.assertEqual(RECEIPT_SHA, digest(payload))
        receipt = json.loads(payload)
        bundle = Path(os.environ["MIXER_PAIR25_BUNDLE"])
        inputs = dict(source_tree_sha256=receipt["build"]["source_tree_sha256"],
                      linux_lock_sha256=receipt["inputHashes"]["localLinuxLockSHA256"],
                      rendered_driver_sha256=receipt["inputHashes"]["renderedBuildDriverSHA256"])
        readback_sha = receipt["readbackChecks"]["readbackSHA256"]
        config, request = self.linux_registration()
        spec = dict(config["registration"]["spec"], source={"sha256": inputs["source_tree_sha256"]},
                    toolchain_lock_sha256=inputs["linux_lock_sha256"])
        config = dict(config, registration=dict(config["registration"], spec=spec))
        request = dict(request, spec=dict(spec, build_id=request["spec"]["build_id"]),
                       guard=dict(request["guard"], expires_at=now_ms() + 60_000))
        operation = request["operation_id"]
        store = self.root / "protocol-state" / operation / linux_importer.STORE
        rows = [{k: v for k, v in row.items() if k != "file"} for row in receipt["artifacts"]]
        expected = dict(status="native_ready", artifacts=rows, profile=ANDROID_PROFILE,
                        platform="android", operation_id=operation)
        running, unavailable = {"status": "running"}, {"error": "unavailable"}
        save = NativeWorker.save

        def fail_completion_commit(worker, operation, value):
            if value["status"] == "native_ready":
                worker.db.execute("UPDATE operations SET value=? WHERE id=?", (literal(value), operation))
                raise sqlite3.OperationalError("fixture failure before completing the publication commit")
            return save(worker, operation, value)

        with self.linux_runner_listener() as (runner, client):
            runner.drop_start_reply = False
            config = self.linux_completion_config(config, client, request, bundle, inputs)
            with self.listener(config) as address:
                self.assertEqual(running, self.call(address, "ensure_started", request))
                runner.transform_reply = lambda reply: self.linux_completion(reply, inputs, readback_sha)
                import_closed_bundle = linux_importer.import_closed_bundle

                def import_before_guard_expires(*args, **kwargs):
                    result = import_closed_bundle(*args, **kwargs)
                    clock.return_value = request["guard"]["expires_at"]
                    return result

                with (patch.object(native_artifact_worker, "now_ms", return_value=now_ms()) as clock,
                      patch.object(linux_importer, "import_closed_bundle", side_effect=import_before_guard_expires)):
                    self.assertEqual({"error": "stale"}, self.call(address, "query", request))
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual(unavailable, self.call(address, "artifacts", request))
                with patch.object(NativeWorker, "save", fail_completion_commit):
                    self.assertEqual({"error": "uncertain"}, self.call(address, "query", request))
                partial = self.protocol_row(request)
                self.assertEqual("uncertain", partial["status"])
                self.assertNotIn("manifest_sha256", partial)
                self.assertNotIn("artifacts", partial)
                self.assertEqual(unavailable, self.call(address, "artifacts", request))
                manifest = store / linux_importer.MANIFEST
                manifest_sha = digest(manifest.read_bytes())
                store_identity = (store.stat().st_dev, store.stat().st_ino)

            renewed = dict(request, guard=dict(request["guard"], epoch=2, owner_id="next-coordinator"))
            with self.listener(config) as address:
                self.assertEqual(unavailable, self.call(address, "artifacts", renewed))
                self.assertEqual(running, self.call(address, "ensure_started", renewed))
                self.assertEqual([operation], runner.starts)
                admitted = self.protocol_row(request)
                self.assertEqual("native_ready", admitted["status"])
                self.assertEqual(renewed["guard"], admitted["guard"])
                self.assertEqual(rows, admitted["artifacts"])
                self.assertEqual(manifest_sha, admitted["manifest_sha256"])
                self.assertEqual(store_identity, (store.stat().st_dev, store.stat().st_ino))
                self.assertEqual({linux_importer.MANIFEST, *(row["sha256"] for row in rows)},
                                 {entry.name for entry in store.iterdir()})
                self.assertEqual(expected, self.call(address, "artifacts", renewed))
                self.assertEqual({"error": "stale"}, self.call(address, "artifacts", request))
                for row in receipt["artifacts"]:
                    retained = store / row["sha256"]
                    self.assertEqual((bundle / row["file"]).read_bytes(), retained.read_bytes())
                    self.assertEqual(0o400, stat.S_IMODE(retained.stat().st_mode))

            seen = len(runner.requests)
            with self.listener(config) as address:
                self.assertEqual(expected, self.call(address, "artifacts", renewed))
                self.assertEqual(running, self.call(address, "query", renewed))
                self.assertEqual(seen, len(runner.requests))
                reopen = linux_importer.reopen_linux_artifacts

                def rehash_before_guard_expires(*args, **kwargs):
                    result = reopen(*args, **kwargs)
                    clock.return_value = renewed["guard"]["expires_at"]
                    return result

                with (patch.object(native_artifact_worker, "now_ms", return_value=now_ms()) as clock,
                      patch.object(linux_importer, "reopen_linux_artifacts", side_effect=rehash_before_guard_expires)):
                    self.assertEqual({"error": "stale"}, self.call(address, "artifacts", renewed))
                inventory = store / rows[-1]["sha256"]
                inventory.chmod(0o600)
                original = inventory.read_bytes()
                inventory.write_bytes(b"!" + original[1:])
                inventory.chmod(0o400)
                self.assertEqual({"error": "uncertain"}, self.call(address, "artifacts", renewed))
                inventory.chmod(0o600)
                inventory.write_bytes(original)
                inventory.chmod(0o400)
                self.assertEqual(expected, self.call(address, "artifacts", renewed))
                runner.transform_reply = lambda reply: reply
                runner.cleanup_observed.set()
                self.assertEqual("stopped", self.call(address, "stop", renewed)["status"])
                self.assertEqual(unavailable, self.call(address, "artifacts", renewed))
            with self.listener(config) as address:
                self.assertEqual(unavailable, self.call(address, "artifacts", renewed))
        print("\nPair25 worker publication " + literal(dict(expected, manifest_sha256=manifest_sha)), flush=True)

    def test_linux_runner_server_composes_across_lost_reply_restart_and_cleanup(self):
        from test_linux_android_runner_server import (
            ContainerObservation, InertContainerAdapter, LinuxAndroidRunnerServer, open_runner, running_runner,
        )

        config, request = self.linux_registration()
        now = now_ms()
        request = dict(request, guard=dict(request["guard"], expires_at=now + 60_000), deadline_ms=now + 120_000)
        successor = dict(request, guard=dict(request["guard"], epoch=2, owner_id="successor"))
        stop = dict(successor, guard=dict(successor["guard"], revision=2))
        contender = dict(request, operation_id="b" * 64,
                         ref=dict(request["ref"], build_id="contender"),
                         spec=dict(request["spec"], build_id="contender"),
                         guard=dict(request["guard"], record_id="contender"))

        directory = self.root / "r"
        directory.mkdir(mode=0o700)
        runner_db = directory / "operations.sqlite"
        client = LinuxAndroidRunnerClient(
            directory / "runner.sock", recipe_sha256=request["spec"]["build_definition_sha256"], store_id="f" * 64,
        )
        adapter = InertContainerAdapter(runner_db, self.assertEqual)
        first = client.operation(request).identity
        other = client.operation(contender)
        running = {"status": "running"}
        uncertain, unavailable = {"error": "uncertain"}, {"error": "unavailable"}

        def runner_listener(*, initialize=False):
            return running_runner(self, open_runner(directory, recipe_sha256=client.recipe_sha256,
                                                    store_id=client.store_id, adapter=adapter, initialize=initialize))

        def expected_runner_reply(action, request, status):
            return {"request": {"version": 1, "action": action, **asdict(client.operation(request))}, "status": status}

        def check_binding(request, phase, status, *, fenced=False):
            operation_id = request["operation_id"]
            binding = {key: request[key] for key in ("ref", "spec", "deadline_ms")}
            binding_sha = digest(literal(binding).encode())
            with closing(sqlite3.connect(runner_db.as_uri() + "?mode=ro", uri=True, timeout=1)) as reader:
                row = reader.execute("SELECT binding, deadline, guard, phase FROM operation WHERE id = ?",
                                     (operation_id,)).fetchone()
            self.assertEqual((binding_sha, request["deadline_ms"], literal(request["guard"]), phase), row)
            worker = self.protocol_row(request)
            self.assertEqual(binding, worker["binding"])
            self.assertEqual(request["guard"], worker["guard"])
            self.assertEqual({"operation_id": operation_id, "binding_sha256": binding_sha,
                              "recipe_sha256": client.recipe_sha256, "store_id": client.store_id},
                             worker["linux_runner"])
            self.assertEqual(status, worker["status"])
            self.assertEqual(1, worker["starts"])
            self.assertIs(worker.get("tombstone", False), fenced)
            return worker

        def check_contender_held(address):
            self.assertEqual(unavailable, self.call(address, "ensure_started", contender))
            self.assertEqual(0, self.protocol_row(contender)["starts"])
            with self.assertRaisesRegex(Refusal, "^uncertain$"):
                client.observe("ensure_started", other)
            self.assertEqual([first], adapter.starts)

        def check_stopped(address, action, request, runner_action):
            closure = expected_runner_reply(runner_action, request, "stopped")
            closure["terminal"] = {"stop_fenced": True, "container_absent": True,
                                   "processes_absent": True, "resources_removed": True}
            diagnostic = (literal({"operation_id": request["operation_id"], "closure": closure}) + "\n").encode()
            diagnostic_sha = digest(diagnostic)
            reply = {"status": "stopped", "diagnostic_sha256": diagnostic_sha}
            self.assertEqual(reply, self.call(address, action, request))
            row = check_binding(request, "stopped", "stopped", fenced=True)
            self.assertEqual(closure, row["closure"])
            self.assertEqual(diagnostic_sha, row["diagnostic_sha256"])
            self.assertEqual(diagnostic, (self.root / "protocol-state" / "blobs" / diagnostic_sha).read_bytes())
            return reply

        with patch.object(native_artifact_worker, "build", side_effect=AssertionError("unexpected native build")) as local_build:
            with runner_listener(initialize=True), self.listener(config, linux_runner=client) as address:
                self.assertEqual({"status": "absent"}, self.call(address, "query", request))
                with patch.object(LinuxAndroidRunnerServer, "send", autospec=True) as dropped:
                    self.assertEqual(uncertain, self.call(address, "ensure_started", request))
                dropped.assert_called_once()
                self.assertEqual(expected_runner_reply("ensure_started", request, "running"), dropped.call_args.args[2])
                check_binding(request, "started", "uncertain")
                self.assertEqual([first], adapter.creates)
                self.assertEqual([first], adapter.starts)

            with runner_listener(), self.listener(config, linux_runner=client) as address:
                self.assertEqual(running, self.call(address, "query", successor))
                self.assertEqual(running, self.call(address, "ensure_started", successor))
                self.assertEqual({"error": "stale"}, self.call(address, "ensure_started", request))
                self.assertEqual(unavailable, self.call(address, "artifacts", successor))
                check_contender_held(address)

                adapter.defer_cleanup.add(first)
                self.assertEqual(uncertain, self.call(address, "stop", stop))
                check_binding(stop, "stopping", "uncertain", fenced=True)

            with runner_listener(), self.listener(config, linux_runner=client) as address:
                adapter.observations[first] = ContainerObservation(first, "absent", True, False)
                self.assertEqual(uncertain, self.call(address, "ensure_started", stop))
                self.assertEqual(expected_runner_reply("ensure_started", stop, "stopping"),
                                 client.observe("ensure_started", client.operation(stop)))
                check_binding(stop, "stopping", "uncertain", fenced=True)
                check_contender_held(address)

                adapter.defer_cleanup.remove(first)
                del adapter.observations[first]
                stopped = check_stopped(address, "ensure_started", stop, "query")
                self.assertEqual(stopped, self.call(address, "ensure_started", stop))
                self.assertEqual(unavailable, self.call(address, "artifacts", stop))
                self.assertEqual("stopped", client.observe("ensure_started", client.operation(stop))["status"])

                self.assertEqual(running, self.call(address, "ensure_started", contender))
                check_stopped(address, "stop", contender, "stop")
                self.assertEqual(unavailable, self.call(address, "artifacts", contender))

            with runner_listener(), self.listener(config, linux_runner=client) as address:
                later = dict(stop, guard=dict(stop["guard"], epoch=3, owner_id="later"))
                self.assertEqual(stopped, self.call(address, "ensure_started", later))
                self.assertEqual("stopped", client.observe("ensure_started", client.operation(later))["status"])
                check_binding(later, "stopped", "stopped", fenced=True)

        local_build.assert_not_called()
        self.assertEqual([first, other.identity], adapter.creates)
        self.assertEqual([first, other.identity], adapter.starts)
        self.assertEqual([first, other.identity], adapter.stops)
        self.assertEqual({}, adapter.observations)
        state = self.root / "protocol-state"
        self.assertEqual({"operations.sqlite", "writer.lock", "blobs"}, {item.name for item in state.iterdir()})
        self.assertEqual({self.protocol_row(op)["diagnostic_sha256"] for op in (stop, contender)},
                         {item.name for item in (state / "blobs").iterdir()})

    def test_linux_runner_retains_admission_across_lost_start_and_controller_reopen(self):
        config, request = self.linux_registration()
        operation_id = request["operation_id"]
        contender = dict(request, operation_id="b" * 64, spec=dict(request["spec"], build_id="contender"),
                         ref=dict(request["ref"], build_id="contender"),
                         guard=dict(request["guard"], record_id="contender"))
        next_lease = dict(request, guard=dict(request["guard"], epoch=2, owner_id="new-coordinator"))
        stop = dict(next_lease, guard=dict(next_lease["guard"], revision=2))
        unavailable, uncertain = {"error": "unavailable"}, {"error": "uncertain"}

        with self.linux_runner_listener() as (runner, client):
            def observe_intent(message):
                row = self.protocol_row(message["identity"])
                self.assertEqual("uncertain", row["status"])
                self.assertEqual(1, row["starts"])
                self.assertEqual(message["identity"], row["linux_runner"])
                self.assertEqual(message["guard"], row["guard"])
                self.assertEqual(message["deadline_ms"], row["binding"]["deadline_ms"])
                self.assertEqual(digest(literal(row["binding"]).encode()), message["identity"]["binding_sha256"])
                if message["action"] == "stop":
                    self.assertIs(row.get("tombstone"), True)

            runner.observe_intent = observe_intent
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual(unavailable, self.call(address, "ensure_started", dict(request, command="arbitrary")))
                foreign = dict(request, spec=dict(request["spec"], organization_id="foreign"))
                self.assertEqual(unavailable, self.call(address, "ensure_started", foreign))
                self.assertEqual([], runner.requests)
                self.assertEqual({"status": "absent"}, self.call(address, "query", request))
                self.assertEqual(uncertain, self.call(address, "ensure_started", request))
                self.assertEqual([operation_id], runner.starts)
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual(unavailable, self.call(address, "artifacts", request))

            wrong_store = LinuxAndroidRunnerClient(client.socket_path, recipe_sha256=client.recipe_sha256,
                                                   store_id="e" * 64)
            for other_client in (None, wrong_store):
                with self.listener(config, linux_runner=other_client) as address:
                    self.assertEqual(unavailable, self.call(address, "stop", next_lease))
            self.assertEqual(["ensure_started"], [item["action"] for item in runner.requests])

            with self.listener(config, linux_runner=client) as address:
                runner.transform_reply = lambda reply: dict(reply, status="absent")
                self.assertEqual({"status": "absent"}, self.call(address, "query", next_lease))
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual(unavailable, self.call(address, "ensure_started", contender))
                runner.transform_reply = lambda reply: reply
                self.assertEqual({"status": "running"}, self.call(address, "query", next_lease))
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", next_lease))
                self.assertEqual([operation_id], runner.starts)
                self.assertEqual({"error": "stale"}, self.call(address, "ensure_started", request))
                self.assertEqual(unavailable, self.call(address, "artifacts", next_lease))
                self.assertEqual(uncertain, self.call(address, "stop", stop))
                self.assertIs(self.protocol_row(request)["tombstone"], True)

            with self.listener(config, linux_runner=client) as address:
                self.assertEqual(uncertain, self.call(address, "ensure_started", stop))
                self.assertEqual("query", runner.requests[-1]["action"])
                self.assertEqual(unavailable, self.call(address, "artifacts", stop))
                self.assertEqual(unavailable, self.call(address, "ensure_started", contender))
                runner.cleanup_observed.set()

                def with_wrong_identity(reply, field):
                    other = dict(reply["request"]["identity"], **{field: "0" * 64})
                    return dict(reply, request=dict(reply["request"], identity=other))

                for field in ("operation_id", "binding_sha256", "recipe_sha256", "store_id"):
                    with self.subTest(field=field):
                        runner.transform_reply = lambda reply: with_wrong_identity(reply, field)
                        self.assertEqual(uncertain, self.call(address, "stop", stop))
                runner.transform_reply = lambda reply: dict(reply, terminal=dict(reply["terminal"], processes_absent=1))
                self.assertEqual(uncertain, self.call(address, "stop", stop))
                runner.transform_reply = lambda reply: dict(reply, terminal={})
                self.assertEqual(uncertain, self.call(address, "stop", stop))
                self.assertEqual(unavailable, self.call(address, "ensure_started", contender))
                runner.transform_reply = lambda reply: reply
                fsync = os.fsync

                def fail_directory_sync(fd):
                    if stat.S_ISDIR(os.fstat(fd).st_mode):
                        raise OSError("fixture evidence directory sync failure")
                    return fsync(fd)

                # Both attempts write complete evidence bytes, then fail to
                # sync them. A retry must still require a successful sync.
                with patch.object(native_artifact_worker.os, "fsync", side_effect=fail_directory_sync) as sync:
                    self.assertEqual(uncertain, self.call(address, "stop", stop))
                    self.assertEqual(uncertain, self.call(address, "stop", stop))
                self.assertEqual(4, sync.call_count)
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual(unavailable, self.call(address, "ensure_started", contender))

                save = NativeWorker.save

                def fail_terminal_commit(worker, operation, value):
                    if value["status"] != "stopped":
                        return save(worker, operation, value)
                    worker.db.execute("UPDATE operations SET value=? WHERE id=?", (literal(value), operation))
                    raise sqlite3.OperationalError("fixture commit failure with a pending write")

                with patch.object(NativeWorker, "save", fail_terminal_commit):
                    self.assertEqual(uncertain, self.call(address, "stop", stop))
                    self.assertEqual(unavailable, self.call(address, "ensure_started", contender))
                    self.assertEqual("uncertain", self.protocol_row(request)["status"])

                stopped = self.call(address, "stop", stop)
                self.assertEqual("stopped", stopped["status"])
                settled = self.protocol_row(request)
                self.assertEqual(stopped["diagnostic_sha256"], settled["diagnostic_sha256"])
                self.assertEqual("stopped", settled["closure"]["status"])
                self.assertEqual(stopped, self.call(address, "ensure_started", stop))
                self.assertEqual(unavailable, self.call(address, "artifacts", stop))
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", contender))
                self.assertEqual([operation_id, contender["operation_id"]], runner.starts)
                self.assertEqual("stopped", self.call(address, "stop", contender)["status"])

    def test_linux_runner_stop_before_start_is_durable_at_both_ends(self):
        config, request = self.linux_registration()
        with self.linux_runner_listener() as (runner, client):
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"error": "uncertain"}, self.call(address, "stop", request))
                row = self.protocol_row(request)
                self.assertEqual(0, row["starts"])
                self.assertIs(row["tombstone"], True)
                self.assertEqual("stopping", runner.operations[request["operation_id"]][1])
            later = dict(request, guard=dict(request["guard"], epoch=2))
            with self.listener(config, linux_runner=client) as address:
                runner.cleanup_observed.set()
                stopped = self.call(address, "ensure_started", later)
                self.assertEqual("stopped", stopped["status"])
                self.assertEqual(stopped, self.call(address, "query", later))
            self.assertEqual(["stop", "query"], [item["action"] for item in runner.requests])
            self.assertEqual([], runner.starts)

    def test_linux_runner_retries_same_id_when_first_start_never_reaches_backend(self):
        config, request = self.linux_registration()
        with self.linux_runner_listener() as (runner, client):
            runner.drop_before_start = True
            runner.drop_start_reply = False
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"error": "uncertain"}, self.call(address, "ensure_started", request))
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual([], runner.starts)
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"status": "absent"}, self.call(address, "query", request))
                self.assertEqual("uncertain", self.protocol_row(request)["status"])
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))
                self.assertEqual([request["operation_id"]], runner.starts)
                runner.cleanup_observed.set()
                self.assertEqual("stopped", self.call(address, "stop", request)["status"])

    def test_linux_runner_attachment_preserves_legacy_recipe_and_existing_row(self):
        config, request = self.linux_registration()
        with self.listener(config) as address:
            legacy_stop = self.call(address, "stop", request)
            self.assertEqual("stopped", legacy_stop["status"])
        with self.linux_runner_listener() as (runner, client):
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual(legacy_stop, self.call(address, "query", request))
                self.assertEqual(legacy_stop, self.call(address, "stop", request))
            other_spec = dict(config["registration"]["spec"], build_definition_sha256="c" * 64)
            config = dict(config, registration={"spec": other_spec, "files": {}})
            other = dict(request, operation_id="b" * 64, spec=dict(other_spec, build_id="build"))
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"status": "absent"}, self.call(address, "query", other))
            self.assertEqual([], runner.requests)

    def test_linux_runner_refuses_malformed_frames_and_unauthorized_socket_peers(self):
        config, request = self.linux_registration()
        with self.linux_runner_listener() as (runner, client):
            runner.drop_start_reply = False
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))
                uncertain = {"error": "uncertain"}
                client.socket_path.chmod(0o660)
                try:
                    self.assertEqual(uncertain, self.call(address, "query", request))
                    self.assertEqual(1, len(runner.requests))
                finally:
                    client.socket_path.chmod(0o600)
                with patch("linux_android_runner.peer_uid", return_value=os.getuid() + 1) as credential_check:
                    self.assertEqual(uncertain, self.call(address, "query", request))
                credential_check.assert_called_once()
                self.assertEqual(1, len(runner.requests))

                for malformed in (b"\n", b" " * 4097, b"{}\n{}\n", b'{"status":"running","status":"running"}\n'):
                    runner.transform_reply = lambda reply: malformed
                    self.assertEqual(uncertain, self.call(address, "query", request))
                runner.transform_reply = lambda reply: reply
                self.assertEqual({"status": "running"}, self.call(address, "query", request))
                runner.cleanup_observed.set()
                self.assertEqual("stopped", self.call(address, "stop", request)["status"])

    def test_linux_runner_deadline_blocks_start_and_live_guard_allows_stop(self):
        config, request = self.linux_registration()
        expired = dict(request, deadline_ms=now_ms() - 1)
        with self.linux_runner_listener() as (runner, client):
            runner.cleanup_observed.set()
            with self.listener(config, linux_runner=client) as address:
                self.assertEqual({"error": "stale"}, self.call(address, "ensure_started", expired))
                stale = dict(expired, guard=dict(expired["guard"], expires_at=expired["deadline_ms"]))
                self.assertEqual({"error": "stale"}, self.call(address, "stop", stale))
                self.assertEqual([], runner.requests)
                self.assertEqual("stopped", self.call(address, "stop", expired)["status"])
            self.assertEqual(["stop"], [item["action"] for item in runner.requests])
            self.assertEqual([], runner.starts)

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

    def android_recipe(self):
        python = Path(sys.executable).resolve()
        swift = self.root / "inert-host-swift"
        swift.write_text(
            '#!/bin/sh\n[ "$#" -eq 1 ] && [ "$1" = --version ] || exit 2\n'
            '[ "${INERT_PROBE_FAIL:-0}" -eq 0 ] || exit 17\nprintf "inert host Swift\\n"\n'
        )
        swift.chmod(0o700)
        source_root = self.root / "source"
        source = source_root / ANDROID_DRIVER
        source.parent.mkdir(parents=True)
        source.write_bytes(
            b"import pathlib, sys\n"
            b"assert len(sys.argv) == 4 and sys.argv[1] == 'build-retained-v1'\n"
            b"assert pathlib.Path.cwd() == pathlib.Path(sys.argv[2])\n"
            b"pathlib.Path(sys.argv[3]).mkdir()\n"
            b"pathlib.Path(sys.argv[3], 'driver-ran').touch()\n"
        )
        tools = {str(python): digest(python.read_bytes()), str(swift): digest(swift.read_bytes())}
        lock = {"android": {"toolchain": {"tools": {"python": {"path": str(python), "sha256": tools[str(python)]}}}}}
        (source_root / "mixer.lock").write_text(literal(lock))
        files = {str(path.relative_to(source_root)): digest(path.read_bytes())
                 for path in (source, source_root / "mixer.lock")}
        mirrors = {}
        for package in ("swift-asn1", "swift-crypto"):
            mirror = self.root / (package + ".git")
            mirror.mkdir()
            (mirror / "HEAD").write_bytes(b"ref: refs/heads/main\n")
            mirrors[package] = {"url": mirror.as_uri(), "tree_sha256": digest(
                ("HEAD\0" + digest((mirror / "HEAD").read_bytes()) + "\n").encode())}
        developer, pins = {}, {}
        for role in ("host", "android"):
            app = self.root / (role + ".app")
            paths = {
                "Contents/Info.plist": plistlib.dumps({"CFBundleIdentifier": "com.apple.dt.Xcode"}),
                "Contents/version.plist": plistlib.dumps({"ProductBuildVersion": role}),
                "Contents/Developer/usr/bin/xcodebuild": role.encode(),
            }
            for relative, data in paths.items():
                path = app / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                if path.name == "xcodebuild":
                    path.chmod(0o700)
            if role == "host":
                driver = "Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
                target = app / driver
                target.parent.mkdir(parents=True)
                frontend = target.with_name("swift-frontend")
                frontend.write_bytes(swift.read_bytes())
                frontend.chmod(0o700)
                target.symlink_to(frontend.name)
                paths[driver] = swift.read_bytes()
            developer[role] = str(app / "Contents/Developer")
            pins[role] = {relative: digest(data) for relative, data in paths.items()}
        self.enterContext(patch("native_artifact_worker.ANDROID_HOST_SWIFT", str(swift), create=True))
        recipe = dict(self.recipe(), cwd=str(source_root), profile=ANDROID_PROFILE, android_python=str(python),
                      inputs=files, android_host_swift=str(swift), tools=tools, android_mirrors=mirrors,
                      environment={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "DEVELOPER_DIR": developer["host"]},
                      android_developer_dir=developer["android"], android_xcode_pins=pins,
                      package_policy="exact-locked-android-file-mirrors-v1")
        return recipe, files

    def android_registration(self, recipe, files):
        recipe_path = self.root / "recipe.json"
        recipe_path.write_text(literal(recipe))
        recipe_sha = digest(recipe_path.read_bytes())
        tree = digest("".join(p + "\0" + sha + "\n" for p, sha in sorted(files.items())).encode())
        spec = dict(self.spec, platform="android", source={"sha256": tree}, toolchain_lock_sha256=files["mixer.lock"],
                    build_definition_sha256=recipe_sha)
        config = dict(self.config, registration={"spec": spec, "files": files, "root": recipe["cwd"],
                                                 "recipe": str(recipe_path)},
                      policy={"cli": recipe["argv"][0], "recipe_sha256": recipe_sha,
                              **{key: recipe[key] for key in ("environment", "inputs", "tools")}})
        request = dict(self.request, spec=dict(spec, build_id="build"), ref=dict(self.ref, platform="android"))
        return config, request

    def android_cli(self, recipe):
        cli = self.root / "inert-cli"
        cli.write_text(
            '#!/bin/sh\nprintf "%s" mixer-command-receipts-10000000-1000-1000-1000-100000000000'
            ' > "$TMPDIR/cli-closed"\nexit 23\n'
        )
        cli.chmod(0o700)
        recipe["argv"] = [str(cli), "build", "--platform", "android", "--directory", recipe["cwd"]]
        recipe["tools"][str(cli)] = digest(cli.read_bytes())

    def test_android_protocol_mirror_drift_before_spawn_releases_capacity(self):
        recipe, files = self.android_recipe()
        self.android_cli(recipe)
        config, request = self.android_registration(recipe, files)
        later = dict(request, operation_id="e" * 64)
        head = self.root / "swift-asn1.git" / "HEAD"
        original = head.read_bytes()
        verify = NativeWorker.verify

        def drift_after_admission(worker, spec):
            approved = verify(worker, spec)
            if worker.load(request["operation_id"])["status"] == "absent":
                head.write_bytes(b"drift after admission")
            return approved

        def wait_for_closure(address, pending):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                reply = self.call(address, "query", pending)
                if reply != {"status": "running"}:
                    return reply
                time.sleep(0.01)
            self.fail("operation never reached a terminal projection")

        with (patch.object(NativeWorker, "verify", drift_after_admission),
              patch("native_artifact_worker.OwnedBuildProcess", wraps=OwnedBuildProcess) as spawn,
              self.listener(config) as address):
            self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))
            first = wait_for_closure(address, request)
            head.write_bytes(original)
            self.assertEqual("preflight_failed", first.get("status"), first)
            state = self.root / "protocol-state"
            raw = (state / "blobs" / first["diagnostic_sha256"]).read_bytes()
            self.assertEqual(first["diagnostic_sha256"], digest(raw))
            self.assertEqual({
                "operation_id": request["operation_id"],
                "closure": {"closed": True, "started": False, "preflight_failed": True,
                            "android_driver_outcome": "not_started"},
            }, json.loads(raw))
            self.assertFalse((state / request["operation_id"] / "launch.json").exists())
            self.assertFalse((state / ("customer-log-v1-" + request["operation_id"])).exists())
            spawn.assert_not_called()
            self.assertEqual(first, self.call(address, "ensure_started", request))
            self.assertEqual({"status": "running"}, self.call(address, "ensure_started", later))
            deadline = time.monotonic() + 5
            launch = state / later["operation_id"] / "launch.json"
            while not launch.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(launch.is_file())
            stopped = self.call(address, "stop", later)
            while stopped == {"error": "uncertain"} and time.monotonic() < deadline:
                time.sleep(0.01)
                stopped = self.call(address, "stop", later)
            proof = json.loads((state / "blobs" / stopped["diagnostic_sha256"]).read_bytes())
            self.assertEqual(23, proof["closure"]["exit"])
            self.assertTrue(proof["closure"]["cli_reaped"] and proof["closure"]["cli_group_absent"])
            exported = state / ("customer-log-v1-" + later["operation_id"])
            self.assertEqual(0o400, exported.stat().st_mode & 0o777)
            self.assertEqual({
                "version": 1, "operationId": later["operation_id"],
                "sourceSha256": request["spec"]["source"]["sha256"],
                "toolchainLockSha256": request["spec"]["toolchain_lock_sha256"],
                "buildDefinitionSha256": request["spec"]["build_definition_sha256"],
                "cliExitCode": 23, "androidDriver": None,
            }, json.loads(exported.read_bytes()))
            spawn.assert_called_once()
        with self.listener(config) as address:
            self.assertEqual(first, self.call(address, "query", request))

    def test_android_admission_pins_both_selected_xcode_distributions(self):
        recipe, files = self.android_recipe()
        self.android_cli(recipe)
        config, request = self.android_registration(recipe, files)
        self.worker.config = config
        self.assertEqual(recipe, self.worker.verify(request["spec"]))
        host = Path(recipe["environment"]["DEVELOPER_DIR"])
        android = Path(recipe["android_developer_dir"])
        host_alias = self.root / "host-alias"
        host_alias.symlink_to(host, target_is_directory=True)
        missing_host = {"PATH": recipe["environment"]["PATH"]}
        pins = recipe["android_xcode_pins"]
        changed_pins = dict(pins, android=dict(pins["android"], **{"Contents/version.plist": "0" * 64}))
        for name, altered in (
            ("missing_host", dict(recipe, environment=missing_host)),
            ("symlink_host", dict(recipe, environment=dict(recipe["environment"], DEVELOPER_DIR=str(host_alias)))),
            ("missing_pins", {key: value for key, value in recipe.items() if key != "android_xcode_pins"}),
            ("wrong_pin", dict(recipe, android_xcode_pins=changed_pins)),
            ("extra_pin", dict(recipe, android_xcode_pins=dict(pins, host=dict(pins["host"], extra="0" * 64)))),
        ):
            with self.subTest(name=name):
                config, request = self.android_registration(altered, files)
                self.worker.config = config
                with self.assertRaisesRegex(Refusal, "unavailable"):
                    self.worker.verify(request["spec"])
        config, request = self.android_registration(recipe, files)
        self.worker.config = config
        for developer in (host, android):
            endpoint = developer / "usr/bin/xcodebuild"
            with self.subTest(endpoint=endpoint):
                endpoint.chmod(0o600)
                try:
                    with self.assertRaisesRegex(Refusal, "unavailable"):
                        self.worker.verify(request["spec"])
                finally:
                    endpoint.chmod(0o700)
        self.assertEqual(recipe, self.worker.verify(request["spec"]))

    def test_android_real_inert_probe_and_driver_roster(self):
        recipe, files = self.android_recipe()
        python, swift = recipe["android_python"], recipe["android_host_swift"]
        # Exercise the worker's real launch, wait, acknowledgement, and receipt reads.
        # This small CLI stand-in runs only the two inert executables above.
        cli = self.root / "inert-cli.py"
        cli.write_text("""
import json, os, subprocess, sys, time
from pathlib import Path
from uuid import UUID

swift, python, mode, project, _, _ = sys.argv[1:]
tmp = Path(os.environ["TMPDIR"])
root = tmp / "mixer-command-receipts-10000000-1000-1000-1000-100000000000"
snapshot = root / "mixer-verify-20000000-2000-2000-2000-200000000000"

def run(argv, directory, retained, order):
    start = time.monotonic_ns()
    child = subprocess.Popen(argv, cwd=directory, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    stdout, stderr = child.communicate()
    assert child.returncode >= 0 and child.stdout.closed and child.stderr.closed
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        terminal = time.monotonic_ns()
    else:
        raise AssertionError("inert command group was still present")
    facts = dict.fromkeys(("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF",
                          "descriptorsClosed", "ownedGroupAbsent", "released"), True)
    item = dict(facts, schema="mixer.owned-command.2", state="TERMINAL",
                command=argv, retainedInputDirectories=retained, pid=child.pid,
                ownedPGID=child.pid, ownedSession=child.pid, runtimeStartedNS=start,
                terminalNS=terminal, exitCode=child.returncode, groupKillSent=False,
                stdoutBytes=len(stdout), stderrBytes=len(stderr), outputTruncated=False)
    if directory is not None:
        item["directory"] = directory
    # The probe's directory sorts after the driver's directory.
    path = root / ("command-" + str(UUID(int=order)).upper())
    path.mkdir(mode=0o700)
    (path / "receipt.json").write_text(json.dumps(item))
    return child.returncode

exit_code = 23
if mode != "empty":
    root.mkdir(mode=0o700)
    if mode == "probe_failed":
        os.environ["INERT_PROBE_FAIL"] = "1"
    probe_exit = run([swift, "--version"], None, [], 2)
    if probe_exit:
        exit_code = probe_exit
    if not probe_exit and mode == "driver":
        snapshot.mkdir(mode=0o700)
        exit_code = run([python, "-I", "-B", "-S", project + "/Generated/MixerAndroid/android-build.py",
                         "build-retained-v1", project, str(snapshot / "android-build")],
                        project, [str(snapshot), project], 1)
(tmp / "cli-closed").write_text(root.name)
sys.exit(exit_code)
""")
        for mode, expected, roster, exit_code in (
            ("driver", "succeeded", [swift, python], 0),
            ("probe_only", "not_started", [swift], 23),
            ("probe_failed", "not_started", [swift], 17),
            ("empty", "not_started", [], 23),
        ):
            with self.subTest(mode=mode):
                recipe["argv"] = [python, "-I", "-B", "-S", str(cli), swift, python, mode, str(self.root)]
                output = self.root / mode
                result = build(recipe, files, output, self.request, LaunchGate())
                self.assertIsInstance(result, dict, result)
                self.assertEqual(expected, result["android_driver_outcome"])
                self.assertEqual(exit_code, result["exit"])
                self.assertEqual(roster, [item["command"] for item in result["commands"]])
                self.assertEqual((mode == "driver"), "android_driver_exit" in result)
                markers = list((output / "tmp").glob("*/mixer-verify-*/android-build/driver-ran"))
                self.assertEqual(int(mode == "driver"), len(markers))
                self.assertEqual({
                    "cliExitCode": exit_code,
                    "androidDriver": {
                        "exitCode": 0, "stdoutBytes": 0, "stderrBytes": 0,
                        "tailTruncated": False, "phases": [],
                    } if mode == "driver" else None,
                }, result.pop("customer_log"))
                self.assertEqual(result, json.loads((output / "closure.json").read_bytes()))
                self.assertFalse({"artifacts", "manifest_sha256"} & result.keys())

    def test_android_retained_report_and_bound_artifact_response(self):
        operation = self.request["operation_id"]
        project = self.root / "project"
        store = self.root / "protocol-state" / operation / "native"
        store.mkdir(mode=0o700, parents=True)
        cli = self.root / "fixture-cli"
        cli.write_bytes(b"fixture")
        inputs = {
            "lock": "mixer.lock",
            "sdkPins": "Generated/MixerSDK/Package.resolved",
            "platformPins": "Platforms/Android/Package.resolved",
            "generatedDriver": ANDROID_DRIVER,
        }
        source = {"treeSHA256": "6ca2e836f54b414591057bd6dfd397e2988ab123d6f209524c893f14064fdbf3"}
        files = {}
        for name, relative in inputs.items():
            path = project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            data = name.encode()
            path.write_bytes(data)
            files[relative] = digest(data)
            source[name] = {"sha256": files[relative], "sizeBytes": len(data)}
        spec = dict(self.spec, platform="android", toolchain_lock_sha256=files["mixer.lock"])
        config = dict(self.config, registration={"spec": spec, "files": files})
        request = dict(self.request, spec=dict(spec, build_id="build"),
                       ref=dict(self.request["ref"], platform="android"))
        command = ["/fixture/python", str(project / ANDROID_DRIVER)]
        binding = {
            "sourceBefore": source,
            "sourceAfter": source,
            "cliExecutable": {"sha256": digest(cli.read_bytes()), "sizeBytes": cli.stat().st_size},
            "command": command,
        }
        report = dict(formatVersion=1, scope="unsigned-android/local-development", binding=binding,
                      storeDevice=store.stat().st_dev, storeInode=store.stat().st_ino)
        products = (
            ("unsignedAPK", "unsigned_apk", b"A" * 27_795_726),
            ("debugSymbols", "debug_symbols", b"symbols"),
            ("resourceInventory", "resource_inventory", b"inventory"),
        )
        expected = []
        for (name, kind, data), public_kind in zip(products, KINDS, strict=True):
            sha = digest(data)
            artifact = store / sha
            artifact.write_bytes(data)
            artifact.chmod(0o400)
            descriptor = dict(kind=kind, sha256=sha, sizeBytes=len(data), ownedPath=str(artifact))
            report[name] = descriptor
            expected.append(dict(kind=public_kind, sha256=sha, sizeBytes=len(data)))

        manifest = store / ANDROID_MANIFEST

        def publish(value):
            manifest.unlink(missing_ok=True)
            manifest.write_text(literal(value))
            manifest.chmod(0o400)

        def read():
            return retained_android_report(store, project, request["spec"], files, cli,
                                           binding["cliExecutable"]["sha256"], command)

        for change in (
            dict(report, scope="unsigned-simulator/local-development"),
            dict(report, storeInode=report["storeInode"] + 1),
            dict(report, binding=dict(binding, command=["/other/python"])),
            dict(report, binding=dict(binding, sourceAfter=dict(source, treeSHA256="0" * 64))),
            dict(report, unsignedAPK=dict(report["unsignedAPK"], sizeBytes=32 * 1024 * 1024 + 1)),
            dict(report, debugSymbols=report["unsignedAPK"]),
        ):
            publish(change)
            with self.assertRaises(Refusal):
                read()
        publish(report)
        result = read()
        self.assertEqual(expected, result["artifacts"])

        with self.listener(config) as address:
            self.assertEqual({"status": "absent"}, self.call(address, "query", request))
        seed = NativeWorker(config, str(store.parent.parent))
        try:
            seed.save(operation, dict(seed.load(operation), status="native_ready", **result))
        finally:
            seed.close()
        ready = {
            "status": "native_ready", "profile": ANDROID_PROFILE, "platform": "android",
            "operation_id": operation, "artifacts": expected,
        }
        with self.listener(config) as address:
            self.assertEqual(ready, self.call(address, "artifacts", request))
            original = store.with_name("original-native")
            for replacement in ("copy", "symlink"):
                with self.subTest(replacement=replacement):
                    store.rename(original)
                    if replacement == "copy":
                        shutil.copytree(original, store)
                    else:
                        store.symlink_to(original, target_is_directory=True)
                    try:
                        self.assertEqual({"error": "uncertain"}, self.call(address, "artifacts", request))
                    finally:
                        if replacement == "copy":
                            shutil.rmtree(store)
                        else:
                            store.unlink()
                        original.rename(store)
            read_owned = native_artifact_worker.read_owned

            def replace_after_last_read(path, *args, **kwargs):
                data = read_owned(path, *args, **kwargs)
                if Path(path).name == report["resourceInventory"]["sha256"]:
                    store.rename(original)
                    shutil.copytree(original, store)
                return data

            try:
                with patch("native_artifact_worker.read_owned", side_effect=replace_after_last_read):
                    self.assertEqual({"error": "uncertain"}, self.call(address, "artifacts", request))
            finally:
                if original.exists():
                    shutil.rmtree(store)
                    original.rename(store)
            self.assertEqual(ready, self.call(address, "artifacts", request))
            symbols = Path(report["debugSymbols"]["ownedPath"])
            symbols.unlink()
            symbols.write_bytes(b"corrupt")
            symbols.chmod(0o400)
            self.assertEqual({"error": "uncertain"}, self.call(address, "artifacts", request))

    def test_android_profile_is_private_and_requires_separate_tool_pins(self):
        recipe, files = self.android_recipe()
        python, swift = recipe["android_python"], recipe["android_host_swift"]
        tools = recipe["tools"]
        alias = self.root / "swift-alias"
        alias.symlink_to(swift)
        with patch("compiler_worker.Worker.verify", return_value=recipe):
            for platform in ("android", "ios"):
                with self.assertRaisesRegex(Refusal, "unavailable"):
                    self.worker.verify(dict(self.spec, platform=platform))
        with patch("native_artifact_worker.OwnedBuildProcess") as spawn:
            for altered, inputs in (
                (dict(recipe, android_python="python3"), files),
                (dict(recipe, android_host_swift="swift"), files),
                (dict(recipe, android_host_swift=None), files),
                (dict(recipe, android_host_swift=python), files),
                (dict(recipe, android_host_swift=str(alias), tools={**tools, str(alias): tools[swift]}), files),
                (dict(recipe, tools={python: tools[python]}), files),
                (dict(recipe, tools={swift: tools[swift]}), files),
                (dict(recipe, tools={**tools, swift: "0" * 64}), files),
                (dict(recipe, tools={**tools, python: "0" * 64}), files),
                (recipe, {}),
            ):
                with self.subTest(altered=altered, inputs=inputs):
                    self.assertEqual({"closed": True, "started": False, "preflight_failed": True,
                                      "android_driver_outcome": "not_started"},
                                     build(altered, inputs, self.root / "refused", self.request, LaunchGate()))
            launch = LaunchGate()
            launch.cancelled = True
            self.assertEqual({"closed": True, "started": False, "android_driver_outcome": "not_started"},
                             build(recipe, files, self.root / "revoked", self.request, launch))
            spawn.assert_not_called()

    def test_android_constructor_failure_retains_unknown_custody(self):
        recipe, files = self.android_recipe()
        with (patch("native_artifact_worker.OwnedBuildProcess", side_effect=OSError) as spawn,
              patch("native_artifact_worker.group_absent") as probe):
            self.assertIs(BuildUncertainty.CLI_PROCESS_HANDLE_UNAVAILABLE,
                          build(recipe, files, self.root / "constructor-error", self.request, LaunchGate()))
            spawn.assert_called_once()
            probe.assert_not_called()

    def test_android_driver_requires_exact_closed_receipt_roster(self):
        recipe, files = self.android_recipe()
        root_name = "mixer-command-receipts-10000000-1000-1000-1000-100000000000"
        snapshot_name = "mixer-verify-20000000-2000-2000-2000-200000000000"
        unproven = BuildUncertainty.CLI_RESULT_UNPROVEN
        invalid = BuildUncertainty.NESTED_RECEIPT_INVALID
        swift = recipe["android_host_swift"]
        cancel = {"stopReason": "cancelled", "exitCode": 15, "groupTerminateSent": True}
        deadline = {"stopReason": "runtime-deadline", "groupKillSent": True}
        cases = (
            ("no_commands", 23, None, None, False, "not_started"),
            ("no_commands_zero", 0, None, None, False, unproven),
            ("no_commands_signalled", -15, None, None, False, unproven),
            ("probe_failed", 1, {"exitCode": 23}, None, False, "not_started"),
            ("probe_deadline", 1, deadline, None, False, "not_started"),
            ("probe_cancelled", 1, cancel, None, True, "not_started"),
            ("cancel_after_probe", 1, {}, None, True, "not_started"),
            ("probe_cancel_without_worker_stop", 1, cancel, None, False, unproven),
            ("probe_only_zero", 0, {}, None, False, unproven),
            ("probe_held", 1, {}, None, False, invalid),
            ("probe_released_false", 1, {"released": False}, None, False, invalid),
            ("probe_wrong_tool", 1, {"command": ["/usr/bin/swift", "--version"]}, None, False, unproven),
            ("probe_wrong_args", 1, {"command": [swift, "-version"]}, None, False, unproven),
            ("probe_wrong_cwd", 1, {"directory": "/"}, None, False, unproven),
            ("probe_wrong_retention", 1, {"retainedInputDirectories": ["/"]}, None, False, unproven),
            ("driver_without_probe", 1, None, {}, False, unproven),
            ("driver_after_failed_probe", 1, {"exitCode": 23}, {}, False, unproven),
            ("driver_after_cancelled_probe", 1, cancel, {}, True, unproven),
            ("driver_failed", 1, {}, {"exitCode": 23}, False, "failed"),
            ("driver_deadline", 1, {}, deadline, False, "failed"),
            ("driver_bad_log_stats", 0, {}, {"stderrBytes": 2**32 + 1}, False, "succeeded"),
            ("cancel", 1, {}, cancel, True, "cancelled"),
            ("success", 0, {}, {}, False, "succeeded"),
            ("cli_failed_after_driver", 1, {}, {}, False, "succeeded"),
            ("stop_after_driver", 0, {}, {}, True, "succeeded"),
            ("duplicate_driver", 1, {}, {}, False, unproven),
            ("duplicate_probe", 1, {}, None, False, unproven),
            ("reordered", 1, {"runtimeStartedNS": 50, "terminalNS": 60}, {}, False, unproven),
            ("overlap", 1, {"terminalNS": 35}, {}, False, unproven),
            ("tied_boundary", 1, {"terminalNS": 30}, {}, False, unproven),
            ("missing_start", 1, {"runtimeStartedNS": None}, {}, False, invalid),
            ("backwards_clock", 1, {}, {"terminalNS": 29}, False, invalid),
            ("wrong_python", 1, {}, {}, False, unproven),
            ("wrong_driver", 1, {}, {}, False, unproven),
            ("wrong_staging", 0, {}, {}, False, unproven),
            ("wrong_retention", 0, {}, {"retainedInputDirectories": []}, False, unproven),
            ("wrong_cwd", 0, {}, {"directory": "/"}, False, unproven),
            ("cli_zero_driver_failed", 0, {}, {"exitCode": 23}, False, unproven),
            ("cancel_without_worker_stop", 1, {}, cancel, False, unproven),
            ("missing_exit", 0, {}, {"exitCode": None}, False, invalid),
            ("missing_eof", 1, {}, {"stderrEOF": None}, False, invalid),
            ("driver_held", 1, {}, {}, False, invalid),
        )
        for name, code, probe_fields, driver_fields, cancelled, expected in cases:
            with self.subTest(name=name):
                launch = LaunchGate()

                def fixture(_argv, *, cwd, env, **kwargs):
                    tmp = Path(env["TMPDIR"])
                    (tmp / "cli-closed").write_text(root_name)

                    def receipt(index, fields, **command_facts):
                        pid = 124 + index
                        item = dict.fromkeys(
                            ("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF",
                             "descriptorsClosed", "ownedGroupAbsent", "released"), True)
                        item.update(schema="mixer.owned-command.2", state="TERMINAL", pid=pid,
                                    ownedPGID=pid, ownedSession=pid, exitCode=0, groupKillSent=False,
                                    stdoutBytes=220, stderrBytes=70, outputTruncated=True,
                                    output="SwiftCompile /private/source.swift\nEXAMPLE_PRIVATE_ENV_TOKEN=opaque",
                                    **command_facts)
                        item.update(fields)
                        nested = tmp / root_name / f"command-{index}"
                        nested.mkdir(parents=True, mode=0o700)
                        (nested / "receipt.json").write_text(literal({
                            key: value for key, value in item.items() if value is not None
                        }))
                        if (name, index) in (("probe_held", 0), ("driver_held", 1)):
                            (nested / "HOLD.json").write_text("{}")

                    if probe_fields is not None:
                        probe = dict(command=[swift, "--version"], retainedInputDirectories=[],
                                     runtimeStartedNS=10, terminalNS=20)
                        receipt(0, probe_fields, **probe)
                        if name == "duplicate_probe":
                            receipt(1, {"runtimeStartedNS": 30, "terminalNS": 40}, **probe)
                    if driver_fields is not None:
                        snapshot = tmp / root_name / snapshot_name
                        command = [recipe["android_python"], "-I", "-B", "-S", str(cwd / ANDROID_DRIVER),
                                   "build-retained-v1", str(cwd), str(snapshot / "android-build")]
                        if name == "wrong_python":
                            command[0] = str(cwd / "unexpected-python")
                        if name == "wrong_driver":
                            command[4] = str(cwd / "other.py")
                        if name == "wrong_staging":
                            command[-1] = str(tmp / "android-build")
                        driver = dict(command=command, directory=str(cwd),
                                      retainedInputDirectories=[str(snapshot), str(cwd)],
                                      runtimeStartedNS=30, terminalNS=40)
                        receipt(1, driver_fields, **driver)
                        if name == "duplicate_driver":
                            receipt(2, {"runtimeStartedNS": 50, "terminalNS": 60}, **driver)

                    def wait(timeout):
                        if cancelled:
                            with launch.lock:
                                launch.cancelled = True
                                launch.request_cli_stop()
                        return code

                    return Mock(pid=123, wait=wait)

                output = self.root / name
                with (patch("native_artifact_worker.OwnedBuildProcess", side_effect=fixture),
                      patch("native_artifact_worker.group_absent", return_value=True)):
                    result = build(recipe, files, output, self.request, launch)
                if isinstance(expected, BuildUncertainty):
                    self.assertIs(expected, result)
                    self.assertFalse((output / "closure.json").exists())
                else:
                    self.assertEqual(expected, result["android_driver_outcome"])
                    self.assertEqual(driver_fields is not None, "android_driver_exit" in result)
                    self.assertTrue(result["closed"] and result["cli_reaped"] and result["cli_group_absent"])
                    if name == "driver_bad_log_stats":
                        self.assertNotIn("customer_log", result)
                    else:
                        self.assertEqual({
                            "cliExitCode": code,
                            "androidDriver": {
                                "exitCode": driver_fields.get("exitCode", 0),
                                "stdoutBytes": 220, "stderrBytes": 70,
                                "tailTruncated": True, "phases": [],
                            } if driver_fields is not None else None,
                        }, result.pop("customer_log"))
                    self.assertEqual(result, json.loads((output / "closure.json").read_bytes()))
                    self.assertFalse({"preflight_failed", "artifacts", "manifest_sha256"} & result.keys())

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


IOS_CLI_FIXTURE = """
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

tmp = Path(os.environ["TMPDIR"])
store = Path(sys.argv[-1])
mode = Path("mixer.lock").read_text()
(tmp / "fixture-cli-pid").write_text(str(os.getpid()))
basename = "mixer-command-receipts-10000000-1000-1000-1000-100000000000"


def write(path, value):
    path.write_text(json.dumps(value))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def wait_for(names):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        for name in names:
            if (tmp / name).is_file():
                return name
        time.sleep(.01)
    raise RuntimeError("Fixture barrier timed out")


if mode == "preflight":
    (tmp / "cli-closed").write_text(basename)
    sys.exit(23)

command = ["/usr/bin/xcodebuild", "CODE_SIGNING_ALLOWED=NO", "generic/platform=iOS Simulator"]
child_code = '''
import pathlib, sys, time
tmp, mode = pathlib.Path(sys.argv[1]), sys.argv[2]
until = time.monotonic() + 12
while time.monotonic() < until:
    if (tmp / 'cancel-requested').is_file():
        sys.exit(24)
    if (tmp / 'release-nested').is_file():
        print('inert output')
        sys.exit(23 if mode == 'failure' else 0)
    time.sleep(.01)
sys.exit(70)
'''
child = subprocess.Popen([sys.executable, "-IB", "-c", child_code, str(tmp), mode],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
pid = child.pid
(tmp / "fixture-nested-pid").write_text(str(pid))

store.mkdir()
artifacts = []
for kind in ("unsigned_native_binary", "debug_symbols", "resource_inventory"):
    data = kind.encode()
    path = store / sha(data)
    path.write_bytes(data)
    path.chmod(0o400)
    artifacts.append(dict(kind=kind, ownedPath=str(path), sizeBytes=len(data), sha256=path.name))
manifest = store / "native-build.json"
write(manifest, {
    "formatVersion": 2, "scope": "unsigned-simulator/local-development",
    "commandResult": {"exitCode": 0, "output": "SwiftCompile inert"},
    "binding": {"command": command, "lockSHA256": sha(mode.encode()),
                "authoritativeSourceDigest": sha(("mixer.lock" + chr(0) + sha(mode.encode()) + chr(10)).encode()),
                "cliExecutableSHA256": sha(Path(sys.argv[0]).read_bytes()),
                "environment": {key: os.environ[key] for key in ("PATH", "TMPDIR", "CFFIXED_USER_HOME")},
                "resourceInventoryPolicy": "retained-app-files-v1"},
    "nativeProduct": {"nativeBinary": artifacts[0], "debugSymbols": artifacts[1]},
    "resourceInventory": artifacts[2],
})
manifest.chmod(0o400)
observed, status = os.waitpid(pid, 0)
child.returncode = code = os.waitstatus_to_exitcode(status)
if observed != pid or code not in (0, 23, 24):
    raise RuntimeError("Fixture child not positively reaped")
with child.stdout, child.stderr:
    raw_out, raw_err = child.stdout.read(), child.stderr.read()
try:
    os.killpg(pid, 0)
except ProcessLookupError:
    pass
else:
    raise RuntimeError("Fixture nested group is still present")
cancelled = code == 24
directory = tmp / basename / "command-fixture"
directory.mkdir(parents=True)
write(directory / "receipt.json", {
    **dict.fromkeys(("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF",
                     "descriptorsClosed", "ownedGroupAbsent", "released"), True),
    "schema": "mixer.owned-command.2", "command": command, "state": "TERMINAL",
    "exitCode": code, "stdoutBytes": len(raw_out), "stderrBytes": len(raw_err), "outputTruncated": False,
    "pid": pid, "ownedPGID": pid, "ownedSession": pid, "runtimeStartedNS": 1, "terminalNS": 2,
    "stopReason": "cancelled" if cancelled else None,
})
if mode != "no-ack":
    (tmp / "cli-closed").write_text(basename)
wait_for(("release-cli",))
sys.exit(code)
"""


@unittest.skipUnless(sys.platform == "darwin", "Independent iOS custody uses macOS")
class IOSCustodySocketTest(unittest.TestCase):
    call = NativeWorkerTest.call

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="mixer-l07-inert-")).resolve()
        self.state = self.root / "state"
        self.operation = "a" * 64
        self.output = self.state / self.operation
        self.tmp = self.output / "tmp"
        self.log = self.state / ("customer-log-v1-" + self.operation)
        self.children = []
        self.addCleanup(self.cleanup_fixture)
        self.entry = Path(ios_build_custody.__file__)
        self.python = [sys.executable, "-IB"] + (["-O"] if sys.flags.optimize else [])

    def prepare(self, mode="success"):
        source = self.root / "source"
        source.mkdir()
        (source / "mixer.lock").write_text(mode)
        lock_sha = digest(mode.encode())
        files = {"mixer.lock": lock_sha}
        cli = self.root / "inert-cli"
        cli.write_text("#!" + sys.executable + " -I\n" + IOS_CLI_FIXTURE)
        cli.chmod(0o500)
        # Read the system stub's bytes for ordinary recipe verification. The
        # only executable used for the build is the pinned inert fixture.
        xcode = Path("/usr/bin/xcodebuild")
        tools = {str(cli): digest(cli.read_bytes()), str(xcode): digest(xcode.read_bytes())}
        env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
        recipe = dict(profile="unsigned-ios-simulator-v1", timeout_seconds=25,
                      argv=[str(cli), "build", "--platform", "ios", "--directory", str(source)],
                      cwd=str(source), environment=env,
                      package_policy="exact-owned-local-manifests-no-external-packages",
                      inputs=files, tools=tools)
        recipe_path = self.root / "recipe.json"
        recipe_path.write_text(literal(recipe))
        recipe_sha = digest(recipe_path.read_bytes())
        scope = dict(organization_id="organization", project_id="project", application_id="app", platform="ios")
        spec = dict(scope, source={"sha256": digest(f"mixer.lock\0{lock_sha}\n".encode())},
                    toolchain_lock_sha256=lock_sha, build_definition_sha256=recipe_sha)
        _, pins = ios_build_custody.runtime_image()
        self.config = dict(worker_id="native", token=secrets.token_hex(24), tenant="organization",
                           registration=dict(spec=spec, root=str(source), recipe=str(recipe_path), files=files),
                           policy=dict(cli=str(cli), recipe_sha256=recipe_sha, environment=env,
                                       inputs=files, tools=tools),
                           ios_custodian=dict(operation_id=self.operation, runtime_sha256=pins))
        self.request = dict(operation_id=self.operation, spec=dict(spec, build_id="build"),
                            ref=dict(scope, build_id="build", fence=1, attempt=1),
                            deadline_ms=now_ms() + 30_000,
                            guard=dict(record_id="record", epoch=1, revision=1,
                                       owner_id="original", expires_at=now_ms() + 25_000))
        self.fresh = dict(self.request, guard=dict(self.request["guard"], epoch=2, owner_id="replacement"))

    def launch(self, name, action, config=None, wrapper=None):
        config_path = self.root / (name + ".json")
        data = literal(config or self.config).encode()
        config_path.write_bytes(data)
        args = [action, str(config_path), digest(data), str(self.state)]
        entry = [str(self.entry)] if wrapper is None else ["-c", wrapper, str(self.entry)]
        with (self.root / (name + ".log")).open("xb") as log:
            proc = OwnedBuildProcess(self.python + entry + args, cwd=self.root, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=log, start_new_session=True)
        self.children.append((proc, action))
        return proc

    def inject_observer(self, injection):
        wrapper = """
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("ios_build_custody", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
bootstrap = module.bootstrap

def instrument(config):
    native = bootstrap(config)
    exec(INJECTION, dict(globals(), native=native))
    return native

module.bootstrap = instrument
raise SystemExit(module.main(sys.argv[2:]))
"""
        return self.launch("observer", "observe", wrapper="INJECTION = " + repr(injection) + wrapper)

    def listen(self, name="worker", config=None, request=None):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            address = listener.getsockname()
        proc = self.launch(name, "worker", dict(config or self.config, port=address[1]))

        def ready():
            try:
                return self.call(address, "query", request or self.request)
            except ConnectionRefusedError:
                return None

        self.wait_for("worker socket", ready)
        return proc, address

    def wait_for(self, label, probe, seconds=7):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = probe()
            if value:
                return value
            time.sleep(.015)
        self.fail("Timed out waiting for " + label)

    def collect(self, proc, expected=None, seconds=9):
        def reap():
            if proc.returncode is None:
                pid, status = os.waitpid(proc.pid, os.WNOHANG)
                if pid == proc.pid:
                    proc.returncode = os.waitstatus_to_exitcode(status)
            return proc.returncode is not None

        self.wait_for("positive direct reap", reap, seconds)
        self.assertTrue(native_artifact_worker.group_absent(proc.pid))
        if expected is not None:
            if expected != proc.returncode:
                logs = {p.name: p.read_text(errors="replace") for p in self.root.glob("*.log")}
                self.fail(f"Expected {expected}, got {proc.returncode}: {logs}")

    def cleanup_fixture(self):
        (self.root / "release-preparation").touch()
        if self.tmp.is_dir():
            for name in ("release-nested", "release-cli"):
                (self.tmp / name).touch()
        for proc, action in self.children:
            if proc.returncode is None and action == "worker":
                os.kill(proc.pid, signal.SIGKILL)
            self.collect(proc, seconds=28)
        for name in ("fixture-cli-pid", "fixture-nested-pid"):
            path = self.tmp / name
            if path.is_file():
                self.assertTrue(native_artifact_worker.group_absent(int(path.read_text())))
        for name in ("inert-pid", "constructor-pid"):
            marker = self.root / name
            if marker.is_file():
                pid = int(marker.read_text())
                self.wait_for("owned child group absence", lambda: native_artifact_worker.group_absent(pid))
        shutil.rmtree(self.root)

    def ledger(self, query):
        database = self.state / "operations.sqlite"
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
            return db.execute(query, (self.operation,)).fetchone()

    def row(self):
        return json.loads(self.ledger("SELECT value FROM operations WHERE id=?")[0])

    def claim(self):
        return self.ledger("""SELECT guard, parent_pid, launch, terminal, uncertain
                              FROM ios_custody_claims WHERE operation=?""")

    def held(self, address, request):
        self.assertEqual({"error": "uncertain"}, self.call(address, "query", request))
        self.assertEqual({"error": "uncertain"}, self.call(address, "ensure_started", request))
        self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", request))
        self.assertEqual((1, "uncertain"), (self.row()["starts"], self.row()["status"]))
        self.assertFalse(self.log.exists())
        self.assertEqual({"error": "unavailable"},
                         self.call(address, "ensure_started", dict(request, operation_id="b" * 64)))

    def diagnostic(self, reply):
        sha = reply["diagnostic_sha256"]
        data = (self.state / "blobs" / sha).read_bytes()
        self.assertEqual(sha, digest(data))
        return json.loads(data)["closure"]

    def test_fresh_guard_reconciles_after_ack_and_positive_reap(self):
        self.prepare()
        worker, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        self.assertIsNone(self.claim())
        self.assertFalse(self.output.exists())
        observer = self.launch("observer", "observe")
        claim = self.wait_for("one CLI launch", lambda: (row := self.claim()) and row[2] and row)
        self.assertEqual(self.request["guard"], json.loads(claim[0]))
        outer = json.loads(claim[2])
        self.assertEqual(observer.pid, claim[1])
        self.assertEqual(outer["pid"], os.getpgid(outer["pid"]))
        self.collect(self.launch("duplicate", "observe"), 3)
        self.assertEqual(claim, self.claim())

        self.wait_for("staged artifact manifest", (self.output / "native" / "native-build.json").is_file)
        os.kill(worker.pid, signal.SIGKILL)
        self.collect(worker, -signal.SIGKILL)
        _, replacement = self.listen("replacement")
        self.held(replacement, self.fresh)
        child_pid = int((self.tmp / "fixture-nested-pid").read_text())
        self.assertEqual(child_pid, os.getpgid(child_pid))
        self.assertEqual({"error": "stale"}, self.call(replacement, "query", self.request))
        (self.tmp / "release-nested").touch()
        self.wait_for("nested acknowledgement", (self.tmp / "cli-closed").is_file)
        self.assertTrue(native_artifact_worker.group_absent(child_pid))
        self.assertEqual(outer["pid"], os.getpgid(outer["pid"]))
        self.assertEqual(claim, self.claim())
        self.held(replacement, self.fresh)

        (self.tmp / "release-cli").touch()
        self.collect(observer, 0)
        self.assertTrue(native_artifact_worker.group_absent(outer["pid"]))
        self.assertEqual({"status": "running"}, self.call(replacement, "query", self.fresh))
        artifacts = self.call(replacement, "artifacts", self.fresh)
        self.assertEqual({"status": "native_ready", "artifacts": [
            {"kind": kind, "sha256": digest(kind.encode()), "sizeBytes": len(kind)} for kind in KINDS
        ]}, artifacts)
        self.assertEqual(0, json.loads(self.log.read_bytes())["compiler"]["exitCode"])
        row = self.row()
        self.assertEqual(1, row["starts"])
        self.assertEqual(self.fresh["guard"], row["guard"])
        self.assertEqual(self.request["guard"], row["ios_custody"]["guard"])
        self.assertEqual("succeeded", row["closure"]["ios_outcome"])
        self.assertEqual(claim[:3], self.claim()[:3])
        self.collect(self.launch("duplicate-after", "observe"), 3)
        self.assertEqual({"status": "closed"}, self.call(replacement, "shutdown"))

    def test_revised_guard_during_preparation_never_launches(self):
        self.prepare()
        revised = dict(self.request, guard=dict(self.request["guard"], revision=2))
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        # Pause the separately started observer after it durably claims the
        # original guard, while leaving the socket and SQLite boundary intact.
        observer = self.inject_observer("""
import time
prepare = native.prepare_build
def pause(*args):
    Path("preparing").touch()
    deadline = time.monotonic() + 8
    while not Path("release-preparation").is_file():
        if time.monotonic() >= deadline:
            raise TimeoutError("Preparation barrier")
        time.sleep(.01)
    return prepare(*args)
native.prepare_build = pause
""")
        self.wait_for("claimed preparation", (self.root / "preparing").is_file)
        self.assertEqual(self.request["guard"], json.loads(self.claim()[0]))
        self.assertEqual({"status": "running"}, self.call(address, "query", revised))
        (self.root / "release-preparation").touch()
        self.collect(observer, 0)
        self.assertFalse((self.tmp / "fixture-cli-pid").exists())
        self.assertIsNone(self.claim()[2])
        refused = self.call(address, "ensure_started", revised)
        self.assertEqual("preflight_failed", refused["status"])
        self.assertEqual({"not_started": "guard_changed"}, self.diagnostic(refused)["ios_custody"])
        self.assertFalse(self.log.exists())
        self.assertEqual(1, self.row()["starts"])
        self.collect(self.launch("duplicate", "observe"), 3)

    def constructor_crosses_deadline(self, address, deadline):
        observer = self.inject_observer(f"""
import time
spawn = native.OwnedBuildProcess
def delayed(*args, **kwargs):
    until = time.monotonic() + 3
    while native.now_ms() <= {deadline}:
        if time.monotonic() >= until:
            raise TimeoutError("Constructor deadline control")
        time.sleep(.005)
    proc = spawn(*args, **kwargs)
    Path("constructor-pid").write_text(str(proc.pid))
    return proc
native.OwnedBuildProcess = delayed
""")
        self.collect(observer)
        self.assertTrue((self.root / "constructor-pid").is_file())
        started = (self.tmp / "fixture-cli-pid").is_file
        if observer.returncode == 74:
            self.wait_for("late CLI fixture marker", started, seconds=1)
        self.assertFalse(started(), "CLI entered after the admission window")
        self.assertEqual(0, observer.returncode)
        failed = self.call(address, "query", self.fresh)
        self.assertEqual("preflight_failed", failed["status"])
        self.assert_inert_closure(failed, "preflight_failed", "admission_expired")

    def test_original_guard_expires_inside_constructor(self):
        self.prepare("preflight")
        deadline = now_ms() + 1_500
        self.request["guard"]["expires_at"] = deadline
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        self.constructor_crosses_deadline(address, deadline)

    def test_operation_deadline_expires_inside_constructor(self):
        self.prepare("preflight")
        deadline = now_ms() + 1_500
        self.request["deadline_ms"] = self.fresh["deadline_ms"] = deadline
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        self.constructor_crosses_deadline(address, deadline)

    def assert_inert_closure(self, reply, status, reason):
        self.assertEqual(status, reply["status"])
        closure = self.diagnostic(reply)
        self.assertFalse(closure["started"])
        terminal = closure["ios_custody"]
        self.assertEqual(reason, terminal["not_started"])
        outer = terminal["inert"]
        identity = json.loads(self.claim()[2])
        self.assertEqual(identity["pid"], identity["pgid"])
        self.assertEqual(identity["pid"], identity["sid"])
        self.assertEqual(dict(identity, parent_pid=self.claim()[1], exit=0, direct_child_reaped=True,
                              group_absent=True, descriptors_closed=True), outer)
        self.assertFalse((self.tmp / "fixture-cli-pid").exists())
        self.assertFalse(self.log.exists())

    def test_parent_release_wakes_launcher_after_guard_expires(self):
        self.prepare("preflight")
        deadline = now_ms() + 1_500
        self.request["guard"]["expires_at"] = deadline
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        observer = self.inject_observer(rf"""
import time
spawn = native.OwnedBuildProcess
def delay_launcher(args, **kwargs):
    args = list(args)
    script = args.index("-c") + 1
    prefix = (
        "import os, time\n"
        "original_read = os.read\n"
        "def record_token(fd, count):\n"
        "    token = original_read(fd, count)\n"
        "    with open('launcher-token', 'wb') as handle:\n"
        "        handle.write(token)\n"
        "    return token\n"
        "os.read = record_token\n"
        "while time.time_ns() // 1_000_000 <= {deadline}: time.sleep(.005)\n"
    )
    args[script] = prefix + args[script]
    return spawn(args, **kwargs)
native.OwnedBuildProcess = delay_launcher
""")
        self.collect(observer, 0)
        self.assertEqual(b"\x01", (self.output / "project" / "launcher-token").read_bytes())
        self.assert_inert_closure(self.call(address, "query", self.fresh), "preflight_failed", "admission_expired")

    def test_stop_committed_after_inert_constructor_before_release(self):
        self.prepare("preflight")
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        observer = self.inject_observer("""
import time
spawn = native.OwnedBuildProcess
def pause(*args, **kwargs):
    proc = spawn(*args, **kwargs)
    Path("constructor-pid").write_text(str(proc.pid))
    until = time.monotonic() + 3
    while not Path("release-preparation").is_file() and time.monotonic() < until:
        time.sleep(.005)
    return proc
native.OwnedBuildProcess = pause
""")
        self.wait_for("inert constructor", (self.root / "constructor-pid").is_file)
        self.assertEqual({"error": "uncertain"}, self.call(address, "stop", self.request))
        self.assertTrue(self.row()["tombstone"])
        self.assertIsNone(self.claim()[2])
        (self.root / "release-preparation").touch()
        self.collect(observer, 0)
        stopped = self.call(address, "query", self.fresh)
        self.assert_inert_closure(stopped, "stopped", "stopped_before_launch")
        self.assertEqual(stopped, self.call(address, "stop", self.fresh))

    def failed_inert_identity_or_journal(self, fail_identity):
        self.prepare("preflight")
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        if not fail_identity:
            with closing(sqlite3.connect(self.state / "operations.sqlite")) as db, db:
                db.execute("""CREATE TRIGGER refuse_launch BEFORE UPDATE OF launch ON ios_custody_claims
                              BEGIN SELECT RAISE(ABORT, 'injected launch write failure'); END""")
        observer = self.inject_observer(f"""
import os, time
spawn = native.OwnedBuildProcess
waitpid = os.waitpid
def inert(args, **kwargs):
    kwargs.pop("pass_fds", None)
    program = "pass" if {fail_identity} else "import time; time.sleep(.35)"
    proc = spawn([sys.executable, "-IB", "-c", program], **kwargs)
    Path("inert-pid").write_text(str(proc.pid))
    if {fail_identity}:
        until = time.monotonic() + 3
        while os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOWAIT | os.WNOHANG) is None:
            if time.monotonic() >= until:
                raise TimeoutError("Inert exit barrier")
            time.sleep(.005)
        def missing(pid):
            if pid == proc.pid:
                raise ProcessLookupError(3, "injected ESRCH after inert exit")
            return getpgid(pid)
        getpgid = os.getpgid
        os.getpgid = missing
    return proc

def observe_reap(pid, flags):
    outcome = waitpid(pid, flags)
    if outcome[0] == pid:
        Path("inert-reaped").write_text(str(pid))
    return outcome
native.OwnedBuildProcess = inert
os.waitpid = observe_reap
""")
        self.collect(observer, 74)
        pid = int((self.root / "inert-pid").read_text())
        self.wait_for("inert child group absence", lambda: native_artifact_worker.group_absent(pid))
        self.assertFalse((self.tmp / "fixture-cli-pid").exists())
        self.assertEqual((None, None, 1), self.claim()[2:])
        self.held(address, self.fresh)
        marker = self.root / "inert-reaped"
        self.assertTrue(marker.exists(), "observer abandoned the exact child without a matching waitpid")
        self.assertEqual(pid, int(marker.read_text()))
        self.assertEqual({"status": "closed"}, self.call(address, "shutdown"))

    def test_exited_inert_child_with_missing_group_identity_is_reaped(self):
        self.failed_inert_identity_or_journal(fail_identity=True)

    def test_failed_launch_record_keeps_exact_inert_child_on_reap_path(self):
        self.failed_inert_identity_or_journal(fail_identity=False)

    def test_replacement_with_moved_root_cannot_stop_existing_claim(self):
        self.prepare("preflight")
        worker, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        shutil.copytree(self.config["registration"]["root"], self.root / "moved-source")
        config = dict(self.config, registration=dict(self.config["registration"], root=str(self.root / "moved-source")))
        self.assertEqual({"status": "closed"}, self.call(address, "shutdown"))
        self.collect(worker, 0)
        before = self.row()
        _, replacement = self.listen("replacement", config)
        self.assertEqual({"error": "uncertain"}, self.call(replacement, "stop", self.fresh))
        self.assertFalse(self.row().get("tombstone"), "replacement fenced another configuration's operation")
        for action in ("query", "ensure_started", "artifacts"):
            self.assertEqual({"error": "uncertain"}, self.call(replacement, action, self.fresh))
        self.assertEqual(before, self.row())
        self.assertIsNone(self.claim())
        self.assertFalse(self.output.exists())
        self.assertEqual({"status": "closed"}, self.call(replacement, "shutdown"))
        _, original = self.listen("original")
        self.assertEqual({"status": "closed"}, self.call(original, "shutdown"))

    def test_stop_tombstone_wins_and_waits_for_both_closures(self):
        self.prepare()
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        observer = self.launch("observer", "observe")
        self.wait_for("staged artifact manifest", (self.output / "native" / "native-build.json").is_file)
        self.assertEqual({"error": "uncertain"}, self.call(address, "stop", self.fresh))
        self.wait_for("cancellation acknowledgement", (self.tmp / "cli-closed").is_file)
        self.assertTrue((self.tmp / "cancel-requested").is_file())
        self.assertTrue(self.row()["tombstone"])
        self.held(address, self.fresh)
        (self.tmp / "release-cli").touch()
        self.collect(observer, 0)
        stopped = self.call(address, "query", self.fresh)
        self.assertEqual("stopped", stopped["status"])
        closure = self.diagnostic(stopped)
        self.assertEqual("cancelled", closure["ios_outcome"])
        self.assertTrue(closure["ios_custody"]["outer"]["direct_child_reaped"])
        self.assertEqual(stopped, self.call(address, "stop", self.fresh))
        self.assertEqual(stopped, self.call(address, "ensure_started", self.fresh))
        self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.fresh))
        self.assertNotIn("artifacts", self.row())
        self.assertTrue(self.log.is_file())

    def test_closed_compiler_failure_is_neither_success_nor_stop(self):
        self.prepare("failure")
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        observer = self.launch("observer", "observe")
        self.wait_for("staged artifact manifest", (self.output / "native" / "native-build.json").is_file)
        (self.tmp / "release-nested").touch()
        (self.tmp / "release-cli").touch()
        self.collect(observer, 0)
        failed = self.call(address, "query", self.fresh)
        self.assertEqual("build_failed", failed["status"])
        self.assertEqual("build_failed", self.diagnostic(failed)["ios_outcome"])
        self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.fresh))
        self.assertFalse(self.row().get("tombstone"))
        self.assertEqual(23, json.loads(self.log.read_bytes())["compiler"]["exitCode"])

    def test_parent_reap_without_nested_ack_keeps_capacity_and_data_held(self):
        self.prepare("no-ack")
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        observer = self.launch("observer", "observe")
        self.wait_for("staged artifact manifest", (self.output / "native" / "native-build.json").is_file)
        (self.tmp / "release-nested").touch()
        (self.tmp / "release-cli").touch()
        self.collect(observer, 74)
        self.assertIsNone(self.claim()[3])
        self.assertEqual(1, self.claim()[4])
        self.held(address, self.fresh)
        self.collect(self.launch("duplicate", "observe"), 3)
        self.assertEqual({"status": "closed"}, self.call(address, "shutdown"))
        later = dict(self.fresh, operation_id="b" * 64)
        options = dict(self.config["ios_custodian"], operation_id=later["operation_id"])
        _, rearmed = self.listen("rearmed", dict(self.config, ios_custodian=options), later)
        self.assertEqual({"error": "unavailable"}, self.call(rearmed, "ensure_started", later))

    def test_ordinary_preflight_failure_has_ack_and_parent_closure(self):
        self.prepare("preflight")
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        self.collect(self.launch("observer", "observe"), 0)
        failed = self.call(address, "query", self.fresh)
        self.assertEqual("preflight_failed", failed["status"])
        closure = self.diagnostic(failed)
        self.assertEqual([], closure["commands"])
        self.assertTrue(closure["ios_custody"]["outer"]["direct_child_reaped"])
        self.assertIsNone(json.loads(self.log.read_bytes())["compiler"])
        self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", self.fresh))

    def test_stop_before_observer_admission_cannot_launch(self):
        self.prepare()
        _, address = self.listen()
        self.assertEqual({"status": "running"}, self.call(address, "ensure_started", self.request))
        self.assertEqual({"error": "uncertain"}, self.call(address, "stop", self.fresh))
        self.collect(self.launch("observer", "observe"), 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.request["guard"], json.loads(self.claim()[0]))
        stopped = self.call(address, "ensure_started", self.fresh)
        self.assertEqual("stopped", stopped["status"])
        self.assertEqual({"not_started": "stopped_before_launch"}, self.diagnostic(stopped)["ios_custody"])

    def test_runtime_rejects_wrong_worker_and_helper_pins(self):
        self.prepare()
        for key in ("native_artifact_worker", "ios_build_custody", "compiler_worker"):
            options = dict(self.config["ios_custodian"])
            options["runtime_sha256"] = dict(options["runtime_sha256"], **{key: "0" * 64})
            config = dict(self.config, ios_custodian=options, port=0)
            self.collect(self.launch(key, "worker", config), 1)
            self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
