# Fixture acquisition/lifecycle envelope contract

This packet proposes the next bounded **contract**, for separate review before
implementation selection. Its finite Python model observes acquisition stages,
operation/function continuity, closed wire forms and lifecycle ordering. It is
independent of the active Rust framing implementation and imports none of it.
There is no Rust integration, real context, semantic replay, target execution or
release authority. `fullReplayAccepted=false`, `storedPrefixValidated=false` and
semantic metric validity remain false in every observation, refusal and failure.
No semantic record counter or metric becomes valid through this model.

The initial137-member freeze was **not accepted**: independent review found
R1 widened type scalars, R2 disconnected the retained candidate owner from the
leaf interface/setup lifetime, and R3 allowed poisoned CAP finish and an
AttributeError on non-CAP finish. The full original freeze plus seal pair is
preserved and byte verified in `history/first-freeze/packet.tar.gz` (139 members,
archive SHA256 `ee5bfd08111a0bd0993b91814add86948622e041d003eb85a6cad678edabdbdc`).
This is the separately authorized amendment, still requiring independent review;
the earlier passing finite tests do not erase those findings.

The binding scope remains `mixer-product-plan.md`, including independently owned
engine implementation, both native platforms, published-package FieldLog and all
GA requirements. `PLAN.md` is an execution index. Computer use, capture, native
simulator/emulator runtime and phones remain paused. This packet uses Python
standard-library finite checks and a standalone Rust value-layout host probe;
no native simulator/emulator or capture process is started or queried.

## Immutable inputs and authority

The accepted design seal is
`c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8`
(67 members); its independent review seal is
`da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc`
(212). Root acceptance is copied from
`verification/swift-ordered-retention-analyzer-root-review/acceptance.json`.
The runner hashes every member before and after, plus all 566 members of the
three upstream prototype/completion/review seals: **845 members total**. Exact
consulted source copies, source lengths/hashes, tool identity, commands and
outputs are retained inside this owned packet. Nothing changes an old packet.

The accepted design's `interface_schema.py` fixes state IDs. Wire coordinates
come from the accepted copied `writer.rs` and `observer.rs`; the exact 24-code
table is copied unchanged. Those sources prove structural ranges and emission
coordinates, not universal applicability of every code/kind/stage combination.
The accepted copied borrowed cache and Swift cache/control source establish the
synchronous acquisition envelope. Relevant copied-source lines are:

| Evidence | Copied source and lines | Implication |
| --- | --- | --- |
| Record fields and closed forms | `writer.rs` 11–56 | Sixteen u64 words; kinds 1–14; closed payload forms |
| Operation/phase assignment | `observer.rs` 84–109 | Phase inherited except Phase; pin/terminal Failure discrimination |
| Original failure coordinate | `observer.rs` 104–109 | Original optional function and at-failure work/instructions |
| Acquire then check header | Swift `cache.rs` 1926–1954 | Header failure can precede requested-function meter adoption |
| Caller cursor storage | Swift `cache.rs` 1530–1554, 1362–1377 | Pre-meter error uses caller's original optional cursor |
| Meter cursor adoption | Swift `cache.rs` 2118–2133 | Later meter sets requested function; this does not constrain every failure |
| Miss/hit and stage hooks | borrowed `cache/borrowed.rs` 765–912 | Lookup, scan/plan, readiness, eviction, build, publication ordering |
| Plan hook variants | Swift `cache.rs` 2203–2268 | PlanEnd empty/conflict/match forms share one next state |
| Release hook | borrowed `cache/borrowed.rs` 710; Swift `cache.rs` 1431–1436 | Successful release is separate from acquisition and has no new stop check |

The table uses shortened names for the copied paths under
`verification/swift-ordered-retention-analyzer-design/inputs`; their complete
names and immutable hashes are in `commands/run-1/result.json`. No source is
restored, compiled or run. The historical 17 invalid/failure15 sidecars retain
their classifications. No current framing source or test is consulted.

## Closed wire forms

