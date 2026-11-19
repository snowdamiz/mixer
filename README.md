# mixer

An independently implemented Swift mobile platform in active development. The
complete scope is [mixer-product-plan.md](mixer-product-plan.md); this repository
does **not** yet satisfy its general-availability or FieldLog gates.

The engine uses official Swift compilers, an owned Swift UI/state contract, native
platform adapters, an owned Rust Wasm interpreter, and separately authorized signed
artifacts and rollout assignments. No Patch/Skip implementation is used.

The iOS product target is **iOS 26.0 and later**, including iOS 27 and subsequent
releases. Package and generated app deployment minimums are 26.0. Runtime
qualification across supported versions remains pending; see product-plan §19.1.

## Development progress

The implementation plan is complete when the eight local gates L01–L08 pass.
Each gate needs working behavior on iOS Simulator and Android emulator with the
console, API, database, workers, and update delivery running locally. Payments,
physical phones, store approval, and live deployment do not block these gates.
They belong to the separate launch checklist.

This snapshot is from November 19, 2026. Run `python3 scripts/progress.py` to
print the table below from the current records. Each mark in **Progress** is one
item in ID order: `█` passed, `▒` in progress, `✗` blocked or failed, and `░` not
started.

| Checklist | Progress | Passed | In progress | Blocked | Not started | Record |
| --- | --- | --- | --- | --- | --- | --- |
| Local gates L01–L08 | `█▒▒▒▒▒▒▒` | 1 | 7 | 0 | 0 | [`gates/local.json`](gates/local.json) |
| FieldLog milestones D0–D6, D8 | `░░▒▒▒▒░░` | 0 | 4 | 0 | 4 | [`dogfood/receipts/milestones.json`](dogfood/receipts/milestones.json) |
| Work packages W01–W18 | `▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒░` | 0 | 17 | 0 | 1 | [`work-graph.json`](work-graph.json) |
| Launch gates G01–G38 | `░▒░░░░░░░░░░▒▒▒▒░░░░░░░░▒▒▒░░░░░░░░░░░` | 0 | 8 | 0 | 30 | [`gates/ga.json`](gates/ga.json) |

### Local gate checklist

A gate is checked only when its record in `gates/local.json` says `passed`.
A checked sub-item has a receipt that shows the behavior at the scope the
receipt states. That evidence does not pass its gate by itself. Unchecked
sub-items are the main open work, not a complete list.
[STATUS.md](STATUS.md) has the full history.

- [x] **L01 Setup, adoption, and export.** Passed independent review on
  November 18. The public CLI and SDK create, export, and build starter apps
  for both targets, and the importer reports on FieldLog's iOS source.
  [L01 decision](verification/receipts/l01-independent-final-review-41a05264.json)
- [ ] **L02 Shared app and native UI.** In progress.
  - [x] The FieldLog task-conflict workflow ran on an iOS 27 Simulator and an
    Android 16 emulator against one shared task contract.
    [Paired workflow](verification/receipts/fieldlog-d2-task-conflict-source-sharing-20261119.json)
  - [x] On Android, FieldLog returns from the report share sheet with its
    workspace and queued changes intact.
    [Report return](verification/receipts/fieldlog-android-offline-report-return-41a05264.json)
  - [ ] Save draft in the Android guest editor. The emulator showed blank frames
    after Save, and the workspace did not change.
    [Latest trace](verification/receipts/fieldlog-android-save-current-frame-root-r6016.json)
  - [ ] Text scaling for accessibility. In a macOS probe, semantic fonts kept
    their size when the text size setting changed.
    [Scale probe](verification/receipts/fieldlog-localization-scale-c2bae0e57.json)
  - [ ] The full screen, navigation, input, and accessibility matrix on both
    targets.
