# Android guest UI transport: bounded executable slice

This is an experimental internal C boundary for root review. It freezes no public
Android UI profile/header, changes no signed selection, and supplies no Swift,
Java, activation, generator, widget or health integration. Root approved this
transport direction before implementation; public profile work waits for review of
its retirement proof. Exact commands, selected source digest, tools and observed
results are in `verification/android-guest-ui-transport/receipt.json`.

This document supersedes two details of `android-signed-guest-ui-design.md`:

- Replace per-presentation pipe/Looper registration with **one process-lifetime
  registration, static userdata and one pipe: two fixed FDs**, plus one acquired
  Looper reference. Sixteen bounded owner slots match the outer runtime reservation
  ceiling. This avoids per-owner userdata removal/free and late-callback hazards.
- The phone restriction concerns physical phones. **Emulator execution is
  permitted**, though this bounded C slice executes neither an emulator nor a
  physical target. The earlier design's combined emulator/device prohibition was
  overbroad. Host tests and Android object/link checks remain separate evidence.

## Internal API and resources

Implementation lives only in `native/android/signed-guest-ui/transport/`:
`transport.c`, `platform_android.c`, `include/mixer_ui_transport.h`, `internal.h`,
independently authored host tests and the reproduction driver `verify.py`.
The header explicitly says experimental/internal; it is not a release contract.

| Operation | Exact meaning |
| --- | --- |
| `mxuit_install()` | Once per process, from the future Java-verified main Looper thread. Capture that thread, create/configure two nonblocking CLOEXEC pipe FDs and register one fixed fd callback using `ALooper_forThread/acquire/addFd`. No owner is admitted before success. Repeated same-thread install is observational; other-thread install rejects. |
| `mxuit_acquire(out owner)` | Reserve one of 16 static slots and issue a positive never-reused UInt64 ID. Zero is invalid; checked exhaustion never wraps. No pointers are handles. |
| `mxuit_request(owner, waiter)` | Accept one positive increasing numeric waiter and set one hint. Busy rejects without replacing the waiter. No document, Task, continuation, object or caller callback is captured by C. |
| `mxuit_hint(owner)` | Coalesce a data-only hint. Without a waiter it sets the slot bit and does not wake/spin the Looper. Closing owners reject. |
| `mxuit_begin_close(owner)` | Sticky close latch. A queued request not yet claimed becomes RETIRE; close during PRESENT requires a subsequent RETIRE request from the same counted consumer. C never invents a terminal native helper when no consumer runs. |
| `mxuit_consumer_joined(owner)` | Internal trusted assertion, admissible once RETIRE has started. Future root glue must call it only after actual `await task.value` returned. It may latch while the native completion hook is still returning; reclaim separately waits for all native leases/fences. C cannot establish a Swift Task's lifetime. |
| `mxuit_try_reclaim(owner)` | Release the slot only after successful RETIRE, no helper/completion/waiter, explicit consumer join and callback-return fence. Sticky I/O/counter failure keeps it counted. Old IDs remain stale after reuse. |
| `mxuit_inspect*` | Data-only bounded diagnostics. A snapshot grants no execution, presentation, health or release authority. |

`mxuit_drain(owner, waiter, PRESENT|RETIRE)` and
`mxuit_complete(owner, waiter, kind, result)` are **required fixed linker symbols**.
There are no setters, function-pointer registries, arbitrary names or callback
contexts. Final root integration will provide weak-model lookup and the synchronous
native helper through these exact symbols. Both hooks execute outside all transport
locks. The product objects intentionally fail to link without those implementations.
The cross-link probe provides clearly test-only hooks that reject drain; it is not
an Android application implementation.

The process retains fixed storage, two FDs and the acquired Looper reference until
exit, including when all owner slots have retired. No per-owner FD, thread, dynamic
allocation, native source, JNI reference or object graph exists in this endpoint.
`registration=1` in diagnostics records its installed process registration lease;
on fatal transport failure the platform callback requests removal by returning 0,
but its static userdata/acquired reference/FD baseline remains retained. It does
not report a successful owner retirement or pretend removal joined a callback.

## Return fence and actual consumer lifetime

The OS callback receives only a static registration tag. At entry, the core checks
the exact private fd, ready state, installing thread and non-reentrancy **before**
reading a hint or advancing any epoch. Only that one serialized Looper thread may
dispatch. The callback reads the one-byte process latch, fences the previous
callback epoch and advances to a checked new epoch. It scans at most 16 slots,
claims at most one request per slot and invokes one synchronous helper at a time.
The scan does not revisit a slot when a completion registers its successor.

While PRESENT/RETIRE runs, that owner has one active helper and its current epoch
is retained. After drain returns, C consumes the old numeric waiter before the
fixed completion hook; this permits the resumed **same** Task to register its next
waiter concurrently. A separate bounded completing lease prevents another drain or
reclamation until the completion hook returns. No lock is held across either hook.
If the resumed consumer actually finishes before that hook's C tail returns, its
join assertion latches without releasing the native completing lease or slot.
Results are at most once. Unknown drain results close the owner as failure.
PRESENT completed after close reports `DRAIN_CLOSE_PENDING`; it is not retirement.
RETIRE failure pins the slot rather than retrying an uncertain teardown.

