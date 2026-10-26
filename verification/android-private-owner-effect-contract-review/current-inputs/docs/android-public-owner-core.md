# Android host ownership core

`OwnerLifecycleV2` implements the selected bounded decision prerequisite in
[the root selection](../verification/android-public-owner-root-review/implementation-selection.json).
It is package-private pure Java under `native/android/owner-core/`, outside the
exported adapter map. It imports only Java standard-library collection and
validation types. No Android effect runner or public Activity integration is
implemented. The original proposal and root clarifications remain immutable.

## Actual behavior

The core binds one Activity/root identity and owns an opaque lifetime, a pending
drain token, one operation token and one current presentation token. It retains
one acquired coordinator identity and three cleanup completion/failure slots.
Each call returns an immutable batch of at most five decisions. It retains no
action history, native event bytes, packet bytes or queue. Only tests keep a
history and manually deliver queue tokens.

Construction begins in `WAITING_WINDOW` with foreground and focus false.
`windowChanged` and `drain` accept fact records; neither record is a concrete
native capture. A ready fact requires matching Activity/root identities, a live
Activity, attachment, non-null window token, positive width/height and available
insets. First readiness schedules one drain; delivery requires a fresh probe
before emitting `OPEN_INITIAL`. Duplicate notifications cannot open twice.
The bound window token cannot be replaced or lost after opening begins.

The returned `OPEN_INITIAL`, `REFRESH_COMMITTED` and `DISPATCH_INPUT` decisions
each create one in-flight operation. Only its exact token may complete it.
Only the first exact opening completion may adopt an acquired resource; this
also applies after retirement so a late resource receives one terminal `CLOSE`.
Opening failure with an acquired resource also closes it. Foreign/duplicate
completions cannot adopt or close a foreign resource. Refresh/input completion
must return the same acquired identity; mismatch retires and closes the owned
resource. A successful current operation issues a fresh presentation token.

Invalidation immediately denies input and emits a nonterminal `SEAL`, then at
most one `QUEUE_DRAIN`. An operation already in flight prevents refresh overlap.
Completion services only its captured dirty epoch; a newer invalidation schedules
one later refresh. Zero size or missing insets keeps the owner dirty and waits
for a real later notification without polling. Refresh emits no engine or input
command and retains the same owner. The core does not hold the committed packet;
the eventual runner must route this decision to the coordinator's retained-byte
refresh method without invoking the Swift engine.

`permits(operationToken)` is specifically a terminal operation fence. Dirty
environment checks remain the native renderer's responsibility. `admitsInput`
requires a live clean owner, foreground, focus, a matching presentation/lifetime,
and no pending operation/drain. `dispatchInput` emits an immediate operation,
retains no payload and creates no replay queue. The future runner must finish it
synchronously. `pause`/`stop` deny input without replacing the session;
`resume`, configuration and focus notifications dirty the environment. Refresh
may finish while background/unfocused, but input remains denied.

Close, detach, destroyed/foreign window facts, loss of the bound token, missing
facts, failed/unconfirmed operations, registration failure and epoch exhaustion
are terminal. Retirement first changes state and revokes fences, then emits
terminal `SEAL`, `CANCEL_QUEUED`, `UNREGISTER`, and `CLOSE` when idle with an owned
resource. A terminal request during any operation defers close until completion;
an operation that never returns leaves actual cleanup pending. Reattachment and
late callbacks never revive that lifetime. Cleanup completions occupy independent
bounded diagnostic slots; first completion wins, and close completion releases
the retained resource reference. These decisions do not perform cleanup or
guarantee its success.

Every entry asserts the injected trusted owner-thread checker before examining
tokens, facts or state, including stale callbacks/completions and observations.
The checker must check or throw without reentry/effects. A package-private epoch
seed constructor exists for deterministic exhaustion controls; normal
construction uses zero. Epochs never wrap, and tokens are never recycled.

## Verification and limits

Run the exact two-source suite with:

```sh
python3 -B native/android/tests/run-owner-core-host.py --attempt <new-name>
```

The runner uses the existing pinned OpenJDK 25 location, or explicit `--jdk` /
`MIXER_JDK`, without downloading tools. It snapshots only the core and host test,
then compiles using `--release 17 -Xlint:all -Werror -proc:none` and empty class/
source paths. It retains compiler/runtime versions, argv, sources, class hashes,
all streams, structured test results and cleanup. Each attempt uses a new owned
output directory; only that attempt's scratch is removed. JVM option environment
variables and implicit classpath are removed from the child environment.

The suite exercises readiness, fresh probes, dirty coalescing, opening/refresh/
input overlap, terminal requests during operations, stale/foreign identities,
late acquisition, unknown outcomes, resource mismatch, configuration/focus/
foreground transitions, independent cleanup decisions/failure identities,
epoch overflow, every entry's thread assertion and 5,000 refresh cycles. The
cycle assertions describe repeated decision controls, not extra product features
or a performance benchmark. See the frozen implementation receipt for exact
counts, source bindings, historical attempts and limitations.

This is **actual host ownership-decision evidence**. No Android stubs are used;
there are no Android runtime or UI claims. Native gate sealing, registered-listener
ownership/partial cleanup, main Looper enforcement, real window/inset readiness,
setter reentry, JNI/Swift transaction safety, stale IME/draw/input suppression,
configuration recreation and state preservation require later integration and
runtime evidence. Actual cleanup attempts and fatal error propagation belong
to the future effect runner.

Public `MixerActivity` remains V1. Source-pair profile 1, SDK/adapter sources,
native ABI, default shared theme and all current unsupported-operation checks
are unchanged. Product API 28+ remains proposed subject to qualification, while
private V2 still rejects API below 36 and unsupported high-contrast/weight/
resource/font states. Later exported integration requires a newly selected
source profile and explicit migration, not lock refresh. Physical phones,
immutable separate-repository published FieldLog packages, signed/store/
operational gates and accountable GA acceptance remain pending. The runtime/
computer-use pause remains in force.
