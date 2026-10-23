# Borrowed Swift execution descriptors

The canonical scoped receipt is
[`2026-10-23-host-v2/receipt.json`](2026-10-23-host-v2/receipt.json). All 68 recorded
commands passed with complete stdout/stderr and hashes. It qualifies immutable
baseline `bd8a8967d32692765de0d4dd14f5d88b7d5009ff` plus exactly these five source
files, independently of concurrent control/WASI/Android/website changes:

- `vm/src/experimental/descriptors.rs`
- `vm/src/experimental/swift.rs`
- `vm/src/experimental/policy.rs`
- `vm/src/experimental/mod.rs`
- `vm/src/experimental/swift_descriptor_tests.rs`

The candidate's 417-file VM source manifest has SHA-256
`a0570ca8b5785f1039548186f70d829e8648f5bf2ab15060e2944106c2c266b7`.
Rust is `1.99.0 (b940084d7 2026-09-28)`, target `aarch64-apple-darwin`.
The prerequisite contract was frozen before coding in [`contract.md`](contract.md).

Reproduce from the checkout with Python 3 and the recorded Rust toolchain:

```sh
python3 verification/swift-execution-descriptors/qualify.py --output /tmp/mixer-swift-descriptor-recheck
```

The runner extracts the immutable baseline into a disposable directory and
overlays only those five files. It verifies that no other VM input changed,
compares the original proof/public-segment/legacy-getter definitions and policy
semantics, and records every copied source file digest. It never instantiates,
initializes or invokes the 53,777,114-byte Swift target.

Each debug and release run passed six new descriptor tests with the actual public
Swift validator, 70 combined unit tests, 54 public validation/cache/execution and
allocator regressions, 11 doctests, and seven default-feature unit tests. The six
new tests also run with only `experimental-swift-reactor` enabled. Compiler checks
include one public positive control and 22 external privacy/lifetime/mutation/
conversion negatives per configuration. A separate in-crate negative compilation
requires exactly eight `E0515` lifetime errors and six `E0594` mutation errors.

The original same-ABI fixture has 34 real ordered Preview1 imports and 99 small
definitions; it retains the required memory/table/export declarations and passes
complete public validation. Tests cover every absolute import/defined index,
mixed numeric type parameters/results, out-of-range indices, exact module-relative
body/initializer/payload cursors, empty collections, zero-length payload at exact
source end, ordered overlapping segments, explicit segment forms, and preserved
padded/multi-byte element-index LEBs. Thirty-two complete immutable traversals
observed zero allocation, reallocation or deallocation requests and unchanged
source, observations and validation usage.

Baseline and candidate layout assertions agree in debug/release:

| Preserved type | Size | Alignment |
| --- | ---: | ---: |
| Swift proof | 664 | 8 |
| Swift metadata | 384 | 8 |
| Legacy proof | 520 | 8 |
| Frozen metadata | 352 | 8 |
| Signature / global / public segment views | 24 each | 8 |
| Closed policy | 8 | 8 |

Memory reports the sealed minimum 584, absent declared maximum and stored host
maximum 768. Table reports minimum 46,713, declared maximum `Some(46_713)` and
stored host maximum 46,713; its policy ceiling remains 65,536. No proof, metadata
or public `SegmentView` fields/layouts changed. All new descriptors/accessors stay
crate-private. No executable owner, cache/control/WASI behavior, policy variant,
dependency, public method or authority constructor was added.

`2026-10-23-first-source-check` preserves an early verification-harness selector
error: the source comparison selected the public `usage` method instead of the
private helper. Its two baseline layout commands passed. The selector was fixed;
`2026-10-23-host` then passed the full qualification. The final canonical rerun
adds the module ordering required by rustfmt and records its passing format check.

These are host prerequisite receipts, not Swift execution, FieldLog dogfood,
mobile/store, operational or GA qualification. The actual target is unexecuted.
Physical-device checks remain pending while phones are disconnected, and no
device discovery or run was attempted. Allocator observations are thread-local
request observations, not RSS or allocator-overhead measurements. Root must still
perform independent review and source-bound combined integration checks. No
commit, push, publication, credential change or customer message was performed.
