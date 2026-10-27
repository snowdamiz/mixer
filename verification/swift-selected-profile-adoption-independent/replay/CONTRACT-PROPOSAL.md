# Private selected-profile runtime adoption proposal

Status: contract preparation; implementation awaits root's exact-roster selection.
Ownership is restricted to this verification directory. No canonical source,
root metadata, frozen packet, commit, or push is changed by this proposal.

Inputs are the immutable real-loader seal
`e1701fb93056b763a06164d7ccf0cae3112f2e27baaa3f4a35aedd8e747665a2`,
independent-review seal
`20841ffd95685e0a65d926c747dfd2c7394341663593cca7c6c01d2c2f329c3f`,
and root's source-traced `real-loader-adoption-next-boundary.json` and scoped
`real-loader-host-acceptance.json`. Frozen orchestration is never rerun.

## Exact private authority and call graph

Define `pub(super) AdoptionBodyV1` in `retained_profile_loader_v1.rs`:

```rust
pub(super) struct AdoptionBodyV1 {
    proof: ValidatedSwiftReactor,
    selected: Option<LoaderProvenanceV1>,
}
```

Fields remain module-private. `LoaderProvenanceV1` becomes nominally
`pub(super)` solely for borrowed typed access; its complete existing fields
remain private, inline, and unchanged. Neither type gains Clone, Copy,
serialization, a raw-proof getter, a parts API, a generic pair constructor,
or an arbitrary selected authority factory.

The only body methods visible to the private parent are `ordinary(proof)`,
which constructs `None`, `proof(&self) -> &ValidatedSwiftReactor`, and
`selected_provenance(&self) -> Option<&LoaderProvenanceV1>`. A derived presence
observation, if needed in tests, is test-only and never grants authority.

`SelectedValidatedProfileV1::adopt(self, budget, started, cancellation)` lives
in the loader module. It consumes the actual non-Clone carrier, creates the
sole `Some(full_original_provenance)` body literal, and immediately calls
`RuntimeControl::adopt_body`. The selected carrier keeps its two existing
borrow/copy inspectors; no owned extraction method is added.

Ordinary call graph:

```text
RuntimeControl::adopt(original proof, original arguments)
  -> AdoptionBodyV1::ordinary(proof) [selected None]
  -> RuntimeControl::adopt_body(body, original arguments)
  -> original complete admission + authentic AdoptedProof
```

Selected call graph:

```text
load_selected_retained_profile_v1(actual File owners, actual budget, cancellation)
  -> complete original validator + byte equality + final metadata recheck
  -> SelectedValidatedProfileV1 { original proof, complete provenance }
  -> SelectedValidatedProfileV1::adopt(self, original run arguments)
  -> AdoptionBodyV1 { original proof, Some(complete provenance) }
  -> same RuntimeControl::adopt_body
  -> same authentic AdoptedProof
  -> same SwiftFunctionCache prepare/construct/complete
```

`RuntimeControl::adopt` retains its exact existing signature. `adopt_body`
contains the one original ledger implementation: all original budget,
deadline, owner, retained source/metadata, control/cancellation, and foundation
admissions remain in their current order. `AdoptedProof` replaces its private
proof field with the body, retains its original two tickets, and forwards only
borrowed proof/provenance access. There is no second ledger or disconnected
wrapper.

On admission failure, `drop(body)` precedes both original proof-ticket refunds
and `finish_owned_cleanup`. In `drop_proof_with_wasi`, body destruction precedes
both independent source and metadata refund attempts. Original failures,
first-failure chronology, snapshots, ownership quarantine, and returned owners
remain typed original payloads. The provenance is inline and allocates no
separate storage, but every source lifetime and move is explicitly counted.

## Exact source migration roster

All paths below are relative to the new owned `source/vm` copy.

- `src/experimental_swift_reactor/retained_profile_loader_v1.rs`: opaque body,
  sole selected consuming adoption, full borrowed provenance, measured private
  loader/adoption layout tuples, and role-correct final metadata recheck.
- `src/experimental_swift_reactor/retained_profile_loader_v1_tests.rs`: actual
  loader-to-adopted/cache flow, full provenance preservation, ordinary absence,
  failure cleanup, layout and role-specific metadata/I/O tests.
- `src/experimental_swift_reactor/control.rs`: shared inner adoption, authentic
  adopted storage, destruction/refunds, explicit adoption entry/move/cleanup
  inventories, foundation construction and final-boundary composition.
