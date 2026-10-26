# Fixture cache-state prerequisite proposal

This proposes the next bounded W08 implementation contract: check the successful
resident, token, direct-map plan and baseline victim transitions in a separately
named **fixture-only** safe-File consumer. It is source-only preparation for
independent review and root selection. It is not selected implementation,
semantic replay acceptance, another retention policy experiment or a target run.

The binding product scope remains `mixer-product-plan.md`, especially sections
1, 10, 20, 22 and 29. The current context is commit
`0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c`. At this proposal's handoff the
accepted envelope's Rust 1.98.1 CI run 40273904826 was queued, not passed. Root
owns its later status/artifact audit. Computer use, capture, native simulator/
emulator execution and phones remain paused. This lane ran only its own finite
source/custody/arithmetic checks; no old harness or product workload was run.

## Why this is the next boundary

The observed full Swift attempt exhausted CacheWork after 23,358,291 guest
instructions. The accepted attribution measurement assigns 53.907% of that
budget to rebuilding previously decoded functions. The two rejected policy
experiments and the unselected proposals do not establish a better policy.
Framing now checks immutable **synthetic** profile identity and closed wire
fields. The envelope additionally checks synchronous acquisition/lifecycle
order. Neither establishes that a recorded hit actually has a resident, that a
published token is the next real token, or that evictions match the copied
baseline algorithm. This proposal closes that finite successful-transition gap.

Only after separate real profile, source/selection, original-result, ledger and
custody qualification could this machinery support questions such as which
functions were rebuilt after actual evictions, whether a direct-map plan was
retained or replaced at that acquisition, and which pinned residents constrained
the observed victim prefix. This slice alone answers those questions only for
independently authored synthetic fixtures. It cannot establish target benefit,
the omitted CAP tail, avoided work, failure applicability, actual decoding cost,
refund/quarantine correctness, guest completion, CPU/RSS, or a replacement policy.
Window/histogram/credit metrics and real historical replay are separate work.

## Exact authority and immutable compatibility boundary

The consulted bytes, exact paths, sizes and SHA-256 values are frozen in
`verification/swift-semantic-adapter-prerequisite/input-manifest.json` and
`source-seams.json`. The accepted design/reviews are design authority. The
copied instrumented completion candidate is the authority for its successful
emission seams. It is **not** a claim about the current live VM source tree.
No current VM tree, frozen hosted inspector/authority driver, rejected WorkerV2,
broad hosted harness or browser callback lane was read, imported or executed.

The source identities are:

| Consulted source | SHA-256 | Provenance |
| --- | --- | --- |
| copied `experimental/cache/borrowed.rs` | `3f3d989216b3e9208e1ff875ec07d6f0940f9f890c3d0035c1544d871e3022a8` | accepted completion candidate, exact archived member identity recorded by accepted design |
| copied Swift `cache.rs` | `90d540a121c0f1c2d941fb74ed652a492f555203bb8543a7aa1d440ccbba7cfd` | same candidate closure |
| copied `writer.rs` | `25e95e2d79068f41b77ba9d23a391797a966b96057686cad2de48b2733193757` | exact closed diagnostic wire source |
| copied `observer.rs` | `9c3c31d6406da4a86abcb4893b0813048f07455340f0976d68adc48dc7805aee` | exact emission coordinates and optional original failure cursor |
| accepted library `analyzer.rs` | `1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b` | 86-member portable envelope pack |
| accepted library `envelope.rs` | `2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef` | same pack |

The design receipt's context revision is
`68468f8fb73f21d2e4b388c41ad15fd01bfd0d93`, its source-tree digest is
`97d53ce629074ea41173c397071057e7af0325e2b2be9cc8f4b1c85ae02be2a5`, and the
132-file completion candidate manifest identity is
`007ba0dc9aaac2402cbf49d08ffaf8a1e2f75e5813ba4996e4936be4d0a92357`.
That context revision is not falsely assigned to each instrumented candidate
file: the exact member hashes above identify those bytes. No archive restoration
or executable reuse is required for this proposal.

