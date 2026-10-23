# Independent Android transport review

The bounded C transport has no reproduced lifetime, concurrency, owner reuse or
callback-return defect under its stated serialized platform-callback contract.
This supports continuing adapter design. It does not qualify Android Looper
execution or freeze the eventual public contract. The adapter obligations below
remain required integration work, not verified outcomes.

Only `verification/android-transport-review/**` was written by this review lane.
No production file, implementation test, original receipt, status, gate or graph
was changed; root owns the wider evidence update. No commit or push was made.

## Reproduction and source identity

Run `python3 verification/android-transport-review/verify.py` from the repository
root. `receipt.json` contains exact commands, actual tool versions, environment,
source revision before/after, source manifests/digest and command output paths.
`source-before.sha256` and `source-after.sha256` are identical selected-input
manifests. The original implementation receipt's ten selected inputs also match
its published manifest; `original-source-match.json` records that check.

The independently authored probes link the unchanged `transport.c` and the
unchanged **actual `platform_android.c`** with original test-only implementations
of `ALooper_forThread/acquire/release/addFd`. The installed official NDK r27d
`android/looper.h` supplies the declarations and event constants. The test Looper
records one fixed callback/data registration and explicitly drives it on the host.
It does not implement or claim Android's event loop semantics.

All nine cases pass independently in fresh processes in Debug, Release,
ASan+UBSan and TSan: **36 case executions**. Strict compiler warnings are errors;
each case has a fifteen-second timeout and explicit result marker. No test-only
transport controls or alternate production implementations are compiled into
these probes. Build artifacts are ignored under this lane's `build/`.

| Original probe | Observed result |
| --- | --- |
| `completing_baton` | A second thread installs the next waiter and closes the owner while the old completion hook is held. The successor survives, no second drain occurs in the same scan, its next claim is RETIRE, and wrong-thread/nested wrapper calls cannot fence. |
| `slot_reuse_during_scan` | A prior retired owner becomes reclaimable at the next callback entry. A preceding slot's hook reclaims it, allocates a new increasing ID in that slot and requests work; the scan drains the new owner exactly once. Every operation on the retired ID remains stale. |
| `many_rounds` | Sixteen owners chain sixty-four PRESENT operations and one RETIRE each: 1,040 drains/completions over sixty-five work callbacks. At most sixteen waiters and one helper exist. A final callback fences all retirements without invoking completion or perpetuating the pipe latch. |
| `join_before_completion_returns` | A synthetic joined assertion latches while a RETIRE completion hook is still held. Fifteen other slots fill the table. Reclamation and owner seventeen remain blocked until hook return and the later callback fence. |
| `registration_guards` | The actual wrapper uses its static data identity, rejects wrong data without owner work, and routes error events to sticky failure/removal. Fixed baseline resources remain accounted and the owner stays pinned. |
| `register_absent` | Missing thread Looper admits no owner and retains no FDs or acquired reference. Repeated installation remains unavailable. |
| `register_rejected` | Failed `ALooper_addFd` releases its temporary acquired reference, closes both FDs, and admits no owner. Repeated installation remains failed. |
| `stale_generation_storm` | Two hundred fifty-six complete retirement/reuse cycles issue distinct increasing owners. Retired owner IDs cannot request, hint, close, join or reclaim a new slot, including with `UINT64_MAX` waiter values. Fixed two-FD/one-registration baseline remains. |
| `waiter_is_immediate_demand` | Three requests produce three PRESENT operations with **zero** external `mxuit_hint` calls. One last fence callback reaches idle. This is an adapter scheduling constraint. |

## Lifecycle, locks and boundedness assessment

`mxuit_install` publishes readiness only after the pipe is configured and the
one fixed registration succeeds. Every production owner lookup and mutation is
under the single mutex. Owner IDs are globally increasing and never wrap; waiter
IDs increase within an owner, so the adapter must key results by the **pair**
`(owner, waiter)`. A bare waiter is not globally unique.

Claiming a slot retains its active lease and hook epoch before unlocking. Both
fixed linker hooks execute outside the mutex. After drain, the old waiter is
consumed and replaced by a completing lease before invoking completion. This
allows a real resumed consumer to register its successor without replacing the
old waiter or permitting another helper. The single forward scan gives one
claim per slot per callback, including when hooks create successors.

The stable slot address is safe while drain/complete execute because active or
completing blocks reclamation. An independent owner in a later slot may be reused
mid-scan only after its **previous** callback epoch has been fenced. The
`slot_reuse_during_scan` probe exercises that boundary directly.

