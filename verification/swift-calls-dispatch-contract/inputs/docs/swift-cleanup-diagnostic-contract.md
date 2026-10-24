# Private Swift cleanup diagnostic contract

The accepted 127-file memory-growth baseline has a reproducible attribution gap:
an actual pinned invocation has a real function and decoded instruction offset,
but a post-pop live-count underflow reports `Cleanup` with no function, offset or
resource. This packet diagnoses that gap and proposes the smallest bounded
repair contract. It contains no implementation candidate, live VM change or
implementation authorization. Root must review this contract before a repair.
G08 and product-plan section 10 remain open.

The authoritative baseline is the archive and manifest accepted by
`verification/swift-memory-growth-root-integration/acceptance.json`, closure
`a0bbe77aca3021e48f1fb76dc97cfbc0406c24e5ba7eacdd33d5dabe8f998d9b`.
Git revision is context; source bytes are the authority. The audit retains that
archive, all 127 hashes, commands, exact executable identities and full test
lists under `verification/swift-cleanup-diagnostic-contract/`. Its only probe
overlay appends tests to two isolated test modules. No production line differs.

## Observed failure and original authority

`control.rs:1605` accepts the actual `Live` resource and amount but no cursor.
Its checked subtraction calls `cleanup_fault_with_wasi` on underflow. That method
sets the first cleanup-invariant latch and calls original `RuntimeControl::fail`
with a freshly constructed cursor whose stage is `Cleanup` and whose function
and offset are `None`. `Fault::new` leaves resource absent and attempted/limit
zero. The actual resource mapping already exists in `live_parts`; the removal
method discards it. The first diagnostic has therefore lost context before any
wrapper receives it.

The narrow probe executes the existing actual-pinned Load caller, not a copied
interpreter. It uses the original strict reactor proof, owner/cache/pin/frame,
real 584-page State memory, WASI adapter and existing disabled-default post-pop
fault selector. The caller obtains function 34 and absolute Wasm offset 1713
from that retained pin, sets `operation.cursor`, charges the existing
instruction/fuel/work boundaries and advances PC. The original value primitive
then consumes its one real address. The existing hook makes its original live
removal reject. Output is:

```text
actualFunction=34 actualOffset=1713 actualStage=Invocation
reportedStage=Cleanup function=None offset=None resource=None
code=swift_run_live_underflow attempted=0 limit=0 wasiCalls=1
postPopValues=0 firstFailurePreserved=true atFailurePreserved=true
afterCleanupAdded=true debtRetained=true
```

This is a synthetic host fixture reproducing a defensive invariant failure;
it is not an observed FieldLog production fault. Five existing tests and three
new probe groups pass in fresh all-feature Release unit contexts. The baseline
binary lists 249 tests and executes the five exact selected tests; the probe
lists 252 and executes its three exact selected tests. No full suite or feature
matrix is implied by this diagnostic audit.

The existing semantics are correct and binding:

- `RuntimeControl::fail` returns the already stored `first_failure` unchanged.
  It creates a new failure only when that slot is empty. No wrapper may fill in
  function/offset/resource on a returned failure after this boundary.
- The cleanup-invariant latch uses `get_or_insert` independently of the first
  terminal cause. A later underflow can set that latch without replacing an
  earlier invocation trap. The earlier `at_failure` must retain its original
  cleanup-invariant value, WASI observation, counters and elapsed observation.
- A new underflow sets its invariant latch before `fail` captures `at_failure`.
  Counts are not changed when `checked_sub` fails. The arena pop/truncate that
  already happened is not undone. The caller's existing debt latch remains
  responsible for preventing a clean completion.
- `record_cleanup` changes only `first_failure.after_cleanup` to a fresh actual
  usage observation. It does not replace the diagnostic or `at_failure`.
  Whole-value equality against a pre-cleanup copy is the wrong post-cleanup
  oracle; compare every original field while permitting that one distinct
  observation to change.
- Removal/refund/cleanup remains independent of new cancellation, deadline,
  fuel, work and admission checks. Owner/pin/ticket retention and explicit
  cleanup reacquisition remain unchanged.

The independent cursorless probe executes all six actual `Live` kinds with zero
current count and an attempted removal of one. All keep `Cleanup` and absent
function/offset/resource without changing any live count. A separate probe
creates an earlier invocation trap, then causes a real original-control removal
underflow: the returned trap and `at_failure` stay identical and only
`after_cleanup.cleanup_invariant` exposes `LiveUnderflow`.

## Exact callsite classification

