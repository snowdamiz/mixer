"""Run focused recipe controls against an independently transferred fixture copy."""

import contextlib
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
import py_compile
import shutil
import signal
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = "6b5f9a5b29559119a9133a551432b47e392950b6"
EVIDENCE = "2260a4e06f46177d8448b41e473f826069291c5a"
RUNNER = HERE.parent / "fieldlog-task-calculation/android-packaging/run.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], timeout=15)


def original(path, name):
    namespace = {"__file__": str(path), "__name__": name}
    exec(compile(git("show", f"{SOURCE}:{path.relative_to(ROOT)}"), str(path), "exec"), namespace)
    return namespace


recipe = load("current_abi", HERE / "current-abi.py")
replay = load("pair_replay", HERE / "replay-android-pair.py")
runner = load("stage_runner", RUNNER)
from current_abi_packet import (
    METADATA_LIMIT, SEALED, bindings, packet_hashes, refusal_responses, require_members, verify_materials,
)
from current_abi_recipe import CALCULATION_LOCK, SOURCES
from package import digest, inventory, read, tree, write


class Controls(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory(prefix="mixer-current-abi-recipe-controls-")
        self.addCleanup(tmp.cleanup)
        self.scratch = Path(tmp.name).resolve()

    def test_transfer(self):
        compact = json.loads(git("show", f"{EVIDENCE}:verification/receipts/fieldlog-android-https-current-abi-b144c2c2.json"))
        require_members(FIXTURE, SEALED | {"SHA256SUMS"})
        files = inventory(FIXTURE, FIXTURE)
        self.assertEqual(files.pop("SHA256SUMS"), compact["custody"]["packetChecksumSHA256"])
        self.assertEqual(len(files), 41)
        self.assertEqual(tree(files), compact["custody"]["packetChecksumSHA256"])
        observed = bindings(FIXTURE)
        verify_materials(FIXTURE, read(FIXTURE / "build.json"), read(FIXTURE / "stock-inspection.json"), observed)
        for label, apk in compact["build"]["apks"].items():
            self.assertEqual(observed["native"][label]["archiveSHA256"], apk["apkSHA256"])
            self.assertEqual(observed["native"][label]["installed"]["identity.json"], apk["descriptorSHA256"])
            for key, compact_key in (("artifactSHA256", "artifactSHA256"), ("manifestSHA256", "signedManifestSHA256"),
                                     ("assignmentSHA256", "signedAssignmentSHA256")):
                self.assertEqual(observed["offers"][label][key], apk[compact_key])

    def observe(self, packet, mode):
        host = read(packet / "old/host.json")
        installation = read(packet / "verifier.json")["installation"]
        command = [sys.executable, "-IB", "-c", """
import json, sys
from urllib.parse import urlencode
from urllib.request import build_opener, ProxyHandler

base, query, mode = sys.argv[1:]
opener = build_opener(ProxyHandler({}))
with opener.open(base + '/v3/updates?' + urlencode(json.loads(query)), timeout=3) as stream:
    path = json.load(stream)['artifact_url']
if mode != 'offer-only':
    if mode == 'wrong-artifact':
        artifact, query = path.split('?', 1)
        path = artifact.rsplit('/', 1)[0] + '/' + '0' * 64 + '?' + query
    try:
        with opener.open(base + path, timeout=3) as stream:
            stream.read()
    except OSError:
        if mode != 'wrong-artifact':
            raise
"""]
        query = host["scope"] | {"channel": "beta", "runtime": host["runtime"], "installation": installation}

        _, exchange = replay.refusal_exchange(
            packet, self.scratch / "phase", host, installation,
            lambda url: subprocess.run(command + [url, json.dumps(query), mode], check=True, timeout=8),
        )
        return exchange

    def test_probe_loopback_boundary(self):
        exchange = self.observe(FIXTURE, "exact")
        self.assertEqual(exchange["artifactSHA256"], bindings(FIXTURE)["offers"]["refused"]["artifactSHA256"])
        with self.assertRaisesRegex(ValueError, "did not complete exactly"):
            self.observe(FIXTURE, "offer-only")
        with self.assertRaisesRegex(ValueError, "request or response differs"):
            self.observe(FIXTURE, "wrong-artifact")
        with socket.socket() as connection:
            connection.settimeout(2)
            self.assertNotEqual(connection.connect_ex(("127.0.0.1", int((FIXTURE / "old/Installed/port.txt").read_text()))), 0)

    def test_incomplete_seal_and_drift(self):
        packet = self.scratch / "packet"
        work = self.scratch / "work"
        (work / "logs").mkdir(parents=True)
        rebuild = read(FIXTURE / "rebuild.json")
        for label, row in rebuild["stageResults"].items():
            write(work / f"logs/{label}.json", row | {"peakSampledScratchKiB": 1})
        lock = digest(ROOT / CALCULATION_LOCK)
        write(work / "preflight.json", rebuild | {"recipeLockSHA256": lock})
        shutil.copytree(FIXTURE, packet, ignore=shutil.ignore_patterns("SHA256SUMS", "rebuild.json", "android-origin.py"))
        for name in ("old/FieldLog.apk", "successor/FieldLog.apk", "host-replay.json", "stock-inspection.json"):
            (packet / name).unlink()
        revision = git("rev-parse", "HEAD").decode().strip()
        with self.assertRaisesRegex(ValueError, "Handoff member mismatch"):
            recipe.seal(work, packet, revision)
        self.assertFalse((packet / "SHA256SUMS").exists())
        original(HERE / "current-abi.py", "old_seal")["seal"](work, packet)
        self.assertTrue((packet / "SHA256SUMS").is_file())
        self.assertNotIn("FieldLog.apk", (packet / "SHA256SUMS").read_text())

        # Use separate test-only receipt fields over a private clone. The
        # historical producer never recorded the new live host observation.
        shutil.copytree(FIXTURE, packet, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("SHA256SUMS", "rebuild.json", "android-origin.py"))
        observed = bindings(packet)
        host_result = read(packet / "host-replay.json")
        verifier = read(packet / "verifier.json")
        refused = observed["offers"]["refused"]
        host = read(packet / "old/host.json")
        host_result["refusalExchange"] = refused | {
            "runtime": host["runtime"], "installation": verifier["installation"],
            "responses": refusal_responses(packet, host, verifier["installation"]),
        }
        host_result["separateVerifierRefusal"] = {"code": verifier["manifestRefusal"], "artifactSHA256": refused["artifactSHA256"]}
        (packet / "host-replay.json").write_text(json.dumps(host_result))
        for name in ("SHA256SUMS", "rebuild.json", "android-origin.py"):
            (packet / name).unlink()
        for name in ("build.json", "stock-inspection.json"):
            path = packet / name
            row = read(path) | {"handoffInputs": observed}
            if name == "stock-inspection.json":
                row["targetPins"]["behaviorReceiptSHA256"] = digest(packet / "host-replay.json")
                row["protocol"]["cases"]["refusedOnBaseline"] = {"code": verifier["manifestRefusal"]}
            path.write_text(json.dumps(row))
        for name in ("old/FieldLog.apk", "successor/Installed/roots.json", "refused/assignment.json"):
            with self.subTest(member=name):
                path = packet / name
                intact = path.read_bytes()
                path.write_bytes(intact + b"\n")
                with self.assertRaisesRegex(ValueError, "differ from build receipt"):
                    recipe.seal(work, packet, revision)
                self.assertFalse((packet / "SHA256SUMS").exists())
                path.write_bytes(intact)
        offer = packet / "refused/manifest.json"
        intact = offer.read_bytes()
        offer.write_bytes(intact + b"\n")
        build = packet / "build.json"
        build.write_text(json.dumps(read(build) | {"handoffInputs": bindings(packet)}))
        with self.assertRaisesRegex(ValueError, "differ from inspection receipt"):
            recipe.seal(work, packet, revision)
        self.assertFalse((packet / "SHA256SUMS").exists())
        offer.write_bytes(intact)
        build.write_text(json.dumps(read(build) | {"handoffInputs": observed}))

        replay_path = packet / "host-replay.json"
        replay_bytes = replay_path.read_bytes()
        validate = recipe.validate_for_seal

        def drift_after_validation(snapshot):
            validate(snapshot)
            replay_path.write_bytes(replay_bytes + b"\n")

        with patch.object(recipe, "validate_for_seal", side_effect=drift_after_validation):
            with self.assertRaisesRegex(ValueError, "changed .*validation"):
                recipe.seal(work, packet, revision)
        self.assertFalse((packet / "SHA256SUMS").exists())
        self.assertFalse((packet / "rebuild.json").exists())
        replay_path.write_bytes(replay_bytes)

        campaign = self.scratch / "projection"
        recipe.verify_recipe(ROOT, revision, campaign=campaign)
        projected = campaign / "work/recipe-source" / (HERE / "current-abi.py").relative_to(ROOT)
        subprocess.run([sys.executable, "-EBS", projected, "seal", work, packet,
                        "--recipe-revision", revision, "--recipe-repo", ROOT], check=True, timeout=20)
        require_members(packet, SEALED | {"SHA256SUMS"})
        files = inventory(packet, packet)
        self.assertEqual(files.pop("SHA256SUMS"), tree(files))

    def test_snapshot_rejects_oversized_metadata(self):
        packet, snapshot = (self.scratch / name for name in ("packet", "snapshot"))
        packet.mkdir()
        with (packet / "build.json").open("wb") as stream:
            stream.truncate(METADATA_LIMIT + 1)
        with self.assertRaisesRegex(ValueError, "Handoff size limit exceeded: build.json"):
            packet_hashes(packet, {"build.json"}, snapshot)
        self.assertEqual((snapshot / "build.json").stat().st_size, 0)

    def copy_recipe(self):
        revision = git("rev-parse", "HEAD").decode().strip()
        lock = self.scratch / CALCULATION_LOCK
        source_paths = SOURCES | {Path(line.split("  ")[1]) for line in (ROOT / CALCULATION_LOCK).read_text().splitlines()}
        for name in source_paths:
            path = self.scratch / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        subprocess.run(["git", "init", "-q", self.scratch], timeout=10, check=True)
        objects = git("rev-parse", "--path-format=absolute", "--git-path", "objects").decode().strip()
        (self.scratch / ".git/objects/info/alternates").write_text(objects + "\n")
        subprocess.run(["git", "-C", self.scratch, "update-ref", "HEAD", revision], timeout=10, check=True)
        return revision, lock

    def test_git_lock_disagrees_with_rehashed_working_files(self):
        revision, lock = self.copy_recipe()
        recipe.verify_recipe(self.scratch, revision)
        altered = self.scratch / RUNNER.relative_to(ROOT)
        old = digest(altered)
        altered.write_bytes(altered.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "run.py"):
            recipe.verify_recipe(self.scratch, revision)
        lock.write_text(lock.read_text().replace(old, digest(altered)))
        with self.assertRaisesRegex(ValueError, "recipe.sha256"):
            recipe.verify_recipe(self.scratch, revision)
        campaign = self.scratch / "build-must-not-start"
        launcher = self.scratch / (HERE / "build-current-abi-android-pair.sh").relative_to(ROOT)
        result = subprocess.run(["/bin/bash", launcher, campaign], capture_output=True, text=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Recipe source differs:", result.stderr)
        self.assertIn("recipe.sha256", result.stderr)
        self.assertFalse(campaign.exists())

    def test_launcher_uses_verified_sources(self):
        self.copy_recipe()
        campaign = self.scratch / "campaign"
        ambient = self.scratch / "ambient"
        ambient.mkdir()
        startup_marker = ambient / "startup-ran"
        (ambient / "sitecustomize.py").write_text(f"open({str(startup_marker)!r}, 'w').close()\n")
        helper = self.scratch / CALCULATION_LOCK.parent / "package.py"
        cache_marker = ambient / "cache-ran"
        poison = ambient / "poison.py"
        poison.write_text(f"open({str(cache_marker)!r}, 'w').close()\n")
        cache = ambient / "cache"
        with patch.object(sys, "pycache_prefix", str(cache)):
            cached_helper = importlib.util.cache_from_source(str(helper))
        py_compile.compile(str(poison), cfile=cached_helper, dfile=str(helper),
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH, doraise=True)

        launcher = self.scratch / (HERE / "build-current-abi-android-pair.sh").relative_to(ROOT)
        result = subprocess.run(
            ["/bin/bash", launcher, campaign], cwd=ambient, capture_output=True, text=True, timeout=40,
            env=os.environ | {"HOME": str(ambient), "PYTHONPATH": str(ambient), "PYTHONPYCACHEPREFIX": str(cache)},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((startup_marker.exists(), cache_marker.exists()), (False, False))
        work = campaign / "work"
        receipt = read(work / "logs/preflight.json")
        self.assertEqual((receipt["exit"], receipt["custody"]), (1, "closed"))
        self.assertIn(str(ambient / "Library/Developer/Toolchains"), (work / "logs/preflight.log").read_text())
        self.assertFalse((work / "logs/fieldlog-fetch.json").exists())
        self.assertEqual((work / "recipe-source" / helper.relative_to(self.scratch)).read_bytes(), helper.read_bytes())

    def test_stage_write_failure_collects_inert_child(self):
        real_replace = Path.replace
        children = []
        real_popen = subprocess.Popen

        def spawn(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child

        for failure in (2, 3):
            root = self.scratch / str(failure)
            (root / "logs").mkdir(parents=True)
            calls = 0

            def replace(path, target):
                nonlocal calls
                calls += 1
                if calls == failure:
                    raise OSError("injected receipt rename failure")
                return real_replace(path, target)

            code = "import time; time.sleep(3)" if failure == 2 else "pass"
            args = [str(RUNNER), str(root), str(root), "inert", "4", sys.executable, "-IB", "-c", code]
            errors = io.StringIO()
            try:
                with patch.object(sys, "argv", args), patch.object(Path, "replace", replace), \
                        patch.object(runner, "size_kib", return_value=0), patch.object(subprocess, "Popen", side_effect=spawn), \
                        contextlib.redirect_stderr(errors):
                    self.assertEqual(runner.main(), 1)
                child = children[-1]
                self.assertTrue(runner.group_absent(child.pid))
                receipt = read(root / "logs/inert.json")
                if failure == 2:
                    self.assertEqual((receipt["exit"], receipt["custody"]), (-signal.SIGKILL, "closed"))
                else:
                    self.assertEqual(receipt["custody"], "UNKNOWN")
                    self.assertIn("exit=0 custody=closed", errors.getvalue())
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=5)

    def test_failed_interrupt_write_and_unknown_fake_group(self):
        (self.scratch / "logs").mkdir()
        for version in ("old", "new", "new-persisted"):
            with self.subTest(version=version):
                launch = original(RUNNER, "old_runner")["main"] if version == "old" else runner.main
                stage = self.scratch / f"logs/{version}.json"
                real_replace = Path.replace

                def replace(path, target):
                    if version != "new-persisted" and stage.exists() and "interrupted" in read(path):
                        raise OSError("injected interrupt or terminal write failure")
                    return real_replace(path, target)

                args = [str(RUNNER), str(self.scratch), str(self.scratch), version, "0", "fake-command"]
                with patch.object(sys, "argv", args), patch.object(subprocess, "Popen") as popen, \
                        patch.object(Path, "replace", replace), patch.object(os, "killpg", side_effect=PermissionError) as kill, \
                        patch.dict(launch.__globals__, {"size_kib": lambda *_: 0}), \
                        patch("time.sleep"), contextlib.redirect_stderr(io.StringIO()):
                    child = popen.return_value
                    child.pid, child.returncode = 987654, -signal.SIGKILL
                    child.poll.return_value = None
                    if version == "old":
                        with self.assertRaisesRegex(OSError, "injected interrupt"):
                            launch()
                        kill.assert_not_called()
                        child.wait.assert_not_called()
                    else:
                        self.assertEqual(launch(), 1)
                        kill.assert_any_call(child.pid, signal.SIGKILL)
                        kill.assert_any_call(child.pid, 0)
                        child.wait.assert_called_once_with(timeout=5)
                    receipt = read(stage)
                    self.assertEqual(receipt["custody"], "UNKNOWN")
                    if version == "new-persisted":
                        self.assertEqual(receipt["exit"], -signal.SIGKILL)
                        self.assertTrue(receipt["collectionErrors"])


if __name__ == "__main__":
    FIXTURE = Path(sys.argv.pop(1)).resolve(strict=True)
    unittest.main()
