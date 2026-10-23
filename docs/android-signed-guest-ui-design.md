# Android signed guest UI: next implementation boundary

Status: proposal for root contract review, 2026-10-23. This document changes no
installed contract, runtime, Android host, gate, or release authority. Initial
inspection used commit `5a0367d6c56bb288ddd45dccc44ddfe20f533781`; the executable
host baseline captured commit `35a9a36c8837fd2dd3e491419b7965b6307cd6b9`. Exact selected input
hashes and device-free commands are in
`verification/android-signed-ui-design/receipt.json`. Concurrent work elsewhere in
the checkout is outside this lane.

The next slice should run the existing **signed** capability/guest-UI pipeline on
Android and attach its private presentation to the existing owned native widget
renderer. It must carry a real button event through the fixed guest event export,
harvest its replacement UI, and earn `first_screen` only through an attached native
layout/display probe. The bounded guest exchange and native VM are reused. The
synchronous development checklist registry is not an activation runtime.

This advances W05/W10. It does not complete their product-plan acceptance: D2 still
requires shared physical Android/iOS flows and accessibility evidence; D4/D5 require
meaningful dual-platform OTA, immutable separate-repository FieldLog consumption,
preserved data and controlled recovery receipts (`mixer-product-plan.md:717-725`,
`:767-773`). Phones remain disconnected; no device query or run is authorized here.

## What exists, and the precise gap

| Inspected seam | Current behavior and required use |
| --- | --- |
| `contracts/guest-ui-event-v1.json`; `docs/guest-ui-event-integration-design.md` | Frozen signed UI selection, fixed startup/event/wake turns, bounded exchange, stop ordering and health requirements. Preserve these bytes and all referenced frozen UI/VM/release/identity contracts. |
| `CapabilityGuestUIRuntime.swift:1,8,38` | The entire public signed facade is behind Apple imports; its presentation accessor is `@MainActor`. Separate platform-independent signed download/start/recovery/close methods from platform presentation construction. |
| `CapabilityGuestUIPresentation.swift:235,265` | Apple owns one counted consumer; the non-Apple `bind` throws `presentationInvariant`. Replacing this stub is necessary; a successful Android module build does not execute it. |
| `CapabilityColdStartWorker.swift:102-141`; `CapabilityColdStartControl.swift:18-31` | The worker binds the exchange before construction/startup, confirms real effects, then records `feature_started`; observation retirement already awaits the presentation task's actual `.value`. Preserve these owners and ordering. |
| `GuestUIExchangeV1.swift:211,255,272,328` | `offer`, `claimPresentation`, `completePresentation`, and `observePresentation` already arbitrate input, claimed frames and receipts. Both platforms must use this exact shared instance. |
| `MixerUI/Reconciliation.swift:69,78,100` | Portable `UIRenderSnapshot`/`UIReconciler` already provide authoritative identities, routing and validated whole-document snapshots. `MixerApple/MixerNativeView.swift:8` wraps them in an Apple-only observable `MixerUIHost`; Android does not need to import that wrapper. |
| `native/android/engine/.../DocumentSession.swift:13`; `SessionRegistry.swift:16,33` | Development reducer state is copied and committed synchronously under a registry lock, with no async work or effects permitted. Its 16 handles and rollback promises cannot be reused to own a signed runtime or its native exit. |
| `native/android/bridge/mixer_android.h:7`; `bridge/jni.c` | Existing create/render/dispatch/destroy ABI is synchronous. Keep it for compiled development apps; add a distinct signed-presentation binding rather than reinterpreting operation 1 as guest execution. |
| `NativeRenderer.java:21,43,44`; `UiPacket.java:16,23,24` | Owned native widgets, strict packet decoding, UInt64 decimal tokens and revision/generation reconciliation exist. Rendering requires the Android main Looper. The current event sink captures a whole source packet and Activity forwards to its current session; signed callbacks must capture immutable attachment/binding scalars instead. |
| `MixerActivity.java:12,15` | Current Activity creates a compiled reducer session and destroys it on teardown. It has no signed store owner, display receipt, async retirement or reopen policy. |
| `cli/.../AndroidProject.swift:30,86,119,131` | The exact copied source list and generated entry choose the compiled reducer. Build rejects declared capabilities and resources. Adding signed mode requires an explicit source/identity closure; removing these guards would not integrate capabilities. |

## Decisions root must freeze before dependent edits

