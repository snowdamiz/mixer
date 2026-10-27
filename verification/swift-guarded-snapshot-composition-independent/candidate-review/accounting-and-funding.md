# Concrete composition corrections and accounting boundary

This review binds candidate seal `bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751`
and final 144-member source tree `140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395`.
It selects no total. The rows below are missing **occurrence-to-funding mappings**;
their measured sizes are not automatically additional bytes. Existing broad
aggregates can cover a row only after an explicit one-to-one assignment.

## Source boundary defect requiring correction first

`cache.rs:4868` exposes `construct_snapshot_in_scope_v1` to sibling modules and
accepts raw cache/control/WASI/adopted parts. `initial_profile_v1.rs:541` exposes
the corresponding raw-parts inner constructor to its parent cache module.
Both create the Selected branch without requiring the owning selected scope.
Two fresh unexecuted witnesses compile in both Debug and optimized builds:
the loader sibling calls the outer wrapper; the cache parent calls the inner.
See `bypass-evidence.json` for exact edits and compiler/source identities.

This is a source authority/funding contract defect. `MissingSelectedProvenance`
still protects encoder bytes and `WorkAuditPending` still blocks this candidate's
writer. An ordinary adoption of an authentic selected carrier can nevertheless
retain selected provenance without the selected owning-scope foundation. Merely
counting the currently intended call site cannot enforce the owning ingress.

Require an opaque control-module-minted consuming capability at **both** cache
entries. It must carry the actual exclusive cache/control borrows, actual optional
WASI borrow and actual adopted owner. The scope alone creates it from its own
fields. Its consuming parts accessor may expose those same parts to the inner
implementation; no constructor, clone, detached permit or replacement raw parts
may be accepted. Finish all capability borrows before moving the scope into Run.
The ordinary ABI can stay unchanged. Measure the new literal, each argument,
forwarding move, parts-return tuple/pattern and inner/core call result, while
removing replaced raw-argument rows by identity rather than adding both recipes.
The caller work audit must include these mint/forward/destructure operations.

## Fresh actual type identities

Four fresh compiler contexts (production/unit, Debug/optimized) agree except
the existing 48-byte unit-only WASI owner difference. Alignment is 8 unless shown.

| Type/role | Bytes | Consequence |
| --- | ---: | --- |
| `Option<SnapshotPlanV1>` | 128 | None keeps full inline storage. |
| `Option<[u8;4096]>` | 4097, align 1 | None keeps the complete transfer slot. |
| `Option<AError>` / `Option<Stop>` | 1096 each | Error/stop copies are large actual payloads. |
| `SnapshotPhaseStorageV1` | 5328 | Refusal return/argument/drop slots require unconditional funding. |
| `(SnapshotAccessV1, SnapshotPhaseStorageV1)` | 6432 | Real begin return tuple; split bindings are separate caller roles. |
| `Result<(usize,SnapshotShapeV1,u64,u64),AError>` | 1096 | Real preflight decision, not the size of its success tuple. |
| normalized `Result<View,ExportError>` | 2248 | Different from raw encoder result. |
| normalized `Result<Cursor,ExportError>` | 2600 | Different from raw encoder result. |
| normalized `Result<Option<Block>,ExportError>` | 2248 | Different from raw encoder result. |
| normalized `Result<Metadata,ExportError>` / `Result<u64,ExportError>` | 2248 each | The two metadata and one seek sites need distinct call-result IDs. |
| `Result<(),ExportError>` | 2248 | Real stop helper result at each source call expression. |
| `(InitialProfileConstructionOutcomeV1,SnapshotAttemptV1)` | 5664 | Guarded block result, then caller pattern/moves. |
| all-eight retirement destructure tuple | 4024 | Includes full Option payloads, not only the selected variant. |
| `Option<SnapshotWasiAttachmentV1>` | 2192 | Empty scope attachment and retained error slots are not zero-sized. |
| `Result<AccountedWasi,SwiftRunFailure>` | 1448 production / 1496 unit | Actual attachment constructor result and success/error moves. |
| `Result<(RuntimeControl,AdoptedProof),SnapshotPreScopeFailureV1>` | 2944 | Authentic common-core return and selected caller pattern. |
| selected scope Result | 8128 production / 8176 unit | Actual return variant storage before any owner exists. |
| `SnapshotPrimaryRetirementV1` / `SnapshotScopeFinishV1` | 7248 / 13232 | Returned diagnostics remain live across final cleanup. |

