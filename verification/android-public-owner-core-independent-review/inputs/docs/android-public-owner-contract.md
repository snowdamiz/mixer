# Android public owner prerequisite: terminal lifecycle core

**Status: proposed for root selection; no public routing or implementation acceptance.**
Reviewed against `1f114d8f235e8042c275a2549fef7d4994272360` and the exact source
bindings in [this packet](../verification/android-public-owner-contract/receipt.json).
The selected prerequisite is one small, deterministic Java ownership transition
core. Its first implementation can live outside the exported adapter and run on
the host. Android wiring is a later, separately selected slice.

The copied-SDK/source-pair implementation is accepted in
[the root receipt](../verification/android-copied-sdk-appearance-contract-root-review/implementation-acceptance.json).
Generated source export, default descriptor packaging, and source-pair admission
are completed prerequisites within their recorded scope. The older
[routing proposal](android-public-appearance-routing-proposal.md) is historical.
None of these receipts selects public V2. The shared theme remains the default;
this proposal makes no branding or appearance change.

## Observed boundary

| Current source | Observed behavior and consequence |
| --- | --- |
| `MixerActivity.java:10–15` | Creates a session, performs V1 exchange and applies the V1 renderer directly in `onCreate`; destroys only the session in `onDestroy`. There is no V2 window readiness, refresh scheduling, or owner token. |
| `NativeCoordinatorV2.java:18–40,73–144,146–185` | Private main-Looper coordinator creates its own session, stages/attaches/commits ordinary input, retains the exact committed packet, and refreshes that packet without an engine transaction. Refresh failure retires both owners. This is the correct transaction boundary to retain. |
| `NativeCoordinatorV2.java:192–243` | Retirement publishes `retired`, clears the packet/session, then independently attempts renderer disposal and session destruction. `close()` enters the live/non-reentrant guard, so it is not an idempotent lifecycle callback and cannot be called from an active transaction. An outer owner needs its own terminal latch and cleanup ordering. |
| `NativeEnvironmentV2.java:34–39,58–100,141–150` | Captures verify owner, generation, window token and a second synchronous tuple read. Actual attached root, positive size, live Activity and insets are required. Listeners invalidate the renderer; they do not request a coordinator refresh. Detach calls invalidation before setting the observer retired. `invalidate()` has no retired early return. A queued callback can therefore still reach the renderer after retirement. |
| `NativeEnvironmentV2.java:70–85,143–150` | Listener registration occurs sequentially in the constructor; a later registration failure has no constructor rollback. Close unregisters sequentially and can stop at the first exception. Future wiring must preserve partial-registration ownership and attempt remaining cleanup. |
| `InstalledAppearanceV2.java:31–60` | Descriptor capture is main-thread, bounded to 64 KiB, renderer-owned and copied. It rejects every resource declaration and non-system-sans typography. It is installed data, not a lifecycle token or permission to run unsupported environments. |
| `NativeRenderer.java:79–105,211–218,281–321,354–365` | Renderer gates events using current presentation, record identity, enabled/attached/shown/focused state; invalidation closes gates and cancels toggle input. Environment-only preparation preserves the current packet/revision. Attachment/commit checks remain authoritative. Renderer disposal closes the environment observer. V2 also rejects API below 36. |
| `NativeAppearanceViewsV2.java:112–143,522–530,608–626,675–690` | Native callbacks and draw/touch/key paths consult renderer authority; toggle cancellation clears ownership before parent callbacks. An outer owner must add lifetime fencing without weakening these checks or replaying rejected input. |
| `SessionRegistry.swift:3–9,36–44,87–155`; `DocumentSession.swift:7–49` | Synchronous, non-reentrant, value-state ordinary registry. One staged candidate per session; native attachment precedes scalar engine commit. Refresh must not call render/dispatch, allocate a new session, advance Swift revision, or run effects. These APIs do not provide saved-state restoration or signed update authority. |
| `AndroidProject.swift:128–173,185–206`; `ProjectGenerator.swift:125–150,212–224` | Generated manifest still declares V1 `MixerActivity`, min API 28, target 37; app-owned Swift entry exports ordinary and private staged functions. Android uses stateful draft/add/toggle; iOS starter uses the read-only surface. State is process-local. Lifecycle core acceptance cannot establish shared interactive parity or state continuity across recreation. |

## Proposed bounded implementation

