# Proposed next stage: owned full-Swift reactor execution

Design for root review, 2026-10-23. This document does not authorize implementation
or target execution. The accepted validation stage remains frozen while root
integrates it. `mixer-product-plan.md` remains binding. This stage would add one
Rust-only execution route; production admission, native ABI, publication, signed
runtime, mobile qualification and every GA gate remain separate.

## Starting evidence and scope

`verification/swift-reactor-validation/2026-10-23-final-v2/receipt.json` is the
canonical complete-validation receipt. It binds the actual 53,777,114-byte
reactor with SHA-256
`24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994`.
All 79,832 defined bodies, including the six former deep-control failures, passed
the owned type validator: 188,428,924 work credits and 54,827,522 bytes internal
peak reservation. It records `executed=false`. This is stronger than the earlier
grammar inventory and still proves no runtime behavior.

The existing `FunctionCache`, `SpanInstance` and standalone `WasiContext` provide
implemented, reviewed building blocks. Their independent meters cannot enforce a
simultaneous combined runtime ceiling. The cache decoder accepts frozen `Limits`
and uses `[Patch; 128]`; the executor reads every runtime limit through legacy
`ValidatedSpans`; WASI starts a later private deadline and reports its four buffer
allocations after constructing them. These are specific private seams required
before composition. Another eager `Module`, duplicate retained source, raw-byte
constructor or conversion of Swift authority into published v3 is forbidden.

## Public authority and state machine

Keep the existing nondefault `experimental-swift-reactor` API and proof opaque.
Root may add the feature dependencies needed for the new private cache/executor.
Existing Cargo features never select a different policy for an old entry point.
The proposed additive public surface is:

```rust,ignore
SwiftReactorInstance::new(
    proof: ValidatedSwiftReactor,
    budget: SwiftRunBudget,
    grants: WasiGrants,
    wasi_budget: WasiBudget,
    cancellation: Cancellation,
) -> Result<SwiftReactorInstance, SwiftRunFailure>;

instance.invoke_corpus() -> Result<i32, SwiftRunFailure>;
instance.usage() -> SwiftRunUsage;
instance.stdout() -> &[u8];
instance.stderr() -> &[u8];
instance.identity() -> SwiftRuntimeIdentity;
```

Names may follow project conventions. The restrictions are binding if accepted:
no arbitrary export/index invocation, public cache/pin access, raw guest memory
view, mutable memory, supplied host context, import callback, policy object,
deserializer, source constructor, fuel setter, budget refill, Clone or conversion
to an executable legacy owner. Existing immutable validation diagnostics on the
proof remain diagnostics. Copied runtime identity contains a distinct policy
identity and validator/decoder/executor revisions, never `Profile::TableMemoryV3`
or a `CacheIdentity` with a fabricated profile. A digest does not authorize this
owner; only complete validation produces its consumed authority.

Private state is `Constructing -> Initializing -> Ready`, followed by any number
of bounded corpus calls or sticky `Exited/Failed`. Construction initializes
memory/table/globals, constructs exactly one internal WASI context and invokes
the sealed `_initialize` index 35 exactly once. Ready requires its exact empty
result and zero live frames, values, controls and pins. No Ready owner escapes a
failed constructor; no retry, fresh context or counter reset hides failed work.
`invoke_corpus()` invokes sealed index 62, requires the already proved `()->i32`
signature and preserves guest state/captures between calls. A nonzero i32 is an
actual result that fails corpus qualification; it is not fabricated as a VM trap.
The qualifying runner performs exactly two calls on one initialized owner.

## Private reuse while preserving frozen owners

Preserve the literal stored fields/layouts of `ValidatedSpans`, `FunctionCache`,
`FunctionPin`, `SpanInstance`, legacy frame/control/meter/failure/usage types and
standalone `WasiContext`. No extra stored policy enum, deadline, ledger pointer,
callback, trait object or discriminator is added to those owners. Preserve old
default and narrowing checks, count/stack limits, import admission, error
precedence, work charging, identities and usage formulas in every feature build.
Private `Metadata<FrozenDeclaration>` and its zero-size specialization stay exact.