Preserve existing `analyze_fixture`, `analyze_fixture_envelope_v1`, all old public
types/getters, enum values, `ReplayOutcome` 104-byte layout, envelope observation
128-byte layout and envelope outcome 232-byte layout on the recorded Apple arm
host. Preserve the exact 49,152-byte `MIXANL01` report schema, reserved words,
validity bits and existing behavior. No new report field or validity bit is
assigned. Existing test expectations that admit arbitrary framing stage
sequences remain valid for `analyze_fixture`. No new semantics is injected into
either old entry point. The existing 86-member pack remains an immutable
regression input; a future new source pack has its own manifest and review.

## Proposed interface

Add a separately named public boundary, after independent contract review and
root selection:

```rust
pub fn analyze_fixture_cache_state_v1(
    stream: &mut File, profile: &mut File, context: &mut File, output: &mut File
) -> Result<FixtureCacheStateOutcomeV1, AnalyzerError>;
```

It uses the accepted safe distinct/quiescent regular-File borrow contract,
`MIXFIX01` context and `MIXPRF01` fixture profile, with the same input lengths,
closed fields and limits. No new context version, arbitrary initial-state API,
raw-record API, boolean authority, digest authorization, FD CLI or live adapter
is introduced. Synthetic rows come only from the actual fixture profile parser;
initial residents/tokens/plans are empty and nonce is 1. AcquireBegin may name
an undefined function because a real source failure can precede Lookup. Every
subsequent successful body-bearing event must join the defined fixture row.

`FixtureCacheStateOutcomeV1` is a private-field, non-Copy, non-Clone repr(C)
aggregate of `ReplayOutcome`, unchanged `FixtureEnvelopeObservationV1` and the
new fixed 256-byte `FixtureCacheStateObservationV1`. Getters borrow its members;
no constructor or serializer is public. Expected Apple arm aggregate size is
488 bytes; a complete Result/source/caller place is bounded by 512 bytes, subject
to fresh compiler layout verification. This is additive API, not an old ABI
change. The output File still receives the framing-only fixed report with no
semantic metrics. The typed fixture observation is not encoded into that report.

The new observation has exactly the 32 u64 words listed in `contract.json`.
Boundary IDs are Unavailable0, ClosedFixtureObserved1, CapCutUnknownTail2,
Refused3, AnalysisLimited4, InternalPoisoned5, ApplicabilityUnavailable6.
`stored_prefix_validated`, `full_replay_accepted`, `semantic_metrics_valid` and
`real_binding_verified` are literal false getters in every variant. Counts are
fixture coordinates/state observations, never accepted semantic-prefix metrics.

`observed_records` is the coherent final framing walk coordinate; the old
framing outcome retains its own independent counters. `cache_state_records`
includes each supported checked ordinary record up to, but not including, the
first refused/unavailable record. Active operation/function/plan/destination
fields use0/MAX when their discriminator is Idle, even if private guarded
storage retains older values. Resident/pin counts are current fixture rows,
not final consuming-ledger values. A late framing/output failure zeros every
new state/coordinate extent; paid debit and literal false authority fields
remain truthful. `fixture_state_observed` only describes the availability of
that synthetic snapshot. Reserved words are always0.

A private semantic leaf receives the same **borrowed** internally decoded
record as the envelope, a checked immutable fixture config/profile view, a
mutable arena borrow, the sole retained Candidate2048 borrow and a private
exactly prepaid semantic budget. No words or prevalidated/accepted boolean can
be supplied from the public API. A same-iteration, nonescaping private loan is
constructed only after actual record-field checks and the actual envelope
reply/debit audit succeed. It carries the record borrow and coordinate, not an
authority boolean. No public/importable loan or record constructor exists.
This requires a reviewed private seam in the new orchestrator, not an export of
the old leaf or a caller's claimed successful envelope outcome.

