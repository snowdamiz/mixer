# Private Swift shared memory helper contract

Candidate frozen for independent/root contract review, 2026-10-24. This is a
compiling original-owner borrow/type and positive accounting prerequisite for
**Load/Store only**. No live VM source is changed, no memory opcode is executed,
and no behavior, native, full-target, Ready, public invocation, release or GA
acceptance follows from these results. `mixer-product-plan.md` remains binding.

## Authority and smallest seam

Root's accepted private control integration is
`verification/swift-control-behavior-root-review/acceptance.json`, with the exact
121-file VM closure
`241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`.
The initial live bytes reproduce that closure. The accepted control checkpoint,
executor-stage, executor-operations and shared-executor-algorithm contracts
continue to bind owners, first failure, accounting, fuel/work and cleanup. A
parent Git HEAD is context, not authority for source bytes; root continued
committing other work while this isolated packet was collected.

The source overlay is 122 files, closure
`b0922009f9fbb9b2b1091ec4b62607cff456288e8d044217481c31bfe826596c`.
It extracts the current Frozen `range`, `load` and `store` bodies into one literal
`shared_memory_methods!` macro. Static leaves select the original Frozen fields
or original Swift phase fields and accepted value primitives. There is no
generic adapter layer, second Swift load/store algorithm, alternate engine,
new instantiated owner, state field, ledger, proof copy, ticket or dependency.
The unchanged `width` helper becomes crate-private so the Swift expansion can
name that same implementation. Every other utility body is retained.

The complete 39-method compiled Frozen `SpanInstance` expansion is identical to
the baseline, including `range`, `load`, `store`, `run`, `copy`, `fill` and `grow`.
Their source ordering can change through extraction; each expanded method is
identical. The original 2,912-byte Frozen reservation expression and measured
result are unchanged. Four existing VM files differ; the new Swift child module
is the fifth overlay file. Fourteen existing containing owner declarations are
byte-identical, all other accepted source files preserve their hashes, and the
observed original owner sizes/alignments/field offsets are unchanged.

## Exact private phase and fixed result slot

The new child module is `experimental_swift_reactor/memory_operations.rs`, nested
under the already accepted `frame_operations` module. Its exact proposed entry is:

```rust,ignore
impl FrameOperationPhase<'_> {
    pub(crate) fn memory_operation(
        &mut self,
        operation: Operation,
        returned: &mut Option<Result<(), SwiftRunFailure>>,
    ) -> Result<(), SwiftRunFailure>;
}
```

`returned` is specifically the actual existing `FrameOperationStorage.entry`
slot. No storage declaration, entry behavior, control-result behavior or existing
completion method changes. A caller must take/drop its previous successful
entry or memory outcome before reusing the slot. It must retain a failure for
existing terminal drain and final owner cleanup; it cannot overwrite that
failure to proceed. Entry guards and frame pins remain in their original State
owners, separate from this diagnostic/result slot.

The method checks vacancy first, before `active`, opcode inspection, work,
operand removal or memory effects. An occupied slot is left intact, the original
first failure remains sticky, terminal drain is requested, and the outer result
is `Err`. A vacant slot receives exactly one actual inner result. An inner
failure requests terminal drain and remains in `returned`; the outer result is
`Ok(())` because publication succeeded. **Outer `Ok` never means that Load/Store
succeeded.** Every caller must inspect the stored result before another fetch or
operation. Both outer and stored result paths, the external slot borrow, retained
failure and caller/completion transfers receive separately named positive
positions even though the concrete existing slot is reused sequentially.

The original fixed `FrameOperationPhase::complete(FrameOperationStorage)` consumes
that actual storage after drain, or retains the original bound/debt when cleanup
cannot complete. No generic `T`, extra completion slot or replacement cleanup
authority is introduced. Dropping an uncompleted phase remains conservative.

The uncalled `memory_pinned_caller_prerequisite` also compiles with the real
phase, fixed storage, original frame pin, cache view and control/WASI borrows.
It demonstrates vacancy before cache view/debits, copying the actual selected
instruction and function, ending the view before effects, the existing fuel/work
and checked-PC boundaries, and atomic publication into the actual entry slot.
It is a compiler witness, **not an accepted dispatcher or complete error-path
orchestration**. The behavior lane must execute the full caller failure paths,
including terminal drain after fetch/charging errors; typing this uncalled
witness qualifies none of those behaviors.

## Caller boundary and original owners

Only a decoded `Operation::Load` or `Operation::Store` selected through the
current actual retained frame pin may reach this API from a future dispatcher.
Copy the selected instruction/operation and actual function/absolute offset,
then end the immutable cache view before calling mutable helpers. No view or
borrowed pin may survive a cache mutation, memory effect or phase completion.
The compiler witness checks those actual borrow shapes without constructing a
mock cache, frame, proof, control, memory arena or WASI owner.