- [ ] **L03 Compiler and owned runtime.** In progress.
  - [x] FieldLog guests run in the owned VM on macOS and save and reload a task.
    [Guest execution](verification/receipts/fieldlog-guest-five-export-repair-r5790.json)
  - [x] Five paired macOS runs matched native and guest results over 60
    actions each.
    [Matched workload](verification/receipts/fieldlog-matched-persisted-host-41a05264.json)
  - [x] Both iOS guest variants passed exact input, Save, dismissal, and
    relaunch on Simulator as bundled guests.
    [Simulator run](verification/receipts/fieldlog-ios-both-variant-save-reopen-root-r6054.json)
  - [x] A macOS benchmark measured a median of 0.50 µs native and 317.27 µs in
    the owned VM from prepared input to frame. The guest is 2,691 bytes gzipped.
    [Host benchmark](verification/receipts/l03-d3-task-completion-host-benchmark-7b61fe1c.json)
  - [ ] A compact guest for signed delivery. The bundled guests exceed the
    signed runtime's 4 MiB limit and use a different ABI.
  - [ ] Guest parity and performance on iOS Simulator and Android emulator.
  - [ ] Complete conformance, fuzzing, differential, and resource-limit checks.
- [ ] **L04 Safe OTA and recovery.** In progress.
  - [x] On Android, a signed guest read the saved task before its first frame.
    The app kept its workspace through Activity recreation, rollback, and a
    cold offline reopen, and it resumed a partial download.
    [Android runtime](verification/receipts/fieldlog-android-hydrated-signed-runtime-41a05264.json)
  - [x] On iOS Simulator, one installed FieldLog task survived a signed
    baseline, review, and rollback, then launched without the delivery URL.
    [iOS runtime](verification/receipts/fieldlog-ios-hydrated-signed-runtime-41a05264.json)
  - [x] Installed Android key rotation passed, and the app kept its update
    offline across the key change.
    [Key rotation](verification/receipts/fieldlog-android-key-rotation-native-41a05264.json)
  - [x] The release origin gives each Android runtime its own signed offer and
    refuses delivery to a different runtime.
    [Runtime cohorts](verification/receipts/fieldlog-android-runtime-cohort-offers-501eca8a.json)
  - [x] `mixer release inspect` reports `ota-compatible` for an eligible edit
    and `store-build-required` for a new Android permission.
    [Inspector cases](verification/receipts/l04-release-inspector-source150-41a05264.json)
  - [ ] Signed delivery through FieldLog's supported entry points, which the
    independent review requires.
    [L04 review](verification/receipts/l04-independent-review-9fd7e7f6eb-41a05264.json)
  - [ ] iOS key rotation.
  - [ ] Installed rollback with FieldLog's selected-draft adapter on both
    targets.
  - [ ] Android in-place binary replacement that keeps the workspace.
- [ ] **L05 Local platform workflow.** In progress.
  - [x] A browser **Create build** click returned HTTP 201 and queued one
    build and one job in PostgreSQL.
    [Browser create](verification/receipts/free-workspace-default-build-create-root-r5990.json)
  - [x] A free iOS Starter build reached `native_succeeded` through Phoenix,
    restricted Oban, and one Xcode run.
    [Closed Starter build](verification/receipts/l05-l07-native-starter-closed-20261119.json)
  - [x] A free client downloaded the app, symbols, and inventory after worker
    shutdown. Cancellation during an Xcode run released capacity once.
    [Native build](verification/receipts/l05-combined-native-build-41a05264.json)
  - [x] Against provider fixtures, the store CLI reconciled a lost
    acknowledgement on both platforms with one submission each.
    [Store fixtures](verification/receipts/l05-local-submission-reconciliation-41a05264.json)
  - [ ] Authenticated artifact delivery and a backup from one closed Starter
    build.
  - [ ] One run of the whole workflow, including update, promotion, and
    rollback.
