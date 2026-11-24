# UP5 compiled inventory

Run the Section 7.2 replay from the repository root on arm64 macOS with the
Android and full-Swift WASI SDKs from the release toolchain manifest. The replay
uses Swift 6.3.3 with Xcode 26.6 for cross-compilation and the native macOS
build. The recorded iOS 17.0 build used Xcode 27.2 at `/Applications/Xcode.app`.
The replay reads the linked guests with Node's WebAssembly API.
[Toolchain manifest](../../../release/toolchain-candidate.json)

```sh
python3 -B compiler/experiments/swiftui-compiled-inventory/replay.py
```

Open the printed `receipt.json` under `verification/local/`. It contains the
exact command arguments, compiler and standard-library fingerprints, source and
artifact hashes, dependency graphs, and macro output. The replay removes its
build outputs, caches, and raw command logs after it observes terminal process
groups. An unresolved group leaves a `HOLD.json` and retains that run's scratch.

## What the compiler and artifacts reveal

| Fixture | What the replay checks |
| --- | --- |
| S1 compiler fixture | `Title.swift` spells the import `SwiftUI`. The iOS feature resolves that import to the local `MixerSwiftUI` binary module. The iOS shell resolves Apple `SwiftUI` and links its framework. The Android and WASI feature builds resolve the source-built module as `SwiftUI`. The Swift dependency scans record `TitleSupport` through the engine. |
| S2 FieldLog | The two source files contain both Foundation import spellings across conditional branches. The macOS graph resolves `Foundation` directly. The reactor graph resolves `FoundationEssentials` directly. The linker map records the Observation and FoundationEssentials archives. Node's WebAssembly parser validates the emitted reactor and inventories its 32 imports and five exports. The two authored guest files contain no `clock_time_get` identifier. The artifact imports `wasi_snapshot_preview1.clock_time_get`. |
| Observation control | The WASI compiler type-checks `ObservationControl.swift` with S2's `TaskRecord`. The compiler dump shows a generated `Observable` conformance, an `ObservationRegistrar`, and tracked accessors for `record`. Removing `@Observable` causes a type-check error at the `Observable` conversion. The S2 baseline reactor uses its existing explicit registrar. |

The S1 replay uses the existing fixture build function directly. CLI export is
covered by the separate S1 replay. Dependency scans record compiler-resolved
modules and their edges. A module in that graph can have no corresponding
linked code or WASI import. The WebAssembly view covers the emitted import and
export descriptors through Node's parser. Mixer VM profile admission, opcode
policy, capability and resource inventory, and production release authorization
remain separate checks. This host-only experiment supplies partial UP5 evidence.
