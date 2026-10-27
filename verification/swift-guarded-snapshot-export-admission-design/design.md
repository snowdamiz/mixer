# Guarded snapshot admission proposal

Status: **proposal for separate review and root selection**. No exporter, wrapper,
new admission profile, grant, or canonical change is implemented by this packet.
The finite Python controls execute a synthetic state machine. Three Rust
compilations measure prototype types and check access to actual private fields;
one negative compilation checks immutable guard access. None runs a native guest.

The only owned directory is this packet. Released inputs and the 144-member
accepted source remain immutable. `input-custody.json` verifies all four released
seals and every member; it does not rerun their commands. Accepted tree is
`9fbdabbc5122f71809483b3b0a0e95a71b9813def61572f366bcebc8ac6d08fb`, revision
context `606c42876855897c315ee279dcd38fabaeb561ad`. Contract format corrections
R1/R2/R3 belong to the separate correction lane and are not duplicated here.

## 1. Source facts and failure boundary

Paths below are relative to the frozen `inputs/accepted-source/vm/` in the
preparation packet, not a changing checkout:

| Source place | Binding fact |
| --- | --- |
| `src/experimental_swift_reactor/control.rs:401` | Actual control owns owner, budget, started, earliest carried deadline/origin, actual Cancellation, original counters, first_failure and three sealed tickets. |
| `control.rs:891..948` | `check`, `check_with_wasi`, `work` and `fail` are terminal paths. Both current cancellation and current deadline can install first_failure. They cannot implement export-only refusal. |
| `control.rs:1435..1484` | Original work counters are CacheWork and ExecutionWork. Checked addition, not a newly minted allowance, bounds work. |
| `control.rs:1110..1218` | Existing construction enlargement calls terminal check/preflight/fail. Existing consuming phase retirement destroys storage before reducing the same ticket. |
| `control.rs:1743..1805` | Final owned cleanup accepts only the exact original foundation; an enlarged unconsumed phase remains charged. |
| `control.rs:288..301` | ReservationTicket has only owner/category/bytes, no clone or independent ledger. |
| `cache.rs:268..281` | Actual cache owns adopted body, original owner, fixed header and three buffer tickets. |
| `cache.rs:1473` | Existing generic `prepare<'a>` is the original shared construction entry. It is not absent. |
| `cache/initial_profile_v1.rs:125..171` | Original early outcomes, complete/inspect, sole guard, header, rows are ordered here. |
| `cache/initial_profile_v1.rs:187..247` | Original inspect verifies actual owner/layout/freshness, before any guard. |
| `experimental_wasi/accounted.rs:19..24,123..150` | Actual context/buffer/header ownership is private; checked_usage is terminal on pairing violation. |
| `execute.rs:9..15` | Actual cancellation read is `&self` and one AtomicBool load. Cloning a handle is unnecessary. |
| `retained_profile_loader_v1.rs:142..169` | Only the loader creates selected AdoptionBody; selected provenance stays opaque and non-Clone. |

The prototype's ticket helper proves private access/signature feasibility only.
It is **not yet the full pairing algorithm** below. In particular it does not
establish expected cache/WASI buffer layouts or perform actual conditional
enlargement. The full writer and its source-place closure remain absent.

## 2. Private types and sole authority route

Proposed modules are the existing original `control.rs`, actual
`AccountedWasi` implementation, existing private initial-profile wrapper, and
`experimental::swift::snapshot_export_v2` inside the validator's privacy boundary.
All new fields/constructors are private. No new public application API is added.