Implement `OwnerLifecycleV2` as an independently authored, package-private pure
Java transition core in `native/android/owner-core/src/dev/mixer/android/`, with
host tests in `native/android/tests/OwnerLifecycleV2HostTests.java`. Do not import
Android classes, JNI, a renderer, installed captures or third-party code. Do not
place it under exported `app/src` in this first slice. It owns decisions, tokens
and an ordered action log; an Android effect runner is explicitly absent.

The core accepts synchronous owner-thread events, readiness facts, and operation
completions. It emits `OPEN_INITIAL`, `REFRESH_COMMITTED`, `DISPATCH_INPUT`, `SEAL`,
`CANCEL_QUEUED`, `UNREGISTER`, and `CLOSE` decisions. Tokens are private object
identities issued by the core, not caller-chosen numbers. A lifetime token, one
pending-drain token and one in-flight operation token are distinct. Host facts
are test inputs only; they cannot mint `NativeEnvironmentV2` or installed
authority. Every entry, including queue delivery and completion, calls an
injected owner-thread assertion before reading or mutating state. The eventual
Android assertion is exactly `Looper.myLooper() == Looper.getMainLooper()`.

| State/event | Required transition and effects |
| --- | --- |
| Construction | `WAITING_WINDOW`; no session, coordinator, packet or queued work. Bind one Activity/root identity for this lifetime. |
| Readiness notification | Probe synchronously. Ready means same Activity/root, Activity not destroyed, attached root, non-null window token, width and height positive, and root insets available. Unready facts before opening retain `WAITING_WINDOW` and do not spin, post repeated polling, or call native code. Attachment alone or `setContentView` return is insufficient. |
| First ready drain | Bind the window token by reference identity; issue exactly one `OPEN_INITIAL`, enter `OPENING`, close input admission. An effect runner would create a fresh coordinator and call `renderInitial` once, using concrete captures. No V1 renderer may share that instance. |
| Successful matching initial completion | Enter `LIVE` only if lifetime/operation/window are current, the operation reports a committed presentation, and no terminal request occurred. Preserve an invalidation received during opening; schedule one later refresh instead of clearing it. |
| Invalidation while live | Synchronously close input admission and mark dirty before posting anything. Increment a checked epoch and coalesce to at most one pending drain. No inline coordinator call from a native listener, layout callback or setter. |
| Refresh drain | Recheck lifetime/drain identity and concrete readiness. With dirty live owner and no in-flight work, issue `REFRESH_COMMITTED`, enter `REFRESHING`. No engine transaction or app event. If size/insets are temporarily unavailable, remain dirty with gates closed and wait for a later real notification; do not poll or treat unavailable data as supported values. |
| Successful matching refresh completion | Enter `LIVE`; clear dirty only for the epoch that was serviced. A later invalidation remains dirty and schedules one follow-up drain. A stale completion cannot clear it or open input. |
| Native input admitted while live/current | Enter `INPUTTING`, issue one immediate `DISPATCH_INPUT` with a fresh operation token, and require synchronous matching completion. Successful completion publishes only the current committed presentation. No input queue or reentrant dispatch; invalidation/close during input follows the same dirty/terminal rules as refresh. |
| Detach, destroyed Activity, changed/lost bound window token, explicit close, epoch exhaustion, or operation failure | Enter terminal `RETIRED` first and revoke lifetime/drain/input admission. Emit `SEAL`, then `CANCEL_QUEUED` and `UNREGISTER`. Request one coordinator `CLOSE` when no operation is executing. A coordinator acquired by an operation that returns after retirement must be closed once and never published. |
| Repeated close, stale/duplicate callback, completion or reattach | Remain terminal; no new session/render/refresh/input and no second cleanup attempt. Stale operation completion still discharges the one recorded owned coordinator if not yet closed. A fresh Activity needs a fresh core; reattachment does not revive this lifetime. |

`OPENING`/`REFRESHING`/`INPUTTING` mean one operation is in flight; no second operation is
issued until its matching completion. Registration/open/refresh/input failures are
terminal for this core even where the private coordinator could prove rollback.
Unknown outcomes never trigger retry or reopen. A close failure is recorded
after authority has been revoked and does not authorize another operation.
The future effect runner retains the primary failure and attaches independent
cleanup failures; fatal `Error` values must remain fatal.

The core exposes a read-only `permits(operationToken)` fence and
`admitsInput(lifetimeToken, presentationToken)` decision. Input admission requires
`LIVE`, no dirty epoch, no pending operation and current token identities. The
renderer must still validate environment, document revision/node generation,
record identity, disabled state, attachment, visibility and window focus.
The core never buffers, replays or rewrites native events. Loss of focus closes
native input immediately but is not a new lifetime or a requirement for initial
layout; a focus notification is an environment invalidation. Pause/stop alone
does not destroy the session or invent Swift lifecycle/effect semantics. Resume
requests a fresh probe/invalidation before native input may resume.