Input is a borrowed 16-word fixture record:
`seq,kind,phase,op,work,instructions,function,offset,len,type,slot,pin_slot,nonce,a,b,c`.
Every scalar must be an actual u64, kind 1–14 and phase 0–5. MAX means absent
only where specified. Full body means function<80,000, offset/len != MAX,
type<=u32::MAX and checked offset+len without u64 overflow. Release also requires
type<=u32::MAX. This fixed source width is independent of an unavailable profile
join; type0 and typeMAX32 pass width alone, while type2^32/MAX64-1 fail. Actual
type<count remains unavailable: a later accepted profile would also reject
typeMAX32 because its count is<=MAX32. A structural body does **not** mean a profile,
source extent, defined body or immutable body identity has been verified.
Unmentioned slots are MAX, nonce is zero, and payload words are zero.

| Kind | Fixture form checked by this envelope |
| --- | --- |
| 1 AcquireBegin | nonzero op, function<80,000, absent offset/len/type |
| 2 Lookup | nonzero op/full body; a0 miss/slotMAX or a1 hit/slot<64; b/c0 |
| 3 PlanBegin | nonzero op/full body; a/b0; c=function&511 |
| 4 PlanEnd | nonzero op/full body; a0 empty or a2 match requires bMAX; a1 conflict requires b<80,000 and b!=function; c=function&511 |
| 5 MissReady | nonzero op/full body; a>0, checked b+a<=c |
| 6/7/8 EvictBegin/Taken/Commit | nonzero op/full acquiring body; slot<64, a>0, b/c0 |
| 9/10 BuildBegin/Ready | nonzero op/full body; a>0, b/c0 |
| 11 PinPublished | nonzero op/full body; slot/pin_slot<64, nonce>0; a0 hit or a1 built; b>0,c1..64 |
| 12 Release | op0,function<80,000,offset!=MAX,type<=MAX32,lenMAX; slot/pin_slot<64,nonce>0,a>0,b0,c0..63 |
| 13 Phase | op0, function/offset/len/typeMAX; a=record phase,b/c0 |
| 14 Failure | absent body; original optional functionMAX or <80,000; a kind1..21,b code1..24,c stage1..6; op discriminates below |

The fixed wire maxima 64/512 are structural. The selected actual slot/pin/entry
limits, profile and resident bytes remain unavailable. Examples passing these
ranges must never be described as valid tokens, correct victims or applicable
failures. Code0 is refused; this does not repair CODE-invalid historical output.

## Complete stage table and guards

Initial state is Idle0, phase0, mask1, last operation0 and no failure latches.
Each record's seq is exactly accepted+1; work/instructions never decrease.
These coordinates denote the fixture observation extent, not a validated
semantic-prefix count. Checked u64 overflow refuses the whole next record.

The table enumerates all **11 states × 14 kinds = 154 combinations**. A dash
refuses the combination even when its wire form is otherwise well formed. All
cells require the shared guards below; `I` means Idle0, `H/M` depends on Lookup.

| State | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Idle0 | Acquire1 | — | — | — | — | — | — | — | — | — | — | I | I | I terminal |
| Acquire1 | — | Hit2/Miss3 | — | — | — | — | — | — | — | — | — | — | — | I pin |
| Hit2 | — | — | — | — | — | — | — | — | — | — | I hit | — | — | I pin |
| Miss3 | — | — | Scan4 | — | — | — | — | — | — | — | — | — | — | I pin |
| Scan4 | — | — | — | Plan5 | — | — | — | — | — | — | — | — | — | I pin |
| Plan5 | — | — | — | — | Ready6 | — | — | — | — | — | — | — | — | I pin |
| Ready6 | — | — | — | — | — | EvictBegin7 | — | — | Build9 | — | — | — | — | I pin |
| EvictBegin7 | — | — | — | — | — | — | EvictTaken8 | — | — | — | — | — | — | I pin |
| EvictTaken8 | — | — | — | — | — | — | — | Ready6 | — | — | — | — | — | I pin |
| Build9 | — | — | — | — | — | — | — | — | — | Built10 | — | — | — | I pin |
| Built10 | — | — | — | — | — | — | — | — | — | — | I built | — | — | I pin |

