from pathlib import Path
import importlib.util
import unittest

spec=importlib.util.spec_from_file_location('apple_toolchain',Path(__file__).parents[1]/'verify-apple-toolchain.py')
apple=importlib.util.module_from_spec(spec);spec.loader.exec_module(apple)


class ToolchainTests(unittest.TestCase):
    def test_observed_ci_swift61_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'required minimum'):
            apple.verify_versions('Xcode 26.3\nBuild version 17C529',
                                  'Apple Swift version 6.1 (swiftlang-6.1)\nTarget: arm64-apple-macosx15.0',
                                  '26.3','17C529')

    def test_supported_patch_and_two_digit_minor_are_accepted(self):
        for version in ['6.2','6.2.3','6.10.1','7.0.0']:
            with self.subTest(version=version):
                self.assertGreaterEqual(apple.verify_versions('Xcode 26.3\nBuild version 17C529',
                    'swift-driver version: 1.2 Apple Swift version '+version+' (release)',
                    '26.3','17C529'),(6,2,0))

    def test_default_or_replaced_xcode_pin_fails(self):
        for value in ['Xcode 16.4\nBuild version 16F6','Xcode 26.3\nBuild version changed','Xcode 26.4\nBuild version 17C529']:
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'pinned'):
                apple.verify_versions(value,'Apple Swift version 6.2.3 (release)','26.3','17C529')

    def test_unknown_and_development_version_text_fails(self):
        for value in ['', '6.2.3', 'Apple Swift version 6.2-dev (snapshot)', 'tool failed']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                apple.swift_version(value)


if __name__=='__main__':
    unittest.main()
