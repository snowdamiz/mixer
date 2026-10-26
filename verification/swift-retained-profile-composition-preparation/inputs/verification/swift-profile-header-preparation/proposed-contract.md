# Closed private scalar/header proposal

Select design review only. Root has accepted the isolated row-body host component
in the bound new acceptance record; real construction/header composition remains
unimplemented and unselected. No public type, getter, enum discriminant, CLI,
fixture parser, allocation/debit cap or existing File protocol changes here.

## 1. Exact construction borrow before any acquisition

Propose a private `InitialProfileBorrowV1<'a>` declared inside the future selected
cache module. Its fields and constructor are private. It holds shared borrows of
one actual `SwiftFunctionCache`, its paired immutable `RuntimeControl`, and the
matching optional `AccountedWasi`; it is neither Clone nor Copy. A successful
constructor borrows through the existing real owner/control pairing preflight;
no raw scalar record, trait implementation, File, event or supplied bool can mint
it. Only a safe actual successful cache construction can reach it. No alternate
validator, adopted-proof constructor, prepaid receipt or raw row import is added.

Conceptual signatures (not compiled source or a measured layout):

```rust
// Private in the exact selected cache module, then consumed by a sibling helper.
fn borrow_initial_profile_v1<'a>(
    cache: &'a SwiftFunctionCache,
    control: &'a mut RuntimeControl,
    wasi: Option<&'a AccountedWasi>,
    selected: &SelectedInvocationBudgetV1,
) -> Result<InitialProfileBorrowV1<'a>, ProfileHeaderErrorV1>;

fn profile_scalars_v1(
    initial: &InitialProfileBorrowV1<'_>,
) -> Result<InitialProfileScalarsV1, ProfileHeaderErrorV1>;

fn encode_profile_header_v1(
    initial: &InitialProfileBorrowV1<'_>,
    claims: &UnverifiedProfileDigestBytesV1,
) -> Result<UnverifiedProfileHeaderV1, ProfileHeaderErrorV1>;
```

`SelectedInvocationBudgetV1` is a private immutable complete17-field scalar record
in canonical `SwiftRunBudget` field order, never `..Default` in admission. Its
future producer must come from a root-selected closed invocation record. The
constructor compares all17 values to the actual control's immutable budget and
checks every existing canonical envelope ceiling. The header subset cannot prove
this comparison or stand in for the complete budget binding in selection. This
proposal selects no invocation budget. Historical retained defaults and finite
narrowings are candidate evidence only.

Derive the snapshot through this cache's actual `proof()`; do not accept a second
snapshot argument that might refer to another owner. Require supported validator
revision1/policy `swift-reactor-experiment-v1`, decoder revision1, imports34,
validated_bodies=defined_functions, checked imports+defined<=80,000 and
actual types<=MAX32. Derive actual source extent and types from this same owner.
The row body must later use that identical retained owner. Its identity can never
be learned from a stream event, previous profile, matching body bytes, fixture
context or digest claim.

At the exact success point after construction and before any cache acquisition,
require actual slot length/capacity equal
`min(actual_budget.cache_entries, actual_defined_functions)`, pin length/capacity
equal actual budget active_pins, and both actual counts in1..64. Require actual
nonce1, no resident entries/pins/recency state, all free pin records, empty plan
cells and initial zero resident index, resident/pinned/construction/live-pin
counts zero, and zero hit/miss/decode/eviction counters. Inspect actual bounded
fields; do not infer virgin state from counters alone. All relevant constructor
success/owner/ticket/capacity checks must already have completed. A failed or
partially cleaned constructor produces no initial borrow. Zero slots (including
zero defined functions) or zero pins is unsupported by the existing profile/
fixture grammar even where the VM itself can construct that narrowed budget;
return unsupported, never clamp to1 or widen the parser.

The selected control may have other runtime/WASI/state owners. Initial Cache
category current must equal the actual cache fixed reservationB and resident
bytes must be0, with no unrelated Cache-category owner. Bind the exact paired
control/WASI identity through existing owner checks; unrelated cache/control,
foreign reservation, missing header, post-acquire/released cache, noninitial
nonce, nonempty plan/index or impossible count/layout refuses. These are new
source paths and require their own actual owner-preserving adversarial controls.
No mutable acquisition can run while the initial borrow exists.