AcquireBegin requires Idle, phase<4, no failure latch, last_operation<MAX and
op=last_operation+1. It stores requested function and active operation. Normal
kinds 2–11 require exactly that function and operation; publication form must
be a0 from Hit or a1 from Built. The FSM does not join body offset/len/type,
bytes, destination, planned masks, tokens, nonce increments or pin counts to
semantic state. Every such check remains a separate unavailable dependency.

Normal non-Phase records retain current phase. Phase requires Idle and strictly
increases to<=5 with a=phase and a previously absent observed-mask bit. It may
skip phases; no intermediate bit or missing event is invented. A closed envelope
observation requires Idle, phase5 and the fixture's exact expected mask. Phase5
is terminal: **every later ordinary kind, including Release, Phase and Failure,
is refused**. At phase4 no new acquisition is possible; Idle Release, one
terminal Failure and advance to Phase5 remain observable.

Release requires Idle and phase<5, including after a pin or terminal failure.
It uses op0 and need not name the last acquired function. Each of the ten open
states refuses it. Its token/resident ownership is unverified; idle-only is
necessary to protect the source's synchronous first-free-pin selection, but is
not sufficient to prove a successful real release.

A nonzero Failure requires an open state, exactly its active operation, and no
previous pin/terminal failure. It closes to Idle and sets the pin-failure latch.
It preserves the actual point where success ended; no implied Taken/Commit,
scan/build completion or publication is created. An op0 terminal Failure requires
Idle and is unique. After either failure, AcquireBegin and every kind2–11 are
forbidden. A pin Failure may be followed by its separate terminal Failure,
Release and legal Phase advances. A terminal Failure can exist without any
acquisition. A second terminal Failure, a terminal Failure during an open pin,
an op-mismatched pin Failure and a resumed stage all fail closed.

**Failure.function is an exception to requested-function continuity.** The
observer emits the original optional cursor. Header checks can fail after
AcquireBegin but before the meter adopts the requested function, so absent or
different cursors cannot be refused by a fabricated equality rule. Root confirms
this source reading. Closed kind/code/stage ranges and op0/nonzero envelope
classification are observations only. Code/kind/resource/stage/cursor
applicability, original-result equality, failure/footer termination and cleanup
ledger equality remain unavailable. The finite tests intentionally admit
in-range triples whose source applicability is unproved, with all semantic
authority false. This is a documented unavailable check, not a permissive
production failure validator.

An intact externally framed sole-CAP stream may cut at **any** observed state,
including an open scan, build, eviction or acquisition. The observation is
`CapCutUnknownTail`; it never invents the closure, terminal Failure, phase5,
mask bits or an uncaptured tail. This packet neither parses nor validates the
footer/CAP/custody framing itself. Missing framing authority is unavailable.
The finish boundary first inspects the retained private status/reply. Poison
or absent state returns fixed `InternalPoisoned` for both CAP and non-CAP;
unsupported state returns `UnavailableState`. It cannot take the CAP branch
first, emit a normal boundary name, dereference an absent state, or turn poison
back into Idle. This also applies if an InternalPoisoned reply accidentally
retains a stale nonempty state field. No subsequent record can resume it.

## Minimal interface and explicit version boundary

Proposed internal interface, requiring separately reviewed implementation:

```rust
type Candidate2048 = [u8; 2048]; // private alias, no wrapper move
fn observe_fixture_envelope_v1(
    arena: &mut [u8], candidate: &mut Candidate2048,
    words: &[u64; 16], steps: &mut StepBudget
) -> FixtureEnvelopeReplyV1;
```

The private orchestrator owns exactly one local `Candidate2048` throughout
setup, its record loop and finish. After reserving the complete534 setup debits,
it initializes that local once from `[0u8;2048]`. The conservative initialization
inventory counts the complete2048-byte literal/source and2048-byte retained
destination, plus the complete borrows/locals/error/return roles below. No
helper returns the candidate by value; no wrapper embeds/moves it, no closure
captures it, and it is never a return/error payload. The logical literal/source
dies before the first record call. Initialization and its source-to-destination
move/copy each debit256 eight-byte units even if the compiler elides a move.
This is a declaration/lifetime contract, not an implemented Rust initializer.

