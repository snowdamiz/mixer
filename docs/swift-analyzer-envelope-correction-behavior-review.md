# Corrected fixture envelope: independent behavioral baseline

Status: **pre-access baseline frozen; execution and acceptance pending**. This
lane has not read the correction implementation, its ledgers/tests, or the
correction operation proposal. Its inputs are the five immutable root selections
and the original frozen behavioral review packet listed in the accompanying
provenance receipt. The original producer and review remain unchanged.

The original candidate's producer reported 64 passing methods. Its independent
review passed 33 corrected public fixtures and nine of ten private controls;
R1 failed. Its independent 64-method replay timed out and is unqualified, with
missing initial partial stdout. These are historical observations, not passes
for future corrected source. No historical test or cost expectation is promoted.

The binding product scope remains `mixer-product-plan.md`; this is a narrow
standalone safe-File fixture-envelope review, not W08/G02 completion. Computer
use, capture, native runtime, simulator/emulator and phone checks remain paused.
This baseline performs only offline reads, hashing and artifact validation; it
does not compile or run the analyzer or discover processes.

`verification/swift-analyzer-envelope-correction-behavior-review/baseline.json`
is the exact independent expected-outcome matrix. Every case is pending. The
following rules determine its results before corrected-source access.

## Cost parameters and admission

Use `E_SETUP`, `E_FINISH`, `E_LEAF`, `B_RECORD`, `W_SETUP`, `W_FINISH` and `G`
only as symbolic values from a later explicit root-selected cost amendment and
its independently audited exact source. No proposed correction number is
selected here. The historical 128-leaf proof was rejected by the independent
accounting audit; the separate correction proposal is also unselected and has
an unresolved early-finalization funding gap. Neither proposal supplies test
parameters. Original selections and numbers remain preserved as history.

Public reserved debit is `E_SETUP*S + E_FINISH*F + E_LEAF*N`, where `S` and `F`
record successful main setup/finish reservations and `N` counts successful main
combined record charges, including later decode failures and skipped leaf calls.
Failed charges add nothing; paid charges are never refunded. Wrapper/guard
charges affect total authored steps, not this public subtotal. A private
underfunded guard can return debit0 while the public paid record retains
`E_LEAF`. Counters describe actual successful reservations, not executions.

The unchanged 8,192 next-record preflight and global ceilings remain binding.
Test exact and one-below boundaries only after the selected schedule and
separately reserved work determine them; do not reuse the old five-record
threshold or capacity. Setup, guard, finalization and **every early-error reply**
must be funded before their dependent work. Setup/finish reservation failure
must precede candidate initialization. An unproved early return is a stop, not
credit borrowed from a branch that never reserved it.

## Poison, refusal and observation

R1's exact original fault is retained: `reply_valid=1`, status1, reason15 and
stale state999. Finalization already recognizes that retained reply as poison;
scheduling must also reject it. Repeat with status3, supported/stale states,
CAP/non-CAP, complete/successfully limited framing and an attempted later valid
record. No later leaf call, reply replacement, candidate reset or state
reconstruction is allowed. Count calls as well as checking the scheduler result.

Poison handling precedes CAP and state dereference. Successful complete framing
returns InternalPoisoned/InternalPoisoned with all fixture fields zero; a
successful limited drain returns AnalysisLimited/InternalPoisoned with zero
fixture fields. A later input error still overrides these outcomes. An absent
reply (`reply_valid=0`) has no readable backing projection, even if backing
contains Observed-shaped or poisoned garbage.

Candidate/cell setup alone never makes a reply valid. Only an actual complete
returned-and-installed leaf reply can set `reply_valid=1`. Complete or
successfully limited zero-call framing returns Unavailable/EnvelopeUnavailable,
all fixture fields zero and the actual symbolic reserved debit. An actual
underfunded Refused/Steps reply is valid, including on the first call; it is
never a fabricated Observed0 initializer.

Absent prior state returns InternalPoisoned/debit0 before ordinary checks.
Otherwise private funds below `E_LEAF` return Refused/Steps, unchanged prior
state/coordinate, unchanged budget and debit0, before shape or coordinate
validation. Check first/later calls, bad next records and exact funding. Ordinary
paid shape/stage/coordinate/checked-access refusals preserve the prior committed
state and retain their paid debit. Every selected cell and write destination
must be checked before mutation. A hypothetical partial commit poisons; it does
not claim rollback or a safe previous prefix. The first refusal or poison
latches while framing continues independently.

## Actual safe-File boundary precedence

Only actual complete framing, strict EOF and successful final input metadata
checks permit complete-envelope finalization. Framing's ordinary
Decision::Unavailable alone proves no such completion. A successful bounded
structural drain is distinct from an incomplete or failed drain.

