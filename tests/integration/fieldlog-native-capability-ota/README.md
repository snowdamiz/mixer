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

## Qualify the installed Android path

Use the [Android calculation source rebuild](../fieldlog-task-calculation/README.md#rebuild-the-android-apk-and-replay-it-on-the-host)
for the storage-only app and the [Android engine-pair recipe](https://github.com/snowdamiz/mixer/blob/71e6ffa51e857d5a1eda3f74c26941996ed275de/tests/integration/fieldlog-android-engine-pair/README.md)
for same-signer APKs, distinct fingerprints, and runtime-specific delivery.

The existing Android FieldLog source guard accepts a storage-only checklist
identity. The Java asset copier, Swift installed-material loader, and asset
packager also list only the storage materials. For an HTTPS successor,
update those three points in the new native build to carry the independently
pinned HTTP configuration and installed grant alongside storage. Seal and
sign the new runtime identity from that build. The current replay supplies
no successor APK. [FieldLog app and loader overlay](https://github.com/snowdamiz/mixer/blob/71e6ffa51e857d5a1eda3f74c26941996ed275de/tests/integration/fieldlog-android-engine-pair/overlays/fieldlog-l04.patch)

1. On the root-owned emulator, install the storage-only APK. Open the
   corrected signed calculation and capture the APK hash, selected task,
   workspace bytes, installation ID, and healthy recovery state.
2. Try the higher-sequence HTTPS offer for the old fingerprint. Capture its
   release refusal and recheck the old runtime's offer. To exercise client
   refusal, use an owned test origin that presents the incompatible signed
   offer to the installed client.
3. Reopen the old APK online and offline. Check that the signed candidate,
   sequence, workspace, and installation ID match the initial readbacks.
   Reuse the calculation recipe's `android-readback.py` for recovery and
   owner retirement.
4. Publish the valid candidate for the new fingerprint and repeat the cohort
   readbacks using the new APK. Close the origin, remove the exact ADB reverse,
   and record cleanup of the owned emulator.
