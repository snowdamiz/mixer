# Compact FieldLog installed guest

Run from the Mixer root on macOS with the installed Swift 6.3.3 toolchain and
Wasm SDK, Xcode Swift, and Rust. Use a fresh output name.

```sh
python3 -B compiler/experiments/fieldlog-installed-guest/run.py fieldlog-installed-guest-check
```

Use `--workspace /path/to/Workspace.swift` to provide the pinned FieldLog
source locally. The runner checks its SHA-256 and otherwise reads the pinned
revision from the FieldLog repository. SwiftPM resolves the existing Mixer SDK
lockfile. The runner keeps binaries, command logs, and the detailed receipt
under the selected `verification/local/` directory.

Pass `--swift-diagnostics` to keep line tables in the two optimized compact
development guests. The runner remaps checkout and home paths and keeps only
the linked `.debug_line` debug section. This lets the installed Swift bridge
display the original file and line when one of these guests traps. The default
run still builds the stripped payloads used by size comparisons.

The host diagnostic replay uses the same compact producer and a fresh build of
the owning VM. Run it from the Mixer root with macOS Swift and the Swift 6.3.3
Embedded toolchain installed.

```sh
python3 compiler/experiments/fieldlog-installed-guest/replay_swift_diagnostics.py local-swift-diagnostics
```

The replay builds optimized Swift traps, checks the source location and native
coordinates, and exercises fallback with the line table stripped or replaced.
It also runs the Swift bridge test suite and checks session retirement. Its
receipt and logs are written to `verification/local/local-swift-diagnostics/`.
Use a fresh output name for each run. The replay uses the SDK's pinned SwiftPM
dependencies and requires no FieldLog checkout or device.

The baseline isolates the completion-bit toggle from FieldLog's
`Workspace.toggleTask` for one seeded inspection task. The review variant
requires a confirmation activation before completing an open task. Reopening a
completed task clears the confirmation. The guest binds the one fixed action
to canonical v1 bytes from the Mixer SDK. This slice has no text-entry or
repository interface. Guest state lasts for the session. The native comparison
compiles the same Swift feature logic and independently checks completion,
progress and outbox behavior through the pinned, unchanged FieldLog Workspace.
Each Workspace toggle must append exactly one task-saved entry for that task
with a new identifier and preserve all existing entries. The review-only
activation must leave the outbox unchanged.

The replay first checks the exact function signatures and export set, one
32-bit unshared memory exported as `memory` at index zero with limits of one
page, and absence of imports and a Wasm start section. It exercises the guard
with in-memory descriptor changes to each compiled guest. The replay input
digest covers the descriptor and command recording helpers.

The host probe uses the canonical Installed Guest UI v1 validator, capability
session worker, exchange and UI reconciler. It compares documents after each
matched activation, checks stale-event refusal and joins native retirement.
Its presentation claims exercise host reconciliation on macOS. The probe
does not observe a native window or commit signed-release health. The paired
full Swift SDK reactor tests the same source against the existing size ceiling.
