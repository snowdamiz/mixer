# Independent review of the private Swift active-frame implementation

Independent review is complete for the frozen private host slice. No unresolved
blocking source, ownership or accounting finding remains in the reviewed closure.
The user requested a pause before root acceptance; root admission, delivery and
tracker updates remain pending for resume. This document does not authorize public
Swift invocation, native execution, publication or a GA gate.

The reviewed source is the 119-file manifest
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`, archived at
`verification/swift-active-frames-implementation/source-freeze/20261024T045840237261Z/`.
Its source archive SHA256 is
`0ffda402ae4a8814d0c82be3492713646c261215efe83f4c762cc7f578588899`.
Qualification uses these archived bytes, independently of later shared-checkout
changes or disposable Cargo targets. The reviewer owns this document and
`verification/swift-active-frames-implementation-review/` only, and made no product
edits, commits or pushes.

## Source and authority review

The review followed original construction, State buffers/header, common Controls,
runtime control, WASI, value primitives and borrowed-cache pin release into the
actual new methods. The original release rejects before mutating pin records,
slots or usage and returns the same actual pin. The final frame code preserves
that authority: failed frames return at the same indexed position, retained frames
form the processed suffix of a bounded pass, and the State entry guard remains
separate from all retained frames. Repeated drain does not retry a completed pass;
explicit cleanup-only reacquisition starts the next pass.

Entry captures actual value/control lengths as synchronous locals after its
active preflight, passes them directly to rollback and returns only after the
attempt's appended effects have been handled. Retained/inactive entry rejection
does not apply fresh snapshots to an old guard. Guard counters record acquired
debits. Rollback removes at most the acquired debit and latches disagreement;
later zero ledger readings cannot clear the latch. Both the value-preparation and
consuming-cleanup barriers reject retained frame state, including zero-frame
states with a guard, nested/outer restore obligation or sticky mismatch.

The new cleanup-independent preflight validates actual original WASI/cache owners,
the actual construction ticket, header and each original State buffer before
State transitions. Original owner checks precede the separate read-only
category/byte layout comparison. The approved construction leaf borrows the real
ticket, checks nonzero owner, live/category/combined sufficiency and exact current
construction layout, then records diagnostics after the borrow. It neither takes
nor substitutes ticket authority. Fresh missing, foreign and wrong-layout cases
were exercised separately for prepare, value, cleanup and resume; each asserts the
intended diagnostic and unchanged pointers, bounds and retained State.

Cleanup-only resume terminalizes the lifecycle and uses retained frames only as
indexed pin storage. It never reinterprets stale frame offsets and does not check
execution work, fuel or cancellation. A pin acquired together with failed cache
completion remains in the guard alongside the exact larger nested reservation;
that nested bound is restored before outer completion. Completion ends the fixed
caller storage and execution parts before restoring the outer reservation, and
clears the cleanup state only after no authority or obligation remains.

Entry retains original first-failure/work ordering: depth before work; one entry
unit before signature and cache lookup; parameters remain owned by the caller on
failure; `locals + 1` work before publication; cancellation before each appended
local; and live debit before each append. Return pops its optional result before
truncation work, callee retirement and caller push. Tests observe these actual
effects and actual WASI usage at failure and after cleanup. No Ready lifecycle,
dispatcher, public invocation route or Frozen interpreter body was added or
changed. Parent access to inherited phase methods independently fails with E0616.

## Positive accounting review

The accepted 1,061 declaration fields remain fully occupied. The implementation
adds 16,804 distinct supplemental fields rather than spending equal-sized aliases,
padding, old scratch or the original value budget. The review checked authored
source aliases and helper/caller edges against exact compiler-typed MIR argument,
local, return, Try/ControlFlow/residual and closure-capture shapes. Four distinct
source/argument/returned/caller positions are retained for every selected MIR
binding. The fresh final-source MIR has 7,220 production and 8,228 unit positions;
types, source names, function identities and capture tuples match the saved
inventory exactly. Only global MIR stream line offsets are excluded from that
equality, because preceding CTFE blocks move them; both complete dumps are saved.

The reviewed call closure includes original-owner preflight and its four callers,
all new entry/return/rollback/drain/complete helpers and closures, value preparation,
consuming cleanup, ticket layout/construction checks and the common function
Control constructor's authored arguments and whole-Control transfers. Shared
primitive-push supplemental rows, construction provenance and all selected unit
fault-hook receiver/capture/wrapper positions are permanent so they also cover
zero-frame callers. Unit hook leaf additions include 924 separately positive MIR
fields. The State cleanup initializer is const-evaluated before header admission;
its source/MIR and the separately propagated State payload growth were checked.

The logical budget excludes compiler-created opaque spills such as the private
Kind literal in the approved constructor, standard-library TLS machinery, and
general test-fixture/independent-probe staging. These exclusions do not stand in
for authored product bindings or injected in-operation fault hooks. The latter
are explicitly accounted. This is a bounded logical ownership review, not a claim
about arbitrary optimizer machine-stack usage.

Two fresh independent exact-field compiler probes and eight portable producer
metadata replays agree for every field's offset, size and alignment. All fields
fit their class, aligned nonzero fields do not overlap, and each source role keeps
its own field. Production has 9,345 total fields; unit builds have 17,865.

| Bound, bytes | Production | Unit |
| --- | ---: | ---: |
| Permanent positions | 1,086,648 | 1,945,656 |
| Execution header | 1,378,536 | 2,238,504 |
| Active frame positions | 929,872 | 1,505,296 |
| Fresh full value component | 119,576 | 119,576 |
| Full frame operation | 1,049,448 | 1,624,872 |
| State inline payload | 424 | 424 |

The original Frozen value component remains 2,912 bytes and the existing Swift
value operation remains 119,576 bytes. State grew by 112 bytes. The revised bounds
are intentionally larger than the proposal: actual implementation positions are
positive additions, and total size alone was never used to establish completeness.

## Executed evidence

The final independent runtime receipt is
`verification/swift-active-frames-implementation-review/results/20261024T050023355218Z/receipt.json`.
It records 57 commands, 682 unmodified candidate unit-test executions and 40
independently authored adversarial probe executions across Swift/all features and
Debug/Release, four baseline/candidate C-export comparisons, and the expected
privacy compile rejection. Twelve unit executables and eight ABI libraries are
preserved in its compact qualifying archive. The independent harness changes no
product body; its exact derived source and helper tests are archived and verified.

The independent probes use actual constructed owners, caches, frames, Controls and
pins. They cover scalar parameter suffix/zero bits, every result-return work
prefix, zero-ledger sticky undercounts, dropped-active cleanup with real WASI
observation, fresh otherwise-valid owner/layout faults, all sixteen four-frame
release masks, retained guard plus multiple failed pins, inactive re-entry
preservation, fixed arena pointers, reservation retention and warm first-allocation
refusal. The producer's AF01–AF22 tests exercise the remaining entry/predebit,
cancellation, decode-policy, nested completion and restore boundaries in all four
configurations. AF04's 257-local case is a real validator rejection before owner
construction, separate from valid 255/256 entry. AF05 uses distinct actual decoded
blocks with function-inclusive Controls; it does not exercise a dispatcher.

AF15's caller result-capacity rejection is explicitly a derived defensive-boundary
injection: in valid operation the preceding pop/retirement naturally frees a slot.
The approved cfg(test) one-shot observation affects the existing primitive capacity
comparison while preserving actual Vec capacity and production semantics. It is
not presented as a naturally reachable failure.

Fresh independent metadata compiles are in
`layout-results/20261024T050837492680Z/` under the review directory. The retained
producer audit and eight exact metadata replays are in
`producer-audit/20261024T051419353958Z/`. That audit checks all 229 producer command
logs, 100 main portable artifacts and the exact frozen source/MIR, then compares
all eight compiler configurations against both fresh independent layouts. The
producer's main receipt is
`verification/swift-active-frames-implementation/results/20261024T050444826239Z/receipt.json`;
its metadata receipt is
`verification/swift-active-frames-implementation/metadata/20261024T050606606361Z/receipt.json`.
All-feature Frozen parity retains 1,232 trace records per profile; Swift-only
configurations have no such trace records. Whole original Frozen source bytes,
shared arithmetic source, public headers and ABI exports were checked separately.

Host tools were rustc 1.99.0 (`b940084d7`, LLVM 23.1.1), Cargo 1.99.0 on
`aarch64-apple-darwin`; exact versions, commands, source digests and raw outputs are
saved. Candidate formatting and library Clippy pass. Broad keep-going Clippy still
fails with the same 26 baseline source-associated diagnostics; this is an accurate
baseline comparison, not a clean broad lint claim. Earlier reviewer harness
compile/tooling failures and the interrupted overlarge metadata code generator are
preserved with explanations; none supplies final qualifying evidence.

`verify_review.py` verifies the saved final packet without any build tree or test
execution. Qualifying executables, sources and logs remain in compact archives.
Every reviewer-owned disposable target/source scratch directory was removed only
after portable evidence verification and a fresh empty `lsof` check; cleanup
sidecars preserve those checks. No reviewer-owned test process remains. No native
runtime, UI automation, capture, simulator, emulator or physical-device activity
was started by this lane.

Root acceptance and any delivery remain pending at the user's pause. Public
invocation/instruction dispatch, native/device matrices, signed/published FieldLog
packages, store/customer operation and all applicable GA gates remain outside this
review. Resume from the exact archive and receipts rather than mutable source or
agent claims.
