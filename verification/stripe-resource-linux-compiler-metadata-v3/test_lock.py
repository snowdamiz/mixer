"""Negative controls for host joining native selections to signed metadata."""
import copy
import unittest

import lock_packages as candidate


def native_fixture():
    names = ("gcc", "libc6-dev", "binutils")
    records = [f"{action} {name} (4:13.2.0-7ubuntu1 Ubuntu:24.04/noble [arm64])"
               for action in ("Inst", "Conf") for name in names]
    return "\n".join(["0 upgraded, 3 newly installed, 0 to remove and 10 not upgraded."]+records)


class LockControls(unittest.TestCase):
    def setUp(self):
        self.item = {"Package": "gcc-13", "Version": "13.3.0-6ubuntu2~24.04.1", "Architecture": "arm64",
                     "Filename": "pool/main/g/gcc-13/gcc-13_13.3.0-6ubuntu2~24.04.1_arm64.deb",
                     "Size": "12345", "Installed-Size": "99", "SHA256": "a"*64,
                     "Depends": "libc6 (>= 2.38), libgcc-s1 (>= 3.0)"}

    def test_epoch_and_tilde_versions_retained_exactly(self):
        items, summary = candidate.native_selection(native_fixture())
        self.assertEqual(items["gcc"]["version"], "4:13.2.0-7ubuntu1")
        self.assertEqual(summary["newlyInstalled"], 3)
        identity = candidate.artifact_identity(self.item)
        self.assertIn("~24.04.1", identity[0])

    def test_inst_conf_missing_duplicate_or_identity_change_refuses(self):
        original = native_fixture()
        for changed in (original.replace("Conf gcc ", "Ignored gcc "),
                        original+"\nInst gcc (4:13.2.0-7ubuntu1 Ubuntu:24.04/noble [arm64])",
                        original.replace("Conf gcc (4:13.2.0-7ubuntu1", "Conf gcc (4:13.2.0-7ubuntu2")):
            with self.assertRaises(ValueError):
                candidate.native_selection(changed)

    def test_missing_root_unknown_origin_architecture_and_removal_refuse(self):
        original = native_fixture()
        for changed in (original.replace("gcc ", "another "), original.replace("Ubuntu:24.04/noble", "Other:24.04/noble"),
                        original.replace("[arm64]", "[amd64]"), original+"\nRemv libc6 [2.39]"):
            with self.assertRaises(ValueError):
                candidate.native_selection(changed)

    def test_native_summary_count_or_missing_summary_refuses(self):
        for changed in (native_fixture().replace("3 newly", "4 newly"), "\n".join(native_fixture().splitlines()[1:])):
            with self.assertRaises(ValueError):
                candidate.native_selection(changed)

    def test_signed_field_digest_size_or_architecture_refuses(self):
        for key, value in (("SHA256", "b"*63), ("Size", "67108865"), ("Size", "-1"),
                           ("Installed-Size", "unknown"), ("Architecture", "amd64")):
            changed = copy.deepcopy(self.item)
            changed[key] = value
            with self.assertRaises(ValueError):
                candidate.artifact_identity(changed)
        changed = copy.deepcopy(self.item)
        del changed["SHA256"]
        with self.assertRaises(ValueError):
            candidate.artifact_identity(changed)

    def test_package_path_traversal_origin_component_or_query_refuses(self):
        for filename in ("../artifact.deb", "/pool/main/a.deb", "pool/main/../x.deb", "pool/universe/a.deb",
                         "pool/main/a.deb?x", "pool/main/a%2f../b.deb", "pool/main/a\\b.deb", "pool/main//a.deb", "https://other/a.deb"):
            changed = copy.deepcopy(self.item)
            changed["Filename"] = filename
            with self.assertRaises(ValueError):
                candidate.artifact_identity(changed)

    def test_duplicate_field_and_orphan_continuation_refuse(self):
        for raw in (b"Package: a\nPackage: b", b" orphan\nPackage: a", b"not a field"):
            with self.assertRaises(ValueError):
                candidate.fields(raw)

    def test_multiline_empty_field_preserves_exact_full_version(self):
        parsed = candidate.fields(b"Version: 1:2.3~ubuntu1\nConffiles:\n /etc/a abcd\nDescription: x\n next")
        self.assertEqual(parsed["Version"], "1:2.3~ubuntu1")
        self.assertEqual(parsed["Conffiles"], "\n /etc/a abcd")


if __name__ == "__main__":
    unittest.main()
