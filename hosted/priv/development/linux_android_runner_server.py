"""Local v1 Android runner for one operator-provisioned store and recipe.

The trusted local adapter receives a RunnerIdentity, a start cutoff in Unix
milliseconds for ensure or resume, and the observed full ID for resume. Its
synchronous effects must be bounded, idempotent by exact identity across
restarts, and leave no deferred start after a clean observation. Observations
must come from the adapter's inventory of that exact operation, including its
processes and resources. An adapter reporting completion_pending must provide
complete(identity, cutoff), which verifies the result and durably closes the
exact started operation without launching or resuming a container.
"""
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
import fcntl
import json
import os
from pathlib import Path
import socket
import sqlite3
import stat
import struct
import time

from compiler_worker import Refusal, literal
from linux_android_runner import (
    FRAME_LIMIT, TERMINAL, TIMEOUT_SECONDS, VERSION, RunnerGuard, RunnerIdentity,
    RunnerOperation, completed_result, peer_uid, positive_integer, sha256, unique_object,
)


@dataclass(frozen=True)
class ContainerObservation:
    identity: RunnerIdentity
    container: str  # running, present, or absent
    processes_absent: bool
    resources_removed: bool
    prepared_id: str | None = None  # Full ID with no prior start intent.
    completion_pending: bool = False

    @property
    def clean(self):
        return self.container == "absent" and self.processes_absent and self.resources_removed


def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise TimeoutError
    return seconds


def receive(connection, deadline):
    data = bytearray()
    while len(data) < FRAME_LIMIT:
        connection.settimeout(remaining(deadline))
        chunk = connection.recv(FRAME_LIMIT - len(data))
        if not chunk:
            break
        data.extend(chunk)
        if b"\n" in chunk:
            if data.count(b"\n") == 1 and data.endswith(b"\n"):
                return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
            break
    raise ValueError("invalid runner request frame")


def live(cutoff):
    if cutoff <= time.time_ns() // 1_000_000:
        raise Refusal("stale")


