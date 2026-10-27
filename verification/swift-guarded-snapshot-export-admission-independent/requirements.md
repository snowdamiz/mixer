# Independent requirements before producer release

## Scope and source facts

These criteria were authored without reading the active producer design. New
wire constants are deliberately not selected here. The old preparation wire
grammar and place roster are historical proposals, not implemented accounting.
Only isolated selected-adoption host scope is accepted by the referenced root
receipt; all later exporter/runtime/custody/product gates remain separate.

The accepted `cache/initial_profile_v1.rs` declares the private guard at line 25,
the eight original outcomes at lines 38–47, and the only guard literal at line
163. The constructor checks occupied slot, selection, prepare, construction,
completion and original `inspect_initial_v1` in that order (lines 125–163).
Inspection performs original cache/adopted/ticket checks, fresh-state checks and
checked conversions (lines 187–248). A new snapshot diagnostic must not move
ahead of any of these original refusal points.

Accepted `control.rs` owns the actual `first_failure`, cancellation and deadline
(lines 400–420). `check_with_wasi` checks existing first failure, then actual
cancellation, then actual `Instant::now() >= deadline` and calls `fail`
(lines 897–920). `fail` writes the first terminal failure once (lines 922–949).
`work_with_wasi` calls that terminal check and then `fail` on checked exhaustion
(lines 1444–1485). `enlarge_construction_with_wasi` also calls the terminal check
and terminal byte preflight (lines 1120–1168). None is a valid implementation
of an export-only refusal. `cancellation()` clones its Arc-backed handle (lines
825–826); a new immutable probe must read `self.cancellation.is_cancelled()`
directly. The accepted cancellation load is immutable and Relaxed, not a clone
(`execute.rs` lines 7–16).

The same control has one original Construction ticket. `end_construction_phase`
first drops supplied storage, then validates owner/category/bounds and subtracts
only the difference (lines 1186–1238). The consuming `finish_owned_cleanup`
retires Construction only when its bytes equal the one known foundation
(lines 1746–1808). Enlarging a ticket never transfers the enlarged phase's actual
storage into RuntimeControl. That ownership fact remains true with new floors.

## Original outcomes, order and nonterminal errors

1. Preserve the exact original eight enum variants, discriminants, inline owner,
   error, failure, completion, header and row payloads. No Debug parsing,
   replacement error or reconstructed payload is evidence of preservation.
2. Add a distinct outer result. Original variants 1–7 before a guard report
   snapshot NotReached. A snapshot failure remains observable if later original
   header encoding refuses. Original header refusal still suppresses rows.
3. Required success-path order is successful original inspection; checked
   nonterminal work predebit; checked nonterminal same-ticket phase admission;
   sole guard; snapshot attempt or already retained outer admission refusal;
   original header encoder; original row writer. Failed snapshot admission must
   still reach the sole original guard/header/rows path with the same primary
   result whenever that original path is otherwise unchanged.
4. Every export-only failure preserves `first_failure` exactly, including None.
   A preexisting real first failure is observed, never overwritten, cleared or
   transformed into a new diagnostic runtime failure. No synthetic replacement
   cursor, WASI usage, terminal fault or callback may enter the original path.
5. No guard is acquired for earlier original failures. No new guard literal,
   constructor retry, preparation/acquisition reentry or mutable control/cache/
   WASI access exists while the original guard or any derived view is live.

## Required concrete private contracts

The producer must provide exact Rust signatures and source implementations; a
comment promising nonterminal behavior is insufficient. Illustrative shapes are
below. A selected-only opaque owning scope may mediate these methods while
keeping actual RuntimeControl private; these are not selected public APIs:

```rust
fn snapshot_interruption_v1(&self) -> Result<(), SnapshotAdmissionErrorV1>;
fn snapshot_predebit_execution_v1(
    &mut self, credits: u64,
) -> Result<(), SnapshotAdmissionErrorV1>;
fn snapshot_enlarge_construction_v1(
    &mut self, required: usize,
) -> Result<SnapshotPhaseV1, SnapshotAdmissionErrorV1>;
```

