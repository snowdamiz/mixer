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

From a Mixer checkout containing `6bc461f4fc`, use the checked-in
runner with macOS Xcode, Python 3.12 or later, and access to the three
pinned source archives. Use a new scratch path and a new receipt path
outside it. The runner reproduces the initial package-access errors
and compares the baseline and corrected host observations.

```sh
area=$(mktemp -d)
python3 -B tests/integration/fieldlog-task-presentation/replay.py \
  "$PWD" "$area/work" --receipt "$area/receipt.json"
```

Pass `--android-swift`, `--android-sdks`, and `--android-developer-dir`
with the Swift 6.3.3 toolchain, its Android SDK directory, and the Xcode
26.6 developer directory to add the Android Swift compile. A failed
requested compile returns a nonzero status and preserves its logs.
On success the runner removes its work directory after publishing the
receipt. If it reports unresolved custody, preserve the reported path.

## Matched compiler inputs

Both builds used Mixer `6bc461f4fc` and FieldLog product tree
`eb08569c13b5`. The Android packing tree adds eight recipe changes.
Independent APK readback verified the ordinary Android launcher, the
linked capability identity, and the call to the shared title field.
Xcode 27.2 linked the ordinary generic arm64 iPhoneOS target with OS
signing disabled. Its separate development-signed Entry Commit material
was added after linking and checked statically.
[Android build](../verification/receipts/fieldlog-d2-pair25-shared-editor-eb08569c.json) ·
[iPhoneOS build](../verification/receipts/fieldlog-d2-shared-task-presentation-eb08569c-iphoneos-corrected.json)

The observed rosters contain 15 Apple and 14 Android app-owned Swift
inputs. Comparing their exact bytes gives the following counts.

| Responsibility | Shared files | Shared bytes | Shared physical lines |
| --- | ---: | ---: | ---: |
| UI | 1 / 6 | 8,621 / 53,737 | 185 / 1,254 |
| Logic and host entry | 5 / 15 | 32,885 / 123,548 | 769 / 2,813 |
| Mixed | 0 / 2 | 0 / 79,958 | 0 / 1,300 |
| All measured inputs | 6 / 23 | 41,506 / 257,243 | 954 / 5,367 |

The shared UI input is `TaskEditorPresentation.swift`. The five shared
logic inputs are `EntryEditor.swift`, `EntrySaveDecision.swift`,
`FieldLogDraftStorage.swift`, `TaskEditor.swift`, and `Workspace.swift`.
The overall share is 17.8% by physical lines, below the 90% goal.
Installed behavior and native accessibility remain unverified for this
pair. [Matched compiler input receipt](../verification/receipts/fieldlog-d2-matched-compiler-inputs-eb08569c.json)

## Shared workspace repository

The next FieldLog tree, `e49ac6bb8229ab3cf8bb23e1176de6babd708054`,
uses byte-identical repository sources in the ordinary Apple and Android
packages. Each export keeps its own buildable package root. The shared
source retains existing snapshot, revision, attachment, outbox, and
atomic write behavior. Apple uses its existing add-photo operation.
The Android-only merged-draft photo operation remains guarded and does
not count as common execution.
[Exact patch against `eb08569c`](../verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb-patch.patch)

The host replay matched 11 baseline and candidate checkpoints for each
package path. Independent review reconstructed both traces and verified
the persisted record and attachment references. An Android arm64 library
and unsigned iPhoneOS app linked. The reported compile and host evidence
leave installed behavior open. The matched counts above cover the earlier
task presentation tree.
[Repository verification](../verification/receipts/fieldlog-d2-workspace-repository-e49ac6bb.json)

## Shared checklist rows

FieldLog `85e6fbe362` uses the same row projection in the ordinary
SwiftUI project screen and Android checklist. The projection supplies
the task and its move eligibility in the full project order. Android
applies its page boundary afterward. The platform routes preserve
their row identity and accessibility labels.
[Exact checklist patch](../verification/receipts/fieldlog-d2-checklist-row-85e6fbe3-patch.patch)

Both package paths compiled and passed the disk-backed host replay.
Android exercised moves in both directions across rows 20 and 21.
Apple verification covered the existing model handlers and linked
SwiftUI call site. Native presentation and interaction remain open.
[Checklist build and replay receipt](../verification/receipts/fieldlog-d2-checklist-row-85e6fbe3.json)

## Combined compiler inputs

FieldLog `85e6fbe362` built for generic arm64 iPhoneOS and as a Pair25
Android development APK on the same Mixer revision, `6bc461f4fc`.
The Android packaging recipe changes eight script files. The 16 Apple
and 15 Android app-owned Swift inputs match the same FieldLog product tree.
[Apple build](../verification/receipts/fieldlog-d2-combined-85e6fbe3-iphoneos.json) ·
[Android package](../verification/receipts/fieldlog-d2-pair25-combined-85e6fbe3.json)

| Responsibility | Shared files | Shared bytes | Shared physical lines |
| --- | ---: | ---: | ---: |
| UI | 2 / 7 | 9,311 / 54,262 | 206 / 1,273 |
| Logic and host entry | 6 / 14 | 48,353 / 111,201 | 1,132 / 2,512 |
| Mixed | 0 / 2 | 0 / 79,940 | 0 / 1,299 |
| All measured inputs | 8 / 23 | 57,664 / 245,403 | 1,338 / 5,084 |

