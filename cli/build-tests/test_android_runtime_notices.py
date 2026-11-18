"""Exercise the Android notice selector and check a locally built unsigned APK."""

import hashlib
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
ICU_LIBRARY = "lib_FoundationICU.so"
ICU_LIBRARY_SHA256 = "41171d3eed0f99b2057b9b528c14a4ad27d07f1e102d106facfcd0db8faf2a4a"
ICU_NOTICE = "third-party-notices/Apple-ICU-76.1-LICENSE.txt"
ICU_NOTICE_SHA256 = "92841ff27a1b2d1030b00e0958af4d1f70353ff42c5dad7041f1950e909ccc5e"
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
        self.libdir = self.artifact / "packaged-libraries"
        self.libdir.mkdir()
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
        self.assertEqual(select(set(), self.libdir), {})
        self.assertEqual(select({self.runtime}, self.libdir), swift)
        self.assertEqual(select({self.ndk}, self.libdir), ndk)
        self.assertEqual(select({self.runtime, self.ndk}, self.libdir), self.expected)

    def test_selected_notice_must_exist_and_be_nonempty_ordinary_file(self):
        select = self.driver["runtime_notices"]
        swift = self.artifact / NOTICE_PATHS["third-party-notices/Swift-SDK-LICENSE.txt"]
        swift.unlink()
        with self.assertRaises(FileNotFoundError):
            select({self.runtime}, self.libdir)
        swift.write_bytes(b" \n")
        with self.assertRaisesRegex(RuntimeError, "notice is empty"):
            select({self.runtime}, self.libdir)
        swift.unlink()
        swift.symlink_to(self.artifact / "android-ndk-r27d/NOTICE")
        with self.assertRaisesRegex(RuntimeError, "ordinary file"):
            select({self.runtime}, self.libdir)

    def test_unknown_packaged_icu_is_refused(self):
        (self.libdir / ICU_LIBRARY).write_bytes(b"unverified ICU library")
        with self.assertRaisesRegex(RuntimeError, "no verified notice binding"):
            self.driver["runtime_notices"]({self.runtime}, self.libdir)

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
    def test_built_starter_apk_contains_exact_runtime_notices(self):
        driver = runpy.run_path(str(DRIVER))
        expected = {name: (driver["ART"] / source).read_bytes()
                    for name, source in NOTICE_PATHS.items()}
        with ZipFile(os.environ["MIXER_ANDROID_NOTICE_TEST_APK"]) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            self.assertIsNone(archive.testzip())
            self.assertIn("lib/arm64-v8a/libswiftCore.so", names)
            self.assertIn("lib/arm64-v8a/libc++_shared.so", names)
            icu_library = archive.read("lib/arm64-v8a/" + ICU_LIBRARY)
            self.assertEqual(icu_library, (driver["RUNTIME"] / ICU_LIBRARY).read_bytes())
            self.assertEqual(hashlib.sha256(icu_library).hexdigest(), ICU_LIBRARY_SHA256)
            expected[ICU_NOTICE] = archive.read(ICU_NOTICE)
            self.assertEqual(hashlib.sha256(expected[ICU_NOTICE]).hexdigest(), ICU_NOTICE_SHA256)
            driver["verify_runtime_notices"](archive, expected)


if __name__ == "__main__":
    unittest.main()
