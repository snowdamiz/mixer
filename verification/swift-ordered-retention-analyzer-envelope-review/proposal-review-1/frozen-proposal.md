# Separate fixture envelope orchestrator proposal

This is **preparation only**, awaiting root's interface/composition approval.
There is no new Rust implementation or accepted combined memory/step proof.
The binding product scope remains `mixer-product-plan.md`, W08/G02; a finite
fixture observation is neither semantic replay nor a completed product gate.
Computer use, capture, native simulator/emulator runtime and phones remain
paused. Only bounded host/direct-rustc/Python work is proposed.

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
coordinate. Both acceptance getters always return false; internal acceptance
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

Before initialization, the envelope is absent. Unknown real context remains
Unavailable/FramingUnavailable. Fixture/profile/header failures, unavailable
initialization or early I/O cannot manufacture a leaf observation. The public
envelope is Unavailable with zero state/coordinate/latch fields, a fixed reason
and its charged debit. Output safety, Budget construction and Arena allocation
errors preserve the accepted outer `Err(AnalyzerError)` behavior without a
report. Input errors after safe output admission follow accepted report
classification. Output/write/postwrite errors return the fixed outer error;
partial physical output stays failed output and carries no returned envelope.

After a leaf Refused or InternalPoisoned result, its first refusal/poison is
latched and no further leaf call occurs. Candidate/arena state is never reset
to resume. The framing walk still decodes/checks subsequent records and the
footer/EOF, then the caller performs all final input metadata comparisons.
Only that complete successful framing path may expose Refused or Poisoned.
The poisoned leaf finish checks status before state/CAP and returns poison for
both CAP and non-CAP, including stale retained state. Refusal cannot become
Closed or CAP observation.

The existing8,192 next-record preflight remains mandatory. A refused preflight
starts the existing bounded byte drain without decoding omitted records or
calling the leaf. A structurally successful drained path with an initialized
leaf has public AnalysisLimited and explicitly **partial fixture extent** from
its last safe leaf reply; its reason is FramingLimited unless an earlier
refusal/poison reason is already latched. Poisoned state/coordinate fields are
zero. A path limited before initialization stays Unavailable/EnvelopeUnavailable.
Neither case calls normal non-CAP leaf finish, and neither supplies a closed
envelope or semantic prefix. A footer, EOF or final
metadata failure takes precedence over that limit and any earlier leaf result:
the envelope becomes Unavailable/FramingInvalid with zero coordinate/state.
A budget/I/O failure while draining preserves its actual fixed framing
classification; an incomplete drain never qualifies a complete boundary.

Only after complete successful framing and input metadata success does private
finish choose: poison, latched refusal, unsupported state, sole CAP cut,
Idle/phase5/exact-mask Closed, or IncompleteBoundary refusal, in that order.
CAP never invents closure or an unobserved tail. Later report errors cannot
return a successful aggregate. No final path upgrades Invalid, AnalysisLimited
or Unavailable into an accepted decision.

## Proposed conservative combined accounting

All ceilings stay fixed: arena8,388,608; named transients65,536 with existing
41,984 reservation; authored steps268,435,456; report49,152 plus future host8,192
=57,344 within65,536. No arena region, report bit/reserved word/version or
semantic report count changes. The report's framing bit keeps its old meaning.

For this first fixture-only composition I propose **debiting the full8,192
combined credits before each decoded record**. This closes a future proof
loophole by consuming the preflight allocation rather than reusing historical
22R or the standalone leaf128R estimate as a complete budget. The8192 includes
framing22, leaf128 and8,042 conservatively reserved framing/helper/orchestrator
credits. The leaf's explicit128-credit StepBudget is a subdivision of that
already charged amount, never an additional source of replay credits. Each
actual loop/helper/return/error operation must still map to a bounded schedule
within that amount; a larger actual bound refuses selection. No unused record
credits are refunded or borrowed by another phase.

Setup534 is charged inside the existing65,536 setup allowance, including both
256-unit candidate initialization/copy roles, twelve initial cells and fixed
setup replies. Finish8 is reserved inside the existing3,000,000 report reserve
before candidate initialization or any envelope-cell mutation. Finish consumes
that reservation and cannot discover a missing debit after a state change.
I/O remains separately within263,584. Arena/profile costs remain1,048,576 and
640,000. At maximum fixed reserves5,017,696, the arithmetic capacity is at most
floor((268,435,456-5,017,696)/8192)=32,155 records before other effects. This is
an intentionally conservative fixture scope, not target throughput or support
for the whole4,194,304-record cap. The unchanged cap is handled by bounded
AnalysisLimited drain. Root must explicitly select this budget choice.

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
