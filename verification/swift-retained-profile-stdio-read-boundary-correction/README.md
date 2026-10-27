# Complete reads on the last permitted attempt

The frozen C01 stdio correction could read the complete requested byte sequence
on attempt 32 and still raise `stdio-read-attempts`. Its loop checked completion
only at the start of an iteration. This isolated correction adds one completion
check after that loop. It performs no additional read and changes neither the
32-attempt limit nor the 512-byte request cap.

The source patch changes only `RawStdio.read`. Acquisition, close ownership,
quarantine, child argv/lifecycle, original errors, retained results and all other
source bytes remain unchanged. The old source is copied from the verified
659-member packet, whose complete custody and digest sidecar were checked before
copying. That packet remains immutable.

`run_checks.py` records 90 fresh bounded commands. Sixteen independently specified
read-boundary cases run against each source. The old source retains three expected
failures for the same R03 defect: 32 one-byte reads, a full 512-byte request completed
in 32 chunks, and 31 controlled interruptions followed by one complete read. All
16 cases pass against the correction. Other cases cover zero/one/31 attempts,
EOF on the last attempt, interruptions exhausting the budget, invalid request
types/sizes and unfinished reads that would require a forbidden 33rd call.

The observations use real, successfully opened raw temporary descriptors. The
test shim only shortens actual `os.read` requests or raises a labeled controlled
`InterruptedError`. It does not fabricate returned bytes. Each owned descriptor
is closed once through its current owner; all direct boundary cases finish healthy.
The test never retries an uncertain saved descriptor number.

The unchanged 26-method composition suite and 307 snapshot mutations pass against
the new source. All 57 unchanged stdio cases pass, including the actual fixed-child
primary/result and mixed cleanup joins. Five of these cases finish healthy; 52
retain their explicit synthetic close/path obligations. Terminally reaping the
containing child does not resolve those model obligations. The separate 142 prior
retained-wrapper lifecycle cases were not repeated for this one-line read change;
their previous passing evidence remains in the original packet.

A short nonempty read on attempt 32 is still rejected when it does not satisfy the
requested length: observing EOF would require another call. In particular, a
fixed child's report smaller than 512 bytes after 31 interruptions does not earn
acceptance merely because the child has exited. The unchanged EOF requirement and
attempt cap remain explicit.

All started check processes were bounded and terminally reaped, and all owned
scratch directories are empty. No native runtime, device, simulator, UI, capture,
process inventory, canonical source, index, publication, commit or push is part of
this correction. Independent review is pending. Real Rust binding/provenance,
8192-context/accounting, canonical/full-target integration, native, FieldLog,
OTA and GA acceptance remain separate obligations.
