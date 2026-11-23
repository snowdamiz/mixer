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

    def create_android(self):
        toolchain = dict(schema=1, sdk_id="export-test", abi="arm64-v8a", min_api=28,
                         target_api=37, swift_version="fixture", javac_version="fixture",
                         java_version="fixture", python_version="fixture", tools={},
                         metadata={}, distributions={}, sdk_search_path="fixture")
        self.script("python3", 'test "$2" = inspect\nprintf "%s\\n" '
                    + shlex.quote(json.dumps(toolchain)) + "\n")
        self.create("--platform", "android", "--android-host", "public-v4",
                    "--android-adapter-path", REPO / "native/android", env=self.tool_env)

    def upgrade(self, sdk=None, *extra, env=None):
        return self.cli("upgrade", self.destination, "--directory", self.project,
                        "--sdk-path", sdk or REPO / "sdk", *extra, env=env)

    def assert_upgrade_refused(self, outcome, code):
        status, report = outcome
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], code, report)
        self.assertFalse(self.destination.exists())
        self.assert_clean_staging()
        return report

    def export(self, env=None):
        return self.cli("export", self.destination, "--directory", self.project, env=env)

    def assert_clean_staging(self):
        self.assertEqual(list(self.root.glob(".mixer-export-*")), [])

    def test_swift_identity_preserves_split_banner_and_legacy_locks(self):
        compiler = "Apple Swift version 6.4.2 (swiftlang-6.4.2.1.9 clang-2100.4.1.1)"
        target = "Target: arm64-apple-macosx27.0.0"
        driver = "swift-driver version: 1.168.6"
        canonical = f"{compiler}\n{target}\n{driver}"
        self.script("swift", r'''
test "$#" = 1 && test "$1" = --version
if test "$EXPORT_STDERR_FIRST" = 1; then
    printf '%s ' "$EXPORT_DRIVER" >&2
    /bin/sleep 0.15
    printf '%s\n%s\n' "$EXPORT_COMPILER" "$EXPORT_TARGET"
else
    printf '%s\n' "$EXPORT_COMPILER"
    /bin/sleep 0.15
    printf '%s ' "$EXPORT_DRIVER" >&2
    /bin/sleep 0.15
    printf '%s\n' "$EXPORT_TARGET"
fi
exit "${EXPORT_SWIFT_EXIT:-0}"
''')
        env = dict(self.tool_env, EXPORT_COMPILER=compiler, EXPORT_TARGET=target,
                   EXPORT_DRIVER=driver, EXPORT_STDERR_FIRST="1")
        self.create(env=env)
        lock_path = self.project / "mixer.lock"
        lock = json.loads(lock_path.read_bytes())
        split_env = dict(env, EXPORT_STDERR_FIRST="0")

        status, report = self.export(split_env)
        self.assertEqual(status, 0, report)
        self.assertEqual(lock["swiftVersion"], canonical)
        shutil.rmtree(self.destination)

        for banner in (
            f"{driver} {compiler}\n{target}",
            f"{driver}\n{compiler}\n{target}",
            f"{compiler}\n{driver} {target}",
            f"{compiler}\n{driver}\n{target}",
        ):
            with self.subTest(banner=banner):
                lock["swiftVersion"] = banner
                lock_path.write_text(json.dumps(lock))
                status, report = self.export(split_env)
                self.assertEqual(status, 0, report)
                self.assertEqual((self.destination / "mixer.lock").read_bytes(), lock_path.read_bytes())
                shutil.rmtree(self.destination)

        status, report = self.upgrade(env=split_env)
        self.assertEqual(status, 0, report)
        self.assertEqual(json.loads((self.destination / "mixer.lock").read_bytes())["swiftVersion"],
                         lock["swiftVersion"])
        shutil.rmtree(self.destination)

        for key, value in (
            ("EXPORT_COMPILER", compiler.replace("6.4.2.1.9", "6.4.2.1.8")),
            ("EXPORT_TARGET", target.replace("arm64", "x86_64")),
            ("EXPORT_DRIVER", driver.replace("1.168.6", "1.168.7")),
            ("EXPORT_DRIVER", driver + "\nunexpected output"),
            ("EXPORT_SWIFT_EXIT", "7"),
        ):
            with self.subTest(key=key, value=value):
                status, report = self.export(dict(split_env, **{key: value}))
                self.assertEqual(status, 1, report)
                self.assertEqual(report["code"], "lock.toolchain-drift", report)
                self.assertFalse(self.destination.exists())
                self.assert_clean_staging()

        for banner in (
            f"{compiler}\n{target}",
            f"{compiler}\n{driver}  {target}",
            f"{compiler}\n{driver}\n{target}\n",
        ):
            with self.subTest(banner=banner):
                lock["swiftVersion"] = banner
                lock_path.write_text(json.dumps(lock))
                status, report = self.export(split_env)
                self.assertEqual(status, 1, report)
                self.assertEqual(report["code"], "lock.toolchain-drift", report)
                self.assertFalse(self.destination.exists())
                self.assert_clean_staging()

    def test_swift_identity_accepts_a_driverless_toolchain(self):
        banner = "Swift version 6.3.3 (swift-6.3.3-RELEASE)\nTarget: arm64-apple-macosx26.0"
        self.script("swift", 'test "$#" = 1 && test "$1" = --version\nprintf "%s\\n" '
                    + shlex.quote(banner) + '\n')
        self.create(env=self.tool_env)
        self.assertEqual(json.loads((self.project / "mixer.lock").read_bytes())["swiftVersion"], banner)
        status, report = self.export(self.tool_env)
        self.assertEqual(status, 0, report)

    def test_upgrade_copies_project_files_and_verifies_the_new_lock(self):
        self.create()
        data = self.project / "OfflineWorkspace" / "draft.json"
        data.parent.mkdir()
        data.write_bytes(b'{"title":"Pressure test"}\n')
        original_lock = (self.project / "mixer.lock").read_bytes()
        incoming = self.root / "IncomingSDK"
        shutil.copytree(REPO / "sdk", incoming)
        (incoming / "upgrade-marker.txt").write_text("target SDK revision\n")

        command = ("upgrade", self.destination, "--directory", self.project, "--sdk-path", incoming)
        status, report = self.cli(*command)
        self.assertEqual(status, 0, report)
        self.assertEqual((self.project / "mixer.lock").read_bytes(), original_lock)
        self.assertEqual((self.destination / data.relative_to(self.project)).read_bytes(), data.read_bytes())
        marker = self.destination / "Generated/MixerSDK/upgrade-marker.txt"
        self.assertEqual(marker.read_bytes(), (incoming / marker.name).read_bytes())
        self.assertNotEqual(json.loads((self.destination / "mixer.lock").read_bytes())["sdkDigest"],
                            json.loads(original_lock)["sdkDigest"])

        status, report = self.cli(*command)
        self.assertNotEqual(status, 0)
        self.assertEqual(report["code"], "export.exists")
        after_upgrade = self.root / "AfterUpgrade"
        status, report = self.cli("export", after_upgrade, "--directory", self.destination)
        self.assertEqual(status, 0, report)
        self.assertEqual((after_upgrade / data.relative_to(self.project)).read_bytes(), data.read_bytes())
        self.assert_clean_staging()

    def test_upgrade_rejects_missing_ios_sources(self):
        self.create()
        incoming = self.root / "SDK"
        incoming.mkdir()
        shutil.copyfile(REPO / "sdk/Package.swift", incoming / "Package.swift")
        self.assert_upgrade_refused(self.upgrade(incoming), "snapshot.sdk")
        shutil.copytree(REPO / "sdk", incoming, dirs_exist_ok=True)
        shutil.rmtree(incoming / "Sources/MixerApple")
        self.assert_upgrade_refused(self.upgrade(incoming), "snapshot.sdk")

    def test_upgrade_requires_sources_for_declared_mixerswiftui(self):
        self.create()
        original_lock = (self.project / "mixer.lock").read_bytes()
        incoming = self.root / "SDK"
        shutil.copytree(REPO / "sdk", incoming)
        module = incoming / "Sources/MixerSwiftUI"
        shutil.rmtree(module)
        module.mkdir()
        for layout in ("empty", "missing"):
            with self.subTest(layout=layout):
                report = self.assert_upgrade_refused(self.upgrade(incoming), "snapshot.sdk")
                self.assertIn("MixerSwiftUI", report["message"])
                self.assertEqual((self.project / "mixer.lock").read_bytes(), original_lock)
            if layout == "empty":
                module.rmdir()

    def test_upgrade_accepts_legacy_sdk_and_preserves_edited_app(self):
        self.create()
        package = self.project / "Package.swift"
        edited_manifest = package.read_bytes() + b"\n// App-owned edit\n"
        package.write_bytes(edited_manifest)
        original_lock = (self.project / "mixer.lock").read_bytes()
        incoming = self.root / "LegacySDK"
        shutil.copytree(REPO / "sdk", incoming)
        shutil.rmtree(incoming / "Sources/MixerSwiftUI")
        legacy = REPO / "cli/Tests/MixerBuildTests/Fixtures/AppleProject/PreSwiftUISDK-Package.swift"
        shutil.copyfile(legacy, incoming / "Package.swift")

        override = incoming / "Package@swift-6.swift"
        shutil.copyfile(REPO / "sdk/Package.swift", override)
        report = self.assert_upgrade_refused(self.upgrade(incoming), "snapshot.sdk")
        self.assertIn("MixerSwiftUI", report["message"])
        override.unlink()

        status, report = self.upgrade(incoming)
        self.assertEqual(status, 0, report)
        self.assertEqual(package.read_bytes(), edited_manifest)
        self.assertEqual((self.destination / "Package.swift").read_bytes(), edited_manifest)
        self.assertEqual((self.project / "mixer.lock").read_bytes(), original_lock)
        sdk = self.destination / "Generated/MixerSDK"
        self.assertEqual((sdk / "Package.swift").read_bytes(), legacy.read_bytes())
        self.assertFalse((sdk / "Sources/MixerSwiftUI").exists())
        self.assert_clean_staging()

    def test_upgrade_requires_a_regular_copied_sdk_manifest(self):
        self.create()
        incoming = self.root / "SDK"
        manifest = incoming / "Package.swift"
        manifest.mkdir(parents=True)
        self.assert_upgrade_refused(self.upgrade(incoming), "snapshot.sdk")
        manifest.rmdir()
        manifest.symlink_to(REPO / "sdk/Package.swift")
        self.assert_upgrade_refused(self.upgrade(incoming), "files.symlink")

    def test_upgrade_refuses_unreadable_target_sdk_directory(self):
        self.create()
        incoming = self.root / "SDK"
        shutil.copytree(REPO / "sdk", incoming)
        unreadable = incoming / "Unreadable"
        unreadable.mkdir()
        (unreadable / "entry").touch()
        unreadable.chmod(0)
        try:
            report = self.assert_upgrade_refused(self.upgrade(incoming), "files.read")
        finally:
            unreadable.chmod(0o700)
        path, _, reason = report["message"].removeprefix("Cannot enumerate ").partition(": ")
        self.assertEqual(Path(path).resolve(), unreadable)
        self.assertTrue(reason)

    def test_upgrade_refuses_unreadable_project_directory(self):
        self.create()
        unreadable = self.project / "Unreadable"
        unreadable.mkdir()
        unreadable.chmod(0)
        try:
            report = self.assert_upgrade_refused(self.upgrade(), "files.read")
        finally:
            unreadable.chmod(0o700)
        path, _, reason = report["message"].removeprefix("Cannot enumerate ").partition(": ")
        self.assertEqual(Path(path).resolve(), unreadable)
        self.assertTrue(reason)

    def test_android_upgrade_rolls_back_after_failed_toolchain_inspection(self):
        self.create_android()
        original = {p.relative_to(self.project): p.read_bytes()
                    for p in self.project.rglob("*") if p.is_file()}
        self.script("python3", "exit 1\n")
        status, report = self.upgrade(None, "--android-adapter-path", REPO / "native/android", env=self.tool_env)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], "android.toolchain", report)
        self.assertFalse(self.destination.exists())
        self.assertEqual(original, {p.relative_to(self.project): p.read_bytes()
                                    for p in self.project.rglob("*") if p.is_file()})
        self.assert_clean_staging()

    def test_android_upgrade_keeps_modified_platform_lock(self):
        self.create_android()
        lock = self.project / "mixer.lock"
        old = json.loads(lock.read_bytes())
        old["android"]["profile"]["id"] = "mixer.android-source-pair.20"
        lock.write_text(json.dumps(old))
        platform_lock = Path("Platforms/Android/Package.resolved")
        edited_platform_lock = (self.project / platform_lock).read_bytes() + b"\n"
        (self.project / platform_lock).write_bytes(edited_platform_lock)
        status, report = self.upgrade(None, "--android-adapter-path", REPO / "native/android", env=self.tool_env)
        self.assertEqual(status, 0, report)
        self.assertEqual(json.loads(lock.read_bytes()), old)
        self.assertEqual((self.project / platform_lock).read_bytes(), edited_platform_lock)
        self.assertEqual((self.destination / platform_lock).read_bytes(), edited_platform_lock)
        new = json.loads((self.destination / "mixer.lock").read_bytes())
        self.assertNotEqual(new["android"]["profile"]["id"], old["android"]["profile"]["id"])
        self.assert_clean_staging()

    def on_final_upgrade_validation(self, action):
        self.script("swift", '''
test "$1" = --version
if test -e "$UPGRADE_PROBE.staged"; then
    ''' + action + '''
elif test -e "$UPGRADE_PROBE.source"; then
    : > "$UPGRADE_PROBE.staged"
else
    : > "$UPGRADE_PROBE.source"
fi
exec "$EXPORT_TEST_SWIFT" "$@"
''')
        return dict(self.tool_env, UPGRADE_PROBE=str(self.root / "probe"))

    def test_upgrade_checks_source_after_final_validation(self):
        self.create()
        draft = self.project / "Resources/draft"
        draft.write_text("original")
        for action in (f"printf changed > {shlex.quote(str(draft))}",
                       f"/bin/mkdir {shlex.quote(str(self.project / 'Resources/Empty'))}"):
            with self.subTest(action=action):
                env = self.on_final_upgrade_validation(action)
                self.assert_upgrade_refused(self.upgrade(env=env), "upgrade.source-changed")
                (self.root / "probe.source").unlink()
                (self.root / "probe.staged").unlink()

    def test_upgrade_checks_staged_bytes_after_final_validation(self):
        self.create()
        env = self.on_final_upgrade_validation(
            'for stage in .mixer-export-*; do printf changed > "$stage/Generated/MixerSDK/Package.swift"; done')
        self.assert_upgrade_refused(self.upgrade(env=env), "upgrade.stage-changed")

    def test_upgrade_cannot_replace_destination_that_appears_during_validation(self):
        self.create()
        ready = self.root / "created"
        destination = shlex.quote(str(self.destination))
        env = self.on_final_upgrade_validation(
            f"/bin/mkdir {destination}; /usr/bin/stat -f %i {destination} > {shlex.quote(str(ready))}")
        status, report = self.upgrade(env=env)
        self.assertEqual(status, 1, report)
        self.assertEqual(report["code"], "export.exists", report)
        self.assertEqual(self.destination.stat().st_ino, int(ready.read_text()))
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assert_clean_staging()

    def test_android_export_reaches_tool_inspection_from_exported_root(self):
        self.create_android()
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
