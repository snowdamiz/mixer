#!/usr/bin/env python3
"""Project the pinned sources into an owned, build-only Xcode fixture."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ENGINE_REVISION = "692f05cd2d31f218ae9b3cef7253a4e7397f8e17"
ENGINE_NAME = "libmixer_vm_capability_experimental.a"
ENGINE_DIGEST = "cd6ae3179965c1c85eb59abb9f6ad670065c109a2e8be8713b3d4cd7edd785c7"
ENGINE_SOURCE_DIGEST = "94061378e14c4c5ed69ce66ee68cc71ded714d56bf309561d7f23fe16b59ca85"
HEADERS = {
    "mixer_vm.h": "18c2498d0d1deae2c998ef9f4b3f811b2184c45e8169610012b05e99342385fd",
    "mixer_vm_capability.h": "9213c34ebf0f14d14f3319172e83647f704f3a02a60d413b4de990884357b4a6",
    "mixer_vm_guest_ui.h": "d8d8217b900662e77787a8729f5c1cfe096b0df25ffe39e289f89d69fc156ab5",
    "mixer_vm_guest_ui_deferred.h": "7a327260d5dd308d698eda79224e85aeb5f7e5ce01b75517fdb9beadef2da06f",
}
PACKAGES = ["capability-activation", "experimental-capability-runtime", "runtime-identity", "sdk", "updates"]


def copy_checked(source, target, expected):
    with source.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise SystemExit(f"Unexpected input digest for {source}: {actual}")
    shutil.copyfile(source, target)


def main():
    root = Path(sys.argv[1]).resolve(strict=True)
    engine = Path(sys.argv[2]).resolve(strict=True)
    revision = sys.argv[3]
    repo = HERE.parents[2]
    if repo / "verification/local" not in root.parents:
        raise SystemExit("Expected a fresh build directory under verification/local")
    mixer = root / "mixer"
    mixer.mkdir()
    archive = subprocess.check_output(["git", "archive", revision, *PACKAGES], cwd=repo)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:
        source.extractall(mixer, filter="data")

    lib = root / "lib"
    lib.mkdir()
    copy_checked(engine / "lib" / ENGINE_NAME, lib / ENGINE_NAME, ENGINE_DIGEST)
    include = mixer / "experimental-capability-runtime/Sources/CMixerVMCapability/include"
    for name, expected in HEADERS.items():
        copy_checked(engine / "include" / name, include / name, expected)

    tests = mixer / "capability-activation/Tests/MixerCapabilityActivationTests"
    experiment = root / "Experiment"
    experiment.mkdir()
    for name in ("UP5ThemeApp.swift", "SignedFixture.swift", "FixtureTheme.swift",
                 "UP5ThemeUITests.swift", "ThemePixels.swift"):
        shutil.copyfile(HERE / name, experiment / name)

    # Extend only the fixture's signed document producer with a disabled sibling.
    program = (tests / "GuestUISignedProgram.swift").read_text()
    anchor = r'\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}'
    if program.count(anchor) != 1:
        raise SystemExit("Expected the one bundled/guest Save document boundary")
    disabled = r',{\"id\":\"unavailable\",\"kind\":\"button\",\"properties\":{\"label\":\"Unavailable\",\"disabled\":true},\"children\":[],\"actions\":[{\"id\":\"sample.disabled\",\"event\":\"activate\"}]}'
    (experiment / "GuestUISignedProgram.swift").write_text(program.replace(anchor, anchor + disabled))

    fixtures = experiment / "Fixtures"
    fixtures.mkdir()
    for name in ("bridge", "storage", "storage-grant", "http", "http-grant"):
        shutil.copyfile(tests / "Fixtures" / f"{name}.json", fixtures / f"{name}.json")
    identity = json.loads((tests / "Fixtures/identity.json").read_text())
    identity["application"]["bundle_id"] = "dev.mixer.fixture.up5theme"
    identity["execution"]["startup_export"] = "mixer_guest_ui_start_v1"
    identity["platform"].update(environment="simulator", minimum_os="17.0", target="arm64-apple-ios17.0-simulator")
    identity["engine"].update(version=ENGINE_REVISION, source_sha256=ENGINE_SOURCE_DIGEST, artifact_sha256=ENGINE_DIGEST)
    identity["dependencies"] = [
        {"id": "mixer.guest-ui-event-v1", "version": "1",
         "artifact_sha256": "34180d46e20e403c9cd3f3aa1584a7b6d0e67e94900267c7aa51c87116566024"},
        {"id": "mixer.guest-ui-native-header-v1", "version": "1",
         "artifact_sha256": HEADERS["mixer_vm_guest_ui.h"]},
    ]
    (fixtures / "identity.json").write_text(json.dumps(identity, sort_keys=True))
    subprocess.run(["ruby", str(HERE / "project.rb"), str(root)], check=True)
    resolution = root / "UP5Theme.xcodeproj/project.xcworkspace/xcshareddata/swiftpm"
    resolution.mkdir(parents=True)
    shutil.copyfile(mixer / "capability-activation/Package.resolved", resolution / "Package.resolved")


if __name__ == "__main__":
    main()
