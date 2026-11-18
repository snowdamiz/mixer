#!/usr/bin/env python3
"""Trusted local operator preparation. Verifies data without starting a worker."""
import json
import os
import secrets
from pathlib import Path
import stat
import sys


def write_private(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)
    path.chmod(0o400)


def worker_api():
    worker = Path(os.environ.get("MIXER_STARTER_WORKER_CODE", "priv/development")).resolve(strict=True)
    sys.path.insert(0, str(worker))
    from native_artifact_worker import NativeWorker, digest, literal
    return NativeWorker, digest, literal


def admit_worker(destination, config_path, startup_pin, dispatch_id, dispatch_port):
    native_worker, digest, literal = worker_api()
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
    verifier.verify(spec)

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

    files = {}
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in directories + names:
            path = Path(parent) / name
            info = path.lstat()
            if not (stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1)):
                raise SystemExit("export contains an unsupported entry")
            if stat.S_ISREG(info.st_mode):
                files[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    tree = digest("".join(name + "\0" + sha + "\n" for name, sha in sorted(files.items())).encode())
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
        "policy": {"recipe_sha256": definition, "cli": str(cli), "environment": environment,
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
    if len(args) == 6 and args[0] == "--from-worker":
        _, destination, startup, pin, worker_id, port = args
        admit_worker(Path(destination), Path(startup), pin, worker_id, int(port))
    elif len(args) == 6:
        destination, root, cli, org, project, app = args
        fixture(Path(destination).absolute(), root, cli, org, project, app)
    else:
        raise SystemExit("usage: prepare-starter.py --from-worker DESCRIPTOR STARTUP_CONFIG SHA256 WORKER_ID PORT")


if __name__ == "__main__":
    main()
