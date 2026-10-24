# Private Apple keyboard full-case preparation V2

V2 corrects the two findings in the rejected V1 source preparation. It is sealed
for independent review only. Native compilation and execution remain unselected;
all six application keyboard cases are unrun, native acceptance is pending, and
carrier/GA acceptance remain false. Physical phones remain disconnected.

V1's 81-file producer seal remains
`1e6a0f82dcb65f035abfc8eca3bb7bbe332b1a265553295773e10855276fb8f9`.
Its immutable changes-required review seal remains
`6693e3a4b17768befb418af498e30d06259e7a3c2e3b81c0895540bd7eab4f33`.
V2 binds and rehashes both packets without changing them or relabeling the V1
source pass accepted. The root-accepted V9 setup observation and execution seal
`d5209edf1f03c2282b73c0d2c08b2635bf310364896c7289fa6c88802d875ae3` remain historical
setup evidence; they provide no application-case pass.

The new `runtime_bindings.py` checks a closed selection of 21 runtime source
files and three case-data files. The initial guard is loaded from its fixed
selected path after its bytes are checked. It refuses an outside preloaded owned
module before importing/configuring the selected runtime. This includes the
historical `durable_settings` module whose bytes match V9 but whose origin is
outside the selected snapshot. The exact V9 module is eagerly selected before
its factory's lazy import. Checks compare module file/spec origin and owned code
filenames; a spoofed file/spec cannot adopt historical function/method code.

The guard walks actual transitive module references, validates selected bytes,
checks fixed case-data origins and parsed case tables, and runs before
composition, dynamic selected loads, Bridge construction, each request, and
orchestration entry. A source/data/cache substitution on an existing Bridge
latches its first binding failure and prevents later work even after the cache
is restored. It does not rescan the 2,332 historical input bindings on every
request. The 29-second setup and two-second setup-request bounds remain intact.
This is a selected harness provenance guard, not a Python process sandbox.

V2 uses a new private `orchestration.run`; it does not use the historical
implementation of `h.run`. The new function preserves the selected native
command sequence, arguments, timeouts, simulator ownership checks, baseline
reconciliation, app/runner handling, and Settings/keyboard semantics. It
registers the five cleanup operations before optional result exports. An outer
finally attempts server shutdown, server close, thread join, owned workspace
removal, and owned simulator/baseline reconciliation independently. Optional
export, path-stat, error-report, lifecycle-report, and verdict-report failures
cannot bypass these attempts.

The command record boundary retains receipt failures in memory without replacing
the observed command exit/error. It refuses the next normal command, while
allowing the already-authorized cleanup commands to continue through their real
exit/status and ownership checks. The first primary exception object is retained
through cleanup and raised afterward; cleanup/reporting failures remain visible
in the outcome. Reporting uncertainty disqualifies strict/run success. A failed
cleanup operation remains failed even if its resource was removed and only its
final receipt failed. An unavailable final receipt does not imply successful
qualification; the command still fails and its live final outcome is false.
These controls do not claim power-loss or failed-media recovery.

The original seven-method runner source is unchanged from V1. Its source-tree
digest remains
`946ab559edadd5352912d5747629256a6287d9ca892d5aad0fbd0a7ce4d81e2c`.
All six original application methods/helpers, the proven V7 Settings path,
`DiagnosticTransport.swift`, and `PublicSwitchSelection.swift` remain exact.
V9 Session and TransactionStore, strict keyboard oracle, stable observation
reader, app archives, endpoint grammar, timing/upload/request budgets, measured
setup JSON requirement, and seven-official-method/six-case predicates remain
unchanged. No application or platform engine source was changed or rebuilt.
`v2-runtime.delta.diff` records changes to the private composition, exporter,
summary, and adapted retained controls; new orchestration and origin-guard files
are explicit sources, not changes to the historical snapshots.

The final host matrix passed **57 methods**: nine retained original oracle
methods, four retained strict Bridge/witness methods, 23 retained composition
methods, and 21 V2 correction methods. The final nine HTTP scenarios make 233
real loopback requests. The archive contains 932 requests across retained
attempts, including earlier successful matrices and the disclosed failed control
attempt. These are synthetic host observations and mocked native process
boundaries, not iOS or physical-device receipts.

Origin controls cover every closed module alias preloaded from outside, the
exact historical durable preload, post-composition lazy substitution, spoofed
module metadata with outside code, each selected data-file mutation, case-data
redirection, and sticky rejection through the actual HTTP handler. Reporting
controls port the review's actual composed-run reproduction. They exercise the
real loopback server/thread and inherited owned-simulator cleanup logic with
native/Popen boundaries mocked, command/attachment/result receipt failures,
optional result-path stat failure, all final reporting stages, preservation of
command exit65 and command errors, blocking new normal work, and each cleanup
operation failing after its real action. All five cleanup attempts occur; test
threads/sockets, owned workspaces, and simulated owned instances are absent
before each control finishes.

`host-controls.json` records command, tool version/binary hash, source tree,
stdout/stderr hashes, exit status and elapsed time. The final import inventory
binds 20 actually loaded sources and four import-data reads (three case tables
plus the runtime selection manifest). The complete selected closure contains one
additional source, the preserved offline replay helper, which is bound but not
loaded by normal composition. `provenance.json` binds 2,332 inputs and distinguishes
the inherited revision label from current file hashes; no Git query occurred.
All copied runtime helpers and runner files are rehashed against their original
inputs. Failed control logs remain retained and explained in `attempt-notes.json`.
Owned synthetic scratch was byte/mode verified into its archive before removal.
No compiler, simulator query/boot, UI, physical phone, or other project's process
or data was addressed.

Bounded review entrypoints are `private-contract.json`, `v2-runtime.delta.diff`,
`runtime-selection.json`, `runtime_bindings.py`, `composition.py`,
`orchestration.py`, `attachment_export.py`, `runtime_summary.py`, `test_v2.py`,
`host-controls.json`, `runtime-import-bindings.json`, `provenance.json`, and the
archive manifest. Read-only verification imports no selected runtime code:

```sh
python3 -B verification/apple-toggle-keyboard-full-case-preparation-v2/run.py verify
python3 -B verification/apple-toggle-keyboard-full-case-preparation-v2/verify_isolated.py
```

The second command runs the complete sealed preflight with process creation and
execution of every selected runtime source forbidden. `compile-proposal.json`
and `run-proposal.json` remain separate, unselected proposals. After independent
and root acceptance, a future generic runner build and separately reviewed
post-build execution adapter must bind its fresh product/archive/tool receipts
before invoking the new orchestration. The current CLI exposes verification
only and supplies no native execution authority.