The caller first establishes slot vacancy, then fetches from that retained pin,
sets the actual invocation cursor, charges exactly one instruction/fuel credit
and the original one execution-work credit, and advances the original frame PC
exactly once. Load/Store helpers add no instruction/fuel debit, PC advance, cache
operation, pin release or allocation. Caller work/cancel/fuel failures stop before
helper effects. Unsupported operations/scalar opcodes fail closed before
inappropriate operand mutation; the caller must not manufacture decoded
instructions or use the partial `width` fallback to admit an unsupported opcode.

`active()` retains the existing original-owner/live agreement checks. The Swift
preflight admits only loads `0x28..=0x35` and stores `0x36..=0x3e`. It checks a real
frame, `base <= operands <= values.len()`, the control floor, sufficient operands
above that floor, an I32 address, and the exact store value type: I32 for
`36/3a/3b`, I64 for `37/3c/3d/3e`, F32 for `38`, F64 for `39` (hex). Wrong types,
missing operands/frames, malformed floors and other operations return a typed
failure before a pop. No local/caller operand is consumed to satisfy a missing
memory operand. These Swift guards do not alter Frozen's validated route.

## Shared Load/Store effects and errors

The shared body preserves the literal existing instruction algorithm:

1. Load removes one typed I32 address; store removes its typed value first and
   then its I32 address. Each accepted value pop charges one execution-work
   credit and removes the actual live value count after the actual pop.
2. Convert the address through `u32` to zero-extend it. Obtain the existing width
   (1/2/4/8), checked-add the `u32` offset, then checked-add width and require the
   final end to be within the original linear-memory Vec length. Arithmetic
   overflow or an out-of-bounds range traps as `memory_out_of_bounds`; no host
   slice/index panic is an acceptable substitute. On this aarch64 host, two u32
   address/offset values do not overflow usize; they still fail bounds. The
   direct `range(usize::MAX, 1)` overflow case belongs in the next host matrix;
   other target-width execution is separately pending.
3. Charge exactly width execution-work credits before reading or writing bytes.
   No bulk fuel, chunk loop, allocation or memory growth is added to these small
   operations. A failed pop/work/check leaves the exact preceding effect prefix;
   operands already removed stay removed. A store cannot write a partial prefix:
   the final bounded copy is at most eight bytes after its last fallible check.
4. Load zero-pads eight bytes, reads with `u64::from_le_bytes`, then uses the exact
   original opcode match. Full integer loads preserve wrapping bit patterns;
   signed narrow loads extend through i8/i16/i32 and unsigned loads zero-extend.
   F32/F64 are integer bit payloads; there is no floating arithmetic, NaN
   canonicalization or host-endian reinterpretation. Unaligned addresses work.
5. Load uses the accepted original push primitive: one more work credit, actual
   agreement/operand/capacity checks and live predebit immediately before its
   infallible publication. Its net successful live-value change is zero. Store
   uses the low width bytes of `bits.to_le_bytes()` and has successful live-value
   reduction two. Failed loads can leave reduction one. Record actual lengths;
   never assert an unconditional successful delta on a trap/failure.

The primitive's post-pop live-removal error is returned unchanged. The new
wrapper compares the actual before/after lengths on an error and marks the
existing `cleanup.live_unreconciled` debt when an actual pop occurred. It adds no
new check, work or live admission after that effect. The accepted first failure
can remain `Cleanup` with absent function/offset/resource and the real WASI
observation. This packet does not fabricate a source diagnostic or close G08.
The existing terminal/deepest-first drain, failed-release pin retention,
cleanup-only retry, fixed completion and first-failure rules continue unchanged.

## Positive accounting and observed layouts

The inventory adds every authored binding and actual unoptimized canonical-MIR
argument/local/return, compiler-promoted constant backing/return, explicit source alias, anonymous capture payload and
direct typed literal with **four distinct positive positions**: source,
argument, returned and caller. It includes typed pop/Result/Try/residual paths,
checked-add/filter/closure state, memory ranges/slices/reborrows, padding and
endian arrays, scalar/value conversions, exact opcode match, actual pin/view/
selected-instruction/cursor/PC caller roles, result-slot admission/publication,
post-pop debt, retained diagnostics and fixed completion/drop transfers.

No existing row, equal-layout alias, already counted result slot, old padding,
Frozen scratch, peak subtraction or unrelated helper supplies credit. Pure
accounting declarations are measured types and are never instantiated owners.
Their `'static` reference spelling measures field types; actual methods use the
original shorter owner/reborrow lifetimes and manufacture no static reference.
All named fields are reserved simultaneously, so this is conservative logical
requested/named-object accounting, **not compiler stack, allocator overhead,
optimizer-temporary or RSS accounting**.

