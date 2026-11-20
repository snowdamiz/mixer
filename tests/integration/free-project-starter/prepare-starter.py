#!/usr/bin/env python3
"""Trusted local operator preparation. Verifies data without starting a worker."""
import io
import json
import os
import secrets
from pathlib import Path
import shutil
import stat
import sys
import tarfile
from tempfile import TemporaryDirectory


# Match sdk/Package.resolved and THIRD_PARTY.yml. Archive digests come from the
# pinned offline FieldLog task-calculation assembly.
DEPENDENCIES = {
    "swift-crypto": ("5.0.3", "c2cbadd7263439d8015189668f96ff5b5be565ce",
                     "29f9386217ba7db19af241148c4663c3ba55b71e8c3e904c7bbad5847253fe92"),
    "swift-asn1": ("1.7.3", "3b6410f7dee09eb33cdd26260c5fd47fda19b0e2",
                   "29dce20ab0de9ccd21374fc4ca6567ad63290b88ff48fc3ec33f38615bdbb68f"),
}
UPSTREAM_SDK_SHA256 = "2b993bd3aa66ba1a8e2e0bd50708e5c1148fafd502f83f8dc1b0ed339c65af35"


def inventory(root, digest):
    files = {}
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(parent) / name
            info = path.lstat()
            if not (stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1)):
                raise ValueError("source contains an unsupported entry")
            if stat.S_ISREG(info.st_mode):
                files[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return files


def replace_once(path, old, new):
    raw = path.read_bytes()
    if raw.count(old) != 1:
        raise ValueError(f"unexpected manifest at {path}")
    path.write_bytes(raw.replace(old, new))


def assemble_local_sdk(destination, upstream, archives):
    _, digest, _ = worker_api()
    from starter_package_closure import SDK_SHA256, tree_digest

    if destination.exists() or destination.is_symlink():
        raise ValueError("local SDK destination already exists")
    with TemporaryDirectory(prefix=".starter-sdk-", dir=destination.parent) as staging:
        sdk = Path(staging) / "sdk"
        if tree_digest(inventory(upstream, digest)) != UPSTREAM_SDK_SHA256:
            raise ValueError("unexpected upstream SDK")
        shutil.copytree(upstream, sdk)
        if tree_digest(inventory(sdk, digest)) != UPSTREAM_SDK_SHA256:
            raise ValueError("upstream SDK changed during copy")
        lock = sdk / "Package.resolved"
        expected = [
            {"identity": name, "kind": "remoteSourceControl", "location": f"https://github.com/apple/{name}.git",
             "state": {"version": version, "revision": revision}}
            for name, (version, revision, _) in sorted(DEPENDENCIES.items())
        ]
        if json.loads(lock.read_bytes())["pins"] != expected:
            raise ValueError("unexpected SDK package pins")

        for name, (_, _, expected_sha) in DEPENDENCIES.items():
            with (archives / f"{name}.tar").open("rb") as handle:
                raw = handle.read(42 * 1024 * 1024)
            if digest(raw) != expected_sha:
                raise ValueError(f"unexpected {name} pinned archive")
            package = sdk / "Dependencies" / name
            package.mkdir(parents=True)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
                # SwiftPM builds these dependency products without upstream
                # test vectors, benchmarks, or their separate manifests.
                members = [entry for entry in archive
                           if entry.name.partition("/")[0] in {"Package.swift", "Sources", "LICENSE.txt", "NOTICE.txt"}]
                archive.extractall(package, members=members, filter="data")

        replace_once(sdk / "Package.swift",
                     b'.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")',
                     b'.package(path: "Dependencies/swift-crypto")')
        replace_once(sdk / "Dependencies/swift-crypto/Package.swift", b'''// Switch between local and remote dependencies depending on an environment variable
if ProcessInfo.processInfo.environment["SWIFTCI_USE_LOCAL_DEPS"] == nil {
    package.dependencies += [
        .package(url: "https://github.com/apple/swift-asn1.git", from: "1.2.0")
    ]
} else {
    package.dependencies += [
        .package(path: "../swift-asn1")
    ]
}

''', b'package.dependencies += [.package(path: "../swift-asn1")]\n\n')
        lock.unlink()
        if tree_digest(inventory(sdk, digest)) != SDK_SHA256:
            raise ValueError("derived SDK does not match the admitted package closure")
        sdk.rename(destination)


def write_private(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
    path.chmod(0o400)


def worker_api():
    worker = Path(os.environ.get("MIXER_STARTER_WORKER_CODE", "priv/development")).resolve(strict=True)
    sys.path.insert(0, str(worker))
    from native_artifact_worker import NativeWorker, digest, literal
    return NativeWorker, digest, literal


def complete_export(root):
    _, digest, _ = worker_api()
    from starter_package_closure import check_starter_inputs, tree_digest

    # The retaining CLI writes this file before computing its source binding.
    # Supply the exact same bytes before registration so both digests include it.
    relative = "Platforms/iOS/Starter.xcodeproj/project.xcworkspace/contents.xcworkspacedata"
    raw = (b'<?xml version="1.0" encoding="UTF-8"?>\n'
           b'<Workspace version="1.0"><FileRef location="self:"></FileRef></Workspace>\n')
    files = inventory(root, digest)
    needs_workspace = relative not in files
    if needs_workspace:
        files[relative] = digest(raw)
    check_starter_inputs(files, (root / "mixer.lock").read_bytes())
    if needs_workspace:
        workspace = root / relative
        workspace.parent.mkdir(exist_ok=True)
        write_private(workspace, raw)
    print(tree_digest(files))


def admit_worker(destination, config_path, startup_pin, dispatch_id, dispatch_port):
    native_worker, digest, literal = worker_api()
    import starter_package_closure as starter
    startup_bytes = config_path.read_bytes()
    if digest(startup_bytes) != startup_pin:
        raise SystemExit("worker startup configuration pin mismatch")
    config = json.loads(startup_bytes)
    if config.get("worker_id") != dispatch_id or config.get("port") != dispatch_port:
        raise SystemExit("worker startup configuration does not match dispatch target")
    if not isinstance(config.get("token"), str) or len(config["token"]) < 32:
        raise SystemExit("invalid worker startup token shape")

    grant = config["registration"]
    spec = grant["spec"]
    files = grant["files"]
    root = Path(grant["root"])
    expected_tree = os.environ.get("MIXER_STARTER_EXPORT_SHA256")
    if expected_tree is not None and spec["source"]["sha256"] != expected_tree:
        raise SystemExit("worker startup source does not match the CLI export digest")

    # Exercise the existing worker verifier without constructing state or running commands.
    verifier = object.__new__(native_worker)
    verifier.config = config
    recipe = verifier.verify(spec)
    if spec["platform"] == "android":
        if starter.KEY in config["policy"]:
            raise SystemExit("iOS package closure does not apply to an Android registration")
    elif recipe.get(starter.KEY) != starter.VERSION:
        raise SystemExit("starter package closure is required")

    worker = {"configuration_sha256": startup_pin, "id": dispatch_id, "port": dispatch_port}
    descriptor = {key: config[key] for key in ("tenant", "registration", "policy")}
    descriptor["worker"] = worker
    raw = literal(descriptor).encode()
    write_private(destination, raw)
    pin = digest(raw)
    print(literal({"id": "starter-" + pin, "pin": pin, "spec": spec, "worker": worker,
                   "files": len(files), "source_bytes": sum((root / name).stat().st_size for name in files)}))


def fixture(destination, root, cli, org, project, app):
    root = Path(root).resolve(strict=True)
    cli = Path(cli).resolve(strict=True)
    recipe = destination.with_suffix(".recipe.json")
    _, digest, literal = worker_api()
    import starter_package_closure as starter

    files = inventory(root, digest)
    starter.check_starter_inputs(files, (root / "mixer.lock").read_bytes())
    tree = starter.tree_digest(files)
    expected_tree = os.environ.get("MIXER_STARTER_EXPORT_SHA256")
    if expected_tree is not None and tree != expected_tree:
        raise SystemExit("export bytes differ from the CLI digest")

    tool_paths = (str(cli), "/usr/bin/xcodebuild")
    tools = {name: digest(Path(name).read_bytes()) for name in tool_paths}
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    recipe_bytes = literal({
        "argv": [str(cli), "build", "--platform", "ios", "--directory", str(root)],
        "cwd": str(root), "environment": environment,
        "profile": "unsigned-ios-simulator-v1",
        "package_policy": "exact-owned-local-manifests-no-external-packages",
        starter.KEY: starter.VERSION,
        "inputs": files, "tools": tools, "timeout_seconds": 1800,
    }).encode()
    definition = digest(recipe_bytes)
    spec = {
        "organization_id": org, "project_id": project, "application_id": app,
        "platform": "ios", "source": {
            "kind": "revision", "reference": os.environ.get("MIXER_STARTER_SOURCE_REFERENCE", "starter-" + tree),
            "sha256": tree,
        },
        "toolchain_lock_sha256": files["mixer.lock"], "build_definition_sha256": definition,
    }
    dispatch_id = os.environ["MIXER_STARTER_DISPATCH_ID"]
    dispatch_port = int(os.environ["MIXER_STARTER_DISPATCH_PORT"])
    config = {
        "tenant": org,
        "registration": {"root": str(root), "recipe": str(recipe), "spec": spec, "files": files},
        "policy": {"recipe_sha256": definition, "cli": str(cli), "environment": environment, starter.KEY: starter.VERSION,
                   "inputs": files, "tools": tools},
        "worker_id": dispatch_id, "port": dispatch_port, "token": secrets.token_hex(32),
    }
    write_private(recipe, recipe_bytes)
    startup = destination.with_suffix(".worker-startup.json")
    startup_bytes = literal(config).encode()
    write_private(startup, startup_bytes)
    for parent, _, names in os.walk(root, topdown=False):
        for name in names:
            (Path(parent) / name).chmod(0o400)
        Path(parent).chmod(0o500)
    admit_worker(destination, startup, digest(startup_bytes), dispatch_id, dispatch_port)


def main():
    args = sys.argv[1:]
    if len(args) == 4 and args[0] == "--local-sdk":
        _, destination, upstream, archives = args
        assemble_local_sdk(Path(destination).absolute(), Path(upstream), Path(archives))
    elif len(args) == 2 and args[0] == "--complete-export":
        complete_export(Path(args[1]).resolve(strict=True))
    elif len(args) == 6 and args[0] == "--from-worker":
        _, destination, startup, pin, worker_id, port = args
        admit_worker(Path(destination), Path(startup), pin, worker_id, int(port))
    elif len(args) == 6:
        destination, root, cli, org, project, app = args
        fixture(Path(destination).absolute(), root, cli, org, project, app)
    else:
        raise SystemExit(
            "usage: prepare-starter.py --local-sdk DESTINATION PINNED_SDK ARCHIVES\n"
            "       prepare-starter.py --complete-export ROOT\n"
            "       prepare-starter.py --from-worker DESCRIPTOR STARTUP_CONFIG SHA256 WORKER_ID PORT"
        )


if __name__ == "__main__":
    main()