Choose **sealed generic borrowed algorithm adapters**, not a new stored wrapper
around a public legacy owner. Extract common decoder/cache/execution algorithms
behind private borrowed `SnapshotView`, `CacheParts` and `ExecutionParts` adapters
with associated pin/frame types and static mode methods. Only the existing
sealed legacy proof and the sealed Swift proof implement snapshot authority.
Adapters borrow original fields; they copy no metadata, source or code. A
zero-size `FrozenMode` resolves original checks/errors, and a private Swift mode
borrows the closed policy plus runtime control. No generic policy is public and
no downstream crate can implement a snapshot or host mode. Public legacy
constructors retain their types and call the frozen specialization. Shared
operation code must not silently change their counter order or semantics.

The Swift route owns a private `SwiftFunctionCache` containing the original
`ValidatedSwiftReactor`, bounded slots/pin records, decode scratch and Swift-only
cache counters/identity. It has a distinct private pin type and no public
constructor. Add only crate-private borrowed proof descriptors for signatures,
types, function spans, globals, ordered segments and the already sealed
`WasiFunction` array. Keep the proof fields, validation API and public proof layout
unchanged; an accessor does not create independent proof authority. Do not
reparse import strings or feed a widened `Limits` into legacy entry points.

Decoder policy getters distinguish float/table grammar, source extent,
parameters per signature, groups, parameters-plus-locals, instructions and
function-inclusive controls. For Swift, verify decoded locals plus sealed
parameter count against 256. Every span uses the actual retained source extent.
The frozen wrapper still uses its exact limits and `[Patch;128]` layout/scratch
accounting. Swift allocates one exact-capacity 512-patch arena during cache
construction, charges its actual `size_of::<Patch>() * capacity`, and reuses it
sequentially across scan and build; no second patch arena or per-miss heap scratch
is introduced. Reset/scan/build/patch work and transient readers/failures are
accounted. Do not reuse the unrelated legacy diagnostic decoder layout estimate.
Both passes must agree on instruction/target/local counts before publication.

The executor uses fixed frame/value/control arenas. Each defined frame owns
exactly one opaque Swift cache pin, including recursive frames; every frame's
function control contributes to the aggregate control count. No cache reference
survives a mutation. Copy only the selected scalar instruction/br_table target,
end the borrow, then mutate state or pin a callee. Numeric helpers are reused
only after proving their pushes fit the existing arena. Ordinary scalar numeric,
float, saturating, table, indirect-signature and bulk-memory semantics remain the
owned engine's semantics, not a new Swift approximation.

## Runtime ledger adoption and reservation ownership

Validation and runtime have separate budgets. Validation already independently
enforces at most 81 MiB internal source+metadata+scratch reservation. This proposal
does not retrofit a 256 MiB runtime ledger into validation. At runtime entry the
constructor synchronously consumes the sealed proof and adopts its trusted exact
retained source and metadata reservations into a fresh private ledger. Validation
scratch is no longer live. The proof's metadata count includes its complete
fixed header, including embedded source/metadata handles. Reject a narrowed
source/metadata/combined ceiling immediately, before any new runtime allocation.
This is an explicit accounting/ownership transfer, not a claim that the ledger
existed when the proof's allocations were made. Preserve validation usage and
peak as historical observations, never add its peak to current runtime usage.

One `RuntimeControl` then owns all runtime reservation and cumulative counters.
Every allocating path synchronously borrows this same authority; there is no
second ledger, snapshot-summing enforcement, thread-local authority, `Rc`/`Arc`
ledger or independent component admission later reconciled with it. Private
non-Clone reservation tickets move with the exact allocations. Proposed seams:

```rust,ignore
RuntimeControl::adopt(proof_usage, run_budget, started, cancellation)
    -> Result<RuntimeControl, SwiftRunFailure>;
control.admit(category, requested_bytes, cursor) -> Result<ReservationTicket, _>;
control.release(ticket); // only after the corresponding storage is dropped
control.check(cursor) -> Result<(), SwiftRunFailure>;
control.work(component, credits, cursor) -> Result<(), SwiftRunFailure>;
```

These are private ownership seams, not final Rust spelling. Tickets are inline
values with closed construction and checked category/byte ownership. They do not
borrow the ledger for an allocation's entire lifetime or contain self-referential
raw pointers. Swift-owned accounted allocations release through explicit cleanup
that drops storage before releasing tickets. Failure to release can conservatively
retain a charge; it can never create room. Cleanup must not allocate, spend work,
call services or check cancellation/deadline.

