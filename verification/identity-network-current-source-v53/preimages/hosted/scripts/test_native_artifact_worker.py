import concurrent.futures
from contextlib import closing, contextmanager, nullcontext
import json
from pathlib import Path
import plistlib
import queue
import secrets
import shutil
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
import native_artifact_worker
from native_artifact_worker import (
    ANDROID_DRIVER, ANDROID_MANIFEST, ANDROID_PROFILE, KINDS, BuildUncertainty, LaunchGate, NativeWorker,
    OwnedBuildProcess, Refusal, build, digest, exchange, literal, mac, now_ms, retained_android_report, serve,
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


if __name__ == "__main__":
    unittest.main()
