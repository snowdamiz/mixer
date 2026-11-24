# UP5 native state and document replay

Run the host replay and the iOS 17.0 compile check from the Mixer checkout root.

```sh
compiler/experiments/swiftui-native-core/HostReplay/run.sh
compiler/experiments/swiftui-native-core/HostReplay/run.sh release
compiler/experiments/swiftui-native-core/HostReplay/run.sh ios
```

The runner builds the checked-out `MixerCore`, `MixerUI`, and `MixerSwiftUI` sources. It compiles the shared fixtures in a separate package namespace with the `SwiftUI=MixerSwiftUI` module alias. The host executable checks snapshots, change sets, and callbacks through the package API. Pass `typed-controls`, `typed-environment`, `ordinary-modifiers`, or `layout-refusals` after a host mode to run that probe alone.

The `ios` mode compiles the same shared fixtures for `arm64-apple-ios17.0` against MixerSwiftUI and Apple SwiftUI using the installed iPhoneOS SDK. It also checks that Apple SwiftUI compiles the authoring in [UnsupportedControls.swift](HostReplay/UnsupportedControls.swift) and [UnsupportedEnvironment.swift](HostReplay/UnsupportedEnvironment.swift) and that MixerSwiftUI rejects each marked line. The runner prints the compiler version, Git revision, and input digest. It removes its build directory under `verification/local/` on exit.

## Host contract

Create a `FeatureSession` for each mount and use it and its bindings from one serial executor. Each session allocates its own mount identity. A frame token combines that identity with a frame ordinal. The renderer captures the token and SDK event envelope together when it installs a callback.

`prepare` builds a fresh view value and stages its state, reconciler, and handlers. Every change set uses the accepted presentation as its base. A new prepare invalidates the previous candidate even when the new build fails. The renderer supplies `.drawnAndInputReady` to `finish` after the exact candidate becomes visible and can receive input. A successful receipt promotes the entire candidate. A failed or canceled receipt for that candidate discards it.

Pass the host's normalized `UIAppearanceEnvironmentV2` to `prepare(environment:_:)` for each candidate. The session copies its scheme and direction into the candidate. Event callbacks read the environment of their accepted frame and view scope, including when a nested mount runs on the same executor.

`dispatch` checks the accepted frame token and routes the envelope through the accepted SDK snapshot. Accepted input invalidates any pending candidate and returns that candidate's token in `DispatchOutcome`. When a failed or invalidated candidate still owns the renderer's speculative display, the host can restore `acceptedPresentation`. A late receipt for that candidate leaves newer work alone. `detach` closes the mount and retires all its tokens.

## Supported subset

The author API covers struct views, result-builder groups and branches, `Text`, `VStack`, `Button`, and array-backed `ForEach` with `Int` or `String` keys. The evaluator discovers direct stored `@State` fields before the body and admits `Int`, `Bool`, and `String` values. A binding projected from state can write during its accepted frame's event turn. Until then, writes to current-frame state during body evaluation invalidate the build. Bindings from earlier frames, unbound projections, and idle contexts have no write authority. An invalid event write rolls back all engine state changes in that event. Side effects on references captured by author code are outside the state transaction.

| Shared authoring | SDK document contract |
| --- | --- |
| `HStack` | Top, center, or bottom alignment. Explicit spacing accepts finite values from 0 to 256. A nil spacing leaves the choice to the renderer. |
| `List` and `Section` | Builder children become list rows or section content. A section can omit its title or supply a string title or a single plain `Text` header. |
| `TextField(_:text:)` | A single-line field with a string label. A `.textChange` event assigns the string payload. |
| `Toggle(_:isOn:)` | A toggle with a string label. A `.valueChange` event assigns the Boolean payload. |
| `@Environment(\.colorScheme)` and `@Environment(\.layoutDirection)` | Typed reads in view bodies and routed actions. The fallback values are `.light` and `.leftToRight` for omitted host input and unbound reads. |

Pass each control a binding projected from the current build's `@State`. The evaluator rejects unbound bindings and bindings from other frames. Control input uses the accepted frame's event scope and the existing string state limit. The replay covers Unicode edits, both Boolean values, keyed row moves, malformed envelopes, and accepted state after a candidate is canceled.

The environment slice exposes reads for these two keys. Subtree modifiers need a document and renderer contract for scoped appearance and layout. Other keys, custom environment storage, and presentation preferences remain outside this slice.

`.disabled(_:)` disables the emitted subtree when passed true. A transparent view that emits multiple roots disables each root, and a descendant's `.disabled(false)` leaves any ancestor restriction in place. The reconciler enforces that restriction when routing input.

`.accessibilityLabel(_:)` and `.accessibilityHint(_:)` store verbatim strings on a single emitted `Text`, `Button`, `TextField`, or `Toggle` node. A container target, zero or multiple emitted nodes, or a repeated property on the same node fails preparation. The document validator still applies its string limits. These three modifiers preserve the underlying view's identity and state.

The engine bounds each build to 4,096 view visits, 64 path components, 128 fields per view, 128 UTF-8 bytes per state declaration, 1,000 rows per loop, 256 UTF-8 bytes per string key, 1,024 state cells, 1,024 UTF-8 bytes per string state value, and 1,024 handlers. The SDK validator applies its configured document limits.

The replay supplies renderer outcomes in a macOS process. iOS runtime behavior, platform drawing, package and project wiring, asynchronous state, row paging, tier 1, the GC work, and signed schema admission require later slices.
