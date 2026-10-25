# Plain-reference focus lifecycle diagnosis

The V8 originals establish focus loss from the plain UIKit reference, but do not
establish its cause. A missing scene association is **not supported**: the same
non-null window and scene identities are observed before loss, at all three new
controller callbacks, and in both unavailable-focus-system snapshots. The minimum
missing observable is whether that window remained key and its scene/application
remained active during the returned Tab interval. No corrective lifecycle patch is
selected by this report.

The result remains **Settings Passed / first Tab Failed**, Xcode exit **65**, zero
skips. `actualNativeFocusTraversal` is the only failed original predicate; the
other nineteen are true. The five recorded cleanup checks pass, the one owned
simulator was deleted, and four baseline simulator states were preserved. This
investigation runs no native process, imports no upstream code, and performs no
Git, device, UI, or service operation. Phones remain disconnected and deferred.

## Exact evidence and source

The [input bindings](../verification/apple-reference-focus-lifecycle-diagnosis/input-bindings.json)
pin eighteen existing files without copying the native tree. In particular:

| Input | SHA-256 |
| --- | --- |
| Root-selected originals | `1cee9899bcbd1739787a6ba991a82e6e1fb924f3225420640a82f2d4040ae8f3` |
| Ten-member V8 result handoff | `0d4ff885c95e54386cd06e53794077defa7acac5cf63525583a8053f053c90de` |
| Authoritative forty-member source archive | `d1262c1e16a4decdca0ecbfdc278b7eaa1282f47d68776bfdede235157019cda` |
| Fresh compile-source archive | `3cfd2e83369b566a48cc50f263ff879bc7da2c7b49cb0a836980da7c5b39cdc1` |
| Fresh product archive | `681059d32edbd63128c8f4552af2ed161d6dce05847397ffa6ce57b5402364d9` |

All forty reviewed source members match the compile-source archive byte for byte
after removing the archive's `accepted/` prefix. The source tree bound by the
native result is `ddd4036d785c1c5f0161f8146ee7295b8df8dcd2bd615b45eebefc4112fcfb0d`.
Revision `6403eea98031207f6e40a72b55dfd3bd4e7e6ec2` is the root-reported V8
context. The later root-reported integration commit
`6b8aba350224ed19f678669bdbea6b359d8de68b` does not change these source inputs.
Mutable PLAN/STATUS are context only and are not rebound by this packet.

Run `d9a1ae2b-ef02-4db2-b2ff-4979213c8236` used arm64 iOS 26.5 simulator build
23F77, Xcode 26.6 / SDK 26.5, with built-app minimum iOS 26.0. Source `Info.plist`
still says 17.0; the built product's actual minimum is 26.0. Neither a host-only
analysis nor this private simulator result qualifies the full product/OS matrix,
FieldLog consumption, physical devices, store operation, or a GA gate.

## Lifecycle and input path

The [derived analysis](../verification/apple-reference-focus-lifecycle-diagnosis/analysis.json)
contains exact archive-member hashes, numbered source slices, product plist
fields, original JSON pointers and a numbered official-log slice.

| Boundary | Selected source / product | Evidence and implication |
| --- | --- | --- |
| App window | `source/Prototype/main.swift:292–299` | `PrototypeDelegate` creates `UIWindow(frame:)`, sets one `PrototypeController`, calls `makeKeyAndVisible`, and retains the window. It has no app activation/background handlers or scene delegate. |
| Scene configuration | Source and built `Info.plist` | Both lack `UIApplicationSceneManifest`; the built app uses the legacy delegate path. Actual samples nevertheless have a stable `windowScene`, so absent manifest and absent association are different claims. |
| Runner | Built `MixerToggleUITests-Runner.app/Info.plist` | The separate Apple runner has its own scene manifest and `_XCTRunnerAppDelegate`. Its lifecycle is not the diagnostic app's lifecycle. |
| Initial preference | `main.swift:285–289` | `didUpdateFocus` calls `super` and records. `preferredFocusEnvironments` returns only the reference button. This can explain initial/default preference; it does not specify the next Tab target. |
| App launch | `harness/UITests/ToggleUITests.swift:333–341` | `launchCase` terminates/launches the diagnostic app, waits for foreground, then issues `resume` and `reset`. This selected case does not issue the available `focus` command. |
| Public key | Harness `:394–423`, `:471–474` | The precondition requires the reference's AX focus; exactly one unmodified public `typeKey(Tab, [])` follows. There is no explicit activation, relaunch, or focus command around it. |
| App code while key returns | `main.swift:97–103`, `:256–283` | The 30-ms timer reads commands and persists changed trace state. The selected stage stays `reset`. No custom key/press handler or focus veto appears in the Swift files within the forty-member source archive; this is source-inspection scope, not proof of platform internals. |

The official log's selected case launches once, reaches foreground, verifies the
reference precondition, synthesizes one Tab, and waits for app idle. It records no
explicit second launch or activate call around that key. The public witness says
foreground before and after, but these two observations do not cover the key
interval. The pinned `XCUIApplication` header explicitly describes app-state
updates as asynchronous.