For each reservation, checked arithmetic computes both the category next value
and combined next value, then commits the debit atomically only if both fit.
Admission occurs before `try_reserve_exact`, initialization or copying. Failed
allocation drops partial storage before releasing its ticket. Require the exact
requested logical capacity; an unexpected allocator-reported capacity is a typed
failure with requested/observed capacity and no successful owner. Do not admit
extra capacity after the allocation to disguise it as compliant. Record any such
fault explicitly; reservation ceilings are not allocator-overhead or RSS claims.

Use disjoint ledger categories and preserve their simultaneous current/peak:

| Category | Included once |
| --- | --- |
| RetainedSource | The proof's actual owned immutable source allocation |
| RetainedMetadata | Actual metadata capacities and the existing proof header |
| Cache | Swift cache's exclusive header, slot/pin capacities, permanent patch arena, resident decoded vector capacities, in-progress entry construction and bounded cache scratch |
| State | Exclusive execution header, arenas, table/globals/memory and temporary old/new memory growth overlap, plus bounded execution scratch |
| Wasi | WASI's fixed context, accounted-wrapper/ticket overhead and its four actual buffer capacities |
| Shared | Exclusive ledger/control header and the shared cancellation backing reservation |
| Construction | Simultaneously live transfer/construction wrappers, borrowed adapter/meter/readers, scalar/failure temporaries and construction scratch not already included above |

Fixed-header subtraction follows the actual nested types, with checked arithmetic:
cache exclusive header excludes `size_of::<ValidatedSwiftReactor>()`; execution
exclusive header excludes embedded cache, WASI owner and control sizes. Their
children are already charged. Build receipts record actual target `size_of` and
alignments; no old 520-byte estimate is copied. During proof/cache/instance
transfer reserve a conservative bound for all simultaneously live old/new wrapper
headers until those temporaries leave scope. A Rust move does not justify
silently deleting real transient wrapper scratch; no second source/meta payload
is copied. Dedicated allocator/layout tests substantiate the accounting model.

The supplied cancellation's handle bytes belong to each containing header. Its
single shared backing allocation is attributed once to Shared while the VM
retains handles, including a WASI clone; cloning must allocate nothing. Root must
provide a private requested-layout measurement for the current
`Cancellation(Arc<AtomicBool>)`, checked against allocator observations on the
qualified target/toolchain. Do not infer backing size from the handle's size or
pretend that arbitrary caller allocations can be discovered. This attribution
is VM reservation accounting, even if the caller also retains a handle. The
control itself uses inline state, not a new shared heap allocation.

Pinned bytes are a subset of cache resident bytes. Construction bytes become
resident with an atomic category-neutral ticket transfer after successful decode;
they are not counted as both. Plan eviction before effects, drop only unpinned
victims, release their tickets after drop, then admit new entry construction.
Cache scratch, existing pinned entries and the new entry coexist in the ledger.
Never sum `CacheUsage.peak_total_reserved` with source/metadata again.

Memory growth retains the old allocation's ticket, admits the complete new
allocation, zero-fills/copies in checked chunks and checks again before commit.
Only after replacing/dropping old storage is its ticket released. At 767->768
pages the two memories alone require 100,597,760 bytes; all other live state still
counts. Declared/host maximum denial returns Wasm -1. Allocation, combined/state,
cancellation, deadline or invariant failure is terminal, not a successful grow
denial. No trap-wide rollback of previous guest writes is claimed.

## Fixed runtime envelope and cumulative counters

`SwiftRunBudget` is a copied Rust-only narrowing budget. Each named dimension
narrows independently; zero is real, checked overflow/widening fails before
allocation, and no input accepts `Limits`, a policy identity or an import resolver.
Static grammar/ABI ceilings remain those proved by the accepted validator.