class LinuxAndroidRunnerServer:
    def __init__(self, listener, db, recipe_sha256, store_id, adapter, identity_pins, require_start_pin):
        self.listener = listener
        self.db = db
        self.recipe_sha256 = recipe_sha256
        self.store_id = store_id
        self.adapter = adapter
        self.identity_pins = identity_pins
        self.require_start_pin = require_start_pin

    def serve_one(self):
        """Handle one connection, or return after the bounded idle wait."""
        try:
            connection, _ = self.listener.accept()
        except TimeoutError:
            return
        with connection:
            try:
                deadline = time.monotonic() + TIMEOUT_SECONDS
                if peer_uid(connection) != os.getuid():
                    return
                request = receive(connection, deadline)
                operation, action, cutoff = self.parse(request)
                status, terminal = self.observe(operation, action, cutoff, deadline)
                if status == "completed":
                    cutoff = min(cutoff, operation.deadline_ms)
                live(cutoff)
                reply = {"request": request, "status": status}
                if terminal is not None:
                    reply["terminal"] = terminal
                self.send(connection, reply, deadline)
            except (OSError, ValueError, KeyError, TypeError, RecursionError,
                    Refusal, sqlite3.Error, struct.error):
                # v1 represents a missing or untrusted observation by EOF.
                return

    def send(self, connection, reply, deadline):
        packet = (literal(reply) + "\n").encode()
        if len(packet) > FRAME_LIMIT:
            raise ValueError("oversized runner reply")
        connection.settimeout(remaining(deadline))
        connection.sendall(packet)

    def parse(self, request):
        if (type(request) is not dict
                or set(request) != {"version", "action", "identity", "guard", "deadline_ms"}
                or type(request["version"]) is not int or request["version"] != VERSION
                or request["action"] not in ("query", "ensure_started", "stop")
                or not positive_integer(request["deadline_ms"])):
            raise Refusal("unavailable")
        identity = RunnerIdentity(**request["identity"])
        if (not sha256(identity.operation_id) or not sha256(identity.binding_sha256)
                or identity.recipe_sha256 != self.recipe_sha256 or identity.store_id != self.store_id):
            raise Refusal("unavailable")
        default_pin = None if self.require_start_pin and request["action"] == "ensure_started" else identity
        if self.identity_pins.get(identity.operation_id, default_pin) != identity:
            raise Refusal("unavailable")
        guard = RunnerGuard(**request["guard"])
        action = request["action"]
        deadline_ms = request["deadline_ms"]
        cutoff = guard.expires_at
        if action == "ensure_started":
            cutoff = min(cutoff, deadline_ms)
        live(cutoff)
        return RunnerOperation(identity, guard, deadline_ms), action, cutoff

    def observe(self, operation, action, cutoff, deadline):
        identity, guard = operation.identity, operation.guard
        key = identity.operation_id
        blocked = False
        with self.db:
            row = self.db.execute(
                "SELECT binding, deadline, guard, phase, completed FROM operation WHERE id = ?", (key,),
            ).fetchone()
            phase, completed = "idle", False
            if row is not None:
                binding, start_deadline, previous, phase, completed = row
                if (binding, start_deadline) != (identity.binding_sha256, operation.deadline_ms):
                    raise Refusal("unavailable")
                self.check_guard(guard, RunnerGuard(**json.loads(previous)))

            if action == "ensure_started" and phase == "idle":
                blocked = self.db.execute(
                    """SELECT 1 FROM operation WHERE phase = 'stopping'
                       OR (phase IN ('admitted', 'started') AND completed = 0) LIMIT 1""",
                ).fetchone() is not None
                if not blocked:
                    phase = "admitted"
            if action == "stop" and phase != "stopped":
                phase = "stopping"
            self.db.execute(
                """INSERT INTO operation (id, binding, deadline, guard, phase) VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET guard = excluded.guard, phase = excluded.phase""",
                (key, identity.binding_sha256, operation.deadline_ms, literal(asdict(guard)), phase),
            )

        if blocked:
            raise Refusal("unavailable")
        if phase == "stopped":
            return "stopped", TERMINAL
        if action == "stop":
            live(cutoff)
            self.adapter.stop(identity)
        observed = self.inventory(identity)
        if phase == "stopping":
            if not observed.clean:
                return "stopping", None
            with self.db:
                self.db.execute("UPDATE operation SET phase = 'stopped' WHERE id = ?", (key,))
            return "stopped", TERMINAL
        if (phase == "admitted" and action == "ensure_started" and not completed and not observed.completion_pending
                and (observed.clean or observed.prepared_id is not None)):
            live(cutoff)
            if observed.prepared_id is None:
                self.adapter.ensure_started(identity, cutoff)
            else:
                self.adapter.resume_prepared(identity, observed.prepared_id, cutoff)
            observed = self.inventory(identity)
        if completed and (not observed.clean or not observed.completion_pending):
            raise Refusal("uncertain")
        if phase in ("admitted", "started") and observed.completion_pending:
            completion_cutoff = min(
                cutoff, operation.deadline_ms,
                time.time_ns() // 1_000_000 + int(remaining(deadline) * 1000),
            )
            live(completion_cutoff)
            terminal = self.adapter.complete(identity, completion_cutoff)
            completed_result(terminal, identity)
            remaining(deadline)
            live(completion_cutoff)
            if not completed:
                with self.db:
                    self.db.execute(
                        "UPDATE operation SET phase = 'started', completed = 1 WHERE id = ?", (key,),
                    )
            live(completion_cutoff)
            return "completed", terminal
        if phase in ("admitted", "started") and observed.container == "running":
            if phase == "admitted":
                with self.db:
                    self.db.execute("UPDATE operation SET phase = 'started' WHERE id = ?", (key,))
            return "running", None
        if phase != "started" and observed.clean and action == "query":
            return "absent", None
        raise Refusal("uncertain")

    @staticmethod
    def check_guard(guard, previous):
        order = (guard.epoch, guard.revision)
        prior = (previous.epoch, previous.revision)
        if (guard.record_id != previous.record_id or order < prior
                or (order == prior and (guard.owner_id != previous.owner_id
                                        or guard.expires_at < previous.expires_at))):
            raise Refusal("stale")

    def inventory(self, identity):
        result = self.adapter.observe(identity)
        if (type(result) is not ContainerObservation or result.identity != identity
                or result.container not in ("running", "present", "absent")
                or type(result.processes_absent) is not bool or type(result.resources_removed) is not bool
                or (result.container == "running" and result.processes_absent)
                or type(result.completion_pending) is not bool
                or (result.completion_pending and
                    (not result.processes_absent or result.prepared_id is not None))
                or (result.prepared_id is not None and (not sha256(result.prepared_id)
                    or result.container != "present" or not result.processes_absent or result.resources_removed))):
            raise Refusal("uncertain")
        return result


