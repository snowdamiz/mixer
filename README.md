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

```sh
swift test
swift test --package-path cli
swift test --package-path updates
swift test --package-path capabilities
cargo test --manifest-path vm/Cargo.toml
cd services && go test -race ./...
```

Run the source CLI with `scripts/mixer`, or build `cli/` and use
`cli/.build/debug/mixer` directly:

```sh
scripts/mixer doctor
scripts/mixer create MyApp
scripts/mixer test --directory MyApp
scripts/mixer build --platform ios --directory MyApp
scripts/mixer run ios --device YOUR_BOOTED_SIMULATOR_UUID --directory MyApp
scripts/mixer import /path/to/existing/swift/project
scripts/mixer release inspect --directory MyApp
scripts/mixer export /path/to/export --directory MyApp
```

Commands return JSON and nonzero status for failed operations. `doctor` returns 2
when required inventory is incomplete. `release inspect` returns a blocked report
until native/guest compiler closure, signed artifacts, and recovery evidence exist.
The importer is advisory and read-only; lexical findings never authorize OTA.

Generated projects bundle an exact SDK source snapshot and compiler identity in
`mixer.lock`. They use JSON syntax in `mixer.yml` (a YAML 1.2 subset); general YAML
parsing remains unfinished. Generated Xcode projects refuse to overwrite modified
project bytes. App-owned native source remains editable. Export excludes build
caches, dotenv secrets, signing certificates/keys and provisioning profiles.

Android consumer generation uses the installed official Swift6.3.3 Android SDK,
NDKr27d, Android37.0/build-tools37.0.0 and JDK25. Their distributions and the copied
owned Java/JNI/runtime sources are locked at creation:

```sh
scripts/mixer create MyAndroidApp --platform android
scripts/mixer build --platform android --directory MyAndroidApp
```

The build compiles the application's shared Swift feature and app-owned Android
entry into an unsigned arm64 APK. It preserves native edits and rejects unsupported
resources/capabilities. Signing, installation, lifecycle and published native SDK
consumption remain pending. See the generated Android README and
[`verification/android-generated-consumer/README.md`](verification/android-generated-consumer/README.md).

## Current components

| Component | Implemented scope | Remaining acceptance |
| --- | --- | --- |
| `sdk/` | Swift state/effects, bounded UI protocol, reconciliation, native Apple controls, guest codecs | Broad UI/navigation/plugins, physical behavior/accessibility, full guest parity |
| `cli/` | Creation, doctor, locked source snapshots, host tests, iOS Simulator build/run, unsigned Android APK generation/build, read-only inventory, export | Full Android lifecycle/resources/plugins, compiler semantic inventory, signing/distribution/debug tooling |
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

Native session/activation tests need the owned static VM archive. Follow
[`runtime/README.md`](runtime/README.md) and [`activation/README.md`](activation/README.md)
to build a frozen source revision and pass its isolated library directory to Swift.
Do not point the linker at a Cargo directory containing both static and dynamic
VM libraries. CI performs the static build and runs the corresponding host suites.

`tests/integration/release-workflow.py` exercises actual local HTTP delivery,
the Swift verifier and integer VM together. `mixer update verify` uses private
bounded snapshots of all input files; it does not publish or activate an update.
See the integration README for build prerequisites. FieldLog lives separately at
`../fieldlog`; its native offline baseline is not a completed dogfood milestone.

## Evidence and delivery

`work-graph.json` preserves W01–W18; `gates/ga.json` preserves G01–G38;
`dogfood/receipts/milestones.json` preserves D0–D8. Current receipts are in
`verification/`; detailed transient build logs and generated apps stay in
`verification/local/`. See [STATUS.md](STATUS.md) for the integrated state.

`python3 scripts/check-policy.py` checks dependency manifests and gate integrity.
It is a guardrail, not independent security, legal, or provenance certification.
The proposed open-engine license and commercial-service terms require release
review before public distribution; `THIRD_PARTY.yml` records current foundations.
