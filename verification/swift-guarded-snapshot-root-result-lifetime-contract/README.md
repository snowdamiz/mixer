# IR02 accessible-result lifetime proposal

This packet proposes the next source slice; it does not select or implement it.
The root coordinator requested the minimum accessible-result lifetime repair,
with no new durable shutdown, lease, allocation, Arc, registry or synchronization
mechanism. All original IR01 permanent-retention behavior remains binding.

The selected proposal uses a real `&'root BootstrapLedgerV1` in an opaque private
`RootBoundV1<'root, T>` envelope. The reference comes only from the consumed
original attempt's acquisition reservation. The short owner borrow and the
original root borrow are separate. A result may outlive its acquisition owner
when the original root remains alive; it may not remain accessible after that
root ends. Binding the result to `'owner` alone would unnecessarily prohibit
the former and would obscure which ledger actually funds it.

`OwnedCorrelationOutcomeV1<'root>` becomes an opaque struct instead of a visible
enum. Its private payload retains the complete selected proof or original
loader/correlation failure, all returned Files including executable Some/None,
and original usage. Every matching/refusal branch keeps the original attempt's
root, including a mismatched foreign expected owner. A mismatch must not choose
the foreign expected owner's root. The actual private generic core gets the same
root-bearing return wrapper as the File facade; tests may substitute guards,
but may not substitute a separate structural ownership program.

The existing public `CorrelatedSelectedProfileV1` reexport and its bare
`into_selected_v1() -> SelectedValidatedProfileV1` escape are removed. The name
may remain as a module-private transition. Its private `into_selected_v1`
returns a bound complete selection bundle, including files and usage. There is
no generic consuming callback, `map`, `into_inner`, `into_parts`, Deref,
AsRef/AsMut, mutable payload borrow, public field or owned error/file projection
available outside the loader's private owner module. A private generic mapper
inside that module is permitted only with a finite reviewed callsite inventory;
it must preserve the exact original reference on every branch.

The sole caller-visible consuming operation after correlation is a fixed
`run_fixture_once_v1`: it takes ownership of rows, snapshot, cancellation and
claims, and returns an opaque `RootBoundFixtureOutcomeV1<'root>`. Its private
fixed leaf operation runs only on the correlated variant. The original reference
is kept in the enclosing live frame while the raw selected proof moves through
`into_snapshot_scope_v1`, `SelectedSnapshotBodyV1`, `AdoptionBodyV1`,
`RuntimeControl`/`AdoptedProof`, `SnapshotScopeV1` and `SnapshotRunV1`, using
their existing visible methods inside the loader's private owner module. Both
original `SnapshotScopeFinishV1` and `SnapshotPreScopeFailureV1` are immediately
captured in the bound return. No callback or mutable scope access escapes that
fixed synchronous operation. A panic unwinds through this frame and cannot
return a bare proof or result. Existing raw control/cache types and the
uncorrelated fixture path keep their APIs; this is a guarantee about the
admitted/correlated family, not a claim that every unrelated raw loader use is
root-funded.

The cache's private admitted path creates an opaque
`AdmittedFixtureOutcomeV1<'root>` using the actual attempt's original-root
reference before setup. Its setup-refusal variant owns the original setup io
error and partial Files; its loaded variant owns the complete bound fixture
result. The separate child wrapper is
`PrepaidOwnedV1<'child, AdmittedFixtureOutcomeV1<'root>>`. The two lifetime
parameters name separate accounts. The original unadmitted
`OwnedFixtureOutcomeV1` stays separate, avoiding an invented `'static` root or
an optional absent root. Account/quote refusal before dispatch returns only the
original account refusal and no newly captured resource payload.

Inspection returns short shared references to originals or scalar observations,
tied to the borrow of the opaque carrier. There is no mutable or owning
projection. Independently copied scalar failure fields and usage observations
may outlive the root; they are not the original backing/owner. This repair does
not claim that caller-created, separately funded copies of observed bytes retain
the original charge. The existing outer path still observes and destroys its child,
then releases only the child destruction token, then retires the acquisition
owner and returns scalar observations. A child destruction token can outlive
the original-root borrow only after the complete child payload was destroyed;
it contains no original proof, File, diagnostic or acquisition refund authority.

## Exact proposed source ownership

Future implementation is confined to a new isolated overlay with these two
changed existing distribution members:

- `src/experimental_swift_reactor/retained_profile_loader_v1.rs`: private
  original-root envelope, two-lifetime scope inputs, opaque correlation and
  fixed fixture-return API, private transitions, borrow-only views and tests.
- `src/experimental_swift_reactor/cache/initial_profile_v1.rs`: separate bound
  admitted container and child signatures, fixed consuming leaf-call wiring,
  diagnostic observation and destruction wiring, and tests.

No new distribution member. `control.rs`, `cache.rs`, all submodule sources,
`host_account_v1.rs` and exact host11 support are unchanged. The existing raw
`run_one_loaded_fixture_v1` remains on the unadmitted path. Its enclosing
`cache::initial_profile_v1` module is private, so it is not callable from the
loader merely because the function has ancestor visibility. The admitted
fixed leaf instead uses existing `SelectedValidatedProfileV1` and
`SnapshotScopeV1` methods directly inside the loader's owner module. If
implementation cannot retain these boundaries,
the lane must return for a new contract; it may not widen visibility, add a raw
extractor, public callback, allocation or additional changed source member.
All new private transitions, captures, move/return places and borrow-view places
need a fresh exact source/MIR/layout/funding review before their sizes/prices are
accepted. A reference-sized field is not permission to reuse old prices.

## What this repair does and does not establish

After a future successful compiler review, a usable opaque admitted result,
borrowed original diagnostic, selected transition or final child resource
container cannot outlive its original ledger in safe code through the published
facade. Raw private code can always be edited to destructure an envelope; its
visibility is not a compiler proof against the implementation itself. Therefore
the finite private construction/destructure/return inventory and the absence of
test-only unwrappers are mandatory source review evidence.

`mem::forget(result)` consumes the result, leaving no accessible original
payload through that handle. Rust may then end the root borrow. The original
storage charge remains retained while the ledger exists; the lexical end or
forgetting of that stack ledger is not durable funding of leaked backing.
Likewise `mem::forget(root)` can bypass any destructor and must not be described
as a healthy shutdown. This proposal adds no Drop abort, panic-on-drop,
outstanding counter, root-close API, or externally owned funding lease. It
therefore does not close forgotten-result/forgotten-root funding, ordinary
root-shutdown accounting, or full root/result charge lifetime. These remain
explicit followons. A stack counter that vanished cannot certify an accounted
leak; this packet makes no such claim.

IR01 remains unchanged: issuing any correlation scope permanently blocks the
acquisition Complete token and whole-storage refund, including unused,
destroyed, extracted, refused or forgotten results. No branch clears the
barrier, renews reservation/cleanup work, or obtains a joint-retirement token.
Native bootstrap policy/startup/allocator/custody and healthy native close,
production selectors, new prices/layouts, FieldLog, OTA and GA remain Pending.

`signature-contract.rs.txt` fixes the proposed API shape; `test-roster.json`
fixes prospective compiler/host evidence. This packet performed only source
reads, hashing and artifact consistency checks. No compiler, product, native,
UI, capture, network or Git operation was run. The root is responsible for a
later source selection and a separately bounded compiler/test budget.
