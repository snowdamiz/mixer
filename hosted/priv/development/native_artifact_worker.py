"""Opt-in local worker for one operator-registered unsigned iOS Simulator project."""
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import socketserver
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid

from compiler_worker import Refusal, Worker, digest, literal
import starter_package_closure as starter

KINDS = ("unsigned_native_binary", "debug_symbols", "resource_inventory")
LIMIT = 256 * 1024 * 1024


class OwnedBuildProcess(subprocess.Popen):
    def __del__(self):
        # On UNKNOWN, only the recorded owner may act. Popen's finalizer
        # otherwise polls and can enqueue the child for implicit future reaps.
        pass


class LaunchGate:
    def __init__(self):
        self.lock = threading.Lock()
        self.cancelled = False
        self.control_directory = None

    def request_cli_stop(self):
        if self.control_directory is not None:
            # The durable tombstone already exists. Only this operation's
            # CLI can interpret the marker and signal its admitted child.
            marker = self.control_directory / "cancel-requested"
            try:
                fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            except FileExistsError:
                return
            os.close(fd)


def now_ms():
    return time.time_ns() // 1_000_000


def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except OSError as error:
        return error.errno == errno.ESRCH
    return False


def read_owned(path, limit, *, allow_owner_write=False):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & (0o022 if allow_owner_write else 0o222)
                or not 0 < before.st_size <= limit):
            raise Refusal("uncertain")
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        named = path.lstat()
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_ctime_ns, s.st_mtime_ns)
        if len(data) != before.st_size or stamp(before) != stamp(after) or stamp(after) != stamp(named):
            raise Refusal("uncertain")
        return data


def check_artifact(store, descriptor, kind):
    sha = descriptor["sha256"]
    if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise Refusal("uncertain")
    path = store / sha
    if descriptor["kind"] != kind or descriptor["ownedPath"] != str(path):
        raise Refusal("uncertain")
    data = read_owned(path, LIMIT)
    if len(data) != descriptor["sizeBytes"] or digest(data) != sha:
        raise Refusal("uncertain")
    return {"kind": kind, "sha256": sha, "sizeBytes": len(data)}


def compiler_log(receipt):
    fields = ("exitCode", "stdoutBytes", "stderrBytes")
    values = {key: receipt.get(key) for key in fields}
    truncated = receipt.get("outputTruncated")
    if (any(type(value) is not int for value in values.values())
            or not -255 <= values["exitCode"] <= 255
            or not all(0 <= values[key] <= 2**32 for key in fields[1:])
            or type(truncated) is not bool):
        raise ValueError("Invalid compiler log fields")
    return dict(values, tailTruncated=truncated, phases=[])


def publish_customer_log(state, operation, spec, log):
    # Keep the public projection outside the per-operation compiler tree.
    # The final name is immutable and never replaces an earlier publication.
    payload = literal(dict(log, version=1, operationId=operation,
                           sourceSha256=spec["source"]["sha256"],
                           toolchainLockSha256=spec["toolchain_lock_sha256"],
                           buildDefinitionSha256=spec["build_definition_sha256"])).encode()
    root = state.lstat()
    if (state.resolve() != state or root.st_uid != os.getuid()
            or root.st_mode != stat.S_IFDIR | 0o700):
        raise ValueError("Invalid retained root")
    fd, name = tempfile.mkstemp(prefix=".customer-log-", dir=state)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fchmod(handle.fileno(), 0o400)
            os.fsync(handle.fileno())
        os.link(name, state / ("customer-log-v1-" + operation), follow_symlinks=False)
    finally:
        os.unlink(name)


