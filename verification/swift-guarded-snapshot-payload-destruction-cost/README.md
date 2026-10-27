# Source146 actual payload destruction interface candidate

This packet derives a source-specific, conditional payload component from the
accepted full source146 / host11 and immutable preoptimization MIR. It selects
no resource cut, policy, quote, budget, grant, fixture, path, root or runtime.
It is ready for independent component review; complete funding is still pending.

The returned `OwnedFixtureOutcomeV1` has two variants. `SetupRefused` contains
`SetupOutcomeV1`, whose Ready variant owns five Files, Refused owns the original
`io::Error` plus five optional Files, and InvariantRefused owns the five options.
`Loaded` owns three loader Files plus an optional executable File, row and
snapshot Files, loader usage, a cancellation owner, eight 32-byte claim fields,
and the original primary outcome. The primary is a loader failure or a typed
leaf result. The loader failure contains an optional original `io::Error` and
scalar validation diagnostics. The leaf result contains scalar diagnostic
aggregates; its export failure can retain one original `io::Error`. Returned
diagnostics own no cache, control, selected proof, vector or boxed source.

The returned graph conservatively requires at most six File destructor entries,
one Error destructor entry and one Arc<AtomicBool> destructor entry. The three
resource counts are a componentwise maximum across alternatives; mutually
exclusive variants are deliberately overcovered. No File destruction proves
close or flush success, descriptor custody completion, healthy cleanup or refund.

The finite source aggregate allowance is **45,195,489 logical units**, computed
as 3,321 source-owned aggregate/field/scalar/control occurrences times
`(1 + 13,608)`. The 13,608-byte root extent comes from accepted actual90 layout
data. For this conservative allowance, every nested inline occurrence is
surcharged at the complete concrete root extent. These are logical native-sized
occurrence units, not observed copying or compiler instruction counts. Enum
control and variant wrapper entries are explicit; borrowing a reference never
destroys its referent. This proposed source aggregate rule does not claim to
reconstruct missing compiler-generated drop glue. Private standard-library,
compiler-lowering, CPU, allocator, kernel and retry implementation work remains
outside the inherited source/call/requested-byte unit.

Actual resource interface and native/resource/backing requests remain mandatory
**positive, independently justified cuts**. The returned expression is therefore:

`45,195,489 + 6*(File_work+File_native) + Error_work+Error_native + Arc_work+Arc_native`

No cut has a default. Each must cover its actual transitive resource contract;
positivity alone is not evidence of a bound. The Error cut includes unknown
backing and transitive dynamic error callbacks. The Arc cut includes the actual
reference-count/final-owner path and backing allowance; an 8-byte handle is no
backing size. The released child candidate's standalone 24-byte allocation probe
is not destructor, allocator-footprint, CPU or refund evidence and is not used to
close these cuts. Resource request sequences are not inferred from the absence
of their standard-library bodies in MIR.

The P0 wrapper hook is excluded. The full MIR retains its authored `Drop`, and
the accepted source takes `owned` before calling the payload destructor. Thus
that P0 hook is at most once and cannot invoke this payload twice during unwind.
This packet cannot replace the separate returned-carrier P5 term: the sixth
child component is the checked sum of positive returned-carrier P5 and positive
actual payload destruction. It must be provisioned before fixture entry and
retained through destruction and eventual retirement.

The seven during-entry payload types are File, Option<File>,
ReturnedLoaderFilesV1, SetupOutcomeV1, SelectedValidatedProfileV1, LoaderFailureV1
and Cancellation. Exact full MIR independently identifies seven setup drop
sites and eleven caller drop sites. Root's immutable child candidate has the
identical roster. Its conservative six setup visits per site plus eleven caller
visits total **53**. `during_entry_payload_destruction_v1` is the maximum cost
of one destruction across all seven types, with each type's own extent and
resource terms. The child component applies the 53 multiplier. This packet
does not apply it a second time or substitute an aggregate cost for a per-visit
maximum. The child lane already charges written drop/control events and typed
transfers; this component covers the body behind those boundaries.

SelectedValidatedProfileV1 contains a boxed byte source, eight metadata vectors
(two Vec<Segment> occurrences), copied metadata/observations and provenance.
Its finite source aggregate allowance is **479,493**, or 413 occurrences times
`(1 + 1,160)`, plus positive source-box and all eight vector resource cuts.
Elements of those vectors have no transitive resource fields or statically
reachable authored destructor. Actual source length, backing capacity and
standard resource requests remain unselected.

The packet also exposes twenty total typed rows, including the leaf shell's
SnapshotScopeV1, SnapshotRunV1, RuntimeControl, AdoptedProof, optional adopted,
optional cache, optional WASI, SnapshotOuterV1 and SnapshotPrimaryRetirementV1
drop cuts. Their source ownership graph is closed to explicit resource
frontiers, while twelve leaf-root inline layout receipts remain pending.
The cache's Vec<SwiftSlot> frontier is expanded rather than hidden in a flat
number: it requires a positive conservative live-element bound, a qualified
SwiftSlot extent, and the complete SwiftSlot element cost with separate positive
Vec<Type>, Vec<DecodedInstruction> and Vec<u32> destructor/backing cuts. SwiftSlot
and these capacities/counts need independent evidence. No parameter is selected
here. A later coordinated compile-only layout query can supply the thirteen
missing size/align observations; no compiler was run for this packet.

The complete immutable source146 MIR contains three authored production Drop
bodies: the excluded P0 PrepaidOwned hook, SessionLease and session::Reservation.
The latter two are absent from this closed payload ownership graph. No
statically reachable product-authored Drop callback occurs in the graph.
Unknown transitive opaque resource callbacks remain inside their positive cuts;
their absence is not claimed. The source inventory separately records Drop
spellings in test or disabled-feature code without treating them as enabled
production bodies. All source declarations, specializations and resource
frontiers are retained in `inventory.json`.

Reproduce the pure checks without changing the frozen packet:

```text
python3 verification/swift-guarded-snapshot-payload-destruction-cost/derive.py --check-only
python3 verification/swift-guarded-snapshot-payload-destruction-cost/freeze.py --check-only
```

`commands/` retains exact pure Python commands, source/tool hashes, output,
time bounds and direct-child completion. Four early checker-only failures are
preserved: copied seal/count text, generic specialization reconciliation,
missing validation-budget graph declaration, and a repeated Segment frontier
key count. They changed no frozen input or product source. The final controls
reject omitted, unknown, zero and malformed resource cuts, missing dynamic
element subcuts, unbound native extents, wrong returned specialization, recursive
unknown ownership and checked arithmetic overflow. Unit input examples are pure
hostile controls, never reviewed values or policy selections.

Only this new packet was written. No frozen program was imported or executed.
No compiler, loader, fixture, VM, cache, scope, writer, constructor, product
executable, native/device/simulator/emulator/UI/capture process, global process
inventory, Git mutation, production action, external message or credential action was
started. Pure Python children completed; no owned native instance or scratch
runtime needed cleanup. Native runtime stays paused. Genuine immutable
executable/build/session/process/caller binding, complete funding, operational
cleanup, immutable separate-repository FieldLog dogfood, native, OTA and GA
qualification remain pending.
