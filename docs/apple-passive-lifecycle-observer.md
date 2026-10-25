# Passive iOS lifecycle observer: source and host prerequisite

This packet implements the single passive diagnostic proposed by the accepted
[lifecycle diagnosis](apple-reference-focus-lifecycle-diagnosis.md), on an owned
copy of its exact accepted source archive. It supplies source and finite macOS
Foundation tests. UIKit compilation, generic simulator builds and native execution
are **pending and unselected**. No live SDK, harness, tracker, provider, dependency
or Git state is changed by this lane.

The historical V8 result remains **Settings Passed / first Tab Failed**, Xcode
exit **65**. Stable observed window/scene association already contradicts the
missing-association explanation at those samples. Event ownership and the cause
of focus-system turnover remain unknown. This supplementary observer cannot
change that verdict, supply an original anchor, infer success, or qualify a GA
gate. Phones remain disconnected and deferred.

## Immutable inputs and candidate

[Input bindings](../verification/apple-passive-lifecycle-observer/input-bindings.json)
bind actual immutable evidence rather than mutable PLAN/STATUS text. The source
context is root-reported revision `6b8aba350224ed19f678669bdbea6b359d8de68b`.

| Input | SHA-256 |
| --- | --- |
| Accepted diagnosis handoff | `0e54a5c61dbefe9908b53c1f1a5d96440187b3d9cd561395337e7a89f4896452` |
| Accepted forty-member source archive | `d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda` |
| Exact V8 result handoff | `0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de` |
| New forty-two-member candidate archive | `042c47cc39166ad25e475a5f213815e2aab926590a520e3eb51e0e04cd97774e` |

The [source manifest](../verification/apple-passive-lifecycle-observer/source-manifest.json)
and [minimal patch](../verification/apple-passive-lifecycle-observer/source.patch)
show one changed existing member, `accepted/source/Prototype/main.swift`, and
two added members, `PassiveLifecycleData.swift` and `PassiveLifecycleObserver.swift`
in the same Prototype directory. The other **thirty-nine** members are byte-exact,
including all `DiagnosticTrace.swift`, original focus-system diagnostics, harness,
oracle, actions, runtime helpers and transport guards.

The controller owns the new observer. Launch registers it after assigning the
root controller and before the original `makeKeyAndVisible`. The existing weak
focus-sample callback calls it after the original focus-system capture. Original
persistence adds only `passiveLifecycleDiagnostic`; all original fields and
serialization options remain. The original timers, public Settings and single
Tab, 29-second Settings allowance, 2-second per-request allowance and anchored
3-second observation remain exact source contracts. The new work adds no poll,
timer, sleep, focus request, activation, scene migration, delegate handler, input
or custom key path. Added processing necessarily changes timing overhead; no
new-run byte identity or unchanged runtime behavior is claimed.

## Closed passive data and ownership

The [contract](../verification/apple-passive-lifecycle-observer/contract.json)
specifies five closed capture sites, fourteen notification kinds, app/scene state
enums, and thirteen fixed columns. The envelope names row schema
`mixer.apple-toggle.passive-lifecycle-row.1`. Every `entries` row has exactly the
`columns` array's thirteen positions: sequence; start/finish uptime; process ID;
site; nullable existing context sequence; nullable notification kind/object
identity; application state; owned window identity/key state; current owned scene
identity/activation state. Identifiers are actual object addresses encoded as
lowercase `0x` hex, without repeating the `ObjectIdentifier(...)` wrapper.
They remain supplementary and never supply original identities or anchors.

The observer captures sequential main-actor state and declares both
`authoritative: false` and `atomic: false`. Finite ordered start/finish uptime
checks reject nonfinite, negative, reversed or overlapping snapshots. Initial
scene absence is explicit at that sample. Later samples read the actual current
`window.windowScene`; initial absence says nothing about later association.
Unknown future UIKit state values are retained explicitly and mark incomplete
data. Missing app/window ownership after registration stops capture and advertises zero tokens. A sample before launch registration records an explicit registration gap while preserving the later registration opportunity.

App/window references are weak, and notification closures capture the observer
weakly. The bounded fourteen-token bag unregisters on removal/deinit. No controller,
application, window or scene is retained by a notification closure after existing
ownership ends. Temporary strong references cover only synchronous filtering and
snapshot reads. Off-main delivery increments a locked bounded fault counter,
marks the exported trace incomplete, and never queues a delayed snapshot.

