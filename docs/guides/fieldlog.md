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