Apple documents `makeKeyAndVisible` as establishing key status at the call and
`isKeyWindow` as the property that reports it; the key window receives keyboard
events. A one-time launch call therefore cannot prove continuing key ownership.
[UIWindow](https://developer.apple.com/documentation/UIKit/UIWindow),
[isKeyWindow](https://developer.apple.com/documentation/uikit/uiwindow/iskeywindow)

Apple's preferred-focus contract searches for the default focused item. Its
heading-none constant supplies no movement heading. Neither the fixed preferred
reference nor heading zero proves that the three callbacks were Tab traversal or
app deactivation. The source contains no evidence-supported focus-veto fix.
[Preferred focus environments](https://developer.apple.com/documentation/uikit/uifocusenvironment/preferredfocusenvironments),
[Heading none](https://developer.apple.com/documentation/uikit/uifocusheading/uifocusheadingnone)

## What the originals discriminate

The exact key interval is uptime **954929.2324480833–954929.5392350417**. The
following rows come from after-original
`/observation/focusSystemDiagnostic/entries/26` through `/31`:

| Entry / time | Focus-system sample |
| --- | --- |
| 26 / 954925.7868055417 | Original system present, reference focused. This app snapshot precedes the later AX precondition. |
| 27 / 954929.3275228334 | Controller callback 2: original system present, focused item null. |
| 28 / 954929.3421207084 | Focus system unavailable; all three controls unfocused. |
| 29 / 954929.5350779584 | Controller callback 3: different system identity, same reference focused. |
| 30 / 954929.5372237917 | Controller callback 4: replacement system present, focused item null. |
| 31 / 954929.5522026668 | Focus system unavailable again, after the key returned. |

Across all six samples the window, scene, and three control identities are
unchanged; each control remains attached to that same window and reports
`canBecomeFocused: true`. The three appended focus contexts are reference → null,
null → reference, reference → null, all heading zero and all timed inside the
returned key interval. This supports examining focus-system availability at the
input/lifecycle boundary; it does not identify the cause of its turnover.

The pinned `UIFocusSystem` header allows a nil lookup when focus interaction is
unsupported or the environment has no focus system. Apple likewise makes scene
focus-system availability conditional on focus support. A nil system does not
prove a missing scene, inactive app, or key-window loss.
[Scene focus system](https://developer.apple.com/documentation/uikit/uiwindowscene/focussystem)

The current supplemental observer records identity, focus state and attachment,
but not `applicationState`, `isKeyWindow`, `scene.activationState`, or lifecycle
notifications. It declares `authoritative: false` and `atomic: false`; sequential
field reads cannot establish atomic co-occurrence. The original app/AX agreement
and failure remain binding. The archived evidence cannot settle whether the app
lost event ownership transiently or focus support reset while its lifecycle
remained active. It does not justify changing the authored toggle or rewriting
the scene setup as a repair for this failure.

## One proposed next diagnostic experiment

Root may select **one** unchanged Settings-plus-first-Tab attempt with a passive,
bounded lifecycle observer. The [proposal](../verification/apple-reference-focus-lifecycle-diagnosis/experiment.json)
is data only; no source patch, compile, simulator selection, or execution has
occurred in this lane.

Install the observer at app launch before `makeKeyAndVisible`. At registration,
each lifecycle notification and each existing focus sample, record one main-actor
row with uptime/sequence, process identity, app state, the owned window's identity
and `isKeyWindow`, its scene identity and activation state. Observe only the
diagnostic app's app notifications and its owned window/scene notifications.
Cap at 64 rows and 16 KiB, retain a dropped/status field, and declare the packet
non-authoritative and non-atomic. Do not add polling, sleeps, focus requests,
window activation, scene migration, custom key handling, or substitute input.
Apple exposes these state transitions through scene notifications; foreground
inactive can remain onscreen while not receiving events.
[UIScene](https://developer.apple.com/documentation/uikit/uiscene),
[Foreground inactive](https://developer.apple.com/documentation/uikit/uiscene/activationstate-swift.enum/foregroundinactive)

| Observed outcome in that one attempt | Discrimination |
| --- | --- |
| An ordered resign-key / deactivate / resign-active transition accompanies the first loss, with state snapshots confirming it. | Supports transient loss of app/window event ownership. It still does not name who caused that transition. |
| The trace covers the key without drops; same window stays key, app active and scene foreground-active at every sampled loss/reacquisition; no corresponding lifecycle transition is observed. | Narrows the failure to focus-system/input support within the still-active app at observed points. Finite samples do not exclude every unobserved transient or prove an Apple defect. |
| Registration, timing, scope or size coverage is incomplete, or native traversal changes. | Report the exact incomplete/new outcome. Do not infer a cause or repeat automatically; the V8 failure remains historical. |

Keep the original oracle, first-reference precondition, public Settings actions,
single public Tab, 29-second Settings session, 2-second per-request allowance,
anchored 3-second switch observation, transport limits, cleanup obligations and
disconnected-phone constraint unchanged. Preserve the new immutable raw packet
and source/product identities before any analysis. The frozen V7 supplemental
join remains replay-only and is neither imported nor executed here.

## Host verification

The sealed packet binds the report, this lane's verifier, exact input hashes,
derived analysis, official-reference notes, proposal, and command receipt.
The verifier reads only named files/archives as data, derives the same findings,
and writes no files:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-reference-focus-lifecycle-diagnosis/audit.py verify
```

It does not browse, invoke a child process, query devices or import upstream
Python/Swift code. Host verification establishes packet consistency and the
listed source/evidence facts; it does not prove a native cause or pass a gate.
