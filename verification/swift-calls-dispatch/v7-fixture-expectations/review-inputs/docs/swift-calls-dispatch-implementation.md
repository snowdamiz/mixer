# Private Swift calls and full dispatch implementation candidate

This isolated candidate is in `verification/swift-calls-dispatch/candidate/`.
The live VM is unchanged. The exact 128-file accepted baseline is closure
`1e89853d56f0ae46720cb0e9d72a4a2a13003f777e1d01f65db154f30782ed9c`,
selected by `verification/swift-calls-dispatch-root-review/selection.json`.
Implementation, complete accounting, executable CD01–CD24 qualification,
independent review and root integration are separate evidence states. Until the
sealed receipt says otherwise, runtime and accounting acceptance are pending.

The current source is the 130-file closure
`ba9231499244692bbed61f0566ec72864a979df9e3fc71511560ec66a2e00c70`,
archived by `candidate-final-source.json`. Exactly eight VM files differ inside
the private copied crate. The rejected earlier closure `3d0840…c0041` and its
method inputs remain under `revisions/v4-review-rejected-3d0840/`; its exact
64-parameter signature path could compare the result as scalar 65 between
checks. No evidence for that source qualifies the corrected source.

The candidate extracts the original run, direct-call and indirect-call
orchestration into static macros. One exhaustive match covers the 27 admitted
Operation variants. Owner access, diagnostics, fetch/prefix, fixed publication,
finish and guarded local/global access are static leaves. Numeric, control,
load/store, bulk-memory and growth algorithms remain the original shared bodies;
Swift frame entry, imported host dispatch and consuming completion retain their
original owners. No new instance/cache/proof/WASI context, arena, ticket, public
invocation API or Ready transition is added. The Frozen regression check compares
all 39 expanded method bodies, including run and call, byte for byte against a
fresh expansion of the accepted baseline. Its original 2,912-byte bound remains.

Root approved the following exact interruption schedule during implementation:
retain the existing `params` work debit for direct calls and imported calls;
retain the indirect signature scan debit `expected.params + actual.params`;
add an ordinary `check_with_wasi` before the first parameter comparison, after
at most 64 scalar comparisons, and at final completion. These checks add no
execution work debit. Existing entry and host parameter scans receive the same
schedule. Comparison and guard failures retain the actual instruction cursor and
RuntimeControl's original first failure. This amendment changes only the Swift
owner path. Frozen work, error order and expansion are unchanged.

The exact indirect schedule is: check before comparing; compare parameters in
order; check after each successful parameter at zero-based index 63, 127, and so
on; compare the optional result; check before returning that result. A parameter
mismatch checks before returning immediately. A length mismatch checks before
returning. Thus exactly 64 parameters receive a check before the optional result
comparison. Entry and host parameter loops retain their existing parameter work
formulas and check before indices 64, 128, and so on, then check at completion;
they do not compare an optional result. Explicit 64- and 65-parameter fixtures
cancel at every selected check and assert independent check and instruction
counts. This distinction between the signature, entry and imported-host owners
is intentional.

Full dispatch uses `prepare_growth` even without a grow instruction. Fetch ends
all cache/frame metadata views before instruction fuel, outer work, checked PC
advance or any arm effect. Imported calls use the existing host parameter debit;
defined calls reuse argument arena slots and acquire one move-only pin per
frame. Indirect calls consume the selector once and compare ordered parameter
and optional result types structurally. All operation publications are inspected;
an outer successful publication does not authorize execution after a stored
failure. Terminal cleanup releases pending original growth storage and drains
frames, then consumes the complete phase/context/growth/fixed-storage carrier
through `complete_growth`.

The only owner-preflight correction replaces missing WASI, cache and State
`expect` panics in private `prepare_growth` with an Invariant from the existing
RuntimeControl. WASI absence has no snapshot to supply; cache/State absence
retains the actual available WASI usage. Those checks precede owner mutation,
new admission, pin acquisition and frame entry. They neither manufacture nor
replace any ledger, owner or control. Missing RuntimeControl remains outside
the admitted constructor boundary and has a separate caught-panic diagnostic;
it is not credited as successful CD01 typed failure behavior. Present-owner
growth ticket splitting, allocation, copy, swap, refund and completion are the
original algorithms.