1. **Additive native profile.** Freeze a new
   `contracts/android-guest-ui-presentation-v1.json`, not edits to guest-UI-v1.
   Reserve dependency ID `mixer.android-guest-ui-presentation-v1`, version `1`,
   binding its exact bytes in the installed identity-v2 and therefore signed
   release-v3 fingerprint. It specifies the main-Looper presentation domain,
   internal bridge operations, counts, display probe and API/toolchain requirements
   below. Missing/wrong/partial Android bindings reject before reservation/store
   work. Capability-only mode must reject this reserved ID as well as the existing
   UI markers; Apple keeps its existing valid bindings. A declaration is not source
   or linked-archive attestation.
2. **Native presentation domain.** Preserve Apple's public model and MainActor
   helper. Specify Android's equivalent as a synchronous, non-reentrant helper on
   the actual Android main Looper, with checked entry from JNI. Do not assume that
   Swift `MainActor` or `DispatchQueue.main` is integrated with Android's Java
   Looper. Introduce no private Swift runtime executor hooks and no alternate
   interpreter worker. This is an additive platform interpretation needing explicit
   root approval; the frozen Apple-specific wording is not silently rewritten.
3. **One fixed rendezvous.** Choose the nonblocking pipe plus `ALooper_addFd`
   endpoint below. It transfers a coalesced hint and one completion continuation;
   it carries no frame. This adds no per-document Swift Task, Handler Runnable,
   executor-job queue, timer or continuous display polling. Record the two owned
   pipe fds and one native registration in close/resource accounting.
4. **API floor and supported native surface.** Recommend a signed host with
   Android min API30, arm64 and the currently pinned official compiler/SDK/NDK;
   UI-v1 permits `accessibilityValue`, for which the existing native adapter needs
   API30. Preserve the compiled development profile's API28 behavior. An API28/29
   signed profile would need a separately specified rejection rule, never omitted
   accessibility semantics. First signed UI remains exactly guest-UI-v1's
   `vStack`, `text`, `button`, with `activate(null)` only.
5. **Lifecycle policy.** First slice uses one foreground Activity attachment:
   pause/detach synchronously revoke input/probe authority and request the existing
   coalesced close; resume/recreation opens a new runtime only after presentation
   retirement and the existing required concrete-retirement barrier. No replay of
   accepted input. State restoration, background execution and multiwindow support
   remain explicit later work. Persisted intent/uncertainty rules still apply.
6. **Public interop surface.** Keep the signed facade's current authority boundary:
   installed execution plus configuration, signed download operations, start,
   read-only presentation/diagnostics, recovery and close. A public screen factory
   accepts only that runtime's unforgeable presentation reference. The JNI methods
   below are private implementation entry points of the bound wrapper, not generic
   application/plugin callbacks or raw executable/document constructors.

These are proposed decisions, not new frozen constants. Do not ship placeholder
profile digests, relax marker checks, or advertise Android signed UI while the
platform stub is still reachable.

## Minimal portable and Android implementation boundary

Keep shared signed selection, download validation, runtime construction, fixed
guest turns, effects enable, health persistence and recovery in
`MixerCapabilityActivation`/the existing worker. Make the facade's common methods
compile on supported non-Apple targets. Keep conditional presentation construction
and the existing Apple accessor; Android exposes an observational state snapshot
without pretending that `ObservableObject`/SwiftUI is available.

Use a private Android `CapabilityGuestUIPresentationBinding` with the same
`bind(exchange) -> Task<Void, Never>` lifetime seam. Its model owns a fresh portable
`UIReconciler` for each exchange binding, current `UIRenderSnapshot`, current opaque
presentation ticket and one attachment identity. None is publicly mutable. Its
platform adapter uses no `AndroidDocumentSession` reducer, arbitrary closure,
caller-selected export or alternate event queue. Use the existing
`CapabilityColdStartObservation.finish()` task join; there is no second activation
coordinator or health consumer.

The installed native host initializes its Looper anchor on the Java main thread,
checks `Looper.myLooper() == Looper.getMainLooper()`, obtains the same thread's
`ALooper_forThread()` and rejects a missing Looper. A process-lifetime native Looper
reference may be shared. Runtime open acquires the existing outer reservation
before allocating its binding/model/endpoint; Android construction must not await
an unintegrated Swift MainActor. Each presentation has at most one endpoint and each
attempt has at most one active native attachment. The endpoint is ready before
`start` can bind/publish an attempt. Duplicate attachment fails before allocating a
second renderer, probe, pipe or consumer. A detached model may retire through its
existing endpoint but cannot offer input or observe health.

