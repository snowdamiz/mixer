The five-file [code patch](code.patch) restores the frozen layouts and preserves actual TaskEditor execution. The complete [afterimages](afterimages/vm/src/experimental) contain the tested source. Canonical VM sources remain unchanged against the recorded 140-file baseline closure. The supplied main revision is `046932c3d6bc07f276f1377f6746328ea7ca4b4f`.

`Policy<'a, const COMMAND: bool = false>` selects command ceilings at compile time and retains the original two runtime variants. `SwiftSelection` replaces the proof's policy and optional entry fields with one eight-byte enum. Its command variant carries the checked entry index. The decoder borrows that selection and preserves the command instruction ceiling. No pointer tagging, unsafe code, sentinel limits, allocation, or hash-specific handling is added.

The patch changes these files:

- `vm/src/experimental/policy.rs`: specialize validation limits, define the sealed Swift selection, and check distinct validation and decode ceilings.
- `vm/src/experimental/swift.rs`: select the specialized validator and store the checked entry in the Swift selection.
- `vm/src/experimental/metadata.rs`: pass the compile-time selection through shared metadata validation.
- `vm/src/experimental/validate.rs`: pass the selection through complete body validation.
- `vm/src/experimental/cache/borrowed.rs`: borrow the Swift selection for runtime decoding.

The two exact baseline tests reproduced `Policy=16` and `ValidatedSwiftReactor=680`. Their unchanged assertions now pass in Debug and Release with all features. Debug uses direct `rustc` with optimization disabled and two codegen units. Release uses Cargo with `--jobs 2`. Both measure Meter 88, Metadata 352, BodyState 144, ValidatedSpans 520, Policy 8, and Swift proof 664 bytes on this aarch64 macOS host.

Release passes all 29 command, validator, allocation, and WASI controls, plus the two layout tests and the new policy selection test. The all-feature library compiles through `clippy-driver` with `-D warnings`. Its exact invocation and wrapper are retained. This is Clippy driver verification within the Cargo compilation, rather than a separate `cargo clippy` invocation.

The unchanged 60,877,726-byte R106 module validates all 80,514 bodies and executes `_start` once. Its 439 stdout bytes match the supplied native oracle SHA-256 `3135cb2d45d78106ddda5675c763457df818085394e7c8c63c84ea210d903f22`; guest stderr is empty. All fourteen engine reservation and live-current counters, plus live tickets, are zero after consuming cleanup. The historical WASI usage snapshot retains its construction measurements; it is not a separate post-destruction ledger measurement. The default decoder still refuses the module byte size, and the fixed reactor still refuses 80,514 defined bodies against its 79,966-body allowance.

The command retains its 131,072-function and 16,000,000-static-instruction ceilings. The fixed reactor retains 80,000 total functions and 8,000,000 static instructions. Public signatures, sealed noncloneable command ownership, consuming execution, checked entry selection, full body validation, capability checks, runtime budgets, and cancellation remain intact. Golden layout assertions and default limits are unchanged. No contract is narrowed.

The campaign consumed 35.02 seconds of recorded compiler, test, and guest command time. Three Cargo invocations reached compilation. A fourth Cargo invocation failed before invoking a compiler because the Clippy wrapper used `execv` for Cargo's PATH-relative `rustc`; the one harness correction changed that call to `execvp`. A subsequent implementation compile failure exposed missing decoder and descriptor forwarding methods; those were corrected before the successful checks. Both failures remain in the raw record. One direct Debug `rustc` build and one actual guest payload ran. All recorded owned command groups are absent, with closed output files. Fresh userdata remains available for review at `/Users/andreyyurlov/.t3/userdata/mixer-command-policy-r138-3k3ocqo8`.

The fresh manifest adds `harness = false` only to the existing example so Cargo can compile and execute the actual guest example alongside the selected tests. This test-only manifest change is isolated in [harness-manifest.patch](harness-manifest.patch) and excluded from the code patch. The canonical example and all golden tests remain unchanged.

[result.json](result.json) records source hashes, exact changed files, preservation checks, counters, and scope. [commands.json](commands.json) records every bounded compiler/test command and its custody result. The raw baseline failures, Debug layout output, Release test output, actual guest bytes, and compiler diagnostics are retained beside them. Tool versions are Cargo 1.99.0 `5f94df478`, rustc 1.99.0 `b940084d7`, and Clippy 0.1.99 `b940084d7e`.

One root review of the changed policy boundary remains pending. The broad experimental suite and fresh ordinary CI remain for root. This child performed no Git operations, push, CI actions, device work, signing, delegation, or held-resource access. R104, R118, PGID4463, the immutable R106 input, historical holds, and the independent native R136 lane are preserved.