For each record, the orchestrator lends one short exclusive mutable candidate
borrow to the leaf. Both the caller8-byte and callee8-byte sized-array borrows
are charged; internal slice views are separately charged. They and every nested
view end before the next call or any finish/drop. The candidate owner stays in
the orchestrator's same local storage and is not copied or re-zeroed per record.
Each admitted call overwrites exactly12 scalar payload words; the other bytes
remain zero from setup. Refusal discards scratch values without treating them
as semantic state. Poison ends the loop, preserves a fixed poisoned reply for
finish, and allows no later call to reconstruct a state. The reply borrows no
candidate/arena bytes and contains no owner reference.

On setup error, the initialized local, if it exists, leaves lexical scope while
only a fixed reply is returned. On ordinary/refused/poisoned finish it likewise
leaves scope after all borrows end. It is a byte array with no custom Drop or
resource owner; do not pass it by value to a drop helper or allocate another
array for cleanup. The finite `FixtureEnvelope` class models one initialization,
stable owner identity, repeated payload overwrites, refusal, poison and close;
its Python storage is not the proposed Rust layout or allocator qualification.

This is a **private leaf**, with no public reexport or arbitrary-word authority
entry point. A future selected fixture-library orchestrator must construct the
initial projector itself, retain the sole arena owner, and call the leaf with
the explicit retained candidate borrow and
an immutable borrow of the record its own reviewed framing path just decoded
from its existing safe File borrow. It accepts no caller-provided `framed`,
`identity_verified`, `context_verified`, `prefix_valid` or acceptance boolean.
The call order, fixed borrow, private state construction and final framing
failure propagation need explicit integration source review; this packet does
not claim compatibility with the uninspected framing implementation's types.
Any type used to carry the internal record has private constructors and cannot
be forged by a public caller to skip that framing path. No new File adoption,
open, clone, descriptor owner or profile/context authority is introduced.

Even that internal decoded-record borrow does not prove complete File framing:
a later malformed record/footer, shortened file or framing refusal invalidates
the orchestrator's framing outcome. The envelope reply can never upgrade it.
It never asserts File/profile framing was performed at all. Fixture-model
callers intentionally construct arbitrary tuples for negatives; those Python
tuples are not a public Rust construction API, framing receipt or trust token.
Unavailable real profile/context/custody bindings remain unavailable through
every internal path. There is no route from this leaf to an acceptance join or
release classification; both acceptance fields remain hard zero.

The reply is a fresh, fixed logical `[u64;16]` (128 bytes): status, reason,
accepted fixture coordinate, state, phase, mask, last operation, active op,
requested function, pin-failure latch, terminal-failure latch, last work, last
instructions, debit, fullReplayAccepted0, storedPrefixValidated0. Requested
function/active op are meaningful only while state!=Idle; stale cells are
guarded by the discriminator. Status is Observed/Refused/InternalPoisoned;
reasons are fixed integer enums, never allocated strings. Python reason strings
are fixture harness conveniences only. `semanticMetricsValid` is always false;
it is not a new report field. The reply contains no semantic counts/list/map.
Status IDs are Observed1, Refused2, InternalPoisoned3. Reason IDs are Observed0,
Steps1, Shape2, Coordinate3, TerminalPhase4, Phase5, ReleaseOpen6,
TerminalFailure7, PinFailure8, ForbiddenResume9, Acquire10, Identity11, Stage12,
PublicationForm13, CheckedAccess14, InternalPoisoned15. Unsupported values refuse
the new interface; this does not assign report decision IDs.

This type is **not a binary report extension**. The accepted report's word15
`validity_mask` has no assigned FSM bit. Decisions CompleteRecords and
TruncatedPrefix require unavailable host authority; AnalysisLimited does not
grant semantic prefix validity. Report reserved fields stay zero, its existing
version/49,152-byte layout is unchanged, and existing readers are not claimed
to understand this new return type. No bit or reserved word is repurposed.
Serialization or any production/report mapping needs an explicit versioned
contract, compatibility review and tests before selection. Fixture observations
may be saved only in this separate preparatory host receipt, not substituted
for the fixed Rust report or an acceptance join.

## Exact arena cells and candidate delta