There are 4,688 positive fields: 2,116 production canonical/alias/literal fields,
2,116 additional unit fields, 404 authored active fields and 52 authored permanent
fields. Eighteen actual canonical functions (including closures and the shared
width body) and two compiler-promoted constant bodies per production/unit configuration are replayed from the final
accounted source MIR. The actual original value and control operation envelopes
remain counted once; memory adds only its fresh active and permanent structs.

| aarch64 Apple observation | Accepted control baseline | Proposed memory prerequisite |
| --- | ---: | ---: |
| Production execution header | 1,514,504 | 1,636,360 |
| Unit execution header | 2,409,184 | 2,531,040 |
| Memory permanent addition | 0 | 121,856 |
| Production memory active addition | 0 | 618,896 |
| Unit memory active addition | 0 | 1,153,832 |
| Production frame operation envelope | 2,211,968 | 2,830,864 |
| Unit frame operation envelope | 3,950,128 | 5,103,960 |
| Production/unit construction envelope | 1,069,144 / 1,071,904 | unchanged |
| Existing nested value envelope | 119,576 | unchanged, counted once |
| Frozen reservation | 2,912 | 2,912 |

State and Combined ceilings remain 128MiB and 256MiB. The authoritative ticket
maximum remains 86. These formulas enlarge the same original execution-header
and construction-ticket bounds; there is no new ticket or state field.
Sixteen actual metadata layouts compare baseline and candidate across Swift-only
and all-feature Debug/Release production/unit builds. Every new field has an
actual offset, size and alignment, lies disjointly within its measured containing
struct, and contributes via the full containing struct size including padding.
Original phase/storage/drop tuple and owner shapes remain identical. This is a
host layout prerequisite; it does not prove runtime admission/restoration.

## Evidence, review boundary and next behavior gate

Rust/Cargo are 1.99.0 on aarch64-apple-darwin. Each command retains argv, cwd,
selected environment, exact source-tree digest, status and raw stdout/stderr.
Final source and independently instrumented metadata copies have separate source
manifests/archives and build targets. The final production/unit canonical MIR,
metadata executable hashes, all sixteen layouts, the 39-method Frozen comparison,
positive schema, authored role recipe and source overlay are sealed in
`verification/swift-memory-helper-contract/`. The initial width-privacy compiler
failure and an expansion attempt spanning an owned accounting-source update are
retained as excluded draft evidence. A fresh stable-source expansion supplies the
qualifying identity. Exposing the existing helper
resolved it without changing its body. Default/span/Swift/all library checks
pass in Debug and Release. Metadata programs/tests execute only sizes/offsets
and method type assignments; they call no memory helper or caller witness.

Run the offline checker with:

```text
python3 -B verification/swift-memory-helper-contract/verify.py
```

The executable next-lane gate is `acceptance_matrix.py` and its frozen
`acceptance-matrix.json`: sixteen exact test groups over Swift/all Debug/Release,
serial bounded strict-ABI synthetic fixtures, at most 64 guest steps per fixture, 64 fixtures and three
frames per case, real 584-page minimum. It requires every named test to exist and
execute exactly once; absent/ignored cases fail. Required groups cover all 23
load/store forms and four types, endian/NaN/unaligned/narrow/wide behavior,
bounds/overflow, opcode/type/floor denials, work/cancel prefixes, actual pinned
caller/fuel/PC, post-pop fault/debt, held pins/retry, capacity/live corruption,
occupied slot preservation, stored-outcome interpretation/completion, warm
allocation refusal, Frozen runtime parity, deferred-opcode rejection and exact
accounting restoration. **All sixteen groups are pending.** Frozen compiled
identity and metadata layout are not substitutes for those behavioral tests.

Copy, fill, MemorySize and growth remain outside this API and fail closed here.
Their existing Frozen algorithms are untouched. Swift growth still needs the
separately ephemeral `SwiftGrowthContext` borrow of the original
`state.buffers[3]`, old/new memory overlap and ticket transfer protocol; this
packet creates no such borrow or implementation. Full dispatch/calls/host imports,
Ready/public invocation, native joins, the separately approved bounded target
runner, immutable published FieldLog consumption from a separate repository,
final physical-phone matrix, signing/store/customer/operational and all GA gates
remain pending. No UI, simulator, emulator, phone, publication, customer message,
credential change, commit or push was performed by this lane. Only uniquely owned
scratch was cleaned; other projects' instances, processes and data were preserved.