`SnapshotAdmissionErrorV1` is an independent diagnostic value. Any retained
preexisting `SwiftRunFailure` is an exact copied observation, not an invocation
of `fail`. The immutable check must source actual same control state, return
existing-first-failure before cancellation before deadline, and perform no Arc
clone, ledger write, allocation or substituted caller clock. Test-only injected
clock/state must not become the production entry signature.

Predebit must check actual interruption and `execution_work.checked_add(credits)`
against the original ExecutionWork budget before commit. It must leave the
counter unchanged on refusal, never alter CacheWork/fuel/calls, and never refund
committed work after storage refusal, empty/malformed/aliased output, missing
selected provenance, encoding disagreement, interrupted write or success.

Same-ticket enlargement must check actual owner/category/current ticket, use
checked category and combined totals, never mint another ticket, and leave all
counters/ticket bytes exactly unchanged on refusal. The required bound must not
shrink the current ticket. An unadmitted fallback must not instantiate the full
encoder buffer or other conditional storage to encode its own refusal.

The phase API must describe ownership of its actual admitted storage and a
consuming end. A token alone is not proof that a separate buffer was destroyed.
The signature and call graph must prevent an unrelated `()`/byte-count argument
from retiring actual exporter storage; any unsafe/private obligation must be
explicitly reviewed and controlled. An alternate accepted floor recognized only
by byte equality at `finish_owned_cleanup` is a cleanup-forgery risk. A caller
must not obtain a zero observation while actual storage charged by that floor
still lives. Refusal branches are part of this requirement.

## Complete storage and lifetime measurement

Measure every newly introduced native identity in unit and ordinary-production
Debug and optimized contexts. Report size and alignment, exact source revision/
tree digest, compiler version and command; do not inherit the old 201 identities
as measurements of new types. Identify every concrete runtime source role,
including unnamed expression results, pattern binds, receiver/argument borrows,
closures/iterators, Result/Option/error slots, every return and caller move,
checked arithmetic, metadata/seek/write errors and cleanup returns.

The conservative permanent early floor must cover wrapper arguments, outer
result ingress/returns/moves and admission/error/control/cleanup shell that can
exist before conditional enlargement or survive afterward. Extend the original
ticket before those roles exist. A selected-only opaque owning adoption scope is
an acceptable design direction if an authentic SelectedValidatedProfileV1 enters
the shared original admission core, the scope owns actual control/adopted proof,
and no owned-control escape exists. Ordinary adopt/adopt_body may retain their
original floor path. This does not prove zero common-core cost: measure common
entry enum, source/return/move/failure roles and every new source-place delta.
The scope finalizer must consume actual outer/result/cleanup storage, retire the
same ticket to its captured original base, then invoke unchanged single-floor
finish_owned_cleanup. A bool/floor supplied by the caller cannot choose that
base or authorize retirement. Original foundation is 366,896 unit /
366,312 production; the 300,000 original grant must still refuse. The historical
400,000 fixture is refusal-path evidence only. No product grant increase is
authorized by this review.

The conditional full phase must include its complete simultaneously possible
source set: preflight counts/plan and moved result; guard/view and results;
source/metadata/provenance/runtime observation borrows; fixed header/provenance/
runtime/directory/record/scalar scratch; one 4,096-byte transfer block; all
File/metadata/seek/write/check results; loop counters and spans; export success/
error/attempt/result copies; phase token/arguments and consuming cleanup. If
there are disjoint phases, prove their boundary by actual consuming storage
transfer before narrowing. A maximum-of-layouts union cannot replace overlapping
source roles without that boundary. Compiler stack reuse and padding do not
authorize subtraction. Include the new layout measurement types themselves only
when instantiated by the runtime, not as fictitious runtime allocations.

Every reachable original early exit and every new admission/encoding/writer/
cleanup error needs a phase-state table with actual storage alive, ticket bytes,
work charged, cleanup action and surviving outer result. Consuming cleanup must
retire real phase storage before returning to the known floor. Permanent result
storage remains charged until its actual owner is consumed. A forgotten phase
must remain charged and produce a cleanup invariant, including if its bytes
coincidentally equal a newly recognized alternate floor.

