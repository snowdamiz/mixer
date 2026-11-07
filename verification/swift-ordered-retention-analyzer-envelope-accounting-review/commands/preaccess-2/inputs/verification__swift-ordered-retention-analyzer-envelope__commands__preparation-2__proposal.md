# Separate fixture envelope orchestrator proposal

This is **preparation only**, awaiting root's interface/composition approval.
There is no new Rust implementation or accepted combined memory/step proof.
The binding product scope remains `mixer-product-plan.md`, W08/G02; a finite
fixture observation is neither semantic replay nor a completed product gate.
Computer use, capture, native simulator/emulator runtime and phones remain
paused. Only bounded host/direct-rustc/Python work is proposed.

This is proposal2. The immutable first proposal remains at
`verification/swift-ordered-retention-analyzer-envelope/commands/preparation-1/proposal.md`,
SHA256 `9cda8638c76d1f8deb60b3fd9bd1d35caf7e7d155c548ad0f95251540ea4a1de`.
Its generic8,042-credit wrapper bucket and32,155-record arithmetic capacity
were not selected. Root instead selected the finalization/debit semantics below
for reviewer confirmation before source implementation authorization.

The accepted framing source is SHA256
`ce8f3013f7ecc9ccdb5ca88db75b7019f6af24cff995907d5d95012edb5d1757`.
Its producer/review seals are
`777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63`
and `a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e`:
270+624=894 members. The amended lifecycle contract seal is
`bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193`;
its independent review seal is
`101e6c9a67e41cce0e3c82c67ba92ef8025da19376b0578f8ddcdd694fb67212`.
Root's separate contract acceptance does not qualify actual Rust composition.

## Proposed compatibility and public boundary

The new owned packet copies the complete accepted framing source and its
20 producer tests byte for byte. Its `analyze_fixture`, `analyze_core`, `walk`,
`observe_inputs`, `ReplayOutcome` and fixed-report path remain unchanged. The
24 independent methods are also replayed from exact copied reviewed sources;
their stage-order negatives retain their framing-only expected observations.
No existing/frozen source, test, receipt, report version or public ABI changes.
New private functions are appended in the new packet for a separate path:

```rust
pub fn analyze_fixture_envelope_v1(
    stream: &mut File, profile_file: &mut File,
    context: &mut File, output: &mut File,
) -> Result<FixtureEnvelopeOutcomeV1, AnalyzerError>;
```

All four inputs are the same safe existing-File borrows with the accepted
distinct/quiescent/regular/offset-zero and empty-exclusive-output preconditions.
The path reuses reviewed private framing/profile/metadata/I/O/report helpers.
It adds no open, clone, File adoption, descriptor, path, source selection, CLI,
host authority, dependency, live VM or hosted implementation.

Proposed public types are `#[repr(C)]` structs with private fields and only
borrowed getters. They have no public constructor, raw-word constructor,
setter, authority flag input, Deserialize, conversion from arbitrary records,
or mutable field access. No public Copy/Clone implementation is proposed.

```rust
#[repr(C)]
pub struct FixtureEnvelopeOutcomeV1 {
    framing: ReplayOutcome,
    envelope: FixtureEnvelopeObservationV1,
}
#[repr(C)]
pub struct FixtureEnvelopeObservationV1 {
    boundary: FixtureEnvelopeBoundaryV1, // repr(u64), separate namespace
    reason: FixtureEnvelopeReasonV1,     // repr(u64), separate namespace
    observed_records: u64, state: u64, phase: u64, mask: u64,
    last_operation: u64, active_operation: u64, requested_function: u64,
    pin_failure: u64, terminal_failure: u64,
    last_work: u64, last_instructions: u64, envelope_debit: u64,
    full_replay_accepted: u64, stored_prefix_validated: u64,
}
```

