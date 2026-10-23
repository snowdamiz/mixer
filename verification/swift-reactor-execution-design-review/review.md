# Independent review of the Swift reactor execution design

Observed 2026-10-23. This lane owns only
`verification/swift-reactor-execution-design-review/**`. The review is static
source and contract inspection. It does not approve an implementation, execute
the retained reactor, repeat validation, measure runtime fit, or pass a product
gate. No product source, test, fixture, dependency, status, gate or work graph is
changed, and no commit or push is performed.

## Verdict

The revised architecture is suitable for bounded implementation. Both review
refinements are now explicit in the reviewed design: the preserved WASI context
remains the sole owner of its WASI counters, and reservation ownership has a
finite inline ticket inventory. Root incorporated them during coordination;
the final text was re-read. There are no outstanding actionable design findings.

This is a recommendation about the design. Runtime acceptance still depends on
the original executable tests, fault evidence and frozen-route regressions in
the design's acceptance table. Exact-target execution still needs root's later
specific approval after that evidence is reviewed.

## Resolved refinement R1: one owner for each meter

The initial draft said `RuntimeControl` owned all cumulative counters while requiring the
literal stored layout and behavior of `WasiContext` to remain unchanged. The
current context stores `WasiUsage` and mutates its calls, work, transfer, random,
log and failure counters internally (`vm/src/experimental_wasi/mod.rs:160`,
`:265`, `:277`, `:398`, `:498`, `:539`). A constructor-only borrowed control
cannot itself become the owner of those active-dispatch counters without a new
dispatch contract or conflicting copies.

Root's chosen resolution is coherent and is explicit in the revised design
(`docs/swift-reactor-execution-stage-design.md:139-148`):

- `RuntimeControl` is the sole combined reservation, deadline and admission
  authority and owns cache/execution cumulative counters.
- The unchanged context counters are the sole WASI call/work/transfer/log/random/
  failure meters. They are never replaced by resettable runtime copies.
- A private runtime dispatch wrapper synchronously checks the shared control
  before/after the actual context dispatch, snapshots its observations and
  latches the first terminal cause. Copying counters into a receipt is
  observation; it cannot authorize admission or replenish a budget.
- The actual adapter's existing `deadline` is seeded with the earlier absolute
  run/WASI deadline, so its checks still enforce the deadline within staging,
  service, rollback backup and commit. Outer checks alone are insufficient.
- Preserve standalone `dispatch` argument/call/work/cancellation/range/authority/
  errno precedence. The Swift wrapper has its own explicit outer boundary;
  it does not reorder the standalone implementation.

This makes independent executor-entered-host and adapter-entered-call counts
intentional. A rejected executor entry never increments the adapter's count.
All those counters accumulate through initialization and both corpus calls.

## Resolved refinement R2: finite ticket storage

The revised design explicitly selects the 86-ticket inventory and aggregate
entry ownership (`docs/swift-reactor-execution-stage-design.md:161-178`).
Tickets must be inline fields in Swift-only owners or already bounded slot
storage. Neither ticket creation nor ledger admission may allocate or grow a
registry. The actual allocation sites support the following concrete inventory.
These are maximum live authoritative ticket values in a proposed representation,
not byte measurements or a requirement to adopt these precise Rust names.

