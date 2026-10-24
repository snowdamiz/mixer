# First lifecycle runtime: preserved failure

Root selected the exact sealed 132-file accounting candidate for a bounded runtime
matrix. The first Swift Debug configuration compiled and listed the exact 23
lifecycle test names, then ran them single-threaded: **21 passed, two failed,
none ignored; exit 101**. The matrix stopped immediately. No unchanged failure
was rerun, and no broader regression or other profile/feature context ran.

Candidate closure:
`0b36b551e2175aa713d698627493519249b6bfea023f05e13de730e6b06f977f`.
Root runtime selection:
`e6ad507b8484d1f34cef67113022927c5d55a459dd9d9caa9a224088ad7e3287`.

Review `receipt.json`, exact `attempts/swift-debug/` command/output/binary/tool
records, `independent-source-traces.json` and `repair-proposal.md`. The proposal
is unselected and unimplemented. It changes only two future test bodies in
`lifecycle_tests.rs`; production lifecycle/growth/accounting source and all Frozen
methods must remain byte-identical. The constructor lifetime sum and cache-hit
4+6 trace are independently derived from bound source charge sites, not new runs.

All owned command targets were removed after empty-holder/process-group checks.
The original candidate/assertions, both failures, full original planned matrix
and entire authored/remaining coverage ledger remain preserved. No full planned
SL row is complete. SL09 is still family-level; SL12 table mutation remains
unsupported/unimplemented/unrun. Runtime and GA acceptance remain false.

```sh
python3 -B verification/swift-reactor-lifecycle-runtime/verify.py --live
```

Replay reads evidence only. It neither compiles nor reruns tests. The external
document `../../docs/swift-reactor-lifecycle-runtime.md` is bound by the receipt.
`seal.json` binds every other packet file. No sealed/live source, shared tracker,
Git, network, native/device or full 53MB target operation was performed.