```rust
// control.rs; separate from SwiftRunFailure and original first_failure.
enum SnapshotStopV1 {
    Existing(SwiftRunFailure), // exact copy of actual original value
    Cancelled,
    Deadline(SwiftDeadlineOrigin),
}
enum SnapshotAdmissionErrorV1 {
    Stop(SnapshotStopV1), Owner, Layout, Arithmetic,
    Work { used: u64, requested: u64, limit: u64 },
    Storage { current: usize, additional: usize, limit: usize },
}
struct SnapshotWorkDebitV1 { credits: u64 } // observation, never a spendable grant
struct SnapshotPlanV1 {
    counts: [u64; 8], source: u64, words: u64, extent: u64, blocks: u64,
    planning_debit: u64, emission_debit: u64,
}
struct SnapshotPhaseV1<'c> {
    control: &'c mut RuntimeControl,
    previous_bound: usize, // captured from actual same ticket, no caller setter
}
enum SnapshotExportAttemptV1 {
    NotReached,
    AdmissionRefused(SnapshotAdmissionErrorV1),
    Attempted(Result<SnapshotExportObservationV1, SnapshotExportErrorV1>),
}
struct InitialProfileWithSnapshotV1 {
    primary: InitialProfileConstructionOutcomeV1, // original enum untouched
    snapshot: SnapshotExportAttemptV1,
}
```

These are proposed signatures, not implemented working entries:

```rust
// Only called from the actual cache/wrapper path after full immutable pairing.
RuntimeControl::observe_snapshot_stop_v1(&self) -> Result<(), SnapshotStopV1>;
RuntimeControl::debit_snapshot_work_v1(&mut self, credits: u64)
    -> Result<SnapshotWorkDebitV1, SnapshotAdmissionErrorV1>;
RuntimeControl::begin_snapshot_phase_v1<'c>(&'c mut self,
    cache: &SwiftFunctionCache, wasi: Option<&AccountedWasi>)
    -> Result<SnapshotPhaseV1<'c>, SnapshotAdmissionErrorV1>;
SnapshotPhaseV1::complete<T>(self, actual_temporary_storage: T)
    -> Result<(), SwiftRunFailure>;

// A private cache method derives shape from its own adopted proof observations.
SwiftFunctionCache::plan_snapshot_v1(&self, phase: &mut SnapshotPhaseV1<'_>)
    -> Result<SnapshotPlanV1, SnapshotAdmissionErrorV1>;

// The authentic guard remains the sole export entry; no raw proof argument.
fn export_snapshot_v2(initial: &InitialProfileBorrowV1<'_>,
    plan: &SnapshotPlanV1, output: &mut File, actual_row_output: &File)
    -> Result<SnapshotExportObservationV1, SnapshotExportErrorV1>;
```

For Rust privacy, `begin_snapshot_phase_v1`'s full cache-field inspection must
be split: the cache child checks its actual private fields and calls narrow
control methods for the adopted/ticket/construction internals. A sibling
`control.rs` method cannot read private cache fields. The prototype uses exactly
this split; it does not pretend that direct sibling field access compiles.
`AccountedWasi` needs crate-private narrow ticket checking because it is a sibling
of the reactor, not a child; fields/constructors remain private. Its accessor
reads `self.context.budget` and `self.context.grants`, never caller copies.

Plan counts authorize nothing: under the sole guard the validator-private bridge
rederives all eight Buffer lengths/capacities/charges, complete scalar state,
actual selected provenance and actual runtime/WASI data; it rejects disagreement
with the precharged shape. No second proof, guard, callback, cancellation handle,
owner increment, reentry, digest-to-proof route or unsigned deserializer exists.
The ordinary selected-missing path remains an ordinary adoption; export refuses
MissingSelected. No raw proof argument is an exporter entry.

## 3. Admission sequence and unchanged original outcomes

1. Reserve the recommended authentic selected scope's full named ingress/outer-
   return/cleanup places in the **original foundation before those objects
   exist**. Section 4 defines the one recommended proposal and rejected options.
   Root selected the proposal direction for review, not implementation/budget.
   Output File acquisition/close/name obligations require a separate admitted
   operational owner. A named preexisting borrowed File does not close that gate.