Expected layouts are observation128, aggregate232 and complete
`Result<aggregate,AnalyzerError>`232. These are **unprobed expectations** until
actual declarations compile and execute under the accepted explicit rustc path.
All three complete values, their construction/return/error arms, caller
receiving places and conservative moves must be measured and inventoried.
An observation128 is not an additional report and does not borrow arena bytes.

`framing()` and `envelope()` return immutable references. Observation getters
return fixed enums/scalars, with `observed_records` documented only as a fixture
coordinate. `envelope_debit` is the cumulative conservative reserved charge
defined below; it is not a count of leaf executions. Both acceptance getters
always return false; internal acceptance
slots are always0. Semantic metrics remain unavailable. No raw byte serializer
or production/report/acceptance mapping is provided.

Public boundary IDs are proposed as Unavailable0, ClosedEnvelopeObserved1,
CapCutUnknownTail2, Refused3, AnalysisLimited4 and InternalPoisoned5. They are
neither leaf status IDs nor report decision IDs. Fixed reason IDs0..15 retain
the contract's Observed/Steps/Shape/Coordinate/TerminalPhase/Phase/ReleaseOpen/
TerminalFailure/PinFailure/ForbiddenResume/Acquire/Identity/Stage/
PublicationForm/CheckedAccess/InternalPoisoned names. Additional fixed reasons
are FramingUnavailable16, FramingInvalid17, FramingLimited18,
EnvelopeUnavailable19, UnavailableState20 and IncompleteBoundary21.

## Private construction, ownership and call order

The new `walk_fixture_envelope_v1` is framing-owned. After its reviewed header,
fixture and profile admission, it owns exactly one local
`let mut candidate: Candidate2048 = [0u8; 2048]` for setup, the loop and finish.
It reserves534 setup debits before that initializer. Its complete literal/source
2048 and retained destination2048 are charged together; the source scope ends
before records. The candidate is never returned, embedded in a movable
wrapper, passed by value, captured, re-zeroed, replaced or explicitly dropped
through a helper. Only bytes888..983 hold the twelve96-byte scalar delta words;
every other candidate byte remains zero. This is a source-lifetime obligation.

A private `FixtureDecodedRecordV1<'a> { words: &'a [u64;16] }` has one private
constructor in that new walk. It is created only after the walk's own decoder,
`record_fields` and wire `Framing::coordinate` checks succeed. Its backing128
bytes belong to the loop. The leaf receives only a short immutable borrow;
the decoded record and all nested views die before the next decode. No public
record type or caller-supplied verified/framed boolean bypass exists.

The private leaf keeps the amended contract's explicit sized-array borrow:

```rust
fn observe_fixture_envelope_v1(
    arena: &mut [u8], candidate: &mut Candidate2048,
    record: &FixtureDecodedRecordV1<'_>, steps: &mut StepBudget,
) -> FixtureEnvelopeReplyV1;
```

`Candidate2048`, `StepBudget { remaining:u64, spent:u64 }` and
`FixtureEnvelopeReplyV1` are private. Reply is the contract's128-byte fixed
16-word value with private constructors and Observed1/Refused2/
InternalPoisoned3 status. Absence is a separately tracked private initialization
discriminator, never a fabricated Observed reply. All reply source/destination/
return/error places and both borrowed-record wrapper levels are charged.
No Result/Option is presumed to have a smaller representation than measured.

To preserve charges and latch state through every returned input error without
an implicit second reply, the new core owns one additional explicitly named
private holder throughout observation, metadata checks, report and return:

```rust
struct FixtureEnvelopeProgressV1 {
    initialized: u64,
    debit: u64,
    reply: FixtureEnvelopeReplyV1,
}
```

Its expected complete value is144 bytes, including the sole cumulative debit8
and initialization discriminator8. The core initializes it once with both
scalars0 and a fixed zero128-byte reply backing. `initialized==0` always guards
that absent backing before reply status/state access; it is never Observed.
The holder embeds no candidate, File, reference or Result/Option. It is not
returned by value or reinitialized. Observation and walk receive short mutable
borrows to the same holder, ending before final projection. Its reply is
replaced only by an owned fixed leaf reply after a call returns; a Refused or
Poisoned reply is then latched, with no later leaf call or replacement.