Arena ceiling stays 8,388,608 bytes. Its scalar region begins at 7,729,760 and
has the accepted 512 u64 cells. The envelope may touch exactly the following
**12 existing named cells = 96 bytes**, with no new region or reserved-cell use.
Table indices are relative to that scalar region.

| Model name | Accepted symbolic cell | Index | Absolute byte offset |
| --- | --- | ---: | ---: |
| accepted | control.accepted_records | 7 | 7,729,816 |
| work | control.last_work | 9 | 7,729,832 |
| instructions | control.last_instructions | 10 | 7,729,840 |
| operation | control.last_operation | 11 | 7,729,848 |
| phase | control.current_phase | 12 | 7,729,856 |
| mask | control.observed_mask | 13 | 7,729,864 |
| expected | control.expected_mask | 14 | 7,729,872 |
| state | active.state | 64 | 7,730,272 |
| active_op | active.operation | 65 | 7,730,280 |
| function | active.function | 66 | 7,730,288 |
| terminal | lifecycle.terminal_seen | 160 | 7,731,040 |
| failed | lifecycle.pin_failure_seen | 161 | 7,731,048 |

Compatibility analysis: these meanings agree with the accepted design's
stage/lifecycle semantics. `control.accepted_records` here is only an internal
fixture coordinate; exposing it as a semantic validated count is forbidden.
This is a projection proposal, not permission for two live owners of these
cells. Future composition must choose exactly one owner and coordinate the
shared phase/sequence work with framing; independent copies must not each
commit coordinates. No active framing implementation is examined or modified.

The accepted single candidate owner is 2,048 bytes. Existing candidate payload
positions are Function0..95, Resident96..159, Pin160..207, Plan208..247,
Window248..375, recency376..887, scalar values888..1143 and histograms1144..1191.
This envelope uses **only its 12 scalar values at candidate bytes888..983**,
in table order. Bytes984..1143 and every other candidate byte stay zero. It
requires no extra candidate, additional semantic row, victim/token table or
per-record allocation. This explicitly narrows the existing 32-value scalar
delta capacity; it does not borrow an unassigned cell or expand the arena.

At initialization all arena cells are zeroed under the existing charged loop;
phase0/mask1, expected fixture mask (<64, bits0/5 required), and operation0 are
installed before any record. Other default fields are zero and state0 guards
inactive identity. Fixture state is private; a caller cannot supply arbitrary
already-trusted State instances to a future implementation.

## Atomic checks and refusal

Read/check every selected arena cell, record scalar, candidate bound and write
destination before mutation. Candidate contains all 12 final values; all other
semantic regions are untouched. Sequence, coordinates, closed forms, identity,
stage/phase/latch checks and budget admission must all succeed before commit.
The last accepted coordinate advances only with the completed delta. Refusal
discards it and retains the prior arena state and coordinate, while retaining
the debit already spent. No half-applied record becomes observed.

The planned commit is a bounded infallible series of prechecked 8-byte writes.
It cannot allocate, call I/O or invoke fallible helpers after the first write.
If the actual implementation nevertheless detects a partial commit failure,
it must return InternalPoisoned, invalidate all semantic output and stop. It
must not serialize the mutated state as the previous valid prefix; historical
accepted coordinate is not authority to do so. The finite fault controls model
both preflight refusal and poisoned partial commit, rather than claim rollback
of arbitrarily failed memory writes.

## Complete proposed envelope roles and unresolved composition

The 65,536-byte ceiling concerns complete named logical transients, not RSS,
optimizer copies, compiler stack, opaque Python/Rust/allocator internals or
kernel memory. Those costs are unqualified. Python objects in the finite model
are not a measurement or implementation of the Rust logical inventory.

The following is a **closed implementation role proposal**, including argument,
return/move and caller storage, not measured Rust layout qualification. All
owners below are fixed byte/u64 arrays or references; no hidden Result, Option,
iterator, closure, File, heap collection or recursive frame is allowed in this
leaf. Checked access uses an explicit `{status:u64,value:u64}` pair. The outer
File/Metadata/read Results and framing owners remain their separate review
obligation; this leaf creates or moves no File/OwnedFd and does no I/O.

