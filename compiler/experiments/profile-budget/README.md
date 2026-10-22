# Full Swift FieldLog size and memory diagnostics

The smallest measured candidate preserves the established FieldLog model observations and the full Swift 6.3.3 WASI SDK, but is still **52,008,982 bytes raw and 18,852,048 bytes gzip9** (mtime0). Its compressed complete-module size is **5.993 times 3MiB**, or 15,706,320 bytes above that diagnostic comparison. No VM resource ceiling was changed. No full Swift owned-VM, device, UI, effect or OTA gate is qualified by this experiment.

The [matrix receipt](evidence/2026-10-22-qualified/receipt.json) records every command, tool version/identity, duration, immutable source/harness/package identity, SDK archive inputs, binary/compressed identity, full model observation object, inventory and attribution. Implementation selection was gpt-6.1-sol/xhigh; this is not independent review. [DESIGN.md](DESIGN.md) records the approved scope and matrix. The source digest for the matrix executable analysis/design files plus the reused owned command recorder is `667c63ec140a86f738c71904c95a05f40406dfcc327eef33489b7b6fb614fa23`.

| Variant | Raw bytes | gzip9 bytes, mtime0 |
| --- | ---: | ---: |
| Pristine supplied release artifact | 60,505,739 | 20,066,881 |
| Fresh ordinary release | 60,506,066 | 20,066,950 |
| Release + objcopy strip-debug | 60,257,830 | 19,985,970 |
| Release + objcopy strip-all | 53,787,147 | 18,973,797 |
| Osize + gnone + explicit WMO | 60,250,673 | 19,989,226 |
| Osize + objcopy strip-debug | 60,250,673 | 19,989,226 |
| Osize + objcopy strip-all | 53,778,053 | 18,976,503 |
| Osize + explicit section GC | 60,250,673 | 19,989,228 |
| Osize + linker strip-debug | 60,250,673 | 19,989,227 |
| Osize + linker strip-all | 53,777,902 | 18,976,357 |
| Osize + linker strip-all + compress-relocations | **52,008,982** | **18,852,048** |

SwiftPM release already supplies `-O`, whole-module optimization and `--gc-sections`. Explicit GC therefore provides a control, not a new reduction. Osize changes the app/model compilation; it does not rebuild the precompiled SDK. Small module-hash differences affect gzip by a few bytes; no timestamp or metadata rewriting was used to hide them. This is the smallest tested option combination, not a global minimum or a representative p95 patch measurement.

All eleven executable variants matched the **complete established observation object**, as did a fresh native build: 1,000 tasks, 5,000 completion basis points, successful Codable round-trip and Unicode preservation, reordered tasks, one committed entry, 1,503 pending changes, empty-title and repeated-commit rejection, and report contents. The model/harness source was unchanged. This comparison covers that corpus, not every public API behavior or a full app. Node WASI was a development-only oracle with argv0, empty environment and no preopened directories. Seven original metadata-boundary/attribution tests pass.

The frozen app source is FieldLog `1587d2d4f02ab2dad9914df97f878727dd622296`; its Git archive SHA-256 is `3f64fd8ff770a5f5e3a233d7170cccdc54c27ea0abb6a273948b260399e291eb`. The unchanged corpus harness SHA-256 is `344168377051c105e60eb84388c54d48c2259224157ac68a1f877ac36a8e7c59`. The pristine Wasm SHA-256 remains `3308fc08ae16bd7247be67b14bd7ea8af754c2610641d517936aa5570f325964`. The smallest candidate SHA-256 is `19ac88f26f0daf34b64acb3c5b895fc79b52701368fc4c532ac8ede5844fee75`; its gzip SHA-256 is `a38f38bac0cccc866dbb8bbe5432c710d3c779dcab0e1afa9a74806b2f70218c`.

The [release link-map attribution](evidence/2026-10-22-qualified/release-attribution.json) identifies **33,976,096 bytes** in the SDK's `lib_FoundationICU.a(icu_packaged_data.cpp.obj):(.rodata.icudt76_dat)`, about 90.1% of the **37,712,880 active data bytes**. This exact immutable data payload matches the official archive member, SHA-256 `7ca4d8abf60fbc0b25e57dc658b8c4c4236774d0c78fff601d3cad2dccd59dd9`. In isolation it compresses to 13,316,652 bytes; that component measurement is not additive compressed accounting and is not subtracted from complete-module totals. The linker trace records `udata.cpp.obj` referencing `icudt76_dat` and the packaged object defining it. Retention under section GC is evidence of a linked dependency; it does **not** prove every packaged locale/Unicode record is individually needed or safely removable. No SDK data or behavior was removed, split into an excluded asset, or replaced by native logic.