| Dimension | Default and maximum |
| --- | ---: |
| Adopted retained source / metadata | 64 MiB / 16 MiB |
| Cache, including construction and scratch / one entry | 16 MiB / 8 MiB |
| Cache entries / active pins | 64 /64 |
| Cache lifetime work | 64,000,000 |
| Live defined frames | 64 |
| Live values, locals plus operands / controls | 16,384 /4,096 |
| Memory host maximum | 768 pages |
| Mutable State category | 128 MiB |
| Combined all runtime categories | 256 MiB |
| Instruction fuel / execution work | 100,000,000 /1,000,000,000 |
| Executor entered host calls | 32,768 |
| Construction+initialize+all invokes cooperative lifetime | 30,000 ms |

`WasiBudget` independently narrows its unchanged maxima: 32,768 calls, 4 MiB
cumulative transfer, 32,000,000 work, 65,536-byte transfer/log bounds, 64 iovecs and
30,000 ms. Cache entry limit concerns decoded payload as currently specified;
slot/header/scratch remain additionally inside Cache. All Shared/Construction/
WASI fixed/scratch bytes are also inside Combined; the partition sum is not a
proof that Combined can never fail. Report measured headroom, not assumed fit.
Stop at the first failing ceiling and retain it for specific root review; never
silently raise any resource to make the target finish.

Fuel charges before each dispatched instruction; a call instruction pays once
for its imported call. Bulk-memory's existing extra fuel remains explicit.
Cache work charges both passes, scans, eviction planning and initialization;
execution work charges state initialization, descriptor/signature scans,
value/control movement, copies and growth. WASI work/transfer stay distinct and
are never counted as guest instruction fuel. Every counter is checked and
lifetime cumulative from construction through both calls; successful invocation
does not refill fuel, work, host, cache, transfer or deadline budgets.

## Deadline and cancellation inside every stage

Capture `started = Instant::now()` at constructor entry before cache/state/WASI
construction; derive one absolute run deadline using checked addition. Invalid
narrowing is rejected without runtime allocation. The validation deadline has
already ended and is reported separately. `RuntimeControl::check` checks the
shared cancellation token and absolute deadline. Work/reservation admission
checks it before work; bounded loops also check between chunks and after their
last chunk before publishing state.

The Swift decoder's reader byte/take paths, both passes, local expansion, patch
reset/write, index/slot/eviction scans, entry allocation and publication must use
that control inside their work. State construction checks inside memory zeroing,
global initialization, segment scans/copies, element decoding and arena setup.
Execution checks before every instruction/import, value/control movement and
each bounded bulk/growth copy. A giant decoder/body or constructor cannot run
under a deadline checked only by the caller around dispatch.

WASI needs a private `new_accounted(grants, budget, same_cancellation,
&mut RuntimeControl)` path. It admits each of its four buffers before allocation,
keeps the public standalone constructor and stored context layout unchanged, and
returns private reservation ownership beside the context. Its existing deadline
field is seeded with `min(run_deadline, wasi_start + narrowed_wasi_duration)`.
Thus the adapter's actual `check()` enforces the earliest deadline internally
before services, during staging/backup/commit and after services before effects
commit. No public caller clock/deadline setter or callback is introduced. Keep
the ordinary standalone constructor's timing and failure precedence exact.
WASI buffers are fixed after construction; its active dispatch needs no new
allocation. Preserve adapter rollback of the current interrupted commit without
allocation, extra work charge or further cancellation/deadline checks.

Deadline is cooperative. A single allocator/platform call cannot be preempted;
check immediately before and after it and record any overshoot. Do not claim
hard realtime, infer that an outer expired check protected guest output, or add
unbounded retries to a service. Production isolation/preemption is outside this
experiment.

## Closed WASI composition

Admission stays exactly the current public Swift proof: 34 ordered complete
Preview1 imports, no start, memory minimum 584 with no declared maximum and host
cap 768, fixed declared table 46,713/46,713, and exactly memory 0, `_initialize` 35
and `mixer_fieldlog_corpus_v1` 62 with their retained signatures. Small original
fixtures must use this same ABI and complete validator. With 34 imports they need
at least 29 defined functions to retain index 62; their code may be small but their
initial memory/table are still the real ABI sizes. No relaxed private fixture
policy or alternative public proof constructor is allowed.

