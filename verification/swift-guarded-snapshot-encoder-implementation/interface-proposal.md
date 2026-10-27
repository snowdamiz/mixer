# Guard-derived MIXSNB02 encoder proposal

Status: proposed interface only; implementation awaits root coordination/release.
Owned write boundary: this directory only. The 144-member accepted source remains
unchanged; a new source variant will be copied beneath this directory and its
exact delta recorded. No admission-design or admission-independent input is read.

## Concrete private component interface

The actual encoder lives at `experimental::swift::snapshot_encoder_v2`, inside
the validator's existing private module boundary. Only the following items are
`pub(crate)`; every field and all other constructors/helpers remain private.

```rust
pub(crate) const SNAPSHOT_TRANSFER_BYTES_V2: usize = 4096;
pub(crate) enum SnapshotEncodeErrorV2 {
    MissingSelectedProvenance,
    UnsupportedLayout,
    UnsupportedPolicy,
    Arithmetic,
    InternalField { code: u32, section: u32, index: u64 },
}
pub(crate) struct SnapshotViewV2<'guard> { /* private actual owner borrows */ }
pub(crate) struct SnapshotCursorV2<'guard> { /* private view, header and cursor */ }
pub(crate) struct SnapshotBlockV2<'block> { /* private borrowed bytes + offset */ }

pub(crate) fn borrow_snapshot_v2<'guard>(
    initial: &'guard InitialProfileBorrowV1<'_>,
) -> Result<SnapshotViewV2<'guard>, SnapshotEncodeErrorV2>;

impl<'guard> SnapshotViewV2<'guard> {
    pub(crate) fn into_cursor(self)
        -> Result<SnapshotCursorV2<'guard>, SnapshotEncodeErrorV2>;
}
impl SnapshotCursorV2<'_> {
    pub(crate) fn encoded_extent(&self) -> u64;
    pub(crate) fn emitted_extent(&self) -> u64;
    pub(crate) fn next_block<'block>(
        &mut self,
        transfer: &'block mut [u8; SNAPSHOT_TRANSFER_BYTES_V2],
    ) -> Result<Option<SnapshotBlockV2<'block>>, SnapshotEncodeErrorV2>;
}
impl SnapshotBlockV2<'_> {
    pub(crate) fn bytes(&self) -> &[u8];
    pub(crate) fn offset(&self) -> u64;
    pub(crate) fn is_final(&self) -> bool;
}
```

View and cursor are non-Clone, non-Copy, opaque, with no public parts/raw-proof
constructor. Their owner borrows use `'guard`, not the backing owner's lifetime.
The view retains `&ValidatedSwiftReactor`, `&LoaderProvenanceV1`, and the actual
guard borrow. Runtime/WASI observations are obtained from the same guard owners,
never separate caller claims. `into_cursor` validates complete source-backed
equations, counts/capacities/categories/spans/types/options/policy/layout/caps and
builds one `[u8;2560]` fixed header. The cursor retains that header, view, absolute
offset and bounded section/element/word state; exact concrete fields/layouts will
be recorded before admission composition. No whole-snapshot output Vec exists.
`next_block` fills continuous bytes across section boundaries; its only output
storage is the caller's borrowed 4096-byte array. It consumes no I/O, callback,
foreign proof/provenance/digest/bool, stop token or work grant. A completed cursor
returns `None`; there is no reset/rewind method. Errors retain a finite scalar
code/section/index and carry no owned strings or I/O error.

## Narrow bridge delta in the isolated source variant

- `src/experimental/swift.rs`: declares private `snapshot_encoder_v2` child.
- `src/experimental/account.rs`: immutable private Buffer inventory accessor
  returns `(len,capacity,size_of::<T>(),charged,category)` from actual fields.
- `src/experimental_swift_reactor/cache/initial_profile_v1.rs`: crate-visible
  opaque guard type; immutable proof/selected-provenance/run-budget/owner/scalar/
  optional-WASI observation accessors. Sole guard literal, original constructor,
  header, rows and eight primary outcomes remain unchanged except the gated host
  observation statement described below.
- `src/experimental_swift_reactor/cache.rs` and `mod.rs`: private guard re-export.
- `src/experimental_swift_reactor/retained_profile_loader_v1.rs`: crate-visible
  opaque provenance type and immutable encoding method/accessors over actual
  five limits, source extent, five digests, opaque nonce and four identities.
- `src/experimental_wasi/mod.rs` and `accounted.rs`: narrowly immutable actual
  context `(WasiBudget,WasiGrants)` observation, forwarded through AccountedWasi.
  No ownership mutation, constructor, clone or caller replacement route.

No changes to admission, foundation/construction reservation, cache/work/stop,
writer, outer observations, operational storage or consuming cleanup are claimed.
Each new type/result/Option/move/helper temporary and caller transfer array will
be named in the complete source-place roster with unit/production layouts.

## Proposed genuine-guard host seam for prior approval

Immediately after the unchanged sole guard literal, add only:

```rust
#[cfg(any(test, mixer_snapshot_encoder_host))]
snapshot_encoder_host::observe_v2(&initial);
```

`snapshot_encoder_host` is a private module gated by the same cfg. It takes only
the actual guard, calls this component, independently writes test artifacts and
records assertions. It never constructs a guard, alters owners, grants, primary
outcomes, header or rows. Tests construct a fresh genuine proof through the actual
validator and actual selected loader/adoption path, then invoke the existing
wrapper in the new isolated variant. They do not execute any frozen wrapper or
one-shot runner. Existing selected fixture materials may be reused as read-only
test inputs; the exact feasible loader route will be documented before running.
Ordinary-production Debug/optimized builds omit the observation statement and
host module. Separate ordinary-production crate-internal compiler probes cover
the exact API/privacy lifetimes; external negative probes must still see the
experimental privacy boundary.

Host observations may allocate/write their own expected/artifact bytes solely
outside the production encoder. Encoder allocation observation covers only the
actual borrow/cursor/block calls. Python oracle comparison uses the accepted
corrected model with exact guard-derived expected fields and all nine sections;
it grants no validation or provenance authority. Genuine positive feasibility
and any host-only fixture grant must be explicitly selected by root, and the
original 300000/400000 refusals remain unchanged.

## Verification proposed

Meaningful unit plus ordinary-production Debug/optimized checks; exact full-byte
Python oracle comparison; all-nine-section, actual resolved enum/type/Option,
capacity-slack, multi-block continuity, end-of-stream and private-field coverage;
missing selected-provenance refusal; negative raw-proof/foreign argument/bool/
digest/callback/literal/clone/move/lifetime/mutation compiler controls. Record
command/tools/source manifest/output/cleanup and every complete new type layout.
No native/UI/capture/process inventory, frozen runner replay, Git-index action,
canonical integration or operational storage acceptance.
