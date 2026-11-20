# Swift language replay commands

Run these commands from the repository root. The
[support matrix](../../swift-language-support.md) describes the scope of each check.

## Native FeatureProbe

Run the [native replay](#native-sdk-controls) to execute the SwiftPM entry.
The macOS executable checks the completion calculation, a record-array JSON
round trip, exact UTF-8 bytes, and blanks rejected by the validator. The JSON
negative case requires a type mismatch on the `completed` field. The default
encoder accepts a finite Double and refuses infinity as an invalid value.

## Compact owned-VM replay

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py
```

Use arm64 macOS with the selected Xcode Swift toolchain, the Swift 6.3.3
release toolchain under `~/Library/Developer/Toolchains`, and arm64 Rust
1.99.0 under `~/.rustup/toolchains`. Cargo builds offline from the VM lockfile.
The command runs FeatureProbe and the two maintained owned VM test suites
listed below. It prints a receipt and uses a fresh directory in
`verification/local/`. Retain the reported directory if custody is UNKNOWN.
See the [recorded host replay](../../../verification/receipts/l03-swift-language-support-b963585e.json)
for the observed outputs.

The replay compiles the unchanged FieldLog review-mode task and compact
adapter. It exercises all three activations in native Swift and through the
installed Guest UI v1 VM C ABI. Each path refuses a truncated and a mismatched
final byte at every turn, leaves the current frame byte-identical, and then
accepts the valid event. The four frames must match each other and the D3
digests. The owned session must close and refuse its stale handle.
The [D3 receipt](../../../verification/receipts/l03-d3-task-review-event-trap-7b61fe1c.json)
records the expected frame digests.

The shared-memory control changes one flag byte in the successful guest.
It requires the same `unsupported` decoder report from the owned validator
and session constructor, with no fuel, host calls, or handle published.
Descriptor-only controls run separately. The compact profile uses one 64 KiB
page, 1,000,000 fuel per turn, and zero host calls for FieldLog. This replay
uses unsigned host fixtures.

## Owned VM capability and validation controls

The compact replay executes the suites below using Rust 1.99.0. To run them
separately, select that toolchain and use a fresh target path.

```sh
cargo test --offline --locked --release --manifest-path vm/Cargo.toml \
  --target-dir verification/local/swift-support-vm \
  --features experimental-capability-native \
  --test experimental_guest_ui_validation --test experimental_capability_guest
```

The VM fixtures cover defined exports and complete validation, approved typed
imports, and refusal of unknown imports or a generic dispatcher. These test
the VM capability contract. A feature that needs a particular platform
service still needs a typed adapter and evidence for that service.

## Native SDK controls

Run on arm64 macOS 26 or later with Swift 6.2 or later and a local
SwiftPM repository cache for the two revisions in
[sdk/Package.resolved](../../../sdk/Package.resolved).

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay_native.py
```

The replay runs the SwiftPM FeatureProbe entry and five native SDK tests.
The tests exercise MixerUI builder output, the document validator, the current
FeatureStore replacement, logical effect removal, and both JSON and guest event
codecs. The replay copies the two dependency repositories into fresh scratch
and checks their checked-out revisions. It prints the command results and
confirms scratch removal after observing process-group closure.

The separate FeatureStore executable compiles the unchanged SDK sources. Its
MainActor waiter starts with [`Task.immediate`](https://github.com/swiftlang/swift-evolution/blob/main/proposals/0472-task-start-synchronously-on-caller-context.md)
and calls `awaitCurrentEffects()` while the gate still holds the effect. The
waiter captures the task before the store removes it. The gate releases each
operation after replacement, cancellation, or stop. The executable joins that
task before checking reducer delivery. The replacement result reaches the
reducer. The three cancelled operations each return a result and deliver none.
See the [native replay receipt](../../../verification/receipts/l03-swift-language-support-w07-correction.json)
for the observations and the original run's unverified cleanup status.

## Owned VM cancellation and retirement

The earlier macOS FieldLog benchmark stopped an accepted button event before
its guest turn began. The exchange delivered one terminal result, published no
frame after stop, and refused later input. The bridge drained and retired the
session. Both compact variants recorded the same behavior. This covers the
owned Guest UI exchange for that timing. See the
[benchmark guard results](../../../verification/receipts/fieldlog-guest-benchmark-41a05264.json).

## Development-only FieldLog model oracle

Use the command and pinned inputs in the
[FieldLog reactor reproduction](../../experiments/fieldlog-reactor/README.md).
Its full Swift/WASI and native model observations cover that corpus. The
Node execution, the owned inventory, and the owned artifact rejection each
have their own scope.