2. Run original SlotOccupied, exact selection, original prepare, construct,
   completion and inspect in their original order and with their original typed
   returns. Outcomes 1..7 retain `NotReached`; snapshot work is not attempted.
3. Immediately after successful `inspect_initial_v1`, before the existing sole
   guard literal, attempt the conditional snapshot phase. It enlarges the same
   original construction ticket only on successful **nonterminal** preflight.
   Full encoding/writer/bridge temporaries are conditional on this admission.
4. For phase admission, inspect existing first_failure first, then full actual
   owner/ticket consistency, then cancellation, then actual current deadline.
   Refuse missing/corrupt/foreign owners independently; do not call any terminal
   owner helper to obtain a diagnostic-only failure. Existing failure is copied
   exactly, never fabricated. On refusal set pending export AdmissionRefused and
   continue the original sole-guard/header/rows path without export.
5. Successful phase admission precedes creation of SnapshotPlan, fixed headers,
   IO results, metadata/seek state or reusable transfer buffer. First debit the
   fixed planning cost. Only then derive source extent and eight logical counts
   from actual same-cache proof observations. Compute the checked formula in
   section 5 and debit the remaining emission allowance before creating guard.
   Failure leaves successful earlier planning debit consumed, with no refund.
6. Create the original `InitialProfileBorrowV1` once at its existing literal.
   If admitted, attempt export once through that guard. Retain its own result.
   The actual File metadata/identity/seek/write checks occur after admission.
7. Call original header encoder, then original row writer if header succeeded,
   even when export admission, metadata, seek, write, attempts, cancellation or
   deadline observation failed. Original header refusal still skips rows. No
   new mutable control access or ledger operation occurs under the live guard.
8. End guard/views/iterators and File borrows. Preserve the original primary
   payload, export result, and phase cleanup result separately. Consume the real
   admitted temporary storage through phase complete; retained outer/error/
   return objects are still charged in the selected shell. Final original cache,
   adopted-proof, WASI and control cleanup follows its original consuming path.

Original enum discriminants 1..8 and every inline owner/error/header/row payload
remain unchanged. No Snapshot error becomes SwiftRunFailure, HeaderRefused,
completion, or original cleanup failure. The original cache slot stays caller
owned. No snapshot failure reruns prepare/construct/acquisition or returns a
ticket. All first-failure state before an export-only failure remains equal.
Success precharge intentionally changes original ExecutionWork usage, separately
attributed by the debit observation; this is not a promise that all later usage
snapshots are byte-identical to a no-export run.

An original HeaderOwnerCheckFailed arises before export admission/debit and
therefore retains its exact original typed failure. Header/refused/row behavior
is preserved only if File alias rejection in section 7 is implemented. Source
analysis and the Python outcome model are not all-eight actual wrapper tests.

## 4. Recommended authentic scope and real foundation tradeoff

The original accepted foundations are 366,896 unit and 366,312 production bytes.
Original 300,000 refuses; historical 400,000 is refusal-path evidence only. No
new floor or positive fixture grant is selected by this document.

The concrete prototype shell is 29,256 bytes in **unit, ordinary-production
Debug and optimized** compilations on the selected aarch64 Apple target. It is
an executable conservative candidate, not a globally minimal bound or a final
implementation measurement. If this exact shell were selected without other
changes, arithmetic would be 396,152 unit /395,568 production bytes. Actual new
entry/borrow/cleanup inventory changes can add to this. No exact-floor positive
behavior follows from these arithmetic figures.

**Recommended proposal: authentic selected adoption scope.** Add an opaque
`SelectedValidatedProfileV1::adopt_for_snapshot_scope` which moves the sole
actual selected body into a narrow control entry. Refactor original `adopt_body`
through one private shared admission core with an unexported
`FoundationProfileV1::{Original,Snapshot}`; only this selected entry may choose
Snapshot after confirming authentic `body.selected_provenance().is_some()`.
Ordinary `adopt` and existing selected ordinary adoption choose Original. Their
existing signatures remain compatible. No
caller bool, arbitrary bytes, raw proof/digest or claimed floor selects a mode.

