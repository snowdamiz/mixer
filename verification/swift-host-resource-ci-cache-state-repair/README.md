# Context fixture setup correction

The isolated proposal changes only `context_schema_scalar_reserved_and_lengths`
in the CI pack's independent fixture source: construct one `Fixture::new()`
baseline, then clone it in the existing three loops. The 23 scalar, 976 reserved,
and four length cases retain their exact bytes, labels, order, fresh per-case
files, analyzer invocation, report assertions, and cleanup. The baseline contains
only byte vectors. It owns no File handles or cursors. All case clones have
independent allocations. Production analyzer and library sources are unchanged.

This removes 1,002 repeated initializations of the same 80,000 profile rows.
Every case still copies and writes its complete profile. It does not establish
performance equivalence, a specific speedup, or future CI timing.

`proposal/fixture-baseline-clone.patch` is the complete proposed correction.
`proposal/independent_tests.rs` has SHA-256
`7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411`.
The canonical frozen pack was unchanged during this lane's qualification; root
owns any subsequent provenance amendment, member/tree/manifest repin and delivery.

The preserved CI failure is run 40507305688, attempt 1, source
`c4d04e56d0175f4c036c878db5ccb7bd9c7b30f0`, Rust 1.98.1 on macOS arm64.
`producer-debug-root-03` timed out at 60 seconds and exited -9. Its owned group
was gone and scratch cleanup succeeded. Only final case
`1002-context-length-8193` remained, with stream/profile/context bytes and an
empty report. Because the original `run` helper removes each preceding case
after its assertions, this is evidence that 1,002 preceding cases completed.
It does not isolate every component of elapsed time or prove a deadlock.

`qualify.py` independently encodes the baseline and all case context bytes in
Python. Its stream, profile and final context match the immutable retained CI
bytes exactly. It compiles the exact proposed source, checks the complete
producer method list, and runs only the focused context method. A second
instrumented derivative compares all 1,003 cases byte-for-byte, checks all four
initial file cursors and empty report files, then observes the original per-case
cleanup. It adds controls that reject changed/truncated inputs, incorrect labels,
case order and framing expectations. The instrumented source preserves every
original analyzer/report assertion; its three inserted observations and appended
controls are outside the proposed patch.

`runs/focused-2/receipt.json` records local Rust 1.99.0, commands, exact source and
compiler identities, raw output hashes and scope. The exact proposed context
method passed once in 49.552365 seconds; its instrumented counterpart passed
once in 55.779036 seconds. The negative controls passed. Active work took
111.163977 seconds. Each child retained the 60-second limit, active work the
600-second limit, and cleanup its separate 60-second limit. Both owned compiler
products were hashed before removal; all owned child groups were gone and
scratch was removed. These are observations of two different focused binaries,
not repeated timing trials.

`runs/focused-1/receipt.json` remains a failed pre-compiler observation: the
inherited PATH contained no `rustc`. The second run explicitly selected the
existing Rust 1.99.0 compiler, with no installation or toolchain fallback.

Recheck the retained bytes with `python3 -B
verification/swift-host-resource-ci-cache-state-repair/audit.py`. The audit uses
the original immutable incident archive, so root can subsequently amend the
canonical pack without changing this baseline. `audit.json` binds the exact and
instrumented source trees and confirms that the proposal preserves original
assertions. The original qualification harness itself expects the original pack;
reproducing it requires the recorded original source revision and retained pack.

A fresh full 103-command run and actual Rust 1.98.1 CI evidence remain pending.
No broad hosted suite, native runtime, simulator/emulator, UI automation, capture,
physical device, signing/store, public V2, dogfood release or GA qualification ran
or is implied. The original CI failure remains a failed observation.