Only root may later select a separate host-positive grant equal to the measured
full actual requirement. Exact-floor/floor-minus-one controls must include
already charged source/metadata/cache/control/WASI and all persistent shell
bytes, not just the new buffer size.

## Work, checkpoints and bounded I/O

The checked work formula must derive only from the actual accepted source extent
and actual immutable logical counts after inspection, and be rechecked under the
guard. Caller counts and the format maximum grant no authority. Each coefficient
requires a source-role map covering preflight, all scalar/boolean/enum/span and
capacity checks, all metadata element passes, source copying, all encoded bytes,
fixed header/zero initialization, block filling, every possible write attempt
including Interrupted, actual immutable interruption reads, error/progress
construction and final success observation. Multiple passes must be counted
multiple times. Arithmetic overflow is an independent outer refusal with no
work or ledger commit.

Use checked continuous blocks: `blocks = total / 4096 + (total % 4096 != 0)` and
`attempts_cap = blocks.checked_mul(32)`. Do not use `(total + 4095) / 4096` without
checking the addition. The exact formula and its cap must include the worst
admissible logical counts and separate source extent, not assume all counters
are small because actual current fixtures are small.

Checkpoint before/after metadata and position calls; at each bounded record or
source-copy/block interval; before and after each real write including a write
returning Interrupted; and before successful return. Define how a simultaneous
post-call cancellation and I/O error is ordered while retaining acknowledged
progress. A returned full write may still yield an outer cancellation/deadline
error after acknowledged bytes equal total; it cannot be reported as unqualified
success. Cooperative checks cannot bound the duration of a blocking File call.

At most 32 calls per continuous block, including Interrupted. Completing call 32
succeeds unless its mandatory post-call interruption check refuses. Incomplete
call 32 refuses without call 33. A section boundary does not reset either block
offset or attempt allowance. Zero/overreport/I/O failure retain exact attempted
call count and acknowledged bytes. No full snapshot/source Vec is allocated and
no partial output is erased to hide progress.

## Actual output identity and remaining gates

The existing row File admission checks only actual regular-file type, empty
length and position zero (`diagnostic_profile.rs` lines 127–139). Distinct Rust
File borrows can alias one inode, including independently opened hardlinks,
symlinks or `try_clone`. Before the first snapshot write, obtain actual metadata
from both borrowed snapshot and row Files and reject equal `(dev, ino)`. The
actual accepted loader already derives these fields from `File::metadata`, not
caller identity assertions (`retained_profile_loader_v1.rs` lines 569–589).
Record metadata failure as snapshot-only refusal before any write. Neither path
text, descriptor integer, File object address nor caller-provided nonce/digest
proves distinctness. Both descriptors must remain quiescent; mutation through
external aliases/name races remains an explicit custody limitation.

Real host controls must use duplicate and separately opened alias handles plus
distinct empty regular files. Reject alias before any write and preserve the
original row file's content/position behavior. Do not delete partial output or
close a borrowed descriptor implicitly. File acquisition and associated opaque
standard-library error allocation, close/name/hash custody, loader operational
admission, full writer, immutable publication, separate-repo FieldLog, devices,
signing/store/customer/operational and all GA gates remain unaccepted.

## Fresh review evidence after root release

Verify the exact frozen producer seal and all referenced source/measurement/
command inputs before reading. Compare the unchanged original enum/body ordering
and every proposed control against accepted source. Run small fresh controls
chosen here, including arithmetic overflow/exact boundary/nonrefund, preexisting
first failure/late cancellation/deadline, admission refusal preserving primary,
all original exits, same-inode output, omitted/forged/actual consuming cleanup
and call-32/33 behavior. Review the actual production implementation/signatures
and measured layouts; this model is not a substitute. Report concrete findings
to root. Do not correct producer files or reinterpret its evidence as a pass.