Return an opaque `SnapshotAdoptionScopeV1` that **owns the original control and
adopted owner**, with private fields and no owned-control extraction. Its methods
borrow that control and its later same cache. It retains shell/profile authority
by actual scope ownership, not inside a new RuntimeControl field or by guessing
from ticket.bytes. Its finalizer must consume the actual shell/result/cleanup
storage and use the original `end_construction_phase` to return the original
ticket to the captured original base before unchanged `finish_owned_cleanup`.
An unconsumed scope cannot call final control cleanup or extract the control.
Source-visible shared-core enum/entry/Result/move places are concretely proposed
in `prototype/profile_append.rs` and measured in `profile-layout-result.json`.
That probe checks the unchanged original adopt_body function type and measures
the new private profile/owned scope/common adapter objects; it does not implement
the refactored admission or execute scope finalization. An unchanged
RuntimeControl layout does not prove zero common admission overhead. No zero-
overhead claim is made. Original floor equivalence is an acceptance test, not an
assumption. The selected-scope ingress itself must be covered in its profile
before its return/caller storage exists.

The fresh common-core candidate delta is **8,536 bytes** in unit, production
Debug and optimized builds. The private profile selector is 1 byte/alignment 1;
actual AdoptionBody=1168, SwiftRunBudget=136, Instant=16, Cancellation=8, original
adoption return=2936 (all those align to 8). The delta deliberately counts two
body/budget/Instant/Cancellation argument/move sets, profile plus alignment, and
two original typed Result handoffs. This is the exact compiler size of the
proposed additional inventory; original inventories remain charged. It is not a
proof that 8,536 is unavoidable or minimal for all possible core refactorings.
If selected unchanged, the Original profile base would be 375,432 unit /
374,848 production rather than 366,896/366,312. That ordinary acceptance and
failure-attempted-byte change is explicit; it is not byte-identical original
adoption behavior and needs review/root acceptance. The original eight wrapper
outcomes and original policy ceilings do not change. This packet selects none
of these numeric foundation changes or host grants.

The opaque owning scope is **5,984 unit /5,936 production** bytes (alignment 8);
the 48-byte unit difference follows the actual test-configured owned component
layouts. The concrete snapshot shell stays 29,256 in all three builds. Scope
argument/Result/Option/owned handoff/finalizer places and the actual encoding
closure still require exact final source measurement. Do not call the partial
sum (410,672 unit /410,040 production for original+common+one scope+one shell)
a complete required floor; there are still unmeasured selected-only places and
the conditional live envelope. Do not use it for a positive grant.

There is one shared admission implementation. Original adopt_body forwards the
actual body/budget/started/Cancellation to private adopt_core with Original. The
narrow selected snapshot entry forwards the authentic selected body with Snapshot.
The original core's budget/owner/admitted-source/metadata/control/cancellation/
construction operations retain their existing order. Each profile's foundation
is computed before its branch's return/caller objects exist. No second ledger,
owner, cancellation backing or alternate construction ticket is introduced.
The common-core adapter delta is admitted in **both** profiles; it cannot be
funded after a return/argument move. Full shell, scope, selected entry/return/
move/cleanup and full encoder storage remain selected-only. All checked const
sums must derive from exact final source places, not merely these prototypes.

After successful original inspect, the conditional live phase borrows the scope's
original control, captures the actual current construction bound, and enlarges
the same ticket for the remaining live exporter temporaries. Phase retirement
returns to that captured scope foundation. Scope finalization later consumes the
actual outer/result/cleanup objects and returns to the Original profile base
(including admitted common-core delta), then unchanged single-floor finish runs.
The captured base is private construction data, never a caller argument. No
method returns an owned control or permits final cleanup before consuming the
scope storage. Actual scope-local adopted/cache/WASI slots retain owners on all
eight original branches; passing arbitrary T/unit instead of typed actual
retirement storage is not an exposed scope finalizer.

