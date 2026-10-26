# Cache-state terminal projection correction

This is the narrow source-contract correction for R1 in the independent
semantic-adapter review. It supplies the previously missing ordered terminal
classifier and complete 32-word projection. It is a separately sealed proposal
for independent review, not implementation selection or Rust/product evidence.
Only this document and `verification/swift-semantic-adapter-terminal-correction/`
are owned. The original 152-member proposal, 35-member review and 21-member
pre-access preparation remain unchanged.

Successful resident/token/plan/victim rules, old APIs/ABI/report, all authority
getters, Candidate ownership/clear/restore rules and every numeric ceiling stay
unchanged. In particular, the proposed semantic7,680 + inherited471 =8,151
charge stays under8,192 preflight. Proposed finish256, guard128, role union29,344
and predicted aggregate488 remain ceilings/predictions requiring actual Rust
source, complete caller/Result lifetimes, fresh layouts and independent proof.
This correction does not claim its classifier fits those costs by measurement.

## Exact inherited Result and child boundary

The source identities remain accepted pack `analyzer.rs`
`1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b`
and `envelope.rs`
`2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef`.
`source-bindings.json` freezes exact source excerpts, full hashes and lines.
The shared-checkout context is `0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c`;
these exact copied sources, rather than the current live VM, govern this table.

The existing envelope core uses `?` for Budget construction, outer T42/F42,
output-safety and Arena construction, then **catches** `observe_inputs` errors,
constructs an outcome and uses `write_report(...)?`. Its final budget check can
also return an outer error. Preserve those distinctions in the new entry:

| Origin | Exact public Result behavior |
| --- | --- |
| Budget/T42/F42, output-safety, Arena failure | `Err(e)`; no aggregate and no 32-word observation |
| New finish256 or setup512 admission failure | Same existing Budget method error propagated as `Err(e)` before a semantic aggregate; no observation or invented paid flags |
| context/profile/header, record read/field/coordinate, drain/footer/EOF or input-stability error inside `observe_inputs` | Caught; if report succeeds, return aggregate with the existing framing/envelope diagnostics plus the projected cache-state observation below |
| New guard128 reservation failure in the walk | Caught existing Budget error, as above; no candidate mutation or semantic call |
| `write_report` reservation/metadata/position/write/length/identity error | `Err(e)`; no returned aggregate, even after prior semantic success/refusal/poison |
| Existing post-write used>limit test | `Err(AnalyzerError{code:4,stage:8,offset:0,record:0,reserved:0})`; no aggregate |

Propagate the original fixed `AnalyzerError` unchanged. Budget methods determine
their actual stage: setup-cap failure is stage2; replay subtraction failure is
stage6; report reservation failure is stage8. No new error code, normalized
replacement, fabricated output outcome or extra Error path is introduced.
`OutputUnavailable` keeps its existing proposed reason ID17 but **is never
emitted by a returned observation** under this Result contract. Output failures
are outer `Err`; partial report bytes remain failed evidence. There is no
all-zero observation accompanying an `Err`: it is absent, not a 32-word value.

For caught input errors, the accepted core gives code15 BINDING→framing
Unavailable/envelope Unavailable+FramingUnavailable16; code4 BUDGET→framing
AnalysisLimited/envelope Unavailable+FramingLimited18; every other code→framing
Invalid/envelope Unavailable+FramingInvalid17. A real read/IO-attempt failure
code6–9 is therefore an invalidating input error, **not** an invented resumable
IO-limit observation. Reserved-I/O-budget exhaustion code4 follows the budget
branch. A complete framing-only fixture normally has framing Decision
Unavailable with the fixture-framing getter true: Decision alone is not a
framing-success test. Preserve the old outcome verbatim.

## Closed classifier input

The finalizer uses separately maintained, private orchestrator receipts, not
caller booleans or public constructors. `terminal-contract.json` is the fixed
machine-readable schema; `classifier.py` is only its finite contract model.

`O` is either no outer error or the exact error already propagated at one of the
sites above. `C` is a closed normalization of the **actual** child result:

| C | Exact source/public child condition |
| --- | --- |
| InputBinding / InputBudget / InputInvalid | The three caught-input branches above, before consulting private progress |
| EnvelopePoison | Envelope InternalPoisoned5/reason15, or AnalysisLimited4/reason15; actual invalid debit is installed as poison by the accepted caller |
| EnvelopeUnavailable | Envelope Unavailable0/reason19 or20 after coherent input completion/limit; absent reply or unsupported private state is not a successful loan |
| EnvelopeRefused | Refused3/reason1–14 or21; also AnalysisLimited4/reason1–14, which retains an earlier real refusal despite later preflight limitation |
| Limited | `Ok(false)`, limited=true, complete=false, framing AnalysisLimited and envelope AnalysisLimited4/FramingLimited18 |
| Cap | `Ok(true)`, complete=true, limited=false, flags1 and envelope CapCutUnknownTail2/Observed0 |
| Closed | `Ok(true)`, complete=true, limited=false, flags0 and envelope ClosedEnvelopeObserved1/Observed0 |
| Unsupported | Every other public-child/loop combination, including contradictory flags, completion or boundary/reason pairing |

