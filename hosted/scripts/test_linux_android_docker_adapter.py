from contextlib import closing, contextmanager
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import os
import queue
import secrets
import shutil
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "priv" / "development"))
from compiler_worker import Refusal, digest, literal
from linux_android_docker_adapter import DockerContainerAdapter, open_docker_runner, rename_bundle, write_owned
from linux_android_runner import TERMINAL, VERSION, LinuxAndroidRunnerClient
from native_artifact_worker import ANDROID_DRIVER, mac, serve
from test_linux_android_artifact_importer import RECEIPT, RECEIPT_SHA


# A direct CLI process with no descendants. Its inventory outlives its calls
# and the runner, modeling separately persisted daemon state.
DOCKER_FIXTURE = '''
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import time

root = Path(__file__).parent
state_path = root / "state.json"
state = json.loads(state_path.read_text())
prefix, args = sys.argv[1:5], sys.argv[5:]
with (root / "commands.jsonl").open("a") as log:
    log.write(json.dumps([*prefix, *args]) + "\\n")
if prefix != ["--config", str(root / "runner"), "--host", "unix://" + str(root / "fixture.sock")]:
    sys.exit(90)

recipe = state["recipe"]
mode = state["mode"]
containers = state["containers"]

def save():
    state_path.write_text(json.dumps(state))

def pid_state(status, pid):
    return {"Status": status, "Running": pid > 0, "Pid": pid,
            "Paused": False, "Restarting": False, "Dead": False}

if args == ["info", "--format", "{{.ID}}"]:
    print(state["daemon"])
elif args == ["image", "inspect", "--platform", recipe["platform"], recipe["image"]]:
    print(json.dumps([{"Id": recipe["image_id"], "Os": "linux", "Architecture": "arm64",
                       "Descriptor": {"digest": recipe["image"].split("@")[1]},
                       "Config": {"Volumes": {"/unexpected": {}} if mode == "volume-image" else None,
                                  "Env": state.get("image_env")}}]))
elif args[:2] == ["volume", "inspect"]:
    volume = state.get("volume")
    if not volume or args != ["volume", "inspect", volume["Name"]]:
        sys.exit(101)
    print(json.dumps([volume]))
elif args[:2] == ["container", "create"]:
    name = args[args.index("--name") + 1]
    cid = hashlib.sha256(name.encode()).hexdigest()
    if cid in containers:
        sys.exit(91)
    image_index = args.index(recipe["image"])
    labels = dict(args[index + 1].split("=", 1) for index, arg in enumerate(args) if arg == "--label")
    mounts, requests = [], []
    for index, arg in enumerate(args):
        if arg == "--mount":
            parts = args[index + 1].split(",")
            fields = dict(part.split("=", 1) for part in parts if "=" in part)
            kind, source, target = (fields[key] for key in ("type", "source", "target"))
            readonly = "readonly" in parts
            request = {"Type": kind, "Source": source, "Target": target, "ReadOnly": readonly}
            mount = {"Type": kind, "Source": source, "Destination": target, "RW": not readonly}
            if kind == "volume":
                volume = state["volume"]
                if source != volume["Name"]:
                    sys.exit(102)
                mount.update(Source=volume["Mountpoint"], Name=source, Driver=volume["Driver"])
                request["VolumeOptions"] = {"NoCopy": "volume-nocopy" in parts}
            else:
                request["BindOptions"] = {"NonRecursive": fields.get("bind-recursive") == "disabled"}
            mounts.append(mount)
            requests.append(request)
    env = dict(row.split("=", 1) for row in (state.get("image_env") or ()))
    env.update(args[index + 1].split("=", 1) for index, arg in enumerate(args) if arg == "--env")
    tmpfs = dict(args[index + 1].split(":", 1) for index, arg in enumerate(args) if arg == "--tmpfs")
    containers[cid] = {
        "Id": cid, "Name": "/" + name, "Platform": "linux", "Image": recipe["image_id"],
        "ImageManifestDescriptor": {"digest": recipe["image"].split("@")[1]},
        "Config": {"Labels": labels, "Image": args[image_index], "Cmd": args[image_index + 1:],
                   "Env": [f"{name}={value}" for name, value in env.items()],
                   "Entrypoint": [args[args.index("--entrypoint") + 1]], "User": args[args.index("--user") + 1]},
        "HostConfig": {"NetworkMode": args[args.index("--network") + 1], "Privileged": "--privileged" in args,
                       "PidMode": "", "IpcMode": args[args.index("--ipc") + 1],
                       "ReadonlyRootfs": "--read-only" in args, "AutoRemove": "--rm" in args,
                       "RestartPolicy": {"Name": args[args.index("--restart") + 1]},
                       "Mounts": requests, "Tmpfs": tmpfs},
        "Mounts": mounts, "State": pid_state("created", 0),
    }
    if mode == "unacknowledged-create":
        state["pending"] = containers.pop(cid)
        save()
        # The CLI will time out while an independently persisted intent exists.
        time.sleep(5)
    save()
    if mode == "socket-replaced-after-create":
        endpoint = root / "fixture.sock"
        endpoint.rename(root / "old-fixture.sock")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as replacement:
            replacement.bind(str(endpoint))
    print(cid if mode != "malformed-create" else cid[:12])
elif args[:2] == ["container", "ls"]:
    cid = args[-1].removeprefix("id=")
    if args[2:] != ["--all", "--quiet", "--no-trunc", "--filter", "id=" + cid]:
        sys.exit(92)
    if mode == "missing-absence":
        sys.exit(93)
    if cid in containers:
        print(cid)
elif args[:1] == ["container"] and args[-1] in containers:
    cid = args[-1]
    container = containers[cid]
    if args[1] == "inspect":
        if mode == "missing-created" or (mode == "missing-terminal" and container["State"]["Status"] == "exited"):
            sys.exit(94)
        print(json.dumps([container]))
    elif args[1] == "start":
        if container["State"]["Status"] != "created":
            sys.exit(95)
        if mode == "start-pending":
            sys.exit(96)
        container["State"] = pid_state("running", 1234)
        output = Path(next(m["Source"] for m in container["Mounts"] if m["Destination"] in ("/output", "/deliver")))
        if state.get("volume") is None:
            (output / "nested").mkdir(mode=0o700)
            (output / "nested" / "fixture-artifact").write_text("fixture output")
        if state.get("products") is not None:
            source = Path(state["products"])
            target = output
            if mode == "unrelated-output":
                target = root / "unrelated-output"
                target.mkdir(mode=0o700)
            for item in source.iterdir():
                shutil.copyfile(item, target / item.name)
                (target / item.name).chmod(0o600)
        if mode == "exit-on-start":
            container["State"] = dict(pid_state("exited", 0), ExitCode=0, OOMKilled=False, Error="")
        save()
        if mode == "lost-start-ack":
            sys.exit(97)
        print(cid)
    elif args[1] == "stop" and args[2:-1] == ["--time", "0"]:
        container["State"] = pid_state("exited", 0)
        save()
        print(cid)
    elif args[1] == "rm" and args[2:] == [cid] and container["State"]["Pid"] == 0:
        del containers[cid]
        save()
        if mode == "timeout-remove":
            time.sleep(5)
        if mode == "lost-remove-ack":
            sys.exit(98)
        print(cid)
    else:
        sys.exit(99)
else:
    sys.exit(100)
'''


class DockerContainerAdapterTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="dk-")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.runner, self.outputs, self.inputs = (self.root / name for name in ("runner", "outputs", "inputs"))
        for path in (self.runner, self.inputs, self.outputs):
            path.mkdir(mode=0o700)
        self.input_file = self.inputs / "project"
        self.input_file.write_text("immutable fixture inputs")
        self.bundle = self.root / "published"
        self.driver = self.inputs / "Export" / ANDROID_DRIVER
        self.recipe = {
            "image": "example.test/mixer/android@sha256:" + "a" * 64,
            "image_id": "sha256:" + "b" * 64, "platform": "linux/arm64",
            "entrypoint": "/bin/worker", "arguments": ["build", "literal ; argument", "--guest-flag"],
        }
        self.manifest = self.root / "recipe.json"
        self.manifest.write_text(json.dumps(self.recipe))
        self.recipe_sha = hashlib.sha256(self.manifest.read_bytes()).hexdigest()
        self.state_file = self.root / "state.json"
        self.state_file.write_text(json.dumps({"recipe": self.recipe, "daemon": "fixture-daemon",
                                              "mode": "normal", "containers": {}}))
        self.docker = self.root / "fixture-docker"
        self.docker.write_text(f"#!{sys.executable}\n" + DOCKER_FIXTURE)
        self.docker.chmod(0o700)
        self.daemon_socket = self.root / "fixture.sock"
        daemon = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(daemon.close)
        daemon.bind(str(self.daemon_socket))
        self.endpoint = self.runner / "runner.sock"
        self.options = {
            "recipe_sha256": self.recipe_sha, "store_id": "d" * 64, "manifest": self.manifest,
            "docker": self.docker, "daemon_socket": self.daemon_socket, "daemon_id": "fixture-daemon",
            "inputs": self.inputs, "outputs": self.outputs, "command_timeout": 0.35,
        }
        self.client = LinuxAndroidRunnerClient(self.endpoint, recipe_sha256=self.recipe_sha, store_id="d" * 64)
        now = time.time_ns() // 1_000_000
        self.first, self.second = (self.client.operation({
            "operation_id": digit * 64, "spec": {"platform": "android", "build_definition_sha256": self.recipe_sha},
            "ref": {"build_id": digit}, "deadline_ms": now + 60_000,
            "guard": {"record_id": digit, "owner_id": "fixture", "epoch": 1, "revision": 0, "expires_at": now + 60_000},
        }) for digit in ("1", "2"))

    @contextmanager
    def listener(self, *, initialize=False):
        ready, errors = queue.Queue(), []
        done = threading.Event()

        def serve():
            try:
                with open_docker_runner(self.runner, initialize=initialize, **self.options) as server:
                    ready.put(True)
                    while not done.is_set():
                        server.serve_one()
            except Exception as error:
                errors.append(error)
                ready.put(False)

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        try:
            if not ready.get(timeout=3):
                raise errors[0]
            yield
        finally:
            done.set()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as wake:
                wake.settimeout(0.2)
                try:
                    wake.connect(str(self.endpoint))
                except FileNotFoundError:
                    pass
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            if errors:
                raise errors[0]

    @contextmanager
    def worker_listener(self, spec, imports=None):
        config = {"worker_id": "native", "token": "fixture" * 5, "tenant": spec["organization_id"],
                  "registration": {"spec": spec, "files": {}}, "port": 0}
        if imports is not None:
            config["linux_artifact_imports"] = imports
        ready = queue.Queue()
        activate = socketserver.TCPServer.server_activate

        def record_listener(server):
            activate(server)
            ready.put(server)

        def run():
            serve(config, str(self.root / "worker-state"), linux_runner=self.client)

        def call(action, request=None):
            body = literal({"worker_id": config["worker_id"], "action": action, "request": request})
            nonce = secrets.token_hex(16)
            envelope = {"body": body, "nonce": nonce, "mac": mac(config["token"], "request", nonce, body)}
            with socket.create_connection(server.server_address, timeout=3) as connection:
                with connection.makefile("rb") as stream:
                    connection.sendall((literal(envelope) + "\n").encode())
                    reply = json.loads(stream.readline())
            self.assertEqual(reply["mac"], mac(config["token"], "response", nonce, reply["body"]))
            return json.loads(reply["body"])

        worker = threading.Thread(target=run, daemon=True)
        with patch.object(socketserver.TCPServer, "server_activate", record_listener):
            worker.start()
            server = ready.get(timeout=3)
        try:
            yield call
        finally:
            try:
                self.assertEqual(call("shutdown"), {"status": "closed"})
            finally:
                server.closed = True
                worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
            self.assertEqual(server.socket.fileno(), -1)

    def state(self):
        return json.loads(self.state_file.read_text())

    def set_state(self, **changes):
        self.state_file.write_text(json.dumps(self.state() | changes))

    def commands(self):
        log = self.root / "commands.jsonl"
        return [json.loads(line)[4:] for line in log.read_text().splitlines()] if log.exists() else []

    def mutations(self):
        return [command for command in self.commands()
                if command[:1] == ["container"] and command[1] in ("create", "start", "stop", "rm")]

    def status(self, action, operation, expected):
        result = self.client.observe(action, operation)
        self.assertEqual(result["status"], expected)
        if expected == "stopped":
            self.assertEqual(result["terminal"], TERMINAL)

    def uncertain(self, action, operation):
        with self.assertRaisesRegex(Refusal, "^uncertain$"):
            self.client.observe(action, operation)

    def bundle_fixture(self, *, lock=b"lock fixture", driver=b"fixture rendered driver",
                       source_tree=None, apk_name="Fixture-unsigned.apk"):
        bundle = self.root / "fixture-products"
        bundle.mkdir(mode=0o700)
        apk, symbols = b"unsigned apk fixture", b"symbols fixture"
        inputs = dict(source_tree_sha256=source_tree or digest(b"fixture source tree"), linux_lock_sha256=digest(lock),
                      rendered_driver_sha256=digest(driver))
        inventory = literal(dict(formatVersion=1, apkSHA256=digest(apk), debugSymbolsSHA256=digest(symbols))).encode()
        artifacts = []
        for kind, name, payload in (
            ("unsigned_native_binary", apk_name, apk),
            ("debug_symbols", "debug-symbols.zip", symbols),
            ("resource_inventory", "resource-inventory.json", inventory),
        ):
            (bundle / name).write_bytes(payload)
            artifacts.append(dict(kind=kind, file=name, sha256=digest(payload), sizeBytes=len(payload)))
        (bundle / "linux-mixer.lock").write_bytes(lock)
        source = inputs["source_tree_sha256"]
        index = literal(dict(unsigned=True, zipCRCVerified=True, artifacts=artifacts,
                             build=dict(source_tree_sha256=source, source_tree_after_sha256=source,
                                        apk_sha256=digest(apk), apk_bytes=len(apk)))).encode()
        (bundle / "readback.json").write_bytes(index)
        return bundle, inputs, digest(index), artifacts

    def completion_fixture(self, source, inputs, driver=b"fixture rendered driver", *, stage=True):
        scope = dict(organization_id="organization", project_id="project", application_id="application",
                     platform="android")
        spec = dict(scope, source={"sha256": inputs["source_tree_sha256"]},
                    toolchain_lock_sha256=inputs["linux_lock_sha256"], build_definition_sha256=self.recipe_sha)
        request = dict(operation_id=self.first.identity.operation_id, spec=dict(spec, build_id="build"),
                       ref=dict(scope, build_id="build", fence=1, attempt=1),
                       deadline_ms=self.first.deadline_ms, guard=asdict(self.first.guard))
        operation = self.client.operation(request)
        grant = dict(identity=asdict(operation.identity), bundle=str(self.bundle), inputs=inputs)
        imports = {request["operation_id"]: grant}
        self.options["completions"] = imports
        if stage:
            self.driver.parent.mkdir(parents=True)
            self.assertEqual(inputs["rendered_driver_sha256"], digest(driver))
            self.driver.write_bytes(driver)
            shutil.copyfile(source / "linux-mixer.lock", self.inputs / "linux-mixer.lock")
        self.set_state(products=str(source))
        return operation, request, spec, imports

    def exit_fixture(self, **state):
        containers = self.state()["containers"]
        [(cid, container)] = containers.items()
        self.assertEqual("running", container["State"]["Status"])
        container["State"].update(
            dict(Status="exited", Running=False, Pid=0, ExitCode=0, OOMKilled=False, Error="") | state,
        )
        self.set_state(containers=containers)
        return cid

    def assert_completed(self, action, operation, inputs, readback):
        request = {"version": VERSION, "action": action, **asdict(operation)}
        self.assertEqual(self.client._exchange(request), {
            "request": request, "status": "completed", "terminal": {
                "inputs": inputs, "readback_sha256": readback, "exit_code": 0,
                "start_fenced": True, "container_absent": True, "processes_absent": True,
                "resources_removed": True,
            },
        })

    def assert_unpublished(self, operation):
        directory = self.root / "worker-state" / operation.identity.operation_id
        self.assertFalse(directory.exists())
        with closing(sqlite3.connect(self.runner / "operations.sqlite")) as db:
            row = db.execute("SELECT completed FROM operation WHERE id = ?", (operation.identity.operation_id,))
            self.assertEqual([(0,)], row.fetchall())

    def publish_and_reopen(self, source, inputs, readback, artifacts, *, fast_exit=False, driver=None):
        args = () if driver is None else (driver,)
        operation, request, spec, imports = self.completion_fixture(source, inputs, *args)
        if fast_exit:
            self.set_state(mode="exit-on-start")
        rows = [{k: v for k, v in record.items() if k != "file"} for record in artifacts]
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.status("query", operation, "absent")
            self.assertEqual([], self.mutations())
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            if not fast_exit:
                cid = self.exit_fixture()
                original = self.state()["containers"][cid]
                mounts = [mount if mount["Destination"] != "/output" else mount | {"Source": str(source)}
                          for mount in original["Mounts"]]
                self.set_state(containers={cid: original | {"Mounts": mounts}})
                self.assertEqual({"error": "uncertain"}, call("query", request))
                self.assert_unpublished(operation)
                self.assertFalse(self.bundle.exists())
                self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
                self.set_state(containers={cid: original})
            self.assertEqual({"status": "running"}, call("query", request))
            self.assertEqual(rows, call("artifacts", request)["artifacts"])
            self.assert_completed("query", operation, inputs, readback)
        self.assertEqual({"readback.json", "linux-mixer.lock", *(row["file"] for row in artifacts)},
                         {file.name for file in self.bundle.iterdir()})
        for file in self.bundle.iterdir():
            self.assertEqual(digest((source / file.name).read_bytes()), digest(file.read_bytes()))
            self.assertEqual(0o400, file.stat().st_mode & 0o777)
        self.assertEqual({}, self.state()["containers"])
        self.assertEqual([], list(self.outputs.iterdir()))
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])
        commands = self.commands()
        with self.listener(), self.worker_listener(spec, imports) as call:
            self.assert_completed("ensure_started", operation, inputs, readback)
            self.assertEqual(rows, call("artifacts", request)["artifacts"])
            self.assertEqual(commands, self.commands())
            self.set_state(mode="normal", products=None)
            self.status("ensure_started", self.second, "running")
            commands = self.commands()
            self.assertEqual("stopped", call("stop", request)["status"])
            self.assertEqual({"error": "unavailable"}, call("artifacts", request))
            self.status("ensure_started", operation, "stopped")
            self.assertEqual(commands, self.commands())
            self.status("stop", self.second, "stopped")

    def test_completed_fast_exit_publishes_and_reopens_through_both_sockets(self):
        self.publish_and_reopen(*self.bundle_fixture(), fast_exit=True)

    def test_fresh_attempt_admits_a_grant_without_a_readback_digest(self):
        source, inputs, _, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(source, inputs)
        with self.listener(initialize=True):
            self.status("query", operation, "absent")
            self.assertFalse(self.bundle.exists())

    def test_fresh_attempt_refuses_existing_destination_and_mismatched_staged_inputs(self):
        source, inputs, _, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(source, inputs)
        shutil.copytree(source, self.bundle)
        with self.listener(initialize=True):
            self.uncertain("ensure_started", operation)
            self.assertEqual((source / "readback.json").read_bytes(), (self.bundle / "readback.json").read_bytes())
            self.assertEqual([], self.mutations())
            self.bundle.rename(self.root / "preexisting")
            for path in (self.driver, self.inputs / "linux-mixer.lock"):
                with self.subTest(path=path):
                    data = path.read_bytes()
                    path.write_bytes(b"wrong staged bytes")
                    self.uncertain("ensure_started", operation)
                    self.assertEqual([], self.mutations())
                    path.write_bytes(data)
            self.status("ensure_started", operation, "running")
            self.status("stop", operation, "stopped")
        self.assertFalse(self.bundle.exists())

    def test_unsafe_index_cannot_be_replaced_after_exit(self):
        source, inputs, _, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(source, inputs)
        with self.listener(initialize=True):
            self.status("ensure_started", operation, "running")
            [output] = self.outputs.iterdir()
            self.exit_fixture()
            path = output / "readback.json"
            index = json.loads(path.read_bytes())
            index["artifacts"][0]["file"] = "../Fixture-unsigned.apk"
            path.write_text(literal(index))
            self.uncertain("query", operation)

            path.write_bytes((source / path.name).read_bytes())
            self.uncertain("query", operation)
            self.assertFalse(self.bundle.exists())
            self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
            self.status("stop", operation, "stopped")

    def test_invalid_artifact_cannot_be_replaced_after_exit(self):
        source, inputs, _, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(source, inputs)
        with self.listener(initialize=True):
            self.status("ensure_started", operation, "running")
            [output] = self.outputs.iterdir()
            self.exit_fixture()
            artifact = output / "Fixture-unsigned.apk"
            data = artifact.read_bytes()
            artifact.write_bytes(b"X" * len(data))
            self.uncertain("query", operation)
            artifact.write_bytes(data)
            self.uncertain("query", operation)
            self.assert_unpublished(operation)
            self.assertFalse(self.bundle.exists())
            self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
            self.status("stop", operation, "stopped")
            self.assertFalse(list(self.bundle.parent.glob(".mixer-l05-*.pending")))

    def test_publish_never_replaces_an_empty_destination_and_recovers_after_rename(self):
        source, inputs, readback, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(source, inputs)

        def block_rename(parent, pending, final):
            os.mkdir(final, mode=0o700, dir_fd=parent)
            rename_bundle(parent, pending, final)

        def interrupt_after_rename(parent, pending, final):
            rename_bundle(parent, pending, final)
            raise OSError("interrupted after rename")

        with self.listener(initialize=True):
            self.status("ensure_started", operation, "running")
            self.exit_fixture()
            with patch("linux_android_docker_adapter.rename_bundle", side_effect=block_rename):
                self.uncertain("query", operation)
            self.assertEqual([], list(self.bundle.iterdir()))
            self.assertEqual({}, self.state()["containers"])
            self.assertEqual([], list(self.outputs.iterdir()))
            self.assert_unpublished(operation)
            self.bundle.rmdir()
        with self.listener():
            with patch("linux_android_docker_adapter.rename_bundle", side_effect=interrupt_after_rename):
                self.uncertain("query", operation)
            self.assert_unpublished(operation)
        with self.listener():
            self.assert_completed("query", operation, inputs, readback)
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])

    def pair25_fixture(self):
        payload = RECEIPT.read_bytes()
        self.assertEqual(RECEIPT_SHA, digest(payload))
        report = json.loads(payload)
        source = Path(os.environ["MIXER_PAIR25_BUNDLE"])
        inputs = dict(source_tree_sha256=report["build"]["source_tree_sha256"],
                      linux_lock_sha256=report["inputHashes"]["localLinuxLockSHA256"],
                      rendered_driver_sha256=report["inputHashes"]["renderedBuildDriverSHA256"])
        artifact_files = [row["file"] for row in report["artifacts"]]
        before = {name: digest((source / name).read_bytes())
                  for name in ["readback.json", "linux-mixer.lock", *artifact_files]}
        self.assertEqual(inputs["linux_lock_sha256"], before["linux-mixer.lock"])
        self.assertEqual(report["readbackChecks"]["readbackSHA256"], before["readback.json"])
        for row in report["artifacts"]:
            self.assertEqual(row["sha256"], before[row["file"]])

        def pinned_source(name):
            return subprocess.check_output(
                ["git", "show", f'{report["exportSource"]}:cli/Sources/MixerBuild/{name}'],
                cwd=RECEIPT.parents[2], timeout=3,
            )

        compat = pinned_source("AndroidSDKCompatibility.swift")
        profile = json.loads(compat.split(b'Data(#"""', 1)[1].split(b'"""#.utf8)', 1)[0])
        profile = (json.dumps(profile, sort_keys=True, indent=2, separators=(",", " : ")) + "\n").encode()
        driver = pinned_source("Resources/android-build.py").replace(
            b"__MIXER_ANDROID_SOURCE_PROFILE_HEX__", profile.hex().encode(),
        )
        return source, inputs, before, report["artifacts"], driver

    @unittest.skipUnless(os.environ.get("MIXER_PAIR25_BUNDLE"), "requires the operator's retained Pair25 bundle")
    def test_pair25_rejects_another_mount_then_publishes_and_reopens_through_both_sockets(self):
        source, inputs, before, artifacts, driver = self.pair25_fixture()
        self.publish_and_reopen(source, inputs, before["readback.json"], artifacts, driver=driver)
        self.assertEqual(before, {name: digest((source / name).read_bytes()) for name in before})

    @unittest.skipUnless(os.environ.get("MIXER_PAIR25_BUNDLE"), "requires the operator's retained Pair25 bundle")
    def test_pair25_products_in_unrelated_output_never_publish(self):
        source, inputs, before, _, driver = self.pair25_fixture()
        operation, request, spec, imports = self.completion_fixture(source, inputs, driver)
        self.set_state(mode="unrelated-output")
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            cid = self.exit_fixture()
            unrelated = self.root / "unrelated-output"
            self.assertEqual(before, {name: digest((unrelated / name).read_bytes()) for name in before})
            self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assert_unpublished(operation)
            self.assertFalse(self.bundle.exists())
            self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
            [output] = self.outputs.iterdir()
            for name in before:
                shutil.copyfile(unrelated / name, output / name)
            self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assertFalse(self.bundle.exists())
            self.assertEqual("stopped", call("stop", request)["status"])
            self.assertNotIn(cid, self.state()["containers"])
            self.assertTrue(unrelated.is_dir())

    def test_completion_requires_exact_success_and_stable_bundle(self):
        bundle, inputs, _, _ = self.bundle_fixture()
        operation, request, spec, imports = self.completion_fixture(bundle, inputs)
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            cid = self.exit_fixture()
            success = self.state()["containers"][cid]
            for changes in ({"ExitCode": 1}, {"ExitCode": False}, {"OOMKilled": True}, {"Error": "failed"}):
                with self.subTest(changes=changes):
                    self.set_state(containers={cid: success | {"State": success["State"] | changes}})
                    self.assertEqual({"error": "uncertain"}, call("query", request))
                    self.assertEqual({"error": "unavailable"}, call("artifacts", request))
                    self.assert_unpublished(operation)
            self.set_state(containers={cid: success | {"Id": "f" * 64}})
            self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
            self.set_state(containers={cid: success})
            newer = replace(operation, guard=replace(operation.guard, epoch=2, owner_id="new"))
            real_write = write_owned

            def interrupt_copy(path, data):
                if path.name == "debug-symbols.zip":
                    path.write_bytes(data[:3])
                    raise OSError("interrupted copy")
                real_write(path, data)

            with patch("linux_android_docker_adapter.write_owned", side_effect=interrupt_copy):
                self.uncertain("query", newer)
            self.assertEqual({"error": "uncertain"}, call("query", request))
            renewed = dict(request, guard=asdict(newer.guard))
            self.assertEqual({"error": "unavailable"}, call("artifacts", renewed))
            self.assert_unpublished(operation)
            self.assertFalse(self.bundle.exists())
            self.assertEqual(["create", "start"], [command[1] for command in self.mutations()])
        with self.listener(), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", renewed))
            self.assertEqual("native_ready", call("artifacts", renewed)["status"])
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])

    def test_completion_remove_timeout_preserves_unknown_across_restart(self):
        bundle, inputs, readback, _ = self.bundle_fixture()
        operation, request, spec, imports = self.completion_fixture(bundle, inputs)
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            self.exit_fixture()
            self.set_state(mode="timeout-remove")
            self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assert_unpublished(operation)
        self.assertEqual({}, self.state()["containers"])
        self.assertEqual(1, len(list(self.outputs.iterdir())))
        self.assertFalse(self.bundle.exists())
        self.set_state(mode="normal")
        with self.listener(), self.worker_listener(spec, imports) as call:
            for action in ("query", "stop", "ensure_started"):
                self.assertEqual({"error": "uncertain"}, call(action, request))
            self.assertEqual({"error": "unavailable"}, call("artifacts", request))
            self.uncertain("ensure_started", self.second)
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])

    def test_stop_wins_over_closed_candidate_after_sync_failure(self):
        bundle, inputs, readback, _ = self.bundle_fixture()
        operation, request, spec, imports = self.completion_fixture(bundle, inputs)
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            self.exit_fixture()
            with patch.object(DockerContainerAdapter, "_sync_output_root", side_effect=OSError("sync failed")):
                self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assert_unpublished(operation)
        self.assertEqual([], list(self.outputs.iterdir()))
        with self.listener(), self.worker_listener(spec, imports) as call:
            with patch.object(DockerContainerAdapter, "_discard_pending", side_effect=OSError("cleanup failed")):
                self.assertEqual({"error": "uncertain"}, call("stop", request))
                self.status("query", operation, "stopping")
            self.assertEqual("stopped", call("stop", request)["status"])
            self.status("query", operation, "stopped")
            self.status("ensure_started", operation, "stopped")
            self.assertEqual({"error": "unavailable"}, call("artifacts", request))
            self.assertFalse(self.bundle.exists())
            self.assertFalse(list(self.bundle.parent.glob(".mixer-l05-*.pending")))
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])

    def test_guard_expiring_after_verified_closure_prevents_completion(self):
        bundle, inputs, readback, _ = self.bundle_fixture()
        operation, request, spec, imports = self.completion_fixture(bundle, inputs)
        complete = DockerContainerAdapter.complete
        clock = SimpleNamespace(time_ns=time.time_ns, monotonic=time.monotonic)

        def expire(adapter, identity, cutoff):
            terminal = complete(adapter, identity, cutoff)
            clock.time_ns = lambda: operation.guard.expires_at * 1_000_000
            return terminal

        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            self.exit_fixture()
            with (patch("linux_android_runner_server.time", clock),
                  patch.object(DockerContainerAdapter, "complete", expire)):
                self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assert_unpublished(operation)
        self.assertEqual([], list(self.outputs.iterdir()))
        commands = self.commands()
        newer = replace(operation.guard, epoch=2, owner_id="next")
        renewed = dict(request, guard=asdict(newer))
        with self.listener(), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", renewed))
            self.assertEqual("native_ready", call("artifacts", renewed)["status"])
        self.assertEqual(commands, self.commands())

    def test_completion_partial_cleanup_is_bounded_and_never_follows_output_links(self):
        bundle, inputs, readback, _ = self.bundle_fixture()
        operation, request, spec, imports = self.completion_fixture(bundle, inputs)
        with self.listener(initialize=True), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            [output] = self.outputs.iterdir()
            (output / "bundle-link").symlink_to(bundle, target_is_directory=True)
            self.exit_fixture()
            with patch("linux_android_docker_adapter.OUTPUT_ENTRIES_PER_PASS", 1):
                self.assertEqual({"error": "uncertain"}, call("query", request))
            self.assertTrue(output.is_dir())
            self.assert_unpublished(operation)
        with self.listener(), self.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("query", request))
            self.assertEqual("native_ready", call("artifacts", request)["status"])
        self.assertEqual([], list(self.outputs.iterdir()))
        self.assertEqual(readback, digest((bundle / "readback.json").read_bytes()))
        self.assertEqual(["create", "start", "rm"], [command[1] for command in self.mutations()])

    def test_pre_completion_journals_reopen_existing_attempt(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
        for name, table, column in (("operations.sqlite", "operation", "completed"),
                                    ("docker-operations.sqlite", "attempt", "successful_exit")):
            with closing(sqlite3.connect(self.runner / name)) as db:
                db.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
                if table == "attempt":
                    db.execute("ALTER TABLE attempt DROP COLUMN exit_output_stamp")
                    db.execute("DROP TABLE seal")
        with self.listener():
            self.status("query", self.first, "running")
            self.status("stop", self.first, "stopped")
        self.assertEqual(["create", "start", "stop", "rm"], [command[1] for command in self.mutations()])

    def test_completion_grant_cannot_follow_a_different_binding(self):
        bundle, inputs, _, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(bundle, inputs)
        other = replace(operation, identity=replace(operation.identity, binding_sha256="e" * 64))
        with self.listener(initialize=True):
            self.uncertain("ensure_started", other)
            self.uncertain("query", other)
            self.status("query", operation, "absent")
            self.assertEqual([], self.mutations())
            self.uncertain("stop", other)
            self.status("ensure_started", operation, "running")
            self.status("stop", operation, "stopped")

    def test_replaced_bundle_directory_after_restart_refuses_completion_and_allows_stop(self):
        bundle, inputs, readback, _ = self.bundle_fixture()
        operation, _, _, _ = self.completion_fixture(bundle, inputs)
        with self.listener(initialize=True):
            self.status("ensure_started", operation, "running")
            self.exit_fixture()
            self.assert_completed("query", operation, inputs, readback)
        original = self.bundle.with_name("original-bundle")
        self.bundle.rename(original)
        shutil.copytree(original, self.bundle)
        with self.listener():
            self.uncertain("query", operation)
            self.status("stop", operation, "stopped")
            self.status("query", operation, "stopped")

    def test_exact_offline_command_duplicate_start_restart_and_stop(self):
        with self.listener(initialize=True):
            self.status("query", self.first, "absent")
            self.assertEqual(self.commands(), [])
            self.status("ensure_started", self.first, "running")
        with self.listener():
            self.status("ensure_started", self.first, "running")
            other_binding = replace(self.first, identity=replace(self.first.identity, binding_sha256="e" * 64))
            self.uncertain("stop", other_binding)
            self.uncertain("ensure_started", self.second)
            [(cid, container)] = self.state()["containers"].items()
            [output] = self.outputs.iterdir()
            self.assertEqual((output / "nested" / "fixture-artifact").read_text(), "fixture output")
            (output / "symlink").symlink_to(self.input_file)
            self.status("stop", self.first, "stopped")
        with self.listener():
            self.status("ensure_started", self.first, "stopped")
            self.status("stop", self.first, "stopped")
        create, start, stop, remove = self.mutations()
        self.assertEqual(start, ["container", "start", cid])
        self.assertEqual(stop, ["container", "stop", "--time", "0", cid])
        self.assertEqual(remove, ["container", "rm", cid])
        guest_user = f"{os.getuid()}:{os.getgid()}" if os.getuid() != 0 else "65534:65534"
        for flag, value in (("--pull", "never"), ("--platform", "linux/arm64"), ("--network", "none"),
                            ("--cap-drop", "ALL"), ("--security-opt", "no-new-privileges=true"),
                            ("--pids-limit", "128"), ("--user", guest_user)):
            self.assertEqual(create[create.index(flag) + 1], value)
        self.assertIn("--read-only", create)
        self.assertNotIn("--privileged", create)
        log_options = [create[index + 1] for index, flag in enumerate(create) if flag == "--log-opt"]
        self.assertEqual(log_options, ["max-size=8m", "max-file=1", "compress=false"])
        self.assertEqual(create[create.index(self.recipe["image"]) + 1:], self.recipe["arguments"])
        self.assertEqual(container["Config"]["Labels"],
                         {f"mixer.runner.{key}": value for key, value in asdict(self.first.identity).items()})
        self.assertEqual(container["Mounts"], [
            {"Type": "bind", "Source": str(self.inputs), "Destination": "/inputs", "RW": False},
            {"Type": "bind", "Source": str(output), "Destination": "/output", "RW": True},
        ])
        self.assertFalse(self.state()["containers"])
        self.assertFalse(list(self.outputs.iterdir()))
        self.assertEqual(self.input_file.read_text(), "immutable fixture inputs")

    def test_stop_before_create_fences_without_docker(self):
        with self.listener(initialize=True):
            self.status("stop", self.first, "stopped")
        with self.listener():
            self.status("ensure_started", self.first, "stopped")
        self.assertEqual(self.commands(), [])

    def test_lost_start_ack_reconciles_exact_running_id_without_starting_again(self):
        self.set_state(mode="lost-start-ack")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
        with self.listener():
            self.status("query", self.first, "running")
            self.status("ensure_started", self.first, "running")
            self.status("stop", self.first, "stopped")
        self.assertEqual([command[1] for command in self.mutations()], ["create", "start", "stop", "rm"])

    def test_worker_and_runner_restart_resumes_exact_prepared_id_once(self):
        scope = dict(organization_id="organization", project_id="project",
                     application_id="application", platform="android")
        spec = dict(scope, source={"sha256": "b" * 64}, toolchain_lock_sha256="c" * 64,
                    build_definition_sha256=self.recipe_sha)
        request = dict(operation_id=self.first.identity.operation_id, spec=dict(spec, build_id="build"),
                       ref=dict(scope, build_id="build", fence=1, attempt=1),
                       deadline_ms=self.first.deadline_ms, guard=asdict(self.first.guard))
        self.set_state(mode="missing-created")
        with self.listener(initialize=True), self.worker_listener(spec) as call:
            self.assertEqual(call("ensure_started", request), {"error": "uncertain"})
        [(cid, container)] = self.state()["containers"].items()
        self.assertEqual(container["State"]["Status"], "created")
        self.assertEqual([command[1] for command in self.mutations()], ["create"])
        self.set_state(mode="normal")
        with self.listener(), self.worker_listener(spec) as call:
            self.assertEqual(call("query", request), {"error": "uncertain"})
            self.assertEqual([command[1] for command in self.mutations()], ["create"])
            self.assertEqual(call("ensure_started", request), {"status": "running"})
            self.assertEqual(call("ensure_started", request), {"status": "running"})
        with self.listener(), self.worker_listener(spec) as call:
            self.assertEqual(call("ensure_started", request), {"status": "running"})
            self.assertEqual(call("stop", request)["status"], "stopped")
            self.assertEqual(call("ensure_started", request)["status"], "stopped")
        self.assertEqual(self.mutations()[1:], [
            ["container", "start", cid], ["container", "stop", "--time", "0", cid], ["container", "rm", cid],
        ])
        self.assertFalse(self.state()["containers"])
        self.assertFalse(list(self.outputs.iterdir()))

    def test_prepared_stop_fences_ensure_even_if_cleanup_must_retry(self):
        self.set_state(mode="missing-created")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
            self.uncertain("stop", self.first)
        self.set_state(mode="normal")
        [(cid, container)] = self.state()["containers"].items()
        self.assertEqual(container["State"]["Status"], "created")
        with self.listener():
            self.status("ensure_started", self.first, "stopping")
            self.uncertain("ensure_started", self.second)
            self.assertEqual([command[1] for command in self.mutations()], ["create"])
            self.status("stop", self.first, "stopped")
            self.status("ensure_started", self.first, "stopped")
        self.assertEqual(self.mutations()[1:], [["container", "rm", cid]])
        self.assertFalse(list(self.outputs.iterdir()))

    def test_prepared_expired_guard_and_deadline_cannot_start(self):
        operation = replace(self.first, guard=replace(self.first.guard, expires_at=self.first.deadline_ms - 1000))
        self.set_state(mode="missing-created")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", operation)
        self.set_state(mode="normal")
        [(cid, _)] = self.state()["containers"].items()
        with self.listener():
            with patch("linux_android_runner_server.time.time_ns", return_value=operation.guard.expires_at * 1_000_000):
                with self.assertRaisesRegex(ValueError, "invalid runner frame"):
                    self.client._exchange({"version": VERSION, "action": "ensure_started", **asdict(operation)})
            renewed = replace(operation, guard=replace(operation.guard, expires_at=operation.deadline_ms + 1000))
            with patch("linux_android_runner_server.time.time_ns", return_value=operation.deadline_ms * 1_000_000):
                with self.assertRaisesRegex(ValueError, "invalid runner frame"):
                    self.client._exchange({"version": VERSION, "action": "ensure_started", **asdict(renewed)})
                self.status("stop", renewed, "stopped")
        self.assertEqual(self.mutations()[1:], [["container", "rm", cid]])
        self.assertFalse(list(self.outputs.iterdir()))

    def test_prepared_guard_expiring_during_resume_cannot_start(self):
        operation = replace(self.first, guard=replace(self.first.guard, expires_at=self.first.deadline_ms - 1000))
        self.set_state(mode="missing-created")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", operation)
        self.set_state(mode="normal")
        [(cid, _)] = self.state()["containers"].items()
        inspect = DockerContainerAdapter._container_state
        expires = operation.guard.expires_at * 1_000_000
        clock = expires - 1_000_000_000

        def inspect_then_expire(adapter, identity, attempt, output, *, cutoff=None):
            nonlocal clock
            state = inspect(adapter, identity, attempt, output, cutoff=cutoff)
            if cutoff is not None:
                clock = expires
            return state

        with self.listener():
            with (patch("linux_android_runner_server.time.time_ns", side_effect=lambda: clock),
                  patch.object(DockerContainerAdapter, "_container_state", inspect_then_expire)):
                self.uncertain("ensure_started", operation)
            self.assertEqual(clock, expires)
            renewed = replace(operation, guard=replace(operation.guard, expires_at=operation.deadline_ms))
            self.status("stop", renewed, "stopped")
        self.assertEqual(self.mutations()[1:], [["container", "rm", cid]])
        self.assertFalse(list(self.outputs.iterdir()))

    def test_wrong_inspected_id_cannot_resume_or_remove_prepared_container(self):
        self.set_state(mode="missing-created")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
        [(cid, container)] = self.state()["containers"].items()
        self.set_state(mode="normal", containers={cid: container | {"Id": "f" * 64}})
        with self.listener():
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.first)
            self.uncertain("ensure_started", self.second)
            self.uncertain("stop", self.first)
            self.assertEqual([command[1] for command in self.mutations()], ["create"])
            self.assertEqual(len(list(self.outputs.iterdir())), 1)
            self.set_state(containers={cid: container})
            self.status("stop", self.first, "stopped")
        self.assertEqual(self.mutations()[1:], [["container", "rm", cid]])

    def test_ambiguous_creation_holds_empty_inventory_and_later_visible_container(self):
        self.set_state(mode="unacknowledged-create")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
        state = self.state()
        self.assertEqual(state["containers"], {})
        with self.listener():
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.first)
            self.uncertain("stop", self.first)
            pending = state["pending"]
            self.set_state(mode="normal", containers={pending["Id"]: pending})
            self.uncertain("stop", self.first)
            self.uncertain("ensure_started", self.second)
        self.assertEqual([command[1] for command in self.mutations()], ["create"])
        self.assertEqual(len(list(self.outputs.iterdir())), 1)

    def test_truncated_create_response_never_becomes_removal_authority(self):
        self.set_state(mode="malformed-create")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
            self.uncertain("stop", self.first)
        self.assertEqual([command[1] for command in self.mutations()], ["create"])
        self.assertEqual(len(self.state()["containers"]), 1)

    def test_socket_replacement_after_create_holds_output_and_prevents_start(self):
        self.set_state(mode="socket-replaced-after-create")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
            self.uncertain("stop", self.first)
        with self.assertRaises(Refusal), open_docker_runner(self.runner, **self.options):
            self.fail("replacement socket accepted")
        self.assertEqual([command[1] for command in self.mutations()], ["create"])
        self.assertEqual(len(list(self.outputs.iterdir())), 1)

    def test_possibly_deferred_start_does_not_remove_still_created_id(self):
        self.set_state(mode="start-pending")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
        self.set_state(mode="normal")
        with self.listener():
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.first)
            self.uncertain("stop", self.first)
            self.uncertain("ensure_started", self.second)
        self.assertEqual([command[1] for command in self.mutations()], ["create", "start"])

    def test_missing_terminal_and_absence_readbacks_preserve_output(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            [output] = self.outputs.iterdir()
            self.set_state(mode="missing-terminal")
            self.uncertain("stop", self.first)
            self.uncertain("query", self.first)
            self.assertTrue(output.is_dir())
            self.assertEqual([command[1] for command in self.mutations()], ["create", "start", "stop"])
        self.set_state(mode="missing-absence")
        with self.listener():
            self.uncertain("stop", self.first)
            self.uncertain("query", self.first)
            self.uncertain("ensure_started", self.second)
            self.assertTrue(output.is_dir())
        self.set_state(mode="normal")
        with self.listener():
            self.status("query", self.first, "stopping")
            self.status("stop", self.first, "stopped")
            self.status("ensure_started", self.second, "running")
            self.status("stop", self.second, "stopped")
        self.assertFalse(output.exists())
        self.assertEqual([command[1] for command in self.mutations()],
                         ["create", "start", "stop", "rm"] * 2)

    def test_lost_remove_ack_is_not_settled_by_an_empty_daemon_inventory(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            self.set_state(mode="lost-remove-ack")
            self.uncertain("stop", self.first)
        self.assertEqual(self.state()["containers"], {})
        self.set_state(mode="normal")
        with self.listener():
            self.uncertain("query", self.first)
            self.uncertain("stop", self.first)
            self.uncertain("ensure_started", self.second)
        self.assertEqual([command[1] for command in self.mutations()], ["create", "start", "stop", "rm"])
        self.assertEqual(len(list(self.outputs.iterdir())), 1)

    def test_terminal_cleanup_requires_synced_output_absence(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            with patch("linux_android_docker_adapter.os.fsync", side_effect=OSError("fixture sync failure")):
                self.uncertain("stop", self.first)
                self.uncertain("query", self.first)
            self.assertFalse(list(self.outputs.iterdir()))
            self.uncertain("ensure_started", self.second)
        commands = self.commands()
        with self.listener():
            self.status("query", self.first, "stopped")
        self.assertEqual(self.commands(), commands)

    def test_wrong_daemon_or_container_labels_cannot_authorize_stop(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
            self.set_state(daemon="different-daemon")
            self.uncertain("query", self.first)
            self.uncertain("stop", self.first)
            containers = self.state()["containers"]
            [container] = containers.values()
            container["Config"]["Labels"]["mixer.runner.binding_sha256"] = "0" * 64
            self.set_state(daemon="fixture-daemon", containers=containers)
            self.uncertain("stop", self.first)
        self.assertEqual([command[1] for command in self.mutations()], ["create", "start"])

    def test_drift_and_image_managed_volumes_fail_before_create(self):
        self.set_state(mode="volume-image")
        with self.listener(initialize=True):
            self.uncertain("ensure_started", self.first)
        self.assertEqual(self.mutations(), [])
        self.assertFalse(list(self.outputs.iterdir()))
        options = self.options | {"daemon_id": "new-daemon"}
        with self.assertRaises(Refusal), open_docker_runner(self.runner, **options):
            self.fail("changed daemon pin accepted")
        self.manifest.write_text("{}")
        with self.assertRaises(Refusal), open_docker_runner(self.runner, **self.options):
            self.fail("changed manifest accepted")

    def test_runner_cannot_reprovision_or_replace_one_journal(self):
        with self.listener(initialize=True):
            self.status("ensure_started", self.first, "running")
        adapter_db = self.runner / "docker-operations.sqlite"
        saved_adapter_db = self.root / adapter_db.name
        adapter_db.rename(saved_adapter_db)
        with self.assertRaises(FileNotFoundError), open_docker_runner(self.runner, **self.options):
            self.fail("missing adapter journal accepted")
        with self.assertRaises(Refusal), open_docker_runner(self.runner, initialize=True, **self.options):
            self.fail("existing runner admitted a new adapter journal")
        self.assertFalse(adapter_db.exists())
        adapter_db.write_bytes(saved_adapter_db.read_bytes())
        adapter_db.chmod(0o600)
        with self.assertRaises(Refusal), open_docker_runner(self.runner, **self.options):
            self.fail("replacement adapter journal accepted")
        saved_adapter_db.rename(adapter_db)

        runner_db = self.runner / "operations.sqlite"
        original = self.root / runner_db.name
        runner_db.rename(original)
        runner_db.write_bytes(original.read_bytes())
        runner_db.chmod(0o600)
        with self.assertRaises(Refusal), open_docker_runner(self.runner, **self.options):
            self.fail("replacement runner journal accepted")
        self.assertEqual([command[1] for command in self.mutations()], ["create", "start"])


if __name__ == "__main__":
    unittest.main()