Every event requires exact identity: the supplied current `UIApplication`, the
owned actual window, or that window's current scene. Other and nil objects are
filtered; no other app/window/scene is enumerated. Apple documents the affected
window as notification object for the four selected window transitions, and the
affected scene for connect/disconnect/activation/deactivation/foreground. The
app foreground/background pages specify `UIApplication` as object. The pinned
active/inactive and scene-background pages omit object wording; this code applies
the same conservative identity filter and makes no completeness claim for
unproven object conventions. See the pinned
[official notes](../verification/apple-passive-lifecycle-observer/official-contract-notes.json),
[Apple window notification contract](https://developer.apple.com/documentation/uikit/uiwindow/didbecomekeynotification),
[app foreground contract](https://developer.apple.com/documentation/uikit/uiapplication/willenterforegroundnotification)
and [scene activation contract](https://developer.apple.com/documentation/uikit/uiscene/didactivatenotification).

The hard ceilings are **64 rows** and **16,384 encoded bytes**, including the
entire supplementary field wrapper, envelope, status, issues and counters under
the original pretty/sorted JSON options and nesting. Before retaining each row,
the actual shared serializer reserves all issue names, the longest registration
status and every maximum bounded counter. Counts saturate at 2,147,483,647.
Refused rows do not grow stored data. `dropped`, `truncated`, issues and registration
status remain truthful as counters grow. Serialization failure only refuses a
diagnostic row; it does not trap or alter the original application result.

Capacity depends on values. The measured worst named scene-notification test
retains **56 rows**, then reports byte truncation; a shorter absent-scene workload
reaches the production 64-row ceiling. No guarantee of 64-row retention or full
Tab-interval coverage follows. The readable-row predecessor retained 25 rows;
its exact archive, test source and 109-check receipt remain historical under
`history/`. Intermediate compact 114-check and 115-check results are also preserved. Any
registration, state, scope, delivery, timing or capacity gap must remain explicit
in a future native result; it cannot establish a cause or authorize a retry.

## Executable host evidence and next build boundary

The finite host test compiles the exact archive member
`PassiveLifecycleData.swift`, with the lane's `HostTests.swift`, using pinned
Xcode 26.6 Apple Swift **6.3.3**, arm64 macOS target **26.0**, and its macOS SDK.
It executes **116 checks** on that shared code: production and reduced-only row
limits; production byte refusal; saturating counters; registration/stopped/unknown
state; strict closed metadata/time validity; fixed row schema/arity/types; every
event identity filter; weak app/window ownership; bounded token insertion/removal
and deinit; concurrent delivery-fault accounting; and original V8 packet retention
after adding/removing only the supplementary field. The byte-growth test remains
under the cap after 2,000 further refusals and maximum off-main count export.

This is Foundation behavior on macOS and source consistency. It is not UIKit
notification execution, actor/concurrency acceptance of the UIKit adapter,
native lifecycle timing, focus traversal, signing, store, physical-device,
FieldLog or product/OS qualification. Host compilation emitted only two weak
probe mutability warnings in test code. The source archive and command receipts
record exact sources, tool output, commands, output hashes and limitations.

Root's next separate generic-build selection must compile the full candidate
Prototype closure, **all twelve Swift files**, explicitly including both new
helpers. The prior explicit source list is incomplete. The unchanged harness has
four Swift members; there are **37 Swift members overall** in this archive. The
existing minimum-iOS 26.0 packaging derivation still needs to be applied and
recorded in a future build receipt; the source Info.plist remains byte-exact.
No build, install, simulator selection, device query, native run or retry has
occurred here. Owned source and host-build scratch are removed; no simulator or
other project's process was touched. Frozen hosted lanes and the frozen V7
supplemental join were neither imported nor executed.

Re-run the sealed read-only consistency verifier without writing files:

```sh
python3 -B verification/apple-passive-lifecycle-observer/audit.py
```

The handoff seals this report, contracts, source package, patch, input/official
bindings, producer scripts and host evidence. Its source-shape checks document
changes and exclusions; they do not authorize an OTA release or prove native
correctness. Future compilation and runtime remain root-selected prerequisites.