The accepted `finalize` tests input error before private poison, then validates
loop state, absence, poison and reply shape before CAP/closure. The new
normalization preserves that result rather than treating every child
AnalysisLimited as the same cause. It never alters either old outcome.

`P` is one private semantic progress tag: Absent, Valid, Poison, Unreadable,
Stale or Malformed. Absent means **zero actual semantic calls** and no latch.
An attempted call without readable backing produces the canonical Poison
guard reply without dereferencing state. Absent after a call, Valid without a
call, stale epoch, unsupported tag, contradictory latch or malformed progress
header is poison. Merely reserving setup/finish does not create observed state.

`L` is exactly one absorbing first semantic terminal latch: None, Refusal,
Failure or Limit. Refusal stores only new semantic reason6–13; Failure stores
reason14 and the actual first Failure record; Limit stores reason1 from a
present, underfunded private semantic admission. Ordinary private guard
readability/invalid-budget/commit/cleanup faults use Poison, not a normal latch.
After any latch, no later semantic call occurs. Later envelope/framing work
and combined charges continue only as already proposed. An injected second
semantic terminal result is stale progress and cannot replace the first latch.

`Q` is the last committed fixture snapshot, readable only after the guards
below: checked-record count M, last sequence M, work/instructions, the prior
envelope stage0–10, active op/function, resident count/bytes, held pins,
next_nonce and guarded plan/victim fields. Its selected slot/pin limits are the
already checked fixture limits. Counters/coordinates are u64, M≤N, resident
count≤slots, held pins≤pins, nonce≥1, masks are selected-slot subsets, and
committed⊆taken⊆selected. Active function<80,000 and op>0 are checked only
when stage≠Idle; inactive storage is never read as a live value. Refusal/Failure/
Limit has stop=M+1≤N and actual call count≥1. Failure's coordinate is that stop;
all other latches have no failure coordinate. Without a latch, M=N; Closed also
requires Q.stage=Idle. Any violated checked snapshot rule becomes poison.
Without a latch, call_count=M>0; with a latch, call_count=M+1. M=0 requires
the initialized empty snapshot (stage/work/instructions/resident count/bytes/
held pins all0 and nonce1). Resident count0 iff resident bytes0; held pins>0
requires a resident. These additional shape guards are exact, not implementation
choices. The complete named guards also live in the machine-readable table.
N and actual semantic call_count cannot exceed the successfully paid NC.
These are contract-model shape/coordinate guards, not proofs of semantic rows.
The successful-transition implementation must independently establish the row
invariants and source provenance.

`N` is the coherent final framing coordinate. `SS`, `SF`, `NC` are the separately
recorded successful semantic setup512/finish256 reservations and new8,151
combined-record charges. They are not read from P/Q. On any returned aggregate,
both admissions succeeded (`SS=SF=1`), so actual debit
`D=512*SS+256*SF+7680*NC`; NC includes paid records whose later read fails or
whose semantic call is skipped after a latch. On an outer `Err`, these costs
may exist internally but no typed flag/debit is returned. The source-constructible
input domain uses booleans SS/SF and NC≤4,194,304; this expression cannot overflow
u64. The actual budget enforces a much smaller executed prefix. An unproved
paid receipt cannot be supplied as an external input or infer authority.

## Total ordered precedence

Evaluate rows in order. Each row's guard is implicitly conjoined with the
negation of every earlier row, making the selected conditions disjoint. The
final two rows exhaust the remaining closed domain. No row after a state-read
failure can inspect Q. `Z` and `V` are the complete projections below.

| Row | Guard after earlier rows fail | Returned result/projection |
| --- | --- | --- |
| T00 | O contains an actual outer error e | `Err(e)`; no observation |
| T01 | C=InputBinding | Z(Unavailable0,FramingUnavailable2) |
| T02 | C=InputBudget | Z(AnalysisLimited4,Steps1) |
| T03 | C=InputInvalid | Z(Unavailable0,FramingInvalid3) |
| T04 | C=EnvelopePoison or P=Poison | Z(InternalPoisoned5,InternalPoison16) |
| T05 | P=Unreadable/Stale/Malformed, or progress header/call/latch contradiction | Z(InternalPoisoned5,InternalPoison16) |
| T06 | C=EnvelopeUnavailable/Unsupported | Z(Unavailable0,EnvelopeUnavailable5) |
| T07 | C=EnvelopeRefused | Z(Refused3,EnvelopeRefused4) |
| T08 | P=Absent with zero calls and no latch | Z(Unavailable0,EnvelopeUnavailable5) |
| T09 | P=Valid but Q/latch guard above fails | Z(InternalPoisoned5,InternalPoison16) |
| T10 | L=Refusal | V(Refused3,stored semantic reason6–13,stop=M+1,failure=0,tail=1) |
| T11 | L=Failure | V(ApplicabilityUnavailable6,FailureApplicability14,stop=M+1,failure=M+1,tail=1) |
| T12 | L=Limit | V(AnalysisLimited4,Steps1,stop=M+1,failure=0,tail=1) |
| T13 | C=Limited, L=None | V(AnalysisLimited4,Steps1,stop=N+1,failure=0,tail=1) |
| T14 | C=Cap, L=None | V(CapCutUnknownTail2,Observed0,stop=0,failure=0,tail=1) |
| T15 | C=Closed, L=None | V(ClosedFixtureObserved1,Observed0,stop=0,failure=0,tail=0) |

