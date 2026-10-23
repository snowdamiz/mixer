# Native capability exit observation proposal

Status: root approved the additive native design for implementation on 2026-10-22.
The candidate implements the installed initializer, observed-call entry point and
joined private lease below. It changes the native source implementation identity;
schema-v1 wire bytes, generated dispatch, VM, C ABI, activation and release contracts
remain unchanged. Candidate qualification is recorded separately in
[`capabilities/verification/exit-observation`](../capabilities/verification/exit-observation/).
No product/GA gate is qualified by this document. The native exit observation is a
dependency of the opt-in [guest capability ABI proposal](guest-capability-abi-proposal.md).

## Observed source behavior

- `Host.swift:95–130` accepts a decoded call and runs the generated dispatch in a
  detached task. `complete` (`150–153`) releases its slot after that async function
  returns. Cancellation/deadline deliver a terminal result and cancel work while
  retaining the slot until that return. This bounds that host's active dispatch
  tasks, but is not proof of the underlying adapter's cleanup boundary.
- `URLSessionHTTPTransport.swift:163–185` records a terminal result, starts
  `invalidateAndCancel`/`finishTasksAndInvalidate`, then resumes its continuation.
  Its actual native request counter is released separately by
  `didBecomeInvalidWithError` (`286–294`). Thus success as well as failure can
  return before invalidation is acknowledged. A closure wrapping `request` hides
  this second boundary from the host.
- Host `close` (`133–136`) cancels work then removes all slots. Work and timers
  capture the host weakly. A cleanup observer stored only in a slot or reached only
  through `self?.complete` cannot survive close/deinit reliably.
- `AppPrivateKeyValueStore.get/put/delete` (`87–109`) are actor-isolated synchronous
  methods satisfying async protocol requirements. They have no suspension point.
  All directory reads, inventory calls, writes, fsyncs, rename/unlink and local
  descriptor `defer` cleanup finish before each method returns or throws.
  `available` checks cancellation before I/O; `replace` checks it again after the
  temporary-file fsync and before rename. No check can undo a rename/delete already
  performed. Actor `close` runs serially after an executing method and closes the
  store's persistent root/lock descriptors. Per-request exit must not mean closing
  that shared store, and cancellation does not prove a durable mutation was undone.

## Minimal additive installed surface

Keep the current `CapabilityHost.HTTPTransport`, legacy initializer, ordinary
`submit(_:deliver:)`, generated service protocols, generated dispatch and all
capability schema-v1 bytes unchanged. The legacy path remains usable for native
applications/tests; its arbitrary HTTP closure or `AppPrivateKeyValueServing`
conformer cannot attest native cleanup by returning alone.

Add a closed native adapter value and a distinct observed-call entry point. Names
below are the root-approved contract:

```swift
#if !os(WASI)
public struct InstalledCapabilityAdapters: Sendable {
    public init(http: URLSessionHTTPTransport? = nil,
                storage: AppPrivateKeyValueStore? = nil)
}

extension CapabilityHost {
    public init(policy: CapabilityPolicy,
                maximumRequests: Int = 64,
                maximumGenerationsPerSlot: UInt32 = .max,
                timeoutMilliseconds: UInt32 = 30000,
                installedAdapters: InstalledCapabilityAdapters) throws

    public func submitObserved(_ bytes: Data,
                               deliver: @escaping Delivery,
                               didExit: @escaping @Sendable () -> Void) throws
}
#endif
```

The value contains only concrete owned native adapters; it is not a new open
protocol and accepts no closure, delegate, custom URL protocol, arbitrary store,
callback-selected factory, or claimed implementation identity. Test-only injection
can remain internal under `@testable import`. Constructing this value alone is not
release/grant/configuration identity binding; that later installed factory is still
required. Both adapter fields may be absent, yielding the ordinary `unavailable`
terminal result without I/O.

