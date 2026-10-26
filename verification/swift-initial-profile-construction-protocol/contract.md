# Initial profile construction protocol V1

This packet proposes exact private data types, ownership, source boundaries and
local structural constants for root and independent review. Product implementation
remains unselected. `protocol-types.rs` is a data-only model; the retained isolated
probe measures it alongside exact original types, without calling a constructor,
minting a guard, encoding a header or writing rows. No runtime or header authority
follows from compilation. The root amendment selection and its complete finite
17-field budget are copied under `inputs/root`; their assigned hashes are checked.

## Closed signatures and privacy

Future product source has this one private orchestration entry point, inside
`cache::initial_profile_v1`:

```rust
fn construct_with_initial_profile_v1(
    cache_out: &mut Option<SwiftFunctionCache>,
    control: &mut RuntimeControl,
    wasi: Option<&AccountedWasi>,
    adopted: AdoptedProof,
    selected: &SelectedInitialProfileV1,
    claims: &UnverifiedProfileDigestBytesV1,
    row_output: &mut File,
) -> InitialProfileConstructionOutcomeV1;

fn write_initial_profile_rows_v1(
    initial: &InitialProfileBorrowV1<'_>,
    output: &mut File,
) -> Result<ProfileRowsObservationV1, ProfileAdapterErrorV1>;

fn profile_scalars_v1(
    initial: &InitialProfileBorrowV1<'_>,
) -> Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>;

fn encode_profile_header_v1(
    initial: &InitialProfileBorrowV1<'_>,
    claims: &UnverifiedProfileDigestBytesV1,
) -> Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>;

fn selected_initial_profile_v1() -> &'static SelectedInitialProfileV1;

fn compare_local_structure_v1(
    selected: &SelectedLocalStructureV1,
) -> Result<(), ProfileHeaderErrorV1>;
```

The wrapper selects the same fixed constructor cursor used for this component:
`Cursor { stage: SwiftRunStage::Initialization, function: None, offset: None }`.
It has no caller cursor or general owner/closure parameter. The two encoding
helpers perform no owner mutation or I/O. Header construction returns 512 bytes
in the outcome; the row writer receives a distinct retained, empty, offset-zero
File and keeps its existing admission, progress, attempt and error semantics.
No composer, hashing, path opening or profile-output File exists in this slice.

The guard, all fields, helper types and producer are private inside the wrapper
module; its child modules may inspect the shared guard. No guard constructor,
cache-taking borrow function, general proof accessor, arbitrary callback,
async/reentry seam, clone/copy implementation or reference escapes the module.
The wrapper contains the sole guard struct literal, only after successful real
phase completion and every guard check. It borrows the caller's actual cache
slot and shared reborrows of the same control and optional WASI, retaining these
through header and row emission. `scalars` is a checked fixed 64-byte copy, not
another owner. The row bridge reads `initial.cache.proof()` directly and passes
it to the unchanged accepted `write_profile_row_body_v1`; no independent proof,
descriptor, owner scalar or raw rows are arguments.

## Exact closed outcome

`protocol-types.rs` fixes the complete Rust fields. `#[repr(u32)]` assigns the
following discriminants; they are private source choices, not an external ABI.
Every original `SwiftRunFailure` is retained unchanged, including its cursor,
first-failure data, usage and cleanup observations. No text/error-code conversion
replaces an original runtime failure. A `Result<(), SwiftRunFailure>` remains the
actual phase-completion result, preserving both failures when construction and
completion fail independently.

