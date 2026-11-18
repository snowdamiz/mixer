# Replay the FieldLog Android photo queue

The ordinary **On device** screen sends a saved entry with one JPEG through the opt-in local sync adapter. The first replay interrupts the upload through the cancel action. The second closes the presentation owner. Both restart the client, resume from the server-confirmed offset, and reconcile a lost final acknowledgment. Each run checks the exact JPEG, one remote event, and the remaining local outbox.

## Run on macOS

Use Apple silicon, Xcode, Git and Python 3.12 or later. Run from the Mixer checkout. The first command creates a new scratch directory. The fetch step downloads the pinned public sources for FieldLog, Mixer Pair23, Swift Crypto and Swift ASN.1. Source preparation checks each patch against its SHA-256 and checks the resulting FieldLog Git tree.

```sh
fixture="$PWD/tests/integration/fieldlog-android-queue"
work=$(mktemp -d "$PWD/verification/local/fieldlog-android-queue.XXXXXXXX")
"$fixture/fetch.sh" "$work/sources"
python3 -B "$fixture/prepare.py" "$work/sources" "$work/prepared"
mkdir "$work/receipts"
"$fixture/journey/replay.sh" "$work/sources" "$work/prepared" "$work/receipts"
```

The macOS replay drives the generated Android Swift entry point against a local HTTP and SQLite backend. An Android session file supplies a loopback port and a synthetic token scoped to one workspace and project. Without that file, the queue stays offline. The source manifest records the accepted app tree, dependency pins and build identities. [Inputs](inputs.json)

## Build the Android export

Use Xcode 26.6, Swift 6.3.3 and its Android SDK with NDK r27d, Android platform 37 with build-tools 37.0.0, and JDK 25. Set the paths to those installations and run the packaging replay on the same prepared sources. The Pair23 packaging patch admits Android's system zlib for FoundationNetworking.

```sh
export DEVELOPER_DIR=/path/to/Xcode_26.6.app/Contents/Developer
export MIXER_SWIFT=/path/to/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift
export MIXER_SWIFT_SDKS_PATH=/path/to/swift-sdks
export ANDROID_HOME=/path/to/android-sdk
export MIXER_JDK=/path/to/jdk-25/Contents/Home
"$fixture/android/replay.sh" "$work/sources" "$work/prepared"
```

Inspect the unsigned APK and its linkage report under `$work/prepared/android-run`. Remove disposable scratch after the commands exit. The original API 36 run used a development-signed APK. It restored an uncommitted draft, saved its photo, resumed the transfer at 65,536 bytes, and reopened the committed workspace offline. [Original native receipt](../../../verification/receipts/fieldlog-android-ordinary-queue-runtime-41a05264.json) · [Resumable backend controls](../fieldlog-entry-sync/README.md)
