# UP5 native state and document replay

From the Mixer checkout root, run the host replay with Swift 6:

```sh
compiler/experiments/swiftui-native-core/HostReplay/run.sh
compiler/experiments/swiftui-native-core/HostReplay/run.sh release
```

The runner builds the checked-out `MixerCore`, `MixerUI`, and `MixerSwiftUI` sources. It compiles [SharedScreen.swift](HostReplay/SharedScreen.swift) in a separate package namespace with the `SwiftUI=MixerSwiftUI` module alias. The host executable calls the package API and verifies the resulting snapshots, change sets, and callbacks. The runner prints the compiler version, Git revision, and input digest. It removes its build directory under `verification/local/` on exit.

## Host contract

Create a `FeatureSession` for each mount and use it and its bindings from one serial executor. Each session allocates its own mount identity. A frame token combines that identity with a frame ordinal. The renderer captures the token and SDK event envelope together when it installs a callback.

`prepare` builds a fresh view value and stages its state, reconciler, and handlers. Every change set uses the accepted presentation as its base. A new prepare invalidates the previous candidate even when the new build fails. The renderer supplies `.drawnAndInputReady` to `finish` after the exact candidate becomes visible and can receive input. A successful receipt promotes the entire candidate. A failed or canceled receipt for that candidate discards it.

`dispatch` checks the accepted frame token and routes the envelope through the accepted SDK snapshot. Accepted input invalidates any pending candidate and returns that candidate's token in `DispatchOutcome`. When a failed or invalidated candidate still owns the renderer's speculative display, the host can restore `acceptedPresentation`. A late receipt for that candidate leaves newer work alone. `detach` closes the mount and retires all its tokens.

## Supported subset

The author API covers struct views, result-builder groups and branches, `Text`, `VStack`, `Button`, and array-backed `ForEach` with `Int` or `String` keys. The evaluator discovers direct stored `@State` fields before the body and admits `Int`, `Bool`, and `String` values. A binding projected from state can write during its accepted frame's event turn. Until then, writes to current-frame state during body evaluation invalidate the build. Bindings from earlier frames, unbound projections, and idle contexts have no write authority. An invalid event write rolls back all engine state changes in that event. Side effects on references captured by author code are outside the state transaction.

The engine bounds each build to 4,096 view visits, 64 path components, 128 fields per view, 128 UTF-8 bytes per state declaration, 1,000 rows per loop, 256 UTF-8 bytes per string key, 1,024 state cells, 1,024 UTF-8 bytes per string state value, and 1,024 handlers. The SDK validator applies its configured document limits.

The replay supplies renderer outcomes in a macOS process. Platform drawing, package and project wiring, typed environment, asynchronous state, row paging, tier 1, the GC work, and signed schema admission require later slices.
