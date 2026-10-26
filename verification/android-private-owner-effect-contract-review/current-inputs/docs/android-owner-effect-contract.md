# Android owner effects: concrete prerequisite and integration boundary

**Proposal for root selection only. No implementation, compilation or runtime
acceptance is asserted by this packet.** The reviewed context is
`4e48ac1a3c1593d46c0dcbaf207053ff5e1b6d5d`. The accepted owner core is the exact
12,473-byte source with SHA-256
`4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6`.
Its [root acceptance](../verification/android-public-owner-core-root-review/implementation-acceptance.json)
accepts host ownership decisions; it explicitly leaves Android effect execution
pending. The current proposal's selected inputs, snapshots and source-only
command results are bound in
[the packet receipt](../verification/android-owner-effect-contract/receipt.json).

The recommended next implementation is **repair the actual
`NativeEnvironmentV2.Observer` listener lifecycle, together with the source-pair
migration that this mapped-source edit necessarily requires**. Land this before
the effect-runner bridge. It removes a concrete resource-ownership failure in the
component the bridge must use; another decision model would leave that failure
untouched. Root must select its exact new source profile and acceptance controls
before implementation. This proposal does not make that selection.

## Current evidence and the smallest coherent slice

| Exact current source | Consequence for the next implementation |
| --- | --- |
| `NativeEnvironmentV2.java:70–85` | Eight registration sites execute sequentially in the constructor without rollback. A later add can throw while earlier listeners remain registered; an add that throws after acquiring is also an uncertain owned registration. |
| `NativeEnvironmentV2.java:61–67,86–91` | Detach invalidates before setting `retired`; `invalidate()` has no retired guard. Delivered callbacks can reach the renderer after retirement. |
| `NativeEnvironmentV2.java:143–150` | Close stops at its first failure and looks up the current `ViewTreeObserver`, rather than retaining the registration target. |
| `NativeRenderer.java:93–101,354–360` | The renderer lazily creates the observer, invalidates gates and closes the observer on disposal. Cancellation can invoke native parent methods. This is actual code to repair and later integrate, not evidence that outer lifetime sealing exists. |
| `NativeCoordinatorV2.java:73–105,146–185,192–205` | Ordinary input stages/attaches/validates before scalar commit and renderer finish. Refresh reuses retained committed bytes without an engine call. `close()` requires a live, idle coordinator; the outer owner must never invoke it during an operation. |
| `MixerActivity.java:12–15` | Public Activity still uses V1 and owns its own inset-padding listener. Replacing it with the current observer setter would silently change ownership. |
| `AndroidSDKCompatibility.swift` and `AndroidProject.swift:31–57` | Profile 1 has a fixed 22 SDK / 20 adapter closure, including the observer. Export admission rejects changed pinned bytes. A direct repair without a selected new profile breaks that admission. |

Recommended slice A owns these future paths, subject to root selection:

- `native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java`: repair the
  existing observer in place. Keep one authoritative registration implementation;
  do not introduce a parallel listener state machine that production never uses.
- `native/android/tests/NativeEnvironmentV2ObserverHostTests.java` and
  `native/android/tests/NativeEnvironmentV2ObserverHostLeaves/`: a new bounded
  package-peer harness and independently authored Android/renderer leaf doubles.
  Freeze the exact leaf file list before execution. Compile the actual observer
  source, rather than a translated ownership algorithm. Leaf behavior supplies
  fault injection and cannot mint real captures or establish Android behavior.
- `native/android/tests/run-environment-observer-host.py`: explicit-source,
  bounded host runner with retained commands/streams and owned scratch cleanup.
- `cli/Sources/MixerBuild/AndroidSDKCompatibility.swift`: root-selected successor
  profile with a new ID and fixed file identities. Profile 1's historical binding
  and receipts remain immutable. The exact successor ID is deliberately unselected.
- `cli/build-tests/test_android_sdk_compatibility.py`: controls for the selected
  successor and rejection of old, edited or recomputed locks before tool/output
  access. Update other existing admission tests only if their assertions actually
  change; do not copy their policy maps.
- New slice-specific documentation and `verification/android-environment-observer-lifecycle/`;
  root coordinates `PLAN.md`, `STATUS.md`, `work-graph.json`, gate records and delivery.

