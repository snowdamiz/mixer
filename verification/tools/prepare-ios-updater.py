#!/usr/bin/env python3
"""Prepare an app-hosted XCTest/Swift Testing project from a frozen updater commit.

This copies the original package tests without changing their assertions. The
only additional test source supplies Bundle.module for the Xcode resource bundle.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--revision', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', a.revision + '^{commit}'], cwd=ROOT, text=True).strip()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    archive = subprocess.check_output(['git', 'archive', revision, 'updates'], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(out, filter='data')
    (out / 'updates').rename(out / 'package')
    app = out / 'app'
    app.mkdir()
    (app / 'Host.swift').write_text('''import SwiftUI
@main struct UpdaterQualificationHost: App {
    var body: some Scene { WindowGroup { Text("Mixer updater app-sandbox qualification") } }
}
''')
    tests = app / 'Tests'
    shutil.copytree(out / 'package/Tests/MixerUpdatesTests', tests)
    (tests / 'FixtureBundle.swift').write_text('''import Foundation
private final class FixtureBundleAnchor: NSObject {}
extension Bundle { static var module: Bundle { Bundle(for: FixtureBundleAnchor.self) } }
''')
    project = app / 'UpdaterHost.xcodeproj'
    project.mkdir()
    template = ROOT / 'verification/tools/ios-numeric/NumericVM.xcodeproj/project.pbxproj'
    pbx = template.read_text().replace('NumericVM', 'UpdaterHost').replace('numericqualification', 'updaterqualification')
    pbx = pbx.replace('Mixer VM Qualification', 'Mixer Updater Qualification')
    pbx = pbx.replace('targets = (A00000000000000000000005);',
        'targets = (A00000000000000000000005,B00000000000000000000001); packageReferences = (C00000000000000000000001);')
    pbx = pbx.replace('A00000000000000000000008,A00000000000000000000017,A00000000000000000000004',
                      'A00000000000000000000008,B00000000000000000000002,A00000000000000000000004')
    pbx = pbx.replace('children = (A00000000000000000000009);', 'children = (A00000000000000000000009,B00000000000000000000003);')
    pbx = pbx.replace('files = (A00000000000000000000018);', 'files = ();')
    pbx = pbx.replace('SWIFT_OBJC_BRIDGING_HEADER = "$(SRCROOT)/Host-Bridging.h"; LIBRARY_SEARCH_PATHS = "$(SRCROOT)/lib"; OTHER_LDFLAGS = "$(inherited) -lmixer_vm -liconv";', 'ENABLE_TESTABILITY = YES;')
    pbx = pbx.replace('path = oracle;', 'path = Fixtures;')
    objects = []
    files, builds = [], []
    for index, file in enumerate(sorted(tests.glob('*.swift'))):
        ref, build = f'D{index:023X}', f'E{index:023X}'
        files.append(ref); builds.append(build)
        objects.append(f'{ref} = {{ isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = {file.name}; sourceTree = "<group>"; }};')
        objects.append(f'{build} = {{ isa = PBXBuildFile; fileRef = {ref}; }};')
    objects += [
        'C00000000000000000000001 = { isa = XCLocalSwiftPackageReference; relativePath = "../package"; };',
        'C00000000000000000000002 = { isa = XCSwiftPackageProductDependency; package = C00000000000000000000001; productName = MixerUpdates; };',
        'C00000000000000000000003 = { isa = PBXBuildFile; productRef = C00000000000000000000002; };',
        'B00000000000000000000001 = { isa = PBXNativeTarget; buildConfigurationList = B00000000000000000000004; buildPhases = (B00000000000000000000005,B00000000000000000000006,B00000000000000000000007); buildRules = (); dependencies = (B00000000000000000000008); name = UpdaterTests; productName = UpdaterTests; productReference = B00000000000000000000003; productType = "com.apple.product-type.bundle.unit-test"; packageProductDependencies = (C00000000000000000000002); };',
        f'B00000000000000000000002 = {{ isa = PBXGroup; path = Tests; children = ({",".join(files)},A00000000000000000000017); sourceTree = "<group>"; }};',
        'B00000000000000000000003 = { isa = PBXFileReference; explicitFileType = wrapper.cfbundle; includeInIndex = 0; path = UpdaterTests.xctest; sourceTree = BUILT_PRODUCTS_DIR; };',
        'B00000000000000000000004 = { isa = XCConfigurationList; buildConfigurations = (B00000000000000000000010); defaultConfigurationIsVisible = 0; defaultConfigurationName = Debug; };',
        f'B00000000000000000000005 = {{ isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({",".join(builds)}); runOnlyForDeploymentPostprocessing = 0; }};',
        'B00000000000000000000006 = { isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (C00000000000000000000003); runOnlyForDeploymentPostprocessing = 0; };',
        'B00000000000000000000007 = { isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (A00000000000000000000018); runOnlyForDeploymentPostprocessing = 0; };',
        'B00000000000000000000008 = { isa = PBXTargetDependency; target = A00000000000000000000005; targetProxy = B00000000000000000000013; };',
        'B00000000000000000000010 = { isa = XCBuildConfiguration; buildSettings = { PRODUCT_BUNDLE_IDENTIFIER = dev.mixer.updaterqualification.tests; PRODUCT_NAME = "$(TARGET_NAME)"; GENERATE_INFOPLIST_FILE = YES; TARGETED_DEVICE_FAMILY = "1,2"; CODE_SIGN_STYLE = Automatic; CURRENT_PROJECT_VERSION = 1; MARKETING_VERSION = 0.1.0; SWIFT_VERSION = 6.0; SWIFT_OPTIMIZATION_LEVEL = "-Onone"; IPHONEOS_DEPLOYMENT_TARGET = 17.0; TEST_HOST = "$(BUILT_PRODUCTS_DIR)/UpdaterHost.app/UpdaterHost"; BUNDLE_LOADER = "$(TEST_HOST)"; LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks @loader_path/Frameworks"; }; name = Debug; };',
        'B00000000000000000000013 = { isa = PBXContainerItemProxy; containerPortal = A00000000000000000000001; proxyType = 1; remoteGlobalIDString = A00000000000000000000005; remoteInfo = UpdaterHost; };',
    ]
    pbx = pbx.replace('\n };\n rootObject', '\n' + '\n'.join(objects) + '\n };\n rootObject')
    (project / 'project.pbxproj').write_text(pbx)
    scheme = project / 'xcshareddata/xcschemes/UpdaterHost.xcscheme'
    scheme.parent.mkdir(parents=True)
    def reference(identifier, name, product):
        return f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{identifier}" BuildableName="{product}" BlueprintName="{name}" ReferencedContainer="container:UpdaterHost.xcodeproj"/>'
    app_ref = reference('A00000000000000000000005', 'UpdaterHost', 'UpdaterHost.app')
    test_ref = reference('B00000000000000000000001', 'UpdaterTests', 'UpdaterTests.xctest')
    scheme.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="2700" version="1.7">
<BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>
<BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="YES">{app_ref}</BuildActionEntry>
<BuildActionEntry buildForTesting="YES" buildForRunning="NO" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="YES">{test_ref}</BuildActionEntry>
</BuildActionEntries></BuildAction>
<TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables><TestableReference skipped="NO">{test_ref}</TestableReference></Testables></TestAction>
<LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO"><BuildableProductRunnable runnableDebuggingMode="0">{app_ref}</BuildableProductRunnable></LaunchAction>
</Scheme>
''')
    hashes = {str(f.relative_to(out)): hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted(out.rglob('*')) if f.is_file() and 'verification' not in f.relative_to(out).parts}
    (out / 'prepared.json').write_text(json.dumps({'source_revision': revision,
        'source_archive_sha256': hashlib.sha256(archive).hexdigest(), 'files': hashes,
        'scope': 'Original updater package/test sources unchanged; Xcode test-host and Bundle.module adapter only'}, indent=2) + '\n')
    print(project)


if __name__ == '__main__':
    main()