## 2. Exact measured layout and reservation receipt

The source definesH/B exactly as in `source-review.md`. Use checked arithmetic for
all additions/products/subtraction/narrowing, including full cached header and
cleanup inventory. The header's cache_base isB, cache_capacity is the actual
selected `budget.cache_bytes`, and entry_limit is actual
`budget.cache_entry_bytes`. Require known complete layouts and B<=capacity.
No extra requirement `entry_limit<=capacity` or `entry_limit>0` is invented;
existing narrowed budgets can fail only on later acquisitions while their
construction/header remains meaningful. Initial cache cannot come from the first
MissReady event or a field copied from an old compiler receipt.

A future exact-source Debug and optimized layout producer must measure and record
`size_of` **and alignment** of at least SwiftFunctionCache, ValidatedSwiftReactor,
SwiftSlot, PinRecord, decode::Patch, Option<ScanPlan>, the complete cleanup
inventory andH, plus constructor/operation/cleanup reservations, actual Vec
lengths/capacities, all new private header/borrow/error types and complete Results,
arguments, caller tuples, File/Metadata/write/composer transfers where applicable.
Bind rustc executable/hash/`-vV`, target triple/data layout, feature/cfg/optimization,
source manifest/patch/build output and header/profile adapter executable hashes.
No layout number is selected by this preparation. Existing row measurements and
historical emission layouts are compiler/source-scoped evidence only.

The independent accounting review must join new borrowed owners, all complete
Results/caller/return/move/error places, source loops and simultaneous lifetimes
with the actual constructor/runtime/analyzer phases. The accepted row union
11,912/13,904 bytes is not an additional budget allowance; neither its source
bound450,652,288 nor the fixture29,344-byte union/7,048 groups authorizes the new
combination. Retained source/metadata and validation scratch/work stay separately
charged under existing limits. No VM reservation/debit change follows.

## 3. Pure fixed header serialization, with explicit unverified claims

`InitialProfileScalarsV1` has private fixed scalar fields and no authority bits.
`UnverifiedProfileDigestBytesV1` holds exactly eight `[u8;32]` slots, named in
`contract.json`. It is explicitly caller-supplied opaque content for encoding;
its existence, nonzero bytes, syntax or equality with context grants no verified
claim. It contains no whole profile, File, String/Vec, snapshot borrow or key.
`UnverifiedProfileHeaderV1` holds exactly `[u8;512]`; it has no acceptance getter.
Encode field by field in little endian according to `contract.json`. Never write
a Rust memory image/cast/transmute. All reserved bytes are0. Do not add the final
selection digest to this header, which would cycle when selection binds the
complete profile hash. This pure serialization function performs no hashing,
I/O, signing, path open, durability or custody operation.

Propose fixed private `ProfileHeaderErrorV1 {code:u32,stage:u32,offset:u64}`:
1 unsupported snapshot policy (stage1),2 unavailable/different complete selected
budget (stage1),3 cache/control ownership mismatch (stage1),4 noninitial cache
(stage2),5 slots/pins unsupported or inconsistent (stage2),6 unavailable/different
layout/build identity (stage3),7 reservation/capacity mismatch (stage3),8 checked
arithmetic/narrowing failure (current stage). Offset is the relevant header byte
coordinate when one exists;0 for owner/budget/virgin-state failures. Stages1/2/3
are owner/budget, initial construction, layout/reservation; stage4 is encoding.
There is no error success value, owned string, raw error text, File, key or owner.
Measure the complete Error/Result/caller before implementation acceptance.
The numerical error code proposal has no public ABI promise or implementation.

## 4. Separate retained-descriptor composition/digest/custody dependency

The accepted row writer requires **empty File at offset0**, one4,096-byte block,
625 blocks,32 write calls/block and20,000 calls/file. It writes2,560,000 bytes.
Writing this512-byte header to the same File first would violate that admission.
Do not silently make the row writer append, seek around a header, reopen/truncate
a path or change its offsets/errors. Root can separately select a future protocol
amendment only after fresh review; this proposal chooses a distinct composition
component instead.

