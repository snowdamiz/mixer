# mixer

An independently implemented Swift mobile platform in active development. The
complete scope is [mixer-product-plan.md](mixer-product-plan.md); this repository
does **not** yet satisfy its general-availability or FieldLog gates.

The engine uses official Swift compilers, an owned Swift UI/state contract, native
platform adapters, an owned Rust Wasm interpreter, and separately authorized signed
artifacts and rollout assignments. No Patch/Skip implementation is used.

## Local development

Requirements: Xcode/Swift 6.2+, Rust, Go 1.26, Python 3. Node is used only as a
development test oracle. See `release/toolchain-candidate.json` for cross-target
compiler candidates; the default Xcode compiler does not match Android/Wasm SDKs.

```sh
swift test --package-path sdk
swift test --package-path cli
swift test --package-path updates
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

## Current components

| Component | Implemented scope | Remaining acceptance |
| --- | --- | --- |
| `sdk/` | Swift state/effects, bounded UI protocol, reconciliation, native Apple controls, guest codecs | Broad UI/navigation/plugins, physical behavior/accessibility, full guest parity |
| `cli/` | Creation, doctor, locked source snapshots, host tests, iOS Simulator build/run, read-only inventory, export | Android workflow, compiler semantic inventory, signing/distribution/debug tooling |
| `vm/` | Owned bounded integer Wasm profile, validation, execution, traps, C ABI, inventory | Full emitted Swift profile/imports/concurrency, fuzz campaigns, independent audit |
| `native/android/` | Swift/JNI/native widgets with physical Pixel input and identity tests | FieldLog adoption, lifecycle/accessibility/performance/device matrix |
| `updates/` | Swift Ed25519/canonical CBOR artifact and assignment verifier; Go interoperability | Durable Swift mobile activation, recovery, delegated key rotation |
| `services/` | Signed CBOR contracts, local durable updater reference, authenticated development release API | Mobile updater, PostgreSQL hosted durability, isolated workers/signers, stores/billing/SSO |
| `compiler/Fixtures/FeatureProbe/` | Real Swift model probe built for host/Android/Wasm | Actual FieldLog dependency graph and production package budgets |

Each component documents its exact limitations. A local backend reference is not
a hosted product. A Wasm run in a development oracle is not a MixerVM pass. Host
unit tests and simulator builds are not physical-device qualification.

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
