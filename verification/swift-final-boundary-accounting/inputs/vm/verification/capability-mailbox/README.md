# Experimental bounded Rust mailbox

This slice is available only with Cargo feature `experimental-capability-mailbox`.
It is an independently authored state machine, not an enabled guest capability
transport. `default=[]` and profiles 1–3, their limits, import validation, existing
session behavior, C symbols/headers, Swift/native routing, and release admission
remain unchanged. Baseline includes numeric repair `16727d2`.

## Rust contract

`Mailbox::new(Limits)` creates disabled inline state. `enable` opens effects once
for its owner; callers must enforce the eventual successful-startup activation
ordering. Previously enqueued disabled calls remain typed `Unavailable` terminal
results and never drain. Operations are the closed enum `HttpRequest/Get/Put/Delete`.

`begin_turn` returns an opaque owner-bound `TurnId`. `enqueue` requires that exact
active turn and snapshots 1...524288 bytes. `finish_turn(Success)` makes its calls
drainable; any active turn blocks call draining. `finish_turn(Trap)` closes the
mailbox, drops queued calls/results, and reports prior running leases for external
cancellation. A stale/foreign finish, including a trap, cannot affect a later turn.
Turn sequence exhaustion rejects further turns without wrapping. Owner IDs use a
checked process atomic identity counter; exhaustion rejects construction, without
wrapping. This counter imposes no process/session quota.

Each request reserves `argument_length + 524288` before the argument snapshot can
allocate. Installed limits may only narrow 8 requests, 8MiB payload reservations,
and a 1...30000ms deadline. Slots include queued, native-running, terminal
unconsumed, and delivery-consumed but still-native-running entries. Requests use
nonzero generation/slot+1 token bits, scoped by a private owner identity. Generation
increments only after full release; `UINT32_MAX` retires the slot permanently.
Rust IDs and leases cannot be forged through this API. This does not qualify
hostile guest raw-token lookup, which still needs an actual import boundary.

`take(output)` first emits one coalesced cancellation control per still-running
cancelled/expired request, ahead of calls and even while a guest turn is active.
Controls have no payload allocation or auxiliary queue. A call take copies the
entire argument snapshot once, returning its opaque `NativeLease`, fixed operation,
and bounded floored remaining milliseconds. Call draining requires no active
turn. Too-small output reports required length without writes or consumption.
Outputs larger than 524288 reject before state/output mutation. All native/guest
payloads are owned copies; no borrowed bytes survive a public call.

`post(&lease, bytes)` copies 1...524288 opaque completion bytes and installs a
terminal result only if no prior terminal/consumption/exit exists. The future
trusted bridge must strictly decode and bind payload schema, operation, grant and
actual adapter identity before posting or I/O. These opaque bytes are deliberately
not called validated JSON here. Built-in `Unavailable/Cancelled/DeadlineExceeded`
are allocation-free typed `Poll::Failure`, not wire payloads or a new capability
failure vocabulary. Wire JSON formatting/validation remains unimplemented.

`poll(id, output)` returns pending without writes, reports exact required bytes
without partial writes, or copies/consumes one complete native payload. A typed
failure consumes delivery without writing bytes. An already-consumed request is
stale even while its native lease remains counted. Full output capacity is checked
even for pending/failure. Rust result discriminants are not frozen C/guest codes.
The eventual guest memory length-word/range/alias contract is a separate gate.

`cancel` installs the first terminal only. Queued cancellation suppresses dispatch;
running cancellation schedules one bounded control. `post` does not acknowledge
adapter exit. `ack_exit(&lease)` borrows its identity so errors remain retryable;
an early actual exit is accepted and prevents subsequent posting, while pending
or terminal-unconsumed delivery retains its slot. Deadline/cancel plus polling
releases an early-exited pending request. Every other release requires both guest
consumption and actual exit (or proof there was no dispatch). Duplicates/replays
reject and dropping a lease never acknowledges exit.

`close` immediately invalidates guest operations and returns a fixed eight-entry
`CloseReport` of outstanding lease identities for cancellation outside the lock.
Undispatched/previously-exited requests are dropped. Running entries retain their
argument storage and full reservation until matching exit acknowledgement. Late
posts cannot revive delivery. Repeated close reports still-running identities
again. Only `ack_exit`, repeat `close`, and read-only `usage` work after close.
The caller must keep this mailbox alive through those acknowledgements: this
standalone value does not enforce the existing counted VM registry/reclamation
lifecycle or prevent its owner from dropping it prematurely.

Every transition uses a short owned mutex; no user callback/native I/O is called
under it. Work consists of scans over eight slots and bounded copies/destruction.
Mutex contention and OS suspension are not hard real-time bounded. Private
`Instant` values, never external/guest time, start at successful enqueue. Take,
post, poll, cancel, finish and explicit expiry check them. `post` rechecks after
fallible allocation/copy, preventing delayed success from winning a deadline.
`limit_deadline` uses `min(existing, original_enqueue + timeout)`, never now plus
timeout; a floored zero expires before later I/O. A take linearizes immediately
before its infallible output copy. The future bridge must recheck/narrow before
actual I/O; dispatch cannot prevent suspension immediately before an OS call.
The first terminal remains immutable even after its deadline. Effects already
started can remain after cancel/close/expiry; no rollback/retry is implemented.

## Allocation and evidence scope

Argument/completion snapshots use `try_reserve_exact`, reject unexpected excess
capacity, and never use a second infallible shrink/boxing allocation. Slot/budget
checks precede allocations; refusal publishes no token/reservation or completion.
An independent expiry check may still install its own terminal during post.
Reservations cover payload Vec capacities, not process RSS, inline metadata,
allocator overhead, caller buffers, OS buffers, bridge tasks/codecs, or native I/O.

On the recorded aarch64 macOS host: inline `Mailbox` size 984 bytes, construction
zero allocations, first standard-library mutex lock one 64-byte allocation. That
std path is infallible: refusing it in a child **aborts with SIGABRT**. This known
negative transcript is retained in allocation logs; it is not graceful rejection
or general OOM/panic safety. Do not replace this with a custom unsafe lock.
Argument and completion allocation refusal are tested separately and return typed
`AllocationFailure` with no added retained allocation. Max payload occupancy uses
16 allocations with retained/peak payload bytes exactly 8388608, separate from
fixed synchronization metadata and caller copies. Actual cancel/control/poll/take/
close/ack paths allocate no auxiliary queue in the measured test.

`verify.py` records complete VM input digests, frozen contract/source comparisons,
source revision, tools, commands, logs, scope and exit status in `receipt.json`.
Default and feature debug/release tests include the unchanged execution suites;
combined feature runs also exercise the existing stream-validation experiment.
Allocator tests include controlled payload refusal, exact/+1 bounds, full-mailbox
occupancy, coalescing, and delayed-post expiry. State tests cover owner/generation/
turn exhaustion, stale/foreign IDs, terminal races, trapped-turn discard, success
publication, early exit, close retention and exact poll/backpressure behavior.

Not qualified: profile 4/guest ABI 2, actual imports/guest hostile memory/token
handling, VM fuel/host-call/byte charges, C buffer layouts/panic boundaries,
counted session registry integration, strict payload codec/grant/native factory
binding, native I/O/rate limits/exit observation, Swift concurrency and scheduler,
activation/identity/release changes, immutable package dogfood, physical devices,
store acceptance, operations, independent security review, or any GA gate. Phones
remain disconnected; no device attempt is made or requested.