The new walker may commit the already checked envelope before semantic
preflight. A semantic refusal is terminal for semantic dispatch: it never
resumes, never exports the envelope successor as a cache-state successor, and
never claims the arena is the prior valid state after a partial commit. It
keeps the prior cache-state coordinate only as a historical observation. The
framing/envelope walk may still validate/drain the bounded remaining input;
their counts and debits stay distinct. A later framing/footer/drift/output
failure suppresses the cache-state extent and supersedes its eligibility.

## Source-bound successful transitions

The source seam inventory freezes exact line spans and excerpt hashes. Guards
below add semantic conditions to the accepted envelope; they do not replace it.

| Seam | Copied source | Required successful-transition rule |
| --- | --- | --- |
| pre-Lookup admission | borrowed 736–762 | Before accepting Lookup, the requested body is defined, current nonce can increment and an actual free pin slot exists. Remember first free slot and current nonce. Do not reject AcquireBegin itself merely because later success is impossible. |
| resident Lookup | borrowed 774–791 | Scan selected resident slots: miss means no matching function; hit means exactly one matching resident at the emitted slot. Its immutable identity comes from the fixture row. Never learn a resident from Lookup. |
| direct-map plan | Swift cache 2203–2268 | Cell is `function & 511`. Empty/conflict/match must describe the actual prior cell. Same function requires complete offset/length/type match. Only completed empty/conflict PlanEnd replaces it. Match retains it; PlanBegin never publishes. |
| byte readiness | borrowed 800–824 | MissReady bytes are positive, within fixture entry capacity, with exact base/capacity. Sum actual resident bytes using checked arithmetic. A previously known matching plan byte result must agree. A successful scan may remain with unknown bytes before MissReady. |
| victim selection | borrowed 823–842 | Choose the shortest eligible prefix ordered by `(last_used, slot)`, exactly equivalent to repeated strict-min source scans. Eligible means occupied, unpinned and not already selected. Start destination at first empty; replace it with every selected victim, so final destination is the **last victim**, including when an empty slot existed. |
| emission/Take/Commit | borrowed 853–868 | Emit selected victims in ascending **slot** order. Begin checks exact bytes and pins0; Taken removes immediately; Commit must join that actual Take. No rollback, synthetic Commit or inferred refund. |
| construction | borrowed 871–897 | BuildBegin needs a feasible complete plan with every selected eviction committed; bytes equal MissReady. BuildReady closes only the temporary build. Neither creates a resident/token. |
| publication | borrowed 898–912 | Built publication uses exact destination; hit publication uses its Lookup resident. Use remembered first-free pin slot and current nonce, increment nonce checked only on success, increment resident pins exactly one, and set `last_used = PinPublished.work`. |
| release | borrowed 633–710; Swift cache 1427–1436 | Join live pin_slot+nonce, resident entry, function/offset/type and bytes; len is MAX. Exact post-count is prior minus one. Clear only that token, preserve resident/last_used. Idle-only envelope guard remains essential. |

A successful Lookup with nonce MAX, no free token slot or undefined function is
Refused. A MissReady may describe an obstructed plan because the source emits it
before planning fails. Preserve that obstruction; any subsequent successful
EvictBegin or BuildBegin is Refused. The genuine Failure, if present, remains an
unavailable applicability boundary. Successful generic index internals are
observed only through Taken/Commit/publication seams; no fictional index events
or unseen allocator/decoder results are reconstructed.

At the **first Failure14**, stop cache-state observation before that record as
`ApplicabilityUnavailable/FailureApplicability`, record its observed coordinate,
and latch terminal semantic dispatch. No triple is semantically accepted merely
because kind/code/stage ranges pass. Do not force requested-function equality:
the observer preserves the original optional cursor, and header failure can
precede meter cursor adoption. No matching failure or zero ledger authorizes a
failed success path. Subsequent Release records can still be envelope-observed;
this cache-state slice does not interpret them after its terminal boundary.

