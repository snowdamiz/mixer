#!/usr/bin/env python3
"""Host guard tests. Every native/process operation is mocked or forbidden."""
import copy
import hashlib
import importlib.util
import io
import json
import pathlib
import signal
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import packet
import runtime


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mixer-toggle-diagnostic-guards-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        patch.object(runtime, "OUT", self.root).start()
        patch.object(runtime, "LIFECYCLE", self.root / "lifecycle.json").start()
        self.record = patch.object(runtime, "record", return_value=self.root / "record.json").start()
        patch.object(runtime, "frontend_pids", return_value=[111]).start()
        for name in ["run", "simctl", "native_snapshot", "process_snapshot"]:
            patch.object(runtime, name, side_effect=AssertionError("Native operation forbidden: " + name)).start()
        self.addCleanup(patch.stopall)
        self.snapshot = {"devices": {"com.apple.CoreSimulator.SimRuntime.iOS-27-0": [{"udid": key, "name": "existing", "state": "Shutdown"} for key in runtime.PROTECTED]}}
        self.identifier = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
        self.current = {"sourceClosureSHA256": runtime.SOURCE_CLOSURE, "ownedSimulator": self.identifier, "before": self.snapshot, "apps": {}, "selectedCandidate": "comparator", "ready": True, "cleanedUp": False, "frontend": {"baselinePIDs": [111], "rootStartedPID": None}}

    def save(self):
        runtime.write_json(runtime.LIFECYCLE, self.current)

    def native(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["devices"][runtime.RUNTIME_ID] = [{"udid": self.identifier, "name": runtime.DEVICE_NAME, "state": "Booted", "deviceTypeIdentifier": runtime.DEVICE_TYPE}]
        return snapshot

    def identity(self, start="Sat Oct 24 11:00:00 2026", command=None, state="S"):
        return {"pid": 222, "start": start, "command": str(runtime.SIMULATOR) if command is None else command, "state": state}

    def own_frontend(self):
        self.current["frontend"].update(rootStartedPID=222, identity=self.identity())
        return self.current["frontend"]

    def archive(self, extra=(), mode=0o644):
        config = packet.CONFIGS["comparator"]
        path = self.root / "test.tar.gz"
        data = b"payload"
        with tarfile.open(path, "w:gz") as stream:
            member = tarfile.TarInfo(config["app"] + "/Info.plist")
            member.size = len(data); member.mode = mode
            stream.addfile(member, io.BytesIO(data))
            for name, kind in extra:
                member = tarfile.TarInfo(name); member.type = kind
                stream.addfile(member)
        manifest = {"archiveSHA256": packet.file_sha(path), "files": {"Info.plist": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}}}
        return path, manifest, config

    def test_01_safe_archive_payload(self):
        path, manifest, config = self.archive()
        self.assertEqual(packet.archive_payload(path, manifest, config)[0], {"Info.plist": b"payload"})

    def test_02_traversal_rejected(self):
        args = self.archive([("MixerAuthoredToggle.app/../escape", tarfile.REGTYPE)])
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            packet.archive_payload(*args)

    def test_03_symlink_rejected(self):
        args = self.archive([("MixerAuthoredToggle.app/link", tarfile.SYMTYPE)])
        with self.assertRaisesRegex(ValueError, "links/special"):
            packet.archive_payload(*args)

    def test_04_duplicate_rejected(self):
        args = self.archive([("MixerAuthoredToggle.app/Info.plist", tarfile.REGTYPE)])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            packet.archive_payload(*args)

    def test_05_extra_file_rejected(self):
        args = self.archive([("MixerAuthoredToggle.app/extra", tarfile.REGTYPE)])
        with self.assertRaisesRegex(ValueError, "Unexpected archive file"):
            packet.archive_payload(*args)

    def test_06_mode_rejected(self):
        args = self.archive(mode=0o777)
        with self.assertRaisesRegex(ValueError, "mode"):
            packet.archive_payload(*args)

    def test_07_digest_rejected(self):
        path, manifest, config = self.archive()
        manifest["archiveSHA256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest"):
            packet.archive_payload(path, manifest, config)

    def test_08_protected_missing_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            runtime.baseline_guard({"devices": {}})

    def test_09_protected_active_rejected(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["devices"]["com.apple.CoreSimulator.SimRuntime.iOS-27-0"][0]["state"] = "Booted"
        with self.assertRaisesRegex(ValueError, "active"):
            runtime.baseline_guard(snapshot)

    def test_10_unrecorded_owned_name_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unrecorded"):
            runtime.baseline_guard(self.native())

    def test_11_baseline_and_protected_ownership_rejected(self):
        self.current["ownedSimulator"] = next(iter(runtime.PROTECTED))
        with self.assertRaisesRegex(ValueError, "baseline/protected"):
            runtime.owned_guard(self.current, self.snapshot)

    def test_12_changed_device_name_rejected(self):
        snapshot = self.native(); snapshot["devices"][runtime.RUNTIME_ID][0]["name"] = "Other project"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runtime.owned_guard(self.current, snapshot)

    def test_13_changed_device_runtime_rejected(self):
        snapshot = self.native(); snapshot["devices"]["other-runtime"] = snapshot["devices"].pop(runtime.RUNTIME_ID)
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runtime.owned_guard(self.current, snapshot)

    def test_14_second_install_rejected_before_native(self):
        self.save()
        with self.assertRaisesRegex(ValueError, "Reuse"):
            runtime.install()

    def test_15_frontend_absent_never_signalled(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", return_value=None).start()
        kill = patch.object(runtime.os, "kill").start()
        runtime.stop_frontend(frontend)
        kill.assert_not_called(); self.assertTrue(frontend["ownedFrontendAbsent"])

    def test_16_frontend_pid_reused_before_signal_rejected(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", return_value=self.identity(start="different")).start()
        kill = patch.object(runtime.os, "kill").start()
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runtime.stop_frontend(frontend)
        kill.assert_not_called()

    def test_17_frontend_command_mismatch_never_signalled(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", return_value=self.identity(command="/other/Simulator")).start()
        kill = patch.object(runtime.os, "kill").start()
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runtime.stop_frontend(frontend)
        kill.assert_not_called()

    def test_18_post_signal_zombie_label_is_only_polled(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", side_effect=[self.identity(), self.identity(command="(Simulator)", state="Z"), None]).start()
        patch.object(runtime.time, "sleep").start()
        kill = patch.object(runtime.os, "kill").start()
        runtime.stop_frontend(frontend)
        kill.assert_called_once_with(222, signal.SIGTERM)
        self.assertTrue(frontend["ownedFrontendAbsent"])

    def test_19_initial_zombie_is_not_signalled(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", side_effect=[self.identity(command="(Simulator)", state="Z"), None]).start()
        kill = patch.object(runtime.os, "kill").start()
        runtime.stop_frontend(frontend)
        kill.assert_not_called(); self.assertTrue(frontend["ownedFrontendAbsent"])

    def test_20_reused_pid_after_exit_preserved(self):
        frontend = self.own_frontend()
        replacement = self.identity(start="different", command="/other/process")
        patch.object(runtime, "process_snapshot", side_effect=[self.identity(), replacement]).start()
        kill = patch.object(runtime.os, "kill").start()
        runtime.stop_frontend(frontend)
        kill.assert_called_once_with(222, signal.SIGTERM)
        self.assertEqual(frontend["pidReusedAfterExit"], replacement)

    def test_21_signal_race_absence_is_handled(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", return_value=self.identity()).start()
        patch.object(runtime.os, "kill", side_effect=ProcessLookupError).start()
        runtime.stop_frontend(frontend)
        self.assertTrue(frontend["ownedFrontendAbsent"])

    def test_22_exit_timeout_is_not_absence(self):
        frontend = self.own_frontend()
        patch.object(runtime, "process_snapshot", return_value=self.identity()).start()
        patch.object(runtime.time, "monotonic", side_effect=[0, 9]).start()
        patch.object(runtime.os, "kill").start()
        runtime.stop_frontend(frontend)
        self.assertFalse(frontend["ownedFrontendAbsent"])

    def test_23_cleanup_only_owned_device(self):
        self.save()
        patch.object(runtime, "native_snapshot", side_effect=[self.native(), self.snapshot]).start()
        calls = patch.object(runtime, "simctl", return_value="").start()
        result = runtime.cleanup()
        self.assertTrue(result["cleanedUp"] and result["preservedExistingDeviceIDsAndStates"])
        self.assertEqual([c.args for c in calls.call_args_list], [("shutdown", self.identifier), ("delete", self.identifier)])

    def test_24_cleanup_failure_not_success(self):
        self.save()
        patch.object(runtime, "native_snapshot", return_value=self.native()).start()
        patch.object(runtime, "simctl", return_value="").start()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.cleanup()
        self.assertFalse(packet.read_json(runtime.LIFECYCLE)["cleanedUp"])

    def test_25_baseline_frontend_preserved(self):
        self.save()
        patch.object(runtime, "native_snapshot", return_value=self.snapshot).start()
        kill = patch.object(runtime.os, "kill").start()
        runtime.cleanup(); kill.assert_not_called()

    def test_26_mismatched_owned_device_is_not_deleted(self):
        self.save(); snapshot = self.native()
        snapshot["devices"][runtime.RUNTIME_ID][0]["name"] = "other"
        patch.object(runtime, "native_snapshot", return_value=snapshot).start()
        calls = patch.object(runtime, "simctl").start()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.cleanup()
        calls.assert_not_called()

    def test_27_failed_checks_cannot_be_pass(self):
        self.command_fixture(checks=[{"pass": False}] * 12)
        with self.assertRaisesRegex(ValueError, "checks failed"):
            runtime.send_command("self-tests")

    def test_28_probe_retains_failed_checks_without_acceptance(self):
        self.command_fixture(checks=[{"pass": False}] * 12)
        result = runtime.send_command("self-tests", strict=False)
        self.assertFalse(result["checksPassed"])
        self.assertTrue(all(item["pass"] is False for item in result["checks"]))

    def test_29_diagnostic_suite_requires_18_completed_checks(self):
        self.current["selectedCandidate"] = "diagnostic"
        self.command_fixture(checks=[{"pass": True}] * 18, complete=True)
        self.assertTrue(runtime.send_command("self-tests")["checksPassed"])

    def test_30_unknown_command_rejected_before_write(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            runtime.send_command("tap")
        self.assertFalse((self.root / "command.txt").exists())

    def command_fixture(self, checks, complete=False):
        self.save()
        patch.object(runtime, "documents", return_value=self.root).start()
        def observe(current=None):
            stage = (self.root / "command.txt").read_text() if (self.root / "command.txt").exists() else "initial"
            (self.root / "stage.txt").write_text(stage)
            return {"stage": stage, "state": {}, "events": [], "checks": checks if stage == "self-tests" else [], "diagnosticSuiteState": "complete" if complete else "not-run"}
        patch.object(runtime, "observation", side_effect=observe).start()

    def test_31_capture_cannot_overwrite(self):
        self.save()
        patch.object(runtime, "observation", return_value={"state": {}, "events": []}).start()
        runtime.capture("one")
        with self.assertRaisesRegex(ValueError, "already exists"):
            runtime.capture("one")

    def test_32_session_install_failure_always_attempts_cleanup(self):
        patch.object(runtime, "install", side_effect=RuntimeError("boot failed")).start()
        clean = patch.object(runtime, "cleanup").start()
        with self.assertRaisesRegex(RuntimeError, "boot failed"):
            runtime.session(30)
        clean.assert_called_once()

    def test_33_session_finish_always_attempts_cleanup(self):
        def install(): runtime.write_json(self.root / "finish-request.json", {})
        patch.object(runtime, "install", side_effect=install).start()
        clean = patch.object(runtime, "cleanup").start()
        runtime.session(30)
        clean.assert_called_once()

    def test_34_session_bounds_fail_before_install(self):
        install = patch.object(runtime, "install").start()
        with self.assertRaisesRegex(ValueError, "bound"):
            runtime.session(901)
        install.assert_not_called()

    def test_35_container_redirect_rejected(self):
        self.current["apps"]["comparator"] = {"container": str(self.root)}
        self.save()
        with self.assertRaisesRegex(ValueError, "outside"):
            runtime.documents()

    def test_36_partial_restore_rejected(self):
        destination = self.root / "restore"; destination.mkdir()
        with self.assertRaisesRegex(ValueError, "without valid app"):
            packet.restore(destination, "comparator")

    def test_37_unattributed_frontend_is_preserved_and_not_accepted_clean(self):
        self.save()
        patch.object(runtime, "native_snapshot", return_value=self.snapshot).start()
        patch.object(runtime, "frontend_pids", return_value=[111, 999]).start()
        kill = patch.object(runtime.os, "kill").start()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.cleanup()
        kill.assert_not_called()
        self.assertEqual(packet.read_json(runtime.LIFECYCLE)["frontend"]["unattributedNewPIDsPreserved"], [999])

    def test_38_session_timeout_always_attempts_cleanup(self):
        patch.object(runtime, "install").start()
        patch.object(runtime.time, "monotonic", side_effect=[0, 31, 31]).start()
        clean = patch.object(runtime, "cleanup").start()
        runtime.session(30)
        clean.assert_called_once()

    def test_39_capture_label_cannot_escape(self):
        self.save()
        with self.assertRaisesRegex(ValueError, "Invalid evidence label"):
            runtime.capture("../escape")

    def test_40_device_and_frontend_cleanup_failures_remain_recorded(self):
        self.own_frontend(); self.save()
        patch.object(runtime, "native_snapshot", return_value=self.snapshot).start()
        patch.object(runtime, "process_snapshot", return_value=self.identity(start="different")).start()
        kill = patch.object(runtime.os, "kill").start()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            runtime.cleanup()
        kill.assert_not_called()
        receipt = packet.read_json(runtime.LIFECYCLE)
        self.assertFalse(receipt["cleanedUp"])
        self.assertEqual(receipt["cleanupErrors"][0]["scope"], "frontend cleanup")


if __name__ == "__main__":
    unittest.main(verbosity=2)