Close is sticky. Close before claim selects RETIRE; close during PRESENT cannot
convert that already running helper into retirement. RETIRE must be requested by
the counted consumer, succeed, finish its completion, and be followed by actual
consumer join and a later callback fence. A failed RETIRE cannot be retried under
the same owner and cannot release capacity. A vanished/stalled consumer or a
global I/O/counter fault may permanently occupy capacity; the design explicitly
chooses that safe failure state.

`in_callback` blocks nested core dispatch before pipe read or epoch change, while
the saved installing thread check blocks concurrent dispatch from another thread.
Clearing `in_callback` after the hooks does **not** publish a callback-return fence.
Only a subsequent accepted same-thread callback entry advances `fenced` to the
previous epoch. The production wrapper has no user-controlled call between core
return and its own return. Together with fixed userdata and no per-owner OS
registration, that makes the stated later-entry proof coherent. The existing
implementation's held platform-tail probe additionally exercises a simulated
tail after core return; this review inspected that source and its receipt rather
than relabeling it native execution.

The core has sixteen scalar owner slots, one waiter/hint per slot, one pipe byte
latch, two process FDs, one registration and one retained Looper reference. It
creates no worker thread, dynamic owner allocation or object/callback registry.
The two fixed hooks carry only numeric identities and enum results. Pipe syscalls
are nonblocking; EINTR retry counts and owner/waiter/epoch/diagnostic increments
are bounded or checked. Fatal errors preserve occupied slots. Diagnostic
`registration=1` denotes the retained registration lease/baseline, even after
the wrapper requests OS callback removal; it is not live delivery authority.

## Required adapter contracts before public freeze

1. **Actual main Looper and Task proof.** Call install only after Java verifies
   `Looper.myLooper() == Looper.getMainLooper()`. Calling from a thread with any
   Looper is insufficient. Call `consumer_joined` only after the counted
   presentation Task's real `value` returns. Host thread IDs and synthetic join
   assertions cannot establish either fact.
2. **Publication before request.** Store the numeric `(owner, waiter)` to
   continuation rendezvous and weak-model association before calling request.
   Another thread can invoke the fixed completion immediately after request
   drops the transport mutex, even before the requesting call returns. Complete
   must atomically consume the matching rendezvous exactly once. Failure rollback
   must compare that exact identity and must never resume an already consumed
   continuation. The registry must remain bounded with the same sixteen slots.
3. **Locks outside fixed hooks.** Preserve the current rule that no transport
   lock spans drain or complete. The binding must copy/consume a registry entry
   under its own short lock and release that lock before native UI work or
   continuation resume. The endpoint stores no strong model, frame or Task.
4. **Demand and stop ordering.** Request is immediate work demand, not passive
   subscription. An unconditional `await request` loop will keep scheduling
   PRESENT operations without new exchange data. The sole counted Task must
   await existing exchange delivery/stop before requesting the corresponding
   helper. Re-check sticky stop around completion: PRESENT result normalization
   precedes the completion hook, so close racing after normalization may coexist
   with an already computed OK result. `completing_baton` exercises that valid
   ordering; the latched stop still causes the queued next request to be RETIRE.
5. **Reclaim wake/retry remains unresolved here.** A fence-only callback invokes
   no completion hook or other adapter notification. A close coordinator that
   joins, tries reclaim once and receives BUSY cannot assume it will be called
   again. The adapter needs a bounded eventual retry/wake path that preserves its
   single counted consumer/coordinator lifetime and avoids an uncounted Task,
   timer or busy loop. The new probes explicitly assert that the later fence
   advances with no extra completion. This is a deferred integration requirement
   already identified by the design, not a claim that the C slice supplies it.
6. **Failure authority.** Unknown helper outcomes, global I/O/counter failure,
   unsuccessful RETIRE or missing join/fence must retain native accounting and
   fail closed. An inspect snapshot, a completed PRESENT or an unregistered OS
   callback cannot independently authorize release or health.

## Evidence limits and normative source

No actual Android Looper, JNI/Java code, Swift continuation, `Task.value`, native
widget, signed runtime or release gate executes in these probes. No emulator or
physical device was queried or run, and no reconnection was requested. ASan leak
detection is disabled; this review makes no memory-footprint, energy or leak
claim. These are additional POSIX state-machine and wrapper-call checks.

The official [NDK Looper documentation](https://developer.android.com/ndk/reference/group/looper)
was read on 2026-10-23. It describes thread-associated Loopers, callback execution
within poll, callback return-based removal, and the possible final callback after
external removal. The retained static registration avoids per-owner userdata
retirement dependence on removal. The installed official header hash is included
in this lane's receipt. The same-thread later-entry fence remains implementation
reasoning whose actual main-Looper integration must receive separate execution
evidence.