`submitObserved` accepts only a call envelope on a host built with
`installedAdapters`. Reject use on a legacy host, a cancellation envelope, malformed
bytes, closed host, wrong owner/generation or unreserved/duplicate call **before**
accepting observation or mutating a slot. If it throws, it has accepted neither
work nor an exit callback. Once it accepts the call, the host owes exactly one
`didExit`, including denied/unavailable requests. Delivery and exit remain separate
signals; exit may arrive before this method returns for a no-I/O rejection.
Cancellation continues through the existing cancellation envelope and does not
install a second observer. A reservation cancelled before any accepted call has no
operation lease and no exit obligation. A call accepted and then cancelled before
its worker starts does have an exit obligation and must resolve it without I/O.

The ordinary submit path on an installed host should use the same internal
resource-aware slot lifecycle, with no external observer. Existing legacy
semantics remain backward compatible and explicitly ineligible for future native
mailbox exit acknowledgement. Do not silently reinterpret an arbitrary closure as
trusted merely because it calls a concrete adapter internally.

## Private lease and lifetime

Each accepted observed call creates one private reference-type lease with a fresh
native identity, the fixed originating `CapabilityRequestID`, and the associated
exit closure. Do not expose this identity to guest wire data or let a caller select
it. Reuse/generation checks still use existing host-issued identities; a stale
callback must also match the slot's current private lease by identity before
releasing it.

The lease joins two one-way facts:

1. **Invocation returned:** the worker finished adapter invocation, result
   validation and its attempted host terminal delivery, or the host proved no
   worker/adapter will run for a denial/unavailable/pre-start cancellation.
2. **Adapter exited:** no operation started, the owned storage method returned
   after synchronous per-operation cleanup, or the owned URLSession transport
   acknowledged invalidation and released its request counter.

Only their conjunction emits `didExit` and makes the installed host slot reusable.
Keep these facts and a once flag under one short lock. Take callback values under
the lock and invoke them only after unlocking. No adapter, URLSession callback,
continuation resume, actor hop, user delivery or external observer runs under it.
Repeated reports are harmless, and deinit alone must never fabricate adapter exit.

The worker strongly retains its lease independently of the weak host. Before any
adapter starts, the worker owns the adapter-exit obligation. Transfer that
obligation to `HTTPTransportExchange` only after the exchange has safely adopted
it; every earlier throw/cancellation path resolves the no-I/O side. Storage can
resolve its side after the concrete actor method returns/throws because no
operation-local I/O survives it. The worker reports invocation-return in `defer`
even if the host has closed or deallocated.

For HTTP, add an internal observed-request overload used only by the closed
installed adapter dispatch. Existing public `request(_:)` uses the same helper
without an external observer. Once a transport lease is acquired, the exchange
retains the cleanup obligation until invalidation. Cancel-before-start/deadline
before session creation resolves it together with transport-counter release.
`didBecomeInvalidWithError` clears session/task ownership, releases that counter,
and reports adapter-exit exactly once. Do not report exit from `finish`, the
continuation resume, timeout, task cancellation, `didCompleteWithError`, or an
arbitrary wrapping closure's return. Callback ordering races must be tested.

The lease's external closure is retained by the worker/exchange, never solely by
the host. It can strongly retain the future private Rust bridge lease and perform
its bounded acknowledgement after host close/deinit. Its optional host slot-release
relay captures the host weakly and checks both request and private lease identity.
Close still stops admission and terminal delivery immediately; removing slots does
not destroy the independent lease. A hung adapter keeps the external lease pending
and cannot be acknowledged merely because host ownership disappeared. This slice
does not impose a new process-wide host/session cap; that belongs to VM registry
integration and requires separate proof.

The observer is a native installed callback, may run synchronously on the current
executor, and must return promptly without waiting for a host actor operation. No
external callback is executed under a lease/transport lock. Delivery may precede
exit; exit can precede the actor's processing of its slot release relay. Consumers must not infer slot availability from callback ordering
alone. Observer callbacks signal this specific request's documented native cleanup
boundary, not total OS socket destruction, process RSS reclamation, global
quiescence, Swift task unwinding guarantees or durable-effect rollback.

## Terminal/exit matrix

