"""Owned benign development compiler worker; process separation is not a sandbox.

One Worker owns durable writes. Its serving loop serializes requests and compiler
completion. A compiler thread owns only the pinned command custodian/output path.
No source is resolved from a request path, URL, input id or job argument.
"""
import ast
import concurrent.futures
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import subprocess
import sys
import time

def digest(data):
    return hashlib.sha256(data).hexdigest()

def literal(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))

class Refusal(Exception):
    pass

class Worker:
    def __init__(self, config, state):
        self.config = config
        self.state = Path(state)
        self.state.mkdir(parents=True, exist_ok=True)
        self.lock = (self.state / "writer.lock").open("ab")
        fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.db = sqlite3.connect(self.state / "operations.sqlite")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
        # Independent iOS custody recovers only rows bound to its configuration.
        self.db.execute("""UPDATE operations SET value=json_set(value,'$.status','uncertain')
            WHERE json_extract(value,'$.status')='running' AND json_type(value,'$.ios_custody') IS NULL""")
        self.db.commit()
        self.future = None
        self.active = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def close(self):
        if self.future is not None:
            raise Refusal("uncertain")
        self.executor.shutdown(wait=False)
        self.db.close()
        self.lock.close()

    def load(self, operation):
        value = self.db.execute("SELECT value FROM operations WHERE id=?", (operation,)).fetchone()
        return json.loads(value[0]) if value else None

    def save(self, operation, value):
        self.db.execute("INSERT INTO operations VALUES(?,?) ON CONFLICT(id) DO UPDATE SET value=excluded.value", (operation, literal(value)))
        self.db.commit()

    def blob(self, data):
        sha = digest(data)
        directory = self.state / "blobs"
        directory.mkdir(exist_ok=True)
        target = directory / sha
        if not target.exists():
            with target.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        if digest(target.read_bytes()) != sha:
            raise Refusal("uncertain")
        return sha

    def authorize(self, spec):
        fields = ("organization_id", "project_id", "application_id", "platform", "source", "toolchain_lock_sha256", "build_definition_sha256")
        key = {field: spec[field] for field in fields}
        grant = self.config["registration"]
        if key != grant["spec"] or key["organization_id"] != self.config["tenant"]:
            raise Refusal("unavailable")
        return grant

    def verify(self, spec):
        return self.verify_recipe(spec, "ios", "exact-owned-local-manifests-no-external-packages")

    def verify_recipe(self, spec, platform, package_policy):
        grant = self.authorize(spec)
        key = grant["spec"]
        root = Path(grant["root"])
        if not root.is_absolute() or any(p.is_symlink() for p in [root, *root.parents]):
            raise Refusal("unavailable")
        files = {}
        excluded = {".build", ".git", ".swiftpm", "node_modules", ".gradle", ".mixer", "target", ".DS_Store"}
        for parent, directories, names in os.walk(root, followlinks=False):
            for name in directories + names:
                path = Path(parent) / name
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise Refusal("unavailable")
                if name in excluded or name.lower().startswith(".env") or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx", ".mobileprovision", ".keystore", ".jks"}:
                    raise Refusal("unavailable")
                if path.is_file():
                    files[str(path.relative_to(root))] = digest(path.read_bytes())
        if files != grant["files"]:
            raise Refusal("unavailable")
        tree = digest("".join(p + "\0" + sha + "\n" for p, sha in sorted(files.items())).encode())
        if tree != key["source"]["sha256"] or digest((root / "mixer.lock").read_bytes()) != key["toolchain_lock_sha256"]:
            raise Refusal("unavailable")
        recipe_bytes = Path(grant["recipe"]).read_bytes()
        recipe = json.loads(recipe_bytes)
        policy = self.config["policy"]
        if digest(recipe_bytes) != key["build_definition_sha256"] or digest(recipe_bytes) != policy["recipe_sha256"]:
            raise Refusal("unavailable")
        if (key["platform"] != platform
                or recipe["argv"] != [policy["cli"], "build", "--platform", platform, "--directory", str(root)]
                or recipe["cwd"] != str(root)):
            raise Refusal("unavailable")
        if recipe["environment"] != policy["environment"] or recipe["package_policy"] != package_policy:
            raise Refusal("unavailable")
        # The trusted setup pins every manifest, capability and SDK file, rather
        # than trying to authorize executable package manifests with syntax scans.
        if recipe["inputs"] != policy["inputs"] or recipe["tools"] != policy["tools"]:
            raise Refusal("unavailable")
        for path, sha in policy["inputs"].items():
            if files.get(path) != sha:
                raise Refusal("unavailable")
        for path, sha in policy["tools"].items():
            if digest(Path(path).read_bytes()) != sha:
                raise Refusal("unavailable")
        return recipe

    def finish(self):
        if self.future is None or not self.future.done():
            return
        operation = self.active
        value = self.load(operation)
        try:
            result = self.future.result()
            if result["terminal_custody"]:
                sha = self.blob(result["diagnostic"])
                value.update(diagnostic_sha256=sha, custody=result["custody"])
                if value.get("tombstone"):
                    value["status"] = "stopped"
                elif result["compiler_error"]:
                    value["status"] = "completed"
                else:
                    value["status"] = "unavailable"
            else:
                value["status"] = "uncertain"
        except BaseException as error:
            value.update(status="uncertain", failure=repr(error))
        self.save(operation, value)
        self.active = None
        self.future = None

    def request(self, action, request):
        self.finish()
        now = time.time_ns() // 1_000_000
        guard = request["guard"]
        if any(request["ref"][key] != request["spec"][key] for key in ("organization_id", "project_id", "application_id", "build_id", "platform")):
            raise Refusal("unavailable")
        if guard["expires_at"] <= now or (action == "ensure_started" and request["deadline_ms"] <= now):
            raise Refusal("stale")
        operation = request["operation_id"]
        if len(operation) != 64 or any(c not in "0123456789abcdef" for c in operation):
            raise Refusal("unavailable")
        binding = {key: request[key] for key in ("ref", "spec", "deadline_ms")}
        value = self.load(operation)
        order = [guard["epoch"], guard["revision"]]
        if value:
            if value["binding"] != binding:
                raise Refusal("unavailable")
            if order < value["order"] or (order == value["order"] and
                (guard["owner_id"] != value["guard"]["owner_id"] or guard["expires_at"] < value["guard"]["expires_at"])):
                raise Refusal("stale")
            if guard["record_id"] != value["guard"]["record_id"]:
                raise Refusal("stale")
        else:
            # Registration authorization is required even for an absent query.
            self.authorize(request["spec"])
            value = {"binding": binding, "status": "absent", "starts": 0}
        value.update(order=order, guard=guard)
        if action == "stop":
            value["tombstone"] = True
            if value["status"] == "absent":
                value.update(status="stopped", diagnostic_sha256=self.blob(b"development stop before start\n"))
            elif value["status"] not in ("completed", "stopped", "unavailable"):
                value["status"] = "uncertain"
        elif action == "ensure_started" and value["status"] == "absent" and not value.get("tombstone"):
            recipe = self.verify(request["spec"])
            occupied = self.db.execute("SELECT id FROM operations WHERE json_extract(value,'$.status') IN ('running','uncertain')").fetchone()
            if self.future is not None or occupied:
                raise Refusal("unavailable")
            # Commit possible execution before submitting it. Crash in this gap
            # retains uncertainty and never silently retries or releases capacity.
            value.update(status="running", starts=1)
            self.save(operation, value)
            self.active = operation
            self.future = self.executor.submit(execute, self.config, recipe, self.state / "command", request)
        elif action not in ("query", "ensure_started", "stop"):
            raise Refusal("unavailable")
        self.save(operation, value)
        if value["status"] in ("uncertain", "unavailable"):
            return {"error": value["status"]}
        if value["status"] in ("completed", "stopped"):
            sha = value["diagnostic_sha256"]
            if digest((self.state / "blobs" / sha).read_bytes()) != sha:
                return {"error": "uncertain"}
        return {k: value[k] for k in ("status", "diagnostic_sha256") if k in value}

