# Independent preaccess diagnostic oracle

The oracle and corrected bindings were frozen before reading any member of the
new `swift-root-bound-work-storage-layout-probe` producer lane. The accepted
proposal, its three fragments, accepted original source146 tree, and existing
independent review are the only producer-derived inputs used. The new lane is
not imported by this parser. No compiler or runtime command has run here.

The original source146 tree is
`91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f`.
Every original source member was independently read and hashed, as were the 66
members of the two accepted inventory/review packets. In-memory application of
exactly two named-query insertions and one actual dispatch-expression
replacement yields diagnostic source146 tree
`2ec0d8555d6a18d7c8222984faaec3a1543c1a1b800f4b90381f70571215516e`.
No diagnostic source file was written by this lane.

`preaccess-oracle.json` pins the accepted contract, source tree, compiler,
argv/environment, bounds, cardinality, identity and refusal policy.
`diagnostic-bindings.json` preserves the original in-memory reconstruction.
`preaccess-oracle-correction.json` pins the original files and corrects exactly
one multiline span's end column in `diagnostic-bindings-corrected.json`.
All original source bytes, byte offsets, query identities and tree digests are
unchanged by that correction. The parser consumes the corrected bindings.

Require 56 unique primary E0308 diagnostics, bound to the exact source
size/align RHS and same-file `pair!` invocation expansion for the 28 frozen
types. Require two unique primary E0512 diagnostics at the two actual closure
transmute expressions, with concrete source and zero target type notes. The
actual closure identity must be exact in both `MaybeUninit<C>` and the leading
u8 `repr(C)` `ClosureAlignmentProbeV1<MaybeUninit<C>>`; a capture proxy or field
sum is not accepted. All source spans, byte coordinates, line/column positions,
source excerpts and supported labels are bound to the independently
reconstructed source. Every missing, duplicate, ambiguous, dependent, malformed
or unexpected primary diagnostic refuses observation. The finite parser is
intentionally permitted to refuse previously unqualified compiler formatting;
such a refusal requires separate review, never an automatic retry.

For concrete source bits S and wrapper bits P, require both positive byte
multiples, `(P-S)/8` positive and a power of two, and `(S/8)%((P-S)/8)==0`.
Only then can the closure byte size be S/8 and alignment be `(P-S)/8`.
These arithmetic rules are source-level reasoning, not measured product data.

`test_independent_parser.py` passed one complete synthetic positive stream and
34 fresh refusal controls. They cover omitted/duplicated diagnostics, wrong
code/source/expansion/query operation, ambiguous spans, nonconcrete/invalid
named layouts, wrong closure/proxy/wrapper/target identity, dependent source
bits, malformed or duplicate-key JSON, unexpected warning/stdout/exit/summary,
and six invalid S/P pairs. Synthetic values are never product observations.

Two reviewer development failures remain preserved. The first was a
lexically-sorted string membership assertion compared against pathlib tuple
order; it occurred before the original oracle was written. The second was the
multiline end-column helper error caught by the synthetic positive stream.
These are reviewer defects, not producer findings. The final corrected
synthetic run passed; no compiler, runtime or producer checker was retried.

Diagnostic strategy qualification, actual layouts, full storage/layout closure,
all work/storage prices, backing capacities, simultaneous peaks, funding,
forgotten-result/root durability, useful joint retirement, full ownership,
native behavior, immutable external FieldLog packages, OTA and GA remain
pending. No canonical source, central metadata, old price, other lane, hosted,
Android, native/UI/capture/phone or global process inventory work occurred.
No native instance was started; no native-instance cleanup is owed. Future
compiler release requires root's separate reservation and complete bounded
runner/source/parser/output/cleanup review.
