#!/usr/bin/env python3
"""Prepare the pinned B-prime experiment in an owned, new verification directory."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ENGINE_REVISION = "692f05cd2d31f218ae9b3cef7253a4e7397f8e17"
PACKAGE_REVISION = "a332356703122de8393115e8e8d42badca6aa1e0"
PACKAGES = ["capability-activation", "experimental-capability-runtime", "runtime-identity", "sdk", "updates"]
PRODUCT = "dev.mixer.fixture.s4native"


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    root = Path(sys.argv[1]).resolve(strict=True)
    if root.parent != REPO / "verification/local":
        raise SystemExit("Expected owned directory under verification/local")
    engine = json.loads((root / "engine/receipt.json").read_text())
    library = root / "engine/lib/libmixer_vm_capability_experimental.a"
    if (engine["source_revision"], engine["rust_target"], engine["library"]["sha256"]) != (
        ENGINE_REVISION, "aarch64-apple-ios-sim", digest(library)
    ):
        raise SystemExit("Expected the pinned arm64 Simulator engine")
    mixer = root / "mixer"
    mixer.mkdir()
    archive = subprocess.check_output(
        ["git", "--no-replace-objects", "archive", PACKAGE_REVISION, *PACKAGES], cwd=REPO
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(mixer, filter="data")
    installed = mixer / "experimental-capability-runtime/Sources/CMixerVMCapability/include"
    for name, header in engine["headers"].items():
        source = root / "engine/include" / name
        if digest(source) != header["sha256"]:
            raise SystemExit(f"Unexpected header: {name}")
        shutil.copyfile(source, installed / name)

    package = mixer / "capability-activation"
    sources = package / "Sources/MixerCapabilityActivation"
    shutil.copyfile(HERE / "S4Readback.swift", sources / "S4Readback.swift")
    # Install the fixture hold and observations only in the isolated package.
    # Keep them scoped to the iOS probe and the presentation instance.
    for name in ("CapabilityGuestUIPresentation", "CapabilityGuestUIApple"):
        path = sources / f"{name}.swift"
        text = path.read_text()
        if name == "CapabilityGuestUIApple":
            original = "MixerNativeView(host: host, onAction: presentation.actionHandler(host: host, attachment: attachment))"
            if text.count(original) != 1:
                raise SystemExit("Expected the native action callback boundary")
            text = text.replace(original, """let callback = presentation.s4Installed(
                        presentation.actionHandler(host: host, attachment: attachment),
                        inputEnabled: presentation.inputEnabled(for: attachment)
                    )
                    MixerNativeView(host: host) { action in
                        presentation.s4RecordNativeCallback(action, callback: callback)
                    }""")
            original = "    var appeared = false\n"
            if text.count(original) != 1:
                raise SystemExit("Expected the pinned iOS probe appearance flag")
            text = text.replace(original, """    private(set) var s4HasAppeared = false
    var appeared = false {
        didSet { if appeared { s4HasAppeared = true } }
    }