Locations below refer to the frozen accepted baseline, not a later shifted
working tree. The machine-readable inventory is `callsite-inventory.json`.

| Original source site | Actual scope and cursor availability | Proposed first repair |
| --- | --- | --- |
| `value_operations.rs:566`, `primitive_pop` | Active pop; actual `operation.cursor` is already held, before/after pop ordering fixed | Pass that cursor to contextual removal; all callers share this original primitive |
| `value_operations.rs:631`, `primitive_numeric` | Active numeric reconciliation after the shared arithmetic body; actual operation cursor exists | Pass that cursor; preserve original removal-before-numeric-result failure precedence |
| `value_operations.rs:649`, `primitive_clear` | Fixed value-phase completion clears the arena, potentially with an old operation cursor still in the struct | Preserve cursorless cleanup; the stored cursor is not evidence of a currently executing instruction |
| `control_operations.rs:259`, `control_remove` | Active shared control leaf, invoked after original value/control pop or truncate | Pass current actual operation cursor; keep existing unreconciled-debt latch |
| `frame_operations.rs:671`, `remove_live` | Shared by active finish, failed-entry rollback and terminal drain | Preserve existing helper for cleanup; add a separate active-finish helper with explicit cursor and identical debt behavior |
| `frame_operations.rs:811,813,832`, `finish_inner` callers of that helper | Active completion of current guest function; original caller cursor exists | Use the active-finish helper for Values, Controls and Frames; never use the removed frame PC as a substitute |
| `frame_operations.rs:714,727,737`, rollback callers | Failed-entry cleanup; no new currently executing instruction is established | Keep original cursorless helper |
| `frame_operations.rs:923,926,941`, drain callers | Terminal cleanup and explicit cleanup retry; operation cursor may be stale | Keep original cursorless helper |
| `cache.rs:1235`, `CacheControl::remove_live` | Shared cache release, pin abandonment, failed build rollback and eviction; wrapper can have a cache/construction cursor or `cache_cursor()` | Preserve unchanged in this first repair; do not infer an invocation from a cache wrapper or a frame function |
| `cache.rs:1449,1470`, cache cleanup | Actual owner cleanup of pin and resident inventories | Keep original cursorless removal |
| `execution.rs:1700,1811` | Consuming State memory cleanup and partial-construction cleanup | Keep original cursorless removal |
| `memory_growth_operations.rs:115`, `release_pending` | Drop/refund of uncommitted pending memory; reused by explicit cleanup; phase cursor can be stale | Keep original cursorless removal, even when called during an invocation failure |
| `control.rs:1602`, `remove_live` wrapper | Explicit no-WASI cleanup convenience | Keep existing behavior and signature |

`CacheControl::remove_live` reaches `ReleaseControl::release_pin`,
`SwiftMeter::abandon_pin`, failed `SwiftMode::build` rollback and
`SwiftMode::drop_entry`. `SwiftFunctionCache::release` constructs a
`cache_cursor()` itself, even if active `finish_inner` initiated the release.
Changing that shared adapter would require a separately reviewed explicit
release-cursor seam and all cache rollback/drop/release accounting. This audit
does not authorize it or promise source attribution for such cache failures.

Related original cursorless cleanup faults are also intentional here:
`end_construction_phase_with_wasi` emits missing-construction,
construction-owner, phase-bound and release-underflow faults
(`control.rs:1125,1132,1140,1154`); `refund_with_wasi` emits release-owner and
release-underflow faults (`1320,1334`). They operate after actual storage drop
or at phase/owner cleanup. A nearby/stored invocation cursor is insufficient
evidence for attaching one. Original `check_reservation_owner` and construction
preflight already accept an explicit real caller cursor; do not change them.

## Proposed private API and failure boundary

Keep `remove_live` and `remove_live_with_wasi` signatures and observable cleanup
behavior. Add exactly one private contextual entry:

```rust,ignore
pub(crate) fn remove_live_at_with_wasi(
    &mut self,
    resource: Live,
    amount: usize,
    cursor: Cursor,
    wasi: Option<WasiUsage>,
) -> Result<(), SwiftRunFailure>;
```

Root selected a narrower implementation direction after reviewing the draft:
preserve the entire existing `remove_live_with_wasi` body byte-for-byte and add
the contextual entry alongside it. The new entry uses the same original
`live_parts(resource)`, `current.checked_sub(amount)` and `live_mut(resource)`
primitives directly. The tiny duplicated successful subtraction is preferable
here to factoring a common body that changes every old cleanup/foundation path
and its canonical MIR. Independent tests must compare both entries for all six
resources. The historical baseline and existing packets remain unchanged.

