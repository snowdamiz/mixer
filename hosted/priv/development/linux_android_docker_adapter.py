"""One offline, operator-staged Docker recipe behind the private v1 runner.

Use a dedicated daemon with a stable Unix socket and stable host directories.
The operator owns the Docker executable, socket, and immutable staged inputs.
Provision once with initialize=True, and reopen both original journals on
restart. Keep the socket and its ancestors under trusted operator control.
"""
from contextlib import closing, contextmanager
import ctypes
from dataclasses import asdict, dataclass
import fcntl
from itertools import islice
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import time

from compiler_worker import Refusal, digest, literal
from linux_android_artifact_importer import (
    KINDS, METADATA_LIMIT, VerifiedLinuxInputs, decode, read_bundle_index, sync_directory, write_owned,
)
from linux_android_pair25_layout import GUEST_USER, Pair25Layout, environment
from linux_android_runner import TIMEOUT_SECONDS, RunnerIdentity, sha256, unique_object
from linux_android_runner_server import ContainerObservation, live, open_runner, private_file, require_private
from native_artifact_worker import ANDROID_DRIVER, file_stamp, open_android_store, read_owned


OUTPUT_ENTRIES_PER_PASS = 4096
OUTPUT_MAX_DEPTH = 32
BUNDLE_METADATA = ("readback.json", "linux-mixer.lock")
BUNDLE_ENTRY_COUNT = len(KINDS) + len(BUNDLE_METADATA)
DRIVER_LIMIT = 8 * 1024 * 1024


@dataclass(frozen=True)
class CompletionGrant:
    identity: RunnerIdentity
    bundle: Path
    inputs: VerifiedLinuxInputs

    @classmethod
    def read(cls, operation, value, private_paths):
        if type(value) is not dict or set(value) != {"identity", "bundle", "inputs"}:
            raise Refusal("unavailable")
        identity = RunnerIdentity(**value["identity"])
        inputs = VerifiedLinuxInputs(**value["inputs"])
        bundle = Path(value["bundle"])
        if (operation != identity.operation_id or not bundle.is_absolute()
                or bundle.name.startswith(".mixer-l05-")
                or not all(sha256(field) for field in (*asdict(identity).values(), *asdict(inputs).values()))
                or any(bundle.is_relative_to(path) or path.is_relative_to(bundle) for path in private_paths)):
            raise Refusal("unavailable")
        return cls(identity, bundle, inputs)

    @property
    def pending(self):
        return self.bundle.with_name(f".mixer-l05-{self.identity.operation_id}.pending")

    def verify_bundle(self, path, pinned_directory, readback_sha256, cutoff):
        live(cutoff)
        with open_android_store(path) as (fd, info):
            if (info.st_dev, info.st_ino) != pinned_directory:
                raise Refusal("uncertain")
            stamps = {name: entry_stamp(fd, name) for name in BUNDLE_METADATA}
            files, rows, _ = read_bundle_index(fd, self.inputs, readback_sha256)
            stamps.update({name: entry_stamp(fd, name) for name in files})
            with os.scandir(fd) as entries:
                if {entry.name for entry in islice(entries, len(stamps) + 1)} != stamps.keys():
                    raise Refusal("uncertain")
            build = decode(read_owned("readback.json", METADATA_LIMIT, dir_fd=fd))["build"]
            if (build["apk_sha256"] != rows[0]["sha256"] or type(build["apk_bytes"]) is not int
                    or build["apk_bytes"] != rows[0]["sizeBytes"]):
                raise Refusal("uncertain")
            for name, row in zip(files, rows, strict=True):
                live(cutoff)
                payload = read_owned(name, row["sizeBytes"], dir_fd=fd)
                if len(payload) != row["sizeBytes"] or digest(payload) != row["sha256"]:
                    raise Refusal("uncertain")
                if row["kind"] == "resource_inventory":
                    inventory = decode(payload)
                    if (type(inventory["formatVersion"]) is not int or inventory["formatVersion"] != 1
                            or inventory["apkSHA256"] != rows[0]["sha256"]
                            or inventory["debugSymbolsSHA256"] != rows[1]["sha256"]):
                        raise Refusal("uncertain")
            if any(entry_stamp(fd, name) != before for name, before in stamps.items()):
                raise Refusal("uncertain")
        live(cutoff)
        return stamps


def entry_stamp(fd, name):
    return file_stamp(os.stat(name, dir_fd=fd, follow_symlinks=False))


def exit_output_stamp(fd, info):
    stamps = []
    for name in BUNDLE_METADATA:
        try:
            stamps.append(entry_stamp(fd, name))
        except FileNotFoundError:
            stamps.append(None)
    return literal([file_stamp(info), *stamps])


def read_mount_file(fd, name, limit, owners):
    # The root-operated runner uses an unprivileged guest; the copied bundle
    # itself is always owned by the runner.
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    with os.fdopen(handle, "rb") as source:
        before = os.fstat(handle)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in owners or before.st_nlink != 1
                or before.st_mode & 0o022 or not 0 < before.st_size <= limit):
            raise Refusal("uncertain")
        payload = source.read(before.st_size + 1)
        stamp = file_stamp(before)
        if len(payload) != before.st_size or stamp != file_stamp(os.fstat(handle)) or stamp != entry_stamp(fd, name):
            raise Refusal("uncertain")
        return payload, stamp


