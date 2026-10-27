# Original validator failure usage traced independently

The frozen 142-source codec baseline has tree
`58a90a1cec00fd3ffbe4d8bee90476f6e136114dbe3d506da8ab4bbd035b8ecd`.
Only its original validator and fixture were used for this probe; no active loader
files were read. The selected SDK ABI declarations also passed compiler type
assertions in `abi_contract.c`.

Exact source pointers within the frozen baseline:

- `experimental/swift.rs:308-321`: copies original `Usage` source and reservation
  peaks into public `SwiftValidationUsage` without normalization.
- `experimental/swift.rs:323-361`: maps the original typed failure fields and
  preserves its original usage snapshot.
- `experimental/swift.rs:367-374`: calls full validation and maps the failure after
  the private validation call unwinds its local source and metadata owners.
- `experimental/swift.rs:417-438`: reserves fixed scratch, checks the visible input
  limit, reserves the proof owner and source copy before allocation.
- `experimental/swift.rs:440-465`: reserves the complete source capacity, charges
  bounded source-copy work, seals exact-capacity source and reads metadata.
- `experimental/swift.rs:466-468`: verifies full ABI, segments, and every body.
- `experimental/swift.rs:493-504`: releases fixed scratch only on success, then
  returns original owner, usage and observations.
- `experimental/account.rs:112-125`: constructs a failure by copying current usage.
- `experimental/account.rs:157-208`: charges requested reservation before allocator
  entry and updates current/category/combined peaks. These are requested logical
  reservations, not allocator overhead, RSS, stack measurements or cleanup proof.
- `experimental/validate.rs:520-524`: unknown opcode fails before the current body
  completion observation; completed prior bodies have already passed.

An independently generated valid fixture preserves the actual fixed ABI, adds an
8 MiB opaque custom payload, and passes all 29 bodies. A second fixture changes
only body28 (absolute function62) to `[0,255,11]`, causing a genuinely late
Unsupported/`opcode` failure after source copy, metadata/ABI and the first 28
bodies. Both modes report exact late bytes8,390,448 and offset8,390,447, with
source8,390,448, metadata_peak2,300, scratch_peak1,048, total_peak8,393,796 and
work16,787,660. The input SHA256 is
`81b28ffe0b37df1b44837cf1a849c470d2edafff2b6a89c4e0c5189da6287b55`.
These numeric outputs come from direct typed fields, with no Debug-string parser.
Elapsed time is deliberately not treated as deterministic.

The loader must include original success and original failure requested peaks
while its own retained buffers still exist. Summing original source plus separate
metadata and scratch peaks is a conservative upper bound; the original combined
peak can be smaller when category peaks occur at different times. The original
failure object must survive unchanged, including its own usage snapshot. Returning
that snapshot is not a statement that the original validator allocations remain
live after failure, nor proof of successful descriptor closure.

`run_baseline_failure.py` records the compiler, exact argv and per-command output
identities. Every command is bounded to60 seconds/1MiB output; the successful
attempt uses9 commands in Debug and optimized. All owned child processes were
terminally waited and scratch artifacts removed. Two reviewer-only compile
fixture mistakes and cleanup evidence were retained before correction; neither
reached runtime or indicates a candidate defect. Native/device/simulator/emulator,
UI/capture/process inventories and all product/GA acceptance remain excluded.
