# Independent actual-source typed-result codec review

Disposition: no blocking finding in the selected **private pure-data codec**.
The implementation is ready for root review at this bounded scope. This is not
canonical integration, runtime invocation, provenance admission or a product gate.

The reviewed candidate is the exact 235-member, 19,708,478-byte packet with seal
SHA-256 `4f5e0ffd63c343511948d1bacc933698cd36369f94b3b96f3047ff325cd94b86`.
Its 142-member distribution tree is
`58a90a1cec00fd3ffbe4d8bee90476f6e136114dbe3d506da8ab4bbd035b8ecd`.
The root selection hash is
`243a10a54d2887e83497190df56eeb1a74763c489eedfd0222dd8665cc034d55`;
the prior independent contract packet is sealed by
`2b94fd0095c898f427809b8f088d5dc2708cdc3f33c8b12bd9936bb10da4d60e`.
Input packets were read-only, including their exact file sets, before and after
the independent controls.

## Custody and actual types

All 140 baseline source identities were checked against the accepted baseline
seal and actual baseline bytes. The candidate adds exactly
`diagnostic_result_v1.rs` and `diagnostic_result_v1_tests.rs`. The only old-file
change is the exact private module append in `experimental_swift_reactor/mod.rs`.
All 11 retained host-support identities equal the accepted sealed baseline. The
manifest comparison also preserves Cargo manifests/lock, public headers, control,
proof, cache, guard and existing owner source bytes. No dependency was added.

The complete codec source and its tests were read alongside actual definitions in
`control.rs`, `experimental/swift.rs` and `experimental_wasi/mod.rs`. Imports refer
to those real types. There are no declaration mirrors. The enum encoders match
the actual enum variants exhaustively, without wildcard acceptance; decoders
explicitly refuse unselected discriminants and inactive payloads. The module is
private, with no runtime caller or public re-export in the selected change.

## Behavior review

- Every public-within-crate encode/decode entry checks its exact extent before
  indexing, decoding, converting source values, or inspecting source content.
  All internal fixed slices follow those checks. The selected host-width rule is
  explicit, and every usize conversion uses checked conversion. Both u32 scalar
  fields are checked on decode. Host execution here is 64-bit only.
- Usage is the complete logical 64-word mapping, including current/peak pairs,
  ticket counts, live counts, all validation observations and all 13 WASI words.
  None and Some(all-zero) WASI remain distinct; absent WASI data must be zero.
  Observation anomalies are retained as data without normalization or admission.
- Scalars use explicit enum mappings, six presence bits, checked optional data,
  one reserved zero word, a 1..128 length and printable ASCII 32..126. All unused
  code bytes are checked for zero. Unknown printable text is allowed as data.
- The result validates magic/version/extent/form, exactly masks 0,1,3,4,5,7,
  metadata reserved bytes, reference structure, every present scalar/usage block,
  and every absent block. It returns only after all present blocks decode. The
  original failure supplies both at_failure and after_cleanup; final_consuming
  comes from a separate borrow. No cleanup or final snapshot replaces another.
- Raw length zero is an empty required artifact reference. All required digest
  patterns, including zeros, are opaque data. Constructor absence is exactly
  tag0/length0/zero32; tags1..8 require length1..65536 and accept arbitrary opaque
  digests. The codec does not check preimages, provenance or semantic joins.
- Encoders compute all fallible words and reference validation before the first
  buffer write. Following preflight, writes have fixed proven bounds. Refusal
  preserves the complete supplied buffer and borrowed originals.
- Result and scalar fields remain private. The view, code text and digests borrow
  the immutable complete input. There is no unsafe conversion, manufactured
  static code, source SwiftRunFailure construction, owner handle or authority
  getter. The codec uses fixed arrays and borrowed slices, with no allocation,
  callback, runtime, I/O, environment, clock, hash or reservation operation.

## Independent execution

`python3 -B verification/swift-typed-result-codec-independent/run_review.py`
uses Rust 1.99.0 on aarch64-apple-darwin, Debug and optimized with overflow checks.
The runner records each exact argv, compiler identity/version, source/variant
digest, terminal result, output hash, elapsed time and bounded output. It does
not invoke the frozen producer runner, predecessor one-shot runner, owner/runtime
broad suite, hosted harness, inspector, authority driver, rejected worker or
stopped Android/Python experiment.

Both modes freshly compile the actual source with only a documented test include,
then pass the original 27 methods and seven independent methods. The producer's
54 positive mask/constructor combinations are actual result round trips. The
independent controls add:

1. Direct construction of actual imported usage/failure types and independent
   little-endian golden usage512/scalar256/result2048 bytes. All fields and three
   distinguishable snapshots are checked without generating the fixture through
   the decoder or calling codec word helpers to build expected bytes.
2. Every bit of every inactive full-result byte, every absent scalar payload word,
   scalar reserved word/code padding byte and absent WASI byte, plus every scalar
   presence bit above bit5, must refuse.
3. All 256 octets at all 128 code positions (32,768 cases per mode), all lengths
   0..256 and u64::MAX; permitted text is preserved and borrowed.
4. All 256 octets at every position of each required digest with raw length zero
   (32,768 cases per mode); every present constructor tag at both length bounds
   with 256 mixed digest patterns (4,096 cases per mode).
5. Extent precedence over invalid source content across lengths 0..2049, full
   backing-buffer preservation, and sentinel-protected exact success slices for
   all three encoders.
6. Each high bit above u32 for function and guest exit, and Some(0) preservation.
7. Named actual stage/kind/resource/WASI variants independently checked against
   selected numeric mappings.

The same candidate compile-contract variant digest is independently reconstructed.
Each mode's positive fixture compiles. All six expected negative lifetime/privacy
fixtures fail with their selected diagnostic: view/code static escape, input
mutation while a live view is later used, private view/scalar fields, and assigning
borrowed code to an authoritative static-code failure. Expected compile failures
are positive refusal controls only alongside that passing positive fixture.

Ordinary production rlib compilation passes in both modes from the unchanged
candidate source. Only two inherited dropping_copy_types warnings occur during
unit compilation, in unchanged control_operations_tests.rs; production compiles
emit no diagnostics. One old host-only layout method per mode reproduces all 165
sealed baseline rows. This deliberately does not rerun the broad owner suite.

The original 165-row inventory does **not** cover codec storage. Separately
reproduced codec sizes/alignment include refusal 24/8, scalar view 88/8,
references 64/8, source observation 80/8 and full unverified view 1680/8; local
word arrays, Option wrappers and byte buffers are recorded in layouts files.
These are host Rust type layouts, not stack measurements, simultaneous lifetime
accounting or operational reservation acceptance.

An initial reviewer-authored include fixture used an invalid inner doc comment
(Rust E0753). It was corrected before behavior testing; the failed command,
fixture and cleanup evidence remain under `attempts/initial-compile/`. It is not
a candidate failure. All scratch/compiler products from both attempts were
removed, every child was terminally waited, and frozen packets remain identical.

## Remaining boundaries

Full producer provenance, loader/exporter/carriers, cryptographic joins, code
applicability, constructor/cleanup semantics, operational codec storage admission,
full context/FSM integration, canonical promotion and runtime routing remain
pending. Native simulator/emulator/device runtime and computer use/capture are
paused and unrun. Separate-repository FieldLog consuming immutable published
packages, OTA/store/customer/operational and GA qualification remain pending.
No canonical/index/Git edit, publication, customer message, native/capture process
or process inventory occurred in this review lane.