The internal ABI is additive and separate from `mixer_android.h`. Freeze concrete
names, integer statuses and complete C/JNI ownership rules with the new profile.
The intended operations are:

| Operation | Exact admitted authority |
| --- | --- |
| `attach(presentationRef, privateScreen)` | On main Looper only; resolve a native-issued positive, never-reused reference to the read-only presentation. Issue a fresh screen attachment. The Java root is a weak global reference, promoted only inside a synchronous UI helper. |
| `activate(inputBindingRef, revisionBits, nodeIDBytes, nodeGenerationBits)` | Private button path only. The input reference is newly issued for the exact exchange issuer plus screen attachment, and invalidated on binding change. `jlong` values carry full UInt64 bits; node ID is 1..128 exact UTF8 bytes copied through region APIs. No action ID, event name, export, capability, value or callback argument. Form `UIEventEnvelope(..., .activate, .null)` internally and pass it to that saved exchange's `offer`. Return a closed local enum: accepted, busy, stale, closed, invalid. |
| `detach(attachment)` | Invalidate its probe and input synchronously on main Looper, clear native listeners/views, revoke the table entry and request coalesced stop. It never equates UI detach with native exit or durable health. |
| private `apply(packet, attachment, inputBindingRef, frameSerial)` | Fixed native-to-Java method on the known wrapper class, reached only by the sole helper. No caller-provided method/class name. Listeners capture this input reference; an existing reference-table entry is never retargeted to a new exchange. Return success only after strict decode, native reconciliation and root attachment complete synchronously; input remains disabled until the native postcheck. |
| private display probe notification | Carries attachment plus a native-issued probe serial, not a boolean or caller-constructed receipt. Its private native table holds the opaque ticket/issuer; the wrapper's real layout/draw checks and exchange live-ticket recheck are both required. |

These operations are not exported guest imports. Native reference-table capacity
must be no larger than existing admitted runtime/presentation owners, acquire a
permit before capture/allocation, reject exhaustion/wrap, and remain counted until
actual close. Never cast a Swift object or guest pointer to a `jlong` handle.

## Delivery, native reconciliation and lifetime

The sole counted presentation Task retains only the delivery reader, a weak model
box and the data-only endpoint while parked. It consumes `deliveryWake`; after a
hint, it requests one native drain and awaits that fixed rendezvous. The endpoint
has one pending bit, at most one waiter and a fixed callback registration. It must
not retain model, runtime, worker, session, Java Activity or arbitrary callback.
Setting its bit writes at most one byte to the nonblocking pipe; repeated hints
coalesce. Handle EINTR, EAGAIN, broken pipe and register failure explicitly.

The main-Looper fd callback resolves the weak model/root only for a synchronous
helper. The helper claims at most one presentation, applies a frame, completes
against the **same** `UIRenderSnapshot`, consumes any event result, refreshes local
interaction state, and releases all strong locals before completing the
rendezvous. It never suspends and holds no exchange/endpoint lock over Java/JNI,
decode, reconciliation or continuation resumption. A hint during apply remains
pending for the next drain. A missing Java root earns no receipt; final stop still
retires the Swift model. The Task awaits its next delivery only after the helper
has released its frame/model/Java locals.

Serialize the snapshot into the existing packet shape (schema1 document plus
exact identity coverage). Preserve raw UTF8 identifiers and full UInt64 decimal
values. Signed decoding additionally enforces the guest subset/limits: original
guest document <=65,536 bytes, 256 nodes, depth16, 64 children and 4,096 UTF8 bytes
per string. The encoded native packet remains bounded by the existing 1MiB JNI
ceiling; that ceiling does not enlarge guest memory/document limits. Retain at most
one encoded packet during a helper, one Java candidate during apply and one current
Java packet; record these native representation bounds separately from the frozen
exchange's one pending/one claimed/one displayed/one worker snapshot slots.

