# Owned span execution receipt — 2026-10-23

This is the additive Rust-only `experimental-span-execution` boundary accepted in
`docs/span-execution-design.md`, under the unchanged v1/v2/v3 limits and exact
`mixer.checkpoint` / `mixer.abort` admission. It is executable architecture
qualification for W08. It does not qualify the real Swift reactor, product OTA,
physical iOS/Android behavior, signed package integration, dogfood distribution,
size/performance targets or any GA gate. No phones were contacted.

## Source and reproducibility

Run from the repository root:

```sh
python3 verification/span-execution/collect.py
```

`receipt.json` records every argv, complete stdout/stderr paths and hashes,
versions and executable hashes, revision, initial working-tree status, elapsed
wall time, explicit environment, and per-command source manifests. The final run
used revision `35a9a36c8837fd2dd3e491419b7965b6307cd6b9` plus the uncommitted source
snapshot with digest
`c949b06d37182a4b5a155af649a5baac9ed749ef3e1ec1fd9615c66e2d548bd4`.
Every recorded final command had identical source digests before and after it.
The manifest covers all current `vm/src/**/*.rs`, VM Cargo metadata, original
shared fixture helpers, new executor tests, accepted contract/product documents
and the collector. Unrelated active lanes remain separate and are not claimed as
validated by feature configurations which do not compile them.

Tools: rustc 1.99.0 / LLVM 23.1.1, Cargo 1.99.0, Node v22.23.3, Python 3.14.8 on
`aarch64-apple-darwin`. `CARGO_TARGET_DIR=/tmp/mixer-span-execution-target` is an
ignored external build location, not a source or distribution artifact.

## Observed matrix

Each row passed in both Debug and Release. Counts include applicable doc tests;
existing ignored tests remain ignored, never counted as passes.

| Features | Passed | Existing ignored |
| --- | ---: | ---: |
| default | 91 | 8 |
| experimental-stream-validation | 108 | 9 |
| experimental-function-cache | 122 | 9 |
| experimental-span-execution | 142 | 9 |
| experimental-span-execution,experimental-capability-native | 225 | 9 |

Focused Clippy with `-D warnings` passed for lib, CLI and all three new test
binaries with the combined explicit feature set. `wider-clippy.json` and its logs
retain a separate broader `--all-targets` failure: preexisting
`field_reassign_with_default` and `manual_dangling_ptr` warnings in
`experimental_guest_ui_allocations.rs` / `experimental_guest_ui_validation.rs`.
Those files are outside this lane. All-features integration including the
concurrently implemented WASI experiment remains the root integrator's check.
The existing ignored streaming Node validation oracle was also explicitly run
and passed; its dedicated log does not convert other ignored tests into passes.

## Semantics and bounds exercised

The new tests run 17 tests (15 semantic/resource tests plus one allocator test and
one development Node oracle), plus three public authority compile-fail doc tests.
They use original project fixture encoders, never external implementation or
fixtures. Numeric parity dispatches all 128 scalar opcodes `0x45..0xc4` and all
eight saturating operations, totaling 176 ordinary/edge cases, with additional
NaNs, signed zeros, divide-by-zero, overflow and conversion traps. All load/store
opcodes and widths, control families including branch-table default/selection,
recursive/direct/structural indirect calls, arguments/results, locals/globals,
ordered data/elements, table null/OOB/type traps, memory size/grow/copy/fill,
checkpoint/abort, persistent state and prior-write retention on traps are covered.
Trap codes, function indices and exact source offsets match the frozen eager
interpreter. The explicit differences are terminal-on-first-error and cumulative
fuel/host/work budgets across successful invocations.

The Node oracle compares 69 original probes for values, spec-permitted NaNs,
traps, full linear-memory hash and length. It supplies independent development
observations, not production runtime authority. NaN payload policy remains the
owned numeric profile's canonical arithmetic NaNs and preserved bitwise bits.

Resource probes include preconstruction/predispatch/asynchronous cancellation,
all budget-widening rejections, exact state-byte and old/new growth overlap
boundaries, zero-value arena success when unused, exact aggregate locals plus
operand capacity and cross-frame control capacity, call-depth, instruction,
host-call and lifetime execution/cache-work exhaustion, pin exhaustion, oversized
callee decode, all checked trap cleanup paths and sticky failure replay. Current
frame/value/control/pin counts return to zero after success and terminal errors;
retained memory and arena reservations remain charged until the owner drops.

## Allocation observations

A dedicated integration-test process uses an independently authored observed
system allocator. A mixed memory/table/global/local/branch-table fixture requests
six constructor allocations. Its first invocation requests three cache decode
allocations and one separate new-memory allocation. Requested constructor heap
peak was 462,872 bytes; the first invocation added a requested peak of 131,357
bytes. These observations are below the separately recorded state/cache
reservation peaks; they are requested allocator bytes, not RSS.

Each constructor and initial-invocation allocation ordinal was separately denied
and separately used to trigger cancellation. Every failure returned a typed
static diagnostic and released all owned pins/temporary reservations. Cache
entries retained after a later memory failure remain charged. Reallocations were
zero. A warmed invocation whose declared memory maximum denies growth completed
with zero allocations while the allocator refused its first hypothetical request;
sticky error replay also made zero allocations.

Mutable values, controls and frames use fixed preallocated aggregate arenas.
Callee arguments become locals in place. Every defined live frame retains one
opaque cache pin; the instruction and selected branch-table scalar are copied
before mutation. Memory growth reserves old/new overlap, precharges zero/copy
work, uses a fallible exact new allocation and checks cancellation per 4 KiB
chunk. Declared/host page denials return `-1`; budget/allocator/cancellation
failures stay terminal typed failures. Cleanup performs no allocation, decoding,
cancellation checks or work/fuel spending.

The default execution budget is 16 MiB mutable state reservations, 16,384 combined
live locals/operands, 4,096 combined live controls, and 64,000,000 lifetime work
credits. These fields only narrow. Source, validation metadata/work and cache
costs remain separately reported. Existing profile memory/table, frame, local,
operand, control, fuel and host-call ceilings remain independently enforced.