def build(recipe, files, output, request, launch):
    output.mkdir(mode=0o700)
    project, store, tmp, home = (output / p for p in ("project", "native", "tmp", "home"))
    for directory in (project, tmp, home):
        directory.mkdir(mode=0o700)
    for relative, sha in files.items():
        source = Path(recipe["cwd"]) / relative
        if source.is_symlink() or not source.resolve().is_relative_to(recipe["cwd"]):
            raise Refusal("unavailable")
        data = source.read_bytes()
        if digest(data) != sha:
            raise Refusal("unavailable")
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    environment = dict(recipe["environment"], TMPDIR=str(tmp), CFFIXED_USER_HOME=str(home))
    argv = [*recipe["argv"][:-1], str(project), "--output", str(store)]
    launch_environment = dict(environment, MIXER_WORKER_COMMAND_CONTROL="1")
    if starter.KEY in recipe:
        launch_environment["HOME"] = str(home)
    with (output / "stdout").open("xb") as stdout, (output / "stderr").open("xb") as stderr:
        with launch.lock:
            now = now_ms()
            remaining = min(recipe["timeout_seconds"], (request["deadline_ms"] - now) / 1000)
            if launch.cancelled or remaining <= 0 or request["guard"]["expires_at"] <= now:
                return {"closed": True, "started": False}
            proc = OwnedBuildProcess(argv, cwd=project, env=launch_environment,
                                     stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr, start_new_session=True)
            launch.control_directory = tmp
        (output / "launch.json").write_text(literal({"pid": proc.pid, "argv": argv}))
        try:
            code = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return {"closed": False}
    # The pinned CLI acknowledges only after its synchronous command scope
    # unwinds without a hold. Never inspect command scratch without that proof.
    try:
        prefix = "mixer-command-receipts-"
        basename = read_owned(tmp / "cli-closed", len(prefix) + 36, allow_owner_write=True).decode("ascii")
        if not basename.startswith(prefix) or str(uuid.UUID(basename[len(prefix):])).upper() != basename[len(prefix):]:
            return {"closed": False}
        if not group_absent(proc.pid):
            return {"closed": False}
        receipt_root = tmp / basename
        try:
            root_info = receipt_root.lstat()
        except FileNotFoundError:
            directories = []
        else:
            if root_info.st_mode != stat.S_IFDIR | 0o700 or root_info.st_uid != os.getuid():
                return {"closed": False}
            directories = sorted(receipt_root.iterdir())
        commands, proof = [], []
        for command in directories:
            if not command.name.startswith("command-"):
                continue
            if not stat.S_ISDIR(command.lstat().st_mode):
                return {"closed": False}
            try:
                (command / "HOLD.json").lstat()
            except FileNotFoundError:
                pass
            else:
                return {"closed": False}
            receipt = command / "receipt.json"
            if not stat.S_ISREG(receipt.lstat().st_mode):
                return {"closed": False}
            data = receipt.read_bytes()
            item = json.loads(data)
            argv_receipt = item["command"]
            if (type(argv_receipt) is not list or not argv_receipt
                    or not all(type(arg) is str for arg in argv_receipt) or not argv_receipt[0].startswith("/")
                    or item["state"] != "TERMINAL"
                    or any(type(item[key]) is not int for key in ("pid", "ownedPGID", "ownedSession"))
                    or item["pid"] != item["ownedPGID"]
                    or item["pid"] != item["ownedSession"] or item["pid"] <= 1
                    or not all(item.get(key) is True for key in ("terminalCustody", "directChildReaped",
                               "stdoutEOF", "stderrEOF", "descriptorsClosed", "ownedGroupAbsent"))):
                return {"closed": False}
            commands.append(item)
            proof.append({"command": argv_receipt[0], "pid": item["pid"],
                          "receipt_sha256": digest(data), "stop_reason": item.get("stopReason"),
                          "group_terminate_sent": item.get("groupTerminateSent", False)})
    except (OSError, ValueError, KeyError, TypeError, Refusal):
        return {"closed": False}
    compiler = [c for c in commands if c["command"][0] == "/usr/bin/xcodebuild"]
    if len(compiler) > 1 or (not compiler and code <= 0):
        return {"closed": False}
    result = {"closed": True, "started": True, "pid": proc.pid, "exit": code,
              "cli_reaped": True, "cli_group_absent": True, "commands": proof}
    if not compiler:
        result["preflight_failed"] = True
    try:
        (output / "closure.json").write_text(literal(result))
    except OSError:
        pass
    try:
        result["customer_log"] = {"cliExitCode": code,
                                  "compiler": compiler_log(compiler[0]) if compiler else None}
    except ValueError:
        pass  # Log projection cannot change the original build or closure outcome.
    if not compiler:
        return result
    try:
        manifest = read_owned(store / "native-build.json", 8 * 1024 * 1024)
        report = json.loads(manifest)
        binding = report["binding"]
        command = compiler[0]["command"]
        if (report["formatVersion"] != 2
                or report["scope"] != "unsigned-simulator/local-development"
                or command != binding["command"] or "CODE_SIGNING_ALLOWED=NO" not in command
                or "generic/platform=iOS Simulator" not in command
                or binding["authoritativeSourceDigest"] != request["spec"]["source"]["sha256"]
                or binding["lockSHA256"] != request["spec"]["toolchain_lock_sha256"]
                or binding["cliExecutableSHA256"] != recipe["tools"][argv[0]]
                or binding["environment"] != environment
                or binding["resourceInventoryPolicy"] != "retained-app-files-v1"):
            return result
        command_result = report["commandResult"]
        log = result.get("customer_log")
        if log and command_result["exitCode"] == log["compiler"]["exitCode"]:
            output_tail = command_result.get("output")
            if isinstance(output_tail, str):
                steps = {line.partition(" ")[0] for line in output_tail[-65_536:].splitlines()}
                log["compiler"]["phases"] = [
                    phase for phase, commands in (
                        ("compile", {"SwiftCompile", "CompileC"}),
                        ("link", {"Ld"}),
                        ("package", {"ProcessInfoPlistFile", "CopySwiftLibs"}),
                    ) if not steps.isdisjoint(commands)
                ]
        if code != 0 or command_result["exitCode"] != 0:
            return result
        products = report["nativeProduct"]
        descriptors = (products["nativeBinary"], products["debugSymbols"], report["resourceInventory"])
        result["artifacts"] = [check_artifact(store, d, k) for d, k in zip(descriptors, KINDS)]
        result["manifest_sha256"] = digest(manifest)
    except (OSError, ValueError, KeyError, TypeError, Refusal):
        pass  # Known closure survives refused or missing artifact evidence.
    return result