**Rejected full-shell global design:** charging all 29,256 shell bytes to every
ordinary owner would avoid a profile, but imposes unnecessary permanent ordinary
overhead. Root explicitly prefers the authentic selected scope. The measured
shell remains useful for accounting the selected scope, not a selected global
foundation change. A common-core overhead may remain; it must be measured and
reported rather than conflated with this rejected global shell.

**Rejected shortcut:** change finish to accept either old or new constant if
construction.ticket.bytes matches one. Any unconsumed enlarged phase could
coincidentally equal the alternate constant, producing false zero cleanup.
Ticket.bytes is mutable accounted extent, not an authenticated mode. C02 retains
this mandatory negative. Changing category or reusing owner bits to encode a mode
would also change existing contracts; neither is proposed.

The phase's fallible **storage** admission cannot use existing
`enlarge_construction_with_wasi`, `preflight_bytes`, `check_reservation_owner` or
`fail`. Its private nonterminal implementation must check: existing failure;
same nonzero owner; existing construction category/extent/live-ticket and exact
current construction charge; checked current+additional; both category and
combined limits; current cancellation/deadline. Only then commit ticket.bytes,
construction.current/peak, combined.current/peak together. Live-ticket count,
other categories, first_failure and cleanup_invariant are unchanged. Any refusal
leaves all ledgers unchanged. These are the original ledger fields, not an
observational parallel ledger. Actual corruption remains diagnostic admission
refusal now; later genuine original consuming cleanup still records its real
invariant through the original cleanup path.

## 5. Explicit checked work contract

Use original **ExecutionWork**; cache compilation work remains CacheWork. A
credit is a documented bound on source-level logical work, not CPU time or RSS.
No additional budget field/grant/refund is introduced. Default original
ExecutionWork limit is 1,000,000,000, and existing narrowing-only ceilings stay.

The planning debit is `P=16,384`. Its implementation must remain a fixed-size
operation: at most 32 original ticket/layout/owner checks; 9 section-scalar
inventory operations; 8 count conversions; fixed checked formula evaluation;
fixed optional runtime/WASI configuration observations. **No record, source-byte,
cache-slot, pin, metadata-buffer or signature-parameter iteration occurs before
this debit.** Constant-size nonterminal admission decision itself and the
storage-arithmetic/return places belong to the pre-admitted shell; this decision
does not get work funded after it occurs. Inability to pay P refuses without
doing planning. A future implementation that adds an unbounded operation here
must revise the formula and cannot claim this receipt covers it.

Let source extent be S, actual counts in signature/parameter/import/function/
global/export/data/element order be `t,p,i,f,g,x,d,e`. Use u64 checked lossless
conversion of all actual usize/u32 values. Validate current fixed logical caps
`512,8192,34,79966,8192,4096,4096,4096` and source cap 67,108,864.

```text
N = t+p+i+f+g+x+d+e
L = 3t+p+5i+3f+4g+4x+4d+4e
E = 2560 + S + 8L
B = E/4096 + (E%4096 != 0)      // no overflow-prone E+4095
A = 32B
R = 32768 + 36E + 4096B + 64N + 16L + 32A + 8B
total planned debit = P + R
```

Every multiplication, addition, conversion and counter advancement is checked;
there is no saturating successful authorization. Arithmetic overflow is an
export AdmissionError. The immutable proof is authoritative under guard; the
preguard observed shape just bounds allowance. Shape mismatch refuses before
metadata/seek/write and retains consumed P/R; it does not mint more allowance.