| Simultaneously charged role | Complete logical bytes |
| --- | ---: |
| Existing complete candidate owner (one; payload96, not a second owner) | 2,048 |
| Caller decoded record backing128 plus record argument borrow8 | 136 |
| Caller arena slice argument16 and callee arena slice16 | 32 |
| Caller/callee StepBudget borrows8 each plus complete two-u64 budget owner16 | 32 |
| Explicit caller/callee `&mut Candidate2048` borrows8 each | 16 |
| Prior 12-word snapshot, leaf owner | 96 |
| Candidate value source temporary12 words, before copy into same candidate | 96 |
| Record scalar destructuring16 words | 128 |
| Fixed predicate/error-coordinate locals16 words | 128 |
| Transition/control/address locals16 words | 128 |
| Eight explicit checked `{status,value}` pair locals | 128 |
| Eight complete checked-arithmetic `Option<u64>` values,16 each | 128 |
| Candidate slice borrow16; reply source borrow8; loop index8 | 32 |
| Leaf reply owner128, caller destination128, conservative return/move128 | 384 |
| Error path reply128 and caller return/move128, conservatively overlapping | 256 |
| Three bounded checked-access frames,256 each | 768 |
| **Record-call named-role sum** | **4,536** |

Each checked-access256 frame owns arena borrow16, candidate borrow16, cell8,
base8,stride8,width8,end8,checked pair16, byte temporary8, value8, return pair16,
loop/index8 =128; it additionally reserves complete `Option<&[u8]>`32,
`Option<&mut[u8]>`32 and `Option<u64>`16, totaling208, with48 unused. The safe
checked slices' Option owners are not omitted. Three frames are charged
simultaneously even when scopes do
not overlap. Checked pair status/error and reply are the complete Result role:
no native Rust `Result<T,E>` is silently presumed to have a particular layout.
If the implementation chooses Result/Option instead, its entire actual value,
source/destination/move and error arms must replace these charges and be probed.
The standalone host probe observes CheckedPair16, Reply128, StepBudget16,
Option<u64>16, both slice Options16 and complete Helper176. The helper remains
charged256 to cover both conservatively reserved32-byte slice Options and48
unused bytes; no measured value expands its reservation. This is value-layout
support for these exact declarations, not an implementation lifetime proof.

The separate **initialization phase** conservatively includes both array values
and complete setup/error/return roles. Its roles cannot overlap record-call
locals: the literal/source and its initializer scope end before the loop.

| Initialization roles | Logical bytes |
| --- | ---: |
| Complete zero literal/source and retained destination,2048 each | 4,096 |
| Caller/callee candidate borrows8 each | 16 |
| Caller/callee arena slice borrows16 each | 32 |
| Caller/callee StepBudget borrows8 each | 16 |
| Complete two-u64 StepBudget owner | 16 |
| Loop/index8, zero-word8 and expected-mask8 | 24 |
| Complete checked status/value pair | 16 |
| Reply source128, caller destination128, conservative return/move128 | 384 |
| Additional complete setup error reply, conservatively overlapping | 128 |
| **Initialization named-role sum** | **4,728** |

The standalone value probe declares the complete InitializationRoles struct and
observes4728 bytes, and Candidate2048/its sized-array borrow2048/8. It does not
construct a runtime candidate or prove source scopes. Record, finish and
teardown are conservatively charged the full4536 call-role sum; no literal or
source array survives from setup. No additional by-value candidate argument,
return or drop move is allowed; any actual implementation adding one must
reopen the inventory rather than assume optimizer elision.

The maximum phase sum4728 reserves **5,120 bytes**, leaving392 unused and zero,
using existing
candidate group2,048 plus3,072 of the accepted control/helper reservation8,192.
There is no claim that the other5,120 helper bytes accommodate an implementation
of framing or nested semantic replay. Named roles are conservatively charged
throughout entry/preflight/commit/return/error; the next call begins only after
the prior reply/source/moves leave scope. Candidate reuse requires no live
borrow from a previous call. Failure or any extra owner/helper invalidates this
closed inventory and refuses selection pending revised review.

