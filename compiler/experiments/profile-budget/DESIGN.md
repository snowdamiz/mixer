# Full Swift FieldLog profile-budget experiment

Scope: preserve FieldLog commit `1587d2d4f02ab2dad9914df97f878727dd622296`, the unchanged established FieldLog corpus harness, Foundation/Codable/Unicode/error semantics, and the official full Swift 6.3.3 WASI SDK. This is a compiler/model experiment, not guest UI/effect/OTA or owned full Swift execution qualification. No Embedded Swift, application substitution, native escape hatch, or VM ceiling changes.

The product plan section 20.2 proposes p95 compressed patch size at most 3MiB over a representative dogfood change corpus, including required guest runtime code, and at most 30MiB added steady-state OTA memory above native mode. One model executable cannot establish either p95 or application RSS; compare its complete-module transfer size and static linear-memory requirement as explicit diagnostic gaps. A WASI command executable is not yet the final MixerGuest feature-module package.

Measured variants:

1. Re-execute and identify the frozen original release artifact; establish the exact expected model observation object.
2. Fresh ordinary SwiftPM release build, verbose compiler/link commands and linker map. Inspect default optimization/WMO/GC choices.
3. Release plus `-Osize -gnone -whole-module-optimization` for application/model compilation. The precompiled full SDK remains unchanged.
4. Variant 3 plus explicit `--gc-sections` as a control: installed official wasm-ld help says GC is already enabled by default.
5. Official llvm-objcopy strip-debug and strip-all over fresh artifacts, and linker strip variants. Preserve the final target-features custom section; compare output/import/semantic observations, not merely link success.
6. Smallest supported size candidate plus `--compress-relocations` and stripped debug, which official lld documents as required for relocation compression.

Every executable variant runs the unchanged corpus through Node's development-only WASI preview1 implementation with argv0, no environment entries or preopened directories, and exact strict JSON observation comparison to native and frozen Wasm runs. The complete established observation object covers 1,000 tasks, 500 completions, Codable round-trip, Unicode preservation, reorder, committed entry, 1,503 pending changes, validation/repeated-commit rejection and report contents. It does not prove every application behavior.

Capture source/archive/harness/package/tool/SDK-input/binary hashes, compiler and linker flags, link-map attribution, section/body/data/table/memory quantities, raw and gzip9 bytes, command duration, and complete output logs. Durations are build/tool wall time, not performance measurements. Keep artifacts/maps/build directories in ignored local output; commit machine-readable identities, compact attribution, observations and source manifests. Preserve exact reproduction commands. No VM source is changed; its read-only inventory remains non-authorizing.

Use only installed official Swift/LLVM tools, Node's existing development oracle and Python standard-library evidence processing. No added dependency. Installed tool/SDK hashes identify observed bytes; they do not establish full source-build or supply-chain attestation.

Official references: [Swift Wasm SDK](https://www.swift.org/documentation/articles/wasm-getting-started.html), [lld WebAssembly](https://lld.llvm.org/WebAssembly.html). Installed compiler/linker `--help` output is the version-specific option authority. Do not switch the pinned compiler because current online examples use a newer release.
