# Apple keyboard full-case independent source and host review

The V1 preparation requires changes before source acceptance. This review binds
producer seal `1e6a0f82dcb65f035abfc8eca3bb7bbe332b1a265553295773e10855276fb8f9`
and its 81 sealed files. It does not select compilation or native execution.

Two actionable findings were reproduced against the actual composition:

1. **P1: final result reporting can bypass all resource cleanup.** The inherited
   `harness.py` lines 374–380 exports the final summary/tests before constructing
   its cleanup operations. If a result-export command cannot record its receipt,
   the exception handler calls `commands.record` again without guarding that
   reporting failure. An unavailable command-receipt sink therefore escapes the
   `finally` block before line 381. The independent test uses the actual composed
   `h.run`, a real loopback server/thread, and mocked native/process boundaries.
   All five inherited cleanup operations were skipped; the thread remained live
   and its synthetic capability workspace remained present. The reviewer then
   shut down/closed the server and joined the thread. The scratch workspace is
   archived and removed by the review collector. Evidence:
   `cleanup-failure-reproduction.json`, `cleanup-recovery.json`, and
   `controls.stderr` in the review packet. A new composition/orchestration
   boundary must attempt all five operations even when official-result export
   and its reporting fail, and preserve the first session exception.
2. **P2: lazy transitive imports escape snapshot-origin enforcement.**
   `composition.py` lines 26–28 checks six directly imported module origins.
   `settings_telemetry.diagnostic_bridge` later imports `durable_settings`
   without checking its origin. Preloading the unchanged historical V9 module
   under that ordinary import name lets composition succeed and a new bridge
   instantiate its outside-snapshot `TransactionStore`. The historical bytes
   happen to match the snapshot in this probe, but the promised runtime source
   origin boundary is unenforced. Evidence: `preloaded-durable.json` and the
   bounded `preloaded-durable` mode in `controls.py`. Fail closed on the complete
   transitive runtime source set before configuring the harness, including lazy
   imports; do not rely on the normal-path inventory to enforce this boundary.

Both producer verification entrypoints pass. The independent normal and repeated
legacy-loading import inventory exactly matches the bound 18 source files and
three case-data files. All 2,175 input bindings are verified by the real sealed
preflight. The fresh review runs 26 passing host test methods: nine retained
original oracle controls, four retained actual Bridge/witness controls, and 13
independent controls including the two expected negative reproductions. Passing
the negative reproductions confirms defects, not source acceptance.

Independent real loopback controls exercise every setup handoff checkpoint,
the 29-second setup limit, pending uploads, wrong/stale/duplicate records,
outstanding retirement/uncertainty, duplicate or unfinished app cases, and late
start/mark/observe/chunk writes. Setup has only the setup test-case completion
marker at handoff, with V9 suite/bundle completion still incomplete. Export
controls execute the canonical composed Commands after two actual legacy
wrapper loads; exactly one export occurs and the first success or failure
receipt stays immutable. Existing attachment output is refused, missing setup
JSON receives no setup credit, and failed receipt fsync blocks a readable
success receipt. Verdict controls require all seven exact official methods and
all six case cursors/verdicts together with setup, export, and cleanup evidence.

The review executes the sealed original oracle/witness controls unmodified,
redirecting only their host temporary root into owned review scratch and
retaining it for archival. Its HTTP record builder reuses `fixtures.py` with one
disclosed scratch-path substitution; `fixture-adapted.py` is retained. These
fixtures contain synthetic data and the native command boundary is mocked.
No compiler, Xcodebuild, simulator/frontend query, screen capture, computer use,
or physical-phone operation was executed. No producer collector was executed.

The first independent attempt failed because the import-audit comparison
included its own later inventory-file read, and the review's fake selected
process did not create its synthetic result directory. Those review controls
were corrected; raw failed logs and code remain in `attempt-1`. The second
attempt confirmed both findings; its logs remain in `attempt-2`. The final
attempt additionally runs the 13 retained oracle/witness controls. These
bookkeeping corrections did not alter producer files or relax a product rule.

`commands.json` retains exact host argv/cwd, Python version/binary hash,
elapsed time, return code, and stdout/stderr hashes. `source-contract.json`
records immutable source comparisons and input identities.
`synthetic-host-evidence-manifest.json` records the byte/mode-verified archive;
`cleanup.json` records owned scratch removal. `review-seal.json` binds this
document, the final receipt, all review source/log/evidence artifacts, and the
producer identity. V1 producer bytes remain unchanged. Physical phones remain
disconnected and deferred; all six application native cases, carrier acceptance,
and GA acceptance remain pending/false. Root owns any next-stage selection.
