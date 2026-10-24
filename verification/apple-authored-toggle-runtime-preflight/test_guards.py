#!/usr/bin/env python3
"""Host-only safety/identity tests. Every native/process operation is mocked."""
import copy
import io
import json
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.dont_write_bytecode = True
import packet
import runtime


class Guards(unittest.TestCase):
    def setUp(self):
        scratch = packet.BASE / "runtime/test-scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.root = pathlib.Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)
        self.addCleanup(patch.stopall)
        patch.object(runtime, "OUT", self.root).start()
        patch.object(runtime, "LIFECYCLE", self.root / "lifecycle.json").start()
        self.record = patch.object(runtime, "record", return_value=self.root / "mock-event.json").start()
        self.snapshot = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-27-0": [
            {"udid": value, "state": "Shutdown", "name": "preserved", "deviceTypeIdentifier": "other"}
            for value in sorted(runtime.PROTECTED)]}}
        self.current = {"candidate": "candidate-2-directional-pan", "sourceClosureSHA256": packet.SOURCE_CLOSURE,
                        "ownedSimulator": "A0000000-0000-0000-0000-000000000001", "before": self.snapshot,
                        "frontend": {"baselinePIDs": [], "rootStartedPID": None}, "cleanedUp": False}

    def native(self, state="Booted"):
        result = copy.deepcopy(self.snapshot)
        result["devices"][runtime.RUNTIME_ID] = [{"udid": self.current["ownedSimulator"], "state": state,
            "name": runtime.DEVICE_NAME, "deviceTypeIdentifier": runtime.DEVICE_TYPE}]
        return result

    def save(self):
        runtime.write_json(runtime.LIFECYCLE, self.current)

    def archive(self, members):
        target = self.root / "test.tar.gz"
        with tarfile.open(target, "w:gz") as stream:
            for name, kind, content in members:
                item = tarfile.TarInfo(name)
                item.type = kind
                item.size = len(content)
                item.mode = 0o644
                stream.addfile(item, io.BytesIO(content) if kind == tarfile.REGTYPE else None)
        return target, {"archiveSHA256": packet.file_sha(target), "files": {}}

    def test_01_frozen_packet_all_43_files_and_19_cases(self):
        result = packet.verify_original()
        self.assertEqual((result["sealedFileCount"], result["retainedPolicyChecksPassed"]), (43, 19))

    def test_02_exact_archive_restore_and_reuse(self):
        result = packet.restore(self.root / "restored")
        self.assertTrue(result["exactManifest"])
        self.assertEqual(result, packet.restore(self.root / "restored"))

    def test_03_restored_binary_corruption_rejected(self):
        packet.restore(self.root / "restored")
        app = self.root / "restored" / packet.APP_NAME
        (app / "MixerAuthoredToggle").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            packet.verify_restored(app)

    def test_04_restore_never_overwrites_unowned_directory(self):
        destination = self.root / "exists"
        destination.mkdir()
        with self.assertRaisesRegex(ValueError, "destination exists"):
            packet.restore(destination)

    def test_05_archive_traversal_rejected(self):
        path, manifest = self.archive([("../escape", tarfile.REGTYPE, b"")])
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            packet.archive_payload(path, manifest)

    def test_06_archive_symlink_rejected(self):
        path, manifest = self.archive([(packet.APP_NAME + "/linked", tarfile.SYMTYPE, b"")])
        with self.assertRaisesRegex(ValueError, "links/special"):
            packet.archive_payload(path, manifest)

    def test_07_archive_unlisted_file_rejected(self):
        path, manifest = self.archive([(packet.APP_NAME + "/extra", tarfile.REGTYPE, b"")])
        with self.assertRaisesRegex(ValueError, "Unexpected archive file"):
            packet.archive_payload(path, manifest)

    def test_08_archive_duplicate_rejected(self):
        path, manifest = self.archive([(packet.APP_NAME, tarfile.DIRTYPE, b""), (packet.APP_NAME, tarfile.DIRTYPE, b"")])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            packet.archive_payload(path, manifest)

    def test_09_archive_digest_changed_rejected(self):
        path, manifest = self.archive([])
        manifest["archiveSHA256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            packet.archive_payload(path, manifest)

    def test_10_macho_wrong_platform_rejected(self):
        import struct
        content = struct.pack("<8I", 0xFEEDFACF, 0x0100000C, 0, 2, 1, 24, 0, 0)
        content += struct.pack("<6I", 0x32, 24, 2, 26 << 16, 27 << 16, 0)
        with self.assertRaisesRegex(ValueError, "iOS Simulator"):
            packet.macho(content)

    def test_11_protected_baseline_must_exist_shutdown(self):
        runtime.baseline_guard(self.snapshot)
        changed = copy.deepcopy(self.snapshot)
        changed["devices"]["com.apple.CoreSimulator.SimRuntime.iOS-27-0"][0]["state"] = "Booted"
        with self.assertRaisesRegex(ValueError, "active"):
            runtime.baseline_guard(changed)

    def test_12_owned_cleanup_cannot_target_protected_id(self):
        self.current["ownedSimulator"] = next(iter(runtime.PROTECTED))
        with self.assertRaisesRegex(ValueError, "baseline/protected"):
            runtime.owned_guard(self.current, self.snapshot)

    def test_13_owned_cleanup_cannot_target_identity_replacement(self):
        snapshot = self.native()
        snapshot["devices"][runtime.RUNTIME_ID][0]["name"] = "Someone else's device"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runtime.owned_guard(self.current, snapshot)

    def test_14_reject_second_active_install_before_any_native_command(self):
        self.save()
        native = patch.object(runtime, "simctl", side_effect=AssertionError("native must not run")).start()
        with self.assertRaisesRegex(ValueError, "Reuse"):
            runtime.install()
        native.assert_not_called()

    def test_15_repeated_harness_command_uses_acknowledged_barrier(self):
        docs = self.root / "Documents"
        docs.mkdir()
        patch.object(runtime, "documents", return_value=docs).start()
        def observe():
            stage = (docs / "command.txt").read_text() if (docs / "command.txt").exists() else "reset"
            (docs / "stage.txt").write_text(stage)
            return {"stage": stage, "state": {}, "events": []}
        patch.object(runtime, "observation", side_effect=observe).start()
        result = runtime.send_command("reset")
        self.assertEqual(result["stage"], "reset")
        stages = self.record.call_args[0][1]["writtenStages"]
        self.assertTrue(stages[0].startswith("runtime-barrier-"))
        self.assertEqual(stages[1], "reset")

    def test_16_unknown_harness_command_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            runtime.send_command("tap")

    def test_17_cleanup_only_recorded_device_and_preserves_baseline(self):
        self.save()
        patch.object(runtime, "native_snapshot", side_effect=[self.native(), self.snapshot]).start()
        native = patch.object(runtime, "simctl", return_value="").start()
        result = runtime.cleanup()
        self.assertTrue(result["cleanedUp"] and result["preservedExistingDeviceIDsAndStates"])
        self.assertEqual(native.call_args_list[0].args, ("shutdown", self.current["ownedSimulator"]))
        self.assertEqual(native.call_args_list[1].args, ("delete", self.current["ownedSimulator"]))

    def test_18_cleanup_failure_is_not_marked_success(self):
        self.save()
        patch.object(runtime, "native_snapshot", side_effect=[self.native(), self.native()]).start()
        patch.object(runtime, "simctl", return_value="").start()
        with self.assertRaisesRegex(ValueError, "cleanup incomplete"):
            runtime.cleanup()
        self.assertFalse(packet.read_json(runtime.LIFECYCLE)["cleanedUp"])

    def test_19_cleanup_preserves_preexisting_frontend(self):
        self.current["frontend"]["baselinePIDs"] = [111]
        self.save()
        patch.object(runtime, "native_snapshot", side_effect=[self.snapshot, self.snapshot]).start()
        terminate = patch.object(runtime.os, "kill").start()
        self.assertTrue(runtime.cleanup()["cleanedUp"])
        terminate.assert_not_called()

    def test_20_cleanup_rejects_frontend_pid_reuse(self):
        self.current["frontend"].update(rootStartedPID=222, identity="old start pinned executable")
        self.save()
        patch.object(runtime, "native_snapshot", return_value=self.snapshot).start()
        patch.object(runtime, "frontend_identity", return_value="different start pinned executable").start()
        terminate = patch.object(runtime.os, "kill").start()
        with self.assertRaisesRegex(ValueError, "PID identity changed"):
            runtime.cleanup()
        terminate.assert_not_called()

    def test_21_capture_cannot_overwrite_evidence(self):
        patch.object(runtime, "observation", return_value={"state": {}, "events": []}).start()
        runtime.capture("one")
        with self.assertRaisesRegex(ValueError, "already exists"):
            runtime.capture("one")

    def test_22_installer_cleans_owned_instance_on_boot_failure(self):
        patch.object(runtime, "verify_handoff").start()
        patch.object(runtime, "verify_original", return_value={}).start()
        patch.object(runtime, "restore", return_value={}).start()
        patch.object(runtime, "tool_fingerprints", return_value={}).start()
        patch.object(runtime, "run", return_value=type("R", (), {"stdout": "Xcode 26.6\nBuild version test\n"})()).start()
        patch.object(runtime, "frontend_pids", return_value=[]).start()
        patch.object(runtime, "native_snapshot", side_effect=[self.snapshot, self.native(), self.native(), self.snapshot]).start()
        def native(*args, **kwargs):
            if args[0] == "list":
                return json.dumps({"runtimes": [{"isAvailable": True, "identifier": runtime.RUNTIME_ID, "version": "26.5",
                    "buildversion": "23F77", "supportedDeviceTypes": [{"identifier": runtime.DEVICE_TYPE}]}]})
            if args[0] == "create":
                return self.current["ownedSimulator"]
            if args[0] == "boot":
                raise RuntimeError("simulated boot failure")
            return ""
        patch.object(runtime, "simctl", side_effect=native).start()
        with self.assertRaisesRegex(RuntimeError, "simulated boot failure"):
            runtime.install()
        result = packet.read_json(runtime.LIFECYCLE)
        self.assertTrue(result["cleanedUp"] and result["ownedDeviceAbsent"])

    def test_23_failed_native_self_tests_are_not_a_pass(self):
        docs = self.root / "Documents"
        docs.mkdir()
        patch.object(runtime, "documents", return_value=docs).start()
        def observe():
            stage = (docs / "command.txt").read_text() if (docs / "command.txt").exists() else "initial"
            (docs / "stage.txt").write_text(stage)
            return {"stage": stage, "state": {}, "events": [], "checks": ([{"pass": False}] * 12 if stage == "self-tests" else [])}
        patch.object(runtime, "observation", side_effect=observe).start()
        with self.assertRaisesRegex(ValueError, "12 passing checks"):
            runtime.send_command("self-tests")

    def test_24_cleanup_stops_only_registered_unchanged_frontend(self):
        self.current["frontend"].update(rootStartedPID=222, identity="same start pinned executable")
        self.save()
        patch.object(runtime, "native_snapshot", side_effect=[self.snapshot, self.snapshot]).start()
        patch.object(runtime, "frontend_identity", side_effect=["same start pinned executable", None, None]).start()
        terminate = patch.object(runtime.os, "kill").start()
        self.assertTrue(runtime.cleanup()["cleanedUp"])
        terminate.assert_called_once_with(222, runtime.signal.SIGTERM)


if __name__ == "__main__":
    unittest.main(verbosity=2)
