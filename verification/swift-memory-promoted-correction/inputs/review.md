# Independent Swift Load/Store behavior review

**Request changes for one accounting omission.** The bounded private behavior
checks pass, but the candidate does not satisfy its complete positive-inventory
contract. Root acceptance and integration must wait for a corrected frozen packet
and review of the affected unit inventory/layouts. This review makes no release
or GA acceptance decision.

The reviewed 123-file candidate is
`6046a5fa8ba3800ec168b7ae6a80cb82bad5ba39b8701cb23a5db720d998bb62`.
Its accepted 121-file baseline is
`241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`.
Every execution uses an independently extracted authoritative archive, never the
mutable live VM. The producer checker passes all 1,451 bindings and the live
baseline check. The review packet binds the source archives, tools, commands,
actual executables, outputs, failed attempts and cleanup.

## Blocking finding

**MR01: Count the unit caller's actual promoted backing and return separately.**
Both fresh Swift-only and all-feature unit MIR contain:

```text
const memory_pinned_step::promoted[0]: &LocalKey<Cell<bool>>
_0: &std::thread::LocalKey<std::cell::Cell<bool>>
_1: std::thread::LocalKey<std::cell::Cell<bool>>
```

This compiler-owned promotion belongs to the actual `tests::PC_OVERFLOW.with`
call site at candidate `src/experimental_swift_reactor/memory_operations.rs:190`.
The producer's own frozen canonical unit MIR also contains it. Its promotion
selector requires `memory_operations::` in the constant name; the compiler names
this body `memory_pinned_step::promoted[0]`, so it is skipped. The 4,792-field
schema counts the caller's `_55` reference but neither promoted binding. Reusing
that reference, another alias, padding or a previously counted owner would
violate the explicit separate-position contract.

Each missing binding needs source, argument, returned and caller positions:
eight additional unit fields. A fresh standalone compiler layout probe observes
8-byte size/alignment for each type: 64 additional named unit bytes. The unit
canonical inventory therefore requires 2,164 fields and the complete inventory
requires 4,800 fields. The existing schema has 2,156 and 4,792 respectively.
The production inventory has no corresponding omission. Regenerate the corrected
schema, final MIR audit, actual unit containing bounds, paired layouts, source
closure, command/executable receipts and frozen checker; the measured current
unit bounds cannot establish coverage for omitted fields.

Evidence: `mir-results.json`, `omitted-promotion-swift-unit.mir`,
`omitted-promotion-all-unit.mir`, `promotion-type-layout` command and
`inventory-results.json` in the review packet. The checker deliberately verifies
this finding and reports `request-changes`; it does not turn a known omission
into an accounting pass.

## Reproduced behavior and authority

All sixteen exact MM01–MM16 names pass once in each Swift-only/all-feature
Debug/Release configuration: 64 selected memory tests. Existing frame/control
and value selections pass in all four configurations: 34 and 12 tests per
configuration. The AF22 source comparison confirms that only the memory active
term was added once to its existing formula; the other scaffold changes expose
existing functions/fields. Regression semantics remain intact.

The actual caller copies the selected instruction/function through the original
retained pin and cache view. Its immutable view ends before mutable effects.
Fuel/instruction, caller work and checked PC each occur once, and the helper
adds no instruction/fuel or PC movement. Early active/cache/missing instruction,
charging and PC errors publish an inner failure, mark terminal/draining state
and stop. `Ok` publication is distinct from the stored operation result. Both
caller and helper preserve occupied success/failure slots and the original first
failure; successful outcomes are taken before reuse. Compiler and runtime
receipts cover the concrete changed hook call-site types, subject to MR01.

MM06 distinguishes cancellation before instruction charging from cancellation
at caller work after the instruction/fuel debit. Helper work/cancellation tests
preserve the exact pop/width/push effect prefix and prohibit partial stores.
MM09 exercises held original pins, retained debt and explicit cleanup-only retry.
MM11 covers occupied success/failure slots in both caller and helper. MM13 uses
58 warmed original-owner fixtures: all 23 forms succeed and trap, with additional
work/cancel checkpoints, under first-allocation refusal with zero observed
allocation/reallocation requests. MM14 explicitly records Frozen feature absence
in Swift-only; it receives no Frozen execution credit from that message.

Six independently authored adversarial tests pass in each configuration, for
24 additional selected tests. They exercise final valid/one-byte-invalid ranges
with nonzero offsets and independent widths for every form; all 27 wrong store
type combinations while preserving a caller/local floor; successive actual
pinned decoding and result taking; actual caller success/trap/occupied paths
under allocation refusal; store post-pop debt with the original Cleanup failure;
and one failed deepest-pin release while other pins drain, followed by explicit
cleanup reacquisition and bound restoration. They reuse original constructed
584-page owners and accepted methods, with no replacement engine, accounting
carrier or duplicated load/store implementation. The largest case has 46 fixture
owners, no fixture exceeds 64 helper attempts, and no case exceeds three frames.
Execution is serial within each selection.

Separate actual Frozen baseline/candidate runs match all 28 observations in
Debug and Release: 56 pairs covering values, bytes, traps, work, fuel, cache and
allocation requests. The original 16-test Frozen integration suite passes on
both archives in both profiles. These small Frozen fixtures use at most two
pages, eight guest instructions and one frame.

Sixteen fresh actual paired metadata layouts reproduce the current candidate
and baseline sizes, alignments and offsets. All fourteen original containing
owner declarations and layouts remain unchanged. The candidate's existing
4,792 schema fields compile with disjoint measured positions, but MR01 prevents
calling that inventory complete. Four fresh production/unit MIR configurations
independently reproduce every existing canonical binding, alias and typed
literal; they include capture payloads, the qualified unit width body and all
promoted bodies, which exposes MR01. The 39 complete expanded Frozen methods
are identical. Frozen reservation is 2,912 bytes, ticket authority remains 86,
State/Combined limits remain 128/256MiB, and dependency manifests are unchanged.

## Failed attempts and limits

One independent runtime test initially compared the entire first failure after
drain; the original drain correctly adds `after_cleanup` usage. Its failed exact
source and outputs are preserved. The corrected assertion preserves the original
diagnostic and `at_failure` observation while requiring cleanup enrichment.
Independent parser drafts also needed complete array types, repeated alias
multiplicity, feature-dependent qualification and compiler indentation. Their
sources and failure descriptions are retained. The final broader promotion audit
found MR01; no candidate implementation was changed by this reviewer.

The existing post-pop absent-cursor/resource `Cleanup` diagnostic is preserved
and is separate from MR01. G08 remains open. Unreconciled debt never counts as
restoration. All memory bounds here are host logical requested/named-object
bounds, with no compiler-stack, allocator-overhead or RSS claim. No native/UI,
simulator/emulator, physical-phone, full Swift ABI, Ready/public Swift invocation,
publication, signing, store, customer, operational or GA qualification ran.
Swift bulk memory/growth, full dispatch/native joins, and separately published
immutable FieldLog consumption remain pending. Owned scratch is archived and
removed; other project files and processes are preserved.
