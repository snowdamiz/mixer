# CLI reference

Run the source CLI with `scripts/mixer`, or build it as shown in
[Getting started](getting-started.md#build-the-cli). Commands return JSON.

```sh
scripts/mixer doctor
scripts/mixer create MyApp
scripts/mixer test --directory MyApp
scripts/mixer run ios --device YOUR_BOOTED_SIMULATOR_UUID --directory MyApp
scripts/mixer release inspect --directory MyApp
scripts/mixer submit status --provider app-store-connect --app-id ASC_APP_ID --build-id BUILD_ID --directory MyApp
```

`doctor` returns 2 when required inventory is incomplete.

## Check whether an update can ship over the air

`mixer release inspect` reports whether a change can ship as a signed
over-the-air update or needs a new store build. To inspect a signed development
update, pass the project that produced it, its qualification bundle, and a
build producer trust file that you obtained independently. The bundle contains
the build provenance, signed offers, and observed guest behavior for each
target.

```sh
scripts/mixer release inspect --directory "$PROJECT" \
  --qualification "$QUALIFICATION_DIR" --producer-trust "$PRODUCER_TRUST_FILE"
```

Read each entry in `targets`. `ota-compatible` with exit 0 means the change can
ship over the air. `store-build-required` with exit 2 means it needs a new store
build, such as when a change adds an Android permission. Without both
qualification options, the command returns 2 with a blocked report. You still
decide whether to publish. See the
[verified cases](../../verification/receipts/l04-release-inspector-source150-41a05264.json).

[Produce and inspect a local FieldLog update](../../cli/release-tools/README.md)
builds both update variants and inspects them.

## Check App Store Connect build status

`submit status` queries an existing App Store Connect build. It reads a
short-lived `MIXER_ASC_BEARER_TOKEN` from the environment and checks the
provider's app and build identity against the project's bundle ID. It writes a
local observation under `.mixer/store`. Exit 0 means build processing
succeeded, and exit 2 means processing is pending.

## Generated projects

- `mixer.lock` pins an exact SDK source snapshot and compiler identity.
- `mixer.yml` uses JSON syntax, which is a subset of YAML 1.2. General YAML
  parsing is not supported yet.
- Generated Xcode projects refuse to overwrite modified project files.
  App-owned native source stays editable.
- The Android build compiles the shared Swift feature and app-owned Android
  entry into an unsigned arm64 APK. It keeps native edits and rejects
  unsupported resources and capabilities. See the generated Android README and
  [the generated consumer notes](../../verification/android-generated-consumer/README.md).
