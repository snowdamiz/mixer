#!/usr/bin/env python3
"""Host-only installed/restored permission and immutable-content cases."""
import copy
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import packet


class PermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {}
        for key, config in packet.CONFIGS.items():
            manifest = packet.expected_manifest(key)
            cls.payloads[key] = packet.archive_payload(packet.ORIGINAL / config["folder"] / "built-app.tar.gz", manifest, config)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mixer-toggle-permission-guards-")
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name).resolve()
        self.events = []
        self.app = self.fixture("comparator")

    def fixture(self, key):
        app = self.root / packet.CONFIGS[key]["app"]
        for directory in [app, app / "Frameworks", app / "_CodeSignature"]:
            directory.mkdir(exist_ok=True); directory.chmod(0o755)
        payload, modes = self.payloads[key]
        for name, data in payload.items():
            path = app / name; path.write_bytes(data); path.chmod(modes[name])
        return app

    def reporter(self, kind, value):
        self.events.append((kind, value))

    def verify(self):
        return packet.verify_installed(self.app, "comparator", self.reporter)

    def rejection(self, reason, name):
        with self.assertRaisesRegex(packet.ValidationError, reason) as caught:
            self.verify()
        failure = caught.exception.details
        self.assertEqual(failure["failedPath"], name)
        self.assertEqual(self.events[0][0], "installed-app-inventory-before-validation")
        self.assertEqual(self.events[-1][0], "installed-app-validation-failed")
        self.assertEqual(self.events[-1][1]["failure"], failure)
        return failure

    def test_01_exact_installed_modes_pass(self):
        result = self.verify()
        self.assertTrue(result["exactManifest"])
        self.assertEqual(len(result["observedPermissions"]["entries"]), 8)
        self.assertEqual(set(result["binaryBuildVersions"]), {"MixerAuthoredToggle", "Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"})

    def test_02_readonly_normalization_passes(self):
        for path in self.app.rglob("*"):
            path.chmod(0o555 if path.is_dir() or path.name == "MixerAuthoredToggle" else 0o444)
        self.app.chmod(0o555)
        result = self.verify()
        self.assertTrue(all(row["permissionMode"] in {0o444, 0o555} for row in result["observedPermissions"]["entries"]))

    def test_03_nonexecutable_dylibs_pass(self):
        for name in ["Frameworks/libMixerCore.dylib", "Frameworks/libMixerUI.dylib"]:
            (self.app / name).chmod(0o644)
        self.assertTrue(self.verify()["exactManifest"])

    def test_04_restored_archive_does_not_accept_installed_normalization(self):
        (self.app / "Info.plist").chmod(0o444)
        self.verify()
        with self.assertRaisesRegex(packet.ValidationError, "Restored archive mode mismatch"):
            packet.verify_restored(self.app, "comparator")

    def test_05_main_must_remain_executable(self):
        (self.app / "MixerAuthoredToggle").chmod(0o644)
        failure = self.rejection("permission policy", "MixerAuthoredToggle")
        self.assertEqual(failure["observed"]["permissionOctal"], "0644")

    def test_06_main_must_retain_all_read_execute_bits(self):
        (self.app / "MixerAuthoredToggle").chmod(0o550)
        self.rejection("permission policy", "MixerAuthoredToggle")

    def test_07_special_permission_bits_rejected(self):
        (self.app / "MixerAuthoredToggle").chmod(0o4755)
        failure = self.rejection("Special permission", "MixerAuthoredToggle")
        self.assertEqual(failure["observed"]["permissionOctal"], "4755")

    def test_08_group_world_writes_rejected(self):
        (self.app / "Info.plist").chmod(0o666)
        failure = self.rejection("Group/world writable", "Info.plist")
        self.assertEqual(failure["observed"]["permissionOctal"], "0666")

    def test_09_metadata_execute_bits_rejected(self):
        (self.app / "Info.plist").chmod(0o755)
        self.rejection("permission policy", "Info.plist")

    def test_10_directory_unsafe_writes_rejected(self):
        (self.app / "Frameworks").chmod(0o777)
        self.rejection("Group/world writable", "Frameworks")

    def test_11_symlink_rejected_without_following_it(self):
        path = self.app / "Info.plist"; path.unlink()
        path.symlink_to(self.root / "absent-external")
        failure = self.rejection("path type", "Info.plist")
        self.assertEqual(failure["observed"]["type"], "symlink")

    def test_12_fifo_rejected_without_opening_it(self):
        path = self.app / "Info.plist"; path.unlink(); os.mkfifo(path)
        failure = self.rejection("path type", "Info.plist")
        self.assertEqual(failure["observed"]["type"], "special")

    def test_13_hardlinked_payload_rejected(self):
        os.link(self.app / "Info.plist", self.root / "outside-hardlink")
        failure = self.rejection("Hard-linked", "Info.plist")
        self.assertEqual(failure["observed"]["linkCount"], 2)

    def test_14_extra_file_rejected(self):
        path = self.app / ".DS_Store"; path.write_bytes(b"extra"); path.chmod(0o644)
        self.rejection("Unexpected app path", ".DS_Store")

    def test_15_missing_file_rejected(self):
        (self.app / "Info.plist").unlink()
        failure = self.rejection("Missing app path", "Info.plist")
        self.assertIsNone(failure["observed"])

    def test_16_exact_content_hash_still_required(self):
        (self.app / "Info.plist").write_bytes(b"changed")
        failure = self.rejection("payload hash", "Info.plist")
        self.assertEqual(failure["observed"]["permissionOctal"], "0644")

    def test_17_complete_inventory_is_logged_before_any_assertion(self):
        expected = packet.scan_app(self.app)
        first = next(row for row in expected["entries"] if row["path"] == ".")
        with patch.object(packet, "validate_inventory", side_effect=packet.ValidationError("forced first assertion", ".", first)):
            self.rejection("forced first assertion", ".")
        self.assertEqual(self.events[0][1]["inventory"], expected)
        self.assertEqual(len(self.events[0][1]["inventory"]["entries"]), 8)

    def test_18_verification_never_repairs_permissions(self):
        before = packet.scan_app(self.app)
        with patch.object(packet.os, "chmod", side_effect=AssertionError("must not change modes")):
            self.verify()
        self.assertEqual(packet.scan_app(self.app), before)

    def test_19_policy_matches_exact_root_selected_finite_sets(self):
        self.assertEqual(packet.INSTALLED_MODES, {"main": {0o555, 0o755}, "dylib": {0o444, 0o555, 0o644, 0o755}, "metadata": {0o444, 0o644}, "directory": {0o555, 0o755}})

    def test_20_diagnostic_app_same_bytes_and_identity_pass(self):
        app = self.fixture("diagnostic")
        result = packet.verify_installed(app, "diagnostic", self.reporter)
        self.assertEqual(result["archiveSHA256"], "0742f08641fdfa4fdf84dc4f69b0938fff79966348810758161d4c1be8582253")
        self.assertEqual(result["binaryBuildVersions"]["MixerToggleDiagnostics"]["fileType"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
