# FieldLog app-owned Swift source sharing

The recorded iOS and Android export targets share **three byte-identical Swift input files**. Only two have a direct use identified in both apps. This is a comparison of the targets built in the v80 iOS and v74 Android export checks, pinned to Mixer evidence base `e1202816e8bb5bbeb3583c0d458918923b895426` (v82). [Source and target receipt](../verification/receipts/fieldlog-d2-app-source-sharing-v82.json)

| Responsibility | Shared Swift files | Shared bytes | Shared physical lines |
| --- | ---: | ---: | ---: |
| UI | 1 / 6 | 7,705 / 50,569 | 168 / 1,184 |
| Logic and host entry | 2 / 7 | 17,308 / 61,844 | 430 / 1,417 |
| Mixed UI and logic | 0 / 1 | 0 / 62,537 | 0 / 896 |
| All measured inputs | 3 / 14 | 25,013 / 174,950 | 598 / 3,497 |

The denominator is the union of production Swift inputs. Each exact match counts once, and each distinct version of a changed file counts separately. The iOS app has 10 inputs and the Android app has seven. Physical lines include comments, blanks, and inactive conditional source.

- **UI.** Both targets list `TaskEditorPresentation.swift`. The iOS target also compiles `FieldLogApp.swift`, `WorkspaceView.swift`, `ProjectDetail.swift`, its own `EntryEditor.swift`, and `TaskEditorAppleFieldsHost.swift`. Android copies the Apple host file byte for byte and excludes it in the manifest. Android's production Swift sources have no direct reference to the shared presentation types outside their own file. Android's `PublicFactory.swift` renders its own Swift UI documents and calls the shared task logic. The single shared UI input establishes compile membership. Its Android link and runtime use remain unverified.
- **Logic.** Both targets list identical `TaskEditor.swift` and `Workspace.swift` as production Swift inputs. Each lists a different `WorkspaceRepository.swift`. The ordinary iOS target owns `WorkspaceModel.swift`. The Android target owns its draft reducer `EntryEditor.swift` and native entry adapter `NativeEntry.swift`.
- **Mixed.** Android's `PublicFactory.swift` combines UI rendering with action routing, persistence, photos, and report sharing. The whole-file method leaves its 62,537 bytes in the overall denominator without assigning a fraction to UI or logic. The receipt lists the app-owned Java and C adapters separately because the plan measures Swift.

