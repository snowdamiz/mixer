# Cold-start cleanup CI assertion repair

This lane changes only `verification/cold-start-cleanup-ci-repair/**`. The test
repair belongs to root. No live activation, bridge, VM, fixture or test source
was edited here. No device operation, commit or push was performed.

The repaired test examined here has SHA-256
`292448a10a86299a55f600ce73b2442b3c84a92543adca4fe8aa7b9b68e4a720`.
The original test is read from `22d048c`; product activation source is frozen
from committed `d6505ac`. This deliberately avoids the concurrent presentation
lane's changing files. That lane's full final module matrix remains separate.
The 29 frozen activation/runtime production Swift files also match hosted
revision `22d048c` byte for byte; the exact comparison is retained in
`final-1/product-revision-equivalence.json`.

The hosted failure reports two observations at the original source lines 216 and
217: occupied slots were 2 against expected 3, and `cleanupPending` was false.
The log is retained at `verification/github-ci-22d048c/swift.log` (log lines
3586–3587). It does not record native submission or actual async return order.
Therefore the exact hosted interleaving remains unproven.

The original synchronization is insufficient for its unconditional assertions.
`CapabilityConcreteSetup.constructOwned` creates the real private KV store before
its next `control.requireOpen` check, adapter group creation, construction owner
preparation and `ExperimentalCapabilityConstruction.create` call. File existence
can therefore be observed while no native construction job has been submitted.
Close may stop the actual signals at that point; the unchanged `requireOpen`
then rejects setup, its actual ordinary/adapter tails return, and capacity can
legally return while the native queue remains held.

Root's repair observes actual `startup` and `close` returns with lock-protected
flags. If it observes anything other than the counted/pending state, it requires
both real async calls to return before releasing the blocked queue, then requires
baseline capacity and no pending cleanup. It retains the ordinary queued path
and final startup rejection/capacity checks. This accepts a completed legal
pre-admission close without treating a filesystem marker as native admission.
It does not force the genuinely queued path on every unmodified fixture run.

The retained derived probes make both schedules explicit:

1. An async gate pauses immediately after actual KV construction and before the
   unchanged stopped/deadline predicate. The test starts real close, observes its
   actual stop signal, releases that setup gate, and awaits the actual startup
   and close tasks while the existing native queue blocker is still held. The
   native submission observation must remain zero. The original assertions fail
   exactly twice; the repaired predicates pass. Neither a cleanup value nor a
   successful return is injected.
2. A bridge observation runs immediately after the real
   `ExperimentalQueues.construction.async` call returns. The native queue is
   already held, so observing one submission proves a real queued create job.
   Before releasing that queue, both original and repaired probes require
   pending cleanup, baseline plus one occupied slot, and both actual return
   flags false. Both original and repaired predicates pass this queued schedule.
3. The complete unmodified repaired eight-test fixture runs with the same rebuilt
   modules and unarmed scheduling hook as a scoped regression.

The scheduling gates use actor continuations, condition/lock state and actual
queue-submission observations. Bounded polling observes these predicates; no
elapsed sleep by itself establishes ordering. Exact derived diffs and their
original frozen sources are retained under each run's `.build/.../source`.

`final-1/receipt.json` records the selected Debug, Release and TSan commands,
tool versions/hashes, immutable derived source hashes, exact retained dependency
and native archive hashes, artifacts, logs, expected original failures, and scope.
`candidate-1/receipt.json` preserves the initial Debug evidence. The expected
original assertion failure is evidence of the test assumption, not a product
failure fabricated or suppressed by the repaired test.

All final source and command-output hashes were rechecked. The completed matrix
has the following outcomes in each of Debug, Release and TSan:

| Schedule / fixture | Original | Repaired |
| --- | --- | --- |
| Before native admission, both actual calls returned while queue held | Exactly two expected original assertion failures | Pass |
| One actual native create job queued, both actual calls still blocked | Pass | Pass |
| Complete unmodified repaired fixture | Separate historical source | Eight tests pass |

The pre-admission trace records baseline capacity, `cleanupPending=false`, zero
native submissions, both return flags true, and queue release false. The queued
trace records baseline plus one capacity, `cleanupPending=true`, one actual
submission, both return flags false, and queue release false. Final cleanup in
each passing test still requires startup rejection and return to baseline.
No root test revision is requested for the inspected repair.

TSan instruments the rebuilt activation/runtime/probe Swift files. Retained
SDK/C/native archive dependencies are checked by digest and remain outside that
instrumentation coverage. This is local deterministic test qualification, not
physical iOS/Android, an immutable published consumer, a production release or a
GA receipt.
