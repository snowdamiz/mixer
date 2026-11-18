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

## Create, export, and build a local app

Run these commands on an Apple silicon Mac from a checkout of the public
`snowdamiz/mixer` repository. This Pair23 pin supplies the matching CLI, SDK,
and Android adapter and includes the default starter's Android lock fix.
Set `DEVELOPER_DIR` to your Xcode installation with the iOS Simulator SDK
and Swift 6.2 or later.

```sh
mixer_rev=f048e40c529aa715ec32edc6f1f13476ed67b2a2
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
"$mixer_cli" build --platform ios --directory "$work/exports/LocalIOS"
```

The build creates an unsigned `LocalIOS.app` under
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
[Default starter build receipt](verification/receipts/android-starter-lock-pair23-735ecec.json)

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

Commands return JSON and nonzero status for failed operations. `doctor` returns 2
when required inventory is incomplete. `release inspect` returns a blocked report
until native/guest compiler closure, signed artifacts, and recovery evidence exist.
The importer is advisory and read-only; lexical findings never authorize OTA.

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