| Ownership | Maximum tickets | Source basis / allocation ownership |
| --- | ---: | --- |
| Adopted proof | 2 | One source ticket and one aggregate metadata ticket. Metadata includes all eight immutable `Buffer` payloads and the existing proof header, with capacities retained from complete validation. `swift.rs:334-358`, `metadata.rs:95-111`. |
| Cache permanent buffers | 3 | Slot vector, pin-record vector, and the proposed single 512-patch vector. Existing slot/pin sites are `cache/mod.rs:407-419`; the patch vector is new Swift-only ownership. |
| Decoded-entry owners | 64 | One aggregate entry ticket covers locals, instruction and branch-target vectors. `cache/decode.rs:404-415` allocates those three. Admit their checked sum before the first allocation; partial failure drops every constructed vector before releasing the entry ticket. |
| Fixed state payloads | 6 | Value, control, frame, memory, table and global vectors. `execution/mod.rs:343-359`. |
| Temporary memory growth | 1 | Complete replacement memory while the old memory remains live. `execution/mod.rs:1179-1198`. |
| WASI buffers | 4 | Scratch, rollback, stdout and stderr. `experimental_wasi/mod.rs:198-201`. Store tickets beside the context in a Swift-only accounted owner. |
| Cancellation backing | 1 | One attributed backing allocation for the supplied `Arc<AtomicBool>`, measured for the qualified target/toolchain. Handles remain inside their containing headers. |
| Exclusive fixed headers | 4 | Swift cache, execution, accounted WASI and control headers after checked nested-header subtraction. The proof header is already in adopted metadata. |
| Construction and scratch | 1 | A conservative inline reservation covering all simultaneously live transfer wrappers, adapters, readers, temporary entries, ticket wrappers and failure/copy temporaries that are not in another category. Compute its complete bound before entering the relevant phase. |
| **Total** | **86** | `2 + 3 + 64 + 6 + 1 + 4 + 1 + 4 + 1`. |

The 64-entry bound includes the incoming decoded entry: when all slots are
occupied, planned unpinned victims drop before construction is admitted
(`cache/mod.rs:605-686`). A 65th live decoded owner is unnecessary. Pins refer to
the existing entry and consume no extra payload ticket; pin-record storage is
already charged. Per-allocation entry tickets would have an upper bound of 214 (`86 + 2*64`);
the reviewed design selects the aggregate entry representation instead.

Every inline ticket/`Option`/wrapper increases the actual Swift slot or header
layout and must be included in its `size_of`/alignment receipt. An aggregate
ticket is released only after all allocations it covers drop. It is not split
or partially refunded. A logical construction-to-resident ownership transfer
must not debit the payload twice or momentarily release it. Cleanup drains
ticket owners without admission, allocation, metered work, services, or checks
that can be defeated by cancellation/deadline. None of these fields belongs in
the frozen legacy owners.

## Inspected constraints that are adequately specified

