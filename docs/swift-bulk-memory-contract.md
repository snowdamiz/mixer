# Private Swift bulk-memory contract

This candidate extends the accepted private Load/Store slice with shared original
Frozen `bulk`, `copy`, `fill` and `MemorySize` semantics. The binding scope is
`mixer-product-plan.md`. Independent review and root acceptance/integration remain
required. This is a bounded host development slice, with no release or GA claim.

The accepted input is the normalized 123-file VM closure
`17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff`,
accepted by `verification/swift-memory-root-integration/acceptance.json` and
subsequently committed as `615a05dc14655dace87c2ff561a610bef4526621`. The
125-file private candidate closure is
`e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626`.
The exact input/source archives and manifests are in
`verification/swift-bulk-memory/`. Git HEAD is context; these closures bind bytes.

## Shared semantics and bounded ownership

`shared_bulk_memory_methods!` contains the literal original Frozen bulk, copy and
fill bodies. Static leaves select the original Frozen fields or the original
Swift phase and accepted helpers. `shared_memory_size!` contains the original
page-to-I32 push expression. The compiler-expanded 39-method Frozen
`SpanInstance` implementation, all fourteen containing owner declarations,
reservation expression and observed 2,912-byte reservation remain identical.
There is one implementation of each memory algorithm and no dependency addition.

Root coordinated parent-private visibility of the accepted `memory_range`,
`memory_pop_value`, `memory_pop32` and `memory_push_value` helpers, with unchanged
bodies. The range macro receives an optional visibility token; its Frozen
expansion is unchanged. The existing 4,096-byte `CHUNK` constant becomes
crate-private so both expansions use the same constant. These are visibility
changes, not new owners or alternate algorithms. The complete accepted memory
accounting suffix, including all 4,800 existing positions, is byte-identical.

The new child module `bulk_memory_operations.rs` is nested in the accepted
`frame_operations` module. Its private entry points are:

```rust,ignore
FrameOperationPhase::bulk_memory_operation(
    &mut self,
    operation: Operation,
    returned: &mut Option<Result<(), SwiftRunFailure>>,
) -> Result<(), SwiftRunFailure>;

bulk_memory_pinned_caller(
    phase: &mut FrameOperationPhase<'_>,
    storage: &mut FrameOperationStorage<'_>,
) -> Result<(), SwiftRunFailure>;
```

The supplied slot is the actual existing `FrameOperationStorage.entry`. Vacancy
is checked before active/cache/fetch/debit/PC/operand/memory effects. An occupied
success or failure is preserved, terminal drain is requested, and the outer
result is Err. A vacant slot receives exactly one actual inner outcome; an inner
failure requests terminal drain while outer Ok records publication. A caller
must inspect that stored outcome. It takes a successful outcome before reusing
the slot, and retains a failure for the original fixed completion and cleanup.
There is no new result owner, slot, ticket, generic completion or cleanup authority.

The bounded caller fetches the actual selected instruction through the retained
original frame pin and actual cache view, copies instruction/function scalars,
and ends the view before effects. It sets the actual invocation cursor, rejects
unsupported operations, charges exactly one instruction/fuel credit and one
execution-work credit, then checked-advances the original PC once. Early active,
fetch, cancellation, fuel, work, PC or helper errors are stored in the same fixed
slot and request the existing drain. Original first failure and WASI attribution
remain sticky. The helper adds no instruction count or PC movement.

## Operation ordering

Only `MemoryCopy`, `MemoryFill` and `MemorySize` are admitted. Active agreement,
a real frame, valid base/operand/control floors and actual memory/page agreement
are required. Copy/fill require three I32 operands above the floor before any
pop; locals or caller operands cannot satisfy a missing memory operand. Size
requires no operand but retains those original frame and memory checks.

Copy removes length, source, destination, each through the accepted typed pop
and actual live-value removal. Fill removes length, value, destination and uses
the value's low byte. Addresses and lengths pass through u32 for zero extension.
Copy validates source then destination ranges; fill validates its destination.
The accepted checked-add range helper rejects overflow and out-of-bounds access
as `memory_out_of_bounds` before indexing or bulk charging. Zero length still
checks ranges: an address at the memory end is valid and an address beyond it is
invalid. No memory effect precedes both validated ranges and charging.