def rename_bundle(parent, source, destination):
    # A normal directory rename can overwrite an empty destination.
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin":
        symbol, flags = "renameatx_np", 0x4  # RENAME_EXCL
    elif sys.platform == "linux":
        symbol, flags = "renameat2", 1  # RENAME_NOREPLACE
    else:
        raise Refusal("unavailable")
    rename = getattr(libc, symbol, None)
    if rename is None:
        raise Refusal("unavailable")
    if rename(parent, os.fsencode(source), parent, os.fsencode(destination), flags) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), destination)


@dataclass(frozen=True)
class DockerRecipe:
    image: str
    image_id: str
    platform: str
    entrypoint: str
    arguments: tuple[str, ...]

    @property
    def manifest_digest(self):
        return self.image.rsplit("@", 1)[1]

    @classmethod
    def read(cls, manifest, expected_digest):
        with Path(manifest).open("rb") as source:
            data = source.read(16_385)
        if len(data) > 16_384 or digest(data) != expected_digest:
            raise Refusal("unavailable")
        spec = json.loads(data, object_pairs_hook=unique_object)
        if (type(spec) is not dict
                or set(spec) != {"image", "image_id", "platform", "entrypoint", "arguments"}
                or type(spec["image"]) is not str
                or not re.fullmatch(r"[a-z0-9][a-z0-9._:/-]*@sha256:[a-f0-9]{64}", spec["image"])
                or type(spec["image_id"]) is not str or not spec["image_id"].startswith("sha256:")
                or not sha256(spec["image_id"][7:])
                or spec["platform"] not in ("linux/arm64", "linux/amd64")
                or type(spec["entrypoint"]) is not str or not spec["entrypoint"].startswith("/")
                or "\0" in spec["entrypoint"] or type(spec["arguments"]) is not list
                or any(type(arg) is not str or "\0" in arg for arg in spec["arguments"])):
            raise Refusal("unavailable")
        return cls(**(spec | {"arguments": tuple(spec["arguments"])}))


def directory_identity(path, *, private=False):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or path.resolve() != path
            or (private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700))):
        raise Refusal("unavailable")
    return info.st_dev, info.st_ino


def socket_identity(path):
    info = path.lstat()
    if not stat.S_ISSOCK(info.st_mode) or path.resolve() != path:
        raise Refusal("unavailable")
    return info.st_dev, info.st_ino


def mount_argument(path, target, *, readonly=False):
    if any(char in str(path) for char in ',"\r\n\0'):
        raise Refusal("unavailable")
    argument = f"type=bind,source={path},target={target},bind-recursive=disabled"
    return argument + ",readonly" if readonly else argument


@dataclass(frozen=True)
class Attempt:
    phase: str
    container_id: str | None
    output_device: int | None
    output_inode: int | None
    successful_exit: int
    exit_output_stamp: str | None


@dataclass(frozen=True)
class Seal:
    device: int
    inode: int
    output_stamp: str
    readback: str | None
    files: str | None

    @property
    def directory(self):
        return self.device, self.inode


