# Mixer Swift SDK development slice

This package independently implements an initial W03/W04 slice. It is not a GA
release, a complete UI inventory, or evidence of native/guest parity. It has no
third-party package dependencies. Implementation uses Swift's standard library,
Foundation, SwiftUI and the platform Swift Testing library.

The product plan's section 8.3 requires the same app design on iOS and Android,
driven by a shared theme. The current authoring schema and Apple/Android controls
do not yet implement that appearance contract; native default styling is an
implementation gap. Platform-specific app appearance must be explicit. Native
accessibility, navigation, text input and system-owned surfaces retain platform
behavior. Side-by-side physical reference-screen review remains pending.

The package uses Swift 6 language mode and declares iOS 17 and macOS 14 minima.
The checked-in receipt records the actual toolchain used; declaring an OS minimum
does not qualify every OS release or device in that range.

## Public products

| Product | Current public behavior |
| --- | --- |
| `MixerCore` | Main-actor `FeatureStore<State, Action>` reducers, named async effects, cancellation/replacement ownership, lifecycle state machine, host `ResourceRegistry` generation handles, schema-1 `NavigationState` restoration, bounded `JSONInputGuard`. |
| `MixerUI` | Explicit-ID result builder, scalar Codable UI document, bounded strict decoder/validator, transactional reconciliation, stable node generations, current-owner event routing. |
| `MixerApple` | `MixerUIHost` and `MixerNativeView` rendering validated nodes with native SwiftUI layout, text, button, toggle, text field, list, section and navigation-root controls. |
| `MixerGuest` | The same owned UI document codec. It does not compile or execute a Swift Wasm guest. |

## Author and present a screen

```swift
import MixerUI
import MixerApple

@MainActor
func makeEditor() throws -> MixerUIHost {
    let document = MixerUI.Navigation("root", title: "FieldLog") {
        MixerUI.List("editor") {
            MixerUI.Section("notes.section", title: "Entry") {
                MixerUI.TextField("entry.notes", "Notes", value: "Roof access clear",
                                  action: "entry.notes.changed", onSubmit: "entry.save")
                    .accessibilityLabel("Inspection notes")
                MixerUI.Toggle("entry.done", "Complete", value: false,
                               action: "entry.done.changed")
            }
            MixerUI.Button("entry.save", "Save draft", action: "entry.save")
        }
    }.document(revision: 1)
    return try MixerUIHost(document: document)
}

// In a SwiftUI body, hold the host as a StateObject/ObservedObject:
// MixerNativeView(host: host, onAction: { action in
//     switch (action.actionID, action.value) {
//     case let ("entry.notes.changed", .string(notes)): /* send typed action */ break
//     case let ("entry.done.changed", .bool(done)): /* send typed action */ break
//     case ("entry.save", .null): /* enqueue a durable save */ break
//     default: break
//     }
// }, onEventFailure: { error in /* report rejected stale input */ })
```

Use `MixerUI.UIDocument` explicitly in files importing SwiftUI/UIKit: UIKit also
defines `UIDocument`. SwiftUI and MixerUI also share common control type names;
qualify those names as in the example.

The app owns its logical state and action types. `FeatureStore` must receive
`try store.transition(.start)` before `try store.send(action)`. Its reducer returns
`[Effect<Action>]`, with `.run(id:operation:)`, `.cancel(id:)` and `.cancelAll`.
An operation asynchronously returns an optional action. Translate failures into
typed actions inside the operation. Reusing an effect ID replaces and cancels its
previous owner. Ignoring cancellation cannot deliver a replaced result. Stopping
the feature cancels all owned work and permanently rejects further actions.

Observers get value snapshots on the main actor, including the current state when
registered. Remove their UUID token when observation ends. Reentrant dispatch from
an observer/reducer is rejected explicitly. `awaitCurrentEffects()` waits for the
currently owned batch, not subsequent effects started by its actions.

After state changes, build a document with a strictly larger revision and call
`try host.update(document)`. An invalid batch leaves the current displayed tree
intact. Native events include the captured revision and generated node identity;
the current host verifies them, resolves the current node's action binding and
validates the event value before invoking the app callback. Removed or replaced
nodes, old revisions and disabled ancestors cannot dispatch actions.

## UI contract and limits

The wire contract is [`contracts/ui-v1.json`](../contracts/ui-v1.json). A document
has `schemaVersion`, `revision`, and `root`; each node has `id`, `kind`,
`properties`, `children`, and `actions`. All fields are required on the wire.
Properties are scalar `UIValue`s. There are no serialized callbacks or native
selectors. Unknown fields, node kinds, property names, event types and schema
versions fail closed. A validator can further restrict the supported node kinds.