The generated driver already receives the single compiled policy through
`AndroidSDKCompatibility.renderDriver`. Keep that one authority. Changes to
`AndroidProject.swift`, `ProjectGenerator.swift` or
`cli/Sources/MixerBuild/Resources/android-build.py` are needed only if the selected
migration contract exposes a real missing behavior; do not add a second profile
authority or an automatic lock-refresh path. Public `MixerActivity`, owner-core
behavior, JNI, Swift engine, descriptor/wire schemas and native support checks
are outside slice A. No new dependency is required.

## Slice A's concrete observer contract

All entries, including stale delivered callbacks and repeated close, enforce
the actual main-Looper check before examining observer state. Initialization
assigns every field needed by callbacks before the first registration. Use
fixed bounded slots for these eight registration sites:

| Slot | Acquisition target retained for removal |
| --- | --- |
| Component callbacks | The exact Activity and observer instance |
| Layout changes | The exact root and layout-listener instance |
| Attach changes | The exact root and attach-listener instance |
| Window focus | The exact `ViewTreeObserver` used by add, plus listener identity |
| Insets | The dedicated private V2 root and its single owned listener |
| Contrast | The exact `UiModeManager` and listener identity |
| High contrast | The exact `AccessibilityManager` and listener identity |
| Animator settings | The exact content resolver and content-observer identity |

Before calling each registration operation, record that the slot may be owned.
After a throwing add, removal of that slot must still be attempted. Do not infer
that a throw proves no acquisition. A failure marks the observer retired before
callbacks or cleanup, then attempts each possibly owned slot independently in
a deterministic order. Successful construction publishes only a completely
registered, nonterminal observer. Detach or terminal failure reentered during
registration must cause construction to unwind and cannot publish a live owner.

Every notification first checks retirement. A retired callback performs no tuple
read, generation change, renderer callback, refresh request or registration.
Detach and epoch exhaustion publish retirement **before** calling any renderer
invalidation or future lifecycle sink. Marking this observer terminal does not
yet establish the later outer owner/transaction fence. During registration,
notifications must not publish an incompletely registered observer; preserve
invalidation and synchronously close any existing gates before external work.
The current second synchronous environment read remains authoritative.

Close marks retirement first, consumes each owned slot before its removal call
and attempts all other slots despite a removal failure or reentrant callback.
Repeated close never retries consumed slots. Remove window focus from the stored
registration target when that target is still alive; do not substitute the
root's replacement observer. A dead target is recorded as such rather than
reported as a successful removal call. Removal diagnostics distinguish attempted,
returned, failed, dead-target and still-uncertain outcomes; they never claim
actual reclamation from a return value alone.

Preserve the original failure and bounded independent cleanup diagnostics.
An `Error` from acquisition, invalidation or cleanup must escape as an `Error`,
including when the primary failure was an ordinary `RuntimeException`. Attaching
diagnostics must not prevent remaining cleanup attempts. Exception suppression
is best effort under allocation failure. Unknown outcomes remain terminal;
there is no reopen/retry loop or catch that converts fatal failure into an
ordinary rejected edit.

Insets ownership in slice A is restricted to the existing **private dedicated
V2 root**, whose creator promises no competing inset-listener setter during the
observer lifetime. The observer cannot recover an arbitrary preexisting listener
from the current source. Slice A must document this restriction and test its
owned listener lifecycle; it must not claim general listener composition or
silently route the public V1 root through it. Before public integration, one
root owner must compose inset invalidation and the chosen padding policy, apply
safe area once, and retain sole setter ownership. No manifest configuration
opt-out is selected.

## Dependency order after the observer repair

1. **Root selects and accepts slice A.** Freeze its public/internal contracts,
   successor source-pair profile, host fault matrix and migration controls.
   Independent review must exercise the actual observer and inspect its native
   signature compilation. Native runtime checks remain pending during the pause.
2. **Root selects one private effect-runner integration slice B.** Add the real
   owner adapter and lifetime fences to the existing coordinator/renderer; keep
   public Activity routing pending. This depends on reliable listener acquisition
   and cleanup, not on claiming native runtime evidence that has not run.
3. **Resume native qualification when authorized.** Run the private lifecycle,
   setter, draw/IME, readiness and refresh matrix, then fix concrete differences.
4. **Select public routing separately.** API 28–35 environment/rendering support,
   current unsupported accessibility/resources/fonts, state continuity and public
   interaction behavior remain explicit blockers. A private owner or a newer
   source profile does not discharge them.

Slice B's proposed ownership is exact enough to constrain a later selection:

