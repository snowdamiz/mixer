# Preaccess review-model correction supplement

Status: **frozen before new candidate access; old source inspection only**.
The original five-member preaccess freeze and its seal remain immutable. This
supplement records errors in that review model; it does not conceal or replace
them. No old or new Rust source has been executed in this lane.

The old source identity is
`verification/swift-ordered-retention-analyzer-envelope-correction/src/envelope.rs`,
SHA-256 `7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1`.
Only that source, the already allowed root addendum/numeric contracts, and this
lane's original freeze were read for reconciliation. New correction source,
producer tests, model and proposal remain unread and unselected here.

## Errors preserved and corrected

| Original frozen assertion | Finding from old source | Corrected control |
| --- | --- | --- |
| `normal-one-above`: before426/after1/debit425/spent425 makes caller predicate true | Lines290–292 require post remaining0 for every paid425 reply. The helper receives no entry budget. | Caller predicate must reject post remaining1/spent425/debit425. A direct leaf with valid readable state may accept entry426 and leave1; that is a separate private leaf threshold control, outside the production caller's exact425 construction. |
| `zero-budget-moved`: before425/after0/debit0/spent0 makes caller predicate false | Entry425 is invisible. The poststate equals an absent-state call entered with0 and returned coherent zero-poison unchanged. | Keep a leaf trace assertion that absent entry425 must remain425. Do not expect the predicate to distinguish that faulty trace from canonical entry0/post0 zero-poison. The correction must accept the canonical coherent zero-poison poststate. |
| `paid-impossible-subtraction`: before424/after0/debit425/spent425 makes caller predicate false | Its poststate is identical to a normal canonical425 call. Old paid branch accepts it. | Keep a leaf trace assertion that readable entry424 returns Steps/debit0 with unchanged budget. The poststate-only paid predicate accepts remaining0/spent425/debit425; it cannot recover whether a faulty leaf entered with424. Production provenance supplies entry425. |
| Paid malformed shape must be closed by existing latches/finalizer, read as a general no-reschedule guarantee | Paid debit branch does not inspect reply shape. `leaf_pending` permits status1 with any reason other than15. The finalizer rejects its enumerated malformed shapes only if that reply remains installed when finalization occurs. | Test debit, scheduling and finalization separately. Status1/reason1 is debit-valid when paid, is pending in the old helper, and is unavailable with zero extent if directly finalized unchanged. A later legitimate dispatch can replace it. Do not impose a broader invented corruption latch. |

The first row is a false preaccess predicate expectation. The second and third
are misplaced before/after obligations, rather than distinguishable malformed
poststates. The fourth is an overbroad reading of an existing defensive path.
The original JSON/document retain every original assertion and original hash.

## Effective controls by boundary

**Direct leaf:** the R2 expectation is unchanged. With entry spent0 and unreadable
prior state, private status3/reason15/debit0/spent0 must precede the threshold and
preserve the entry remaining budget, supplied arena and full Candidate2048.
Test lengths0/32/7,731,055 against credits0/1/424/425/426 and the full readability
boundary7,731,056. Readable first/later states with credits0..424 return actual
prior state as Refused/Steps, private debit0 and no mutations, even for malformed
next records. Valid readable normal calls at425/426 debit425 and leave0/1.
These are trace assertions with the actual entry snapshot available.

**Poststate-only caller predicate:** use only `remaining`, `spent` and reply words
as the real helper does. Paid425 requires remaining0 and spent425; positive
remaining with paid425 is rejected. Refused/Steps zero requires remaining<425,
spent0 and debit0. The required correction additionally preserves canonical
zero-poison status3/reason15 with spent0/debit0 for returned remaining
0/1/424/425/426. It must not substitute poisoned425 for that coherent zero reply.
Reject debit1/424/426/u64::MAX, incompatible spent, and paid nonzero remaining.
No predicate claim is made about an inaccessible entry budget. The effective
table includes old source-derived outcomes and correction expectations; none
are runtime results.

**Canonical helper provenance:** `poisoned(debit)` at old lines102–103 produces
status3/reason15, zero extent and reserved words14/15 zero. `reply` at99–100 maps
the twelve state words and zeros14/15. Its actual old leaf callsites produce
status1/reason0 or status2 with named reasons1..13. Arbitrarily calling a private
helper with invented status/reason is not an actual leaf-producer path. Source
review and bounded tests must establish the selected producer's canonical forms;
the debit predicate is not a reply-shape or entry-history certificate.

**Scheduling and finalization:** status3 or reason15 is terminal; R1's actual
status1/reason15/stale-state999 remains a binding no-later-dispatch control.
Canonical status2 Refused is terminal. In contrast, old status1/reason1 remains
pending. If directly finalized with valid successful framing and no subsequent
dispatch, status1/reason1, status2/reason0, unsupported status/reason, state>10,
phase>5, mask>=64 or failure flags>1 yield Unavailable/UnavailableState and zero
extent. Poison takes precedence over CAP/state examination after framing input
validation. Input Err retains its earlier suppression path and paid debit.
Do not infer that all fabricated private tuples can never schedule or project.

**Public/orchestration invariants:** old lines320–323 construct entry425/spent0,
install only the complete returned reply, mark it valid and apply the predicate.
That provenance makes paid remaining0 meaningful. Main B471 still prepays and
retains425 before decode and dispatch decisions. Preserve the public formula,
zero-call581, report suppression/prefix, actual safe-File and API controls from
the original freeze. The G111/112/113 vectors refer to credits available at its
local admission, not total public input limits. G funding/new pre-read ownership
still requires independent accounting and explicit root selection before review
of new code. No additional guard budget is inferred from this supplement.

## Remaining limits

General arbitrary-private-reply corruption defense is not established by the
old implementation or the accepted R1/R2 contract. Only the named source-derived
helper cases and finalizer conditions above are frozen. A broader guarantee
would require an explicit root contract decision and independently accounted
source changes; it is not silently promoted to an acceptance requirement.
There is no unresolved ambiguity for the three budget rows once entry traces
and poststate inputs are kept distinct. Canonical zero-poison preservation is
still a required new-source behavior, not a fact established about old source.

All planned new-source methods, API probes and File controls remain unexecuted.
No native/UI/capture, hosted harness, process discovery, compiler or runtime was
started. No product/root metadata, old packet, original freeze, commit or push
was changed. Await root's exact selected-candidate handoff.