| Term | Required implementation coverage |
| --- | --- |
| 32768 | Fixed 320-word header coverage, nine directories, five validation/17 runtime/7 optional WASI/five grants, actual provenance fixed fields, stable enums, all duplicate equality checks, constant metadata/seek/identity calls and their both-side checks. |
| 4E | Complete logical byte generation, source copy, block filling/cursor progression and final extent verification. Every source byte is included. |
| 32E | Maximum total requested write bytes across at most 32 calls per continuous block, including repeated tails after Interrupted/short writes. Counting calls alone would miss retry byte work. |
| 4096B | Full reusable-block initialization/clear bound, including partial last block. No full snapshot Vec. |
| 64N | Every Buffer element visited once, record/span/enum/range/type-index checks, loop bookkeeping and stop checks both sides of each record. Signature parameter ranges are O(1); do not nested-rescan parameters per signature. |
| 16L | Scalar lossless conversions, endian generation, encoding-word loops and their both-side checks. |
| 32A | Each attempted native write, original result classification, checked progress, attempt accounting and pre/post stop observations. Interrupted consumes one attempt. |
| 8B | Continuous-block entry/exit, final/full decision and both-side observations. |

These constants are a concrete proposed implementation contract: each helper
must annotate its fixed/record/word/byte/attempt costs and pass an actual operation
count audit against the terms before this formula can authorize execution. They
are not evidence that an unwritten implementation stays within them. No semantic
Wasm revalidation or digest calculation is hidden inside these terms.

The independent maximum envelope produces E=69,765,152, N=109,184, L=331,716,
B=17,033, A=545,056; R=2,611,218,696, P+R=2,611,235,080. This correctly **refuses
the original 1,000,000,000 limit**; no maximum-derived grant is authorized.
Small real proofs may fit the original remaining work. Each successful debit
uses checked `used+credits <= original_budget.execution_work`; its exact original
used/requested/limit are retained on refusal. P can succeed and R refuse: P stays
attributed/consumed. No unused allowance is refunded after a fast/failed export.

## 6. Immutable stop semantics

Production `observe_snapshot_stop_v1(&self)` has no injected time/callback:
existing original first_failure wins; else actual cancellation wins; else compare
`Instant::now() >= self.deadline`; else continue. Deadline is the actual carried
earliest run/WASI Instant and actual `deadline_origin`, never reconstructed from
milliseconds or reset at export start. It uses actual `self.cancellation` by
immutable borrow, not `cancellation()`'s clone. Existing failure is copied
unchanged; all new stop observations are separate export values. No usage,
first_failure, cleanup invariant, work or reservation mutation occurs.

The cache bridge performs full owner/ticket pairing before interpreting foreign
component data. Required ticket checks are exact owner and expected
category/charged extent for original adopted source/metadata, actual cache
header and three buffers, actual WASI header/four buffers if Some, and original
construction ticket. Current category/combined counters and live-ticket count
must cover those original tickets. `reservation_owner_matches` alone is not
enough; it is only an identity observation in accepted source. No foreign WASI
usage or configuration is attributed before this pairing. Existing first_failure
has precedence over new pairing/stop/debit failures; owner mismatch precedes new
cancel/deadline attribution of component data.

Check before and after: each fixed/word/record loop step; each bounded source
copy/clear action (at most 4096 bytes); each actual metadata call; stream-position
call; every write attempt, including Interrupted/error; and final successful
extent publication. Recompute from actual guard.control each time. Never use an
earlier successful check as permission for the next action. Native operations
are cooperative and cannot be forcibly interrupted; observed overshoot is not
claimed as a hard syscall latency limit.

## 7. File and bounded write semantics

Use the actual borrowed regular empty File at position zero. Compare actual
`metadata.dev()/ino()` of **both** snapshot File and actual row File before any
snapshot write, rejecting aliases even when handles are distinct. Same inode
could otherwise alter original rows and violate primary preservation. Require
the named quiescent-owner scope; metadata identity observation is not an
operational custody or close proof. Snapshot metadata, row metadata, their
Metadata/Result/identity/error places and work are part of conditional admission.
Do not accept a caller-supplied identity instead of reading the actual File.