A private compile-time host mode selects frozen legacy checkpoint/abort or the
Swift context only after matching its sealed owner. A Swift imported call reads
the sealed `WasiFunction` by absolute index, borrows the exact typed argument
slice from the value arena and disjoint mutable guest memory, and dispatches
synchronously to the internal context. No name reinterpretation, arbitrary
callback, guest-memory pointer escape, reentry or runtime capability negotiation
exists. The adapter's default-deny behavior remains unchanged for every function.
Grants are explicit; qualification grants random, realtime, monotonic and both
capture sinks. No paths, sockets, host environment or filesystem are granted.

The executor checks/charges its host-call counter before entering WASI. The
adapter independently charges actual entered calls and its own work/transfer.
Record attempted-but-rejected calls at the precise boundary; counts may differ
when the executor refuses entry. Preserve standalone WASI argument/budget/
authority/range/error precedence. `Errno` produces the official unsigned errno
encoded in one Wasm i32 and normal guest control flow. `proc_exit(u32)`, including
zero, is a sticky guest exit; it never pushes success or exits the native process.
Adapter failure terminalizes the instance with the exact underlying typed cause.

## Diagnostics and cleanup

Add Swift-only copied failure/usage types; do not widen existing public enums or
change old error categories. `SwiftRunFailure` carries stage, static code,
closed kind/resource, absolute function/source offset when present, attempted/
limit/observed capacity, selected deadline origin, cumulative cache/execution/
WASI counters and ledger current/peak snapshots. Distinguish invalid budget,
cancelled, deadline, allocation, source/metadata adoption, combined/category
exhaustion, fuel/work/host/pin/frame/value/control limits, decoder mismatch,
unsupported environment, guest trap, guest exit, WASI failure and invariant.
Keep original cache/WASI diagnostic details where relevant. No diagnostic
construction allocates or captures secure random bytes.

The first terminal cause is immutable. Later calls return it without decoding,
service, allocation or guest execution. A failure receipt has separate snapshots
at first failure and after cleanup; it must not overwrite the first cursor or
hide a transient peak. Terminal invocation cleanup drains every frame/pin and
clears live values/controls; their current counts become zero while owned memory,
cache and fixed arenas remain reserved until drop. Constructor failure drops
all ownership, reports zero live runtime reservations after cleanup, and retains
the failure/peak snapshots. Dropping a partially built frame after pin acquisition
releases that pin exactly once. Release errors indicate an invariant failure;
cleanup still drains the remaining owner and never replaces the first failure.

## Qualification and executable acceptance

Implementation acceptance is separate from permission to execute the exact
target. Root first reviews the shared seams, synthetic evidence, frozen-route
regressions and source isolation. The retained full reactor is not instantiated,
initialized or invoked until root explicitly approves that bounded attempt.

The qualification runner hashes the actual immutable target allocation with
standard cryptography and requires the exact size/SHA before validation. It
records input length and actual capacity, keeps input alive through validation,
then drops that external allocation before runtime construction. A borrow cannot
discover unrelated caller allocations. Report validation internal peak,
runner-input-plus-internal overlap and runtime simultaneous ledger peak as
separate quantities. There is no second retained source or eager module.

After complete proof acquisition and input drop, construct once with explicit
grants and fixed/narrowed budgets; record construction and `_initialize` phase
usage. Invoke the corpus twice on that same owner. Capture actual stdout/stderr
bytes and phase boundaries; parse two complete duplicate-free objects from
actual captured stdout, reject missing/extra fields/objects, and compare every
field and type to the retained native reference. Never print an expected object
as a substitute or accept only `status`. Required 11 observations are
`codableRoundTrip=true`, `committedEntries=1`, `completionBasisPoints=5000`,
`emptyTitleRejected=true`, `pendingChanges=1503`, `reordered=true`,
`repeatedCommitRejected=true`, `reportIncludesEntry=true`, `status="passed"`,
`taskCount=1000`, and `unicodePreserved=true`. Both actual return codes must be 0.
Node reference call counts/memory pages are development observations rather than
exact acceptance counts for the different bounded fd sink.

Required original executable evidence before target approval:

