"""Exercise the runner entry point with a real socket and fixture Docker."""

from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import test_linux_android_docker_adapter as fixture
from compiler_worker import digest
from linux_android_runner import LinuxAndroidRunnerClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tests/integration/managed-android-local-linux-pair25"))
import test_managed_layout as layout_fixture
from linux_android_pair25_layout import ARGUMENTS, ENTRYPOINT, IMAGE_IDS, LOADER, PLATFORM


CLI = Path(__file__).resolve().parents[1] / "priv" / "development" / "linux_android_runner_cli.py"
PAIR25_CLI = """
from pathlib import Path
import runpy
import sys

receipt, products, python = sys.argv[1:4]
sys.argv = sys.argv[4:]
sys.path.insert(0, str(Path(sys.argv[0]).parent))
import linux_android_pair25_layout as layout
layout.RECEIPT_SHA256 = receipt
layout.PRODUCTS_RECEIPT_SHA256 = products
layout.NOBLE_PYTHON_SHA256 = python
runpy.run_path(sys.argv[0], run_name="__main__")
"""


class RunnerCLITest(unittest.TestCase):
    def setUp(self):
        self.docker = fixture.DockerContainerAdapterTest()
        self.addCleanup(self.docker.doCleanups)
        self.docker.setUp()
        self.config = self.docker.root / "config.json"
        self.cli = [str(CLI)]
        self.write_config()

    def write_config(self):
        data = json.dumps(dict(self.docker.options, directory=self.docker.runner), default=os.fspath).encode()
        self.config.write_bytes(data)
        self.config.chmod(0o600)
        self.config_digest = digest(data)

    def command(self, mode, sha=None):
        return [sys.executable, *["-O"] * sys.flags.optimize, "-B", *self.cli, mode,
                str(self.config), sha or self.config_digest]

    def invoke(self, mode, sha=None):
        return subprocess.run(self.command(mode, sha), stdin=subprocess.DEVNULL, capture_output=True, timeout=5)

    @contextmanager
    def serve(self):
        with subprocess.Popen(self.command("serve"), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            try:
                deadline = time.monotonic() + 5
                while not self.docker.endpoint.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(self.docker.endpoint.exists(), "runner did not open the socket")
                yield
            finally:
                if process.poll() is None:
                    process.terminate()
                try:
                    _, error = process.communicate(timeout=4)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate(timeout=4)
                    raise
                self.assertEqual(process.returncode, 0, error)
                self.assertFalse(self.docker.endpoint.exists())

    def test_configuration_is_checked_before_provisioning(self):
        self.assertNotEqual(self.invoke("initialize", "0" * 64).returncode, 0)
        self.assertNotEqual(self.invoke("serve").returncode, 0)
        data = self.config.read_bytes().replace(b"{", b'{"store_id": "duplicate", ', 1)
        self.config.write_bytes(data)
        self.assertNotEqual(self.invoke("initialize", digest(data)).returncode, 0)
        self.assertFalse((self.docker.runner / "operations.sqlite").exists())
        self.assertFalse((self.docker.runner / "docker-operations.sqlite").exists())
        self.assertEqual(self.docker.commands(), [])

    def test_runner_reopen_preserves_and_closes_the_exact_operation(self):
        initialized = self.invoke("initialize")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertFalse(self.docker.endpoint.exists())
        self.assertNotEqual(self.invoke("initialize").returncode, 0)
        self.assertEqual(self.docker.commands(), [])

        with self.serve():
            self.docker.status("query", self.docker.first, "absent")
            self.assertEqual(self.docker.commands(), [])
            self.docker.status("ensure_started", self.docker.first, "running")
        [container_id] = self.docker.state()["containers"]
        self.assertEqual(len(self.docker.mutations()), 2)

        with self.serve():
            self.docker.status("query", self.docker.first, "running")
            self.docker.status("ensure_started", self.docker.first, "running")
            self.assertEqual(len(self.docker.mutations()), 2)
            self.docker.status("stop", self.docker.first, "stopped")
        _, start, stop, remove = self.docker.mutations()
        self.assertEqual([start[-1], stop[-1], remove[-1]], [container_id] * 3)
        self.assertEqual(self.docker.state()["containers"], {})
        self.assertEqual(list(self.docker.outputs.iterdir()), [])

    def stage_pair25(self, *, projected=False):
        stage = layout_fixture.ManagedLayoutTest()
        self.addCleanup(stage.doCleanups)
        stage.setUp()
        if projected:
            stage.project_lock()
            stage.approve_projection()
            layout = stage.read_projection()
        else:
            layout = stage.read()
        layout.output(stage.name).rmdir()
        docker = self.docker
        docker.recipe = {
            "image": layout.image, "image_id": layout.image_ids[1], "platform": PLATFORM,
            "entrypoint": ENTRYPOINT, "arguments": list(ARGUMENTS),
        }
        docker.outputs = stage.root / "outputs"
        docker.manifest.write_text(json.dumps(docker.recipe))
        docker.recipe_sha = digest(docker.manifest.read_bytes())
        docker.options.pop("inputs")
        docker.options.pop("outputs")
        docker.options.update(pair25_root=stage.root, recipe_sha256=docker.recipe_sha)
        docker.client = LinuxAndroidRunnerClient(
            docker.endpoint, recipe_sha256=docker.recipe_sha, store_id=docker.options["store_id"],
        )
        with patch.multiple(layout_fixture.pair25, RECEIPT_SHA256=stage.pin, PRODUCTS_RECEIPT_SHA256=stage.products_pin):
            volume = stage.volume(layout)
        docker.set_state(recipe=docker.recipe, volume=volume,
                         image_env=["PATH=/usr/bin:/bin", "HOME=/root"])
        self.cli = ["-c", PAIR25_CLI, stage.pin, stage.products_pin,
                    stage.toolchain["tools"]["python"]["sha256"], str(CLI)]
        source, inputs, readback, artifacts = docker.bundle_fixture(
            lock=(stage.root / "lock/linux-mixer.lock").read_bytes(),
            driver=(stage.root / stage.project / "Generated/MixerAndroid/android-build.py").read_bytes(),
            source_tree=layout.source_tree_sha256, apk_name="UpgradeStarter-unsigned.apk",
        )
        self.assertEqual(inputs, layout.verified_inputs)
        operation, request, spec, imports = docker.completion_fixture(source, inputs, stage=False)
        self.write_config()
        return operation, request, spec, imports, inputs, readback, source, artifacts

    def test_pair25_requires_exclusive_layout_and_the_registered_input_pins(self):
        self.stage_pair25()
        self.docker.options["outputs"] = self.docker.outputs
        self.write_config()
        self.assertNotEqual(self.invoke("initialize").returncode, 0)
        del self.docker.options["outputs"]
        grant = next(iter(self.docker.options["completions"].values()))
        grant["inputs"]["linux_lock_sha256"] = "f" * 64
        self.write_config()
        self.assertNotEqual(self.invoke("initialize").returncode, 0)
        self.assertFalse((self.docker.runner / "docker-operations.sqlite").exists())
        self.assertEqual(self.docker.commands(), [])

    def test_projected_pair25_starts_before_products_exist_and_pins_approval_on_reopen(self):
        operation, request, spec, imports, inputs, _, source, artifacts = self.stage_pair25(projected=True)
        docker = self.docker
        driver_receipt = {"exitCode": 0, "stdoutBytes": 71, "stderrBytes": 9, "outputTruncated": False}
        index = source / "readback.json"
        index.write_text(json.dumps(json.loads(index.read_bytes()) | {"androidDriverLog": driver_receipt}))
        readback = digest(index.read_bytes())
        log = docker.root / "worker-state" / ("customer-log-v1-" + operation.identity.operation_id)
        initialized = self.invoke("initialize")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        with self.serve(), docker.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            docker.exit_fixture()
            docker.assert_completed("query", operation, inputs, readback)
            self.assertEqual({"status": "running"}, call("query", request))
            self.assertFalse(log.exists())
            rows = [{key: value for key, value in row.items() if key != "file"} for row in artifacts]
            result = call("artifacts", request)
            self.assertEqual("native_ready", result.get("status"), result)
            self.assertEqual(rows, result["artifacts"])
            original_log = log.read_bytes()
            original_inode = log.stat().st_ino
            self.assertEqual(0o400, log.stat().st_mode & 0o777)
            self.assertEqual({
                "version": 1, "operationId": operation.identity.operation_id,
                "sourceSha256": inputs["source_tree_sha256"],
                "toolchainLockSha256": inputs["linux_lock_sha256"],
                "buildDefinitionSha256": docker.recipe_sha,
                "cliExitCode": 0, "androidDriver": {
                    "exitCode": 0, "stdoutBytes": 71, "stderrBytes": 9, "tailTruncated": False, "phases": [],
                },
            }, json.loads(original_log))

        self.assertEqual({}, docker.state()["containers"])
        self.assertEqual([], list(docker.outputs.iterdir()))
        with self.serve(), docker.worker_listener(spec, imports) as call:
            docker.assert_completed("query", operation, inputs, readback)
            self.assertEqual(result, call("artifacts", request))
            self.assertEqual(original_log, log.read_bytes())
            self.assertEqual(original_inode, log.stat().st_ino)
        approval = docker.options["pair25_root"] / "projection.json"
        approval.write_bytes(approval.read_bytes() + b"\n")
        volume = docker.state()["volume"]
        volume["Labels"]["mixer.pair25.projection"] = digest(approval.read_bytes())
        docker.set_state(volume=volume)
        mutations = docker.mutations()
        self.assertNotEqual(self.invoke("serve").returncode, 0)
        self.assertEqual(mutations, docker.mutations())

    def test_pair25_rechecks_volume_and_resumes_to_sealed_result_across_cli_restarts(self):
        operation, request, spec, imports, inputs, readback, source, artifacts = self.stage_pair25()
        docker = self.docker
        volume = docker.state()["volume"]
        drift = volume | {"CreatedAt": "2026-11-21T05:22:00Z"}
        docker.set_state(volume=None)
        self.assertNotEqual(self.invoke("initialize").returncode, 0)
        self.assertFalse((docker.runner / "docker-operations.sqlite").exists())
        docker.set_state(volume=volume)
        initialized = self.invoke("initialize")
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        with self.serve():
            unregistered = replace(operation, identity=replace(operation.identity, operation_id="f" * 64))
            docker.uncertain("ensure_started", unregistered)
            docker.set_state(volume=None)
            docker.uncertain("ensure_started", operation)
            self.assertEqual([], docker.mutations())
            self.assertEqual([], list(docker.outputs.iterdir()))

            docker.set_state(volume=volume, mode="missing-created")
            docker.uncertain("ensure_started", operation)
            [created] = docker.mutations()
            [output] = docker.outputs.iterdir()
            self.assertEqual(0o777, output.stat().st_mode & 0o777)
            [cid] = docker.state()["containers"]
            self.assertIn("65534:65534", created)

            docker.set_state(volume=drift, mode="normal")
            docker.uncertain("ensure_started", operation)
            docker.set_state(volume=volume)
            [container] = docker.state()["containers"].values()
            docker.set_state(containers={cid: container | {"Image": IMAGE_IDS[0]}})
            docker.uncertain("ensure_started", operation)
            docker.set_state(containers={cid: container})

            loader = docker.options["pair25_root"] / "lib64" / LOADER
            target = loader.readlink()
            loader.unlink()
            loader.symlink_to("/unexpected-loader")
            docker.uncertain("ensure_started", operation)
            loader.unlink()
            loader.symlink_to(target)
            self.assertEqual([created], docker.mutations())
            self.assertEqual([], list(output.iterdir()))

        docker.set_state(volume=drift)
        self.assertNotEqual(self.invoke("serve").returncode, 0)
        docker.set_state(volume=volume, image_env=["PATH=/wrong"])
        self.assertNotEqual(self.invoke("serve").returncode, 0)
        docker.set_state(image_env=["PATH=/usr/bin:/bin", "HOME=/root"])
        with self.serve(), docker.worker_listener(spec, imports) as call:
            self.assertEqual({"status": "running"}, call("ensure_started", request))
            self.assertEqual(cid, docker.exit_fixture())
            original = docker.state()["containers"][cid]
            mounts = [mount if mount["Destination"] != "/deliver" else mount | {"Source": str(source)}
                      for mount in original["Mounts"]]
            docker.set_state(containers={cid: original | {"Mounts": mounts}})
            self.assertEqual({"error": "uncertain"}, call("query", request))
            docker.assert_unpublished(operation)
            docker.set_state(containers={cid: original})
            docker.assert_completed("query", operation, inputs, readback)
            self.assertEqual({"status": "running"}, call("query", request))
            rows = [{key: value for key, value in row.items() if key != "file"} for row in artifacts]
            self.assertEqual(rows, call("artifacts", request)["artifacts"])

        self.assertEqual({}, docker.state()["containers"])
        self.assertEqual([], list(docker.outputs.iterdir()))
        _, start, remove = docker.mutations()
        self.assertEqual([cid, cid], [start[-1], remove[-1]])
        self.assertEqual({path.name for path in source.iterdir()}, {path.name for path in docker.bundle.iterdir()})
        for path in docker.bundle.iterdir():
            self.assertEqual((source / path.name).read_bytes(), path.read_bytes())
            self.assertEqual(0o400, path.stat().st_mode & 0o777)

        commands = docker.mutations()
        with self.serve(), docker.worker_listener(spec, imports) as call:
            docker.assert_completed("ensure_started", operation, inputs, readback)
            self.assertEqual(rows, call("artifacts", request)["artifacts"])
        self.assertEqual(commands, docker.mutations())


if __name__ == "__main__":
    unittest.main()
