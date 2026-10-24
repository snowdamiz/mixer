# Integrated private Swift bulk-memory checkpoint

The reviewed original-owner copy, fill and MemorySize operations are now integrated
in the live VM. This is scoped host development acceptance. Full dispatch, memory
growth, host imports, Ready/public invocation, native targets and GA remain open.

The reviewed 125-file candidate closure is
`e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626`.
The integrated closure is
`96c945a817c81be17fb526067d87cc667a21cdaf5a47be18179e10fe5ed8de0d`.
Their only difference removes four spaces from each otherwise blank line 1050 and
1051 of `experimental/execution/mod.rs`. The exact normalization patch, rejected
whitespace preflight, both manifests and nine applied paths are retained. The
reviewed and normalized sources are not described as byte-identical.

The private actual-pinned caller uses the existing result slot, original frame,
cache, control and WASI owners. It checks slot vacancy before effects, ends the
cache view before execution, charges instruction/work and advances PC once.
The shared Frozen copy/fill body retains checked ranges, overlapping-copy
semantics, bulk debit and bounded chunk cancellation effects. MemorySize uses the
original observed page count and typed/live-accounted push. Original first failure,
terminal drain and explicit cleanup retry remain intact. No public capability or
new implementation dependency was introduced.

Producer evidence includes 312 selected executions across four configurations,
64 Frozen differential pairs, 64 Frozen integration selections, 16 paired layouts,
eight library checks and CI Clippy. Independent review adds 64 fresh candidate
selections and 12 independently authored selections, four fresh compiler MIR
inventories, four fresh layout runs and exact identity for 39 Frozen methods and
14 containing owners. Remaining producer evidence is reused with exact bindings,
not relabeled as fresh review execution. Historical producer/reviewer harness
failures remain preserved and excluded from successful evidence.

All 4,800 accepted memory positions remain exact and 4,324 new bulk positions are
accounted. The 1,672 old unit canonical labels change only by the independently
checked containing-module qualification. The production/unit bulk active additions
are 642,456/1,206,544 bytes, and the permanent addition is 121,856 bytes. Complete
frame envelopes are 3,478,968/6,299,432 bytes; existing State/Combined limits remain
128/256 MiB with 86 tickets. These are named-object accounting bounds, not RSS or
compiler-stack measurements.

Root ran the normalized live source on aarch64 macOS with Rust/Cargo 1.99.0:
78 focused bulk/memory/frame/value/control tests and 16 Frozen integration tests
pass in serial all-feature Release; the Swift-only CI Clippy command passes with
warnings denied. Whitespace passes. The owned Cargo scratch was removed after an
empty open-holder check. No native instance or physical phone was used by these
host commands.

The read-only replay command is:

```sh
python3 -B verification/swift-bulk-memory-root-integration/verify.py --live
```

Memory growth and its original ticket borrow are the next isolated implementation
slice. Full supported Swift execution, actionable source diagnostics including
G08's absent-cursor Cleanup case, cross-platform native joins, immutable published
FieldLog consumption from a separate repository, final phone testing, signing,
store, customer, operational and GA acceptance remain pending.