All compiler and runtime attempts are archived with source closures, commands,
raw output, tools and available executables before owned scratch is removed.
Failures remain evidence. Accounting selects explicit complete compiler headers,
including bare free function names, their closure/promoted descendants and every
changed original body. Source/argument/return/caller placements, typed aliases,
closures, Try/residuals and literals receive disjoint additive named rows.
Root confirmed that test fixture builders/assertions are inventoried separately:
they execute outside admitted product execution, and their fixture allocation
must not become product admission credit. Runtime-reachable unit hooks and TLS
bodies remain in the charged partition. Bounds describe named logical objects,
not physical stack or RSS.

The final V5 inventory contains 89,124 distinct named roles: 87,644 ordinary
exact typed fields, 432 exact inferred never-type fields, 16 exact private Kind
fields, and 1,032 finite compiler-layout positions. The last group is a separate
numeric proof method: 560 original actual-closure positions, 248 original
private-std positions, 96 compiler-discovered TLS closure positions, 112 actual
closure constant positions, eight exact PhantomData constant positions and
eight exact `std::alloc::Global` constant positions. It is not a set of typed
surrogate fields. Zero-sized positions remain explicit, with actual identity
and alignment; they are not dropped as optimizer eliminations.

Stable type inference instantiates `NeverActivePositions<!>` and
`NeverPermanentPositions<!>` from an uncalled `fn() -> !` item. `Infallible` is
not a replacement for `!`. Kind fields live in a child of the original defining
module with no visibility widening. `AtomicBool` is the genuine public alias
for the original atomic bool type. Closure capture tuples, byte arrays,
pointer erasure and same-size substitutes receive no typed credit. The original
failed complete declaration, the 560 tuple substitutions and the failed unstable
Global declaration attempts remain retained historical evidence.

There are 82,768 active roles and 6,356 permanent roles. Every complete
`prepare_growth` and call-dispatch `complete` body, including compiler closure
and promoted descendants, is permanent. That moves 6,320 roles from the rejected
all-active placement; the original 36 complete-carrier permanent roles stay
separate. `temporal-position-mapping-v5.json` records each role's phase, and the
V4-to-V5 source correction removes 32 scanner-only typed roles after eliminating
the former redundant loop predicate. Another 1,936 scanner descriptors are
explicitly recompiled/renumbered in the old-to-final mapping; each retains its
actual final type and proof method. Those are rejected-candidate comparisons,
not credit carried from old rows. Original baseline accounting positions are
never removed or reused.

The temporal proof uses the existing execution header, not a newly invented
phase owner. Original construction admits the complete header before allocating
and publishing State. `original_owners` verifies that exact header before
`prepare_growth` performs its work. Header ownership survives the active frame
enlargement and original frame-bound restoration, so it still covers all
preparation and consuming-completion return/caller storage. Original final
cleanup consumes returned storage through `drop_cleanup_return_storage` before
refunding that header. Merely renaming an active field would not establish this
lifetime; the source paths and actual final header formula are both review
inputs.

Each numeric position has a checked aligned interval in a distinct active or
permanent, production or unit component. Final formulas add the full compiler
size of the corresponding exact typed class, exact inferred-never class, exact
Kind class and the selected numeric components using checked addition. They add
to the original frame/header formulas without subtracting old rows, overlapping
old padding or raising a limit. The compiler reports every typed field's actual
type, size, alignment and offset, including named zero-sized fields. The paired
layout report checks all prior Positions/Inventory classes and seven original
owner layouts. Maximum tickets remains 86, State 128 MiB and Combined 256 MiB.

The compiler tool is a small metadata-only `rustc_driver`, built against the
matching official Rust 1.99.0 commit
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, LLVM 23.1.1,
`aarch64-apple-darwin`. It queries `tcx.layout_of` on each actual MIR local type,
constant and implicit function item; full MIR headers include free functions,
closures, promoted and anonymous TLS constant bodies. Concrete function-item
operands are inventoried separately with actual DefPathHash and zero-byte,
alignment-one layout. Compiler session DefId indices can change when source
items are added; the exact finite reconciliation retains both raw displays and
requires unchanged DefPathHash, full path, generic arguments, role and complete
layout. Only numeric session indices are ignored for that display comparison.

