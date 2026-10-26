# Independent selected scalar-cursor Rust controls

The exact root-selected `cache_state.rs` source
`f98f7801925bc280e0e2a9c08ec2b4841b7ffc2942d2fedf6c4d3b4c1796bf1b`
compiled and passed seven independently authored host methods in Debug and `-O`
with Rust 1.99.0 on macOS arm64. Each mode executes 16,456 stable merge cases,
2,056 actual semantic G2-admitted/G5 cases, 27 malformed/request refusal cases,
and 21 complete layout measurements. Normal instrumentation observes 320 moves
and at most 289 comparisons across the five later passes. The uninstrumented
seed pairs still perform source work; these counters are not a complete work
bound or replacement for the root-selected conservative source model.

The independently authored sort oracle orders standard-library `(timestamp,
physical slot)` tuples. Its prefix oracle uses `u128` sum/subtraction, without
calling a producer model or reusing G5's `u64` arithmetic. Every eligible slot
occurs once, every absent result is byte 255, and the timestamp, eligibility,
unrelated Candidate bytes, and the arena's resident/pin regions remain intact.
The merge corpus includes empty/full masks, all singletons and complements,
every pair and missing pair, four exhaustive eight-bit windows, random full
masks, stable ties, and ordinary `u64::MAX` timestamp data.

Actual semantic calls include full-u64 totals, MAX-sized resident/request,
checked base/request boundaries, full pinned and unpinned occupancy, sparse
victims, and arbitrary generations. One accepted private state deliberately
uses duplicate nonrequested identities and two equal-nonce tokens referencing
the same pinned row while another row retains pins. G2 admits that aggregate-
consistent state, and G5 matches the independent oracle. The nonunderflow
argument needs the checked total and distinct eligible physical rows; it does
not assume a per-row token bijection. Malformed occupied/pin/reserved/function/
size/count/total/token/nonce states and invalid request arithmetic all refuse
with their expected reason and preserve the complete arena.

The base closure's 570 members (15,387,058 bytes) and the independent sealed
source review's 54 members were verified before copying. All three library
files and necessary original tests/oracles are copied from frozen C3; only
`cache_state.rs` is replaced with the selected source. The compiler derivative
is exactly that full selected source followed by an 89-byte `cfg(test)` module
declaration. The selected prefix hash, full derivative hash, suffix text, every
compiled source/test hash, commands, compiler version, PID/PGID, timestamps,
60-second deadlines, raw outputs, and output hashes are retained.

The 84 embedded original methods compile but are filtered out of this
independent seven-method execution. Their expectations are unchanged, including
the two obsolete private merge fixtures. The producer owns the two explicitly
approved adaptations and reruns the complete embedded/regression/API/File
corpus. This packet does not reinterpret filtered tests as passes.

All five commands passed in 9.671 seconds total; the longest child took 7.173
seconds. Both binaries were hashed before removal and all five children returned.
No scratch directory, native runtime, UI automation, capture process, process
inventory, or Git command was started. No other lane's files were written.

The selected source retains historical comments saying "UNSELECTED", "Never
compiled or run", and six instrumented passes/384 moves/321 comparisons. Those
comments are stale after this host run, but the immutable selected bytes remain
unchanged. The receipt and source hash define the accepted implementation scope.

Root bound the final producer seal `efc43d467a112522b40b4113bb21aa13086c0669d9d911707a85a148e3d4037c`.
Independent producer-seal and raw-receipt review passed; `review.md` and
`final-decision.json` accept the isolated Rust host implementation component.
This component acceptance does not select canonical integration,
a broader/full target, arbitrary public File admission/reachability, physical
phones, Swift/native runtime, signing/store/customer/operations, immutable
published-package FieldLog dogfood, or any GA gate. Native runtime, capture and
UI remain paused. Logical/source-model bounds remain the independently selected
conditional argument, not measured stack/ABI/allocator/RSS evidence.

The read-only producer audit preserved three reviewer authoring failures before
its successful final run: a narrow diagnostic allowlist initially omitted E0451,
then E0432/E0061; a later check assumed pre-compaction baseline byte paths rather
than following frozen C3 content manifests. Exact auditor versions and errors
are retained under `evidence/audit-attempt1..3`. Neither the selected source nor
the producer packet changed. The final auditor follows and verifies each
content manifest; no producer runner/checker was imported or executed.