| Future owned path | Contract to coordinate before implementation |
| --- | --- |
| New `native/android/app/src/dev/mixer/android/NativeOwnerV2.java` | One Activity/root lifetime, main Handler drain adapter, synchronous ordinary input dispatch, concrete readiness probes, terminal latch and independent cancel/unregister/close results. Own no Swift state or packet copy. |
| Move `native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java` to `native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java` | Move the one canonical accepted implementation into the export closure; update its host runner source path. Do not maintain copied authoritative implementations. Core behavior changes require their own review. |
| `NativeEnvironmentV2.java` | The same concrete observer registers before initial opening and supplies readiness notifications plus real captures. Bind capture authority once to the acquired renderer. Introduce one package-private typed invalidation/terminal sink; no second readiness listener set and no caller-created capture authority. |
| `NativeCoordinatorV2.java` | Accept the registered concrete observer and a shared terminal state; remain the sole session/committed-packet owner. Route initial/input/refresh decisions to its existing methods. Close only after the active operation returns; retain real cleanup attempt/failure information if internal retirement already occurred. |
| `NativeRenderer.java` | Accept the single externally owned observer; move unregister responsibility to the outer owner. Add scalar lifetime sealing, gate/input and candidate/precommit checks. Preserve renderer retirement and all concrete capture/current-record checks. |
| `NativeAppearanceViewsV2.java` | Only if needed to enforce actual draw/touch/key/IME/accessibility terminal gating and safe toggle cancellation. Existing authority checks remain mandatory. |
| `native/android/tests/NativeOwnerV2HostTests.java`, `native/android/tests/NativeOwnerV2HostLeaves/`, new bounded host runner; existing private integration Activity/instrumentation | Test the actual new owner with faulting leaves, then cross-compile the real Android sources. Author native cases now; execute them only after the pause is lifted. |
| `AndroidSDKCompatibility.swift` and relevant admission tests | A further explicitly selected source-profile migration for added/moved/edited mapped sources. Slice A's profile cannot be refreshed silently either. |

The sink and capture binding above are proposed internal contracts, not newly
available APIs. Slice B must retire/replace the old renderer-owned observer path
as one coherent change. It must not retain both disposal owners or add a second
authoritative source implementation. No public Swift API, C/JNI symbol, packet
field, descriptor field or stable binary ABI is selected by this proposal.

## Effect-runner rules that slice B must prove

**Terminal sealing is immediate.** On a terminal native callback, publish the
outer terminal latch and close actual current and pending draw/input gate flags
before running callbacks, cancellation, core decisions or cleanup. Do not depend
on a later operation-completion check. Split scalar sealing from cancellation
that can call native parent methods. If detach or close reenters a native setter,
the remaining attach/precommit path must observe the terminal latch and abort or
retire before engine commit. Dirty invalidation also seals input synchronously,
while preserving the renderer's independent environment checks.

Use a trusted shared terminal-state object/direct field for scalar fence reads.
`OwnerLifecycleV2.permits()` is a terminal operation fence only; its injected
thread checker is not a concrete environment check. Never insert a call through
that checker, an arbitrary predicate or a sink between engine commit and
renderer finish. Preserve the current no-callback/no-capture/no-allocation/no-
native-mutation interval at `NativeCoordinatorV2.java:100–104`. Complete the core
operation and publish its new presentation token only after finish returns.
Unknown commit/attachment outcomes remain terminal and do not trigger retries.

**One drain, no input replay.** Queue exactly the drain identity issued by the
core on the main Handler. Reprobe the actual Activity/root/window/size/insets on
delivery. Cancellation targets the owned runnable; ineffective cancellation is
still fenced by lifetime and drain identities. Do not poll unavailable geometry.
Native input must pass both core admission and existing renderer/native checks,
receive an operation token and finish synchronously. Never buffer rejected native
events or bypass the core by retaining the current coordinator callback route.

**Refresh retains ordinary state.** `REFRESH_COMMITTED` invokes the coordinator's
`refreshEnvironment()` with exactly its retained packet. It must not create a
session, call exchange/prepare/commit/dispatch, advance Swift revision, run an
effect or manufacture input. A newer invalidation during refresh remains dirty
and gets one later drain. Concrete captures and native validation can reject an
operation even when the core still permits it.

**Disposal follows completion.** Terminal state does not call nonreentrant
coordinator `close()` inside an active operation. Cancellation and unregister
may finish independently; close is issued once when the matching operation
returns. A late acquired coordinator is never published and receives its one
terminal disposition. If the coordinator already internally retired, report
its recorded actual cleanup attempts/failures rather than invoking a second
close or inferring reclamation. If an operation never returns, its deferred
close remains pending. A completion report never proves actual resource release.
Fatal `Error` values escape after best-effort independent cleanup.