| Tag and variant | Construction | Completion | Header | Rows | Surviving owner |
| --- | --- | --- | --- | --- | --- |
| 1 `SlotOccupied { adopted }` | not attempted | not attempted | not attempted | not attempted | consumed real adopted returned; existing cache untouched |
| 2 `SelectionRefused { error, adopted }` | not attempted | not attempted | not attempted | not attempted | consumed real adopted returned |
| 3 `PreparationFailed { failure, adopted }` | not attempted; prepare failed | not attempted | not attempted | not attempted | consumed real adopted returned |
| 4 `ConstructionFailed { failure: CacheConstructionFailure, completion }` | failed | exact Ok/Err retained | not attempted | not attempted | exact optional `failure.rejected_adopted` retained |
| 5 `PhaseCompletionFailed { failure }` | succeeded | failed | not attempted | not attempted | caller `cache_out` is Some |
| 6 `HeaderRefused { error }` | succeeded | succeeded | failed with fixed profile error | not attempted | caller `cache_out` is Some |
| 7 `HeaderOwnerCheckFailed { failure }` | succeeded | succeeded | failed with exact original runtime owner-check error | not attempted | caller `cache_out` is Some |
| 8 `HeaderEncoded { header, rows }` | succeeded | succeeded | succeeded, bytes retained | exact Ok/Err retained | caller `cache_out` is Some |

There is no successful variant with rows not attempted, or header-refusal variant
with a successful row observation. A header remains available if rows fail after
partial acknowledged output. Tags 2 and 6 use the proposed fixed 16-byte profile
error `{code:u32, stage:u32, offset:u64}`. An occupied slot has its own tag and
does not invent a ninth header error. Intermediate admission is the closed
`ProfileAdmissionFailureV1::{Refused=1(ProfileHeaderErrorV1),
Runtime=2(SwiftRunFailure)}` sum. Runtime-check errors choose tag 7, never code 3
in place of their original failure. Profile code 3 is limited to a defensive
local ownership-invariant refusal that produced no runtime error. Error 6 means
only mismatch/unavailability of the named local structural constants below;
external build identity remains separate. The rest of the preparation's error
codes/stages/offsets and byte map remain as amended by root.

`#[must_use]` on the proposed outcome calls out its cleanup responsibility.
Dropping a Rust proof/ticket field is not a ledger refund. A caller must destructure
owned payloads and use their actual owning control. In particular, slot refusal
and failed owner pairing may return an adopted proof belonging to a different
control; the supplied control must never refund that foreign proof. A constructor
failure with `rejected_adopted: None` already consumed its adopted owner through
the unchanged partial cleanup and must not replay that cleanup. Every constructed
cache remains in the caller slot on completion/header/row failure. No wrapper
cleanup silently destroys it, no diagnostic failure invokes a refund, and no
runtime failure is cleared or reclassified.

## Closed execution order and original types

1. If `cache_out.is_some()`, return tag 1 before reading that cache, the selected
   record, claims or output File. Preserve the consumed `AdoptedProof` inline.
2. Compare all 17 selected budget fields, every canonical ceiling, and the named
   local structural constants before preparation. Refusal returns tag 2 plus the
   untouched adopted proof; no constructor/phase/output was attempted. Test-only
   explicit alternative full records are separate from the selected producer.
3. Keep `preparation: Option<Result<CacheConstructionPhase<'_>, SwiftRunFailure>>`
   and move its success phase out with `take`. Invoke unchanged
   `SwiftFunctionCache::prepare(control, wasi, &adopted, cursor)` once. On failure,
   retain its exact failure and adopted owner (tag 3). No phase exists to complete.
4. Keep the original `ConstructionReturnSlot =
   Option<Result<SwiftFunctionCache, CacheConstructionFailure>>`. Invoke unchanged
   `CacheConstructionPhase::construct(&mut self, adopted)` exactly once. Move the
   successful cache into caller `cache_out`, or retain the entire exact failure
   inline for tag 4. Do not copy or rebuild either owner. `CacheConstructionFailure`
   has exactly `failure: SwiftRunFailure, rejected_adopted: Option<AdoptedProof>`;
   `AdoptedProof` contains the actual sealed proof and its source/metadata tickets.