These added roles require explicit inventory before code acceptance: holder144
retained, complete holder source144/destination144/conservative move144; raw
zero-reply source128 and constructor value128; holder/debit helper caller and
callee borrows48 across three bounded pairs; scalar charge arithmetic and
complete checked-arithmetic Options, if used. The candidate stays the separate
single walk local. These are conservative proposed named roles, not measured
layout or proof that all group reservations fit. Source must reconcile any
actual additional constructor, copy, Result/Option or temporary rather than
hide it within these names.

The leaf alone owns the twelve selected SCALAR cells. It initializes their
phase0/mask1/expected-mask/operation0 state once and commits them only after all
shape, shared-coordinate, lifecycle, candidate-range and destination checks.
It implements the accepted11-state/154-cell table, u32 type width, independent
Failure cursor, Idle Release after failure, terminal phase5, CAP open-state
observation and poison-first finish. It creates no token/resident/victim/plan
authority or source-applicability rule.

Two distinct coordinates coexist deliberately and are charged explicitly:
the existing complete Framing80 wire cursor advances for every framing-admitted
record, even after an envelope refusal. The twelve arena cells include the
envelope fixture coordinate and do not alias that struct. They advance only
on atomic leaf success. Their prior snapshot96, candidate payload96, decoded
record128, leaf reply128, caller reply128 and conservative return/move128 are
all separate roles. Framing never writes these cells; the leaf never mutates
Framing or promotes its coordinates. This duplication is necessary to finish
wire validation after a refused lifecycle observation. It is not two writers
of shared semantic cells or two semantic accepted-prefix counters.

## Failure, absence and finalization precedence

Eligibility is determined by successful private input observation, explicit
`Framing.complete`/`Framing.limited`, and **all three final input metadata
checks**. It is never inferred from `ReplayOutcome.decision`: successful
ordinary fixture framing already uses Decision::Unavailable. A successful
limited structural drain is distinct from a returned drain error.

The table is exhaustive over returned input/framing status and private leaf
status. "Zero fields" means observed_records/state/phase/mask/last_operation/
active_operation/requested_function/pin_failure/terminal_failure/last_work/
last_instructions are all0. Every row preserves the truthful cumulative
`envelope_debit`; both acceptance slots stay0. "Safe extent" means the last
fully committed fixture reply only, with no semantic-prefix or metric validity.

| Private input/framing result, including metadata | Leaf status | Public boundary / reason | Coordinate/state fields | Finish behavior |
| --- | --- | --- | --- | --- |
| Returned Err with code BINDING | Any, including absent/refused/poisoned | Unavailable / FramingUnavailable | Zero fields | No leaf finish |
| Returned Err with code BUDGET | Any | Unavailable / FramingLimited | Zero fields | No leaf finish; failed drain is not a partial observation |
| Returned Err with any other code | Any | Unavailable / FramingInvalid | Zero fields | No leaf finish |
| Success, complete, all metadata success | Absent | Unavailable / EnvelopeUnavailable | Zero fields | No leaf finish |
| Success, complete, all metadata success | Observed, supported state, sole CAP | CapCutUnknownTail / Observed | Safe extent, including actual open state | Private poison-first CAP finish |
| Success, complete, all metadata success | Observed, supported Idle/phase5/exact mask, non-CAP | ClosedEnvelopeObserved / Observed | Safe extent | Private poison-first non-CAP finish |
| Success, complete, all metadata success | Observed, supported incomplete boundary, non-CAP | Refused / IncompleteBoundary | Safe extent | Private poison-first non-CAP finish |
| Success, complete, all metadata success | Observed but unsupported state | Unavailable / UnavailableState | Zero fields | Refuse unsupported state before CAP/state projection |
| Success, complete, all metadata success | Latched Refused | Refused / first latched reason | Safe extent | No normal finish or status upgrade |
| Success, complete, all metadata success | Latched Poisoned | InternalPoisoned / InternalPoisoned | Zero fields | Poison-first refusal for CAP and non-CAP |
| Success, limited structural drain, all metadata success | Absent | Unavailable / EnvelopeUnavailable | Zero fields | No normal non-CAP finish |
| Success, limited structural drain, all metadata success | Observed | AnalysisLimited / FramingLimited | Safe **partial** fixture extent | No normal non-CAP finish |
| Success, limited structural drain, all metadata success | Latched Refused | AnalysisLimited / first latched reason | Safe **partial** fixture extent | No normal non-CAP finish |
| Success, limited structural drain, all metadata success | Latched Poisoned | AnalysisLimited / InternalPoisoned | Zero fields | No normal non-CAP finish or state dereference |
| Unexpected success with neither complete nor limited, inconsistent flags, or unknown private status | Any | Unavailable / UnavailableState | Zero fields | Fail closed; no normal finish |

