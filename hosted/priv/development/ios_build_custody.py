"""Private macOS custody for an operator-registered iOS worker.

Run the worker and the reusable supervisor (or legacy observer) independently.
Only the custody owner parents the CLI. Both roles share the private SQLite ledger.
"""

from contextlib import ExitStack, closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import sqlite3
import stat
import subprocess
import sys
import time
from types import ModuleType
from typing import NamedTuple

SOURCE = ("compiler_worker", "starter_package_closure", "native_artifact_worker")
ENTRY = "ios_build_custody"
PIN_LIMIT = 8 * 1024 * 1024
POLL_SECONDS = 0.05
ADMISSION_SECONDS = 60
INERT_REAP_SECONDS = 5
REUSABLE_VERSION = 2
INERT_LAUNCHER = r"""
import os
import sys
import time

fd = int(sys.argv[1])
token = os.read(fd, 1)
if not token:
    sys.exit(0)
if token != b"\x01":
    sys.exit(2)
os.set_inheritable(fd, False)
argv = sys.argv[3:]
if time.time_ns() // 1_000_000 >= int(sys.argv[2]):
    sys.exit(0 if os.write(fd, b"E") == 1 else 2)
os.execv(argv[0], argv)
"""
_runtime = None


class Claim(NamedTuple):
    operation: str
    plan_sha256: str
    guard: str
    parent_pid: int


