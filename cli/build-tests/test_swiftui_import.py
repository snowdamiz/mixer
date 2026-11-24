"""Run with a built mixer on macOS: python3 -B cli/build-tests/test_swiftui_import.py /path/to/mixer"""

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
PACKAGE = """// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "MigrationExample", platforms: [.iOS(.v17)], targets: [
    .target(name: "SharedFeature"),
    .target(name: "GapFeature"),
    .target(name: "AppleShell", dependencies: ["SharedFeature"]),
])
"""
UP5_SHARED = REPO / "compiler/experiments/swiftui-native-core/HostReplay/SharedScreen.swift"
APPLE = """import UIKit
import SwiftUI
import struct SwiftUI.ScrollView
import SharedFeature
@MainActor func makeScreen() -> UIViewController {
    UIHostingController(rootView: ScrollView { Screen(rows: [Row(1, "Notes")]) })
}
"""
GAPS = """import SwiftUI
import struct SwiftUI.ScrollView; import struct SwiftUI.ScrollView
import struct SwiftUI.NavigationStack
struct GapScreen: View {
    var body: some View { ScrollView { NavigationStack { Text("Notes") } } }
}
"""
EXPECTED = [(2, 15, "ScrollView"), (2, 49, "ScrollView"), (3, 15, "NavigationStack")]


def verify(mixer, work):
    check = unittest.TestCase()
    package = work / "Sample"
    shared = package / "Sources/SharedFeature/SharedScreen.swift"
    apple = package / "Sources/AppleShell/Shell.swift"
    gap = package / "Sources/GapFeature/GapScreen.swift"
    files = {
        package / "Package.swift": PACKAGE.encode(),
        shared: UP5_SHARED.read_bytes(),
        apple: APPLE.encode(),
        gap: GAPS.encode(),
    }
    for path, source in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source)
    for directory in ("tmp", "module-cache", "apple-modules", "mixer-modules"):
        (work / directory).mkdir()
    env = dict(os.environ, TMPDIR=str(work / "tmp"), LC_ALL="C",
               SWIFTPM_MODULECACHE_OVERRIDE=str(work / "module-cache"))

    def run(*argv, exit_code=0):
        print(shlex.join(map(str, argv)), flush=True)
        result = subprocess.run(argv, cwd=REPO, env=env, capture_output=True, text=True, timeout=60)
        check.assertEqual(exit_code, result.returncode, result.stdout + result.stderr)
        return result

    print("Source base", run("git", "rev-parse", "HEAD").stdout.strip())
    print(run("xcrun", "--sdk", "iphoneos", "swiftc", "--version").stdout.strip())
    sdk = run("xcrun", "--sdk", "iphoneos", "--show-sdk-path").stdout.strip()
    compiler = ("xcrun", "--sdk", "iphoneos", "swiftc", "-swift-version", "6",
                "-target", "arm64-apple-ios17.0", "-sdk", sdk, "-module-cache-path", work / "module-cache")
    apple_modules = work / "apple-modules"
    mixer_modules = work / "mixer-modules"

    def emit_module(module, modules, *sources, extra=()):
        run(*compiler, "-package-name", "Mixer", "-parse-as-library", "-emit-module",
            "-module-name", module, "-I", modules, "-emit-module-path", modules / f"{module}.swiftmodule",
            *extra, *sources)

    for module in ("MixerCore", "MixerUI", "MixerSwiftUI"):
        sources = sorted((REPO / "sdk/Sources" / module).glob("*.swift"))
        for source in sources:
            print(hashlib.sha256(source.read_bytes()).hexdigest(), source.relative_to(REPO))
        emit_module(module, mixer_modules, *sources)
    alias = ("-I", mixer_modules, "-module-alias", "SwiftUI=MixerSwiftUI")
    emit_module("SharedFeature", apple_modules, shared)
    run(*compiler, *alias, "-typecheck", shared)
    run(*compiler, "-I", apple_modules, "-typecheck", apple)
    run(*compiler, "-typecheck", gap)
    result = run(*compiler, *alias, "-typecheck", gap, exit_code=1)
    expected_diagnostics = [
        f"{gap}:{line}:{column}: error: struct '{symbol}' does not exist in module 'SwiftUI'"
        for line, column, symbol in EXPECTED
    ]
    scoped_diagnostics = [line for line in result.stderr.splitlines()
                          if line.startswith(f"{gap}:") and "does not exist in module" in line]
    check.assertEqual(expected_diagnostics, scoped_diagnostics, result.stderr)
    print("\n".join(scoped_diagnostics))

    description = work / "description.json"
    description.write_text(run(
        "xcrun", "swift", "package", "--package-path", package, "--scratch-path", work / "swiftpm",
        "describe", "--type", "json",
    ).stdout, encoding="utf-8")
    output = work / "report.json"
    report = json.loads(run(mixer, "import", package, "--swiftpm-description", description, "--output", output).stdout)
    check.assertEqual(report, json.loads(output.read_bytes()))
    plain_report = json.loads(run(mixer, "import", package).stdout)
    check.assertEqual(plain_report["findings"], report["findings"])
    check.assertEqual(plain_report["swiftUISubset"], report["swiftUISubset"])
    check.assertEqual((1, "advisory-only", "unverified"),
                      (report["schema"], report["authority"], report["technicalEligibility"]))
    check.assertEqual(Counter(f"SwiftUI.{symbol}" for _, _, symbol in EXPECTED),
                      report["swiftUISubset"]["scopedImportCounts"])
    modules = {module["name"]: module for module in report["swiftPackage"]["modules"]}
    check.assertEqual("compiler-review", modules["SharedFeature"]["sourceClassification"])
    check.assertEqual("platform-specific", modules["AppleShell"]["sourceClassification"])
    check.assertEqual("SharedFeature", modules["AppleShell"]["localDependencies"][0]["module"])
    check.assertFalse(any("symbol" in finding for finding in modules["AppleShell"]["findings"]))
    check.assertEqual("shared-after-api-adaptation", modules["GapFeature"]["sourceClassification"])
    findings = [finding for finding in report["findings"] if finding["category"] == "swiftui-subset-gap"]
    check.assertEqual(
        [(str(gap.relative_to(package)), line, column, f"SwiftUI.{symbol}") for line, column, symbol in EXPECTED],
        [(finding["file"], finding["line"], finding["column"], finding["symbol"]) for finding in findings],
    )
    for path, source in files.items():
        check.assertEqual(source, path.read_bytes())
        print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(package))
    print("PASS unchanged dual-compiled feature, Apple shell distinction, and exact scoped import counts")


def replay(mixer):
    scratch = REPO / "verification/local"
    scratch.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=scratch, prefix="gc1-import-fixture.")).resolve()
    try:
        verify(Path(mixer).resolve(strict=True), work)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        print(f"Interrupted fixture command. Preserved scratch at {work}", file=sys.stderr)
        raise
    except BaseException:
        shutil.rmtree(work)
        raise
    else:
        shutil.rmtree(work)


class SwiftUIImportTests(unittest.TestCase):
    def test_compiler_and_importer_agree_on_scoped_imports(self):
        mixer = os.environ.get("MIXER_STORE_TEST_CLI")
        if not mixer:
            self.skipTest("Set MIXER_STORE_TEST_CLI to the built macOS mixer executable")
        replay(mixer)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    replay(sys.argv[1])