After all hooks, the callback core clears active state and writes one coalesced
fence byte. **That last C owner access is not treated as callback return.** Its
epoch remains unfenced while the platform wrapper's C tail is still executing.
A subsequent callback entry on the same non-reentrant thread proves the prior
platform callback returned, and only then advances the return fence. It requires
no owner pointer or per-owner userdata to survive in the platform queue.

A no-hook fence callback emits no new fence byte, so idle owners do not create a
perpetual callback loop. New requests coalesce with the fence byte. A stalled
Looper, held helper, held completion, held platform callback tail, absent terminal
consumer request or absent actual Task join keeps the corresponding slot occupied.
If the Looper never returns, close remains pending. The process baseline is not
disguised as an owner leak that can be reclaimed unsafely.

The host `callback_tail` case deliberately holds the platform wrapper **after**
drain, completion and the core's last owner access all returned, but before that
wrapper returns to its event loop. It supplies the Task-join assertion, fills the
other 15 slots, and verifies that reclaim and new-owner capacity remain blocked.
A different thread cannot advance the epoch; nested invocation from the drain hook
also cannot. Releasing the held tail permits a later callback to fence the old
epoch, after which the exact old slot may be reclaimed with a fresh monotonic ID.

This proves the POSIX state-machine safety condition under a serialized platform
driver. It does not claim the host driver is Android's Looper, nor that a C flag can
prove Swift's `Task.value`. The future adapter still needs actual main-Looper/JNI
and counted Task integration tests before public contract freeze.

## Failure and boundedness rules

There is one global pending-byte latch under a short mutex. Each owner has one
hint, one numeric waiter, one helper/completion lease and fixed scalar state.
All owner/waiter/epoch counters reject exhaustion. Cumulative diagnostic counters
also check increments; failure closes admission and pins owners. No sequence wraps.

Pipe write/read failure, unexpected EOF/byte, exhausted bounded EINTR retries or
platform error events fail closed. EAGAIN without the transport's own pending bit
is conservatively treated as failure, not assumed delivery. Failed fence writes
never advance the return fence. No owner is released on guessed callback progress.
The private process-lifetime pipe ends must never be closed by outside code; the
transport does not change the application's process-wide signal dispositions.
Before registration succeeds, pipe/fcntl/register failures close unregistered FDs
and admit no owner. Once registered, fixed baseline resources remain accounted.

Close does not itself create a C worker or synthetic callback. The future single
presentation Task receives the existing exchange stop hint and requests RETIRE,
then really returns; root's existing close coordinator awaits it, asserts consumer
join here and waits for `try_reclaim` to pass the later callback fence. This slice
does not add a second Swift Task or timer to implement that later wait. Root must
review its wake/retry wiring, weak-model ownership and final native-exit accounting
when the adapter is added. Presentation retirement remains distinct from native
capability exit and durable uncertainty.

## Reproduce and assess evidence

Run `python3 native/android/signed-guest-ui/transport/verify.py`. It uses only
installed official tools; no package resolution, downloads, device queries or app
publication. Host tests run independently in fresh processes in Debug, Release,
ASan+UBSan and TSan. Strict warnings are errors. Each test has a bounded timeout and
explicit pass marker; logs record actual commands and versions. Leak detection is
disabled in ASan, so the receipt makes no leak/RSS/energy claim.

The original executable cases cover 16-slot capacity/fair scans, 80,000 concurrent
coalesced hints, successors registered during completion, close before/during a
helper, held callback tail, nested/wrong-thread/fd entry, stalled consumer, missing
join, failed/unknown hooks, failed reads/writes/fence/initialization, bounded EINTR,
EAGAIN rejection, owner/waiter/epoch exhaustion, stale IDs and repeated reclamation
with the same two process FDs. Test-only typed failure/counter controls are absent
from the Android product objects; no test callback setter enters product code.

The Android check compiles the actual C core/platform wrapper against installed
NDK r27d API30 arm64 headers, verifies that missing fixed hooks fail a
`--no-undefined` shared link, links a test-only probe against `libandroid`, and
records ELF/symbol/dependency/alignment output. This is object/link evidence only:
no Android Looper has executed, no JNI/Java/widget code is supplied, and no
signed-runtime/native-screen/health milestone is passed.

Normative reference: [official NDK Looper documentation](https://developer.android.com/ndk/reference/group/looper)
and the exact installed `android/looper.h` hash recorded by the verifier. The
documented possible final callback after removal is why this design never frees
per-owner callback userdata or treats `ALooper_removeFd` as a join. Main-thread
serialization and the later-entry epoch fence are the implementation's explicitly
stated reasoning, to be independently reviewed rather than accepted as platform
qualification.