def is_sha256(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def runtime_image():
    directory = Path(__file__).resolve(strict=True).parent
    paths = {name: directory / (name + ".py") for name in (*SOURCE, ENTRY)}
    paths["python"] = Path(sys.executable).resolve(strict=True)
    sources = {}
    pins = {}
    for name, path in paths.items():
        with path.open("rb") as handle:
            data = handle.read(PIN_LIMIT + 1)
        if not 0 < len(data) <= PIN_LIMIT:
            raise ValueError("Invalid pinned runtime input length")
        sources[name] = (path, data)
        pins[name] = hashlib.sha256(data).hexdigest()
    return sources, pins


def bootstrap(config):
    global _runtime
    sources, pins = runtime_image()
    if (sys.platform != "darwin" or not sys.flags.isolated
            or config["ios_custodian"]["runtime_sha256"] != pins):
        raise ValueError("Invalid iOS custody runtime")
    # Use the verified source snapshots directly. Imports must not resolve
    # worker modules through sys.path or reuse a bytecode cache.
    for name in SOURCE:
        path, data = sources[name]
        module = ModuleType(name)
        module.__file__ = str(path)
        sys.modules[name] = module
        exec(compile(data, str(path), "exec"), module.__dict__)
    _runtime = pins
    sys.modules[ENTRY] = sys.modules[__name__]
    return sys.modules["native_artifact_worker"]


def require(condition):
    if not condition:
        from compiler_worker import Refusal
        raise Refusal("uncertain")


def private_directory(path):
    info = path.lstat()
    require(path.is_absolute() and path.resolve() == path and info.st_uid == os.getuid()
            and info.st_mode == stat.S_IFDIR | 0o700)


def load_row(db, operation):
    found = db.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchone()
    return json.loads(found[0]) if found else None


def retained_xcode_command(native, project, files):
    private_directory(project)
    raw = native.read_owned(project / "mixer.yml", 1024 * 1024, allow_owner_write=True)
    require(native.digest(raw) == files.get("mixer.yml"))
    config = json.loads(raw)
    name = config["name"]
    require(type(name) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", name))
    derived = project / ".mixer" / "ios-build"
    return [
        "/usr/bin/xcodebuild", "-project", str(project / "Platforms" / "iOS" / (name + ".xcodeproj")),
        "-scheme", name, "-configuration", "Debug", "-sdk", "iphonesimulator",
        "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", str(derived),
        "-clonedSourcePackagesDirPath", str(derived / "SourcePackages"), "-jobs", "4",
        "DEBUG_INFORMATION_FORMAT=dwarf-with-dsym", "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES",
        "ENABLE_DEBUG_DYLIB=NO", "COMPILER_INDEX_STORE_ENABLE=NO", "CODE_SIGNING_ALLOWED=NO", "build",
    ]


def nested_closure(native, tmp, files):
    private_directory(tmp.parent)
    private_directory(tmp)
    basename = native.read_cli_ack(tmp)
    require(not isinstance(basename, native.BuildUncertainty))
    nested = native.read_nested_receipts(tmp, basename, strict=True)
    require(not isinstance(nested, native.BuildUncertainty))
    _, receipts = nested
    require(len(receipts) <= 2)
    for item, _ in receipts:
        require(item["schema"] == "mixer.owned-command.2" and item["released"] is True
                and item.get("uncertainty") is None
                and type(item["exitCode"]) is int and -255 <= item["exitCode"] <= 255)
        reason = item.get("stopReason")
        require(reason in (None, "cancelled", "runtime-deadline", "generated-output-limit",
                           "aggregate-output-limit"))
        terminated = item.get("groupTerminateSent")
        killed = item.get("groupKillSent", False)
        require((terminated is None or type(terminated) is bool) and type(killed) is bool
                and (not terminated or reason == "cancelled")
                and (not killed or reason not in (None, "cancelled")))
    probe = receipts[0][0] if receipts and receipts[0][0]["command"] == ["/usr/bin/swift", "--version"] else None
    compiler = receipts[1:] if probe is not None else receipts
    require(len(compiler) <= 1)
    if compiler:
        item, _ = compiler[0]
        command = item["command"]
        require(command[0] == "/usr/bin/xcodebuild" and "CODE_SIGNING_ALLOWED=NO" in command
                and "generic/platform=iOS Simulator" in command)
        if "mixer.yml" in files or probe is not None:
            require(probe is not None and command == retained_xcode_command(native, tmp.parent / "project", files))
            require(probe["exitCode"] == 0 and probe.get("stopReason") is None
                    and probe["terminalNS"] <= item["runtimeStartedNS"])
    return nested, {"receipt_root": basename, "receipt_sha256s": [sha for _, sha in receipts]}


def classify(code, receipts, *, stop_requested):
    require(code >= 0)
    if not receipts:
        require(code > 0)
        return "preflight_failed"
    child, _ = receipts[-1]
    reason = child.get("stopReason")
    if reason == "cancelled":
        require(code > 0 and stop_requested)
        return "cancelled"
    if child["command"][0] != "/usr/bin/xcodebuild":
        require(code > 0)
        return "preflight_failed"
    if reason in ("runtime-deadline", "generated-output-limit", "aggregate-output-limit"):
        require(code > 0)
        return "build_failed"
    require(reason is None)
    if code == 0:
        require(child["exitCode"] == 0)
        return "succeeded"
    return "build_failed"


def check_ledger_mode(db, custody):
    # The listener holds the writer lock and startup transaction. Check mode
    # before pinning authority or recovering any operation.
    tables = {name for name, in db.execute("""SELECT name FROM sqlite_schema WHERE type='table'
        AND name IN ('ios_supervisor_authority','ios_custody_plans')""")}
    reusable = custody is not None and custody.reusable
    if not tables:
        scope = "$.ios_custody" if reusable else "$.ios_custody.version"
        require(db.execute("""SELECT 1 FROM operations
            WHERE json_type(value,?) IS NOT NULL LIMIT 1""", (scope,)).fetchone() is None)
        return
    require(reusable and tables == {"ios_supervisor_authority", "ios_custody_plans"})
    custody.check_authority(db)
    require(db.execute("""SELECT 1 FROM operations
        WHERE json_type(value,'$.ios_custody') IS NOT NULL
          AND (json_type(value,'$.ios_custody.version') IS NOT 'integer'
               OR json_extract(value,'$.ios_custody.version') IS NOT ?
               OR json_extract(value,'$.ios_custody.configuration') IS NOT ?)
        LIMIT 1""", (REUSABLE_VERSION, custody.configuration)).fetchone() is None)


class IOSCustody:
    def __init__(self, config):
        from compiler_worker import Refusal, digest, literal

        options = config["ios_custodian"]
        self.reusable = type(options.get("version")) is int and options["version"] == REUSABLE_VERSION
        self.operation = options.get("operation_id")
        if self.reusable:
            valid = (set(options) == {"version", "authority_id", "runtime_sha256"}
                     and is_sha256(options["authority_id"])
                     and type(config["worker_id"]) is str and bool(config["worker_id"]))
        else:
            valid = (set(options) == {"operation_id", "runtime_sha256"} and is_sha256(self.operation))
        if (not valid or _runtime is None or options["runtime_sha256"] != _runtime
                or config["registration"]["spec"]["platform"] != "ios"
                or "linux_runner" in config):
            raise Refusal("unavailable")
        self.registration = config["registration"]
        authority = {key: config[key] for key in ("tenant", "registration", "policy", "ios_custodian")}
        if self.reusable:
            authority["worker_id"] = config["worker_id"]
        self.configuration = digest(literal(authority).encode())

    def initialize(self, db):
        db.execute("""CREATE TABLE IF NOT EXISTS ios_custody_claims (
            operation TEXT PRIMARY KEY, plan_sha256 TEXT NOT NULL, guard TEXT NOT NULL,
            parent_pid INTEGER NOT NULL, launch TEXT, terminal TEXT,
            uncertain INTEGER NOT NULL DEFAULT 0) WITHOUT ROWID""")
        if self.reusable:
            db.execute("""CREATE TABLE IF NOT EXISTS ios_supervisor_authority (
                singleton INTEGER PRIMARY KEY CHECK (singleton=1), configuration TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS ios_custody_plans (
                operation TEXT PRIMARY KEY, plan TEXT NOT NULL) WITHOUT ROWID""")
            db.execute("INSERT OR IGNORE INTO ios_supervisor_authority VALUES (1,?)",
                       (self.configuration,))
            self.check_authority(db)
            db.execute("""UPDATE operations SET value=json_set(value,'$.status','uncertain')
                WHERE json_extract(value,'$.status')='running'
                  AND json_extract(value,'$.ios_custody.version')=?
                  AND json_extract(value,'$.ios_custody.configuration')=?""",
                       (REUSABLE_VERSION, self.configuration))
            return
        db.execute("""UPDATE operations SET value=json_set(value,'$.status','uncertain')
            WHERE id=? AND json_extract(value,'$.status')='running'
              AND json_extract(value,'$.ios_custody.configuration')=?""",
                   (self.operation, self.configuration))

    def check_authority(self, db):
        require(db.execute("SELECT configuration FROM ios_supervisor_authority WHERE singleton=1")
                .fetchone() == (self.configuration,))

    def matches(self, operation, row):
        intent = row["ios_custody"]
        if intent["configuration"] != self.configuration:
            return False
        if self.reusable:
            return type(intent.get("version")) is int and intent["version"] == REUSABLE_VERSION
        return operation == self.operation

    def submit(self, worker, operation, row, recipe):
        from compiler_worker import Refusal, digest, literal

        if self.reusable:
            plan = literal({"operation_id": operation, "binding": row["binding"], "recipe": recipe,
                            "configuration": self.configuration, "guard": row["guard"]})
            row.update(status="running", starts=1, ios_custody={
                "version": REUSABLE_VERSION, "configuration": self.configuration,
                "plan_sha256": digest(plan.encode()),
            })
            with worker.db:
                worker.db.execute("INSERT INTO ios_custody_plans VALUES (?,?)", (operation, plan))
                worker.write_operation(operation, row)
            return
        if operation != self.operation:
            raise Refusal("unavailable")
        # The current request guard may advance later. This snapshot never changes.
        row.update(status="running", starts=1, ios_custody={
            "guard": row["guard"], "recipe": recipe, "configuration": self.configuration,
        })
        worker.save(operation, row)

    def plan(self, db, operation, row):
        from compiler_worker import digest, literal

        require(row is not None and row["starts"] == 1 and self.matches(operation, row))
        intent = row["ios_custody"]
        if self.reusable:
            found = db.execute("SELECT plan FROM ios_custody_plans WHERE operation=?", (operation,)).fetchone()
            require(found is not None and digest(found[0].encode()) == intent["plan_sha256"])
            plan = json.loads(found[0])
            require(plan["operation_id"] == operation and plan["configuration"] == self.configuration
                    and literal(plan["binding"]) == literal(row["binding"]))
            return plan, intent["plan_sha256"]
        return intent, digest(literal({"operation_id": self.operation, "binding": row["binding"],
                                       "intent": intent}).encode())

    def launch_refusal(self, row, intent):
        from native_artifact_worker import literal, now_ms

        if row.get("tombstone"):
            return "stopped_before_launch"
        if literal(row["guard"]) != literal(intent["guard"]):
            return "guard_changed"
        if row["status"] != "running":
            return "admission_interrupted"
        if min(row["binding"]["deadline_ms"], intent["guard"]["expires_at"]) <= now_ms():
            return "admission_expired"
        return None

    def observe(self, state):
        import native_artifact_worker as native

        require(not self.reusable)
        private_directory(state)
        database = state / "operations.sqlite"
        with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as db:
            db.execute("PRAGMA synchronous=FULL")
            until = time.monotonic() + ADMISSION_SECONDS
            while time.monotonic() < until:
                row = load_row(db, self.operation)
                if row and "ios_custody" in row:
                    return self.claim_and_run(native, db, state, self.operation)
                if row and row["status"] != "absent":
                    break
                time.sleep(POLL_SECONDS)
            return False

    def supervise(self, state, stopping):
        import native_artifact_worker as native

        require(self.reusable)
        private_directory(state)
        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
        with os.fdopen(os.open(state / "ios-supervisor.lock", flags, 0o600), "wb") as lock:
            info = os.fstat(lock.fileno())
            require(info.st_mode == stat.S_IFREG | 0o600 and info.st_uid == os.getuid()
                    and info.st_nlink == 1)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            database = state / "operations.sqlite"
            with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as db:
                db.execute("PRAGMA synchronous=FULL")
                self.check_authority(db)
                while not stopping():
                    # No restart owns a prior claim's waitpid or launch rights.
                    require(db.execute("""SELECT 1 FROM ios_custody_claims
                        JOIN ios_custody_plans USING (operation)
                        WHERE terminal IS NULL LIMIT 1""").fetchone() is None)
                    pending = db.execute("""SELECT operation FROM ios_custody_plans
                        LEFT JOIN ios_custody_claims USING (operation)
                        WHERE ios_custody_claims.operation IS NULL LIMIT 1""").fetchone()
                    if pending is None:
                        time.sleep(POLL_SECONDS)
                    else:
                        self.claim_and_run(native, db, state, pending[0])
        return True

    def claim_and_run(self, native, db, state, operation):
        with db:
            db.execute("BEGIN IMMEDIATE")
            if self.reusable:
                self.check_authority(db)
            row = load_row(db, operation)
            intent, sha = self.plan(db, operation, row)
            ownership = Claim(operation, sha, native.literal(intent["guard"]), os.getpid())
            inserted = db.execute("""INSERT INTO ios_custody_claims
                (operation, plan_sha256, guard, parent_pid) VALUES (?,?,?,?)
                ON CONFLICT DO NOTHING""", ownership)
            if inserted.rowcount != 1:
                return False
            refusal = self.launch_refusal(row, intent)
            if refusal:
                self.record_terminal(native, db, ownership, {"not_started": refusal})
                return True

        try:
            return self.run_claim(native, db, state, ownership, intent, row["binding"]["deadline_ms"])
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, native.Refusal):
            # This owner may mark its claim uncertain but never relinquish it.
            with db:
                db.execute("""UPDATE ios_custody_claims SET uncertain=1
                    WHERE operation=? AND plan_sha256=? AND guard=? AND parent_pid=? AND terminal IS NULL""",
                           ownership)
            raise

    def run_claim(self, native, db, state, ownership, intent, operation_deadline):
        operation, sha, guard, parent_pid = ownership
        recipe = intent["recipe"]
        output = state / operation
        cli = Path(recipe["argv"][0])
        with ExitStack() as logs:
            try:
                cli_stamp = native.file_stamp(cli.lstat())
                require(cli.is_absolute() and cli.resolve(strict=True) == cli
                        and native.digest(native.read_owned(cli, native.LIMIT)) == recipe["tools"][str(cli)])
                project, _, tmp, _, argv, env = native.prepare_build(
                    recipe, self.registration["files"], output, None)
                stdout = logs.enter_context((output / "stdout").open("xb"))
                stderr = logs.enter_context((output / "stderr").open("xb"))
            except (OSError, native.Refusal):
                with db:
                    self.record_terminal(native, db, ownership, {"not_started": "preparation_failed"})
                return True

            with db:
                db.execute("BEGIN IMMEDIATE")
                row = load_row(db, operation)
                require(self.plan(db, operation, row)[1] == sha)
                refusal = self.launch_refusal(row, intent)
                if refusal:
                    self.record_terminal(native, db, ownership, {"not_started": refusal})
                    return True

            control, child = socket.socketpair()
            proc = None
            released = False
            admission_end = min(operation_deadline, intent["guard"]["expires_at"])
            with control, child:
                try:
                    launcher = [str(Path(sys.executable).resolve(strict=True)), "-IBS", "-c", INERT_LAUNCHER,
                                str(child.fileno()), str(admission_end), *argv]
                    proc = native.OwnedBuildProcess(launcher, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                                    stdout=stdout, stderr=stderr, start_new_session=True,
                                                    pass_fds=(child.fileno(),))
                    child.close()
                    pid = proc.pid
                    launch = {"pid": pid, "pgid": os.getpgid(pid), "sid": os.getsid(pid)}
                    require(pid > 1 and pid == launch["pgid"] == launch["sid"] and pid != parent_pid)
                    recorded = native.literal(launch)
                    with db:
                        changed = db.execute("""UPDATE ios_custody_claims SET launch=? WHERE operation=?
                            AND plan_sha256=? AND guard=? AND parent_pid=?
                            AND launch IS NULL AND terminal IS NULL AND uncertain=0""",
                                             (recorded, *ownership))
                        require(changed.rowcount == 1)

                    # Serialize the one-shot release with durable guard and stop writes.
                    with db:
                        db.execute("BEGIN IMMEDIATE")
                        row = load_row(db, operation)
                        require(self.plan(db, operation, row)[1] == sha)
                        claim = db.execute("""SELECT plan_sha256, guard, parent_pid, launch, terminal, uncertain
                            FROM ios_custody_claims WHERE operation=?""", (operation,)).fetchone()
                        require(claim == (sha, guard, parent_pid, recorded, None, 0))
                        if self.reusable:
                            self.check_authority(db)
                            require(os.getpgid(pid) == os.getsid(pid) == pid)
                        refusal = self.launch_refusal(row, intent)
                        if not refusal and native.file_stamp(cli.lstat()) != cli_stamp:
                            refusal = "preparation_failed"
                        runtime_start = time.monotonic()
                        now = native.now_ms()
                        if not refusal and admission_end <= now:
                            refusal = "admission_expired"
                        if not refusal:
                            deadline = runtime_start + min(recipe["timeout_seconds"],
                                                           (operation_deadline - now) / 1000)
                            require(control.send(b"\x01") == 1)
                            released = True
                finally:
                    try:
                        if not released:
                            control.close()  # EOF leaves the launcher inert.
                    finally:
                        if proc is not None:
                            code = self.reap(proc, db, operation, tmp if released else None,
                                             deadline if released else time.monotonic() + INERT_REAP_SECONDS)

                if released:
                    # The private channel is close-on-exec. Only the launcher
                    # can report expiry after release and before CLI entry.
                    control.setblocking(False)
                    report = control.recv(2)
                    require(report in (b"", b"E"))
                    if report == b"E":
                        refusal = "admission_expired"

        require(native.group_absent(proc.pid))
        outer = dict(launch, parent_pid=parent_pid, exit=code, direct_child_reaped=True,
                     group_absent=True, descriptors_closed=True)
        if refusal:
            require(code == 0)
            with db:
                self.record_terminal(native, db, ownership, {"not_started": refusal, "inert": outer})
            return True

        nested, proof = nested_closure(native, tmp, self.registration["files"])
        outcome = classify(code, nested[1], stop_requested=load_row(db, operation).get("tombstone") is True)
        with db:
            self.record_terminal(native, db, ownership, {"outer": outer, "nested": proof, "outcome": outcome})
        return True

    def reap(self, proc, db, operation, tmp, deadline):
        track_stop = tmp is not None
        stop_error = None
        while True:
            # Popen.wait can synthesize exit 0 on ECHILD. Only a matching waitpid counts.
            pid, status = os.waitpid(proc.pid, os.WNOHANG)
            if pid == proc.pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                if stop_error is not None:
                    raise stop_error
                return proc.returncode
            require(time.monotonic() < deadline)
            if track_stop:
                try:
                    row = load_row(db, operation)
                    if row is None:
                        raise ValueError("Operation missing while tracking stop")
                    if row.get("tombstone"):
                        fd = os.open(tmp / "cancel-requested", os.O_WRONLY | os.O_CREAT |
                                     os.O_EXCL | os.O_NOFOLLOW, 0o600)
                        os.close(fd)
                        track_stop = False
                except (OSError, sqlite3.Error, ValueError, TypeError) as error:
                    stop_error = error
                    track_stop = False
            time.sleep(POLL_SECONDS)

    def record_terminal(self, native, db, ownership, terminal):
        changed = db.execute("""UPDATE ios_custody_claims SET terminal=?
            WHERE operation=? AND plan_sha256=? AND guard=? AND parent_pid=?
              AND terminal IS NULL AND uncertain=0""", (native.literal(terminal), *ownership))
        require(changed.rowcount == 1)

    def reconcile(self, worker, operation, row):
        import native_artifact_worker as native

        claim = worker.db.execute("""SELECT plan_sha256, guard, parent_pid, launch, terminal, uncertain
            FROM ios_custody_claims WHERE operation=?""", (operation,)).fetchone()
        if claim is None or (claim[4] is None and not claim[5]):
            return
        try:
            require(not claim[5])
            result = self.terminal_result(native, worker.db, operation, worker.state / operation, row, claim[:5])
        except (OSError, ValueError, KeyError, TypeError, native.Refusal):
            row["status"] = "uncertain"
            worker.save(operation, row)
            return
        if row["guard"]["expires_at"] <= native.now_ms():
            raise native.Refusal("stale")
        log = result.pop("customer_log", None)
        if log is not None:
            try:
                native.publish_customer_log(worker.state, operation, row["binding"]["spec"], log,
                                            idempotent=True)
            except (OSError, ValueError, native.Refusal):
                pass
        # All operation writes are serialized by the listener. Recheck the
        # authenticated lease after artifact verification and log publication.
        if self.reusable and row["guard"]["expires_at"] <= native.now_ms():
            raise native.Refusal("stale")
        artifacts = result.pop("artifacts", None)
        manifest_sha = result.pop("manifest_sha256", None)
        row.update(status="closed", closure=result)
        if artifacts is not None:
            row.update(status="native_ready", artifacts=artifacts, manifest_sha256=manifest_sha)
        worker.save(operation, row)

    def terminal_result(self, native, db, operation, output, row, claim):
        sha, guard, parent_pid, launch, terminal = claim
        intent, expected = self.plan(db, operation, row)
        require(sha == expected and guard == native.literal(intent["guard"]) and parent_pid > 1)
        terminal = json.loads(terminal)
        if "not_started" in terminal:
            require(terminal["not_started"] in (
                "stopped_before_launch", "guard_changed", "admission_interrupted",
                "admission_expired", "preparation_failed"))
            if launch is None:
                require(set(terminal) == {"not_started"})
            else:
                require(set(terminal) == {"not_started", "inert"})
                _, code = self.closed_outer(native, launch, parent_pid, terminal["inert"])
                require(code == 0)
            return {"closed": True, "started": False, "preflight_failed": True, "ios_custody": terminal}

        pid, code = self.closed_outer(native, launch, parent_pid, terminal["outer"])
        nested, proof = nested_closure(native, output / "tmp", self.registration["files"])
        require(terminal["nested"] == proof)
        outcome = classify(code, nested[1], stop_requested=row.get("tombstone") is True)
        require(terminal["outcome"] == outcome)
        result = native.collect_build_result(
            output, intent["recipe"], self.registration["files"], row["binding"]["spec"], pid, code, nested,
            stop_before_artifacts=row.get("tombstone", False) or outcome != "succeeded",
        )
        require(not isinstance(result, native.BuildUncertainty))
        if outcome == "succeeded" and "artifacts" not in result and not row.get("tombstone"):
            outcome = "artifact_refused"
        result.update(ios_custody=terminal, ios_outcome=outcome)
        return result

    def closed_outer(self, native, launch, parent_pid, outer):
        launch = json.loads(launch)
        pid, code = launch["pid"], outer["exit"]
        require(type(pid) is int and pid > 1 and pid != parent_pid and type(code) is int
                and native.literal(launch) == native.literal({"pid": pid, "pgid": pid, "sid": pid})
                and native.literal(outer) == native.literal(dict(
                    launch, parent_pid=parent_pid, exit=code, direct_child_reaped=True,
                    group_absent=True, descriptors_closed=True)))
        return pid, code


def main(argv):
    action, configuration, expected, state = argv
    config_bytes = Path(configuration).read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != expected:
        raise ValueError("Configuration digest mismatch")
    config = json.loads(config_bytes)
    native = bootstrap(config)
    os.umask(0o077)
    if action == "worker":
        native.serve(config, state)
        return 0
    if action in ("observe", "supervisor"):
        try:
            custody = IOSCustody(config)
            if action == "observe":
                return 0 if custody.observe(Path(state)) else 3

            stopping = False

            def stop(signum, frame):
                nonlocal stopping
                stopping = True

            signal.signal(signal.SIGINT, stop)
            signal.signal(signal.SIGTERM, stop)
            return 0 if custody.supervise(Path(state), lambda: stopping) else 3
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, native.Refusal):
            return 74
    raise ValueError("Invalid iOS custody role")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