def require_private(info, mode):
    if info.st_uid != os.getuid() or info.st_mode != mode:
        raise Refusal("unavailable")


@contextmanager
def private_file(path, flags):
    fd = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    try:
        require_private(os.fstat(fd), stat.S_IFREG | 0o600)
        yield fd
    finally:
        os.close(fd)


@contextmanager
def open_runner(directory, *, recipe_sha256, store_id, adapter, initialize=False,
                identity_pins=None, require_start_pin=False):
    """Open a dedicated private directory with a fixed runner.sock endpoint.

    Use initialize once for a new store identity. A restart requires the
    original database and an adapter attached to the same durable inventory.
    """
    directory = Path(directory)
    if directory.resolve() != directory or not sha256(recipe_sha256) or not sha256(store_id):
        raise Refusal("unavailable")
    require_private(directory.lstat(), stat.S_IFDIR | 0o700)
    with private_file(directory / "writer.lock", os.O_WRONLY | os.O_CREAT) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / "operations.sqlite"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if initialize else os.O_RDONLY
        with private_file(path, flags):
            with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=TIMEOUT_SECONDS)) as db:
                db.execute("PRAGMA synchronous=FULL")
                if initialize:
                    with db:
                        db.execute("BEGIN")
                        db.execute("CREATE TABLE store (version INTEGER, recipe TEXT, id TEXT)")
                        db.execute("INSERT INTO store VALUES (?, ?, ?)", (VERSION, recipe_sha256, store_id))
                        db.execute(
                            """CREATE TABLE operation (
                                 id TEXT PRIMARY KEY, binding TEXT NOT NULL, deadline INTEGER NOT NULL,
                                 guard TEXT NOT NULL, phase TEXT NOT NULL
                                 CHECK (phase IN ('idle', 'admitted', 'started', 'stopping', 'stopped')))""",
                        )
                if db.execute("SELECT * FROM store").fetchall() != [(VERSION, recipe_sha256, store_id)]:
                    raise Refusal("unavailable")
                if "completed" not in {column[1] for column in db.execute("PRAGMA table_info(operation)")}:
                    with db:
                        db.execute("""ALTER TABLE operation ADD COLUMN completed INTEGER NOT NULL
                                      DEFAULT 0 CHECK (completed IN (0, 1))""")
                with runner_socket(directory / "runner.sock") as listener:
                    yield LinuxAndroidRunnerServer(listener, db, recipe_sha256, store_id, adapter,
                                                   dict(identity_pins or {}), require_start_pin)


@contextmanager
def runner_socket(path):
    # The directory is dedicated to this runner and the writer lock is held.
    try:
        old = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if old.st_uid != os.getuid() or not stat.S_ISSOCK(old.st_mode):
            raise Refusal("unavailable")
        path.unlink()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
        listener.bind(str(path))
        created = path.lstat()
        try:
            path.chmod(0o600)
            listener.listen()
            listener.settimeout(TIMEOUT_SECONDS)
            yield listener
        finally:
            try:
                if os.path.samestat(created, path.lstat()):
                    path.unlink()
            except FileNotFoundError:
                pass