Reuse existing native widget/property mappings and identity reconciliation through
an internal signed construction path. Its listeners capture only the immutable
attachment/binding, revision, node ID and generation, not the whole packet or a
mutable Activity session field. Clear listeners on removed/detached Views. A busy
or lagging input refresh uses a native interaction overlay; it neither mutates the
guest document nor calls `requireSuccessor` with the same revision. Enabling is
`authored ancestor-enabled && attached && confirmed && live && no turn/event &&
displayed == latest`. Recheck in Swift even if Android displayed an enabled button.
Java's action map is never guest execution authority.

Validate the whole Java candidate before changing Views. Any unexpected JNI,
decoder, allocation or renderer failure retires the visible tree and records the
existing typed `presentation/presentationInvariant` through the shared exchange;
never show a partially successful/degraded screen. Preserve bridge failure details
and pre-/post-intent recovery classification. Zero from the guest event export
acknowledges delivery only; actual granted KV completion still arrives through the
existing capability completion wake and harvest-before-new-I/O path.

Close first latches shared stop, terminalizes accepted input, discards pending
frames and invalidates ticket/probe authority. It does not wait for Android to
stop effects admission. The fixed final drain retires native Views/listeners and
the model. The consumer remains counted until actual `Task.value` returns, including
its final rendezvous and retirement. The native endpoint has an explicit active
callback lease; remove/retire its registration and join callback quiescence before
freeing context, deleting weak JNI references, closing its fds or reusing the permit.
An early logical completion flag is insufficient. A stalled Looper or callback
keeps close/replacement pending. `ALooper_removeFd` alone is not a join: Android
documents a possible final already-signalled callback; use self-unregistration on
the final callback plus a retained registration tombstone/lease through its safe C
epilogue, and test a callback stalled after its helper has returned.

Never block the Java main thread waiting for Swift `close()`; it must service the
final drain. Activity callbacks revoke synchronously and hand close to the existing
single lifetime close owner. `cleanupPending` continues to describe actual native
exits independently of presentation retirement. Rebinding creates a new reconciler,
renderer binding and opaque attachment; an old listener cannot reconstruct input
against a new runtime whose node/revision happens to match.

## Native first-screen and manifest requirements

The private `MixerGuestScreen` Android wrapper owns one root/probe. On the same
current ticket, require resumed Activity, non-finishing/non-destroyed lifecycle,
attached visible window/root, window focus, `isShown`, completed nonempty native
layout and a nonempty visible intersection. A root update, Activity creation,
native apply return, `onResume`, offscreen Canvas or JVM fake never earns health.

Observe the actual root's child drawing completion with an owned `dispatchDraw`
override after `super.dispatchDraw`; record data only there. The fixed weak probe
then waits across a subsequent Choreographer display interval, with at most one
pending `FrameCallback` object, and rechecks lifecycle, visibility, attachment,
revision/frame and stop before its private notification. Revision replacement,
detach, pause or stop invalidate the old probe. Do not use `OnDrawListener` as an
after-draw receipt or remove listeners from its draw callback. The native callback
still must pass `exchange.observePresentation` using the saved private ticket.
One pending receipt survives newer same-attempt revisions while the coordinator is
busy; stop/replacement discard it. The current worker records `first_screen`, and
the full observation interval/all milestones still govern `commitHealth`.

This establishes native layout/draw/display-cycle observation only. Screenshot,
native button action, accessibility hierarchy and eventually physical evidence are
separate qualification. Neither a Choreographer callback nor a receipt is
compositor, pixel or human-perception proof.

Release/installed/build rejection must be explicit:

- Require the complete frozen guest UI dependency/header/startup triple, ABI2,
  identity2, release3, exact Android native profile dependency and exactly installed
  milestones `{feature_started, first_screen}`. Keep ordinary signed artifact,
  assignment, target, runtime fingerprint, grants and replay checks.
- Bind the actual Android native source/archive/JNI/class closure and official
  toolchain in provenance. Compile the fixed UI VM symbols and real activation
  dependencies into the final shared library; no stub module-only success.
- Compile only the installed capability adapters actually supported by this host.
  Missing Android adapters, unsupported UI operations/resources/navigation,
  mismatched limits, unknown required features, insufficient API/ABI or an absent
  Looper reject. No generic Java lookup, arbitrary native capability callback,
  silent text fallback or placeholder UI.
- The signed sample's AndroidManifest must name the signed Activity/entry, state
  its approved min/target API and use an app-private durable directory. Any HTTP
  transport requires installed INTERNET permission and the existing ordinary
  trust/TLS policy; guests cannot add Android permissions by manifest metadata.
  An offline KV-only fixture needs no unnecessary network permission.