**Required later effect-runner contract:** retirement during an in-flight native
setter must synchronously seal actual draw/input gates. Coordinator and renderer
must consult the terminal fence before attachment validation/commit and never
publish a presentation after revocation. Keep the existing no-callback/no-capture/
no-allocation interval between scalar engine commit and renderer finish. If
revocation happens earlier in the same main-thread call stack, the candidate must
abort or retire; checking only after the operation returns is insufficient. A
pure action log cannot establish this Android guarantee. Physical detach cannot
be made safe merely by ignoring a later completion.

## Concrete later integration touchpoints

1. `MixerActivity` owns one root and eventual owner adapter. Install readiness
   notifications after `setContentView`; postpone V2 construction/initial render
   until the real probe succeeds. `onDestroy` seals first and releases in `finally`.
   Preserve ordinary app-owned Swift factory/reducer behavior; do not substitute
   the repository checklist. No public Activity edit is selected here.
2. `NativeEnvironmentV2.Observer` publishes typed invalidation/terminal reasons
   after closing renderer gates. Terminal state must precede detach callbacks;
   retired observers ignore queued notifications. Registration records acquired
   listeners incrementally, rolls back on partial failure and attempts all owned
   unregistrations on close. Preserve the registered `ViewTreeObserver` identity
   for removal; do not remove from an unrelated replacement observer. Root inset
   ownership must be composed in one place: the present Activity padding listener
   and observer's setter cannot silently replace each other. Apply safe area once.
3. `NativeCoordinatorV2` remains the sole ordinary session/committed-packet owner.
   Bridge the core's terminal fence and refresh decision without making `close()`
   reentrant or reopening a retired renderer. Its existing retirement already
   attempts renderer and engine cleanup independently; observer cleanup must
   acquire the same guarantee. No UI event or refresh may use legacy exchange.
4. `NativeRenderer`/`NativeAppearanceViewsV2` keep all existing native admission,
   candidate, editor/IME, toggle-cancellation and stale-environment checks. Add
   lifetime fencing to gates/input and the precommit validation, with no callbacks
   inserted into the scalar commit/finish interval. Only a current successful
   operation can open a current gate. Do not synthesize stale readiness/captures.
5. Configuration delivered to the same Activity invalidates the complete tuple
   and refreshes exactly the committed bytes. Activity recreation retires the
   old root/session; new Activity uses a new core and session. Never transfer an
   old coordinator, native record, capture or queued event. The current app loses
   process-local value state on recreation; this core does not fix that. A later
   explicit value-state save/restore contract is required before claiming user
   state continuity. Do not add manifest `configChanges` as a shortcut.

## API, profile and support consequences

The pure core adds no public Swift API, UI packet field, appearance descriptor
field, C/JNI symbol or native feature support. Document schema 1, packet schema 1,
`mixer.native-appearance.2` / `measuredShared2`, and the private staged ABI remain
as currently recorded. This is not signing, OTA eligibility, or release authority.
No third-party dependency is added.

`mixer.android-source-pair.1` binds the accepted 22 SDK + 20 adapter files; all 42
still match `559858810e133640d52730972a6610e98442be6d`. A host-only core outside
that exported map does not alter it. Later copying the core or editing any
mapped SDK/adapter file requires root-selected **new source-pair profile and
explicit migration/recreation**, updated closed file maps/digests, driver and
common preaccess controls, and fresh generated-app tests. Do not refresh profile
1 or a stale lock from the working tree. Any new Android public runtime/fingerprint
or stable native ABI needs its own selection and installed-binary compatibility
evidence; the internal source-pair ID does not confer those properties.

Product §19.1 retains proposed **Android API 28+**, subject to qualification.
The current private V2 checks in both renderer and observer reject API below 36.
The public high-contrast read/listener used by the observer first appears in API
36; that explains a current implementation floor, not a product-baseline change.
The owner core can be implemented independently while retaining every rejection.
Removing the floor or substituting `false` for unknown accessibility state is not
part of this prerequisite. API 28–35 environment capture/rendering and native
compatibility remain a hard blocker to selecting V2 as the public default.

