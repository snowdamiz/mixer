# Source146 resource-interface price candidate

This component supplies finite prices for the actual File, cancellation Arc,
closed-route Error and Vec/Box frontiers behind the accepted source146 payload
and newly frozen constructor destructor roster. It is a source/interface
candidate for independent review. It selects no host budget, runtime grant,
fixture, path, process identity or execution authority. Compiled standard-library
body correspondence remains pending.

The exact source/host trees are `690755b7…0185` and `027394c3…0de2`, with
`rustc1.99.0 b940084d7eb6a299eb4bfeb8e34901bc051e7ac4` targeting
`aarch64-apple-darwin`. The accepted payload and independent layout packets,
official Rust discovery packet, complete146 source manifest,11 host support
members, exact full MIR, original90/55 queries, full exact146 compiler layout
output and frozen constructor roster are rehashed. Additional official Rust
helpers/primitive declarations were fetched only at that same commit. No
installed toolchain or source input was changed.

The inherited unit counts source/aggregate/destructor-interface occurrences
plus explicitly declared native-sized and requested-backing allowances.
`contract.json` names every interface event and native operand slot. A record
costs one interface unit; its named fields contribute their native widths.
Mutually exclusive branch records are summed conservatively. These records
measure interfaces. Private standard-library implementation, compiler lowering,
allocator implementation/physical overhead, kernel implementation, private
retries, CPU instructions, time, stack high-water and RSS remain outside this
unit. None is silently treated as an in-unit zero.

The actual File chain is `std::fs::File -> sys::fs::File -> FileDesc -> OwnedFd`.
Its branch-union price is9 interface units plus73 native operand bytes. It pays
four ownership/destructor interfaces, the library-UB predicate, optional fcntl
and errno observations, optional abort interface, and close with its ignored
result. The native slots include receiver pointers, fd/command/result widths and
the borrowed static abort-message reference. This is one close request, with
no inferred close retry. It proves no close success, flush, descriptor retirement,
healthy cleanup or refund. The fcntl branch is included regardless of whether
the installed std binary compiled that check away.

The cancellation Arc price is15 interface units plus173 native/requested bytes.
It covers the strong decrement and final-owner predicate/acquire/assertion,
drop_slow, AtomicBool payload visit, implicit Weak decrement and final-owner
predicate/acquire/assertion, and Global deallocation request. Both assertion
failure interfaces are conservatively included. The native side also retains
the separately qualified24-byte backing request with alignment8. The actual
AtomicBool has no product callback; Cancellation's private field is created by
Default and shared by Clone, with no exposed Weak/raw-pointer construction.
An8-byte handle or zero added clone allocation is never substituted for
destruction or backing. Repeated work-cut backing surcharges deliberately
overcover individual destructor visits; they do not create extra storage owners.

The Error price is3 interface units plus32 native operand bytes, with zero
dynamic owned backing only for this exact closed route. Product setup fixes
valid read-only File options or valid write/create_new options. This excludes
the standard OpenOptions invalid-combination branches that construct custom
Error values. File read/write/metadata/position and loader getcwd failures use
the OS tag; path NUL conversion uses a borrowed static-message tag. Full MIR
binds both generic read_request call sites to actual File. Error values are
preserved without arbitrary injected callbacks. The core/alloc/std split is
retained: custom Error would invoke both outer-drop and inner dynamic callbacks,
so `source_ceiling_cuts` rejects custom, generic, unknown or other provenance.
This price is not a bound for an arbitrary io::Error.

Vec and Box are specialized to Global. `Global::alloc_impl_runtime` returns
`ptr.cast_slice(layout.size())`; its deallocation implementation explicitly
states allocate/grow/shrink expose exactly the requested layout. RawVec
grow_exact computes `len + additional`, completes allocation before publishing
the pointer/cap, and stores that requested cap. The product uses fresh vectors
for these exact reserves and checks capacity before ordinary filling. Failed
allocation leaves the old/empty cap; a capacity-refusal path is still covered by
the same source-request bound for this concrete allocator. None of this infers
malloc's physical footprint or promises arbitrary allocator behavior.

