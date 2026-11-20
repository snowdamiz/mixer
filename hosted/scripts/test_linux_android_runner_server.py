from contextlib import closing, contextmanager
from dataclasses import asdict, replace
from pathlib import Path
import queue
import socket
import sqlite3
import stat
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "priv" / "development"))
from compiler_worker import Refusal, literal
from linux_android_runner import FRAME_LIMIT, TERMINAL, VERSION, LinuxAndroidRunnerClient
from linux_android_runner_server import ContainerObservation, LinuxAndroidRunnerServer, open_runner


class InertContainerAdapter:
    """Inventories and effects outlive runner connections and listener restarts."""

    def __init__(self, db_path, check):
        self.db_path = db_path
        self.check = check
        self.observations = {}
        self.creates = []
        self.starts = []
        self.stops = []
        self.defer_cleanup = set()

    def observe(self, identity):
        return self.observations.get(identity, ContainerObservation(identity, "absent", True, True))

    def check_intent(self, identity, phase):
        # A separate connection sees only committed intent.
        with closing(sqlite3.connect(self.db_path, timeout=1)) as db:
            row = db.execute(
                "SELECT binding, phase FROM operation WHERE id = ?", (identity.operation_id,),
            ).fetchone()
        self.check(row, (identity.binding_sha256, phase))

    def ensure_started(self, identity, cutoff_ms):
        self.check_intent(identity, "admitted")
        if identity not in self.starts and time.time_ns() // 1_000_000 < cutoff_ms:
            self.creates.append(identity)
            self.starts.append(identity)
            self.observations[identity] = ContainerObservation(identity, "running", False, False)

    def stop(self, identity):
        self.check_intent(identity, "stopping")
        self.stops.append(identity)
        if identity not in self.defer_cleanup and self.observe(identity) is not None:
            self.observations.pop(identity, None)


@contextmanager
def running_runner(test, opened_runner):
    ready = queue.Queue()
    stop = threading.Event()
    errors = []

    def run():
        try:
            with opened_runner as server:
                ready.put((server.listener, Path(server.listener.getsockname())))
                while not stop.is_set():
                    server.serve_one()
        except Exception as error:
            errors.append(error)
            ready.put(None)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    started = None
    try:
        started = ready.get(timeout=3)
        if started is None:
            raise errors[0]
        yield
    finally:
        stop.set()
        thread.join(timeout=3)
        test.assertFalse(thread.is_alive())
        if started is not None:
            listener, endpoint = started
            test.assertEqual(-1, listener.fileno())
            test.assertFalse(endpoint.exists())
        if errors:
            raise errors[0]


class LinuxAndroidRunnerServerTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="lr-")
        self.addCleanup(scratch.cleanup)
        self.directory = Path(scratch.name).resolve()
        self.endpoint = self.directory / "runner.sock"
        self.db_path = self.directory / "operations.sqlite"
        self.recipe, self.store = "a" * 64, "b" * 64
        self.client = LinuxAndroidRunnerClient(self.endpoint, recipe_sha256=self.recipe, store_id=self.store)
        self.adapter = InertContainerAdapter(self.db_path, self.assertEqual)
        self.now = time.time_ns() // 1_000_000
        self.first = self.operation("c")
        self.contender = self.operation("d")

    def operation(self, operation_digit):
        return self.client.operation({
            "operation_id": operation_digit * 64,
            "spec": {"platform": "android", "build_definition_sha256": self.recipe},
            "ref": {"build_id": operation_digit},
            "guard": {"record_id": operation_digit, "epoch": 1, "revision": 1,
                      "owner_id": "coordinator", "expires_at": self.now + 60_000},
            "deadline_ms": self.now + 120_000,
        })

    def open_runner(self, **options):
        configuration = dict(recipe_sha256=self.recipe, store_id=self.store, adapter=self.adapter)
        return open_runner(self.directory, **(configuration | options))

    def listener(self, *, initialize=False):
        return running_runner(self, self.open_runner(initialize=initialize))

    def status(self, action, operation, expected):
        reply = self.client.observe(action, operation)
        self.assertEqual(reply["status"], expected)
        if expected == "stopped":
            self.assertEqual(reply["terminal"], TERMINAL)

    def uncertain(self, action, operation):
        with self.assertRaisesRegex(Refusal, "^uncertain$"):
            self.client.observe(action, operation)

    def request(self, action="ensure_started", operation=None):
        return {"version": VERSION, "action": action, **asdict(operation or self.first)}

    def raw(self, packet):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(2)
            client.connect(str(self.endpoint))
            try:
                client.sendall(packet)
                if b"\n" not in packet:
                    client.shutdown(socket.SHUT_WR)
                return client.recv(FRAME_LIMIT)
            except (BrokenPipeError, ConnectionResetError):
                return b""

    def test_lost_reply_after_create_and_start_then_restart(self):
        original_send = LinuxAndroidRunnerServer.send

        def drop_ensure(server, connection, reply, deadline):
            if reply["request"]["action"] == "ensure_started":
                self.assertEqual(reply["status"], "running")
                return
            original_send(server, connection, reply, deadline)

        with patch.object(LinuxAndroidRunnerServer, "send", drop_ensure):
            with self.listener(initialize=True):
                self.status("query", self.first, "absent")
                self.uncertain("ensure_started", self.first)
                self.assertEqual(self.adapter.creates, [self.first.identity])
                self.assertEqual(self.adapter.starts, [self.first.identity])
        with self.listener():
            self.status("query", self.first, "running")
            self.status("ensure_started", self.first, "running")
            self.uncertain("ensure_started", self.contender)
        self.assertEqual(self.adapter.creates, [self.first.identity])
        self.assertEqual(self.adapter.starts, [self.first.identity])

    def test_known_start_does_not_repeat_after_inventory_becomes_empty(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
        del self.adapter.observations[self.first.identity]
        with self.listener(), patch.object(self.adapter, "ensure_started") as ensure:
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.first)
            ensure.assert_not_called()
            self.uncertain("ensure_started", self.contender)
            self.status("stop", self.first, "stopped")

    def test_unobserved_start_holds_slot_and_same_id_can_retry_after_absence(self):
        self.adapter.observations[self.first.identity] = None
        with self.listener(initialize=True):
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.first)
            self.uncertain("ensure_started", self.contender)
            self.assertEqual(self.adapter.starts, [])
        del self.adapter.observations[self.first.identity]
        with self.listener():
            self.status("query", self.first, "absent")
            self.uncertain("ensure_started", self.contender)
            self.status("ensure_started", self.first, "running")
        self.assertEqual(self.adapter.starts, [self.first.identity])

    def test_stop_before_start_fences_even_when_first_observation_is_missing(self):
        self.adapter.observations[self.first.identity] = None
        with self.listener(initialize=True):
            self.uncertain("stop", self.first)
            self.uncertain("ensure_started", self.first)
            self.uncertain("ensure_started", self.contender)
        del self.adapter.observations[self.first.identity]
        with self.listener():
            self.status("ensure_started", self.first, "stopped")
            changed = replace(self.contender, identity=replace(self.contender.identity, binding_sha256="f" * 64))
            self.uncertain("ensure_started", changed)
            self.status("ensure_started", self.contender, "running")
        with self.listener():
            self.status("query", self.first, "stopped")
            self.status("stop", self.first, "stopped")
        self.assertEqual(self.adapter.stops, [self.first.identity])
        self.assertEqual(self.adapter.starts, [self.contender.identity])

    def test_stop_after_start_holds_slot_until_all_exact_cleanup_facts(self):
        identity = self.first.identity
        self.adapter.defer_cleanup.add(identity)
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            self.status("stop", self.first, "stopping")
        with self.listener():
            for proof, status in (
                (None, None),
                (ContainerObservation(self.contender.identity, "absent", True, True), None),
                (ContainerObservation(identity, "absent", 1, True), None),
                (ContainerObservation(identity, "present", True, True), "stopping"),
                (ContainerObservation(identity, "absent", False, True), "stopping"),
                (ContainerObservation(identity, "absent", True, False), "stopping"),
            ):
                with self.subTest(proof=proof):
                    self.adapter.observations[identity] = proof
                    if status is None:
                        self.uncertain("query", self.first)
                    else:
                        self.status("query", self.first, status)
                    self.uncertain("ensure_started", self.contender)
                    self.assertEqual(self.adapter.starts, [identity])
            self.status("ensure_started", self.first, "stopping")
            self.adapter.observations[identity] = ContainerObservation(identity, "absent", True, True)
            self.status("query", self.first, "stopped")
        self.adapter.observations[identity] = None
        with self.listener():
            self.status("ensure_started", self.first, "stopped")
            self.status("ensure_started", self.contender, "running")
        self.assertEqual(self.adapter.starts, [identity, self.contender.identity])

    def test_lost_terminal_reply_replays_fence_after_restart(self):
        def drop_stop(_server, _connection, reply, _deadline):
            self.assertEqual(reply["status"], "stopped")
            self.assertEqual(reply["terminal"], TERMINAL)

        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            with patch.object(LinuxAndroidRunnerServer, "send", drop_stop):
                self.uncertain("stop", self.first)
            self.assertNotIn(self.first.identity, self.adapter.observations)
        with self.listener():
            self.status("ensure_started", self.contender, "running")
            self.status("stop", self.first, "stopped")
            self.status("query", self.contender, "running")
        self.assertEqual(self.adapter.stops, [self.first.identity])

    def test_binding_and_guard_are_stable_across_restarts(self):
        with self.listener(initialize=True):
            self.status("query", self.first, "absent")
        guard = self.first.guard
        identity = self.first.identity
        with self.listener():
            for operation in (
                replace(self.first, identity=replace(identity, binding_sha256="f" * 64)),
                replace(self.first, deadline_ms=self.first.deadline_ms + 1),
                replace(self.first, guard=replace(guard, record_id="other")),
                replace(self.first, guard=replace(guard, revision=0)),
                replace(self.first, guard=replace(guard, owner_id="other")),
                replace(self.first, guard=replace(guard, expires_at=guard.expires_at - 1)),
            ):
                with self.subTest(operation=operation):
                    self.uncertain("stop", operation)
            newer = replace(self.first, guard=replace(guard, epoch=2, revision=0, owner_id="successor"))
            self.status("ensure_started", newer, "running")
        with self.listener():
            self.uncertain("stop", self.first)
            self.status("query", newer, "running")
        self.assertEqual(self.adapter.stops, [])
        self.assertEqual(self.adapter.starts, [identity])

    def test_socket_refuses_invalid_frames_credentials_and_authority(self):
        request = self.request()
        frames = [
            b'{"version":1,"version":1}\n',
            b" " * FRAME_LIMIT + b"\n",
            literal(request).encode(),
            literal(request).encode() + b"\n{}\n",
        ]
        packets = [
            request | {"version": True},
            request | {"action": "artifacts"},
            request | {"path": "/arbitrary", "argv": ["arbitrary"]},
            request | {"guard": request["guard"] | {"epoch": True}},
            request | {"guard": request["guard"] | {"expires_at": self.now}},
            request | {"deadline_ms": self.now},
            request | {"identity": request["identity"] | {"recipe_sha256": "1" * 64}},
            request | {"identity": request["identity"] | {"store_id": "2" * 64}},
            request | {"identity": request["identity"] | {"operation_id": "../other"}},
        ]
        frames.extend((literal(packet) + "\n").encode() for packet in packets)
        with self.listener(initialize=True):
            self.assertEqual(self.endpoint.lstat().st_mode, stat.S_IFSOCK | 0o600)
            for frame in frames:
                with self.subTest(frame=frame[:100]):
                    self.assertEqual(self.raw(frame), b"")
            with patch("linux_android_runner_server.peer_uid", return_value=-1):
                self.assertEqual(self.raw((literal(request) + "\n").encode()), b"")
            self.assertEqual(self.adapter.starts, [])
            self.assertEqual(self.adapter.stops, [])
            self.status("ensure_started", self.first, "running")

    def test_elapsed_start_deadline_still_permits_query_and_stop(self):
        expired = replace(self.first, deadline_ms=self.now)
        with self.listener(initialize=True):
            with self.assertRaisesRegex(Refusal, "^stale$"):
                self.client.observe("ensure_started", expired)
            self.status("query", expired, "absent")
            self.status("stop", expired, "stopped")
        self.assertEqual(self.adapter.starts, [])

    def test_store_requires_explicit_provisioning_and_exclusive_private_writer(self):
        with self.assertRaises(FileNotFoundError), self.open_runner():
            self.fail("missing store opened")
        self.directory.chmod(0o755)
        with self.assertRaises(Refusal), self.open_runner(initialize=True):
            self.fail("non-private directory opened")
        self.directory.chmod(0o700)
        with self.listener(initialize=True):
            with self.assertRaises(BlockingIOError), self.open_runner():
                self.fail("second listener opened")
            self.status("query", self.first, "absent")
        with self.assertRaises(FileExistsError), self.open_runner(initialize=True):
            self.fail("existing store reinitialized")
        for options in ({"recipe_sha256": "1" * 64}, {"store_id": "2" * 64}):
            with self.subTest(options=options):
                with self.assertRaises(Refusal), self.open_runner(**options):
                    self.fail("other authority opened pinned store")
        self.endpoint.write_text("foreign file")
        with self.assertRaises(Refusal), self.open_runner():
            self.fail("non-socket endpoint replaced")
        self.assertEqual(self.endpoint.read_text(), "foreign file")
        self.endpoint.unlink()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as orphan:
            orphan.bind(str(self.endpoint))
        with self.listener():
            self.status("query", self.first, "absent")


if __name__ == "__main__":
    unittest.main()
