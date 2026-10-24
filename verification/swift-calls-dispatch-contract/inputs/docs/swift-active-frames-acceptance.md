# Private active-frame implementation acceptance

Root accepted the private host frame slice on October 24, 2026, after the user
resumed implementation. The accepted 119-file VM tree is
`4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4`.
The historical implementation/review documents and seals remain unchanged.
Their pause-era pending-root language is superseded by this decision.

[Root acceptance](../verification/swift-active-frames-root-review/acceptance.json)
binds 2,148 inputs and observations. Root read the actual original-owner
preflight, entry/rollback, return, indexed pin drain and fixed-storage completion
methods and their changed value/consuming-cleanup barriers. The independent
[resume audit](swift-active-frames-resume-audit.md) checks the exact worktree,
full producer/reviewer seals, compiler layouts and 229 command origins.

Saved executions comprise 904 producer candidate tests across four feature/build
configurations, 682 independent candidate tests, 40 independent adversarial
probes, eight producer layouts and two independent fresh layouts. Of 229 producer
command records, 204 are explicitly reused and 25 fresh. Final runtime results
originate from the exact 4f16367b source; the older f10e candidate is excluded.
Root performed source and saved-evidence review at resume, without rerunning
compiler or test binaries. Existing committed 6df4807 CI passes all jobs but does
not qualify this previously uncommitted candidate; new CI follows delivery.

The production header is 1,378,536 bytes and frame-operation bound 1,049,448;
State is 424 bytes. These are logical ownership budgets, not machine-stack
measurements. The original 119,576-byte value component and public default
ceilings stay unchanged. Narrower valid budgets may reject during construction.
Broad Clippy still reports 26 baseline diagnostics. AF15's capacity rejection is
an explicit derived defensive injection.

This acceptance permits dependent source development. Public invocation,
instruction dispatch and initialized reactor state remain absent. Native runtime
checks remain paused and physical-phone final qualification remains pending.
Separate-repository immutable FieldLog packages, signing, store/customer and
operational evidence remain required. No GA or dogfood gate is verified.