The ordinary release attributes 15,746,061 bytes of function input contributions to code. Only 121,191 of those bytes (about 0.77%) belong to the FieldLogModels and corpus objects. Other major inputs include SwiftCore, FoundationEssentials, Foundation, CoreFoundation, FoundationInternationalization and the SDK's ICU code/data. The link map separately identifies 382,248 bytes of zero-fill allocations; these are not compressed active-data payload. Input contribution totals exclude alignment and binary framing; use the binary section measurements for module totals.

Every variant declares **584 initial memory pages = 38,273,024 bytes (36.5MiB)** and no explicit maximum. Node observed **625 pages = 40,960,000 bytes after the corpus**. These are linear-memory observations, not process RSS, total app memory or native-versus-OTA overhead. The explicit `--max-memory=4194304` experiment fails linking with `maximum memory too small, 38273024 bytes needed`. The existing owned VM's 64-page/4MiB ceiling is unchanged. The plan's ≤30MiB added steady-state memory budget requires an actual native/OTA app comparison; these diagnostics do not pass it.

Ordinary release has 79,823 defined functions, 5,271 globals and 6,510,037 body instructions. The Osize/compressed candidate has 79,837 defined functions and 6,505,962 body instructions; all still exceed the unchanged VM function/global/instruction quotas, as do raw bytes and initial memory. The table's 46,700 entries fit the bounded v3 table ceiling. All 34 WASI imports remain unsupported by the current owned execution profile. Every inventory invocation uses the experiment's pinned VM executable SHA-256 `960e0ab684259d307d3100a3878488dcd261fbbb13d12c04bf40ea8d59f3e70c` and records strict rejection; metadata inspection remains non-authorizing.

The [same-path clean rebuild control](evidence/2026-10-22-qualified/rebuild-control/receipt.json) produced byte-identical raw and gzip artifacts and repeated the complete model observation comparison. Original build artifacts/maps were restored and hash-checked. [Different-root diagnostics](evidence/2026-10-22-qualified/reproducibility.json) found 32 changed bytes in the two app-owned `.swift_modhash` entries; path-independent compiler reproducibility is unqualified. Two early attempts completed model comparisons but failed final metadata cross-checks; their local evidence is retained under ignored `local/*/failed-matrix-evidence`. The final receipt was rerun end to end from corrected measurement code.

The metadata corrections are explicit: installed llvm-objcopy rejects a dump of the input contribution name `.rodata.icudt76_dat` because this Wasm object exposes a core DATA section. That unsupported command and stderr remain in the successful receipt. An original bounded reader measures the official llvm-ar object's single active DATA segment instead. Also, this lld map's DATA file offsets omit five framing bytes; extraction maps the symbol's **linear-memory address through decoded binary segments** and verifies the archive payload hash. A dedicated test prevents using the diagnostic map file offset as an extraction offset. This reader does not validate or authorize executable modules.

Strip-debug removes source debugging information. Strip-all also removes the function-name section; the smallest candidate has neither original source maps nor a qualified debugger. This loss remains unresolved and is not a production recommendation. The required embedded SDK data remains counted. Package layering, caching or deltas would need a separate compatibility/resource design and honest required-runtime transfer accounting.

To repeat, use an unused name (outputs are created exclusively):

```sh
python3 -B compiler/experiments/profile-budget/run.py --name another-run
python3 -B compiler/experiments/profile-budget/rebuild_control.py --receipt compiler/experiments/profile-budget/evidence/another-run/receipt.json
```

The runner requires the exact supplied pristine artifact, the separate FieldLog repository with the pinned commit, installed Swift 6.3.3/full WASI SDK, Xcode26.6 selected per command, existing Node and Python standard library. Build directories, maps, SDK object extractions and binaries remain in ignored owned `local/` directories; committed receipts bind their identities and reproduction commands. No added dependency, global toolchain selection, existing compiler qualification script or VM source change was made.

Recorded native build wall time was 12.277 seconds and the six Wasm build commands ranged from 3.534 to 6.051 seconds on this Mac during development; the same-path smallest rebuild took 4.305 seconds. These are command-duration diagnostics, not CPU benchmarks, warm-loop p95, interpreter performance or release acceptance measurements. Installed tool/SDK input hashes identify observed bytes; full toolchain/SDK source-build attestation remains outside this experiment. The 3MiB comparison is a quantified residual gap, not a reviewed product-budget revision.
