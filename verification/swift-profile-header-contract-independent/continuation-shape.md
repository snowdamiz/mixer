# Proposed bounded R3/R5 construction continuation

This is a review recommendation for root selection, **not implemented Rust or a
selected new runtime API**. Remove the proposed general
`borrow_initial_profile_v1(&existing_cache, ...)` entry point. Shape checks on an
already supplied cache cannot prove before-first-attempt chronology. The initial
guard must be created only inside the fresh cache construction path.

A concrete private orchestration shape is:

```rust
// New private host-diagnostic constructor wrapper in the selected cache module.
// No public exposure, arbitrary callback, generic owner implementation or runtime adoption.
fn construct_with_initial_profile_v1(
    cache_out: &mut Option<SwiftFunctionCache>,
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
    adopted: AdoptedProof,
    selected: &SelectedInitialProfileV1,
    claims: &UnverifiedProfileDigestBytesV1,
    row_output: &mut File,
) -> InitialProfileConstructionOutcomeV1;

// This sibling bridge is callable only with the internally created private guard.
// It takes no independent snapshot, raw owner scalar, row slice or descriptor.
fn write_initial_profile_rows_v1(
    initial: &InitialProfileBorrowV1<'_>,
    output: &mut File,
) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>;
```

`SelectedInitialProfileV1` is the amended R1 root-selected private input: the
complete17-field budget and the exact named local structural selection, if that
comparison is selected. It carries no verified external-build flag or caller
constructor. Its exact fixed contents, sole producer and all complete layout
places must be named before implementation selection. Do not infer that this
type or an admitted layout identity already exists.

The constructor wrapper follows this closed source protocol:

1. Admission requires `cache_out` to be None; an occupied slot is refused before
   inspecting or observing that cache. The consumed real AdoptedProof must pair
   with the actual control through existing safe checks. The selected complete
   budget is compared before construction. The caller cannot pass a previously
   acquired SwiftFunctionCache, clone a proof, supply raw validated rows or turn
   a caller boolean into authority.
2. Invoke the unchanged safe `SwiftFunctionCache::prepare`, then exactly one
   actual `CacheConstructionPhase::construct`. Keep its original return slot and
   all original typed failures/optional rejected AdoptedProof. On failure do not
   form a guard. Preserve existing actual cleanup/quarantine ownership; do not
   turn profile errors into replacement runtime failure kinds or refunds.
3. Move a successfully constructed cache into the exclusively borrowed caller
   `cache_out` storage. Consume/complete the real construction phase and original
   returned phase storage using the existing protocol. If completion fails, keep
   the actual cache in that slot for its original owner cleanup; no guard or
   profile success is emitted. The full closed outcome retains the original
   typed completion error. No borrowed guard is returned from a moved local.
4. Only inside this success branch, after phase completion and before any
   operation-preparation or acquisition can be called, create the private guard
   from a shared borrow of `cache_out.as_ref()` and shared reborrows of this
   control and this supplied optional WASI. The **only guard constructor/literal
   occurrence** belongs to this branch; no sibling/general cache-taking guard
   constructor is exposed. All original exact cache-shape/length/capacity,
   supported-proof, authentic owned-ticket, B/reservation, full budget and local
   layout checks still apply. Every SwiftCacheUsage field except fixed_reserved
   equals its actual constructor default, including peaks and own active_pins;
   control live cache entries/pins are zero. Other state/WASI usage is allowed.
5. Call only the named fixed scalar/encoding helper and restricted row bridge
   while that guard is live. No arbitrary callback, trait-provided continuation,
   user code, acquisition, mutable owner reference, control admission, worker
   reentry or suspension point is reachable between construction and emission.
   The bridge obtains **this guard's retained cache.proof() internally** and
   calls the unchanged accepted row writer with the empty offset0 File. Because
   the guard/cache/control remain shared-borrowed, no safe mutable cache/control
   operation can overlap it. Lifetime/privacy/compiler facts need fresh actual
   Rust tests; the shape in this document does not prove them.
6. End/destroy the guard before releasing the exclusive wrapper argument borrows
   or returning to any caller that can acquire/mutate/clean up the cache. Only
   the original cache owner, actual fixed header bytes and fixed observations/
   errors may survive; no guard, proof reference, capability flag or acceptance
   getter escapes. The completed wrapper returns cache_out ownership to its
   caller in every constructed-cache branch, including header/row failure.

`InitialProfileConstructionOutcomeV1` must be a named fixed closed outcome with
the original constructor failure and rejected-proof ownership, original phase
completion failure, optional header result and optional row-writer result
represented without ambiguity. Not-attempted is distinct from success/error.
Its exact discriminants/fields are a remaining preimplementation contract task;
no size, code, transfer allowance or new error ABI is selected by this review.
The wrapper is not complete for implementation selection until root closes that
outcome inventory and its ownership-preserving failure protocol. In particular,
do not use `Result<Header, HeaderError>` to discard a real constructor/completion
failure or the only cleanup owner.

The new wrapper and every actual caller, selected-data producer, private bridge,
complete outcome/error/Result/caller/return/move place, guard lifetime, File/
Metadata transfer and loop must be included in the exact new source/build and
unchanged-limit accounting selection. This is a host-only cache-construction
diagnostic path; it executes no guest, native runtime, replay or full target.
No eight-digest verification, composition, custody or actual-header authority is
implemented or authorized here. The row File remains distinct from the later
profile output and retains its original acknowledged-progress semantics.

Under recommended R2 this captures the supplied optional owner and proves common
control ownership. It makes no claim about a prior cache's historical optional
WASI instance because no prior cache is accepted. Under recommended R4 it proves
exact actual cache-owned tickets and B equality without claiming that byte
equality excludes a preexisting unrelated zero-byte Cache ticket. If root instead
requires global categorical exclusivity, its selected caller must begin with
fresh adoption and enumerate every allowed pre-cache admission; neither this
signature nor local postconstruction shape alone supplies that fact.