5. In both construct-result branches invoke the unchanged
   `CacheConstructionPhase::complete<T>(self, returned_phase_storage: T)
   -> Result<(), SwiftRunFailure>` once with
   `T = (Option<Result<CacheConstructionPhase<'_>, SwiftRunFailure>>,
   ConstructionReturnSlot)`. Both supplied original slots have been taken and
   are None. The actual phase consumes their storage before restoring the prior
   construction bound. Retain its original Ok/Err. Construct failure returns
   tag 4 with both typed results; construct success plus completion failure
   returns tag 5 with the cache still in the caller slot.
6. In the remaining success branch inspect actual supported proof and exact
   initial cache shape, original authentic owner/ticket/category/byte checks,
   B/reservation/capacity and actual lengths/capacities. Runtime owner-check errors
   survive as tag 7; fixed profile refusals as tag 6. Only then create the one
   private guard. No acquisition, prepare_operation, control admission, mutable
   cache/control/WASI access, guest/native code or suspension is reachable.
7. While the shared guard lives, only the named scalar/encoding helpers and
   guard-to-row bridge run. The only writer closure is the unchanged accepted
   private adapter's fixed `File.write` closure, never a caller callback. Preserve
   exact header bytes and exact row result in tag 8. End the guard before return.

For later actual cache cleanup the original signature is
`SwiftFunctionCache::cleanup<'a>(owned: &mut Option<Self>,
control: &'a mut RuntimeControl, wasi: Option<&'a AccountedWasi>)
-> Result<CacheCleanupTail<'a>, SwiftRunFailure>`.
On cleanup preflight error the cache remains in its slot. On success its original
tail must consume caller owner/return/outcome storage through
`CacheCleanupTail::complete<T>(self, returned_phase_storage: T,
outcome: &mut Option<SwiftRunFailure>)`. This original tail has the actual shared
accounting header and original optional cleanup failure; do not substitute a
profile result for it. The implementation/caller accounting review must include
the new larger outcome/move/storage places through this boundary and all early
branches before claiming the unchanged limits suffice. Layout measurements alone
do not prove that join or authorize any construction-bound enlargement.

The complete initial invariant includes all SwiftCacheUsage fields except
fixed_reserved equal to constructor defaults, exact free pin records, empty
resident slots/plans/index, nonce 1, exact patch/plan/index lengths and capacities,
zero control live cache entries/pins and actual Cache current==B. Other
runtime/state/WASI owners are allowed. Supplied Some(WASI) proves authentic common
control ownership; None is allowed. B equality excludes unrelated positive Cache
bytes, and asserts nothing about unrelated zero-byte Cache tickets.

## Named local structural selection

`local-structure-proposal.json` supplies literal proposed values for one reviewed
`SELECTED_INITIAL_PROFILE_V1` static. The sole production producer is
`selected::selected_initial_profile_v1() -> &'static SelectedInitialProfileV1`.
No caller constructor, bool, external authority record or freshly generated
expected-layout table is admitted. Root must select these exact literals before
implementation; the later comparator computes actual size/alignment and compares
against those fixed literals. This packet runs a measurement probe only and does
not report a successful product comparison.

The immutable record has the exact 17-field SwiftRunBudget plus
`SelectedLocalStructureV1`. That structural record contains the schema, entry
count, word width, little-endian marker, header/row byte counts, row count,
header-word/digest-slot/digest-byte/trailing-zero counts, outcome/error schema
versions, the four original cleanup/header/construction/operation formula values,
selected maximum slots/pins, fixed B at that maximum, and all 165 complete type
sizes/alignments. Each entry has `{id:u32, reserved:u32=0, bytes:u64, alignment:u64}`;
ordered IDs/types are fixed by `local-layout-type-index.json`. The derived-field
mapping is: `cache_cleanup_bytes <- cache_cleanup_temporary_bytes`,
`cache_header_bytes <- cache_header_bytes`, `cache_construction_bytes <-
cache_construction_bytes`, `cache_operation_bytes <- cache_operation_bytes`, and
`cache_fixed_at_selected_maxslots <- cache_fixed_64_slots_64_pins`.

