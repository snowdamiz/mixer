#!/usr/bin/env python3
"""Assemble the isolated FieldLog source overlay, sign it and cross-build XCTest."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MIXER = "79233ba123a394459b792beac648138808cd0930"
FIELDLOG = "552559d2d3278abb9b1aa7dcf0288102c09a202b"
PACKAGES = ["capability-activation", "experimental-capability-runtime", "runtime-identity", "sdk", "updates"]
TEST = "FieldLogUITests/FieldLogSignedOTATests/testSignedBaselineReviewRollbackAndOfflineReopen"
ORIGINAL_PROVENANCE = "fieldlog-compact-abi2-41a05264"
ORIGINAL_PAIR = {
    "baseline": {"bytes": 2757, "sha256": "7429ae900e0624570b8a0e4f024098fda79e8cb25bfa27132933e2a7939f0dfb"},
    "reviewed": {"bytes": 2790, "sha256": "eff19ec5956886c919f5ec00b1a3bd123a491ed4c7623ceed7bec7991595389d"},
}
DEPENDENCIES = [
    {"id": "mixer.guest-ui-event-v1", "version": "1",
     "artifact_sha256": "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"},
    {"id": "mixer.guest-ui-native-header-v1", "version": "1",
     "artifact_sha256": "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"},
]

def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()

def load_pair(args):
    raw = args.pair_manifest.read_bytes()
    checksum = hashlib.sha256(raw).hexdigest()
    if checksum != args.pair_manifest_sha256:
        raise ValueError("Pair manifest SHA-256 mismatch")
    manifest = json.loads(raw)
    if manifest["fieldlogRevision"] != FIELDLOG:
        raise ValueError("Pair manifest has the wrong FieldLog revision")
    if args.fresh_candidate:
        if manifest["status"] != "pass":
            raise ValueError("Fresh pair requires a passing installed-guest host replay receipt")
        modules = manifest["guests"]
        provenance = f"fieldlog-fresh-{checksum[:32]}"
    else:
        if manifest["id"] != ORIGINAL_PROVENANCE:
            raise ValueError("Expected the original compact pair receipt")
        modules = manifest["modules"]
        provenance = ORIGINAL_PROVENANCE
    if set(modules) != set(ORIGINAL_PAIR):
        raise ValueError("Expected exactly baseline and reviewed modules")
    payloads = {}
    records = {}
    for name, source in (("baseline", args.baseline), ("reviewed", args.reviewed)):
        module = modules[name]
        size, sha256 = module["bytes"], module["sha256"]
        if type(size) is not int or not 8 <= size <= 4_194_304 or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"Invalid {name} size or digest in pair manifest")
        with source.open("rb") as file:
            payload = file.read(size + 1)
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != sha256:
            raise ValueError(f"{name} bytes do not match pair manifest")
        if not payload.startswith(b"\x00asm\x01\x00\x00\x00"):
            raise ValueError(f"{name} is not a Wasm v1 module")
        payloads[name] = payload
        records[name] = {"bytes": size, "sha256": sha256}
    if args.fresh_candidate:
        if records == ORIGINAL_PAIR:
            raise ValueError("Use the original pair receipt for the original bytes")
    elif records != ORIGINAL_PAIR:
        raise ValueError("Original pair digests differ from the pinned pair")
    if records["baseline"]["sha256"] == records["reviewed"]["sha256"]:
        raise ValueError("Expected distinct baseline and reviewed payloads")
    return {"provenanceID": provenance, "manifestSHA256": checksum, "modules": records}, payloads

def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"Unexpected source anchor {old!r} in {path}")
    path.write_text(text.replace(old, new))

def tree_digest(root, paths):
    entries = sorted(file for path in paths for file in ([path] if path.is_file() else path.rglob("*")) if file.is_file())
    return hashlib.sha256("".join(f"{digest(file)}  {file.relative_to(root)}\n" for file in entries).encode()).hexdigest()

def source_overlay(out):
    mixer = out / "mixer"
    mixer.mkdir()
    archive = subprocess.check_output(["git", "archive", MIXER, *PACKAGES], cwd=REPO)
    subprocess.run(["tar", "-xf", "-", "-C", str(mixer)], input=archive, check=True)
    fieldlog = out / "fieldlog"
    package = fieldlog / "Package.swift"
    replace(package, '.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")',
            '.package(path: "../mixer/sdk")')
    package.write_text(package.read_text().replace('package: "mixer"', 'package: "sdk"'))
    shutil.copyfile(HERE / "SignedTask.swift", fieldlog / "ios/FieldLog/SignedTask.swift")
    shutil.copyfile(HERE / "FieldLogSignedOTATests.swift", fieldlog / "ios/FieldLogUITests/FieldLogSignedOTATests.swift")
    shutil.copyfile(HERE / "SignedTaskObservation.swift", mixer / "capability-activation/Sources/MixerCapabilityActivation/SignedTaskObservation.swift")
    app = fieldlog / "ios/FieldLog/FieldLogApp.swift"
    replace(app, "WorkspaceView().environmentObject(model).tint(FieldStyle.green).task { await model.open() }",
            """Group {
        if let launch = SignedTaskLaunch.current {
          SignedTaskView(launch: launch)
        } else {
          WorkspaceView().environmentObject(model).task { await model.open() }
        }
      }
        .tint(FieldStyle.green)""")
    project = fieldlog / "ios/FieldLog.xcodeproj/project.pbxproj"
    for old, new in [
        ("packageReferences = (A00000000000000000000020);", "packageReferences = (A00000000000000000000020, C00000000000000000000001);"),
        ("A00000000000000000000026); };", "A00000000000000000000026, C00000000000000000000002); };"),
        ("A00000000000000000000034); sourceTree", "A00000000000000000000034, C00000000000000000000004, C00000000000000000000006); sourceTree"),
        ("A00000000000000000000044); runOnly", "A00000000000000000000044, C00000000000000000000005); runOnly"),
        ("A00000000000000000000027); runOnly", "A00000000000000000000027, C00000000000000000000003); runOnly"),
        ("A00000000000000000000013 = { isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = ();",
         "A00000000000000000000013 = { isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (C00000000000000000000007);"),
        ("children = (B00000000000000000000009);", "children = (B00000000000000000000009, C00000000000000000000008);"),
        ("files = (B00000000000000000000012);", "files = (B00000000000000000000012, C00000000000000000000009);"),
        (" objects = {", """ objects = {
  C00000000000000000000001 = { isa = XCLocalSwiftPackageReference; relativePath = "../../mixer/capability-activation"; };
  C00000000000000000000002 = { isa = XCSwiftPackageProductDependency; package = C00000000000000000000001; productName = MixerCapabilityActivation; };
  C00000000000000000000003 = { isa = PBXBuildFile; productRef = C00000000000000000000002; };
  C00000000000000000000004 = { isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = SignedTask.swift; sourceTree = "<group>"; };
  C00000000000000000000005 = { isa = PBXBuildFile; fileRef = C00000000000000000000004; };
  C00000000000000000000006 = { isa = PBXFileReference; lastKnownFileType = folder; path = Installed; sourceTree = "<group>"; };
  C00000000000000000000007 = { isa = PBXBuildFile; fileRef = C00000000000000000000006; };
  C00000000000000000000008 = { isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = FieldLogSignedOTATests.swift; sourceTree = "<group>"; };
  C00000000000000000000009 = { isa = PBXBuildFile; fileRef = C00000000000000000000008; };"""),
    ]:
        replace(project, old, new)
    project.write_text(project.read_text().replace(
        "INFOPLIST_KEY_CFBundleDisplayName = FieldLog;",
        "INFOPLIST_KEY_CFBundleDisplayName = FieldLog; INFOPLIST_FILE = FieldLog/OTAInfo.plist;"))
    (fieldlog / "ios/FieldLog/OTAInfo.plist").write_bytes(plistlib.dumps({
        "NSAppTransportSecurity": {"NSAllowsLocalNetworking": True},
    }))
    lock = mixer / "capability-activation/Package.resolved"
    shutil.copyfile(lock, fieldlog / "ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved")

def sign(out, run, pair, payloads):
    engine = json.loads((out / "engine/receipt.json").read_text())
    library = out / "engine/lib/libmixer_vm_capability_experimental.a"
    if engine["source_revision"] != MIXER or engine["rust_target"] != "aarch64-apple-ios-sim" or digest(library) != engine["library"]["sha256"]:
        raise ValueError("Unexpected iOS Simulator engine")
    include = out / "mixer/experimental-capability-runtime/Sources/CMixerVMCapability/include"
    for name, header in engine["headers"].items():
        source = out / "engine/include" / name
        if digest(source) != header["sha256"]:
            raise ValueError(f"Engine header mismatch: {name}")
        shutil.copyfile(source, include / name)
    fixtures = out / "signed"
    fixtures.mkdir()
    (fixtures / "Installed").mkdir()
    (fixtures / "pair.json").write_text(json.dumps(pair, indent=2) + "\n")
    for name, payload in payloads.items():
        (fixtures / f"{name}.wasm").write_bytes(payload)

    template = json.loads((out / "mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/identity.json").read_text())
    template["dependencies"] = DEPENDENCIES
    (fixtures / "identity-template.json").write_text(json.dumps(template))
    shutil.copyfile(out / "mixer/capability-activation/Tests/MixerCapabilityActivationTests/Fixtures/bridge.json",
                    fixtures / "Installed/bridge.json")

    fieldlog = out / "fieldlog"
    compiler = Path(subprocess.check_output(["xcrun", "--find", "swift-frontend"], text=True).strip())
    sdk = Path(subprocess.check_output(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], text=True).strip())
    xcode = subprocess.check_output(["xcodebuild", "-version"], text=True).strip()
    xcrun = lambda *args: subprocess.check_output(["xcrun", *args], text=True).strip()
    app_sources = tree_digest(fieldlog, [fieldlog / "Sources", fieldlog / "ios/FieldLog"])
    xcode_project = fieldlog / "ios/FieldLog.xcodeproj/project.pbxproj"
    binding = {
        "engine": {
            "version": MIXER, "source_sha256": engine["source_manifest_sha256"], "artifact_sha256": digest(library),
        },
        "toolchain": {
            "compiler_version": subprocess.check_output([str(compiler), "-version"], text=True).splitlines()[0], "compiler_sha256": digest(compiler),
            "sdk_version": xcrun("--sdk", "iphonesimulator", "--show-sdk-version"), "sdk_sha256": digest(sdk / "SDKSettings.json"),
            "build_tools_sha256": hashlib.sha256(xcode.encode()).hexdigest(),
        },
        "build": {
            "settings_sha256": digest(xcode_project),
            "link_inputs_sha256": tree_digest(out, [out / "mixer" / name for name in PACKAGES]),
            "native_fallback_sha256": app_sources,
            "permissions_sha256": hashlib.sha256(b"simulator ad hoc; no application entitlements; loopback delivery").hexdigest(),
            "entitlements_sha256": hashlib.sha256(b"{}").hexdigest(),
            "resource_policy_sha256": digest(fixtures / "Installed/bridge.json"),
        },
    }
    (fixtures / "binding.json").write_text(json.dumps(binding, indent=2))
    signer = out / "signer"
    (signer / "Sources/Sign").mkdir(parents=True)
    (signer / "Package.swift").write_text("""// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "FieldLogSigner", platforms: [.macOS(.v14)], dependencies: [
  .package(path: "../mixer/runtime-identity"), .package(path: "../mixer/updates"),
], targets: [.executableTarget(name: "Sign", dependencies: [
  .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
  .product(name: "MixerUpdates", package: "updates"),
])])
""")
    shutil.copyfile(HERE / "Sign.swift", signer / "Sources/Sign/main.swift")
    shutil.copyfile(out / "mixer/capability-activation/Package.resolved", signer / "Package.resolved")
    run("sign", ["swift", "run", "--package-path", str(signer), "--scratch-path", str(out / "signer-build"),
                 "--skip-update", "Sign", str(fixtures)])
    shutil.copytree(fixtures / "Installed", fieldlog / "ios/FieldLog/Installed")
    return xcode

def main(out, pair, payloads):
    commands = []
    env = dict(os.environ, TMPDIR=str(out / "tmp") + "/", CLANG_MODULE_CACHE_PATH=str(out / "clang-cache"),
               SWIFTPM_MODULECACHE_OVERRIDE=str(out / "swift-cache"), GIT_TERMINAL_PROMPT="0",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
    def run(name, command):
        with (out / f"logs/{name}.log").open("xb") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        commands.append({"argv": command, "exit": result.returncode, "log": f"logs/{name}.log"})
        (out / "build-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        result.check_returncode()

    if digest(out / "fieldlog.tar.gz") != "75d2ce2663ade805ca40831b17a460c248e88c62a7689d5a671182bbf0ed7840":
        raise ValueError("Expected confirmed public FieldLog archive")
    fieldlog = out / "fieldlog"
    fieldlog.mkdir()
    run("unpack-fieldlog", ["tar", "-xzf", str(out / "fieldlog.tar.gz"), "--strip-components=1", "-C", str(fieldlog)])
    origin = tree_digest(out, [fieldlog])
    source_overlay(out)
    xcode = sign(out, run, pair, payloads)
    base = ["/usr/bin/xcodebuild", "-project", str(out / "fieldlog/ios/FieldLog.xcodeproj"), "-scheme", "FieldLog",
            "-configuration", "Debug", "-sdk", "iphonesimulator", "-destination", "generic/platform=iOS Simulator",
            "-derivedDataPath", str(out / "derived-data"), "-clonedSourcePackagesDirPath", str(out / "source-packages"),
            "-packageCachePath", str(out / "package-cache"), "-disablePackageRepositoryCache", "-scmProvider", "system"]
    run("resolve", base + ["-resolvePackageDependencies", "-skipPackageUpdates"])
    resolved = out / "fieldlog/ios/FieldLog.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    if json.loads(resolved.read_text())["pins"] != json.loads((out / "mixer/capability-activation/Package.resolved").read_text())["pins"]:
        raise ValueError("Resolved dependency revisions differ")
    run("build", base + ["-disableAutomaticPackageResolution", "-onlyUsePackageVersionsFromResolvedFile",
                         "-resultBundlePath", str(out / "build.xcresult"), "build-for-testing", "ARCHS=arm64",
                         f"LIBRARY_SEARCH_PATHS={out / 'engine/lib'}", "ENABLE_DEBUG_DYLIB=NO",
                         "CODE_SIGN_IDENTITY=-", "CODE_SIGNING_REQUIRED=NO", "CODE_SIGN_ENTITLEMENTS="])
    products = out / "derived-data/Build/Products"
    [test_run] = list(products.glob("*.xctestrun"))
    app = products / "Debug-iphonesimulator/FieldLog.app"
    app_info = plistlib.loads((app / "Info.plist").read_bytes())
    if [app_info[k] for k in ["CFBundleIdentifier", "MinimumOSVersion", "CFBundleSupportedPlatforms"]] != [
            "dev.mixer.fieldlog", "26.0", ["iPhoneSimulator"]]:
        raise ValueError("Built product differs from signed identity")
    if app_info.get("NSAppTransportSecurity") != {"NSAllowsLocalNetworking": True}:
        raise ValueError("Missing loopback request policy")
    if tree_digest(app, [app / "Installed"]) != tree_digest(out / "signed", [out / "signed/Installed"]):
        raise ValueError("Installed materials differ from signed identity")
    run("macho", ["xcrun", "vtool", "-show-build", str(app / "FieldLog")])
    macho = (out / "logs/macho.log").read_text()
    if "platform IOSSIMULATOR" not in macho or "minos 26.0" not in macho:
        raise ValueError("Unexpected Mach-O platform or deployment version")
    run("arch", ["lipo", "-archs", str(app / "FieldLog")])
    if (out / "logs/arch.log").read_text().strip() != "arm64":
        raise ValueError("Unexpected app architecture")
    receipt = {
        "status": "generic_build_for_testing_passed_runtime_pending", "xcode": xcode,
        "fieldlogRevision": FIELDLOG, "fieldlogInputTreeSHA256": origin,
        "fieldlogArchiveSHA256": digest(out / "fieldlog.tar.gz"), "mixerRevision": MIXER,
        "dependencyLockSHA256": digest(resolved), "testIdentifier": TEST, "bundleIdentifier": app_info["CFBundleIdentifier"],
        "appVersion": app_info["CFBundleShortVersionString"], "appBuild": app_info["CFBundleVersion"],
        "minimumOS": app_info["MinimumOSVersion"], "sdkBuild": app_info["DTSDKBuild"],
        "runtimeFingerprint": json.loads((out / "signed/host.json").read_text())["runtime"],
        "installedIdentitySHA256": digest(app / "Installed/identity.json"),
        "installedMaterialTreeSHA256": tree_digest(app, [app / "Installed"]),
        "appExecutableSHA256": digest(app / "FieldLog"), "appTreeSHA256": tree_digest(products, [app]),
        "engineArchiveSHA256": digest(out / "engine/lib/libmixer_vm_capability_experimental.a"),
        "engineSourceSHA256": json.loads((out / "engine/receipt.json").read_text())["source_manifest_sha256"],
        "productsTreeSHA256": tree_digest(products, [products]),
        "xctestrun": str(test_run), "xctestrunSHA256": digest(test_run),
        "pair": pair,
        "commands": "build-commands.json",
    }
    (out / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Prepared directory containing FieldLog archive, engine, service and logs/tmp directories")
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--reviewed", required=True, type=Path)
    parser.add_argument("--pair-manifest", required=True, type=Path)
    parser.add_argument("--pair-manifest-sha256", required=True)
    parser.add_argument("--fresh-candidate", action="store_true", help="Use a passing installed-guest replay receipt for fresh bytes")
    args = parser.parse_args()
    try:
        pair, payloads = load_pair(args)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    main(args.output.resolve(strict=True), pair, payloads)
