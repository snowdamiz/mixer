"""Operator-only launch layout for the offline Pair25 Starter."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


RECEIPT_SHA256 = "3f39b098a207e39a2da5e2500b80532cd130ee124c1e0f9d91f6029fe3dd4b44"
PRODUCTS_RECEIPT_SHA256 = "6c97dc344d5413fc07d5dd976dfa791e93388b7c33d1af811efc83654f63b89a"
MANIFEST = "sha256:3ad77b443f5f41d8c6c693659d9c951538dfeb79403e67cd40abca2501d4f191"
IMAGE = f"docker.io/library/swift@{MANIFEST}"
IMAGE_IDS = (MANIFEST, "sha256:3af9ff4bbeb3912a60bee99a537e4bd44e9010a8f933eefe29161e0f472464e9")
NOBLE_MANIFEST = "sha256:a7ec691ec569f1ff646952ffad348aebf5d829718e91ad56ae05cae6e57016f8"
NOBLE_IMAGE_IDS = (NOBLE_MANIFEST, "sha256:c3fd097562c903a6bf029409205d84f59f71cd229f0f0dbfa63cab8210fe98ef")
NOBLE_WORKER_SHA256 = "91b99b725fce85c2079ef662d3fb1421b2d9745154d722289d5f60669f36bed0"
NOBLE_PYTHON_SHA256 = "5e7abc424ac0e3db245a4d6e420c3d3cd5f21b11f78e4a46f029064ebdc1d653"
PROJECTION = "projection.json"
PROJECTION_DIGESTS = {"source_tree_sha256", "linux_lock_sha256", "rendered_driver_sha256",
                      "mac_lock_sha256", "platform_lock_sha256"}
PLATFORM = "linux/arm64"
GUEST_USER = "65534:65534"
ENTRYPOINT = "/bin/sh"
WORKER_SETUP = "umask 022; mkdir /work/home; ulimit -f 524288; umask 077; "
WORKER_EXEC = 'exec /python/bin/python3.12 /recipe/worker.py "$1"'
LOCK_ARGUMENTS = ("-euc", WORKER_SETUP + WORKER_EXEC, "pair25-worker", "lock")
ARGUMENTS = (
    "-euc",
    WORKER_SETUP + "(set -C; cat /project/mixer.lock > /deliver/linux-mixer.lock); " + WORKER_EXEC,
    "pair25-worker", "build",
)
TMPFS = (
    ("/tmp", "rw,nosuid,nodev,exec,size=512m"),
    ("/work", "rw,nodev,nosuid,exec,size=3g,mode=0700,uid=65534,gid=65534"),
)
ENV = (
    ("HOME", "/work/home"),
    ("PYTHONHOME", "/python"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("GIT_CONFIG_GLOBAL", "/dev/null"),
    ("GIT_CONFIG_NOSYSTEM", "1"),
    ("GIT_ALLOW_PROTOCOL", "file"),
    ("GIT_CONFIG_COUNT", "2"),
    ("GIT_CONFIG_KEY_0", "url.file:///mirrors/swift-asn1.git.insteadOf"),
    ("GIT_CONFIG_VALUE_0", "https://github.com/apple/swift-asn1.git"),
    ("GIT_CONFIG_KEY_1", "url.file:///mirrors/swift-crypto.git.insteadOf"),
    ("GIT_CONFIG_VALUE_1", "https://github.com/apple/swift-crypto.git"),
    ("JAVA_TOOL_OPTIONS", "-XX:ActiveProcessorCount=4 -Xmx1024m"),
)
BIND_INPUTS = (
    ("glibc", "/lib/x86_64-linux-gnu"), ("lib64", "/lib64"),
    ("recipe", "/recipe"), ("readonly/Export", "/project"),
    ("android-sdk", "/android-sdk"), ("mirrors", "/mirrors"), ("python", "/python"),
    ("lock/linux-mixer.lock", "/project/mixer.lock"),
)
TOOLCHAIN_TARGET = "/toolchain"
OUTPUT_TARGET = "/deliver"
METADATA_LIMIT = 1024 * 1024
LOADER = "ld-linux-x86-64.so.2"


class LayoutError(ValueError):
    """Missing, changed or incompatible operator inputs or daemon readback."""


def require(condition, message):
    if not condition:
        raise LayoutError(message)


def path_text(path):
    value = str(path)
    require(path.is_absolute() and not any(c in value for c in ',"\r\n\0'), f"Invalid mount path {path}")
    return value


def checked_path(path, kind):
    try:
        info = path.lstat()
        canonical = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise LayoutError(f"Cannot open staged path {path}") from error
    require(canonical == path and stat.S_IFMT(info.st_mode) == kind, f"Invalid staged path {path}")
    return info


def private_directory(path):
    info = checked_path(path, stat.S_IFDIR)
    require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
            f"Expected an operator-owned 0700 directory at {path}")


def stamp(info):
    return info.st_dev, info.st_ino, info.st_ctime_ns, info.st_mtime_ns, info.st_size


def pinned_file(path, expected, *, metadata=False, executable=False, private=False):
    info = checked_path(path, stat.S_IFREG)
    limit = METADATA_LIMIT if metadata else 128 * METADATA_LIMIT
    require(info.st_nlink == 1 and 0 < info.st_size <= limit, f"Invalid staged file {path}")
    if private:
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600,
                f"Expected an operator-owned 0600 approval at {path}")
    if executable:
        require(info.st_mode & 0o111, f"Staged tool is not executable at {path}")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as handle:
        require(stamp(os.fstat(handle.fileno())) == stamp(info), f"Staged file replaced at {path}")
        if metadata:
            data = handle.read(limit + 1)
            actual = hashlib.sha256(data).hexdigest()
        else:
            data = None
            digest = hashlib.sha256()
            remaining = info.st_size
            while remaining:
                chunk = handle.read(min(remaining, METADATA_LIMIT))
                require(chunk, f"Staged file truncated at {path}")
                digest.update(chunk)
                remaining -= len(chunk)
            actual = digest.hexdigest()
        require(stamp(os.fstat(handle.fileno())) == stamp(info)
                and stamp(checked_path(path, stat.S_IFREG)) == stamp(info), f"Staged file changed at {path}")
    require((private and expected is None) or actual == expected, f"SHA-256 mismatch at {path}")
    return data, stamp(info)


def unique_object(pairs):
    value = dict(pairs)
    require(len(value) == len(pairs), "Duplicate JSON key in staged metadata")
    return value


def environment(rows):
    if rows is None:
        return {}
    require(type(rows) is list, "Invalid Docker environment readback")
    result = {}
    for row in rows:
        require(type(row) is str, "Invalid Docker environment entry")
        name, sep, value = row.partition("=")
        require(sep and name and name not in result, "Invalid or duplicate Docker environment key")
        result[name] = value
    return result


@dataclass(frozen=True)
class Pair25Layout:
    root: Path
    source_tree_sha256: str
    linux_lock_sha256: str
    rendered_driver_sha256: str
    stage_directories: tuple
    stage_files: tuple
    projection_sha256: str | None = None

    @classmethod
    def read(cls, operator_root):
        """Admit a pre-staged layout before opening the managed runner."""
        root = Path(operator_root)
        path_text(root)
        private_directory(root)
        private_directory(root / "outputs")
        directories = {}
        files = {}

        def directory(relative):
            info = checked_path(root / relative, stat.S_IFDIR)
            directories[relative] = (info.st_dev, info.st_ino)

        def pinned(relative, expected, **options):
            data, files[relative] = pinned_file(root / relative, expected, **options)
            return data

        try:
            for relative, _ in BIND_INPUTS[:-1]:
                directory(relative)
            for relative in (".", "outputs", "lock"):
                directory(relative)
            try:
                (root / PROJECTION).lstat()
            except FileNotFoundError:
                projection_sha = None
                receipt = json.loads(pinned("recipe/receipt.json", RECEIPT_SHA256, metadata=True),
                                     object_pairs_hook=unique_object)
                products = json.loads(pinned("recipe/retained-products.json", PRODUCTS_RECEIPT_SHA256, metadata=True),
                                      object_pairs_hook=unique_object)
                require(products["priorPackagingReceipt"]["sha256"] == RECEIPT_SHA256,
                        "Retained product receipt does not bind the toolchain receipt")
                require(receipt["toolSources"]["swiftArm64Image"] == IMAGE,
                        "Pair25 toolchain is not bound to the recorded Swift image")
                build = products["build"]
                require(build["source_tree_sha256"] == build["source_tree_after_sha256"],
                        "Pair25 receipt has different input and output source tree identities")
                source = products["inputHashes"]
                pins = {"mac_lock_sha256": source["macMixerLockSHA256BeforeAndAfter"],
                        "linux_lock_sha256": source["localLinuxLockSHA256"],
                        "rendered_driver_sha256": source["renderedBuildDriverSHA256"],
                        "platform_lock_sha256": source["platformLockSHA256BeforeAndAfter"],
                        "source_tree_sha256": build["source_tree_sha256"]}
                manifest, worker_sha = MANIFEST, products["fixtureSHA256"]["worker.py"]
            else:
                data = pinned(PROJECTION, None, metadata=True, private=True)
                pins = json.loads(data, object_pairs_hook=unique_object)
                require(type(pins) is dict and pins.keys() == {"schema"} | PROJECTION_DIGESTS
                        and type(pins["schema"]) is int and pins["schema"] == 1
                        and all(type(pins[key]) is str and re.fullmatch(r"[0-9a-f]{64}", pins[key])
                                for key in PROJECTION_DIGESTS), "Invalid Pair25 projection approval")
                projection_sha = hashlib.sha256(data).hexdigest()
                manifest, worker_sha = NOBLE_MANIFEST, NOBLE_WORKER_SHA256
            project = "readonly/Export/"
            mac_lock = pinned(project + "mixer.lock", pins["mac_lock_sha256"], metadata=True)
            linux_lock = pinned("lock/linux-mixer.lock", pins["linux_lock_sha256"], metadata=True)
            mac, linux = (json.loads(data, object_pairs_hook=unique_object) for data in (mac_lock, linux_lock))
            toolchain = linux["android"].pop("toolchain")
            if projection_sha is None:
                require(toolchain == receipt["toolchain"], "Unexpected Linux lock toolchain identity")
            else:
                require(toolchain["tools"]["python"] == {
                    "path": "/python/bin/python3.12", "sha256": NOBLE_PYTHON_SHA256},
                    "Unexpected Pair25 Noble Python tool")
            require(toolchain["distributions"]["swift_toolchain"] == {
                "path": "/", "sha256": manifest.removeprefix("sha256:")},
                "Pair25 toolchain is not bound to the pinned Swift image")
            del mac["android"]["toolchain"]
            require(mac == linux, "Linux lock changes fields beyond android.toolchain")
            pinned(project + "Generated/MixerAndroid/android-build.py", pins["rendered_driver_sha256"])
            for relative in ("Platforms/Android/Package.resolved", "Generated/MixerSDK/Package.resolved"):
                pinned(project + relative, pins["platform_lock_sha256"])
            pinned("recipe/worker.py", worker_sha)
            for field in ("tools", "metadata"):
                for entry in toolchain[field].values():
                    if entry["path"].startswith(("/python/", "/android-sdk/")):
                        pinned(entry["path"][1:], entry["sha256"], executable=field == "tools")
            for package in ("swift-asn1", "swift-crypto"):
                mirror = f"mirrors/{package}.git"
                directory(mirror)
                directory(f"{mirror}/objects")
                for name in ("HEAD", "config"):
                    files[f"{mirror}/{name}"] = stamp(checked_path(root / mirror / name, stat.S_IFREG))
            require(os.readlink(root / "lib64" / LOADER) == f"/lib/x86_64-linux-gnu/{LOADER}",
                    "Unexpected Pair25 x86 compatibility loader link")
            for name in (LOADER, "libc.so.6"):
                relative = f"glibc/{name}"
                files[relative] = stamp(checked_path(root / relative, stat.S_IFREG))
        except (OSError, TypeError, KeyError, AttributeError, UnicodeError, json.JSONDecodeError) as error:
            raise LayoutError("Cannot admit the Pair25 stage") from error
        return cls(root, pins["source_tree_sha256"], pins["linux_lock_sha256"],
                   pins["rendered_driver_sha256"], tuple(directories.items()), tuple(files.items()), projection_sha)

    @property
    def image(self):
        return f"docker.io/library/swift@{self.image_ids[0]}"

    @property
    def image_ids(self):
        return IMAGE_IDS if self.projection_sha256 is None else NOBLE_IMAGE_IDS

    @property
    def launch_environment(self):
        return {"PAIR25_VERIFIED_SWIFT_MANIFEST": self.image_ids[0], **dict(ENV)}

    @property
    def verified_inputs(self):
        return {"source_tree_sha256": self.source_tree_sha256, "linux_lock_sha256": self.linux_lock_sha256,
                "rendered_driver_sha256": self.rendered_driver_sha256}

    @property
    def volume_name(self):
        return "mixer-pair25-" + hashlib.sha256(os.fsencode(self.root)).hexdigest()

    @property
    def volume_labels(self):
        labels = {"mixer.pair25.stage": str(self.root), "mixer.pair25.lock": self.linux_lock_sha256}
        if self.projection_sha256 is not None:
            return labels | {"mixer.pair25.projection": self.projection_sha256}
        return labels | {"mixer.pair25.receipt": RECEIPT_SHA256, "mixer.pair25.products": PRODUCTS_RECEIPT_SHA256}

    def recheck_stage(self):
        """Cheap pre-create/pre-start check against the admitted immutable stage."""
        private_directory(self.root)
        private_directory(self.root / "outputs")
        for relative, identity in self.stage_directories:
            info = checked_path(self.root / relative, stat.S_IFDIR)
            require((info.st_dev, info.st_ino) == identity, f"Staged directory replaced at {relative}")
        for relative, identity in self.stage_files:
            require(stamp(checked_path(self.root / relative, stat.S_IFREG)) == identity,
                    f"Staged file changed at {relative}")
        try:
            link = os.readlink(self.root / "lib64" / LOADER)
        except OSError as error:
            raise LayoutError("Pair25 compatibility loader link is missing") from error
        require(link == f"/lib/x86_64-linux-gnu/{LOADER}", "Pair25 compatibility loader link changed")

    def output(self, container_name):
        require(re.fullmatch(r"mixer-l05-[0-9a-f]{64}", container_name), "Invalid managed container name")
        return self.root / "outputs" / container_name

    def volume_identity(self, inspect):
        """Compare and persist this identity across runner restarts and before start."""
        require(inspect.get("Name") == self.volume_name and inspect.get("Driver") == "local"
                and inspect.get("Scope") == "local" and inspect.get("Labels") == self.volume_labels
                and "Options" in inspect and inspect["Options"] in (None, {}), "Unexpected Pair25 volume")
        mountpoint, created = inspect.get("Mountpoint"), inspect.get("CreatedAt")
        require(type(mountpoint) is str and type(created) is str and bool(created), "Missing volume identity")
        path = Path(mountpoint)
        require(path_text(path) == mountpoint and ".." not in path.parts
                and path.parts[-3:] == ("volumes", self.volume_name, "_data"), "Unexpected volume mountpoint")
        return mountpoint, created

    def verify_recipe(self, recipe):
        require(recipe.image == self.image and recipe.image_id in self.image_ids and recipe.platform == PLATFORM
                and recipe.entrypoint == ENTRYPOINT and recipe.arguments == ARGUMENTS, "Unexpected Pair25 recipe")

    def create_arguments(self, container_name):
        """Fixed Docker create suffix, from --tmpfs through the build argument."""
        output = self.output(container_name)
        info = checked_path(output, stat.S_IFDIR)
        require(info.st_uid == os.getuid(), "Operation output is not operator-owned")
        flags = []
        for target, options in TMPFS:
            flags.extend(("--tmpfs", f"{target}:{options}"))
        flags.extend(("--user", GUEST_USER))
        for relative, target in BIND_INPUTS:
            flags.extend(("--mount", f"type=bind,source={path_text(self.root / relative)},target={target},"
                                     "bind-recursive=disabled,readonly"))
        flags.extend(("--mount", f"type=volume,source={self.volume_name},target={TOOLCHAIN_TARGET},"
                                 "readonly,volume-nocopy"))
        flags.extend(("--mount", f"type=bind,source={path_text(output)},target={OUTPUT_TARGET},"
                                 "bind-recursive=disabled"))
        for name, value in self.launch_environment.items():
            flags.extend(("--env", f"{name}={value}"))
        return (*flags, "--entrypoint", ENTRYPOINT, self.image, *ARGUMENTS)

    def verify_container(self, inspect, container_name, volume_identity, image_env):
        """Check the Pair25-specific part of the exact container inspect result."""
        config, host = inspect["Config"], inspect["HostConfig"]
        require(config.get("Entrypoint") == [ENTRYPOINT] and config.get("Cmd") == list(ARGUMENTS)
                and config.get("User") == GUEST_USER and host.get("Tmpfs") == dict(TMPFS)
                and environment(config.get("Env")) == (environment(image_env) | self.launch_environment),
                "Pair25 container launch settings differ")
        expected = {target: ("bind", str(self.root / relative), False, "", "")
                    for relative, target in BIND_INPUTS}
        expected[TOOLCHAIN_TARGET] = ("volume", volume_identity[0], False, self.volume_name, "local")
        output = str(self.output(container_name))
        # Docker Desktop rewrites the writable host bind into its VM share.
        # Both inspect views must identify the same exact operation path.
        if sys.platform == "darwin" and any(
            mount.get("Destination") == OUTPUT_TARGET and mount.get("Source") == "/host_mnt" + output
            for mount in inspect["Mounts"]
        ):
            output = "/host_mnt" + output
        expected[OUTPUT_TARGET] = ("bind", output, True, "", "")
        actual = {}
        for mount in inspect["Mounts"]:
            target = mount["Destination"]
            require(target not in actual and type(mount["RW"]) is bool, "Invalid Pair25 mount readback")
            actual[target] = (mount["Type"], mount["Source"], mount["RW"],
                              mount.get("Name") or "", mount.get("Driver") or "")
        require(actual == expected, "Pair25 container mounts differ")

        requested = {}
        for mount in host["Mounts"]:
            target = mount["Target"]
            require(target in expected and target not in requested, "Unexpected Pair25 mount request")
            kind, source, writable, name, _ = expected[target]
            require(mount["Type"] == kind and mount["Source"] == (name or source)
                    and mount.get("ReadOnly", False) is (not writable), "Pair25 mount request differs")
            if kind == "bind":
                options = mount["BindOptions"]
                require(options.get("NonRecursive") is True and options.get("Propagation", "") in ("", "rprivate")
                        and not any(options.get(key) for key in (
                            "CreateMountpoint", "ReadOnlyNonRecursive", "ReadOnlyForceRecursive")),
                        "Pair25 bind options differ")
            else:
                require(mount["VolumeOptions"] == {"NoCopy": True}, "Pair25 volume options differ")
            requested[target] = True
        require(requested.keys() == expected.keys() and not host.get("Binds") and not host.get("VolumesFrom"),
                "Unexpected Pair25 mount requests")