An unsupported state under an otherwise Observed limited reply is likewise
Unavailable/UnavailableState with zero fields, never a partial observation.
Poison status is checked before state access and before either CAP/non-CAP
branch, including a poisoned reply that accidentally retains stale state.
There is no route from an unsupported/absent/poisoned private value to Observed.

Output safety, Budget construction and Arena allocation failures preserve the
accepted outer `Err(AnalyzerError)` behavior and return no aggregate/report.
An error returned from the new input/framing path preserves the actual fixed
framing outcome/error classification and uses the first three table rows;
this includes early context/profile/header/setup/I/O failure and an incomplete
drain. A setup or finish reservation failure cannot initialize the candidate.
Output write or postwrite verification errors remain outer errors without a
successful aggregate. Partial physical output stays failed output.

After Refused or InternalPoisoned, the first reply is latched, the candidate/
arena state is never reset and no later leaf call occurs. The framing path
continues its independent decoder/field/coordinate checks through footer/EOF
and final metadata. Any later returned error suppresses all earlier leaf fields
using the top three rows, while retaining debit. A preflight limit instead
drains bounded bytes without decoding omitted records or calling the leaf;
only successful drain/footer/EOF/all-metadata completion enters limited rows.
Framing's getter separately remains AnalysisLimited for those limited paths.
The mixed AnalysisLimited/first-refusal-or-poison reason is deliberate; it
describes a limited framing run and its retained leaf reason, never a valid
semantic prefix. CAP never invents closure, phase bits or an unobserved tail.

## Proposed conservative combined accounting

All ceilings stay fixed: arena8,388,608; named transients65,536 with existing
41,984 reservation; authored steps268,435,456; report49,152 plus future host8,192
=57,344 within65,536. No arena region, report bit/reserved word/version or
semantic report count changes. The report's framing bit keeps its old meaning.

The existing8,192 next-record preflight is mandatory and unchanged. Before
decoding any admitted record, the main Budget atomically charges the combined
fixed debit **B=22 framing +128 envelope +W wrapper/helper groups**, with B<=8192.
The leaf's128-credit StepBudget is a prepaid subdivision of that charge, not
an additional replay-credit source. All128 are paid even if the record later
fails read/framing, the leaf refuses, or a prior refusal/poison means the leaf
is skipped. No refund or later phase reuse is allowed.

W must be derived from bounded actual source groups: main charge/debit update,
private decoded-record construction and argument/borrow setup, latch/skip
control, complete reply source/destination/return/error/move handling, and
record-loop bookkeeping not already charged by framing22 or leaf128. Each
group must map its actual operations/helpers and worst branch to the same
authored group rule as the contract. Conservatively rounding an individually
named worst-case group is permitted; an unassigned padding bucket is not.
Exact W/B and full source/type/lifetime/step mapping require separate review
before implementation acceptance. No numeric W/B or complete-record capacity
is selected in this proposal.

