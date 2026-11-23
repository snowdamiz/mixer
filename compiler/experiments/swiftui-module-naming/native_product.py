#!/usr/bin/env python3
"""Compile the published MixerSwiftUI product in a generated iOS app and its export."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import shutil
import tempfile

from replay import ALIAS, HERE, ROOT, Replay, require, sha256


APP = "NativeProduct"
BASELINE = "51b5cc47da8160d3249a46bc3fb3e480a40eac43"
FIXTURE = HERE / APP


def wire_feature(project):
    manifest = project / "Package.swift"
    stock = manifest.read_text()
    old_target = (
        '.target(name: "AppFeatures", dependencies: '
        '["AppModels", .product(name: "MixerUI", package: "MixerSDK")]),'
    )
    new_target = '''.target(
            name: "AppFeatures",
            dependencies: [
                "AppModels",
                .product(name: "MixerUI", package: "MixerSDK"),
                .product(name: "MixerSwiftUI", package: "MixerSDK"),
            ],
            swiftSettings: [.unsafeFlags(["-module-alias", "SwiftUI=MixerSwiftUI"], .when(platforms: [.iOS]))]
        ),'''
    require(stock.count(old_target) == 1, "Stock AppFeatures target changed")
    manifest.write_text(stock.replace(old_target, new_target))
    shutil.copyfile(FIXTURE / "SharedTitle.swift", project / "Sources/AppFeatures/SharedTitle.swift")
    shutil.copyfile(FIXTURE / "AppleShell.swift", project / "Platforms/iOS" / f"{APP}App.swift")


def inventory(project):
    # The CLI export excludes .mixer build state.
    files = {}
    for directory, folders, names in os.walk(project):
        folders[:] = [folder for folder in folders if folder != ".mixer"]
        for name in names:
            path = Path(directory) / name
            files[str(path.relative_to(project))] = sha256(path)
    return files


def build(replay, label, project, *, expect_shared):
    target = project / "Platforms/iOS" / f"{APP}.xcodeproj"
    derived = project / ".mixer/ios-build"
    status, output, errors = replay.run(
        label, "/usr/bin/xcodebuild", "-project", target, "-scheme", APP,
        "-configuration", "Debug", "-sdk", "iphonesimulator",
        "-destination", "generic/platform=iOS Simulator", "-derivedDataPath", derived,
        "-resultBundlePath", replay.work / f"{label}.xcresult",
        "-clonedSourcePackagesDirPath", replay.work / "xcode-packages",
        "-packageCachePath", replay.work / "xcode-package-cache", "-skipPackageUpdates",
        "-jobs", "8", "CODE_SIGNING_ALLOWED=NO", "ENABLE_DEBUG_DYLIB=NO", "build", limit=300,
    )
    if expect_shared is None:
        require(status != 0 and any("product 'MixerSwiftUI'" in line and "not found" in line
                                    for line in (output + errors).splitlines()),
                f"{label}: expected missing SDK product, see command output")
        return {"missingProduct": "MixerSwiftUI", "exit": status}
    require(status == 0, f"{label}: build exited {status}, see command output")
    run = replay.checked
    app = derived / "Build/Products/Debug-iphonesimulator" / f"{APP}.app"
    binary = app / APP
    info = plistlib.loads((app / "Info.plist").read_bytes())
    require(info["MinimumOSVersion"] == "17.0", f"{label}: unexpected Info.plist floor")
    version = run(f"{label}-vtool", "/usr/bin/xcrun", "vtool", "-show-build", binary)
    platforms = {line.split()[1] for line in version.splitlines() if line.lstrip().startswith("platform ")}
    floors = {line.split()[1] for line in version.splitlines() if line.lstrip().startswith("minos ")}
    require(platforms == {"IOSSIMULATOR"} and floors == {"17.0"}, f"{label}: unexpected Mach-O floor")
    libs = run(f"{label}-otool", "/usr/bin/xcrun", "otool", "-L", binary)
    require("SwiftUI.framework/SwiftUI" in libs, f"{label}: Apple SwiftUI is missing")
    symbols = run(f"{label}-nm", "/usr/bin/xcrun", "nm", binary)
    require("$s7SwiftUI4Text" in symbols, f"{label}: Apple SwiftUI.Text is missing")
    require(("$s11AppFeatures11SharedTitleO4makey12MixerSwiftUI4Text" in symbols) == expect_shared,
            f"{label}: unexpected MixerSwiftUI.Text linkage")
    invocations = [shlex.split(line) for line in output.splitlines() if "builtin-SwiftDriver --" in line]
    modules = {argv[argv.index("-module-name") + 1] for argv in invocations}
    alias_modules = set()
    for argv in invocations:
        if "-module-alias" in argv:
            require(tuple(argv[argv.index("-module-alias"):][:2]) == ALIAS, f"{label}: unexpected module alias")
            alias_modules.add(argv[argv.index("-module-name") + 1])
    require(alias_modules == ({"AppFeatures"} if expect_shared else set()),
            f"{label}: unexpected alias scope {alias_modules}")
    required_modules = {APP, "AppFeatures", "MixerSwiftUI"} if expect_shared else {APP, "AppFeatures"}
    require(required_modules <= modules, f"{label}: missing compiler invocations {required_modules - modules}")
    return {"binarySHA256": sha256(binary), "minOS": info["MinimumOSVersion"],
            "aliasModules": sorted(alias_modules), "linkedMixerText": expect_shared}


def execute(replay, mixer, baseline):
    run = replay.checked
    revision = run("revision", "/usr/bin/git", "rev-parse", "HEAD").strip()
    old_revision = run("baseline-revision", "/usr/bin/git", "rev-parse", baseline).strip()
    xcode = run("xcode-version", "/usr/bin/xcodebuild", "-version").strip()
    swift = run("swift-version", "/usr/bin/xcrun", "swiftc", "--version").strip()
    work = replay.work
    archive = work / "baseline.tar"
    baseline_source = work / "baseline"
    baseline_source.mkdir()
    run("archive-baseline", "/usr/bin/git", "archive", "-o", archive, old_revision, "sdk")
    run("extract-baseline", "/usr/bin/tar", "-xf", archive, "-C", baseline_source)
    old_sdk = baseline_source / "sdk"
    new_sdk = ROOT / "sdk"

    def cli(label, *args, expected_error=None):
        status, output, errors = replay.run(label, mixer, *args)
        if status != 0 and any(marker in output + errors for marker in
                               ("process.custody-", '"process.receipt"')):
            replay.record_hold({"name": label}, "CLI reported unverified nested command custody")
        if expected_error:
            require(status != 0 and expected_error in output + errors, f"{label}: unexpected CLI result")
        else:
            require(status == 0, f"{label}: CLI exited {status}, see command output")

    def create(label, sdk):
        project = work / label
        cli(f"create-{label}", "create", APP, "--sdk-path", sdk, "--directory", project)
        return project

    before = create("before", old_sdk)
    original = work / "original"
    cli("upgrade-stock", "upgrade", original, "--sdk-path", new_sdk, "--directory", before)
    for path in ("Package.swift", f"Platforms/iOS/{APP}App.swift",
                 f"Platforms/iOS/{APP}.xcodeproj/project.pbxproj"):
        require((before / path).read_bytes() == (original / path).read_bytes(),
                f"SDK upgrade changed stock project file {path}")

    engine = old_sdk / "Sources/MixerSwiftUI"
    shutil.rmtree(engine)
    legacy = work / "legacy"
    cli("upgrade-pre-pivot-sdk", "upgrade", legacy, "--sdk-path", old_sdk, "--directory", before)
    engine.mkdir()
    incomplete = work / "incomplete"
    cli("upgrade-incomplete-sdk", "upgrade", incomplete, "--sdk-path", old_sdk, "--directory", before,
        expected_error="missing Swift sources for MixerSwiftUI")
    require(not incomplete.exists(), "Upgrade published an incomplete MixerSwiftUI snapshot")

    results = {"stock": build(replay, "build-stock", before, expect_shared=False)}
    wire_feature(before)
    results["baselineShared"] = build(replay, "build-baseline-shared", before, expect_shared=None)
    wire_feature(original)
    results["shared"] = build(replay, "build-shared", original, expect_shared=True)

    exported = work / "exported"
    cli("export", "export", exported, "--directory", original)
    files = inventory(original)
    require(files == inventory(exported), "CLI export changed the project bytes")
    shutil.rmtree(original)
    results["exported"] = build(replay, "build-exported", exported, expect_shared=True)
    (replay.directory / "result.json").write_text(json.dumps({
        "revision": revision, "baseline": old_revision, "xcode": xcode, "swift": swift,
        "cliSHA256": sha256(mixer), "rootManifestSHA256": sha256(ROOT / "Package.swift"),
        "generatorSHA256": sha256(ROOT / "cli/Sources/MixerBuild/ProjectGenerator.swift"),
        "exportedFiles": files, "results": results,
    }, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True, help="CLI built from the checkout under test")
    parser.add_argument("--baseline", default=BASELINE, help="Revision before the SDK exposes MixerSwiftUI")
    args = parser.parse_args()
    mixer = args.mixer.resolve(strict=True)
    local = ROOT / "verification/local"
    local.mkdir(parents=True, exist_ok=True)
    receipt = Path(tempfile.mkdtemp(prefix="up5-native-product-", dir=local))
    print(receipt, flush=True)
    replay = Replay(receipt)
    try:
        execute(replay, mixer, args.baseline)
    finally:
        if not replay.hold:
            shutil.rmtree(replay.work)
    print("PASS: stock app and exported shared-feature app compiled at iOS 17.0.")


if __name__ == "__main__":
    main()