| Area | Design assessment and implementation proof obligation |
| --- | --- |
| Authority and scope | The proposed public owner consumes the only complete opaque Swift proof, exposes only the sealed corpus call and immutable diagnostics/captures, and offers no bytes/policy/import/cache/pin/memory/clone/refill escape. `ValidatedSwiftReactor` actually owns one boxed source plus private complete metadata and `[WasiFunction;34]` (`swift.rs:141-148`). The exact-target digest belongs to the qualification runner; structural same-ABI fixtures may obtain the same proof but cannot acquire exact-target qualification. |
| Frozen owners | Literal fields/layouts, old defaults/narrowing, error precedence, work order, identities and usage formulas are explicitly frozen for every feature build. The current cache and executor store concrete frozen proof/cache/pin types (`cache/mod.rs:215-223`; `execution/mod.rs:118-143`). A distinct Swift owner and sealed borrowed generic algorithm adapters avoid widened `Limits` or a stored discriminator. Require old/new feature collision cases and actual layout/counter snapshots when extracting the algorithms. |
| Proof adoption and total peak | The accepted validator reserves the full proof header as Metadata (`swift.rs:328-332`), retains exact-capacity source and metadata buffers, and releases validation scratch before returning (`:387`). Runtime adoption may trust those sealed current reservations without adding historical validation peak. The runner drops external input first. Current/peak category-plus-combined admission, proof/cache/instance transfer wrappers, header subtraction, old/new growth and cancellation backing attribution are explicit. No RSS/allocator-overhead claim follows from this model. |
| Decoder control and scratch | Current `PassState` has `[Patch;128]` (`cache/decode.rs:126-130`), frozen `Limits`, local-only expansion (`:156-169`) and function-inclusive control admission (`:203`). The proposed distinct 512-patch Swift arena, parameters-plus-locals check, actual source extent and count/build equality are necessary and covered. Test exact function-inclusive 512 acceptance and 513 rejection in addition to the retained 379-depth evidence; no second Swift pass arena or hidden per-miss allocation is acceptable. |
| Cache and execution | Existing bounded LRU/nonce/pin architecture and copy-before-mutate instruction dispatch can be reused through borrowed adapters. Each Swift defined frame owns a distinct opaque pin; function controls count in live controls. Keep indirect full structural signature comparison, scalar/float/saturating/bulk semantics and numeric helper capacity proof. The design explicitly meters scans, initialization, copies and growth and preserves lifetime cache/fuel/work/host ceilings. |
| WASI ABI/grants | Complete validation resolves the ordered exact 34 imported signatures once. Runtime dispatch uses that sealed descriptor by absolute index. Explicit random, realtime, monotonic and both capture grants qualify the experiment; default-deny path/socket/filesystem/environment behavior remains. `Errno` is normal unsigned i32 guest flow; `proc_exit`, including zero, is a sticky guest exit and never native process termination. |
| Deadline | Constructor start precedes runtime work. Shared checks occur inside decoder passes/reset, initialization, movement, copying and growth. Carried earliest deadline is inside actual WASI `check`, before/after service and within commit. Cooperative allocator/platform overshoot is recorded and not called preemption. No runtime check can retroactively undo a successful guest write; only the current WASI commit has its existing rollback promise. |
| Initialization and persistence | Exactly one internal context and sealed `_initialize` call produce Ready only with empty results and zero live frames/values/controls/pins. Failed construction yields no Ready owner. Two sealed corpus calls use the same owner, state and cumulative budgets; nonzero i32 remains a real failed-qualification result. |
| Failure and cleanup | First cause remains immutable, later invocation executes nothing, snapshots distinguish failure from cleanup, and cleanup drains all frames/pins and live stacks. Retained payloads remain charged on terminal invocation until drop. Constructor failure drops all ownership and reports zero live runtime reservations. Existing frozen `terminal` overwrites post-cleanup usage (`execution/mod.rs:484-491`), so the new Swift diagnostic must be distinct and preserve both snapshots. |
| Qualification/evidence | The full retained artifact is not executed by design review. Later runner requires actual immutable size/hash before validation, separate input/internal overlap versus runtime ledger, construction/init/two-call phase observations, actual stdout/stderr and zero returns. It must parse two complete duplicate-free objects, reject extra/missing fields/objects, check types and all 11 retained native observations, and keep the first failed ceiling. Local qualification still leaves published independent FieldLog, size/performance, physical iOS/Android, store/customer/operational/GA gates open. |

## Evidence and limitations

The collector hashes the exact reviewed dirty source files, the design/evidence
receipts and the retained artifact. It checks file-manifest integrity and source
drift only; those assertions are not type validation, execution, allocation,
conformance or behavior tests. It records command argv, executable resolution/
hash, tool versions, revision, dirty state, output hashes and scope. Root's
already passing validation audits are not rerun or represented as this lane's
tests. Existing canonical validation remains historical `executed=false`
evidence, distinct from implementation/runtime qualification.

The original proposal is preserved at
`verification/swift-reactor-execution-design/proposal-before-root-refinements.md`.
Its SHA-256 matches the original design manifest's document hash, so the old
receipt remains historical evidence for that proposal. This review binds the
revised current design separately. Changes to `PLAN.md` since the old collection
are recorded as source drift and belong to root's active status work; the
reviewed VM sources still match the canonical validation source hashes.

No physical device is discovered, queried or run, and no reconnection is
requested. No engine implementation/test is written here. New artifact files
are confined to this review directory. No source or tests from Patch/Skip,
generated third-party engine material, or alternate runtime dependency is used.
