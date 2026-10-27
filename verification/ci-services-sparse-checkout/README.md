# Services CI sparse checkout

Run 40545367451 at `9398732c23648a82097d5a72b02b1c77af818e41`
shows the services job still in checkout while its fifteen-minute allowance is
being consumed. The preceding VM job exhibited the same fetch problem and its
validated sparse checkout completed in seven seconds, followed by all VM checks
passing. These observations motivate applying input selection to services too;
no services pass or terminal timeout is inferred from an in-progress observation.

Only the services checkout configuration changes. All module verification, vet
and race-test commands, the pinned Go 1.26.4 toolchain and the fifteen-minute job
timeout remain unchanged. The complete `services/` tree includes all Go packages,
testdata, embedded SQL migrations, module locks and package-local fixtures.
`services/protocol/v2_test.go` also reads `../../contracts/release-v2.json`, which
is explicitly included. No root Go workspace or toolchain configuration exists
at the selected source revision. No dependency is added or changed.

The one-shot local audit uses real Git sparse checkout at that exact commit.
All 153 selected files (4,379,716 bytes) match the Git tree and original source
hashes. It runs the existing
`TestV2StaticCrossLanguageVectorAndFrozenDescriptor` test with local Go 1.26.4
and network/module updates disabled. That test passes. A second invocation with
only the external contract removed fails specifically because that file is
missing; its exit 1 and output are retained as the intended negative control.
The exact contract is restored before complete post-check hashes and a clean
tracked-tree check.

`receipt.json` records twelve bounded commands with argv, environment, Python
and Go executable hashes, versions, outputs, exits, elapsed times and exact
owned process-group cleanup. The local Go test is a focused non-race host check,
not the full service race suite. Existing Go module/build caches are preserved;
the owned sparse clone, temporary Go scratch and generated test files are removed.
No PostgreSQL server, hosted harness, product service, device, simulator/emulator,
UI or capture process is launched. The host Go compiler/test subprocesses are
explicitly within this receipt's scope. Remote transfer timing and the entire
changed services job still require CI.