The original bulk body charges `ceil(length / 64)` fuel, without increasing the
instruction count, then charges exactly `length` execution-work credits. Each
pop contributes its original one work credit. Work denial after the bulk fuel
charge retains that fuel, and popped operands remain removed. Zero length still
runs the original fuel/check and work/check boundaries with zero credits.

Copy uses backward chunks when destination exceeds source, and forward chunks
otherwise, including equal addresses. Each chunk checks the original control
before at most 4,096 bytes of `copy_within`. Fill checks before each bounded slice
fill. Overlap therefore has the original memmove behavior. Chunk cancellation
retains the actual completed forward prefix or backward suffix, three consumed
operands, and the already charged full bulk fuel/work. There is no rollback or
extra final check after the last chunk. Zero length executes no chunk check.

Size reads the original control's admitted observed live page count after
checking that memory length is a whole number of pages and agrees with that
count. The shared expression pushes its I32 representation through the accepted
push helper, including capacity checks and live predebit immediately before
publication. It allocates no memory, charges one helper work credit and no bulk
fuel. All three operations preserve the original memory Vec/ticket/capacity.

Post-pop removal errors use the existing memory debt wrapper. Actual value
removal can precede a live-accounting failure, so success deltas are never
assumed on error. Terminal/deepest-first drain retains failed-release pins and
allows only explicit cleanup retry. Unreconciled live debt retains conservative
original authority. G08's preserved absent-cursor Cleanup diagnostic remains open.

## Positive accounting and limits

The new independent `PermanentPositions` and `ActivePositions` are measured
logical accounting declarations, never instantiated owners. Every authored
binding, canonical MIR argument/local/return, alias, direct typed literal,
capture payload and selected compiler promotion has distinct positive source,
argument, returned and caller fields. The same selection rule applies to
functions and promoted bodies, including standalone
`bulk_memory_pinned_step::promoted[0]` and the actual preflight closure promotion.
Actual test-module promotions are excluded. No accepted row, equal-layout alias,
old padding, Frozen scratch, peak subtraction or reused slot supplies credit.

There are 4,324 fresh fields: 1,952 production canonical positions, 2,004
additional unit canonical positions, 316 authored active and 52 authored
permanent positions. The old 4,800 memory fields remain exact. Visibility causes
1,672 existing unit canonical labels to acquire their full containing-module
qualification; the explicit delta contains only `mirFunction` spelling. All
existing fields, types, bindings, aliases, literals, positions and counts match.
Four actual final compiler configurations reproduce both old and new inventories.

| aarch64 host logical named-object bound | Production | Unit |
| --- | ---: | ---: |
| Accepted memory active addition, preserved | 624,544 | 1,142,760 |
| Fresh bulk active addition | 642,456 | 1,206,544 |
| Fresh bulk permanent addition | 121,856 | 121,856 |
| Complete execution header | 1,758,216 | 2,652,896 |
| Complete frame operation envelope | 3,478,968 | 6,299,432 |
| Original construction envelope, preserved | 1,069,144 | 1,071,904 |

Eight accepted-baseline and eight final-candidate actual compiler metadata runs
cover Swift-only/all-feature Debug/Release production/unit builds. Every fresh
field has a measured aligned, disjoint interval within its measured containing
struct. Original owner sizes, alignments and offsets are identical. The complete
existing memory component is retained and the fresh bulk component is added to
the original header/frame formulas. The fixed State/Combined limits remain
128/256 MiB and authoritative ticket maximum remains 86. These are conservative
simultaneous logical named-object bounds; compiler stack, allocator overhead,
optimizer temporaries and RSS are not claimed.

Growth and its ephemeral original memory-ticket borrow, host imports, full
Swift dispatch/calls, Ready/public invocation, native joins, the full Swift target,
separate-repository immutable published FieldLog consumption, physical phones,
signing, store, customer, operational and GA gates remain pending. No native,
simulator/emulator, phone or UI tool is used by this lane.