The actual Rust1.99.0 aarch64-apple-darwin Debug/optimized probes agree on all 165
entries. Original H=92,128, B(64 slots,64 pins)=118,240 and cleanup inventory=62,888
bytes. The fixed outcome is 2,912 bytes; the guard 88; selected record 4,216;
proposed caller 12,312; phase storage 6,912; emission storage 4,768; disjoint move
inventory 14,040. These listed types have alignment 8. The complete table retains
every alignment, complete Results/Options, original phase/cleanup types and
File/Metadata/I/O transfers; aggregate H/cleanup values are byte formulas, not
fabricated complete Rust types with a made-up alignment. Vec payload extents,
actual lengths/capacities and actual lifetime/source-work bounds require the
later real implementation and tests.

The probe-source manifest has 136 files: exact canonical132 plus row2, the row
module delta, then two named probe-only files and three declared probe bridges.
It includes the three canonical C headers and none of the four archived changes.
The external receipt binds source tree, rustc executable/version/hash, target
cfg/features/data layout, optimization commands and measured executable hashes.
Executables and all owned compiler/TMP/Cargo scratch were removed after retained
outputs were hashed. That external provenance does not make the product helper
verify source, compiler, executable, receipt or any of the eight opaque claims.

## Exact proposed next source closure

Use another fresh canonical132+row2+row module delta, with these six new files:

- `src/experimental_swift_reactor/cache/initial_profile_v1.rs`: wrapper, sole
  guard literal, private fixed types, original-result choreography and row bridge.
- `src/experimental_swift_reactor/cache/initial_profile_v1/header.rs`: checked
  fixed scalar derivation and pure field-by-field 512-byte encoding.
- `src/experimental_swift_reactor/cache/initial_profile_v1/selected.rs`: sole
  immutable complete budget/local selection literal and producer.
- `src/experimental_swift_reactor/cache/initial_profile_v1/local_structure.rs`:
  explicit named actual layout comparisons against selected literals.
- `src/experimental_swift_reactor/cache/initial_profile_v1/tests.rs`: finite
  actual-owner/constructor/phase/header/row/failure and layout tests.
- `src/experimental_swift_reactor/cache/initial_profile_v1/compile_contracts.rs`:
  test-only signature, privacy and forbidden-lifetime compile cases.

The sole original-source production delta is the private `initial_profile_v1`
module declaration in `cache.rs`; the accepted row `mod.rs` delta remains exact.
The resulting distribution is 140 named paths. A separately named finite host
runner is `verification/swift-initial-profile-construction-host/run_component.py`.
Its fixed compiler-input roster, each under that host folder's `compile_cases/`,
is `positive_contract.rs`, `guard_literal_from_sibling.rs`, `guard_escape.rs`,
`proof_escape.rs`, `cache_move.rs`, `cache_mutation.rs`, `control_mutation.rs`,
`row_foreign_snapshot.rs`, `callback_reentry.rs`, and
`external_selection_literal.rs`. These ten retained sources are authored fixed
fixtures owned by the named compile_contracts test module; the runner records
their exact placement/injection and compiler argv so a case cannot pass merely
because an unrelated module failed to import. There is no generic callback or
runtime fixture injection in the product path. The runner and these ten inputs
are inventoried separately, giving 140 distribution paths plus 11 named host
support sources, rather than silently including support in the 140 count.
Any extra harness, generated Rust source, manifest or bridge requires a revised
exact closure/count before acceptance.
Do not reuse the old exact132 analyzer verifier as if it covers this expansion.

`test-plan.md` defines the finite next verification. No full suite/full target,
archived instrumentation merge, canonical integration, digest/custody/composer,
real context, actual runtime, native/device, FieldLog, CI or GA claim is selected.
