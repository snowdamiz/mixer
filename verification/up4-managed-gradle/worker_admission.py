"""Replay the Pair32 managed Compose admission boundary with the pinned CLI."""

import argparse
from contextlib import closing
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import time
import unittest


def replay(args):
    sys.path.insert(0, str(args.source / "hosted/scripts"))
    harness = importlib.import_module("test_native_artifact_worker")
    worker = harness.native_artifact_worker

    class Pair32Admission(harness.NativeWorkerTest):
        def setUp(self):
            self.root = args.scratch.resolve()
            self.root.mkdir(mode=0o700)
            self.spec = dict(organization_id="organization", project_id="project", application_id="application")
            self.config = dict(worker_id="native", token="test" * 8, tenant="organization")
            self.ref = dict(self.spec, build_id="build", fence=1, attempt=1)

        def recipe_for_compose(self):
            source = self.root / "project"
            driver = source / worker.ANDROID_DRIVER
            driver.parent.mkdir(parents=True)
            driver.write_bytes((args.source / "cli/Sources/MixerBuild/Resources/android-build.py").read_bytes())
            compose = source / worker.ANDROID_COMPOSE_PREFIX
            compose.mkdir(parents=True)
            (compose / "mixer-compose.json").write_text(harness.literal(dict(
                schema=1, host="public-compose-v1", application="dev.mixer.managedfixture", minAPI=28, targetAPI=37,
            )))
            (source / "mixer.yml").write_text(harness.literal(dict(
                schema=1, application="dev.mixer.managedfixture", name="ManagedFixture", language="swift",
                targets=["android"], toolchainLock="mixer.lock", capabilities=[], androidHost="public-compose-v1",
                updates=dict(activation="cold-start", compatibility="exact-runtime-fingerprint",
                             requireArtifactSignature=True, requireAssignmentSignature=True),
            )))
            cli = str(args.cli)
            python = str(Path(sys.executable).resolve(strict=True))
            tools = {path: harness.digest(Path(path).read_bytes()) for path in (cli, worker.ANDROID_HOST_SWIFT, python)}
            (source / "mixer.lock").write_text(harness.literal({"android": {"toolchain": {"tools": {
                "python": {"path": python, "sha256": tools[python]},
            }}}}))
            files = {path.relative_to(source).as_posix(): harness.digest(path.read_bytes())
                     for path in source.rglob("*") if path.is_file()}
            mirrors = {}
            for package in worker.ANDROID_MIRROR_ENV:
                mirror = args.mirrors / f"{package}.git"
                mirrors[package] = dict(url=mirror.as_uri(), tree_sha256=worker.android_mirror_fingerprint(mirror))
            pins = {}
            for role, developer in (("host", args.host_developer), ("android", args.android_developer)):
                names = [worker.XCODE_INFO, worker.XCODE_VERSION, worker.XCODEBUILD]
                if role == "host":
                    names.append(worker.XCODE_SWIFT)
                pins[role] = {name: harness.digest((developer.parent.parent / name).read_bytes()) for name in names}
            return dict(
                cwd=str(source), argv=[cli, "build", "--platform", "android", "--directory", str(source)],
                environment={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "DEVELOPER_DIR": str(args.host_developer)},
                package_policy=worker.ANDROID_PACKAGE_POLICY, profile=worker.ANDROID_PROFILE, tools=tools, inputs=files,
                android_python=python, android_host_swift=worker.ANDROID_HOST_SWIFT, android_mirrors=mirrors,
                android_developer_dir=str(args.android_developer), android_xcode_pins=pins, timeout_seconds=15,
            ), files

        def registration(self, recipe, files, operation):
            now = harness.now_ms()
            self.request = dict(operation_id=operation, deadline_ms=now + 60_000,
                                guard=dict(record_id="record", epoch=1, revision=1, owner_id="coordinator",
                                           expires_at=now + 60_000))
            return self.android_registration(recipe, files)

        def ledger(self, operation):
            path = self.root / "protocol-state/operations.sqlite"
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
                row = db.execute("SELECT value FROM operations WHERE id = ?", (operation,)).fetchone()
            return json.loads(row[0])

        def test_pair32_managed_compose(self):
            recipe, files = self.recipe_for_compose()
            operation = "a" * 64
            config, request = self.registration(recipe, files, operation)
            state = self.root / "protocol-state"
            with self.listener(config) as address:
                self.assertEqual({"status": "running"}, self.call(address, "ensure_started", request))
                limit = time.monotonic() + 10
                while time.monotonic() < limit:
                    self.call(address, "query", request)
                    value = self.ledger(operation)
                    if value["status"] != "running":
                        break
                    time.sleep(0.01)
                self.assertEqual("closed", value["status"], value)
                self.assertEqual(1, value["starts"])
                closure = value["closure"]
                self.assertEqual("not_started", closure["android_driver_outcome"])
                self.assertEqual([], closure["commands"])
                self.assertEqual(1, closure["exit"])
                self.assertTrue(closure["cli_reaped"] and closure["cli_group_absent"])
                self.assertEqual({"error": "unavailable"}, self.call(address, "artifacts", request))
                stopped = self.call(address, "stop", request)
                self.assertEqual("stopped", stopped["status"])
                self.assertEqual(stopped, self.call(address, "ensure_started", request))

            output = state / operation
            failure = json.loads((output / "stdout").read_bytes())
            self.assertEqual("android.compose-local", failure["code"])
            self.assertFalse((output / "native").exists())
            terminal = (state / "blobs" / stopped["diagnostic_sha256"]).read_bytes()
            self.assertEqual(stopped["diagnostic_sha256"], harness.digest(terminal))
            self.assertEqual(dict(operation_id=operation, closure=closure), json.loads(terminal))
            with self.listener(config) as address:
                self.assertEqual(stopped, self.call(address, "query", request))
            self.assertEqual(1, self.ledger(operation)["starts"])

            # Use the real Compose environment names to test operator recipe admission.
            recipe["environment"].update(MIXER_COMPOSE_GRADLE=str(args.gradle), ANDROID_HOME=str(args.sdk),
                                         MIXER_JDK=str(args.jdk), MIXER_COMPOSE_DEPENDENCY_CACHE=str(args.cache))
            refused_operation = "b" * 64
            config, request = self.registration(recipe, files, refused_operation)
            with self.listener(config) as address:
                self.assertEqual({"error": "unavailable"}, self.call(address, "ensure_started", request))
                self.assertEqual({"status": "absent"}, self.call(address, "query", request))
            self.assertEqual(0, self.ledger(refused_operation)["starts"])
            self.assertFalse((state / refused_operation).exists())
            print(harness.literal(dict(cliError=failure, cliStarts=1, driverStarts=0, gradleStarts=0,
                                       composeEnvironmentStarts=0, artifacts="unavailable", stopAfterClosure="stopped",
                                       stoppedAfterReopen=True, workerListenersClosed=True, cliGroupAbsent=True)))

    suite = unittest.TestSuite([Pair32Admission("test_pair32_managed_compose")])
    return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "cli", "mirrors", "host-developer", "android-developer", "gradle", "sdk", "jdk", "cache"):
        parser.add_argument("--" + name, required=True, type=lambda value: Path(value).resolve(strict=True))
    parser.add_argument("--scratch", required=True, type=Path, help="fresh owned directory to retain until custody is known")
    sys.exit(0 if replay(parser.parse_args()) else 1)
