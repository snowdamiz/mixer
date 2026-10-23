Independent review found no actionable issue in the bounded test-only repair to
`verification/android-binding-stage4/HostTests.swift`. The added idle predicate is
causally sufficient for this fixture's initial single-frame delivery. The new
held-c assertion checks the required fresh-write precondition immediately before
injection. Original fault fanout, reservation pinning and exchange-stop assertions
remain unchanged. Root retains integration and gate acceptance responsibility.

The failed hosted TSan receipt at c687e69 binds the original fixture and reports
only `HOST_FAIL line=109 test observation deadline`. This is the old wait helper's
line, so the retained log cannot identify which invocation timed out. A controlled
valid schedule demonstrates a mechanism that the repair prevents; it does not
establish the exact scheduling cause of that hosted failure.

The C transport increments `completions` before invoking the Swift completion,
while `in_callback` remains set. b's actual UI leave has already set the one-byte
pipe latch. A c request admitted at that point can run in the same callback; its
leave sees that pending byte and skips the write syscall, leaving a one-shot
write-fault injection unconsumed. `mxuit_inspect` takes all three predicate values
under one transport lock. After the last hook, the callback clears its active bit
and establishes any return-fence demand under that same lock. Waiting for both
inactive and no pending byte excludes the overlap.

There is no latent b delivery demand for this fixture. `frameExchange` finishes
its startup frame and confirms effects before binding the reader. Those signals
coalesce into one pending wake. b consumes it before its only PRESENT request;
completing the initial presentation has no event-result branch and emits no new
delivery signal. The lifetime task's next operation is another reader wait.

The independent probe builds private copied actual Swift/C/SDK sources. Its only
binding changes are observation barriers immediately before real Swift completion
delivery and after b's real resumed request clears its rendezvous. The unchanged
transport, fixed native bridge and real lifetime tasks provide every result and
fence. SDK's existing read-only `hasWaitingConsumer` observation confirms b parks
after the delayed continuation resumes, without another C request. All six
Debug/Release/TSan schedules passed:

| Schedule | c callback | Pending byte at held c apply | Observation |
| --- | --- | --- | --- |
| Old predicate | Same epoch 1 as b | 1 | c leaves without fault; a later real Swift/C request consumes the retained injection and reports IO 8. |
| Fixed predicate | Epoch 3, after actual idle epoch 2 | 0 | Delayed b task resumes and parks with requests still 2; c's leave consumes the injection and reports IO 8. |

Both schedules preserve the original final fault-fanout assertions. The fixed
probe observes actual idle while b's resumed task is still held, so it also
exercises the delayed-task boundary rather than assuming the task ran promptly.

`audit-receipt.json` records 993 checked file bindings. All 151 original runner
inputs remain present; only HostTests.swift differs from the failed hosted input
map. The audit checks all 117 retained ordinary pass markers, source snapshots,
logs, executables and native inputs, then independently replays the unmodified
candidate fault-leave executable once per Debug/Release/TSan mode. All three
replays pass. New unrelated untracked SDK files are outside the explicit frozen
input set.

Run from the repository root:

```sh
python3 verification/android-fault-leave-ci-independent-review/run.py
python3 verification/android-fault-leave-ci-independent-review/audit.py
```

The probe deliberately requires a fresh `build/task-barrier` directory. Build
directories are ignored; checked-in scripts, overlays, exact source manifests,
commands, compiler versions and output hashes retain reproducibility. Local
compiler is Apple Swift 6.4 (`swiftlang-6.4.0.34.1`) and Apple Clang 21.0.0
(`clang-2100.3.34.2`), arm64 macOS 27.0. The reused real Rust archive is bound to
d814055 and is not rebuilt or TSan instrumented. This is host fixture ordering
evidence; pinned hosted Swift 6.2.4, JNI/Looper, physical devices, signed UI,
release and GA qualification remain outside it.

Two earlier review-probe attempts are retained with their source and logs. The
first did not compile because it used private C implementation field names
instead of public snapshot names. The second compiled but timed out because the
existing inherited HoldingExecutor did not hold the targeted task job on this
compiler. Neither is a candidate-source failure or a claimed pass. The final
probe replaces that scheduling assumption with the explicit observation barrier.
