"""Private v1 client for one operator-pinned Linux Android recipe.

The runner's store owns idempotent ensure and permanent stop for each exact
operation, including a stop received before its first ensure. A stopped reply
attests to positive observation of container, process, and resource cleanup
in that store. The runner must listen as the operator's user. Each connection
exchanges one newline-terminated JSON request and one response before EOF.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import os
import socket
import stat
import struct
import sys
import time

from compiler_worker import Refusal, digest, literal


VERSION = 1
FRAME_LIMIT = 4096
TIMEOUT_SECONDS = 1
TERMINAL = {"stop_fenced": True, "container_absent": True,
            "processes_absent": True, "resources_removed": True}
COMPLETION_FACTS = ("start_fenced", "container_absent", "processes_absent", "resources_removed")


def sha256(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def positive_integer(value):
    return type(value) is int and 0 < value < 2**63


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


def peer_uid(connection):
    if sys.platform == "linux":
        ucred = struct.Struct("=iII")  # pid, uid, gid
        return ucred.unpack(connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, ucred.size))[1]
    if sys.platform == "darwin":
        # SOL_LOCAL=0, LOCAL_PEERCRED=1. The Darwin xucred prefix is version, uid.
        credentials = connection.getsockopt(0, 1, 255)
        version, uid = struct.unpack_from("=II", credentials)
        if version == 0:
            return uid
    raise ValueError("unsupported runner peer credentials")


@dataclass(frozen=True)
class RunnerIdentity:
    operation_id: str
    binding_sha256: str
    recipe_sha256: str
    store_id: str


@dataclass(frozen=True)
class RunnerGuard:
    record_id: str
    epoch: int
    revision: int
    owner_id: str
    expires_at: int

    def __post_init__(self):
        if (not all(type(value) is str and 0 < len(value) <= 128 for value in (self.record_id, self.owner_id))
                or not positive_integer(self.epoch) or not positive_integer(self.expires_at)
                or type(self.revision) is not int or not 0 <= self.revision < 2**63):
            raise Refusal("unavailable")


@dataclass(frozen=True)
class RunnerOperation:
    identity: RunnerIdentity
    guard: RunnerGuard
    deadline_ms: int


def completed_result(terminal, identity):
    from linux_android_artifact_importer import ClosedLinuxResult, VerifiedLinuxInputs

    if (type(terminal) is not dict
            or set(terminal) != {"inputs", "readback_sha256", "exit_code", *COMPLETION_FACTS}
            or not sha256(terminal["readback_sha256"])
            or type(terminal["exit_code"]) is not int or terminal["exit_code"] != 0
            or any(terminal[field] is not True for field in COMPLETION_FACTS)):
        raise ValueError("invalid completion")
    raw_inputs = terminal["inputs"]
    if type(raw_inputs) is not dict:
        raise ValueError("invalid completion inputs")
    inputs = VerifiedLinuxInputs(**raw_inputs)
    if not all(sha256(value) for value in raw_inputs.values()):
        raise ValueError("invalid completion inputs")
    return ClosedLinuxResult(**dict(terminal, inputs=inputs, identity=asdict(identity)))


class LinuxAndroidRunnerClient:
    def __init__(self, socket_path, *, recipe_sha256, store_id):
        self.socket_path = Path(socket_path)
        if not self.socket_path.is_absolute() or not sha256(recipe_sha256) or not sha256(store_id):
            raise Refusal("unavailable")
        self.recipe_sha256 = recipe_sha256
        self.store_id = store_id

    def operation(self, request):
        if set(request) != {"operation_id", "ref", "spec", "guard", "deadline_ms"}:
            raise Refusal("unavailable")
        spec = request["spec"]
        operation_id = request["operation_id"]
        deadline = request["deadline_ms"]
        if (spec["platform"] != "android" or spec["build_definition_sha256"] != self.recipe_sha256
                or not sha256(operation_id) or not positive_integer(deadline)):
            raise Refusal("unavailable")
        try:
            guard = RunnerGuard(**request["guard"])
        except TypeError as error:
            raise Refusal("unavailable") from error
        binding = {key: request[key] for key in ("ref", "spec", "deadline_ms")}
        identity = RunnerIdentity(operation_id, digest(literal(binding).encode()), self.recipe_sha256, self.store_id)
        return RunnerOperation(identity, guard, deadline)

    def observe(self, action, operation):
        if action not in ("ensure_started", "query", "stop"):
            raise Refusal("unavailable")
        now = time.time_ns() // 1_000_000
        if operation.guard.expires_at <= now or (action == "ensure_started" and operation.deadline_ms <= now):
            raise Refusal("stale")
        request = {"version": VERSION, "action": action, **asdict(operation)}
        try:
            reply = self._exchange(request)
            if literal(reply["request"]) != literal(request):
                raise ValueError("mismatched observation")
            status = reply["status"]
            if (status == "completed" and action in ("ensure_started", "query")
                    and set(reply) == {"request", "status", "terminal"}):
                return completed_result(reply["terminal"], operation.identity)
            if status == "stopped" and set(reply) == {"request", "status", "terminal"}:
                if literal(reply["terminal"]) == literal(TERMINAL):
                    return reply
            if set(reply) == {"request", "status"} and status in ("absent", "running", "stopping"):
                return reply
        except (OSError, ValueError, KeyError, TypeError, RecursionError, struct.error) as error:
            raise Refusal("uncertain") from error
        raise Refusal("uncertain")

    def _exchange(self, request):
        path = self.socket_path
        directory, endpoint = path.parent.lstat(), path.lstat()
        if (path.resolve() != path or directory.st_uid != os.getuid() or endpoint.st_uid != os.getuid()
                or directory.st_mode != stat.S_IFDIR | 0o700 or endpoint.st_mode != stat.S_IFSOCK | 0o600):
            raise ValueError("runner socket must be private")
        packet = (literal(request) + "\n").encode()
        if len(packet) > FRAME_LIMIT:
            raise ValueError("oversized runner request")
        deadline = time.monotonic() + TIMEOUT_SECONDS
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(TIMEOUT_SECONDS)
            connection.connect(str(path))
            if peer_uid(connection) != os.getuid():
                raise ValueError("unexpected runner peer owner")
            connection.settimeout(max(0, deadline - time.monotonic()))
            connection.sendall(packet)
            data = bytearray()
            while len(data) <= FRAME_LIMIT:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                connection.settimeout(remaining)
                chunk = connection.recv(FRAME_LIMIT + 1 - len(data))
                if not chunk:
                    if data.count(b"\n") == 1 and data.endswith(b"\n"):
                        return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
                    break
                data.extend(chunk)
        raise ValueError("invalid runner frame")