The future standard-library host component first derives the actual row-body File
from the same retained validated owner, hashes its actual2,560,000 bytes with
`hashlib.sha256` through its retained descriptor, then obtains the header's
opaque digest bytes from independently verified exact artifacts. It creates one
separate exclusive/no-follow initially empty profile output, encodes/writes the
512-byte header and streams the exact retained row-body bytes after it. The
profile is exactly2,560,512 bytes. Borrowed/partial/write bytes and descriptor
ownership survive failures truthfully; no output rollback/durability is implied.
Use one fixed bounded buffer with an independently selected complete work/
logical-place/attempt/cleanup proof. This source is not implemented or authorized
by scalar encoding, and it does not inherit the row writer's20,000-call bound or
the accepted analyzer's reservations.

Hash the complete retained profile and its body subrange independently, both
before and after any consumer run, checking profile-body hash equals the actual
row-body File hash and header slot7. Also hash and verify the original input,
canonical complete source manifests/patch, exact event schema, compiled profile
adapter binary/build receipt, complete measured layout receipt and the exact
canonical immutable validated-snapshot binding record. That last record's stable
schema/bytes and provenance are themselves a missing dependency; never hash a
Rust pointer/object image or label source-only hash as a whole validated snapshot
without a selected record definition. Baseline/candidate digest preimages must be
exact canonical manifest bytes with accepted build/source provenance, not an
ambiguous concatenation. All eight slot meanings/preimages need closed schema
versions in the future selection-verification contract.

Use standard cryptography only. Rust std has no SHA-256 API; no custom crypto or
new crypto dependency is proposed. Digest-byte serialization is not proof. The
separate accepted analyzer design requires retained same-descriptor pre/post
hashing, regular/no-follow parent/component/path identity and exact lengths,
exclusive outputs, bounded reads/writes/EOF, closed launch argv/pass_fds, exactly
once private child descriptor adoption, no parent reads/seeks while inherited
OFDs are live, and terminal child/reap/cleanup. The existing fixture runner proves
trusted quiescent fixture evidence only. Current receipts do not prove hostile
path races or coordinated rewriting; unsupported custody must remain unavailable.
The independent host64M selection-verification and18M replay-custody proposals
have their own fixed scopes/limits and missing implementation proofs. The new
composition step must not silently borrow those budgets or expand their scopes.

## 5. Real context and acceptance remain separate

Keep `MIXFIX01` parser and all literal-false authority getters unchanged. It uses
opaque echoes and checks only selected baseline/candidate/schema joins; importing
real hashes into those slots does not create real binding. A colluding synthetic
profile/event can satisfy a finite fixture without actual snapshot provenance.
The future actual context has a separately named, closed supported schema;
no magic/version is selected here. It must retain exact8192 bytes partitioned as
selection<=4096 + original-result<=2048 + custody<=2048 with reserved0, exact
adapter versions/lengths/digest offsets, real selected source/schema/tool/target/
complete budget binding and host verification receipts. It must admit only after
all prerequisites are independently verified. No caller bool or phase mask is
an authority seam.

Real context additionally needs the strict typed original result and raw bytes,
original optional failure cursor preserved even pre-meter, applicable failure
kind/code/stage/resource/attempted/limit, original terminal result, at-failure/final
work/instructions, all15 final reservation/live/ticket comparisons, refund/
quarantine and lifecycle/cleanup correspondence, and accepted writer/selection/
custody receipts. These dependencies cannot be derived from row success or
this header. A phase-only bridge does not exercise full body-identity semantics.

Real replay/semantic metrics/report joins/private CLI/custody/full-target/native/
FieldLog acceptance are later separately selected slices. Rust prefix observation
can never set fullReplayAccepted by itself. A future accepted host join can report
complete-records or only truncated-prefix under CAP, without claiming guest
success or a known uncaptured tail. All original invalid/failure15 and failed
whole-suite receipts stay immutable. No runtime/release/GA authority is selected.
