"""Opt-in local worker for one operator-registered unsigned iOS Simulator project."""
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from enum import Enum
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import socketserver
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from urllib.parse import unquote, urlsplit
from xml.parsers.expat import ExpatError

from compiler_worker import Refusal, Worker, digest, literal
import starter_package_closure as starter

KINDS = ("unsigned_native_binary", "debug_symbols", "resource_inventory")
LIMIT = 256 * 1024 * 1024
ANDROID_PROFILE = "unsigned-android-local-v1"
ANDROID_PACKAGE_POLICY = "exact-locked-android-file-mirrors-v1"
ANDROID_MIRROR_ENV = {
    "swift-asn1": "MIXER_WORKER_ANDROID_SWIFT_ASN1_MIRROR",
    "swift-crypto": "MIXER_WORKER_ANDROID_SWIFT_CRYPTO_MIRROR",
}
ANDROID_DRIVER = "Generated/MixerAndroid/android-build.py"
ANDROID_MANIFEST = "android-build-v1.json"
ANDROID_HOST_SWIFT = "/usr/bin/swift"
XCODE_INFO = "Contents/Info.plist"
XCODE_VERSION = "Contents/version.plist"
XCODEBUILD = "Contents/Developer/usr/bin/xcodebuild"
XCODE_SWIFT = "Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
XCODE_PLIST_LIMIT = 1024 * 1024
XCODE_EXECUTABLE_LIMIT = 256 * 1024 * 1024
ANDROID_ARTIFACTS = (
    ("unsignedAPK", "unsigned_apk", 32 * 1024 * 1024),
    ("debugSymbols", "debug_symbols", 16 * 1024 * 1024),
    ("resourceInventory", "resource_inventory", 16 * 1024 * 1024),
)


class BuildUncertainty(Enum):
    CLI_PROCESS_HANDLE_UNAVAILABLE = "cli_process_handle_unavailable"
    CLI_LAUNCH_RECORD_FAILED = "cli_launch_record_failed"
    CLI_WAIT_TIMEOUT = "cli_wait_timeout"
    CLI_ACK_MISSING = "cli_ack_missing"
    CLI_ACK_INVALID = "cli_ack_invalid"
    CLI_GROUP_UNCONFIRMED = "cli_group_unconfirmed"
    NESTED_RECEIPT_INVALID = "nested_receipt_invalid"
    CLI_RESULT_UNPROVEN = "cli_result_unproven"
    FUTURE_EXCEPTION = "future_exception"


class AndroidDriverOutcome(Enum):
    NOT_STARTED = "not_started"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUCCEEDED = "succeeded"


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


def file_stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_nlink,
            info.st_size, info.st_ctime_ns, info.st_mtime_ns)


def read_owned(path, limit, *, allow_owner_write=False, dir_fd=None):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=dir_fd)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or before.st_mode & (0o022 if allow_owner_write else 0o222)
                or not 0 < before.st_size <= limit):
            raise Refusal("uncertain")
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        named = os.stat(path, dir_fd=dir_fd, follow_symlinks=False)
        if (len(data) != before.st_size or file_stamp(before) != file_stamp(after)
                or file_stamp(after) != file_stamp(named)):
            raise Refusal("uncertain")
        return data


