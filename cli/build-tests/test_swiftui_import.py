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
        assert result.returncode == exit_code, (result.returncode, result.stdout, result.stderr)
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
    assert scoped_diagnostics == expected_diagnostics, result.stderr
    print("\n".join(scoped_diagnostics))

    description = work / "description.json"
    description.write_text(run(
        "xcrun", "swift", "package", "--package-path", package, "--scratch-path", work / "swiftpm",
        "describe", "--type", "json",
    ).stdout, encoding="utf-8")
    output = work / "report.json"
    report = json.loads(run(mixer, "import", package, "--swiftpm-description", description, "--output", output).stdout)
    assert report == json.loads(output.read_bytes())
    plain_report = json.loads(run(mixer, "import", package).stdout)
    assert plain_report["findings"] == report["findings"]
    assert plain_report["swiftUISubset"] == report["swiftUISubset"]
    assert (report["schema"], report["authority"], report["technicalEligibility"]) == (1, "advisory-only", "unverified")
    assert report["swiftUISubset"]["scopedImportCounts"] == Counter(f"SwiftUI.{symbol}" for _, _, symbol in EXPECTED)
    modules = {module["name"]: module for module in report["swiftPackage"]["modules"]}
    assert modules["SharedFeature"]["sourceClassification"] == "compiler-review"
    assert modules["AppleShell"]["sourceClassification"] == "platform-specific"
    assert modules["AppleShell"]["localDependencies"][0]["module"] == "SharedFeature"
    assert all("symbol" not in finding for finding in modules["AppleShell"]["findings"])
    assert modules["GapFeature"]["sourceClassification"] == "shared-after-api-adaptation"
    findings = [finding for finding in report["findings"] if finding["category"] == "swiftui-subset-gap"]
    assert [(finding["file"], finding["line"], finding["column"], finding["symbol"]) for finding in findings] == [
        (str(gap.relative_to(package)), line, column, f"SwiftUI.{symbol}") for line, column, symbol in EXPECTED
    ]
    for path, source in files.items():
        assert path.read_bytes() == source
        print(hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(package))
    print("PASS unchanged dual-compiled feature, Apple shell distinction, and exact scoped import counts")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    scratch = REPO / "verification/local"
    scratch.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(dir=scratch, prefix="gc1-import-fixture.")).resolve()
    try:
        verify(Path(sys.argv[1]).resolve(strict=True), work)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        print(f"Interrupted fixture command. Preserved scratch at {work}", file=sys.stderr)
        raise
    except BaseException:
        shutil.rmtree(work)
        raise
    else:
        shutil.rmtree(work)