- [ ] **L06 Free accounts and administration.** In progress.
  - [x] A real browser signed in and created a free organization and project
    with payments disabled.
    [Browser onboarding](verification/receipts/free-workspace-browser-onboarding-root-r5946.json)
  - [x] Over local HTTP, a free owner passed login, authorization, quotas,
    export, and deletion.
    [Self-service HTTP](verification/receipts/free-self-service-http-private-evidence-r5868.json)
  - [x] The console refused organization exit until the owner's build
    settled. Another tenant kept its export and access.
    [Settled exit](verification/receipts/l06-settled-exit-65c89e08.json)
  - [ ] One browser journey in which a free owner manages the workspace and
    uses its build services.
    [Browser administration](verification/receipts/l06-combined-console-browser-793196991d.json)
- [ ] **L07 Security and local reliability.** In progress.
  - [x] Release metadata and artifacts restored from a PostgreSQL backup.
    [Backup and restore](verification/receipts/release-postgres-backup-restore-20261118.json)
  - [x] The API recovered browser sessions after a refused pool checkout and
    after both browser lifecycle connections were exhausted.
    [Session recovery](verification/receipts/l07-recovery-v33-41a05264.json) ·
    [Checkout recovery](verification/receipts/l07-bounded-checkout-recovery-c2bae0e5.json)
  - [ ] Backup and restore of one closed native build, reconciled with Phoenix.
  - [ ] An independent provenance and licensing review.
- [ ] **L08 FieldLog and documentation.** In progress.
  - [x] The public upgrade, recovery, and exit replay built FieldLog's Android
    APK without the original project, SDK checkouts, or Mixer CLI.
    [Upgrade and exit replay](verification/receipts/l08-public-upgrade-02002272.json)
  - [x] In host checks, FieldLog's storage writers for both platforms refused
    overlapping draft and entry IDs and recovered after a write fault.
    [Storage checks](verification/receipts/fieldlog-l08-cross-platform-draft-overlap-20261119.json)
  - [ ] The complete FieldLog workflow on both targets through public tooling,
    including OTA, rollback, and export.
  - [ ] The reviewed 20-change OTA corpus.

### FieldLog dogfood milestones

L08 needs the local version of every milestone except D7. Statuses come from
the `localAcceptance` records in `dogfood/receipts/milestones.json`.

- [ ] **D0 Baseline.** Not started.
- [ ] **D1 Engine adoption.** Not started.
- [ ] **D2 Shared Android.** In progress.
- [ ] **D3 Interpreted parity.** In progress.
- [ ] **D4 OTA delivery.** In progress.
- [ ] **D5 Recovery.** In progress.
- [ ] **D6 Platform workflow.** Not started.
- **D7 Production use.** Deferred. The plan does not require it.
- [ ] **D8 Scenario confidence.** Not started.

## Create, export, and build a local app

Run these commands on an Apple silicon Mac from a checkout of the public
`snowdamiz/mixer` repository. This Pair24 pin supplies the matching CLI, SDK,
and Android adapter used by the corrected default starter.
Set `DEVELOPER_DIR` to your Xcode installation with the iOS Simulator SDK
and Swift 6.2 or later.

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

Keep the CLI beside its SwiftPM resource bundle. Local builds may resolve
pinned SwiftPM dependencies. They require neither a payment service nor
store credentials.

### Export and build for iOS Simulator

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