""")
            original = '''        guard link.timestamp > firstTimestamp else { return }
        _ = presentation?.observeNativeDisplay(ticket)
'''
            if text.count(original) != 1:
                raise SystemExit("Expected the pinned iOS display acknowledgment call")
            text = text.replace(original, '''        guard link.timestamp > firstTimestamp else { return }
        if let presentation, presentation.s4HoldNativeAcknowledgment {
            presentation.s4HeldDisplayTicket = S4DisplayTicket(ticket)
            return
        }
        if let presentation, presentation.observeNativeDisplay(ticket) {
            presentation.s4AcknowledgedDisplayTicket = S4DisplayTicket(ticket)
        }
''')
        else:
            original = "    private var observedNativeDisplay = false\n"
            if text.count(original) != 1:
                raise SystemExit("Expected the pinned native display latch")
            text = text.replace(original, original + '''    #if os(iOS)
    public var s4HoldNativeAcknowledgment = false
    public internal(set) var s4HeldDisplayTicket: S4DisplayTicket?
    public internal(set) var s4AcknowledgedDisplayTicket: S4DisplayTicket?
    public internal(set) var s4NativeCallbackCount = 0
    var s4LastNativeCallback: (@MainActor () -> Void)?
    var s4LastInstalledCallback: (@MainActor (RoutedUIAction) -> Void)?
    var s4LastInstalledWithInputEnabled = false
    #endif
''')
        path.write_text(text + (HERE / f"{name}.inc").read_text())
    apple = mixer / "sdk/Sources/MixerApple"
    shutil.copyfile(HERE / "S4NativeTheme.swift", apple / "S4NativeTheme.swift")
    renderer = apple / "MixerNativeView.swift"
    text = renderer.read_text()
    for original, replacement in [
        ("    @Published internal private(set) var featureDisplayID: UUID?\n",
         "    @Published internal private(set) var featureDisplayID: UUID?\n"
         "    public var s4SharedTheme: S4NativeTheme?\n"),
        ("        .id(host.snapshot.identity(for: host.snapshot.document.root.id))\n",
         "        .id(host.snapshot.identity(for: host.snapshot.document.root.id))\n"
         "        .modifier(S4NativeThemeStyle(theme: host.s4SharedTheme))\n"),
    ]:
        if text.count(original) != 1:
            raise SystemExit("Expected a unique S4 theme adapter anchor in the pinned MixerNativeView")
        text = text.replace(original, replacement)
    renderer.write_text(text)

    experiment = root / "Experiment"
    experiment.mkdir()
    for name in ("S4NativeApp.swift", "S4SignedFixture.swift", "S4SharedTheme.swift", "S4NativeUITests.swift", "S4ThemePixels.swift"):
        shutil.copyfile(HERE / name, experiment / name)
    tests = package / "Tests/MixerCapabilityActivationTests"
    shutil.copyfile(tests / "GuestUISignedProgram.swift", experiment / "GuestUISignedProgram.swift")

    fixtures = experiment / "Fixtures"
    fixtures.mkdir()
    for name in ("bridge", "storage", "storage-grant", "http", "http-grant"):
        shutil.copyfile(tests / "Fixtures" / f"{name}.json", fixtures / f"{name}.json")
    identity = json.loads((tests / "Fixtures/identity.json").read_text())
    identity["application"]["bundle_id"] = PRODUCT
    identity["execution"]["startup_export"] = "mixer_guest_ui_start_v1"
    identity["platform"].update(
        environment="simulator", minimum_os="17.0", target="arm64-apple-ios17.0-simulator"
    )
    identity["engine"].update(
        version=ENGINE_REVISION, source_sha256=engine["source_manifest_sha256"], artifact_sha256=digest(library)
    )
    identity["dependencies"] = [
        {"id": ident, "version": "1", "artifact_sha256": sha}
        for ident, sha in [
            ("mixer.guest-ui-event-v1", "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"),
            ("mixer.guest-ui-native-header-v1", "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5"),
        ]
    ]
    (fixtures / "identity.json").write_text(json.dumps(identity, sort_keys=True))
    subprocess.run(["ruby", str(HERE / "project.rb"), str(root)], check=True)
    resolution = root / "S4Native.xcodeproj/project.xcworkspace/xcshareddata/swiftpm"
    resolution.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(package / "Package.resolved", resolution / "Package.resolved")
    package_tree = subprocess.check_output(
        ["git", "--no-replace-objects", "rev-parse", f"{PACKAGE_REVISION}^{{tree}}"], cwd=REPO, text=True
    ).strip()
    (root / "inputs.json").write_text(json.dumps({
        "package_revision": PACKAGE_REVISION,
        "package_tree": package_tree,
        "package_archive_sha256": hashlib.sha256(archive).hexdigest(),
        "engine_revision": ENGINE_REVISION,
        "engine_source_manifest_sha256": engine["source_manifest_sha256"],
        "engine_archive_sha256": engine["library"]["sha256"],
        "fixture_sha256": {path.name: digest(path) for path in sorted(HERE.iterdir())
                           if path.suffix in {".swift", ".inc", ".py", ".rb", ".sh"}},
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
