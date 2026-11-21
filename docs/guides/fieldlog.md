# FieldLog fixtures and replays

FieldLog is the real Swift app that tests Mixer end to end. It lives in the
separate [`snowdamiz/fieldlog`](https://github.com/snowdamiz/fieldlog)
repository. This guide reproduces the FieldLog builds and replays used in
Mixer's verification.

Build the Mixer CLI first with the
[README quick start](../../README.md#create-export-and-build-a-local-app).
The commands below reuse its `$work` directory. Run them from the Mixer
checkout.

## Apply the Pair23 Android migration

The Android export used FieldLog revision
`552559d2d3278abb9b1aa7dcf0288102c09a202b` with a local five-file migration.
The migration updates the downstream workflow, the recipe, the recipe tests,
the README, and the app-specific `Platforms/Android/Package.resolved`. Apply the
verified patches to a fresh FieldLog checkout.

```sh
fieldlog_fixtures="$(pwd)/verification/fieldlog-pair23"
git clone https://github.com/snowdamiz/fieldlog.git "$work/FieldLog"
git -C "$work/FieldLog" checkout --detach 552559d2d3278abb9b1aa7dcf0288102c09a202b
git -C "$work/FieldLog" apply "$fieldlog_fixtures/public-build.patch"
git -C "$work/FieldLog" apply "$fieldlog_fixtures/draft-fields.patch"
```

The first patch reproduces the public export build. The second keeps field
identities within each draft and gives new drafts fresh fields. Together they
reproduce the app sources used for the Android photo persistence test. See the
[build receipt](../../verification/receipts/fieldlog-public-pair23-export-41a05264.json)
and the
[runtime receipt](../../verification/receipts/fieldlog-android-photo-persistence-41a05264.json).

## Apply the Android Activity lifecycle fixes

These two fixes let the Android app return from the photo picker and the
report share sheet. Apply them to the same checkout.

```sh
git -C "$work/FieldLog" apply "$fieldlog_fixtures/photo-return.patch"
git -C "$work/FieldLog" apply "$fieldlog_fixtures/report-return.patch"
```

The Activity delivers each result after it resumes and its window regains
focus. On API 36, a separate app read the exported report offline. On return,
FieldLog showed the share-sheet closure message and kept the workspace and
queued changes. See the
[report transfer and return receipt](../../verification/receipts/fieldlog-android-offline-report-return-41a05264.json).

## Build the generated report app

With the migration applied, follow `Integrations/GeneratedReport/README.md` in
the FieldLog checkout. Use the CLI, SDK checkout, and adapter from Mixer
revision `735ecec14e10e2dfed1e58a122c3fab08e569bef` for that recipe. The recipe
uses `public-v4` and keeps FieldLog's own dependency pins.

1. Run the recipe with `--prepare-only` to create the project.
2. Pass the prepared project to `mixer export`.
3. Pass the export to `mixer build --platform android`.

The receipt covers a relocated development APK build. Signed update and
rollback checks cover separate development fixtures. The ordinary FieldLog
mobile OTA workflow is still open. See the
[current status](../../STATUS.md#november-18-local-verification).

## Build the v74 export in independent Android CI

Run this replay on an Apple silicon Mac with Python 3.12 or later and the
toolchain variables from [Build for Android](../../README.md#build-for-android).
Use Xcode 26.6 for `DEVELOPER_DIR` and Xcode 27.2 for the host CLI builds.
The replay fetches the pinned FieldLog and Pair23 checkouts and the locked
SwiftPM dependencies. The local Mixer checkout needs the v74 commit.

```sh
	mkdir -p verification/local
	python3 -B tests/integration/fieldlog-independent-export/replay.py \
		--host-developer-dir /Applications/Xcode.app/Contents/Developer \
		--receipt verification/local/my-fieldlog-v74-export.json
```

Use a new path for `--receipt`. The replay applies the four patches above,
prepares FieldLog with the Pair23 recipe, and upgrades the project with the
CLI from v74 (`44aecbeb6a82a4a93321cff6a8ab86c5aa421900`). It keeps FieldLog's
platform lock and compares app-owned files before and after export.

The replay moves the export to a fresh `Build/CI` directory and removes the
preparation tree. The bundled Android driver then builds the unsigned APK
with a fresh home, caches, and output directory. The receipt captures the
source and lock hashes, APK checks, and scratch cleanup. This is the Android
build step of product plan §16.3. The installed launch is a separate step.
[Verified build receipt](../../verification/receipts/fieldlog-independent-export-v74.json)

## Replay offline sync and the photo queue

- [FieldLog offline sync replay](../../tests/integration/fieldlog-entry-sync/README.md).
  On macOS, the first replay checks the queue after a lost acknowledgement. The
  second cancels a partial photo upload, restarts the client, and checks the
  resumed JPEG against the saved bytes.
- [Android photo queue replay](../../tests/integration/fieldlog-android-queue/README.md).
  It prepares FieldLog from the pinned public sources and runs the generated
  Android entry point against the local backend. The same sources build an
  unsigned arm64 APK.
- [Installed upgrade replay](../../tests/integration/fieldlog-ios-installed-upgrade/README.md).
  It replaces the iOS app in place and checks that the draft, JPEG, and pending
  changes survive.

## Produce and inspect a signed update

[Produce and inspect a local FieldLog update](../../cli/release-tools/README.md)
builds both update variants and runs `mixer release inspect` on them.