Source ceilings are64MiB for each source Box,16MiB for a metadata frontier,
8MiB for an individual decoded resident vector,64 SwiftSlot elements of136
bytes,64 PinRecords of16 bytes,512 Patches of32 bytes,512 optional ScanPlans
of56 bytes, and65536 bytes for each payload/cache/WASI byte vector. The cache
index itself is192 bytes. The shared Vec<Type> cut conservatively uses16MiB
across metadata and resident contexts. Metadata and resident sums remain
separate tighter category constraints in `capacity-backing-interface.json`;
charging each frontier at its individual maximum is conservative. Validator
metadata is capped at16MiB and scratch at1MiB, including attempted allocation
and failed-reserve paths after category admission. This packet does not price
all loader temporary byte-vector visits with the65536-byte payload cut.

For a plain nonzero-sized element with N source occurrences, max live count L
and requested-byte ceiling B, the vector cut is `(4 + N*L) + (24+B+N*B)`.
The24 bytes describe pointer/size/alignment at the deallocation interface.
The native surcharge follows `sum(size(T) over live elements) <= backing <= B`;
it does not invent or substitute a concrete element layout. L is additionally
bounded using the exact recorded compiler element extent. All plain elements
have a closed source graph with no resource fields or reachable authored Drop.
The byte Box analogue is `(3+L)+(24+2*B)`.

Vec<SwiftSlot> uses a4-unit/8728-byte base plus64 visits of the complete accepted
SwiftSlot component:2603 plus separate positive Vec<Type>,
Vec<DecodedInstruction> and Vec<u32> cuts. All three nested cuts are mandatory.
Empty actual slots are conservatively charged as fully resident slots.

The returned payload component is **45,196,204**. The during-entry maximum of
one complete typed row across the exact seven accepted types is
**1,210,256,815**; the child component applies its53 visits separately. P0 and
the returned-carrier P5 are separate. `components.json` exposes all20 typed rows.

`internal-rows.json` adds13 complete typed body prices for constructor teardown.
A separately implemented closed type algebra reconciles every accepted row
before adding Partial and the three scalar phase declarations. The retained
exact146 layout output closes Partial1432B, cache failure/carrier2312B,
initial outcome3416B, attempt2248B and phase storage5328B; all align8. The frozen
constructor roster's12 requested typed body cuts sum **134,288,951,629**.
Constructor source/callee shells are separate. A phase-storage body price is
also available, but its multiplier is not selected because that frozen roster
classifies it as inline-only and requests no opaque cut for it. No caller
multiplier is invented in the per-one rows.

The evaluator refuses changed contract data, wrong source/host/target/allocator,
unqualified Error provenance, missing/zero/unknown cuts, missing nested vectors,
wrong SwiftSlot extent/live count, malformed graph ownership and u64 overflow.
The pure executable controls include explicit enumeration of live element
occurrences/extents, monotonicity, callback-provenance and hostile mutations.
Synthetic values are only controls; no selected resource values come from them.
Four checker failures are retained: the seal/count delimiter was copied
into a digest, two source excerpt ranges missed an intended assertion, and an
Arc source anchor used the former AtomicUsize spelling instead of Atomic<usize>.
They changed no source input and started no product process.

Reproduce without changing this packet:

```text
python3 -B verification/swift-guarded-snapshot-resource-cost/derive.py --check-only
python3 -B verification/swift-guarded-snapshot-resource-cost/controls.py --check-only
python3 -B verification/swift-guarded-snapshot-resource-cost/freeze.py --check-only
```

Exact Rust source commit matching the compiler is source provenance, not proof
that every precompiled std body has the same instantiation. Remaining binary
correspondence needs File/OwnedFd's conditional check/close calls, Arc/Weak
final-owner and24-byte deallocation, the Error closed tags, and concrete
Vec/Box teardown layouts. A tiny coordinated std-only IR probe may expose
generic bodies; nongeneric external bodies may require symbol/disassembly
evidence from the already installed libraries. This packet ran no compiler.

Only this folder was written. Bounded pure Python children were waited and
their owned process groups were absent. No product, loader, fixture, VM, cache,
scope, writer, constructor runtime, native/device/simulator/emulator/UI/capture,
global process inventory, Git mutation, production action, external message,
credential action or installed-toolchain change occurred. Native runtime is
paused; complete host funding, genuine immutable caller/build/session/executable
binding and execution, cleanup, FieldLog, OTA and GA acceptance remain pending.
