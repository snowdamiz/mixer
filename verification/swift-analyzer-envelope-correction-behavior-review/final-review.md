# Independent selected-source behavioral review

Verdict: **withhold acceptance for R2, missing-prior-state debit precedence**.
The exact selected candidate is envelope SHA-256
`7b8237abbaec492e595508eb7456dab38fbb0d92d8d3cd5a88184f7c1082b9d1`,
under producer seal
`4ddff8237bd49cab9f6191be89e4764966e1af5dfa686bb931ac1372d1e98df1`.
The root-selected numeric amendment is
`199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c`.
This lane changes no candidate, original packet, baseline document, root metadata
or gate, and makes no commit or push.

The independent final run executes19 methods: **18 pass, one fails**. One
external positive and eight independent expected-negative API probes pass.
The producer's70 methods,21,714 model comparisons and32 layouts are verified
producer evidence, not independently rerun results. This review neither retries
the original timed-out64 closure nor claims a completed independent70 replay.

## R2: unreadable prior state is charged before poison

The accepted implementation-accounting addendum states: “Absent state ->
InternalPoisoned/debit0; otherwise remaining<128 -> Steps/prior state/debit0”.
The selected numeric amendment changes the normal threshold to425 while
preserving that absence priority. The frozen independent baseline and selected
supplement preserve it. Root confirmed that unreadable required prior state is
a concrete negative boundary for this rule.

`independent_absent_prior_state_precedes_normal_debit` supplies private arena
lengths0 and32, neither of which can contain even the first required prior-state
cell. It tries credits0,1,424,425 and426 with a valid next record. All ten calls
return status3/reason15 and leave arena/candidate bytes unchanged. The four
normally funded calls nevertheless report debit425, spend425 and reduce the
budget by425. Expected private debit/spend is0 for these absent-state cases.
The assertion records actual debit vector
`[0,0,0,425,425,0,0,0,425,425]` against ten zeros.

The source subtracts the normal debit and sets `spent` before testing
`arena.len() < 7_731_056`. This explains the exact output. It is a private
defensive contract mismatch; the normal safe-File walk supplies an initialized,
full arena. Public paid-record accounting remains a separate reservation and
must still retain425 after a successful B471 charge. This finding does not
authorize changing that public counter or borrowing unassigned funding.

The exact source, negative control, stdout/stderr hashes and debit table are in
`final-review/finding-R2.json` and `final-review/runs/run-2/`. Root must coordinate
any separate source/funding correction and a fresh exact-source review. This
lane does not change or loosen the frozen expectation.

## Observed passing controls and their limits

The prepared R1 fault now passes: status1/reason15 with stale state999 cannot
schedule another leaf and finalizes as poison with zero extent. The poison
cross-product, absent backing, first/later guards, all credits0..424 for valid
and malformed records, exact425/426 funding and final checked-cell refusal pass.
The full underfunding loop makes1,700 guarded calls and compares complete
arena/candidate snapshots. A separate private call counter observes no later
leaf dispatch after reason15 while paid subdivisions continue accumulating.

Fresh actual Files cover hit/build completion, a CAP cut, unknown context,
profile/body/header errors and late-footer suppression. Seven File fixtures
each execute both old and new public entries. Their framing classification,
counts/error and fixed49,152-byte reports match; only report word9, truthful
authored steps, is excluded from byte equality. Complete reports retain version1,
reserved/semantic zeros and false acceptance getters. Scripted private I/O
additionally covers late EOF/error/metadata drift, paid decode failure, output
error/zero/overreport/postwrite failure, failed limited drain, alias identity,
bounded I/O and allocation refusal. Those scripted receipts are host/private
controls, not actual File, native or device claims.

The exact main-admission debit checks pass0/534/581 for setup/finish/guard
reservation failure. No selected candidate cell is initialized before those
reservations. The independently searched five-record threshold is4,965,753;
one less retains four records and debit2,281. A lower successful limited drain
has no reply, zero extent and debit581. A bad footer still overrides a limited
observation. These are the exact fixture's bounds, not a record-capacity claim.

`coverage.json` maps all32 frozen control IDs to exact executed methods, source
observations, the R2 failure and remaining gaps. It does **not** mark32 passes.
The CAP method's eleven prefix cuts cover ten distinct states because Ready6
appears twice; an independent Hit2 CAP cut remains pending. No artificial
partial-commit callback was added to the infallible unrolled commit. The private
poison fault controls and source inspection cover its defensive result, while
arbitrary partial-memory-failure execution is unqualified. Complete source
costs/types/lifetimes and F05 funding proof belong to the separate final
accounting review. This packet does not qualify the full finite model matrix,
all old44 methods, every actual-File alias variant or target behavior.

## Preserved failures, ownership and cleanup

Run1 passed17 of18 methods. Its failure was a reviewer assertion comparing the
entire arena before and after setup refusal; inherited framing-reader writes
legitimately change that buffer. The corrected assertion checks the twelve
selected cells, reply absence and exact debit. The old source, complete raw
failure output, classification and narrow diff remain retained. Candidate
source and frozen expectations are unchanged. Run2's different failing test is
the concrete R2 candidate mismatch above. The collector accepted exit101 only
to finish API probes after that known failing control; it does not call the
failed suite a pass.

Each command has an owned session/group, file-backed partial stdout/stderr,
deadline, exact argv/tool versions and cleanup receipt. The runner's deliberately
timed-out Python qualifier preserves its partial marker and confirms direct-child
reaping and owned-group disappearance. No analyzer command timed out. Only
targeted owned-group liveness was checked; no unrelated process discovery ran.
Owned fixture scratch is archived before removal and owned binaries are hashed
before removal, after all corresponding child/group cleanup receipts succeed.
`cleanup.json` maps retained archive members to original bytes/hashes.

All306 admitted producer members and both earlier freezes (39+13 members) verify
unchanged before/after the runs and cleanup. The source/test archives, exact
production prefixes, module-only appends, test changes, commands and raw outputs
are sealed in this final-review packet. Computer use, capture, native runtime,
simulator/emulator and phone checks remain paused. No hosted harness, engine,
CLI, customer, signing/store, published FieldLog, operations or GA evidence is
promoted. R1 passes in this scope; acceptance remains withheld for R2 and the
explicitly incomplete qualification boundaries.
