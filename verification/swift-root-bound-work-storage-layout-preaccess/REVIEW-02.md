# Frozen v2 correction review

V2 closes strict JSON duplicate handling and the asynchronous launch/cleanup
entry gaps. Release is still deferred for an explicit publication cutoff.

All 16 v2 members and all 173 original members, both seals, membership closure,
byte lengths and tree digests were independently verified. The complete six-file
code delta was reconstructed from exact original/v2 bytes and matches
`correction-delta.patch`. Plan
`ac581da773865faf19b72eef8f2b12d3693b6e691ca910130f4e01f97e241c3d`
preserves source146, diagnostic146, queries, compiler/toolchain, argv, cwd, full
environment and bounds. Original source members and all preaccess stage files
remain unchanged. No producer code was imported or replayed here.

`strict_json.py` rejects conflicting and identical duplicate keys recursively
and rejects nonfinite JSON constants. Diagnostics and custody use it. The
retained 42 producer controls include raw duplicate-key bytes at multiple
depths. `TrackedLaunch` retains the process internally before raising a pending
request; the outer unconditional cleanup reads that internal handle. All four
handlers only record, including during cleanup. No inherited blocked mask or
preexec action is introduced. Explicit work, capture and parser checkpoints
retain the planned deadlines. These address R01 and the launch/cleanup-entry
parts of R02.

One R02 publication gap remains: `record_interruption_failure` runs once before
receipt construction, and `launch.receipt()` copies pending signals before both
runtime files are written. The handlers continue recording until after those
writes. An interruption during publication can therefore be absent from the
written receipt while acceptance remains true. The synthetic finalization
case injects before that snapshot and does not cover publication itself.
Furthermore, the accepted receipt precedes observation publication, so a failed
observation write can leave an acceptance flag without the observation file.

Root authorized an explicit finite cutoff after completed compiler cleanup,
hashes and parsing. A proposed one-way cutoff flag must be set before freezing
pending handler observations: all observed pre-cutoff requests reject; later
observations are explicitly outside that completed observation and only record
and return. Publish the observation before the final accepted receipt. Tests
must inject before cutoff, between cutoff/snapshot, and during both writes,
with the exact finite semantics documented. This avoids promising to retain
signals observed after completion and needs no child-inherited signal mask.

No compiler/runtime or synthetic producer replay occurred. All actual layouts,
diagnostic strategy behavior, prices, backing, peaks, funding, ownership and GA
remain pending. Root alone may release a separately frozen corrected runner.