The accepted design's overall41,984-byte group allocation was provisional.
Neither this arithmetic nor its 23,552-byte margin proves a combined analyzer
inventory. Actual Rust types/lifetimes, framing overlap, report/output Results,
complete caller roles and retained returns require separate implementation
source/layout review. **Complete Rust and combined lifetime qualification are
withheld.** The fixed arena remains7,873,120 used/8,388,608 and the report remains
49,152, host record8,192, aggregate57,344/65,536; this packet adds no production
output. These are contract ceilings, not measured runtime/RSS results.

## Explicit debit schedule and historical estimate withheld

The production cap stays268,435,456 authored Rust analysis steps. This fixture
leaf proposes exactly**128 debits per admitted record**, including refusals.
Before entry it requires128 available credits. All groups are charged, including
inactive checks/commit groups on refusal; no early error bypasses accounting.
One group is at most16 bounded scalar operations or one<=128-byte fixed copy.
Any internal data-dependent loop, hidden comparator, format or allocation is
forbidden. Each checked/copy/initialization loop iteration is explicitly charged.

| Fixed schedule | Debits |
| --- | ---: |
| Sixteen checked 8-byte word loads/decodes | 16 |
| Twelve selected cell reads | 12 |
| Twelve candidate-value initialization/copy iterations | 12 |
| Twenty-four closed-form predicate slots | 24 |
| Twelve sequence/coordinate/phase/identity/failure gate slots | 12 |
| Twelve transition/delta construction slots | 12 |
| Twelve candidate/write-address invariant slots | 12 |
| Twelve commit-store slots, no-op on refusal | 12 |
| Four reply/finish groups | 4 |
| Twelve always-charged bookkeeping/error slots | 12 |
| **Total** | **128** |

This is a proposed authored instruction schedule, not measured CPU instructions
or proof of a Rust compiler's output. The model checks budget boundaries and
returns128/0 debit; it does not instrument a nonexistent Rust implementation.
Separate review must map every actual operation/helper/argument/return to these
slots and refuse any overflow. New requirements may force a larger debit and a
shorter observable prefix under the same cap.
Amended leaf setup proposes534 debits inside the existing65,536 allowance:
256 to zero the complete2048-byte literal/source,256 for its complete move/copy
into the retained destination,12 to install the named cells,2 expected-mask
predicate groups,4 budget/reservation/borrow bookkeeping groups and4 fixed
setup reply/error source/destination/move groups. This replaces the incomplete
initial274 proposal; it does not expand any reserve. No per-record zeroing is
allowed under128. Each record's12 candidate word assignments stay in its
existing12 candidate slots, and the explicit sized-array borrow bookkeeping
fits its always-charged12 bookkeeping slots. R1 adds one fixed-width predicate
within the existing24 shape slots; there is no new loop.

Eight finish groups inside the existing report reserve are: private origin/
status, poison/absent/unsupported state, fixture CAP branch, Idle/phase/mask
boundary, and four complete fixed reply/source/destination/move/error groups.
Poison is checked before CAP and before any state-field dereference. The
rest of setup/reporting remains a separate composition obligation; unused
reserves are not returned to replay.

The accepted **22-group** per-record semantic estimate is not inherited by this
envelope. Even without policy/metrics, this conservative leaf is128. It fits
inside8,192 in isolation; **the old combined8,192 preflight proof is withheld**
until composition includes all framing, semantic, helper and failure work.
The leaf's128 admission is not permission to reduce a future combined reserve.

Keep the accepted reserves: arena initialization1,048,576, profile640,000,
setup65,536, reserved I/O263,584 and reporting3,000,000: fixed5,017,696. Merely
replacing historical22R with128R at R2,889,656 would cost374,893,664 before
additional recency/policy loops, exceeding268,435,456. With no other record work,
the maximum arithmetic capacity is floor((268,435,456−5,017,696)/128)=2,057,951
records. This is an upper bound, not an accepted target length or throughput
promise; a retained8,192 reserve or other work lowers it. The full4,194,304
record cap is not guaranteed and old229,870,640 estimate cannot qualify this
leaf. Setup/report/I/O reserves cannot be borrowed for extra replay.

## Executable evidence and selection boundary

