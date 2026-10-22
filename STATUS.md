# Implementation status

Product status: **in development; no GA or dogfood gate passed**.

The repository began with only the product plan on October 22, 2026. It now has
an owned Swift SDK and native adapters, Rust interpreter, local release service,
native Swift signature verifier, CLI, and a separate FieldLog repository.
`work-graph.json` retains every W01–W18 package; all G01–G38 and D0–D8 gates remain
open. Implemented slices do not replace their complete acceptance requirements.

Observed implementation and evidence:

- Swift state/effects, generation-checked resources, bounded UI documents,
  reconciliation and native Apple controls pass host tests and iOS compilation.
  Raw UI decoding requires strict duplicate-key/Unicode/resource validation.
  An independently checked generated iOS consumer builds and runs in a dedicated
  simulator; this is not physical FieldLog D1 acceptance.
- The Android Swift/JNI/native widget adapter runs on a physical Pixel 8 Pro.
  Instrumentation and real input/touch paths verify text, task creation, toggles,
  stable IDs and stale-event rejection. See `native/android/verification/receipt.json`.
- The dependency-free owned Wasm interpreter executes the bounded integer-v1
  profile. Independent review includes differential numerical/control/memory and
  malformed-input checks. Full Swift artifacts are rejected. Numeric-v2 support
  is being implemented without expanding integer-v1 acceptance silently.
- The Go development service verifies canonical signed artifacts and separately
  signed rollout assignments, with scoped authorization, durable local state and
  retry/replay tests. It refuses production mode. Local HTTP → Swift verification
  → owned integer VM integration checks both iOS and Android metadata scopes.
- The Swift verifier uses pinned standard cryptography and matches Go signature,
  canonical-CBOR and cohort vectors. The verifier executable runs on the physical
  Pixel and rejects replay. This is protocol evidence, not mobile OTA activation.
  Independent review fixed cross-verifier authority, strict pinned configuration
  decoding and bounded reads. The reviewed binary passed the physical retest.
- The CLI creates source-locked projects, builds/tests host packages, generates and
  runs iOS simulator apps, inventories migration concerns and exports source.
  Local update verification snapshots bounded inputs so signatures and executable
  validation examine identical bytes. Publication remains unavailable.
- `../fieldlog` is a separate repository with native SwiftUI screens, durable
  offline drafts/outbox, projects/checklists, photos and report sharing. Baseline
  commit `1587d2d4f02ab2dad9914df97f878727dd622296` builds, installs and launches on
  the physical iPhone 12. Isolated UI workflow tests are in progress. Authentication,
  backend synchronization and real user adoption are not implemented or simulated.
- Actual FieldLog models at that immutable revision produce matching observations
  on macOS, the physical Pixel and the full Swift Wasm SDK in a development oracle:
  1,000 tasks, 50% progress, ordering, Unicode draft restoration, entry commit and
  report generation. The 60.5 MB Wasm module is rejected by the owned VM; neither
  full Swift execution nor production package-size budgets have passed.

Official Swift 6.3.3 Android/Wasm SDKs are installed and compiler probes have run
on a physical Pixel and in a development-only Node WASI oracle. Xcode 27.1 / Swift
6.4 builds Apple targets. Cross compilation uses Xcode 26.6's matching macOS SDK
through per-command `DEVELOPER_DIR`; no global Xcode selection was changed.

The critical next dependencies are actual FieldLog model/feature compiler closure,
the full owned Swift execution profile, typed native capabilities, broader native
UI/lifecycle behavior, and durable device update activation/recovery. Hosted
PostgreSQL services, isolated builds/signing, stores, console/commercial features,
independent security/operational reviews, users and paid pilots remain mandatory.
There is no remote CI or production deployment receipt and no GA claim.
