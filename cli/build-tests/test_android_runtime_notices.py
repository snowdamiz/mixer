"""Exercise the Android notice selector and check a locally built unsigned APK."""

import io
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

DRIVER = Path(__file__).resolve().parents[1] / "Sources/MixerBuild/Resources/android-build.py"
NOTICE_PATHS = {
    "third-party-notices/Swift-SDK-LICENSE.txt": "swift-resources/usr/share/swift/LICENSE.txt",
    "third-party-notices/Android-NDK-NOTICE.txt": "android-ndk-r27d/NOTICE",
    "third-party-notices/Android-NDK-NOTICE.toolchain.txt": "android-ndk-r27d/NOTICE.toolchain",
}
RUNTIME_RELATIVE = "swift-resources/usr/lib/swift-aarch64/android"
NDK_RELATIVE = "android-ndk-r27d/toolchains/llvm/prebuilt/darwin-x86_64"
NDK_LIBS = "sysroot/usr/lib/aarch64-linux-android"


class AndroidRuntimeNoticesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.artifact = Path(self.temp.name).resolve()
        with patch.dict(os.environ, {"MIXER_ANDROID_ARTIFACT_PATH": str(self.artifact)}):
            self.driver = runpy.run_path(str(DRIVER))
        self.runtime = self.artifact / RUNTIME_RELATIVE
        self.ndk = self.artifact / NDK_RELATIVE / NDK_LIBS
        self.expected = {}
        for index, (entry, relative) in enumerate(NOTICE_PATHS.items()):
            path = self.artifact / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            self.expected[entry] = f"Toolchain notice {index}\n".encode()
            path.write_bytes(self.expected[entry])

    def test_notice_set_follows_runtime_library_origins(self):
        select = self.driver["runtime_notices"]
        swift = {entry: data for entry, data in self.expected.items() if "/Swift-" in entry}
        ndk = {entry: data for entry, data in self.expected.items() if "/Android-" in entry}
        self.assertEqual(select(set()), {})
        self.assertEqual(select({self.runtime}), swift)
        self.assertEqual(select({self.ndk}), ndk)
        self.assertEqual(select({self.runtime, self.ndk}), self.expected)

    def test_selected_notice_must_exist_and_be_nonempty_ordinary_file(self):
        select = self.driver["runtime_notices"]
        swift = self.artifact / NOTICE_PATHS["third-party-notices/Swift-SDK-LICENSE.txt"]
        swift.unlink()
        with self.assertRaises(FileNotFoundError):
            select({self.runtime})
        swift.write_bytes(b" \n")
        with self.assertRaisesRegex(RuntimeError, "notice is empty"):
            select({self.runtime})
        swift.unlink()
        swift.symlink_to(self.artifact / "android-ndk-r27d/NOTICE")
        with self.assertRaisesRegex(RuntimeError, "ordinary file"):
            select({self.runtime})

    def test_archive_rejects_missing_altered_and_extra_notices(self):
        verify = self.driver["verify_runtime_notices"]
        first = next(iter(NOTICE_PATHS))
        cases = [
            (self.expected, True),
            ({}, False),
            ({key: data for key, data in self.expected.items() if key != first}, False),
            ({**self.expected, first: b"altered"}, False),
            ({**self.expected, "third-party-notices/unexpected": b"extra"}, False),
        ]
        for notices, accepted in cases:
            with self.subTest(entries=notices.keys(), accepted=accepted):
                buffer = io.BytesIO()
                with ZipFile(buffer, "w") as archive:
                    archive.writestr("classes.dex", b"unrelated payload")
                    for name, data in notices.items():
                        archive.writestr(name, data)
                with ZipFile(buffer) as archive:
                    if accepted:
                        verify(archive, self.expected)
                    else:
                        with self.assertRaisesRegex(RuntimeError, "notices differ"):
                            verify(archive, self.expected)

    @unittest.skipUnless(os.environ.get("MIXER_ANDROID_NOTICE_TEST_APK"),
                         "Set MIXER_ANDROID_NOTICE_TEST_APK to a built starter APK")
    def test_built_starter_apk_contains_exact_installed_notices(self):
        driver = runpy.run_path(str(DRIVER))
        expected = {name: (driver["ART"] / source).read_bytes()
                    for name, source in NOTICE_PATHS.items()}
        with ZipFile(os.environ["MIXER_ANDROID_NOTICE_TEST_APK"]) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIsNone(archive.testzip())
            self.assertIn("lib/arm64-v8a/libswiftCore.so", names)
            self.assertIn("lib/arm64-v8a/libc++_shared.so", names)
            driver["verify_runtime_notices"](archive, expected)


if __name__ == "__main__":
    unittest.main()
