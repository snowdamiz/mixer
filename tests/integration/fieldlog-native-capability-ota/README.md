# Replay a FieldLog native capability OTA refusal

Run the macOS host replay from the Mixer checkout with a fresh run name.

```sh
python3 -B tests/integration/fieldlog-native-capability-ota/replay.py my-replay
```

Use the toolchains and public dependency access listed in the [FieldLog
calculation replay](../fieldlog-task-calculation/README.md). The runner archives
Mixer `71e6ffa51e857d5a1eda3f74c26941996ed275de` and checks its tree and source
archive. It builds the developer release service, the owned VM, and the
FieldLog calculation host with the pinned public FieldLog storage and models.
It stages the test changes in the disposable build. Find the command logs
and full receipt in `verification/local/fieldlog-task-calculation-my-replay/`.

The storage-only host activates the corrected calculation at sequence 2.
An offer at sequence 3 adds the native `network.http.v1` capability and its
installed configuration and grant. The old and new offers carry the same
corrected Wasm.

- The developer service returns HTTP 422 with `artifact_invalid` and
  `v3 host contract mismatch` for the candidate signed for the old fingerprint.
- The old runtime's update route still returns the original signed offer.
  The new runtime's route goes from HTTP 204 to the signed sequence-3 offer
  after the candidate publishes under its matching fingerprint. The new
  host verifies that offer and admits the native HTTPS adapter in its
  execution policy. The calculation guest issues no HTTPS request.
- The old host refuses both sequence-3 forms before staging. The recovery
  file stays byte-identical across the refusals. The host renders the same
  healthy candidate and shows 33%, 100%, and 0% from saved tasks. A fresh
  process repeats the readback offline. The binary and workspace bytes match
  across both processes.

The replay covers developer release admission, runtime-scoped delivery, and
host recovery for §22.2.12. It uses an Apple-host presentation witness and
runtime-specific queries to the developer service. Mobile installation,
native display, and enrollment enforcement in the hosted service need their
own evidence. [Host receipt](../../../verification/receipts/fieldlog-native-capability-ota-71e6ffa.json)

## Reproduce the CLI store-build result

Use the [FieldLog release-inspection recipe](../../../cli/release-tools/README.md)
with its source-bound, signed qualification packet. The earlier run exercised
a real Android camera-permission change, reported Android
`store-build-required`, and preserved the prior signed FieldLog offer.
The CLI requires the packaged native inputs, the macOS host probes, and the
independently pinned producer trust. The HTTPS host replay provides the OTA
refusal and does not produce that qualification packet.
[Earlier CLI receipt](../../../verification/receipts/fieldlog-release-inspection-clean-pin-41a05264.json)

## Build the Android native handoff

Use the toolchains and SDK paths from the [Android calculation source
rebuild](../fieldlog-task-calculation/README.md#rebuild-the-android-apk-and-replay-it-on-the-host).
Use a new directory under ignored `verification/local/` and keep loopback
port 41897 free.

```sh
mkdir -p verification/local
tests/integration/fieldlog-native-capability-ota/build-android-pair.sh \
  "$PWD/verification/local/fieldlog-android-https-my-run"
```

The launcher first checks the storage-only calculation rebuild. It then applies
the successor overlay to the traced FieldLog source and rebuilds Java and JNI
against the same VM archive. Both APKs use one disposable development signer
and one OTA root. The installed HTTPS assets come from the SDK revision linked
by the calculation recipe, with the same bytes as the reviewed host replay.
Only the successor material loader accepts the two-capability identity.

The Android loopback relay serves the exact signed APK-scoped offers. The pair
replay checks that enabling the successor leaves the old offer byte-identical
and that each offer verifies only against its own runtime. The macOS probes
execute the same corrected guest against both packaged material sets. They
check the old host's refusal and cold offline fallback, then open the
successor against the same workspace and installation ID.

Use the sealed `handoff/` directory for the [root-owned Android
replay](ANDROID-HANDOFF.md). After the launcher verifies the seal and all
commands close, remove the owned `work/` and `calculation/` directories.
On failure, inspect the current campaign's stage receipts. Preserve the
campaign if custody remains unknown.

The stock inspector requires distinct compiled payload hashes and signed
qualification from a trusted producer. This pair keeps the payload identical
and supplies development APK and OTA signatures. The stock inspector's
classification for this HTTPS delta remains pending.

## Build the current-ABI Android pair

Use the Android calculation toolchains and install Homebrew OpenSSL 3 for the
diagnostic signature. Run from a Mixer checkout that contains
`b144c2c2042a4499365d1186f46d43fba1832143` and its source objects.
Commit the recipe inputs before launch and use a new campaign directory. The
launcher pins the recipe to the checkout commit before running the build and
checks that same commit again before publishing the complete handoff checksums.

```sh
mkdir -p verification/local
campaign="$PWD/verification/local/fieldlog-android-current-abi-my-run"
tests/integration/fieldlog-native-capability-ota/build-current-abi-android-pair.sh "$campaign"
(cd "$campaign/handoff" && shasum -a 256 -c SHA256SUMS)
```

The launcher builds both arm64 JNI libraries against one fresh VM archive.
It verifies the linker maps, APK signatures, and identical compiled
`AndroidManifest.xml` bytes, including version code 1 in both APKs. The
storage-only APK receives the baseline calculation guest. The HTTPS APK
receives the corrected guest. The two APKs share an APK signer and an OTA
trust root.

Check `handoff/host-replay.json` for the calculation and recovery observations.
The refusal observation binds the host probe's loopback update and artifact
requests to the signed incompatible offer and records the saved-candidate
fallback. The compatibility error comes from a separate verification of that
offer.
Check `handoff/stock-inspection.json` for the stock verifier results and the
inspector outcome. The inspector admits both native identities and checks
the exact packages and signed offers. It stops at `release.invalid-evidence`
because its confirmation-flow schema cannot decode the calculation
observations. The current host replay leaves Android installation and
store-build classification pending.

After the checksum check succeeds, keep `handoff/` and remove the campaign's
`work/` directory. If the launcher fails, check the stage receipts in
`work/logs/` before removing the campaign. Preserve any stage whose custody
is `UNKNOWN`.
