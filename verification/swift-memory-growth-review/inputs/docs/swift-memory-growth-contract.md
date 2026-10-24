# Private Swift memory growth contract

Isolated private candidate under root review; root integration and independent
acceptance remain pending. Current qualification is bound by
`verification/swift-memory-growth/receipt.json`.
The binding scope remains `mixer-product-plan.md` section 10. This lane owns an
isolated verification overlay, its two documents, and its evidence directory.
Growth, full dispatch, host imports, Ready/public invocation, the full Swift
payload, native joins, physical phones, release, and GA remain pending.

## Original-owner seam

`SwiftGrowthContext<'a>` holds only `&'a mut Option<ReservationTicket>`, borrowed
from the actual `SwiftExecutionState.buffers[3]`. `prepare_growth(cursor)` returns
`Result<(FrameOperationPhase<'_>, SwiftGrowthContext<'_>), SwiftRunFailure>`.
Preparation performs the existing original-owner and empty-frame checks and
admits the existing frame envelope, then destructures the State once to make
all disjoint vector, cleanup, and ticket borrows. Existing owner declarations,
ExecutionParts, phases, and FrameOperationStorage do not acquire a field.

The caller separately owns `SwiftGrowthStorage`. Its indispensable state is the
actual existing `GrowthTransfer`, whose new/old Vec and ticket slots hold real
ownership, plus the newly admitted page delta and a sticky unresolved-live-debt
flag. It contains no second operation outcome; FrameOperationStorage.entry is
the only outcome slot. Storage is admitted as additional named objects in the
original header/frame envelope, including preparation, argument, return, caller,
transfer, cleanup, and compiler-generated positions.

A short `SwiftGrowthExecution` wrapper borrows the actual phase, context, and
caller storage. It never owns or copies a ticket. The shared growth macro keeps
the literal Frozen algorithm and chooses only static leaf adapters for memory,
maximum, allocation, rollback, and commit. Frozen's expanded 39 methods, fourteen
owner declarations, reservation expression, 2,912-byte bound, and trace must
remain identical.

## Authority and failure table

The original ticket slot is named S; the actual GrowthTransfer new ticket slot
is N, and its old ticket slot is O. T means the complete new byte reservation.
Each slot is an Option owning at most one original non-Copy ticket. No copied
identity is treated as release authority. Every explicit cleanup step checks the
actual borrowed ticket before taking it. A failed owner/layout/debt precheck
retains that Option; the complete charge stays in the actual control.

| Boundary or return | Original memory and S | Transfer Vec/ticket authority | Page debit and completion |
| --- | --- | --- | --- |
| Before allocation or new-ticket admission fails | Original Vec and S unchanged | N/O absent; no replacement allocation | No new page debit; original operation failure is stored once. |
| T admitted, page admission fails | Original Vec and S unchanged | N owns T before the fallible page check | No page delta acquired; explicit cleanup validates N then refunds only T. |
| T and delta admitted, allocator/capacity/check fails | Original Vec and S unchanged | N owns T; any real new allocation is destroyed before refund | Remove only the newly acquired delta; failure retains N or sticky live debt. |
| Partial zero, partial copy, or final check fails | Original Vec, bytes, and S unchanged | Shared local new Vec is destroyed before rollback; N still owns T | Rollback removes only new delta; no old-page repair; original failure remains first. |
| Before replacement | Original Vec and S remain live beside full new Vec and N | Both original byte reservations remain charged | New page delta is already admitted; final cancellation/deadline check has passed. |
| Replace and drop old storage | S receives N's actual ticket; original ticket moves to O | New Vec becomes original State memory; old Vec is held in GrowthTransfer.old until dropped | Committed pages agree with original Vec; no new fallible instruction effect intervenes. |
| Old refund precheck fails | New Vec and S remain committed | Old storage already destroyed; O retains its actual old ticket and charge | Terminal outcome; explicit cleanup retries O independently of cancellation/fuel/work. |
| Old refund succeeds | New Vec and S remain committed | O absent and old Vec empty; no authority duplicated | Acquired delta belongs to committed State and must never be rolled back. |
| Result push fails after commit | Committed new Vec and S retained | Any O is retained as above | Growth remains committed, delta retained; actual result arena/live debt follows accepted push semantics. |
| Explicit cleanup retry fails | Current original memory and S retained | Failed N/O remains in caller storage | Sticky debt never clears itself or creates room; no outcome overwrites first failure. |
| Successful storage completion | Current original memory and S retained | New/old Vec slots and N/O empty | No uncommitted delta or unresolved debt; destroy context/storage/preparation wrappers before existing frame-envelope completion. |

The existing refund API consumes invalid tokens on error. Growth must therefore
validate ownership, exact layout, and ledger sufficiency while each token still
occupies N/O before calling that API. It must never take a ticket and then do a
fallible precheck. The borrowed predicate check proves every owner, nonzero-ticket and checked
subtraction predicate in the original refund body. The same exclusive control
borrow continues directly through Option take and drop_reserved_with_wasi((),
ticket, same WASI observation). No callback, fallible check, or mutable alias
intervenes. There is no reachable post-take rejection or replacement ticket.

## Ordering and bounds

Maximum denial and unsigned delta overflow return Wasm I32 -1; zero returns old
pages. Allocation, State/Combined admission, cancellation, deadline, and invariant
failures are terminal. Charge the shared new-bytes plus old-bytes work schedule;
retain instruction/fuel/PC effects already performed by the actual pinned caller.
Admit complete T alongside old memory, admit only positive delta pages, allocate
exactly, zero and copy in checked chunks, check after the last copy, replace,
drop old storage, refund O, and push old pages. No precommit failure changes the
original memory bytes or S. No postcommit error rolls back committed growth.

All accepted 4,800 memory and 4,324 bulk inventory positions remain exact.
Limits remain State 128 MiB, Combined 256 MiB, and ticket maximum 86 unless a
separately reviewed arithmetic contradiction requires a change. Accounting is
positive simultaneous named-object storage with measured padding and standalone
promotions, never peak subtraction or reused aliases. G08's absent-cursor cleanup
diagnostic remains open. Native/device/UI tools are excluded from this lane.

## Explicit completion ownership

`complete_growth(phase, context, growth, frame_storage, preparation)` returns
`GrowthCompletion::Completed(FrameCompletion)` only after growth/preparation
storage is vacant and destroyed within the original frame envelope. Otherwise
`GrowthCompletion::Retained` returns those exact five values to the caller.
The caller invokes `release_growth_pending` on mutable retained values and
retries completion explicitly. A retained N/O ticket or sticky uncommitted page
debt prevents ordinary completion. The original fixed frame cleanup may itself
retain pins/bounds after growth storage is empty; its existing explicit resume
path remains authoritative.

All final compile/runtime/layout receipts use source-closure and explicit
feature/profile/unit-or-production/layout-or-runtime target contexts. The first
shared-cache collector receipts and the controlled interrupted compile are
retained but excluded. See `swift-memory-growth-implementation.md` for exact
accounting, fresh versus historical test scope, and remaining gates.
