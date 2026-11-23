# Upgrade, recover, and exit

This guide upgrades a locked Mixer project to a new SDK. It also covers
recovery from an interrupted edit and a build of the Android export without
the Mixer CLI. The commands use the FieldLog Android example.

## Before you start

- Export a recovery copy with the original CLI and host Swift toolchain before
  you change the project's SDK.
- Close editors and builds.
- Back up installed app data, signing material, and any files that export
  excludes.
- Set the Android toolchain variables from
  [Build for Android](../../README.md#build-for-android) and use Xcode 26.6
  throughout.
- Run the commands from a checkout of the public Mixer repository with both
  Mixer revisions available locally.

## Build both CLIs and prepare the old project

These commands build the original and target CLIs and prepare the FieldLog
project with the original one.

```sh
mixer_repo="$(git rev-parse --show-toplevel)"
upgrade_rev=02002272c334dd0a3750c502ad5819b26d57fe0d
pair20_rev=8efc1a9e5b1602117f8211c95bfd4203cc91f689
fieldlog_rev=552559d2d3278abb9b1aa7dcf0288102c09a202b
work="$(mktemp -d "${TMPDIR:-/tmp}/mixer-upgrade.XXXXXX")"
target_checkout="$work/upgrade-inputs"
mkdir "$target_checkout"
git archive "$upgrade_rev" cli sdk updates native/android | tar -xf - -C "$target_checkout"

git clone --shared --no-checkout "$mixer_repo" "$work/pair20"
git -C "$work/pair20" sparse-checkout set cli sdk updates native/android
git -C "$work/pair20" checkout --detach "$pair20_rev"

swift build --package-path "$work/pair20/cli" --scratch-path "$work/pair20-cli" \
	--cache-path "$work/pair20-cache" --jobs 6 --product mixer
swift build --package-path "$target_checkout/cli" --scratch-path "$work/upgrade-cli-build" \
	--cache-path "$work/upgrade-cli-cache" --jobs 6 --product mixer
old_cli="$work/pair20-cli/debug/mixer"
new_cli="$work/upgrade-cli-build/debug/mixer"
"$old_cli" version
"$new_cli" version

git clone --depth 1 --filter=blob:none --sparse https://github.com/snowdamiz/fieldlog.git \
	"$work/FieldLog-baseline"
git -C "$work/FieldLog-baseline" fetch --depth 1 --filter=blob:none origin "$fieldlog_rev"
git -C "$work/FieldLog-baseline" sparse-checkout set Integrations/GeneratedReport
git -C "$work/FieldLog-baseline" checkout --detach "$fieldlog_rev"
source_project="$work/FieldLog-old"
python3 "$work/FieldLog-baseline/Integrations/GeneratedReport/scripts/build-android.py" \
	--mixer "$old_cli" --sdk-checkout "$work/pair20" \
	--android-adapter-path "$work/pair20/native/android" \
	--output "$source_project" --prepare-only
```

## Seed the lock, upgrade, and build

The historical recipe leaves the Android package lock absent. To test lock
preservation, seed the prepared project with the FieldLog platform lock from
the Pair23 migration. The first command applies only the lock file from that
patch.

```sh
platform_lock=Platforms/Android/Package.resolved
fieldlog_path=Integrations/GeneratedReport/$platform_lock
git -C "$work/FieldLog-baseline" apply --include="$fieldlog_path" \
	"$mixer_repo/verification/fieldlog-pair23/public-build.patch"
cp "$work/FieldLog-baseline/$fieldlog_path" "$source_project/$platform_lock"

recovery_copy="$work/FieldLog-recovery"
upgraded_project="$work/FieldLog-upgraded"
build_copy="$work/FieldLog-build"
"$old_cli" export "$recovery_copy" --directory "$source_project"
"$new_cli" upgrade "$upgraded_project" --directory "$source_project" \
	--sdk-path "$target_checkout/sdk" \
	--android-adapter-path "$target_checkout/native/android"
cmp "$source_project/$platform_lock" "$upgraded_project/$platform_lock"
"$new_cli" export "$build_copy" --directory "$upgraded_project"
"$new_cli" build --platform android --directory "$build_copy"
```

The upgrade writes the new SDK, Android adapter, and `mixer.lock` into a new
copy. It keeps an existing `Platforms/Android/Package.resolved`. If the Android
dependency pins conflict, follow your app's dependency migration for the target
SDK.

## Upgrade an iOS Starter

Set `new_cli` to a CLI with the iOS 17 Starter migration and
`target_checkout` to the checkout of that revision. Set `source_project`
to your iOS Starter and `upgraded_project` to a new path. For an iOS-only
Starter, omit `--android-adapter-path`.

```sh
"$new_cli" upgrade "$upgraded_project" --directory "$source_project" \
	--sdk-path "$target_checkout/sdk"
"$new_cli" build --platform ios --directory "$upgraded_project"
```

The upgrade copies the source project, then replaces the bundled SDK and
updates `mixer.lock` in the copy. For a byte-for-byte match to the stock iOS
26 Starter `Package.swift`, the upgrade changes the manifest to iOS 17 and
regenerates the existing stock Xcode project in the same copy. If Mixer
reports `generate.modified`, reconcile your edits to the generated Xcode
project before retrying. If you edited `Package.swift`, the upgrade copies
it byte for byte. Review your app's minimum iOS version and dependency
requirements before building that copy.

## Upgrade the maintained FieldLog app

Build the maintained FieldLog app from its app-owned
`ios/FieldLog.xcodeproj`. `mixer upgrade` replaces the bundled SDK and
updates `mixer.lock`. Update the separately bundled capability packages,
package locks, VM headers, and VM archive for the same pin before rebuilding.
Follow the maintained FieldLog export recipe for those inputs. Reopen your
saved data in the upgraded app before switching to it.
[Maintained FieldLog iOS build](fieldlog-ios-export.md#build-the-maintained-fieldlog-app-with-the-capability-vm)

## Exercise the Pair24 to Pair25 upgrade with a public V4 Starter

Use the Android toolchain variables from the README and a fresh `work`
directory. Build the host CLIs with Xcode 27.2, then use Xcode 26.6 for the
Android commands. Both CLI builds and the exported app resolve their locked
Swift dependencies. An existing verified local mirror of each package can
supply those revisions.

```sh
pair24=59cab78cd8ac7a43c718914fc83fb56b33e3ef60
pair25=57f3ed4f17b80f15fc6d646b14c6dbfa05bd7eea
for rev in "$pair24" "$pair25"; do
    mkdir "$work/$rev"
    git archive --format=tar -o "$work/$rev.tar" "$rev" cli sdk updates runtime-identity native/android
    tar -xf "$work/$rev.tar" -C "$work/$rev"
    DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
        swift build --package-path "$work/$rev/cli" --scratch-path "$work/$rev-cli" \
        --only-use-versions-from-resolved-file --product mixer
done
old_cli="$work/$pair24-cli/debug/mixer"
new_cli="$work/$pair25-cli/debug/mixer"
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer

"$old_cli" create UpgradeStarter --platform android --android-host public-v4 \
    --directory "$work/Pair24" --sdk-path "$work/$pair24/sdk" \
    --android-adapter-path "$work/$pair24/native/android"
"$old_cli" export "$work/Recovery" --directory "$work/Pair24"
"$new_cli" upgrade "$work/Pair25" --directory "$work/Pair24" \
    --sdk-path "$work/$pair25/sdk" --android-adapter-path "$work/$pair25/native/android"
cmp "$work/Pair24/Platforms/Android/Package.resolved" "$work/Pair25/Platforms/Android/Package.resolved"
"$new_cli" export "$work/Export" --directory "$work/Pair25"
mv "$work/Export" "$work/IndependentProject"
(
    cd "$work/IndependentProject"
    python3 Generated/MixerAndroid/android-build.py build "$PWD"
)
```

Use your installed Xcode 27.2 path in the CLI build command. The Pair25 CLI
reports `android.sdk-profile-mismatch` if you build or export the Pair24
project directly. The public V4 APK targets API 37 and requires API 36. Check
the arm64 ELF, exact launcher, 16 KiB APK alignment, notices, and retained
platform lock in the [independent export receipt](../../verification/receipts/l01-l08-pair25-independent-export-20261119.json).

## Recover from an interrupted project edit

If upgrade reports `lock.sdk-drift` after an interrupted SDK edit, save the
damaged file separately. Then restore the original bytes from the recovery
copy. If the damage is limited to the bundled SDK manifest, run these commands
before you retry the upgrade.

```sh
sdk_manifest=Generated/MixerSDK/Package.swift
cp "$source_project/$sdk_manifest" "$work/damaged-Package.swift"
cp "$recovery_copy/$sdk_manifest" "$source_project/$sdk_manifest"
```

If an upgrade destination already exists, keep it and choose a fresh
destination for the retry. If an interrupted FieldLog save reports a storage
error, close and reopen the workspace. Check the saved entry, draft, and outbox
before you try the save again.

## Test an installed upgrade on iOS Simulator

Build both app versions from the pinned checkouts and import a photo through
Files. The replay replaces the app in place. It checks that the same draft,
JPEG, and pending changes survive. Follow the
[installed upgrade replay](../../tests/integration/fieldlog-ios-installed-upgrade/README.md).

## Build an Android export without the Mixer CLI

Export a fresh copy to move to a build machine. Keep its bundled SDK, Android
adapter, and dependency lock together. Use the tool versions and installation
paths recorded in `mixer.lock`. Move installed app data separately.

```sh
exit_copy="$work/FieldLog-exit"
mkdir "$work/NativeExit"
"$new_cli" export "$exit_copy" --directory "$upgraded_project"
mv "$exit_copy" "$work/NativeExit/FieldLogGenerated"
(
	cd "$work/NativeExit/FieldLogGenerated"
	python3 Generated/MixerAndroid/android-build.py build "$PWD"
)
```

The FieldLog build writes `.mixer/android-build/FieldLogGenerated-unsigned.apk`
in the export. The public replay built this APK while the original project,
the SDK checkouts, and the Mixer CLI builds were unavailable. It also reopened
a saved FieldLog workspace through the app's storage code on the host. See the
[upgrade, recovery, and exit replay](../../verification/receipts/l08-public-upgrade-02002272.json).

For a disposable development replay, stop FieldLog before copying
`files/FieldLog/workspace.json` and the matching `files/FieldLog/photos/`
directory. Restore both to the exported development app before its first
launch. The replay used `adb run-as`, which requires a debuggable app.
The two APKs had different development certificates and used separate
installs. Keep the backup until the exported app opens the same draft
and saved entry, lists the pending changes, and reads back the same
workspace and photo bytes.
[Installed Android exit replay](../../verification/receipts/fieldlog-e39a5ea3-relocated-android-workspace-readback.json)

To run this build from the maintained FieldLog source with the v74 SDK,
follow the [independent Android CI replay](fieldlog.md#build-the-v74-export-in-independent-android-ci).
