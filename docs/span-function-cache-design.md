# W08 bounded decoded-function cache design

Status: root accepted for implementation on 2026-10-23. This document is the exact
bounded implementation contract; it does not authorize execution or admission of
full Swift. The existing complete streaming validator remains the only producer
of `ValidatedSpans`. Implementation ownership is `vm/src/experimental/cache/`,
`vm/tests/span_function_cache*.rs`, this document, and
`verification/span-function-cache/`. Root owns feature/module exposure, shared
status/gate files, commits, and pushes.

## Boundary and identity

Add a Rust-only nondefault `experimental-function-cache` feature depending on
`experimental-stream-validation`. No default route, C symbol/layout, native
wrapper, profile grammar/ceiling, import admission, archive, or UI change is made.
`FunctionCache::new(ValidatedSpans, CacheBudget, &Cancellation)` consumes the exact
sealed complete result. There is no bytes/path/hash/proof deserialization
constructor, alternate limits argument, clone, source mutation, or source copy.
Invalid uncalled or unreachable code must fail complete streaming validation
before the constructor can receive authority. Imports are not decoded entries.

Each cache owns its source, exact selected profile/limits, metadata and
`ValidatedSpans::VALIDATOR_REVISION`, plus `DECODER_REVISION = 1`. A checked global
monotonic atomic owner number is issued without allocation; exhaustion fails
closed and never wraps/reuses an identity. Cache identity is process-local only,
not a security signature or portable artifact identifier. An entry key is
`(owner identity, validator revision, decoder revision, absolute function index)`;
profile/limits and immutable source are bound by the unchangeable owner. No
external hash supplies validation authority. Moving a cache does not change it.

## API and pins

`pin(function_index, &Cancellation)` returns an opaque, non-Clone `FunctionPin`.
A pin contains only the owner number, a bounded pin-table slot and a checked
monotonic nonce. It contains no pointer/reference/Arc. `view(&pin)` verifies all
three values and the current entry, then returns a short borrow into the cache.
The view exposes the exact immutable locals, instructions, branch targets and
function/type/absolute-source positions. A future executor may keep pins in
frames, take a short instruction borrow, copy a Copy instruction, end the borrow,
then pin a recursive or indirect callee. No returned reference can survive a
mutable cache operation. This component provides no executor or invoke method.

Each active pin has a preallocated record identifying its resident slot; entries
have a pin count. Repeated pins of the same function consume separate pin slots
and increment that count. Nonces never wrap. `release(pin)` consumes a successful
pin and removes its record; release performs no allocation, cancellation check,
work charge, eviction, or decoding, so cleanup remains possible after a trap,
cancellation or exhausted decode budget. An incorrect-owner/stale release
returns an allocation-free `ReleaseFailure` retaining the original pin, allowing
the caller to recover it. Double/stale token use fails closed. Forgetting a pin
leaves its record and payload counted and ineligible for eviction; dropping the
cache drops all of its own storage safely. There is no automatic cross-object
Drop callback, unsafe dangling reference, or `Arc::new`/`Box::new` allocation.

Default auxiliary budgets, independently narrowable and never executable-profile
limits: 16 MiB total additional cache reservation; 8 MiB maximum entry payload;
64 resident slots; 64 active pins; 64,000,000 lifetime work credits. Zero byte or
work ceilings are legal deliberate rejection configurations; slot/pin ceilings
must be positive and at most defaults. A budget cannot widen any default. Actual
resident slots are `min(max_entries, defined_function_count)`; pin records are
`max_pins`. All caches have their own budgets; this does not provide an aggregate
multi-session memory admission controller.

## Fallible decoding and reservation model

The frozen decoder uses infallible `Vec::push` growth, per-branch `Vec` payloads,
and allocating diagnostics/inventory. It is a parity reference only, not called
by this cache. The new original decoder emits Copy operations and absolute byte
offsets. `BrTable { first, count, default }` indexes one flat `Vec<u32>` rather
than allocating a vector per instruction. Block/else targets are patched in an
exact-capacity instruction vector using a bounded 128-element control array.
The supported operation meanings and control target indices match frozen IR.

A fully metered first pass re-reads the requested validated body and counts exact
expanded locals (parameters remain in compact source metadata), instructions and
branch targets. It reads every immediate and zero-count local group, checks
arithmetic and current frozen limits, and determines the exact payload charge:

`E = locals * size_of(Type) + instructions * size_of(DecodedInstruction)
     + branch_targets * size_of(u32)`.

The second pass allocates those three vectors using `try_reserve_exact`, rejects
unexpected capacity, expands locals and decodes/patches the instruction/branch
vectors without any growth. Every push is preceded by a verified capacity and
work check. Zero-capacity vectors do not allocate. No `collect`, `to_vec`,
allocating format/String, vector shrink, or infallible allocation is permitted
on cache constructor, decode, pin, failure, or release paths. No general-purpose
dependency is added.

