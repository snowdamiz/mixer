# Closed independent real-binding contract review

The next implementation is the **pure typed-result data codec inside the actual
accepted isolated VM tree**. Root selected this boundary during review. Complete
producer provenance, code applicability, loader/exporter integration, context
authority and semantic replay are separate pending work; they are not conditions
for implementing this codec. No authority getter or public route is added.

The reviewed preparation seal is
`e6e4b3b1d32ade11ef3136f3e4416e86bb8c0a32889af6bbe62a1799cb093b01`:
69 members, 859841 bytes, exact file set, no sidecar. Every member hash passed
before and after controls. The four declaration fragments were independently
reconstructed from the frozen source copies and equal `actual_data_records.rs`
byte for byte. The binding product plan's owned implementation, explicit failure,
bounded resources, original diagnostic and immutable evidence requirements remain
in scope; this data slice passes no integrated product gate.

## Selected implementation contract

Copy the exact accepted 140 distribution + 11 host-support baseline. Add only
`source/vm/src/experimental_swift_reactor/diagnostic_result_v1.rs` and its sibling
`diagnostic_result_v1_tests.rs`, and a private module declaration in
`experimental_swift_reactor/mod.rs`. Distribution closure becomes142, with11
unchanged host-support files. Test/receipt orchestration belongs outside those
source manifests and must be enumerated separately. Import the real existing
types; an extracted declaration mirror is insufficient implementation evidence.

Recommended API shapes, all crate-private, with names adjustable to repository
conventions:

```rust
fn encode_usage_v1(value: &SwiftRunUsage, output: &mut [u8]) -> Result<(), CodecRefusalV1>;
fn decode_usage_v1(input: &[u8]) -> Result<SwiftRunUsage, CodecRefusalV1>;
fn encode_failure_scalar_v1(value: &SwiftRunFailure, output: &mut [u8]) -> Result<(), CodecRefusalV1>;
fn decode_failure_scalar_v1(input: &[u8]) -> Result<UnverifiedFailureScalarsV1<'_>, CodecRefusalV1>;
fn encode_result_v1(value: ResultObservationV1<'_>, output: &mut [u8]) -> Result<(), CodecRefusalV1>;
fn decode_result_v1(input: &[u8]) -> Result<UnverifiedResultViewV1<'_>, CodecRefusalV1>;
```

`ResultObservationV1` borrows `Option<&SwiftRunFailure>`, independently borrows
`Option<&SwiftRunUsage>` for final consuming usage, and requires an unverified
reference record. `after_cleanup` is taken only from the borrowed actual failure;
there is no separately supplied potentially conflicting after-cleanup snapshot.
The original source objects remain borrowed and available after refusal. Decoded
code text borrows input; never leak bytes to fabricate `&'static str` or construct
an authoritative `SwiftRunFailure` from wire bytes. The result view borrows the
immutable complete input, has private fields, and is explicitly unverified.

All entry points reject wrong extents before indexing. Encoders preflight the
whole supplied record and leave the caller buffer byte-for-byte unchanged on
refusal. Use caller buffers and direct LE field writes; no allocation, file I/O,
hashing, environment observation, owner admission, callback, or runtime call is
part of this module. Do not normalize anomalous observations.

Retain the frozen contract's exact usage512, scalar256 and result2048 layouts
(contract sections4–5), enum IDs and byte order. They are logical LE encodings,
never Rust object images. `selection.json` closes the amendments:

- All source `usize` fields use checked u64 widening and checked host narrowing;
  the supported target scope is host `usize<=64`. Reject unsupported wider source
  values/architectures, never truncate. Function/guest-exit are u32; overflow
  refuses. Counters and reference byte lengths remain u64. All option flags,
  discriminants, optional zero payloads and reserved bytes are exact.
- Failure scalar code is1..128 exact bytes in ASCII32..126. Unknown printable
  code text, even an unusual stage/kind/code combination, remains representable
  data. A later semantic consumer must use the separately selected applicability
  registry; this codec performs no such admission. Refuse unsupported code bytes
  and retain the original failure rather than truncate or parse Debug text.
- Result presence masks are exactly0,1,3,4,5,7. Failure-present requires full scalar
  and at-failure decoding. After-cleanup-present requires failure-present and full
  usage decoding. Final-consuming usage has independent presence and full usage
  decoding. Every absent payload byte is zero. WASI=None requires its13-word tail
  zero; Some(all-zero) is distinct. Unknown enums or hidden inactive payloads
  refuse before returning a view.
- Constructor tag0 means no participating constructor: length0 and32 zero digest
  bytes. Tags1..8 require a complete-constructor reference byte length1..65536.
  The positive digest is an opaque32-byte claim, with any bit pattern permitted.
  Constructor tags do not impose stage/kind/failure-mask semantics in this codec.