Union fields from all eight compiler contexts also require a separate contextual
identity proof. `identity_bridge.py` compares the actual recursive compiler type
graph, including pointer/reference distinction and mutability, tuple elements,
array lengths, generic type/const arguments, function ABI/safety/variadics and
higher-ranked binders. For local definitions it retains both raw contextual
hashes and requires an explicit contextual hash reconstruction after matching
the exact compiler disambiguated definition path, frozen file bytes and compiler
span bytes. Both hash halves depend on the crate seed. The tool reconstructs
every path step with the official pinned StableHasher algorithm, asserting the
exact root and final hashes against `tcx.def_path_hash`. The previously rejected
local-hash equality assumption remains archived. The hash interpretation and
algorithm are bound to the official retained `def_id.rs` and `definitions.rs`.
External definitions retain
exact raw DefPathHash and crate identity against the pinned official sysroot.
Missing, ambiguous or unsupported graph nodes reject the packet.

Every union field type has a deduplicated compiler-produced `type-layout` record,
even when that type does not occur as a local in the destination context. The
bridge compares complete bytes/alignment, fields and offsets, variants and tag
metadata, resolving every contained field identity through the same actual
compiler graph. Captured aliases use this full actual type record rather than
their shallow capture-transfer row. Same-size changed primitive, mutability,
definition, generic-argument, binder, crate-seed, path-step, disambiguator and raw
hash controls must all reject. These records
strengthen proof only; they do not change product source or grant acceptance.

Official distribution manifest and component checksums, exact compiler/sysroot
bytes, driver source/build commands, raw query output, field/variant metadata,
licenses and diagnostic-only runtime exclusion are retained in
`tool-preparation/20261024T160529443594Z/` and the referenced attempts. No
installer or shared toolchain configuration is changed. This compiler component
is tooling within the repository's existing official Rust dependency, and is
never linked into Mixer runtime. Compiler diagnostic flags do not authorize a
product language feature or public runtime route.

`inventory_v5.py` treats a type-name classifier only as a proposal. Every numeric
proposal must match the exact preselected 1,032-field set, canonical type/body
identity, position, config, binding and full layout. A missing or new field,
different actual type, unsupported compiler output, incomplete local/header,
duplicate role, missing layout, overflow or excess bound rejects the packet.
`finite-exception-reconciliation-v5.json` records the full old-to-final mapping;
root's final finite selection and independent review are still separate gates.
The final inventory is regenerated directly from the final eight query hashes.
Reservation literals changed by the final formula are retained as actual final
MIR values and reconciled explicitly; they are not erased from the proof.

Metadata probes execute only size/offset/formula printers in disposable copied
overlays. Their append-only projection to the frozen source is bound per run.
They do not construct a reactor, validate Wasm, enter frames or invoke dispatch.
The sixteen baseline/candidate layouts and eight candidate MIR contexts cover
Swift-only/all-features, Debug/Release and production/unit separately. Frozen's
2,912-byte formula is independently recomputed from actual compiler sizes in
all four all-features contexts, in addition to the 39 expanded-body comparison.

The only newly appended helpers in the eighth changed test file borrow and arm
the existing old-refund/cancellation TLS slots before admitted execution. A
fixture guard restores every original ticket/foreign owner/check setting on
ordinary return and unwind; a caught fixture panic tests that restoration. The
original TLS declarations and runtime hook bodies remain an exact baseline
prefix. Complete compiler partitions inventory fixture construction, assertions
and compile-only accounting helpers separately. Direct compiler callee identity
records and the harness boundary must prove that these fixture helpers do not
execute during admitted product execution; naming alone is not an exemption.

The 60 development fixtures execute the actual copied production dispatch with
original validation, cache, WASI, State, pins and growth owners. They include all
27 operation variants and the CD01–CD24 prefixes, an independent 21-instruction
mixed program trace, cold-cache and growth allocation measurements, and warm
cached dispatch under a rejecting allocator. Development passes are explicitly
unqualified while accounting review is pending. After independent acceptance,
root must select qualified execution of all four feature/profile contexts,
library/Frozen regressions and required admission/allocation checks on the same
sealed source. A passing diagnostic does not discharge that gate.

Physical phones remain disconnected and deferred. No native test instance is
created by this packet. The full Swift artifact, initialization/Ready lifecycle,
source mapping, native parity, immutable separate-repository FieldLog dogfood,
OTA publication, signing/store, customer/operational and GA gates remain open.
