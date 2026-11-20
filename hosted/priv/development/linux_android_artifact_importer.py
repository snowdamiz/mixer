"""Private artifact import for an operator-owned, closed Linux Android bundle.

The caller supplies its registered input pins and exact runner identity. It must
independently authenticate the successful terminal result, including the
readback digest. A bundle and the runner's v1 stopped reply cannot supply that
authority. The worker owns the operation directory and serializes publication
with its surrounding operation state transitions.
"""
from dataclasses import asdict, dataclass
import errno
import json
import os
from pathlib import Path
import stat
import tempfile

from compiler_worker import Refusal, digest, literal
from native_artifact_worker import (
    ANDROID_ARTIFACTS, KINDS, check_artifact, command_log, open_android_store, read_owned,
)


STORE = "native"
MANIFEST = "linux-artifacts-v1.json"
SCOPE = "unsigned-android/managed-linux"
METADATA_LIMIT = 1024 * 1024
IDENTITY_FIELDS = {"operation_id", "binding_sha256", "recipe_sha256", "store_id"}
CAPS = dict(zip(KINDS, (limit for _, _, limit in ANDROID_ARTIFACTS), strict=True))


@dataclass(frozen=True)
class VerifiedLinuxInputs:
    source_tree_sha256: str
    linux_lock_sha256: str
    rendered_driver_sha256: str


@dataclass(frozen=True)
class ClosedLinuxResult:
    identity: dict[str, str]  # asdict(RunnerIdentity)
    inputs: VerifiedLinuxInputs
    readback_sha256: str
    exit_code: int
    start_fenced: bool
    container_absent: bool
    processes_absent: bool
    resources_removed: bool


def is_digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def unique_object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate key")
    return result


def decode(data):
    value = json.loads(data, object_pairs_hook=unique_object)
    if type(value) is not dict:
        raise Refusal("uncertain")
    return value


def operation_store(operation_directory, identity):
    if type(identity) is not dict or set(identity) != IDENTITY_FIELDS or not all(
        is_digest(value) for value in identity.values()
    ):
        raise Refusal("unavailable")
    directory = Path(operation_directory)
    if directory.name != identity["operation_id"] or directory.resolve(strict=True) != directory:
        raise Refusal("unavailable")
    for path in (directory.parent, directory):
        info = path.lstat()
        if info.st_mode != stat.S_IFDIR | 0o700 or info.st_uid != os.getuid():
            raise Refusal("unavailable")
    return directory / STORE


def verify_authority(identity, inputs, terminal):
    if (type(inputs) is not VerifiedLinuxInputs or not all(is_digest(value) for value in asdict(inputs).values())
            or type(terminal) is not ClosedLinuxResult or terminal.identity != identity
            or terminal.inputs != inputs or not is_digest(terminal.readback_sha256)
            or type(terminal.exit_code) is not int or terminal.exit_code != 0
            or not all(fact is True for fact in (terminal.start_fenced, terminal.container_absent,
                                                 terminal.processes_absent, terminal.resources_removed))):
        raise Refusal("unavailable")


def verify_rows(rows):
    if type(rows) is not list or len(rows) != len(KINDS):
        raise Refusal("uncertain")
    for kind, row in zip(KINDS, rows, strict=True):
        if (type(row) is not dict or set(row) != {"kind", "sha256", "sizeBytes"}
                or row["kind"] != kind or not is_digest(row["sha256"])
                or type(row["sizeBytes"]) is not int or not 0 < row["sizeBytes"] <= CAPS[kind]):
            raise Refusal("uncertain")
    if len({row["sha256"] for row in rows}) != len(KINDS):
        raise Refusal("uncertain")


def read_bundle_index(fd, inputs, readback_sha):
    payload = read_owned("readback.json", METADATA_LIMIT, allow_owner_write=True, dir_fd=fd)
    if digest(payload) != readback_sha:
        raise Refusal("uncertain")
    index = decode(payload)
    build, entries = index["build"], index["artifacts"]
    if (index["unsigned"] is not True or index["zipCRCVerified"] is not True
            or type(build) is not dict or build["source_tree_sha256"] != inputs.source_tree_sha256
            or build["source_tree_after_sha256"] != inputs.source_tree_sha256
            or type(entries) is not list or len(entries) != len(KINDS)
            or digest(read_owned("linux-mixer.lock", METADATA_LIMIT, allow_owner_write=True, dir_fd=fd))
            != inputs.linux_lock_sha256):
        raise Refusal("uncertain")
    files, rows = [], []
    for entry in entries:
        if type(entry) is not dict:
            raise Refusal("uncertain")
        row = entry.copy()
        name = row.pop("file")
        if type(name) is not str or Path(name).name != name or "\\" in name or "\x00" in name:
            raise Refusal("uncertain")
        files.append(name)
        rows.append(row)
    verify_rows(rows)
    apk, symbols, inventory = files
    if not apk.endswith("-unsigned.apk") or symbols != "debug-symbols.zip" or inventory != "resource-inventory.json":
        raise Refusal("uncertain")
    log = None
    if "androidDriverLog" in index:
        receipt = index["androidDriverLog"]
        if (type(receipt) is not dict or set(receipt) != {"exitCode", "stdoutBytes", "stderrBytes", "outputTruncated"}
                or receipt["exitCode"] != 0):
            raise Refusal("uncertain")
        log = {"cliExitCode": 0, "androidDriver": command_log(receipt)}
    return files, rows, log