- The raw-original-result reference is required and has a u64 length0..MAX plus
  an opaque32-byte digest. Length0 means an empty referenced artifact, never
  absence. Session, typed-result-schema and writer digests are also required
  fixed32-byte arguments. Any digest bit pattern, including zero, is data only.
  No source/preimage/session equality, receipt completeness, cryptographic trust
  or real retained file follows from a syntactically present reference. Later
  readers must select finite I/O bounds before using any claimed length.

The full result header retains words0..3 magic/version1/length2048/form1; word4
mask, word5 constructor tag, word6 raw byte length, word7 constructor byte length;
bytes64..96 raw digest,96..128 constructor digest,128..160 session digest,
160..192 schema digest,192..224 writer digest;224..256 zero. The scalar and three
usage partitions remain256..512,512..1024,1024..1536,1536..2048.

## Concrete findings and controls

No current extracted failure/usage field or enum variant is omitted. The21 failure
kinds,6 stages,17 resource variants (including7 reservation categories),2 deadline
origins,5 cleanup invariants,8 WASI failures (including5 budget resources), all
optionals, elapsed/deadline fields and all13 WASI words survive. Source validation
failure itself is a different type and is outside this run-result codec.

The frozen `context_contract.py:85–100` intentionally checks framing rather than
all present payloads. Three independently executed probes show it accepts:
(1) failure-present with zero/invalid failure and usage bytes, (2) final-present
with a zero invalid deadline origin, and (3) constructor tags1..8 without their
receipt. Its authority flags correctly remain false. These are concrete reasons
to implement a complete result decoder; do not promote that framing helper as
one. Its limits do not invalidate the frozen packet's stated framing scope.

Seven independent Rust methods test54 valid mask/constructor combinations;
malformed present scalar fields and code padding; every present usage partition;
hidden option payloads, wrong extents/reserved bytes; constructor presence and
65536-byte boundaries; final usage independence and all15 ledger positions;
unknown codes/anomalous observations without semantic admission. These run with
the frozen14 methods, giving21 Debug and21 optimized passes. Python runs the
frozen12 and3 new framing-gap methods, giving15 passes. Frozen custody is unchanged
and owned compiler scratch is removed. See receipt and exact commands/logs.

The next author must port these controls to **the actual VM module** and add
wrong-output-length and unchanged-output-on-refusal tests, borrowed-view/code
lifetime positive/negative compilation, actual imported-type exhaustive matches,
and a complete positive full-result round trip including all54 states. The review
reference checker validates the intended envelope; it is not the new product
encoder/decoder and supplies no actual VM integration evidence.

The15 final ledgers map unchanged to usage words
0,2,4,6,8,10,12,14,16,18,20,22,24,26,28. Preserve each observation independently;
do not infer final consumption from after-cleanup or defaults. Quarantine remains
331496 construction/combined bytes, one live ticket and the actual invariant when
observed. A codec may preserve this data; healthy-zero, actual consuming cleanup,
footer/FSM joins and external fd/name obligations are pending semantic work.

## Later integration boundary

Select the private selected-validation wrapper and private AdoptedProof sidecar
when integration starts; preserve public proof layout. Keep wrapper/sidecar
constructors private to the loader, with no clone/deserializer or public parts
extraction that permits proof/provenance transplant. Selected adoption must share
actual original admission/cleanup. A crate-visible guard needs a private-module
re-export path, since the current cache/initial-profile module chain is private;
any snapshot borrow must be tied to the guard borrow rather than only its backing
owner lifetime, and no raw-proof serializer entry may bypass the guard.

That integration still needs exact build/session/constructor/cleanup schemas,
finite simultaneous owner/work/descriptor rosters and fresh configuration-specific
sidecar/guard/result lifetime accounting. The broad148+17 proposed roster is not
selected for the codec slice. Existing proof/control/cache/guard owner layouts
are unchanged by the codec; the historical165-entry inventory is not newly claimed
as a complete codec storage inventory. No exporter or live runtime path invokes
the new codec yet, so do not claim its operational accounting is already accepted.

Canonical promotion, provenance/semantic authority, full context/FSM/replay,
native/simulator/emulator/UI/capture execution, physical matrix, separate-repo
FieldLog with published packages, OTA/store/customer/operational and GA gates
remain pending. No active implementation lanes, forbidden hosted tools/harnesses,
Android startup experiment, process inventories, canonical/index edits, commits,
pushes, messages to customers or publication were used.

Reproduce the bounded review controls with:

```sh
python3 -B verification/swift-retained-profile-real-binding-contract-review/run_review.py
```

Verify the closed packet without mutation with:

```sh
python3 -B verification/swift-retained-profile-real-binding-contract-review/seal_review.py
```