| Highest applicable condition | Boundary / reason | Fixture fields |
| --- | --- | --- |
| Outer output safety, Budget construction, allocation, write or postwrite Err | No aggregate | No successful observation |
| Returned input/framing BINDING error | Unavailable / FramingUnavailable | All zero |
| Returned input/framing BUDGET error | Unavailable / FramingLimited | All zero |
| Other returned input/framing error | Unavailable / FramingInvalid | All zero |
| Inconsistent complete/limited/return flags or unsupported private values | Unavailable / UnavailableState | All zero |
| Successful framing; no complete returned reply | Unavailable / EnvelopeUnavailable | All zero |
| Complete framing; retained poison | InternalPoisoned / InternalPoisoned | All zero |
| Successful limited drain; retained poison | AnalysisLimited / InternalPoisoned | All zero |
| Complete framing; latched ordinary refusal | Refused / first refusal | Last committed fixture extent |
| Successful limited drain; latched ordinary refusal | AnalysisLimited / first refusal | Last committed fixture extent |
| Successful limited drain; supported Observed reply | AnalysisLimited / FramingLimited | Last committed fixture extent |
| Complete framing; supported Observed reply; sole CAP | CapCutUnknownTail / Observed | Actual state, including open state |
| Complete framing; supported Observed; non-CAP; Idle/phase5/exact mask | ClosedEnvelopeObserved / Observed | Last committed fixture extent |
| Complete framing; supported Observed; other non-CAP boundary | Refused / IncompleteBoundary | Last committed fixture extent |

Unknown private status/reason/state/phase/mask/latch values and unsupported
framing flags fail closed. A poison marker is recognized before examining its
stale state. Input errors precede every private state. Every aggregate row
retains its actual reserved debit and preserves the framing classification.
Zero fixture fields means all eleven extent/state/phase/mask/operation/function/
latch/work/instruction getters, not only the state discriminator.

Exercise these rules through actual Files for public cases and a private,
test-only seam on an exact owned source copy for faults. Cover unknown context,
closed context/profile/header failures, setup/finish reservation failures,
post-charge record decoding failure, late malformed record/footer, strict EOF,
metadata drift, successful and failed limited drains, and output failures.
Valid/refused/poisoned early replies cannot override a later framing error.
Paid decode failure and each charged record after a latch still add `E_LEAF`
even when no leaf runs. Input failure before any actual reply stays unavailable.

## Finite behavior, memory and public surface

Recheck complete hit/build/eviction paths; eleven sole-CAP cut states; incomplete
non-CAP state; phase4/5; all ordinary kinds after phase5; independent/absent
Failure function cursors; no success-stage resumption after failure; legal Idle
Release after pin/terminal failure. These remain fixture observations with no
token/resident/victim/body/failure-applicability authority.

Retain exactly one local 2,048-byte candidate. Its initialization source dies
before records; no wrapper, return, error, cleanup move or closure owns another.
Only candidate bytes888..983 and the twelve selected scalar arena cells may
change through the leaf. Other candidate bytes remain zero; refusal/underfunding
controls compare the complete pre/post arena and candidate. Repeated records
reuse the owner; no per-record allocation or retained record list is permitted.
The accountant independently checks complete types, moves, Results and lexical
overlap against unchanged memory ceilings; behavior tests alone cannot qualify
those bounds.

Preserve old `analyze_fixture`, ReplayOutcome ABI, fixed 49,152-byte report,
version, validity mask and reserved zeros. Compare every old/new framing field
and report byte; only the truthful authored-step field may differ according to
the later selected schedule. All acceptance/semantic getters remain hard false.
The new entry accepts existing safe File borrows. External positive/negative
compiler probes must verify immutable getters and reject private leaf/record
access, arbitrary-word/trust-boolean construction, aggregate field mutation,
observation Copy and aggregate Clone. No descriptor adoption, open/clone owner,
authority constructor, raw serializer or report validity bit is introduced.

## Bounded later execution

Root must first hand over an exact corrected source seal and explicit selected
cost contract, including early-finalization funding. Freeze both without
altering this baseline. Resolve a mechanical symbol-to-source/API map in a
separate receipt; behavioral changes require an explicit amendment and preserved
old expectations. Do not silently adapt expectations to the implementation.

Compile only the standalone owned exact source and independent bounded controls
when root authorizes that next stage. Begin with exact R1 and public finality
cases, then private boundaries, API probes and separately bounded compatibility
methods. Do not rerun the historical timed-out combined 64 command. Historical
33/44/64 totals are not a corrected-source test selection or a current pass.

Every future child gets a dedicated owned process group/session, an absolute
deadline and durable stdout/stderr files from launch. On timeout or exception,
preserve partial bytes, terminate only that owned group, escalate if necessary,
reap all known children and record cleanup before releasing scratch. Never kill
a shared group or discover unrelated processes. Report each method's actual
exit/signal/timeout and keep incomplete methods unqualified. No runtime child
may be left behind. Keep the native/capture pause in force.

This freeze authorizes no product publication, hosted harness, catalog
inspector, rejected WorkerV2, Patch/Skip source/dependency, acceptance join,
native/device/signing/store/customer/operations/FieldLog or GA promotion.