At sole CAP with no earlier refusal/unavailability, preserve the checked fixture
state at its observed cut, including open scan/build/Take and live pins.
`CapCutUnknownTail` neither closes the operation nor clears any row. Non-CAP
requires the accepted closed envelope. A complete no-Failure fixture may be
ClosedFixtureObserved; real replay acceptance remains false. Empty streams,
absent/private malformed state, failed setup and poison have explicit
unavailable or poisoned observations, never fabricated empty success.

## Fixed state, transaction and accounting obligations

Use only the accepted arena regions: Function80,000x96, Resident64x64,
Pin64x48, Plan512x40 and named control/active/planner scalars. Immutable fixture
identity fields are never overwritten by events. Resident generation/reserved
stay zero; publication/acquisition coordinates are labelled derived fixture
coordinates, not unseen product generation state. Pin rows record entry, actual
published nonce, operation, acquisition ordinal (the monotone operation number),
and publication work/instruction coordinates. These are fixed fixture
coordinates; no held-interval metric is granted here. Plan requested_bytes starts
unknown0 and becomes known only at successful matching MissReady. No recency,
window, histogram, top-list, expanded map or spare arena store is added.

Every accepted transition changes at most one resident row, one pin row, one
plan row and 32 named scalar words. Preflight reads/checks all bounds/arithmetic
and stages the complete delta; only then do fixed infallible checked-range
copies commit it. No fallible callback/I/O/allocation follows first mutation.
Unexpected partial commit poisons and suppresses every state extent. Refusal
leaves semantic arena state unchanged. Induction from empty construction plus
local transitions preserves resident uniqueness, token ownership, pin totals,
resident bytes and plan identity; a second growing invariant structure is not
permitted. Private corruption controls must exercise that induction boundary.

One retained Candidate2048 is shared sequentially, never passed/returned by
value and never co-borrowed by the two leaves. Semantic scratch layout is:
timestamp64x8 at0, merge-index A64x8 at512, merge-index B64x8 at1024,
Resident64 at1536, Pin48 at1600, Plan40 at1648, scalar32x8 at1688 and104 zero
reserved bytes at1944. Stable bottom-up merge sorting uses at most321 pair
comparisons and384 index moves over six passes; keys are read once from the
arena into the timestamp scratch. Eligibility uses MAX-tailed indices, not
invented timestamps for ineligible slots. Per record, after any semantic
return, clear the scratch **in place** and restore candidate bytes888..983 from
the envelope's12 arena scalar cells7,9,10,11,12,13,14,64,65,66,160,161. The next envelope call
therefore receives its exact previous payload and zero nonpayload bytes. No
fresh `[0;2048]` source/destination pair is created each record. All clear,
restore, borrow and transfer work must be included below.

The new walker proves the full arena length and all12 restore ranges before
granting the private semantic loan. The same exclusive, non-resizable arena
slice survives through the leaf and cleanup, and semantic writes are disjoint
from those12 envelope cells. Every ordinary success/refusal/private Error reply
returns to one cleanup block before any next leaf dispatch; it cannot use `?`
or another outer return that bypasses cleanup. Cleanup has no callback,
allocation, fallible conversion or unproved range after the first clear store.
The source ledger must account for all256 in-place zero-word iterations,
12 complete scalar loads and restores, their loop/borrow/copy/return work and
every source/destination place. No2048-byte zero initializer is hidden in a
helper argument. An outer read/footer/drift/output Error occurs only with the
candidate already clean/restored; pre-candidate setup Error has no such owner.
If private readability/ownership proof fails before a loan, the guard does not
touch scratch. An unexpected commit/cleanup fault latches poison, suppresses
extent and disables **both** later leaf dispatches, so no damaged candidate is
reused; only bounded framing/drain/finalization may continue. A failure cannot
claim successful restoration when the proof was unavailable. These paths are
mandatory independent controls, not exception-based cleanup assumptions.

Global ceilings stay arena8,388,608, complete named transients65,536,
reserved transients41,984, authored steps268,435,456, setup65,536,
report3,000,000, I/O263,584, next-record preflight8,192,
Rust report49,152 and aggregate report65,536. The proposed new-path ceilings are:

| Proposed semantic per-record group | Maximum authored debits |
| --- | ---: |
| admission, prior controls and record loan | 256 |
| up to64 resident probes plus64 token probes and scratch seeding | 2,560 |
| up to321 stable merge comparisons,8 each | 2,568 |
| up to384 index transfers,2 each | 768 |
| up to64 selected-prefix arithmetic steps,10 each | 640 |
| complete delta staging/commit plus candidate clear/restore | 640 |
| complete reply/received/progress transfers, audit and terminal paths | 248 |
| **semantic ceiling per successfully paid combined record** | **7,680** |

These are **proposed admissible source-work ceilings**, not a verified ledger
for missing Rust. Each micro-operation, loop guard, fixed copy, little-endian
conversion, full Result and caller move must map exactly once to a ledger row;
scalar blocks use at most16 named operations/group and copies at most128 bytes/
group. Group maxima are not interchangeable spare credits. Missing or
over-budget mapping blocks implementation acceptance; it never increases a cap.
No implicit optimizer elision supplies the bound.

The inherited combined framing/envelope/wrapper record charge stays471 on old
paths. The new path prepays exactly471+7,680 = **8,151**, only after unchanged
8,192 preflight, leaving41. Charge the full amount even if a later read or
framing check refuses, semantic dispatch is already latched or a later footer
invalidates observations. The old public envelope debit remains exactly
`534*S_paid + 47*F_paid + 425*N_B`. New public fixture semantic debit is exactly
`512*SS_paid + 256*SF_paid + 7680*N_C`; N_C counts successful new combined
charges, not leaf invocations or valid records. No refund or double counting.

Proposed extra semantic setup512 reserves fixed scalar initialization/views and
all new wrapper source/destination work. It reuses the already initialized
Candidate2048. Extra finish256 reserves projection, complete aggregate/Result/
caller moves and early-error finalization. A separately reserved terminal
guard128 covers one absent/readability/invalid-private-budget/underfunded leaf;
it latches immediately and cannot be reused. Old G112 retains its existing
envelope ownership. The report reserve must fund old6,446 +new256+128 =6,830;
actual per-source finalization and zero-call paths still require review. Existing
setup allowance must be checked against the **entire** new setup, including
profile/context/setup failures, rather than only512. Reserved I/O funding and
drain/EOF limits remain unchanged. No semantic tail runs after a budget stop.

Proposed reservation order is the existing Budget/T42/F42 boundary, then new
finish256 **before** any new semantic Progress/observation/aggregate owner,
then new setup512. If new finish admission fails, only the existing funded
fixed AnalyzerError path may return; no new aggregate is constructed. Setup
failure preserves whichever reservations actually succeeded. After actual
context/profile/header admission, reserve the unchanged envelope setup534,
finish47/G112 and new terminal guard128 before candidate/scalar mutation.
No guard or inactive branch funds an otherwise unpaid early return. Every
one of these proposed amounts and declaration sizes remains provisional until
actual Rust source, complete caller/Result lifetimes and fresh layouts are
independently reconciled.

The conservative historical fixed non-record allowance in `contract.json`
leaves an arithmetic maximum of32,317 paid8,151 records under the global cap.
That is an upper bound, not a complete historical replay promise; actual
setup/I/O/refusal can stop earlier. The original2,889,656-record arithmetic
envelope would exceed this cap by a wide margin. This source-only prerequisite
is useful through finite fixtures and makes no claim to consume it in full.