class DockerContainerAdapter:
    """The runner serializes calls, including across runner restarts."""

    def __init__(self, configuration, recipe, command_timeout, completions, layout):
        self.recipe = recipe
        self.completions = completions
        self.bundle_parents = {operation: value["parent_identity"]
                               for operation, value in configuration.get("completions", {}).items()}
        self.recipe_sha256 = configuration["recipe_sha256"]
        self.store_id = configuration["store_id"]
        self.daemon_id = configuration["daemon_id"]
        self.inputs = Path(configuration["inputs"])
        self.outputs = Path(configuration["outputs"])
        self.stage_identity = tuple(configuration["stage_identity"])
        self.output_root_identity = tuple(configuration["output_root_identity"])
        self.daemon_socket = Path(configuration["socket"])
        self.socket_identity = tuple(configuration["socket_identity"])
        self.guest_user = configuration["guest_user"]
        self.layout = layout
        self.timeout = command_timeout
        directory = configuration["directory"]
        self.cli_config = Path(directory) / "config.json"
        self.environment = {"HOME": directory, "LC_ALL": "C", "PATH": os.defpath}
        self.command = (
            configuration["docker"], "--config", directory,
            "--host", "unix://" + configuration["socket"],
        )

    def _docker(self, *arguments, cutoff=None):
        if socket_identity(self.daemon_socket) != self.socket_identity:
            raise Refusal("uncertain")
        try:
            self.cli_config.lstat()
        except FileNotFoundError:
            pass
        else:
            # Docker config can inject proxy environment variables into create.
            raise Refusal("unavailable")
        timeout = self.timeout
        if cutoff is not None:
            live(cutoff)
            timeout = min(timeout, (cutoff * 1_000_000 - time.time_ns()) / 1_000_000_000)
            if timeout <= 0:
                raise Refusal("stale")
        try:
            result = subprocess.run(
                (*self.command, *arguments), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, env=self.environment, timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired as error:
            # Reaping the CLI does not settle a mutation accepted by the daemon.
            raise Refusal("uncertain") from error
        if (socket_identity(self.daemon_socket) != self.socket_identity
                or result.returncode != 0 or len(result.stdout) > 65_536):
            raise Refusal("uncertain")
        return result.stdout.decode("utf-8")

    def _check_daemon(self, *, cutoff=None):
        if self._docker("info", "--format", "{{.ID}}", cutoff=cutoff) != self.daemon_id + "\n":
            raise Refusal("uncertain")

    def _inspect(self, kind, target, *options, cutoff=None):
        response = json.loads(
            self._docker(kind, "inspect", *options, target, cutoff=cutoff),
            object_pairs_hook=unique_object,
        )
        if type(response) is not list or len(response) != 1 or type(response[0]) is not dict:
            raise Refusal("uncertain")
        return response[0]

    def _check_image(self, cutoff):
        image = self._inspect("image", self.recipe.image, "--platform", self.recipe.platform, cutoff=cutoff)
        if (f'{image["Os"]}/{image["Architecture"]}' != self.recipe.platform
                or image["Id"] != self.recipe.image_id
                or image["Descriptor"]["digest"] != self.recipe.manifest_digest
                or type(image["Config"]) is not dict
                or image["Config"].get("Volumes") not in (None, {})):
            raise Refusal("uncertain")
        return image["Config"].get("Env")

    def admit_layout(self):
        self._check_daemon()
        self.image_env = self._check_image(None)
        environment(self.image_env)
        self.layout.recheck_stage()
        self.volume_identity = self._read_volume()
        return {
            "stage_directories": self.layout.stage_directories,
            "stage_files": self.layout.stage_files,
            "volume_identity": self.volume_identity,
            "image_env": self.image_env,
        }

    def _read_volume(self, cutoff=None):
        data = self._inspect("volume", self.layout.volume_name, cutoff=cutoff)
        return self.layout.volume_identity(data)

    def _check_volume(self, cutoff):
        if self.layout is not None and self._read_volume(cutoff) != self.volume_identity:
            raise Refusal("uncertain")

    @staticmethod
    def _name(identity):
        return "mixer-l05-" + digest(literal(asdict(identity)).encode())

    @staticmethod
    def _labels(identity):
        return {f"mixer.runner.{field}": value for field, value in asdict(identity).items()}

    def _output(self, identity):
        if directory_identity(self.outputs, private=True) != self.output_root_identity:
            raise Refusal("uncertain")
        if self.layout is not None:
            return self.layout.output(self._name(identity))
        return self.outputs / self._name(identity)

    def _attempt(self, identity):
        if (type(identity) is not RunnerIdentity or not sha256(identity.operation_id)
                or not sha256(identity.binding_sha256) or identity.recipe_sha256 != self.recipe_sha256
                or identity.store_id != self.store_id):
            raise Refusal("unavailable")
        row = self.db.execute(
            """SELECT binding, phase, cid, device, inode, successful_exit, exit_output_stamp
               FROM attempt WHERE operation = ?""",
            (identity.operation_id,),
        ).fetchone()
        if row is None:
            return None
        if row[0] != identity.binding_sha256 or (row[2] is not None and not sha256(row[2])):
            raise Refusal("uncertain")
        return Attempt(*row[1:])

    def _completion(self, identity):
        grant = self.completions.get(identity.operation_id)
        return grant if grant is not None and grant.identity == identity else None

    def _seal_record(self, identity):
        row = self.db.execute(
            "SELECT device, inode, output_stamp, readback, files FROM seal WHERE operation = ?",
            (identity.operation_id,),
        ).fetchone()
        return Seal(*row) if row is not None else None

    @contextmanager
    def _bundle_parent(self, grant):
        parent = grant.bundle.parent
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            require_private(info, stat.S_IFDIR | 0o700)
            expected = tuple(self.bundle_parents[grant.identity.operation_id])
            if (info.st_dev, info.st_ino) != expected or directory_identity(parent, private=True) != expected:
                raise Refusal("uncertain")
            yield fd
            if directory_identity(parent, private=True) != expected:
                raise Refusal("uncertain")
        finally:
            os.close(fd)

    def _verify_staged_inputs(self, grant, cutoff):
        if self.layout is not None:
            live(cutoff)
            self.layout.recheck_stage()
            return
        if directory_identity(self.inputs) != self.stage_identity:
            raise Refusal("uncertain")
        if grant is not None:
            for name, limit, expected in (
                ("linux-mixer.lock", METADATA_LIMIT, grant.inputs.linux_lock_sha256),
                (f"Export/{ANDROID_DRIVER}", DRIVER_LIMIT, grant.inputs.rendered_driver_sha256),
            ):
                live(cutoff)
                path = self.inputs / name
                if path.resolve(strict=True) != path or digest(read_owned(path, limit, allow_owner_write=True)) != expected:
                    raise Refusal("uncertain")
            if directory_identity(self.inputs) != self.stage_identity:
                raise Refusal("uncertain")

    def _verify_start_inputs(self, identity, cutoff):
        grant = self._completion(identity)
        if grant is None and (self.layout is not None or identity.operation_id in self.completions):
            raise Refusal("unavailable")
        if grant is not None:
            self._check_unused_destination(grant)
        self._verify_staged_inputs(grant, cutoff)

    def _create_arguments(self, identity, output):
        if self.layout is not None:
            return self.layout.create_arguments(self._name(identity))
        return (
            "--tmpfs", "/tmp:rw,nosuid,nodev,exec,size=512m",
            "--user", self.guest_user, "--mount", mount_argument(self.inputs, "/inputs", readonly=True),
            "--mount", mount_argument(output, "/output"), "--entrypoint", self.recipe.entrypoint,
            self.recipe.image, *self.recipe.arguments,
        )

    def _phase(self, identity, phase):
        with self.db:
            self.db.execute("UPDATE attempt SET phase = ? WHERE operation = ?", (phase, identity.operation_id))

    def _output_present(self, output, attempt):
        try:
            found = directory_identity(output)
        except FileNotFoundError:
            return False
        if attempt is None or found != (attempt.output_device, attempt.output_inode):
            raise Refusal("uncertain")
        return True

    def _container_state(self, identity, attempt, output, *, cutoff=None):
        data = self._inspect("container", attempt.container_id, cutoff=cutoff)
        config, state = data["Config"], data["State"]
        labels = config["Labels"]
        host = data["HostConfig"]
        if (data["Id"] != attempt.container_id or data["Name"] != "/" + self._name(identity)
                or type(labels) is not dict
                or any(labels.get(key) != value for key, value in self._labels(identity).items())
                or config["Image"] != self.recipe.image or data["Platform"] != "linux"
                or data["Image"] != self.recipe.image_id
                or data["ImageManifestDescriptor"]["digest"] != self.recipe.manifest_digest
                or config["Entrypoint"] != [self.recipe.entrypoint]
                or (config["Cmd"] if config["Cmd"] is not None else []) != list(self.recipe.arguments)
                or config["User"] != self.guest_user or host["NetworkMode"] != "none"
                or host["PidMode"] not in ("", "private") or host["IpcMode"] != "private"
                or host["Privileged"] is not False or host["ReadonlyRootfs"] is not True
                or host["AutoRemove"] is not False or host["RestartPolicy"]["Name"] != "no"
                or any(state[key] is not False for key in ("Paused", "Restarting", "Dead"))
                or type(state["Pid"]) is not int):
            raise Refusal("uncertain")
        if self.layout is not None:
            self.layout.verify_container(data, self._name(identity), self.volume_identity, self.image_env)
        else:
            mounts = [(m["Type"], m["Source"], m["Destination"], m["RW"]) for m in data["Mounts"]]
            if (sorted(mounts) != sorted([
                    ("bind", str(self.inputs), "/inputs", False),
                    ("bind", str(output), "/output", True),
                ]) or any(type(mount[3]) is not bool for mount in mounts)):
                raise Refusal("uncertain")
        if state["Status"] == "running" and state["Running"] is True and state["Pid"] > 0:
            return state
        if state["Status"] in ("created", "exited") and state["Running"] is False and state["Pid"] == 0:
            return state
        raise Refusal("uncertain")

    @staticmethod
    def _successful(state):
        return (state["Status"] == "exited" and type(state.get("ExitCode")) is int and state["ExitCode"] == 0
                and state.get("OOMKilled") is False and state.get("Error") == "")

    def _confirm_removed(self, attempt, *, cutoff=None):
        self._check_daemon(cutoff=cutoff)
        if self._docker("container", "ls", "--all", "--quiet", "--no-trunc",
                        "--filter", f"id={attempt.container_id}", cutoff=cutoff) != "":
            raise Refusal("uncertain")

    def _sync_output_root(self):
        fd = os.open(self.outputs, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) != self.output_root_identity:
                raise Refusal("uncertain")
            os.fsync(fd)
        finally:
            os.close(fd)

    def observe(self, identity):
        attempt = self._attempt(identity)
        output = self._output(identity)
        if attempt is None:
            self._output_present(output, None)
            return ContainerObservation(identity, "absent", True, True)
        if attempt.phase in ("creating", "removing"):
            raise Refusal("uncertain")
        present = self._output_present(output, attempt)
        seal = self._seal_record(identity)
        pending = attempt.successful_exit == 1 and seal is not None and seal.readback is not None
        if attempt.phase == "cleaning":
            # This phase durably records successful removal and exact absence.
            staged = False
            grant = self._completion(identity)
            if grant is not None and seal is not None:
                with self._bundle_parent(grant) as parent:
                    staged = os.path.lexists(grant.pending)
                    if not staged:
                        os.fsync(parent)
            elif grant is not None and os.path.lexists(grant.pending):
                raise Refusal("uncertain")
            if not present:
                self._sync_output_root()
            return ContainerObservation(identity, "absent", True, not (present or staged), completion_pending=pending)
        if attempt.phase == "removed":
            self._confirm_removed(attempt)
            if not present:
                raise Refusal("uncertain")
            return ContainerObservation(identity, "absent", True, False, completion_pending=pending)
        if not present:
            raise Refusal("uncertain")
        self._check_daemon()
        state = self._container_state(identity, attempt, output)
        if state["Status"] == "running":
            return ContainerObservation(identity, "running", False, False)
        if state["Status"] == "created" and attempt.phase == "created":
            return ContainerObservation(identity, "present", True, False, prepared_id=attempt.container_id)
        pending = attempt.phase == "starting" and self._successful(state) and self._completion(identity) is not None
        return ContainerObservation(identity, "present", state["Status"] == "exited", False,
                                    completion_pending=pending)

    def ensure_started(self, identity, cutoff_ms):
        if self._attempt(identity) is not None:
            raise Refusal("uncertain")
        output = self._output(identity)
        self._output_present(output, None)
        self._verify_start_inputs(identity, cutoff_ms)
        self._check_daemon(cutoff=cutoff_ms)
        image_env = self._check_image(cutoff_ms)
        if self.layout is not None and image_env != self.image_env:
            raise Refusal("uncertain")
        self._check_volume(cutoff_ms)
        live(cutoff_ms)
        with self.db:
            self.db.execute("INSERT INTO attempt (operation, binding, phase) VALUES (?, ?, 'creating')",
                            (identity.operation_id, identity.binding_sha256))
        output.mkdir(mode=0o700)
        if self.layout is not None or os.getuid() == 0:
            # Permit the fixed unprivileged guest to write beneath the private output root.
            output.chmod(0o777)
        device, inode = directory_identity(output)
        labels = [part for key, value in self._labels(identity).items() for part in ("--label", f"{key}={value}")]
        response = self._docker(
            "container", "create", "--name", self._name(identity), *labels, "--pull", "never",
            "--platform", self.recipe.platform, "--network", "none", "--ipc", "private",
            "--cgroupns", "private", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges=true", "--no-healthcheck", "--restart", "no",
            "--memory", "5g", "--memory-swap", "5g", "--cpus", "4", "--pids-limit", "128",
            "--log-driver", "local", "--log-opt", "max-size=8m", "--log-opt", "max-file=1",
            "--log-opt", "compress=false",
            *self._create_arguments(identity, output), cutoff=cutoff_ms,
        )
        if not response.endswith("\n") or not sha256(response[:-1]):
            raise Refusal("uncertain")
        with self.db:
            self.db.execute(
                "UPDATE attempt SET phase = 'created', cid = ?, device = ?, inode = ? WHERE operation = ?",
                (response[:-1], device, inode, identity.operation_id),
            )
        self._start_created(identity, self._attempt(identity), output, cutoff_ms)

    def resume_prepared(self, identity, container_id, cutoff_ms):
        attempt = self._attempt(identity)
        if attempt is None or attempt.phase != "created" or attempt.container_id != container_id:
            raise Refusal("uncertain")
        output = self._output(identity)
        self._check_daemon(cutoff=cutoff_ms)
        self._start_created(identity, attempt, output, cutoff_ms)

    def _start_created(self, identity, attempt, output, cutoff_ms):
        if self._container_state(identity, attempt, output, cutoff=cutoff_ms)["Status"] != "created":
            raise Refusal("uncertain")
        if not self._output_present(output, attempt):
            raise Refusal("uncertain")
        self._verify_start_inputs(identity, cutoff_ms)
        with open_mount(output, (attempt.output_device, attempt.output_inode)) as (fd, _), os.scandir(fd) as entries:
            if next(entries, None) is not None:
                raise Refusal("uncertain")
        self._check_volume(cutoff_ms)
        live(cutoff_ms)
        self._phase(identity, "starting")
        self._docker("container", "start", attempt.container_id, cutoff=cutoff_ms)

    def stop(self, identity):
        attempt = self._attempt(identity)
        output = self._output(identity)
        if attempt is None:
            self._output_present(output, None)
            return
        if attempt.phase in ("creating", "removing"):
            raise Refusal("uncertain")
        if attempt.phase in ("created", "starting"):
            if not self._output_present(output, attempt):
                raise Refusal("uncertain")
            self._check_daemon()
            state = self._container_state(identity, attempt, output)["Status"]
            if state == "running":
                self._docker("container", "stop", "--time", "0", attempt.container_id)
                state = self._container_state(identity, attempt, output)["Status"]
            if not (state == "exited" or (state == "created" and attempt.phase == "created")):
                raise Refusal("uncertain")
            attempt = self._remove(identity, attempt, successful=False)
        cutoff = time.time_ns() // 1_000_000 + int(TIMEOUT_SECONDS * 1000)
        self._clean(identity, attempt, output, cutoff)
        grant = self._completion(identity)
        if grant is not None:
            self._discard_pending(grant, cutoff)

    def complete(self, identity, cutoff):
        grant = self._completion(identity)
        attempt = self._attempt(identity)
        output = self._output(identity)
        if grant is None or attempt is None:
            raise Refusal("uncertain")
        if attempt.phase == "starting":
            if not self._output_present(output, attempt) or directory_identity(self.inputs) != self.stage_identity:
                raise Refusal("uncertain")
            self._check_daemon(cutoff=cutoff)
            state = self._container_state(identity, attempt, output, cutoff=cutoff)
            if not self._successful(state):
                raise Refusal("uncertain")
            self._seal_output(grant, attempt, output, cutoff)
            attempt = self._remove(identity, attempt, successful=True, cutoff=cutoff)
        if not attempt.successful_exit or attempt.phase not in ("removed", "cleaning"):
            raise Refusal("uncertain")
        seal = self._seal_record(identity)
        if seal is None or not sha256(seal.readback):
            raise Refusal("uncertain")
        self._clean(identity, attempt, output, cutoff)
        if self._output_present(output, attempt):
            raise Refusal("uncertain")
        self._sync_output_root()
        self._publish_bundle(grant, seal, cutoff)
        return {
            "inputs": asdict(grant.inputs), "readback_sha256": seal.readback, "exit_code": 0,
            "start_fenced": True, "container_absent": True, "processes_absent": True, "resources_removed": True,
        }

    def _check_unused_destination(self, grant):
        with self._bundle_parent(grant):
            if os.path.lexists(grant.bundle) or os.path.lexists(grant.pending):
                raise Refusal("uncertain")

    def _seal_output(self, grant, attempt, output, cutoff):
        identity = grant.identity
        seal = self._seal_record(identity)
        pin = (attempt.output_device, attempt.output_inode)
        with self._bundle_parent(grant) as parent, open_mount(output, pin) as (source, info):
            live(cutoff)
            # Keep the first terminal snapshot even when its metadata is missing.
            closed = exit_output_stamp(source, info)
            if attempt.exit_output_stamp is None:
                with self.db:
                    self.db.execute("UPDATE attempt SET exit_output_stamp = ? WHERE operation = ?",
                                    (closed, identity.operation_id))
            elif attempt.exit_output_stamp != closed:
                raise Refusal("uncertain")
            self._verify_staged_inputs(grant, cutoff)
            if os.path.lexists(grant.bundle):
                raise Refusal("uncertain")
            owners = {os.getuid(), int(self.guest_user.split(":")[0])}
            live(cutoff)
            index, index_stamp = read_mount_file(source, "readback.json", METADATA_LIMIT, owners)
            records = decode(index)["artifacts"]
            if type(records) is not list or len(records) != len(KINDS):
                raise Refusal("uncertain")
            names = [record["file"] for record in records]
            if any(type(name) is not str or not name or Path(name).name != name or "\0" in name
                   or "\\" in name or name in (".", "..") for name in names):
                raise Refusal("uncertain")
            stamps = {name: entry_stamp(source, name) for name in (*BUNDLE_METADATA, *names)}
            if (stamps["readback.json"] != index_stamp
                    or closed != literal([file_stamp(info), *(stamps[name] for name in BUNDLE_METADATA)])):
                raise Refusal("uncertain")
            snapshot = literal([file_stamp(info), stamps])
            if seal is None:
                os.mkdir(grant.pending.name, mode=0o700, dir_fd=parent)
                pin = directory_identity(grant.pending, private=True)
                # Pin the staging directory before any copy can be interrupted.
                os.fsync(parent)
                with self.db:
                    self.db.execute("INSERT INTO seal (operation, device, inode, output_stamp) VALUES (?, ?, ?, ?)",
                                    (identity.operation_id, *pin, snapshot))
                seal = self._seal_record(identity)
            if seal.output_stamp != snapshot:
                raise Refusal("uncertain")
            if seal.readback is not None:
                self._verify_seal(grant, grant.pending, seal, cutoff)
                return

            # A failed copy can only change files in the pinned staging
            # directory. Rebuild that directory's contents from the same raw snapshot.
            with open_android_store(grant.pending) as (fd, pending):
                if (pending.st_dev, pending.st_ino) != seal.directory:
                    raise Refusal("uncertain")
                with os.scandir(fd) as entries:
                    previous = list(islice(entries, BUNDLE_ENTRY_COUNT + 1))
                    if (len(previous) > BUNDLE_ENTRY_COUNT
                            or any(not entry.is_file(follow_symlinks=False) for entry in previous)):
                        raise Refusal("uncertain")
            for entry in previous:
                (grant.pending / entry.name).unlink()

            live(cutoff)
            lock, lock_stamp = read_mount_file(source, "linux-mixer.lock", METADATA_LIMIT, owners)
            if lock_stamp != stamps["linux-mixer.lock"]:
                raise Refusal("uncertain")
            write_owned(grant.pending / "readback.json", index)
            write_owned(grant.pending / "linux-mixer.lock", lock)
            readback = digest(index)
            with open_android_store(grant.pending) as (fd, _):
                files, rows, _ = read_bundle_index(fd, grant.inputs, readback)
            for name, row in zip(files, rows, strict=True):
                live(cutoff)
                payload, copied = read_mount_file(source, name, row["sizeBytes"], owners)
                if copied != stamps[name]:
                    raise Refusal("uncertain")
                write_owned(grant.pending / name, payload)
            verified = grant.verify_bundle(grant.pending, seal.directory, readback, cutoff)
            sync_directory(grant.pending)
            self._check_daemon(cutoff=cutoff)
            if (not self._successful(self._container_state(identity, attempt, output, cutoff=cutoff))
                    or any(entry_stamp(source, name) != before for name, before in stamps.items())
                    or file_stamp(info) != file_stamp(os.fstat(source))
                    or file_stamp(info) != file_stamp(output.lstat())):
                raise Refusal("uncertain")
            live(cutoff)
            with self.db:
                self.db.execute("UPDATE seal SET readback = ?, files = ? WHERE operation = ?",
                                (readback, literal(verified), identity.operation_id))

    @staticmethod
    def _verify_seal(grant, path, seal, cutoff):
        if literal(grant.verify_bundle(path, seal.directory, seal.readback, cutoff)) != seal.files:
            raise Refusal("uncertain")

    def _publish_bundle(self, grant, seal, cutoff):
        with self._bundle_parent(grant) as parent:
            if os.path.lexists(grant.pending):
                self._verify_seal(grant, grant.pending, seal, cutoff)
                live(cutoff)
                rename_bundle(parent, grant.pending.name, grant.bundle.name)
            else:
                self._verify_seal(grant, grant.bundle, seal, cutoff)
            if directory_identity(grant.bundle, private=True) != seal.directory:
                raise Refusal("uncertain")
            os.fsync(parent)
        live(cutoff)

    def _discard_pending(self, grant, cutoff):
        seal = self._seal_record(grant.identity)
        if not os.path.lexists(grant.pending):
            return
        if seal is None:
            raise Refusal("uncertain")
        with self._bundle_parent(grant) as parent:
            remove_output(grant.pending, seal.directory, cutoff)
            os.fsync(parent)

    def _remove(self, identity, attempt, *, successful, cutoff=None):
        if cutoff is not None:
            live(cutoff)
        with self.db:
            self.db.execute("UPDATE attempt SET phase = 'removing', successful_exit = ? WHERE operation = ?",
                            (successful, identity.operation_id))
        if self._docker("container", "rm", attempt.container_id, cutoff=cutoff) != attempt.container_id + "\n":
            raise Refusal("uncertain")
        self._phase(identity, "removed")
        return self._attempt(identity)

    def _clean(self, identity, attempt, output, cutoff):
        if attempt.phase == "removed":
            self._confirm_removed(attempt, cutoff=cutoff)
            if not self._output_present(output, attempt):
                raise Refusal("uncertain")
            self._phase(identity, "cleaning")
        if self._output_present(output, attempt):
            remove_output(output, (attempt.output_device, attempt.output_inode), cutoff)


@contextmanager
def open_mount(output, pin):
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if (info.st_dev, info.st_ino) != pin:
            raise Refusal("uncertain")
        yield fd, info
    finally:
        os.close(fd)


def remove_output(output, pin, cutoff):
    # Only entered after exact absence. The private parent has no guest writer.
    # Limit depth and entries per pass. A partial pass remains in 'cleaning'.
    budget = OUTPUT_ENTRIES_PER_PASS
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

    def empty(fd, depth):
        nonlocal budget
        with os.scandir(fd) as entries:
            for entry in entries:
                live(cutoff)
                budget -= 1
                if budget < 0 or depth >= OUTPUT_MAX_DEPTH:
                    raise Refusal("uncertain")
                if entry.is_dir(follow_symlinks=False):
                    child = os.open(entry.name, flags, dir_fd=fd)
                    try:
                        if os.fstat(child).st_dev != pin[0]:
                            raise Refusal("uncertain")
                        empty(child, depth + 1)
                    finally:
                        os.close(child)
                    os.rmdir(entry.name, dir_fd=fd)
                else:
                    os.unlink(entry.name, dir_fd=fd)

    live(cutoff)
    with open_mount(output, pin) as (fd, _):
        empty(fd, 0)
        live(cutoff)
        if directory_identity(output) != pin:
            raise Refusal("uncertain")
        output.rmdir()


@contextmanager
def open_docker_runner(directory, *, recipe_sha256, store_id, manifest, docker, daemon_socket,
                       daemon_id, inputs=None, outputs=None, pair25_root=None,
                       initialize=False, command_timeout=0.2, completions=None):
    """Bind the v1 listener to its operator-pinned Docker recipe and journal.

    The manifest is JSON with image (repository@sha256:...), image_id (the
    exact local Docker image ID), platform, entrypoint, and arguments. The
    guest sees pre-staged inputs at /inputs and a fresh directory at /output.
    Use a daemon mapping the nonroot worker UID to the runner's UID on bind
    mounts. For a root runner the guest uses UID 65534.

    Optional completions maps operation IDs to the same grants as the
    worker's linux_artifact_imports: identity, inputs and bundle. The bundle
    path must be absent with a private operator-owned parent outside the bind
    mounts. Stage the pinned Linux lock at inputs/linux-mixer.lock and the
    rendered driver inside inputs/Export. The guest emits readback.json, the
    Linux lock and the indexed artifacts directly under /output.

    For Pair25, supply pair25_root in place of inputs and outputs. Its layout
    binds the recipe, stage and pre-provisioned volume. Each start requires a
    completion grant registered with the layout's input pins.
    """
    directory, docker, daemon_socket = map(Path, (directory, docker, daemon_socket))
    require_private(directory.lstat(), stat.S_IFDIR | 0o700)
    if (not sha256(recipe_sha256) or not sha256(store_id)
            or directory.resolve() != directory or not docker.is_absolute() or not daemon_socket.is_absolute()
            or not re.fullmatch(r"[a-zA-Z0-9:_-]{1,128}", daemon_id)
            or not math.isfinite(command_timeout) or not 0 < command_timeout <= 1):
        raise Refusal("unavailable")
    recipe = DockerRecipe.read(manifest, recipe_sha256)
    layout = None
    if pair25_root is None:
        if inputs is None or outputs is None:
            raise Refusal("unavailable")
        inputs, outputs = map(Path, (inputs, outputs))
        mount_argument(inputs, "/inputs", readonly=True)
        mount_argument(outputs, "/output")
        disjoint = ((inputs, outputs), (inputs, directory), (outputs, directory))
    else:
        if inputs is not None or outputs is not None:
            raise Refusal("unavailable")
        layout = Pair25Layout.read(pair25_root)
        layout.verify_recipe(recipe)
        inputs, outputs = layout.root, layout.root / "outputs"
        disjoint = ((inputs, directory),)
    stage_identity = directory_identity(inputs)
    output_root_identity = directory_identity(outputs, private=True)
    daemon_socket_identity = socket_identity(daemon_socket)
    for left, right in disjoint:
        if left.is_relative_to(right) or right.is_relative_to(left):
            raise Refusal("unavailable")
    if completions is not None and type(completions) is not dict:
        raise Refusal("unavailable")
    grants = {operation: CompletionGrant.read(operation, value, (directory, inputs, outputs))
              for operation, value in (completions or {}).items()}
    if any((grant.identity.recipe_sha256, grant.identity.store_id) != (recipe_sha256, store_id)
           for grant in grants.values()):
        raise Refusal("unavailable")
    if layout is not None and any(asdict(grant.inputs) != layout.verified_inputs for grant in grants.values()):
        raise Refusal("unavailable")
    if len({grant.bundle for grant in grants.values()}) != len(grants):
        raise Refusal("unavailable")
    configuration = {
        "recipe_sha256": recipe_sha256, "store_id": store_id, "directory": str(directory),
        "docker": str(docker), "socket": str(daemon_socket), "daemon_id": daemon_id,
        "socket_identity": daemon_socket_identity,
        "guest_user": GUEST_USER if layout is not None or os.getuid() == 0 else f"{os.getuid()}:{os.getgid()}",
        "inputs": str(inputs), "stage_identity": stage_identity,
        "outputs": str(outputs), "output_root_identity": output_root_identity,
    }
    lock_flags = os.O_RDWR | os.O_CREAT if initialize else os.O_RDONLY
    with private_file(directory / "docker-writer.lock", lock_flags) as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = directory / "docker-operations.sqlite"
        runner_db = directory / "operations.sqlite"
        journal_binding = os.read(lock, 1024)
        if initialize:
            if journal_binding:
                raise Refusal("unavailable")
            try:
                runner_db.lstat()
            except FileNotFoundError:
                pass
            else:
                raise FileExistsError(runner_db)
        if grants:
            configuration["completions"] = {
                operation: {
                    "identity": asdict(grant.identity), "bundle": str(grant.bundle),
                    "inputs": asdict(grant.inputs),
                    "parent_identity": directory_identity(grant.bundle.parent, private=True),
                }
                for operation, grant in grants.items()
            }
        adapter = DockerContainerAdapter(configuration, recipe, command_timeout, grants, layout)
        if layout is not None:
            configuration["pair25"] = adapter.admit_layout()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if initialize else os.O_RDONLY
        with private_file(path, flags) as adapter_journal, closing(
                sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=1)) as db:
            def bound_journals():
                info = runner_db.lstat()
                require_private(info, stat.S_IFREG | 0o600)
                adapter_info = os.fstat(adapter_journal)
                return literal(((info.st_dev, info.st_ino), (adapter_info.st_dev, adapter_info.st_ino))).encode()

            db.execute("PRAGMA synchronous=FULL")
            adapter.db = db
            if initialize:
                with db:
                    db.execute("BEGIN")
                    db.execute("CREATE TABLE configuration (value TEXT NOT NULL)")
                    db.execute("INSERT INTO configuration VALUES (?)", (literal(configuration),))
                    db.execute(
                        """CREATE TABLE attempt (
                               operation TEXT PRIMARY KEY, binding TEXT NOT NULL, phase TEXT NOT NULL,
                               cid TEXT, device INTEGER, inode INTEGER,
                               CHECK (phase IN ('creating', 'created', 'starting', 'removing', 'removed', 'cleaning')),
                               CHECK ((phase = 'creating' AND cid IS NULL AND device IS NULL AND inode IS NULL)
                                   OR (phase != 'creating' AND cid IS NOT NULL AND device IS NOT NULL AND inode IS NOT NULL))
                           )""",
                    )
            if db.execute("SELECT value FROM configuration").fetchall() != [(literal(configuration),)]:
                raise Refusal("unavailable")
            if not initialize and journal_binding != bound_journals():
                raise Refusal("unavailable")
            if "successful_exit" not in {column[1] for column in db.execute("PRAGMA table_info(attempt)")}:
                with db:
                    db.execute("""ALTER TABLE attempt ADD COLUMN successful_exit INTEGER NOT NULL
                                  DEFAULT 0 CHECK (successful_exit IN (0, 1))""")
            with db:
                if "exit_output_stamp" not in {column[1] for column in db.execute("PRAGMA table_info(attempt)")}:
                    db.execute("ALTER TABLE attempt ADD COLUMN exit_output_stamp TEXT")
                db.execute("""CREATE TABLE IF NOT EXISTS seal (
                                  operation TEXT PRIMARY KEY, device INTEGER NOT NULL, inode INTEGER NOT NULL,
                                  output_stamp TEXT NOT NULL, readback TEXT, files TEXT,
                                  CHECK ((readback IS NULL) = (files IS NULL))
                              )""")
            with open_runner(directory, recipe_sha256=recipe_sha256, store_id=store_id,
                             adapter=adapter, initialize=initialize,
                             identity_pins={key: grant.identity for key, grant in grants.items()},
                             require_start_pin=layout is not None) as server:
                if initialize:
                    binding = bound_journals()
                    if os.write(lock, binding) != len(binding):
                        raise Refusal("unavailable")
                    os.fsync(lock)
                yield server