Run `python3 -B verification/swift-ordered-retention-analyzer-fsm-contract/run_checks.py run-1`
only once for the retained run directory; use a fresh owned run directory for a
new receipt. `verify.py` rechecks the eventual sealed packet without modifying
upstream evidence and reruns only the finite model. All attempted runs, including
failures, are retained; no prior failure is overwritten as a later pass.

Historical first-freeze run5 passes18 finite methods plus the standalone Rust1.99.0
`aarch64-apple-darwin` layout compile/execution, on Python3.14.8. Its external
source snapshot digest is
`6365807b3c70dd5812fa600875f434086f0a620b4a7acb362e73887935d8be78`;
the finite model/test/layout hashes are recorded separately. Run1 passes17
methods before the initialization-mask control was added. Run2 stops before
tests at cross-run snapshot admission: root concurrently updated PLAN.md.
The previous snapshot and explicit failed-attempt receipt are retained. Run3
uses per-run immutable source snapshots and passes17 methods/layout; run4 adds
the18th method; run5 repeats the final exact model after reason IDs are fixed.
The five accepted seals and all845 members match before/after
each executed receipt. Root metadata/HEAD may advance independently; exact
consulted sealed sources and per-run copies remain fixed.

Independent findings freeze
`31460ea35508acfc5b0093f5f32874b1baa69f4377285ce4060c503f98d765e6`
retains208 members and the exact failing reproductions. The original producer
freeze and these findings are checked byte for byte before/after amendment
runs, alongside all845 upstream members. Their copies and the separate
`amendment.json` preserve the prior seal and changed-file hashes; the current
seal pair identifies the amended packet without a circular embedded self-hash.

Amended **run8 passes24 methods** and a fresh standalone value-layout compile/
execution on the same Python3.14.8/Rust1.99.0 host toolchain. External source
snapshot digest is
`e4d8450382a3833731b7991dd700dffc0d9bdd605c390e02a33f1c1cce4915f8`.
It includes u32 boundaries across every full-body kind and Release, all four
exact independent width reproductions, one retained candidate across repeated
calls and refusal, setup admission, complete two-phase arithmetic, and poison
through CAP/non-CAP/state/reply/owner boundaries. Pure transition `observe`
remains a mathematical fixture helper; `FixtureEnvelope` models retained-owner
call order. Neither is a public Rust entry or actual File framing authority.
Preliminary amendment run6 also passes24 methods but is superseded: its layout
output still printed old setup530 and its initialization role declaration lacked
both caller/callee arena and budget borrows. Run7 corrects that bookkeeping and
records the final534 setup and4728 peak. Run8 repeats those exact finite
sources while verifying the retained findings archive, so future independent
review edits cannot drift this packet's custody check. The archive preserves
all208 findings members plus seal pair (210), SHA256
`4d1a0f8ea4ae290831059e3cf3cd54e5e53c6701eb43d5a56397bd1de5c8282c`,
at `history/findings-freeze-1/packet.tar.gz`. These attempts remain intact; the
initially rejected freeze is not rewritten as a clean result.

Only the owned standalone layout binaries are retained as evidence. No
disposable source/build scratch, bytecode or native instance is created. Every
synchronous host child exits and is reaped. No native/capture/target process
discovery or UI automation occurs. The packet contains no new dependency.

The tests independently encode expected legal paths and the154-cell matrix.
They cover Lookup/PlanEnd/publication/Failure discriminator forms, CAP cuts at
every legal path position, mismatched operation/function, all ten illegal
Release stages at all phases, failure/resumption, independent/absent cursors,
phase4/5, strict phase advance without inferred traversal, u64 coordinates,
budget boundaries, preflight atomic refusal and poisoned partial commit. Test
execution counts are fixture coverage, never semantic metric validity.

This packet is ready only for separate contract review. Root selects Rust
implementation after current framing review and this contract review; no
implementation is implicitly selected by publication of this document.
Resident/token/plan/victim policy, source/profile/original-result/ledger/custody/
crypto authority and real context remain unavailable. CLI, source preparer,
driver, full target, native/device/compiler qualification, signing/store,
customer/operations, published FieldLog and all GA gates stay pending.