Setup534 is charged inside the existing65,536 setup allowance, including both
256-unit candidate initialization/copy roles, twelve initial cells and fixed
setup replies. Finish8 is reserved inside the existing3,000,000 report reserve
before candidate initialization or any envelope-cell mutation. Finish consumes
that reservation and cannot discover a missing debit after a state change.
The operations are sequential: setup534 succeeds and is recorded, then finish8
succeeds and is recorded, then and only then candidate initialization/mutation
may occur. If the second charge fails, setup534 remains charged while the
candidate remains absent. I/O remains separately within263,584. Arena/profile
costs remain1,048,576 and640,000. No full-cap or target throughput claim follows.

`envelope_debit` is exactly the cumulative conservative **reserved envelope**
charge, including suppressed results and prepaid calls that never execute:

`envelope_debit = 534*S + 8*F + 128*N`,

where S is1 only after the main setup534 charge succeeds, F is1 only after the
main finish/report8 reservation succeeds, and N counts successful main combined
B record charges. S/F are each0 or1, F implies S and initialization requires
both. Increment128 immediately after each successful main B charge, before any
record read or framing check, including all later records after a latched
refusal/poison. Failure of the B charge does not increment N. No refunds apply.
The debit survives every unavailable/zero-field projection; it is never copied
from the last leaf reply's per-call debit128. Finish's prepaid8 remains charged
even if an error prevents finish. A failed setup charge adds0; a successful
setup followed by failed finish reservation retains534. With N<=4,194,304,
the elementary counter bound is536,871,454, within u64; actual main Budget
admission is stricter. This arithmetic is a counter-overflow bound, not a
claimed achievable record count or extra reserve.

The combined inventory must reconcile the accepted14,248-byte authored bound
with actual added roles in every lexical phase, without spending the23,552
unassigned margin. The candidate2048 reservation becomes occupied. Its setup
source2048 uses the existing paths/setup group; record leaf helper/checked-pair/
complete Option/argument/reply roles use the control/helper group; new public
aggregate/Result/receiving/move and observation values use report/error. Existing
File/Metadata/Reader/decoder/error/I/O owners remain fully charged when live.
The leaf's standalone4,728 initialization/4,536 record bounds are not blindly
added as a second complete owner or treated as a combined qualification.
Every actual complete type and every added caller/helper chain must be probed
and enumerated. Any group overflow requires revised review, not silent margin
use or optimizer elision.

## Proposed host verification and selection boundary

After root approval, implement only in this owned packet and use direct
`/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc`
with `-Dwarnings`, standard library only. Run the unchanged44 framing methods,
new lifecycle stage/closed-form/ownership/poison controls and differential
comparisons against the frozen finite model. Exercise legal hit/miss/build/
eviction/failure/release/phase paths, all154 stage cells, u32 boundaries,
independent Failure cursors, exact masks, CAP cuts, refusal followed by malformed
tail/footer/EOF/metadata, absence/setup/output failures, strict budget edges,
bounded drain and zero semantic report regions. Probe complete layouts and
reconcile the full source/lifetime/caller/step inventory before freezing.

Every run uses new owned source snapshots and directories, records commands,
tool executable/version hashes, HEAD as context, consulted source tree digests,
raw stdout/stderr and actual scope, including failures. Rehash all894 accepted
framing members and corrected contract/review members before/after; never
execute or edit a frozen runner. Preserve original845 upstream members and
historical sidecar classifications. Clean only owned disposable scratch after
all synchronous children return; no native/capture/process/device discovery.

Source/FD/CLI/real binding, cryptography/custody, source failure applicability,
token/resident/victim/plan/metrics replay, writer repair, live VM/full target,
native/device/compiler/signing/store/customer/operations, published-package
FieldLog and GA acceptance remain pending. This proposal selects none of them.