| Accepted call path | Terminal result | Exit proof |
| --- | --- | --- |
| Grant denial / missing installed adapter | Fixed failure | Host proves no invocation/I/O started. |
| Cancellation before detached worker begins | Cancelled | Worker observes cancellation; no adapter adoption; worker returns. |
| HTTP argument validation / cancellation / deadline / quota failure before exchange adoption | Existing error mapping | Invocation returns and no session was created; an acquired transport counter is released if applicable. |
| HTTP success, response rejection, redirect, TLS/network failure, cancellation or deadline after adoption | First terminal transition wins | Invocation-return plus exchange invalidation/counter-release receipt. |
| Storage success/failure/cancellation before or during serial operation | Existing outcome, including possible uncertain commit | Concrete actor method returns/throws with local descriptor cleanup complete, then worker returns. |
| Host close/deinit during any adapter work | Delivery cancelled/suppressed by current host semantics | Same adapter-specific exit proof, retained independently of host. |
| Duplicate/late terminal or cleanup callback | No replacement delivery | Private lease once flag prevents duplicate exit/reuse. |

Malformed/unowned calls, cancelled unused reservations and rejected observed API
uses are not accepted calls; they have no callback obligation. Host deinit currently
cancels work without promising delivery; keep that distinction explicit.

## Executable proof for the implementation slice

Use the existing capabilities Swift test target. Add deterministic internal seams,
not a public arbitrary-adapter exit authority. Cover:

- Observer registration rejects legacy hosts/cancel envelopes/malformed/stale calls
  without consuming the reservation or running a callback.
- Success, denied/unavailable, cancelled before worker start, quota/validation
  failure, deadline, explicit cancellation and duplicate/late reports emit once.
- Separate terminal-return and invalidation controls prove delivery/task return
  cannot release installed host capacity or the observed lease early.
- Exit-before-worker-return and worker-return-before-exit both require the join.
- Close and releasing the last host reference retain cleanup observation until
  delayed invalidation, suppress late delivery, and do not keep the host alive.
- Shared storage operations retain serialization; exit follows synchronous local
  cleanup; cancellation cannot be represented as a rollback receipt.
- Old closure-based behavior/codecs continue passing; generated-source checks stay
  deterministic. Record source identity changes through the existing generator
  after source approval. Do not hand-edit generated native identity output.

Mac tests establish these source/runtime boundaries only. Physical iOS/Android,
OS lifecycle/TLS qualification, Rust mailbox integration, C unwind containment,
separate immutable-package consumption, signing, stores, independent review and
GA gates remain pending. Phones are disconnected; this lane makes no device query,
run or reconnect request.

## Inspection evidence

Read-only baseline: revision `b4f13ec9a78b882380a6cfba0a9607990ca9babe` on
`main`, with unrelated VM/Android review changes already in the worktree. Commands:
`cat AGENTS.md`, `nl -ba`/`sed` source reads, `rg`/`rg --files`, `git status --short`,
`git rev-parse HEAD`, `git --version`, `swift --version`, `shasum -a 256`.
Tools: Git 2.56.0; Apple Swift 6.4
(`swiftlang-6.4.0.34.1 clang-2100.3.34.1`), target
`arm64-apple-macosx27.0.0`.

File-byte SHA-256 inspection anchors:

```text
e603568d64b73513c27d72a6bfef7d82fadad3e1dc5344bd52a1ac93899805a6  sdk/Sources/MixerCapabilities/Host.swift
70f8e149bf3a761c71f243f22b07e40dd0a1f2e52b8ff6db2260224937e3f61b  sdk/Sources/MixerCapabilities/URLSessionHTTPTransport.swift
a2f5378900f257e4f2806fd3568a683d9808f15debcb186be94dfb9aa44f3be7  sdk/Sources/MixerCapabilities/AppPrivateKeyValueStore.swift
6dbb44cd4bb37d0abd4cc99db21b50074f6fa06cca529aac9714f6134cad6b65  docs/guest-capability-abi-proposal.md
```

This inspection baseline predates implementation. Executable candidate evidence
belongs to the separate exit-observation receipt; no gate is passed by inspection.