The copied cursor is a transient diagnostic input. It grants no authority and
is not stored in RuntimeControl, State, cache, frame, pin, ticket or completion
storage. No `Option<Cursor>` core, new public type/field, alternate controller,
diagnostic ledger or dependency is needed. A common-body refactor is outside
this selected first repair.

The new entry observes the actual `live_parts(resource)` tuple and performs its
one `current.checked_sub(amount)` computation. On success it writes exactly
that result to the same original live count. It performs no ordinary check and
no work/fuel/admission/allocation/pin/PC operation. On underflow:

1. Set the existing independent `LiveUnderflow` latch with `get_or_insert`.
2. Call original `fail` immediately using the exact supplied
   cursor and an Invariant `swift_run_live_underflow` fault. Its resource is the
   exact existing `live_parts` mapping for the supplied `Live`; attempted is the
   actual requested removal amount and limit is the actual removable current
   count, both in that resource's count units. This limit describes current
   availability, not the configured live ceiling. Preserve exact representable
   values on qualified targets. Leave observed-capacity/WASI-failure/guest-exit
   absent as today.
3. Return exactly what original `fail` returns. If a first failure already
   exists, it wins in every field, including its prior resource and snapshot.

The separate unchanged old entry retains stage Cleanup, absent function/offset/
resource, zero attempted/limit and its actual optional WASI observation. It does
not call the new entry. Neither entry gains a new ordinary check.

The caller must have established that cursor from the current actual retained
pin/selected decoded instruction before effects, as already required by the
accepted private callers. Preserve its stage and each optional field exactly;
do not synthesize missing values, infer a current offset from an advanced PC,
borrow a callee's entry offset, retain a cache view through mutation, or map a
host/cursorless cleanup to Invocation. Direct private test helpers with a
synthetic cursor do not establish original-source execution evidence.

Add a private `FrameOperationPhase::remove_live_at` helper (or an equally explicit
name) used only by the three active `finish_inner` removals. It must pass the
actual current `self.phase.operation.cursor`, preserve the existing bool result
and sticky `cleanup.live_unreconciled` behavior, and introduce no new preflight
after the already visible truncation. Leave `FrameOperationPhase::remove_live`
and every rollback/drain caller on the old cleanup route. The control helper and
two active value primitives call the new RuntimeControl entry directly. This is
the complete first implementation scope.

Do not append source data to an error in `control_pop_value`, memory/bulk/growth
wrappers, host wrappers, stored-result slots, `terminal`, `drain`, `complete`,
`record_cleanup`, logging or a public display layer. Those positions are after
the first-failure boundary and cannot safely correct the original snapshot.
The concurrent host-operation candidate must retain baseline behavior until an
independently reviewed implementation is integrated; its future pops inherit
this seam through the original value primitive, without a host-local rewrite.

## Accounting, layouts and Frozen contract

This is an API proposal, so no new byte totals, changed layout identity or
canonical-MIR replay are claimed. The repair's producer must inventory the
actual final source rather than assuming that a small Rust edit is free:

- Four distinct positive source/argument/returned/caller positions for each
  new cursor transfer, `Live` and amount copies, optional WASI
  observation/reborrow, contextual-method call/return, exact resource mapping,
  usage/current/checked-sub Option and branch result, independent latch result,
  Fault construction/limit fields, existing `fail` receiver/return and every
  Result/Try/residual/returned failure. Include aliases, typed literals,
  compiler-promoted constants, closures and changed reborrows from final MIR.
- Every changed caller gets its own positive additions. `primitive_pop` and
  `primitive_numeric` affect the value envelope used once by frame/control/
  memory/bulk/growth and future host operations. `control_remove` and its
  expanded shared leaves affect the control active inventory. Active finish's
  new helper affects frame accounting. The old fixed completion/storage and
  retained diagnostic positions are already occupied and supply no credit.
- Preserve old cleanup/foundation path source and canonical MIR unchanged.
  `FinalFaultInventory` and `FOUNDATION_FINAL_BOUNDARY_BYTES` remain obligations,
  not spare credit for the new method. Charge the new contextual method in each
  relevant active caller envelope and retained diagnostic position. A producer
  must prove those changed methods are called only after their existing
  envelope admission. If an unexpected old-path/foundation change is needed,
  stop and reopen this selected contract before widening it. Propagate the
  actual relevant nested/outer admission/restoration formulas. Existing
  per-path authored/MIR reservations must remain positive and preserved.
