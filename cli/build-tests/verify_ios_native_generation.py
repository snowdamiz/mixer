"""Build the generated app with Xcode. Supply an existing CLI, SDK and new work path."""

import hashlib
import json
import plistlib
import subprocess
import sys
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify(mixer, sdk, work):
    work.mkdir()
    root = work / "app"

    def cli(label, *arguments, refusal=None):
        command = [str(mixer), *arguments, "--directory", str(root)]
        result = subprocess.run(command, cwd=work, capture_output=True, text=True)
        (work / f"{label}.json").write_text(result.stdout)
        (work / f"{label}.stderr").write_text(result.stderr)
        if refusal:
            assert result.returncode == 1, (command, result.returncode, result.stdout, result.stderr)
            assert json.loads(result.stdout)["code"] == refusal, result.stdout
        else:
            assert result.returncode == 0, (command, result.returncode, result.stdout, result.stderr)
        return json.loads(result.stdout)

    cli("create", "create", "FieldLog", "--application", "dev.mixer.fieldlog", "--sdk-path", str(sdk))
    platform = root / "Platforms/iOS"
    project = platform / "FieldLog.xcodeproj"
    pbxproj = project / "project.pbxproj"
    receipt = project / "mixer-generated.sha256"
    native_plist = project / "MixerNativeInfo.plist"
    pins = project / "project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
    pins.parent.mkdir(parents=True)
    pins.write_bytes((root / "Generated/MixerSDK/Package.resolved").read_bytes())
    starter_project = pbxproj.read_bytes()
    starter_receipt = receipt.read_bytes()
    assert sha256(starter_project) == "d113e6084cc1ec940e2a04f35705e188763e33b071a69ee22fb3b91979d80624"
    assert starter_receipt == (sha256(starter_project) + "\n").encode()
    config_path = root / "mixer.yml"
    starter_config = config_path.read_bytes()
    app = root / ".mixer/ios-build/Build/Products/Debug-iphonesimulator/FieldLog.app"
    derived = root / ".mixer/ios-build"
    build = ("build", "--platform", "ios")

    folder = platform / "CheckoutRelease/ChecklistRelease"
    folder.mkdir(parents=True)
    (folder / "nested").mkdir()
    resources = {"port.txt": b"43123\n", "nested/bridge.json": b'{"transport":"fixture"}\n'}
    for relative, data in resources.items():
        (folder / relative).write_bytes(data)
    (platform / "ChecklistProbe.swift").write_text(
        'import Foundation\n'
        'enum ChecklistProbe {\n'
        '    static var title: String {\n'
        '        Bundle.main.url(forResource: "ChecklistRelease", withExtension: nil) == nil\n'
        '            ? "Missing" : ProbeLabel.ready\n'
        '    }\n'
        '}\n'
    )
    (platform / "ProbeLabel.swift").write_text('enum ProbeLabel { static let ready = "Checklist ready" }\n')
    (platform / "Undeclared.swift").write_text('#error("The generator must compile only declared sources")\n')
    description = "Connect to the developer checklist service on this local network."
    config = json.loads(starter_config)
    declarations = {
        "swiftSources": ["ProbeLabel.swift", "ChecklistProbe.swift"],
        "resourceFolders": ["CheckoutRelease/ChecklistRelease"],
        "localNetworkUsageDescription": description,
        "allowsLocalNetworking": True,
    }

    def set_native(value):
        config_path.write_text(json.dumps({**config, "iosNative": value}))

    refusals = {}

    def refuse(label, code, expected_project=starter_project):
        cli(label, *build, refusal=code)
        assert pbxproj.read_bytes() == expected_project
        assert not derived.exists()
        refusals[label] = code

    for field in ("buildSettings", "buildScripts", "NSAllowsArbitraryLoads"):
        set_native({**declarations, field: True})
        refuse(field, "config.ios-native")
    set_native({**declarations, "swiftSources": ["../Outside.swift"]})
    refuse("traversal", "config.ios-native")
    set_native({**declarations, "swiftSources": ["$OTHER.swift"]})
    refuse("substitution", "config.ios-native")
    set_native({**declarations, "swiftSources": ["Missing.swift"]})
    refuse("missing", "generate.ios-native-path")
    alias = platform / "Alias.swift"
    alias.symlink_to(platform / "ProbeLabel.swift")
    set_native({**declarations, "swiftSources": [alias.name]})
    refuse("swift-symlink", "generate.ios-native-path")
    alias.unlink()
    link = folder / "nested/link.json"
    link.symlink_to(project / "missing.json")
    set_native(declarations)
    refuse("nested-resource-symlink", "generate.ios-native-path")
    link.unlink()
    receipt.unlink()
    refuse("missing-receipt", "generate.modified")
    receipt.write_bytes(starter_receipt)
    edited = starter_project + b"// app-owned modification\n"
    pbxproj.write_bytes(edited)
    refuse("edited-project", "generate.modified", edited)
    receipt.write_text(sha256(edited) + "\n")
    refuse("self-receipted-project", "generate.modified", edited)
    pbxproj.write_bytes(starter_project)
    receipt.write_bytes(starter_receipt)

    config_path.write_bytes(starter_config)
    starter = cli("starter-build", *build)
    starter_plist = plistlib.loads((app / "Info.plist").read_bytes())
    assert "NSLocalNetworkUsageDescription" not in starter_plist
    assert "NSAppTransportSecurity" not in starter_plist
    assert not (app / "ChecklistRelease").exists() and not native_plist.exists()
    assert pbxproj.read_bytes() == starter_project and receipt.read_bytes() == starter_receipt

    entry = platform / "FieldLogApp.swift"
    starter_entry = entry.read_bytes()
    entry.write_text('import SwiftUI\n@main struct FieldLogApp: App {\n'
                     '    var body: some Scene { WindowGroup { Text(ChecklistProbe.title) } }\n'
                     '}\n')
    set_native(declarations)
    configured = cli("native-build", *build)
    native_project = pbxproj.read_bytes()
    native_receipt = receipt.read_bytes()
    plist = plistlib.loads((app / "Info.plist").read_bytes())
    assert plist["CFBundleIdentifier"] == "dev.mixer.fieldlog"
    assert plist["NSLocalNetworkUsageDescription"] == description
    assert plist["NSAppTransportSecurity"] == {"NSAllowsLocalNetworking": True}
    assert plist["NSAppTransportSecurity"]["NSAllowsLocalNetworking"] is True
    assert (app / "FieldLog").is_file()
    for relative, data in resources.items():
        assert (app / "ChecklistRelease" / relative).read_bytes() == data
    assert not (app / "CheckoutRelease").exists()

    set_native({**declarations, "swiftSources": sorted(declarations["swiftSources"])})
    cli("reordered-build", *build)
    assert native_project == pbxproj.read_bytes() and native_receipt == receipt.read_bytes()
    entry.write_bytes(starter_entry)
    config_path.write_bytes(starter_config)
    cli("restore-starter", *build)
    assert not native_plist.exists()
    assert pbxproj.read_bytes() == starter_project and receipt.read_bytes() == starter_receipt
    restored_plist = plistlib.loads((app / "Info.plist").read_bytes())
    assert "NSLocalNetworkUsageDescription" not in restored_plist
    assert "NSAppTransportSecurity" not in restored_plist
    assert not (app / "ChecklistRelease").exists()

    print(json.dumps({
        "buildCommand": configured["command"],
        "starterExit": starter["exitCode"],
        "configuredExit": configured["exitCode"],
        "starterProjectSHA256": sha256(starter_project),
        "nativeProjectSHA256": sha256(native_project),
        "bundleIdentifier": plist["CFBundleIdentifier"],
        "bundleResourceSHA256": {f"ChecklistRelease/{path}": sha256(data) for path, data in resources.items()},
        "bundleInfoPlist": {key: plist[key] for key in ("NSLocalNetworkUsageDescription", "NSAppTransportSecurity")},
        "refusals": refusals,
        "reorderedProjectIdentical": True,
        "starterRestoredByteForByte": True,
    }, indent=2))


if __name__ == "__main__":
    verify(*(Path(value).resolve() for value in sys.argv[1:]))