One metadata call per File and one stream-position call, each with pre/post stop
checks and original std::io::Error retention. Interrupted in these calls refuses
directly; no hidden loop is added. Any additional future metadata comparison or
IO call requires its own named place, work and checks. Snapshot identity is not
hashed or published by this slice.

Fill one reusable 4096-byte block continuously across all header/section/field
boundaries. Do not reset attempt allowance for a record or section. For each
block make at most 32 explicit `File::write` calls, including Interrupted. Call
32 which completes the block succeeds, subject to the after-call stop check.
Incomplete call 32 refuses with progress and never makes call 33. No `write_all`
or generic callback is an exposed exporter authority entry. A generic fault seam
can exist only inside the private implementation test writer.

Record native return before its post-check. For valid positive `n<=requested`,
checked-add n to acknowledged block/total bytes before returning a post-call
stop, so successful bytes remain visible even if cancellation arrives inside
the call. Zero, overreported n and original other I/O errors refuse. Invalid n
never increments acknowledged bytes. A native error plus a post-call stop retains
both: original IO error is primary export cause and `post_stop` is additional
evidence. Interrupted with a stop retains that original error and stop; without
a stop it spends an attempt and retries. Incomplete final attempt retains last
Interrupted if present, attempt=32, calls and acknowledged progress. Partial
output is retained; no implicit deletion/retry/seek reset hides its identity.

Observation/error must retain at least code, stage/block, within-block attempts,
requested/acknowledged bytes, calls, original optional io::Error, optional
post-call stop and exact original admission error. No Debug-string parsing or
replacement failure values. Successful output claims only acknowledged bytes
and calls. fsync, descriptor close, immutable name, post-write digest/custody,
published package and retained source acquisition remain separate gates.

## 8. Places, lifetimes and consuming cleanup

`prototype/initial_append.rs` names the measured conservative shell. Every field
is a separate source role, even when compiler optimization might reuse storage:

| Proposed actual source role | Lifetime / ownership |
| --- | --- |
| control/WASI/adopted ingress borrows; previous/enlarged arithmetic slots | Exist before conditional begin, so shell/profile foundation. No owned proof clone. |
| phase Result and independent admission-error slot | Callee return and caller retained failure are conservatively both admitted. Success and error variants within one Result are mutually exclusive. |
| attempt return | Persists across original header/row calls. Holds export error or admission error by original typed move. Enum alternatives are exclusive. |
| wrapper outer return and caller Option<outer> | Both counted while crossing call boundary; outer includes unchanged original primary inline. Source of a Rust move dies when moved; no semantic owner cloning. |
| wrapper moved outer and caller moved Option<outer> | Additional conservative named handoff roles, intentionally summed despite possible non-overlap/reuse. Four full outer roles are charged in the candidate shell. |
| cleanup failure Option and cleanup Result | Actual consuming-phase outcome retained independently of primary/export. Survive until their real final use/drop. |

Measured values are RuntimeControl=1720, admission/stop=1096 each, phase=16,
export error/attempt=2232 each, outer=5648, original primary=3416, shell=29256;
all align to 8. Unit/Debug/optimized agree. The probe emits compiler constants;
it does not allocate or execute these inventory structs. Constructor/raw result
export and final typed control-cleanup result still need later dedicated places.

Conditional live storage must additionally name and freshly measure every
SnapshotPlan/Result/moved plan and counts/inventories; guard bridge/view/Result
and all Buffer inventory/iterator/reborrow slots; header[2560], loader[576],
runtime[512], directory[9], scalar/record[5] scratch; transfer[4096], cursor,
block/attempt/call counters; both actual File borrows/metadata/results/identities;
seek/result/position; write/result/error; stop/owner/ticket/debit helper args,
returns and original failures; successful return/observation/error moves; and
the actual consuming close-of-phase helper and its argument tuple. Use checked
`count * size_of<T> + ...` source-place sums in a const initializer. Do not infer
coverage from the old 201 layouts or this prototype shell. Do not subtract the
old wrapper roles unless final source proves that those roles were replaced.

