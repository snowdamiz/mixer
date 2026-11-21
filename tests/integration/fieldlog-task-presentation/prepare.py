"""Install the pinned ordinary app through its production source recipe."""
import runpy
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

work = Path(sys.argv[1])
arm = sys.argv[2]
replay = Path(sys.argv[3])
trees = {
    "baseline": "380e764598c31181d16ef2fbb91c95bf95693375",
    "initial": "1fb23eb6096ce5d3eb170d47808ab4119e3659c4",
    "candidate": "eb08569c13b5f65e25edd0dfde1fe70fc8278ece",
}
root = work / arm
root.mkdir()
archive = root / "fieldlog.tar"
with archive.open("wb") as output:
    subprocess.run(["git", "-C", work / "fieldlog", "archive", trees[arm],
                    "--", "Integrations/GeneratedReport"], stdout=output, check=True)
with tarfile.open(archive) as source:
    source.extractall(root, filter="data")

app = root / "App"
sdk = app / "Generated/MixerSDK"
shutil.copytree(work / "mixer/sdk", sdk)
recipe = runpy.run_path(str(root / "Integrations/GeneratedReport/scripts/build-android.py"))
files, modules = recipe["app_inputs"]()
# The maintained recipe normally starts from mixer create's platform layout.
(app / "Platforms/Android/Tests/AppAndroidTests").mkdir(parents=True)
recipe["install_app_inputs"](app, files, modules)

# Preserve both app manifests exactly. Resolve the pinned SDK's one remote
# dependency using the local archive checked by reconstruct.sh.
manifest = sdk / "Package.swift"
text = manifest.read_text()
remote = '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")'
assert text.count(remote) == 1
manifest.write_text(text.replace(remote, '.package(path: "../../../../swift-crypto")'))
(app / "Platforms/Android/Package.resolved").unlink()

host = root / "HostReplay"
sources = host / "Sources/Replay"
sources.mkdir(parents=True)
shutil.copyfile(replay, sources / "Replay.swift")
(host / "Package.swift").write_text('''// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "FieldLogHostReplay",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../App/Platforms/Android"),
        .package(path: "../App"),
        .package(path: "../App/Generated/MixerSDK"),
    ],
    targets: [
        .executableTarget(name: "Replay", dependencies: [
            .product(name: "AppAndroid", package: "Android"),
            .product(name: "FieldLogFeatures", package: "App"),
            .product(name: "FieldLogModels", package: "App"),
            .product(name: "FieldLogStorage", package: "App"),
            .product(name: "MixerAndroid", package: "MixerSDK"),
            .product(name: "MixerUI", package: "MixerSDK"),
        ]),
    ]
)
''')
print(f"Installed {arm} {trees[arm]} with pinned FieldLog application and platform manifests")
