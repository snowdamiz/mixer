"""Official build-for-testing only; no native instance is created or queried."""
import json
import pathlib
import sys
import run

BASE, ROOT = run.BASE, run.ROOT
h = run.inherited
assert not (BASE / "packet-seal.json").exists(), "Sealed preparation is immutable"
commands = h.Commands(BASE / "runner-build-commands.json")
files = {str(p.relative_to(ROOT)): run.sha(p) for p in sorted((BASE / "harness").rglob("*")) if p.is_file()}
versions = {}
for key, argv in {"xcode": [str(h.DEVELOPER / "usr/bin/xcodebuild"), "-version"],
                  "swift": [str(h.DEVELOPER / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"), "--version"],
                  "python": [sys.executable, "--version"]}.items():
    versions[key] = commands.run(argv)[1]
assert versions["xcode"].startswith("Xcode 26.6\n")
commands.run([str(h.DEVELOPER / "usr/bin/xcodebuild"), "build-for-testing", "-project",
              str(BASE / "harness/MixerToggleUITests.xcodeproj"), "-scheme", "MixerToggleUITests",
              "-sdk", "iphonesimulator", "-destination", "generic/platform=iOS Simulator",
              "-derivedDataPath", str(BASE / "build"), "CODE_SIGNING_ALLOWED=NO", "ARCHS=arm64"], timeout=180)
assert all(run.sha(ROOT / n) == d for n, d in files.items())
products = h.tree(h.PRODUCTS)
tool_paths = [h.DEVELOPER / "usr/bin/xcodebuild", h.DEVELOPER / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc",
              h.DEVELOPER / "Platforms/iPhoneSimulator.platform/Developer/SDKs/iPhoneSimulator26.5.sdk/SDKSettings.json",
              pathlib.Path("/usr/bin/xcrun"), pathlib.Path("/usr/bin/codesign"), pathlib.Path(sys.executable).resolve()]
manifest = {"schema": "mixer.apple-toggle.native-interruption-runner.1", "sourceFiles": files,
            "products": products, "productTreeSHA256": run.hashlib.sha256(h.json_bytes(products)).hexdigest(),
            "productArchiveSHA256": h.archive_products(products), "versions": versions,
            "toolFiles": {str(p): run.sha(p) for p in tool_paths}, "nativeExecution": False}
h.write(BASE / "build-products-manifest.json", manifest)
print(json.dumps({"status": "official-runner-build-passed-native-not-run", "products": len(products), "productTreeSHA256": manifest["productTreeSHA256"]}))
