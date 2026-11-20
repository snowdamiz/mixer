"""Bounded Pair25 recovery controls with the stock Python worker and runner."""
from contextlib import closing, contextmanager
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from threading import Event, Lock, Thread
import time
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import run

DEVELOPMENT = run.REPO / "hosted/priv/development"
sys.path.insert(0, str(DEVELOPMENT))
from compiler_worker import Refusal, literal
from linux_android_artifact_importer import STORE
from linux_android_runner import RunnerIdentity
from native_artifact_worker import NativeWorker


@contextmanager
def owned_scratch(receipts):
    root = Path(tempfile.mkdtemp(prefix="p25u-")).resolve()
    try:
        yield root
    finally:
        if all(command["groupAbsent"] for command in receipts.values()):
            shutil.rmtree(root)
        else:
            print(f"Runner custody unresolved, retaining {root}", file=sys.stderr)


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.addCleanup(os.umask, os.umask(0o077))
        self.sessions = {"owner": "owner", "outsider": "outsider"}
        self.scope = dict(organization_id="organization", project_id="project", application_id="application",
                          platform="android", build_id="build", source_sha256="b" * 64,
                          toolchain_lock_sha256=run.sha(run.INERT_LOCK), build_definition_sha256="d" * 64)

    def test_checkout_burst_closes_active_connections_at_shared_deadline(self):
        post_handlers = set()
        signed_reads = set()
        lock = Lock()
        refused = Event()
        stop = Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                with lock:
                    post_handlers.add(self.client_address)
                    if len(post_handlers) == run.BURST_RETRIES:
                        refused.set()
                stop.wait(timeout=8)

            def do_GET(self):
                with lock:
                    signed_reads.add(self.path)
                try:
                    self.send_response(200)
                    self.send_header("Content-Length", "128")
                    self.end_headers()
                    for _ in range(128):
                        if stop.wait(0.025):
                            break
                        self.wfile.write(b"x")
                except (BrokenPipeError, ConnectionResetError):
                    pass

        class Server(ThreadingHTTPServer):
            daemon_threads = False

        with Server((run.HOST, 0), Handler) as server:
            thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02})
            thread.start()
            port = server.server_port
            origin = f"http://{run.HOST}:{port}"
            auth = {"origin": origin, "port": port, "csrf": "fixture", "build": {}}
            release = {kind: {"url": f"{origin}/v3/{kind}", "sha256": "0" * 64}
                       for kind in ("offer", "artifact")}

            def ready(seconds):
                self.assertTrue(refused.wait(timeout=seconds))
                return {"before_begin": True, "queue_ns": [0] * run.BURST_RETRIES}

            started = time.monotonic()
            try:
                with patch.object(run, "BURST_SECONDS", 1):
                    with self.assertRaises(TimeoutError):
                        run.checkout_burst(auth, "owner", release, ready,
                                           lambda: self.fail("released timed-out POSTs"))
                self.assertLess(time.monotonic() - started, 1.75)
                self.assertEqual(signed_reads, {"/v3/offer", "/v3/artifact"})
            finally:
                stop.set()
                server.shutdown()
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())

    def detail(self, state, artifacts=()):
        running = state == "running"
        return {field: self.scope[key] for field, key in run.DETAIL_SCOPE.items()} | {
            "revision": 1 if running else 2, "state": state, "attempt": 1, "failureCode": None,
            "workerCompletionPending": running, "artifacts": list(artifacts),
        }

    def replay(self, *, finishes):
        receipts = {}
        with owned_scratch(receipts) as root:
            scope = self.scope
            recipe = scope["build_definition_sha256"]
            state = root / "worker"
            runner_dir = root / "r"
            runner_dir.mkdir(mode=0o700)
            runner = dict(socket_path=str(runner_dir / "runner.sock"), recipe_sha256=recipe, store_id="f" * 64)
            registration = {key: scope[key] for key in run.SPEC_FIELDS} | {
                "source": {"sha256": scope["source_sha256"]},
                "toolchain_lock_sha256": scope["toolchain_lock_sha256"], "build_definition_sha256": recipe,
            }
            operation = "a" * 64
            now = time.time_ns() // 1_000_000
            binding = dict(spec=dict(registration, build_id=scope["build_id"]), deadline_ms=now + 30_000,
                           ref={key: scope[key] for key in (*run.SPEC_FIELDS, "build_id")} | {"attempt": 1, "fence": 1})
            identity = RunnerIdentity(operation, run.sha(literal(binding).encode()), recipe, runner["store_id"])
            grant = dict(identity=asdict(identity), bundle=str(root / "bundle"), inputs={
                "source_tree_sha256": scope["source_sha256"], "linux_lock_sha256": scope["toolchain_lock_sha256"],
                "rendered_driver_sha256": "e" * 64,
            })
            config = dict(tenant=scope["organization_id"], worker_id="worker", token="inert" * 8,
                          registration={"spec": registration, "files": {}}, linux_runner=runner,
                          linux_artifact_imports={operation: grant})
            config_file = root / "worker.json"
            run.write(config_file, config)
            guard = dict(record_id="record", epoch=1, revision=1, owner_id="oban:1:initial", expires_at=now + 25_000)
            request = dict(binding, operation_id=operation, guard=guard)
            command = [sys.executable, "-B", run.HERE / "run.py", "--inert-child", root, DEVELOPMENT, "20"]
            with run.owned(root, "runner", command, root, {"PAIR25_CANCEL": "1"}, receipts,
                           lambda: (root / "runner.done").touch(exist_ok=False)) as child:
                run.wait(lambda: Path(runner["socket_path"]).is_socket(), 3, child)
                with closing(NativeWorker(config, str(state))) as worker:
                    self.assertEqual(worker.request("ensure_started", request), {"status": "running"})
                original = run.read(root / "inert.start")
                run.require_no_bundle(state, grant)
                request["guard"] = dict(guard, epoch=2, owner_id="oban:1:reopened")
                with closing(NativeWorker(config, str(state))) as worker:
                    if finishes:
                        (root / "inert.finish-after-reopen").touch(exist_ok=False)
                    self.assertEqual(worker.request("query", request), {"status": "running"})
                    row = worker.load(operation)
                    self.assertEqual((row["binding"], row["starts"], row["linux_runner"]), (binding, 1, asdict(identity)))
                    [(op, fingerprint, deadline, raw, phase, completed)] = run.runner_journal(runner_dir)
                    self.assertEqual((op, fingerprint, deadline, json.loads(raw), phase, completed),
                                     (operation, identity.binding_sha256, binding["deadline_ms"],
                                      request["guard"], "started", int(finishes)))
                    state_name = "native_succeeded" if finishes else "running"
                    query = "?" + urlencode(scope)
                    descriptors = [dict(item, downloadPath="/console-api/v1/build-artifacts/" + item["kind"] + query)
                                   for item in row.get("artifacts", [])]

                    def fixture_http(auth, path, *, cookie=None, empty_post=False):
                        if path == "/auth/session":
                            return 200, {}, b'{"state":"authenticated"}'
                        if cookie != "owner":
                            return (404 if cookie else 401), {}, b""
                        if path == run.BUILD + query:
                            return 200, {}, literal({"build": self.detail(state_name, descriptors)}).encode()
                        if empty_post and path == run.CANCEL + query and not finishes:
                            detail = dict(self.detail("running"), revision=2, state="cancelling")
                            return 202, {}, literal({"outcome": "applied", "build": detail}).encode()
                        if path == run.LOGS + query and finishes:
                            log = run.read(state / ("customer-log-v1-" + operation))
                            return 200, {"cache-control": "no-store"}, literal({
                                "buildLogs": dict(self.detail(state_name), events=[
                                    dict(log["androidDriver"], event="android_driver_finished"),
                                    {"event": "build_command_finished", "exitCode": log["cliExitCode"]},
                                ]),
                            }).encode()
                        for entry in descriptors:
                            if path == entry["downloadPath"]:
                                media, filename = run.ATTACHMENTS[entry["kind"]]
                                content = (state / operation / STORE / entry["sha256"]).read_bytes()
                                return 200, {"Content-Type": media,
                                             "Content-Disposition": f'attachment; filename="{filename}"'}, content
                        raise AssertionError(path)

                    observed = {}
                    with patch.object(run, "http", side_effect=fixture_http) as http:
                        first = run.read_recovery_detail({}, scope, self.sessions, observed, "afterReopen")
                        self.assertEqual(run.verify_recovery_detail(first, scope), state_name)
                        if finishes:
                            reply = worker.request("artifacts", request)
                            self.assertEqual(reply["status"], "native_ready")
                            output, _, terminal = run.verify_downloads({}, scope, self.sessions, row, run.INERT_DRIVER_LOG)
                            self.assertEqual([item["kind"] for item in output], list(run.ATTACHMENTS))
                            self.assertEqual(terminal["buildId"], scope["build_id"])
                            final = run.read_recovery_detail({}, scope, self.sessions, observed, "final")
                            self.assertEqual(first["detail"], final["detail"])
                            self.assertFalse(any(call.kwargs.get("empty_post") for call in http.call_args_list))
                            self.assertFalse((root / "inert.stop").exists())
                        else:
                            self.assertEqual(run.request_cancel({"cookie": "owner"}, scope), 202)
                            posts = [call for call in http.call_args_list if call.kwargs.get("empty_post")]
                            self.assertEqual(len(posts), 1)
                            request["guard"] = dict(guard, epoch=3, revision=2, owner_id="oban:2:cancel")
                            self.assertEqual(worker.request("stop", request)["status"], "stopped")
                            self.assertEqual(run.read(root / "inert.stop"), {"identity": asdict(identity)})
                            with self.assertRaises(Refusal):
                                worker.request("artifacts", request)
                            run.require_no_bundle(state, grant)
                    self.assertEqual(run.read(root / "inert.start"), original)
            self.assertTrue(receipts["runner"]["groupAbsent"])
            self.assertFalse(Path(runner["socket_path"]).exists())

    def test_active_operation_can_be_cancelled(self):
        self.replay(finishes=False)

    def test_original_operation_can_finish_during_recovery(self):
        self.replay(finishes=True)

    def test_first_read_is_retained_when_state_is_rejected(self):
        receipt = {}
        payload = literal({"build": self.detail("timed_out"), "private": "omitted"}).encode()
        with patch.object(run, "http", return_value=(200, {"Set-Cookie": "omitted"}, payload)):
            observed = run.read_recovery_detail({}, self.scope, self.sessions, receipt, "afterReopen")
        with self.assertRaisesRegex(RuntimeError, "unexpected post-reopen"):
            run.verify_recovery_detail(observed, self.scope)
        self.assertEqual(receipt["afterReopen"]["ownerHTTP"], 200)
        self.assertEqual(receipt["afterReopen"]["detail"]["state"], "timed_out")
        self.assertNotIn("omitted", literal(receipt))

    def test_cancel_conflict_requires_opt_in_and_exact_code(self):
        auth = {"cookie": "owner"}
        for code, allowed in (("conflict", True), ("conflict", False), ("idempotency_conflict", True)):
            with self.subTest(code=code, allowed=allowed):
                reply = literal({"error": {"code": code}}).encode()
                with patch.object(run, "http", return_value=(409, {}, reply)) as http:
                    if code == "conflict" and allowed:
                        self.assertEqual(run.request_cancel(auth, self.scope, allow_completion_conflict=allowed), 409)
                    else:
                        with self.assertRaises(RuntimeError):
                            run.request_cancel(auth, self.scope, allow_completion_conflict=allowed)
                    http.assert_called_once_with(auth, run.CANCEL + "?" + urlencode(self.scope),
                                                 cookie="owner", empty_post=True)


if __name__ == "__main__":
    unittest.main()
