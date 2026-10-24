"""Deb822 baseline inventory parsing controls; no package execution."""
import unittest

from audit_retained import stanza


class StatusControls(unittest.TestCase):
    def test_empty_field_and_continuation_do_not_change_version(self):
        value = stanza("Package: sample\nArchitecture: arm64\nVersion: 1:2.3-4\nConffiles:\n /etc/sample abcd\nDescription: first\n second\n")
        self.assertEqual(value["Version"], "1:2.3-4")
        self.assertEqual(value["Conffiles"], "\n /etc/sample abcd")
        self.assertEqual(value["Description"], "first\n second")

    def test_epoch_and_colon_in_value_are_retained(self):
        self.assertEqual(stanza("Version: 1:2.3-4\nHomepage: https://example.invalid/x\n"),
                         {"Version": "1:2.3-4", "Homepage": "https://example.invalid/x"})


if __name__ == "__main__":
    unittest.main()
