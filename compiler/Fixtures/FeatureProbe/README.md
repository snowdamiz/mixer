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

## Swift floating-point replay

Run the compact owned-VM replay above to compare the task measurement preview
in native Swift and the installed Guest UI v1 ABI. The ABI selects
`table-memory-v3`. The host reads seven inputs from a file and sends the
operand bytes through the guest event buffer.

The replay checks exact result bits for Float and Double addition, subtraction,
multiplication, and division. It checks less-than and equality to zero.
The cases cover fractional values, rounding at 2^24 and 2^53, the smallest
normal values with subnormal products, and both signs of zero. Both paths
refuse a 23-byte input without publishing a new result. The guest closes and
rejects its stale session handle.

The fixture exchanges binary data through the compact ABI. Coverage is limited
to the seven finite inputs on arm64 macOS. The receipt records the input bytes,
both outputs, and the instructions in the Swift-emitted guest.
[Floating-point replay receipt](../../../verification/receipts/swift-floating-point-preview-6f4fdee12e.json)

## Swift associated-type replay

Run the compact owned-VM replay above. The input file selects signed readings
or a wrapping counter for each pair of 16-bit values. The generic
`readingChange` function extracts two values of `Format.Reading` and passes
them to the same format's change operation. The two concrete formats use
`Int16` and `UInt16`.

Native Swift and installed Guest UI v1 must return the same exact
little-endian `Int32` bytes for all four events. Both paths refuse a
four-byte truncation of the five-byte event and preserve the last result.
Closing the guest session makes the old handle invalid. This covers
statically specialized generic calls on arm64 macOS.
[Associated-type replay receipt](../../../verification/receipts/l03-swift-associated-types-v73.json)

## Swift property-wrapper replay

Run the compact owned-VM replay above. Native Swift and Embedded Swift
compile the same `PropertyWrapper.swift`. The host sends little-endian
`UInt16` readings from a file as successive preview events. The value-type
wrapper caps the stored reading at 1,000. Its `$measurement` projection
counts changes to that bounded value.

Both paths must emit the same eight-byte frames. Readings 240, 1,250 and
1,200 produce reading/count pairs (240, 1), (1,000, 2) and (1,000, 2).
The full-width reserved reading 65,535 is refused and leaves the previous
frame byte-identical. The next reading, 480, must produce (480, 3).
The Guest UI V1 session closes and its stale handle is refused. This covers
one concrete wrapper and projection on arm64 macOS.
[Property-wrapper replay receipt](../../../verification/receipts/l03-swift-property-wrapper-v77.json)

## Swift result-builder replay

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --result-builder
```

This focused replay uses one Foundation-free menu builder with `if/else` and
`for` child expressions. A three-byte event selects a priority marker, a
starting digit, and zero to three children. Native Swift emits the exact
four-byte frames for `.12`, `!456`, and `.` with zero padding. A four-child
event is refused before rendering and preserves the `!456` frame.

Embedded Swift 6.3.3 emits an object from the same builder source. The
default one-page Guest UI V1 link reports undefined `posix_memalign` and
`free`. The focused command prints the native observations and linker
diagnostic before exiting 1.
[Result-builder replay receipt](../../../verification/receipts/l03-swift-result-builder-v78.json)

## Swift result builder with the stock WASI allocator

With the Swift 6.3.3 WASI SDK installed, opt into the pinned allocator archive.

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --result-builder --stock-wasi-allocator
```

The replay reproduces the no-archive link failure, then links the same object
with the verified `libc.a`. The unsigned guest runs through the Guest UI V1
C ABI on arm64 macOS with zero imports, zero host calls, and one fixed 64 KiB
page. Native and guest frames match for conditional and iterated children.
The four-child refusal preserves the prior frame. The next valid event
renders, and the guest reclaims its slot and rejects the retired handle.
[Reviewed replay](../../../verification/receipts/l03-swift-result-builder-stock-wasi-allocator.json) ·
[Repeat and existing modes](../../../verification/receipts/l03-swift-result-builder-stock-wasi-allocator-regressions.json)

## Swift fixed-slot result-builder replay

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --fixed-slot-result-builder
```

Native Swift and Embedded Swift compile the same `FixedSlotResultBuilder.swift`.
The builder uses `buildEither` for the priority marker and `buildOptional`
for each of three child slots. The three-byte event supplies the marker,
starting digit, and child count. A fixed-arity `buildBlock` packs the four
bytes into a `UInt32`.

The replay compares all four child counts in native Swift and through the
installed Guest UI V1 C ABI. Both paths preserve the `!456` frame when the
event requests four children, then render the next valid event. The replay
closes the guest session, reopens the same registry slot with a new generation
and a zeroed frame, and checks that the old handle is still rejected.
[Fixed-slot replay receipt](../../../verification/receipts/l03-swift-fixed-slot-result-builder.json)

## Swift enum payload and typed throws replay

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --enum-typed-throws
```