Actual ledger retirement waits until guard, bridge and views are dead. Pass the
real temporary tuple/closure to `SnapshotPhaseV1::complete`; it delegates to
original `end_construction_phase_with_wasi(storage, captured_previous_bound,...)`.
That path destroys storage before reducing construction/combined and keeps
original quarantine/invariant behavior. There is no observational Drop refund.
An early return or forgotten phase leaves the full conditional charge. The
caller records cleanup failure separately and does not replace primary/export.
No cancellation/deadline/work test can block genuine cleanup. Retained outer
result/errors are not retired with temporary storage because their foundation
scope still exists. The owner must consume them before final closure retirement.

Only the original control later cleans up actual cache/adopted source/metadata/
WASI. No exporter success implies zero ledgers. Uncertain external File/name/
descriptor obligations stay charged/pending. The synthetic C01-C03 controls show
the required arithmetic/state transitions; **no actual consuming exporter
cleanup** is implemented or exercised in this packet.

## 9. Evidence and next executable boundary

`expanded-controls-result.json` contains nine finite Python groups: checked
extent/work overflow and original envelope refusal; existing failure/owner/
cancel/deadline precedence; complete and incomplete exact-32/partial/Interrupted;
zero/overreported I/O and metadata/seek failures; before/after stop and combined
IO/stop; no live-guard funding/refund/new owner; actual-destruction prerequisite;
counterfeit alternate-floor refusal; atomic nonterminal storage exhaustion;
and modeled original eight outcomes/chronology. These are design controls, not
actual validator, File writer or wrapper behavior tests.

`compile-result.json` plus `unit-layout-result.json` retain ordinary-production
Debug/optimized and unit compiler constants and one E0596-only negative for
mutating actual guard.control. The prototype has only private helper additions,
no altered original guard literal/primary enum and no RuntimeControl fields.
`compile-source-manifest.json` identifies every compiled source byte. The WASI
prototype reads actual private configuration, after prototype ticket checks.
No full ownership/layout admission correctness is inferred from compilation.
`profile-layout-result.json` separately measures the common-core adapter and
owning scope in unit/production Debug/optimized builds and preserves the original
adopt_body signature. No scope adoption/finalizer path executes. The root's
recommended proposal direction is retained by exact hash in
`proposal-direction-custody.json`; it authorizes review direction only.

The unit configuration compile first refused because CARGO_MANIFEST_DIR was not
set; its original stderr/command is retained under
`commands/compile-unit-layout-attempt-1`. The corrected compiler-only run points
that standard compile variable at the disposable exact source copy and runs no
unit tests. An earlier runner PATH lookup failure is retained in attempt-1.json.
All compiler children were reaped and all scratch/products removed; cleanup JSON
retains this. Tool versions are Python 3.14.8 and rustc 1.99.0 /LLVM 23.1.1.

Before an executable exporter slice: separate independent review, root selection
of the concrete private contracts and measured selected profile; implementation of source-derived
places and helper operation counts; fresh unit/production Debug/optimized full
layout/floor measurements; unchanged original grants and original refusals;
only then a separately named root-selected host positive fixture at fresh exact
required floor with floor-minus-one controls. Implement real all-eight payload/
ordering/IO/owner/cleanup tests and the counterfeit-floor negative. No funding
after guard, no new grant, no widening ordinary policy or silent implicit refund.

No native runtime, UI, capture, device, simulator, emulator, process inventory,
hosted/rejected worker, stopped Android, Git action, publication or canonical
file change was performed. Native checks remain paused; loader operational
allocation/IO; File acquisition/close/custody; complete constructor typed raw
result/final-ledger export; semantic replay; FieldLog immutable separate-repo
published packages; signing/store/customer/operational and GA remain pending.
No new global memory-budget pass or GA gate is claimed.
