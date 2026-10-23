# Review-only internal scheduling and metadata harness

Candidate-5 results are recorded in the parent README and exact receipts. The
public target imports public products and runs against unmodified frozen source.
This separate target requires labelled source copies, retains the concrete store,
and uses existing SDK internal scheduling hooks. No production hooks, adapter
authority, synthetic successful completion or trust change is introduced.

`make-derived-review.py` refuses production checkout inputs and destinations,
checks the pinned manifest before and after copying, requires each hook anchor
exactly once, and records all input/changed source/test/resource hashes in
`derived-review.json`. Controls only delay or reorder real observations. Gate
continuations cap at sixteen; synchronous gates have a bounded hang escape that
fails the test. Such escapes supply no request deadline authority. Performance of
instrumented copies does not characterize production performance.

The 14 main cases run in their own filtered process in debug, release and scoped
Swift/C-shim Thread Sanitizer:

1. Empty native Call payload is strict local rejection with no I/O. Guest imports
   independently reject empty length before token/Call issuance; only this derived
   boundary injects a structurally valid zero-length C Call payload.
2. Both actual policy-denial callbacks occur before acceptance publication; no
   result handling or ack occurs while the submit worker is pending.
3. Multiple signals cannot relaunch one queued admission worker.
4. Actual exit forwarded before a held real result waits for post decision.
5. Forwarded real result while actual exit forwarding is held retains ownership.
6. Absent forwarded result reaches C expiry; late payload cannot refill a tombstone.
7. Eight raw takes and two deliberately exhausted close scans still finish without
   another host callback or close control rescuing cleanup.
8. Real C take paused before Swift registration resumes after close: local no-I/O
   ack, no concrete effect and no spurious status failure.
9. Real wake raced with completed close records no spurious failure.
10. Pre-admission remaining query raced with close records no spurious failure and
    joins an explicit local no-I/O ticket without starting a worker.
11. Accepted-work exit/deadline confirmation raced with close records no spurious
    failure, acknowledges actual exit and never relabels it as local no-I/O.
12. Close after host ID recording, before waiter publication, disposes reservation.
13. Close after encoding, before waiter resumption, suppresses host admission.
14. Real concrete storage held at SDK afterInvocation retains the independent exit
    owner after public close/deinit. Fifteen pending constructions keep the 17th
    out; sixteen real replacement C creations after release detect a lost old ack.
    No retained callback in these review controls props up this ownership test.

`InternalBridgeMetadataFaultReviewTests` runs separately in each mode. It mutates
successful startup report bytes after the real C call: wrong ABI or invalid i32
must close admission and conservatively quarantine the attempt even if cleanup
later succeeds. `InternalBridgeConstructorFaultReviewTests` runs in another
filtered process per mode. Wrong ABI, unexpected published error handle and
success with hidden zero handle retain one capacity permit each, while custom
input buffer deallocation proves no module buffer remains captured. The hidden
no-I/O handle may conservatively remain until the filtered process terminates.
These intentional quarantines must not contaminate process-capacity cases.

The Rust archive is unchanged and uninstrumented by Swift TSan. These cases prove
bounded observed logical ownership transitions; they do not prove no runtime Task
objects, RSS, OS resources, rollback, physical execution, publication or GA.