def check_artifact(store, descriptor, kind, limit=LIMIT, *, dir_fd=None):
    sha = descriptor["sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise Refusal("uncertain")
    path = store / sha
    if descriptor["kind"] != kind or descriptor["ownedPath"] != str(path):
        raise Refusal("uncertain")
    expected_size = descriptor["sizeBytes"]
    if type(expected_size) is not int or not 0 < expected_size <= limit:
        raise Refusal("uncertain")
    data = read_owned(path if dir_fd is None else sha, limit, dir_fd=dir_fd)
    if len(data) != expected_size or digest(data) != sha:
        raise Refusal("uncertain")
    return {"kind": kind, "sha256": sha, "sizeBytes": len(data)}


@contextmanager
def open_android_store(store):
    if store.resolve(strict=True) != store:
        raise Refusal("uncertain")
    fd = os.open(store, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if info.st_mode != stat.S_IFDIR | 0o700 or info.st_uid != os.getuid():
            raise Refusal("uncertain")
        yield fd, info
        if (store.resolve(strict=True) != store or file_stamp(info) != file_stamp(os.fstat(fd))
                or file_stamp(info) != file_stamp(store.lstat())):
            raise Refusal("uncertain")
    finally:
        os.close(fd)


def android_store_report(fd, info):
    manifest = read_owned(ANDROID_MANIFEST, 8 * 1024 * 1024, dir_fd=fd)
    report = json.loads(manifest)
    if (type(report["formatVersion"]) is not int or report["formatVersion"] != 1
            or report["scope"] != "unsigned-android/local-development"
            or type(report["storeDevice"]) is not int or report["storeDevice"] != info.st_dev
            or type(report["storeInode"]) is not int or report["storeInode"] != info.st_ino):
        raise Refusal("uncertain")
    return report, digest(manifest)


def android_store_artifacts(store, fd, report):
    artifacts = []
    for (field, local_kind, limit), public_kind in zip(ANDROID_ARTIFACTS, KINDS, strict=True):
        descriptor = check_artifact(store, report[field], local_kind, limit, dir_fd=fd)
        artifacts.append(dict(descriptor, kind=public_kind))
    if len({artifact["sha256"] for artifact in artifacts}) != len(ANDROID_ARTIFACTS):
        raise Refusal("uncertain")
    return artifacts


def android_export_fingerprint(files):
    # The worker registration hashes file rows. The retained CLI report also
    # binds directories created when those exact rows are materialized.
    directories = {str(parent) for relative in files for parent in PurePosixPath(relative).parents
                   if parent.parts}
    fingerprint = hashlib.sha256()
    for relative in sorted(directories | files.keys(), key=lambda path: path.encode("utf-8")):
        fingerprint.update(relative.encode("utf-8"))
        if relative in directories:
            fingerprint.update(b"\x00\x01")
        else:
            fingerprint.update(b"\x00\x00" + bytes.fromhex(files[relative]))
    return fingerprint.hexdigest()


def android_mirror_fingerprint(root):
    entries = {}
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            path = Path(parent) / name
            info = path.lstat()
            if info.st_mode & 0o022:
                raise Refusal("unavailable")
            if stat.S_ISREG(info.st_mode):
                with path.open("rb") as handle:
                    entries[path.relative_to(root).as_posix()] = hashlib.file_digest(handle, "sha256").hexdigest()
            elif not stat.S_ISDIR(info.st_mode):
                raise Refusal("unavailable")
    return digest("".join(path + "\0" + sha + "\n" for path, sha in sorted(entries.items())).encode())


def android_mirror_environment(recipe):
    mirrors = recipe["android_mirrors"]
    if set(mirrors) != set(ANDROID_MIRROR_ENV):
        raise Refusal("unavailable")
    environment = {}
    for package, variable in ANDROID_MIRROR_ENV.items():
        mirror = mirrors[package]
        url = mirror["url"]
        root = Path(unquote(urlsplit(url).path))
        if (not root.is_absolute() or root.resolve() != root
                or root.name != package + ".git" or root.as_uri() != url
                or not root.is_dir() or root.stat().st_mode & 0o022
                or android_mirror_fingerprint(root) != mirror["tree_sha256"]):
            raise Refusal("unavailable")
        environment[variable] = url
    return environment


def retained_android_report(store, project, spec, files, cli, cli_sha, command):
    source = {
        "treeSHA256": android_export_fingerprint(files),
        "lock": {
            "sha256": spec["toolchain_lock_sha256"],
            "sizeBytes": (project / "mixer.lock").stat().st_size,
        },
    }
    for name, relative in (
        ("sdkPins", "Generated/MixerSDK/Package.resolved"),
        ("platformPins", "Platforms/Android/Package.resolved"),
        ("generatedDriver", ANDROID_DRIVER),
    ):
        source[name] = {"sha256": files[relative], "sizeBytes": (project / relative).stat().st_size}
    with open_android_store(store) as (fd, info):
        report, manifest_sha = android_store_report(fd, info)
        binding = report["binding"]
        if (binding["command"] != command
                or binding["cliExecutable"] != {"sha256": cli_sha, "sizeBytes": cli.stat().st_size}
                or binding["sourceBefore"] != source or binding["sourceAfter"] != source):
            raise Refusal("uncertain")
        return {"artifacts": android_store_artifacts(store, fd, report), "manifest_sha256": manifest_sha}


def check_retained_android_artifacts(store, value):
    try:
        with open_android_store(store) as (fd, info):
            report, manifest_sha = android_store_report(fd, info)
            if manifest_sha != value["manifest_sha256"]:
                raise Refusal("uncertain")
            artifacts = android_store_artifacts(store, fd, report)
            # Compare the complete ordered public rows saved at initial admission.
            if literal(artifacts) != literal(value["artifacts"]):
                raise Refusal("uncertain")
            return artifacts
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        raise Refusal("uncertain") from error


def command_log(receipt):
    fields = ("exitCode", "stdoutBytes", "stderrBytes")
    values = {key: receipt.get(key) for key in fields}
    truncated = receipt.get("outputTruncated")
    if (any(type(value) is not int for value in values.values())
            or not -255 <= values["exitCode"] <= 255
            or not all(0 <= values[key] <= 2**32 for key in fields[1:])
            or type(truncated) is not bool):
        raise ValueError("Invalid command log fields")
    return dict(values, tailTruncated=truncated, phases=[])


def publish_customer_log(state, operation, spec, log, *, idempotent=False):
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
        destination = state / ("customer-log-v1-" + operation)
        try:
            os.link(name, destination, follow_symlinks=False)
        except FileExistsError:
            if (not idempotent or destination.lstat().st_mode != stat.S_IFREG | 0o400
                    or read_owned(destination, 2_048) != payload):
                raise
    finally:
        os.unlink(name)


def check_xcode_pin(path, expected, *, executable=False):
    # Xcode ships the Swift driver name as a link to swift-frontend. Admit that
    # exact sibling alias while retaining /usr/bin/swift as the launch name.
    named = path
    named_info = named.lstat()
    if path.name == "swift" and stat.S_ISLNK(named_info.st_mode):
        if os.readlink(path) != "swift-frontend":
            raise Refusal("unavailable")
        path = path.with_name("swift-frontend")
    if path.resolve(strict=True) != path or (executable and not os.access(path, os.X_OK)):
        raise Refusal("unavailable")
    limit = XCODE_EXECUTABLE_LIMIT if executable else XCODE_PLIST_LIMIT
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if (not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit
                or (executable and not before.st_mode & 0o111)):
            raise Refusal("unavailable")
        if executable:
            checksum = hashlib.sha256()
            for remaining in range(before.st_size, 0, -XCODE_PLIST_LIMIT):
                count = min(remaining, XCODE_PLIST_LIMIT)
                chunk = handle.read(count)
                if len(chunk) != count:
                    raise Refusal("unavailable")
                checksum.update(chunk)
            data, actual = None, checksum.hexdigest()
        else:
            data = handle.read(limit + 1)
            actual = digest(data)
        if (actual != expected or named.resolve(strict=True) != path
                or file_stamp(named_info) != file_stamp(named.lstat())
                or file_stamp(before) != file_stamp(os.fstat(handle.fileno()))
                or file_stamp(before) != file_stamp(path.lstat())):
            raise Refusal("unavailable")
        return data


def admit_android_xcodes(recipe):
    pins = recipe.get("android_xcode_pins")
    if type(pins) is not dict or set(pins) != {"host", "android"}:
        raise Refusal("unavailable")
    selections = (("host", recipe["environment"].get("DEVELOPER_DIR")),
                  ("android", recipe.get("android_developer_dir")))
    try:
        for role, selection in selections:
            if type(selection) is not str:
                raise Refusal("unavailable")
            developer = Path(selection)
            if (not developer.is_absolute() or str(developer.resolve(strict=True)) != selection
                    or developer.name != "Developer" or developer.parent.name != "Contents"
                    or developer.parent.parent.suffix != ".app" or not developer.is_dir()):
                raise Refusal("unavailable")
            app = developer.parent.parent
            files = {XCODE_INFO, XCODE_VERSION, XCODEBUILD}
            if role == "host":
                files.add(XCODE_SWIFT)
            rows = pins[role]
            if type(rows) is not dict or set(rows) != files:
                raise Refusal("unavailable")
            info = plistlib.loads(check_xcode_pin(app / XCODE_INFO, rows[XCODE_INFO]))
            version = plistlib.loads(check_xcode_pin(app / XCODE_VERSION, rows[XCODE_VERSION]))
            if (type(info) is not dict or info.get("CFBundleIdentifier") != "com.apple.dt.Xcode"
                    or type(version) is not dict or not isinstance(version.get("ProductBuildVersion"), str)
                    or not version["ProductBuildVersion"]):
                raise Refusal("unavailable")
            check_xcode_pin(app / XCODEBUILD, rows[XCODEBUILD], executable=True)
            if role == "host":
                check_xcode_pin(app / XCODE_SWIFT, rows[XCODE_SWIFT], executable=True)
    except (OSError, ValueError, TypeError, RuntimeError, plistlib.InvalidFileException, ExpatError) as error:
        raise Refusal("unavailable") from error


def admit_android_tools(recipe, files) -> tuple[str, str]:
    swift = recipe.get("android_host_swift")
    python = recipe.get("android_python")
    driver_sha = recipe["inputs"].get(ANDROID_DRIVER)
    if swift != ANDROID_HOST_SWIFT or swift == python or not driver_sha or files.get(ANDROID_DRIVER) != driver_sha:
        raise Refusal("unavailable")
    for tool in (swift, python):
        if type(tool) is not str or not tool.startswith("/"):
            raise Refusal("unavailable")
        executable = Path(tool)
        expected_sha = recipe["tools"].get(tool)
        try:
            if (not expected_sha or str(executable.resolve(strict=True)) != tool
                    or not executable.is_file() or not os.access(executable, os.X_OK)
                    or digest(executable.read_bytes()) != expected_sha):
                raise Refusal("unavailable")
        except (OSError, ValueError, RuntimeError) as error:
            raise Refusal("unavailable") from error
    admit_android_xcodes(recipe)
    return swift, python


def interpret_android_driver(
    commands: list[dict], swift: str, python: str, project: Path, receipt_root: Path, cli_exit: int, cancelled: bool,
) -> AndroidDriverOutcome | BuildUncertainty:
    unproven = BuildUncertainty.CLI_RESULT_UNPROVEN
    if cli_exit < 0 or len(commands) > 2:
        return unproven
    if not commands:
        return AndroidDriverOutcome.NOT_STARTED if cli_exit > 0 else unproven

    probe = commands[0]
    if (probe["command"] != [swift, "--version"] or probe.get("directory") is not None
            or probe.get("retainedInputDirectories") != []):
        return unproven
    probe_outcome = android_command_outcome(probe, cli_exit, cancelled)
    if isinstance(probe_outcome, BuildUncertainty):
        return probe_outcome
    if len(commands) == 1:
        return AndroidDriverOutcome.NOT_STARTED if cli_exit > 0 else unproven

    receipt = commands[1]
    if probe_outcome is not AndroidDriverOutcome.SUCCEEDED or probe["terminalNS"] >= receipt["runtimeStartedNS"]:
        return unproven
    argv = receipt["command"]
    staging = Path(argv[-1])
    snapshot = staging.parent
    prefix = "mixer-verify-"
    try:
        if not snapshot.name.startswith(prefix):
            return unproven
        snapshot_id = str(uuid.UUID(snapshot.name[len(prefix):])).upper()
    except ValueError:
        return unproven
    expected_snapshot = receipt_root / (prefix + snapshot_id)
    if (argv != [python, "-I", "-B", "-S", str(project / ANDROID_DRIVER),
                 "build-retained-v1", str(project), str(expected_snapshot / "android-build")]
            or receipt.get("directory") != str(project)
            or receipt.get("retainedInputDirectories") != [str(expected_snapshot), str(project)]):
        return unproven
    return android_command_outcome(receipt, cli_exit, cancelled)


def android_command_outcome(
    receipt: dict, cli_exit: int, cancelled: bool,
) -> AndroidDriverOutcome | BuildUncertainty:
    unproven = BuildUncertainty.CLI_RESULT_UNPROVEN
    exit_code = receipt.get("exitCode")
    reason = receipt.get("stopReason")
    terminated = receipt.get("groupTerminateSent", False)
    killed = receipt.get("groupKillSent")
    if (receipt.get("schema") != "mixer.owned-command.2" or receipt.get("released") is not True
            or receipt.get("uncertainty") is not None
            or type(exit_code) is not int or not 0 <= exit_code <= 255
            or type(terminated) is not bool or type(killed) is not bool):
        return BuildUncertainty.NESTED_RECEIPT_INVALID
    if reason == "cancelled":
        return AndroidDriverOutcome.CANCELLED if cancelled and cli_exit > 0 and not killed else unproven
    if terminated:
        return unproven
    if reason in ("runtime-deadline", "generated-output-limit", "aggregate-output-limit"):
        return AndroidDriverOutcome.FAILED if cli_exit > 0 else unproven
    if reason is not None or killed:
        return unproven
    if exit_code == 0:
        return AndroidDriverOutcome.SUCCEEDED
    return AndroidDriverOutcome.FAILED if cli_exit > 0 else unproven


def prepare_build(recipe, files, output, android_tools):
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
    if android_tools is not None:
        swift, python = android_tools
        launch_environment.update(
            android_mirror_environment(recipe), HOME=str(home),
            MIXER_WORKER_NATIVE_PROFILE=ANDROID_PROFILE,
            MIXER_WORKER_ANDROID_HOST_SWIFT=swift, MIXER_WORKER_ANDROID_PYTHON=python,
            MIXER_WORKER_ANDROID_DEVELOPER_DIR=recipe["android_developer_dir"],
        )
    return project, store, tmp, environment, argv, launch_environment


def read_cli_ack(tmp):
    # The pinned CLI acknowledges only after its synchronous command scope
    # unwinds without a hold. Never inspect command scratch without that proof.
    try:
        prefix = "mixer-command-receipts-"
        basename = read_owned(tmp / "cli-closed", len(prefix) + 36, allow_owner_write=True).decode("ascii")
        if not basename.startswith(prefix) or str(uuid.UUID(basename[len(prefix):])).upper() != basename[len(prefix):]:
            return BuildUncertainty.CLI_ACK_INVALID
    except FileNotFoundError:
        return BuildUncertainty.CLI_ACK_MISSING
    except (OSError, ValueError, Refusal):
        return BuildUncertainty.CLI_ACK_INVALID
    return basename


def read_nested_receipts(tmp, basename, *, strict):
    try:
        receipt_root = tmp / basename
        try:
            root_info = receipt_root.lstat()
        except FileNotFoundError:
            directories = []
        else:
            if root_info.st_mode != stat.S_IFDIR | 0o700 or root_info.st_uid != os.getuid():
                return BuildUncertainty.NESTED_RECEIPT_INVALID
            directories = sorted(receipt_root.iterdir())
        receipts = []
        for command in directories:
            if not command.name.startswith("command-"):
                continue
            if not stat.S_ISDIR(command.lstat().st_mode):
                return BuildUncertainty.NESTED_RECEIPT_INVALID
            try:
                (command / "HOLD.json").lstat()
            except FileNotFoundError:
                pass
            else:
                return BuildUncertainty.NESTED_RECEIPT_INVALID
            receipt = command / "receipt.json"
            if not stat.S_ISREG(receipt.lstat().st_mode):
                return BuildUncertainty.NESTED_RECEIPT_INVALID
            data = (receipt.read_bytes() if not strict
                    else read_owned(receipt, 1024 * 1024, allow_owner_write=True))
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
                return BuildUncertainty.NESTED_RECEIPT_INVALID
            if strict:
                start, terminal = item.get("runtimeStartedNS"), item.get("terminalNS")
                if type(start) is not int or type(terminal) is not int or not 0 < start <= terminal < 2**64:
                    return BuildUncertainty.NESTED_RECEIPT_INVALID
            receipts.append((item, digest(data)))
    except (OSError, ValueError, KeyError, TypeError, Refusal):
        return BuildUncertainty.NESTED_RECEIPT_INVALID
    if strict:
        # Command directory names are random. The CLI serializes commands on one monotonic clock.
        receipts.sort(key=lambda entry: entry[0]["runtimeStartedNS"])
    return receipt_root, receipts


def build(recipe, files, output, request, launch):
    android = recipe.get("profile") == ANDROID_PROFILE
    with ExitStack() as logs:
        try:
            android_tools = admit_android_tools(recipe, files) if android else None
            project, store, tmp, environment, argv, launch_environment = prepare_build(
                recipe, files, output, android_tools)
            stdout = logs.enter_context((output / "stdout").open("xb"))
            stderr = logs.enter_context((output / "stderr").open("xb"))
        except (OSError, Refusal):
            if not android:
                raise
            # This block cannot reach the process constructor. Every failure
            # from the constructor onward retains the existing custody rules.
            return {"closed": True, "started": False, "preflight_failed": True,
                    "android_driver_outcome": AndroidDriverOutcome.NOT_STARTED.value}
        with launch.lock:
            now = now_ms()
            remaining = min(recipe["timeout_seconds"], (request["deadline_ms"] - now) / 1000)
            if launch.cancelled or remaining <= 0 or request["guard"]["expires_at"] <= now:
                result = {"closed": True, "started": False}
                if android_tools is not None:
                    result["android_driver_outcome"] = AndroidDriverOutcome.NOT_STARTED.value
                return result
            try:
                proc = OwnedBuildProcess(argv, cwd=project, env=launch_environment,
                                         stdin=subprocess.DEVNULL,
                                         stdout=stdout, stderr=stderr, start_new_session=True)
            except OSError:
                # A constructor error can leave child custody unknown.
                return BuildUncertainty.CLI_PROCESS_HANDLE_UNAVAILABLE
            launch.control_directory = tmp
        launch_record = literal({"pid": proc.pid, "argv": argv})
        try:
            (output / "launch.json").write_text(launch_record)
        except OSError:
            return BuildUncertainty.CLI_LAUNCH_RECORD_FAILED
        try:
            code = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            return BuildUncertainty.CLI_WAIT_TIMEOUT
    basename = read_cli_ack(tmp)
    if isinstance(basename, BuildUncertainty):
        return basename
    if not group_absent(proc.pid):
        return BuildUncertainty.CLI_GROUP_UNCONFIRMED
    nested = read_nested_receipts(tmp, basename, strict=android_tools is not None)
    if isinstance(nested, BuildUncertainty):
        return nested
    return collect_build_result(output, recipe, files, request["spec"], proc.pid, code, nested,
                                android_tools=android_tools, cancelled=launch.cancelled)


def collect_build_result(output, recipe, files, spec, pid, code, nested, *, android_tools=None,
                         cancelled=False, stop_before_artifacts=False):
    project, store, tmp, home = (output / p for p in ("project", "native", "tmp", "home"))
    environment = dict(recipe["environment"], TMPDIR=str(tmp), CFFIXED_USER_HOME=str(home))
    cli = recipe["argv"][0]
    receipt_root, receipts = nested
    commands = [item for item, _ in receipts]
    proof = [{"command": item["command"][0], "pid": item["pid"], "receipt_sha256": sha,
              "stop_reason": item.get("stopReason"), "group_terminate_sent": item.get("groupTerminateSent", False)}
             for item, sha in receipts]
    result = {"closed": True, "started": True, "pid": pid, "exit": code,
              "cli_reaped": True, "cli_group_absent": True, "commands": proof}
    if android_tools is not None:
        outcome = interpret_android_driver(commands, *android_tools, project, receipt_root, code, cancelled)
        if isinstance(outcome, BuildUncertainty):
            return outcome
        result["android_driver_outcome"] = outcome.value
        log_key = "androidDriver"
        log_receipt = None
        if len(commands) == 2:
            result["android_driver_exit"] = commands[1]["exitCode"]
            log_receipt = commands[1]
    else:
        compiler = [c for c in commands if c["command"][0] == "/usr/bin/xcodebuild"]
        if len(compiler) > 1 or (not compiler and code <= 0):
            return BuildUncertainty.CLI_RESULT_UNPROVEN
        if not compiler:
            result["preflight_failed"] = True
        log_key = "compiler"
        log_receipt = compiler[0] if compiler else None
    try:
        (output / "closure.json").write_text(literal(result))
    except OSError:
        pass
    try:
        result["customer_log"] = {"cliExitCode": code,
                                  log_key: command_log(log_receipt) if log_receipt is not None else None}
    except ValueError:
        pass  # Log projection cannot change the original build or closure outcome.
    if android_tools is not None:
        if outcome is AndroidDriverOutcome.SUCCEEDED and code == 0 and not cancelled:
            try:
                result.update(retained_android_report(
                    store, project, spec, files, Path(cli), recipe["tools"][cli],
                    commands[1]["command"],
                ))
            except (OSError, ValueError, KeyError, TypeError, Refusal):
                pass  # Preserve known closure if the retained products are unavailable.
        return result
    if not compiler or stop_before_artifacts:
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
                or binding["authoritativeSourceDigest"] != spec["source"]["sha256"]
                or binding["lockSHA256"] != spec["toolchain_lock_sha256"]
                or binding["cliExecutableSHA256"] != recipe["tools"][cli]
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
    def __init__(self, config, state, *, linux_runner=None):
        os.umask(0o077)
        Path(state).mkdir(mode=0o700, exist_ok=True)
        path = Path(state)
        info = path.lstat()
        if (not path.is_absolute() or path.resolve() != path or info.st_uid != os.getuid()
                or info.st_mode != stat.S_IFDIR | 0o700):
            raise Refusal("unavailable")
        if linux_runner is None and "linux_runner" in config:
            from linux_android_runner import LinuxAndroidRunnerClient

            linux_runner = LinuxAndroidRunnerClient(**config["linux_runner"])
        self.ios_custody = None
        if "ios_custodian" in config:
            from ios_build_custody import IOSCustody

            self.ios_custody = IOSCustody(config)
        super().__init__(config, state)
        self.linux_runner = linux_runner
        self.launch = None

    def initialize_ledger(self):
        from ios_build_custody import check_ledger_mode

        check_ledger_mode(self.db, self.ios_custody)
        super().initialize_ledger()
        if self.ios_custody is not None:
            self.ios_custody.initialize(self.db)
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
        if spec["platform"] == "android":
            recipe = self.verify_recipe(spec, "android", ANDROID_PACKAGE_POLICY)
            files = self.config["registration"]["files"]
            toolchain = json.loads((Path(recipe["cwd"]) / "mixer.lock").read_bytes())["android"]["toolchain"]
            swift, python = admit_android_tools(recipe, files)
            python_pin = toolchain["tools"]["python"]
            if (recipe.get("profile") != ANDROID_PROFILE or starter.KEY in recipe
                    or set(recipe["tools"]) != {recipe["argv"][0], swift, python}
                    or recipe["inputs"] != files
                    or python_pin != {"path": python, "sha256": recipe["tools"][python]}
                    or recipe["environment"].get("PATH") != "/usr/bin:/bin:/usr/sbin:/sbin"
                    or set(recipe["environment"]) - {"PATH", "DEVELOPER_DIR", "LANG", "LC_ALL"}
                    or type(recipe["timeout_seconds"]) is not int
                    or not 1 <= recipe["timeout_seconds"] <= 1800):
                raise Refusal("unavailable")
            android_mirror_environment(recipe)
            return recipe
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
            result = BuildUncertainty.FUTURE_EXCEPTION
        value["status"] = "uncertain"
        if isinstance(result, BuildUncertainty):
            value["uncertainty_reason"] = result.value
            result = {}
        elif result["closed"]:
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

    def capacity_occupied(self):
        occupied = self.db.execute(
            "SELECT 1 FROM operations WHERE json_extract(value,'$.status') IN ('running','uncertain')"
        ).fetchone()
        return self.future is not None or occupied is not None

    def request_linux(self, action, request, previous):
        from linux_android_artifact_importer import ClosedLinuxResult

        runner = self.linux_runner
        bound = runner.operation(request)
        identity = asdict(bound.identity)
        operation = bound.identity.operation_id
        recorded = previous.get("linux_runner") if previous is not None else None
        if recorded is not None and recorded != identity:
            raise Refusal("unavailable")

        reply = super().request("query", request)
        value = self.load(operation)
        if action == "artifacts":
            return self.linux_artifacts(bound, identity, value)
        if value["status"] == "stopped":
            return reply
        if action == "stop":
            value.update(tombstone=True, status="uncertain", linux_runner=identity)
            self.save(operation, value)
        if value["status"] == "native_ready":
            return {"status": "running"}
        if value["status"] == "absent":
            if action == "query":
                return reply
            if self.capacity_occupied():
                raise Refusal("unavailable")
            value.update(status="uncertain", starts=1, linux_runner=identity)
            self.save(operation, value)

        # Once fenced, a request to ensure can only observe the same operation.
        if action == "ensure_started" and value.get("tombstone"):
            action = "query"
        observed = runner.observe(action, bound)
        now = now_ms()
        if bound.guard.expires_at <= now or (action == "ensure_started" and bound.deadline_ms <= now):
            raise Refusal("stale")
        if isinstance(observed, ClosedLinuxResult):
            if value.get("tombstone"):
                raise Refusal("uncertain")
            return self.settle_linux_completion(bound, identity, value, observed)
        if value.get("tombstone") and observed["status"] == "stopped":
            return self.settle_linux_stop(operation, value, observed, bound.guard.expires_at)
        if not value.get("tombstone"):
            if observed["status"] == "running":
                return {"status": "running"}
            if action == "query" and observed["status"] == "absent":
                # The caller may replay ensure for this ID. The reservation
                # survives because a delayed ensure could still reach the runner.
                return {"status": "absent"}
        raise Refusal("uncertain")

    def settle_linux_completion(self, bound, identity, value, terminal):
        from linux_android_artifact_importer import (
            VerifiedLinuxInputs, import_closed_bundle, sync_directory, verify_authority,
        )

        operation = bound.identity.operation_id
        # Only the digest-pinned operator configuration selects a bundle.
        # Neither the public request nor the runner reply supplies its location.
        try:
            grant = self.config["linux_artifact_imports"][operation]
            if set(grant) != {"identity", "bundle", "inputs"} or grant["identity"] != identity:
                raise Refusal("unavailable")
            inputs = VerifiedLinuxInputs(**grant["inputs"])
            bundle = Path(grant["bundle"])
            if not bundle.is_absolute():
                raise Refusal("unavailable")
        except (KeyError, TypeError, ValueError) as error:
            raise Refusal("unavailable") from error
        verify_authority(identity, inputs, terminal)
        self.require_linux_artifact_window(bound)
        directory = self.state / operation
        try:
            # The TCP listener and the state writer lock serialize this import
            # with guard updates and stop. Sync the new directory entry before
            # committing a reference to a store underneath it.
            directory.mkdir(mode=0o700, exist_ok=True)
            sync_directory(self.state)
            result = import_closed_bundle(bundle, directory, expected_identity=identity,
                                          verified_inputs=inputs, terminal=terminal)
            result.pop("customer_log", None)
            self.require_linux_artifact_window(bound)
            with self.db:
                self.save(operation, dict(value, status="native_ready", **result))
        except (OSError, sqlite3.Error) as error:
            raise Refusal("uncertain") from error
        return {"status": "running"}

    @staticmethod
    def require_linux_artifact_window(bound):
        if min(bound.guard.expires_at, bound.deadline_ms) <= now_ms():
            raise Refusal("stale")

    def linux_artifacts(self, bound, identity, value):
        from linux_android_artifact_importer import reopen_linux_artifacts, sync_directory

        if value["status"] != "native_ready" or value.get("tombstone"):
            raise Refusal("unavailable")
        self.require_linux_artifact_window(bound)
        operation = bound.identity.operation_id
        result = reopen_linux_artifacts(self.state / operation, expected_identity=identity,
                                        manifest_sha256=value["manifest_sha256"])
        if result["artifacts"] != value["artifacts"]:
            raise Refusal("uncertain")
        self.require_linux_artifact_window(bound)
        if "customer_log" in result:
            try:
                publish_customer_log(self.state, operation, value["binding"]["spec"],
                                     result["customer_log"], idempotent=True)
                sync_directory(self.state)
            except (OSError, ValueError) as error:
                raise Refusal("uncertain") from error
            self.require_linux_artifact_window(bound)
        return {"status": "native_ready", "artifacts": result["artifacts"], "profile": ANDROID_PROFILE,
                "platform": "android", "operation_id": operation}

    def settle_linux_stop(self, operation, value, closure, guard_expires_at):
        diagnostic = (literal({"operation_id": operation, "closure": closure}) + "\n").encode()
        sha = digest(diagnostic)
        directory = self.state / "blobs"
        try:
            directory.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(dir=directory) as staging:
                pending = Path(staging) / "evidence"
                with pending.open("xb") as handle:
                    handle.write(diagnostic)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(pending, directory / sha)
            # Always sync on retry, including when a previous rename succeeded.
            for path in (directory, self.state):
                fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        except OSError as error:
            raise Refusal("uncertain") from error
        if guard_expires_at <= now_ms():
            raise Refusal("stale")
        value.update(status="stopped", diagnostic_sha256=sha, closure=closure)
        try:
            with self.db:
                self.save(operation, value)
        except sqlite3.Error as error:
            raise Refusal("uncertain") from error
        return {"status": "stopped", "diagnostic_sha256": sha}

    def request(self, action, request):
        if action not in ("query", "ensure_started", "stop", "artifacts"):
            raise Refusal("unavailable")
        self.authorize(request["spec"])
        if action == "ensure_started" and request["deadline_ms"] <= now_ms():
            raise Refusal("stale")
        operation = request["operation_id"]
        if type(operation) is not str:
            raise Refusal("unavailable")
        previous = self.load(operation)
        if previous is not None and "ios_custody" in previous:
            if self.ios_custody is None or not self.ios_custody.matches(operation, previous):
                raise Refusal("uncertain")
        runner = self.linux_runner
        registered_for_runner = (runner is not None and request["spec"]["platform"] == "android"
                                 and request["spec"]["build_definition_sha256"] == runner.recipe_sha256)
        runner_bound = previous is not None and "linux_runner" in previous
        unstarted = previous is None or (previous["status"] == "absent" and not previous.get("tombstone"))
        if registered_for_runner and (runner_bound or unstarted):
            return self.request_linux(action, request, previous)
        if runner_bound:
            raise Refusal("unavailable")
        reply = super().request("query", request)
        value = self.load(operation)
        if "ios_custody" in value:
            if action == "stop" and value["status"] in ("running", "uncertain"):
                self.stop(operation, value)
            if value["status"] in ("running", "uncertain"):
                self.ios_custody.reconcile(self, operation, value)
            if value["status"] == "closed" and value.get("tombstone"):
                stopped = self.stop(operation, value)
                if action != "artifacts":
                    return stopped
            if value["status"] == "uncertain":
                if action == "stop":
                    return {"error": "uncertain"}
                reply = {"error": "uncertain"}
        status = value["status"]
        if action == "stop":
            if status == "absent":
                return super().request("stop", request)
            if status == "stopped":
                return reply
            return self.stop(operation, value)
        if action == "artifacts" and status == "native_ready" and now_ms() < request["deadline_ms"]:
            store = self.state / operation / "native"
            android = value["binding"]["spec"]["platform"] == "android"
            if android:
                artifacts = check_retained_android_artifacts(store, value)
                return {"status": "native_ready", "artifacts": artifacts, "profile": ANDROID_PROFILE,
                        "platform": "android", "operation_id": operation}
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
        if status == "closed" and "ios_custody" in value:
            return {"status": "build_failed", "diagnostic_sha256": self.closure_diagnostic(operation, value)}
        if status in ("closed", "native_ready"):
            # Reconciliation can install the stop tombstone when its deadline expires.
            return {"status": "running"}
        if action == "ensure_started" and status == "absent" and not value.get("tombstone"):
            recipe = self.verify(request["spec"])
            if self.capacity_occupied():
                raise Refusal("unavailable")
            if self.ios_custody is not None and request["spec"]["platform"] == "ios":
                self.ios_custody.submit(self, operation, value, recipe)
                return {"status": "running"}
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
        # Independent owners retain custody across controller shutdown.
        # Unproven in-process custody still prevents shutdown.
        if self.db.execute("""SELECT 1 FROM operations
                WHERE json_extract(value,'$.status')='uncertain'
                  AND json_type(value,'$.linux_runner') IS NULL
                  AND json_type(value,'$.ios_custody') IS NULL""").fetchone():
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


def serve(config, state, *, linux_runner=None):
    worker = NativeWorker(config, state, linux_runner=linux_runner)

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

    class Server(socketserver.TCPServer):
        # A replacement listener uses the same pinned loopback port even
        # when connections from the previous listener are in TIME_WAIT.
        allow_reuse_address = worker.ios_custody is not None and worker.ios_custody.reusable

    with Server(("127.0.0.1", config["port"]), Handler) as server:
        server.timeout = 0.1
        server.closed = False
        while not server.closed:
            server.handle_request()
            if not server.closed:
                worker.finish()


def configured_linux_runner(config):
    if "linux_runner" not in config:
        if "linux_artifact_imports" in config:
            raise Refusal("unavailable")
        return None
    from linux_android_runner import LinuxAndroidRunnerClient

    runner = config["linux_runner"]
    spec = config["registration"]["spec"]
    if (type(runner) is not dict or set(runner) != {"socket_path", "recipe_sha256", "store_id"}
            or type(runner["socket_path"]) is not str
            or spec["platform"] != "android"
            or spec["build_definition_sha256"] != runner["recipe_sha256"]):
        raise Refusal("unavailable")
    return LinuxAndroidRunnerClient(**runner)


if __name__ == "__main__":
    configuration = Path(sys.argv[1]).read_bytes()
    if digest(configuration) != sys.argv[2]:
        raise SystemExit("Configuration digest mismatch")
    config = json.loads(configuration)
    try:
        linux_runner = configured_linux_runner(config)
    except (Refusal, KeyError, TypeError, ValueError) as error:
        raise SystemExit("Invalid Linux runner configuration") from error
    serve(config, sys.argv[3], linux_runner=linux_runner)