- Use additive measured inventory types with checked formulas. Preserve original
  ticket ownership and the maximum 86 tickets, State 128 MiB and Combined
  256 MiB ceilings. No new ticket, owner field, heap allocation or shadow
  accounting is authorized. Value active bytes remain counted once; do not add
  them once per memory/control/bulk/growth consumer or borrow unrelated padding.
- The expected concrete owner declarations remain byte-identical: RuntimeControl,
  SwiftRunFailure/Usage/Cursor, SwiftReactorInstance/Lifecycle, State, frame,
  entry guard/cleanup state, cache/pin/ticket, WASI, operation phase/parts and
  fixed storage/completion shapes. Measure every containing inventory, actual
  owner size/alignment/offset, header and frame/foundation/constructor envelope
  across Swift-only/all, Debug/Release, production/unit. Any unexpected owner
  layout change reopens the contract; expected sameness is not measured proof.

Do not edit the shared arithmetic/control/memory/call algorithms merely to carry
this diagnostic context. Existing static Swift leaves can call the contextual
primitive without changing their Frozen leaf. Reproduce all 39 Frozen expanded
`SpanInstance` methods byte-for-byte, the original 2,912-byte reservation, and
Frozen runtime parity. Frozen's historical terminal diagnostic rewrite remains
its separate behavior; Swift must keep immutable `at_failure` and separately
observed `after_cleanup`.

## Required implementation and independent review evidence

The proposed producer matrix is in `repair-acceptance-matrix.json`. It is pending,
not satisfied by the baseline probes. Execute it in Swift-only/all-feature
Debug/Release, serial allocator observation, fresh source/features/profile/
production-unit contexts, exact test names/counts and retained binary hashes.
Original tests with historical absent-attribution expectations must be retained
in old packets; future live expectations change only for the explicitly active
contextual routes. Do not rewrite any historical proof.

The behavior matrix must establish contextual failures for an actual pinned
control pop, Load and Store, bulk memory and MemoryGrow pop, numeric
reconciliation, active control truncation and each active frame-finish removal;
all six exact Live/resource/count mappings; success and zero removals; unchanged
post-effect/work/fuel/PC prefixes; earlier-first-failure preservation; actual
nonzero WASI usage; cursorless cleanup/rollback/refund controls with a deliberately
stale stored cursor; retained original pins/tickets/debt; repeated drain,
explicit cleanup reacquisition, fixed completion and consuming-owner barriers;
and allocation refusal. Use finite fault hooks only where an actual defensive
underflow cannot otherwise be induced; they must exercise the original
primitive, be disabled by default and have separately measured unit accounting.

Independent review must reconstruct the candidate from the accepted baseline,
audit every exact callsite selection, add at least one different actual-pinned
body/offset and nested frame, verify every original diagnostic/`at_failure`
field against copies across cleanup, replay final canonical MIR and metadata,
and reject broad cleanup attribution or after-the-fact diagnostic mutation.
Compiler checks, formatting and scoped Clippy are required. Existing broad
Clippy failures must be compared by diagnostic identity if that scope is run.
Root reviews source delta and receipts before live integration. No regex-only
source test, compile-only witness or agent assertion can authorize a release.

This first repair would restore truthful current Wasm invocation attribution for
the named routes. It would not supply original Swift file/line mapping, readable
Swift stacks, module IDs, debugger transport or all compiler/bridge/native
failures demanded by section 10.4 and G08. A Wasm offset alone remains
insufficient. No existing source map or module identity is guessed into this
contract; those need their own actual compiler/runtime/source-map evidence.

## Audit replay and cleanup

Run `python3 -B verification/swift-cleanup-diagnostic-contract/verify.py` for the
sealed offline audit. `collect.py` is a one-time fresh collector and refuses to
overwrite its completed receipt. It records full argv, cwd, tool versions,
selected environment, source manifests before/after, raw output and command
process-group cleanup. The two exact binaries and source archives are retained;
targets were never shared between baseline and probe.

All newly owned command groups ended with zero surviving members. The sole
scratch root contained 276 files / 20,116,567 bytes, had zero open holders, and
was removed. No native/UI/emulator/simulator/physical device, discovery,
publication, external message, credential operation, Git mutation or tracker
edit occurred. Other projects' processes and instances were preserved. Full
Swift/public/native/FieldLog immutable separate-repository release, final phones,
signing/store/customer/operational and GA gates remain pending.