| Area | Required tests and observations |
| --- | --- |
| Authority | External compile-fail tests for forged/Clone/legacy proof conversion, bytes construction, arbitrary entry, memory/cache/pin escape, custom host/policy and downstream snapshot implementation |
| Decode/cache | Same-ABI fixtures; 512-control interpretation and accepted 379+ depth; all admitted op families; count/build agreement; exact entry/cache capacity; eviction, hits, all-pinned, 64 pins and per-frame ownership; work/cancel/deadline inside both passes |
| State/execution | Scalar/float/saturating, direct/recursive/indirect calls, full structural signatures, locals/globals, branching/br_table, ordered overlapping segments, memory load/store/size/grow/copy/fill, traps and repeated stateful calls; admitted original fixtures compared with frozen semantics/oracles where applicable |
| Initialization | Exactly-once marker and effects, empty result, zero live counts on Ready; every init trap/budget/cancel/deadline/exit path returns no Ready owner and does not retry |
| WASI | All 34 resolved descriptors, explicit denied grants, actual OS random/clocks, exact errno/result placement, capture bytes, logical fd close, path/poll denial, proc_exit 0/nonzero, default-deny, no native effects outside specified services |
| Shared ledger | Narrow total that fails before first runtime allocation; enough category room but insufficient combined room; cache construction while pinned/resident entries live; memory old/new overlap; source/meta/header attribution; WASI pre-allocation admission; exact current/peak and no pinned/source double count |
| Failure/cleanup | Every fallible allocation ordinal in constructor/cache miss/growth/WASI construction; requested/observed capacities; failure immediately after pin acquisition, recursive return/trap, indirect error and all terminal causes; no leaked pins/live counts, cleanup allocation/work/service-free even when cancelled |
| Deadline/fuel | Expire within cache scan/build/reset, zeroing/segments, growth, WASI staging/service/commit; earliest runtime deadline beats later WASI deadline and vice versa; overshoot recorded; cache/execution/fuel/host/WASI budgets accumulate through init and both calls |
| Frozen regressions | Default, stream/cache, span execution, standalone WASI and all-feature Debug/Release tests; external API compile checks; focused lint; layouts plus usage/counter/error snapshots unchanged for frozen routes even with Swift enabled |

Tests use independently authored source/fixtures and project-owned code. No
Patch/Skip implementation, source, tests, dependencies or third-party execution
engine is imported. Official platform tools/specifications are permitted.
Qualification receipts bind source-file hashes/tree manifest, revision plus
dirty state, compiler/tool versions and hashes, complete commands/output,
artifact/proof/runtime identity, budgets, phase counters, reservations, cleanup
and exact observation comparisons. A failed attempt keeps the first failure;
it is not rerun with raised caps without specific review.

## Proposed bounded implementation lanes

Root approves contracts and assigns ownership before dependent edits. These are
future lane boundaries, not current authorization:

| Order / owner | Bounded work and files |
| --- | --- |
|0 / root | Freeze private snapshot/control/ticket/diagnostic contracts; expose only necessary Swift borrowed descriptors; Cargo/lib wiring and any private cancellation-layout helper; own existing validator source and proof layout preservation |
|1 / cache lane | `experimental/cache` borrowed algorithms and Swift-only cache/decode module; exact legacy stored-layout preservation; original same-ABI cache/authority tests and receipts; depends on root's borrowed proof/control seam |
|1 / WASI lane | Private accounted construction, carried existing deadline and private reservation owner in `experimental_wasi`; preserve standalone surface/layout/counters; seam tests and receipts; depends on root control seam, independent of cache code |
|2 / runtime lane | New Swift control/ledger and private execution composition after root assigns those files, plus borrowed execution adapter extraction in `experimental/execution`; fixed arenas, one-pin frames, typed lifetime failures and same-ABI synthetic execution evidence; no cache/WASI lane file edits |
|3 / root and independent review | Integrate lanes, inspect source isolation and complete old-route regression evidence; approve or reject one bounded exact-target runner attempt; own status/work graph/gates and commits/push/CI |

For actual parallel dispatch use the repository-required fresh `gpt-6.1-sol`,
`xhigh` agents with bounded ownership. If extraction needs another lane's files,
coordinate before editing. Do not sweep unfinished work into commits. No target
execution, production publication, customer messages, destructive migration,
credential change, new device discovery/run or request to reconnect phones is
implied. FieldLog must later consume immutable published packages from another
repository; this local experiment, even if successful, cannot qualify dogfood,
product size/performance, physical iOS/Android or a GA gate.