def write_owned(path, data):
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fchmod(handle.fileno(), 0o400)
        os.fsync(handle.fileno())


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def store_manifest(info, admission):
    return {**admission, "scope": SCOPE, "storeDevice": info.st_dev, "storeInode": info.st_ino}


def _reopen(store, identity, *, manifest_sha=None, admission=None):
    with open_android_store(store) as (fd, info):
        payload = read_owned(MANIFEST, METADATA_LIMIT, dir_fd=fd)
        actual_sha = digest(payload)
        if manifest_sha is not None and actual_sha != manifest_sha:
            raise Refusal("uncertain")
        report = decode(payload)
        if (report["scope"] != SCOPE or report["identity"] != identity
                or report["storeDevice"] != info.st_dev or report["storeInode"] != info.st_ino
                or (admission is not None and payload != literal(store_manifest(info, admission)).encode())):
            raise Refusal("uncertain")
        rows = report["artifacts"]
        verify_rows(rows)
        artifacts = [
            check_artifact(store, dict(row, ownedPath=str(store / row["sha256"])),
                           row["kind"], CAPS[row["kind"]], dir_fd=fd)
            for row in rows
        ]
        result = {"manifest_sha256": actual_sha, "artifacts": artifacts}
        if "customerLog" in report:
            result["customer_log"] = report["customerLog"]
        return result


def import_closed_bundle(bundle, operation_directory, *, expected_identity, verified_inputs, terminal):
    """Import from a locally provisioned directory and return a durable manifest pin."""
    try:
        store = operation_store(operation_directory, expected_identity)
        verify_authority(expected_identity, verified_inputs, terminal)
        bundle = Path(bundle)
        if bundle.is_relative_to(store.parent) or store.is_relative_to(bundle):
            raise Refusal("unavailable")
        with tempfile.TemporaryDirectory(prefix=".linux-native-", dir=store.parent) as staging:
            pending = Path(staging) / STORE
            pending.mkdir(mode=0o700)
            with open_android_store(bundle) as (fd, _):
                files, rows, log = read_bundle_index(fd, verified_inputs, terminal.readback_sha256)
                for name, row in zip(files, rows, strict=True):
                    data = read_owned(name, row["sizeBytes"], allow_owner_write=True, dir_fd=fd)
                    if len(data) != row["sizeBytes"] or digest(data) != row["sha256"]:
                        raise Refusal("uncertain")
                    if row["kind"] == "resource_inventory":
                        inventory = decode(data)
                        if (type(inventory["formatVersion"]) is not int or inventory["formatVersion"] != 1
                                or inventory["apkSHA256"] != rows[0]["sha256"]
                                or inventory["debugSymbolsSHA256"] != rows[1]["sha256"]):
                            raise Refusal("uncertain")
                    write_owned(pending / row["sha256"], data)
            admission = {"identity": expected_identity, "inputs": asdict(verified_inputs),
                         "readbackSha256": terminal.readback_sha256, "artifacts": rows}
            if log is not None:
                admission["customerLog"] = log
            write_owned(pending / MANIFEST, literal(store_manifest(pending.stat(), admission)).encode())
            _reopen(pending, expected_identity, admission=admission)
            sync_directory(pending)
            if not os.path.lexists(store):
                try:
                    pending.rename(store)
                except OSError as error:
                    if error.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                        raise
            result = _reopen(store, expected_identity, admission=admission)
            sync_directory(store.parent)
            return result
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        raise Refusal("uncertain") from error


def reopen_linux_artifacts(operation_directory, *, expected_identity, manifest_sha256):
    """Recheck the worker-retained bytes under the stored operation and manifest pin."""
    if not is_digest(manifest_sha256):
        raise Refusal("unavailable")
    try:
        store = operation_store(operation_directory, expected_identity)
        return _reopen(store, expected_identity, manifest_sha=manifest_sha256)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        raise Refusal("uncertain") from error