The fresh export seeds Xcode’s workspace lock from the bundled SDK so the app
uses the same Swift package revisions. The build creates an unsigned `LocalIOS.app` under
`.mixer/ios-build/Build/Products/Debug-iphonesimulator/` in the export.
The relocated starter built for arm64 Simulator. [Local verification](STATUS.md#november-18-local-verification)

### Export and build for Android

Install the official Swift 6.3.3 toolchain and its Android Swift SDK with
NDK r27d, Android platform 37.0, build-tools 37.0.0, JDK 25, and Python 3.
Set the following paths to your installations. Use Xcode 26.6 with its macOS
26.5 SDK for the Android cross-build. Keep the same tool selections during
creation, export, and build.

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

The default Android host is `legacy-v1`. Creation seeds
`Platforms/Android/Package.resolved` with the admitted SDK pins and export
preserves the lock. The build produces an unsigned arm64 APK at
`.mixer/android-build/LocalAndroid-unsigned.apk` in the export. Add
`--android-host public-v4` at creation to select the public V4 host.
[Default starter API 36 runtime](verification/receipts/l01-default-starter-pair24-runtime-41a05264.json)

Export to a new directory outside the source project. You can move the export
and build it after the original project and SDK checkout are out of reach.
The export includes app source, the locked SDK, and the Android adapter when
present. It excludes build caches, dotenv secrets, signing credentials, and
provisioning profiles. Keep a separate copy of data stored by an installed app.
[Independent host export receipt](verification/receipts/l01-public-cli-independent-export-41a05264.json)

### Inspect an existing Swift app

```sh
"$mixer_cli" import "$work/LocalIOS/Sources" --output "$work/import.json"
```

Replace the source path with your app's Swift directory. For FieldLog, use
`ios/FieldLog` in its separate checkout. The importer reads the source and
writes an advisory migration report. Apply adaptations manually in your own
project. The report leaves technical eligibility unverified.
[FieldLog advisory import receipt](verification/receipts/fieldlog-advisory-import-root-r5864.json)

### FieldLog Pair23 Android fixture

FieldLog lives in a separate repository. The Android export used FieldLog
revision `552559d2d3278abb9b1aa7dcf0288102c09a202b` with a local five-file
migration. The migration updates the downstream workflow, recipe, recipe
tests, README, and app-specific `Platforms/Android/Package.resolved`. The
base checkout needs that migration to use Pair23. From the Mixer checkout,
apply the verified patches to a fresh FieldLog checkout:

```sh
fieldlog_fixtures="$(pwd)/verification/fieldlog-pair23"
git clone https://github.com/snowdamiz/fieldlog.git "$work/FieldLog"
git -C "$work/FieldLog" checkout --detach 552559d2d3278abb9b1aa7dcf0288102c09a202b
git -C "$work/FieldLog" apply "$fieldlog_fixtures/public-build.patch"
git -C "$work/FieldLog" apply "$fieldlog_fixtures/draft-fields.patch"
```

The first patch reproduces the public export build. The second preserves
field identities within each draft and gives new drafts fresh fields.
Together they reproduce the app sources used for the Android photo
persistence test. [Build receipt](verification/receipts/fieldlog-public-pair23-export-41a05264.json) · [Runtime receipt](verification/receipts/fieldlog-android-photo-persistence-41a05264.json)

For the ordinary Android app that returns from the photo picker and report
share sheet, apply the two Activity lifecycle fixes to that same checkout:

```sh
git -C "$work/FieldLog" apply "$fieldlog_fixtures/photo-return.patch"
git -C "$work/FieldLog" apply "$fieldlog_fixtures/report-return.patch"
```

The Activity delivers each result after it resumes and its window regains
focus. On API 36, an independent app read the exported report offline. On
return, FieldLog displayed the share-sheet closure message and retained the
workspace and queued changes. [Report transfer and return](verification/receipts/fieldlog-android-offline-report-return-41a05264.json)

To exercise the saved entry and JPEG against a local backend, use the [FieldLog offline sync replay](tests/integration/fieldlog-entry-sync/README.md). On macOS, the first replay verifies the queue after a lost acknowledgement. The second cancels a partial photo upload, restarts the client, and verifies the resumed JPEG against the saved bytes.

To reproduce the Android **On device** queue, prepare FieldLog from the pinned
public sources and run the generated Android entry point against the local
backend. The same prepared sources build an unsigned arm64 APK.
[Android photo queue replay](tests/integration/fieldlog-android-queue/README.md)

With the migration applied, follow `Integrations/GeneratedReport/README.md`.
Use the CLI, SDK checkout, and adapter from Mixer revision
`735ecec14e10e2dfed1e58a122c3fab08e569bef` for that recipe. It uses
`public-v4` and preserves FieldLog's own dependency pins. Use
`--prepare-only` to create the project. Pass the prepared project to
`mixer export`, then pass the export to `mixer build --platform android`.
The receipt covers a relocated development APK build.
Signed update and rollback checks cover separate development fixtures.
The ordinary FieldLog mobile OTA workflow remains open.
[Current status](STATUS.md#november-18-local-verification)

### Upgrade a locked project

Export a recovery copy with the original CLI and host Swift toolchain before
you change the project's SDK. Close editors and builds first. Back up
installed app data, signing material, and any files excluded from export
separately.

For the FieldLog Android example, set the Android toolchain variables above
and use Xcode 26.6 throughout. Run these commands from the public Mixer
checkout with both Mixer revisions available locally.

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

The historical recipe leaves the Android package lock absent. To exercise
lock preservation, seed the prepared project with the FieldLog platform lock
from the Pair23 migration. This applies only the lock file from that patch.

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
copy. It preserves an existing `Platforms/Android/Package.resolved`. If
the Android dependency pins conflict, follow your app's dependency migration
for the target SDK. For an iOS-only project, omit `--android-adapter-path`
and select `--platform ios` for the build. Reopen your saved data in the
upgraded app before switching to it.

### Recover from an interrupted project edit

If upgrade reports `lock.sdk-drift` after an interrupted SDK edit, save the
damaged file separately and restore the original bytes from the recovery
copy. For damage limited to the bundled SDK manifest, run the following
commands before retrying the upgrade.

```sh
sdk_manifest=Generated/MixerSDK/Package.swift
cp "$source_project/$sdk_manifest" "$work/damaged-Package.swift"
cp "$recovery_copy/$sdk_manifest" "$source_project/$sdk_manifest"
```

If an upgrade destination already exists, keep it and choose a fresh
destination for the retry. For an interrupted FieldLog save that reports a
storage error, close and reopen the workspace. Check the saved entry, draft,
and outbox before trying the save again.

To test an installed FieldLog upgrade on iOS Simulator, build both app versions
from the pinned checkouts and import a photo through Files. The replay replaces
the app in place and checks that the same draft, JPEG, and pending changes
survive. [Installed upgrade replay](tests/integration/fieldlog-ios-installed-upgrade/README.md)

### Build an Android export without the Mixer CLI

Export a fresh copy to transfer to a build machine. Keep its bundled SDK,
Android adapter, and dependency lock together. Use the tool versions and
installation paths recorded in `mixer.lock`. Transfer installed app data
separately.

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

The FieldLog build writes
`.mixer/android-build/FieldLogGenerated-unsigned.apk` in the export. The
public replay built this APK with the original project, SDK checkouts, and
Mixer CLI builds unavailable. It also reopened a saved FieldLog workspace
through the app's storage code on the host. [Upgrade, recovery, and exit replay](verification/receipts/l08-public-upgrade-02002272.json)

## Local development

The repository root is a Swift package exporting `MixerCore`, `MixerUI`,
`MixerApple`, `MixerGuest` and `MixerCapabilities` from the same sources as `sdk/`.
An external project can use `https://github.com/snowdamiz/mixer.git` with a full
commit revision and product package identity `mixer`. Pin a reviewed revision;
these are development APIs, with no stable release tag or compatibility guarantee.
The root package does not distribute the VM, updater or activation binary.
Their immutable native packaging remains separate work.

Requirements: Xcode/Swift 6.2+, Rust, Go 1.26.4, Python 3.12+. Node is used only as a
development test oracle. See `release/toolchain-candidate.json` for cross-target
compiler candidates; the default Xcode compiler does not match Android/Wasm SDKs.

The CLI tests require the `mixer` executable built with the same Swift toolchain.

```sh
swift test
swift build --package-path cli --product mixer -j 2
MIXER_STORE_CLI_BIN_DIR="$(swift build --package-path cli --product mixer -j 2 --show-bin-path)"
test -x "$MIXER_STORE_CLI_BIN_DIR/mixer"
MIXER_STORE_CUSTODY_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mixer-cli-tests.XXXXXX")"
MIXER_STORE_TEST_CLI="$MIXER_STORE_CLI_BIN_DIR/mixer" \
	MIXER_STORE_CUSTODY_DIR="$MIXER_STORE_CUSTODY_DIR" \
	MIXER_SUITE_HOLD="$MIXER_STORE_CUSTODY_DIR/SUITE-HOLD.json" swift test --package-path cli
swift test --package-path updates
swift test --package-path capabilities
cargo test --manifest-path vm/Cargo.toml
cd services && go test -race ./...
```

Run the source CLI with `scripts/mixer`, or use
`"$MIXER_STORE_CLI_BIN_DIR/mixer"` after the build above:

```sh
scripts/mixer doctor
scripts/mixer create MyApp
scripts/mixer test --directory MyApp
scripts/mixer run ios --device YOUR_BOOTED_SIMULATOR_UUID --directory MyApp
scripts/mixer release inspect --directory MyApp
scripts/mixer submit status --provider app-store-connect --app-id ASC_APP_ID --build-id BUILD_ID --directory MyApp
```

Commands return JSON. `doctor` returns 2 when required inventory is incomplete.
The importer produces an advisory migration report.

To inspect a signed FieldLog development update, supply the project that produced
the candidate, its qualification bundle, and your independently obtained build
producer trust file. The bundle contains the build provenance, signed offers,
and observed guest behavior for each target.
[Produce both FieldLog variants locally](cli/release-tools/README.md).

```sh
scripts/mixer release inspect --directory "$FIELDLOG_PROJECT" \
  --qualification "$QUALIFICATION_DIR" --producer-trust "$PRODUCER_TRUST_FILE"
```

Read each entry in `targets`. In the verified confirmation-flow edit, both
iOS and Android reported `ota-compatible` and the command exited 0. Adding
the Android camera permission changed the Android result to
`store-build-required` and the command exited 2. Omitting both qualification
options also returns 2, with a blocked report. The operator still owns the
publication decision. [Verified cases](verification/receipts/l04-release-inspector-source150-41a05264.json)

`submit status` queries an existing App Store Connect build using a short-lived
`MIXER_ASC_BEARER_TOKEN` supplied through the launch environment. It checks the
provider app/build identity against the project's bundle ID and retains a local
observation under `.mixer/store`. Exit 0 means build processing succeeded; exit 2
means processing is pending. TestFlight readiness, review approval and availability
remain unverified. Live App Store Connect qualification is still pending.

Generated projects bundle an exact SDK source snapshot and compiler identity in
`mixer.lock`. They use JSON syntax in `mixer.yml` (a YAML 1.2 subset); general YAML
parsing remains unfinished. Generated Xcode projects refuse to overwrite modified
project bytes. App-owned native source remains editable. Export excludes build
caches, dotenv secrets, signing certificates/keys and provisioning profiles.

The public Android host batches native input against one installed snapshot and
publishes one model revision per batch. It preserves the original event bytes and
refuses stale owners or revisions.
API37 emulator tests cover native typing, Add with draft reset, and Toggle.
OS IME service behavior, keyboard/window parity, physical devices, and immutable
published-package qualification remain pending.

The build compiles the application's shared Swift feature and app-owned Android
entry into an unsigned arm64 APK. It preserves native edits and rejects unsupported
resources/capabilities. Release signing, distribution, broader lifecycle/device
coverage, and immutable published SDK consumption remain pending. See the generated Android README and
[`verification/android-generated-consumer/README.md`](verification/android-generated-consumer/README.md).

## Current components

| Component | Implemented scope | Remaining acceptance |
| --- | --- | --- |
| `sdk/` | Swift state/effects, bounded UI protocol, reconciliation, native Apple controls, guest codecs | Broad UI/navigation/plugins, physical behavior/accessibility, full guest parity |
| `cli/` | Creation, doctor, locked source snapshots, host tests, iOS Simulator build/run, unsigned Android APK generation/build, read-only inventory, export, existing App Store Connect build status | Full Android lifecycle/resources/plugins, compiler semantic inventory, signing/distribution/debug tooling |
| `vm/` | Owned bounded integer/numeric/table-memory profiles, validation, execution, persistent C sessions, inventory | Full emitted Swift profile/imports, aggregate memory design, fuzz campaigns, independent audit |
| `runtime/` | Typed native Swift sessions and complete validation without session allocation | Immutable published native artifacts and full runtime identity |
| `activation/` | Signed cold-start selection into owned VM, signed limits, retained state, health and fallback | Full Swift/UI/capability integration, physical lifecycle/recovery and FieldLog adoption |
| `capabilities/` | Generated Swift/Java codecs, bounded request ownership, typed HTTP hook, real app-private key-value storage | Guest/JNI transport, bundled networking, other native families and physical qualification |
| `native/android/` | Swift/JNI/native widgets with physical Pixel input and identity tests | FieldLog adoption, lifecycle/accessibility/performance/device matrix |
| `updates/` | Swift signed artifact/assignment verifier and durable recovery store with scoped physical receipts | Integrated physical activation, state migration and delegated key rotation |
| `services/` | Signed CBOR contracts, authenticated development release API, local PostgreSQL tenant transactions/audit/outbox | Hosted identity/durability, isolated workers/signers, stores/billing/SSO |
| `compiler/` | Full-SDK FieldLog model corpus and measured size/layout experiments | Full feature dependency graph, owned Swift execution and production budgets |

Each component documents its exact limitations. A local backend reference is not
a hosted product. A Wasm run in a development oracle is not a MixerVM pass. Host
unit tests and simulator builds are not physical-device qualification.

For store preparation, use the [reviewer information template](docs/store-reviewer-information-template.md)
to disclose the actual interpreter, update boundary, native fallback and review
steps for each submitted build. Store and FieldLog release qualification remain pending.

Native session/activation tests need the owned static VM archive. Follow
[`runtime/README.md`](runtime/README.md) and [`activation/README.md`](activation/README.md)
to build a frozen source revision and pass its isolated library directory to Swift.
Do not point the linker at a Cargo directory containing both static and dynamic
VM libraries. CI performs the static build and runs the corresponding host suites.

`tests/integration/release-workflow.py` exercises actual local HTTP delivery,
the Swift verifier and integer VM together. `mixer update verify` uses private
bounded snapshots of all input files; it does not publish or activate an update.
See the integration README for build prerequisites.

## Evidence and delivery

The implementation plan completes when the eight local end-to-end checks in
[`gates/local.json`](gates/local.json) pass. Testing and early launch are free.
Live deployment, stores, physical devices, registry publication, outside adoption,
and payment implementation or activation are separate follow-up work. See
[the complete gate mapping](mixer-product-plan.md#29-completion-gates-and-later-qualification).

`work-graph.json` preserves W01–W18; `gates/ga.json` preserves G01–G38;
`dogfood/receipts/milestones.json` preserves D0–D8. Current receipts are in
`verification/`; detailed transient build logs and generated apps stay in
`verification/local/`. Historical generated payloads are available on demand from
the [verification archive](verification/README.md); new checkouts retain the
current fixtures, reports and held evidence. See [STATUS.md](STATUS.md) for the
integrated state.

`python3 scripts/check-policy.py` checks dependency manifests and gate integrity.
It is a guardrail, not independent security, legal, or provenance certification.
The proposed open-engine license and commercial-service terms require release
review before public distribution; `THIRD_PARTY.yml` records current foundations.