class NativeWorker(Worker):
    def __init__(self, config, state):
        os.umask(0o077)
        Path(state).mkdir(mode=0o700, exist_ok=True)
        path = Path(state)
        info = path.lstat()
        if (not path.is_absolute() or path.resolve() != path or info.st_uid != os.getuid()
                or info.st_mode != stat.S_IFDIR | 0o700):
            raise Refusal("unavailable")
        super().__init__(config, state)
        self.launch = None
        self.db.execute("CREATE TABLE IF NOT EXISTS request_nonces (nonce BLOB PRIMARY KEY) WITHOUT ROWID")

    def consume_nonce(self, nonce):
        # Keep spent nonces with the operation state, including across shutdown
        # and restart. Commit before dispatch even when the action may refuse.
        with self.db:
            inserted = self.db.execute(
                "INSERT INTO request_nonces VALUES (?) ON CONFLICT DO NOTHING",
                (bytes.fromhex(nonce),),
            )
        if inserted.rowcount == 0:
            raise Refusal("stale")

    def verify(self, spec):
        recipe = super().verify(spec)
        env = recipe["environment"]
        cli = recipe["argv"][0]
        if (spec["platform"] != "ios" or recipe.get("profile") != "unsigned-ios-simulator-v1"
                or cli not in recipe["tools"] or "/usr/bin/xcodebuild" not in recipe["tools"]
                or env.get("PATH") != "/usr/bin:/bin:/usr/sbin:/sbin"
                or set(env) - {"PATH", "DEVELOPER_DIR", "LANG", "LC_ALL"}
                or type(recipe["timeout_seconds"]) is not int
                or not 1 <= recipe["timeout_seconds"] <= 1800):
            raise Refusal("unavailable")
        policy = self.config["policy"]
        if starter.KEY in recipe or starter.KEY in policy:
            if (recipe.get(starter.KEY) != starter.VERSION or policy.get(starter.KEY) != starter.VERSION
                    or recipe["inputs"] != self.config["registration"]["files"]
                    or set(recipe["tools"]) != {cli, "/usr/bin/xcodebuild"}):
                raise Refusal("unavailable")
            try:
                starter.check_starter_inputs(recipe["inputs"], (Path(recipe["cwd"]) / "mixer.lock").read_bytes())
            except (OSError, ValueError, AttributeError) as error:
                raise Refusal("unavailable") from error
        return recipe

    def finish(self):
        if self.future is None or not self.future.done():
            return
        value = self.load(self.active)
        try:
            result = self.future.result()
        except Exception:
            result = {"closed": False}
        value["status"] = "uncertain"
        if result["closed"]:
            value.update(status="closed", closure={k: v for k, v in result.items()
                                                   if k not in ("artifacts", "manifest_sha256", "customer_log")})
            if "artifacts" in result and not value.get("tombstone"):
                value.update(status="native_ready", artifacts=result["artifacts"],
                             manifest_sha256=result["manifest_sha256"])
        self.save(self.active, value)
        if "customer_log" in result:
            try:
                publish_customer_log(self.state, self.active, value["binding"]["spec"],
                                     result["customer_log"])
            except (OSError, ValueError):
                pass  # A missing export does not change custody or artifact delivery.
        self.future = None
        self.active = None
        self.launch = None

    def stop(self, operation, value):
        value["tombstone"] = True
        if value["status"] in ("running", "uncertain"):
            value["status"] = "uncertain"
            if self.active == operation:
                # Block a final spawn while committing the tombstone. Keep the
                # in-memory revocation even if persistence fails.
                with self.launch.lock:
                    self.launch.cancelled = True
                    self.save(operation, value)
                    self.launch.request_cli_stop()
            else:
                self.save(operation, value)
            return {"error": "uncertain"}

        # Persist the tombstone before attempting the evidence write.
        value["status"] = "closed"
        self.save(operation, value)
        sha = self.closure_diagnostic(operation, value)
        value.update(status="stopped", diagnostic_sha256=sha)
        self.save(operation, value)
        return {"status": "stopped", "diagnostic_sha256": sha}

    def closure_diagnostic(self, operation, value):
        return self.blob((literal({"operation_id": operation, "closure": value["closure"]}) + "\n").encode())

    def request(self, action, request):
        if action not in ("query", "ensure_started", "stop", "artifacts"):
            raise Refusal("unavailable")
        self.authorize(request["spec"])
        if action == "ensure_started" and request["deadline_ms"] <= now_ms():
            raise Refusal("stale")
        reply = super().request("query", request)
        operation = request["operation_id"]
        value = self.load(operation)
        status = value["status"]
        if action == "stop":
            if status == "absent":
                return super().request("stop", request)
            if status == "stopped":
                return reply
            return self.stop(operation, value)
        if action == "artifacts" and status == "native_ready" and now_ms() < request["deadline_ms"]:
            store = self.state / operation / "native"
            if digest(read_owned(store / "native-build.json", 8 * 1024 * 1024)) != value["manifest_sha256"]:
                raise Refusal("uncertain")
            for descriptor in value["artifacts"]:
                check_artifact(store, dict(descriptor, ownedPath=str(store / descriptor["sha256"])),
                               descriptor["kind"])
            return {"status": "native_ready", "artifacts": value["artifacts"]}
        if action == "artifacts":
            raise Refusal("unavailable")
        if status == "closed" and not value.get("tombstone") and value["closure"].get("preflight_failed"):
            return {"status": "preflight_failed", "diagnostic_sha256": self.closure_diagnostic(operation, value)}
        if status in ("closed", "native_ready"):
            # Reconciliation can install the stop tombstone when its deadline expires.
            return {"status": "running"}
        if action == "ensure_started" and status == "absent" and not value.get("tombstone"):
            recipe = self.verify(request["spec"])
            occupied = self.db.execute("SELECT 1 FROM operations WHERE json_extract(value,'$.status') IN ('running','uncertain')").fetchone()
            if self.future is not None or occupied:
                raise Refusal("unavailable")
            value.update(status="running", starts=1)
            self.save(operation, value)
            self.active = operation
            self.launch = LaunchGate()
            self.future = self.executor.submit(build, recipe, self.config["registration"]["files"],
                                               self.state / operation, request, self.launch)
            return {"status": "running"}
        return reply

    def close(self):
        self.finish()
        if self.db.execute("SELECT 1 FROM operations WHERE json_extract(value,'$.status')='uncertain'").fetchone():
            raise Refusal("uncertain")
        super().close()


