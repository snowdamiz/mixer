# Independent Swift reactor validation-stage review

No open actionable defect remains in the reviewed validation-stage source. This conclusion is bounded to complete fixed-policy host validation, proof authority and frozen legacy validation behavior. It does not qualify execution, packages, signing, device behavior or GA release.

The implementation owner explicitly froze the post-refactor engine/tests and confirmed the complete `2026-10-23-final-v2/local/source` capture. The independent runner copied that source into a private read-only snapshot, captured all source/assets plus probe sources, and used separate build targets. VM manifest SHA256 is `ff8bd3b1d92d4c8dc577bb20e3eb8137f7ce4d6bd6d22741372d5ac4afd56ec2`; both the owner source and private review source remained unchanged. `receipt.json` records 115 commands, tool versions, all outputs and source manifests. The three `*-source.tar.gz` archives preserve every tested byte.

## Resolved review risk

Initial source review identified shared layout additions to `Meter`, `Metadata` and `BodyState` that could increase fixed reservations charged to frozen `validate_spans`, including feature-dependent changes. The owner corrected this before freeze using zero-sized frozen control/declaration specializations and Swift-only observations/declared forms. No reviewer production edit was made. Frozen `Meter`, `Metadata`, `BodyState`, `ValidatedSpans` and borrowed policy layouts remain 88/352/144/520/8 bytes on this 64-bit host.

Independent public-API comparison against immutable `e299f1a60eb06dc9405021fc49ced215eaa42336` now matches bit-for-bit, including success/error kind/code/function/offset, work and every reservation field. The witness set includes an empty module, one function, active data beyond initial memory (still accepted by legacy validation), control depth at its frozen boundary and over that boundary. Sixteen exact/minus-one metadata/scratch/work budget vectors also produce identical admission and failures across all five configurations:

| Configuration | Result |
| --- | --- |
| Old baseline, stream feature, Release | Golden observations |
| Reviewed source, stream only, Release | Identical |
| Reviewed source, Swift feature, Release | Identical |
| Reviewed source, all features, Release | Identical |
| Reviewed source, Swift feature, Debug | Identical |

For example, the empty legacy module still charges metadata520, scratch peak744 and work16; one function still charges metadata544, scratch peak808 and work64. Default-feature repository regressions and later integration checks remain root-owned; these witnesses exercise the frozen stream entry point, which requires its feature.

## Independent executable probes

`probe.rs` independently encodes the fixed structural ABI with hand-authored constants; it does not use the owner's fixture builder or `WasiFunction::ALL`. Its hardcoded signatures/names were separately checked against the retained `descriptors.json`. All 147 cases pass in Swift Release, all-features Release and Swift Debug. Each configuration also passes all41 observed allocation-failure ordinals and all41 cancellation ordinals, with exact call counts and unchanged owned live bytes after cleanup.

The cases cover source-copy ownership after caller mutation/drop; every import signature/name, namespace/order/duplicates/extras; declared memory maximum versus absence; table maximum presence; export names/signatures; rejected start sections and malformed UTF8; invalid types in every one of the29 defined bodies, including uncalled/unreachable code; invalid dead local/branch/call/load alignment and unsupported instructions; valid polymorphic unreachable; unsigned initial data/element bounds including empty boundary segments and negative offsets; immutable ordered overlapping segment views; exact/narrowed/zero/widened budgets; deadline zero/overflow; and pre-cancellation before allocation.

Eight external negative compile probes reject for their expected reason: proof fabrication, cloning, source mutation, borrowed-source escape, conversion to legacy proof/eager module/cache, and access to private policy construction. They compile against the reviewed all-feature library; a missing feature/library cannot count as the expected rejection.

## Source and evidence review

- The public Swift proof owns an immutable copied source, private policy and private metadata. No public arbitrary import policy, relaxed proof producer, deserializer, Clone, mutation or executable conversion exists. The distinct identity never constructs widened published `Limits`.
- Exact ABI checks require all34 ordered closed adapter resolutions with full signatures, fixed table46,713/46,713, memory584 with absent declared maximum and host cap768, exact three export names/kinds/indices/signatures, and no start or imported resources. Declaration flags and absolute declaration locations survive normalization.
- Every defined body passes the operand/control validator before its success counter advances. Unreachable code retains type/index checks. Separate signature/aggregate/local/group/global/count/operand/control/instruction bounds are explicit, rather than widening legacy fields.
- Source, metadata and scratch reservations are checked/fallible, include old/new growth overlap and fixed state, and reject unexpected capacities. Cancellation/deadline checks surround bounded source copies and occur in source/metadata/name/body work. Error state is inline and cleanup drops buffers without work, allocation or cancellation dependence. The owner's frozen56-ordinal tests independently record source/metadata/body real delayed-allocation deadline checks; this review did not substitute elapsed-time guesses for stage coverage.
- Swift-only active segment checks use unsigned destinations and checked addition against initial extents before sealing. Shared legacy validation still defers these bounds as before, verified by the public witness.

`final-qualification-integrity.json` independently hashes the retained target and verifies all98 captured source/assets against the canonical final-v2 receipt. Its VM manifest exactly matches the independent review snapshot. Target size53,777,114 and SHA256 `24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994` match. The qualifying driver hashes the actual retained caller allocation, keeps it alive through validation and equality comparison, and records real length/capacity separately from internal reservations. The receipt records all79,832 bodies validated, including the six formerly rejected deep bodies, 6,505,659 instructions, 188,428,924 work credits, internal peak54,827,522 and caller-capacity overlap108,604,636 bytes. Its focused Debug/Release, proof-authority and lint commands all exit0. These are reservation/capacity observations, never RSS or execution results.

The first independent attempt hit the owner's incomplete snapshot omission of existing `include_bytes!` JSON during the all-feature build. `intermediate-missing-assets/` preserves that failed harness attempt and its exact sources/logs. Complete final-v2 assets fixed the capture; engine/test code was unchanged. This failure is not presented as product evidence or a passing check.

## Remaining boundaries

Only this new review directory was written by this review task. No production/test source, frozen allocator evidence, dependencies, device state, commits or pushes were changed. No Wasm was instantiated or executed. Root still owns integration regression/CI and any later implementation stage, published package dogfood, target/compiler/signing/store, physical-device and accountable GA gates.