- Keep the existing CLI capability/resource guards until an explicit signed host
  source closure and installed adapter policy replace them with tested support.
  Never auto-select a signed host from a method name or source regex. The new path
  must verify app-owned manifest/entry/source hashes, not silently regenerate edits.

## Bounded implementation lanes after freeze

The smallest first implementation is a **standalone signed Android fixture**, not
a generator migration. Give it `native/android/signed-guest-ui/` for its explicit
Activity/manifest/app-owned Swift entry, build script and integration tests. Link
the same owned SDK/runtime/activation packages directly for development. This is
separate from `cli`'s generated consumer, published packages and FieldLog gates.
Do not change the existing compiled checklist Activity, `mixer_android.h` ABI,
generator snapshot or app-template entry in this first slice.

Root's minimal production file assignment would be:

- Edit `capability-activation/Package.swift`,
  `Sources/MixerCapabilityActivation/CapabilityGuestUIRuntime.swift`,
  `CapabilityGuestUIPresentation.swift` and `CapabilityInstalledExecutionMode.swift`
  for platform split, known native profile and wiring. Keep worker/control task
  joins unchanged unless executable evidence demonstrates a missing native lease.
- Add `capability-activation/Sources/MixerCapabilityActivation/CapabilityGuestUIAndroid.swift`
  for the read-only model, portable reconciler and fixed binding.
- Add `capability-activation/Sources/MixerCapabilityAndroidUI/{endpoint.c,rendezvous.c}`
  and `include/MixerCapabilityAndroidUI.h` for the bounded native endpoint. The
  Android implementation links only documented NDK APIs; host tests exercise the
  POSIX state core, not fake successful Android platform calls.
- Add `native/android/signed-guest-ui/{bridge,app,tests}` and its explicit build
  driver. Reuse existing owned `Json.java`/`UiPacket.java`/native widget mappings
  through a coordinated internal signed constructor and scalar listener binding;
  assign those exact shared Java edits to one lane. Avoid copying the compiled
  checklist reducer into the fixture.

Use the plan's requested fresh-context `gpt-6.1-sol`/`xhigh` agents. Root coordinates
contracts and shared-file integration; dependent lanes start only after their exact
seams are frozen.

| Lane | Exclusive ownership | Deliverable / blocking prerequisite |
| --- | --- | --- |
| Root / portable activation | New Android presentation contract; common facade/platform binding split; installed-mode policy; package wiring; coordinator/close changes only if needed; STATUS/work graph/gates | Freeze six decisions above and preserve all old frozen hashes. Keep existing Apple tests/consumer semantics. |
| Native rendezvous | New small C pipe/Looper endpoint and private header under a newly assigned Android interop target; POSIX host tests and Android JNI shell | One data-only hint/waiter, weak references, checked registration, failure paths and actual callback retirement. Must not edit root activation files or existing JNI entry file without coordination. |
| Android presentation | New Android private binding/model and signed wrapper/probe; coordinated internal NativeRenderer/UiPacket changes; pure packet/probe tests | UIReconciler + exact exchange, scalar listeners, interaction overlay, main-Looper helper, real layout/draw probe. Depends on frozen root/native signatures. |
| Integration / qualification | Explicit app-owned signed Android fixture entry/build driver, host/JNI harness, source manifests and evidence; CLI snapshot/entry only after root assignment | Actual signed download -> native VM -> widget packet -> native activate -> KV completion -> replacement -> observed health. Separate host evidence from Android execution. Root owns commits/pushes and CI review. |

## Executable acceptance plan, with devices excluded

Each run records argv, tool versions, exact revision/selected source manifest,
native archive/link inputs, exit/output, scope and accountable reviewer. No code
scanner or keyword count substitutes for execution or release eligibility.