Shared physical lines rose from 17.8% to 26.3%, below the 90% goal.
`ChecklistRow.swift` and `WorkspaceRepository.swift` account for the
two newly shared inputs. The byte-identical repository files include
49 Android-only photo code lines. Excluding those lines from the
shared numerator gives 1,289 of 5,084 physical lines (25.4%). Both
figures measure source overlap. Installed behavior remains unverified.
[Compiler input comparison](../verification/receipts/fieldlog-d2-combined-85e6fbe3-compiler-inputs.json)

## Shared checklist moves

FieldLog `64841ade77` uses `Workspace.taskOrder(moving:by:)` for
directional checklist moves on both targets. Apple resolves the move
inside its queued repository transaction and keeps drag ordering.
Android resolves it from the admitted presentation and verifies the
repository revision before saving. The moved task stays actionable
when it crosses the page boundary.
[Exact move patch](../verification/receipts/fieldlog-d2-checklist-move-source.patch)

The paired host replay checked completion, moves across rows 20–21,
stale and invalid action refusal, exact outbox changes, and cold reopen.
Both ordinary arm64 builds linked the shared model. Each roster pair
contains 21 distinct app-owned Swift inputs, eight of them byte-identical
across targets. The unshared portion fell from 3,293 to 3,287 lines as
shared source gained 13 lines.

| Responsibility | Baseline shared / total lines | Candidate shared / total lines |
| --- | ---: | ---: |
| UI | 452 / 1,470 | 452 / 1,470 |
| Logic and host entry | 1,061 / 2,037 | 1,074 / 2,043 |
| Mixed | 0 / 1,299 | 0 / 1,300 |
| All measured inputs | 1,513 / 4,806 | 1,526 / 4,813 |

The physical share rises from 31.5% to 31.7% in these
ordinary-build rosters. They exclude the additional signed Android
package targets in the preceding comparison. Android lists the
246-line, SwiftUI-only `TaskEditorAppleFieldsHost.swift` in its compiler
inputs with the file body disabled. Excluding that file and the 49
Android-only repository lines from the candidate's shared count gives
1,231 of 4,813 lines (25.6%). This adjustment covers the identified
conditional source. Native behavior remains a separate check.
[Host and build receipt](../verification/receipts/fieldlog-d2-checklist-move.json) ·
[Compiler inputs](../verification/receipts/fieldlog-d2-checklist-move-compiler-inputs.json)

## Shared project screens

FieldLog `e39a5ea393` shares checklist progress and actions, project
drafts and saved entries, and pending-change ordering and labels.
Apple keeps its native SwiftUI controls. Android keeps its captured
revision, render preflight, and page focus. The pending list reads
commits in reverse append order.
[Exact source patch](../verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3.patch)

The paired host tests exercised completion, moves across rows 20–21,
list and queue order, stale refusals, and exact cold reopen in each arm.
Both stock arm64 targets linked. Shared physical lines rose from 1,526
to 1,626, and unshared lines fell from 3,287 to 3,275. The shared lines
include 61 additional UI lines and 39 additional logic lines. The
deduplicated source total rose from 4,813 to 4,901 lines, with physical
overlap increasing from 31.7% to 33.2%. These compiler inputs include
conditional bodies that differ between targets. Device UI and Android
APK assembly remain unverified for this tree.
[Compiler rosters](../verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3-compiler-inputs.json) ·
[Host and build receipt](../verification/receipts/fieldlog-d2-ordinary-screens-e39a5ea3.json)

## Linked Create and editor composition

The two products compiled and linked from FieldLog tree
`74cdeca2ed0d4b0eb6b1bc1a6c5fa278b8ee498a`. The source roster matches
27 iOS Swift inputs and 16 standalone Android inputs to their linked
objects. Fourteen production Swift files match byte for byte. The
union counts a matched file once and counts each unmatched version
separately. [Linked source and object roster](../verification/receipts/l08-d2-composite-linked-rosters-20261123.json)

| Responsibility | Shared physical Swift lines | Swift union |
| --- | ---: | ---: |
| UI | 586 | 2,007 |
| Logic | 1,175 | 2,007 |
| Mixed | 607 | 1,767 |
| Total | 2,368 | 5,781 |

The measured Swift share is **40.96%** against the 90% target. The
standalone app union rises to **7,208** physical lines when it includes
the three app-owned Java and C adapters. SDK sources and XCTest stay
outside the app union. These linked products cover the measured
ordinary workflow composition. The matched Android app passed static
APK checks and still needs the installed replay.
[Build evidence](../verification/receipts/fieldlog-composite-native-handoff-25402a6b.json)

The corresponding iOS Simulator run passed all three original selectors.
Its stopped-workspace evidence covers task creation and completion,
reorder, draft and saved-entry navigation, queue paging and cold
readback. The Unicode, multiline and refusal controls remain host
evidence.
[Independent native review](../verification/receipts/l08-d2-composite-native-independent-review-dfb0d819.json)

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
