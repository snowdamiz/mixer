# Actual private typed-result codec implementation

Status: isolated source implementation with bounded host validation; frozen for
independent review. The selected contract is retained in `selection.json`.
`mixer-product-plan.md` remains the product completion scope.

The candidate copies the exact sealed 140-file accepted VM distribution and all
11 unchanged host-support files. Only the private module declaration in
`experimental_swift_reactor/mod.rs` changes. The two new distribution sources are
`diagnostic_result_v1.rs` and `diagnostic_result_v1_tests.rs`, making 142
candidate distribution members. No dependency or public API was added. The
codec imports the actual existing control, validation-usage and WASI types;
there are no extracted type mirrors. Every original source/support identity was
checked against the accepted baseline seal before copying and after validation.
`source-manifest.json` closes all candidate distribution bytes; orchestration,
compile fixtures and evidence are separate packet members.

## Implemented behavior

The module serializes the selected logical little-endian usage512, scalar256 and
result2048 records. It checks source usize conversions, u32 function/guest-exit
widths, every actual enum, exact extents, presence and optional payloads, code
length/ASCII/padding and all reserved bytes. It decodes every present full-result
partition before returning. Result masks are exactly 0,1,3,4,5,7. Each usage field,
including all 13 WASI words, is preserved without normalization. WASI=None and
Some(all-zero) remain distinct.

Encoders borrow their source objects and preflight all fallible operations before
the first caller-buffer write. Refusal leaves the entire supplied output unchanged.
The original failure supplies its own after_cleanup observation; final_consuming
is independently borrowed. The decoder returns a private-fields explicitly
unverified view tied to its complete immutable input. Code text and reference
digests borrow that input. No static code is fabricated and no SwiftRunFailure is
constructed from decoded bytes.

The required raw reference length can be 0..u64::MAX; zero describes an empty
referenced artifact. Constructor tag0 requires length0 and zero32 digest; tags1..8
require length1..65536. All required digest patterns, including zeros, are opaque
unverified data. Unknown printable code text and anomalous observations remain
data, without stage/kind/code or constructor semantic admission. This module
performs no allocation, I/O, hashing, environment observation, callback, owner
admission, runtime invocation or reservation mutation.

## Validation and limits

Rust 1.99.0 on aarch64-apple-darwin, Debug and optimized with overflow checking:

- 27 actual-module methods per mode: 14 ported proposal controls, 7 ported
  independent envelope controls, and 6 fresh controls. Positive complete result
  round trips cover all 54 mask/constructor combinations and exact decoded
  scalars, references and snapshots. Malformed-present and hidden payloads,
  every wrong extent through 2049, refusal preservation, every actual enum,
  width/None-vs-zero/WASI cases, all 15 ledger positions and three distinct
  snapshots are tested.
- One positive and six negative lifetime/privacy compiler fixtures per mode.
  Borrowed view/code lifetime use compiles; static escape, live-input mutation,
  private-field access and assigning decoded code to an authoritative source
  failure fail with the selected Rust diagnostics.
- One existing host-only original-owner layout method per mode: all 165 unit
  layouts match the frozen sealed expected result. This is the unchanged owner
  inventory and does not cover codec storage.
- Ordinary production rlib compilation passes in both modes. Only two inherited
  unit-test dropping_copy_types warnings occur in unchanged
  control_operations_tests.rs; ordinary production compilation emits no warnings.

`data-layouts.json` reports codec data sizes separately, including these new
host type measurements (bytes/alignment): CodecRefusalV1 24/8;
UnverifiedFailureScalarsV1 88/8; UnverifiedResultReferencesV1 64/8;
ResultObservationV1 80/8; UnverifiedResultViewV1 1680/8. Usage/scalar/result
buffers are 512/256/2048 bytes with alignment1; fixed local word arrays and their
Option wrappers are also reported. These are Rust type sizes, not compiler-stack
measurements, complete simultaneous-lifetime accounting or an operational
reservation acceptance. No runtime path invokes the codec.

`receipt.json`, `command-receipts.json`, `logs/`, `compile-variants.json`,
`custody.json`, `input-custody-after.json` and `cleanup.json` retain the exact
commands, executable/tool identities and versions, flags, source digest, outputs,
variant append/fixture identities and terminal cleanup. Git revision is context;
the complete source-manifest digest identifies the compiled source. Owned scratch
and compiler products were removed and every child terminally waited.

Canonical promotion, real producer provenance/loader/exporter/carriers,
cryptographic source/preimage/session joins, code applicability, complete
constructor/cleanup semantics, operational storage admission, full context/FSM
replay, native simulator/emulator/device validation, separate-repo FieldLog with
published packages, OTA/store/customer/operational and GA acceptance remain
pending. No native/UI/capture runtime, process inventory, predecessor one-shot
runner, forbidden hosted harness or Android startup experiment was invoked.
No canonical/index/commit/push, publication or customer message occurred.

Read-only verification of the frozen exact path set:

```sh
python3 -B verification/swift-typed-result-codec-implementation/seal_packet.py
python3 -B verification/swift-typed-result-codec-implementation/verify_inputs.py
```

To reproduce controls, first make a working copy and run its `run_checks.py` with
paths adjusted for the repository location. It writes only its owned directory.
It does not invoke the retained predecessor host runner. Do not rerun preparation
or validation in the frozen original: that would deliberately change sealed
members. `prepare.py`, `build_codec.py` and `build_tests.py` retain the authored
assembly procedure; their output is already present as the exact source bytes.
