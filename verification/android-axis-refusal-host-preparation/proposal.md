# Android axis refusal: isolated host-test preparation

Source/data preparation only. Compilation, discovery and all 19 tests are **UNRUN**. This directory selects no tool, host, run, budget, workflow or source pair.

The frozen package has 27 files / 284,605 bytes: the full 21-source SDK22 code closure (5 MixerCore + 16 MixerUI), the exact axis-refusal DocumentSession candidate, unchanged SessionRegistry, three exact test files and one minimal manifest. Its source-row projection is `257ed4dfa93d43b15d4bfe2d51372d261e4fec5fd9e80c3f1ca62b1967a3a793`. The source manifest SHA256 is `601b9722df4f42c6649f0e0b6943fe5e3ad96bc6ebeeeecc186da475875e5782`.

The copied 26 existing files retain exact bytes. Only Package.swift is newly authored. The canonical SDK22 projection, including its original manifest as provenance, remains `bc03288599ece5612cc4dce8b80fc404942584e0477ec9333bd39c0fa7d352d0`. Candidate DocumentSession is `cf1954af12e316bcd7cf8ea4def41d2dc6b26921fffa60177bce477c7f0749b7`; its source manifest is `fb82f04bef4b9ea6cfc2cb2756a95090bc242f8290727139b9b6ba151f941f08`.

The minimal host manifest preserves the original module and test-target names and Swift 6 mode. It declares only MixerCore, MixerUI, MixerAndroidRuntime and MixerAndroidRuntimeTests. The original SDK/engine manifests declare additional product and test targets, so using them would require unrelated source closure. This overlay is a focused behavior check; acceptance of the canonical package topology is a separate later integration obligation.

The required imports are official toolchain modules: PackageDescription, Foundation, Dispatch, XCTest and Swift Testing, plus the local MixerCore/MixerUI/MixerAndroidRuntime modules. There are no external package, Java, Android SDK, JNI, C bridge, native UI, resource file or network dependencies in this host package. The complete file rows, original paths, module dependencies and test names are in source-manifest.json.

## Remote integration proposal

Reuse the existing Swift CI host pattern in .github/workflows/verify.yml: macos-15, explicitly verified Xcode 26.3 build 17C529, its official Swift toolchain, and the existing 30-minute outer job bound. Those are references to an existing pattern; the actual host/tool/run and finite budget must be separately bound. The workflow already executes `swift test --package-path native/android/engine`. No workflow or runner is installed here, and no old process helper is imported or changed.

After separate remote selection, transfer the frozen package, rehash all 27 rows and the source-row projection, record tool provenance using the existing verifier, and run the proposed argv from source-manifest.json:

`<verified-swift> test --package-path <frozen-package> --scratch-path <fresh-owned-host-scratch> --jobs 2`

This is one normal SwiftPM compile/test invocation over the package's only test target, without a filter or skip-build path. Two build jobs is an unselected proposal, not an empirical limit. Retain the exact argv, tool/host provenance, separate raw stdout/stderr, source digests before/after, exit status, selected finite bound and cleanup outcome. Any failed attempt remains visible; this packet grants no retries. Do not execute this proposal locally while the current local compiler/product-runtime hold remains active.

## Exact executable acceptance criteria — pending

- XCTest: all eight named AndroidTextFieldAxisRefusalTests methods pass, zero skipped/failed.
- Swift Testing: all four RuntimeTests methods and seven TransactionTests methods pass, zero skipped/failed.
- Both framework summaries and each exact named result must be retained. A single summary cannot establish the other framework; an eight-test XCTest pass with zero Swift Testing tests is incomplete.
- SwiftPM/compiler success, all 19 methods, unchanged source identity, finite completion and accurate owned cleanup are required. Preserve/classify compiler diagnostics and unrelated tool warnings; exit zero alone is insufficient.

The eight candidate tests cover typed default/horizontal packet equality and accepted edits; raw-horizontal SDK preservation with Android initialization refusal; reducer rollback and original-identity recovery; nested refusal; malformed-axis validation priority; later malformed-sibling priority; vertical refusal; and later vertical-sibling priority. The eleven original tests retain atomic reducer/routing behavior, packet-size and buffer limits, registry ownership, staged commit/abort, stale identity, and concurrent decision behavior. No test was rewritten or converted between frameworks.

The current source pair remains SDK22/adapter23. This package does not select the proposed adapter24, change canonical code, qualify the Java decoder or full source pair, establish native/device behavior, publish FieldLog packages, or satisfy OTA/GA gates. Native/UI/capture and all existing process/custody holds remain binding. No simulator or emulator was started, so this preparation created no native cleanup obligation.