def execute(config, recipe, output, request):
    now = time.time_ns() // 1_000_000
    if min(request["deadline_ms"], request["guard"]["expires_at"]) <= now:
        raise Refusal("stale")
    output.mkdir(parents=True, exist_ok=False)
    path = Path(config["custodian"])
    data = path.read_bytes()
    if digest(data) != "ff48bf22b68ea737978f72bf8cc6a6a0f0f3c31afc26ce12168fcbaec7f81a52":
        raise Refusal("unavailable")
    namespace = dict(globals(), ROOT=Path(recipe["cwd"]), OUT=output, records=[])
    namespace["save"] = lambda name, value: (output / name).write_text(json.dumps(value, indent=2) + "\n")
    definitions = [n for n in ast.parse(data).body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in ("InertPopen", "run")]
    exec(compile(ast.Module(body=definitions, type_ignores=[]), str(path), "exec"), namespace)
    receipt_parent = Path(recipe["environment"]["TMPDIR"])
    previous = set(receipt_parent.glob("mixer-command-receipts-*"))
    try:
        namespace["run"]("public-compiler", ["/usr/bin/env", "-i", *[k + "=" + v for k, v in recipe["environment"].items()], *recipe["argv"]], timeout=min(recipe["timeout_seconds"], (request["deadline_ms"] - now) / 1000))
    except AssertionError:
        pass  # Nonzero exit is expected; custody facts still must all be true.
    record = namespace["records"][-1]
    terminal = all(record.get(key) for key in ("bothEOF", "closedFDs", "ownedGroupAbsentESRCH")) and record.get("state") == "direct_reaped"
    if not terminal:
        return {"terminal_custody": False}
    raw = (output / "public-compiler.stdout").read_bytes()
    stderr = (output / "public-compiler.stderr").read_bytes()
    nested = []
    for directory in set(receipt_parent.glob("mixer-command-receipts-*")) - previous:
        for command in directory.glob("command-*"):
            hold = command / "HOLD.json"
            receipt = command / "receipt.json"
            if hold.exists():
                namespace["save"]("nested-custody.json", {"terminal": False, "hold": str(hold)})
                return {"terminal_custody": False}
            if not receipt.is_file():
                return {"terminal_custody": False}
            item = json.loads(receipt.read_bytes())
            nested.append(item)
            if not all(item.get(k) for k in ("terminalCustody", "directChildReaped", "stdoutEOF", "stderrEOF", "descriptorsClosed", "ownedGroupAbsent")):
                return {"terminal_custody": False}
    namespace["save"]("nested-custody.json", {"terminal": bool(nested), "commands": nested})
    if not nested:
        return {"terminal_custody": False}
    valid = False
    try:
        result = json.loads(raw)
        diagnostic = result["output"]
        valid = result["exitCode"] != 0 and not result["outputTruncated"] and result["command"][0] == "xcodebuild" and "CODE_SIGNING_ALLOWED=NO" in result["command"] and "DeliberateTypeError.swift" in diagnostic and "cannot convert value of type 'String' to specified type 'Int'" in diagnostic
    except (KeyError, ValueError, TypeError):
        pass
    return {"terminal_custody": True, "compiler_error": valid,
            "diagnostic": raw + b"\n---stderr---\n" + stderr, "custody": record}

def serve(config, state):
    worker = Worker(config, state)
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", config["port"]))
        server.listen(8)
        server.settimeout(.05)
        while True:
            worker.finish()
            try:
                connection, _ = server.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(1)
                try:
                    packet = bytearray()
                    while not packet.endswith(b"\n"):
                        chunk = connection.recv(4096)
                        if not chunk or len(packet) + len(chunk) > 262144:
                            raise Refusal("unavailable")
                        packet.extend(chunk)
                    message = json.loads(packet)
                    if message["worker_id"] != config["worker_id"] or not hmac.compare_digest(message["token"], config["token"]):
                        raise Refusal("unavailable")
                    if message["action"] == "shutdown":
                        worker.close()
                        connection.sendall(b'{"status":"closed"}\n')
                        return
                    reply = worker.request(message["action"], message["request"])
                except Refusal as error:
                    reply = {"error": str(error)}
                except (KeyError, ValueError, TypeError, OSError):
                    reply = {"error": "unavailable"}
                connection.sendall((literal(reply) + "\n").encode())

if __name__ == "__main__":
    configuration = Path(sys.argv[1]).read_bytes()
    assert digest(configuration) == sys.argv[2]
    serve(json.loads(configuration), sys.argv[3])