def mac(token, direction, nonce, body):
    data = (direction + "\n" + nonce + "\n" + body).encode()
    return hmac.new(token.encode(), data, hashlib.sha256).hexdigest()


def exchange(worker, envelope):
    config = worker.config
    nonce = envelope["nonce"]
    body = envelope["body"]
    if (len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce)
            or not hmac.compare_digest(envelope["mac"], mac(config["token"], "request", nonce, body))):
        raise Refusal("unavailable")
    message = json.loads(body)
    if message["worker_id"] != config["worker_id"]:
        raise Refusal("unavailable")
    close = message["action"] == "shutdown"
    try:
        worker.consume_nonce(nonce)
        if close:
            worker.close()
            body = {"status": "closed"}
        else:
            body = worker.request(message["action"], message["request"])
    except Refusal as error:
        close, body = False, {"error": str(error)}
    body = literal(body)
    return close, {"body": body, "mac": mac(config["token"], "response", nonce, body)}


def serve(config, state):
    worker = NativeWorker(config, state)

    class Handler(socketserver.StreamRequestHandler):
        timeout = 1

        def handle(self):
            try:
                packet = self.rfile.readline(262_145)
                if len(packet) > 262_144 or not packet.endswith(b"\n"):
                    return
                close, reply = exchange(worker, json.loads(packet))
            except (Refusal, ValueError, KeyError, TypeError, OSError):
                return
            self.server.closed = close
            self.wfile.write((literal(reply) + "\n").encode())

    with socketserver.TCPServer(("127.0.0.1", config["port"]), Handler) as server:
        server.timeout = 0.1
        server.closed = False
        while not server.closed:
            server.handle_request()
            if not server.closed:
                worker.finish()


if __name__ == "__main__":
    configuration = Path(sys.argv[1]).read_bytes()
    if digest(configuration) != sys.argv[2]:
        raise SystemExit("Configuration digest mismatch")
    serve(json.loads(configuration), sys.argv[3])
