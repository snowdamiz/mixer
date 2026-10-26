# Independent selected absent-state behavioral review

Verdict: **the frozen corrected controls pass in this bounded host review**.
Root acceptance remains separate. The selected source is envelope SHA-256
`2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef` with unchanged
parent analyzer `1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b`.
The root selection is `ae90b289519d0588a27cae4db0a7ce4a74ce3016c9c2f790fd962775ec4fd2e0`.
No candidate source, product code, root metadata, old packet, commit or push is
changed by this review.

There are **14 distinct passing methods against byte-identical selected source
copies**: twelve in run3 and two narrow admission/error methods in run5. A
separate test-only dispatch overlay has **two passing methods** in run6; it is
not counted as unchanged-source execution. One external positive and eight
expected-negative API compile probes pass with the intended diagnostics. One
host layout method observes32 complete type/handle/result layouts on rustc1.99.0,
aarch64-apple-darwin. These counts are not a full70/model, native or device replay.

## R2, caller validation and unchanged accounting

All15 absent-state calls at lengths0,32 and7,731,055 with credits0/1/424/425/426
return canonical status3/reason15/debit0, preserve entry spent0 and remaining
budget, and preserve every supplied arena byte and Candidate2048 byte. The exact
original ten-call debit vector is now ten zeros. Full readability at7,731,056
separates that path from ordinary debit425 calls. Readable first/later state,
valid/malformed next records and every credit0..424 produce1,700 unchanged
Refused/Steps prior-state returns. Exact425/426 ordinary observed/refused controls
retain debit425 and leave0/1 respectively. Twelve invalid nonzero entry-spent
controls return unpaid poison and preserve supplied state; their incoherent
spent/debit forms are rejected by the caller predicate.

The independently frozen corrected caller table has19 passing poststate cases.
Canonical zero-poison with remaining0/1/424/425/426 survives the validator without
being replaced by poisoned425. Paid425 requires post remaining0/spent425; the
paid remaining1 case is correctly rejected by the caller helper even though a
direct private leaf can accept entry426. Malformed debit amounts and incompatible
spent forms are rejected. A helper without an entry-budget input cannot certify
that a poststate came from the correct earlier budget; before/after preservation
is checked on the direct leaf and exact425 construction is checked at the source
callsite.

G is independently root-selected as the existing single112 reservation covering
one terminal unpaid absence/invalid-spent/underfunded path, with main-paid W24
owning reply installation/validation/fallback. This review does not redo the
accountant's352 offline checks or claim source costs from runtime timing. Local
G admission at111 fails with debit581, no reply and unchanged selected cells;
112/113 pass. Setup and finish refusal retain0/534 respectively before selected
cell initialization. Full-arena Reader buffer writes are allowed on setup refusal;
the assertion checks selected cells rather than the entire arena. Public B471
continues to retain425 before decode or dispatch decisions. The public formula
`534*S_paid + 47*F_paid + 425*N_B` remains unchanged.

## File, report, latch and privacy evidence

Seven fresh actual-File cases run both public APIs: phase completion, CAP,
late bad footer, bad header, bad profile, unknown context and a malformed second
record. Framing decision/count/error match, and all49,152 report bytes match
after excluding only truthful steps word9. Reports retain version1, semantic/
reserved zeros and false acceptance getters. Completion/CAP debit2706 for five
paid records; the bad second record retains1431 for two paid records despite
only one framed record. Input errors suppress state extents. These fixtures test
the framing/phase envelope, not hit/build replay or a full finite FSM matrix.

Two further actual-File cases use the explicitly private limit seam and actual
full Arena construction. A successful limited drain with zero actual leaf calls
has debit581 and Unavailable/EnvelopeUnavailable with zero extent; a bad footer
overrides it and suppresses extent. They are not public API limit controls.
Three scripted output refusals return outer errors with no aggregate. A private
allocator helper refusal returns ALLOCATION/ARENA; an outer zero-limit call
returns BUDGET/ARENA without a report. Whole-core allocator-fault injection and
every inherited I/O/alias variant are not claimed.

The overlay replaces one production dispatch callsite with a test-only counting
function that delegates to the unchanged selected leaf body, then appends that
wrapper and its private tests. `instrumentation-binding.json` records the exact
single replacement and suffix. Normal actual public File construction counts
five dispatches and debit2706. Separate private compositions first obtain a real
short-arena poison or underfunded/refused reply, install it at the private
progress seam, and execute the actual walk on five framed records: no later leaf
dispatch occurs while five main B payments remain. The R1 status1/reason15/
stale-state999 seam similarly prevents later dispatch. These composed private
tests do **not** claim the public safe-File path naturally produces absent state,
nor an end-to-end fault or a repeated private-call funding entitlement.

The inherited validator boundary remains explicit. Coherent paid debit alone
does not validate shape or authority. Fabricated paid status1/reason1 is
debit-valid and can schedule before finalization; if directly finalized while
still installed, the existing enumerated shape checks suppress it. Actual leaf
helpers produce canonical forms; no general arbitrary-private-corruption latch
is claimed. Status3/reason15 priority and R1 are binding and pass. The public
positive signature probe and eight negative probes preserve private record/leaf/
fields, no Copy/Clone, no word/trust constructor, no serializer and no descriptor
authority entry. Compiler errors are checked for their intended code and symbol.

## Preserved reviewer failures and evidence boundary

The original preaccess freeze and its correction supplement remain unchanged.
Their four review-model errors remain recorded: funded426 was incorrectly treated
as a positive caller case; two before/after assertions were misplaced into a
poststate-only helper; and paid malformed shape was read as a broader terminal
latch promise. The supplement was frozen from old source before new candidate
access and remains the effective clarification.

Three later reviewer execution errors are retained with original source/test/
runner snapshots and raw output: run1 lowercased `u64::MAX` and did not compile;
run2 passed11 methods and failed an incorrect Result240 layout assertion (actual
232, matching the existing accounting contract); run3's two counter methods
failed before walk dispatch because the fixture root collided with its binary path;
one initial private absent-state call had already returned in the composition.
The selected source stayed unchanged. Run3's exact-source12 methods and API
controls passed; run4 fixed the counter path and passed. A cleanup hash-manifest
retention gap in run4 is disclosed; run6 repeats only the unchanged two counter
methods and retains per-run cleanup. No candidate mismatch was found within the
executed scope. Failures are not removed or counted as passes.

Every runtime child has a dedicated process group, deadline at most120seconds,
file-backed partial output, direct-child reaping and an owned-group disappearance
receipt. Three deliberately timed-out short Python runner controls retain their
partial marker and cleanup; no candidate or compiler command timed out. Cleanup
hashes owned binaries and fixture bytes before deletion, retains actual reports,
and leaves no owned scratch run directory. Only targeted owned-group liveness is
checked; no unrelated process discovery occurs. Final admission rechecks the
original ten frozen members and selected proposal/accountant packet identities.

`coverage.json`, `final-receipt.json` and `seal.json` bind exact sources, tests,
tools, commands, reports, outputs, failures and cleanup. Unchanged prior facts are
named references, not fresh replay results. This does not qualify old44,
producer70, the full finite model, all hit/build/CAP states, arbitrary partial
memory failure, a compiler/native target, physical phones, CLI/engine, full target,
OTA/release/signing/store, customer operations, published FieldLog or GA. Computer
use, capture, UI and native simulator/emulator tests remain paused; phones remain
disconnected. Implementation/product/GA acceptance is not promoted here.