| Check | Required assertions / honest boundary |
| --- | --- |
| Portable Swift Debug, Release and TSan suites | Existing SDK exchange/wake and signed activation tests continue passing. Add Android model-core tests with internal test-only native executor: valid signed selection and strict marker negatives; frame exactness; fresh reconciler; stale issuer/binding/node; one event through result consumption; no wrap or replay; event vs wake ordering; before-/after-intent failure and uncertainty. These run on Mac, not Android widgets. |
| Native POSIX endpoint host executable | Flood/coalesce hints, single waiter, no frame capture, EINTR/EAGAIN/broken pipe, duplicate registration, close before/while/after drain, model/root disappearance, stalled helper and callback tail. Assert max live task1, waiter1, active helper1 and fixed fd/registration counts; capacity is not reused while any retirement tail is held. |
| Pure Java/JVM contract executable | Existing raw decoder tests plus signed-subset/UInt64/UTF8/identity coverage, duplicate escaped keys, limits and input overlay/probe state transitions. No Android `android.jar` stub method may be treated as renderer execution. |
| Owned host JNI library + JVM executable | Use real JDK JNI region/weak-ref/exception APIs with fixed test entry points; force missing root, pending exception, allocation/output failure, stale and foreign handles. Verify full unsigned revision/generation bit round trips and local-ref release. Test-only loop/render drivers do not qualify Android Looper/widgets. |
| Official Android Swift/NDK link | Reuse installed exact `aarch64-unknown-linux-android28` SDK and matching Swift6.3.3; compile complete Android signed facade/binding, native VM archive, Swift Crypto/updates/activation dependencies and JNI. NDK `-Wall -Wextra -Werror`, `-landroid`, linked symbol/DT_NEEDED/ELF alignment inspection. Fail missing link closure; never download a replacement graph/toolchain. SDK triple28 can compile a minAPI30 app, but the APK/profile must state the approved runtime floor. |
| Java/D8/APK inspection | Official javac Java17 bytecode against pinned Android SDK, D8, aapt2 and zipalign. Inspect the actual unsigned signed-host APK manifest/classes/native dependency closure/hash; compare immutable inputs before/after. Build-only APK is neither signature validation nor installed UI/runtime evidence. Local production keys never enter this lane. |
| Independent signed end-to-end host fixture | Existing privately generated standard test keys sign real release/assignment bytes; no public document/artifact/milestone injection. Execute independently authored bytecode startup, actual button event, granted KV operation and actual ready wake. Assert display receipt absent without native observation; a test-only probe validates store plumbing only. Preserve effects-disabled startup and full observation timing. |
| Android emulator / physical native fixture | **Pending; not executed while devices are disconnected.** Eventually run the linked APK's actual native button/logic/KV/display flow, detached/background/rotation/process-death/error races, AX/screenshots, offline reopen and preserved-data recovery. Emulator and physical receipts remain distinct; neither host tests nor cross-linking satisfy this row. |
| FieldLog / product gates | **Pending.** Separate repository, immutable published packages, meaningful logic plus UI OTA, D2/D4/D5 receipts, independent security/recovery review, accessibility, memory/performance/16KiB-page/lifecycle/store/operational and accountable GA reviewer evidence. |

The current lane's `collect_baseline.py` observed 8 Swift host tests and 34 Java
wire checks passing, with selected source inputs unchanged during the run. It runs only the existing small
Android-engine Swift host suite and pure Java contract executable into this lane's
scratch directory. It inventories installed versions and hashes the inspected
source closure; it does not run `native/android/verify.py`, whose version inventory
still invokes adb even without `--device`. It builds no new signed runtime and
grants no Android pass. Generated scratch products are excluded from review.

## Official platform sources checked for this proposal

- [NDK Looper API](https://developer.android.com/ndk/reference/group/looper): fd
  registration and explicit late-callback hazard on removal underpin the bounded
  endpoint and its separate retirement lease.
- [Android View API](https://developer.android.com/reference/android/view/View):
  attachment, layout, visibility and window focus are necessary probe observations.
- [Choreographer.FrameCallback](https://developer.android.com/reference/android/view/Choreographer.FrameCallback):
  callbacks execute on the Choreographer's associated Looper and concern a display
  frame, rather than proving the pixels reached a person.
- [OnDrawListener](https://developer.android.com/reference/android/view/ViewTreeObserver.OnDrawListener):
  this callback precedes drawing and forbids view/listener mutation there; it is
  unsuitable as an after-draw acknowledgment.
- [JNI guidance](https://developer.android.com/ndk/guides/jni-tips): retain no
  thread-local JNIEnv across calls, promote weak global references before use, and
  check exceptions around region/fixed-method calls.
- [Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle):
  foreground, teardown and process recreation need distinct handling; this first
  profile closes on pause and makes no transparent restoration claim.

The pipe/Looper rendezvous and conservative probe sequence are design inferences
from these platform APIs, not already verified Android behavior in this repository.
