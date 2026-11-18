"""Use MIXER_STORE_TEST_CLI for discovery or pass the built mixer as an argument."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
MIXER = os.environ.get("MIXER_STORE_TEST_CLI")


class PublicExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if MIXER is None:
            raise unittest.SkipTest("Set MIXER_STORE_TEST_CLI to the built macOS mixer executable")
        cls.mixer = Path(MIXER).resolve(strict=True)
        if not cls.mixer.is_file() or not os.access(cls.mixer, os.X_OK):
            raise ValueError(f"Expected an executable mixer at {cls.mixer}")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="mixer-export-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / "Source"
        self.destination = self.root / "Export"
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.env = dict(os.environ, TMPDIR=str(self.root))
        swift = shutil.which("swift", path=self.env["PATH"])
        self.assertIsNotNone(swift, "The export tests need the selected Swift compiler")
        self.tool_env = dict(self.env, PATH=str(self.tools) + os.pathsep + self.env["PATH"],
                             EXPORT_TEST_SWIFT=str(Path(swift).absolute()))

    def script(self, name, body):
        path = self.tools / name
        path.write_text("#!/bin/sh\nset -eu\n" + body)
        path.chmod(0o700)
        return path

    def cli(self, *args, env=None):
        result = subprocess.run([self.mixer, *args], cwd=self.root, env=env or self.env,
                                capture_output=True, text=True)
        self.assertTrue(result.stdout, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def create(self, *extra, env=None):
        status, report = self.cli(
            "create", "App", "--directory", self.project,
            "--sdk-path", REPO / "sdk", *extra, env=env,
        )
        self.assertEqual(status, 0, report)

    def export(self, env=None):
        return self.cli("export", self.destination, "--directory", self.project, env=env)

    def assert_clean_staging(self):
        self.assertEqual(list(self.root.glob(".mixer-export-*")), [])

    def test_android_export_reaches_tool_inspection_from_exported_root(self):
        # Seed only the create-time inventory. Build uses the real exported driver.
        toolchain = dict(schema=1, sdk_id="export-test", abi="arm64-v8a", min_api=28,
                         target_api=37, swift_version="fixture", javac_version="fixture",
                         java_version="fixture", python_version="fixture", tools={},
                         metadata={}, distributions={}, sdk_search_path="fixture")
        self.script("python3", 'test "$2" = inspect\nprintf "%s\\n" '
                    + shlex.quote(json.dumps(toolchain)) + "\n")
        self.create("--platform", "android", "--android-host", "public-v4",
                    "--android-adapter-path", REPO / "native/android", env=self.tool_env)
        platform_lock = Path("Platforms/Android/Package.resolved")
        sdk_lock = self.project / "Generated/MixerSDK/Package.resolved"
        self.assertEqual((self.project / platform_lock).read_bytes(), sdk_lock.read_bytes())
        (self.project / "Resources/.empty/nested").mkdir(parents=True)
        (self.project / ".env").write_text("excluded")
        (self.project / ".env.example").write_text("exported")
        (self.project / "local.p12").write_text("excluded")
        (self.project / ".build").mkdir()
        (self.project / ".build/ignored").symlink_to(self.project)

        status, report = self.export()
        self.assertEqual(status, 0, report)
        self.assertTrue((self.destination / "Resources/.empty/nested").is_dir())
        self.assertEqual((self.destination / ".env.example").read_text(), "exported")
        self.assertTrue((self.destination / ".gitignore").is_file())
        for name in (".env", "local.p12", ".build"):
            self.assertFalse((self.destination / name).exists(), name)
        self.assertEqual((self.project / "mixer.lock").read_bytes(),
                         (self.destination / "mixer.lock").read_bytes())
        self.assertEqual((self.project / platform_lock).read_bytes(),
                         (self.destination / platform_lock).read_bytes())
        self.project.rename(self.root / "OriginalAway")
        stop = self.script("stop-before-compilation", 'printf "%s\\n" EXPORT_TEST_TOOL_VERSION\n')
        status, report = self.cli("build", "--platform", "android", "--directory", self.destination,
                                  env=dict(self.env, MIXER_SWIFT=str(stop)))
        self.assertEqual(status, 1, report)
        self.assertIn("Supported Android compiler is official Swift", report["output"])
        self.assertEqual(Path(report["command"][-1]).resolve(), self.destination)
        self.assertEqual(list(self.destination.glob("**/*.apk")), [])

        # Older exports have the same admitted SDK and driver but no platform lock.
        exported_lock = self.destination / platform_lock
        original_lock = exported_lock.read_bytes()
        exported_lock.unlink()
        status, report = self.cli("build", "--platform", "android", "--directory", self.destination,
                                  env=dict(self.env, MIXER_SWIFT=str(stop)))
        self.assertEqual(status, 1, report)
        self.assertIn("Supported Android compiler is official Swift", report["output"])
        self.assertEqual(exported_lock.read_bytes(), original_lock)
        self.assertEqual(list(exported_lock.parent.glob(".mixer-dependencies-*")), [])
        self.assert_clean_staging()

    def test_unreadable_source_fails_with_path_and_no_destination(self):
        self.create()
        unreadable = self.project / "Unreadable"
        unreadable.mkdir()
        (unreadable / "entry").write_text("must not be silently dropped")
        unreadable.chmod(0)
        try:
            status, report = self.export()
        finally:
            unreadable.chmod(0o700)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], "files.read", report)
        path, _, reason = report["message"].removeprefix("Cannot enumerate ").partition(": ")
        self.assertEqual(Path(path).resolve(), unreadable)
        self.assertTrue(reason)
        self.assertFalse(self.destination.exists())
        self.assert_clean_staging()

    def test_changed_sdk_after_source_verification_fails_before_publication(self):
        self.create()
        sdk = self.project / "Generated/MixerSDK/Package.swift"
        self.script("swift", 'test "$1" = --version\nprintf "%s\\n" "// changed" > '
                    + shlex.quote(str(sdk)) + '\nexec "$EXPORT_TEST_SWIFT" "$@"\n')
        status, report = self.export(self.tool_env)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], "lock.sdk-drift", report)
        self.assertEqual(sdk.read_text(), "// changed\n")
        self.assertFalse(self.destination.exists())
        self.assert_clean_staging()

    def test_competing_exports_publish_once_and_clean_private_stages(self):
        self.create()
        self.script("swift", '''
test "$1" = --version
if test -e "$EXPORT_READY.first"; then
    : > "$EXPORT_READY.staged"
    for attempt in $(/usr/bin/seq 1 100); do
        if test -e "$EXPORT_GO"; then exec "$EXPORT_TEST_SWIFT" "$@"; fi
        /bin/sleep 0.1
    done
    exit 1
fi
: > "$EXPORT_READY.first"
exec "$EXPORT_TEST_SWIFT" "$@"
''')
        go = self.root / "publish"
        writers = [self.root / "writer-a", self.root / "writer-b"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [pool.submit(self.export, dict(self.tool_env, EXPORT_GO=str(go),
                                                      EXPORT_READY=str(writer))) for writer in writers]
            try:
                deadline = time.monotonic() + 8
                while not all(writer.with_suffix(".staged").exists() for writer in writers):
                    self.assertFalse(any(attempt.done() for attempt in attempts))
                    self.assertLess(time.monotonic(), deadline, "Both exports must reach staged verification")
                    time.sleep(0.025)
                self.assertFalse(self.destination.exists())
            finally:
                go.touch()
            outcomes = sorted((attempt.result() for attempt in attempts), key=lambda outcome: outcome[0])
        self.assertEqual([status for status, _ in outcomes], [0, 1], outcomes)
        self.assertEqual(outcomes[1][1]["code"], "export.exists")
        for source in self.project.rglob("*"):
            if source.is_file():
                self.assertEqual(source.read_bytes(), (self.destination / source.relative_to(self.project)).read_bytes(), source)
        self.assert_clean_staging()

    def test_concurrent_empty_destination_keeps_its_inode(self):
        self.create()
        self.script("swift", '''
test "$1" = --version
if test -e "$EXPORT_READY"; then
    /bin/mkdir "$EXPORT_DESTINATION"
    /usr/bin/stat -f %i "$EXPORT_DESTINATION" > "$EXPORT_READY"
else
    : > "$EXPORT_READY"
fi
exec "$EXPORT_TEST_SWIFT" "$@"
''')
        ready = self.root / "ready"
        status, report = self.export(dict(self.tool_env, EXPORT_READY=str(ready),
                                          EXPORT_DESTINATION=str(self.destination)))
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], "export.exists", report)
        self.assertEqual(self.destination.stat().st_ino, int(ready.read_text()))
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assert_clean_staging()


if __name__ == "__main__":
    MIXER = Path(sys.argv.pop(1)).resolve(strict=True)
    unittest.main(verbosity=2)