High contrast, nondefault font weight, declared resources and bundled fonts are
also still rejected by this private slice. Later support must provide real
capture/rendering behavior and evidence; lifecycle modeling cannot claim those
states supported. D8 `--min-api 28`, source inclusion, host tests or a successful
API 37 build cannot discharge that blocker. Public routing remains pending after
this contract and after any future pure-core pass.

## Deterministic acceptance matrix for the next core slice

Use a manually drained fake queue, injected thread assertion, identity-distinct
root/window/lifetime/presentation tokens, operation completions delivered in any
order, and an action recorder. No sleeps, Android stubs, fake installed descriptor
authority, or source-text assertions as behavior tests. Every row is **planned,
not executed in this proposal**.

| Control | Required observable result |
| --- | --- |
| Each entry from wrong thread | Reject before any state/action change, including stale close/completion. |
| Unattached/null-token/zero-width/zero-height/missing-insets readiness | No open, render, JNI or polling; later complete readiness opens once. |
| Duplicate attach/layout/ready notifications | Exactly one open and one initial operation; distinct tokens. |
| Dirty burst before drain; invalidate during opening/refresh | At most one drain; serviced epoch cannot erase newer dirty epoch; exactly one needed follow-up. |
| Dirty owner becomes zero-sized then ready | Gate remains closed; no refresh while unready; one refresh when ready. |
| Environment refresh | Only refresh command; same coordinator/committed packet identity, no input/open/engine action. A fake port proves routing only. |
| Detach or close before initial readiness | Terminal; queue/reattach cannot create a session. |
| Detach/close during open, refresh or input | Fence becomes false synchronously; no publish; one eventual close for an acquired coordinator. |
| Callback already dequeued before cancellation; old lifetime after recreation | No effect even if queue removal deliberately does nothing. |
| Reordered/foreign/duplicate operation completions | Cannot publish, clear dirty, close a foreign coordinator or double-close an owned one. |
| Old presentation/native event after invalidation/refresh/retirement | Denied; no event buffering or replay. Native renderer checks remain separately required. |
| Token replacement/loss after binding; destroyed Activity | Terminal, including during in-flight operation; no same-core rebind. |
| Open/registration/refresh failure, unknown outcome, epoch exhaustion | Terminal before cleanup; no retry. Seed the epoch for exhaustion; never wrap. |
| Failed cancel/unregister/close completion reports | All owned cleanup decisions remain issued independently; diagnostics preserve primary/secondary identity and terminal state. Actual attempts and fatal-error propagation belong to the later effect runner. |
| Pause/stop/resume and same-Activity configuration | No session recreation/effects; resume/config dirty the environment; no stale input before refresh. |
| Full old/new Activity sequence | Fresh tokens and session decision for new owner; old state cannot affect it. No saved-state continuity claim. |

The core receipt must identify itself as **host ownership-decision evidence**.
Actual listener delivery, partial registration cleanup, main Looper enforcement,
real readiness/insets, reentrant native setter revocation, JNI rollback/unknown
outcomes, native stale IME/input/draw suppression and same-Activity/recreation
behavior require the later Android adapter and runtime matrix. Those checks are
pending during the user pause. API 28/intermediate/current OS, resources/fonts,
TalkBack, final side-by-side physical design parity, signed/store/operations,
immutable published separate-repository FieldLog consumption and accountable GA
review remain pending. No native/capture process was started or queried here.

## Official platform basis

Checked 2026-10-25 America/New_York; exact access time and fetch limitations are
in [the source note](../verification/android-public-owner-contract/platform-sources.json).
These are specifications, not implementation sources or runtime receipts.

- [View reference](https://developer.android.com/reference/android/view/View):
  attachment and nullable window-token APIs are distinct facts; positive size
  and insets are additional requirements selected from the current consumer.
- [Looper reference](https://developer.android.com/reference/android/os/Looper):
  the application main Looper belongs to its main thread.
- [Handler reference](https://developer.android.com/reference/android/os/Handler):
  queue removal targets pending callbacks; a terminal flag/token must still
  fence delivered work.
- [AccessibilityManager reference](https://developer.android.com/reference/android/view/accessibility/AccessibilityManager):
  high-contrast read/listener are API 36, so no equivalent older public API is
  established by this source review.
- [WindowInsets.Type reference](https://developer.android.com/reference/android/view/WindowInsets.Type):
  the current typed system-bars path starts at API 30; older API handling still
  needs an explicit design even apart from the API 36 floor.
- [Configuration changes for Views](https://developer.android.com/topic/architecture/views/resources/runtime-changes-views):
  both recreation and updates within one Activity must be handled, and state
  preservation is a separate responsibility. No manifest opt-out is selected.