Thus a prior semantic refusal or first Failure survives a legal Release/phase
tail, CAP or a later ordinary preflight limit (T10/T11 before T13–15). A later
envelope refusal/unavailability suppresses that snapshot (T06/T07); a later
poison suppresses it as poison. A later read/footer/drift error supersedes it
through T01–03. A later output failure returns no aggregate at all. Caught input
error priority intentionally matches the accepted child before examining a
stale poison marker. None of these paths resumes semantics or becomes success.

## Every observation word

For `Z`, initialize all32 words to0, then assign word0=boundary, word1=reason,
word21=D, word22=SS and word23=SF. All other words stay0. In particular,
stop/failure coordinates, next_nonce, tail_unknown and fixture_state_observed
are0; **do not install Idle/MAX sentinels into suppressed extent**. Here0 means
unavailable/inapplicable, not a measured empty cache, known tail or nonce0.
Old framing/envelope diagnostics remain available in the unchanged child
members. No Q dereference, old valid prefix or stale aggregate supplies Z.

For `V`, the following assigns every word, with u64 MAX as the inactive sentinel.
`active = Q.stage!=0`; `miss = 3≤Q.stage≤10`;
`planned = 6≤Q.stage≤10`; `pending = Q.stage in{7,8}`.

| Word | Exact V expression |
| ---: | --- |
| 0 / 1 | selected boundary / reason from T10–15 |
| 2 | N |
| 3 | M |
| 4 | selected stop |
| 5 / 6 / 7 | M / Q.last_work / Q.last_instructions |
| 8 | Q.active_operation if active, else0 |
| 9 | Q.requested_function if active, elseMAX |
| 10 / 11 / 12 / 13 | Q.resident_count / Q.resident_bytes / Q.held_pins / Q.next_nonce |
| 14 | Q.requested_function&511 if miss, elseMAX |
| 15 / 16 / 17 | Q.selected_mask / Q.taken_mask / Q.committed_mask if planned, else each0 |
| 18 | Q.pending_victim if pending, elseMAX |
| 19 | Q.destination if planned and a feasible destination exists, elseMAX |
| 20 | selected failure coordinate |
| 21 / 22 / 23 | D / SS / SF |
| 24 / 25 | 1 / selected tail |
| 26 / 27 / 28 / 29 | each0: stored-prefix, full-replay, metrics and real-binding authority |
| 30 / 31 | each0: reserved |

If planned but obstructed, destination is MAX and no success event is invented.
Pending must name a selected slot within fixture slots. Feasible destination
must be within fixture slots; inactive fields may retain arbitrary private
storage but are never projected or dereferenced as live values. On Idle,
active_operation is0, function/plan/pending/destination areMAX and masks are0.
Failure preserves the snapshot **before** its record, including an open Taken
removal; it does not replace its stage with the child envelope's later Idle.
M=0 can be a real observed initial snapshot after an actual first semantic
refusal/Failure call; zero calls are always T08, never this observed snapshot.

The new reason ID15 IncompleteBoundary, like OutputUnavailable17, has no
canonical emitted row here. An inherited envelope incomplete boundary is T07,
and a contradictory open Q with a no-latch Closed child is T09 poison. Existing
enum IDs remain unchanged. Every emitted reason is determined above.

## Bounded evidence and remaining gates

`expected-cases.json` freezes full32-word expected rows independently of the
classifier implementation, including overlapping terminal cases. Outer-Err
cases explicitly expect `observation=null` and the unchanged five fixed error
fields. The executable checks are called **contract-model checks**, not Rust,
semantic replay, physical/device or product tests. Finite Cartesian controls
exercise all closed child/progress/latch classes and total mutually exclusive
row selection; declaration/custody checks bind the exact accepted source and
all old152+35+21 members before/after. Preserved preparation/authoring attempts
remain in this new packet.

Independent review of R1, root selection, actual source/loan/cleanup/borrow
proofs, full semantic field/transition controls, actual-File tests, fresh
compiler layouts and exact work/memory/caller accounting remain pending. Real
profile/selection/original-result/failure applicability/ledger/crypto/custody,
CLI/live VM/target, native/device/compiler/signing/store/customer/operations,
immutable published FieldLog and GA remain unavailable. No CI qualification is
claimed here. Computer use/capture/native runtimes/phones remain paused. No
old harness/model is executed, no unrelated process is queried, and no product,
profile/dependency/CI/root metadata, commit or push is changed by this lane.