- `src/experimental_swift_reactor/cache.rs`: affected owner/failure/partial and
  transfer layout reporting and source-lifetime inventories. Header accounting
  continues subtracting only original `ValidatedSwiftReactor`; body sidecar
  bytes remain in the actual cache remainder. Refresh all affected cleanup,
  construction, operation and preflight envelopes from actual embedded types.
- `src/experimental_swift_reactor/execution.rs`: affected bootstrap,
  construction, move, final and cleanup inventory assertions and exact layout
  literals. No execution semantics or limits change.
- `src/experimental_swift_reactor/cache/initial_profile_v1.rs`: preserve all
  eight constructor variants and the sole fresh initial guard; expand layout
  roster capacity and measure all wrapper input/phase/emission/caller/moves.
- `src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs`:
  keep all original IDs1..165 and types; append and compare new loader/adoption
  records to actual compile-time layout measurements.
- `src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs`: update
  measured affected old literals and append new exact records; budgets remain
  identical. Production and unit selections must describe their real config.
- `src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs` and
  `compile_contracts.rs`: complete layout, all-outcome, guard chronology,
  actual-owner, failure/refund and budget matrix migration.
- `cache_tests.rs` / `execution_tests.rs` only for exact affected old layout or
  budget assertions; any additional necessary path requires coordination.

No source changes are planned outside this roster. The independent host11
support copy is an immutable baseline; new harnesses and compiler cases live
under this lane and have their own manifest/identities.

## Layout and accounting process

Keep all original 165 records even when their sizes do not change. Append all
23 loader measurement classes already separately reported by the accepted
loader, then the new body, optional complete provenance, borrowed provenance,
adoption entry/move/cleanup inventories, and actual pair/result/option transfer
owners. A final exact appended roster is retained before literals are promoted.
Private loader types are measured where defined; const size/alignment tuples
allow comparison without making their fields or constructors visible.

Measure ordinary production and unit configurations separately in debug and
optimized modes. Unit hooks can enlarge owners; a unit-only number must never
stand in for production. Preserve all first compilation/assertion/test failures.
Collect prospective measurements first, review them, then promote literal
changes and rerun strict actual-versus-selected comparisons. No literal is
derived dynamically at runtime to bypass a selected-profile mismatch.

The adoption inventory names ordinary proof input, selected carrier input,
body literal/source/argument/return, optional provenance and full provenance
move, admitted pair/result/option and caller transfer places, failure payloads,
destruction arguments, original ticket/refund results and cleanup snapshots.
Compose required places into the initial foundation before dependent
preparation; a later enlargement cannot retroactively cover them. Recompute
cache/header/construction/operation/final envelopes using the actual full owner
types. Source-lifetime accounting is conservative requested storage, not RSS,
allocator overhead or physical compiler stack.

Loader File owners and pre-adoption allocations retain separate accounting.
Their numeric fit does not grant operational runtime admission. Runtime ledger
zero does not prove external descriptor close or name cleanup. No cap is raised;
newly insufficient narrowed budgets must retain honest typed refusal.

## Required bounded tests

- Genuine retained source/build/session/executable input produces the selected
  carrier; consume it into authentic adopted/cache owners and compare every
  original provenance field through a borrow. Keep actual Files independently
  returned/owned throughout and preserve original I/O/validation failures.
- Ordinary adoption keeps its signature and produces no selected provenance.
- Positive consumer compilation; negative literal, private field, Clone,
  deserialization, proof/provenance owned escape, parts/pair/mint bypass and
  cross-owner controls. Borrow lifetimes must prevent owner mutation/move.
- Original admission budget/deadline/cancellation/owner exhaustion behavior;
  failure drops before refunds; both independent refund failures retain their
  original errors and quarantine rather than healthy zero.
- All eight original constructor variants retain real adopted/cache/failure
  owners and original phase completion payloads. Verify original prepare,
  construct, complete, owner, initial-state and sole fresh-guard chronology.
- Exact old165 plus appended production/unit layouts and source-lifetime
  envelopes; original limit ceilings and narrowed refusal matrices.
- R1: final recheck uses Source, Build, Session, Executable respectively.
  Focused metadata mismatch and original metadata I/O error tests assert exact
  role, offset and error payload for each File; the four owners still return.

No snapshot/export/context route is added. Native/UI/capture/runtime process
inventories remain paused. Trusted-launcher and quiescent-host limitations,
raw pathname/argv unrun cases, package authentication, exporter/context,
operational loader storage, FieldLog, OTA/store/customer and GA remain pending.