The ordinary iOS `FieldLog.app` uses public FieldLog `552559d2` and the v80 SDK. The independently exported Android `AppAndroid` library uses the separate `Integrations/GeneratedReport` app from that commit, four v74 overlays, and the v74 SDK after the Pair23 preparation. The Android recipe installs maintained app source over the generated starter. SwiftPM selects the installed Android manifests and ignores the unrelated generated starter targets. [iOS build](https://github.com/snowdamiz/mixer/blob/e1202816e8bb5bbeb3583c0d458918923b895426/verification/receipts/fieldlog-ios-independent-export-v80.json), [Android build](https://github.com/snowdamiz/mixer/blob/e1202816e8bb5bbeb3583c0d458918923b895426/verification/receipts/fieldlog-independent-export-v74.json)

The prior iOS receipt covers a generic Simulator build. The Android launch receipt covers development-signed startup on an API 36 emulator. Its producer receipt hash differs from the compact v74 build receipt, and the pinned records lack a signed-to-unsigned APK hash binding. The earlier task-conflict audit covers a different patched workflow. The 90% whole-app goal remains unassessed because these app targets lack a matched revision and feature baseline. [Android launch](https://github.com/snowdamiz/mixer/blob/e1202816e8bb5bbeb3583c0d458918923b895426/verification/receipts/fieldlog-independent-export-android-launch-v74.json), [Task-conflict audit](https://github.com/snowdamiz/mixer/blob/e1202816e8bb5bbeb3583c0d458918923b895426/verification/receipts/fieldlog-d2-task-conflict-source-sharing-20261119.json)

## Shared task presentation in the ordinary Android editor

FieldLog tree `eb08569c13b5f65e25edd0dfde1fe70fc8278ece` uses
`TaskEditorPresentation` to build the inline title field and dispatch
title and responsible edits and Save from the ordinary Android checklist.
The app retains its action IDs, accessibility metadata, and discard on
close. The shared Android SPI crosses the production SwiftPM package
boundary. The two copies of the presentation source remain byte-identical.
[Full patch against FieldLog tree `380e7645`](../verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-full.patch)

The original candidate failed to compile across the production package
split. The corrected candidate and baseline passed the macOS host replay
through `PublicAndroidApplication` and the disk-backed repository. Discard
preserved the workspace bytes. Save persisted one task and one linked
`taskSaved` record through cold reopen. The corrected package also linked
an arm64 Android Swift library for API 28 with Swift 6.3.3 and Xcode 26.6.
The earlier Swift frontend crash under Xcode 27.2 remains recorded.
[Build and host receipt](../verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c.json) · [Xcode 27.2 failure receipt](../verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-xcode27-failure.json)

APK packaging and installed verification for this tree remain pending.
The historical counts above describe the earlier exports. The 90%
whole-app assessment still needs a matched application baseline.

## Reproduce the source measurement

From the Mixer repository on a Mac with Git, Python, and SwiftPM, run the following in Bash. The commands use the receipt, the public FieldLog pin, and the four overlays. They evaluate package metadata without building either app or resolving SDK dependencies.

```bash
set -euo pipefail
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
receipt="$PWD/verification/receipts/fieldlog-d2-app-source-sharing-v82.json"
python3 -B - "$work" "$receipt" <<'PY'
import hashlib, importlib.util, json, subprocess, sys
from pathlib import Path
from shutil import copyfile

work, receipt_path = map(Path, sys.argv[1:])
receipt = json.loads(receipt_path.read_bytes())
def run(*args):
    return subprocess.check_output(args)
def digest(data):
    return hashlib.sha256(data).hexdigest()

pin = receipt["fieldlog"]
public, patched, android = (work / name for name in ("ios", "patched", "android"))
run("git", "clone", "--quiet", "--depth=1", "--no-tags",
    "--revision=" + pin["revision"], pin["url"], public)
assert run("git", "-C", public, "rev-parse", "HEAD^{tree}").decode().strip() == pin["tree"]
run("git", "clone", "--quiet", public, patched)
target = receipt["targets"]["android"]
for overlay in target["overlaysInApplicationOrder"]:
    data = run("git", "show", target["overlaySourceRevision"] + ":" + overlay["path"])
    assert digest(data) == overlay["sha256"]
    subprocess.run(["git", "-C", patched, "apply", "--index", "-"], input=data, check=True)
assert run("git", "-C", patched, "write-tree").decode().strip() == target["fieldlogPatchedTree"]

manifest = public / "Package.swift"
source = manifest.read_bytes()
assert digest(source) == receipt["targets"]["ios"]["originalPackageSHA256"]
old = b'.package(url: "https://github.com/snowdamiz/mixer.git", revision: "56ff14c925168284761c5aca4f0bd4129cf3c995")'
manifest.write_bytes(source.replace(old, b'.package(path: "Generated/MixerSDK")')
                     .replace(b'package: "mixer"', b'package: "MixerSDK"'))

recipe_path = patched / target["recipe"]["originalPath"]
assert digest(recipe_path.read_bytes()) == target["recipe"]["sha256"]
spec = importlib.util.spec_from_file_location("fieldlog_recipe", recipe_path)
recipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recipe)
(android / "Platforms/Android/Tests/AppAndroidTests").mkdir(parents=True)
# The installer reads only the SDK pin list. Use the admitted matching app pins.
sdk_lock = android / "Generated/MixerSDK/Package.resolved"
sdk_lock.parent.mkdir(parents=True)
copyfile(recipe.APP / "Platforms/Android/Package.resolved", sdk_lock)
recipe.install_app_inputs(android, *recipe.app_inputs())
sdk_lock.unlink()
for platform, root in (("ios", public), ("android", android)):
    for path, expected in receipt["targets"][platform]["metadataSHA256"].items():
        assert digest((root / path).read_bytes()) == expected, path
    for unit in receipt["sourceUnits"].values():
        if platform in unit:
            row = unit[platform]
            data = (root / row["buildPath"]).read_bytes()
            assert (digest(data), len(data), data.count(b"\n")) == (
                row["sha256"], row["bytes"], row["physicalLines"]), row["buildPath"]
PY

for package in ios android android/Platforms/Android; do
    swift package --package-path "$work/$package" --scratch-path "$work/build" \
        --cache-path "$work/cache" --config-path "$work/config" \
        --security-path "$work/security" --manifest-cache none \
        --disable-dependency-cache describe --type json
done
plutil -convert json -o - "$work/ios/ios/FieldLog.xcodeproj/project.pbxproj"
```

Compare the source paths in the SwiftPM output to the receipt by target. For iOS, follow the `FieldLog` scheme to its app target and resolve that target's `PBXSourcesBuildPhase` and three local package products. The resulting list matches the v80 receipt's `bundle.compiledOriginalAppSources`. For Android, follow `AppAndroid` to `FieldLogAndroid` and its three `Application` products in the root package. Compare `sha256` for the admitted counterparts and sum `bytes` and `physicalLines` by category, counting each shared pair once in the union.