## Executable acceptance plan; nothing in this section has run

For slice A, compile exactly the production observer, independently authored
host harness and a closed list of faulting leaf doubles with the installed
official JDK: `javac --release 17 -Xlint:all -Werror -proc:none`, empty classpath/
sourcepath and stripped implicit JVM option/classpath variables. Then run the
package-peer harness with assertions enabled. The selected runner must freeze
sources/tools/argv/streams/classes and reap bounded owned children, removing
only its own scratch. No Android stubs may be reported as native evidence.

The finite host matrix must cover every registration slot failing both before
and after acquisition; the successful prefix and uncertain failing slot all
receive cleanup attempts; every removal failure independently and combined;
reentrant detach/close during add/removal; retired delivered callbacks; generation
exhaustion; wrong-thread calls before stale guards; repeated close; stored versus
replacement/dead window-observer identities; and fatal `Error` during acquisition,
renderer invalidation and each cleanup position. Assert actual fake add/remove
call order and callback counts, not an expected decision-log copy. Include a
successful registration/capture/close control and no reopen after any failure.

For source/profile acceptance, execute the actual Swift CLI and rendered driver
against fresh created/copied projects under the selected successor profile.
Verify fixed source maps and descriptor identities, ordinary app-owned Swift
factory/reducer behavior, rejection of profile-1 locks without migration and
rejection after edits even when generic tree digests are recomputed. Preserve
preaccess controls: rejection before tool discovery, source hashing outside the
admitted closure, or build-output creation. Do not self-refresh stale locks.

Cross-compilation follows host controls: compile the complete actual adapter
against the pinned installed Android SDK jar using the existing Java 17 policy;
run D8 with `--min-api 28`; build the ordinary app-owned Swift/JNI target with the
selected official Swift Android SDK/NDK in fresh owned output. Use the generated
driver's admitted project path, not the repository checklist engine as a stand-in.
Capture exact tool versions/binary hashes, SDK/NDK identities, source/profile/tree
digests, complete argv/streams, class/DEX/ELF output identities and cleanup. Avoid
`native/android/build.py` for this acceptance path: its top-level execution uses
shared build directories and creates a debug signing key if absent. Compile-only
evidence does not require changing credentials or publishing/signing a release.

Slice B adds actual owner/core/coordinator ordering tests with a manually drained
queue and faulting native leaves: close/detach during opening, each attachment
setter and input/refresh; stale/duplicate/foreign drain/completion; late acquisition;
no reentrant close; never-returning operation pending cleanup; terminal gate state
before cancellation callbacks; no engine calls/revision change on exact-packet
refresh; dirty epoch during every operation; fatal cleanup errors; and proof that
no callback/capture/allocation hook appears in the successful commit/finish gap.
The real concrete candidate/capture checks remain separately required. These
host controls are prerequisites for runtime work, not substitutes for it.

When runtime use is authorized again, the pending Android matrix includes actual
main-Looper identity; partial platform registration/removal; delivered callbacks
after retirement; root attachment/window-token loss/replacement; zero geometry
and delayed insets; detach/close reentered by native setters before commit; draw,
touch, key, accessibility and stale IME suppression; fresh tuple refresh with the
same Swift revision; pause/stop/resume/focus; configuration recreation; and actual
cleanup behavior. Respect one active owned instance and retained cleanup receipts.
Final physical-phone lifecycle/performance and device/OS/accessibility coverage
remain pending. No instance/process inventory or runtime probe is needed now.

## Unchanged product limits and evidence boundary

Product section 19.1 still proposes Android API 28+ subject to qualification.
Private V2 rejects API below 36, high contrast, nondefault weight, declared
resources and bundled fonts. Keep every rejection until actual supported
behavior is implemented and qualified. Neither a host pass, API 37 compilation
nor D8 `--min-api 28` establishes API 28–35 support or selects public V2.
Activity recreation still loses process-local ordinary value state; the owner
must retire the old lifetime and cannot transfer native records, captures,
queued input or a coordinator to the new root. Saved-state continuity needs its
own explicit contract.

No native/compiler/signing/store/customer/operational or GA gate is passed here.
No OTA eligibility or release authority follows from this proposal. Immutable
published packages consumed by FieldLog from a separate repository, final phones
and accountable GA review remain pending. The active computer-use/capture/native
runtime pause is preserved. Official platform links in the prior
[owner contract](android-public-owner-contract.md#official-platform-basis) are historical
specification inputs; this source-only proposal fetched no new platform facts.