Charge fixed `size_of(FunctionCache)` plus the exact full resident-slot vector
capacity and pin-record vector capacity before constructor allocations. These
are additional conservative cache reservations; the embedded validated owner
header may also occur in its retained validator reservation. A fixed scratch
reservation explicitly covers the reader/pass/meter/error state and bounded
control array. It is an accounting model, not compiler stack layout or RSS.
All constructor arrays use exact fallible reserve and metered initialization.

`resident_bytes` includes every live entry payload, including pinned entries;
`pinned_bytes` is the pinned subset and is reported separately without adding it
a second time. Before building one miss, reserve E while every existing resident
entry remains counted. Thus the admission check is

`fixed + resident_bytes + construction_bytes + scratch <= capacity_bytes`.

There is only one construction in this single-owner mutable cache. Once the
preflight has established E, an oversize E fails before eviction or allocation.
A miss may evict least-recently-used unpinned entries until a slot and E fit.
Scan work and a planned eviction-count charge are checked before any destructive
cache action; cancellation/work failure during the bounded selection scan leaves
entries intact. The selected evictions can be applied as one bounded phase after
that precheck. Pinned entries are never selected. If all suitable entries are
pinned, return a specific exhaustion error with no construction allocation.
Dropping an evicted payload happens before releasing its reservation. Reserve E
before the first construction allocation; release it after partial decode drops
on failure. Once construction is complete and cancellation is checked, publish
it in an empty slot and move its charge to resident bytes without duplication.
The miss pin is published only after all decoding and owner/nonce/pin checks.

Resident/pinned/construction/fixed/scratch reservations, their peaks, work, hits,
misses, successful decodes and evictions are exposed as scalars. The combined
reservation also reports retained source plus validator metadata. Failed
construction never leaks a reservation or entry, but a failed miss may have
already evicted unpinned entries after its checked eviction phase. That behavior
is explicit; publication is transactional, cache retention is not a promise.

## Work, cancellation and errors

The cache uses a separate cumulative lifetime work counter, never execution fuel.
Charge before byte/immediate reads, zero-count local traversal, local expansion,
instruction emission, branch-target traversal/emission, control patching,
resident-slot scans, pin-record scans, LRU selection and eviction. Check existing
cooperative Cancellation before each charged operation, before each allocation,
after allocation, before eviction application and before publishing a pin/entry.
There are no unmetered quadratic comparisons/sorts or body traversals. Allocation
and fixed-size bounded drop calls are not wall-clock preemptible. In particular,
no canceled request can return a cached hit or new pin, and cancellation before
lookup/preflight causes no eviction.

Errors contain only static codes and scalar function/absolute-byte/work/usage
state. Distinguish invalid budget, invalid/import function index, wrong/stale pin,
entry oversize, capacity/all-pinned/pin exhaustion, work exhaustion,
identity/nonce exhaustion, cancellation, allocation failure, and impossible
validated-body/decoder mismatch. A mismatch fails closed and yields no entry;
it does not reclassify or widen validator acceptance.

## Verification and completion boundary

Original tests will build legal existing v1/v2/v3 modules and compare decoded
locals/opcodes/constants/immediates/offsets/control targets/flat branch payloads
with the frozen decoder through internal unit assertions where private IR is
needed. Cover nested block/if/else/loop, recursion and indirect-call token
retention (cache behavior only), repeated hits/pins, LRU eviction, all-pinned
exhaustion, oversized entry, exact/one-byte capacity and work boundaries,
zero-count locals, invalid uncalled body before cache construction, caller-buffer
independence, source lifetime, moving caches, wrong-owner releases, forgotten
pins, canceled hit/miss, decode cancellation and allocation failures at every
constructor/decode allocation ordinal. A separately gated allocator test must
show requested peaks bounded by reservations, no reallocations, and complete
heap cleanup after failure/drop. Canceled/failed decode leaves no entry/pin.

Record commands, tool versions, source revision and dirty-tree digest, outputs,
scope and limitations under `verification/span-function-cache/`. Reuse an
existing Cargo target and offline local fixtures; create no dependency graph.
Run focused debug/release cache tests plus relevant existing streaming/default
checks and frozen-source/C ABI isolation checks coordinated with root. Formatting
and Clippy apply to the new feature. Existing validators/decoders/tests/fixtures
remain original repository work; no external engine implementation is imported.

Acceptance is a decoded-function cache for already supported legal modules.
Execution bridge, actual recursive/indirect guest execution, trap/close runtime
integration, WASI, larger ceilings/full Swift, FieldLog guest qualification,
physical iOS/Android, standards/fuzz/security review, aggregate session accounting,
immutable published consumer packages, release/OTA and all GA gates remain pending.