Raw JSON must enter through `UIValidator.decode`, `UIDocument.decode`, or
`GuestUICodec.decode`. They preflight the original bytes before Foundation decoding:
duplicate object keys reject even when Unicode escapes or surrogate pairs encode
the same decoded key. Malformed UTF-8, unpaired UTF-16 escapes, JSON syntax errors,
trailing data and excessive resources reject without repairing or rewriting input.
Key equality uses decoded UTF-8 byte sequences with no Unicode normalization.
The JSON guard does not canonicalize or authorize a release.

Codable encoding remains available. Direct external `JSONDecoder` decoding of
`UIDocument`, standalone `UINode` or `UIActionBinding` throws `unguardedDecoder`:
a `Decoder` has already discarded duplicate raw-key information, so only the
sanctioned path receives the internal preflight marker. A Boolean user-info flag
cannot bypass that marker. Construct values in memory with their public
initializers and validate them before rendering.

`MixerCore.JSONInputGuard.validate(_:limits:)` is a reusable additive guard for
other wire consumers. It bounds total bytes, container depth, total JSON values,
decoded key/string bytes, and 256 bytes per numeric token. The UI raw decoder derives
its JSON container-depth bound as twice its UI-node depth plus two and its value
bound as forty times its UI-node count plus sixteen. The normal UI validator then
enforces schema-specific node, property, identifier, action and child bounds.

Default limits are 1 MiB per encoded message, 4,096 total nodes, 64 levels including
the root, 1,000 children per node, 128 UTF-8 bytes per identifier, 16 KiB per property
string, 16 properties per node and four actions per node. IDs are unique across
the document. Identifiers reject ASCII controls/DEL. Wire encode/decode enforce
the exact message size; validating an in-memory tree also bounds its aggregate
content size. Decoder depth/node/child limits apply while constructing the tree.
`UIValidationLimits` supports bounded host-specific limits; invalid configurations
are rejected rather than used.

All nodes support disabled state and accessibility label/hint/value/identifier.
Text supports four styles, selection and line limits. Button has normal,
destructive and cancel roles. Text-field values dispatch `.textChange` strings
and optionally `.submit`; toggles dispatch `.valueChange` booleans. Buttons
dispatch `.activate` with null. Stack spacing/alignment values are validated.
Native accessibility roles, text input and scrolling come from their platform
controls; custom accessibility actions, announcements and focus APIs are absent.

Reconciliation reports insertions, removals, kind replacements, scalar/action
changes and movement separately. Reordering within a native collection preserves
the generated identities. A native view reparented across different containers may
be recreated by SwiftUI even when its logical ID survives; retained focus/scroll
and native resource behavior need platform-specific qualification.

## Navigation and resource ownership

`NavigationState` is a bounded, schema-1 value stack of `NavigationRoute` values
with stable IDs, names and string parameters. `encoded()` and
`restore(from:maximumBytes:)` round-trip those values; restoration rejects future
schemas, duplicate route IDs and oversized state. This initial native
`Navigation` UI node hosts exactly one root. It does not yet drive destinations,
sheets, tabs, deep links, interactive back or process-recreation UI behavior.

Host resource registries require a host-chosen session-unique owner ID. Handles
contain owner, slot and generation. Releasing and reusing a slot invalidates old
handles; foreign owners and closed registries reject access. There is no guest
capability registry or authorization inference from holding an arbitrary token.

## Verification and remaining surface

Run `python3 sdk/verification/verify.py --ios` from the repository root to reproduce
the host tests and unsigned iOS-arm64 cross-build. The script writes command,
toolchain, source digest, scope, exit code and full output under
`sdk/verification/current/`. It fails if source files change during verification.
The default run omits the iOS cross-build when `--ios` is absent.

The current tests exercise reducer behavior, lifecycle rejection, effect
replacement/cancellation (including operations ignoring cancellation), resource
ownership, versioned restoration, malformed wire input, limits, 1,000-row logical
identity/reorder, typed event ownership, atomic host updates and a macOS SwiftUI
rendering smoke test. Strict-JSON regressions additionally exercise escaped-key
collisions, surrogate pairs, malformed Unicode/UTF-8, raw Codable bypass attempts,
syntax/resource bounds and the maximum supported 128-node nesting depth. These are
implementer-run host tests. They do not qualify
physical iOS/Android interaction, VoiceOver/TalkBack, IME composition, keyboard,
retained scroll, frame performance, crash recovery, signing, store distribution
or an independently published FieldLog package consumption run.

Still unsupported: Android adapter, Swift Wasm compilation/execution/runtime
imports, native/guest effect parity, dependency tracking/observable environment,
property-wrapper bindings, localization services, secure fields, slider/stepper/
picker/progress, form focus validation, grids/adaptive/safe-area APIs, pagination,
refresh/swipe gestures, images/assets/shapes/transitions, custom gestures,
destination navigation, and all section-9 native capability families. Unknown UI
operations reject rather than display placeholders. SwiftUI view construction
currently uses type erasure; no latency, memory or frame-rate budget is claimed.
W03 and W04 remain in progress until their full acceptance evidence is available.
