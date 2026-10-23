# Execution-stage design inspection, 2026-10-23

This is a design-only source inspection, not an independent implementation audit,
execution receipt, approval, allocation measurement or gate pass. The proposed
contract is `docs/swift-reactor-execution-stage-design.md`. Root owns acceptance,
integration and any later exact-target attempt. No product code, tests, fixture,
dependency, status, work graph or gate is changed by this lane.

The collector records tool versions and complete read-only command output,
current revision/dirty state and a source-file hash manifest, including the
uncommitted validator. It hashes the retained artifact without validating,
instantiating or executing it. Its assertions only bind existing evidence and
document integrity; they are not program validation or OTA admission.

## Source findings and chosen boundaries

1. `experimental/swift.rs` already retains a single source, private complete
   metadata, distinct borrowed closed policy, 34 sealed `WasiFunction` values,
   exact usage and complete observations. Its public proof is non-Clone and
   immutable. Private borrowed descriptors suffice for cache/execution; no new
   proof payload/layout or validator-ledger retrofit is needed.
2. `experimental/mod.rs::ValidatedSpans` and frozen `Metadata` have distinct
   layouts from the Swift proof. `policy.rs` already avoids representing Swift
   as v3 `Limits`. Keep those definitions exact; shared algorithms borrow the
   two sealed representations through static private adapters.
3. `cache/mod.rs::FunctionCache` stores the proof, budget, usage, owner/nonce and
   slot/pin vectors directly. Its source/meta observations are not allocation
   tickets. Preserve that public owner and identities/layouts; use a separate
   private Swift owner and pin type, reusing borrowed algorithms.
4. `cache/decode.rs` reads frozen `Limits`, derives float admission from public
   `Profile`, and has a 128-element patch array. Swift needs closed policy getters
   and one accounted 512-element scratch arena, reused across both passes. The
   old specialization must retain its exact 128-element scratch/layout/formulas.
5. Cache `Meter::check` checks only cancellation. All reader work flows through
   the meter. The Swift meter must carry the private runtime control inside scan,
   build, patch/reset and allocation/publication, with no new deadline in the
   frozen meter or old public error enums.
6. `execution/mod.rs` obtains runtime ceilings from `cache.spans().limits()` and
   invokes only exact checkpoint/abort. New compile-time borrowed modes must
   resolve Swift frame/value/control/memory/fuel/host ceilings independently and
   dispatch only sealed `WasiFunction`. Existing public `SpanInstance` stored
   fields and generic method behavior must not widen.
7. Existing frames already own one opaque pin; the loop copies a selected scalar
   instruction/br_table target before mutation. Preserve that architecture,
   including all acquired-pin failure cleanup and cumulative counters.
8. Execution `allocation` precharges State and memory growth preserves old/new
   reservations, but it has no combined authority. New Swift allocation paths
   must admit both category and Combined atomically before heap allocation and
   retain tickets through overlap until storage is dropped.
9. Standalone WASI constructs four buffers before reporting reservations. It
   cannot enforce a shared total from the outside. A private accounted
   constructor admits each buffer and returns private ticket ownership beside
   its unchanged `WasiContext` layout; standalone behavior remains exact.
10. WASI's existing deadline field and internal checks protect staging, service,
    backup and commit, with rollback on an interrupted commit. Seed that field
    with the earliest runtime/WASI absolute deadline in the private constructor;
    no outer-around-dispatch approximation or extra public callback is needed.
11. Root clarified the stage boundary: validation has its own <=81 MiB admission.
    Runtime synchronously adopts trusted retained source/meta, rejects narrowed
    totals before any new runtime allocation and then uses one ledger. Transfer
    wrapper headers/scratch must be counted separately; validation history is
    not current runtime allocation. The runner drops external input first.
12. `Cancellation` currently wraps `Arc<AtomicBool>`. Shared backing reservation
    attribution must count one backing, not multiple clone handles or handle
    size alone. The design requires a private target/toolchain layout measurement
    backed by allocator evidence before making a measured runtime claim.
13. The retained native reference contains 11 complete observations. Qualification
    must compare two actual captured complete objects and return codes after
    exactly one initializer, without mutating the model or substituting expected
    JSON. Existing reference host-call counts are not sink-equivalence promises.

## Evidence limits

The canonical final-v2 receipt proves complete owned validation of all 79,832
defined bodies under the separate accepted policy. Its 188,428,924 work credits
and 54,827,522-byte internal reservation peak are historical validation facts,
not runtime fit, cache demand, call depth, fuel sufficiency or performance.
The proposed 64 MiB source, 16 MiB cache, 128 MiB State, 256 MiB Combined, 64 frames/pins,
768 pages and 30 s runtime ceilings remain unmeasured runtime limits.

No compiler build, unit test, guest run, new platform service, device discovery,
phone run, commit or push is performed by this collector. Source manifest
comparison records drift from the canonical validator snapshot rather than
silently assuming that a Git revision binds dirty working-tree contents. Root
must review any relevant mismatch before implementation or execution evidence
is attributed to a source tree.