Native Swift and Embedded Swift compile the same Foundation-free
`EnumTypedThrows.swift`. Each three-byte runtime event selects either an item
with quantity and unit price or a flat fee. The quote function uses
`throws(QuoteRefusal)` and throws the calculated total when it exceeds 1,000.

The replay compares eight-byte frames from native Swift and the installed
Guest UI V1 C ABI. A flat fee of 12 and an item total of 1,000 succeed.
The 1,100 refusal preserves the 1,000 frame byte-for-byte. The next valid
event publishes 57 and the caught payload of 1,100 as two little-endian
`UInt32` values. The guest closes, rejects its stale handle, and reopens the
registry slot with a zeroed frame.

Coverage is limited to this value-type action and concrete typed throw/catch
on arm64 macOS. Untyped throwing, Foundation and signed or device execution
remain unqualified by this replay.
[Enum and typed throws replay receipt](../../../verification/receipts/l03-swift-enum-typed-throws.json)

This mode emits the object to stdout before linking it. A fixed object output
argument keeps Swift's module hash stable across scratch directories with the
same compiler and inputs.
[Reproducibility receipt](../../../verification/receipts/l03-swift-enum-typed-throws-reproducibility-160fb742.json)

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

## Swift escaping closure replay

On arm64 macOS, run the compact probe with the same Swift and WASI tools as
the enum replay. The first command captures a reference object. The
second captures the value directly.

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --escaping-closure
python3 -B compiler/Fixtures/FeatureProbe/replay.py --escaping-closure-value-only
```

Native Swift reads the stored capture across turns, replaces it, and
releases it. Exact frames record title deinitialization on replacement
and inspection deinitialization on release in the object case. A later
invocation leaves the release frame unchanged. Embedded Swift emits
objects for both variants. The default import-free Wasm link fails with
undefined `posix_memalign` and `free`.
[Initial replay](../../../verification/receipts/l03-swift-escaping-closure-1ef43cbb.json) ·
[Exact object-capture replay](../../../verification/receipts/l03-swift-escaping-closure-final-object-0ed34547.json)

With the Swift 6.3.3 WASM SDK installed under `~/.swiftpm/swift-sdks`, add
`--stock-wasi-allocator` to replay either closure with the SDK's pinned `libc.a`.

```sh
python3 -B compiler/Fixtures/FeatureProbe/replay.py --escaping-closure --stock-wasi-allocator
python3 -B compiler/Fixtures/FeatureProbe/replay.py --escaping-closure-value-only --stock-wasi-allocator
```

Each run checks the archive digest and reproduces the link refusal before
linking the same object with `libc.a`. The replay requires zero imports, one
64 KiB page, and the existing Guest UI V1 exports. The owned VM validates and
runs the guest under the 1,000,000-fuel per-turn ceiling. The replay checks
exact native and guest frames, refusal, and session retirement. This unsigned
replay covers the two closure fixtures on arm64 macOS.
[Stock WASI allocator replay receipt](../../../verification/receipts/l03-swift-stock-wasi-allocator-replay.json)

## Fixed-page guest allocation recovery

Run the [maintained allocation replay](../../experiments/guest-local-allocation-control/README.md)
with the pinned Swift 6.3.3 WASI archive and VM build on arm64 macOS.
The unsigned Guest UI V1 fixture uses one 64 KiB page and makes zero host calls.

The tenth aligned 4,096-byte allocation returns WASI `ENOMEM`. Freeing a
middle block lets the allocator return the same address on retry. The guest
checks the survivor and replacement canaries and then frees every block.
A fresh generation starts clean and repeats the result. Both retired handles
are refused.
[Independent replay receipt](../../../verification/receipts/l03-guest-allocator-release-maintained-root-abadfffa10.json)

## Configured guest memory growth

Run the [paired allocation replay](../../experiments/guest-allocator-growth-control/README.md)
to compare the reviewed fixed-page fixture and a one-to-two-page guest.
The growth fixture checks the exact allocation that grows memory,
pre-growth canaries, `ENOMEM` at its ceiling, reuse, and retirement.
[Reviewed growth receipt](../../../verification/receipts/l03-guest-allocator-growth-strict-41a05264.json)

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