These 22 type identities have raw LLVM lines and exact 144-source variant
preimages in `commands/independent-layout-*/`. They are not a simultaneous sum.

## Missing caller/scope occurrence assignments

Use the actual candidate line numbers below, not prototype append-file lines.

| Source | Rows that need explicit source IDs and lifetime placement |
| --- | --- |
| `control.rs:606-615,1825-1859` | Added Original adapter argument/return places and closed retirement/failure helper arguments, call results and returns. Map inherited adoption entry/move/cleanup rows to the relocated original core first; add only new adapter/helper occurrences. |
| loader `into_snapshot_scope_v1`, `control.rs:1892-1898` | Authentic carrier/body/capability literal and moves; `?` core return/error; successful control/adopted pattern; full scope literal/Result/caller return slots. All precede or survive Construction admission. |
| `initial_profile_v1.rs:125-186,313-318` | New Original wrapper/core call boundary, OriginalAccess begin return, shared-control argument/return, guard-block tuple and branch finish primary/access argument/return places. Original's unit Attempt/Storage do not erase these added source frames. |
| `initial_profile_v1.rs:328-356,385-406` | Begin tuple expression, branch begin return, core caller access/storage bindings, branch finish storage argument, access completion storage argument and refused `drop(storage)` argument. Every actual full 5328-byte slot on the refused path belongs to unconditional foundation, even if an admitted path uses the same source spelling. |
| `initial_profile_v1.rs:388-398` | Pairing/storage-preflight/debit/shape/emission/commit call results, decision closure capture and return; shape error/return/pattern moves. New helper closure identities and `?` error moves have not been mapped by the 58 encoder-only shape list. |
| `initial_profile_v1.rs:424-439,446-468` | Six concrete normalizer call sites: View, Cursor, Block, metadata twice, position once. Give raw call-result, normalizer argument, normalized return, writer call-result, success/error pattern and move distinct IDs. Repeated dynamic block calls reuse source roles; they do not mint unbounded distinct storage. |
| `initial_profile_v1.rs:424-439,444-513` | Actual outer writer closure; stop/error closures; checked arithmetic closures; `ok_or_else` block refusal; post-stop capture closures. Measure the exact expressions with their actual writer/stop captures rather than substituting encoder representative captures. |
| `initial_profile_v1.rs:467-514` | Block Option conversion and pattern, byte-slice/fat-reference arguments/returns, 32-attempt range/iterator/item, native io Result and error moves, Interrupted Option/take, normalized writer closure Result, final attempt literal/return. Persistent attempt/outer errors go in foundation; writer-only frames may be conditional if their calls have ended before completion. |
| `control.rs:1901-1921` | Attachment receiver/argument/cursor, original phase Result and pattern, 1448/1496-byte construction Result, actual WASI move into scope, construction/completion/attachment literal-return-Option/reference. Reconcile existing original WASI phase inventory; do not append it a second time. |
| `initial_profile_v1.rs:524-537` | Real 4024-byte match tuple expression and seven caller patterns, individual Some moves, rejected adopted transfer, adopted cleanup call-result, 7248-byte retirement literal/return. Current aggregate retirement fields cannot implicitly cover all these separate expression/return roles. |
| `control.rs:1933-1956` | Consuming Run and scope patterns, paired observation, outer retirement call-result, actual cache cleanup Result/tail/complete arguments, failed cache Option drop, WASI cleanup Result, retained attachment/error results, usage return and 13232-byte final literal/return/caller move. |