Keep all existing complete24656-byte storage roles. Proposed additional roles
are control1,280 (within control8,192's prior6,656), wire256 (within wire3,072's
prior2,616), report2,896 (within report8,192's prior4,296) and setup256 (within
setup12,288's prior5,168). Total proposed complete union29,344 <41,984; no
23,552 unassigned global margin is spent. Candidate remains exactly2,048.
Control covers private Progress144, both complete reply/received128 places,
record/config/arena/candidate/budget borrows, loop/prior/helper/Option/Pair
places and errors. Report covers observation source+destination512, aggregate
source+destination976, complete Result source+caller1,024, projection256 and
error128. Union is a conservative named-role bound, not simultaneous stack/RSS.
The future ledger must locate every source/destination, its lexical phase and
drop boundary, including error paths; no by-value loan/candidate/array move or
missing caller Result may be ignored. Fresh size/layout evidence is mandatory.

## Independent implementation tests to prepare before source access

`test-design.json` freezes finite success/negative/refusal cases with expected
full scalar/row results. It is a test **design**, not executed semantic evidence.
The independent verifier must encode raw16-word records/closed frames and
fixture rows separately, before reading new producer code. Its victim oracle
uses a sorted eligible prefix; implementation merge code must not be imported.
All observations must assert four false authority getters and zero reserved
words. Key expected outcomes include:

* One built publication then a hit publishes nonces1/2 to pin slots0/1, resident
  pins2 and `last_used` equal to the second publication's work. Releasing nonce1
  leaves pins1 and preserves last_used; duplicate release is Refused.
* With base0,capacity10,request6, one empty slot and residents
  slot1(bytes3,time9), slot2(bytes3,time1), select only2 and publish to2,
  preserving original empty0. With request8 select2 then1, emit1 then2 and
  publish to1. Timestamp ties choose the lower slot.
* PlanBegin followed by CAP publishes no plan. Completed empty/conflict PlanEnd
  publishes complete identity before byte-count readiness; CAP there retains
  unknown bytes0. A colliding function+512 replaces the named old function.
* Failure immediately before Taken retains its victim; after Taken retains the
  removal; after BuildReady creates no resident/token. All three terminate as
  ApplicabilityUnavailable at the Failure coordinate, with no synthetic Commit,
  refund, rollback, failure equality or cleanup claim.
* Exact8,151 new charge, preflight8,191/8,192, semantic private7,679/7,680,
  missing state at funded/unfunded budgets, finish/guard/setup failure, late bad
  footer/drift/output and complete Result/candidate ownership are independent
  controls. Old API/layout/report byte behavior is checked unchanged.

Required future evidence also includes every supported successful kind with
all body/payload fields independently mutated, slot/pin limits1/64, 64-way
ties/reverse timestamps/pinned obstruction, nonce MAX-1/MAX, u64 checked sums,
plan match/empty/conflict, fabricated resident/token duplicates, stale token,
Taken/Commit ordering, all CAP cut states, terminal nonresumption, poison
precedence, zero-call absence, allocation/read/write/EOF/drift refusal and
fresh public API rejection probes. No synthetic initial-state shortcut can
qualify the production entry: private state seeding, if used to reach numeric
extremes, is labelled separately from actual-File controls from empty state.

## Remaining selection gates and limits

Independent contract review must resolve the proposed source-work ceilings,
private seam/loan provenance, exact scalar write ownership, candidate reset
schedule and complete owner/transfer ledger before root selects implementation.
The byte regions and aggregate size predictions are not compiler or behavioral
evidence. Root may select a corrected finite contract; this document cannot
silently authorize a wider checker or a changed old API.

No real profile generator, selection/source verifier, registered selection
receipt, original-result adapter, code/kind/resource/stage/cursor applicability,
all15 ledger joins, cryptographic/custody host adapter, CLI/FD adoption,
corrected writer, target driver or live VM integration is implemented or
selected. Original invalid/failure15 sidecars remain immutable. No policy,
dependency, cap, signing key, customer/production action or root gate is changed.
Physical/native/compiler/signing/store/operations/published-package FieldLog
and accountable GA requirements retain their actual pending status.

The proposal receipt records only source hashes, finite declaration/arithmetic/
custody results and owned cleanup. It does not relabel an unrun native or Rust
semantic test as passing. No native/capture/runtime instance, scratch build or
unrelated process was started or queried. Root retains acceptance and delivery
authority; this lane made no commit or push.
