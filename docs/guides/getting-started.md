# Getting started

This guide builds the Mixer CLI, creates starter apps for iOS and Android,
exports them, and inspects an existing Swift app. Local builds need no payment
service and no store credentials. They may resolve pinned SwiftPM dependencies.

## Requirements

- An Apple silicon Mac with Xcode, the iOS Simulator SDK, and Swift 6.2 or later.
- A checkout of the public `snowdamiz/mixer` repository. Run every command from
  its root.
- For Android only: the tools listed in [Build for Android](#build-for-android).

## Build the CLI

The pinned revision supplies a matching CLI, SDK, and Android adapter. Set
`DEVELOPER_DIR` to your Xcode installation.

```sh
mixer_rev=c7956233d69caeffadfa5ab84227c3b2e09ff41d
work="$(mktemp -d "${TMPDIR:-/tmp}/mixer-local.XXXXXX")"
mkdir "$work/inputs" "$work/exports"
git archive "$mixer_rev" cli sdk updates native/android | tar -xf - -C "$work/inputs"
export DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer
swift build --package-path "$work/inputs/cli" --scratch-path "$work/cli-build" --product mixer
mixer_cli="$work/cli-build/debug/mixer"
"$mixer_cli" version
```

Keep the CLI beside its SwiftPM resource bundle.

## Build for iOS Simulator

```sh
"$mixer_cli" create LocalIOS --platform ios --directory "$work/LocalIOS" \
	--sdk-path "$work/inputs/sdk"
"$mixer_cli" export "$work/exports/LocalIOS" --directory "$work/LocalIOS"
"$mixer_cli" config validate --directory "$work/exports/LocalIOS"
ios_export="$work/exports/LocalIOS"
xcode_pins="$ios_export/Platforms/iOS/LocalIOS.xcodeproj/project.xcworkspace/xcshareddata/swiftpm"
mkdir -p "$xcode_pins"
cp "$ios_export/Generated/MixerSDK/Package.resolved" "$xcode_pins/Package.resolved"
"$mixer_cli" build --platform ios --directory "$work/exports/LocalIOS"
```

Copying `Package.resolved` gives Xcode the same Swift package revisions as the
bundled SDK. The build creates an unsigned `LocalIOS.app` under
`.mixer/ios-build/Build/Products/Debug-iphonesimulator/` in the export.

## Build for Android

Install these tools and keep the same selections during creation, export, and
build:

- The official Swift 6.3.3 toolchain and its Android Swift SDK.
- NDK r27d, Android platform 37.0, and build-tools 37.0.0.
- JDK 25 and Python 3.
- Xcode 26.6 with its macOS 26.5 SDK for the Android cross-build.

Set these paths to your installations, then create, export, and build:

```sh
export DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer
export MIXER_SWIFT="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift"
export MIXER_SWIFT_SDKS_PATH="$HOME/Library/org.swift.swiftpm/swift-sdks"
export MIXER_ANDROID_ARTIFACT_PATH="$MIXER_SWIFT_SDKS_PATH/swift-6.3.3-RELEASE_android.artifactbundle/swift-android"
export ANDROID_HOME=/opt/homebrew/share/android-commandlinetools
export MIXER_JDK=/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home

"$mixer_cli" create LocalAndroid --platform android --directory "$work/LocalAndroid" \
	--sdk-path "$work/inputs/sdk" --android-adapter-path "$work/inputs/native/android"
cmp "$work/LocalAndroid/Platforms/Android/Package.resolved" \
	"$work/LocalAndroid/Generated/MixerSDK/Package.resolved"
"$mixer_cli" export "$work/exports/LocalAndroid" --directory "$work/LocalAndroid"
"$mixer_cli" config validate --directory "$work/exports/LocalAndroid"
"$mixer_cli" build --platform android --directory "$work/exports/LocalAndroid"
```

Creation seeds `Platforms/Android/Package.resolved` with the SDK's pins, and
export keeps that lock. The build produces an unsigned arm64 APK at
`.mixer/android-build/LocalAndroid-unsigned.apk` in the export. The default
Android host is `legacy-v1`. To select the public V4 host, add
`--android-host public-v4` at creation.

## Export a project

Export to a new directory outside the source project. You can move the export
and build it after the original project and SDK checkout are gone. The export
includes the app source, the locked SDK, and the Android adapter when present.
It excludes build caches, dotenv secrets, signing credentials, and provisioning
profiles. Back up data stored by an installed app separately.

## Inspect an existing Swift app

```sh
"$mixer_cli" import "$work/LocalIOS/Sources" --output "$work/import.json"
```

Replace the source path with your app's Swift directory. The importer writes an
advisory migration report. Apply its suggested changes in your own project. The
report does not confirm that the app can run on Mixer.

For a Swift package you trust, generate a description with SwiftPM and pass it
to the importer. Use the package root for both commands.

```sh
swift package --package-path "$package" describe --type json > "$work/package-description.json"
"$mixer_cli" import "$package" --swiftpm-description "$work/package-description.json"
```

SwiftPM evaluates the manifest when it generates the description. The report
marks targets with missing or uninspected sources as `unverified-sources`.
Refresh the description after you change the package.

## Upgrade a locked project

The current Android CLI creates projects with source pair 25. Build or export a
project locked to pair 24 with its matching CLI. To move it to the current CLI,
export a recovery copy with the original CLI, then run `mixer upgrade` into a
new directory. The upgrade writes the new SDK, Android adapter, and
`mixer.lock`, and keeps an existing `Platforms/Android/Package.resolved`.

[Upgrade, recover, and exit](upgrade-recover-and-exit.md) walks through a full
FieldLog Android example.

## Next steps

- [CLI reference](cli.md)
- [Add a Mixer screen to a UIKit app](uikit-migration.md)
- [FieldLog fixtures and replays](fieldlog.md)