No claim is made that all these rows need new bytes: the required work is to
assign each source occurrence once, record overlap with inherited and candidate
aggregates, then compute the checked conservative envelope from that assignment.

At `control.rs:1936-1938`, the finalizer reduces the actual selected WASI pairing
result to `.is_ok()` and drops its typed admission error, using no WASI observation
on refusal. Actual cache/WASI cleanup returns are retained separately. This is an
explicit diagnostic disposition to settle for foreign/layout fault controls,
not a demonstrated runtime cleanup-loss failure: the authentic scope cannot
externally swap its WASI field. Name the pairing call/return/error source roles
and either retain the typed pairing result or document and test the intentionally
unattributed observation policy without relabeling its diagnostic as a cleanup
return. Adding a retained field changes Finish and its inventory/work rows.

## Minimal funding and lifetime design for the next candidate

1. Close the raw-parts boundary first, then freeze the new exact source. Binding
   costs and argument moves from this correction must join the same accounting.
2. Preserve one authoritative common foundation formula. Extend it by the exact
   added ordinary adapter/helper/Original branch occurrences; preserve the old
   original core and cleanup roles by identity. This common amount must be chosen
   before source/control/Construction admission. It cannot be recovered later by
   enlarging a cache phase, increasing a budget or accepting equal byte counts.
3. Place selected early ingress, scope/return/error owners, all refused full Option
   slots, persistent outer/error/completion and finalizer result places in the
   selected pre-Construction recipe. Place only proved admitted-only temporary
   source roles in the conditional phase. The current phase's `storage` and
   `storage_drop` labels cannot simply charge the refused path conditionally.
4. Reconcile the encoder-local callee inventory from the separately owned lane:
   `encoder::<qualified function>::return-expression` is its callee role;
   `caller::<writer callsite>::call-result`, caller argument/move and writer-held
   view/cursor/block/result owners are this side. Transfer/guard/proof pointees
   stay external; encoder reference argument slots remain in that callee lane.
5. Keep the selected charge through the actual retained outer/retirement/finish
   lifetimes. Calling `outer.retire_v1` does not end the 7248-byte retained result;
   returning Finish keeps 13232 bytes of actual diagnostics. Healthy narrowing
   requires either a single authoritative common recipe that explicitly covers
   the surviving diagnostic roles, or a consuming helper cutset that destroys
   every selected extra before original finish. A captured equal byte base or
   dropping only plan/transfer does not establish that cutset. The current
   conservative ConstructionBound/retained charge behavior is correct to keep.
6. Preserve original limits and the encoder-only accepted work interface. Join
   the separately reviewed caller/control/capability/stop work before replacing
   WorkAuditPending. Select the bounded-call stop amendment explicitly. Only
   then release a new source/work/storage-bound genuine host execution matrix.

## Actual writer semantics and next fixture dependencies

Source has two descriptor metadata calls, one stream-position call, at most 32
explicit writes per block, and no flush, sync, truncate, close or durable-publication
operation. The alias test uses both live descriptor `(dev,ino)` pairs, so separate
handles to the row inode are rejected. It does not compare snapshot output to the
four loader provenance identities. Intact nonempty loader inputs fail the empty
output check; a stronger all-input-identity policy would need an explicit helper,
its source/work/storage rows and separate tests. The fresh host must own both
create_new output handles and state whether external writer access is excluded.

Successful partial-write bytes update progress before a post-write stop is
returned. Original io::Error and a simultaneous post-stop survive IO failure.
The 32nd complete write succeeds; the 32nd incomplete/Interrupted write refuses.
These are source-reviewed semantics; deterministic finite native-return tests,
actual aliases/metadata/seek controls, all-eight outcomes, original primary
continuation, pre/post-stop and consuming cleanup remain execution dependencies.
No genuine writer, VM, native runtime or paused surface ran in this review.
